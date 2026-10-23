"""Differential cases for client/cl_keys.cpp's key-event half (CL_KeyEvent, CL_CharEvent) against the Store build.

Every input sets up random key state for local client 0 (each key's down/repeats/binding, anyKeyDown,
locSelInputState), random key catchers and connection state, cls.uiStarted, cl_bypassMouseInput and the Escape menu
flag. Everything the two functions hand a key to is faked and logged with its arguments (the bindings, the menus,
LUI, the chat line, the menu choices), and the fakes return random answers; the LUI key event sometimes changes the
key catchers, as a Lua handler can, so the order in which the functions re-read them is checked too.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX

from syms import va
from win32_display import CURRENT, log_value
from win32_messages import Messages

STORE = "iw6mp64_MSStore_ship"
PK_ANYKEYDOWN, PK_KEYS, PK_LOCSEL = 0x120, 0x124, 0xD24
K_ESCAPE, K_ALT, K_F4, K_MOUSE1 = 0x1B, 0x9E, 0xAA, 0xC8
SPECIAL_KEYS = [K_ESCAPE, K_ESCAPE, K_F4, K_MOUSE1, K_MOUSE1 + 1, K_MOUSE1 + 2, K_MOUSE1 + 3, 0x60, 0x7E, 0x9A, 0x9B,
                0x9C, 0x9D, 0xA3, 0xA4, 0xA5, 0x0D, 0x20, 0x77]
BINDINGS = [0, 0, 1, 2, 0x27, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x58, 0x59, 0x5B, 0x63, 0x64, -1, -3]


def _key_state(r):
    down = r.choice([0, 0, 0, 1, 1, 2, -1])
    repeats = r.choice([0, 0, 0, 1, 1, 2, 5, -1, 0x7FFFFFFF])
    return struct.pack("<iii", down, repeats, r.choice(BINDINGS + [r.randint(0, 0x64)]))


def _fake(name, sig, result=None, after=None):
    def run(mu):
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", name, *(log_value(mu, c, i) for i, c in enumerate(sig))))
        if after and m is not None:
            after(m, mu)
        return result(mu) if callable(result) else result
    return run


def _state(r):
    keys = b"".join(_key_state(r) for _ in range(256))
    any_down = r.choice([0, 0, 1, 2, 5, -1])
    locsel = r.choice([0, 1, 2, 3])
    catchers = r.choice([0, 0, 0, 1, 8, 8, 0x10, 0x10, 0x20, 0x20, 0x40, 0x50, 0x11, 0x18, 0x21, 0x30,
                         r.getrandbits(8)])
    connstate = r.choice([0, 1, 2, 3, 5, 7, 8, 9, 10, 10, 10, 10, 11, -1])
    ui_started = r.choice([0, 1, 1, 1])
    esc_flag = r.choice([0, 1])
    bypass = r.choice([None, 0, 1, 1])
    alt_down = r.choice([0, 1, -1])
    returns = {
        "lui": r.choice([0, 1, 1, 1]),
        "menu": r.choice([0, 1, 2, 6, 6, 9]),
        "wants": r.choice([0, 1]),
        "gamepad": r.choice([0, 0, 1]),
        "esc_menu": r.choice([1, 7, 8, 9]),
        "controller": r.choice([0, 1, 3]),
        "lui_catchers": r.choice([None, None, None, 0, 0x10, 0x20, 0x41, 1]),
    }

    def setup(w):
        Messages([]).install(w.m)  # an empty message queue; sets CURRENT for the logging fakes
        pk = va("playerKeys")
        w.write(pk + PK_KEYS, keys)
        w.write(pk + PK_KEYS + 12 * K_ALT, struct.pack("<i", alt_down))
        w.write(pk + PK_ANYKEYDOWN, struct.pack("<i", any_down))
        w.write(pk + PK_LOCSEL, struct.pack("<i", locsel))
        ui = va("clientUIActives")
        w.write(ui + 4, struct.pack("<ii", catchers, connstate))
        w.u32(va("cls") + 0x114, ui_started)
        w.write(va("unk_14416A0F9"), bytes([esc_flag]))
        if bypass is None:
            w.u64(va("cl_bypassMouseInput"), 0)
        else:
            dvar = w.alloc(bytes(0x60))
            w.write(dvar + 0x10, bytes([bypass]))
            w.u64(va("cl_bypassMouseInput"), dvar)
        w.m.on_import("user32.dll!PostQuitMessage",
                      lambda mu: w.m.observed.append(("import", "PostQuitMessage", mu.reg_read(UC_X86_REG_RCX))))
        state["returns"] = returns
    return setup


state = {"returns": {}}


def _ret(key):
    return lambda mu: state["returns"].get(key, 0)


def _lui_changes_catchers(m, mu):
    new = state["returns"].get("lui_catchers")
    if new is not None:
        m._emulated_write(va("clientUIActives") + 4, struct.pack("<i", new))


FAKES = {
    "?Message_Key@@YAXW4LocalClientNum_t@@H@Z": _fake("Message_Key", "ii"),
    "?CL_StopLogoOrCinematic@@YAXW4LocalClientNum_t@@@Z": _fake("CL_StopLogoOrCinematic", "i"),
    "?UI_SetActiveMenu@@YAHW4LocalClientNum_t@@H@Z": _fake("UI_SetActiveMenu", "ii", 1),
    "?sub_140527D90@@YAHW4LocalClientNum_t@@@Z": _fake("sub_140527D90", "i", _ret("esc_menu")),
    "?sub_140222E90@@YA_NXZ": _fake("sub_140222E90", "", _ret("lui")),
    "?CL_ControllerIndexFromClientNum@@YAHW4LocalClientNum_t@@@Z": _fake("CL_ControllerIndexFromClientNum", "i", _ret("controller")),
    "?sub_140222ED0@@YAXW4LocalClientNum_t@@HHHH@Z": _fake("sub_140222ED0", "iiiii", None, _lui_changes_catchers),
    "?UI_KeyEvent@@YAXW4LocalClientNum_t@@HH@Z": _fake("UI_KeyEvent", "iii"),
    "?UI_GetActiveMenu@@YA?AW4uiMenuCommand_t@@W4LocalClientNum_t@@@Z": _fake("UI_GetActiveMenu", "i", _ret("menu")),
    "?sub_140503AD0@@YAHW4LocalClientNum_t@@H@Z": _fake("sub_140503AD0", "ii", _ret("wants")),
    "?CL_IsGamepadEnabled@@YA_NW4LocalClientNum_t@@@Z": _fake("CL_IsGamepadEnabled", "i", _ret("gamepad")),
    "?CL_ExecBinding@@YAXW4LocalClientNum_t@@HHH@Z": _fake("CL_ExecBinding", "iiii"),
    "?Field_CharEvent@@YA_NW4LocalClientNum_t@@PEBUScreenPlacement@@PEAUfield_t@@H@Z":
        _fake("Field_CharEvent", "iqqi", 1),
    "?sub_140221EC0@@YAXW4LocalClientNum_t@@H@Z": _fake("sub_140221EC0", "ii"),
}


def _key_args(r):
    roll = r.random()
    key = K_ESCAPE if roll < 0.15 else K_F4 if roll < 0.25 else r.choice(SPECIAL_KEYS) if roll < 0.55 \
        else r.randint(0, 255)
    return [0, key, r.choice([0, 0, 1, 1, 1, 2, -1]), r.getrandbits(32)]


def _char_args(r):
    return [0, r.choice([0x60, 0x7E, 0x41, 0x61, 0x0D, 0x1B, r.randint(0, 255), r.getrandbits(32)])]


def case(symbol, seed, args, n):
    r = random.Random(seed)
    inputs = [{"args": args(r), "setup": _state(r)} for _ in range(n)]
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": FAKES, "inputs": inputs}


CASES = [
    case("?CL_KeyEvent@@YAXW4LocalClientNum_t@@HHI@Z", 2219, _key_args, 3000),
    case("?CL_CharEvent@@YAXW4LocalClientNum_t@@H@Z", 2759, _char_args, 600),
]
