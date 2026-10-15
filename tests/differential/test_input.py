"""Differential cases for the input files: client/cl_keys.cpp, client/cl_gamepad.cpp, client_mp/cl_input.cpp.

These functions work on global state (key bindings, key catchers, console command arguments, button state), so
every input sets up a random but reproducible state first (harness Writer) and then calls with random arguments.
Both the original and the reconstruction see the same state; every byte either writes to the globals, the TLS
block (dvar_modifiedFlags) included, is compared.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX

from syms import static, va

# struct layouts (analysis/iw6_ds_ps4/pdb/types.h)
PLAYER_KEYS_SIZE, KEYS_OFF, OVERSTRIKE_OFF, ANYKEY_OFF, LOCSEL_OFF = 0xD28, 0x124, 0x11C, 0x120, 0xD24
UI_KEYCATCHERS, UI_CONNSTATE, UI_NEXTSCROLL, UI_DPADNEXT, UI_DPADLATEST = 0x4, 0x8, 0xC, 0x10, 0x14
CLS_UISTARTED = 0x114
KB_SIZE, NUM_BUTTONS = 0x14, 35

BIND_COMMANDS = ["", "+attack", "-attack", "+melee", "-melee", "+frag", "-frag", "+smoke", "-smoke",
                 "+breath_sprint", "-breath_sprint", "+usereload", "-usereload", "+speed_throw", "-speed_throw",
                 "+actionslot 1", "-actionslot 1", "+actionslot 2", "-actionslot 2", "+actionslot 3",
                 "-actionslot 3", "+actionslot 4", "-actionslot 4", "+stance", "-stance", "+gostand", "-gostand",
                 "+melee_zoom", "-melee_zoom", "+changezoom", "-changezoom", "+ads_akimbo_accessible",
                 "-ads_akimbo_accessible", "+attack_akimbo_accessible", "-attack_akimbo_accessible",
                 "+melee_breath", "-melee_breath", "+sprint_zoom", "-sprint_zoom", "togglemenu", "weapnext", "pause",
                 "chatmodepublic", "chatmodeteam", "togglescores"]
KEY_NAMES = ["TAB", "ENTER", "ESCAPE", "SPACE", "BACKSPACE", "MOUSE1", "MOUSE2", "MWHEELUP", "F1", "F12", "SHIFT",
             "CTRL", "ALT", "UPARROW", "KP_ENTER", "SEMICOLON", "BUTTON_A", "BUTTON_START", "DPAD_UP", "APAD_LEFT",
             "tab", "Mouse1", "a", "Z", "1", ";", "0x1f", "0xa0", "0xff", "0x0", "0xg5", "0x", "0x123", "",
             "NOTAKEY", "\x7f", "\xe9", "\x80", "\xff"]
AXIS_NAMES = ["A_RSTICK_X", "A_RSTICK_Y", "A_LSTICK_X", "A_LSTICK_Y", "A_RTRIGGER", "A_LTRIGGER", "a_lstick_y",
              "A_NOPE"]
VIRT_NAMES = ["VA_SIDE", "VA_FORWARD", "VA_UP", "VA_YAW", "VA_PITCH", "VA_ATTACK", "va_yaw", "VA_NOPE"]
MAP_NAMES = ["MAP_LINEAR", "MAP_SQUARED", "map_squared", "MAP_CUBIC"]


def _int(r):
    return r.choice([0, 1, -1, 2, 3, 255, 256, 0x7FFFFFFF, -0x80000000, r.randint(-5, 300)])


def _key(r):
    x = r.random()
    if x < 0.7:
        return r.randint(0, 255)
    return r.choice([-1, 256, 300, -2, r.randint(0, 40)])


def _binding(r):
    return r.randint(0, 44) if r.random() < 0.9 else r.choice([45, 100, -1])


def _state(r):
    """Random global state, as a setup function (same bytes for both runs)."""
    keys = bytearray()
    for _ in range(256):
        down = r.choice([0, 0, 0, 1, 1, 2, -1]) if r.random() < 0.3 else 0
        repeats = r.choice([0, 1, 2, 5]) if down else 0
        binding = _binding(r) if r.random() < 0.4 else 0
        keys += struct.pack("<iii", down, repeats, binding)
    overstrike, anykey, locsel = r.choice([0, 1]), r.choice([0, 1, 3, -1]), r.choice([0, 1, 2])
    catchers = r.choice([0, 1, 8, 0x10, 0x40, 0x11, 0x18, 0x58, r.getrandbits(8)])
    connstate = r.randint(0, 10)
    scroll, dpadnext, dpadlatest = r.choice([0, 100, 500, r.randint(-50, 2000)]), r.randint(-50, 2000), r.choice([0, 0x14, 0x15, 0x16, 0x17, 5])
    uistarted, frame_msec, multi = r.choice([0, 1]), r.choice([0, 1, 16, 33, 0xFFFFFFFF]), r.choice([0, 1])
    debounce = r.choice([0, 100, 250, -5])
    language = r.choice([0, 1, 1, 2])
    gaglobs = struct.pack("<6i", *(r.randint(-5, 5) for _ in range(6))) + b"".join(
        struct.pack("<ii", r.choice([0, 1, 5, 0xFF]), r.choice([0, 1, 0xFF])) for _ in range(6))
    kb = b"".join(struct.pack("<iiIIBBxx", r.choice([0, 0, 5, 9, -1]), r.choice([0, 0, 7]), r.getrandbits(8),
                              r.getrandbits(10), r.choice([0, 1]), r.choice([0, 1])) for _ in range(NUM_BUTTONS))

    def setup(w):
        pk = va("playerKeys")
        w.write(pk + KEYS_OFF, keys)
        w.u32(pk + OVERSTRIKE_OFF, overstrike)
        w.u32(pk + ANYKEY_OFF, anykey)
        w.u32(pk + LOCSEL_OFF, locsel)
        ui = va("clientUIActives")
        w.u32(ui + UI_KEYCATCHERS, catchers)
        w.u32(ui + UI_CONNSTATE, connstate)
        w.u32(ui + UI_NEXTSCROLL, scroll)
        w.u32(ui + UI_DPADNEXT, dpadnext)
        w.u32(ui + UI_DPADLATEST, dpadlatest)
        w.u32(va("cls") + CLS_UISTARTED, uistarted)
        w.u32(va("frame_msec"), frame_msec)
        w.u32(va("cl_multi_gamepads_enabled"), multi)
        dvar = w.alloc(bytes(0x60))
        w.u32(dvar + 0x10, debounce)  # dvar_t.current.integer
        w.u64(va("gpad_dpadDebounceTime"), dvar)
        lang = w.alloc(bytes(0x60))
        w.u32(lang + 0x10, language)
        w.u64(va("loc_language"), lang)
        w.write(static("client/cl_gamepad.cpp", "gaGlobs"), gaglobs)
        w.write(static("client_mp/cl_input.cpp", "playersKb"), kb)
    return setup


def _with_args(state, argv):
    """State plus console command arguments (Cmd_Argc/Cmd_Argv read cmd_args at its current nesting)."""
    def setup(w):
        state(w)
        ptrs = [w.cstr(a) for a in argv]
        array = w.alloc(b"".join(struct.pack("<Q", p) for p in ptrs) + bytes(8))
        ca = va("cmd_args")
        w.u32(ca, 0)                     # nesting
        w.u32(ca + 0x44, len(argv))      # argc[0]
        w.u64(ca + 0x68, array)          # argv[0]
    return setup


def _cmd(r):
    x = r.random()
    if x < 0.7:
        return r.choice(BIND_COMMANDS[1:])
    if x < 0.85:
        return r.choice(BIND_COMMANDS[1:]).upper()
    return r.choice(["", "bind", "+ATTACKX", "togglescores ", "+actionslot 9"])


def _lc(r):
    return 0 if r.random() < 0.9 else r.choice([1, 2])


def _dvar_ints(r):
    """Dvar_GetInt by name, for dvars the emulator never registered (menu scroll delays)."""
    values = {b"gpad_menu_scroll_delay_first": r.choice([0, 300, 420]),
              b"gpad_menu_scroll_delay_rest_start": r.choice([0, 100, 210]),
              b"gpad_menu_scroll_delay_rest_end": r.choice([0, 50, 110]),
              b"gpad_menu_scroll_delay_rest_accel": r.choice([0, 5, 33, -7])}
    return lambda mu: values.get(bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 40)).split(b"\0")[0], 0)


def _error_entering(r):
    value = r.choice([0, 0, 1])
    return lambda mu: value


def cstr(s):
    return s.encode("latin1") + b"\0"


def inputs(seed, make, n=300):
    r = random.Random(seed)
    return [make(r) for _ in range(n)]


def _plain(fn, **fakes):
    """Inputs with random state and arguments from fn(r) -> list; fakes: symbol -> maker(r) of a fake."""
    return lambda r: {"args": fn(r), "setup": _state(r), "fakes": {s: make(r) for s, make in fakes.items()}}


def _command(arg_lists):
    """Inputs for a console command: random state and argv from arg_lists(r)."""
    return lambda r: {"args": [], "setup": _with_args(_state(r), arg_lists(r))}


def _bind_args(r):
    n = r.choice([0, 1, 2, 3, 3, 3, 4])
    return ["bind", r.choice(KEY_NAMES), _cmd(r), "extra"][:n]


def _swap_args(r):
    n = r.choice([2, 3, 3, 3, 3, 4])
    return ["bind_swap", r.choice(KEY_NAMES), r.choice(KEY_NAMES), "x"][:n]


def _unbind_args(r):
    return ["unbind", r.choice(KEY_NAMES), "x"][:r.choice([1, 2, 2, 2, 3])]


def _axis_args(r):
    n = r.choice([1, 2, 2, 3, 3, 4, 4, 4])
    return ["bindaxis", r.choice(AXIS_NAMES), r.choice(VIRT_NAMES), r.choice(MAP_NAMES)][:n]


def _cmdargv_args(r):
    n = r.randint(0, 4)
    return [f"arg{i}" for i in range(n)]


CASES = [
    {"symbol": "?Cmd_Argv@@YAPEBDH@Z", "ret": "cstr",
     "inputs": inputs(220, lambda r: {"args": [r.randint(0, 5)],
                                      "setup": _with_args(lambda w: None, _cmdargv_args(r))})},
    {"symbol": "?Key_GetOverstrikeMode@@YAHW4LocalClientNum_t@@@Z", "ret": "int",
     "inputs": inputs(1697, _plain(lambda r: [_lc(r)]))},
    {"symbol": "?Key_SetOverstrikeMode@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(1703, _plain(lambda r: [_lc(r), _int(r)]))},
    {"symbol": "?Key_IsDown@@YAHW4LocalClientNum_t@@H@Z", "ret": "int",
     "inputs": inputs(1709, _plain(lambda r: [_lc(r), _key(r)]))},
    {"symbol": "?Key_StringToKeynum@@YAHPEBD@Z", "ret": "int",
     "inputs": inputs(1731, _plain(lambda r: [cstr(r.choice(KEY_NAMES))]))},
    {"symbol": "?Key_IsValidGamePadChar@@YA_ND@Z", "ret": "char",
     "inputs": [[c] for c in range(-128, 128)] + [[c] for c in range(0, 40)]},
    {"symbol": "?Key_KeynumToString@@YAPEBDHHH@Z", "ret": "cstr",
     "inputs": inputs(1805, _plain(lambda r: [_key(r), r.choice([0, 0, 1, 2]), r.choice([0, 1, 1, 2])]), 600)},
    {"symbol": "?Key_SetBinding@@YAXW4LocalClientNum_t@@HH@Z", "ret": "void",
     "inputs": inputs(1898, _plain(lambda r: [_lc(r), _key(r), _binding(r)]))},
    {"symbol": "?Key_GetBindingForCmd@@YAHPEBD@Z", "ret": "int",
     "inputs": inputs(1929, _plain(lambda r: [cstr(_cmd(r))]))},
    {"symbol": "?Key_GetBinding@@YAHW4LocalClientNum_t@@H@Z", "ret": "int",
     "inputs": inputs(1955, _plain(lambda r: [_lc(r), r.randint(0, 255)]))},
    {"symbol": "?Key_GetCommandAssignmentInternal@@YAHW4LocalClientNum_t@@PEBDQEAHH@Z", "ret": "int",
     "inputs": inputs(1963, _plain(lambda r: [_lc(r), cstr(_cmd(r)), bytes(16), r.choice([0, 1, 1, 2])]))},
    {"symbol": "?Key_GetCommandAssignment@@YAHW4LocalClientNum_t@@PEBDQEAH@Z", "ret": "int",
     "inputs": inputs(2030, _plain(lambda r: [_lc(r), cstr(_cmd(r)), bytes(16)]))},
    {"symbol": "?Key_Unbind_f@@YAXXZ", "ret": "void", "inputs": inputs(2055, _command(_unbind_args))},
    {"symbol": "?Key_Unbindall_f@@YAXXZ", "ret": "void", "inputs": inputs(2076, _plain(lambda r: []), 40)},
    {"symbol": "?Key_Bind_f@@YAXXZ", "ret": "void", "inputs": inputs(2092, _command(_bind_args))},
    {"symbol": "?Key_SwapBind_f@@YAXXZ", "ret": "void", "inputs": inputs(2163, _command(_swap_args))},
    {"symbol": "?CL_InitKeyCommands@@YAXXZ", "ret": "void", "inputs": inputs(2356, _plain(lambda r: []), 20)},
    {"symbol": "?Key_ClearStates@@YAXW4LocalClientNum_t@@@Z", "ret": "void",
     "observe": {"?CL_GamepadButtonEvent@@YAXW4LocalClientNum_t@@HHHI@Z": "iiii"},
     "inputs": inputs(3157, _plain(lambda r: [0], **{"?Com_ErrorEntering@@YA_NXZ": _error_entering}), 100)},
    {"symbol": "?CL_GetKeyBindingInternal@@YAHW4LocalClientNum_t@@PEBDQEAY0IA@DH@Z", "ret": "int",
     "inputs": inputs(3169, _plain(lambda r: [_lc(r), cstr(_cmd(r)), bytes(r.getrandbits(8) for _ in range(256)),
                                              r.choice([0, 1, 1])]))},
    {"symbol": "?CL_GetGamePadBinding@@YAHW4LocalClientNum_t@@PEBDQEAY0IA@D@Z", "ret": "int",
     "inputs": inputs(3206, _plain(lambda r: [_lc(r), cstr(_cmd(r)), bytes(r.getrandbits(8) for _ in range(256))]))},
    {"symbol": "?Key_Shutdown@@YAXXZ", "ret": "void", "inputs": inputs(3249, _plain(lambda r: []), 40)},
    {"symbol": "?Key_IsCatcherActive@@YA_NW4LocalClientNum_t@@H@Z", "ret": "char",
     "inputs": inputs(3271, _plain(lambda r: [_lc(r), r.choice([1, 8, 0x10, 0x40, -1, 0, r.getrandbits(8)])]))},
    {"symbol": "?Key_RemoveCatcher@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(3289, _plain(lambda r: [_lc(r), ~r.choice([1, 8, 0x10, 0x40]) if r.random() < 0.8 else _int(r)]))},
    {"symbol": "?Key_SetCatcher@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(3301, _plain(lambda r: [_lc(r), r.choice([0, 1, 8, 0x10, 0x40, 0x18, r.getrandbits(8)])]))},

    {"symbol": "?CL_InitGamepadCommands@@YAXXZ", "ret": "void", "inputs": inputs(173, _plain(lambda r: []), 20)},
    {"symbol": "?CL_InitGamepadAxisBindings@@YAXXZ", "ret": "void", "inputs": inputs(180, _plain(lambda r: []), 20)},
    {"symbol": "?Axis_Bind_f@@YAXXZ", "ret": "void", "inputs": inputs(279, _command(_axis_args))},
    {"symbol": "?Axis_Unbindall_f@@YAXXZ", "ret": "void", "inputs": inputs(343, _plain(lambda r: []), 20)},
    {"symbol": "?CL_CheckForIgnoreDueToRepeat@@YA_NW4LocalClientNum_t@@HHH@Z", "ret": "char",
     "inputs": inputs(579, _plain(lambda r: [0, r.choice([20, 21, 22, 23, 28, 29, 30, 31, 1, 5, 200]),
                                             r.choice([0, 1, 2, 3, 10, 40, -1]), r.choice([0, 100, 500, r.randint(-100, 2500)])],
                                  **{"?Dvar_GetInt@@YAHPEBD@Z": _dvar_ints}), 600)},
    {"symbol": "?CL_GamepadButtonEvent@@YAXW4LocalClientNum_t@@HHHI@Z", "ret": "void",
     # CL_ExecBinding is empty in the server build: check what it is called with
     "observe": {"?CL_ExecBinding@@YAXW4LocalClientNum_t@@HHH@Z": "iiii", "?UI_KeyEvent@@YAXW4LocalClientNum_t@@HH@Z": "iii",
                 "?CG_TranslateGamepadButton@@YA_NW4LocalClientNum_t@@HH@Z": "iii"},
     "inputs": inputs(732, _plain(lambda r: [0, r.randint(0, 3), r.choice([1, 2, 3, 14, 20, 21, 22, 23, 28, 5, 9,
                                                                           r.randint(0, 255)]),
                                             r.choice([0, 0, 1, 1, 2, -1]), r.choice([0, 0, 1, 5000])]), 600)},

    {"symbol": "?CL_UseReload@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(469, _plain(lambda r: [0, r.choice([0, 5, 7, 9, -1, r.randint(0, 255)])]))},
    {"symbol": "?CL_SpecPrev@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(482, _plain(lambda r: [0, r.choice([0, 5, 7, 9, -1, r.randint(0, 255)])]))},
    {"symbol": "?CL_SpecNext@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(489, _plain(lambda r: [0, r.choice([0, 5, 7, 9, -1, r.randint(0, 255)])]))},
    {"symbol": "?CL_ToggleSpec@@YAXW4LocalClientNum_t@@H@Z", "ret": "void",
     "inputs": inputs(496, _plain(lambda r: [0, r.choice([0, 5, 7, 9, -1, r.randint(0, 255)])]))},
]

# The state set up above uses the PS4 server's globals; the Store build doesn't have them all identified yet.
for _case in CASES:
    _case.setdefault("build", "iw6_ds_ps4")
