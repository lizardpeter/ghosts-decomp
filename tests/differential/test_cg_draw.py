"""Differential cases for CG_DrawActive (cgame_mp/cg_draw_mp.cpp) and the client setters it calls
(client_mp/cl_cgame_mp.cpp), against the Store build.

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
CASES = [
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
