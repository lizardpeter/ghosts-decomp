"""Differential cases for the font loaders (src/gfx_d3d/r_font_load_db.cpp) against the Store build: random Font_s
structures (every pointer null, inline, insert or an offset; glyph counts of 0, 1 and more) with dbstream.py's
logged stream fakes and logged fakes for Load_MaterialHandle, Load_Font and Load_FontAsset.
tools/fastfile/font.py is the same logic, checked against the game on real zones (docs/assets/fonts.md)."""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"

FAKES = {
    **ds.STREAM_FAKES,
    "?Load_FontAsset@@YAXPEAPEAUFont_s@@@Z": ds.asset_linker("Load_FontAsset"),
    "?Load_MaterialHandle@@YAX_N@Z": ds.recorder("Load_MaterialHandle", "b", ("varMaterialHandle",)),
    "?Load_Font@@YAX_N@Z": ds.recorder("Load_Font", "b", ("varFont", "g_streamPos")),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    return {"symbol": symbol, "build": STORE, "ret": "void",
            "fakes": {k: v for k, v in FAKES.items() if k != symbol}, "inputs": [make(rnd) for _ in range(n)]}


def _font(r):
    b = bytearray(r.randbytes(0x28))
    struct.pack_into("<Q", b, 0, ds.pointer(r) & (2 ** 64 - 1))
    struct.pack_into("<i", b, 0xC, r.choice([0, 1, 5, r.randint(0, 40)]))
    for off in (0x10, 0x18, 0x20):
        struct.pack_into("<Q", b, off, ds.pointer(r, inline=0.45, insert=0.1) & (2 ** 64 - 1))
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + 0x28] = b
    zone = ds.Zone(r, (bytes(b) if flag else b"") + r.randbytes(0x1000))

    def setup(w):
        zone.start(w)
        w.u64(va("varFont"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _handle(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
    value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
    struct.pack_into("<Q", buf, OFF_STRUCT, value)
    zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

    def setup(w):
        zone.start(w)
        w.u64(va("varFontHandle"), HEAP + OFF_STRUCT)
        w.u64(va("varFont"), HEAP + 0x30000 + r.getrandbits(8))
    return {"args": [flag, bytes(buf)], "setup": setup}


CASES = [
    case("?Load_Font@@YAX_N@Z", 0xCE20, _font),
    case("?Load_FontHandle@@YAX_N@Z", 0xCF50, _handle),
]
