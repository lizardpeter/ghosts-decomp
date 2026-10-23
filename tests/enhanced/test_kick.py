"""The view kick on a fixed 5 ms grid (enhanced/bgame/bg_kick.cpp).

What must hold, for the cgame's own kick arrays (cg_s kickAVel/kickAngles):
- at every time that is a multiple of 5 ms, the kick is bit for bit what the Store build's BG_KickAngles gives when
  called with 5 ms frames, whatever the frame pattern (1 ms, 2-3 ms, 144 Hz's 7/6 ms, 4 ms, 16/17 ms, mixed);
- with 5 ms frames it is the original at every frame;
- between grid times it is the grid state advanced by the carried time with the original step (it moves every frame);
- when something else changes the arrays between frames (a shot adds velocity, a spawn clears them), the grid starts
  again from that state: at every multiple of 5 ms after the shot, the kick is the original 5 ms run from the state
  at the shot, whatever the frame pattern and wherever the shot falls; a cleared kick stays cleared;
- any other caller (the bots' arrays) gets the original exactly.
"""
import struct

from syms import va

SYMBOL = "?BG_KickAngles@@YAXPEBUplayerState_s@@HQEAM1@Z"
WEAPON = "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z"
ALT = "?BG_UsingAlternate@@YA_NPEBUplayerState_s@@@Z"
OVERLAY_FN = "?BG_GetOverlay@@YAPEBUADSOverlay@@TWeapon@@_N@Z"
ATTACH_FN = "?BG_GetWeaponAttachments@@YAXTWeapon@@_NQEAPEBUWeaponAttachment@@@Z"
COMPLETE, OVERLAY = 0x510000, 0x530000
CG_KICK_AVEL, CG_KICK_ANGLES = 0xB5268, 0xB5274
KICK_SIZE = 4 * 12 + 8  # KickGrid


def _weapon_setup(index, hip, ads, frac):
    """A weapon with the given center speeds (index 0: none, 2400), hip or ADS by frac, no attachments."""
    ps = bytearray(0x1000)
    struct.pack_into("<IIf", ps, 0x41C, index, 0, frac)

    def setup(w):
        if index:
            complete = bytearray(0x100)
            struct.pack_into("<ff", complete, 0xB4, ads, hip)
            w.m.mu.mem_write(COMPLETE, bytes(complete))
            w.u64(va("bg_weaponCompleteDefs") + 8 * index, COMPLETE)
            w.u64(va("bg_weaponDefs") + 8 * index, 0)
        w.m.mu.mem_write(OVERLAY + 0x20, struct.pack("<I", 0))

    def no_attachments(mu):
        from unicorn.x86_const import UC_X86_REG_R8
        mu.mem_write(mu.reg_read(UC_X86_REG_R8), bytes(32))

    fakes = {WEAPON: lambda mu: index, ALT: lambda mu: 0, OVERLAY_FN: lambda mu: OVERLAY, ATTACH_FN: no_attachments}
    return bytes(ps), setup, fakes


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def _original(env, weapon, vel, ang, msec):
    ps, setup, fakes = weapon
    _, bufs, _, _ = env.machine.call(env.table[SYMBOL], [ps, msec, struct.pack("<3f", *vel), struct.pack("<3f", *ang)],
                                     "void", setup, _hooks(env, fakes))
    return struct.unpack("<3f", bufs[1]), struct.unpack("<3f", bufs[2])  # buffers: ps, vel, ang


def _read(written, address, size, previous):
    return b"".join(written.get(address + i, previous[i:i + 1]) for i in range(size))


class Enhanced:
    """The enhanced function called on the cgame's arrays frame after frame, its statics carried between calls."""

    def __init__(self, env, weapon, vel, ang):
        self.env, self.weapon = env, weapon
        self.vel, self.ang = list(vel), list(ang)
        self.grid = bytes(KICK_SIZE)

    def frame(self, msec, ps_override=None):
        env = self.env
        ps, base, fakes = self.weapon
        cg = va("cgArray")
        k = env.data("s_kick")
        vel_b, ang_b, grid = struct.pack("<3f", *self.vel), struct.pack("<3f", *self.ang), self.grid

        def setup(w):
            base(w)
            w.write(cg + CG_KICK_AVEL, vel_b)
            w.write(cg + CG_KICK_ANGLES, ang_b)
            w.write(k, grid)
        _, _, written, _ = env.call(SYMBOL, [ps_override or ps, msec, cg + CG_KICK_AVEL, cg + CG_KICK_ANGLES],
                                    setup=setup, fakes=fakes)
        self.vel = list(struct.unpack("<3f", _read(written, cg + CG_KICK_AVEL, 12, vel_b)))
        self.ang = list(struct.unpack("<3f", _read(written, cg + CG_KICK_ANGLES, 12, ang_b)))
        self.grid = _read(written, k, KICK_SIZE, grid)
        return tuple(self.vel), tuple(self.ang)


def _reference(env, weapon, vel, ang, total, shots=None):
    """The original with 5 ms frames: {time: state} at every multiple of 5 up to total; shots {time: dvel}."""
    out = {0: (tuple(vel), tuple(ang))}
    vel, ang = list(vel), list(ang)
    for t in range(5, total + 1, 5):
        if shots and (t - 5) in shots:
            vel = [v + d for v, d in zip(vel, shots[t - 5])]
        v, a = _original(env, weapon, vel, ang, 5)
        vel, ang = list(v), list(a)
        out[t] = (v, a)
    return out


PATTERNS = {"1 ms": [1], "2/3 ms": [2, 3], "3 ms": [3], "4 ms": [4], "144 Hz": [7, 7, 7, 6, 7, 7],
            "240 Hz": [4, 4, 4, 4, 4, 5], "16/17 ms": [16, 17, 17], "mixed": [1, 6, 2, 9, 3, 4, 0, 5]}
SHOT = (-160.0, 35.0, 0.0)


def _weapons():
    return {"no weapon": _weapon_setup(0, 0, 0, 0.0), "hip": _weapon_setup(0x11, 1800.0, 900.0, 0.0),
            "ads": _weapon_setup(0x11, 1800.0, 900.0, 1.0)}


def test_same_kick_at_every_frame_rate(env):
    for wname, weapon in _weapons().items():
        ref = _reference(env, weapon, SHOT, (0.0, 0.0, 0.0), 300)
        moved = False
        for pname, pattern in PATTERNS.items():
            e = Enhanced(env, weapon, SHOT, (0.0, 0.0, 0.0))
            t = i = 0
            while t < 300:
                msec = pattern[i % len(pattern)]
                i += 1
                state = e.frame(msec)
                t += msec
                if t % 5 == 0 and t in ref:
                    assert state == ref[t], (wname, pname, t, state, ref[t])
            moved = moved or ref[300] != ref[0]
        assert moved, wname


def test_original_at_5_ms_frames_and_moves_between(env):
    weapon = _weapons()["hip"]
    e = Enhanced(env, weapon, SHOT, (0.0, 0.0, 0.0))
    vel, ang = list(SHOT), [0.0, 0.0, 0.0]
    for _ in range(20):
        assert e.frame(5) == _original(env, weapon, vel, ang, 5)
        vel, ang = map(list, _original(env, weapon, vel, ang, 5))
    # between grid times: the grid state plus the carried time, with the original step
    e = Enhanced(env, weapon, SHOT, (0.0, 0.0, 0.0))
    shown = [e.frame(1) for _ in range(4)]
    assert len(set(shown)) == 4, shown  # it moves every frame
    for n, state in enumerate(shown, 1):
        assert state == _original(env, weapon, SHOT, [0.0, 0.0, 0.0], n), (n, state)


def _after_shot(env, weapon, pattern, warmup, dvel):
    """Frames of `pattern` for `warmup` ms, then a shot (dvel added to the arrays) before the next frame, then 200 ms
    more. Checks the kick at every multiple of 5 ms after the shot against the original 5 ms run from the state at the
    shot; returns how many times it checked."""
    e = Enhanced(env, weapon, SHOT, (0.0, 0.0, 0.0))
    t = i = 0
    while t < warmup:
        msec = pattern[i % len(pattern)]
        e.frame(msec)
        t += msec
        i += 1
    e.vel = list(struct.unpack("<3f", struct.pack("<3f", *(v + d for v, d in zip(e.vel, dvel)))))  # as float32
    ref = _reference(env, weapon, e.vel, e.ang, 200)
    since = checked = 0
    while since < 200:
        msec = pattern[i % len(pattern)]
        i += 1
        state = e.frame(msec)
        since += msec
        if since % 5 == 0 and since in ref:
            assert state == ref[since], (pattern, warmup, since, state, ref[since])
            checked += 1
    return checked


def test_kick_after_a_shot_is_the_same_at_every_frame_rate(env):
    weapon = _weapons()["hip"]
    for pname, pattern in PATTERNS.items():
        for warmup in (0, 3, 52, 61):  # on and off the previous kick's grid
            assert _after_shot(env, weapon, pattern, warmup, (-120.0, -20.0, 0.0)) > 0, (pname, warmup)


def test_cleared_kick_stays_cleared(env):
    weapon = _weapons()["hip"]
    e = Enhanced(env, weapon, SHOT, (0.0, 0.0, 0.0))
    for _ in range(7):
        e.frame(1)
    e.vel, e.ang = [0.0] * 3, [0.0] * 3  # spawn / weapon change clears it
    for _ in range(9):
        assert e.frame(1) == ((0.0,) * 3, (0.0,) * 3)
    # a new kick after that starts its own grid
    e.vel = list(SHOT)
    ref = _reference(env, weapon, SHOT, (0.0, 0.0, 0.0), 60)
    t = 0
    while t < 60:
        state = e.frame(3)
        t += 3
        if t % 5 == 0:
            assert state == ref[t], (t, state, ref[t])


def test_other_callers_get_the_original(env):
    weapon = _weapons()["hip"]
    ps, setup, fakes = weapon
    for msec in (1, 3, 7, 50):
        args = [ps, msec, struct.pack("<3f", *SHOT), struct.pack("<3f", 2.0, -1.0, 0.0)]
        _, got, _, _ = env.call(SYMBOL, args, setup=setup, fakes=fakes)
        _, want, _, _ = env.machine.call(env.table[SYMBOL], args, "void", setup, _hooks(env, fakes))
        assert got[1:] == want[1:], msec


def test_other_callers_keep_their_own_steps(env):
    """Two calls on the same non-cgame arrays, the statics carried between them: still the original's two calls
    (a grid would have merged the two 3 ms calls into a 5 ms and a 1 ms step)."""
    weapon = _weapons()["hip"]
    ps, setup, fakes = weapon
    k = env.data("s_kick")
    vel, ang = struct.pack("<3f", *SHOT), struct.pack("<3f", 0.0, 0.0, 0.0)
    want_v, want_a = list(SHOT), [0.0] * 3
    grid = bytes(KICK_SIZE)
    for _ in range(3):
        g = grid

        def run_setup(w, g=g):
            setup(w)
            w.write(k, g)
        _, got, written, _ = env.call(SYMBOL, [ps, 3, vel, ang], setup=run_setup, fakes=fakes)
        grid = _read(written, k, KICK_SIZE, grid)
        want_v, want_a = _original(env, weapon, want_v, want_a, 3)
        assert struct.unpack("<3f", got[1]) == want_v and struct.unpack("<3f", got[2]) == want_a
        vel, ang = got[1], got[2]


def test_angle_changed_elsewhere_restarts_the_grid(env):
    """Only the angle changed from outside (no velocity change): the grid starts again from it too."""
    weapon = _weapons()["hip"]
    e = Enhanced(env, weapon, SHOT, (0.0, 0.0, 0.0))
    for _ in range(3):
        e.frame(1)
    e.ang = list(struct.unpack("<3f", struct.pack("<3f", e.ang[0] - 1.5, e.ang[1], e.ang[2])))
    ref = _reference(env, weapon, e.vel, e.ang, 40)
    since = 0
    while since < 40:
        state = e.frame(1)
        since += 1
        if since % 5 == 0:
            assert state == ref[since], (since, state, ref[since])
