"""Differential cases for the GfxWorld zone loaders (src/gfx_d3d/r_gfx_world_load_db.cpp) against the Store build.

The stream functions are dbstream.py's logged fakes; each loader's callees (the nested Load_* functions, the image,
material and model pointer loaders, the GPU buffer creators) are logged fakes recording the stream variables they
see. The structures are random with small counts, and the zone bytes are laid out as each loader reads them (an
element's counts and pointers decide what follows), so loops run a few times and nested arrays load for real.
docs/assets/world.md; the same logic in tools/fastfile/gfxworld.py is checked against the game on real maps.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT
from harness import HEAP

STORE = "iw6mp64_MSStore_ship"
WORLD = HEAP + OFF_AUX            # the GfxWorld whose counts the nested loaders read (varGfxWorld)
WORLD_AT = OFF_AUX


def _rec(name, spec="", globals_=(), ret=None):
    return ds.recorder(name, spec, globals_, ret=ret)


def _view(mu):
    """Load_VertexBufferView(view, vb, size, name): the name logged as text (its address differs per build)."""
    name = ds.arg(mu, 3)
    text = bytes(mu.mem_read(name, 32)).split(b"\0")[0] if name else None
    ds.log("Load_VertexBufferView", ds.arg(mu, 0), ds.arg(mu, 1), ds.arg(mu, 2) & 0xFFFFFFFF, text)


CALLEES = {
    "?Load_GfxImagePtr@@YAX_N@Z": _rec("Load_GfxImagePtr", "b", ("varGfxImagePtr", "g_streamPos")),
    "?Load_MaterialHandle@@YAX_N@Z": _rec("Load_MaterialHandle", "b", ("varMaterialHandle", "g_streamPos")),
    "?Load_XModelPtr@@YAX_N@Z": _rec("Load_XModelPtr", "b", ("varXModelPtr", "g_streamPos")),
    "?Load_VertexBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXH@Z": _rec("Load_VertexBuffer", "qqi"),
    "?Load_IndexBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXH@Z": _rec("Load_IndexBuffer", "qqi"),
    "?Load_VertexBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@IPEBD@Z": _view,
    "?sub_1401B3D60@@YAXPEAUGfxSubdivCache@@@Z": _rec("sub_1401B3D60", "q", ("unk_144425088",)),
    "?sub_1406B8020@@YAHPEAPEAXPEAX_K@Z": _rec("sub_1406B8020", "qqq", ret=0),
    "?Load_GfxWorldAsset@@YAXPEAPEAUGfxWorld@@@Z": ds.asset_linker("Load_GfxWorldAsset"),
    # nested loaders, for the tests of their callers
    "?Load_GfxWorldDpvsPlanes@@YAX_N@Z": _rec("Load_GfxWorldDpvsPlanes", "b", ("varGfxWorldDpvsPlanes", "g_streamPos")),
    "?Load_GfxCellTree@@YAX_N@Z": _rec("Load_GfxCellTree", "b", ("varGfxCellTree", "g_streamPos")),
    "?Load_GfxCell@@YAX_N@Z": _rec("Load_GfxCell", "b", ("varGfxCell", "g_streamPos")),
    "?Load_GfxWorldDraw@@YAX_N@Z": _rec("Load_GfxWorldDraw", "b", ("varGfxWorldDraw", "g_streamPos")),
    "?Load_GfxWorldVertexData0@@YAX_N@Z": _rec("Load_GfxWorldVertexData0", "b", ("varGfxWorldVertexData0",)),
    "?Load_GfxWorldVertexLayerData@@YAX_N@Z": _rec("Load_GfxWorldVertexLayerData", "b", ("varGfxWorldVertexLayerData",)),
    "?Load_GfxLightGrid@@YAX_N@Z": _rec("Load_GfxLightGrid", "b", ("varGfxLightGrid", "g_streamPos")),
    "?Load_GfxLightGridTree@@YAX_N@Z": _rec("Load_GfxLightGridTree", "b", ("varGfxLightGridTree",)),
    "?Load_GfxShadowGeometryArray@@YAX_N_K@Z": _rec("Load_GfxShadowGeometryArray", "bq", ("varGfxShadowGeometry",)),
    "?Load_GfxLightRegion@@YAX_N@Z": _rec("Load_GfxLightRegion", "b", ("varGfxLightRegion",)),
    "?Load_GfxStaticModelVertexLightingInfo@@YAX_N@Z":
        _rec("Load_GfxStaticModelVertexLightingInfo", "b", ("varGfxStaticModelVertexLightingInfo", "g_streamPos")),
    "?sub_140361E10@@YAX_N_K@Z": _rec("sub_140361E10", "bq", ("varGfxConstantBufferPtr", "g_streamPos")),
    "?Load_GfxWorldDpvsStatic@@YAX_N@Z": _rec("Load_GfxWorldDpvsStatic", "b", ("varGfxWorldDpvsStatic", "g_streamPos")),
    "?Load_GfxWorldDpvsDynamic@@YAX_N@Z": _rec("Load_GfxWorldDpvsDynamic", "b", ("varGfxWorldDpvsDynamic",)),
    "?sub_1401B7180@@YAXPEAPEAXPEAXI@Z": _rec("sub_1401B7180", "qqi", ("varUmbraTome",)),
    "?Load_GfxWorld@@YAX_N@Z": ds.clobbering(_rec("Load_GfxWorld", "b", ("varGfxWorld", "g_streamPos")),
                                             varGfxWorldPtr=HEAP + OFF_AUX + 0x1000),
}
FAKES = {**ds.STREAM_FAKES, **CALLEES}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


# --- helpers -------------------------------------------------------------------------------------------------------

def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & 0xFFFFFFFFFFFFFFFF)


def _u32(b, off, v):
    struct.pack_into("<I", b, off, v & 0xFFFFFFFF)


def _ptr(r, null=0.25):
    """An always-inline pointer field: null or any non-zero value."""
    return 0 if r.random() < null else r.choice([FOLLOWING, INSERT, r.getrandbits(64) | 1])


def _small(r, top=3):
    return r.choice([0, 1, r.randint(0, top), top])


def _input(r, struct_bytes, feed, var_values, extra_args=()):
    """A buffer with the structure at OFF_STRUCT and a GfxWorld at OFF_AUX; the zone is the structure (when the
    loader is called with atStreamStart) followed by `feed`."""
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    world = var_values.pop("_world", None)
    if world is not None:
        buf[WORLD_AT:WORLD_AT + len(world)] = world
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + bytes(feed) + r.randbytes(0x40))

    def setup(w):
        zone.start(w)
        for name, value in var_values.items():
            w.u64(ds.va(name), value)
    return {"args": [flag, *extra_args, bytes(buf)], "setup": setup}


def _world(r, **counts):
    w = bytearray(r.randbytes(0xA30))
    defaults = {"planeCount": 0x14, "nodeCount": 0x18, "surfaceCount": 0x1C, "skyCount": 0x20,
                "lastSun": 0x30, "primaryLights": 0x34, "cellCount": 0x50, "modelCount": 0x758,
                "materialMemoryCount": 0x784, "dynClients0": 0x9C0, "dynClients1": 0x9C4, "heroLights": 0xA0C,
                "tomeSize": 0xA1C}
    for name, off in defaults.items():
        _u32(w, off, counts.get(name, _small(r)))
    return w


# --- Load_GfxWorldDpvsPlanes ---------------------------------------------------------------------------------------

def _dpvs_planes(r):
    s = bytearray(r.randbytes(0x20))
    _u32(s, 0, _small(r, 2))                                     # cellCount (<< 9 words of runtime bits)
    _q(s, 0x08, r.choice([0, FOLLOWING, r.getrandbits(64) | 1]))  # planes: inline, else an offset
    _q(s, 0x10, _ptr(r))
    _q(s, 0x18, _ptr(r))
    world = _world(r, planeCount=_small(r, 4), nodeCount=_small(r, 4))
    return _input(r, s, r.randbytes(0x200), {"varGfxWorldDpvsPlanes": HEAP + OFF_STRUCT, "varGfxWorld": WORLD,
                                             "_world": world})


# --- Load_GfxCellTree ----------------------------------------------------------------------------------------------

def _cell_tree(r):
    cells = 4
    index = r.randrange(cells)
    counts = [_small(r, 3) for _ in range(cells)]
    world = _world(r, cellCount=cells)
    counts_at, trees_at = OFF_AUX + 0xB00, OFF_STRUCT - 8 * index
    _q(world, 0x70, HEAP + counts_at)
    _q(world, 0x78, HEAP + trees_at)
    s = bytearray(8)
    _q(s, 0, _ptr(r))
    feed = bytearray()
    extra = bytearray()
    for _ in range(counts[index]):
        t = bytearray(r.randbytes(0x38))
        n = _small(r, 4)
        struct.pack_into("<H", t, 0x20, n)
        p = r.choice([0, FOLLOWING, FOLLOWING, r.getrandbits(64) | 2])
        _q(t, 0x28, p)
        feed += t
        if p == FOLLOWING:
            extra += r.randbytes(2 * n)
    inp = _input(r, s, feed + extra, {"varGfxCellTree": HEAP + OFF_STRUCT, "varGfxWorld": WORLD, "_world": world})
    # aabbTreeCounts inside the buffer
    buf = bytearray(inp["args"][-1])
    for i, c in enumerate(counts):
        struct.pack_into("<i", buf, counts_at + 4 * i, c)
    inp["args"][-1] = bytes(buf)
    if index:   # the element before ours belongs to the same array; keep it out of the way of the struct test
        pass
    return inp


# --- Load_GfxCell --------------------------------------------------------------------------------------------------

def _cell(r):
    s = bytearray(r.randbytes(0x48))
    portals = _small(r, 3)
    struct.pack_into("<i", s, 0x18, portals)
    _q(s, 0x20, _ptr(r))
    s[0x28] = _small(r, 5)
    _q(s, 0x30, _ptr(r))
    s[0x38] = _small(r, 5)
    _q(s, 0x40, _ptr(r))
    feed, extra = bytearray(), bytearray()
    if struct.unpack_from("<Q", s, 0x20)[0]:
        for _ in range(portals):
            p = bytearray(r.randbytes(0x50))
            vc = _small(r, 4)
            p[0x34] = vc
            vp = _ptr(r)
            _q(p, 0x28, vp)
            feed += p
            if vp:
                extra += r.randbytes(12 * vc)
    return _input(r, s, feed + extra + r.randbytes(16), {"varGfxCell": HEAP + OFF_STRUCT})


# --- Load_GfxWorldVertexData0 / Load_GfxWorldVertexLayerData -------------------------------------------------------

def _draw(r):
    d = bytearray(r.randbytes(0xB0))
    _u32(d, 0x00, _small(r, 3))                 # reflectionProbeCount
    _u32(d, 0x20, _small(r, 3))                 # reflectionProbeReferenceCount
    struct.pack_into("<i", d, 0x38, _small(r, 2))   # lightmapCount
    _u32(d, 0x6C, _small(r, 4))                 # vertexCount
    _u32(d, 0x80, _small(r, 16))                # vertexLayerDataSize
    _u32(d, 0x98, _small(r, 6))                 # indexCount
    for off in (0x08, 0x10, 0x18, 0x28, 0x30, 0x40, 0x48, 0x50, 0x70, 0x88, 0xA0):
        _q(d, off, _ptr(r))
    return d


def _vertex_data(r):
    s = bytearray(r.randbytes(0x10))
    _q(s, 0, _ptr(r))
    draw = _draw(r)
    inp = _input(r, s, r.randbytes(0x100), {"varGfxWorldVertexData0": HEAP + OFF_STRUCT,
                                            "varGfxWorldDraw": HEAP + OFF_AUX, "_world": draw})
    return inp


def _layer_data(r):
    s = bytearray(r.randbytes(0x10))
    _q(s, 0, _ptr(r))
    draw = _draw(r)
    return _input(r, s, r.randbytes(0x40), {"varGfxWorldVertexLayerData": HEAP + OFF_STRUCT,
                                            "varGfxWorldDraw": HEAP + OFF_AUX, "_world": draw})


# --- Load_GfxWorldDraw ---------------------------------------------------------------------------------------------

def _world_draw(r):
    d = _draw(r)
    probes, refs = struct.unpack_from("<I", d, 0)[0], struct.unpack_from("<I", d, 0x20)[0]
    feed = bytearray()
    if struct.unpack_from("<Q", d, 0x08)[0]:
        feed += r.randbytes(8 * probes)
    if struct.unpack_from("<Q", d, 0x10)[0]:
        recs, extra = bytearray(), bytearray()
        for _ in range(probes):
            p = bytearray(r.randbytes(0x20))
            n = _small(r, 2)
            _u32(p, 0x18, n)
            vp = _ptr(r)
            _q(p, 0x10, vp)
            recs += p
            if vp:
                extra += r.randbytes(0x60 * n)
        feed += recs + extra
    if struct.unpack_from("<Q", d, 0x18)[0]:
        feed += bytes(0x18 * probes)
    if struct.unpack_from("<Q", d, 0x28)[0]:
        feed += r.randbytes(12 * refs)
    if struct.unpack_from("<Q", d, 0x30)[0]:
        feed += r.randbytes(refs)
    return _input(r, d, feed + r.randbytes(0x200), {"varGfxWorldDraw": HEAP + OFF_STRUCT})


# --- Load_GfxLightGrid / Load_GfxLightGridTree ---------------------------------------------------------------------

def _light_grid(r):
    g = bytearray(r.randbytes(0x620))
    axis = r.randrange(3)
    _u32(g, 0x14, axis)
    lo = r.randrange(0, 1000)
    struct.pack_into("<H", g, 0x08 + 2 * axis, lo)
    struct.pack_into("<H", g, 0x0E + 2 * axis, lo + _small(r, 5))
    for off, top in ((0x28, 16), (0x38, 3), (0x48, 2), (0x70, 4), (0x80, 16)):
        _u32(g, off, _small(r, top))
    g[0x67] = _small(r, 4)
    for off in (0x20, 0x30, 0x40, 0x50, 0x68, 0x78, 0x88):
        _q(g, off, _ptr(r))
    return _input(r, g, r.randbytes(0x400), {"varGfxLightGrid": HEAP + OFF_STRUCT})


def _light_grid_tree(r):
    t = bytearray(r.randbytes(0x50))
    struct.pack_into("<i", t, 4, _small(r, 6))
    struct.pack_into("<i", t, 0x40, _small(r, 20))
    _q(t, 0x38, _ptr(r))
    _q(t, 0x48, _ptr(r))
    return _input(r, t, r.randbytes(0x80), {"varGfxLightGridTree": HEAP + OFF_STRUCT})


# --- Load_GfxShadowGeometryArray -----------------------------------------------------------------------------------

def _shadow_geometry(r):
    count = _small(r, 3)
    recs, extra = bytearray(), bytearray()
    for _ in range(count):
        g = bytearray(r.randbytes(0x18))
        a, b = _small(r, 4), _small(r, 4)
        struct.pack_into("<HH", g, 0, a, b)
        pa, pb = _ptr(r), _ptr(r)
        _q(g, 8, pa)
        _q(g, 0x10, pb)
        recs += g
        if pa:
            extra += r.randbytes(4 * a)
        if pb:
            extra += r.randbytes(2 * b)
    inp = _input(r, b"", b"", {"varGfxShadowGeometry": HEAP + OFF_STRUCT})
    flag = inp["args"][0]
    buf = bytearray(inp["args"][-1])
    if not flag:                               # the array is already in place
        buf[OFF_STRUCT:OFF_STRUCT + len(recs)] = recs
    zone = ds.Zone(r, (bytes(recs) if flag else b"") + bytes(extra) + r.randbytes(0x40))
    var = {"varGfxShadowGeometry": HEAP + OFF_STRUCT}

    def setup(w):
        zone.start(w)
        for name, value in var.items():
            w.u64(ds.va(name), value)
    return {"args": [flag, count, bytes(buf)], "setup": setup}


# --- Load_GfxLightRegion -------------------------------------------------------------------------------------------

def _light_region(r):
    s = bytearray(r.randbytes(0x10))
    n = _small(r, 3)
    _u32(s, 0, n)
    _q(s, 8, _ptr(r))
    feed, extra = bytearray(), bytearray()
    if struct.unpack_from("<Q", s, 8)[0]:
        for _ in range(n):
            h = bytearray(r.randbytes(0x58))
            a = _small(r, 3)
            _u32(h, 0x48, a)
            p = _ptr(r)
            _q(h, 0x50, p)
            feed += h
            if p:
                extra += r.randbytes(0x14 * a)
    return _input(r, s, feed + extra, {"varGfxLightRegion": HEAP + OFF_STRUCT})


# --- Load_GfxStaticModelVertexLightingInfo -------------------------------------------------------------------------

def _smodel_lighting(r):
    s = bytearray(r.randbytes(0x38))
    _u32(s, 0x34, _small(r, 4))
    _q(s, 0, _ptr(r))
    return _input(r, s, r.randbytes(0x80), {"varGfxStaticModelVertexLightingInfo": HEAP + OFF_STRUCT})


# --- sub_140361E10 -------------------------------------------------------------------------------------------------

def _byte_ptrs(r):
    count = _small(r, 4)
    ptrs = b"".join(struct.pack("<Q", _ptr(r)) for _ in range(count))
    inp = _input(r, b"", b"", {})
    flag = inp["args"][0]
    buf = bytearray(inp["args"][-1])
    if not flag:
        buf[OFF_STRUCT:OFF_STRUCT + len(ptrs)] = ptrs
    zone = ds.Zone(r, (ptrs if flag else b"") + r.randbytes(0x20))

    def setup(w):
        zone.start(w)
        w.u64(ds.va("varGfxConstantBufferPtr"), HEAP + OFF_STRUCT)
    return {"args": [flag, count, bytes(buf)], "setup": setup}


# --- Load_GfxWorldDpvsStatic ---------------------------------------------------------------------------------------

def _dpvs_static(r):
    s = bytearray(r.randbytes(0x118))
    smodels, surfaces = _small(r, 2), _small(r, 3)
    _u32(s, 0, smodels)
    _u32(s, 4, _small(r, 4))
    _u32(s, 0x30, _small(r, 4))
    _u32(s, 0x34, _small(r, 4))
    _u32(s, 0xF0, _small(r, 2))
    _u32(s, 0xF4, _small(r, 2))
    for off in range(0x38, 0x110, 8):
        if off not in (0xF0,):
            _q(s, off, _ptr(r))
    world = _world(r, surfaceCount=surfaces)
    return _input(r, s, r.randbytes(0x1200), {"varGfxWorldDpvsStatic": HEAP + OFF_STRUCT, "varGfxWorld": WORLD,
                                              "_world": world})


# --- Load_GfxWorldDpvsDynamic --------------------------------------------------------------------------------------

def _dpvs_dynamic(r):
    s = bytearray(r.randbytes(0x50))
    _u32(s, 0, _small(r, 3))
    _u32(s, 4, _small(r, 3))
    for off in range(0x10, 0x50, 8):
        _q(s, off, _ptr(r))
    world = _world(r, cellCount=_small(r, 3))
    return _input(r, s, r.randbytes(0x600), {"varGfxWorldDpvsDynamic": HEAP + OFF_STRUCT, "varGfxWorld": WORLD,
                                             "_world": world})


# --- sub_1401B7180 -------------------------------------------------------------------------------------------------

def _tome(r):
    data = r.choice([0, 0, HEAP + 0x100, r.getrandbits(64)])
    buf = r.randbytes(ds.BUF_SIZE)

    def setup(w):
        ds.M["m"] = w.m
    return {"args": [HEAP + 0x40, data, r.getrandbits(32), buf], "setup": setup}


# --- Load_GfxWorld -------------------------------------------------------------------------------------------------

def _gfx_world(r):
    w = _world(r, cellCount=_small(r, 2), skyCount=_small(r, 2), modelCount=_small(r, 2),
               materialMemoryCount=_small(r, 2), heroLights=_small(r, 2), tomeSize=_small(r, 32))
    last = r.randrange(4)
    _u32(w, 0x30, last)
    _u32(w, 0x34, last + r.choice([1, 1, 2]))   # primaryLightCount: (count - last) * 0x2000 - 0x2000 words of bits
    for off in (0x00, 0x08):
        _q(w, off, r.choice([0, FOLLOWING, FOLLOWING, r.getrandbits(64) | 1]))
    for off in (0x28, 0x70, 0x78, 0x80, 0x760, 0x788, 0x848, 0x850, 0x858, 0x860, 0x868, 0x870, 0x878, 0x880,
                0x888, 0x890, 0x898, 0xA10, 0xA20):
        _q(w, off, _ptr(r))
    feed = bytearray()
    for off in (0x00, 0x08):
        if struct.unpack_from("<Q", w, off)[0] == FOLLOWING:
            feed += b"name" + bytes([0x30 + r.randrange(10)]) + b"\0"
    skies = struct.unpack_from("<i", w, 0x20)[0]
    if struct.unpack_from("<Q", w, 0x28)[0]:
        recs, extra = bytearray(), bytearray()
        for _ in range(skies):
            s = bytearray(r.randbytes(0x20))
            n = _small(r, 3)
            struct.pack_into("<i", s, 0, n)
            p = _ptr(r)
            _q(s, 8, p)
            recs += s
            if p:
                extra += r.randbytes(4 * n)
        feed += recs + extra
    inp = _input(r, w, feed + r.randbytes(0x1000), {"varGfxWorld": HEAP + OFF_STRUCT})
    return inp


def _gfx_world_ptr(r):
    buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
    value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
    _q(buf, OFF_STRUCT, value)
    zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

    def setup(w):
        zone.start(w)
        w.u64(ds.va("varGfxWorldPtr"), HEAP + OFF_STRUCT)
    return {"args": [flag, bytes(buf)], "setup": setup}


CASES = [
    case("?Load_GfxWorldDpvsPlanes@@YAX_N@Z", 0xCA0, _dpvs_planes),
    case("?Load_GfxCellTree@@YAX_N@Z", 0xEE10, _cell_tree),
    case("?Load_GfxCell@@YAX_N@Z", 0xEC90, _cell),
    case("?Load_GfxWorldVertexData0@@YAX_N@Z", 0x1E00, _vertex_data),
    case("?Load_GfxWorldVertexLayerData@@YAX_N@Z", 0x1EB0, _layer_data),
    case("?Load_GfxWorldDraw@@YAX_N@Z", 0x1830, _world_draw),
    case("?Load_GfxLightGrid@@YAX_N@Z", 0xF650, _light_grid),
    case("?Load_GfxLightGridTree@@YAX_N@Z", 0xF8A0, _light_grid_tree),
    case("?Load_GfxShadowGeometryArray@@YAX_N_K@Z", 0xFBD0, _shadow_geometry),
    case("?Load_GfxLightRegion@@YAX_N@Z", 0xF950, _light_region),
    case("?Load_GfxStaticModelVertexLightingInfo@@YAX_N@Z", 0xFD70, _smodel_lighting),
    case("?sub_140361E10@@YAX_N_K@Z", 0x1E10, _byte_ptrs),
    case("?Load_GfxWorldDpvsStatic@@YAX_N@Z", 0x0DD0, _dpvs_static),
    case("?Load_GfxWorldDpvsDynamic@@YAX_N@Z", 0x0990, _dpvs_dynamic),
    case("?sub_1401B7180@@YAXPEAPEAXPEAXI@Z", 0x7180, _tome),
    case("?Load_GfxWorld@@YAX_N@Z", 0xFF30, _gfx_world, n=150),
    case("?Load_GfxWorldPtr@@YAX_N@Z", 0x1D10, _gfx_world_ptr),
]
