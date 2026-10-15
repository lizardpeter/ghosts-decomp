"""Differential cases for the mouse half of client_mp/cl_input.cpp against the Store build.

Random client state (mouse accumulators and index, sensitivity scale, yaw/pitch speed caps, view angles, pm_flags,
frame_msec, cls.frametime, key catchers, connection state, strafe/mlook buttons) and random mouse dvars, set up as
scratch dvar_t's. The engine around the mouse code is faked and its arguments compared: the UI, the cgame,
aim assist (AimAssist_UpdateMouseInput gets its whole AimInput checked and returns a made-up AimOutput), the
profile settings (gpadEnabled).
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX

from syms import _names, static, va
from win32 import HWND_GAME, Win32

STORE = "iw6mp64_MSStore_ship"
CL_MOUSEDX, CL_FOVSCALE, CL_VIEWANGLES = 0x3534, 0x3568, 0x3610
KB_SIZE, KB_STRAFE, KB_MLOOK = 0x14, 8, 13
SETTINGS = 0x500E00  # scratch GamerSettingState (gpadEnabled at +0x2BC)


def _f(r, *choices):
    return r.choice(choices) if r.random() < 0.7 else r.uniform(-3, 3)


def _state(r):
    dx = [r.choice([0, 0, 1, -1, 7, -40, 300, r.randint(-5000, 5000)]) for _ in range(2)]
    dy = [r.choice([0, 0, 1, -1, 5, -25, 200, r.randint(-5000, 5000)]) for _ in range(2)]
    index = r.choice([0, 1])
    fov_scale = r.choice([1.0, 1.0, 0.5, 0.35, 0.0])
    max_pitch, max_yaw = r.choice([0.0, 0.0, 90.0, 0.5]), r.choice([0.0, 0.0, 90.0, 0.5])
    angles = [r.uniform(-400, 400) for _ in range(3)]
    view_delta = [r.uniform(-5, 5) for _ in range(3)]
    pm_flags = r.choice([0, 0, 0, 0x800, 0x801])
    frame_msec = r.choice([0, 1, 7, 16, 16, 33, 100])
    frametime = r.choice([0, 7, 16, 33])
    dvars = {
        "m_filter": ("b", r.choice([0, 1])),
        "m_pitch": ("f", _f(r, 0.022, 0.022, -0.022, 0.0)),
        "m_yaw": ("f", _f(r, 0.022, 0.022, -0.022)),
        "m_forward": ("f", _f(r, 0.25, -0.25)),
        "m_side": ("f", _f(r, 0.25, -0.25)),
        "cl_sensitivity": ("f", r.choice([5.0, 1.5, 0.01, 100.0, r.uniform(0, 20)])),
        "cl_mouseAccel": ("f", r.choice([0.0, 0.0, 0.5, 2.0])),
        "cl_freelook": ("b", r.choice([0, 1, 1])),
        "cl_bypassMouseInput": ("b", r.choice([0, 0, 1])),
        "r_displayMode": ("i", r.choice([0, 0, 1, 2])),
    }
    strafe, mlook = r.random() < 0.25, r.random() < 0.3
    catchers = r.choice([0, 0, 0x10, 0x40, 0x50, 0x1])
    connstate = r.choice([0, 1, 5, 9, 10, 10, 10])
    gpad = r.random() < 0.15
    win = Win32(foreground=HWND_GAME, show_count=r.randint(-2, 1))

    def setup(w):
        cl = va("clients")
        w.write(cl + CL_MOUSEDX, struct.pack("<5i", *dx, *dy, index))
        w.write(cl + CL_FOVSCALE, struct.pack("<3f", fov_scale, max_pitch, max_yaw))
        w.write(cl + CL_VIEWANGLES, struct.pack("<6f", *angles, *view_delta))
        w.u32(cl + 0x8 + 0xC, pm_flags)
        w.u32(va("frame_msec"), frame_msec)
        w.u32(va("cls") + 0x118, frametime)
        for name, (kind, value) in dvars.items():
            d = w.alloc(bytes(0x60))
            w.write(d + 0x10, struct.pack({"b": "<B", "f": "<f", "i": "<i"}[kind], value))
            w.u64(va(name), d)
        kb = static("client_mp/cl_input.cpp", "playersKb")
        w.write(kb + KB_STRAFE * KB_SIZE + 0x10, bytes([strafe]))
        w.write(kb + KB_MLOOK * KB_SIZE + 0x10, bytes([mlook]))
        ui = va("clientUIActives")
        w.u32(ui + 0x4, catchers)
        w.u32(ui + 0x8, connstate)
        w.m.mu.mem_write(SETTINGS + 0x2BC, bytes([gpad]))
        w.u64(va("g_wv") + 0x10, HWND_GAME)
        Win32(**vars(win)).install(w.m)
    return setup


def _ret(value):
    return lambda mu: value


def _aim_assist(mu):
    """Record the AimInput, return an AimOutput derived from it (pitch + 1, yaw - 2, melee fields kept)."""
    inp = bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 0x33))  # 0x33 is padding
    m = _aim_assist.machine
    m.observed.append(("AimInput", inp))
    pitch, yaw = struct.unpack_from("<f", inp, 8)[0], struct.unpack_from("<f", inp, 0x14)[0]
    mu.mem_write(mu.reg_read(UC_X86_REG_RDX), struct.pack("<ffHB", pitch + 1.0, yaw - 2.0,
                                                         *struct.unpack_from("<HB", inp, 0x30)) + b"\0")
    return None


def _melee_to_cmd(mu):
    out = bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 0xB))  # 0xB is padding
    _aim_assist.machine.observed.append(("AimOutput", out, mu.reg_read(UC_X86_REG_RDX)))
    return None


def _input(args, extra_fakes=()):
    def make(r):
        fakes = {
            "?UI_GetActiveMenu@@YA?AW4uiMenuCommand_t@@W4LocalClientNum_t@@@Z": _ret(r.choice([0, 6, 2])),
            "?UI_MouseEvent@@YAXW4LocalClientNum_t@@HH@Z": _ret(None),
            "?sub_140222E90@@YA_NXZ": _ret(r.choice([1, 1, 0])),
            "?sub_140223950@@YAXW4LocalClientNum_t@@HH@Z": _ret(None),
            "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": _ret(SETTINGS),
            "?CG_GetPredictedPlayerState@@YAPEBUplayerState_s@@W4LocalClientNum_t@@@Z": _ret(0x500D00),
            "?BG_MeleeChargeShouldLockView@@YAHPEBUplayerState_s@@E@Z": _ret(r.choice([0, 0, 0, 1])),
            "?AimAssist_UpdateMouseInput@@YAXPEBUAimInput@@PEAUAimOutput@@@Z": _aim_assist,
            "?sub_14027B800@@YAXPEBUAimOutput@@PEAUusercmd_s@@@Z": _melee_to_cmd,
        }
        state = _state(r)

        def setup(w):
            _aim_assist.machine = w.m
            state(w)
        return {"args": args(r), "setup": setup, "fakes": fakes}
    return make


OBSERVE = {
    "?UI_GetActiveMenu@@YA?AW4uiMenuCommand_t@@W4LocalClientNum_t@@@Z": "i",
    "?UI_MouseEvent@@YAXW4LocalClientNum_t@@HH@Z": "iii",
    "?sub_140222E90@@YA_NXZ": "",
    "?sub_140223950@@YAXW4LocalClientNum_t@@HH@Z": "iii",
    "?sub_14030B720@@YAXH@Z": "i",
    "?IN_ShowSystemCursor@@YAXH@Z": "i",
    "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": "i",
    "?CG_GetPredictedPlayerState@@YAPEBUplayerState_s@@W4LocalClientNum_t@@@Z": "i",
    "?BG_MeleeChargeShouldLockView@@YAHPEBUplayerState_s@@E@Z": "qb",
}


def inputs(seed, args, n):
    r = random.Random(seed)
    return [_input(args)(r) for _ in range(n)]


def _usercmd(r):
    cmd = bytearray(r.getrandbits(8) for _ in range(0x3C))
    if r.random() < 0.5:
        cmd[0x1C] = r.choice([0, 127, 129, 120, 5])
        cmd[0x1D] = r.choice([0, 127, 129, 136, 250])
    return bytes(cmd)


def _mouse_args(r):
    return [r.randint(-100, 2000), r.randint(-100, 1200), r.choice([0, 0, 1, -3, 40, r.randint(-900, 900)]),
            r.choice([0, 0, -1, 2, -30, r.randint(-600, 600)])]


def _movement_args(r):
    """CL_GetMouseMovement(cl, &mx, &my): cl is clients[0]; mx and my come back in the two buffers."""
    return [_names(STORE)["clients"], bytes(8), bytes(8)]


CASES = [
    {"symbol": "?CL_MouseEvent@@YAHHHHH@Z", "build": STORE, "ret": "int", "observe": OBSERVE,
     "inputs": inputs(1741, _mouse_args, 800)},
    {"symbol": "?CL_ShowSystemCursor@@YAXH@Z", "build": STORE, "ret": "void", "observe": OBSERVE,
     "inputs": inputs(1795, lambda r: [r.choice([0, 1])], 100)},
    {"symbol": "?CL_MouseMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@M@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE,
     "inputs": inputs(2168, lambda r: [0, _usercmd(r), ("f", r.choice([0.0, 0.016, 0.033, r.uniform(0, 1)]))], 1500)},
]
CASES += [
    {"symbol": "?CL_GetMouseMovement@@YAXPEAUclientActive_t@@PEAM1@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE, "inputs": inputs(2147, _movement_args, 600)},
    {"symbol": "?sub_14030D4A0@@YAXPEAUclientActive_t@@PEAM1@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE, "inputs": inputs(2148, _movement_args, 1500)},
]
