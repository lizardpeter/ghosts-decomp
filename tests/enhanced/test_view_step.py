"""The own view at the render time: the presentation's step-forward (enhanced/cgame_mp/cg_view_step.cpp, called by the
tick loop's presentation in enhanced/cgame_mp/cg_tick.cpp; docs/fps.md 7.6, docs/cgame-frame.md 4.10).

Whole client frames through the enhanced CG_DrawActiveFrame (frame_sim.TickGame) with the faithful prediction
running the Store build's own Pmove (noclip, forward held, the view turning every frame), at 1 ms, 2.5 ms (2/3) and
4.17 ms (4, 4, 4, 4, 4, 5) frames:
- the drawn origin (what CG_CalcViewValues sees) advances every frame by the frame's own time at the drawn velocity,
  where the run with the step off stands still on frames without a tick;
- the drawn angles are AngleNormalize180(round16(clViewangles + kick) · 360/65536 + delta_angles) of the same frame,
  the kick being the canonical one stepped forward to the render time;
- after the frame, the predicted state is bit-identical to a run with the step off, every frame; CG_SavePlayerState
  after a swap without the frame's end (the safety-net restore) saves the canonical state;
- an event the partial step adds (a Pmove fake that adds one only for the temporary command) never reaches pe, the
  saved pe or CG_TransitionPlayerState;
- the character info the animation conditions are written to is the same as without the step;
- a step up during the partial move lowers the drawn origin by the step;
- the zero-leftover case: no time to move, the angles still follow the frame.
"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_sim import (CL_VIEWANGLES, CG_SAVED, KB_FORWARD, PS_SIZE, TickGame, f32, rd, wmem)  # noqa: E402
from harness import TLS_BLOCK  # noqa: E402
from syms import va  # noqa: E402
from test_tick import kick_step  # noqa: E402

PATTERNS = {"1 ms": [1], "2.5 ms": [2, 3], "4.17 ms": [4, 4, 4, 4, 4, 5]}


def _vec(ps, off):
    return struct.unpack_from("<3f", ps, off)


def _run(env, pattern, frames, enabled=True, pmove=None, anim=None, kick=(0.25, -0.5, 0.0)):
    kwargs = {"pmove": pmove} if pmove else {}
    if anim:
        kwargs["anim"] = anim
    g = TickGame(env, render_time_view=enabled, kick=kick, **kwargs)
    g.frame(1)
    g.client.key(KB_FORWARD, True)
    for i in range(frames):
        g.frame(pattern[i % len(pattern)])
    return g


def _angle_norm180(x):
    scaled = f32(x * f32(0.0027777778))
    return f32(f32(scaled - f32(math.floor(f32(scaled + 0.5)))) * 360.0)


def test_view_moves_every_frame_with_its_own_time(env):
    for name, pattern in PATTERNS.items():
        g = _run(env, pattern, 150)
        ref = _run(env, pattern, 150, enabled=False)
        still_ref = 0
        for k in range(60, len(g.drawn)):
            dt = g.times[k] - g.times[k - 1]
            x0, x1 = _vec(g.drawn[k - 1], 0x1C)[0], _vec(g.drawn[k], 0x1C)[0]
            vx = _vec(g.drawn[k], 0x28)[0]
            assert vx > 50, (name, vx)
            assert abs((x1 - x0) - vx * dt * 0.001) <= 0.03 * vx * dt * 0.001 + 0.01, (name, k, x1 - x0, vx, dt)
            if _vec(ref.drawn[k], 0x1C)[0] == _vec(ref.drawn[k - 1], 0x1C)[0]:
                still_ref += 1
        if pattern != [4, 4, 4, 4, 4, 5]:
            assert still_ref > 0, name  # the canonical view stands still on frames without a tick


def _stepped_kick(env, g):
    """The kick the frame's view command carries: the canonical kick after the frame (the latest tick's) stepped to the
    render time (no fraction here: cl.serverTime)."""
    cg = va("cgArray")
    canon = struct.unpack("<6f", g.world.read(cg + 0xB5268, 24))
    rest = g.times[-1] - g.ticks.rows[-1][1]
    return kick_step(env, canon[:3], canon[3:], float(rest)) if rest > 0 else canon[3:]


def test_view_angles_are_the_frames(env):
    for name, pattern in PATTERNS.items():
        g = _run(env, pattern, 60)
        world = g.world
        kick = _stepped_kick(env, g)
        view = struct.unpack("<3f", world.read(va("clients") + CL_VIEWANGLES, 12))
        ps = g.drawn[-1]
        delta = _vec(ps, 0x64)
        for i in range(3):
            short = math.floor(f32(f32(f32(view[i] + f32(kick[i] + 0.0)) * f32(182.04445)) + 0.5)) & 0xFFFF
            want = _angle_norm180(f32(f32(short * f32(360.0 / 65536.0)) + delta[i]))
            assert _vec(ps, 0x184)[i] == want, (name, i, _vec(ps, 0x184), want)


def test_canonical_state_unchanged_after_draw_and_save(env):
    for name, pattern in PATTERNS.items():
        g = _run(env, pattern, 80)
        ref = _run(env, pattern, 80, enabled=False)
        for k, (a, b) in enumerate(zip(g.after, ref.after)):
            assert a == b, (name, k)
        assert g.world.read(va("cgArray") + CG_SAVED, 0x78) == ref.world.read(va("cgArray") + CG_SAVED, 0x78)
        swapped = sum(1 for k in range(len(g.drawn)) if g.drawn[k] != ref.drawn[k])
        assert swapped > len(g.drawn) // 3, name


PRESENT = "?CG_PresentOwnView@@YAXW4LocalClientNum_t@@@Z"


def test_save_without_draw_restores(env):
    """The own view swapped in (CG_PresentOwnView) and no frame end after it: CG_SavePlayerState puts the canonical
    state back before it saves."""
    g = _run(env, [1], 42)
    ref = _run(env, [1], 42, enabled=False)
    g.client.clock(1)
    ref.client.clock(1)
    for run in (g, ref):
        run.world.poke(env.data("cls_realtimeUs"), struct.pack("<q", run.client.realtime * 1000))
    g.call(PRESENT, [0])
    cg = va("cgArray")
    assert g.world.read(cg, PS_SIZE) != ref.world.read(cg, PS_SIZE)  # swapped
    g.call("save", [0])
    ref.call("save", [0])
    assert g.world.read(cg + CG_SAVED, 0x78) == ref.world.read(cg + CG_SAVED, 0x78)
    assert g.world.read(cg, PS_SIZE) == ref.world.read(cg, PS_SIZE)


class EventPmove:
    """Pmove, faked: moves commandTime and the origin, sets the angles from the command, and adds a predictable
    event to pe only for a command whose time is off the 5 ms grid (the temporary command)."""

    def __init__(self, phase):
        self.phase = phase

    def __call__(self, mu):
        from win32_display import arg
        pm = arg(mu, 0)
        ps = struct.unpack("<Q", rd(mu, pm, 8))[0]
        t, now = struct.unpack("<i", rd(mu, pm + 8, 4))[0], struct.unpack("<i", rd(mu, ps, 4))[0]
        if t > now:
            wmem(mu, ps, struct.pack("<i", t))
            x = struct.unpack("<f", rd(mu, ps + 0x1C, 4))[0]
            wmem(mu, ps + 0x1C, struct.pack("<f", x + 0.19 * (t - now)))
            angles = struct.unpack("<3i", rd(mu, pm + 0x10, 12))
            wmem(mu, ps + 0x184, struct.pack("<3f", *((a & 0xFFFF) * (360.0 / 65536.0) for a in angles)))
            if (t - self.phase) % 5:
                seq = struct.unpack("<i", rd(mu, ps + 0x128, 4))[0]
                wmem(mu, ps + 0x128, struct.pack("<i", seq + 1))
                wmem(mu, ps + 0x12C + 8 * (seq & 3), struct.pack("<ii", 7, 99))
        return None


def test_partial_step_events_never_reach_pe(env):
    for name, pattern in PATTERNS.items():
        phase = 100001  # Client's start time + the 1 ms first frame: the grid's phase
        g = _run(env, pattern, 40, pmove=EventPmove(phase))
        ref = _run(env, pattern, 40, enabled=False, pmove=EventPmove(phase))
        cg = va("cgArray")
        for k, (a, b) in enumerate(zip(g.after, ref.after)):
            assert a[0x128:0x154] == b[0x128:0x154], (name, k)
            assert a == b, (name, k)
        assert g.world.read(cg + CG_SAVED + 0x4C, 0x2C) == ref.world.read(cg + CG_SAVED + 0x4C, 0x2C)
        assert g.ticks.events == ref.ticks.events == [], (name, g.ticks.events[:3])
        # the step did add events in its copy: the drawn state moved, the event counter didn't
        assert any(v[0x1C:0x28] != w[0x1C:0x28] for v, w in zip(g.drawn, ref.drawn))


class AnimCounter:
    """BG_AnimUpdatePlayerStateConditions, faked: counts its calls in the client's character info (bgs + 0x459F0, the
    bgs the thread's TLS block points at: cg.bgs while the cgame frame runs)."""

    def __init__(self):
        self.calls = 0

    def __call__(self, mu):
        self.calls += 1
        bgs = struct.unpack("<Q", rd(mu, TLS_BLOCK + 0x10, 8))[0]
        n = struct.unpack("<I", rd(mu, bgs + 0x459F0, 4))[0]
        wmem(mu, bgs + 0x459F0, struct.pack("<I", n + 1))
        return None


def test_character_info_restored(env):
    counts, calls = {}, {}
    cg_bgs = va("cgArray") + 0xB54C8
    for enabled in (True, False):
        anim = AnimCounter()
        g = TickGame(env, render_time_view=enabled, anim=anim)
        g.frame(1)
        g.client.key(KB_FORWARD, True)
        g.frame(1)
        g.frame(3)  # a tick and a 2 ms partial step
        g.frame(1)  # a 3 ms partial step
        counts[enabled] = g.world.read(cg_bgs + 0x459F0, 4)
        calls[enabled] = anim.calls
    assert counts[True] == counts[False], counts
    assert calls[True] > calls[False], calls  # the partial steps ran the animation conditions


class StepPmove(EventPmove):
    """EventPmove that also steps up 8 units (pm->viewChange 8, origin z + 8) in the temporary command."""

    def __call__(self, mu):
        from win32_display import arg
        pm = arg(mu, 0)
        ps = struct.unpack("<Q", rd(mu, pm, 8))[0]
        t, now = struct.unpack("<i", rd(mu, pm + 8, 4))[0], struct.unpack("<i", rd(mu, ps, 4))[0]
        super().__call__(mu)
        if t > now and (t - self.phase) % 5:
            z = struct.unpack("<f", rd(mu, ps + 0x24, 4))[0]
            wmem(mu, ps + 0x24, struct.pack("<f", z + 8.0))
            wmem(mu, pm + 0x15C, struct.pack("<f", 8.0))
        return None


def test_step_up_in_the_partial_move_is_smoothed(env):
    g = _run(env, [1], 12, pmove=StepPmove(100001))
    ref = _run(env, [1], 12, enabled=False, pmove=StepPmove(100001))
    lifted = 0
    for v, r in zip(g.drawn, ref.drawn):
        assert _vec(v, 0x1C)[2] == _vec(r, 0x1C)[2]  # the drawn height is the canonical one, not 8 higher
        lifted += _vec(v, 0x1C)[0] != _vec(r, 0x1C)[0]
    assert lifted


def test_angles_follow_without_time_to_move(env):
    g = TickGame(env, kick=(0.0, 0.0, 0.0))
    g.frame(1)
    for _ in range(9):
        g.frame(1)
    while not (g.frame_commands[-1] and struct.unpack_from("<i", g.frame_commands[-1][-1])[0] == g.client.server_time):
        g.frame(1)  # until a frame ends exactly on a tick: no leftover
    # the clock is pulled back by 1 ms: cl->serverTime stays, no tick, no time to move; the mouse still turned
    before = struct.unpack("<3f", g.world.read(va("clients") + CL_VIEWANGLES, 12))
    g.frame(1, delta_change=-1)
    assert not g.frame_commands[-1]
    assert g.times[-1] == g.times[-2]
    ps = g.drawn[-1]
    view = struct.unpack("<3f", g.world.read(va("clients") + CL_VIEWANGLES, 12))
    assert view != before
    delta = _vec(ps, 0x64)
    for i in range(2):
        short = math.floor(f32(f32(view[i] * f32(182.04445)) + 0.5)) & 0xFFFF
        want = _angle_norm180(f32(f32(short * f32(360.0 / 65536.0)) + delta[i]))
        assert _vec(ps, 0x184)[i] == want, (i, _vec(ps, 0x184), want)
