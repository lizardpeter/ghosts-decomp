"""The viewmodel's recoil on a fixed 5 ms grid of the cgame's time (enhanced/bgame/bg_recoil.cpp).

What must hold:
- at every time that is a multiple of 5 ms, the recoil is bit for bit the Store build's with 5 ms frames, whatever the
  frame pattern; with 5 ms frames it is the original at every frame;
- between grid times it is the grid state advanced to the frame's time with the original step (it moves every frame);
- a second call at the same time gives the same result (the cgame may call it twice in a frame);
- a shot (recoilSpeed changed from outside) restarts the grid from that state: after it, at every multiple of 5 ms,
  the recoil is the original 5 ms run from the state at the shot; time going back restarts it too;
- weapons that don't aim down the sight are left alone, as in the original.
"""
import struct

from syms import va
from test_bg_weapons_view import ADS, GUN_KICK, PS, WEAPON, WEAPDEF, COMPLETE
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP

SYMBOL = "?BG_CalculateWeaponMovement_Recoil@@YAXPEAUweaponState_t@@@Z"
GRID_SIZE = 12 * 4 + 12
HIP = [1000.0, 2000.0, 24.0, 40.0]
ADS_KICK = [800.0, 2000.0, 16.0, 20.0]
SHOT = (0.0, 0.0, 0.0, 300.0, -120.0, 0.0)  # recoilAngles, recoilSpeed


def _weapon(aims=True, frac=1.0):
    index = 0x11

    def setup(w):
        w.m.mu.mem_write(PS + 0x420, struct.pack("<If", 0, frac))
        weapdef = bytearray(0xB00)
        struct.pack_into("<ff", weapdef, 0x640, 6.0, 4.0)
        w.m.mu.mem_write(WEAPDEF, bytes(weapdef))
        w.m.mu.mem_write(COMPLETE, bytes(0x100))
        w.u64(va("bg_weaponCompleteDefs") + 8 * index, COMPLETE)
        w.u64(va("bg_weaponDefs") + 8 * index, WEAPDEF)

    def gun_kick(mu):
        rsp = mu.reg_read(UC_X86_REG_RSP)
        outs = [mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9)]
        outs += [struct.unpack("<Q", bytes(mu.mem_read(rsp + 0x28 + 8 * i, 8)))[0] for i in range(6)]
        for p, v in zip(outs, HIP + ADS_KICK):
            mu.mem_write(p, struct.pack("<f", v))

    fakes = {WEAPON: lambda mu: index, GUN_KICK: gun_kick, ADS: lambda mu: 0xA5C300 | int(aims)}
    return setup, fakes


def _ws(frametime, time, recoil):
    ws = bytearray(0x90)
    struct.pack_into("<Q", ws, 0, PS)
    struct.pack_into("<f", ws, 0xC, frametime)
    struct.pack_into("<i", ws, 0x14, time)
    struct.pack_into("<6f", ws, 0x3C, *recoil)
    return bytes(ws)


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def _f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _original(env, weapon, recoil, msec, time=0):
    setup, fakes = weapon
    _, bufs, _, _ = env.machine.call(env.table[SYMBOL], [_ws(_f32(msec * _f32(0.001)), time, recoil)], "void",
                                     setup, _hooks(env, fakes))
    return struct.unpack_from("<6f", bufs[0], 0x3C)


class Enhanced:
    def __init__(self, env, weapon, recoil, time=1000):
        self.env, self.weapon, self.recoil, self.time = env, weapon, tuple(recoil), time
        self.grid = bytes(GRID_SIZE)

    def frame(self, msec, time=None):
        env = self.env
        setup, fakes = self.weapon
        g = env.data("s_recoil")
        grid = self.grid
        self.time = self.time + msec if time is None else time

        def run_setup(w):
            setup(w)
            w.write(g, grid)
        _, bufs, written, _ = env.call(SYMBOL, [_ws(_f32(msec * _f32(0.001)), self.time, self.recoil)],
                                       setup=run_setup, fakes=fakes)
        self.grid = b"".join(written.get(g + i, grid[i:i + 1]) for i in range(GRID_SIZE))
        self.recoil = struct.unpack_from("<6f", bufs[0], 0x3C)
        return self.recoil


def _reference(env, weapon, recoil, total):
    out = {0: tuple(recoil)}
    for t in range(5, total + 1, 5):
        recoil = _original(env, weapon, recoil, 5)
        out[t] = recoil
    return out


PATTERNS = {"1 ms": [1], "2/3 ms": [2, 3], "3 ms": [3], "4 ms": [4], "144 Hz": [7, 7, 7, 6, 7, 7],
            "240 Hz": [4, 4, 4, 4, 4, 5], "16/17 ms": [16, 17, 17], "mixed": [1, 6, 2, 9, 3, 4, 0, 5]}


def _run(env, weapon, pattern, start, total, check):
    """Frames of pattern from `start` (the state at time 0 of the run), checking against the reference."""
    e = Enhanced(env, weapon, start)
    e.frame(0)  # the first call starts the grid at this frame's time
    ref = _reference(env, weapon, start, total)
    t = i = 0
    while t < total:
        msec = pattern[i % len(pattern)]
        i += 1
        state = e.frame(msec)
        t += msec
        if t % 5 == 0 and t in ref:
            check(state, ref[t], t)
    return e


def test_same_recoil_at_every_frame_rate(env):
    for aim in (1.0, 0.0, 0.5):
        weapon = _weapon(frac=aim)
        ref = _reference(env, weapon, SHOT, 250)
        assert ref[250] != ref[0] and ref[20] != ref[0], aim
        for pname, pattern in PATTERNS.items():
            def check(state, want, t):
                assert state == want, (aim, pname, t, state, want)
            _run(env, weapon, pattern, SHOT, 250, check)


def test_original_at_5_ms_and_moves_between(env):
    weapon = _weapon()
    e = Enhanced(env, weapon, SHOT)
    e.frame(0)
    recoil = SHOT
    for _ in range(12):
        recoil = _original(env, weapon, recoil, 5)
        assert e.frame(5) == recoil
    e = Enhanced(env, weapon, SHOT)
    e.frame(0)
    shown = [e.frame(1) for _ in range(4)]
    assert len(set(shown)) == 4, shown
    for n, state in enumerate(shown, 1):
        assert state == _original(env, weapon, SHOT, n), (n, state)


def test_second_call_at_the_same_time(env):
    weapon = _weapon()
    e = Enhanced(env, weapon, SHOT)
    e.frame(0)
    for msec in (3, 1, 7, 2):
        first = e.frame(msec)
        assert e.frame(msec, time=e.time) == first, msec  # same time again: no further step


def test_shot_restarts_the_grid(env):
    weapon = _weapon()
    for pname in ("1 ms", "144 Hz", "mixed"):
        pattern = PATTERNS[pname]
        e = Enhanced(env, weapon, SHOT)
        e.frame(0)
        i = 0
        for _ in range(9):
            e.frame(pattern[i % len(pattern)])
            i += 1
        kicked = list(e.recoil)
        kicked[3] = _f32(kicked[3] + 250.0)
        kicked[4] = _f32(kicked[4] - 90.0)
        e.recoil = tuple(kicked)
        ref = _reference(env, weapon, kicked, 150)
        since = 0
        while since < 150:
            msec = pattern[i % len(pattern)]
            i += 1
            state = e.frame(msec)
            since += msec
            if since % 5 == 0 and since in ref:
                assert state == ref[since], (pname, since, state, ref[since])


def test_time_going_back_restarts(env):
    weapon = _weapon()
    e = Enhanced(env, weapon, SHOT, time=5000)
    for _ in range(6):
        e.frame(3)
    state = e.recoil
    # a new cgame (time back to 100): the state is taken as it is at the frame before
    got = e.frame(4, time=100)
    assert got == _original(env, weapon, state, 4), got


def test_non_ads_weapon_left_alone(env):
    weapon = _weapon(aims=False)
    e = Enhanced(env, weapon, SHOT)
    for msec in (0, 1, 3, 7, 5):
        assert e.frame(msec) == tuple(_f32(v) for v in SHOT)
