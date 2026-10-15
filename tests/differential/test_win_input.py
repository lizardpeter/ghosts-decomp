"""Differential cases for win32/win_input.cpp against the Store build (the servers have no mouse code).

Every input sets up random mouse state (s_wmv, window centre, in_appactive, in_mouse, r_displayMode, the window
and cursor in the Win32 model, video and monitor size, connection state) and compares globals, Win32 calls and
calls into the rest of the engine. CL_MouseEvent, IN_GamepadsMove and the gamepad/dvar helpers are faked
(their own behaviour is not this file's), and their arguments are compared.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX

from syms import va
from win32 import HWND_GAME, Win32

STORE = "iw6mp64_MSStore_ship"
RESET = -100000


def _state(r):
    init, active = r.random() < 0.85, r.random() < 0.5
    old_buttons = r.randint(0, 31)
    old_pos = (RESET, r.randint(-50, 2000)) if r.random() < 0.3 else (r.randint(-50, 2000), r.randint(-50, 1200))
    center = (r.randint(0, 2000), r.randint(0, 1200))
    appactive = r.choice([0, 1, 1, 1])
    in_mouse = r.random() < 0.85
    display_mode = r.choice([0, 0, 1, 2])
    connstate = r.choice([0, 1, 5, 9, 10, 10, 10])
    hwnd = r.choice([HWND_GAME] * 4 + [0])
    sys_time = r.getrandbits(32)
    display = (r.choice([1920, 1280, 2560, 800]), r.choice([1080, 720, 1440, 600]))
    monitor = (r.choice([1920, 2560, 3840, 1280]), r.choice([1080, 1440, 2160, 720]))
    left, top = r.randint(-100, 300), r.randint(-100, 200)
    window = (left, top, left + r.choice([800, 1280, 1920]), top + r.choice([600, 720, 1080]))
    cursor = (r.randint(window[0] - 300, window[2] + 300), r.randint(window[1] - 300, window[3] + 300))
    if r.random() < 0.3:
        cursor = center
    elif r.random() < 0.4:  # on and next to the window edges
        cursor = (r.choice([window[0] - 1, window[0], window[2] - 1, window[2], cursor[0]]),
                  r.choice([window[1] - 1, window[1], window[3] - 1, window[3], cursor[1]]))
    win = Win32(foreground=r.choice([HWND_GAME, HWND_GAME, HWND_GAME, 0x20020, 0]), cursor=cursor, window=window,
                client_origin=(window[0] + 8, window[1] + 30), client_size=(window[2] - window[0] - 16,
                                                                           window[3] - window[1] - 38),
                show_count=r.randint(-3, 2))

    def setup(w):
        wmv = va("s_wmv")
        w.write(wmv, struct.pack("<iiiBB", old_buttons, *old_pos, active, init))
        w.u32(va("window_center_x"), center[0])
        w.u32(va("window_center_y"), center[1])
        w.u32(va("in_appactive"), appactive)
        mouse_dvar = w.alloc(bytes(0x60))
        w.write(mouse_dvar + 0x10, bytes([in_mouse]))
        w.u64(va("in_mouse"), mouse_dvar)
        mode = w.alloc(bytes(0x60))
        w.u32(mode + 0x10, display_mode)
        w.u64(va("r_displayMode"), mode)
        w.u32(va("clientUIActives") + 0x8, connstate)
        gwv = va("g_wv")
        w.u64(gwv + 0x10, hwnd)
        w.u32(gwv + 0x40, sys_time)
        vid = va("cls") + 0x180  # cls.vidConfig
        w.u32(vid + 0x8, display[0])
        w.u32(vid + 0xC, display[1])
        w.u32(vid + 0x20, monitor[0])
        w.u32(vid + 0x24, monitor[1])
        Win32(**vars(win)).install(w.m)  # a fresh copy: the model's state changes during the call
    return setup


def _returns(value):
    return lambda mu: value


def _register(mu):
    return 0x500F00  # a scratch dvar_t (inside SCRATCH, zeroed)


FAKES = {
    "?CL_MouseEvent@@YAHHHHH@Z": None,  # per input
    "?IN_GamepadsMove@@YAXXZ": _returns(None),
    "?Sys_QueEvent@@YAXHW4sysEventType_t@@HHHPEAX@Z": _returns(None),
    "?IN_StartupGamepads@@YAXXZ": _returns(None),
    "?sub_140549740@@YAXP6AXH@Z@Z": _returns(None),
    "?sub_140549770@@YAXP6AXH@Z@Z": _returns(None),
    "?sub_14054A330@@YAXXZ": _returns(None),
    "?sub_14054A2E0@@YAXXZ": _returns(None),
    "?Dvar_ClearModified@@YAXPEBUdvar_t@@@Z": _returns(None),
    "?Dvar_RegisterBool@@YAPEBUdvar_t@@PEBD_NI0@Z": _register,
    "?Dvar_GetBool@@YA_NPEBD@Z": None,  # per input
}
OBSERVE = {
    "?CL_MouseEvent@@YAHHHHH@Z": "iiii",
    "?IN_GamepadsMove@@YAXXZ": "",
    "?Sys_QueEvent@@YAXHW4sysEventType_t@@HHHPEAX@Z": "iiii",
    "?sub_14030B6E0@@YAXH@Z": "i",
    "?IN_StartupGamepads@@YAXXZ": "",
    "?sub_140549740@@YAXP6AXH@Z@Z": "q",
    "?sub_140549770@@YAXP6AXH@Z@Z": "q",
    "?sub_14054A330@@YAXXZ": "",
    "?sub_14054A2E0@@YAXXZ": "",
    "?Dvar_ClearModified@@YAXPEBUdvar_t@@@Z": "q",
    "?Dvar_RegisterBool@@YAPEBUdvar_t@@PEBD_NI0@Z": "sbis",
    "?Dvar_GetBool@@YA_NPEBD@Z": "s",
}


def _input(args):
    def make(r):
        fakes = {k: v for k, v in FAKES.items() if v}
        fakes["?CL_MouseEvent@@YAHHHHH@Z"] = _returns(r.choice([0, 1, 1]))
        fakes["?Dvar_GetBool@@YA_NPEBD@Z"] = _returns(r.choice([0, 0, 0, 1]))
        return {"args": args(r), "setup": _state(r), "fakes": fakes}
    return make


def inputs(seed, args, n=400):
    r = random.Random(seed)
    return [_input(args)(r) for _ in range(n)]


def case(symbol, seed, args=lambda r: [], n=400, ret="void"):
    return {"symbol": symbol, "build": STORE, "ret": ret, "observe": OBSERVE, "inputs": inputs(seed, args, n)}


CASES = [
    case("?IN_RecenterMouse@@YAXXZ", 218),
    case("?IN_ActivateMouse@@YAXH@Z", 329, lambda r: [r.choice([0, 1])]),
    case("?IN_MouseEvent@@YAXH@Z", 405, lambda r: [r.randint(0, 31) if r.random() < 0.9 else r.getrandbits(32)]),
    case("?IN_SetCursorPos@@YAXHH@Z", 506, lambda r: [r.randint(-100, 2000), r.randint(-100, 1200)]),
    case("?IN_ShowSystemCursor@@YAXH@Z", 522, lambda r: [r.choice([0, 1, 2])]),
    case("?IN_Shutdown@@YAXXZ", 637),
    case("?IN_Init@@YAXXZ", 579, n=50),
    case("?IN_Activate@@YAXH@Z", 597, lambda r: [r.choice([0, 1, 5])]),
    case("?IN_Frame@@YAXXZ", 615, n=1500),
]
