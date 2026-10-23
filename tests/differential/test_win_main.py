"""Differential cases for win32/win_main.cpp (the event queue and the message pump) against the Store build.

Every input sets up a random event queue (eventQue, eventHead, eventTail: empty, a few events, full, wrapped,
overflowing, and odd counters), a random window message queue (win32_messages: keys, system keys, characters, mouse
buttons and wheel, WM_NULL/WM_TIMER, sometimes WM_QUIT) whose messages the Store build's own window procedure
handles, the key catchers, the mouse-button state and a random line in the console window's buffer. The critical
section, the console, Com_Quit_f and R_CheckLostDevice calls are observed, the Win32 and heap calls logged, so the
two runs must make the same calls in the same order and leave the same queue behind.
"""
import random
import struct

from syms import va
from win32_messages import Messages, Msg

STORE = "iw6mp64_MSStore_ship"
EV_SIZE = 0x20
CONSOLE_LINE = 0x149D626E8  # Sys_ConsoleInput's line buffer (win_syscon.cpp static, name unknown)

# the messages MainWndProc turns into events (or passes on)
WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x102, 0x104, 0x105
MOUSE = (0x200, 0x201, 0x202, 0x204, 0x205, 0x207, 0x208, 0x20B, 0x20C)
WM_MOUSEWHEEL = 0x20A


def _event(r, ptr_ok=True):
    ptr = r.choice([0, 0, 0, 0x5D0000 + 0x40 * r.randint(0, 15)]) if ptr_ok else 0
    return struct.pack("<iiiiiiQ", r.choice([0, 0, 0, r.getrandbits(31)]), r.getrandbits(32) - (1 << 31),
                       r.choice([0, 1, 1, 1, 2, 3, r.randint(4, 9)]), r.randint(0, 300), r.choice([0, 1]),
                       r.choice([0, 0, 5, 300]), ptr)


def _counters(r, empty):
    tail = r.choice([0, 0, 5, 250, 255, 256, 1000, r.getrandbits(20), 0x7FFFFF00])
    n = 0 if r.random() < empty else r.choice([0, 0, 1, 1, 2, 3, 10, 255, 256, 257, 300, -1, -5])
    return tail + n, tail


def _message(r):
    kind = r.random()
    lparam = (r.getrandbits(8) << 16) | (r.getrandbits(1) << 24) | r.choice([0, 1 << 30, 1 << 31])
    if r.random() < 0.15:
        lparam = (0x29 << 16) | r.choice([0, 1 << 24])  # the console key's scan code
    if kind < 0.45:
        return Msg(r.choice([WM_KEYDOWN, WM_KEYUP, WM_KEYDOWN, WM_SYSKEYDOWN, WM_SYSKEYUP]),
                   r.choice([r.randint(1, 0x91), 0x0D, 0x1B, 0x20, 0x41, 0x57, 0x60, 0x65, 0x6E, 0xA0, 0xDE]),
                   lparam, r.getrandbits(32))
    if kind < 0.6:
        return Msg(WM_CHAR, r.choice([0x41, 0x61, 0x60, 0x7E, 0x0D, r.randint(0, 255)]), lparam, r.getrandbits(32))
    if kind < 0.85:
        return Msg(r.choice(MOUSE), r.getrandbits(7), r.getrandbits(32), r.getrandbits(32))
    if kind < 0.93:
        return Msg(WM_MOUSEWHEEL, r.choice([120, -120, 240, 0]) << 16, 0, r.getrandbits(32))
    return Msg(r.choice([0x0, 0x113]), r.getrandbits(16), 0, r.getrandbits(32))


def _state(r, empty=0.0):
    head, tail = _counters(r, empty)
    slots = {i & 0xFF: _event(r) for i in range(tail - 2, tail + min(max(head - tail, 0), 260) + 2)}
    msgs = [_message(r) for _ in range(r.choice([0, 0, 1, 2, 3, 6] if empty < 0.5 else [0, 1, 2, 3, 6]))]
    if r.random() < 0.1:
        msgs.insert(r.randint(0, len(msgs)), Msg(0x12))  # WM_QUIT
    line = r.choice([None, None, None, b"", b"map mp_prisonbreak", b"x", b"say hi\n"])
    catchers = r.choice([0, 0, 1, 0x10, 0x40, 0x50, r.getrandbits(8)])
    ui_flag = r.choice([0, 0, 1])
    buttons, mouse_init = r.randint(0, 31), r.random() < 0.8
    vk_chars = {vk: r.choice([vk, 0x80 | r.getrandbits(7), 0]) for vk in range(0x20, 0x92) if r.random() < 0.3}
    sys_time = r.getrandbits(32)
    console_cs = r.random() < 0.3

    def setup(w):
        Messages(msgs, vk_chars=vk_chars).install(w.m)
        q = va("eventQue")
        for i, data in slots.items():
            w.write(q + EV_SIZE * i, data)
        w.write(va("eventHead"), struct.pack("<i", head - (1 << 32) if head >= 1 << 31 else head))
        w.write(va("eventTail"), struct.pack("<i", tail))
        if line is not None:
            w.write(CONSOLE_LINE, line + b"\0")
        w.u32(va("clientUIActives") + 4, catchers)
        w.u32(0x149AC3C8C, ui_flag)  # MapKey's other key-catching flag (name unknown)
        w.write(va("s_wmv"), struct.pack("<i", buttons))
        w.write(va("s_wmv") + 0xC, bytes([0, mouse_init]))
        w.u32(va("g_wv") + 0x40, sys_time)
    return setup


def _logged_return(value):
    return lambda mu: value


FAKES = {
    "?Com_Quit_f@@YAXXZ": _logged_return(None),
    "?R_CheckLostDevice@@YA_NXZ": _logged_return(0),
}
OBSERVE = {
    "?Sys_EnterCriticalSection@@YAXW4CriticalSection@@@Z": "i",
    "?Sys_LeaveCriticalSection@@YAXW4CriticalSection@@@Z": "i",
    "?Sys_ConsoleInput@@YAPEADXZ": "",
    "?Sys_Milliseconds@@YAHXZ": "",
    "?Com_Quit_f@@YAXXZ": "",
    "?R_CheckLostDevice@@YA_NXZ": "",
    "?I_strncpyz@@YAXPEADPEBDH@Z": "qsi",
}


def case(symbol, seed, args=lambda r: [], n=500, ret="void", empty=0.0):
    """empty: the share of inputs whose event queue starts empty (the pump runs only then)"""
    r = random.Random(seed)
    inputs = [{"args": args(r), "setup": _state(r, empty)} for _ in range(n)]
    return {"symbol": symbol, "build": STORE, "ret": ret, "fakes": FAKES, "observe": OBSERVE, "inputs": inputs}


def _que_args(r):
    return [r.choice([0, 0, r.getrandbits(32)]), r.choice([0, 1, 2, 3, r.getrandbits(32)]), r.choice([0, 200, -1]),
            r.choice([0, 1]), r.choice([0, 7]), r.choice([0, 0x5D0400])]


CASES = [
    case("?Sys_QueEvent@@YAXHW4sysEventType_t@@HHHPEAX@Z", 973, _que_args),
    case("?Sys_ShutdownEvents@@YAXXZ", 1018),
    case("?Sys_LoadingKeepAlive@@YAXXZ", 1048),
    case("?Sys_GetEvent@@YA?AUsysEvent_t@@XZ", 1096, lambda r: [bytes(EV_SIZE)], n=800, empty=0.6),
]
