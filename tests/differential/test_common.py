"""Differential cases for qcommon/common.cpp (Com_EventLoop) against the Store build.

Every input sets up a random event queue (key, character, console and bad events; the console text allocated in the
modelled heap) and a random window message queue whose messages the Store build's own window procedure turns into
more events (win32_messages), so the events come through the real Sys_GetEvent of each run. The event handlers
(CL_KeyEvent, CL_CharEvent, Cbuf_AddText, Com_Error) are faked and logged with their arguments. The three packet
sources hand out a random number of packets each (writing a distinct address into `from`), the large-local buffer is
faked, and CL_PacketEvent logs the address, the message's buffer and size, and the time. com_sv_running decides
whether the network is read.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RCX, UC_X86_REG_RDX

from syms import va
from win32_display import CURRENT, log_value
from win32_messages import Messages, Msg

STORE = "iw6mp64_MSStore_ship"
EV_SIZE = 0x20
TEXT = 0x5D0000      # console text the queued SE_CONSOLE events own (inside SCRATCH)
LARGE_BUF = 0x5E0000  # what LargeLocal::GetBuf hands out

state = {}


def _log(name, sig, result=None, after=None):
    def run(mu):
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", name, *(log_value(mu, c, i) for i, c in enumerate(sig))))
            if after:
                after(m, mu)
        return result(mu) if callable(result) else result
    return run


def _source(name, from_reg, msg_reg):
    """A packet source: returns 1 for its first state[name] calls, writing a distinct address into `from`."""
    def run(mu):
        m = CURRENT.get("m")
        left = state.get(name, 0)
        m.observed.append(("call", name, left))
        if left <= 0:
            return 0
        state[name] = left - 1
        state["serial"] = state.get("serial", 0) + 1
        adr = struct.pack("<I4BHHI", 4, 10, 0, 0, state["serial"], 28960, 0, state["serial"] * 3)
        m._emulated_write(mu.reg_read(from_reg), adr)
        msg = mu.reg_read(msg_reg)
        m._emulated_write(msg + 0x1C, struct.pack("<i", 16 * state["serial"]))  # cursize
        return 1
    return run


def _packet_event(mu):
    m = CURRENT.get("m")
    from_ptr, msg = mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    data, maxsize, cursize = struct.unpack("<Q8xii", bytes(mu.mem_read(msg + 8, 0x18)))
    m.observed.append(("call", "CL_PacketEvent", log_value(mu, "i", 0), bytes(mu.mem_read(from_ptr, 16)), data,
                       maxsize, cursize, log_value(mu, "i", 3)))
    return 1


def _event(r):
    kind = r.choice([1, 1, 1, 2, 2, 3, 3, 4, 7])
    text = r.choice([b"", b"bind x +attack", b"quit"]) if kind == 3 else None
    return kind, text, struct.pack("<iiiiii", 0, r.getrandbits(31), kind, r.randint(0, 260), r.choice([0, 1]),
                                   len(text) + 1 if text is not None else 0)


def _state(r):
    tail = r.choice([0, 3, 250, 255, 1000, r.getrandbits(20)])
    events = [_event(r) for _ in range(r.choice([0, 0, 1, 2, 3, 5, 12]))]
    msgs = [Msg(r.choice([0x100, 0x101, 0x102, 0x201, 0x202, 0x20A]), r.choice([0x41, 0x1B, 0x20, 0x57, 1, 120 << 16]),
                r.getrandbits(25), r.getrandbits(32)) for _ in range(r.choice([0, 0, 0, 1, 3]))]
    packets = {"NET_GetLoopPacket": r.choice([0, 0, 1, 2]), "NET_GetDeferredClientPacket": r.choice([0, 0, 1, 3]),
               "NET_GetClientPacket": r.choice([0, 0, 1, 2])}
    sv_running = r.choice([0, 0, 1])
    catchers = r.choice([0, 0x10, 1])

    def setup(w):
        Messages(msgs).install(w.m)
        state.clear()
        state.update(packets)
        q = va("eventQue")
        for i, (kind, text, data) in enumerate(events):
            ptr = 0
            if text is not None:
                ptr = TEXT + 0x40 * i
                w.m.mu.mem_write(ptr, text + b"\0")
            w.write(q + EV_SIZE * ((tail + i) & 0xFF), data + struct.pack("<Q", ptr))
        w.write(va("eventHead"), struct.pack("<i", tail + len(events)))
        w.write(va("eventTail"), struct.pack("<i", tail))
        dvar = w.alloc(bytes(0x60))
        w.write(dvar + 0x10, bytes([sv_running]))
        w.u64(va("com_sv_running"), dvar)
        w.u32(va("clientUIActives") + 4, catchers)
        w.write(va("s_wmv") + 0xC, bytes([0, 1]))
    return setup


FAKES = {
    "?CL_KeyEvent@@YAXW4LocalClientNum_t@@HHI@Z": _log("CL_KeyEvent", "iiii"),
    "?CL_CharEvent@@YAXW4LocalClientNum_t@@H@Z": _log("CL_CharEvent", "ii"),
    "?Cbuf_AddText@@YAXW4LocalClientNum_t@@PEBD@Z": _log("Cbuf_AddText", "is"),
    "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _log("Com_Error", "isi"),
    "?CL_PacketEvent@@YA_NW4LocalClientNum_t@@Unetadr_s@@PEAUmsg_t@@H@Z": _packet_event,
    "?NET_GetLoopPacket@@YAHW4netsrc_t@@PEAUnetadr_s@@PEAUmsg_t@@@Z":
        _source("NET_GetLoopPacket", UC_X86_REG_RDX, UC_X86_REG_R8),
    "?NET_GetDeferredClientPacket@@YA_NPEAUnetadr_s@@PEAUmsg_t@@@Z":
        _source("NET_GetDeferredClientPacket", UC_X86_REG_RCX, UC_X86_REG_RDX),
    "?NET_GetClientPacket@@YAHPEAUnetadr_s@@PEAUmsg_t@@@Z": _source("NET_GetClientPacket", UC_X86_REG_RCX,
                                                                    UC_X86_REG_RDX),
    "??0LargeLocal@@QEAA@_K@Z": _log("LargeLocal::LargeLocal", "pq", lambda mu: mu.reg_read(UC_X86_REG_RCX)),
    "?GetBuf@LargeLocal@@QEAAPEAXXZ": _log("LargeLocal::GetBuf", "p", LARGE_BUF),
    "??1LargeLocal@@QEAA@XZ": _log("LargeLocal::~LargeLocal", "p"),
    "?R_CheckLostDevice@@YA_NXZ": lambda mu: 0,
}
OBSERVE = {
    "?Sys_EnterCriticalSection@@YAXW4CriticalSection@@@Z": "i",
    "?Sys_LeaveCriticalSection@@YAXW4CriticalSection@@@Z": "i",
    "?MSG_Init@@YAXPEAUmsg_t@@PEAEH@Z": "qqi",
    "?Sys_Milliseconds@@YAHXZ": "",
}


def _inputs(seed, n):
    r = random.Random(seed)
    return [{"args": [], "setup": _state(r)} for _ in range(n)]


CASES = [
    {"symbol": "?Com_EventLoop@@YAXXZ", "build": STORE, "ret": "void", "fakes": FAKES,
     "observe": {k: v for k, v in OBSERVE.items() if k != "?MSG_Init@@YAXPEAUmsg_t@@PEAEH@Z"},
     "inputs": _inputs(4367, 800)},
]
