"""Differential cases for database/db_file_load.cpp: staging reads into g_fileBuf (memory-backed files and
ReadFileEx), waiting for them, the uncompressed and inflated reads, the compressor choice and the error paths.

Each input draws g_load (file, buffers, sizes, offset, error, the stream's input), g_loadOutstandingRead, the
compressor statics, and a DBFile in scratch memory (disk or memory-backed, sometimes named mp_playlists). The OS
and the engine are scripted for both runs alike and record their arguments: ReadFileEx (succeeds, or fails with
ERROR_HANDLE_EOF or another error), GetLastError, SleepEx, CloseHandle, remove, Sys_WaitDatabaseThread,
LoadBar_ReadResident, LiveStorage_GetLocalPlaylistFilename, DB_AuthLoad_Inflate (copies what fits and returns a
scripted result), DB_AuthLoad_InflateInit/End. Sys_Error and Com_Error record their message and stop the run (they
don't return in the game).

These cases are the Store build's (its layouts and callees differ from the servers'; records/functions.tsv keeps
the server copies at compiles with the reason).
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

from harness import HEAP
from syms import va

M = {}
LOAD = None  # g_load's address, per build
OFF = {"file": 0x0, "fileBuffer": 0x8, "readSize": 0x10, "completed": 0x18, "offset": 0x20, "start_in": 0x28,
       "overlapped": 0x30, "readError": 0x50, "next_in": 0x58, "avail_in": 0x60, "next_out": 0x68, "avail_out": 0x70,
       "readingResident": 0xB0}
PLAYLIST_PATH = 0x5FF800
MEMBUF = 0x5FD000            # a memory-backed file's bytes (scratch memory)
# The input's DBFile is passed as an extra buffer argument after the function's own, so the harness compares it
# afterwards (the memory-backed reads move its buffer pointer and size); dbfile_at() gives its address.


def _rec(*entry):
    M["m"].observed.append(entry)


def _u64(mu, a):
    return struct.unpack("<Q", bytes(mu.mem_read(a, 8)))[0]


def _u32(mu, a):
    return struct.unpack("<I", bytes(mu.mem_read(a, 4)))[0]


def _args(mu, n):
    regs = [mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)]
    rsp = mu.reg_read(UC_X86_REG_RSP)
    return (regs + [_u64(mu, rsp + 0x28 + 8 * i) for i in range(max(0, n - 4))])[:n]


def stop(name):
    def fn(mu):
        a = _args(mu, 3)
        fmt = M["m"].read_cstr(a[0] if name == "Sys_Error" else a[1])
        _rec(name, fmt, *(a[1:] if name == "Sys_Error" else a[2:]))
        mu.emu_stop()
        return 0
    return fn


def fake_inflate(mu):
    """DB_AuthLoad_Inflate(stream, flush, finish): moves min(avail_in, avail_out) bytes, returns the plan's result."""
    stream, flush, finish = _args(mu, 3)
    nin, ain, nout, aout = (_u64(mu, stream), _u32(mu, stream + 8), _u64(mu, stream + 0x10), _u32(mu, stream + 0x18))
    n = min(ain, aout, M["plan"].pop(0) if M["plan"] else 0x7FFFFFFF)
    if n and nout:
        mu.mem_write(nout, bytes(mu.mem_read(nin, n)))
    mu.mem_write(stream, struct.pack("<QI", nin + n, ain - n))
    mu.mem_write(stream + 0x10, struct.pack("<QI", nout + n, aout - n))
    _rec("DB_AuthLoad_Inflate", stream, flush & 0xFFFFFFFF, finish & 0xFFFFFFFF, n)
    return M["results"].pop(0) if M["results"] else 0


def record(name, n, ret=0):
    def fn(mu):
        _rec(name, *_args(mu, n))
        return ret() if callable(ret) else ret
    return fn


FAKES = {
    "?Sys_Error@@YAXPEBDZZ": stop("Sys_Error"),
    "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": stop("Com_Error"),
    "?Sys_WaitDatabaseThread@@YAXXZ": record("Sys_WaitDatabaseThread", 0),
    "?LoadBar_ReadResident@@YAX_K@Z": record("LoadBar_ReadResident", 1),
    "?LiveStorage_GetLocalPlaylistFilename@@YAPEBDXZ": record("LiveStorage_GetLocalPlaylistFilename", 0, PLAYLIST_PATH),
    "?DB_AuthLoad_Inflate@@YAHPEAUdb_z_stream_s@@HH@Z": fake_inflate,
    "?DB_AuthLoad_InflateInit@@YAHPEAUdb_z_stream_s@@HPEBD@Z":
        record("DB_AuthLoad_InflateInit", 3, lambda: M["results"].pop(0) if M["results"] else 0),
    "?DB_AuthLoad_InflateEnd@@YAXPEAUdb_z_stream_s@@@Z": record("DB_AuthLoad_InflateEnd", 1),
}


def os_script(m, r):
    def readfileex(mu):
        h, buf, n, ovl = _args(mu, 4)
        cb = _args(mu, 5)[4]
        _rec("ReadFileEx", h, buf, n & 0xFFFFFFFF, ovl, cb, bytes(mu.mem_read(ovl, 0x20)))
        ok = M["readok"].pop(0) if M["readok"] else 1
        from unicorn.x86_const import UC_X86_REG_RAX
        mu.reg_write(UC_X86_REG_RAX, ok)

    def getlasterror(mu):
        from unicorn.x86_const import UC_X86_REG_RAX
        mu.reg_write(UC_X86_REG_RAX, M["lasterror"])
        _rec("GetLastError")

    def simple(name, n):
        def fn(mu):
            _rec(name, *(_args(mu, n)))
        return fn
    m.on_import("kernel32.dll!ReadFileEx", readfileex)
    m.on_import("kernel32.dll!GetLastError", getlasterror)
    m.on_import("kernel32.dll!SleepEx", simple("SleepEx", 2))
    m.on_import("kernel32.dll!CloseHandle", simple("CloseHandle", 1))
    m.on_import("api-ms-win-crt-filesystem-l1-1-0.dll!remove", lambda mu: _rec("remove", M["m"].read_cstr(_args(mu, 1)[0])))


def state(r, w):
    load = va("g_load")
    fbuf = va("g_fileBuf")
    w.write(MEMBUF, r.randbytes(0x300))
    dbfile = M["dbfile"]
    w.write(PLAYLIST_PATH, b"players2/playlists.info\0")
    cur = fbuf + r.choice([0, 0x40000])
    avail = r.choice([0, 0, 1, 7, 0x20, 0x100])
    w.u64(load + OFF["file"], dbfile)
    w.u64(load + OFF["fileBuffer"], cur)
    w.u64(load + OFF["readSize"], r.choice([~0 & (2 ** 64 - 1), 0, 0x40000, 0x40001, 0x80000, 0x1234, r.getrandbits(36)]))
    w.u64(load + OFF["completed"], r.choice([0, 0x40000, 0x100, r.getrandbits(18)]))
    w.u64(load + OFF["offset"], r.choice([0, 0x2C, r.getrandbits(40)]))
    w.u32(load + OFF["readError"], r.choice([0, 0, 0x26, 0x17]))
    w.u64(load + OFF["next_in"], fbuf + r.randrange(0, 0x400))
    w.u32(load + OFF["avail_in"], avail)
    w.u32(load + OFF["readingResident"], r.choice([0, 1]))
    w.u32(va("g_loadOutstandingRead"), r.choice([0, 1, 2, 2]))
    w.write(fbuf, r.randbytes(0x500))
    w.write(fbuf + 0x40000, r.randbytes(0x100))
    set_ = r.random() < 0.5
    w.write(va("s_compressorTypeIsSet"), bytes([set_]))
    w.u32(va("s_compressorTypeIndex"), r.choice([0, 2, 1]))
    M["plan"] = [r.choice([0x7FFFFFFF, 1, 0x10, 0]) for _ in range(8)]
    M["results"] = [r.choice([0, 0, 0, 1, 2, -3 & 0xFFFFFFFF, -6 & 0xFFFFFFFF]) for _ in range(8)]
    M["readok"] = [r.choice([1, 1, 0]) for _ in range(8)]
    M["lasterror"] = r.choice([0x26, 0x26, 0x5])


def dbfile(r):
    disk = r.random() < 0.5
    name = r.choice([b"mp_alien_town_path", b"mp_playlists", b"common_mp", b"MP_PLAYLISTS"])
    # (a size whose low 32 bits are negative as an int makes the original memcpy ~4 GB: see docs/fastfiles.md)
    msize = r.choice([0, 1, 0x20, 0x300, 0x40000, 0x50000, 0x100000000 + r.randrange(0x1000)])
    return (struct.pack("<QQQ", r.choice([0x4C8, 0x123456]) if disk else 0, msize, MEMBUF) + name +
            b"\0" * (64 - len(name)))


def dbfile_at(args):
    """Where the harness maps the extra DBFile buffer: after the function's own buffer arguments."""
    return HEAP + sum((len(a) + 16 + 0xFFF) & ~0xFFF for a in args if isinstance(a, (bytes, bytearray)))


def inputs(seed, args, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        s = r.getrandbits(32)
        a = args(r)
        f = dbfile(r)
        at = dbfile_at(a)
        a = [at if x is DBFILE else x for x in a]

        def setup(w, s=s, at=at):
            M["m"], M["dbfile"] = w.m, at
            os_script(w.m, r)
            state(random.Random(s), w)
        out.append({"args": [*a, *([0] * (4 - len(a))), f], "setup": setup})
    return out


DBFILE = object()   # stands for the DBFile's address in an argument list


def case(symbol, seed, args=lambda r: [], ret="void"):
    return {"build": "iw6mp64_MSStore_ship", "symbol": symbol, "ret": ret, "inputs": inputs(seed, args), "fakes": FAKES}


CASES = [
    case("?DB_DirtyDiscError@@YAXXZ", 0x4A0),
    case("?DB_FileReadCompletion@@YAXKKPEAU_OVERLAPPED@@@Z", 0x4A1,
         args=lambda r: [r.choice([0, 0x26, 5]), r.choice([0, 0x40000, r.getrandbits(32)]), 0]),
    case("?DB_FinishLoadXFile@@YAXXZ", 0x4A2),
    case("?sub_1403497F0@@YAPEAUDBFile@@XZ", 0x4A3, ret="int64"),
    case("?DB_InflateInit@@YAXH@Z", 0x4A4, args=lambda r: [r.choice([0, 1, 2])]),
    case("?DB_InflateShutdown@@YAXXZ", 0x4A5),
    case("?DB_InitLoadXFile@@YAXPEAUDBFile@@_K@Z", 0x4A6,
         args=lambda r: [DBFILE, r.choice([0, 0x2C, r.getrandbits(40)])]),
    case("?DB_WaitXFileStage@@YAXXZ", 0x4A7),
    case("?DB_ReadXFile@@YAXPEAE_KH@Z", 0x4A8,
         args=lambda r: [bytes(0x200), r.choice([0, 1, 4, 0x48, 0x1F0]), r.choice([0, 2])]),
    case("?DB_ReadXFileStage@@YAXXZ", 0x4A9),
    case("?DB_ReadXFileUncompressed@@YAXPEAE_K@Z", 0x4AA,
         args=lambda r: [r.choice([bytes(0x200), 0]), r.choice([0, 1, 4, 8, 0x18, 0x1F0])]),
    case("?DB_SetFileLoadCompressor@@YAXH@Z", 0x4AB, args=lambda r: [r.choice([0, 2, 1, 3, -1])]),
]
