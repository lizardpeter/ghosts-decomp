"""The cgame's 5 ms tick loop and its presentation pass (enhanced/cgame_mp/cg_tick.cpp; docs/cgame-frame.md 4.2,
4.8, 4.10).

Whole client frames through the enhanced CG_DrawActiveFrame (frame_sim.TickGame: the clock, CG_SavePlayerState, the
frame; the prediction runs the Store build's own Pmove, noclip, or a fake one that adds predictable events).

(a) The simulation is the same at every frame pattern: 1 s of game time at 60, 144, 165, 240, 360, 500 and 1000 fps
    (fractional periods on the integer client clock) with delta nudges of +1, -1 and -2 ms, forward held, shots (kick
    velocity added in the events of fixed ticks) and events 0x3A counted at fixed ticks, against a reference of 5 ms
    frames: at every tick its times (cg.oldTime/time/frametime and bgs.time/frametime = t_{k-1}/t_k/5), the predicted
    state (all 0x3328 bytes), cg_pmove, the kick, and the usercmd of every tick are bit-identical; every predictable
    event is fired once, at the same tick, and every 0x3A event too. With the mouse moving, the input is the frame's
    (by design: read once, right after the frame wait); a reference fed the same angles per tick gives bit-identical
    states, so the simulation is a function of the command stream only.
(b) No tick boundary between this frame's input and its view: the drawn angles are this frame's (the Store build's own
    frame pipeline, one command per frame, draws the same angles at 1000 fps and 4.17 ms frames, bit for bit); the
    drawn origin is a Pmove of the canonical state to floor(T_r) plus velocity * frac(T_r); the view command carries
    the kick stepped forward to T_r while the real commands carry the canonical kick of the previous tick.
- The faithful frame: with the loop off the enhanced CG_DrawActiveFrame makes exactly the original's calls and writes
  (the differential test's 1500 frame inputs, against the Store build).
"""
import math
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_sim import (CL_CMDS, CL_CMDNUMBER, CL_KICK, CL_VIEWANGLES, CMD_SIZE, KB_FORWARD, PS_SIZE, PM_SIZE,  # noqa: E402
                       S, TickGame, Mouse, World, f32, frame_pattern, noop, rd, scratch_setup, wmem)
from syms import va  # noqa: E402

FPS = [60, 144, 165, 240, 360, 500, 1000]
NUDGES = {200: 1, 450: -1, 700: -2}     # real ms after the start: the delta's change (CL_SetCGameTime's nudges)
START = 100001                          # the first frame's cl.serverTime: the grid's phase
SHOTS = {START + 5 * 20: (-160.0, 35.0, 0.0), START + 5 * 61: (-120.0, -20.0, 0.0),
         START + 5 * 137: (-90.0, 44.0, 0.0)}
COUNTS = {START + 5 * 33: 1, START + 5 * 90: 2}   # events 0x3A counted by the transition in these ticks
CG_KICK_AVEL = 0xB5268


class EventPmove:
    """Pmove, faked: the command's time, a constant speed along x, the angles from the command, and one predictable
    event every 25 ms of command time (type 7, its time as the parm)."""

    def __call__(self, mu):
        from win32_display import arg
        pm = arg(mu, 0)
        ps = struct.unpack("<Q", rd(mu, pm, 8))[0]
        t, now = struct.unpack("<i", rd(mu, pm + 8, 4))[0], struct.unpack("<i", rd(mu, ps, 4))[0]
        if t > now:
            wmem(mu, ps, struct.pack("<i", t))
            x = struct.unpack("<f", rd(mu, ps + 0x1C, 4))[0]
            wmem(mu, ps + 0x1C, struct.pack("<f", f32(x + f32(0.19 * (t - now)))))
            angles = struct.unpack("<3i", rd(mu, pm + 0x10, 12))
            wmem(mu, ps + 0x184, struct.pack("<3f", *((a & 0xFFFF) * (360.0 / 65536.0) for a in angles)))
            if t // 25 != now // 25:
                seq = struct.unpack("<i", rd(mu, ps + 0x128, 4))[0]
                wmem(mu, ps + 0x128, struct.pack("<i", seq + 1))
                wmem(mu, ps + 0x12C + 8 * (seq & 3), struct.pack("<ii", 7, t))
        return None


def _run(env, pattern, nudges=None, pmove=None, mouse=None, shots=SHOTS, counts=COUNTS, kick_avel=(0.0, 0.0, 0.0),
         first=1, keys=True):
    g = TickGame(env, pmove=pmove, mouse=mouse or Mouse(0.0, 0.0), shots=shots, kick_avel=kick_avel)
    g.ticks.counts = dict(counts or {})
    if keys:
        g.client.key(KB_FORWARD, True)   # held from before the first frame: every command's move is the same
    start = g.client.realtime
    applied = set()
    g.frame(first)
    for msec in pattern:
        elapsed = g.client.realtime - start + msec
        change = 0
        for at, d in (nudges or {}).items():
            if at not in applied and elapsed >= at:
                applied.add(at)
                change += d
        g.frame(msec, change)
    return g


def _by_tick(g):
    rows = {}
    for frame, time, old, msec, bgs_time, bgs_msec, ps, pm, kick, recoil in g.ticks.rows:
        assert time not in rows, ("a tick ran twice", time)
        rows[time] = (old, msec, bgs_time, bgs_msec, ps, pm, kick, recoil)
    cmds = {}
    for frame in g.frame_commands:
        for raw in frame:
            t = struct.unpack_from("<i", raw)[0]
            assert t not in cmds, ("a command time twice", t)
            cmds[t] = raw
    return rows, cmds


def _compare(name, g, ref, upto=None, minimum=150):
    rows, cmds = _by_tick(g)
    ref_rows, ref_cmds = _by_tick(ref)
    common = sorted(set(rows) & set(ref_rows))
    if upto is not None:
        common = [t for t in common if t <= upto]
    assert len(common) >= minimum, (name, len(common))
    assert common == sorted(ref_rows)[:len(common)], name   # no tick missing at the start or in between
    for t in common:
        old, msec, bgs_time, bgs_msec, ps, pm, kick, recoil = rows[t]
        assert (old, msec, bgs_time, bgs_msec) == (t - 5, 5, t, 5), (name, t, old, msec, bgs_time, bgs_msec)
        r = ref_rows[t]
        assert ps == r[4], (name, t, "state", _first_diff(ps, r[4]))
        assert pm == r[5], (name, t, "cg_pmove", _first_diff(pm, r[5]))
        assert kick == r[6], (name, t, "kick", struct.unpack("<6f", kick), struct.unpack("<6f", r[6]))
        assert recoil == r[7], (name, t, "recoil")
        assert cmds[t] == ref_cmds[t], (name, t, "usercmd")
    last = common[-1]
    events = [e for e in g.ticks.events if e[0] <= last]
    ref_events = [e for e in ref.ticks.events if e[0] <= last]
    assert events == ref_events, (name, events[:5], ref_events[:5])
    assert [s for _, s, _, _ in events] == list(range(events[0][1], events[0][1] + len(events))) if events else True
    ee = [e for e in g.ticks.entity_events if e[0] <= last]
    assert ee == [e for e in ref.ticks.entity_events if e[0] <= last], name
    return common


def _first_diff(a, b):
    return next((hex(i) for i in range(min(len(a), len(b))) if a[i] != b[i]), None)


def test_a_simulation_identical_at_every_frame_rate(env):
    """(a) with the Store build's Pmove (noclip), forward held, the shots' kick, the delta nudges."""
    ref = _run(env, [5] * 200, NUDGES)
    rows, _ = _by_tick(ref)
    kicks = {struct.unpack("<6f", r[6]) for r in rows.values()}
    assert len(kicks) > 50   # the kick moved: the shots went in
    xs = {struct.unpack_from("<f", r[4], 0x1C)[0] for r in rows.values()}
    assert len(xs) > 100     # the player moved
    for fps in FPS:
        g = _run(env, frame_pattern(fps, 1000), NUDGES)
        _compare(f"{fps} fps", g, ref)


def test_a_events_once_at_the_same_tick(env):
    """(a) with predictable events from the prediction (EventPmove): every one fired once, at the same tick, at every
    frame rate; the 0x3A events of the counted ticks too."""
    ref = _run(env, [5] * 200, NUDGES, pmove=EventPmove())
    assert len(ref.ticks.events) >= 35, len(ref.ticks.events)
    assert len(ref.ticks.entity_events) == 0  # no entity is view-locked: the count fires nothing (see below)
    for fps in FPS:
        g = _run(env, frame_pattern(fps, 1000), NUDGES, pmove=EventPmove())
        _compare(f"{fps} fps", g, ref)


def test_a_viewlocked_events_once_per_tick(env):
    """The 0x3A events CG_TransitionPlayerState counts in a tick fire on the view-locked entity in that tick."""
    def run(pattern):
        g = TickGame(env, mouse=Mouse(0.0, 0.0))
        cg = va("cgArray")
        g.world.poke(cg + 0x1E8, struct.pack("<i", 0x41))   # viewlocked_entNum
        g.ticks.counts = dict(COUNTS)
        g.frame(1)
        for msec in pattern:
            g.frame(msec)
        return g
    ref = run([5] * 100)
    assert [t for t, _, ev in ref.ticks.entity_events] == [START + 5 * 33] + [START + 5 * 90] * 2
    assert all(ev == 0x3A for _, _, ev in ref.ticks.entity_events)
    for fps in (60, 240, 1000):
        g = run(frame_pattern(fps, 500))
        assert g.ticks.entity_events == ref.ticks.entity_events, fps


class TimeMouse:
    """CL_MouseMove, faked: the view's yaw and pitch as a function of the frame's time (com_frameTime)."""

    def __init__(self):
        self.calls = 0

    def __call__(self, mu):
        t = struct.unpack("<i", rd(mu, va("com_frameTime"), 4))[0] - 100000
        cl = va("clients")
        wmem(mu, cl + CL_VIEWANGLES, struct.pack("<2f", f32(math.sin(t * 0.004) * 12.0), f32(t * 0.0371)))
        self.calls += 1
        return None


class ReplayMouse:
    """CL_MouseMove, faked: the angles another run used for the tick this frame makes (the next grid time)."""

    def __init__(self, env, angles):
        self.grid = env.data("s_grid")
        self.angles = angles

    def __call__(self, mu):
        t = struct.unpack("<i", rd(mu, self.grid, 4))[0] + 5
        if t in self.angles:
            wmem(mu, va("clients") + CL_VIEWANGLES, self.angles[t])
        return None


def test_a_state_is_a_function_of_the_commands(env):
    """With the mouse moving, each tick's command has the angles of the frame that made it; a 5 ms run fed the same
    angles per tick has bit-identical states and commands at every tick."""
    for fps in (60, 165, 1000):
        g = _run(env, frame_pattern(fps, 600), mouse=TimeMouse())
        # the angles of the frame that made each tick
        angles = {}
        for frame_cmds, view in zip(g.frame_commands, g.view_angles):
            for raw in frame_cmds:
                angles[struct.unpack_from("<i", raw)[0]] = view
        ref = _run(env, [5] * 120, mouse=ReplayMouse(env, angles))
        _compare(f"{fps} fps", g, ref, minimum=110)
        turned = {struct.unpack_from("<3f", ref_row, 0x184) for ref_row in (r[4] for r in _by_tick(ref)[0].values())}
        assert len(turned) > 50, fps


def test_frames_without_a_tick_simulate_nothing(env):
    """At 1000 fps four frames in five make no tick: the canonical state, the kick, the saved state and the client's
    command ring stay as the last tick left them; CL_SendCmd still runs once a frame."""
    g = _run(env, [1] * 60, kick_avel=(-160.0, 35.0, 0.0))
    cg = va("cgArray")
    ticked = {frame for frame, *_ in g.ticks.rows}
    for k in range(2, len(g.after)):
        if k not in ticked:
            assert g.after[k] == g.after[k - 1], k
    assert len(g.sent) == len(g.after)


def test_b_view_angles_are_the_frames_like_the_original(env):
    """(b) The drawn angles at 1000 fps and 4.17 ms frames, the mouse turning every frame, no kick: bit for bit the
    angles the Store build's own frame (CL_CreateNewCommands making one command per frame at cl.serverTime,
    CG_PredictPlayerState) draws: no tick boundary between this frame's input and its view."""
    for pattern in ([1] * 40, [4, 4, 4, 4, 4, 5] * 6):
        g = _run(env, pattern, mouse=Mouse(), shots={}, counts={})
        store = StoreFrames(env)
        for msec in [1] + pattern:
            store.frame(msec)
        assert len(store.drawn) == len(g.drawn)
        for k, (ours, theirs) in enumerate(zip(g.drawn, store.drawn)):
            if k == 0:
                continue
            assert ours[0x184:0x190] == theirs[0x184:0x190], (pattern[:2], k, struct.unpack_from("<3f", ours, 0x184),
                                                             struct.unpack_from("<3f", theirs, 0x184))


class StoreFrames:
    """The Store build's own frame pipeline, for comparison: CG_SavePlayerState, CL_CreateNewCommands (one command per
    frame at cl.serverTime), CG_PredictPlayerState and CG_DrawActive, all the Store's code."""

    def __init__(self, env):
        from frame_sim import Client, cgame_fakes, generator_fakes, CG_SNAP, CG_PLATFORM_CONTACT, CG_SAVED, SNAP
        from syms import static
        self.env = env
        self.world = World(env)
        self.client = Client(env, self.world, mouse=Mouse())
        self.client.key(KB_FORWARD, True)
        self.fakes = dict(generator_fakes(self.client.mouse))
        self.fakes.update(cgame_fakes())
        w, cg = self.world, va("cgArray")
        start = self.client.realtime + 1
        ps = bytearray(0x620)
        struct.pack_into("<iiiiI", ps, 0, start - 5, 2, 0, 0, 0x4000)
        struct.pack_into("<i", ps, 0x44, 0x7FF)
        struct.pack_into("<ii", ps, 0x5C, 800, 190)
        struct.pack_into("<i", ps, 0x70, 0x7FF)
        struct.pack_into("<i", ps, 0xBC, 0x7FF)
        struct.pack_into("<if", ps, 0x190, 60, 60.0)
        struct.pack_into("<i", ps, 0x1E8, 0x7FF)
        w.poke(cg, bytes(ps))
        w.poke(cg + 0xE08, struct.pack("<i", 0x7FF))
        w.poke(cg + CG_SNAP, struct.pack("<QQ", SNAP, SNAP))
        w.poke(cg + CG_PLATFORM_CONTACT, struct.pack("<i", 0x7FF))
        w.poke(cg + 0x71890, struct.pack("<i", start - 5))
        w.poke(static("cgame_mp/cg_predict_mp.cpp", "cg_pmove") + 0x108, struct.pack("<6f", 0, 0, 35, 15, 15, 35))
        w.poke(cg + CG_SAVED, struct.pack("<i", start - 5))
        self.drawn = []

    def call(self, name, args):
        env, w = self.env, self.world
        hooks = {}
        for s, fn in self.fakes.items():
            for a in (env.dll.exports.get(s), env.table.get(s)):
                if a:
                    hooks[a] = fn

        def setup(m):
            scratch_setup(m)
            w.apply(m)
        value, _, written, _ = env.machine.call(env.table[S[name]], args, "void", setup, hooks, {})
        assert not (isinstance(value, str) and value.startswith("fault")), value
        w.mem.update(written)

    def frame(self, msec):
        c, cg = self.client, va("cgArray")
        old = struct.unpack("<i", self.world.read(cg + 0x71890, 4))[0]
        c.clock(msec)
        self.world.poke(cg + 0x71894, struct.pack("<i", old))
        self.world.poke(cg + 0x71890, struct.pack("<i", c.server_time))
        self.call("save", [0])
        self.call("create", [0])
        self.call("predict", [0])
        self.drawn.append(self.world.read(cg, 0x620))
        self.call("draw", [0, 0])


def _vec(b, off):
    return struct.unpack_from("<3f", b, off)


def test_b_view_command_kick_stepped_real_commands_canonical(env):
    """The view command carries the kick advanced to the own view's presentation time (BG_KickAnglesStep of the
    canonical kick by T_r - t_latest); every real command carries the canonical kick of the tick before it."""
    for fraction_us in (0, 400):
        g = TickGame(env, mouse=Mouse(0.0, 0.0), kick_avel=(-160.0, 35.0, 0.0), shots={})
        g.client.key(KB_FORWARD, True)
        g.frame(1, fraction_us=fraction_us)
        kicks = {}          # tick time -> the kick angles after its step (the next row's "before")
        rows = []
        for msec in [1, 2, 1, 3, 1, 1, 4, 2, 1, 1, 12, 16, 7, 1, 23, 2]:   # some frames with several ticks
            g.frame(msec)
        rows = g.ticks.rows
        for row, nxt in zip(rows, rows[1:]):
            kicks[row[1]] = struct.unpack("<3f", nxt[8][12:24])
        # the real commands: angles = round(clViewangles + kick at t - 5)
        for frame in g.frame_commands[2:]:
            for raw in frame:
                t = struct.unpack_from("<i", raw)[0]
                if t - 5 in kicks:
                    want = tuple(math.floor(f32(f32(0.0 + kicks[t - 5][i]) * f32(182.04445)) + 0.5) & 0xFFFF
                                 for i in range(3))
                    got = tuple(v & 0xFFFF for v in struct.unpack_from("<3i", raw, 8))
                    assert got == want, (t, got, want)
        # the view command of the last frame: the kick of the latest tick, stepped by T_r - t_latest
        view = g.world.read(g.env.data("cl_viewCmd"), CMD_SIZE)
        cg = va("cgArray")
        canon = struct.unpack("<6f", g.world.read(cg + CG_KICK_AVEL, 24))
        latest = rows[-1][1]
        rest = g.times[-1] + fraction_us / 1000.0 - latest
        assert rest > 0
        stepped = kick_step(env, canon[:3], canon[3:], rest)
        want = tuple(math.floor(f32(f32(0.0 + stepped[i]) * f32(182.04445)) + 0.5) & 0xFFFF for i in range(3))
        assert tuple(v & 0xFFFF for v in struct.unpack_from("<3i", view, 8)) == want, (rest, stepped)
        assert stepped != canon[3:]


STEP = "?BG_KickAnglesStep@@YAXPEBUplayerState_s@@MQEAM1@Z"
KICK = "?BG_KickAngles@@YAXPEBUplayerState_s@@HQEAM1@Z"
OVERLAY_FN = "?BG_GetOverlay@@YAPEBUADSOverlay@@TWeapon@@_N@Z"
WEAPON = "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z"


def _kick_fakes():
    from frame_sim import OVERLAY
    return {WEAPON: lambda mu: 0, OVERLAY_FN: lambda mu: OVERLAY}


def kick_step(env, vel, ang, msec):
    ps = bytes(0x1000)
    _, bufs, _, _ = env.call(STEP, [ps, ("f", msec), struct.pack("<3f", *vel), struct.pack("<3f", *ang)],
                             setup=lambda w: None, fakes=_kick_fakes())
    return struct.unpack("<3f", bufs[2])


def test_kick_step_is_the_original_for_whole_msec(env):
    """BG_KickAnglesStep with a whole msec is BG_KickAngles (the Store build's) bit for bit; BG_KickAngles itself is
    the original for every caller (it is not replaced any more)."""
    from frame_sim import OVERLAY
    r = random.Random(14)
    for _ in range(40):
        vel = [r.choice([0.0, -160.0, 35.0, r.uniform(-300, 300)]) for _ in range(3)]
        ang = [r.choice([0.0, 1.5, -2.0, 9.9, r.uniform(-10, 10)]) for _ in range(3)]
        msec = r.choice([1, 2, 3, 4, 5, 7, 12, 50])
        ps = bytes(0x1000)
        args_i = [ps, msec, struct.pack("<3f", *vel), struct.pack("<3f", *ang)]
        hooks = {env.table[s]: f for s, f in _kick_fakes().items()}
        _, want, _, _ = env.machine.call(env.table[KICK], args_i, "void", lambda w: None, hooks, {})
        _, mine, _, _ = env.call(KICK, args_i, setup=lambda w: None, fakes=_kick_fakes())
        assert mine[1:] == want[1:], (vel, ang, msec)
        _, stepped, _, _ = env.call(STEP, [ps, ("f", float(msec)), args_i[2], args_i[3]], setup=lambda w: None,
                                    fakes=_kick_fakes())
        assert stepped[1:] == want[1:], (vel, ang, msec)


def test_faithful_frame_with_the_loop_off(env):
    """cg_tickLoop 0 (and the own view's step off): the enhanced CG_DrawActiveFrame makes the original's calls with
    the original's arguments in the original's order, and the same writes, for the differential test's inputs."""
    import test_cg_view as d
    off = {env.data("cg_tickLoop"): struct.pack("<i", 0), env.data("cg_renderTimeView"): struct.pack("<i", 0)}
    r = random.Random(4816)
    lo, hi = env.dll.base, env.dll.base + env.dll.size
    for n in range(400):
        case = d._frame_input(r)
        hooks = {}
        for s, fn in case["fakes"].items():
            for a in (env.dll.exports.get(s), env.table.get(s)):
                if a:
                    hooks[a] = fn

        def setup(w, case=case):
            case["setup"](w)
            for a, v in off.items():
                w.write(a, v)
        theirs = env.machine.call(env.table[d.SYM["CG_DrawActiveFrame"]], case["args"], "int", setup, hooks, {})
        mine = env.machine.call(env.dll.exports[d.SYM["CG_DrawActiveFrame"]], case["args"], "int", setup, hooks, {})
        assert mine[0] == theirs[0], n
        assert mine[3] == theirs[3], (n, next(((i, a, b) for i, (a, b) in enumerate(zip(mine[3], theirs[3])) if a != b),
                                              (len(mine[3]), len(theirs[3]))))
        w_mine = {a: v for a, v in mine[2].items() if not lo <= a < hi}
        assert w_mine == theirs[2], n


PRESENT = "?CG_PresentOwnView@@YAXW4LocalClientNum_t@@@Z"


def _swap_run(env, present_before, save):
    g = TickGame(env, mouse=Mouse(), kick_avel=(-160.0, 35.0, 0.0), shots={})
    g.client.key(KB_FORWARD, True)
    g.frame(1)
    for k in range(12):
        if k in present_before:
            for _ in range(present_before[k]):
                g.call(PRESENT, [0])
        g.frame(3 if k % 2 else 2, save=save)
    return g


def test_a_tick_never_simulates_a_presented_state(env):
    """The own view swapped in (CG_PresentOwnView, once or twice) before a frame that skips CG_SavePlayerState: the
    tick puts the canonical state back before it simulates, so every tick's state is the run's without the swaps."""
    ref = _swap_run(env, {}, save=False)
    for swaps in ({3: 1, 7: 1}, {3: 2, 8: 3}):
        g = _swap_run(env, swaps, save=False)
        assert [r[6] for r in g.ticks.rows] == [r[6] for r in ref.ticks.rows], swaps
        assert g.after == ref.after, swaps
    # presenting twice steps from the canonical state both times: CG_SavePlayerState then saves the canonical state
    g = _swap_run(env, {}, save=True)
    g.client.clock(1)
    g.world.poke(env.data("cls_realtimeUs"), struct.pack("<q", g.client.realtime * 1000))
    cg = va("cgArray")
    canonical = g.world.read(cg, PS_SIZE)
    g.call(PRESENT, [0])
    once = g.world.read(cg, PS_SIZE)
    g.call(PRESENT, [0])
    assert g.world.read(cg, PS_SIZE) == once != canonical
    g.call("save", [0])
    assert g.world.read(cg, PS_SIZE) == canonical


class MoverLog:
    """CG_AdjustPositionForMover, faked as frame_sim's (no platform: in = out, no deltas), logging (from, to)."""

    def __init__(self):
        self.calls = []

    def __call__(self, mu):
        from win32_display import arg
        self.calls.append((arg(mu, 3) & 0xFFFFFFFF, arg(mu, 4) & 0xFFFFFFFF))
        wmem(mu, arg(mu, 5), rd(mu, arg(mu, 1), 12))
        wmem(mu, arg(mu, 6), bytes(12))
        wmem(mu, arg(mu, 7), bytes(12))
        return None


def test_platform_move_per_tick(env):
    """The early prediction (the platform's move) runs in every tick up to the tick's time: in a frame's first tick from
    cg.predictFromTime (the snapshot's time, as the original once a frame), in the others from the previous tick."""
    g = TickGame(env, mouse=Mouse(0.0, 0.0))
    log = MoverLog()
    g.fakes[S["adjust"]] = log
    cg = va("cgArray")
    snap_time = 99990
    g.frame(1)
    for msec in frame_pattern(60, 200):
        g.world.poke(cg + 0x71898, struct.pack("<i", snap_time))   # what 1402D3230 sets every frame
        log.calls.clear()
        n = len(g.ticks.rows)
        g.frame(msec)
        times = [r[1] for r in g.ticks.rows[n:]]
        assert len(times) >= 3
        want = [(snap_time, times[0])] + [(t - 5, t) for t in times[1:]]
        assert [c for c in log.calls if c in want] == want, (log.calls, want)


def test_a_tick_events_reach_the_next_command(env):
    """A tick's events that change what the next command carries (the weapon to select, extra buttons) reach the
    next tick's command, at every frame rate (the hand-off is per tick, not at the frame's end)."""
    writes = {START + 5 * 40: [(0xB2768, struct.pack("<I", 0x0207))], START + 5 * 41: [(0x10E82C, struct.pack("<i", 0x400))],
              START + 5 * 77: [(0xB2768, struct.pack("<I", 0x0105)), (0x10E82C, struct.pack("<i", 0x20000))]}

    def run(pattern):
        return _run(env, pattern, counts={}, shots={})

    def run_with(pattern):
        orig = TickGame.__init__

        def init(self, *a, **k):
            orig(self, *a, **k)
            self.ticks.writes = writes
        TickGame.__init__ = init
        try:
            return run(pattern)
        finally:
            TickGame.__init__ = orig
    ref = run_with([5] * 100)
    _, cmds = _by_tick(ref)
    plain = run([5] * 100)
    _, plain_cmds = _by_tick(plain)
    for t in (START + 5 * 41, START + 5 * 42, START + 5 * 78):
        assert cmds[t] != plain_cmds[t], t   # the next command carries the change
    assert cmds[START + 5 * 40] == plain_cmds[START + 5 * 40]   # not the tick's own command
    for fps in (60, 1000):
        g = run_with(frame_pattern(fps, 500))
        _compare(f"{fps} fps", g, ref, minimum=90)


def test_d_other_categories_leave_the_own_view(env):
    """Each category other than the own view switched to PM_EXTRAPOLATE with a 7 ms lead: the own view (its drawn
    state and its view command with the stepped kick) and the canonical state are the default run's. The own view
    switched to PM_INTERPOLATE: the drawn state is the canonical one."""
    def run(category=None, mode=None):
        g = TickGame(env, mouse=Mouse(), kick_avel=(-160.0, 35.0, 0.0), shots={})
        if category is not None:
            g.world.poke(env.data("cg_presentMode") + 4 * category, struct.pack("<i", mode))
            g.world.poke(env.data("cg_presentExtrapolateMsec"), struct.pack("<d", 7.0))
        g.client.key(KB_FORWARD, True)
        g.frame(1)
        views = []
        for msec in (1, 2, 1, 3, 1, 1, 4, 2):
            g.frame(msec, fraction_us=300)
            views.append(g.world.read(env.data("cl_viewCmd"), CMD_SIZE))
        return g, views
    base, base_views = run()
    for category in range(1, 6):
        g, views = run(category, 2)
        assert g.drawn == base.drawn and views == base_views, category
        assert g.after == base.after, category
    g, views = run(0, 1)
    assert g.after == base.after
    assert all(d == a[:0x620] for d, a in zip(g.drawn, g.after))
    assert g.drawn != base.drawn


def test_a_viewmodel_animation_per_tick(env):
    """CG_UpdateViewWeaponAnim (the viewmodel's XAnim) runs once in every tick with the tick's times, never in the
    presentation: the viewmodel is drawn at the latest tick's pose (docs/cgame-frame.md 4.10)."""
    for pattern in ([1] * 30, [16, 17, 17] * 4, [5] * 12):
        g = TickGame(env, mouse=Mouse(0.0, 0.0))
        seen = []

        def anim(mu):
            cg = va("cgArray")
            seen.append((g.client.frame_index,) + struct.unpack("<iii", rd(mu, cg + 0x7188C, 12)))
            return None
        g.fakes["?CG_UpdateViewWeaponAnim@@YAXW4LocalClientNum_t@@@Z"] = anim
        g.frame(1)
        for msec in pattern:
            g.frame(msec)
        want = [(frame, 5, t, t - 5) for frame, t, *_ in g.ticks.rows]
        assert seen == want, (pattern[:3], seen[:4], want[:4])
