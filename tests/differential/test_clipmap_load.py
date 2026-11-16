"""Differential cases for the collision map and map entity zone loaders (src/qcommon/cm_load_db.cpp) against the
Store build.

The stream functions are dbstream.py's logged fakes; each loader's callees (the nested Load_* functions,
Load_ScriptStringCustom, Load_cbrushside_tArray) are logged fakes recording the stream variables they see. The
structures are random with small counts, and the zone bytes are laid out as each loader reads them where an element's
contents decide what follows. docs/assets/collision.md; the same logic in tools/fastfile/clipmap.py is checked
against the game on real maps.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, OFF_AUX, OFF_STRUCT
from harness import HEAP

STORE = "iw6mp64_MSStore_ship"


def _rec(name, spec="", globals_=()):
    return ds.recorder(name, spec, globals_)


def _loader(t, *extra):
    return f"?Load_{t}@@YAX_N@Z", _rec(f"Load_{t}", "b", (f"var{t}", "g_streamPos", *extra))


CALLEES = dict([
    _loader("MapTriggers"),
    _loader("ClientTriggers", "varMapTriggers"),
    _loader("ClientTriggerBlend"),
    _loader("SpawnPointEntityRecord"),
    _loader("SpawnPointRecordList"),
    _loader("SplinePointEntityRecord"),
    _loader("SplinePointRecordList"),
    _loader("SplineRecordList"),
    _loader("cbrushside_t", "varcplane_t"),
    _loader("cbrush_t", "varcbrush_array_t"),
    _loader("cLeafBrushNodeLeaf_t", "varcLeafBrushNode_t", "varcLeafBrushNodeData_t"),
    ("?Load_ScriptStringCustom@@YAXPEAW4scr_string_t@@@Z",
     _rec("Load_ScriptStringCustom", "q", ("varscr_string_t", "varSpawnPointEntityRecord"))),
    ("?Load_cbrushside_tArray@@YAX_N_K@Z", ds.array_loader("Load_cbrushside_tArray", "varcbrushside_t", 0x10)),
])
FAKES = {**ds.STREAM_FAKES, **CALLEES}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


# --- helpers -------------------------------------------------------------------------------------------------------

def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & 0xFFFFFFFFFFFFFFFF)


def _get_q(b, off):
    return struct.unpack_from("<Q", b, off)[0]


def _small(r, top=3):
    return r.choice([0, 1, r.randint(0, top), top])


def _inline(r, null=0.25):
    """An always-inline pointer field: null or any non-zero value."""
    return 0 if r.random() < null else r.choice([FOLLOWING, r.getrandbits(64) | 1])


def _input(r, struct_bytes, feed, var_values, aux=None):
    """A buffer with the structure at OFF_STRUCT (and `aux` at OFF_AUX); the zone is the structure (when the loader
    is called with atStreamStart) followed by `feed`."""
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    if aux is not None:
        buf[OFF_AUX:OFF_AUX + len(aux)] = aux
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + bytes(feed) + r.randbytes(0x80))

    def setup(w):
        zone.start(w)
        for name, value in var_values.items():
            w.u64(ds.va(name), value)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _plain(size, var, counts=(), inline=(), pointers=(), feed=0x400):
    """A structure of `size` random bytes with small counts (offset, format, top) and pointer fields that are
    always inline when set (`inline`) or inline-or-offset (`pointers`); the zone after it is random."""
    def make(r):
        s = bytearray(r.randbytes(size))
        for off, fmt, top in counts:
            struct.pack_into(fmt, s, off, _small(r, top))
        for off in inline:
            _q(s, off, _inline(r))
        for off in pointers:
            _q(s, off, ds.pointer(r))
        return _input(r, s, r.randbytes(feed), {var: HEAP + OFF_STRUCT})
    return make


# --- map entities ---------------------------------------------------------------------------------------------------

_map_triggers = _plain(0x30, "varMapTriggers", counts=[(0, "<I", 4), (0x10, "<I", 4), (0x20, "<I", 4)],
                       pointers=(0x08, 0x18, 0x28))

_client_triggers = _plain(0x88, "varClientTriggers", counts=[(0, "<I", 5), (0x30, "<H", 4), (0x40, "<I", 40)],
                          inline=(0x38, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70, 0x78, 0x80),
                          pointers=(0x08, 0x18, 0x28))

_client_trigger_blend = _plain(0x10, "varClientTriggerBlend", counts=[(0, "<H", 4)], inline=(8,))

_spawn_record = _plain(0x28, "varSpawnPointEntityRecord", feed=0x40)

_spawn_list = _plain(0x10, "varSpawnPointRecordList", counts=[(0, "<H", 4)], inline=(8,))

_spline_point = _plain(0x48, "varSplinePointEntityRecord", inline=(0x08, 0x38, 0x40))

_spline_point_list = _plain(0x10, "varSplinePointRecordList", counts=[(0, "<H", 4)], inline=(8,), feed=0x600)

_spline_list = _plain(0x10, "varSplineRecordList", counts=[(0, "<H", 4)], inline=(8,))


def _map_ents(r):
    s = bytearray(r.randbytes(0x100))
    _q(s, 0, ds.pointer(r))
    _q(s, 8, _inline(r))
    struct.pack_into("<i", s, 0x10, _small(r, 60))
    return _input(r, s, r.randbytes(0x100), {"varMapEnts": HEAP + OFF_STRUCT})


# --- brushes and ClipInfo -------------------------------------------------------------------------------------------

_brushside = _plain(0x10, "varcbrushside_t", pointers=(0,), feed=0x40)

_brush = _plain(0x30, "varcbrush_t", pointers=(0x08, 0x10), feed=0x40)


def _leaf(r):
    s = bytearray(8)
    _q(s, 0, ds.pointer(r))
    node = bytearray(r.randbytes(0x18))
    struct.pack_into("<h", node, 2, r.choice([0, 1, _small(r, 6), -1, -0x7FFF]))
    return _input(r, s, r.randbytes(0x40), {"varcLeafBrushNodeLeaf_t": HEAP + OFF_STRUCT,
                                            "varcLeafBrushNode_t": HEAP + OFF_AUX}, aux=node)


def _clip_info(r):
    c = bytearray(r.randbytes(0x80))
    counts = {0x00: 3, 0x10: 3, 0x20: 3, 0x30: 8, 0x40: 3, 0x50: 4}
    for off, top in counts.items():
        struct.pack_into("<I", c, off, _small(r, top))
    struct.pack_into("<H", c, 0x60, _small(r, 3))
    for off in (0x08, 0x18, 0x28, 0x38, 0x48, 0x58, 0x68, 0x70, 0x78):
        _q(c, off, ds.pointer(r))
    feed = bytearray()
    if _get_q(c, 0x08) == FOLLOWING:
        feed += r.randbytes(0x14 * struct.unpack_from("<I", c, 0)[0])
    if _get_q(c, 0x18) == FOLLOWING:
        # the materials, then each one's name as the XString fake reads it (a length byte and the letters)
        for _ in range(struct.unpack_from("<I", c, 0x10)[0]):
            m = bytearray(r.randbytes(0x10))
            _q(m, 0, ds.pointer(r))
            feed += m
    return _input(r, c, feed + r.randbytes(0x800), {"varClipInfo": HEAP + OFF_STRUCT})


CASES = [
    case("?Load_MapTriggers@@YAX_N@Z", 0x2E40, _map_triggers),
    case("?Load_ClientTriggers@@YAX_N@Z", 0xB0A0, _client_triggers),
    case("?Load_ClientTriggerBlend@@YAX_N@Z", 0xB030, _client_trigger_blend),
    case("?Load_SpawnPointEntityRecord@@YAX_N@Z", 0x7100, _spawn_record),
    case("?Load_SpawnPointRecordList@@YAX_N@Z", 0x71A0, _spawn_list),
    case("?Load_SplinePointEntityRecord@@YAX_N@Z", 0x72D0, _spline_point),
    case("?Load_SplinePointRecordList@@YAX_N@Z", 0x73B0, _spline_point_list),
    case("?Load_SplineRecordList@@YAX_N@Z", 0x7460, _spline_list),
    case("?Load_MapEnts@@YAX_N@Z", 0x2C10, _map_ents),
    case("?Load_cbrushside_t@@YAX_N@Z", 0xF9D0, _brushside),
    case("?Load_cbrush_t@@YAX_N@Z", 0xF900, _brush),
    case("?Load_cLeafBrushNodeLeaf_t@@YAX_N@Z", 0xF7D0, _leaf),
    case("?Load_ClipInfo@@YAX_N@Z", 0xB360, _clip_info),
]
