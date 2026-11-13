"""Differential cases for database/db_stream.cpp, db_stream_load.cpp, db_fastfile_pointer.cpp and
db_stringtable_load.cpp: the zone stream (block positions, the push/pop stack, reading, pointer conversion).

Block memory and the XZoneMemory live in a buffer passed as an extra argument after the function's own (the
callee ignores it; the harness maps it at HEAP and compares it afterwards), so everything the functions write
through g_streamPos and the block pointers is compared. The stream state (g_streamPos, g_streamPosArray,
g_streamPosIndex, g_streamZoneMem, g_streamPosStack and its index) is drawn per input and compared as globals.
DB_ReadXFile is faked for both runs: it fills the destination from a per-input byte source and records each call
(the decompressed stream is what it stands for); SL_GetString records its string and returns a handle.
"""
import random
import struct

from harness import HEAP
from syms import va

M = {}
MEM_SIZE = 0x4000            # block memory: seven blocks of 0x400 at HEAP + 0x800, the XZoneMemory at HEAP + 0x100
ZONEMEM = HEAP + 0x100
BLOCKS = HEAP + 0x800
BLOCK_SIZE = 0x400


def _u64(mu, a):
    return struct.unpack("<Q", bytes(mu.mem_read(a, 8)))[0]


def fake_read_xfile(mu):
    """DB_ReadXFile(pos, size, flush): `size` bytes of the input's source, recorded."""
    from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RCX, UC_X86_REG_RDX
    pos, size, flush = (mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8))
    src = M["source"]
    data = bytes(src[(M["cursor"] + i) % len(src)] for i in range(size))
    M["cursor"] += size
    mu.mem_write(pos, data)
    M["m"].observed.append(("DB_ReadXFile", pos, size, flush & 0xFFFFFFFF))
    return 0


def fake_sl_getstring(mu):
    from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX
    s = M["m"].read_cstr(mu.reg_read(UC_X86_REG_RCX))
    user = mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF
    M["m"].observed.append(("SL_GetString", s, user))
    return (hash(s) & 0xFFFF) | 0xFFFF00000000 | (len(s) << 16)   # high bits: callers keep only 32


FAKES = {"?DB_ReadXFile@@YAXPEAE_KH@Z": fake_read_xfile, "?SL_GetString@@YA?AW4scr_string_t@@PEBDI@Z": fake_sl_getstring}


def block_addr(i, off=0):
    return BLOCKS + BLOCK_SIZE * i + off


def memory(r):
    """The extra buffer: random block contents and an XZoneMemory pointing at the blocks."""
    mem = bytearray(r.randbytes(MEM_SIZE))
    for i in range(7):
        struct.pack_into("<QQ", mem, ZONEMEM - HEAP + 16 * i, block_addr(i), BLOCK_SIZE)
    return mem


def stream_state(r, w, index=None):
    """Random stream state: each block's saved position somewhere in its first half, the current one in
    g_streamPos, a stack of up to 6 pushes."""
    index = r.randrange(7) if index is None else index
    for i in range(7):
        w.u64(va("g_streamPosArray") + 8 * i, block_addr(i, r.randrange(0, BLOCK_SIZE // 2)))
    w.u64(va("g_streamPos"), block_addr(index, r.randrange(0, BLOCK_SIZE // 2)))
    w.u32(va("g_streamPosIndex"), index)
    w.u64(va("g_streamZoneMem"), ZONEMEM)
    depth = r.randrange(0, 7)
    w.u32(va("g_streamPosStackIndex"), depth)
    for k in range(depth + 1):
        b = r.randrange(7)
        w.write(va("g_streamPosStack") + 16 * k, struct.pack("<QI", block_addr(b, r.randrange(0, 0x200)), b))
    return index


def inputs(seed, args, n=200, index=None, extra=None):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        mem = memory(r)
        source = bytearray(r.randbytes(64) if r.random() < 0.7 else bytes(r.choice([0, 0x41, 0x7A]) for _ in range(64)))
        source[r.randrange(64)] = 0          # strings end somewhere
        a = args(r, mem)
        state_seed = r.getrandbits(32)

        def setup(w, state_seed=state_seed, source=source, index=index):
            M["m"], M["source"], M["cursor"] = w.m, source, 0
            rr = random.Random(state_seed)
            stream_state(rr, w, index if index is None or isinstance(index, int) else rr.choice(index))
            if extra:
                extra(rr, w)
        pad = [0] * (4 - len(a)) if len(a) < 4 else []
        out.append({"args": [*a, *pad, bytes(mem)], "setup": setup})
    return out


def case(symbol, seed, args=lambda r, mem: [], ret="void", **kw):
    return {"symbol": symbol, "ret": ret, "inputs": inputs(seed, args, **kw), "fakes": FAKES}


def packed_offset(r):
    """A stored offset: block in bits 32-35 (sometimes junk above), offset + 1 below; within the blocks."""
    b, off = r.randrange(7), r.randrange(0, BLOCK_SIZE - 8)
    return (r.choice([0, 0, r.getrandbits(28)]) << 36) | (b << 32) | (off + 1)


def ptr_to(mem, r, at):
    """A block pointer stored in the memory buffer at HEAP + at; returns its address."""
    struct.pack_into("<Q", mem, at - HEAP, block_addr(r.randrange(7), r.randrange(0, BLOCK_SIZE // 2)))
    return at


def xstring_args(r, mem):
    """A string pointer (in the buffer) to the current-ish position; DB_ReadXFile's source decides its length."""
    at = HEAP + 0x200 + 8 * r.randrange(8)
    struct.pack_into("<Q", mem, at - HEAP, block_addr(r.randrange(7), r.randrange(0, BLOCK_SIZE - 0x80)))
    return [at]


def load_script_string_setup(r, w):
    # varXAssetList -> a list whose strings are handles (as Load_TempStringCustom leaves them)
    count = 16
    table = w.alloc(struct.pack(f"<{count}Q", *(r.getrandbits(64) for _ in range(count))))
    xal = w.alloc(struct.pack("<iiQiiQQ", count, 0, table, 0, 0, 0, 0))
    w.u64(va("varXAssetList"), xal)


def script_string_args(r, mem):
    at = HEAP + 0x300
    struct.pack_into("<I", mem, at - HEAP, r.randrange(16))
    struct.pack_into("<I", mem, at - HEAP + 4, r.getrandbits(32))
    return [at]


CASES = [
    case("?DB_InitStreams@@YAXPEAUXZoneMemory@@@Z", 0x1A0, args=lambda r, mem: [ZONEMEM]),
    case("?DB_PushStreamPos@@YAXI@Z", 0x1A1, args=lambda r, mem: [r.randrange(7)]),
    case("?DB_PopStreamPos@@YAXXZ", 0x1A2),
    case("?DB_InsertPointer@@YAPEAEXZ", 0x1A3, ret="int64"),
    case("?Load_Stream@@YAX_NPEAX_K@Z", 0x1A4, index=(2, 2, 0, 3, 6),
         args=lambda r, mem: [r.choice([0, 1, 1, 1, 0x100]), block_addr(r.randrange(7), r.randrange(0x200)),
                              r.choice([0, 1, 8, 0x13, r.randrange(0x100)])]),
    case("?DB_ConvertOffsetToAlias@@YAXPEA_K@Z", 0x1A5,
         args=lambda r, mem: [struct.pack_into("<Q", mem, 0x300, packed_offset(r)) or HEAP + 0x300]),
    case("?DB_ConvertOffsetToPointer@@YAXPEA_K@Z", 0x1A6,
         args=lambda r, mem: [struct.pack_into("<Q", mem, 0x300, packed_offset(r)) or HEAP + 0x300]),
    case("?DB_GetPackedOffsetStreamPos@@YAX_KPEIAIPEIA_K@Z", 0x1A7,
         args=lambda r, mem: [r.choice([0, 1, packed_offset(r), r.getrandbits(64)]), HEAP + 0x300, HEAP + 0x308]),
    case("?Load_XStringCustom@@YAXPEAPEBD@Z", 0x1A8, args=xstring_args),
    case("?Load_TempStringCustom@@YAXPEAPEBD@Z", 0x1A9, args=xstring_args),
    case("?Load_ScriptStringCustom@@YAXPEAW4scr_string_t@@@Z", 0x1AA, args=script_string_args,
         extra=load_script_string_setup),
]
