"""Differential cases for the Store-only subdivision buffer code (src/gfx_d3d/r_subdiv.cpp) against the Store build.

The buffer creators are logged fakes (arguments, C strings by content, stack arguments included) that hand back
recognisable buffer and view handles, so every call, its order and where each handle is stored are compared.
R_ReleaseBuffer is a logged fake too. Inputs: a surface with 0..3 subdivision levels whose counts and array pointers
vary (zero counts, null cone arrays, patch flags with bits 8 and 9), the info's "converted" flag on or off, and
r_loadForRenderer on or off.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RSP

import dbstream as ds
from dbstream import arg, log, u64
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
SURF, INFO, LEVELS, ARRAYS = 0x0, 0x100, 0x200, 0x2000
STATE = {}


def _stack(mu, i):
    return u64(mu, mu.reg_read(UC_X86_REG_RSP) + 8 + 8 * i)


def _str(a):
    return ds.M["m"].read_cstr(a) if a else None


def _handle(out, tag):
    STATE["n"] = STATE.get("n", 0) + 1
    if ds.in_buffer(out, 8):
        ds.write(out, struct.pack("<Q", tag | STATE["n"]))


def _create(mu):  # sub_1401AC310(bytes, bindFlags, usage, data, name, &buffer)
    out = _stack(mu, 5)
    log("sub_1401AC310", arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF, arg(mu, 2) & 0xFFFFFFFF, arg(mu, 3),
        _str(_stack(mu, 4)), out if ds.in_buffer(out, 8) else "a local")  # locals sit at different stack offsets
    STATE["n"] = STATE.get("n", 0) + 1
    ds.write(out, struct.pack("<Q", 0xC10000000000 | STATE["n"]))  # a local of the caller: stack, plain write


def _view(name, tag):
    def fake(mu):
        log(name, arg(mu, 0), _str(arg(mu, 1)), arg(mu, 2))
        _handle(arg(mu, 2), tag)
    return fake


def _index_buffer(mu):  # sub_140601970(&ib, size, data, name)
    log("sub_140601970", arg(mu, 0), arg(mu, 1) & 0xFFFFFFFF, arg(mu, 2), _str(arg(mu, 3)))
    _handle(arg(mu, 0), 0xC30000000000)


FAKES = {
    "?sub_1401AC310@@YAXIIW4D3D11_USAGE@@PEBXPEBDPEAPEAUID3D11Buffer@@@Z": _create,
    "?sub_1401AC3F0@@YAXPEAUID3D11Buffer@@PEBDPEAPEAUID3D11ShaderResourceView@@@Z": _view("sub_1401AC3F0", 0xC40000000000),
    "?sub_1401AC380@@YAXPEAUID3D11Buffer@@PEBDPEAPEAUID3D11UnorderedAccessView@@@Z": _view("sub_1401AC380", 0xC50000000000),
    "?sub_140601970@@YAXPEAPEAUID3D11Buffer@@HPEBX@Z": _index_buffer,
    "?R_ReleaseBuffer@@YAJPEAUID3D11Buffer@@@Z": ds.recorder("R_ReleaseBuffer", "q", ret=0),
    "?sub_1401AC0E0@@YAXPEAPEAUID3D11ShaderResourceView@@@Z": ds.recorder("sub_1401AC0E0", "q"),
    "?sub_1401B4100@@YAXPEAUXSurface@@@Z": ds.recorder("sub_1401B4100", "q"),
}


def case(symbol, seed, make, n=200, fakes=FAKES):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in fakes.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _dvar_setup(on):
    def setup(w):
        ds.M["m"] = w.m
        STATE["n"] = 0
        dvar = w.alloc(struct.pack("<QIBB2x", 0, 0, 0, 0) + struct.pack("<I", 1 if on else 0) + bytes(0x50))
        w.u64(va("r_loadForRenderer"), dvar)
    return setup


def _count(r):
    return r.choice([0, 0, 1, r.randint(1, 12), r.randint(100, 300)])


def _surface(r):
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    levels = r.choice([0, 1, 1, 2, 3])
    struct.pack_into("<B", buf, SURF + 7, levels)
    struct.pack_into("<Q", buf, SURF + 0x80, HEAP + INFO)
    struct.pack_into("<QI", buf, INFO, HEAP + LEVELS, r.getrandbits(32) & ~4 if r.random() < 0.6 else 4)
    for i in range(levels):
        lv = LEVELS + 0xE8 * i
        counts = [_count(r) for _ in range(17)]
        counts[1] = r.choice([0, 1, r.randint(1, 40)])          # regularPatchCount drives a loop
        struct.pack_into("<17I", buf, lv + 8, *counts)
        for k, off in enumerate(range(0x50, 0x98, 8)):
            struct.pack_into("<Q", buf, lv + off, HEAP + ARRAYS + 0x1000 * i + 0x100 * k)
        if r.random() < 0.3:
            struct.pack_into("<Q", buf, lv + 0x90, 0)             # no cones
        flags = HEAP + ARRAYS + 0x1000 * i + 0x100
        for k in range(counts[1]):
            struct.pack_into("<I", buf, flags - HEAP + 4 * k, r.choice([0x100, 0x200, 0x300, r.getrandbits(32)]))
    return buf


def _build(r):
    buf, on = _surface(r), r.random() < 0.8
    return {"args": [HEAP + SURF, bytes(buf)], "setup": _dvar_setup(on)}


def _build_via_info(r):
    buf, on = _surface(r), r.random() < 0.8
    return {"args": [HEAP + SURF + 0x80, HEAP + SURF, bytes(buf)], "setup": _dvar_setup(on)}


def _cache(r):
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    struct.pack_into("<I", buf, 0, r.choice([0, 0, 0x100, r.getrandbits(32)]))
    return {"args": [HEAP, bytes(buf)], "setup": _dvar_setup(True)}


def _release(r):
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    struct.pack_into("<Q", buf, 0, r.choice([0, r.getrandbits(64)]))
    return {"args": [HEAP, bytes(buf)], "setup": _dvar_setup(True)}


CASES = [
    case("?sub_1401B4100@@YAXPEAUXSurface@@@Z", 0x4100, _build, n=300),
    case("?sub_1401B3DC0@@YAXPEAPEAUXSurfaceSubdivInfo@@PEAUXSurface@@@Z", 0x3DC0, _build_via_info, n=60),
    case("?sub_1401B3D60@@YAXPEAUGfxSubdivCache@@@Z", 0x3D60, _cache, n=60),
    case("?sub_1401AC5B0@@YAXPEAPEAUID3D11Buffer@@@Z", 0xC5B0, _release, n=60),
]
