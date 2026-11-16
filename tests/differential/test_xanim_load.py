"""Differential cases for the animation zone loaders (src/xanim/xanim_load_db.cpp) against the Store build.

The stream functions are dbstream.py's logged fakes; each loader's callees (the nested Load_* functions,
Load_scr_string_tArray, Load_ScriptStringCustom, Load_XAnimPartsAsset) are logged fakes recording the stream
variables they see. Structures are random with small counts, both frame-count regimes (under and from 256 frames,
which switch the index tables between bytes and u16), sizes of 0 (frame0 instead of frames), and counts with the top
bit set. docs/assets/animations.md; tools/fastfile/xanim.py is the same logic, checked
against the game on real zones.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
PARTS = HEAP + OFF_AUX            # an XAnimParts header the inner loaders read numframes from
PART = HEAP + OFF_AUX + 0x100     # a trans / quat2 / quat part the inner loaders read size and smallTrans from


def _rec(name, *globals_):
    return ds.recorder(name, "b", globals_)


FAKES = {
    **ds.STREAM_FAKES,
    "?Load_scr_string_tArray@@YAX_N_K@Z": ds.array_loader("Load_scr_string_tArray", "varscr_string_t", 4),
    "?Load_ScriptStringCustom@@YAXPEAW4scr_string_t@@@Z":
        ds.recorder("Load_ScriptStringCustom", "q", ("varscr_string_t", "varXAnimNotifyInfo")),
    "?Load_XAnimIndices@@YAX_N@Z": _rec("Load_XAnimIndices", "varXAnimIndices", "g_streamPos"),
    "?Load_XAnimDynamicIndicesTrans@@YAX_N@Z": _rec("Load_XAnimDynamicIndicesTrans", "varXAnimDynamicIndicesTrans",
                                                    "g_streamPos"),
    "?Load_XAnimDynamicIndicesDeltaQuat2@@YAX_N@Z": _rec("Load_XAnimDynamicIndicesDeltaQuat2",
                                                         "varXAnimDynamicIndicesDeltaQuat2", "g_streamPos"),
    "?Load_XAnimDynamicIndicesDeltaQuat@@YAX_N@Z": _rec("Load_XAnimDynamicIndicesDeltaQuat",
                                                        "varXAnimDynamicIndicesDeltaQuat", "g_streamPos"),
    "?Load_XAnimDynamicFrames@@YAX_N@Z": _rec("Load_XAnimDynamicFrames", "varXAnimDynamicFrames",
                                              "varXAnimPartTransFrames", "g_streamPos"),
    "?Load_XAnimPartTrans@@YAX_N@Z": _rec("Load_XAnimPartTrans", "varXAnimPartTrans", "g_streamPos"),
    "?Load_XAnimDeltaPartQuatDataFrames2@@YAX_N@Z": _rec("Load_XAnimDeltaPartQuatDataFrames2",
                                                         "varXAnimDeltaPartQuatDataFrames2", "varXAnimDeltaPartQuat2",
                                                         "g_streamPos"),
    "?Load_XAnimDeltaPartQuatDataFrames@@YAX_N@Z": _rec("Load_XAnimDeltaPartQuatDataFrames",
                                                        "varXAnimDeltaPartQuatDataFrames", "varXAnimDeltaPartQuat",
                                                        "g_streamPos"),
    "?Load_XAnimDeltaPart@@YAX_N@Z": _rec("Load_XAnimDeltaPart", "varXAnimDeltaPart", "g_streamPos"),
    "?Load_XAnimParts@@YAX_N@Z": ds.clobbering(_rec("Load_XAnimParts", "varXAnimParts", "g_streamPos"),
                                               varXAnimPartsPtr=HEAP + OFF_AUX + 0x400,
                                               varXAnimParts=HEAP + OFF_AUX + 0x500),
    "?Load_XAnimPartsAsset@@YAXPEAPEAUXAnimParts@@@Z": ds.asset_linker("Load_XAnimPartsAsset"),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & 0xFFFFFFFFFFFFFFFF)


def _inline(r, null=0.3):
    """An always-inline pointer field: null or any non-zero value."""
    return 0 if r.random() < null else r.choice([FOLLOWING, r.getrandbits(64) | 1])


def _numframes(r):
    return r.choice([0, 1, r.randint(2, 255), 255, 256, r.randint(256, 2000)])


def _size(r):
    return r.choice([0, 0, 1, r.randint(1, 40), 0xFF, 0x100])


def _input(r, struct_bytes, var_values, aux=None, feed=0x2000, flag=None):
    """A buffer with the structure at OFF_STRUCT (and `aux` at OFF_AUX); the zone is the structure (when the loader
    is called with atStreamStart) followed by random bytes."""
    flag = r.random() < 0.5 if flag is None else flag
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    if aux is not None:
        buf[OFF_AUX:OFF_AUX + len(aux)] = aux
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + r.randbytes(feed))

    def setup(w):
        zone.start(w)
        for name, value in var_values.items():
            w.u64(va(name), value)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _aux(r):
    """An XAnimParts header (numframes at +0x12, indexCount at +0x28) at OFF_AUX and a part (size, smallTrans) at
    +0x100."""
    a = bytearray(r.randbytes(0x200))
    struct.pack_into("<H", a, 0x12, _numframes(r))
    struct.pack_into("<I", a, 0x28, r.choice([0, 1, r.randint(1, 300), 0x800]))
    struct.pack_into("<H", a, 0x100, _size(r))
    a[0x102] = r.choice([0, 1, r.getrandbits(8)])
    return a


def _indices(r):
    s = bytearray(8)
    _q(s, 0, _inline(r))
    return _input(r, s, {"varXAnimIndices": HEAP + OFF_STRUCT, "varXAnimParts": PARTS}, aux=_aux(r))


def _dynamic_indices(var, part_var):
    def make(r):
        return _input(r, r.randbytes(2), {var: HEAP + OFF_STRUCT, "varXAnimParts": PARTS, part_var: PART},
                      aux=_aux(r))
    return make


def _dynamic_frames(r):
    s = bytearray(8)
    _q(s, 0, _inline(r))
    return _input(r, s, {"varXAnimDynamicFrames": HEAP + OFF_STRUCT, "varXAnimPartTrans": PART}, aux=_aux(r))


def _part_trans(r):
    s = bytearray(r.randbytes(0x30))
    struct.pack_into("<H", s, 0, _size(r))
    return _input(r, s, {"varXAnimPartTrans": HEAP + OFF_STRUCT})


def _quat_frames(var, part_var):
    def make(r):
        s = bytearray(r.randbytes(0x10))
        _q(s, 0, _inline(r))
        return _input(r, s, {var: HEAP + OFF_STRUCT, part_var: PART}, aux=_aux(r))
    return make


def _delta_part(r):
    s = bytearray(0x18)
    for off in (0, 8, 0x10):
        _q(s, off, _inline(r))
    # the 8-byte quat2 / quat headers the loader reads from the zone after aligning: their size decides frame0 or
    # frames, so the zone starts (after the 0x18 header when loaded at the stream start) with a few candidates
    feed = b"".join(struct.pack("<HHI", _size(r), r.getrandbits(16), r.getrandbits(32)) for _ in range(64))
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + 0x18] = s
    zone = ds.Zone(r, (bytes(s) if flag else b"") + feed + r.randbytes(0x400))

    def setup(w):
        zone.start(w)
        w.u64(va("varXAnimDeltaPart"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _parts(r):
    p = bytearray(r.randbytes(0x88))
    _q(p, 0, ds.pointer(r))
    struct.pack_into("<H", p, 8, r.choice([0, 1, r.randint(1, 200), 0xFFFF, 0x8001]))
    for off, top in ((0xA, 200), (0xC, 100), (0xE, 200), (0x10, 50), (0x12, 2000)):
        struct.pack_into("<H", p, off, r.choice([0, 1, r.randint(0, top)]))
    p[0x1E] = r.choice([0, 1, r.randint(0, 40)])        # boneCount[9]
    p[0x1F] = r.choice([0, 1, r.randint(0, 6)])         # notifyCount
    struct.pack_into("<I", p, 0x24, r.choice([0, 1, r.randint(0, 300)]))
    for off in range(0x38, 0x88, 8):
        if off != 0x70:
            _q(p, off, _inline(r))
    return _input(r, p, {"varXAnimParts": HEAP + OFF_STRUCT})


def _parts_ptr(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
    value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
    _q(buf, OFF_STRUCT, value)
    zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))
    stale = HEAP + 0x30000 + r.getrandbits(8)

    def setup(w):
        zone.start(w)
        w.u64(va("varXAnimPartsPtr"), HEAP + OFF_STRUCT)
        w.u64(va("varXAnimParts"), stale)
    return {"args": [flag, bytes(buf)], "setup": setup}


CASES = [
    case("?Load_XAnimIndices@@YAX_N@Z", 0xCF10, _indices),
    case("?Load_XAnimDynamicIndicesTrans@@YAX_N@Z", 0xCE90,
         _dynamic_indices("varXAnimDynamicIndicesTrans", "varXAnimPartTrans")),
    case("?Load_XAnimDynamicIndicesDeltaQuat2@@YAX_N@Z", 0xCD90,
         _dynamic_indices("varXAnimDynamicIndicesDeltaQuat2", "varXAnimDeltaPartQuat2")),
    case("?Load_XAnimDynamicIndicesDeltaQuat@@YAX_N@Z", 0xCE10,
         _dynamic_indices("varXAnimDynamicIndicesDeltaQuat", "varXAnimDeltaPartQuat")),
    case("?Load_XAnimDynamicFrames@@YAX_N@Z", 0xCCE0, _dynamic_frames),
    case("?Load_XAnimPartTrans@@YAX_N@Z", 0xCFA0, _part_trans),
    case("?Load_XAnimDeltaPartQuatDataFrames2@@YAX_N@Z", 0xCBA0,
         _quat_frames("varXAnimDeltaPartQuatDataFrames2", "varXAnimDeltaPartQuat2")),
    case("?Load_XAnimDeltaPartQuatDataFrames@@YAX_N@Z", 0xCC40,
         _quat_frames("varXAnimDeltaPartQuatDataFrames", "varXAnimDeltaPartQuat")),
    case("?Load_XAnimDeltaPart@@YAX_N@Z", 0xCA20, _delta_part),
    case("?Load_XAnimParts@@YAX_N@Z", 0xD040, _parts),
    case("?Load_XAnimPartsPtr@@YAX_N@Z", 0xD3D0, _parts_ptr),
]
