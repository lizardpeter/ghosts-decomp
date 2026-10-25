"""The high-resolution clock, the render time and the presentation's mode table (docs/cgame-frame.md 4.1, 4.3,
stage 1: enhanced/win32/win_clock.cpp, enhanced/client_mp/cl_render_time.cpp, enhanced/cgame_mp/cg_present.cpp and
the own view in enhanced/cgame_mp/cg_view_step.cpp).

What must hold:
- the clock: Sys_Milliseconds is floor(microseconds since the first read / 1000) of QueryPerformanceCounter, and gives
  the same values as the original Sys_Milliseconds does from a timeGetTime that reads the same milliseconds; the
  enhanced sub_140316290 writes exactly what the original writes (cls.realtime, cls.frametime, frametime_base,
  frame_msec, old_com_frameTime, the flags) and keeps cls_realtimeUs = 1000 * cls.realtime + the clock's distance
  past com_frameTime (0..999 µs);
- the render time T_r: cl.serverTime + the fraction while the client's time runs with cls.realtime; monotonic; in
  [cl.serverTime, cl.serverTime + 1) apart from the slew; a correction of the client's time (+1, -1, -2 ms: a delta
  nudge or a held cl.serverTime) leaves T_r continuous and is put back within one snapshot interval; a large one
  (300 ms) jumps;
- (c) other entities: at 2.5, 4.17 and 6.94 ms frames cg.frameInterpolation advances by exactly delta T_r / the
  snapshot interval each frame (the original's alternates), and an entity's position (the original
  CG_InterpolateEntityPosition) by speed * delta T_r, within float rounding; with no fraction it is the original bit
  for bit;
- (b) the own view (whole frames through the enhanced CG_DrawActiveFrame's tick loop): the drawn origin is the partial
  Pmove to floor(T_r) plus velocity * (T_r - floor(T_r)), the drawn angles this frame's; with T_r on a command time
  and no fraction, the original angle rule;
- (d) one switch per category: flipping the other entities' mode changes cg.frameInterpolation and nothing of the
  own view; flipping the own view's changes the drawn view and not cg.frameInterpolation; INTERPOLATE for the own view
  draws the canonical prediction.
"""
import math
import random
import struct

from harness import TLS_BLOCK
from syms import va
from frame_sim import (CL_SERVERTIME, CLS_REALTIME, CG_NEXTSNAP, CG_SNAP, CG_TIME, TickGame, World, rd, wmem)
from win32_display import arg

MS = "?Sys_Milliseconds@@YAHXZ"
US = "?Sys_Microseconds@@YA_JXZ"
CLOCK = "?sub_140316290@@YAXHM@Z"
RENDER = "?CL_RenderTime@@YANXZ"
INTERP = "?CG_SetFrameInterpolation@@YAXW4LocalClientNum_t@@@Z"
LERP = "?CG_InterpolateEntityPosition@@YAXPEAUcg_s@@PEAUcentity_s@@@Z"
CL_SNAPTIME, CL_OLDSNAPTIME = 0x3484, 0x34C0
CG_INTERP = 0x71888
SNAP0 = 0x00500000 + 0xC0000
SNAP1 = 0x00500000 + 0xC8000
CENT = 0x238


def _i(v):
    return struct.pack("<i", v)


class Qpc:
    """QueryPerformanceCounter/Frequency as import stubs reading a script."""

    def __init__(self, frequency, counts):
        self.frequency, self.counts, self.i = frequency, list(counts), 0

    def install(self, m):
        def qpc(mu):
            mu.mem_write(arg(mu, 0), struct.pack("<q", self.counts[min(self.i, len(self.counts) - 1)]))
            self.i += 1
            from unicorn.x86_const import UC_X86_REG_RAX
            mu.reg_write(UC_X86_REG_RAX, 1)

        def qpf(mu):
            mu.mem_write(arg(mu, 0), struct.pack("<q", self.frequency))
            from unicorn.x86_const import UC_X86_REG_RAX
            mu.reg_write(UC_X86_REG_RAX, 1)
        m.on_import("kernel32.dll!QueryPerformanceCounter", qpc)
        m.on_import("kernel32.dll!QueryPerformanceFrequency", qpf)


def _clock_reset(world, env=None):
    world.poke(va("sys_timeBasesInitialized"), _i(0))
    if env is not None:
        world.poke(env.data("sys_qpcInitialized"), _i(0))


def _qpc_run(env, world, q, symbol, ret):
    value, _ = world.call(symbol, [], lambda w: q.install(w.m), {}, ret=ret)
    return value


def test_milliseconds_from_qpc(env):
    """The first call reads the base, then every call one count: ms and µs since the base, floored."""
    for frequency in (10_000_000, 3_579_545, 2_400_000_000, 1000):
        r = random.Random(frequency)
        base = r.randrange(0, 1 << 40)
        counts = [base]
        for _ in range(120):
            counts.append(counts[-1] + r.choice([0, 1, frequency // 1000, frequency // 997,
                                                 r.randrange(0, frequency // 10 + 1)]))
        q = Qpc(frequency, [base] + counts)
        world = World(env)
        _clock_reset(world, env)
        for k, c in enumerate(counts):
            if k % 2:
                assert _qpc_run(env, world, q, US, "int64") == (c - base) * 1_000_000 // frequency, (frequency, k)
            else:
                assert _qpc_run(env, world, q, MS, "int") == (c - base) * 1000 // frequency, (frequency, k)


def test_milliseconds_same_rule_as_the_original(env):
    """The original Sys_Milliseconds with a timeGetTime that reads the same milliseconds returns the same values."""
    r = random.Random(51)
    frequency, base = 10_000_000, 123_456_789
    counts = [base]
    for _ in range(100):
        counts.append(counts[-1] + r.choice([1, 5_000, 9_999, 10_000, 166_667, 41_667, 69_444]))
    tgt0 = 0xFFFF0000  # near the 32-bit wrap, as timeGetTime can be
    ours, theirs = World(env), World(env)
    _clock_reset(ours, env)
    _clock_reset(theirs)
    q = Qpc(frequency, [base] + counts)
    for k, c in enumerate(counts):
        mine = _qpc_run(env, ours, q, MS, "int")
        ms = (c - base) * 1000 // frequency

        def setup(w, ms=ms):
            def stub(mu):
                from unicorn.x86_const import UC_X86_REG_RAX
                mu.reg_write(UC_X86_REG_RAX, (tgt0 + ms) & 0xFFFFFFFF)
            w.m.on_import("winmm.dll!timeGetTime", stub)
            theirs.apply(w)
            if k == 0:  # the original's first call reads its base and now: both tgt0 + 0
                pass
        value, _, written, _ = env.machine.call(env.table[MS], [], "int", setup, {}, {})
        theirs.mem.update(written)
        assert mine == value, (k, mine, value)


def _clock_fakes():
    noop = lambda mu: None
    return {s: noop for s in ("?R_SyncGpu@@YAXP6AH_K@Z@Z", "?IN_Frame@@YAXXZ", "?sub_14054B4B0@@YAXH@Z",
                              "?sub_14017A6C0@@YAXPEAUDataValidation@@H@Z", "?sub_140223CE0@@YAXXZ",
                              "?sub_140191F80@@YAXXZ", "?sub_14018F6C0@@YAXXZ")}


def test_client_clock_writes_the_originals_and_microseconds(env):
    r = random.Random(316)
    frequency = 10_000_000
    cls = va("cls")
    us_var = env.data("cls_realtimeUs")
    for _ in range(150):
        realtime = r.randrange(0, 1 << 30)
        frame_time = r.randrange(1000, 1 << 30)
        old = frame_time - r.choice([0, 1, 7, 16, 250, -3])
        msec = r.choice([1, 7, 16, 50, 100])
        now_us = frame_time * 1000 + r.choice([0, 1, 499, 999, 1000, 4000, -2000])
        flags = (r.choice([0, 1]), r.choice([0, 1]))

        def setup(w):
            w.write(cls + CLS_REALTIME, _i(realtime) + bytes(flags))
            w.write(va("com_frameTime"), _i(frame_time))
            w.write(va("old_com_frameTime"), _i(old))
            w.write(va("sys_timeBasesInitialized"), _i(1))
            w.write(env.data("sys_qpcInitialized"), _i(1))
            w.write(env.data("sys_qpcBase"), struct.pack("<q", 0))
            w.write(env.data("sys_qpcFrequency"), struct.pack("<q", frequency))
            Qpc(frequency, [max(0, now_us) * 10]).install(w.m)
        args = [msec, ("f", msec * 0.001)]
        _, _, mine, _ = env.call(CLOCK, args, "void", setup, _clock_fakes())
        _, _, theirs, _ = env.machine.call(env.table[CLOCK], args, "void", setup,
                                            {env.table[s]: f for s, f in _clock_fakes().items()}, {})
        mine_us = b"".join(mine.pop(us_var + i, b"\0") for i in range(8))
        mine = {a: v for a, v in mine.items() if not env.dll.base <= a < env.dll.base + env.dll.size}
        assert mine == theirs
        past = min(999, max(0, max(0, now_us) - frame_time * 1000))
        assert struct.unpack("<q", mine_us)[0] == (realtime + msec) * 1000 + past


class RenderClock:
    """Drives CL_RenderTime frame by frame: cls.realtime, cls_realtimeUs, cl.serverTime and the snapshot times."""

    def __init__(self, env, start_us=100_000_000, interval=50):
        self.env, self.world = env, World(env)
        self.t_us = start_us
        self.delta = 0
        self.server_time = None
        self.interval = interval
        self.results = []

    def frame(self, period_us, delta_change=0, hold=False):
        self.t_us += period_us
        realtime = self.t_us // 1000
        self.delta += delta_change
        new = realtime + self.delta
        if self.server_time is None or not hold:
            self.server_time = new if self.server_time is None else max(self.server_time, new)
        cls, cl = va("cls"), va("clients")
        w = self.world
        w.poke(cls + CLS_REALTIME, _i(realtime))
        w.poke(self.env.data("cls_realtimeUs"), struct.pack("<q", self.t_us))
        w.poke(cl + CL_SERVERTIME, _i(self.server_time))
        snap = self.server_time - self.server_time % self.interval
        w.poke(cl + CL_SNAPTIME, _i(snap))
        w.poke(cl + CL_OLDSNAPTIME, _i(snap - self.interval))
        value, _ = w.call(RENDER, [], lambda w: None, {}, ret="double")
        self.results.append((self.server_time, self.t_us % 1000 / 1000.0, value))
        return value


def test_render_time_is_server_time_plus_fraction(env):
    for period in (2500, 4167, 6944, 1000, 16667):
        c = RenderClock(env)
        for _ in range(60):
            c.frame(period)
        for server, frac, value in c.results:
            assert value == server + frac, (period, server, frac, value)
            assert server <= value < server + 1
        assert all(b[2] > a[2] for a, b in zip(c.results, c.results[1:]))


def test_render_time_slews_small_corrections(env):
    for change in (1, -1, -2, 2):
        c = RenderClock(env, interval=50)
        for _ in range(20):
            c.frame(4167)
        before = c.results[-1]
        c.frame(4167, delta_change=change)
        after = c.results[-1]
        # continuous: T_r advanced by the frame's real time, not by the correction
        assert abs((after[2] - before[2]) - 4.167) < 0.002, (change, before, after)
        # put back linearly within one snapshot interval of real time
        for _ in range(13):
            c.frame(4167)
        server, frac, value = c.results[-1]
        assert abs(value - (server + frac)) < 1e-9, (change, c.results[-14:])
        values = [v for _, _, v in c.results]
        assert all(b > a for a, b in zip(values, values[1:]))


def test_render_time_held_server_time(env):
    """cl.serverTime held (the new time would go back): T_r goes on with the real time and catches up."""
    c = RenderClock(env)
    for _ in range(20):
        c.frame(1000)
    c.frame(1000, delta_change=-1)    # cls.realtime + 1, cl.serverTime held
    assert c.results[-1][0] == c.results[-2][0]
    assert c.results[-1][2] > c.results[-2][2]
    for _ in range(60):
        c.frame(1000)
    server, frac, value = c.results[-1]
    assert value == server + frac


def test_render_time_jumps_on_large_corrections(env):
    c = RenderClock(env)
    for _ in range(10):
        c.frame(4167)
    c.frame(4167, delta_change=300)
    server, frac, value = c.results[-1]
    assert value == server + frac


def _snapshots(world, t0, t1, a, b):
    """Two snapshots at t0 and t1 and an entity moving from a to b between them (stationary trajectories)."""
    cg, ents = va("cgArray"), va("cg_entitiesArray")
    world.poke(SNAP0 + 0x3C7C, _i(t0))
    world.poke(SNAP1 + 0x3C7C, _i(t1))
    world.poke(cg + CG_SNAP, struct.pack("<QQ", SNAP0, SNAP1))
    e = ents + CENT * 5
    world.poke(e + 0x94, struct.pack("<iii3f3f", 0, 0, 0, *a, 0, 0, 0))
    world.poke(e + 0xB8, bytes(0x24))
    world.poke(e + 0x104, struct.pack("<iii3f3f", 0, 0, 0, *b, 0, 0, 0))
    world.poke(e + 0x128, bytes(0x24))
    world.poke(e + 0xFC, _i(4))
    return e


def _interp_frames(env, period_us, frames=40, mode=None, lead=None):
    c = RenderClock(env)
    if mode is not None:
        c.world.poke(env.data("cg_presentMode") + 4 * 2, _i(mode))
    if lead is not None:
        c.world.poke(env.data("cg_presentExtrapolateMsec"), struct.pack("<d", lead))
    cg = va("cgArray")
    out = []
    for _ in range(frames):
        c.frame(period_us)
        t0 = c.server_time - c.server_time % 50
        cent = _snapshots(c.world, t0, t0 + 50, (0.0, 0.0, 0.0), (190.0 * 0.05, 0.0, 0.0))
        c.world.poke(cg + CG_TIME, _i(c.server_time))
        c.world.call(INTERP, [0], lambda w: None, {})
        c.world.call(LERP, [cg, cent], lambda w: None, {})
        frac = struct.unpack("<f", c.world.read(cg + CG_INTERP, 4))[0]
        x = struct.unpack("<f", c.world.read(cent + 0x18, 4))[0]
        out.append((c.results[-1][2], t0, frac, x))
    return out


def test_other_entities_smooth_at_uneven_periods(env):
    for period in (2500, 4167, 6944):
        out = _interp_frames(env, period)
        for (ta, sa, fa, xa), (tb, sb, fb, xb) in zip(out, out[1:]):
            if sa != sb:
                continue  # a new snapshot pair
            want = (tb - ta) / 50
            assert abs((fb - fa) - want) < 2e-6, (period, ta, tb, fa, fb)
            assert abs((xb - xa) - 190.0 * (tb - ta) / 1000) < 2e-4, (period, xa, xb)


def test_frame_interpolation_original_without_fraction(env):
    """No fraction, no slew: the enhanced CG_SetFrameInterpolation writes what the original writes."""
    r = random.Random(1038)
    cg = va("cgArray")
    for _ in range(300):
        t0 = r.randrange(-(1 << 31), 1 << 31)
        t1 = r.choice([t0, t0 + 50, t0 + 1, t0 - 50, r.randrange(-(1 << 31), 1 << 31)])
        now = r.choice([t0, t0 + 25, t1, t1 + 10, r.randrange(-(1 << 31), 1 << 31)])
        t1 = (t1 + (1 << 31)) % (1 << 32) - (1 << 31)
        now = (now + (1 << 31)) % (1 << 32) - (1 << 31)

        def setup(w):
            w.write(SNAP0 + 0x3C7C, _i(t0))
            w.write(SNAP1 + 0x3C7C, _i(t1))
            w.write(cg + CG_SNAP, struct.pack("<QQ", SNAP0, SNAP1))
            w.write(cg + CG_TIME, _i(now))
            w.write(va("cls") + CLS_REALTIME, _i(1000))
            w.write(env.data("cls_realtimeUs"), struct.pack("<q", 1_000_000))
            w.write(va("clients") + CL_SERVERTIME, _i(now))
        _, _, mine, _ = env.call(INTERP, [0], "void", setup, {})
        _, _, theirs, _ = env.machine.call(env.table[INTERP], [0], "void", setup, {}, {})
        mine = {a: v for a, v in mine.items() if not env.dll.base <= a < env.dll.base + env.dll.size}
        assert mine == theirs, (t0, t1, now)


def _f(ps, off, n=3):
    return struct.unpack_from(f"<{n}f", ps, off)


def _own_view_run(env, fraction_us, mode=0, frames=(1, 1, 3, 2, 2, 3, 1), entities_mode=None):
    """Frames through the enhanced CG_DrawActiveFrame with a fraction in the client's clock: (cl.serverTime, the drawn
    state (what CG_CalcViewValues sees), the canonical state after the frame)."""
    from frame_sim import KB_FORWARD
    g = TickGame(env)
    g.world.poke(env.data("cg_presentMode"), _i(mode))
    if entities_mode is not None:
        g.world.poke(env.data("cg_presentMode") + 8, _i(entities_mode))
        g.world.poke(env.data("cg_presentExtrapolateMsec"), struct.pack("<d", 7.0))
    g.frame(1)
    g.client.key(KB_FORWARD, True)
    out = []
    for msec in frames:
        g.frame(msec, fraction_us=fraction_us)
        out.append((g.times[-1], g.drawn[-1], g.after[-1][:0x620]))
    return out


def test_own_view_steps_to_the_render_time_with_the_rest(env):
    base = _own_view_run(env, 0)
    for fraction_us in (250, 600, 999):
        run = _own_view_run(env, fraction_us)
        for (st, d0, c0), (st1, d1, c1) in zip(base, run):
            assert c0 == c1  # the canonical state never depends on the presentation
            v = _f(d1, 0x28)
            for i in range(3):
                want = d0[0x1C + 4 * i:0x20 + 4 * i]
                want = struct.unpack("<f", want)[0] + v[i] * (fraction_us / 1000 * 0.001)
                got = _f(d1, 0x1C)[i]
                assert abs(got - want) <= 1e-4 * max(1.0, abs(want)), (fraction_us, i, got, want)
            assert _f(d1, 0x184) == _f(d0, 0x184)  # the same frame's angles
        moved = [_f(d, 0x1C)[0] for _, d, _ in run]
        assert any(abs(b - a) > 0 for b, a in zip(moved, [_f(d, 0x1C)[0] for _, d, _ in base]))


def test_own_view_interpolate_mode_is_canonical(env):
    run = _own_view_run(env, 600, mode=1)
    for _, drawn, canonical in run:
        assert drawn[:0x620] == canonical[:0x620]


def test_switching_one_category_changes_only_it(env):
    # other entities: EXTRAPOLATE with a lead moves the blend, not the own view
    plain = _interp_frames(env, 4167, frames=12)
    extra = _interp_frames(env, 4167, frames=12, mode=2, lead=7.0)
    assert all(abs((fe - fp) - 7.0 / 50) < 2e-6 for (_, sp, fp, _), (_, se, fe, _) in zip(plain, extra) if sp == se)
    view_a = _own_view_run(env, 600)
    g_mode = _own_view_run_with_entities_mode(env, 600, 2)
    assert [d for _, d, _ in view_a] == [d for _, d, _ in g_mode]
    # the own view: INTERPOLATE changes the drawn view, not the other entities' blend
    entities_with_view_mode = _interp_frames_with_view_mode(env, 4167, 1)
    assert [x[2] for x in entities_with_view_mode] == [x[2] for x in _interp_frames(env, 4167, frames=12)]
    assert [d for _, d, _ in _own_view_run(env, 600, mode=1)] != [d for _, d, _ in view_a]


def _own_view_run_with_entities_mode(env, fraction_us, entities_mode):
    return _own_view_run(env, fraction_us, entities_mode=entities_mode)


def _interp_frames_with_view_mode(env, period_us, view_mode):
    orig = RenderClock.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        self.world.poke(env.data("cg_presentMode"), _i(view_mode))
    RenderClock.__init__ = init
    try:
        return _interp_frames(env, period_us, frames=12)
    finally:
        RenderClock.__init__ = orig


def test_milliseconds_after_the_other_time_base_init(env):
    """14054FD70 sets sys_timeBasesInitialized from timeGetTime first: the QPC clock still takes its own base."""
    q = Qpc(10_000_000, [5_000_000, 5_000_000, 5_123_456, 6_000_000])
    world = World(env)
    world.poke(va("sys_timeBasesInitialized"), _i(1))
    world.poke(va("sys_timeBase"), _i(777))
    world.poke(env.data("sys_qpcInitialized"), _i(0))
    assert _qpc_run(env, world, q, MS, "int") == 0
    assert _qpc_run(env, world, q, MS, "int") == 12
    assert _qpc_run(env, world, q, MS, "int") == 100
    assert struct.unpack("<i", world.read(va("sys_timeBase"), 4))[0] == 777


def test_render_time_never_goes_back(env):
    """A slew put back faster than real time (a 1 ms snapshot interval) would move T_r back: it holds instead."""
    c = RenderClock(env, interval=1)
    for _ in range(5):
        c.frame(1000)
    c.frame(5000, delta_change=-5)    # a 5 ms frame with cl.serverTime held: a correction of -5, slewed
    assert c.results[-1][0] == c.results[-2][0]
    held = c.results[-1][2]
    c.frame(1000)                     # the whole slew put back in 1 ms: T_r would fall by 4 ms
    assert c.results[-1][2] >= held
    values = [v for _, _, v in c.results]
    assert all(b >= a for a, b in zip(values, values[1:]))


def test_present_time_and_mode_per_category(env):
    cg = va("cgArray")
    for category in range(6):
        for mode in (0, 1, 2, 7):
            def setup(w):
                w.write(cg + CG_TIME, _i(5000))
                w.write(va("cls") + CLS_REALTIME, _i(4000))
                w.write(env.data("cls_realtimeUs"), struct.pack("<q", 4_000_250))
                w.write(va("clients") + CL_SERVERTIME, _i(5000))
                w.write(env.data("cg_presentMode") + 4 * category, _i(mode))
                w.write(env.data("cg_presentExtrapolateMsec"), struct.pack("<d", 3.0))
            got_mode, _, _, _ = env.call("?CG_PresentMode@@YA?AW4PresentMode@@W4PresentCategory@@@Z", [category],
                                         "int", setup)
            got_time, _, _, _ = env.call("?CG_PresentTime@@YANW4PresentCategory@@@Z", [category], "double", setup)
            want_mode = mode if mode in (0, 1, 2) else 0
            assert got_mode == want_mode, (category, mode, got_mode)
            if category == 0 and want_mode == 1:
                assert got_time == 5000.0
            elif want_mode == 2:
                assert got_time == 5003.25
            else:
                assert got_time == 5000.25, (category, mode, got_time)
