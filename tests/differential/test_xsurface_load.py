"""Differential cases for the XSurface loaders (src/gfx_d3d/r_xsurface_load_db.cpp) against the Store build.

The stream functions are dbstream.py's logged fakes; the D3D11 buffer loaders (Load_VertexBuffer and co., tested on
their own in test_r_buffers.py) are logged fakes that store a recognisable buffer or view, so the order of the
calls, their arguments (sizes, data pointers, debug names) and which stored buffer each view is made from are all
compared. XSurfaceGetVert0Size is faked to return a per-input size, so its use is visible. The vertex union loaders
and the collision tree loader run for real inside Load_XSurface (and have their own cases); the Store-only
subdivision loaders have their own cases. Store layouts only (XSurface is 0xE8 bytes here, 0xC8 in the servers).
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RSP

import dbstream as ds
from dbstream import FOLLOWING, OFF_AUX, OFF_STRUCT, arg, log, u64
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
SURF_SIZE, TREE_SIZE, INFO_SIZE, LEVEL_SIZE = 0xE8, 0x38, 0x38, 0xE8
STATE = {}


def _string(mu, a):
    return ds.M["m"].read_cstr(a) if a else None


def _creator(name, spec, out_tag):
    """A fake D3D buffer or view loader: logs its arguments (s = C string) and stores a tagged handle through its
    first argument."""
    def fake(mu):
        got = []
        for i, k in enumerate(spec):
            v = arg(mu, i) if i < 4 else u64(mu, mu.reg_read(UC_X86_REG_RSP) + 8 + 8 * i)
            got.append(_string(mu, v) if k == "s" else v & {"q": (1 << 64) - 1, "i": 0xFFFFFFFF}[k])
        log(name, *got)
        out = arg(mu, 0)
        STATE["n"] = STATE.get("n", 0) + 1
        if ds.in_buffer(out, 8):
            ds.write(out, struct.pack("<Q", out_tag | STATE["n"]))
    return fake


def _vert0size(mu):
    log("XSurfaceGetVert0Size", arg(mu, 0))
    return STATE["vert0"]


FAKES = {
    **ds.STREAM_FAKES,
    "?Load_VertexBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXH@Z": _creator("Load_VertexBuffer", "qqi", 0xB0000000000),
    "?Load_IndexBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXH@Z": _creator("Load_IndexBuffer", "qqi", 0xB1000000000),
    "?Load_VertexBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@IPEBD@Z":
        _creator("Load_VertexBufferView", "qqis", 0xB2000000000),
    "?Load_IndexBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@IPEBD@Z":
        _creator("Load_IndexBufferView", "qqis", 0xB3000000000),
    "?Load_RawDataBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXIPEBD@Z": _creator("Load_RawDataBuffer", "qqis", 0xB4000000000),
    "?Load_RawDataBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@PEAXIPEBD@Z":
        _creator("Load_RawDataBufferView", "qqqis", 0xB5000000000),
    "?XSurfaceGetVert0Size@@YAHPEBUXSurface@@@Z": _vert0size,
    # the subdivision loader leaves varXSurface on another surface (OFF_AUX, no pointers): Load_XSurface must keep
    # &surf->subdiv from before the call and take everything after it from varXSurface
    "?sub_14035F3A0@@YAX_N@Z": ds.clobbering(
        ds.recorder("sub_14035F3A0", "b", ("unk_144425090", "varXSurface", "g_streamPos")), varXSurface=HEAP + OFF_AUX),
    "?sub_1401B3DC0@@YAXPEAPEAUXSurfaceSubdivInfo@@PEAUXSurface@@@Z": ds.recorder("sub_1401B3DC0", "qq"),
}

SUBDIV_FAKES = {
    **ds.STREAM_FAKES,
    "?sub_14035F430@@YAX_N_K@Z": ds.recorder("sub_14035F430", "bq", ("unk_144425080", "g_streamPos")),
    "?sub_1401B3D60@@YAXPEAUGfxSubdivCache@@@Z": ds.recorder("sub_1401B3D60", "q", ("unk_144425088",)),
}


def case(symbol, seed, make, fakes=FAKES, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in fakes.items() if k != symbol}  # never the function under test itself
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(buf, off, v):
    struct.pack_into("<Q", buf, off, v & 0xFFFFFFFFFFFFFFFF)


def _surface(r):
    s = bytearray(r.randbytes(SURF_SIZE))
    struct.pack_into("<HHHBB", s, 0, r.getrandbits(16), r.choice([0, 1, r.randint(1, 300), 0xFFFF]),
                     r.choice([0, 1, r.randint(1, 500), 0xFFFF]), r.choice([0, 1, r.randint(1, 6), 255]),
                     r.choice([0, 1, 2, 255]))
    struct.pack_into("<8h", s, 8, *[r.choice([0, 0, 1, r.randint(1, 40), -r.randint(1, 3), 0x7FFF]) for _ in range(8)])
    for off in (0x18, 0x20, 0x40, 0x48, 0x50, 0x68, 0x88, 0x90):
        _q(s, off, ds.pointer(r))
    _q(s, 0x80, r.choice([0, 0, FOLLOWING, r.getrandbits(64)]))  # subdiv: any nonzero value is inline
    return s


def _setup(zone, var_values, vert0=None):
    def setup(w):
        zone.start(w)
        STATE["n"] = 0
        if vert0 is not None:
            STATE["vert0"] = vert0
        for name, value in var_values:
            w.u64(va(name), value)
    return setup


def _rigid_feed(r, s):
    """Zone bytes for Load_XSurface up to the rigid vertex lists, laid out as the loader reads them, so that the
    lists (and their collision trees, inline with odd leaf counts) are loaded for real: vertices, triangles, then
    the list array and each inline tree's header, nodes and leafs."""
    vc, tc, rc = struct.unpack_from("<HHB", s, 2)
    feed = bytearray()
    if struct.unpack_from("<Q", s, 0x18)[0] == FOLLOWING:
        feed += r.randbytes(0x20 * vc)
    if struct.unpack_from("<Q", s, 0x20)[0] == FOLLOWING:
        feed += r.randbytes(6 * tc)
    if struct.unpack_from("<Q", s, 0x40)[0] != FOLLOWING:
        return bytes(feed)
    lists, trees = bytearray(), bytearray()
    for _ in range(rc):
        tree = r.choice([FOLLOWING, FOLLOWING, 0, r.getrandbits(64)])
        lists += r.randbytes(8) + struct.pack("<Q", tree)
        if tree == FOLLOWING:
            nodes, leafs = r.choice([0, 1, 3]), r.choice([1, 3, 5, 0])
            header = bytearray(r.randbytes(TREE_SIZE))
            struct.pack_into("<I4xQI4xQ", header, 0x18, nodes, r.choice([0, 1]), leafs, r.choice([0, 1, 1]))
            trees += header
            if struct.unpack_from("<Q", header, 0x20)[0]:
                trees += r.randbytes(0x10 * nodes)
            if struct.unpack_from("<Q", header, 0x30)[0]:
                trees += r.randbytes(2 * leafs)
    return bytes(feed + lists + trees)


def _load_surface(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.5
    s = _surface(r)
    if r.random() < 0.5:  # a surface whose rigid vertex lists and collision trees load inline
        struct.pack_into("<HHB", s, 2, r.randint(0, 60), r.randint(0, 60), r.randint(1, 5))
        _q(s, 0x40, FOLLOWING)
    buf[OFF_STRUCT:OFF_STRUCT + SURF_SIZE] = s
    other = bytearray(SURF_SIZE)  # where the faked subdivision loader leaves varXSurface
    struct.pack_into("<HHHBB8h", other, 0, 0, r.randint(0, 9), r.randint(0, 9), 0, 0, *[r.randint(0, 3) for _ in range(8)])
    buf[OFF_AUX:OFF_AUX + SURF_SIZE] = other
    zone = ds.Zone(r, (bytes(s) if flag else b"") + _rigid_feed(r, s) + r.randbytes(0x2000))
    vert0 = r.choice([0x20, 0x20, 0x18, 7, 0])
    return {"args": [flag, bytes(buf)], "setup": _setup(zone, [("varXSurface", HEAP + OFF_STRUCT)], vert0)}


def _vertex_union(var):
    def make(r):
        buf = bytearray(r.randbytes(ds.BUF_SIZE))
        s = _surface(r)
        buf[OFF_STRUCT:OFF_STRUCT + SURF_SIZE] = s
        zone = ds.Zone(r)
        return {"args": [r.random() < 0.5, bytes(buf)],
                "setup": _setup(zone, [("varXSurface", HEAP + OFF_STRUCT), (var, HEAP + OFF_STRUCT + 0x18)])}
    return make


def _collision_tree(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.5
    t = bytearray(r.randbytes(TREE_SIZE))
    struct.pack_into("<I", t, 0x18, r.choice([0, 1, r.randint(1, 200), 0xFFFFFFFF]))
    struct.pack_into("<I", t, 0x28, r.choice([0, 1, r.randint(1, 200), 0x80000000]))
    _q(t, 0x20, r.choice([0, FOLLOWING, r.getrandbits(64)]))
    _q(t, 0x30, r.choice([0, FOLLOWING, r.getrandbits(64)]))
    buf[OFF_STRUCT:OFF_STRUCT + TREE_SIZE] = t
    zone = ds.Zone(r, (bytes(t) if flag else b"") + r.randbytes(0x2000))
    return {"args": [flag, bytes(buf)], "setup": _setup(zone, [("varXSurfaceCollisionTree", HEAP + OFF_STRUCT)])}


def _subdiv_info(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.5
    info = bytearray(r.randbytes(INFO_SIZE))
    _q(info, 0, r.choice([0, FOLLOWING, r.getrandbits(64)]))
    s = _surface(r)
    buf[OFF_STRUCT:OFF_STRUCT + INFO_SIZE] = info
    buf[OFF_AUX:OFF_AUX + SURF_SIZE] = s
    zone = ds.Zone(r, (bytes(info) if flag else b"") + r.randbytes(0x100))
    return {"args": [flag, bytes(buf)],
            "setup": _setup(zone, [("unk_144425090", HEAP + OFF_STRUCT), ("varXSurface", HEAP + OFF_AUX)])}


def _level(r):
    lv = bytearray(r.randbytes(LEVEL_SIZE))
    struct.pack_into("<17I", lv, 0x8, *[r.choice([0, 1, r.randint(1, 64), r.randint(1, 600), 0xFFFFFFFF,
                                                  0x80000001]) for _ in range(17)])
    _q(lv, 0, ds.pointer(r))
    for off in range(0x50, 0x98, 8):
        _q(lv, off, r.choice([0, 0, FOLLOWING, r.getrandbits(64)]))
    return lv


def _subdiv_levels(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.4
    count = r.choice([0, 1, 1, 2, r.randint(1, 4)])
    levels = b"".join(_level(r) for _ in range(count))
    buf[OFF_STRUCT:OFF_STRUCT + len(levels)] = levels
    s = _surface(r)
    buf[OFF_AUX:OFF_AUX + SURF_SIZE] = s
    zone = ds.Zone(r, (levels if flag else b"") + r.randbytes(0x2000))
    return {"args": [flag, count, bytes(buf)],
            "setup": _setup(zone, [("unk_144425080", HEAP + OFF_STRUCT), ("varXSurface", HEAP + OFF_AUX)])}


def _vert0_size(r):
    return {"args": [r.choice([0, HEAP, r.getrandbits(47)])]}


CASES = [
    case("?Load_XSurface@@YAX_N@Z", 0xEAF0, _load_surface, n=300),
    case("?Load_GfxPackedVertexUnion@@YAX_N@Z", 0xFAC0, _vertex_union("varGfxPackedVertexUnion")),
    case("?Load_GfxPackedMotionVertexUnion@@YAX_N@Z", 0xFA50, _vertex_union("varGfxPackedMotionVertexUnion")),
    case("?Load_XSurfaceCollisionTree@@YAX_N@Z", 0xF2E0, _collision_tree),
    case("?sub_14035F3A0@@YAX_N@Z", 0xF3A0, _subdiv_info, fakes=SUBDIV_FAKES),
    case("?sub_14035F430@@YAX_N_K@Z", 0xF430, _subdiv_levels, fakes=dict(ds.STREAM_FAKES)),
    {"symbol": "?XSurfaceGetVert0Size@@YAHPEBUXSurface@@@Z", "build": STORE, "ret": "int",
     "inputs": [_vert0_size(random.Random(i)) for i in range(40)]},
]
