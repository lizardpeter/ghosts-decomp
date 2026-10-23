"""Keys and mouse buttons applied after the frame wait (enhanced/client/cl_late_input.cpp, records/patches.tsv P0009).

What must hold:
- outside the game (a key catcher set, not CA_ACTIVE, an error being handled, or no cgame) nothing is pumped or taken;
- in game, the window messages are pumped once (Sys_LoadingKeepAlive), then queued events are handed to
  CL_KeyEvent/CL_CharEvent in order, as Com_EventLoop would, until the first event that isn't safe mid-frame: console
  text, Escape, Alt+F4, a press of an unsafe binding (+frag/+smoke, action slots, togglemenu, weapnext, pause,
  chatmode, weapprev), or a release whose "-" half is unsafe; it and everything after it stay queued;
- an auto-repeat press is safe whatever its binding; the state is re-tested before every event (a handler may open
  a menu); the queue is only touched under the event queue's critical section; it doesn't re-enter;
- the enhanced R_SyncGpu calls it last, after every wait, and not when the device is lost.
"""
import struct

from frame_model import log
from syms import va
from win32_display import logged_fake

DISPATCH = "?CL_DispatchLateInput@@YAXXZ"
KEY_EVENT = "?CL_KeyEvent@@YAXW4LocalClientNum_t@@HHI@Z"
CHAR_EVENT = "?CL_CharEvent@@YAXW4LocalClientNum_t@@H@Z"
KEEP_ALIVE = "?Sys_LoadingKeepAlive@@YAXXZ"
ERROR_ENTERING = "?Com_ErrorEntering@@YA_NXZ"
ENTER_CS = "?Sys_EnterCriticalSection@@YAXW4CriticalSection@@@Z"
LEAVE_CS = "?Sys_LeaveCriticalSection@@YAXW4CriticalSection@@@Z"

SE_KEY, SE_CHAR, SE_CONSOLE = 1, 2, 3
K_ESCAPE, K_ALT, K_F4 = 0x1B, 0x9E, 0xAA
CA_ACTIVE = 0xA
KEYS = 0x124       # PlayerKeyState::keys (12 bytes each: down, repeats, binding)
CGAME_UP = 0x3390  # the pointer CL_ExecBinding tests in cgArray

# bindings (src/client/cl_keys.cpp; docs/input.md, the CL_ExecBinding table)
ATTACK, FRAG, SMOKE, ACTIONSLOT1, STANCE, WEAPNEXT, TOGGLEMENU = 0x1, 0x5, 0x7, 0xF, 0x1D, 0x56, 0x55


def _state(env, events, head=None, tail=7, catchers=0, conn=CA_ACTIVE, cgame=True, bindings=None, down=None,
           repeats=None, guard=False):
    """events: (type, value, value2) from eventTail on; bindings/down/repeats: {key: value}."""
    def setup(w):
        q = va("eventQue")
        for i, (typ, value, value2) in enumerate(events):
            w.write(q + ((tail + i) & 0xFF) * 0x20, struct.pack("<iiiiiiQ", 0, 1000 + i, typ, value, value2, 0, 0))
        w.u32(va("eventTail"), tail)
        w.u32(va("eventHead"), tail + len(events) if head is None else head)
        ui = va("clientUIActives")
        w.write(ui + 4, struct.pack("<ii", catchers, conn))
        w.u64(va("cgArray") + CGAME_UP, 0x900000 if cgame else 0)
        pk = va("playerKeys")
        for key in set(bindings or {}) | set(down or {}) | set(repeats or {}):
            w.write(pk + KEYS + key * 12, struct.pack("<iii", (down or {}).get(key, 0), (repeats or {}).get(key, 0),
                                                       (bindings or {}).get(key, 0)))
        w.write(env.data("s_dispatchingLateInput"), bytes([guard]))
    return setup


def _run(env, setup, error=0, key_event=None):
    fakes = {
        KEEP_ALIVE: logged_fake("Sys_LoadingKeepAlive", ""),
        KEY_EVENT: key_event or logged_fake("CL_KeyEvent", "iiii"),
        CHAR_EVENT: logged_fake("CL_CharEvent", "ii"),
        ERROR_ENTERING: logged_fake("Com_ErrorEntering", "", error),
        ENTER_CS: logged_fake("Enter", "i"),
        LEAVE_CS: logged_fake("Leave", "i"),
    }
    _, _, written, observed = env.call(DISPATCH, [], setup=setup, fakes=fakes)
    calls = [o[1:] for o in observed if o[0] == "call" and o[1] != "Com_ErrorEntering"]
    tail = struct.unpack("<I", b"".join(written.get(va("eventTail") + i, b"\x00") for i in range(4)))[0] \
        if va("eventTail") in written else None
    return calls, tail


def _dispatched(calls):
    return [c for c in calls if c[0] in ("CL_KeyEvent", "CL_CharEvent")]


def _balanced(calls):
    depth = 0
    for c in calls:
        if c[0] == "Enter":
            assert c[1] == 0x11 and depth == 0, calls
            depth += 1
        elif c[0] == "Leave":
            assert c[1] == 0x11 and depth == 1, calls
            depth -= 1
        elif c[0] in ("CL_KeyEvent", "CL_CharEvent", "Sys_LoadingKeepAlive"):
            assert depth == 0, calls  # handlers and the pump run outside the queue's critical section
    assert depth == 0, calls


def test_safe_keys_dispatched_in_order(env):
    events = [(SE_KEY, ord("w"), 1), (SE_CHAR, ord("w"), 0), (SE_KEY, 0xC8, 1), (SE_KEY, ord("w"), 0)]
    calls, tail = _run(env, _state(env, events, bindings={ord("w"): STANCE, 0xC8: ATTACK}))
    assert calls[0] == ("Sys_LoadingKeepAlive",), calls
    assert _dispatched(calls) == [("CL_KeyEvent", 0, ord("w"), 1, 1000), ("CL_CharEvent", 0, ord("w")),
                                  ("CL_KeyEvent", 0, 0xC8, 1, 1002), ("CL_KeyEvent", 0, ord("w"), 0, 1003)], calls
    assert tail == 11
    _balanced(calls)


def test_stops_at_first_unsafe_event_and_keeps_the_rest(env):
    for unsafe, bindings, extra in (
            ((SE_KEY, ord("g"), 1), {ord("g"): FRAG}, {}),
            ((SE_KEY, ord("q"), 1), {ord("q"): SMOKE}, {}),
            ((SE_KEY, ord("1"), 1), {ord("1"): ACTIONSLOT1}, {}),
            ((SE_KEY, ord("1"), 0), {ord("1"): ACTIONSLOT1}, {}),        # -actionslot 1 (0x10) is unsafe too
            ((SE_KEY, 0xC9, 1), {0xC9: WEAPNEXT}, {}),
            ((SE_KEY, ord("p"), 1), {ord("p"): TOGGLEMENU}, {}),
            ((SE_KEY, 0x5A + 0x20, 1), {0x7A: 0x5A}, {}),                 # weapprev
            ((SE_KEY, K_ESCAPE, 1), {}, {}),
            ((SE_KEY, K_ESCAPE, 0), {}, {}),  # its press always stays queued, so its release does too
            ((SE_KEY, K_F4, 1), {}, {"down": {K_ALT: 1}}),
            ((SE_KEY, 300, 1), {}, {}),                                   # out of CL_KeyEvent's range
            ((SE_CONSOLE, 0, 0), {}, {}),
            ((0x7, 0, 0), {}, {})):
        events = [(SE_KEY, ord("w"), 1), unsafe, (SE_KEY, ord("w"), 0)]
        b = {**bindings, ord("w"): ATTACK}
        calls, tail = _run(env, _state(env, events, bindings=b, **extra))
        assert _dispatched(calls) == [("CL_KeyEvent", 0, ord("w"), 1, 1000)], (unsafe, calls)
        assert tail == 8, (unsafe, tail)
        _balanced(calls)


def test_safe_variants_of_unsafe_keys(env):
    cases = (
        ((SE_KEY, ord("g"), 0), {ord("g"): FRAG}, {}),           # -frag (6) only releases the button
        ((SE_KEY, ord("q"), 0), {ord("q"): SMOKE}, {}),
        ((SE_KEY, ord("1"), 1), {ord("1"): ACTIONSLOT1}, {"repeats": {ord("1"): 1}}),  # auto-repeat
        ((SE_KEY, K_F4, 1), {}, {}),                              # F4 without Alt
        ((SE_KEY, ord("p"), 0), {ord("p"): TOGGLEMENU}, {}),      # single commands do nothing on release
    )
    for event, bindings, extra in cases:
        calls, tail = _run(env, _state(env, [event], bindings=bindings, **extra))
        assert _dispatched(calls) == [("CL_KeyEvent", 0, event[1], event[2], 1000)], (event, calls)
        assert tail == 8


def test_nothing_outside_the_game(env):
    events = [(SE_KEY, ord("w"), 1)]
    for kwargs, error in (({"catchers": 0x10}, 0), ({"catchers": 0x40}, 0), ({"catchers": 0x1}, 0),
                          ({"catchers": 0x8}, 0), ({"catchers": 0x20}, 0), ({"conn": 9}, 0), ({"conn": 0}, 0),
                          ({"cgame": False}, 0), ({}, 1), ({"guard": True}, 0)):
        calls, tail = _run(env, _state(env, events, bindings={ord("w"): ATTACK}, **kwargs), error=error)
        assert calls == [], (kwargs, error, calls)  # not even the pump
        assert tail is None


def test_empty_queue_only_pumps(env):
    calls, tail = _run(env, _state(env, []))
    assert [c[0] for c in calls] == ["Sys_LoadingKeepAlive", "Enter", "Leave"], calls
    assert tail is None


def test_events_queued_by_the_pump_are_taken(env):
    """The pump's window procedure queues what arrived during the waits; those are the events this is for."""
    base = _state(env, [], bindings={ord("w"): ATTACK})

    def pump(mu):
        from win32_display import CURRENT
        m = CURRENT["m"]
        log("call", "Sys_LoadingKeepAlive")
        m._emulated_write(va("eventQue") + 7 * 0x20, struct.pack("<iiiiiiQ", 0, 2000, SE_KEY, ord("w"), 1, 0, 0))
        m._emulated_write(va("eventHead"), struct.pack("<I", 8))

    fakes_pump = pump
    calls, tail = _run_with(env, base, {KEEP_ALIVE: fakes_pump})
    assert _dispatched(calls) == [("CL_KeyEvent", 0, ord("w"), 1, 2000)], calls
    assert tail == 8


def _run_with(env, setup, extra):
    fakes = {
        KEEP_ALIVE: logged_fake("Sys_LoadingKeepAlive", ""),
        KEY_EVENT: logged_fake("CL_KeyEvent", "iiii"),
        CHAR_EVENT: logged_fake("CL_CharEvent", "ii"),
        ERROR_ENTERING: logged_fake("Com_ErrorEntering", "", 0),
        ENTER_CS: logged_fake("Enter", "i"),
        LEAVE_CS: logged_fake("Leave", "i"),
    }
    fakes.update(extra)
    _, _, written, observed = env.call(DISPATCH, [], setup=setup, fakes=fakes)
    calls = [o[1:] for o in observed if o[0] == "call" and o[1] != "Com_ErrorEntering"]
    tail = struct.unpack("<I", b"".join(written.get(va("eventTail") + i, b"\x00") for i in range(4)))[0] \
        if va("eventTail") in written else None
    return calls, tail


def test_state_retested_after_each_event(env):
    """A handler that opens a menu (sets a key catcher) stops the drain right after it."""
    def key_event(mu):
        from unicorn.x86_const import UC_X86_REG_EDX
        from win32_display import CURRENT
        m = CURRENT["m"]
        log("call", "CL_KeyEvent", 0, mu.reg_read(UC_X86_REG_EDX))
        m._emulated_write(va("clientUIActives") + 4, struct.pack("<i", 0x10))

    events = [(SE_KEY, ord("w"), 1), (SE_KEY, ord("w"), 0)]
    calls, tail = _run(env, _state(env, events, bindings={ord("w"): ATTACK}), key_event=key_event)
    assert _dispatched(calls) == [("CL_KeyEvent", 0, ord("w"))], calls
    assert tail == 8


def test_queue_wraps(env):
    events = [(SE_KEY, ord("a") + i, 1) for i in range(4)]
    calls, tail = _run(env, _state(env, events, tail=0xFE, bindings={ord("a") + i: ATTACK for i in range(4)}))
    assert [c[2] for c in _dispatched(calls)] == [ord("a") + i for i in range(4)], calls
    assert tail == 0x102


# ---- R_SyncGpu calls it last ---------------------------------------------------------------------------------

def test_sync_gpu_dispatches_last(env):
    import test_frame_wait as fw
    seen = 0
    for inp in fw._inputs(0xE7, 40):
        inp = dict(inp, fakes=dict(inp["fakes"], **{DISPATCH: logged_fake("CL_DispatchLateInput", "")}))
        want = fw._original(env, fw.SYNC, inp)
        got = env.call(fw.SYNC, inp["args"], "void", setup=inp["setup"], fakes=inp["fakes"])
        calls = got[3]
        if ("call", "Sys_Milliseconds") not in want[3]:
            assert ("call", "CL_DispatchLateInput") not in calls  # lost device: no frame
            continue
        assert calls[-1] == ("call", "CL_DispatchLateInput"), calls[-3:]
        assert fw._normalized(env, calls[:-1]) == fw._normalized(env, want[3])
        seen += 1
    assert seen >= 20, seen
