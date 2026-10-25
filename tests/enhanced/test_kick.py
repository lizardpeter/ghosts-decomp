"""The view kick in the tick loop (P0014 folded: enhanced/cgame_mp/cg_tick.cpp, enhanced/bgame/bg_kick.cpp;
docs/cgame-frame.md 4.5, 4.10).

The cgame's kick (cg_s kickAVel/kickAngles) is integrated once per 5 ms tick by the unchanged original BG_KickAngles
with 5; the presentation steps a copy of it forward to the render time for the view command only. What must hold,
through whole frames of the enhanced CG_DrawActiveFrame (frame_sim.TickGame):
- at every tick the kick is bit for bit what the Store build's BG_KickAngles gives when called with 5 ms frames,
  whatever the frame pattern (1 ms, 2-3 ms, 144 Hz's 7/6 ms, 4 ms, 16/17 ms, mixed with 0 ms frames), for no weapon,
  hip and ADS center speeds;
- with 5 ms frames it is the original at every frame;
- between ticks the view command carries the canonical kick stepped by the time since the latest tick with the
  original step (it moves every frame, and the canonical kick doesn't);
- a shot (velocity added in a tick's events) gives at every later tick the original 5 ms run from the state at the
  shot, whatever the frame pattern and wherever the shot falls;
- without otherFlags 0x4000 (a spawn, a kill cam) the kick is cleared in the next tick and stays cleared;
- a change of the arrays from outside between frames is the state the next tick integrates from;
- any other caller (the bots' arrays) gets the original: BG_KickAngles is not replaced.
"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_sim import CMD_SIZE, Mouse, TickGame, f32, rd, wmem  # noqa: E402
from syms import va  # noqa: E402
from test_tick import EventPmove, kick_step  # noqa: E402

SYMBOL = "?BG_KickAngles@@YAXPEBUplayerState_s@@HQEAM1@Z"
WEAPON = "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z"
ALT = "?BG_UsingAlternate@@YA_NPEBUplayerState_s@@@Z"
OVERLAY_FN = "?BG_GetOverlay@@YAPEBUADSOverlay@@TWeapon@@_N@Z"
ATTACH_FN = "?BG_GetWeaponAttachments@@YAXTWeapon@@_NQEAPEBUWeaponAttachment@@@Z"
COMPLETE, OVERLAY = 0x510000, 0x530000
CG_KICK_AVEL = 0xB5268
START = 100001


class Weapon:
    """A weapon with the given center speeds (index 0: none, 2400), hip or ADS by frac, no attachments."""

    def __init__(self, index, hip, ads, frac):
        self.index, self.hip, self.ads, self.frac = index, hip, ads, frac
        ps = bytearray(0x1000)
        struct.pack_into("<IIf", ps, 0x41C, index, 0, frac)
        self.ps = bytes(ps)

    def setup(self, w):
        if self.index:
            complete = bytearray(0x100)
            struct.pack_into("<ff", complete, 0xB4, self.ads, self.hip)
            w.m.mu.mem_write(COMPLETE, bytes(complete))
            w.u64(va("bg_weaponCompleteDefs") + 8 * self.index, COMPLETE)
            w.u64(va("bg_weaponDefs") + 8 * self.index, 0)
        w.m.mu.mem_write(OVERLAY + 0x20, struct.pack("<I", 0))

    def fakes(self):
        def no_attachments(mu):
            from unicorn.x86_const import UC_X86_REG_R8
            mu.mem_write(mu.reg_read(UC_X86_REG_R8), bytes(32))
        return {WEAPON: lambda mu: self.index, ALT: lambda mu: 0, OVERLAY_FN: lambda mu: OVERLAY,
                ATTACH_FN: no_attachments}


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def _original(env, weapon, vel, ang, msec):
    """The Store build's BG_KickAngles."""
    _, bufs, _, _ = env.machine.call(env.table[SYMBOL], [weapon.ps, msec, struct.pack("<3f", *vel),
                                                         struct.pack("<3f", *ang)], "void", weapon.setup,
                                     _hooks(env, weapon.fakes()), {})
    return struct.unpack("<3f", bufs[1]), struct.unpack("<3f", bufs[2])


def _reference(env, weapon, vel, ang, total, shots=None):
    """The original with 5 ms frames: {time since the start: (vel, ang)} after each step; shots {time: dvel} added
    before the step that ends at that time."""
    out = {0: (tuple(vel), tuple(ang))}
    vel, ang = list(vel), list(ang)
    for t in range(5, total + 1, 5):
        if shots and t in shots:
            vel = list(struct.unpack("<3f", struct.pack("<3f", *(v + d for v, d in zip(vel, shots[t])))))
        v, a = _original(env, weapon, vel, ang, 5)
        vel, ang = list(v), list(a)
        out[t] = (v, a)
    return out


class KickGame(TickGame):
    """Frames with the weapon's kick functions, the weapon in the predicted state, and a Pmove fake (the kick never
    depends on the movement)."""

    def __init__(self, env, weapon, vel, ang=(0.0, 0.0, 0.0), shots=None):
        super().__init__(env, kick_avel=vel, kick=ang, pmove=EventPmove(), mouse=Mouse(0.0, 0.0), shots=shots)
        self.fakes.update(weapon.fakes())
        self.world.poke(va("cgArray") + 0x41C, weapon.ps[0x41C:0x428])
        self.weapon = weapon

    def call(self, name, args, ret="void"):
        from frame_sim import S, scratch_setup

        def setup(w):
            scratch_setup(w)
            self.weapon.setup(w)
        return self.world.call(S[name] if name in S else name, args, setup, self.fakes, ret=ret)

    def kicks(self):
        """{tick time: (vel, ang)} after the tick's step: the next tick's row, or the arrays after the last frame."""
        rows = self.ticks.rows
        out = {}
        for row, nxt in zip(rows, rows[1:]):
            kick = nxt[8]
            out[row[1]] = (struct.unpack("<3f", kick[:12]), struct.unpack("<3f", kick[12:]))
        last = struct.unpack("<6f", self.world.read(va("cgArray") + CG_KICK_AVEL, 24))
        out[rows[-1][1]] = (last[:3], last[3:])
        return out


PATTERNS = {"1 ms": [1], "2/3 ms": [2, 3], "3 ms": [3], "4 ms": [4], "144 Hz": [7, 7, 7, 6, 7, 7],
            "240 Hz": [4, 4, 4, 4, 4, 5], "16/17 ms": [16, 17, 17], "mixed": [1, 6, 2, 9, 3, 4, 0, 5]}
SHOT = (-160.0, 35.0, 0.0)


def _weapons():
    return {"no weapon": Weapon(0, 0, 0, 0.0), "hip": Weapon(0x11, 1800.0, 900.0, 0.0),
            "ads": Weapon(0x11, 1800.0, 900.0, 1.0)}


def _frames(g, pattern, total):
    t = i = 0
    while t < total:
        msec = pattern[i % len(pattern)]
        g.frame(msec)
        t += msec
        i += 1


def test_same_kick_at_every_frame_rate(env):
    for wname, weapon in _weapons().items():
        ref = _reference(env, weapon, SHOT, (0.0, 0.0, 0.0), 300)
        assert ref[300] != ref[0], wname
        for pname, pattern in PATTERNS.items():
            g = KickGame(env, weapon, SHOT)
            g.frame(1)       # the first tick, at START: its step is the first 5 ms of the reference
            _frames(g, pattern, 300)
            kicks = g.kicks()
            checked = 0
            for t, state in kicks.items():
                since = t - START + 5
                if since in ref:
                    assert state == ref[since], (wname, pname, t, state, ref[since])
                    checked += 1
            assert checked >= 55, (wname, pname, checked)


def test_original_at_5_ms_frames_and_moves_between(env):
    weapon = _weapons()["hip"]
    g = KickGame(env, weapon, SHOT)
    vel, ang = list(SHOT), [0.0, 0.0, 0.0]
    for _ in range(20):
        g.frame(5 if g.ticks.rows else 1)
        vel, ang = map(list, _original(env, weapon, vel, ang, 5))
        assert struct.unpack("<6f", g.world.read(va("cgArray") + CG_KICK_AVEL, 24)) == tuple(vel + ang)
    # between ticks: the view command's kick is the canonical one stepped by the time since the latest tick
    g = KickGame(env, weapon, SHOT)
    g.frame(1)
    shown = []
    for _ in range(4):
        g.frame(1)
        canon = struct.unpack("<6f", g.world.read(va("cgArray") + CG_KICK_AVEL, 24))
        rest = g.times[-1] - g.ticks.rows[-1][1]
        stepped = _step(env, weapon, canon[:3], canon[3:], rest)
        view = g.world.read(env.data("cl_viewCmd"), CMD_SIZE)
        want = tuple(math.floor(f32(f32(0.0 + stepped[i]) * f32(182.04445)) + 0.5) & 0xFFFF for i in range(3))
        got = tuple(v & 0xFFFF for v in struct.unpack_from("<3i", view, 8))
        assert got == want, (rest, got, want)
        assert stepped == _original(env, weapon, canon[:3], canon[3:], rest)[1]  # the original step for whole ms
        shown.append(got)
    assert len(set(shown)) == 4, shown  # it moves every frame
    assert len({struct.unpack("<6f", r[8]) for r in g.ticks.rows}) == 1  # the canonical kick only moved at the tick


def _step(env, weapon, vel, ang, msec):
    _, bufs, _, _ = env.call("?BG_KickAnglesStep@@YAXPEBUplayerState_s@@MQEAM1@Z",
                             [weapon.ps, ("f", float(msec)), struct.pack("<3f", *vel), struct.pack("<3f", *ang)],
                             setup=weapon.setup, fakes=weapon.fakes())
    return struct.unpack("<3f", bufs[2])


def test_kick_after_a_shot_is_the_same_at_every_frame_rate(env):
    weapon = _weapons()["hip"]
    dvel = (-120.0, -20.0, 0.0)
    for at in (0, 15, 55, 60):      # the shot's tick, after the start: on and off the previous kick's settling
        shot_tick = START + at
        ref = _reference(env, weapon, SHOT, (0.0, 0.0, 0.0), 260, shots={at + 5: dvel})
        for pname, pattern in PATTERNS.items():
            g = KickGame(env, weapon, SHOT, shots={shot_tick: dvel})
            g.frame(1)
            _frames(g, pattern, 260)
            checked = 0
            for t, state in g.kicks().items():
                since = t - START + 5
                if since in ref:
                    assert state == ref[since], (pname, at, t, state, ref[since])
                    checked += t >= shot_tick
            assert checked > 30, (pname, at, checked)


def test_cleared_kick_stays_cleared(env):
    weapon = _weapons()["hip"]
    g = KickGame(env, weapon, SHOT)
    g.frame(1)
    for _ in range(7):
        g.frame(1)
    cg = va("cgArray")
    g.world.poke(cg + 0x10, struct.pack("<I", 0))  # otherFlags without 0x4000 (a spawn, a kill cam)
    n = len(g.ticks.rows)
    for _ in range(12):
        g.frame(1)
    assert len(g.ticks.rows) > n + 1
    assert struct.unpack("<6f", g.world.read(cg + CG_KICK_AVEL, 24)) == (0.0,) * 6
    for row in g.ticks.rows[n + 1:]:
        assert struct.unpack("<6f", row[8]) == (0.0,) * 6
    # a new kick after that, with the flag back: the original 5 ms run from it
    g.world.poke(cg + 0x10, struct.pack("<I", 0x4000))
    g.world.poke(cg + CG_KICK_AVEL, struct.pack("<3f", *SHOT))
    first = g.ticks.rows[-1][1] + 5
    _frames(g, [3], 60)
    ref = _reference(env, weapon, SHOT, (0.0, 0.0, 0.0), 60)
    for t, state in g.kicks().items():
        if t >= first and t - first + 5 in ref:
            assert state == ref[t - first + 5], (t, state)


def test_change_from_outside_is_the_next_ticks_state(env):
    """Only the angle changed from outside between frames (no velocity change): the next ticks integrate from it."""
    weapon = _weapons()["hip"]
    g = KickGame(env, weapon, SHOT)
    g.frame(1)
    for _ in range(3):
        g.frame(1)
    cg = va("cgArray")
    k = list(struct.unpack("<6f", g.world.read(cg + CG_KICK_AVEL, 24)))
    k[3] = f32(k[3] - 1.5)
    g.world.poke(cg + CG_KICK_AVEL, struct.pack("<6f", *k))
    first = g.ticks.rows[-1][1] + 5
    _frames(g, [1], 40)
    ref = _reference(env, weapon, k[:3], k[3:], 40)
    checked = 0
    for t, state in g.kicks().items():
        if t >= first and t - first + 5 in ref:
            assert state == ref[t - first + 5], (t, state)
            checked += 1
    assert checked >= 7


def test_other_callers_get_the_original(env):
    """BG_KickAngles is the original for every caller, its steps its own (two 3 ms calls are two 3 ms steps)."""
    weapon = _weapons()["hip"]
    for msec in (1, 3, 7, 50):
        args = [weapon.ps, msec, struct.pack("<3f", *SHOT), struct.pack("<3f", 2.0, -1.0, 0.0)]
        _, got, _, _ = env.call(SYMBOL, args, setup=weapon.setup, fakes=weapon.fakes())
        _, want, _, _ = env.machine.call(env.table[SYMBOL], args, "void", weapon.setup, _hooks(env, weapon.fakes()), {})
        assert got[1:] == want[1:], msec
    vel, ang = list(SHOT), [0.0] * 3
    want_v, want_a = list(SHOT), [0.0] * 3
    for _ in range(3):
        _, got, _, _ = env.call(SYMBOL, [weapon.ps, 3, struct.pack("<3f", *vel), struct.pack("<3f", *ang)],
                                setup=weapon.setup, fakes=weapon.fakes())
        want_v, want_a = _original(env, weapon, want_v, want_a, 3)
        vel, ang = struct.unpack("<3f", got[1]), struct.unpack("<3f", got[2])
        assert vel == want_v and ang == want_a
