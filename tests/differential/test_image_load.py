"""Differential cases for the GfxImage zone loaders (src/gfx_d3d/r_image_load_db.cpp), Load_ImageStream and the
picmip helpers that run after an image loads (src/database/db_registry.cpp, src/gfx_d3d/r_image.cpp,
src/gfx_d3d/r_image_load_common.cpp). Store build only: the servers' GfxImage is 0x38 bytes and their
Load_ImageStream does nothing.

The stream functions are dbstream.py's logged fakes; each loader's callees are logged fakes too (Load_Texture,
Load_GfxImageAsset, the pak opener). docs/assets/images.md.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
IMAGE_SIZE = 0x68

LOAD_TEXTURE = "?Load_Texture@@YAXPEAPEAUGfxImageLoadDef@@PEAUGfxImage@@@Z"
FAKES = {
    **ds.STREAM_FAKES,
    LOAD_TEXTURE: ds.recorder("Load_Texture", "qq", ("varbyte", "g_streamPos")),
    "?Load_GfxTextureLoad@@YAX_N@Z": ds.recorder("Load_GfxTextureLoad", "b", ("varGfxTextureLoad", "varGfxImage",
                                                                             "g_streamPos")),
    "?sub_1403723B0@@YAXPEAUGfxImage@@@Z": ds.recorder("sub_1403723B0", "q", ("varGfxImage",)),
    "?Load_GfxImage@@YAX_N@Z": ds.clobbering(ds.recorder("Load_GfxImage", "b", ("varGfxImage", "g_streamPos")),
                                             varGfxImagePtr=HEAP + OFF_AUX + 0x400),
    "?Load_GfxImageAsset@@YAXPEAPEAUGfxImage@@@Z": ds.asset_linker("Load_GfxImageAsset"),
}


def case(symbol, seed, make, fakes=FAKES, n=200, ret="void"):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in fakes.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": ret, "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(buf, off, v):
    struct.pack_into("<Q", buf, off, v & 0xFFFFFFFFFFFFFFFF)


def _image_bytes(r):
    h = bytearray(r.randbytes(IMAGE_SIZE))
    h[0x1D] = r.choice([0, 2, 5, 8, 11, 11, r.randrange(256)])                       # semantic
    struct.pack_into("<i", h, 0x24, r.choice([0, 1, r.randrange(0x400), r.randrange(0x1000), -r.randrange(1, 8)]))
    return h


def _texture_load(r):
    """Load_GfxTextureLoad: varGfxImage is a header in the buffer, varGfxTextureLoad its +0x38."""
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.5
    h = _image_bytes(r)
    _q(h, 0x38, r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1]))
    buf[OFF_STRUCT:OFF_STRUCT + IMAGE_SIZE] = h
    zone = ds.Zone(r, r.randbytes(0x2000))

    def setup(w):
        zone.start(w)
        w.u64(va("varGfxImage"), HEAP + OFF_STRUCT)
        w.u64(va("varGfxTextureLoad"), HEAP + OFF_STRUCT + 0x38)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _image(r):
    """Load_GfxImage: the header from the zone (atStreamStart) or already in place; name pointer of every kind."""
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.5
    h = _image_bytes(r)
    _q(h, 0x60, ds.pointer(r))
    buf[OFF_STRUCT:OFF_STRUCT + IMAGE_SIZE] = h
    zone = ds.Zone(r, (bytes(h) if flag else b"") + r.randbytes(0x2000))

    def setup(w):
        zone.start(w)
        w.u64(va("varGfxImage"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _image_ptr(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
    value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
    _q(buf, OFF_STRUCT, value)
    zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

    def setup(w):
        zone.start(w)
        w.u64(va("varGfxImagePtr"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


# ---- Load_ImageStream ----------------------------------------------------------------------------------------------

THIS_FILE = 0x7C0000001000   # sub_1403497F0's fake result: the fastfile being loaded
ROWS = 0x200                 # the rows live in the buffer at HEAP + ROWS


def _stream_fakes(state):
    def next_row(mu):
        i = state["next"]
        state["next"] += 1
        ds.log("sub_1403492E0", i)
        return HEAP + ROWS + 0x18 * i

    def this_file(mu):
        ds.log("sub_1403497F0")
        return THIS_FILE

    def sprintf(mu):
        dest, size, fmt, n = (ds.arg(mu, i) for i in range(4))
        text = bytes(mu.mem_read(fmt, 16)).split(b"\0")[0]
        ds.log("Com_sprintf", dest, size & 0xFFFFFFFF, text, n & 0xFFFFFFFF)

    def open_pak(mu):
        handles, count, image, index = (ds.arg(mu, i) for i in range(4))
        sp = mu.reg_read(__import__("unicorn").x86_const.UC_X86_REG_RSP)
        localized = ds.u64(mu, sp + 0x28) & 0xFFFF
        ds.log("sub_140548160", handles, count & 0xFFFFFFFF, image & 0xFFFFFFFF, index & 0xFFFF, localized)
        return state["handles"].get(index & 0xFFFF, 0)

    return {
        "?sub_1403492E0@@YAPEAUStreamImageRow@@XZ": next_row,
        "?sub_1403497F0@@YAPEAUDBFile@@XZ": this_file,
        "?Com_sprintf@@YAXPEADHPEBDZZ": sprintf,
        "?sub_140548160@@YAPEAXPEAPEAXHHII@Z": open_pak,
        "?sub_1403710C0@@YAXXZ": ds.recorder("sub_1403710C0"),
        "?DB_DirtyDiscError@@YAXXZ": ds.recorder("DB_DirtyDiscError"),
    }


STATE = {"next": 0, "handles": {}}


def _image_stream(r):
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    index = r.choice([0, 1, 31, 32, 33, r.randrange(1, 600)])
    h = _image_bytes(r)
    h[0x35] = r.choice([0, 1, 1, 1, r.randrange(256)])
    h[0x1F] = r.randrange(256)
    for k in range(4):
        struct.pack_into("<HH", h, 0x40 + 8 * k, r.choice([0, 1, r.randrange(4096)]), r.choice([1, r.randrange(4096)]))
    buf[OFF_STRUCT:OFF_STRUCT + IMAGE_SIZE] = h
    files = [r.choice([0, 0, 1, 2, r.randrange(1, 0x60)]) for _ in range(4)]
    for k in range(4):
        end = r.choice([0, r.getrandbits(40), r.getrandbits(64)])
        struct.pack_into("<HHIQQ", buf, ROWS + 0x18 * k, r.choice([0, 0, 1]), files[k], r.getrandbits(32),
                         r.getrandbits(64), end)
    opened = {f: r.choice([0, 0x1234, r.getrandbits(64)]) for f in set(files) if r.random() < 0.4}
    results = {f: r.choice([0, 0x5678 + f, r.getrandbits(64)]) for f in set(files)}
    bits = r.getrandbits(32)

    def setup(w):
        STATE["next"] = 0
        STATE["handles"] = results
        ds.M["m"] = w.m
        base = va("unk_14604CA10")
        for f in range(0x60):
            w.u64(base + 8 * f, opened.get(f, 0))
        w.u32(va("unk_14604C200") + 4 * (index >> 5), bits)
    return {"args": [index, bytes(buf)[OFF_STRUCT:OFF_STRUCT + IMAGE_SIZE] + bytes(ROWS - IMAGE_SIZE)
                     + bytes(buf[ROWS:ROWS + 0x60])], "setup": setup}


# ---- picmip helpers -----------------------------------------------------------------------------------------------

PICMIP_GLOBALS = ("unk_14A2E2968", "unk_14A2E296C", "unk_14A2E2970")


def _picmip_setup(r):
    values = [r.choice([-1, 0, 1, 2, 3, 4, r.randrange(-50, 50), r.getrandbits(32)]) for _ in PICMIP_GLOBALS]

    def setup(w):
        for g, v in zip(PICMIP_GLOBALS, values):
            w.u32(va(g), v & 0xFFFFFFFF)
    return setup


def _get_picmip(r):
    return {"args": [r.choice(list(range(16)) + [r.randrange(256)]), r.randbytes(2)], "setup": _picmip_setup(r)}


def _levels(r):
    h = _image_bytes(r)
    h[0x1F] = r.choice([0, 2, r.randrange(256)])
    count = r.choice([0, 1, 2, 3, 4, 4])
    size = r.choice([16, 64, 128, 256])
    for k in range(4):
        w = hgt = 0
        if k < count:
            w, hgt = size << k, (size << k) >> r.choice([0, 0, 1, 2])
            if r.random() < 0.1:
                w, hgt = r.randrange(4096), r.randrange(4096)
        struct.pack_into("<HHI", h, 0x40 + 8 * k, w, hgt, r.getrandbits(32))
    return h


def _count_levels(r):
    return {"args": [bytes(_levels(r))]}


def _set_picmip(r):
    h = _levels(r)
    return {"args": [bytes(h), HEAP + 0x20], "setup": _picmip_setup(r)}


CASES = [
    case("?Load_GfxTextureLoad@@YAX_N@Z", 0xF1D0, _texture_load),
    case("?Load_GfxImage@@YAX_N@Z", 0xF120, _image),
    case("?Load_GfxImagePtr@@YAX_N@Z", 0xF380, _image_ptr),
    case("?Load_ImageStream@@YAXIPEAUGfxImage@@@Z", 0x4E70, _image_stream, fakes=_stream_fakes(STATE)),
    case("?Image_GetPicmip@@YAXEPEAUPicmip@@@Z", 0xB3C0, _get_picmip, fakes={}),
    case("?sub_14062D6A0@@YAIPEBUGfxImage@@@Z", 0xD6A0, _count_levels, fakes={}, ret="int"),
    case("?sub_14062E430@@YAXPEAUGfxImage@@PEAUPicmip@@@Z", 0xE430, _set_picmip, fakes={}),
    case("?sub_1403723B0@@YAXPEAUGfxImage@@@Z", 0x23B0, lambda r: {"args": [bytes(_levels(r))], "setup": lambda w: ds.M.update(m=w.m)},
         fakes={"?sub_14062E430@@YAXPEAUGfxImage@@PEAUPicmip@@@Z": ds.recorder("sub_14062E430", "qq")}, n=40),
]
