"""Differential cases for the XModel loaders (src/xanim/xmodel_load_db.cpp) against the Store build.

Each loader runs on its own: the stream functions are dbstream.py's logged fakes, and the loaders it calls are
logged fakes too (Load_XModelSurfsPtr, Load_PhysPresetPtr, ...), except the small fixups, which run for real. Inputs
draw every pointer field from null / inline / insert / offset, counts from small values and edge cases (numRootBones
greater than numBones, negative numCollSurfs), and atStreamStart both ways. The XModel layout is the Store build's
(0x258 bytes; the servers' is 0x228), so the cases are for the Store build only.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT, arg, log, u64
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
XMODEL_SIZE, LOD_SIZE, SURFS_SIZE = 0x258, 0x40, 0x38


def _surfs_ptr_fake(mu):
    """Load_XModelSurfsPtr: logs, then leaves *varXModelSurfsPtr null or pointing at an XModelSurfs in OFF_AUX,
    chosen by the value found, for Load_XModelSurfsFixup to read."""
    p = ds.get_global("varXModelSurfsPtr")
    v = u64(mu, p)
    log("Load_XModelSurfsPtr", arg(mu, 0) & 0xFF, p, v)
    target = 0 if v % 5 == 0 else HEAP + OFF_AUX + SURFS_SIZE * (v % 7)
    ds.write(p, struct.pack("<Q", target))


FAKES = {
    **ds.STREAM_FAKES,
    "?Load_scr_string_tArray@@YAX_N_K@Z": ds.array_loader("Load_scr_string_tArray", "varscr_string_t", 4),
    "?Load_MaterialHandleArray@@YAX_N_K@Z": ds.array_loader("Load_MaterialHandleArray", "varMaterialHandle", 8),
    "?Load_XModelSurfsPtr@@YAX_N@Z": _surfs_ptr_fake,
    "?Load_PhysPresetPtr@@YAX_N@Z": ds.recorder("Load_PhysPresetPtr", "b", ("varPhysPresetPtr",), ("varPhysPresetPtr",)),
    "?Load_PhysCollmapPtr@@YAX_N@Z": ds.recorder("Load_PhysCollmapPtr", "b", ("varPhysCollmapPtr",),
                                                  ("varPhysCollmapPtr",)),
    # the nested loaders overwrite the pointer variables, as loading a nested asset can: the callers must use the
    # slot they saved, not re-read the global
    "?Load_XModel@@YAX_N@Z": ds.clobbering(ds.recorder("Load_XModel", "b", ("varXModel", "g_streamPos")),
                                           varXModelPtr=HEAP + OFF_AUX + 0x400, varXModel=HEAP + OFF_AUX + 0x500),
    "?Load_XModelSurfs@@YAX_N@Z": ds.clobbering(ds.recorder("Load_XModelSurfs", "b", ("varXModelSurfs", "g_streamPos")),
                                                varXModelSurfsPtr=HEAP + OFF_AUX + 0x400),
    "?Load_XSurface@@YAX_N@Z": ds.recorder("Load_XSurface", "b", ("varXSurface",)),
    "?Load_XModelAsset@@YAXPEAPEAUXModel@@@Z": ds.asset_linker("Load_XModelAsset"),
    "?Load_XModelSurfsAsset@@YAXPEAPEAUXModelSurfs@@@Z": ds.asset_linker("Load_XModelSurfsAsset"),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}  # never the function under test itself
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _buffer(r):
    return bytearray(r.randbytes(ds.BUF_SIZE))


def _q(buf, off, v):
    struct.pack_into("<Q", buf, off, v & 0xFFFFFFFFFFFFFFFF)


def _xmodel(r):
    m = bytearray(r.randbytes(XMODEL_SIZE))
    bones = r.choice([0, 1, 2, r.randint(1, 40), 255])
    roots = r.choice([0, 1, min(bones, r.randint(0, 3)), bones, bones + r.randint(1, 3)]) & 0xFF
    m[8], m[9], m[10], m[11] = bones, roots, r.choice([0, 1, r.randint(1, 30), 255]), r.choice([0, 1, r.randint(0, 9)])
    for off in (0x00, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58, 0x60):
        _q(m, off, ds.pointer(r))
    for off in (0x68, 0x1F8, 0x208, 0x230):  # always-inline arrays: any nonzero value means "follows"
        _q(m, off, r.choice([0, 0, FOLLOWING, r.getrandbits(64)]))
    struct.pack_into("<i", m, 0x1F4, r.choice([0, 1, r.randint(1, 50), -1, -r.randint(1, 5)]))
    for lod in range(6):
        _q(m, 0x70 + LOD_SIZE * lod + 8, r.choice([0, FOLLOWING, INSERT, r.getrandbits(64)]))
    return m


def _load_xmodel(r):
    buf, flag = _buffer(r), r.random() < 0.5
    m = _xmodel(r)
    buf[OFF_STRUCT:OFF_STRUCT + XMODEL_SIZE] = m
    zone = ds.Zone(r, (bytes(m) if flag else b"") + r.randbytes(0x2000))

    def setup(w):
        zone.start(w)
        w.u64(va("varXModel"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _asset_ptr(var, target_var):
    def make(r):
        buf, flag = _buffer(r), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        _q(buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))
        stale = HEAP + 0x30000 + r.getrandbits(8)

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            w.u64(va(target_var), stale)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _asset_ptr_array(r):
    buf, flag, count = _buffer(r), r.random() < 0.3, r.choice([0, 1, 2, r.randint(1, 12)])
    values = [r.choice([0, FOLLOWING, INSERT, r.getrandbits(64)]) for _ in range(count)]
    for i, v in enumerate(values):
        _q(buf, OFF_STRUCT + 8 * i, v)
    zone = ds.Zone(r, (b"".join(struct.pack("<Q", v) for v in values) if flag else b"") + r.randbytes(0x100))

    def setup(w):
        zone.start(w)
        w.u64(va("varXModelPtr"), HEAP + OFF_STRUCT)
    return {"args": [flag, count, bytes(buf)], "setup": setup}


def _load_surfs(r):
    buf, flag = _buffer(r), r.random() < 0.5
    s = bytearray(r.randbytes(SURFS_SIZE))
    _q(s, 0, ds.pointer(r))
    _q(s, 8, r.choice([0, FOLLOWING, r.getrandbits(64)]))
    struct.pack_into("<H", s, 0x10, r.choice([0, 1, r.randint(1, 12), 60]))
    buf[OFF_STRUCT:OFF_STRUCT + SURFS_SIZE] = s
    zone = ds.Zone(r, (bytes(s) if flag else b"") + r.randbytes(0x2000))

    def setup(w):
        zone.start(w)
        w.u64(va("varXModelSurfs"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _surfs_fixup(r):
    buf = _buffer(r)
    target = r.choice([0, HEAP + OFF_AUX])
    _q(buf, OFF_STRUCT, target)
    return {"args": [HEAP + OFF_STRUCT, HEAP + 0x100, bytes(buf)]}


def _db_surfs_fixup(r):
    buf = _buffer(r)
    m = bytearray(r.randbytes(XMODEL_SIZE))
    m[0x1F1] = r.choice([0, 1, 2, 6, r.randint(1, 6), 0x80, 0xFF])
    default = HEAP + 0x30000
    for lod in range(6):
        surfs = HEAP + OFF_AUX + SURFS_SIZE * lod
        _q(m, 0x70 + LOD_SIZE * lod + 8, surfs if r.random() < 0.95 else 0)
        aux = bytearray(r.randbytes(SURFS_SIZE))
        if r.random() < 0.3:
            _q(aux, 8, default)
        struct.pack_into("<H", aux, 0x10, r.choice([0, 1, r.randint(1, 60), 0xFFFF]))
        buf[OFF_AUX + SURFS_SIZE * lod:OFF_AUX + SURFS_SIZE * (lod + 1)] = aux
    buf[OFF_STRUCT:OFF_STRUCT + XMODEL_SIZE] = m

    def setup(w):
        w.u64(va("g_defaultSurfs"), default)
    return {"args": [HEAP + OFF_STRUCT, r.getrandbits(64), bytes(buf)], "setup": setup}


CASES = [
    case("?Load_XModel@@YAX_N@Z", 0xE020, _load_xmodel, n=300),
    case("?Load_XModelPtr@@YAX_N@Z", 0xE530, _asset_ptr("varXModelPtr", "varXModel")),
    case("?Load_XModelPtrArray@@YAX_N_K@Z", 0xE620, _asset_ptr_array),
    case("?Load_XModelSurfs@@YAX_N@Z", 0xE750, _load_surfs),
    case("?Load_XModelSurfsPtr@@YAX_N@Z", 0xE860, _asset_ptr("varXModelSurfsPtr", "varXModelSurfs")),
    case("?Load_XModelSurfsFixup@@YAXPEAPEAUXModelSurfs@@PEAUXModelLodInfo@@@Z", 0x4250, _surfs_fixup),
    case("?DB_XModelSurfsFixup@@YAXTXAssetHeader@@PEAX@Z", 0x12F0, _db_surfs_fixup),
]
