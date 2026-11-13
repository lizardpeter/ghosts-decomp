"""Differential cases for database/db_fastfile_load.cpp: DB_LoadXFile's sequence, and the streamed image row
cursor.

The file side is scripted for both runs: DB_ReadXFileUncompressed and DB_ReadXFile take their bytes from the
input's prefix and zone streams (a fastfile's header with random magic, version, compressor, streamed image rows
and sizes; an XFile, an XAssetList and an XAsset array) and record each request. Everything with an effect outside
the stream functions records its arguments: DB_InitLoadXFile, DB_DirtyDiscError and Com_Error (both stop the run,
as they don't return), DB_FinishLoadXFile, DB_SetFileLoadCompressor, DB_InflateInit, LoadBar_IsComplete (scripted),
LoadBar_LoadingFastfile, DB_AllocXZoneMemory (gives the blocks places in the input's buffer), Load_ScriptStringList,
Load_XGlobalsPtr, Load_XAsset (the XAsset it was given), the signature copy, DB_InflateShutdown and the image pak
index load. The stream functions (DB_InitStreams, push/pop, AllocLoad_XAsset, Load_Stream) run for real.

These cases are the Store build's (its layouts and callees differ from the servers'; records/functions.tsv keeps
the server copies at compiles with the reason).
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX

from harness import HEAP, STACK, STACK_SIZE
from syms import va

M = {}
INLINE = 0xFDFDFDFFFFFFFFFF
SIGNED, UNSIGNED = 0x3030313066665749, 0x3030317566665749
BLOCKS = HEAP + 0x1000
DBFILE = 0x5FE000


def _regs(mu):
    return [mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)]


def _rec(*e):
    M["m"].observed.append(e)


def reader(kind):
    def fn(mu):
        pos, size = _regs(mu)[:2]
        if size > 0x100000:      # a negative asset count makes Load_Stream ask for ~2^64 bytes: record only
            _rec("read " + kind, where(pos), size)
            return 0
        src = M[kind]
        data = src[M[kind + "_at"]:M[kind + "_at"] + size]
        data += bytes(size - len(data))
        M[kind + "_at"] += size
        if pos:
            mu.mem_write(pos, data)
        _rec("read " + kind, where(pos), size)
        return 0
    return fn


def where(pos):
    """A local's address differs between the original's frame and the reconstruction's: record it as 'stack'."""
    return "stack" if STACK <= pos < STACK + STACK_SIZE else pos


def stopper(name):
    def fn(mu):
        a = _regs(mu)
        _rec(name, *(a[:1] if name == "Com_Error" else ()), M["m"].read_cstr(a[1]) if name == "Com_Error" else None)
        mu.emu_stop()
        return 0
    return fn


def recorder(name, n=0, ret=0, cut=None):
    def fn(mu):
        a = _regs(mu)[:n]
        _rec(name, *a)
        return ret() if callable(ret) else ret
    return fn


def fake_alloc(mu):
    sizes_ptr, name, zm = _regs(mu)[:3]
    sizes = struct.unpack("<7Q", bytes(mu.mem_read(sizes_ptr, 56)))
    _rec("DB_AllocXZoneMemory", where(sizes_ptr), sizes, M["m"].read_cstr(name), zm)
    for i in range(7):
        mu.mem_write(zm + 16 * i, struct.pack("<QQ", BLOCKS + 0x400 * i if sizes[i] else 0, sizes[i]))
    return 0


def fake_load_xasset(mu):
    a = struct.unpack("<Q", bytes(mu.mem_read(va("varXAsset"), 8)))[0]
    _rec("Load_XAsset", _regs(mu)[0] & 0xFF, a, bytes(mu.mem_read(a, 16)))
    return 0


FAKES = {
    "?DB_ReadXFileUncompressed@@YAXPEAE_K@Z": reader("prefix"),
    "?DB_ReadXFile@@YAXPEAE_KH@Z": reader("zone"),
    "?DB_InitLoadXFile@@YAXPEAUDBFile@@_K@Z": recorder("DB_InitLoadXFile", 2),
    "?DB_DirtyDiscError@@YAXXZ": stopper("DB_DirtyDiscError"),
    "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": stopper("Com_Error"),
    "?DB_FinishLoadXFile@@YAXXZ": recorder("DB_FinishLoadXFile"),
    "?DB_SetFileLoadCompressor@@YAXH@Z": recorder("DB_SetFileLoadCompressor", 1),
    "?DB_InflateInit@@YAXH@Z": recorder("DB_InflateInit", 1),
    "?LoadBar_IsComplete@@YAHXZ": recorder("LoadBar_IsComplete", 0, lambda: M["complete"]),
    "?LoadBar_LoadingFastfile@@YAX_K0@Z": recorder("LoadBar_LoadingFastfile", 2),
    "?DB_AllocXZoneMemory@@YAXQEA_KPEBDPEAUXZoneMemory@@@Z": fake_alloc,
    "?Load_ScriptStringList@@YAX_N@Z": recorder("Load_ScriptStringList", 1),
    "?Load_XGlobalsPtr@@YAX_N@Z": recorder("Load_XGlobalsPtr", 1),
    "?Load_XAsset@@YAX_N@Z": fake_load_xasset,
    "?sub_140348960@@YAXPEAE@Z": recorder("signature", 1),
    "?DB_InflateShutdown@@YAXXZ": recorder("DB_InflateShutdown"),
    "?sub_140375350@@YAXXZ": recorder("sub_140375350"),
}


def prefix(r):
    magic = r.choice([SIGNED, SIGNED, UNSIGNED, 0x3030313166665749])
    version = r.choice([0x235, 0x235, 0x235, 0x234, 0x236])
    rows = r.choice([0, 0, 1, 4, 9, 0x6281])
    out = struct.pack("<QI", magic, version) + bytes([1, r.choice([0, 2, 1]), 8, 4]) + r.randbytes(8)
    out += struct.pack("<I", rows)
    for _ in range(min(rows, 12)):
        out += struct.pack("<HHIQQ", r.randrange(2), r.randrange(100), 0, r.getrandbits(40), r.getrandbits(40))
    a = r.getrandbits(32)
    out += struct.pack("<QQ", a, a + r.choice([0, 1, r.getrandbits(30)]))
    return out


def zone(r):
    sizes = [r.choice([0, 0x100, 0x3F0]) for _ in range(7)]
    count = r.choice([0, 1, 3, 7, -1])
    lst = struct.pack("<iiQiiQQ", r.randrange(5), 0, r.choice([0, INLINE]), count, 0,
                      r.choice([0, INLINE, INLINE]), r.choice([0, INLINE]))
    assets = b"".join(struct.pack("<iiQ", r.randrange(0x3F), 0, INLINE) for _ in range(max(count, 0)))
    return struct.pack("<9Q", 0x1000, 0, *sizes) + lst + assets


def inputs(seed, n=250):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        pre, zn = prefix(r), zone(r)
        disk = r.random() < 0.5
        complete = r.choice([0, 1])
        s = r.getrandbits(32)

        def setup(w, pre=pre, zn=zn, disk=disk, complete=complete, s=s):
            M.update(m=w.m, prefix=pre, prefix_at=0, zone=zn, zone_at=0, complete=complete)
            w.write(DBFILE, struct.pack("<QQQ", 0x4C8 if disk else 0, 0, 0) + b"mp_test_zone\0")
            from test_db_stream import stream_state
            stream_state(random.Random(s), w)
        out.append({"args": [bytes(0x3000), DBFILE, HEAP + 0x200], "setup": setup})
    return out


CASES = [
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DB_LoadXFile@@YAXPEAUXZoneMemory@@PEAUDBFile@@PEAE@Z", "ret": "void", "fakes": FAKES,
     "inputs": inputs(0x7A0)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?sub_1403492E0@@YAPEAUStreamImageRow@@XZ", "ret": "int64",
     "inputs": [{"args": [], "setup": (lambda w, k=k: w.u32(va("unk_144310BF4"), k))}
                for k in [0, 1, 2, 3, 0x627F, 0x6280, 0xFFFFFFFF] + list(range(4, 40))]},
]
