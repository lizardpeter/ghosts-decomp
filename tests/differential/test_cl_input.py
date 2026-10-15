"""Differential cases for client_mp/cl_input.cpp's button code against the Store build.

Random button state (all 35 kbuttons of local client 0), frame_msec, com_frameTime, stance, and the profile's
gpadEnabled; reliable commands are faked and their arguments compared.
"""
import random
import struct

from syms import _names, static, va

STORE = "iw6mp64_MSStore_ship"
KB_SIZE, NUM_BUTTONS = 0x14, 35
SETTINGS = 0x500E00
CL_STANCE = 0x3548  # stanceHeld, stance


def _kbutton(r):
    keys = [r.choice([0, 0, 0, 5, 9, 200, -1, r.randint(0, 255)]) for _ in range(2)]
    downtime = r.choice([0, 0, 100, 5000, r.getrandbits(32)])
    msec = r.choice([0, 0, 3, 16, 33, 100, 40, r.getrandbits(32)])
    return struct.pack("<iiIIBBxx", *keys, downtime, msec, r.random() < 0.4, r.random() < 0.3)


def _state(r):
    kb = b"".join(_kbutton(r) for _ in range(NUM_BUTTONS))
    frame_msec = r.choice([0, 1, 16, 16, 33, 100])
    frame_time = r.choice([0, 100, 5000, 100000, r.getrandbits(31)])
    stance = (r.choice([0, 1]), r.choice([0, 1, 2]))
    gpad = r.random() < 0.3

    def setup(w):
        w.write(static("client_mp/cl_input.cpp", "playersKb"), kb)
        w.u32(va("frame_msec"), frame_msec)
        w.u32(va("com_frameTime"), frame_time)
        w.write(va("clients") + CL_STANCE, struct.pack("<Bxxxi", *stance))
        w.m.mu.mem_write(SETTINGS + 0x2BC, bytes([gpad]))
    return setup


FAKES = {
    "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": lambda mu: SETTINGS,
    "?sub_140311D60@@YAXW4LocalClientNum_t@@HH@Z": lambda mu: None,
}
OBSERVE = {"?sub_140311D60@@YAXW4LocalClientNum_t@@HH@Z": "iii",
           "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": "i"}


def _kb_ptr(r):
    """A pointer to one of local client 0's kbuttons (fills in the address at run time)."""
    return _names(STORE)["playersKb"] + KB_SIZE * r.randint(0, NUM_BUTTONS - 1)


def case(symbol, seed, args, n=400, ret="void"):
    rnd = random.Random(seed)
    inputs = [{"args": args(rnd), "setup": _state(rnd), "fakes": FAKES} for _ in range(n)]
    return {"symbol": symbol, "build": STORE, "ret": ret, "observe": OBSERVE, "inputs": inputs}


def _key(r):
    return r.choice([0, 5, 9, 200, -1, r.randint(0, 255)])


def _time(r):
    return r.choice([0, 0, 100, 4000, r.getrandbits(32)])


CASES = [
    case("?CL_IsGamepadEnabled@@YA_NW4LocalClientNum_t@@@Z", 109, lambda r: [0], 60, "char"),
    case("?IN_KeyDown@@YAXPEAUkbutton_t@@HI@Z", 172, lambda r: [_kb_ptr(r), _key(r), _time(r)]),
    case("?IN_KeyUp@@YAXPEAUkbutton_t@@HI@Z", 227, lambda r: [_kb_ptr(r), _key(r), _time(r)]),
    case("?CL_KeyState@@YAMPEAUkbutton_t@@@Z", 289, lambda r: [_kb_ptr(r)], 800, "float"),
    case("?CL_SetStance@@YAXW4LocalClientNum_t@@W4StanceState@@@Z", 332, lambda r: [0, r.choice([0, 1, 2])]),
    case("?CL_UseReload@@YAXW4LocalClientNum_t@@H@Z", 469, lambda r: [0, _key(r)]),
    case("?CL_SpecPrev@@YAXW4LocalClientNum_t@@H@Z", 482, lambda r: [0, _key(r)]),
    case("?CL_SpecNext@@YAXW4LocalClientNum_t@@H@Z", 489, lambda r: [0, _key(r)]),
    case("?CL_ToggleSpec@@YAXW4LocalClientNum_t@@H@Z", 496, lambda r: [0, _key(r)]),
    case("?IN_IsTalkKeyHeld@@YA_NXZ", 1374, lambda r: [], 60, "char"),
    case("?CL_KeyActiveOrPressed@@YA_NW4LocalClientNum_t@@H@Z", 2281, lambda r: [0, r.randint(0, NUM_BUTTONS - 1)],
         ret="char"),
    case("?CL_UpdateCmdButton@@YAXW4LocalClientNum_t@@PEAIHI@Z", 2293,
         lambda r: [0, struct.pack("<I", r.getrandbits(32)), r.randint(0, NUM_BUTTONS - 1), 1 << r.randint(0, 31)]),
    case("?CL_ClearKeys@@YAXW4LocalClientNum_t@@@Z", 3491, lambda r: [0], 40),
]
