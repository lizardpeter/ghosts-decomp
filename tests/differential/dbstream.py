"""Logged fakes of the zone stream for differential tests of the asset loaders (Load_* functions).

A generated loader (Load_XModel, Load_XSurface, ...) reads the zone through a handful of stream functions owned by
the fastfile pipeline (include/database/db_stream_api.h). To test a loader on its own, against the original, those
are replaced by Python for both runs:

- Load_Stream(atStreamStart, ptr, size): logged; with atStreamStart and size, copies the next `size` bytes of the
  input's zone bytes into ptr and advances g_streamPos by size (the real one reads the zone file there).
- DB_PushStreamPos / DB_PopStreamPos: logged (block switching is the pipeline's; the loaders only bracket).
- DB_ConvertOffsetToPointer / DB_ConvertOffsetToAlias: logged with the value found, which is replaced by a
  recognisable "resolved" address, so the caller's later use of the field is visible.
- DB_InsertPointer: logged; returns the next slot of an insert table inside the compared buffer.
- Load_XStringCustom: logged; writes a NUL-terminated string from the zone bytes at *str and advances g_streamPos.

Every input works in one buffer passed as the first pointer argument after the function's own arguments (it lands at
HEAP, harness.py): the structure under test at OFF_STRUCT, the stream at OFF_STREAM (g_streamPos starts there, at a
random misalignment), the insert table at OFF_INSERT. The buffer is compared after the call, so every byte a loader
writes into loaded data is checked, as are the globals it sets (var*, g_streamPos) and the logged calls.
"""
import struct

from unicorn import UcError
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX

from harness import HEAP
from syms import va

FOLLOWING = 0xFDFDFDFFFFFFFFFF
INSERT = 0xFDFDFDFFFFFFFFFE
BUF_SIZE = 0x8000
OFF_STRUCT, OFF_AUX, OFF_STREAM, OFF_INSERT = 0x0, 0x1800, 0x3000, 0x7F00
RESOLVED = 0x7E0000000000  # DB_ConvertOffsetToPointer's fake result: RESOLVED | (offset & 0xFFFFFFFF)
ALIASED = 0x7D0000000000

SYM = {
    "Load_Stream": "?Load_Stream@@YAX_NPEAX_K@Z",
    "DB_PushStreamPos": "?DB_PushStreamPos@@YAXI@Z",
    "DB_PopStreamPos": "?DB_PopStreamPos@@YAXXZ",
    "DB_ConvertOffsetToPointer": "?DB_ConvertOffsetToPointer@@YAXPEA_K@Z",
    "DB_ConvertOffsetToAlias": "?DB_ConvertOffsetToAlias@@YAXPEA_K@Z",
    "DB_InsertPointer": "?DB_InsertPointer@@YAPEAEXZ",
    "Load_XStringCustom": "?Load_XStringCustom@@YAXPEAPEBD@Z",
}

M = {}  # the current call's machine and zone (set by the setup of each input)


def u64(mu, a):
    return struct.unpack("<Q", bytes(mu.mem_read(a, 8)))[0]


def u32(mu, a):
    return struct.unpack("<I", bytes(mu.mem_read(a, 4)))[0]


def arg(mu, i):
    return mu.reg_read((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)[i])


def log(*entry):
    M["m"].observed.append(entry)


def write(addr, data):
    """A write made by a fake: journaled if it lands in an image (globals), plain otherwise (HEAP)."""
    M["m"]._emulated_write(addr, bytes(data))


def set_global(name, value):
    write(va(name), struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF))


def get_global(name):
    return u64(M["m"].mu, va(name))


def in_buffer(addr, size):
    return HEAP <= addr and addr + size <= HEAP + BUF_SIZE


class Zone:
    """One input's zone: the bytes Load_Stream hands out, and the fake's counters. Reset before each run."""

    def __init__(self, r, stream_bytes=None):
        self.data = stream_bytes if stream_bytes is not None else r.randbytes(0x3000)
        self.misalign = r.randrange(16)
        self.reset()

    def reset(self):
        self.pos = 0
        self.inserts = 0

    def take(self, n):
        out = self.data[self.pos:self.pos + n]
        self.pos += len(out)
        return out + bytes(n - len(out))

    def start(self, w):
        """Setup part shared by every loader test: remember the machine, reset the zone, place g_streamPos."""
        M["m"], M["zone"] = w.m, self
        self.reset()
        w.u64(va("g_streamPos"), HEAP + OFF_STREAM + self.misalign)


# --- fakes of the stream functions -------------------------------------------------------------------------------

def _load_stream(mu):
    flag, ptr, size = arg(mu, 0) & 0xFF, arg(mu, 1), arg(mu, 2)
    log("Load_Stream", flag, ptr, size)
    if flag and size:
        zone = M["zone"]
        if size <= 0x10000 and in_buffer(ptr, size):
            write(ptr, zone.take(size))
        else:
            zone.pos += size  # the zone advances as the real one would; nothing lands outside the buffer
        set_global("g_streamPos", get_global("g_streamPos") + size)


def _push(mu):
    log("DB_PushStreamPos", arg(mu, 0) & 0xFFFFFFFF)


def _pop(mu):
    log("DB_PopStreamPos")


def _convert(mu):
    p = arg(mu, 0)
    v = u64(mu, p)
    log("DB_ConvertOffsetToPointer", p, v)
    write(p, struct.pack("<Q", RESOLVED | (v & 0xFFFFFFFF)))


def _alias(mu):
    p = arg(mu, 0)
    v = u64(mu, p)
    log("DB_ConvertOffsetToAlias", p, v)
    write(p, struct.pack("<Q", ALIASED | (v & 0xFFFFFFFF)))


def _insert(mu):
    zone = M["zone"]
    slot = HEAP + OFF_INSERT + 8 * zone.inserts
    zone.inserts += 1
    log("DB_InsertPointer", slot)
    return slot


def _xstring(mu):
    p = arg(mu, 0)
    s = u64(mu, p)
    zone = M["zone"]
    n = zone.take(1)[0] % 24
    text = bytes(0x61 + b % 26 for b in zone.take(n)) + b"\0"
    log("Load_XStringCustom", p, s)
    if in_buffer(s, len(text)):
        write(s, text)
    set_global("g_streamPos", get_global("g_streamPos") + len(text))


STREAM_FAKES = {
    SYM["Load_Stream"]: _load_stream,
    SYM["DB_PushStreamPos"]: _push,
    SYM["DB_PopStreamPos"]: _pop,
    SYM["DB_ConvertOffsetToPointer"]: _convert,
    SYM["DB_ConvertOffsetToAlias"]: _alias,
    SYM["DB_InsertPointer"]: _insert,
    SYM["Load_XStringCustom"]: _xstring,
}


# --- fakes of callees -----------------------------------------------------------------------------------------------

def array_loader(name, var_name, elem_size):
    """A fake Load_<T>Array(atStreamStart, count) of plain data: logs, and with atStreamStart loads count elements at
    the array variable (as the real one's Load_Stream does)."""
    def fake(mu):
        flag, count = arg(mu, 0) & 0xFF, arg(mu, 1)
        dest = get_global(var_name)
        log(name, flag, count, dest)
        if flag and count:
            size = count * elem_size
            if size <= 0x10000 and in_buffer(dest, size):
                write(dest, M["zone"].take(size))
            set_global("g_streamPos", get_global("g_streamPos") + size)
    return fake


def recorder(name, spec="", globals_=(), deref=(), ret=None):
    """A fake that logs its arguments (spec: one letter per register argument, b/i/q) and the values of some
    globals (and of what pointer globals point at), and returns `ret`."""
    masks = {"b": 0xFF, "i": 0xFFFFFFFF, "q": (1 << 64) - 1}

    def fake(mu):
        got = [arg(mu, i) & masks[k] for i, k in enumerate(spec)]
        got += [get_global(g) for g in globals_]
        for g in deref:
            p = get_global(g)
            try:
                got.append(u64(mu, p))
            except UcError:
                got.append(None)
        log(name, *got)
        return ret
    return fake


def clobbering(fake, **values):
    """Wrap a fake so it also overwrites globals afterwards (as a nested loader may), to tell a caller that kept a
    value in a local from one that re-reads the global."""
    def wrapped(mu):
        ret = fake(mu)
        for name, value in values.items():
            set_global(name, value)
        return ret
    return wrapped


def asset_linker(name):
    """A fake Load_<T>Asset(T **ptr) (DB_LinkXAssetEntry): logs, and replaces *ptr as linking to an asset already
    loaded would, so a caller that copies *ptr afterwards (into an insert slot) shows it re-read it."""
    def fake(mu):
        p = arg(mu, 0)
        v = u64(mu, p) if in_buffer(p, 8) else None
        log(name, p, v)
        if v is not None:
            write(p, struct.pack("<Q", v ^ 0x5500000000))
    return fake


def pointer(r, inline=0.45, insert=0.0, null=0.2):
    """A pointer field's zone value: null, inline data (FOLLOWING), an insert slot, or an offset."""
    x = r.random()
    if x < null:
        return 0
    if x < null + inline:
        return FOLLOWING
    if x < null + inline + insert:
        return INSERT
    return r.choice([0x10000000 | r.getrandbits(28), r.getrandbits(64) or 1, INSERT, 1])
