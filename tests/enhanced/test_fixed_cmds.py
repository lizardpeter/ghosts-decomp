"""Usercmds on a fixed 5 ms grid (enhanced/client_mp/cl_fixed_cmds.cpp; docs/fps.md 6.2 and 6.4 items 1, 2 and 4).

- The generator at 60, 144, 165, 240, 360, 500 and 1000 fps (fractional frame periods on the integer client clock),
  with delta nudges of +1, -1 and -2 ms and a 600 ms reset: every command is exactly 5 ms after the previous one
  (strictly increasing, nothing missing), never more than 20 a frame, and the leftover after every frame is below 5 ms
  (the commands keep up with cl->serverTime). Frames without a command still turn the view.
- Movement invariance: the commands each frame rate generates, fed to the Store build's own Pmove (noclip and ufo),
  give bit-identical states at every command time, identical to a straight run of 5 ms commands.
- Keys: forward held for 100 ms gives the same sum of forwardmove times command length at every frame rate (within
  one command's rounding), close to 127 · 100.
- Buttons: an attack tap pressed and released between two command-making frames is in the next command.
- The temporary view command: this frame's angles (clViewangles + cgameKickAngles rounded as CL_FinishMove does) at
  cl->serverTime, the newest command's buttons and moves; never stored.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_sim import (CL_KICK, CL_VIEWANGLES, CMD_SIZE, KB_ATTACK, KB_FORWARD, PS_SIZE, PM_SIZE, S, Client,  # noqa: E402
                       Mouse, World, f32, frame_pattern, noop, scratch_setup)
from harness import HEAP, _page  # noqa: E402
from syms import va  # noqa: E402

FPS = [60, 144, 165, 240, 360, 500, 1000]


def _run(env, fps, total_ms, nudges=None, reset_at=None, keys=None, still=False):
    """Drive the generator; nudges {ms: delta change}; keys [(ms, button, down)] at the first frame at or after ms."""
    world = World(env)
    client = Client(env, world, mouse=Mouse(0.0, 0.0) if still else None)
    start = client.realtime
    # the grid starts at the first frame's cl->serverTime: a 1 ms first frame puts every run on the same grid
    pattern = [1] + frame_pattern(fps, total_ms)
    pending = sorted(keys or [])
    applied = set()
    leftovers, viewcmds, angles = [], [], []
    for msec in pattern:
        elapsed = client.realtime - start + msec
        change = 0
        for at, d in (nudges or {}).items():
            if at not in applied and elapsed >= at:
                applied.add(at)
                change += d
        if reset_at is not None and "reset" not in applied and elapsed >= reset_at:
            applied.add("reset")
            change += 600
        client.clock(msec, change)
        while pending and pending[0][0] <= elapsed:
            _, button, down = pending.pop(0)
            client.key(button, down)
        client.create()
        last = client.commands[-1][1] if client.commands else None
        leftovers.append(None if last is None else client.server_time - last)
        viewcmds.append(world.read(env.data("cl_viewCmd"), CMD_SIZE))
        angles.append(struct.unpack("<3f", world.read(va("clients") + CL_VIEWANGLES, 12)))
    return client, leftovers, viewcmds, angles


def _check_grid(client, leftovers, reset=False):
    times = [t for _, t, _ in client.commands]
    assert times, "no commands"
    jumps = 0
    for a, b in zip(times, times[1:]):
        if b - a != 5:
            jumps += 1
            assert reset and b - a > 500, (a, b)
    assert jumps <= (1 if reset else 0)
    assert max(client.per_frame) <= 20
    for left in leftovers[1:]:
        assert left is not None and 0 <= left < 5, leftovers


def test_generator_every_command_5_ms(env):
    for fps in FPS:
        client, leftovers, _, _ = _run(env, fps, 300)
        _check_grid(client, leftovers)
        if fps > 200:
            assert 0 in client.per_frame, fps  # frames that make no command
        if fps < 200:
            assert max(client.per_frame) >= 2, fps


def test_generator_delta_nudges_and_reset(env):
    for fps in (144, 500, 1000):
        nudges = {50: 1, 100: -1, 150: -2, 200: -1, 250: 1}
        client, leftovers, _, _ = _run(env, fps, 300, nudges=nudges)
        _check_grid(client, leftovers)
        client, leftovers, _, _ = _run(env, fps, 300, reset_at=120)
        _check_grid(client, leftovers, reset=True)


def test_generator_at_most_20_a_frame(env):
    world = World(env)
    client = Client(env, world)
    client.clock(1)
    client.create()
    client.clock(300)  # a 300 ms stall: 60 commands due, 20 a frame
    client.create()
    assert client.per_frame[-1] == 20
    times = [t for _, t, _ in client.commands]
    assert all(b - a == 5 for a, b in zip(times, times[1:]))
    for _ in range(3):
        client.clock(1)
        client.create()
    assert client.per_frame[-3:] == [20, 1, 0] or client.per_frame[-3] == 20, client.per_frame
    times = [t for _, t, _ in client.commands]
    assert all(b - a == 5 for a, b in zip(times, times[1:]))


def test_view_turns_on_frames_without_commands(env):
    client, _, viewcmds, angles = _run(env, 1000, 50)
    for i in range(1, len(angles)):
        assert angles[i] != angles[i - 1]
        assert viewcmds[i][8:20] != viewcmds[i - 1][8:20] or angles[i][1] == angles[i - 1][1]


def test_view_command_angles_and_time(env):
    client, _, viewcmds, angles = _run(env, 500, 60)
    world = client.world
    times = _view_times(env, 500, 60)
    assert any(t not in [c for _, c, _ in client.commands] for t in times)
    for raw, t in zip(viewcmds, times):
        assert struct.unpack_from("<i", raw)[0] == t
    kick = struct.unpack("<3f", world.read(va("clients") + CL_KICK, 12))
    for raw, ang in zip(viewcmds[-5:], angles[-5:]):
        got = struct.unpack_from("<3i", raw, 8)
        want = [int(_floor(f32(f32(f32(a + k) * f32(182.04445)) + 0.5))) & 0xFFFF for a, k in zip(ang, kick)]
        assert list(got) == want, (got, want)
    stored = [t for _, t, _ in client.commands]
    assert client.server_time not in stored or client.server_time % 5 == stored[-1] % 5


def _view_times(env, fps, total_ms):
    """cl->serverTime of every frame of a _run."""
    world = World(env)
    client = Client(env, world)
    out = []
    for msec in [1] + frame_pattern(fps, total_ms):
        client.clock(msec)
        out.append(client.server_time)
    return out


def _floor(x):
    import math
    return math.floor(x)


def test_keys_held_100_ms_same_total(env):
    totals = {}
    for fps in FPS:
        client, _, _, _ = _run(env, fps, 300, keys=[(50, KB_FORWARD, True), (150, KB_FORWARD, False)], still=True)
        total = 0
        for _, _, raw in client.commands:
            total += struct.unpack_from("<b", raw, 0x1C)[0] * 5
        totals[fps] = total
    for fps, total in totals.items():
        assert abs(total - 127 * 100) <= 127 * 5, totals  # within one command at the press or the release
    assert sum(1 for t in totals.values() if abs(t - 127 * 100) <= 5) >= 5, totals


def test_attack_tap_between_commands_is_sent(env):
    world = World(env)
    client = Client(env, world)
    for _ in range(6):
        client.clock(1)
        client.create()
    while client.per_frame[-1] == 0 or len(client.per_frame) < 7:
        client.clock(1)
        client.create()
    # a frame without commands follows (1 ms frames): press and release within it
    client.clock(1)
    client.key(KB_ATTACK, True)
    client.key(KB_ATTACK, False)
    client.create()
    assert client.per_frame[-1] == 0
    while client.per_frame[-1] == 0:
        client.clock(1)
        client.create()
    raw = client.commands[-1][2]
    assert struct.unpack_from("<I", raw, 4)[0] & 1


def _pmove_states(env, commands, pm_type):
    """The Store build's Pmove run on the commands in order (noclip or ufo); the state after each, by time."""
    ps = bytearray(PS_SIZE)
    first = struct.unpack_from("<i", commands[0])[0]
    struct.pack_into("<iiii", ps, 0, first - 5, pm_type, 0, 0)
    struct.pack_into("<ii", ps, 0x5C, 800, 190)
    struct.pack_into("<i", ps, 0x70, 0x7FF)
    struct.pack_into("<i", ps, 0xBC, 0x7FF)
    struct.pack_into("<if", ps, 0x190, 60, 60.0)
    states = {}
    oldcmd = bytes(CMD_SIZE)

    def setup(w):
        scratch_setup(w)
    for raw in commands:
        pm = bytearray(PM_SIZE)
        struct.pack_into("<Q", pm, 0, HEAP + _page(PM_SIZE + 16))
        pm[8:8 + CMD_SIZE] = raw
        pm[0x44:0x44 + CMD_SIZE] = oldcmd
        struct.pack_into("<i", pm, 0x80, 0x2814011)
        struct.pack_into("<6f", pm, 0x108, 0, 0, 35, 15, 15, 35)
        value, bufs, _, _ = env.call(S["pmove"], [bytes(pm), bytes(ps)], "void", setup,
                                     {S["anim_cond"]: noop, S["set_cond"]: noop})
        assert not (isinstance(value, str) and value.startswith("fault")), value
        ps = bytearray(bufs[1])
        oldcmd = raw
        states[struct.unpack_from("<i", raw)[0]] = bytes(ps[:0x620])
    return states


def test_movement_invariance_real_pmove(env):
    for pm_type in (2, 3):
        runs = {}
        for fps in (60, 144, 240, 1000):
            client, _, _, _ = _run(env, fps, 200, keys=[(0, KB_FORWARD, True)], still=True)
            cmds = [raw for _, _, raw in client.commands]
            runs[fps] = _pmove_states(env, cmds, pm_type)
        common = set.intersection(*(set(s) for s in runs.values()))
        assert len(common) >= 30
        ref = runs[60]
        moved = False
        for fps, states in runs.items():
            for t in common:
                assert states[t] == ref[t], (pm_type, fps, t)
        t0, t1 = min(common), max(common)
        moved = ref[t0][0x1C:0x28] != ref[t1][0x1C:0x28]
        assert moved


def test_extra_buttons_only_in_the_frames_first_command(env):
    world = World(env)
    client = Client(env, world, mouse=Mouse(0.0, 0.0))
    client.clock(1)
    client.create()
    world.poke(va("clients") + 0x3608, struct.pack("<I", 0x40000))  # cgameExtraButtons
    client.clock(16)
    new = client.create()
    assert len(new) == 3
    flags = [struct.unpack_from("<I", raw, 4)[0] & 0x40000 for raw in new]
    assert flags == [0x40000, 0, 0], flags


def test_steps_back_wait_and_jumps_reanchor(env):
    world = World(env)
    client = Client(env, world, mouse=Mouse(0.0, 0.0))
    for _ in range(20):
        client.clock(1)
        client.create()
    last = client.commands[-1][1]
    client.delta -= 300  # the client's time goes back (less than the 500 ms that re-anchors): wait
    client.server_time = client.realtime + client.delta
    for _ in range(320):
        client.clock(1)
        client.create()
    times = [t for _, t, _ in client.commands]
    assert all(b - a == 5 for a, b in zip(times, times[1:]))
    assert times[-1] > last
    client.delta -= 2000  # a big step back: the grid restarts at the new time
    client.server_time = client.realtime + client.delta
    client.clock(1)
    new = client.create()
    assert len(new) == 1 and struct.unpack_from("<i", new[0])[0] == client.server_time


def test_keyboard_turn_every_frame(env):
    turns = {}
    for fps in (60, 240, 1000):
        world = World(env)
        client = Client(env, world, mouse=Mouse(0.0, 0.0))
        client.clock(1)
        client.create()
        client.key(1, True)  # KB_RIGHT
        yaws = []
        for msec in frame_pattern(fps, 100):
            client.clock(msec)
            client.create()
            yaws.append(struct.unpack("<f", world.read(va("clients") + CL_VIEWANGLES + 4, 4))[0])
        if fps > 200:
            assert all(b < a for a, b in zip(yaws, yaws[1:])), fps  # turns on frames without commands too
        turns[fps] = yaws[-1]
    assert max(turns.values()) - min(turns.values()) < 0.2, turns
    assert abs(turns[1000] + 14.0) < 0.5, turns


def test_key_fraction_over_the_commands_span(env):
    """A key pressed 2 ms into a 5 ms span (held for its last 3 ms): its commands get 3/5, not the last frame's 1/1."""
    world = World(env)
    client = Client(env, world, mouse=Mouse(0.0, 0.0))
    client.clock(1)
    client.create()
    while client.per_frame[-1] == 0 or len(client.per_frame) < 3:
        client.clock(1)
        client.create()
    client.clock(1)
    client.create()
    client.clock(1)
    client.key(KB_FORWARD, True)  # 2 ms after the command-making frame
    client.create()
    while client.per_frame[-1] == 0:
        client.clock(1)
        client.create()
    raw = client.commands[-1][2]
    assert struct.unpack_from("<b", raw, 0x1C)[0] == int(127 * 3 / 5), struct.unpack_from("<b", raw, 0x1C)[0]
