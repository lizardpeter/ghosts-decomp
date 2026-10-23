"""Differential cases for bgame/bg_jump.cpp (the Store build, and the PS4 server where its code is the same).

Every case passes the playerState_s as a buffer of its own (a trailing argument the function doesn't take, so the
harness compares it), with pmove_t.ps pointing at it. Random state: pm_flags (the jump, ladder, mantle and refusal
bits), pm_type, pm_time around the slowdown thresholds (0, 1200, 1699/1700, 1800/1801), gravity (800, 0, negative,
huge), origin and jumpOriginZ around the jump height and step size (exact ties too), velocity, the ladder vector,
jumpTime against cmd.serverTime around 500 ms, the aim spread near 255, the buttons and oldcmd buttons, the forward
move's sign, the ground trace's hit entity and the view direction. NaN and infinities appear in the floats.

The engine around them is faked and logged with its arguments: the omnvar lookup ("alt_jump_height" absent, or
present with a value that is 0, 39, 50, negative or NaN, through G_Omnvar_GetData or the cgame's copy by
pm->handler), PM_GetEffectiveStance, BG_GetEntityState (an entity of type 12, 14 or another), PM_GroundSurfaceType,
BG_PackFootstepEventParm, BG_AddPredictableEventToPlayerstate, BG_AnimUpdatePlayerStateConditions and
BG_AnimScriptEvent. Vec3Normalize runs for real.

The PS4 server has Jump_Start and Jump_PushOffLadder as functions of their own, and normalizes the ladder push
direction by hand: its Jump_Check cases leave the ladder flag clear. Its Jump_GetJumpHeight returns 39 for the cgame's
movement (pm->handler 0), having no cgame omnvars: its cases use handler 1.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_XMM0

import syms
from harness import HEAP, _page
from win32_display import CURRENT, log_value

STORE = "iw6mp64_MSStore_ship"
PS4 = "iw6_ds_ps4"
PM_SIZE, PML_SIZE, PS_SIZE = 0x178, 0xA4, 0x620
OMNVAR_DATA, ENTITY = 0x5E0000, 0x5E1000  # scratch


def _f(r, *common):
    return r.choice([*common, float("nan"), float("inf"), -float("inf"), r.uniform(-500, 500)])


def _log(name, sig, result=None):
    def run(mu):
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", name, *(log_value(mu, c, i) for i, c in enumerate(sig))))
        return result(mu) if callable(result) else result
    return run


def _ret_float(name, value, sig=""):
    def run(mu):
        _log(name, sig)(mu)
        mu.reg_write(UC_X86_REG_XMM0, struct.unpack("<I", struct.pack("<f", value))[0])
        return None
    return run


SYM = {
    "index": "?Omnvar_GetIndexByName@@YAIPEBD@Z",
    "def": "?Omnvar_GetDef@@YAPEBUOmnvarDef@@I@Z",
    "gdata": "?G_Omnvar_GetData@@YAPEAUOmnvarData@@IHQEAUplayerState_s@@@Z",
    "cgdata": "?sub_140543040@@YAPEAUOmnvarData@@W4LocalClientNum_t@@I@Z",
    "stance": "?PM_GetEffectiveStance@@YA?AW4EffectiveStance@@PEBUplayerState_s@@@Z",
    "entity": "?BG_GetEntityState@@YAPEBUentityState_s@@EH@Z",
    "surface": "?PM_GroundSurfaceType@@YAIPEAUpml_t@@@Z",
    "pack": "?BG_PackFootstepEventParm@@YAHPEBUplayerState_s@@H@Z",
    "event": "?BG_AddPredictableEventToPlayerstate@@YAXHHPEAUplayerState_s@@@Z",
    "conditions": "?BG_AnimUpdatePlayerStateConditions@@YAXPEAUpmove_t@@@Z",
    "anim": "?BG_AnimScriptEvent@@YAHPEAUplayerState_s@@W4scriptAnimEventTypes_t@@HHPEAI@Z",
    "height": "?Jump_GetJumpHeight@@YAMPEAUpmove_t@@@Z",
}


class World:
    """The faked engine for one input: the omnvar, the stance, the ground entity, the surface type."""

    def __init__(self, r):
        self.index = r.choice([0xFFFFFFFF, 0xFFFFFFFF, 5, 0x30])
        self.data = r.choice([0, 1, 1, 1])
        self.value = r.choice([0.0, 39.0, 50.0, -10.0, 12.5, 39.37, 3e38, float("nan")])
        self.stance = r.choice([0, 0, 0, 0, 1, 2, 3])
        self.etype = r.choice([1, 12, 14, 13, 0])
        self.surface = r.choice([0, 0, 1, 7, 29])
        self.parm = r.getrandbits(16)

    def setup(self, w):
        CURRENT["m"] = w.m
        w.m.mu.mem_write(OMNVAR_DATA, struct.pack("<If", 0x1234, self.value))
        w.m.mu.mem_write(ENTITY, struct.pack("<ii", 77, self.etype))

    def fakes(self):
        data = OMNVAR_DATA if self.data else 0
        return {
            SYM["index"]: _log("Omnvar_GetIndexByName", "s", self.index),
            SYM["def"]: _log("Omnvar_GetDef", "i", 0x5E2000),
            SYM["gdata"]: _log("G_Omnvar_GetData", "iiq", data),
            **({SYM["cgdata"]: _log("CG_Omnvar_GetData", "ii", data)} if syms.BUILD == STORE else {}),
            SYM["stance"]: _log("PM_GetEffectiveStance", "q", self.stance),
            SYM["entity"]: _log("BG_GetEntityState", "bi", ENTITY),
            SYM["surface"]: _log("PM_GroundSurfaceType", "q", self.surface),
            SYM["pack"]: _log("BG_PackFootstepEventParm", "qi", self.parm),
            SYM["event"]: _log("BG_AddPredictableEventToPlayerstate", "iiq"),
            SYM["conditions"]: _log("BG_AnimUpdatePlayerStateConditions", "q"),
            SYM["anim"]: _log("BG_AnimScriptEvent", "qiiiq", 0),
        }


def _ps(r, ladder=True):
    ps = bytearray(PS_SIZE)
    flags = r.choice([0, 0, 0x2000, 0x2000, 0x8, 0x2008, 0x4, 0x400, 0x40000, 0x180, 0x2180, r.getrandbits(32)])
    if not ladder:
        flags &= ~0x8
    struct.pack_into("<iiiI", ps, 0, r.choice([0, 1000, r.getrandbits(31)]), r.choice([0, 0, 1, 6, 7, 8, -1]),
                     r.choice([0, 0, 1, 1199, 1200, 1699, 1700, 1800, 1801, 5000, -3]), flags)
    z = _f(r, 0.0, 10.0, 38.9, 39.0, 39.1, 57.0, 100.0)
    struct.pack_into("<3f", ps, 0x1C, _f(r, 0.0), _f(r, 0.0), z)
    struct.pack_into("<3f", ps, 0x28, _f(r, 0.0, 190.0), _f(r, 0.0, -190.0), _f(r, 0.0, 250.0, -100.0, 1e30))
    struct.pack_into("<i", ps, 0x5C, r.choice([800, 800, 0, -800, 100000, 1]))
    struct.pack_into("<i", ps, 0x70, r.choice([0x7FE, 0x7FF, 3]))
    struct.pack_into("<3f", ps, 0x74, *r.choice([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0),
                                                 (0.6, 0.8, 0.0), (r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))]))
    struct.pack_into("<i", ps, 0x80, r.choice([0, 500, 1000, r.getrandbits(31)]))
    struct.pack_into("<f", ps, 0x84, r.choice([0.0, 0.0, z, z - 18.0, z - 39.0, z - 20.9, z + 1.0, r.uniform(-50, 50)]))
    struct.pack_into("<i", ps, 0x240, r.choice([0, 1]))
    struct.pack_into("<f", ps, 0x428, r.choice([0.0, 100.0, 191.0, 200.0, 255.0, float("nan")]))
    return ps


def _pm(r, ps_va, ps):
    pm = bytearray(PM_SIZE)
    struct.pack_into("<Q", pm, 0, ps_va)
    jump_time = struct.unpack_from("<i", ps, 0x80)[0]
    struct.pack_into("<I", pm, 8, r.choice([jump_time + 499, jump_time + 500, jump_time + 2000, r.getrandbits(31)])
                     & 0xFFFFFFFF)
    struct.pack_into("<I", pm, 0xC, r.choice([0x400, 0x400, 0x400, 0, 0x401, r.getrandbits(32)]))
    struct.pack_into("<b", pm, 0x24, r.choice([0, 127, -127, -1, 64]))
    struct.pack_into("<I", pm, 0x48, r.choice([0, 0, 0, 0x400, r.getrandbits(32)]))
    pm[0x174] = r.choice([0, 1, 1]) if syms.BUILD == STORE else 1  # the PS4 server has no cgame omnvars: 39
    return pm


def _pml(r):
    pml = bytearray(r.getrandbits(8) for _ in range(PML_SIZE))
    struct.pack_into("<3f", pml, 0, *r.choice([(1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.6, -0.8, 0.0),
                                               (r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))]))
    struct.pack_into("<H", pml, 0x54, r.choice([0x7FF, 0x7FF, 0x7FE, 5]))
    return pml


def _check_input(r, ladder):
    world = World(r)
    ps = _ps(r, ladder)
    ps_va = HEAP + _page(PM_SIZE + 16) + _page(PML_SIZE + 16)
    pm = _pm(r, ps_va, ps)
    return {"args": [bytes(pm), bytes(_pml(r)), bytes(ps)], "setup": world.setup, "fakes": world.fakes()}


def _pm_ps_input(r, extra=None):
    """(pm, ps[, extra]) with pm.ps at the second buffer."""
    world = World(r)
    ps = _ps(r)
    pm = _pm(r, HEAP + _page(PM_SIZE + 16), ps)
    args = [bytes(pm), bytes(ps)]
    if extra is not None:
        args.append(extra)
    return {"args": args, "setup": world.setup, "fakes": world.fakes()}


def _origin(r, ps):
    z = struct.unpack_from("<f", ps, 0x24)[0]
    jz = struct.unpack_from("<f", ps, 0x84)[0]
    return struct.pack("<3f", 0.0, 0.0, r.choice([z, z - 1.0, z + 1.0, jz + 21.0, jz + 20.0, jz + 39.0, 0.0,
                                                   float("nan"), r.uniform(-50, 80)]))


def _clamp_input(r):
    inp = _pm_ps_input(r)
    inp["args"].append(_origin(r, inp["args"][1]))
    return inp


def _step_input(r):
    inp = _pm_ps_input(r)
    inp["args"] += [_origin(r, inp["args"][1]), struct.pack("<f", r.choice([0.0, 18.0, -1.0]))]
    return inp


def _ps_only(r):
    return {"args": [bytes(_ps(r))]}


def _height_input(r):
    world = World(r)
    pm = bytearray(PM_SIZE)
    pm[0x174] = r.choice([0, 1]) if syms.BUILD == STORE else 1
    return {"args": [r.choice([bytes(pm), bytes(pm), 0])], "setup": world.setup, "fakes": world.fakes()}


OBSERVE = {SYM["height"]: "q"}


def _cases(symbol, ret, make, n, seed, build=None):
    r = random.Random(seed)
    case = {"symbol": symbol, "ret": ret, "inputs": [make(r) for _ in range(n)]}
    if build:
        case["build"] = build
    return case


CASES = [
    _cases("?Jump_GetJumpHeight@@YAMPEAUpmove_t@@@Z", "float", _height_input, 400, 114),
    _cases("?Jump_ClearState@@YAXPEAUplayerState_s@@@Z", "void", _ps_only, 200, 161),
    _cases("?Jump_GetStepHeight@@YA_NPEAUpmove_t@@PEAUplayerState_s@@QEBMPEAM@Z", "char", _step_input, 1500, 171),
    _cases("?Jump_IsPlayerAboveMax@@YA_NPEAUpmove_t@@PEAUplayerState_s@@@Z", "char", _pm_ps_input, 800, 196),
    _cases("?Jump_ActivateSlowdown@@YAXPEAUplayerState_s@@@Z", "void", _ps_only, 300, 207),
    _cases("?Jump_ApplySlowdown@@YAXPEAUplayerState_s@@@Z", "void", _ps_only, 800, 220),
    _cases("?Jump_ReduceFriction@@YAMPEAUplayerState_s@@@Z", "float", _ps_only, 800, 273),
    _cases("?Jump_ClampVelocity@@YAXPEAUpmove_t@@PEAUplayerState_s@@QEBM@Z", "void", _clamp_input, 1500, 296),
    _cases("?Jump_Check@@YA_NPEAUpmove_t@@PEAUpml_t@@@Z", "char", lambda r: _check_input(r, True), 3000, 445, STORE),
    _cases("?Jump_Check@@YA_NPEAUpmove_t@@PEAUpml_t@@@Z", "char", lambda r: _check_input(r, False), 1500, 445, PS4),
    _cases("?Jump_RegisterDvars@@YAXXZ", "void", lambda r: [], 20, 0),
]
