"""Differential cases for win32/win_net.cpp and universal/com_net.cpp against the Store build.

No case touches a network: every Winsock call goes to the model in winsock.py, which logs it with its arguments
(bytes sent, sockaddrs, lengths), so the original and the reconstruction must make the same calls in the same
order. Random state per input: the network dvars (values and modified flags, from Dvar_Register* fakes that hand
back preset dvars), the sockets and flags in win_net.cpp's statics, the Winsock results (WSAStartup, socket handles
or INVALID_SOCKET, ioctlsocket/setsockopt/bind/connect failures, WSAGetLastError codes), a scripted SOCKS5 server
(method, authentication and UDP ASSOCIATE replies, short and malformed ones included), incoming datagrams with
their source addresses (from the SOCKS relay or not, good and bad checksums, 0..maxsize bytes), gethostname and
gethostbyname results. DemonWare (dwRecvFrom, dwSendTo, dwNetadrToCommonAddr and the unnamed dw helpers) and
Com_Error are faked and record what they are given.

The top of the stack is filled with 0xCC before each call: NET_OpenSocks sends an uninitialized byte (the second
method byte when authenticating), which then reads the same in both runs.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

from harness import HEAP, STACK, STACK_SIZE
from syms import static, va
from winsock import INVALID_SOCKET, SOCKET_ERROR, WSAECONNREFUSED, WSAECONNRESET, WSAEWOULDBLOCK, Winsock, sockaddr_in

STORE = "iw6mp64_MSStore_ship"
M = {}  # the machine and per-run fake state of the current call


def _rec(*entry):
    M["m"].observed.append(entry)


def _i32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _read(mu, a, n):
    return bytes(mu.mem_read(a, n))


def _write(a, data):
    M["m"]._emulated_write(a, data)


def _checksum(data: bytes) -> int:
    """Sys_Checksum: big-endian 16-bit words, an odd last byte added unshifted, folded, inverted."""
    s = 0
    n = len(data)
    i = 0
    while n - i > 1:
        s += (data[i] << 8) | data[i + 1]
        i += 2
    if n - i > 0:
        s += data[i]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


# --- dvars ---------------------------------------------------------------------------------------------------------

DVAR_NAMES = ("net_noudp", "net_socksEnabled", "net_socksServer", "net_socksPort", "net_socksUsername",
              "net_socksPassword", "net_ip", "net_port")
DVAR_GLOBALS = {"net_noudp": "net_noudp", "net_socksEnabled": "net_socksEnabled", "net_socksServer": "net_socksServer",
                "net_socksPort": "net_socksPort", "net_socksUsername": "net_socksUsername",
                "net_socksPassword": "net_socksPassword", "net_ip": "ip", "net_port": "port"}


def _dvar(w, value, modified=False):
    """A scratch dvar_t: value is an int (bool/int dvars), bytes (a string) or None (a null string pointer)."""
    if isinstance(value, (bytes, bytearray)):
        current = w.cstr(bytes(value))
    elif value is None:
        current = 0
    else:
        current = value & 0xFFFFFFFF
    return w.alloc(bytes(0xD) + bytes([modified]) + bytes(2) + struct.pack("<Q", current) + bytes(0x48))


def _register(mu):
    name = M["m"].read_cstr(mu.reg_read(UC_X86_REG_RCX)).decode()
    return M["dvars"][name]


def _set_int(mu):
    M["m"].mu.mem_write(mu.reg_read(UC_X86_REG_RCX) + 0x10, struct.pack("<i", _i32(mu.reg_read(UC_X86_REG_RDX))))


# --- DemonWare and the rest of the engine ----------------------------------------------------------------------------

def _dw_recv_from(mu):
    frm, data, size = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF
    _rec("dwRecvFrom", frm, data, size)
    ret, payload, adr = M["dw_recv"].pop(0) if M["dw_recv"] else (-2, b"", None)
    if payload:
        _write(data, payload[:size])
    if adr:
        _write(frm, adr)
    return ret & 0xFFFFFFFF


def _dw_send_to(mu):
    n, data, to = mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    _rec("dwSendTo", n, _read(mu, data, min(n, 0x1000)), _read(mu, to, 16))
    return M["dw_send"] & 0xFFFFFFFF


def _common_addr(adr: bytes) -> bytes:
    return (adr * 3)[:37]


def _dw_netadr_to_common(mu):
    adr, buf, size, sec = (mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX),
                           mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_R9))
    a = _read(mu, adr, 16)
    _rec("dwNetadrToCommonAddr", a, size, sec)
    ok = M["dw_common"]
    if ok:
        _write(buf, _common_addr(a)[:size])
    return ok


def _com_error(mu):
    _rec("Com_Error", mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, M["m"].read_cstr(mu.reg_read(UC_X86_REG_RDX)),
         mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF)


def _aa0b0(mu):
    adr = mu.reg_read(UC_X86_REG_RCX)
    _rec("sub_1405AA0B0", _read(mu, adr, 16))
    _write(adr + 4, M["aa0b0_ip"])
    _write(adr + 8, M["aa0b0_port"])
    return M["aa0b0"]


def _a8980(mu):
    _rec("sub_1405A8980", mu.reg_read(UC_X86_REG_RCX))
    return M["a8980"] & 0xFFFFFFFF


def _a8ad0(mu):
    _rec("sub_1405A8AD0")
    return M["a8ad0"]


def _a8300(mu):
    out, p2, p3 = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    _rec("sub_1405A8300", p2, p3)
    _write(out, M["a8300_adr"])
    return M["a8300"]


FAKES = {
    "?Dvar_RegisterBool@@YAPEBUdvar_t@@PEBD_NI0@Z": _register,
    "?Dvar_RegisterInt@@YAPEBUdvar_t@@PEBDHHHI0@Z": _register,
    "?Dvar_RegisterString@@YAPEBUdvar_t@@PEBD0I0@Z": _register,
    "?Dvar_SetInt@@YAXPEBUdvar_t@@H@Z": _set_int,
    "?dwRecvFrom@@YAHQEAUnetadr_s@@QEAXI@Z": _dw_recv_from,
    "?dwSendTo@@YAHIPEBXUnetadr_s@@@Z": _dw_send_to,
    "?dwNetadrToCommonAddr@@YA_NUnetadr_s@@PEAEIQEAVbdSecurityID@@@Z": _dw_netadr_to_common,
    "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _com_error,
    "?sub_1405AA0B0@@YA_NPEAUnetadr_s@@@Z": _aa0b0,
    "?sub_1405A8980@@YAHPEBUnetadr_s@@@Z": _a8980,
    "?sub_1405A8AD0@@YAIXZ": _a8ad0,
    "?sub_1405A8300@@YA_NPEAUnetadr_s@@PEBE1@Z": _a8300,
}
OBSERVE = {
    "?Dvar_RegisterBool@@YAPEBUdvar_t@@PEBD_NI0@Z": "sbis",
    "?Dvar_RegisterInt@@YAPEBUdvar_t@@PEBDHHHI0@Z": "siii",
    "?Dvar_RegisterString@@YAPEBUdvar_t@@PEBD0I0@Z": "ssis",
    "?Dvar_SetInt@@YAXPEBUdvar_t@@H@Z": "qi",
    "?I_stricmp@@YAHPEBD0@Z": "ss",
    "?I_irand@@YAHHH@Z": "ii",
    # reconstructed callees, watched at both copies
    "?NET_OpenSocks@@YAXH@Z": "i",
    "?Sys_StringToSockaddr@@YAHPEBDPEAUsockaddr@@@Z": "s",
    "?SockadrToNetadr@@YAXPEAUsockaddr@@PEAUnetadr_s@@@Z": "",
    "?NetadrToSockadr@@YAXPEAUnetadr_s@@PEAUsockaddr@@@Z": "",
    "?Sys_Checksum@@YAGPEAEH@Z": "qi",
    "?Sys_ChecksumCopy@@YAGPEAE0H@Z": "",
}


# --- per-input state -------------------------------------------------------------------------------------------------

HANDLES = [0x1F0, 0x2A4, 0x3B8, 0x10, 1]
NAMES = [b"", b"localhost", b"LOCALHOST", b"192.168.1.20", b"10.0.0.7", b"socks.example", b"gamepc", b"nowhere",
         b"0bad", b"1.2.3"]


def _host_table(r):
    hosts = {}
    for name in (b"socks.example", b"gamepc", b"nowhere", b"myhost"):
        if r.random() < 0.8:
            n = r.choice([0, 1, 1, 2, 3, 5, 16, 17, 20]) if name == b"gamepc" else r.choice([1, 1, 2, 3])
            hosts[name] = (r.choice([2, 2, 2, 2, 23]), [bytes(r.getrandbits(8) for _ in range(4)) for _ in range(n)])
    return hosts


def _random_socket(r):
    return r.choice([0, 0, INVALID_SOCKET, r.choice(HANDLES)])


class State:
    """Everything one input sets up; setup() applies it identically before each of the two runs."""

    def __init__(self, r, winsock=None, dvars=None, statics=None, extra=None):
        self.winsock = winsock or Winsock()
        self.dvars = dvars or {}
        self.statics = statics or {}
        self.extra = extra or {}
        self.holdrand = r.getrandbits(32)

    def setup(self, w):
        M.clear()
        M["m"] = w.m
        w.m.mu.mem_write(STACK + STACK_SIZE - 0x10000, b"\xCC" * 0x10000)
        M["dvars"] = {name: _dvar(w, *spec) for name, spec in self.dvars.items()}
        for name, value in self.statics.items():
            if name in ("socksRelayAddr", "localIP"):
                w.write(va(name), value)
            elif isinstance(value, tuple):  # a global dvar pointer: (dvar value, modified) or None for a null pointer
                w.u64(va(name), _dvar(w, *value))
            elif value is None:
                w.u64(va(name), 0)
            elif name in ("ip_socket", "socks_socket", "unk_149D62370", "ip", "port") or name.startswith("net_"):
                w.u64(va(name), value)
            else:
                w.u32(va(name), value)
        w.u32(static("universal/com_math.cpp", "holdrand"), self.holdrand)  # I_irand's seed
        for k, v in self.extra.items():
            M[k] = list(v) if isinstance(v, list) else v
        M.setdefault("dw_recv", [])
        M.setdefault("dw_send", 0)
        M.setdefault("dw_common", 1)
        self.winsock.copy().install(w.m)


def _dvar_specs(r, socks=None):
    """Values for every network dvar (the fakes hand these back from Dvar_Register*)."""
    user = bytes(r.choice(b"abcdefgh") for _ in range(r.choice([0, 0, 1, 5, 12, 30])))
    password = bytes(r.choice(b"0123456789") for _ in range(r.choice([0, 0, 1, 8, 30])))
    if socks is not None:
        user, password = socks
    return {
        "net_noudp": (r.choice([0, 0, 0, 1]), r.random() < 0.3),
        "net_socksEnabled": (r.choice([0, 1]), r.random() < 0.3),
        "net_socksServer": (r.choice([b"socks.example", b"socks.example", b"nowhere", b""]), r.random() < 0.3),
        "net_socksPort": (r.choice([1080, 0, 65535, 9050]), r.random() < 0.3),
        "net_socksUsername": (user, r.random() < 0.3),
        "net_socksPassword": (password, r.random() < 0.3),
        "net_ip": (r.choice(NAMES + [None]), r.random() < 0.3),
        "net_port": (r.choice([27016, 27016, 0, 65535, -1, 28960, r.randint(0, 65535)]), r.random() < 0.3),
    }


def _global_dvars(r, specs):
    """The dvar pointers in the globals before the call: null, or a dvar (with a modified flag)."""
    out = {}
    for name, glob in DVAR_GLOBALS.items():
        out[glob] = None if r.random() < 0.25 else (specs[name][0], r.random() < 0.4)
    return out


def _socks_replies(r, ws, authenticate):
    """A SOCKS5 server's replies: method selection, authentication, UDP ASSOCIATE (each sometimes bad)."""
    method = r.choice([0, 0, 2, 2, 1, 0xFF])
    first = r.choice([bytes([5, method])] * 6 + [bytes([4, method]), bytes([5]), bytes([5, method, 0]), SOCKET_ERROR, 0])
    ws.recv.append(first)
    if r.random() < 0.15:
        ws.send.append(SOCKET_ERROR)
    if isinstance(first, bytes) and first[:1] == b"\x05" and len(first) == 2 and method == 2:
        ws.recv.append(r.choice([b"\x01\x00"] * 5 + [b"\x01\x01", b"\x05\x00", b"\x01", SOCKET_ERROR]))
        if r.random() < 0.15:
            ws.send.append(SOCKET_ERROR)
    relay = bytes(r.getrandbits(8) for _ in range(4)) + struct.pack(">H", r.randint(1, 65535))
    ws.recv.append(r.choice([
        b"\x05\x00\x00\x01" + relay, b"\x05\x00\x00\x01" + relay, b"\x05\x00\x00\x01" + relay + b"extra",
        b"\x05\x00", b"\x05\x00\x00", b"\x05\x00\x00\x01\x0a",  # short: the rest of the request stays in buf
        b"\x05\x01\x00\x01" + relay, b"\x05\x00\x00\x03" + relay, b"\x04\x00\x00\x01" + relay, b"\x05",
        SOCKET_ERROR]))
    if r.random() < 0.15:
        ws.send.append(SOCKET_ERROR)  # the UDP ASSOCIATE send (or an earlier one): its failure is ignored


def _winsock(r, socks_attempts=1):
    ws = Winsock(startup=r.choice([0, 0, 0, 10091]), hosts=_host_table(r),
                 hostname=r.choice([b"gamepc", b"gamepc", b"nowhere", None]),
                 last_error=r.choice([WSAEWOULDBLOCK, WSAECONNREFUSED, WSAECONNRESET]))
    ws.errors = [r.choice([WSAEWOULDBLOCK, WSAECONNREFUSED, WSAECONNRESET, 10047]) for _ in range(4)]
    for _ in range(12):
        ws.sockets.append(r.choice([INVALID_SOCKET] + [None] * 4 + HANDLES))
    ws.sockets = [s for s in ws.sockets if s is not None] if r.random() < 0.5 else []
    ws.ioctl = [r.choice([0, 0, 0, SOCKET_ERROR]) for _ in range(10)]
    ws.setsockopt = [r.choice([0, 0, 0, SOCKET_ERROR]) for _ in range(10)]
    ws.bind = [r.choice([0, 0, SOCKET_ERROR]) for _ in range(10)]
    ws.connect = [r.choice([0, 0, 0, SOCKET_ERROR])]
    for _ in range(socks_attempts):
        _socks_replies(r, ws, True)
    return ws


# --- inputs per function ---------------------------------------------------------------------------------------------

def _net_state(r, socks_only=False):
    specs = _dvar_specs(r)
    statics = _global_dvars(r, specs)
    statics.update({
        "ip_socket": _random_socket(r), "socks_socket": _random_socket(r), "networkingEnabled": r.choice([0, 1]),
        "usingSocks": r.choice([0, 1]), "winsockInitialized": r.choice([0, 1]), "numIP": r.randint(0, 16),
        "localIP": bytes(r.getrandbits(8) for _ in range(64)),
        "socksRelayAddr": sockaddr_in(bytes(r.getrandbits(8) for _ in range(4)), r.randint(0, 65535),
                                      bytes(r.getrandbits(8) for _ in range(8)) if r.random() < 0.3 else bytes(8)),
    })
    return State(r, winsock=_winsock(r), dvars=specs, statics=statics)


def _inputs_net(seed, n, args=lambda r: []):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        st = _net_state(r)
        out.append({"args": args(r), "setup": st.setup})
    return out


def _datagram(r, relay, maxsize, socks):
    """recvfrom's next datagram: (data, source sockaddr), or an error."""
    if r.random() < 0.2:
        return SOCKET_ERROR
    payload = bytes(r.getrandbits(8) for _ in range(r.choice([0, 1, 2, 3, 7, 30, 100, maxsize, maxsize + 5])))
    from_relay = r.random() < (0.6 if socks else 0.25)  # without SOCKS, a datagram that merely looks like one
    if from_relay and r.random() < 0.8:
        header = r.choice([b"\0\0\0\x01", b"\0\0\0\x01", b"\0\0\0\x01", b"\0\0\x01\x01", b"\0\0\0\x03"])
        payload = header + bytes(r.getrandbits(8) for _ in range(6)) + payload
    size = r.choice([len(payload), len(payload), len(payload), 0, 1, 2, 9, 10, 11, maxsize - 2])
    body = payload[:max(size - 2, 0)]
    if size >= 2:
        c = _checksum(body)
        if r.random() < 0.2:
            c ^= 1 << r.randint(0, 15)
        data = body + struct.pack(">H", c)
    else:
        data = payload[:size]
    if from_relay:
        # recvfrom may fill sin_zero; Sys_GetPacket clears it on ip_socket before comparing with the relay address
        source = relay[:8] + (bytes(r.getrandbits(8) for _ in range(8)) if r.random() < 0.5 else bytes(8))
    else:
        source = sockaddr_in(bytes(r.getrandbits(8) for _ in range(4)), r.randint(0, 65535),
                             bytes(r.getrandbits(8) for _ in range(8)))
        if r.random() < 0.1:
            source = struct.pack("<H", 23) + source[2:]
    return data, source


MSG_DATA = 0x50  # data buffer offset inside the msg_t argument (after 0x38 of msg_t and 0x18 guard bytes)


def _get_packet_inputs(seed, n):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        maxsize = r.choice([0x20, 0x40, 0x100, 0x200])
        relay = sockaddr_in(bytes(r.getrandbits(8) for _ in range(4)), r.randint(0, 65535))
        using = r.choice([0, 1, 1])
        ip_sock = r.choice([0, 0x1F0, 0x1F0, 0x1F0])
        other = r.choice([0, 0, 0, 0x2A4, 0x1F0])
        ws = Winsock(last_error=r.choice([WSAEWOULDBLOCK, WSAECONNREFUSED, WSAECONNRESET]))
        ws.recvfrom = [_datagram(r, relay, maxsize, using) for _ in range(2)]
        ws.errors = [r.choice([WSAEWOULDBLOCK, WSAECONNREFUSED, WSAECONNRESET]) for _ in range(2)]
        dw = []
        for _ in range(2):
            ret = r.choice([-2, -9, -1, -5, 0, 1, 2, 3, 12, maxsize, maxsize - 1])
            body = bytes(r.getrandbits(8) for _ in range(max(ret - 2, 0)))
            c = _checksum(body) ^ (0 if r.random() < 0.8 else 0x100)
            payload = body + struct.pack(">H", c) if ret >= 2 else bytes(r.getrandbits(8) for _ in range(max(ret, 0)))
            dw.append((ret, payload, bytes(r.getrandbits(8) for _ in range(16)) if r.random() < 0.7 else None))
        st = State(r, winsock=ws, statics={"ip_socket": ip_sock, "unk_149D62370": other, "usingSocks": using,
                                           "socksRelayAddr": relay}, extra={"dw_recv": dw})
        msg = bytearray(MSG_DATA + maxsize + 8)
        struct.pack_into("<iiQQiiiiiiii", msg, 0, 0, 0, HEAP + 0x1000 + MSG_DATA, 0, maxsize,
                         r.randint(-5, 50), 0, r.randint(-5, 50), 0, 0, 0, 0)
        msg[0x38:MSG_DATA] = bytes(r.choice([0, 0xFF]) for _ in range(MSG_DATA - 0x38))  # data[-2], data[-1]
        msg[MSG_DATA:] = bytes(r.getrandbits(8) for _ in range(maxsize + 8))
        adr = bytes(r.getrandbits(8) for _ in range(16))
        out.append({"args": [adr, bytes(msg)], "setup": st.setup})
    return out


def _send_packet_inputs(seed, n):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        length = r.choice([0, 1, 2, 3, 17, 100, 1200, 1278, r.randint(0, 1278)])
        data = bytes(r.getrandbits(8) for _ in range(max(length, 1)))
        to = struct.pack("<I", r.choice([3, 3, 4, 4, 4, 0, 1, 2, 5])) + bytes(r.getrandbits(8) for _ in range(12))
        ws = Winsock()
        ws.sendto = [r.choice([None, None, SOCKET_ERROR, 0, 5])]
        st = State(r, winsock=ws, statics={"ip_socket": r.choice([0, 0x1F0, 0x1F0])},
                   extra={"dw_send": r.choice([0, 5, length + 2, -1, -9])})
        out.append({"args": [length, data, to], "setup": st.setup})
    return out


def _socks_inputs(seed, n):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        st = _net_state(r)
        auth = r.random() < 0.5
        user = bytes(r.choice(b"abcdefgh") for _ in range(r.choice([0, 1, 5, 12, 30] if auth else [0])))
        password = bytes(r.choice(b"0123456789") for _ in range(r.choice([0, 1, 8, 30] if auth else [0])))
        if auth and not user and not password:
            user = b"u"
        st.dvars["net_socksUsername"] = (user, False)
        st.dvars["net_socksPassword"] = (password, False)
        for name in ("net_socksServer", "net_socksPort", "net_socksUsername", "net_socksPassword"):
            st.statics[name] = st.dvars[name]
        ws = st.winsock
        ws.sockets = [r.choice([INVALID_SOCKET] + HANDLES * 3)]
        ws.recv, ws.send = [], []
        _socks_replies(r, ws, auth)
        if r.random() < 0.3:  # fail one chosen send: the method, authentication or UDP ASSOCIATE request
            ws.send = [None] * r.choice([0, 1, 1, 2, 2]) + [SOCKET_ERROR]
        out.append({"args": [r.choice([27016, 0, 65535, 28961, -1, 70000])], "setup": st.setup})
    return out


def _string_inputs(seed, n, out_size):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        name = r.choice(NAMES + [b"8.8.8.8", b"255.255.255.255", b"9", b"myhost"])
        ws = Winsock(hosts=_host_table(r))
        if r.random() < 0.1 and name in ws.hosts:
            ws.hosts[name] = (2, [])  # no addresses: the original indexes h_addr_list[0], a null pointer
        st = State(r, winsock=ws)
        out.append({"args": [name + b"\0", bytes(r.getrandbits(8) for _ in range(out_size))], "setup": st.setup})
    return out


def _plain_inputs(seed, n, args, extra=lambda r: {}, statics=lambda r: {}):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        st = State(r, statics=statics(r), extra=extra(r))
        out.append({"args": args(r), "setup": st.setup})
    return out


def _rbytes(r, n):
    return bytes(r.getrandbits(8) for _ in range(n))


def _netadr(r):
    return struct.pack("<I", r.choice([0, 1, 2, 3, 4, 4, 4, 5])) + _rbytes(r, 12)


def _in_addr(r):
    return r.choice([b"\x7f\0\0\x01", b"\x7f\0\0\x01", _rbytes(r, 4), b"\0\0\0\0"])


def case(symbol, inputs, ret="void"):
    return {"symbol": symbol, "build": STORE, "ret": ret, "fakes": FAKES, "observe": OBSERVE, "inputs": inputs}


def _snprintf(mu):
    """_snprintf for the "%u.%u.%u.%u" call only: the PS4 server's static CRT copy faults uninitialized."""
    buf, n, fmt = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    rsp = mu.reg_read(UC_X86_REG_RSP)
    args = [mu.reg_read(UC_X86_REG_R9) & 0xFFFFFFFF] + [
        struct.unpack("<I", _read(mu, rsp + 0x28 + 8 * i, 4))[0] for i in range(3)]
    f = M["m"].read_cstr(fmt)
    _rec("_snprintf", n, f, *args)
    out = (f.decode() % tuple(args)).encode() if f == b"%u.%u.%u.%u" else b""
    _write(buf, (out + b"\0")[:n])
    return len(out)


def shared_case(symbol, inputs, ret="void", fakes=None):
    """universal/com_net.cpp: the same file in the Store build and the reference (PS4 server, a Windows exe that
    imports the same Winsock): the case runs against every build that has the function."""
    return {"symbol": symbol, "ret": ret, "fakes": fakes or {}, "observe": {"?I_irand@@YAHHH@Z": "ii"},
            "inputs": inputs}


def _xnaddr_args(r):
    adr = _netadr(r)
    x = _common_addr(adr) if r.random() < 0.5 else _rbytes(r, 37)
    if r.random() < 0.2:
        x = x[:36] + bytes([x[36] ^ 1])
    return [x, adr]


CASES = [
    # universal/com_net.cpp
    shared_case("?NET_CompareInAddrs@@YAHPEBUin_addr@@0@Z",
         _plain_inputs(219, 300, lambda r: (lambda a: [a, a if r.random() < 0.4 else _in_addr(r)])(_in_addr(r))),
         "int"),
    shared_case("?sub_140535CF0@@YAHPEBUin_addr@@@Z", _plain_inputs(220, 200, lambda r: [_in_addr(r)]), "int"),
    shared_case("?NET_InAddrSetLoopback@@YAXPEAUin_addr@@@Z", _plain_inputs(191, 50, lambda r: [_rbytes(r, 8)])),
    shared_case("?NET_InAddrToIpAddr@@YAXPEBUin_addr@@QEAE@Z", _plain_inputs(205, 100, lambda r: [_rbytes(r, 4), _rbytes(r, 8)])),
    shared_case("?NET_InAddrToString@@YAXPEBUin_addr@@QEAD@Z", _plain_inputs(143, 200, lambda r: [_in_addr(r), _rbytes(r, 24)]),
                fakes={"_snprintf": _snprintf}),
    shared_case("?NetadrToSockadr@@YAXPEAUnetadr_s@@PEAUsockaddr@@@Z",
         _plain_inputs(100, 300, lambda r: [_netadr(r), _rbytes(r, 16)])),
    shared_case("?SockadrToNetadr@@YAXPEAUsockaddr@@PEAUnetadr_s@@@Z",
         _plain_inputs(111, 300, lambda r: [struct.pack("<H", r.choice([2, 2, 0, 23])) + _rbytes(r, 14), _rbytes(r, 16)])),
    shared_case("?Sys_Checksum@@YAGPEAEH@Z",
         _plain_inputs(484, 400, lambda r: [_rbytes(r, 0x600), r.choice([-3, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                                                                           r.randint(0, 0x5FF), 0x5FF])]), "short"),
    shared_case("?Sys_ChecksumCopy@@YAGPEAE0H@Z",
         _plain_inputs(514, 400, lambda r: [_rbytes(r, 0x600), _rbytes(r, 0x600),
                                            r.choice([-2, 0, 1, 2, 3, 4, 5, r.randint(0, 0x5FF), 0x5FF])]), "short"),
    shared_case("?Sys_StringToAdr@@YAHPEBDPEAUnetadr_s@@@Z", _string_inputs(468, 400, 16), "int"),
    shared_case("?Sys_StringToSockaddr@@YAHPEBDPEAUsockaddr@@@Z", _string_inputs(393, 400, 16), "int"),
    # win32/win_net.cpp
    case("?sub_14054EF80@@YA_NPEBIGPEAUnetadr_s@@@Z",
         _plain_inputs(1, 200, lambda r: [_rbytes(r, 4), r.getrandbits(16), _rbytes(r, 16)],
                       extra=lambda r: {"aa0b0": r.choice([0, 1]), "aa0b0_ip": _rbytes(r, 4),
                                        "aa0b0_port": _rbytes(r, 2)}), "char"),
    case("?sub_14054EFA0@@YAXPEBUnetadr_s@@PEAI@Z", _plain_inputs(2, 100, lambda r: [_netadr(r), _rbytes(r, 8)])),
    case("?sub_14054EFB0@@YAHPEBUnetadr_s@@@Z",
         _plain_inputs(3, 100, lambda r: [_netadr(r)], extra=lambda r: {"a8980": r.choice([0, 1, 1, 2, 3, -1])}), "int"),
    case("?NET_GetDvars@@YAHXZ", _inputs_net(1220, 300), "int"),
    case("?NET_GetXnAddrForNetAddr@@YAHPEBUnetadr_s@@PEAUXNADDR@@PEAVbdSecurityID@@@Z",
         _plain_inputs(2591, 100, lambda r: [_netadr(r), _rbytes(r, 40), r.choice([0, 0x1234, r.getrandbits(64)])],
                       extra=lambda r: {"dw_common": r.choice([0, 1, 1])}), "int"),
    case("?NET_Init@@YAXXZ", _inputs_net(1549, 1500)),
    case("?sub_14054F2E0@@YA_NPEBI@Z",
         _plain_inputs(4, 100, lambda r: (lambda h: [struct.pack("<I", h)])(r.choice([0, 7, 0xFFFFFFFF])),
                       extra=lambda r: {"a8ad0": r.choice([0, 7, 0xFFFFFFFF])}), "char"),
    case("?NET_OpenIP@@YAXXZ", _inputs_net(1165, 1500)),
    case("?NET_OpenSocks@@YAXH@Z", _socks_inputs(1000, 1500)),
    case("?sub_14054F8D0@@YAHXZ", _plain_inputs(5, 20, lambda r: []), "int"),
    case("?sub_14054F8E0@@YA_NPEBUXNADDR@@PEBUnetadr_s@@@Z",
         _plain_inputs(6, 300, _xnaddr_args, extra=lambda r: {"dw_common": r.choice([0, 1, 1, 1])}), "char"),
    case("?Sys_GetLocalIP@@YA?AUin_addr@@H@Z",
         _plain_inputs(905, 100, lambda r: [r.randint(0, 15)], statics=lambda r: {"localIP": _rbytes(r, 64)}), "int"),
    case("?sub_14054F950@@YAHXZ",
         _plain_inputs(7, 50, lambda r: [], statics=lambda r: {"numIP": r.randint(-1, 17)}), "int"),
    case("?Sys_GetPacket@@YAHPEAUnetadr_s@@PEAUmsg_t@@@Z", _get_packet_inputs(452, 3000), "int"),
    case("?Sys_SendPacket@@YA_NHPEBXUnetadr_s@@@Z", _send_packet_inputs(654, 600), "char"),
    case("?sub_14054FC70@@YA_NPEBEPEAIPEAG@Z",
         _plain_inputs(8, 300, lambda r: [_rbytes(r, 48), _rbytes(r, 4), _rbytes(r, 2)],
                       extra=lambda r: (lambda h: {"a8300": r.choice([0, 1]), "a8ad0": r.choice([h, h, 9]),
                                                   "a8300_adr": struct.pack("<I", r.choice([2, 4, 4, 1])) + _rbytes(r, 8)
                                                   + struct.pack("<I", h)})(r.choice([3, 9, 0xFFFFFFFF]))), "char"),
]
