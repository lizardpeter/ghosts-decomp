"""Differential cases for cgame/cg_camera.cpp (and its com_math helper) against the Store build.

Random FOVs (the cg_fov range, ADS and vehicle FOVs, the 170 clamp, extremes past 180 and negative ones), random
window aspect ratios and viewMult in cgs, a random cg_fovScale as a scratch dvar_t, and random refdef tangents.

CG_GetViewFov: random predicted player state (pm_type, link/other/entity flags, weapon flags), cg_s FOV state
(remote missile camera, scripted FOV, hybrid scope state and fraction), the FOV dvars, and fakes for every engine
callee (weapon, ADS and camera FOVs, zoom fraction, the yes/no tests with garbage above the returned byte), whose
arguments are compared."""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R9, UC_X86_REG_XMM0

from syms import va

STORE = "iw6mp64_MSStore_ship"
ASPECTS = (4 / 3, 16 / 10, 16 / 9, 21 / 9, 32 / 9, 5 / 4, 1.0, 0.5)


def _fov(r):
    return r.choice([65.0, 80.0, 90.0, 55.0, 30.0, 170.0, 1.0, 0.0, 180.0, 200.0, -65.0,
                     r.uniform(1, 170), r.uniform(-400, 400)])


def _setup(r):
    aspect = r.choice(ASPECTS + (r.uniform(0, 5),))
    mult = r.choice([1.0, 1.0, 0.5, 2.0, r.uniform(-2, 2)])
    tan_y = r.choice([0.4778, 0.75, r.uniform(-3, 3)])
    scale = r.choice([1.0, 1.0, 0.2, 2.0, 0.0, r.uniform(-2, 2)])

    def setup(w):
        w.write(va("cgsArray") + 0x10, struct.pack("<ff", aspect, mult))
        w.write(va("cgArray") + 0x718DC, struct.pack("<f", tan_y))
        d = w.alloc(bytes(0x60))
        w.write(d + 0x10, struct.pack("<f", scale))
        w.u64(va("cg_fovScale"), d)
    return setup


def inputs(seed, args, n):
    r = random.Random(seed)
    return [{"args": args(r), "setup": _setup(r)} for _ in range(n)]


CASES = [
    {"symbol": "?CG_CalcFov@@YAXW4LocalClientNum_t@@M@Z", "build": STORE, "ret": "void",
     "inputs": inputs(912, lambda r: [0, ("f", _fov(r))], 600)},
    {"symbol": "?sub_1402E9060@@YAMXZ", "build": STORE, "ret": "float", "inputs": inputs(913, lambda r: [], 300)},
    {"symbol": "?sub_140532D80@@YAXMMPEAM0@Z", "build": STORE, "ret": "void",
     "inputs": inputs(914, lambda r: [("f", _fov(r)), ("f", r.choice(ASPECTS + (r.uniform(-5, 5),))),
                                      bytes(4), bytes(4)], 600)},
]


def _fbits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _rf(value):
    def run(mu):
        mu.reg_write(UC_X86_REG_XMM0, _fbits(value))
    return run


def _rb(value):
    return lambda mu: 0xA5C300 | value  # only the low byte is the bool


FOV_FAKES = {
    "weapon": "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z",
    "ads": "?BG_ADSZoomFov@@YAMPEBUplayerState_s@@TWeapon@@_N@Z",
    "hybrid": "?BG_CanHybridToggle@@YA_NPEBUplayerState_s@@TWeapon@@_N@Z",
    "third": "?BG_IsThirdPersonMode@@YA_NPEBUplayerState_s@@@Z",
    "zoom": "?CG_GetWeaponZoom@@YAMPEBUcg_s@@TWeapon@@@Z",
    "hybridFov": "?sub_140288830@@YAMPEBUplayerState_s@@TWeapon@@_N2@Z",
    "held": "?sub_140294880@@YA_NPEBUplayerState_s@@@Z",
    "zooms": "?BG_IsAimDownSight@@YA_NTWeapon@@_N@Z",
    "varZoom": "?sub_1402869E0@@YAMPEBUplayerState_s@@TWeapon@@@Z",
    "camera": "?sub_1405B7A60@@YA_NW4LocalClientNum_t@@@Z",
    "cameraFov": "?sub_1405B6C50@@YAMW4LocalClientNum_t@@@Z",
    "offset": "?sub_1405B7890@@YA_NW4LocalClientNum_t@@@Z",
    "offsetFov": "?sub_1405B7B10@@YAMPEBUcg_s@@M@Z",
    "adjust": "?sub_140187D70@@YAHW4LocalClientNum_t@@@Z",
    "adjustFov": "?sub_140187060@@YAMW4LocalClientNum_t@@M@Z",
}
FOV_OBSERVE = {
    FOV_FAKES["weapon"]: "q", FOV_FAKES["ads"]: "qib", FOV_FAKES["hybrid"]: "qib", FOV_FAKES["third"]: "q",
    FOV_FAKES["zoom"]: "qi", FOV_FAKES["hybridFov"]: "qibb", FOV_FAKES["held"]: "q", FOV_FAKES["zooms"]: "ib",
    FOV_FAKES["varZoom"]: "qi", FOV_FAKES["camera"]: "i", FOV_FAKES["cameraFov"]: "i", FOV_FAKES["offset"]: "i",
    FOV_FAKES["offsetFov"]: "qf", FOV_FAKES["adjust"]: "i", FOV_FAKES["adjustFov"]: "if",
}


def _view_fov(r):
    def fov():
        return r.choice([65.0, 80.0, 50.0, 30.0, 15.0, 8.0, 0.0, 170.0, 200.0, r.uniform(-10, 200)])

    first, second = fov(), fov()

    def hybrid_fov(mu):
        mu.reg_write(UC_X86_REG_XMM0, _fbits(second if mu.reg_read(UC_X86_REG_R9) & 0xFF else first))

    weapon = r.choice([0, 0x11, 0x2300, 0x4507, r.getrandbits(32)])
    fakes = {
        FOV_FAKES["weapon"]: lambda mu: weapon,
        FOV_FAKES["ads"]: _rf(fov()),
        FOV_FAKES["hybrid"]: _rb(r.choice([0, 1, 1])),
        FOV_FAKES["third"]: _rb(r.choice([0, 0, 1])),
        FOV_FAKES["zoom"]: _rf(r.choice([0.0, 1.0, 0.5, r.random(), r.uniform(-1, 2)])),
        FOV_FAKES["hybridFov"]: hybrid_fov,
        FOV_FAKES["held"]: _rb(r.choice([0, 0, 1])),
        FOV_FAKES["zooms"]: _rb(r.choice([0, 1, 1])),
        FOV_FAKES["varZoom"]: _rf(r.choice([0.0, 0.0, 25.0, 15.0, 8.0, -5.0])),
        FOV_FAKES["camera"]: _rb(r.choice([0, 0, 0, 1])),
        FOV_FAKES["cameraFov"]: _rf(fov()),
        FOV_FAKES["offset"]: _rb(r.choice([0, 0, 1])),
        FOV_FAKES["offsetFov"]: _rf(fov()),
        FOV_FAKES["adjust"]: lambda mu, v=r.choice([0, 0, 1, 0x100]): v,
        FOV_FAKES["adjustFov"]: _rf(fov()),
    }
    rare = lambda p, v, other=0: v if r.random() < p else other  # noqa: E731
    pm_type = r.choice([0, 0, 0, 6, 5])
    other_flags = rare(0.1, 0x200000) | (r.getrandbits(32) & ~0x200000 if r.random() < 0.3 else 0)
    link_flags = rare(0.15, 4) | rare(0.2, 0x3)
    e_flags = rare(0.1, r.choice([0x800, 0x1000, 0x2000])) | rare(0.2, 0x4400)
    weap_flags = r.choice([0, 0x4000, r.getrandbits(32)])
    missile = r.random() < 0.1
    scripted = fov()
    state = r.choice([0, 1, 2, 3, 4, 5, 6, 0xFFFFFFFF, 4, 5])
    frac = r.choice([0.0, 1.0, 0.25, r.random()])
    dvars = {"cg_fov": r.choice([65.0, 80.0, r.uniform(65, 80)]), "cg_fovScale": r.choice([1.0, 1.0, 0.2, 2.0]),
             "cg_fovMin": r.choice([1.0, 1.0, 40.0, 160.0]), "missileRemoteFOV": r.choice([15.0, 120.0])}
    no_zoom, held_in = r.choice([0, 0, 0, 1, 0x100]), r.choice([0, 0, 1])

    def setup(w):
        cg = va("cgArray")
        w.write(cg + 4, struct.pack("<i", pm_type))
        w.write(cg + 0x10, struct.pack("<II", other_flags & 0xFFFFFFFF, link_flags))
        w.u32(cg + 0x124, e_flags)
        w.u32(cg + 0x420, weap_flags)
        w.write(cg + 0xB4EF8, struct.pack("<If", state, frac))
        w.write(cg + 0x10E79F, bytes([missile]))
        w.write(cg + 0x10EDC4, struct.pack("<f", scripted))
        w.u32(va("unk_143D33E80"), no_zoom)
        w.write(va("unk_143D33E84"), bytes([held_in]))
        for name, value in dvars.items():
            d = w.alloc(bytes(0x60))
            w.write(d + 0x10, struct.pack("<f", value))
            w.u64(va(name), d)
    return {"args": [0], "setup": setup, "fakes": fakes}


CASES.append({"symbol": "?CG_GetViewFov@@YAMW4LocalClientNum_t@@@Z", "build": STORE, "ret": "float",
              "observe": FOV_OBSERVE, "inputs": [_view_fov(r) for r in [random.Random(1162)] for _ in range(3000)]})
