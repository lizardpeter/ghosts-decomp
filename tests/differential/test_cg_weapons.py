"""Differential cases for the viewmodel (cgame/cg_weapons.cpp: CG_AddViewWeapon), against the Store build.

Every callee is faked and logged with its arguments: the model functions, the gun conditions, the ADS test, the hip
integrator 14027B740, the bob conditions, BG_CalculateWeaponMovement (logged with the weaponState_t it gets, all but
the bob angles the original leaves uninitialised; it writes new values into every integrated field and the origin and
angles), 1402F51A0 (logged with the origin and angles; writes the placement) and 1402F30A0 (logged with the placement
and the gun flag). The inputs vary pm_type (the 5 and 6 early return), third person, the third-person test, the
cubemap shot, cg_drawGun, the two gun tests, eFlags 0x203800, the weapon (none; a variation with or without its model
and the fallback; a scope, an under-barrel and any of the seven other attachments, each model present or not; the
scope's extra model), the arms model, the ADS test and fWeaponPosFrac (0, 1, between, NaN: the hip integrator and the
ADS state), the shell shock parms (none: 3000), the damage time (0 or not), pm_flags 1, otherFlags 0x2000 and the bob
tests.
"""
import random
import struct

from harness import SCRATCH
from syms import va
from test_cg_view import _log, _logged, CURRENT, _rd
from win32_display import arg, log_value

STORE = "iw6mp64_MSStore_ship"
SYMBOL = "?CG_AddViewWeapon@@YAXW4LocalClientNum_t@@@Z"
WEAPDEF = SCRATCH + 0x10000
GUNMODELS = SCRATCH + 0x11000
MODELS38 = SCRATCH + 0x11400
COMPLETE = SCRATCH + 0x12000
SCOPES, UNDERBARRELS, OTHERS = SCRATCH + 0x12100, SCRATCH + 0x12200, SCRATCH + 0x12300
ATTS = SCRATCH + 0x13000
ATTMODELS = SCRATCH + 0x14000
PARMS = SCRATCH + 0x18000
DVAR = SCRATCH + 0x19000
STRINGS = SCRATCH + 0x1A000
CENT = 0x55550000
INDEX = 0x23


def _flt(mu):
    from unicorn.x86_const import UC_X86_REG_XMM1
    return mu.reg_read(UC_X86_REG_XMM1) & 0xFFFFFFFF


def _fakes(s):
    f = {}
    f["?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z"] = _logged("BG_GetViewmodelWeapon", "p",
                                                                               lambda mu: s["weapon"])
    f["?sub_14018DB60@@YAPEBDW4LocalClientNum_t@@PEBUclientInfo_t@@PEBUcharacterInfo_t@@HH@Z"] = _logged(
        "sub_14018DB60", "ippii", STRINGS)
    f["?R_RegisterModel@@YAPEAUXModel@@PEBD@Z"] = _logged("R_RegisterModel", "s", 0x66660000)
    f["?sub_14037AEA0@@YAXPEAUXModel@@@Z"] = _logged("sub_14037AEA0", "q")
    f["?sub_14037AEF0@@YAXPEBUXModel@@@Z"] = _logged("sub_14037AEF0", "q")
    f["?sub_14028F230@@YA_NTWeapon@@_N@Z"] = _logged("sub_14028F230", "ib", lambda mu: s["f230"])
    f["?sub_1402C59B0@@YAXXZ"] = _logged("sub_1402C59B0", "")
    f["?sub_1402F7640@@YAPEBUXModel@@TWeapon@@PEBUWeaponAttachment@@@Z"] = _logged("sub_1402F7640", "iq",
                                                                                   lambda mu: s["extra"])
    f["?BG_IsThirdPersonMode@@YA_NPEBUplayerState_s@@@Z"] = _logged("BG_IsThirdPersonMode", "p", lambda mu: s["tp"])
    f["?sub_1402AF8A0@@YA_NPEBUplayerState_s@@H@Z"] = _logged("sub_1402AF8A0", "p", lambda mu: s["af8a0"])
    f["?sub_14028F050@@YA_NPEBUplayerState_s@@@Z"] = _logged("sub_14028F050", "p", lambda mu: s["f050"])
    f["?BG_IsAimDownSight@@YA_NTWeapon@@_N@Z"] = _logged("BG_IsAimDownSight", "ib", lambda mu: s["ads"])

    def hip(mu):
        _log("call", "sub_14027B740", log_value(mu, "p", 0), _flt(mu), arg(mu, 2))
        mu.mem_write(arg(mu, 2), struct.pack("<f", s["hip"]))
    f["?sub_14027B740@@YAXPEBUplayerState_s@@MPEAM@Z"] = hip
    f["?sub_140300960@@YAHW4LocalClientNum_t@@PEBUplayerState_s@@H@Z"] = _logged("sub_140300960", "ipi",
                                                                                lambda mu: s["c0960"])
    f["?sub_140294C30@@YAHPEBUplayerState_s@@HH@Z"] = _logged("sub_140294C30", "pii", lambda mu: s["c4c30"])

    def movement(mu):
        ws, origin, angles, bob = arg(mu, 0), arg(mu, 1), arg(mu, 2), arg(mu, 3) & 0xFFFFFFFF
        data = _rd(mu, ws, 0x90)
        _log("call", "BG_CalculateWeaponMovement", struct.unpack("<Q", data[:8])[0], data[8:0x78], data[0x84:0x90], bob,
             len({ws, origin, angles}))
        new = bytearray(data)
        for off in range(0x10, 0x78, 4):
            if off in (0x14, 0x18):
                continue
            v = struct.unpack_from("<f", new, off)[0]
            struct.pack_into("<f", new, off, (v * 0.5 + off) if v == v else 1.5)
        mu.mem_write(ws, bytes(new))
        mu.mem_write(origin, struct.pack("<3f", 1.25, -2.5, 3.75))
        mu.mem_write(angles, struct.pack("<3f", 0.5, 7.0, -1.0))
    f["?BG_CalculateWeaponMovement@@YAXPEAUweaponState_t@@QEAM1H@Z"] = movement

    def place(mu):
        cg, p, angles = arg(mu, 0), arg(mu, 1), arg(mu, 2)
        _log("call", "sub_1402F51A0", cg, _rd(mu, p + 0x10, 12), _rd(mu, angles, 12))
        mu.mem_write(p, struct.pack("<4f", 0.1, 0.2, 0.3, 0.4))
        mu.mem_write(p + 0x1C, struct.pack("<f", 1.0))
    f["?sub_1402F51A0@@YAXPEAUcg_s@@PEAUGfxScaledPlacement@@PEAM@Z"] = place

    def scene(mu):
        _log("call", "sub_1402F30A0", arg(mu, 0) & 0xFFFFFFFF, _rd(mu, arg(mu, 1), 0x20), arg(mu, 2), arg(mu, 3),
             struct.unpack("<i", _rd(mu, mu.reg_read(__import__("unicorn").x86_const.UC_X86_REG_RSP) + 0x28, 4))[0])
    f["?sub_1402F30A0@@YAXW4LocalClientNum_t@@PEBUGfxScaledPlacement@@PEBUplayerState_s@@PEAUcentity_s@@H@Z"] = scene
    return f


def _f(r):
    return r.choice([0.0, 1.0, -2.5, r.uniform(-50, 50), float("nan")])


def _input(r):
    s = {}
    variation = r.choice([0, 0, 3, 63])
    scope = r.choice([0, 0, 1, 7])
    under = r.choice([0, 0, 1, 3])
    others = r.choice([0, 0, 1, 0x40, 0x55, 0x7F, 0x80])
    index = r.choice([0, INDEX, INDEX, INDEX])
    s["weapon"] = index | variation << 8 | scope << 14 | under << 17 | others << 19
    for k in ("f230", "tp", "af8a0", "f050", "ads", "c0960", "c4c30"):
        s[k] = r.choice([0, 1])
    s["tp"] = r.choice([0, 0, 0, 1])
    s["extra"] = r.choice([0, 0x77770000])
    s["hip"] = _f(r)
    gun_present = [r.choice([0, 0x71000000 + i]) for i in range(64)]
    m38 = [r.choice([0, 0x72000000 + i]) for i in range(64)]
    extras = (r.choice([0, 0x73000000]), r.choice([0, 0x73000008]))
    att_models = [[r.choice([0, 0x74000000 + 0x100 * a + i]) for i in range(64)] for a in range(16)]
    pm_type = r.choice([0, 0, 1, 2, 5, 6, 7, -1])
    third = r.choice([0, 0, 0, 1])
    cubemap = r.choice([0, 0, 0, 2])
    draw_gun = r.choice([1, 1, 1, 0])
    eflags = r.choice([0, 0, 0, 0x800, 0x200000, 0x1000, r.getrandbits(32)])
    frac = r.choice([0.0, 0.0, 1.0, 0.5, 0.2, 0.25, float("nan")])
    pm_flags = r.choice([0, 1, r.getrandbits(32)])
    other = r.choice([0, 0x2000, r.getrandbits(32)])
    weap_flags = r.choice([0, 0x4000, r.getrandbits(32)])
    viewmodel = r.choice([0, 0, 1, 2, -1])
    client = r.choice([0, 5, 17])
    time, base = r.getrandbits(31), r.getrandbits(31)
    damage = r.choice([0, 0, r.getrandbits(31)])
    frametime = r.choice([0, 1, 5, 16, -3, r.getrandbits(31)])
    parms = r.choice([0, PARMS])
    fade = r.getrandbits(16)
    floats = [_f(r) for _ in range(40)]
    ints = [r.getrandbits(32) for _ in range(8)]
    ads_state = r.getrandbits(32)

    def setup(w):
        CURRENT["m"] = w.m
        mu = w.m.mu
        cg = va("cgArray")
        ps = bytearray(0x640)
        struct.pack_into("<IiiII", ps, 0, 0, pm_type, 0, pm_flags, other)
        struct.pack_into("<I", ps, 0x124, eflags)
        struct.pack_into("<ii", ps, 0x17C, client, viewmodel)
        struct.pack_into("<IIf", ps, 0x41C, s["weapon"], weap_flags, frac)
        struct.pack_into("<f", ps, 0x634, floats[0])
        w.write(cg, bytes(ps))
        w.write(cg + 0x13CC, struct.pack("<i", base))
        w.write(cg + 0x3328, struct.pack("<Q", CENT))
        w.write(cg + 0x3330, struct.pack("<I7f", ads_state, *floats[1:8]))
        w.write(cg + 0x336C, struct.pack("<i", cubemap))
        w.write(cg + 0x7188C, struct.pack("<ii", frametime, time))
        w.write(cg + 0x718AC, struct.pack("<i", third))
        w.write(cg + 0x71944, struct.pack("<II", ints[0], ints[1]))
        w.write(cg + 0xA9A90, struct.pack("<3f", *floats[8:11]))
        w.write(cg + 0xA9AD8, struct.pack("<15f", *floats[11:26]))
        w.write(cg + 0xB5240, struct.pack("<i", damage))
        w.write(cg + 0xB525C, struct.pack("<3f", *floats[26:29]))
        w.write(cg + 0xB528C, struct.pack("<5f", *floats[29:34]))
        w.write(cg + 0xB5310, struct.pack("<QII", parms, ints[2], ints[3]))
        w.write(cg + 0x10E8C4, struct.pack("<f", floats[34]))
        mu.mem_write(PARMS + 0x14, struct.pack("<i", fade))
        mu.mem_write(DVAR + 0x10, bytes([draw_gun]))
        w.u64(va("cg_drawGun"), DVAR)
        mu.mem_write(STRINGS, b"viewhands_x\0")
        weapdef = bytearray(0x400)
        struct.pack_into("<Q", weapdef, 0x8, GUNMODELS)
        struct.pack_into("<Q", weapdef, 0x38, MODELS38)
        struct.pack_into("<QQ", weapdef, 0x358, *extras)
        mu.mem_write(WEAPDEF, bytes(weapdef))
        mu.mem_write(GUNMODELS, struct.pack("<64Q", *gun_present))
        mu.mem_write(MODELS38, struct.pack("<64Q", *m38))
        complete = bytearray(0x100)
        struct.pack_into("<QQQ", complete, 0x20, SCOPES, UNDERBARRELS, OTHERS)
        mu.mem_write(COMPLETE, bytes(complete))
        for a in range(16):
            att = bytearray(0x40)
            struct.pack_into("<Q", att, 0x28, ATTMODELS + 0x200 * a)
            mu.mem_write(ATTS + 0x100 * a, bytes(att))
            mu.mem_write(ATTMODELS + 0x200 * a, struct.pack("<64Q", *att_models[a]))
        mu.mem_write(SCOPES, struct.pack("<7Q", *(ATTS + 0x100 * a for a in range(7))))
        mu.mem_write(UNDERBARRELS, struct.pack("<3Q", *(ATTS + 0x100 * a for a in range(7, 10))))
        mu.mem_write(OTHERS, struct.pack("<7Q", *(ATTS + 0x100 * a for a in range(9, 16))))
        w.u64(va("bg_weaponDefs") + 8 * INDEX, WEAPDEF)
        w.u64(va("bg_weaponCompleteDefs") + 8 * INDEX, COMPLETE)

    return {"args": [0], "setup": setup, "fakes": _fakes(s)}


r = random.Random(4815)
CASES = [
    {"symbol": SYMBOL, "build": STORE, "ret": "void", "inputs": [_input(r) for _ in range(1200)]},
]
