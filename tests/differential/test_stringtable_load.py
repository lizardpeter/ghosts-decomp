"""Differential cases for string tables and localized strings (src/universal/com_stringtable_load_db.cpp,
src/universal/com_stringtable_obj.cpp) against the Store build.

The loaders run with dbstream.py's logged stream fakes and logged fakes for the nested loaders and the asset
linkers, on random structures (every pointer null, inline, insert or an offset; table sizes of 0, 1 and more).
StringTable_HashString runs on random byte strings (bytes from 0x80 included: they are signed chars) with the game's
the CRT's tolower played as the C locale has it (the emulator has no CRT); StringTable_LookupRowNumForValue on random tables whose cells repeat values in other cases, with
I_stricmp the game's and Com_Error a logged fake. tools/fastfile/strings.py is the same logic, checked against the
game on real zones (docs/assets/strings.md).
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"

FAKES = {
    **ds.STREAM_FAKES,
    "?Load_StringTableAsset@@YAXPEAPEAUStringTable@@@Z": ds.asset_linker("Load_StringTableAsset"),
    "?Load_LocalizeEntryAsset@@YAXPEAPEAULocalizeEntry@@@Z": ds.asset_linker("Load_LocalizeEntryAsset"),
    "?Load_StringTable@@YAX_N@Z": ds.recorder("Load_StringTable", "b", ("varStringTable", "g_streamPos")),
    "?Load_LocalizeEntry@@YAX_N@Z": ds.recorder("Load_LocalizeEntry", "b", ("varLocalizeEntry", "g_streamPos")),
}


def _cstr(mu, a, limit=256):
    out = bytearray()
    while len(out) < limit:
        c = mu.mem_read(a + len(out), 1)[0]
        if not c:
            break
        out.append(c)
    return bytes(out)


def _com_error(mu):
    from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX
    ds.log("Com_Error", mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, _cstr(mu, mu.reg_read(UC_X86_REG_RDX)),
           mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_R9) & 0xFFFFFFFF)


def _tolower(mu):
    """tolower (the CRT import, api-ms-win-crt-string) with the C locale unchanged: A-Z become a-z, everything else,
    the negative values of signed chars from 0x80 included, stays (the emulator has no CRT, so the import is
    played here). Logged."""
    from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX
    c = mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF
    c = c - (1 << 32) if c & 0x80000000 else c
    ds.log("tolower", c)
    mu.reg_write(UC_X86_REG_RAX, (c + 32 if 65 <= c <= 90 else c) & 0xFFFFFFFF)


def _attach(w):
    """No zone: give the logged fakes this call's machine, and play the CRT's tolower."""
    ds.M["m"] = w.m
    w.m.on_import("api-ms-win-crt-string-l1-1-0.dll!tolower", _tolower)


def case(symbol, seed, make, ret="void", fakes=None, n=200):
    rnd = random.Random(seed)
    f = {k: v for k, v in (FAKES if fakes is None else fakes).items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": ret, "fakes": f, "inputs": [make(rnd) for _ in range(n)]}


def _loader_input(r, struct_bytes, var, feed=0x1000):
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + r.randbytes(feed))

    def setup(w):
        zone.start(w)
        w.u64(va(var), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _string_table(r):
    b = bytearray(r.randbytes(0x18))
    struct.pack_into("<Q", b, 0, ds.pointer(r) & (2 ** 64 - 1))
    struct.pack_into("<ii", b, 8, r.choice([0, 1, 3, r.randint(0, 6)]), r.choice([0, 1, 2, r.randint(0, 6)]))
    struct.pack_into("<Q", b, 0x10, r.choice([0, FOLLOWING, r.getrandbits(64)]))
    return _loader_input(r, bytes(b), "varStringTable")


def _localize(r):
    b = struct.pack("<QQ", ds.pointer(r) & (2 ** 64 - 1), ds.pointer(r) & (2 ** 64 - 1))
    return _loader_input(r, b, "varLocalizeEntry")


def _handle_ptr(var, inner):
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        struct.pack_into("<Q", buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            w.u64(va(inner), HEAP + 0x30000 + r.getrandbits(8))
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


WORDS = [b"snow", b"SNOW", b"brush", b"none", b"img_camo_iw6_snow", b"\xe9t\xe9", b"", b"A", b"a", b"Zz9_"]


def _hash_input(r):
    s = r.choice(WORDS) if r.random() < 0.5 else bytes(r.randint(1, 255) for _ in range(r.randint(0, 40)))
    return {"args": [s + b"\0"], "setup": _attach}


def _lookup_input(r):
    cols, rows = r.choice([0, 1, 3, r.randint(0, 5)]), r.choice([0, 1, 4, r.randint(0, 8)])
    base = HEAP
    cells_at, strings_at = 0x40, 0x40 + 0x10 * max(cols * rows, 1)
    buf = bytearray(strings_at + 0x400)
    struct.pack_into("<QiiQ", buf, 0, 0, cols, rows, base + cells_at)
    pos = strings_at
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
    import strings
    for i in range(cols * rows):
        word = r.choice(WORDS)
        if r.random() < 0.1:
            p, h = 0, r.getrandbits(32) - (1 << 31)
        else:
            p = base + pos
            buf[pos:pos + len(word) + 1] = word + b"\0"
            pos += len(word) + 1
            x = r.random()       # the stored hash: right, another word's (so I_stricmp decides), or random
            h = strings.string_hash(word if x < 0.8 else r.choice(WORDS)) if x < 0.9 else r.getrandbits(32) - (1 << 31)
        struct.pack_into("<Qi", buf, cells_at + 0x10 * i, p, h)
    column = r.choice([0, 1, 2, cols, cols + 1]) if cols else r.choice([0, 1])
    return {"args": [bytes(buf), column, r.choice(WORDS) + b"\0"], "setup": _attach}


LOOKUP_FAKES = {"?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _com_error}

CASES = [
    case("?Load_StringTable@@YAX_N@Z", 0x7980, _string_table),
    case("?Load_StringTablePtr@@YAX_N@Z", 0x7B00, _handle_ptr("varStringTablePtr", "varStringTable")),
    case("?Load_LocalizeEntry@@YAX_N@Z", 0x26F0, _localize),
    case("?Load_LocalizeEntryPtr@@YAX_N@Z", 0x27E0, _handle_ptr("varLocalizeEntryPtr", "varLocalizeEntry")),
    case("?StringTable_HashString@@YAHPEBD@Z", 0x6D10, _hash_input, ret="int", fakes={}),
    case("?StringTable_LookupRowNumForValue@@YAHPEBUStringTable@@HPEBD@Z", 0x6C50, _lookup_input, ret="int",
         fakes=LOOKUP_FAKES),
]
