"""Differential cases for the smaller asset loaders against the Store build: post-processing (src/gfx_d3d/
r_postfx_load_db.cpp), tracers (src/bgame/bg_tracer_load_db.cpp), glass and effect tables
(src/effectscore/fx_world_load_db.cpp) and animation classes (src/xanim/xanim_load_db.cpp).

The stream functions are dbstream.py's logged fakes; each loader's callees (nested loaders, the asset pointer loaders
of materials, effects, physics presets and scriptables, Load_SndAliasCustom, Load_ScriptStringCustom,
Load_scr_string_tArray and the Load_<T>Asset linkers) are logged fakes recording the stream variables they see.
Structures are random, with null, inline, insert and offset pointers and small and large counts. tools/fastfile
(postfx.py, weapon.py, mapfx.py, xanim.py) is the same logic, checked against the game on whole real zones.
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"


def _rec(name, spec, *globals_):
    return ds.recorder(name, spec, globals_)


def _ptr_rec(name, var):
    return _rec(name, "b", var)


def _snd(mu):
    p = ds.arg(mu, 0)
    ds.log("Load_SndAliasCustom", p, ds.u64(mu, p) if ds.in_buffer(p, 8) else None)


def _script_string(mu):
    p = ds.arg(mu, 0)
    v = ds.u32(mu, p) if ds.in_buffer(p, 4) else None
    ds.log("Load_ScriptStringCustom", p, v)
    if v is not None:
        ds.write(p, struct.pack("<I", (v * 7 + 1) & 0xFFFFFFFF))


ASSET = {
    "Colorization": "?Load_ColorizationAsset@@YAXPEAPEAUColorization@@@Z",
    "ColorizationSet": "?Load_ColorizationSetAsset@@YAXPEAPEAUColorizationSet@@@Z",
    "ToneMapping": "?Load_ToneMappingAsset@@YAXPEAPEAUToneMapping@@@Z",
    "TracerDef": "?Load_TracerDefAsset@@YAXPEAPEAUTracerDef@@@Z",
    "GlassWorld": "?Load_GlassWorldAsset@@YAXPEAPEAUGlassWorld@@@Z",
    "FxWorld": "?Load_FxWorldAsset@@YAXPEAPEAUFxWorld@@@Z",
    "FxImpactTable": "?Load_FxImpactTableAsset@@YAXPEAPEAUFxImpactTable@@@Z",
    "SurfaceFxTable": "?Load_SurfaceFxTableAsset@@YAXPEAPEAUSurfaceFxTable@@@Z",
    "AnimationClass": "?Load_AnimationClassAsset@@YAXPEAPEAUAnimationClass@@@Z",
    "FxEffectDef": "?Load_FxEffectDefAsset@@YAXPEAPEAUFxEffectDef@@@Z",
}

FAKES = {
    **ds.STREAM_FAKES,
    **{sym: ds.asset_linker(f"Load_{k}Asset") for k, sym in ASSET.items()},
    "?Load_MaterialHandle@@YAX_N@Z": _ptr_rec("Load_MaterialHandle", "varMaterialHandle"),
    "?Load_PhysPresetPtr@@YAX_N@Z": _ptr_rec("Load_PhysPresetPtr", "varPhysPresetPtr"),
    "?Load_FxEffectDefHandle@@YAX_N@Z": _ptr_rec("Load_FxEffectDefHandle", "varFxEffectDefHandle"),
    "?Load_FxEffectDef@@YAX_N@Z": _rec("Load_FxEffectDef", "b", "varFxEffectDef", "g_streamPos"),
    "?Load_ScriptableDefPtr@@YAX_N@Z": _ptr_rec("Load_ScriptableDefPtr", "varScriptableDefPtr"),
    "?Load_SndAliasCustom@@YAXPEAPEAUsnd_alias_list_t@@@Z": _snd,
    "?Load_ScriptStringCustom@@YAXPEAW4scr_string_t@@@Z": _script_string,
    "?Load_scr_string_tArray@@YAX_N_K@Z": ds.array_loader("Load_scr_string_tArray", "varscr_string_t", 4),
    "?Load_FxEffectDefHandleArray@@YAX_N_K@Z": _rec("Load_FxEffectDefHandleArray", "bq", "varFxEffectDefHandle",
                                                   "g_streamPos"),
    "?Load_Colorization@@YAX_N@Z": _rec("Load_Colorization", "b", "varColorization", "g_streamPos"),
    "?Load_ColorizationPtr@@YAX_N@Z": _ptr_rec("Load_ColorizationPtr", "varColorizationPtr"),
    "?Load_ColorizationSet@@YAX_N@Z": _rec("Load_ColorizationSet", "b", "varColorizationSet", "g_streamPos"),
    "?Load_ToneMapping@@YAX_N@Z": _rec("Load_ToneMapping", "b", "varToneMapping", "g_streamPos"),
    "?Load_TracerDef@@YAX_N@Z": _rec("Load_TracerDef", "b", "varTracerDef", "g_streamPos"),
    "?Load_G_GlassName@@YAX_N@Z": _rec("Load_G_GlassName", "b", "varG_GlassName", "g_streamPos"),
    "?Load_G_GlassData@@YAX_N@Z": _rec("Load_G_GlassData", "b", "varG_GlassData", "g_streamPos"),
    "?Load_GlassWorld@@YAX_N@Z": _rec("Load_GlassWorld", "b", "varGlassWorld", "g_streamPos"),
    "?Load_FxGlassDef@@YAX_N@Z": _rec("Load_FxGlassDef", "b", "varFxGlassDef", "g_streamPos"),
    "?Load_FxGlassSystem@@YAX_N@Z": _rec("Load_FxGlassSystem", "b", "varFxGlassSystem", "g_streamPos"),
    "?Load_FxWorld@@YAX_N@Z": _rec("Load_FxWorld", "b", "varFxWorld", "g_streamPos"),
    "?Load_FxImpactTable@@YAX_N@Z": _rec("Load_FxImpactTable", "b", "varFxImpactTable", "g_streamPos"),
    "?Load_SurfaceFxTable@@YAX_N@Z": _rec("Load_SurfaceFxTable", "b", "varSurfaceFxTable", "g_streamPos"),
    "?Load_AnimationAimSet@@YAX_N@Z": _rec("Load_AnimationAimSet", "b", "varAnimationAimSet", "g_streamPos"),
    "?Load_AnimationStateArray@@YAX_N_K@Z": _rec("Load_AnimationStateArray", "bq", "varAnimationState",
                                                "g_streamPos"),
    "?Load_AnimationStateMachine@@YAX_N@Z": _rec("Load_AnimationStateMachine", "b", "varAnimationStateMachine",
                                                "g_streamPos"),
    "?Load_AnimationClass@@YAX_N@Z": _rec("Load_AnimationClass", "b", "varAnimationClass", "g_streamPos"),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & 0xFFFFFFFFFFFFFFFF)


def _ptr(r):
    return ds.pointer(r, inline=0.45, insert=0.1)


def _input(r, struct_bytes, var_values, aux=None, flag=None, feed=0x2000, extra_args=()):
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
    return {"args": [flag, *extra_args, bytes(buf)], "setup": setup}


def _struct(size, ptrs=(), counts=()):
    """A maker of `size` random bytes with pointer fields at `ptrs` and (offset, fmt, choices) counts."""
    def make(r):
        b = bytearray(r.randbytes(size))
        for off in ptrs:
            _q(b, off, _ptr(r))
        for off, fmt, top in counts:     # top < 0: a loop count (kept small: a huge one only times out)
            big = [] if top < 0 else [r.getrandbits(8 * struct.calcsize(fmt))]
            struct.pack_into("<" + fmt, b, off, r.choice([0, 1, 2, r.randint(0, abs(top))] + big))
        return b
    return make


def _body(var, size, ptrs=(), counts=()):
    mk = _struct(size, ptrs, counts)
    return lambda r: _input(r, mk(r), {var: HEAP + OFF_STRUCT})


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


def _array(var, size, ptrs=(), counts=(), top=4):
    mk = _struct(size, ptrs, counts)

    def make(r):
        n = r.choice([0, 1, 2, r.randint(0, top)])
        return _input(r, b"".join(mk(r) for _ in range(n)), {var: HEAP + OFF_STRUCT}, extra_args=(n,))
    return make


def _glass_system(r):
    b = bytearray(r.randbytes(0xA8))
    for off in range(0x30, 0x98, 8):
        _q(b, off, _ptr(r))
    struct.pack_into("<I", b, 8, r.choice([0, 1, r.randint(0, 4)]))     # defCount: a loop count
    for off, top in ((0xC, 64), (0x10, 16), (0x14, 32), (0x18, 16), (0x24, 64), (0x2C, 64)):
        struct.pack_into("<I", b, off, r.choice([0, 1, r.randint(0, top), r.getrandbits(32), 0xFFFFFFFD]))
    return _input(r, b, {"varFxGlassSystem": HEAP + OFF_STRUCT}, feed=0x3000)


def _anim_class(r):
    b = bytearray(r.randbytes(0x58))
    for off in (0, 8, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50):
        _q(b, off, _ptr(r))
    for off in (0x20, 0x22):
        struct.pack_into("<H", b, off, r.choice([0, 1, r.randint(0, 20), r.getrandbits(16)]))
    return _input(r, b, {"varAnimationClass": HEAP + OFF_STRUCT})


CASES = [
    case("?Load_Colorization@@YAX_N@Z", 0xB830, _body("varColorization", 0x30, (0x28,))),
    case("?Load_ColorizationPtr@@YAX_N@Z", 0xB8C0, _handle_ptr("varColorizationPtr", "varColorization")),
    case("?Load_ColorizationSet@@YAX_N@Z", 0xB9B0, _body("varColorizationSet", 0x68, (0,))),
    case("?Load_ColorizationSetPtr@@YAX_N@Z", 0xBAD0, _handle_ptr("varColorizationSetPtr", "varColorizationSet")),
    case("?Load_ToneMapping@@YAX_N@Z", 0x83B0, _body("varToneMapping", 0x70, (0x68,))),
    case("?Load_ToneMappingPtr@@YAX_N@Z", 0x8440, _handle_ptr("varToneMappingPtr", "varToneMapping")),
    case("?Load_TracerDef@@YAX_N@Z", 0x8530, _body("varTracerDef", 0x78, (0,))),
    case("?Load_TracerDefPtr@@YAX_N@Z", 0x85D0, _handle_ptr("varTracerDefPtr", "varTracerDef")),
    case("?Load_G_GlassName@@YAX_N@Z", 0xEBA0, _body("varG_GlassName", 0x18, (0, 0x10), ((0xC, "H", 50),))),
    case("?Load_G_GlassData@@YAX_N@Z", 0xEAA0, _body("varG_GlassData", 0x90, (0, 0x18), ((8, "I", 50),
                                                                                       (0x10, "I", -5)))),
    case("?Load_GlassWorld@@YAX_N@Z", 0x1FE0, _body("varGlassWorld", 0x10, (0, 8))),
    case("?Load_GlassWorldPtr@@YAX_N@Z", 0x20B0, _handle_ptr("varGlassWorldPtr", "varGlassWorld")),
    case("?Load_FxGlassDef@@YAX_N@Z", 0xDD30, _body("varFxGlassDef", 0x78)),
    case("?Load_FxGlassSystem@@YAX_N@Z", 0xDE80, _glass_system, n=300),
    case("?Load_FxWorld@@YAX_N@Z", 0xE910, _body("varFxWorld", 0xB0, (0,))),
    case("?Load_FxWorldPtr@@YAX_N@Z", 0xE9B0, _handle_ptr("varFxWorldPtr", "varFxWorld")),
    case("?Load_FxEffectDefHandleArray@@YAX_N_K@Z", 0xD210, _array("varFxEffectDefHandle", 8, (0,), top=6)),
    case("?Load_FxImpactTable@@YAX_N@Z", 0xE380, _body("varFxImpactTable", 0x10, (0, 8))),
    case("?Load_FxImpactTablePtr@@YAX_N@Z", 0xE4E0, _handle_ptr("varFxImpactTablePtr", "varFxImpactTable")),
    case("?Load_SurfaceFxTable@@YAX_N@Z", 0x8180, _body("varSurfaceFxTable", 0x10, (0, 8))),
    case("?Load_SurfaceFxTablePtr@@YAX_N@Z", 0x82C0, _handle_ptr("varSurfaceFxTablePtr", "varSurfaceFxTable")),
    case("?Load_AnimationAimSet@@YAX_N@Z", 0xA460, _body("varAnimationAimSet", 0x70)),
    case("?Load_AnimationStateArray@@YAX_N_K@Z", 0xA970,
         _array("varAnimationState", 0x28, (0x10, 0x18, 0x20), ((0xD, "B", 6),))),
    case("?Load_AnimationStateMachine@@YAX_N@Z", 0xABE0,
         _body("varAnimationStateMachine", 0x18, (8, 0x10), ((4, "H", 5), (6, "H", 5)))),
    case("?Load_AnimationClass@@YAX_N@Z", 0xA550, _anim_class),
    case("?Load_AnimationClassPtr@@YAX_N@Z", 0xA880, _handle_ptr("varAnimationClassPtr", "varAnimationClass")),
]
