"""The viewmodel's recoil in the tick loop (P0015 folded: enhanced/cgame/cg_weapons.cpp, enhanced/cgame_mp/cg_tick.cpp;
docs/cgame-frame.md 4.5, 4.10).

The viewmodel's movement half of CG_AddViewWeapon runs once per 5 ms tick with frametime 0.005, so the recoil is the
original BG_CalculateWeaponMovement_Recoil's own 5 ms step; the presentation half steps a copy of the tick's state to
the viewmodel's presentation time. Through whole frames of the enhanced CG_DrawActiveFrame (frame_sim.TickGame) with
the real CG_AddViewWeapon halves and the Store build's BG_CalculateWeaponMovement and recoil (the sway, bob and angle
steps faked; BG_SetWeaponMovementAngles records the weaponState_t each call gets):
- at every tick the canonical recoil (cg_s) is bit for bit the Store build's recoil with 5 ms frames from a shot
  (recoilSpeed set in a tick's events), whatever the frame pattern, aimed, at the hip and half way;
- with 5 ms frames it is the original at every frame;
- the drawn recoil is the canonical one stepped by the time since the latest tick with the original (one step of
  1..4 ms: it moves every frame), and the presentation never writes the canonical state (a second shot later is the
  original from the state at that tick);
- a weapon that doesn't aim down the sight is left alone, as in the original.
(The grid's restart when the time went back is gone with the grid: the ticks are the commands' grid, which restarts
on its own, docs/fps.md 6.2.)
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_sim import CMD_SIZE, Mouse, TickGame, f32, rd, wmem  # noqa: E402
from syms import va  # noqa: E402
from test_tick import EventPmove  # noqa: E402
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP  # noqa: E402

SYMBOL = "?BG_CalculateWeaponMovement_Recoil@@YAXPEAUweaponState_t@@@Z"
GUN_KICK = "?BG_GetGunKickSpeed@@YAXTWeapon@@_NPEAM2222222@Z"
WEAPON = "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z"
ADS = "?BG_IsAimDownSight@@YA_NTWeapon@@_N@Z"
ANGLES = "?BG_SetWeaponMovementAngles@@YAXPEAUweaponState_t@@PEAM@Z"
BOB = "?BG_CalculateWeaponMovement_Bob@@YAXPEAUweaponState_t@@@Z"
MOVEMENT = "?BG_CalculateWeaponMovement@@YAXPEAUweaponState_t@@QEAM1H@Z"
UNNAMED_STEPS = (0x1402971C0, 0x140298100)       # BG_CalculateWeaponMovement's first two steps (the sway; no names)
WEAPDEF, COMPLETE, GUNMODELS, DVAR = 0x520000, 0x510000, 0x528000, 0x529000
HIP = [1000.0, 2000.0, 24.0, 40.0]
ADS_KICK = [800.0, 2000.0, 16.0, 20.0]
SHOT = (0.0, 0.0, 0.0, 300.0, -120.0, 0.0)  # recoilAngles, recoilSpeed
CG_RECOIL = 0xA9AFC
START = 100001
INDEX = 0x11


def _f32s(v):
    return tuple(f32(x) for x in v)


def _gun_kick(mu):
    rsp = mu.reg_read(UC_X86_REG_RSP)
    outs = [mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9)]
    outs += [struct.unpack("<Q", bytes(mu.mem_read(rsp + 0x28 + 8 * i, 8)))[0] for i in range(6)]
    for p, v in zip(outs, HIP + ADS_KICK):
        mu.mem_write(p, struct.pack("<f", v))


def _weapon_setup(w):
    weapdef = bytearray(0xB00)
    struct.pack_into("<ff", weapdef, 0x640, 6.0, 4.0)
    struct.pack_into("<Q", weapdef, 0x8, GUNMODELS)
    w.m.mu.mem_write(WEAPDEF, bytes(weapdef))
    w.m.mu.mem_write(GUNMODELS, bytes(0x200))
    w.m.mu.mem_write(COMPLETE, bytes(0x100))
    w.m.mu.mem_write(DVAR + 0x10, b"\1")
    w.u64(va("bg_weaponCompleteDefs") + 8 * INDEX, COMPLETE)
    w.u64(va("bg_weaponDefs") + 8 * INDEX, WEAPDEF)
    w.u64(va("cg_drawGun"), DVAR)


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def _ws(frametime, recoil, ps):
    ws = bytearray(0x90)
    struct.pack_into("<Q", ws, 0, ps)
    struct.pack_into("<f", ws, 0xC, frametime)
    struct.pack_into("<6f", ws, 0x3C, *recoil)
    return bytes(ws)


PS_BUF = 0x530000


def _original(env, aims, frac, recoil, frametime):
    """The Store build's BG_CalculateWeaponMovement_Recoil for one call with this frametime (seconds)."""
    def setup(w):
        _weapon_setup(w)
        w.m.mu.mem_write(PS_BUF + 0x41C, struct.pack("<IIf", INDEX, 0, frac))
    fakes = {WEAPON: lambda mu: INDEX, GUN_KICK: _gun_kick, ADS: lambda mu: 0xA5C300 | int(aims)}
    _, bufs, _, _ = env.machine.call(env.table[SYMBOL], [_ws(f32(frametime), recoil, PS_BUF)], "void", setup,
                                     _hooks(env, fakes), {})
    return struct.unpack_from("<6f", bufs[0], 0x3C)


def _reference(env, aims, frac, recoil, total):
    out = {0: _f32s(recoil)}
    for t in range(5, total + 1, 5):
        recoil = _original(env, aims, frac, recoil, f32(5 * f32(0.001)))
        out[t] = recoil
    return out


class RecoilGame(TickGame):
    """Frames with the real CG_AddViewWeapon halves and the Store build's BG_CalculateWeaponMovement and recoil."""

    def __init__(self, env, aims=True, frac=1.0, shots=None):
        super().__init__(env, pmove=EventPmove(), mouse=Mouse(0.0, 0.0))
        for sym in ("?CG_AddViewWeapon@@YAXW4LocalClientNum_t@@@Z", MOVEMENT):
            self.fakes.pop(sym, None)
        self.calls = []   # (frame, ws frametime, recoil after the recoil step)
        noop = lambda mu: None

        def angles(mu):
            from win32_display import arg
            ws = arg(mu, 0)
            self.calls.append((self.client.frame_index, struct.unpack("<f", rd(mu, ws + 0xC, 4))[0],
                               struct.unpack("<6f", rd(mu, ws + 0x3C, 24))))
            return None
        self.fakes.update({WEAPON: lambda mu: INDEX, GUN_KICK: _gun_kick, ADS: lambda mu: 0xA5C300 | int(aims),
                           ANGLES: angles, BOB: noop, UNNAMED_STEPS[0]: noop, UNNAMED_STEPS[1]: noop})
        cg = va("cgArray")
        self.world.poke(cg + 0x41C, struct.pack("<IIf", INDEX, 0, frac))
        self.ticks.writes = {t: [(CG_RECOIL, struct.pack("<6f", *v))] for t, v in (shots or {}).items()}

    def call(self, name, args, ret="void"):
        from frame_sim import S, scratch_setup

        def setup(w):
            scratch_setup(w)
            _weapon_setup(w)
        return self.world.call(S[name] if name in S else name, args, setup, self.fakes, ret=ret)

    def recoil_after_ticks(self):
        """{tick time: the canonical recoil after it}: the next tick's row, the cg_s state after the last frame."""
        rows = self.ticks.rows
        out = {}
        for frame_rows in zip(rows, rows[1:]):
            out[frame_rows[0][1]] = frame_rows[1][9]
        out[rows[-1][1]] = struct.unpack("<6f", self.world.read(va("cgArray") + CG_RECOIL, 24))
        return out

    def presented(self, frame):
        """The presentation's call in that frame: the last one."""
        return [c for c in self.calls if c[0] == frame][-1]


PATTERNS = {"1 ms": [1], "2/3 ms": [2, 3], "3 ms": [3], "4 ms": [4], "144 Hz": [7, 7, 7, 6, 7, 7],
            "240 Hz": [4, 4, 4, 4, 4, 5], "16/17 ms": [16, 17, 17], "mixed": [1, 6, 2, 9, 3, 4, 0, 5]}
SHOT_TICK = START + 5 * 4


def _frames(g, pattern, total):
    t = i = 0
    while t < total:
        msec = pattern[i % len(pattern)]
        g.frame(msec)
        t += msec
        i += 1


def _check_ticks(g, ref, name, first=SHOT_TICK):
    checked = 0
    for t, state in g.recoil_after_ticks().items():
        since = t - first + 5
        if t >= first and since in ref:
            assert tuple(state) == ref[since], (name, t, state, ref[since])
            checked += 1
    return checked


def test_same_recoil_at_every_frame_rate(env):
    for aim in (1.0, 0.0, 0.5):
        ref = _reference(env, True, aim, SHOT, 250)
        assert ref[250] != ref[0] and ref[20] != ref[0], aim
        for pname, pattern in PATTERNS.items():
            g = RecoilGame(env, frac=aim, shots={SHOT_TICK: SHOT})
            g.frame(1)
            _frames(g, pattern, 280)
            assert _check_ticks(g, ref, (aim, pname)) >= 45, (aim, pname)


def test_original_at_5_ms_and_moves_between(env):
    g = RecoilGame(env, shots={START: SHOT})
    g.frame(1)          # the shot's tick
    recoil = _original(env, True, 1.0, SHOT, f32(5 * f32(0.001)))
    for _ in range(12):
        g.frame(5)
        recoil = _original(env, True, 1.0, recoil, f32(5 * f32(0.001)))
        assert struct.unpack("<6f", g.world.read(va("cgArray") + CG_RECOIL, 24)) == recoil
        assert g.presented(g.client.frame_index - 1)[2] == recoil   # no time to step: the tick's own
    # between ticks: the drawn recoil is the canonical one stepped by the time since the latest tick
    g = RecoilGame(env, shots={START: SHOT})
    g.frame(1)
    shown, canons = [], set()
    for _ in range(4):
        g.frame(1)
        canon = struct.unpack("<6f", g.world.read(va("cgArray") + CG_RECOIL, 24))
        canons.add(canon)
        rest = g.times[-1] - g.ticks.rows[-1][1]
        frame, frametime, drawn = g.presented(g.client.frame_index - 1)
        assert frametime == f32(rest * 0.001), (rest, frametime)
        assert drawn == _original(env, True, 1.0, canon, f32(rest * 0.001)), (rest, drawn)
        assert drawn == _original(env, True, 1.0, canon, f32(rest * f32(0.001)))  # the original's frame of rest ms
        shown.append(drawn)
    assert len(set(shown)) == 4, shown
    assert len(canons) == 1 and len(g.ticks.rows) == 1  # no tick in these frames: the canonical recoil stood still


def test_second_shot_from_the_canonical_state(env):
    """A second shot at a later tick: from then on the original from the canonical state at that tick, whatever the
    frame pattern (the presentation's steps never reached the canonical state)."""
    second = START + 5 * 23
    ref1 = _reference(env, True, 1.0, SHOT, 23 * 5 - 20)
    kicked = list(ref1[second - SHOT_TICK])
    kicked[3] = f32(kicked[3] + 250.0)
    kicked[4] = f32(kicked[4] - 90.0)
    ref2 = _reference(env, True, 1.0, kicked, 150)
    for pname in ("1 ms", "144 Hz", "mixed"):
        g = RecoilGame(env, shots={SHOT_TICK: SHOT, second: tuple(kicked)})
        g.frame(1)
        _frames(g, PATTERNS[pname], 300)
        assert _check_ticks(g, ref1, pname) >= 15
        assert _check_ticks(g, ref2, pname, first=second) >= 25


def test_non_ads_weapon_left_alone(env):
    g = RecoilGame(env, aims=False, shots={SHOT_TICK: SHOT})
    g.frame(1)
    _frames(g, [1, 3, 7, 5], 100)
    for t, state in g.recoil_after_ticks().items():
        if t >= SHOT_TICK:
            assert tuple(state) == _f32s(SHOT), (t, state)


def test_viewmodel_mode_is_its_own(env):
    """The viewmodel's presentation follows its own mode only: PM_EXTRAPOLATE with a 7 ms lead steps the copy by the
    rest + 7; PM_INTERPOLATE draws the latest tick's state; the own view's PM_INTERPOLATE changes nothing of it."""
    def run(category=None, mode=None):
        g = RecoilGame(env, shots={START: SHOT})
        if category is not None:
            g.world.poke(env.data("cg_presentMode") + 4 * category, struct.pack("<i", mode))
            g.world.poke(env.data("cg_presentExtrapolateMsec"), struct.pack("<d", 7.0))
        g.frame(1)
        out = []
        for _ in range(3):
            g.frame(1)
            out.append(g.presented(g.client.frame_index - 1)[1:])
        return out
    base = run()
    assert [round(ft * 1000) for ft, _ in base] == [1, 2, 3]
    assert run(0, 1) == base                                # the own view's mode: not the viewmodel's
    assert [round(ft * 1000) for ft, _ in run(1, 2)] == [8, 9, 10]
    assert [ft for ft, _ in run(1, 1)] == [0.0, 0.0, 0.0]
