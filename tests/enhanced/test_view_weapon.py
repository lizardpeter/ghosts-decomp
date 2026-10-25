"""The viewmodel split (enhanced/cgame/cg_weapons.cpp; docs/cgame-frame.md 4.10), against the Store build's
CG_AddViewWeapon with the differential test's 1200 inputs (tests/differential/test_cg_weapons.py: every callee a
logged fake):
- outside a tick-loop frame the enhanced CG_AddViewWeapon is the original: the same calls with the same arguments,
  the same writes;
- the tick half (CG_ViewWeaponTick) writes exactly what the original writes to the integrated state (the ADS state,
  the hip value, recoil, sway, base angles and origin, the idle factor), with the same weaponState_t, and makes none
  of the presentation's calls (models, gun flag, placement, scene), its speed from 14026A870 instead of cg.xyspeed;
- the presentation half writes none of the integrated state, steps a copy of it (the weaponState_t BG_CalculateWeapon
  Movement gets is cg_s's with the frametime of the time since the latest tick), and makes the original's placement
  and scene calls.
"""
import random
import struct

import test_cg_weapons as d
from syms import va

SYMBOL = d.SYMBOL
TICK = "?CG_ViewWeaponTick@@YAXW4LocalClientNum_t@@@Z"
SPEED = "?sub_14026A870@@YAMPEBUplayerState_s@@H@Z"
STATE = [(0x3330, 0x20), (0x630, 8), (0xA9AD8, 0x40), (0x10E8C0, 8)]  # the integrated state (cg_s), whole qwords
PRESENT_CALLS = {"BG_GetViewmodelWeapon", "sub_14018DB60", "R_RegisterModel", "sub_14037AEA0", "sub_14037AEF0", "sub_14028F230",
                 "sub_1402C59B0", "sub_1402F7640", "sub_1402AF8A0", "sub_14028F050", "sub_1402F51A0",
                 "sub_1402F30A0"}


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def _state(written, base):
    out = {}
    for off, n in STATE:
        for i in range(n):
            a = base + off + i
            if a in written:
                out[a] = written[a]
    return out


def _speed(mu):
    """14026A870, faked: cg.xyspeed + 1 (the Store run gets that in cg.xyspeed: the tick must use this, not cg's)."""
    from unicorn.x86_const import UC_X86_REG_XMM0
    v = struct.unpack("<f", bytes(mu.mem_read(va("cgArray") + 0xB5264, 4)))[0]
    mu.reg_write(UC_X86_REG_XMM0, struct.unpack("<I", struct.pack("<f", v + 1.0))[0])
    return None


def _inputs(n):
    r = random.Random(4815)
    return [d._input(r) for _ in range(n)]


def _run(env, case, symbol, loop_frame, original=False, speed_plus_one=False):
    flag = env.data("cg_tickLoopFrame")

    def setup(w):
        case["setup"](w)
        w.write(flag, struct.pack("<i", loop_frame))
        if speed_plus_one:
            a = va("cgArray") + 0xB5264
            v = struct.unpack("<f", bytes(w.m.mu.mem_read(a, 4)))[0]
            w.write(a, struct.pack("<f", v + 1.0))
    fakes = dict(case["fakes"])
    fakes[SPEED] = _speed
    target = env.table[symbol] if original else env.dll.exports[symbol]
    value, _, written, observed = env.machine.call(target, case["args"], "void", setup, _hooks(env, fakes), {})
    assert not (isinstance(value, str) and value.startswith("fault")), value
    lo, hi = env.dll.base, env.dll.base + env.dll.size
    return {a: v for a, v in written.items() if not lo <= a < hi}, observed


def test_faithful_outside_the_tick_loop(env):
    for n, case in enumerate(_inputs(1200)):
        mine = _run(env, case, SYMBOL, 0)
        theirs = _run(env, case, SYMBOL, 0, original=True)
        assert mine[1] == theirs[1], (n, next(((i, a, b) for i, (a, b) in enumerate(zip(mine[1], theirs[1])) if a != b),
                                             (len(mine[1]), len(theirs[1]))))
        assert mine[0] == theirs[0], n


def _calls(observed):
    return [c for c in observed if c[0] == "call"]


def test_tick_half_is_the_originals_movement(env):
    cg = va("cgArray")
    moved = 0
    for n, case in enumerate(_inputs(1200)):
        theirs_w, theirs_o = _run(env, case, SYMBOL, 0, original=True, speed_plus_one=True)
        mine_w, mine_o = _run(env, case, TICK, 1)
        want = [c for c in _calls(theirs_o) if c[1] not in PRESENT_CALLS]
        got = [c for c in _calls(mine_o) if c[1] != "BG_GetViewmodelWeapon"]
        assert got == want, (n, got[:6], want[:6])
        assert _state(mine_w, cg) == _state(theirs_w, cg), n
        assert not set(mine_w) - set(_state(mine_w, cg)), (n, sorted(hex(a) for a in set(mine_w) - set(_state(mine_w, cg)))[:8])
        moved += any(c[1] == "BG_CalculateWeaponMovement" for c in want)
    assert moved > 100, moved


def test_presentation_half_steps_a_copy(env):
    cg = va("cgArray")
    stepped = 0
    for n, case in enumerate(_inputs(600)):
        theirs_w, theirs_o = _run(env, case, SYMBOL, 0, original=True)
        mine_w, mine_o = _run(env, case, SYMBOL, 1)
        assert not _state(mine_w, cg), (n, sorted(hex(a) for a in _state(mine_w, cg))[:12])
        theirs_c, mine_c = _calls(theirs_o), _calls(mine_o)
        drop = {"BG_GetViewmodelWeapon", "BG_IsAimDownSight", "sub_14027B740", "BG_CalculateWeaponMovement"}
        a_, b_ = [c for c in mine_c if c[1] not in drop], [c for c in theirs_c if c[1] not in drop]
        assert a_ == b_, (n, next(((i, x, y) for i, (x, y) in enumerate(zip(a_, b_)) if x != y), (len(a_), len(b_))))
        mv = [c for c in mine_c if c[1] == "BG_CalculateWeaponMovement"]
        tv = [c for c in theirs_c if c[1] == "BG_CalculateWeaponMovement"]
        assert len(mv) == len(tv), n
        for m, t in zip(mv, tv):
            # the same weaponState_t but its frametime and time (the presentation's) and its speed
            mb, tb = bytearray(m[3]), bytearray(t[3])
            for off in (0x4, 0xC):
                mb[off:off + 4] = tb[off:off + 4] = b"\0\0\0\0"
            assert mb == tb, n
            assert struct.unpack_from("<f", m[3], 0x4)[0] >= 0.0
            stepped += 1
    assert stepped > 60, stepped
