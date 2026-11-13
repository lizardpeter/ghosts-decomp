"""Differential cases for the physics asset loaders (src/physics/physpreset_load_db.cpp) and the brush loaders they
use (src/qcommon/cm_brush_related_load_db.cpp).

The stream functions are dbstream.py's logged fakes; each loader's callees are logged fakes too, except
Load_cbrushside_tArray, which runs for real under Load_cbrushWrapper_t. PhysPreset, PhysCollmap, PhysGeomInfo and
BrushWrapper have the same layout in the Store build and the servers, so these cases run against both the Store
build and the PS4 reference build (where Load_PhysGeomInfoArray is a function of its own; the Store build inlines it
into Load_PhysCollmap).
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_STRUCT
from harness import HEAP
from syms import va

PRESET_SIZE, COLLMAP_SIZE, GEOM_SIZE, WRAPPER_SIZE, BRUSH_SIZE, SIDE_SIZE = 0x58, 0x58, 0x48, 0x58, 0x30, 0x10

FAKES = {
    **ds.STREAM_FAKES,
    "?Load_PhysPreset@@YAX_N@Z": ds.clobbering(ds.recorder("Load_PhysPreset", "b", ("varPhysPreset", "g_streamPos")),
                                               varPhysPresetPtr=HEAP + ds.OFF_AUX + 0x400),
    "?Load_PhysCollmap@@YAX_N@Z": ds.clobbering(ds.recorder("Load_PhysCollmap", "b", ("varPhysCollmap", "g_streamPos")),
                                                varPhysCollmapPtr=HEAP + ds.OFF_AUX + 0x400),
    "?Load_PhysPresetAsset@@YAXPEAPEAUPhysPreset@@@Z": ds.asset_linker("Load_PhysPresetAsset"),
    "?Load_PhysCollmapAsset@@YAXPEAPEAUPhysCollmap@@@Z": ds.asset_linker("Load_PhysCollmapAsset"),
    "?Load_BrushWrapper@@YAX_N@Z": ds.recorder("Load_BrushWrapper", "b", ("varBrushWrapper", "g_streamPos")),
    "?Load_cbrushWrapper_t@@YAX_N@Z": ds.recorder("Load_cbrushWrapper_t", "b", ("varcbrushWrapper_t", "g_streamPos")),
}


def case(symbol, seed, make, fakes=FAKES, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in fakes.items() if k != symbol}  # never the function under test itself
    return {"symbol": symbol, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(buf, off, v):
    struct.pack_into("<Q", buf, off, v & 0xFFFFFFFFFFFFFFFF)


def _header(size, pointers, counts=(), var=None, extra=()):
    """An input that loads one header of `size` bytes at OFF_STRUCT through `var`: pointer fields (offset ->
    chooser), count fields (offset, format, chooser) and more globals to set (name, value)."""
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.5
        h = bytearray(r.randbytes(size))
        for off, choose in pointers.items():
            _q(h, off, choose(r))
        for off, fmt, choose in counts:
            struct.pack_into(fmt, h, off, choose(r))
        buf[OFF_STRUCT:OFF_STRUCT + size] = h
        zone = ds.Zone(r, (bytes(h) if flag else b"") + r.randbytes(0x2000))
        values = [(name, f(r) if callable(f) else f) for name, f in extra]

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            for name, value in values:
                w.u64(va(name), value)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _any(r):
    return ds.pointer(r)


def _inline(r):
    return r.choice([0, 0, FOLLOWING, r.getrandbits(64)])


def _asset_ptr(var):
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        _q(buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _sides(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.4
    count = r.choice([0, 1, 2, r.randint(1, 20)])
    sides = bytearray(r.randbytes(SIDE_SIZE * count))
    for i in range(count):
        _q(sides, SIDE_SIZE * i, _any(r))
    buf[OFF_STRUCT:OFF_STRUCT + len(sides)] = sides
    zone = ds.Zone(r, (bytes(sides) if flag else b"") + r.randbytes(0x1000))

    def setup(w):
        zone.start(w)
        w.u64(va("varcbrushside_t"), HEAP + OFF_STRUCT)
    return {"args": [flag, count, bytes(buf)], "setup": setup}


def _geoms(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.4
    count = r.choice([0, 1, 2, r.randint(1, 10)])
    geoms = bytearray(r.randbytes(GEOM_SIZE * count))
    for i in range(count):
        _q(geoms, GEOM_SIZE * i, _inline(r))
    buf[OFF_STRUCT:OFF_STRUCT + len(geoms)] = geoms
    zone = ds.Zone(r, (bytes(geoms) if flag else b"") + r.randbytes(0x1000))

    def setup(w):
        zone.start(w)
        w.u64(va("varPhysGeomInfo"), HEAP + OFF_STRUCT)
    return {"args": [flag, count, bytes(buf)], "setup": setup}


def _small(r):
    return r.choice([0, 1, r.randint(1, 30), 0xFFFF])


def _sides_count(r):  # numsides drives a loop: keep it within the emulator's instruction budget
    return r.choice([0, 1, r.randint(1, 30), r.randint(100, 300)])


CASES = [
    case("?Load_PhysPreset@@YAX_N@Z", 0x5500, _header(PRESET_SIZE, {0x00: _any, 0x20: _any}, var="varPhysPreset")),
    case("?Load_PhysPresetPtr@@YAX_N@Z", 0x55F0, _asset_ptr("varPhysPresetPtr")),
    case("?Load_PhysCollmap@@YAX_N@Z", 0x52B0,
         _header(COLLMAP_SIZE, {0x00: _any, 0x10: _inline},
                 [(0x08, "<I", lambda r: r.choice([0, 1, 2, r.randint(1, 12)]))], var="varPhysCollmap")),
    case("?Load_PhysCollmapPtr@@YAX_N@Z", 0x5410, _asset_ptr("varPhysCollmapPtr")),
    case("?Load_PhysGeomInfoArray@@YAX_N_K@Z", 0x81F0, _geoms),
    case("?Load_BrushWrapper@@YAX_N@Z", 0xAF80,
         _header(WRAPPER_SIZE, {0x50: _any}, [(0x18, "<H", _small)], var="varBrushWrapper")),
    case("?Load_cbrushWrapper_t@@YAX_N@Z", 0xF860,
         _header(BRUSH_SIZE, {0x08: _inline, 0x10: _inline}, [(0x00, "<H", _sides_count)], var="varcbrushWrapper_t",
                 extra=[("varBrushWrapper", HEAP + 0x30000)]),
         fakes=dict(ds.STREAM_FAKES)),
    case("?Load_cbrushside_tArray@@YAX_N_K@Z", 0xFA50, _sides, fakes=dict(ds.STREAM_FAKES)),
]
