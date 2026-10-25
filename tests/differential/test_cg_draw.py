"""Differential cases for CG_DrawActive and sub_1402AA2A0 (cgame_mp/cg_draw_mp.cpp) and the client setters
CG_DrawActive calls (client_mp/cl_cgame_mp.cpp), against the Store build.

sub_1402AA2A0 (the ramp): cls.frametime (0, 1, 16, 300, negative), the ramp (-1..1, past the ends, 0, NaN), both
flags, pm_flags 1 and 0x10, 14031FED0's answer (faked), the ADS-in time BG_GetADSTransTimes writes (faked: 0.2,
0, NaN).

CG_DrawActive: random zoom sensitivity and shellshock sensitivity (0, NaN, negative), kick and ADS offset angles (NaN
payloads too, so the order of the additions is visible), the selected weapon, offhand and alternate value, the extra
buttons, the client's extra buttons before. The setters run for real; sub_1402891D0 (empty) and CL_RenderScene are
faked and logged with their arguments (the refdef pointer as the address it is).
"""
import random
import struct

from syms import va
from win32_display import CURRENT, log_value

STORE = "iw6mp64_MSStore_ship"
CL_WEAPON, CL_FOVSCALE, CL_KICK, CL_EXTRA = 0x355C, 0x3568, 0x3574, 0x3608
CG_ZOOM, CG_WEAPSEL, CG_OFFHAND, CG_KICK, CG_OFFSET, CG_SHELLSHOCK, CG_EXTRA = (
    0xB1B18, 0xB2768, 0xB4F0C, 0xB5274, 0xB5280, 0xB5320, 0x10E82C)


def _log(name, sig):
    def run(mu):
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", name, *(log_value(mu, c, i) for i, c in enumerate(sig))))
        return None
    return run


def _bits(r):
    return r.choice([0x7FC00001, 0xFFC00002, 0x7F800000, struct.unpack("<I", struct.pack("<f", r.uniform(-20, 20)))[0],
                     0, 0x80000000, struct.unpack("<I", struct.pack("<f", r.uniform(-1, 1)))[0]])


def _draw_input(r):
    zoom = struct.pack("<f", r.choice([1.0, 0.5, 0.0, float("nan"), r.uniform(0, 2)]))
    shell = struct.pack("<f", r.choice([0.0, 0.0, 0.5, -1.0, float("nan"), r.uniform(0, 2)]))
    angles = struct.pack("<6I", *(_bits(r) for _ in range(6)))
    weapons = struct.pack("<III", r.getrandbits(32), r.getrandbits(32), r.choice([0, 0, 1, -1 & 0xFFFFFFFF]))
    extra, cl_extra = r.getrandbits(32), r.getrandbits(32)

    def setup(w):
        CURRENT["m"] = w.m
        cg, cl = va("cgArray"), va("clients")
        w.write(cg + CG_ZOOM, zoom)
        w.write(cg + CG_SHELLSHOCK, shell)
        w.write(cg + CG_KICK, angles[:12])
        w.write(cg + CG_OFFSET, angles[12:])
        w.write(cg + CG_WEAPSEL, weapons[:4])
        w.write(cg + CG_WEAPSEL + 4, weapons[8:])
        w.write(cg + CG_OFFHAND, weapons[4:8])
        w.u32(cg + CG_EXTRA, extra)
        w.u32(cl + CL_EXTRA, cl_extra)
    fakes = {"?sub_1402891D0@@YAXI@Z": _log("sub_1402891D0", "i"),
             "?CL_RenderScene@@YAXW4LocalClientNum_t@@PEBXH@Z": _log("CL_RenderScene", "iqi")}
    return {"args": [0, r.choice([0, 1, 2, r.getrandbits(31)])], "setup": setup, "fakes": fakes}


def _client_input(r, args):
    junk = bytes(r.getrandbits(8) for _ in range(0xB0))

    def setup(w):
        w.write(va("clients") + 0x355C, junk)
    return {"args": args, "setup": setup, "fakes": {"?sub_1402891D0@@YAXI@Z": _log("sub_1402891D0", "i")}}


r = random.Random(1805)
def _ramp_input(r, near=False):
    frametime = r.choice([0, 1, 5, 16, 300, -7, 7, 13, 33, r.getrandbits(16)])
    ramp = r.choice([0.0, 1.0, -1.0, 0.5, -0.3, 1.5, -2.0, 0.001, float("nan"), 0.9995, -0.9995])
    up, down = r.choice([0, 1]), r.choice([0, 1])
    flags = r.choice([0, 1, 0x10, 0x11, r.getrandbits(32)])
    enabled = r.choice([0, 1, 1])
    if near:   # just below the limits, standing still: the clamps' exact bounds
        frametime, ramp, flags, enabled = r.choice([0, -1]), r.choice([0.9995, -0.9995, 0.99999]), 0, 1
    ads_in = r.choice([0.2, 0.35, 0.0, float("nan"), 0.3, 0.7, 0.123, 0.45])

    def setup(w):
        CURRENT["m"] = w.m
        cg = va("cgArray")
        w.write(va("cls") + 0x118, struct.pack("<i", frametime))
        w.write(cg + 0xC, struct.pack("<I", flags))
        w.write(cg + 0x41C, struct.pack("<II", 0x11, r2))
        w.write(cg + 0x10F823, bytes([down, up]))
        w.write(cg + 0x10F828, struct.pack("<f", ramp))

    r2 = r.choice([0, 0x4000])

    def times(mu):
        from win32_display import arg
        from unicorn.x86_const import UC_X86_REG_RSP
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", "BG_GetADSTransTimes", log_value(mu, "p", 0), arg(mu, 1) & 0xFFFFFFFF,
                               arg(mu, 2) & 0xFF))
        out = struct.unpack("<Q", bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RSP) + 0x28, 8)))[0]
        mu.mem_write(arg(mu, 3), struct.pack("<f", ads_in))
        mu.mem_write(out, struct.pack("<f", 0.1))
        return None
    fakes = {"?sub_14031FED0@@YA_NH@Z": lambda mu: enabled,
             "?CL_ControllerIndexFromClientNum@@YAHW4LocalClientNum_t@@@Z": lambda mu: 0,
             "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z": lambda mu: 0x11,
             "?BG_GetADSTransTimes@@YAXPEBUplayerState_s@@TWeapon@@_NPEAM3@Z": times}
    return {"args": [0], "setup": setup, "fakes": fakes}


CASES = [
    {"symbol": "?sub_1402AA2A0@@YAXW4LocalClientNum_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [_ramp_input(r) for _ in range(800)] + [_ramp_input(r, near=True) for _ in range(40)]},
    {"symbol": "?CG_DrawActive@@YAXW4LocalClientNum_t@@H@Z", "build": STORE, "ret": "void",
     "inputs": [_draw_input(r) for _ in range(600)]},
    {"symbol": "?CL_SetFOVSensitivityScale@@YAXW4LocalClientNum_t@@M@Z", "build": STORE, "ret": "void",
     "inputs": [_client_input(r, [0, ("f", r.uniform(-2, 2))]) for _ in range(50)]},
    {"symbol": "?CL_SetUserCmdAimValues@@YAXW4LocalClientNum_t@@PEBM@Z", "build": STORE, "ret": "void",
     "inputs": [_client_input(r, [0, bytes(r.getrandbits(8) for _ in range(12))]) for _ in range(50)]},
    {"symbol": "?CL_SetUserCmdWeapons@@YAXW4LocalClientNum_t@@IIH@Z", "build": STORE, "ret": "void",
     "inputs": [_client_input(r, [0, r.getrandbits(32), r.getrandbits(32), r.choice([0, 1, -1, r.getrandbits(31)])])
                for _ in range(100)]},
    {"symbol": "?CL_SetExtraButtons@@YAXW4LocalClientNum_t@@H@Z", "build": STORE, "ret": "void",
     "inputs": [_client_input(r, [0, r.getrandbits(31)]) for _ in range(50)]},
]
