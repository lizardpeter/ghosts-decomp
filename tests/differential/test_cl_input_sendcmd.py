"""Differential cases for building user commands and sending them (client_mp/cl_input.cpp) against the Store build.

Random client state: connection state, the client mode at unk_143E96824, cmdNumber and all 128 usercmds, the
out-packet ring (packetBackupMask, p_cmdNumber/p_realtime), snap.valid/messageNum, the predicted origin and vehicle
state, the connection's sequences, reliable and server commands (sometimes long enough to overflow the message),
the netchan's outgoing sequence, address type and unsent fragments, cls.realtime, cl_maxpackets and cl_packetdup.

Every engine call is faked and recorded with what it was given: CL_CreateCmd (returns a random usercmd through its
hidden result pointer), the clViewangles tamper check, MSG_SetDefaultUserCmd, IN_Frame, CL_SyncGpu. The msg.cpp
writers are faked by a model that records each value written (strings and usercmds by content, since the message
and nullcmd live on the stack) and appends bytes to msg->data, so the 9-byte header copy, the compressor's input and
the final packet handed to CL_Netchan_Transmit are all compared.
"""
import random
import struct
import zlib

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

from syms import va

STORE = "iw6mp64_MSStore_ship"

# clientActive_t (Store layout, include/client_mp/client_mp.h)
CL_SNAP_VALID, CL_SNAP_MESSAGENUM, CL_SERVERID = 0x347C, 0x3488, 0x34E0
CL_ORIGIN, CL_VEHSTATE, CL_PREDTIME, CL_VIEWANGLES = 0x3580, 0x3598, 0x360C, 0x3610
CL_CMDS, CL_CMDNUMBER, CL_BACKUPMASK, CL_OUTPACKETS = 0x3628, 0x5428, 0xE034, 0xE044
CMD_SIZE = 0x3C
# clientConnection_t
CLC_LASTSEND, CLC_CHECKSUMFEED, CLC_RELIABLESEQ, CLC_RELIABLEACK = 0x1C, 0x128, 0x12C, 0x130
CLC_RELIABLECMDS, CLC_SERVERMSGSEQ, CLC_SERVERCMDSEQ, CLC_SERVERCMDS = 0x134, 0x20134, 0x20138, 0x20140
CLC_NETCHAN = 0x40148
NC_REMOTETYPE, NC_UNSENT = 0x10, 0x3C

M = {}  # the machine of the current call, for fakes that record


def _rec(*entry):
    M["m"].observed.append(entry)


def _u32(mu, a):
    return struct.unpack("<I", bytes(mu.mem_read(a, 4)))[0]


def _i32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _cstr(mu, a, limit=1100):
    return M["m"].read_cstr(a, limit)


def _global(a):
    """An address in the original's image is the same in both runs; anything else (the stack) is not."""
    return a if 0x140000000 <= a < 0x150000000 else "local"


# --- the msg.cpp model -------------------------------------------------------------------------------------------

def _append(mu, msg, payload):
    data = struct.unpack("<Q", bytes(mu.mem_read(msg + 8, 8)))[0]
    maxsize, cursize = struct.unpack("<ii", bytes(mu.mem_read(msg + 0x18, 8)))
    n = max(0, min(len(payload), maxsize - cursize))
    if n:
        mu.mem_write(data + cursize, payload[:n])
    mu.mem_write(msg + 0x1C, struct.pack("<i", cursize + len(payload)))


def _msg_init(mu):
    msg, data, length = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), _i32(mu.reg_read(UC_X86_REG_R8))
    mu.mem_write(msg, bytes(0x38))
    mu.mem_write(msg + 8, struct.pack("<Q", data))
    mu.mem_write(msg + 0x18, struct.pack("<i", length))
    M["msg"] = msg
    _rec("MSG_Init", length, _global(data))


def _writer(name, payload_of):
    def fake(mu):
        msg = mu.reg_read(UC_X86_REG_RCX)
        payload, record = payload_of(mu)
        _rec(name, msg == M.get("msg"), *record)
        _append(mu, msg, payload)
    return fake


def _byte(mu):
    v = _i32(mu.reg_read(UC_X86_REG_RDX))
    return bytes([v & 0xFF]), (v,)


def _long(mu):
    v = _i32(mu.reg_read(UC_X86_REG_RDX))
    return struct.pack("<i", v), (v,)


def _bits(mu):
    v, bits = _i32(mu.reg_read(UC_X86_REG_RDX)), _i32(mu.reg_read(UC_X86_REG_R8))
    return bytes([0xB0 | (v & 0xF)]), (v, bits)


def _string(mu):
    s = _cstr(mu, mu.reg_read(UC_X86_REG_RDX))
    return s + b"\0", (s,)


def _delta_usercmd(mu):
    key, frm, to = _i32(mu.reg_read(UC_X86_REG_RDX)), mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9)
    record = (key, _global(frm), bytes(mu.mem_read(frm, CMD_SIZE)), _global(to), bytes(mu.mem_read(to, CMD_SIZE)))
    return bytes([0xD0, key & 0xFF]), record


def _compress(mu):
    train, frm, to, size = (mu.reg_read(UC_X86_REG_RCX) & 0xFF, mu.reg_read(UC_X86_REG_RDX),
                            mu.reg_read(UC_X86_REG_R8), _i32(mu.reg_read(UC_X86_REG_R9)))
    ok = 0 <= size <= 0x7F7
    src = bytes(mu.mem_read(frm, size)) if ok else b""
    data = struct.unpack("<Q", bytes(mu.mem_read(M["msg"] + 8, 8)))[0] if M.get("msg") else None
    _rec("MSG_WriteBitsCompress", train, size, src, frm == (data or 0) + 9)
    if ok:
        mu.mem_write(to, bytes(b ^ 0x5A for b in src))  # "compressed": a reversible scramble of the input
    return size if ok else 0


def _default_usercmd(pattern):
    def fake(mu):
        ps, cmd = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
        _rec("MSG_SetDefaultUserCmd", ps, _global(cmd))
        mu.mem_write(cmd, pattern)
    return fake


def _hash_key(mu):
    s, maxlen = _cstr(mu, mu.reg_read(UC_X86_REG_RCX)), _i32(mu.reg_read(UC_X86_REG_RDX))
    _rec("Com_HashKey", s, maxlen)
    return zlib.crc32(s) & 0x7FFFFFFF


def _transmit(result):
    def fake(mu):
        chan, data, length = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), _i32(mu.reg_read(UC_X86_REG_R8))
        _rec("CL_Netchan_Transmit", chan, length, bytes(mu.mem_read(data, length)) if 0 <= length <= 0x800 else None)
        return result
    return fake


def _next_fragment(mu):
    chan = mu.reg_read(UC_X86_REG_RCX)
    _rec("CL_Netchan_TransmitNextFragment", chan)
    left = _u32(mu, chan + NC_UNSENT)
    mu.mem_write(chan + NC_UNSENT, struct.pack("<I", (left - 1) & 0xFFFFFFFF))


def _com_error(mu):
    _rec("Com_Error", _i32(mu.reg_read(UC_X86_REG_RCX)), _cstr(mu, mu.reg_read(UC_X86_REG_RDX)))


def _disconnect(mu):
    _rec("sub_1403125F0", _i32(mu.reg_read(UC_X86_REG_RCX)), _cstr(mu, mu.reg_read(UC_X86_REG_RDX)),
         _i32(mu.reg_read(UC_X86_REG_R8)))


def _args(name, spec):
    """Record the integer arguments: q = 64-bit, i = 32-bit signed."""
    regs = (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)

    def fake(mu):
        _rec(name, *[mu.reg_read(r) if k == "q" else _i32(mu.reg_read(r)) for r, k in zip(regs, spec)])
    return fake


def _create_cmd(cmd):
    def fake(mu):
        out, lc = mu.reg_read(UC_X86_REG_RCX), _i32(mu.reg_read(UC_X86_REG_RDX))
        _rec("CL_CreateCmd", lc, bytes(mu.mem_read(va("clients") + CL_VIEWANGLES, 12)))
        mu.mem_write(out, cmd)
        return out
    return fake


def _validate(mu):
    rsp = mu.reg_read(UC_X86_REG_RSP)
    force = bytes(mu.mem_read(rsp + 0x28, 1))[0]
    _rec("sub_14017AB80", mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), _i32(mu.reg_read(UC_X86_REG_R8)),
         _i32(mu.reg_read(UC_X86_REG_R9)), force)


def _revalidate(mu):
    # the new command must already be in place when the validation data is recorded again
    cl = va("clients")
    slot = _u32(mu, cl + CL_CMDNUMBER) & 0x7F
    _rec("sub_14017AAE0", mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), _i32(mu.reg_read(UC_X86_REG_R8)),
         _i32(mu.reg_read(UC_X86_REG_R9)), bytes(mu.mem_read(cl + CL_CMDS + CMD_SIZE * slot, CMD_SIZE)))


def _ret(name, value, spec="i"):
    rec = _args(name, spec)

    def fake(mu):
        rec(mu)
        return value
    return fake


# --- state --------------------------------------------------------------------------------------------------------

def _cmdstr(r, n):
    return bytes(r.choice(b"abcdefghijklmnopqrstuvwxyz 0123456789\"") for _ in range(n))


def _state(r):
    connstate = r.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 10, 10, 10, 10])
    mode = r.choice([0, 0, 0, 0, 1, 2, 3, 3, 4, -1])
    cmd_number = r.choice([0, 127, 128, 1000, r.getrandbits(31), r.randint(-50, 50)])
    cmds = bytes(r.getrandbits(8) for _ in range(CMD_SIZE * 128))
    mask = r.choice([15, 15, 15, 7, 3, 0])
    realtime = r.choice([0, 1000, 50000, r.randint(0, 1 << 30)])
    out_packets = b"".join(struct.pack(
        "<iii", cmd_number - r.choice([0, 1, 2, 3, 5, 31, 32, 33, 40, -1, -100, r.randint(-1 << 20, 1 << 20)]),
        r.getrandbits(31), realtime - r.choice([0, 9, 10, 32, 33, 34, 66, 67, 999, 1000, r.randint(-5000, 5000)]))
        for _ in range(16))
    sms = r.getrandbits(31)
    snap = (r.choice([0, 0, 1, 1, 2]), r.choice([sms, sms, sms - 1, r.getrandbits(31)]))
    origin = struct.pack("<3f", *[r.uniform(-1e5, 1e5) for _ in range(3)])
    veh = bytearray(r.getrandbits(8) for _ in range(0x68))
    veh[0:4] = struct.pack("<i", r.choice([0, 0, 0x7FF, 0x7FF, 1, 5, 0x7FE, 0x800, -1]))
    pred_time = r.getrandbits(31)
    viewangles = struct.pack("<3f", *[r.uniform(-360, 360) for _ in range(3)])
    ack = r.choice([0, 5, 126, 127, 1000, r.getrandbits(30)])
    seq = ack + r.choice([0, 0, 0, 1, 1, 2, 3, -1, -5])
    if r.random() < 0.2:
        seq = ack + r.choice([3, 4])
        long_cmds = True
    else:
        long_cmds = False
    lengths = [r.choice([1000, 900]) if long_cmds else r.randint(0, 40) for _ in range(ack + 1, seq + 1)]
    if long_cmds and r.random() < 0.5:
        # bring the model's message size (9-byte header, 6 bytes + text per command, 1 byte clc_EOF) close to the
        # 0x800 bytes CL_WritePacket checks against
        lengths = [1000] + [0] * (len(lengths) - 1)
        lengths[-1] += r.randint(0x7F4, 0x804) - 10 - 6 * len(lengths) - sum(lengths)
    reliable = {i & 127: _cmdstr(r, n) for i, n in zip(range(ack + 1, seq + 1), lengths)}
    scs = r.getrandbits(31)
    server_cmd = _cmdstr(r, r.choice([0, 5, 31, 32, 33, 60]))
    checksum = r.getrandbits(32)
    outgoing = r.choice([0, 1, 16, 17, r.getrandbits(31), r.randint(-100, 100)])
    remote = r.choice([2, 4, 4, 4, 0, 1])
    unsent = r.choice([0, 0, 0, 1, 3])
    last_send = realtime - r.choice([0, 1, 999, 1000, 1001, 5000, -10])
    maxpackets = r.choice([15, 30, 30, 60, 100, 1, 7])
    packetdup = r.choice([0, 1, 2, 5, r.randint(-20, 20)])
    server_id = r.getrandbits(32)
    sync_flags = bytes([r.getrandbits(1), r.getrandbits(1)])  # cls.gpuSyncedPrevFrame, inputUpdatedPrevFrame

    def setup(w):
        cl, clc, ui = va("clients"), va("clientConnections"), va("clientUIActives")
        w.u32(ui + 0x8, connstate)
        w.u32(va("unk_143E96824"), mode)
        w.write(cl + CL_SNAP_VALID, struct.pack("<i", snap[0]))
        w.write(cl + CL_SNAP_MESSAGENUM, struct.pack("<i", snap[1]))
        w.u32(cl + CL_SERVERID, server_id)
        w.write(cl + CL_ORIGIN, origin)
        w.write(cl + CL_VEHSTATE, bytes(veh))
        w.u32(cl + CL_PREDTIME, pred_time)
        w.write(cl + CL_VIEWANGLES, viewangles)
        w.write(cl + CL_CMDS, cmds)
        w.write(cl + CL_CMDNUMBER, struct.pack("<i", cmd_number))
        w.u32(cl + CL_BACKUPMASK, mask)
        w.write(cl + CL_OUTPACKETS, out_packets)
        w.u32(clc + CLC_LASTSEND, last_send)
        w.u32(clc + CLC_CHECKSUMFEED, checksum)
        w.write(clc + CLC_RELIABLESEQ, struct.pack("<ii", seq, ack))
        for i, s in reliable.items():
            w.write(clc + CLC_RELIABLECMDS + 1024 * i, s + b"\0")
        w.write(clc + CLC_SERVERMSGSEQ, struct.pack("<ii", sms, scs))
        w.write(clc + CLC_SERVERCMDS + 1024 * (scs & 127), server_cmd + b"\0")
        w.write(clc + CLC_NETCHAN, struct.pack("<i", outgoing))
        w.u32(clc + CLC_NETCHAN + NC_REMOTETYPE, remote)
        w.u32(clc + CLC_NETCHAN + NC_UNSENT, unsent)
        w.u32(va("cls") + 0x120, realtime)
        w.write(va("cls") + 0x124, sync_flags)
        for name, value in (("cl_maxpackets", maxpackets), ("cl_packetdup", packetdup)):
            d = w.alloc(bytes(0x60))
            w.write(d + 0x10, struct.pack("<i", value))
            w.u64(va(name), d)
    return setup


def _input(r, args):
    cmd = bytes(r.getrandbits(8) for _ in range(CMD_SIZE))
    nullcmd = bytes(r.getrandbits(8) for _ in range(CMD_SIZE))
    fakes = {
        "?CL_CreateCmd@@YA?AUusercmd_s@@W4LocalClientNum_t@@@Z": _create_cmd(cmd),
        "?sub_14017AB80@@YAXPEAUDataValidation@@PEBXHH_N@Z": _validate,
        "?sub_14017AAE0@@YAXPEAUDataValidation@@PEBXHH@Z": _revalidate,
        "?MSG_SetDefaultUserCmd@@YAXPEBUplayerState_s@@PEAUusercmd_s@@@Z": _default_usercmd(nullcmd),
        "?CL_SyncGpu@@YAXP6AH_K@Z@Z": _args("CL_SyncGpu", "q"),
        "?IN_Frame@@YAXXZ": _args("IN_Frame", ""),
        "?sub_140345260@@YA_NW4LocalClientNum_t@@@Z": _ret("sub_140345260", r.choice([0, 1, 1])),
        "?MSG_Init@@YAXPEAUmsg_t@@PEAEH@Z": _msg_init,
        "?MSG_WriteByte@@YAXPEAUmsg_t@@H@Z": _writer("MSG_WriteByte", _byte),
        "?MSG_WriteLong@@YAXPEAUmsg_t@@H@Z": _writer("MSG_WriteLong", _long),
        "?MSG_WriteBits@@YAXPEAUmsg_t@@HH@Z": _writer("MSG_WriteBits", _bits),
        "?MSG_WriteBit0@@YAXPEAUmsg_t@@@Z": _writer("MSG_WriteBit0", lambda mu: (b"\x00", ())),
        "?MSG_WriteBit1@@YAXPEAUmsg_t@@@Z": _writer("MSG_WriteBit1", lambda mu: (b"\x01", ())),
        "?MSG_WriteString@@YAXPEAUmsg_t@@PEBD@Z": _writer("MSG_WriteString", _string),
        "?MSG_WriteDeltaUsercmdKey@@YAXPEAUmsg_t@@HPEBUusercmd_s@@1@Z": _writer("MSG_WriteDeltaUsercmdKey",
                                                                                _delta_usercmd),
        "?MSG_WriteBitsCompress@@YAH_NPEBEPEAEH@Z": _compress,
        "?Com_HashKey@@YAHPEBDH@Z": _hash_key,
        "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _com_error,
        "?Com_ErrorEntered@@YA_NXZ": _ret("Com_ErrorEntered", r.choice([0, 0, 1]), ""),
        "?sub_1403125F0@@YAXW4LocalClientNum_t@@PEBDH@Z": _disconnect,
        "?CL_Netchan_Transmit@@YA_NPEAUnetchan_t@@PEAEH@Z": _transmit(r.choice([1, 1, 0])),
        "?CL_Netchan_TransmitNextFragment@@YAXPEAUnetchan_t@@@Z": _next_fragment,
        "?sub_14031AA70@@YAXPEAUclientActive_t@@HPEBUPlayerVehicleState@@@Z": _args("sub_14031AA70", "qiq"),
        "?CL_SavePredictedOriginForServerTime@@YAXPEAUclientActive_t@@H@Z": _args("CL_SavePredicted", "qi"),
    }
    state = _state(r)

    def setup(w):
        M["m"], M["msg"] = w.m, None
        state(w)
    return {"args": args, "setup": setup, "fakes": fakes}


def case(symbol, seed, n, extra_fakes=None):
    r = random.Random(seed)
    inputs = []
    for _ in range(n):
        inp = _input(r, [0])
        inp["fakes"].update(extra_fakes or {})
        inputs.append(inp)
    return {"symbol": symbol, "build": STORE, "ret": "void", "inputs": inputs}


CASES = [
    case("?CL_CreateNewCommands@@YAXW4LocalClientNum_t@@@Z", 2706, 600),
    case("?CL_CreateCmdsDuringConnection@@YAXW4LocalClientNum_t@@@Z", 3092, 400),
    case("?sub_14030BAD0@@YAXW4LocalClientNum_t@@@Z", 3093, 400),
    case("?CL_Input@@YAXW4LocalClientNum_t@@@Z", 3107, 400),
    case("?CL_WritePacket@@YAXW4LocalClientNum_t@@@Z", 2842, 1500),
    # CL_WritePacket is reconstructed too: faking it (both copies) isolates CL_SendCmd's rate limiting
    case("?CL_SendCmd@@YAXW4LocalClientNum_t@@@Z", 3082, 1500,
         {"?CL_WritePacket@@YAXW4LocalClientNum_t@@@Z": _args("CL_WritePacket", "i")}),
]
