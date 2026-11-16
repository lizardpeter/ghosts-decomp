"""Differential cases for the effect zone loaders (src/effectscore/fx_load_db.cpp) against the Store build.

The stream functions are dbstream.py's logged fakes; each loader's callees (the nested Load_* functions, the asset
pointer loaders of materials, models, images, light defs and particle animations, Load_XString,
Load_FxEffectDefFromName and the Load_<T>Asset linkers) are logged fakes recording the stream variables they see.
Structures are random with every element type the loaders branch on (and others), visual counts of 0, 1 and more,
null, inline, insert and offset pointers, and counts with the top bit set. docs/assets/effects.md;
tools/fastfile/fx.py is the same logic, checked against the game on real zones.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
ELEM = HEAP + OFF_AUX            # an FxElemDef the visuals / extended loaders read elemType and visualCount from
ELEM_SIZE = 0x138
TYPES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xA, 0xB, 0xC, 0xD, 0xE, 0xF, 0x10, 0x11, 0x12, 0xFF]


def _rec(name, spec, *globals_):
    return ds.recorder(name, spec, globals_)


def _from_name(mu):
    """Load_FxEffectDefFromName(const char **name): logs, and replaces a non-null name as the lookup would."""
    p = ds.arg(mu, 0)
    v = ds.u64(mu, p) if ds.in_buffer(p, 8) else None
    ds.log("Load_FxEffectDefFromName", p, v)
    if v:
        ds.write(p, struct.pack("<Q", v ^ 0x6600000000))


FAKES = {
    **ds.STREAM_FAKES,
    "?Load_MaterialHandle@@YAX_N@Z": _rec("Load_MaterialHandle", "b", "varMaterialHandle"),
    "?Load_MaterialHandleArray@@YAX_N_K@Z": _rec("Load_MaterialHandleArray", "bq", "varMaterialHandle"),
    "?Load_XModelPtr@@YAX_N@Z": _rec("Load_XModelPtr", "b", "varXModelPtr"),
    "?Load_XString@@YAX_N@Z": _rec("Load_XString", "b", "varXString"),
    "?Load_GfxImagePtr@@YAX_N@Z": _rec("Load_GfxImagePtr", "b", "varGfxImagePtr"),
    "?Load_FxEffectDefFromName@@YAXPEAPEBD@Z": _from_name,
    "?Load_FxEffectDefAsset@@YAXPEAPEAUFxEffectDef@@@Z": ds.asset_linker("Load_FxEffectDefAsset"),
    "?Load_GfxLightDefAsset@@YAXPEAPEAUGfxLightDef@@@Z": ds.asset_linker("Load_GfxLightDefAsset"),
    "?Load_FxParticleSimAnimationAsset@@YAXPEAPEAUFxParticleSimAnimation@@@Z":
        ds.asset_linker("Load_FxParticleSimAnimationAsset"),
    "?Load_GfxLightDefPtr@@YAX_N@Z": _rec("Load_GfxLightDefPtr", "b", "varGfxLightDefPtr"),
    "?Load_FxParticleSimAnimationPtr@@YAX_N@Z": _rec("Load_FxParticleSimAnimationPtr", "b",
                                                     "varFxParticleSimAnimationPtr"),
    "?Load_GfxLightDef@@YAX_N@Z": _rec("Load_GfxLightDef", "b", "varGfxLightDef", "g_streamPos"),
    "?Load_FxParticleSimAnimation@@YAX_N@Z": _rec("Load_FxParticleSimAnimation", "b", "varFxParticleSimAnimation",
                                                  "g_streamPos"),
    "?Load_FxTrailDef@@YAX_N@Z": _rec("Load_FxTrailDef", "b", "varFxTrailDef", "g_streamPos"),
    "?Load_FxFlareDef@@YAX_N@Z": _rec("Load_FxFlareDef", "b", "varFxFlareDef", "g_streamPos"),
    "?Load_FxElemVisuals@@YAX_N@Z": _rec("Load_FxElemVisuals", "b", "varFxElemVisuals", "varFxElemDef"),
    "?Load_FxElemVisualsArray@@YAX_N_K@Z": _rec("Load_FxElemVisualsArray", "bq", "varFxElemVisuals",
                                               "g_streamPos"),
    "?Load_FxElemDefVisuals@@YAX_N@Z": _rec("Load_FxElemDefVisuals", "b", "varFxElemDefVisuals", "varFxElemDef"),
    "?Load_FxElemExtendedDefPtr@@YAX_N@Z": _rec("Load_FxElemExtendedDefPtr", "b", "varFxElemExtendedDefPtr",
                                                "varFxElemDef", "g_streamPos"),
    "?Load_FxElemDefArray@@YAX_N_K@Z": ds.clobbering(_rec("Load_FxElemDefArray", "bq", "varFxElemDef",
                                                          "g_streamPos"), varFxElemDef=HEAP + OFF_AUX + 0x600),
    "?Load_FxEffectDef@@YAX_N@Z": ds.clobbering(_rec("Load_FxEffectDef", "b", "varFxEffectDef", "g_streamPos"),
                                                varFxEffectDef=HEAP + OFF_AUX + 0x700),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & 0xFFFFFFFFFFFFFFFF)


def _ptr(r):
    return ds.pointer(r, inline=0.45, insert=0.1)


def _count(r, top=4):
    return r.choice([0, 1, 1, 2, r.randint(0, top)])


def _elem(r):
    e = bytearray(r.randbytes(ELEM_SIZE))
    e[0xB4] = r.choice(TYPES)
    e[0xB6] = r.choice([0, 1, 2, 3, r.getrandbits(8)])
    e[0xB7] = r.choice([0, 1, 3, r.getrandbits(8)])
    e[0xB8] = r.choice([0, 1, 3, r.getrandbits(8)])
    for off in (0xC0, 0xC8, 0xD0, 0xF0, 0xF8, 0x100, 0x118):
        _q(e, off, _ptr(r))
    return e


def _input(r, struct_bytes, var_values, aux=None, flag=None, feed=0x2000):
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


def _handle_ptr(var, inner):
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        _q(buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))
        stale = HEAP + 0x30000 + r.getrandbits(8)

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            w.u64(va(inner), stale)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _effect(r):
    h = bytearray(r.randbytes(0x40))
    _q(h, 0, _ptr(r))
    for off in (0x14, 0x18, 0x1C):
        struct.pack_into("<i", h, off, r.choice([0, 1, 2, r.randint(-3, 5), r.getrandbits(31)]))
    _q(h, 0x38, _ptr(r))
    return _input(r, h, {"varFxEffectDef": HEAP + OFF_STRUCT})


def _elem_array(r):
    n = _count(r, 3)
    elems = b"".join(_elem(r) for _ in range(n))
    inp = _input(r, elems, {"varFxElemDef": HEAP + OFF_STRUCT}, feed=0x3000)
    inp["args"].insert(1, n)
    return inp


def _elem_def_visuals(r):
    e = _elem(r)
    v = bytearray(8)
    _q(v, 0, _ptr(r))
    return _input(r, v, {"varFxElemDefVisuals": HEAP + OFF_STRUCT, "varFxElemDef": ELEM}, aux=e)


def _extended(r):
    e = _elem(r)
    v = bytearray(8)
    _q(v, 0, _ptr(r))
    return _input(r, v, {"varFxElemExtendedDefPtr": HEAP + OFF_STRUCT, "varFxElemDef": ELEM}, aux=e)


def _visuals(r):
    e = _elem(r)
    v = bytearray(8)
    _q(v, 0, _ptr(r))
    return _input(r, v, {"varFxElemVisuals": HEAP + OFF_STRUCT, "varFxElemDef": ELEM}, aux=e)


def _visuals_array(r):
    e = _elem(r)
    n = _count(r)
    v = bytearray()
    for _ in range(n):
        v += struct.pack("<Q", _ptr(r))
    inp = _input(r, bytes(v), {"varFxElemVisuals": HEAP + OFF_STRUCT, "varFxElemDef": ELEM}, aux=e)
    inp["args"].insert(1, n)
    return inp


def _trail(r):
    t = bytearray(r.randbytes(0x30))
    struct.pack_into("<i", t, 0x14, r.choice([0, 1, r.randint(0, 40), -1, r.getrandbits(31)]))
    struct.pack_into("<i", t, 0x20, r.choice([0, 1, r.randint(0, 60), -1, r.getrandbits(31)]))
    _q(t, 0x18, _ptr(r))
    _q(t, 0x28, _ptr(r))
    return _input(r, t, {"varFxTrailDef": HEAP + OFF_STRUCT})


def _flare(r):
    f = bytearray(r.randbytes(0x70))
    for off in (0x40, 0x44, 0x48, 0x4C):
        struct.pack_into("<i", f, off, r.choice([0, 1, r.randint(0, 20), -1, -2, r.getrandbits(31)]))
    for off in (0x50, 0x58, 0x60, 0x68):
        _q(f, off, _ptr(r))
    return _input(r, f, {"varFxFlareDef": HEAP + OFF_STRUCT})


def _light_def(r):
    d = bytearray(r.randbytes(0x30))
    _q(d, 0, _ptr(r))
    return _input(r, d, {"varGfxLightDef": HEAP + OFF_STRUCT})


def _particle_sim(r):
    p = bytearray(r.randbytes(0x60))
    _q(p, 0, _ptr(r))
    for off, top in ((0x40, 40), (0x18, 30), (0x3C, 20)):
        struct.pack_into("<I", p, off, r.choice([0, 1, r.randint(0, top), r.getrandbits(32)]))
    for off in (0x48, 0x50, 0x58):
        _q(p, off, _ptr(r))
    return _input(r, p, {"varFxParticleSimAnimation": HEAP + OFF_STRUCT})


CASES = [
    case("?Load_FxTrailDef@@YAX_N@Z", 0xE850, _trail),
    case("?Load_FxFlareDef@@YAX_N@Z", 0xDBD0, _flare),
    case("?Load_FxElemExtendedDefPtr@@YAX_N@Z", 0xD750, _extended, n=300),
    case("?Load_FxElemVisuals@@YAX_N@Z", 0xD900, _visuals, n=300),
    case("?Load_FxElemVisualsArray@@YAX_N_K@Z", 0xD9E0, _visuals_array, n=300),
    case("?Load_FxElemDefVisuals@@YAX_N@Z", 0xD600, _elem_def_visuals, n=300),
    case("?Load_FxElemDefArray@@YAX_N_K@Z", 0xD340, _elem_array),
    case("?Load_FxEffectDef@@YAX_N@Z", 0xD040, _effect),
    case("?Load_FxEffectDefHandle@@YAX_N@Z", 0xD120, _handle_ptr("varFxEffectDefHandle", "varFxEffectDef")),
    case("?Load_GfxLightDef@@YAX_N@Z", 0xF470, _light_def),
    case("?Load_GfxLightDefPtr@@YAX_N@Z", 0xF560, _handle_ptr("varGfxLightDefPtr", "varGfxLightDef")),
    case("?Load_FxParticleSimAnimation@@YAX_N@Z", 0xE5D0, _particle_sim),
    case("?Load_FxParticleSimAnimationPtr@@YAX_N@Z", 0xE760,
         _handle_ptr("varFxParticleSimAnimationPtr", "varFxParticleSimAnimation")),
]
