#!/usr/bin/env python3
"""Effects in Call of Duty: Ghosts PC zones (Microsoft Store build): FxEffectDef (asset type 0x25, "fx") with its
elements, and the two asset types only effects use: GfxLightDef (0x1B, "lightdef") and FxParticleSimAnimation
(0x3E, "particlesimanimation").

1. Loader: the Store build's loaders statement for statement (Load_FxEffectDefHandle 14034D120 and the functions
   under it); tests/fastfile/fx_check.py checks them against the game on real zones.
2. Reader: read_effect turns a loaded FxEffectDef into dataclasses (elements, their visuals, sampled velocity and
   visual states, extended definitions). docs/assets/effects.md.

The layouts are the servers' PDBs' (FxEffectDef 0x40, FxElemDef 0x138), and every offset the Store loaders touch
agrees with them. The element types do not: the Store build has two more after the particle simulation animation
(6 and 7, not identified), so its numbers from the cloud on are the servers' + 2 (docs, "Element types").
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import iw6ff

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
BLOCK_TEMP, BLOCK_VIRTUAL = 0, 3
ASSET_FX, ASSET_LIGHTDEF, ASSET_PARTICLE_SIM_ANIMATION = 0x25, 0x1B, 0x3E
EFFECT_SIZE, ELEM_SIZE = 0x40, 0x138

# Store build element types (FxElemDef.elemType, +0xB4), by what the loaders do with each
ELEM_TRAIL, ELEM_FLARE, ELEM_PARTICLE_SIM_ANIMATION = 3, 4, 5
ELEM_SPARK_FOUNTAIN, ELEM_MODEL, ELEM_OMNI_LIGHT, ELEM_SPOT_LIGHT = 0xA, 0xB, 0xC, 0xD
ELEM_SOUND, ELEM_DECAL, ELEM_RUNNER, ELEM_VECTORFIELD = 0xE, 0xF, 0x10, 0x11
ELEM_TYPE_NAMES = {0: "sprite_billboard", 1: "sprite_oriented", 2: "tail", 3: "trail", 4: "flare",
                   5: "particle_sim_animation", 8: "cloud", 9: "spark_cloud", 0xA: "spark_fountain", 0xB: "model", 0xC: "omni_light",
                   0xD: "spot_light", 0xE: "sound", 0xF: "decal", 0x10: "runner", 0x11: "vector_field"}

HOOKS = {"material_ptr": None, "xmodel_ptr": None, "image_ptr": None}


def _hook(name):
    fn = HOOKS[name]
    if fn is None:
        raise NotImplementedError(f"fx.HOOKS[{name!r}] is not set (register() sets it)")
    return fn


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _u8(s, a):
    return s.read(a, 1)[0]


def _effect_ref(s, at):
    """An FxEffectDefRef (effectOnImpact, a runner's visual, ...): the name's XString rule, then 140371ED0
    (Load_FxEffectDefFromName): a non-null name becomes the handle DB_FindXAssetHeader (14036C290) finds for it (type
    0x25). The name is kept in s.fx_ref_names (field address -> name) for read_effect, since an effect of another zone
    leaves no name behind."""
    s.xstring_ptr(at)
    p = s.u64(at)
    if p:
        name = s.cstr(p)
        names = getattr(s, "fx_ref_names", None)
        if names is None:
            names = s.fx_ref_names = {}
        names[at] = name.decode("latin1")
        s.put_u64(at, s.find_asset(ASSET_FX, name))


# ==== 1. loader ===================================================================================================

def load_light_def(s, h: int, at_stream_start: bool = True):
    """14034F470 (Load_GfxLightDef): 0x30 bytes, in the virtual block: name, then two GfxLightImage (image pointer and
    sampler, 0x10 each) at +8 and +0x18, their images by Load_GfxImagePtr (14034F380)."""
    s.load(at_stream_start, h, 0x30)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    for off in (8, 0x18):
        _hook("image_ptr")(s, h + off)
    s.pop()


load_light_def_ptr = iw6ff.asset_ptr(ASSET_LIGHTDEF, lambda s, h: load_light_def(s, h, True))   # 14034F560


def load_particle_sim_animation(s, h: int, at_stream_start: bool = True):
    """14034E5D0 (Load_FxParticleSimAnimation): 0x60 bytes, in the virtual block: name, material (+8), then three
    arrays when non-null: +0x48 (u32 count at +0x40) × 0x20 aligned 32, +0x50 (u32 at +0x18) × 8 aligned 4, +0x58
    (u32 at +0x3C) × 0x10 aligned 4."""
    s.load(at_stream_start, h, 0x60)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    _hook("material_ptr")(s, h + 8)
    for ptr, count, size, align in ((0x48, 0x40, 0x20, 32), (0x50, 0x18, 8, 4), (0x58, 0x3C, 0x10, 4)):
        if s.u64(h + ptr):
            p = s.align(align)
            s.put_u64(h + ptr, p)
            s.load(True, p, struct.unpack("<I", s.read(h + count, 4))[0] * size)
    s.pop()


# 14034E760 (Load_FxParticleSimAnimationPtr): the header aligned to 32
load_particle_sim_animation_ptr = iw6ff.asset_ptr(ASSET_PARTICLE_SIM_ANIMATION,
                                                  lambda s, h: load_particle_sim_animation(s, h, True), align=32)


def _load_visual(s, elem: int, p: int):
    """One FxElemVisuals (8 bytes, already read) by the element's type (14034D900, 14034D9E0's body)."""
    t = _u8(s, elem + 0xB4)
    if t == ELEM_MODEL:
        _hook("xmodel_ptr")(s, p)
    elif t == ELEM_RUNNER:
        _effect_ref(s, p)
    elif t in (ELEM_SOUND, ELEM_VECTORFIELD):
        s.xstring_ptr(p)
    elif t == ELEM_PARTICLE_SIM_ANIMATION:
        load_particle_sim_animation_ptr(s, p)
    elif t == ELEM_OMNI_LIGHT:
        pass
    elif t == ELEM_SPOT_LIGHT:
        load_light_def_ptr(s, p)
    else:
        _hook("material_ptr")(s, p)


def _load_visuals(s, elem: int):
    """14034D600: FxElemDef.visuals (+0xD0) by type: a decal's mark array (any non-null value: aligned 4,
    visualCount × 3 material handles); one visual in place (visualCount 0 or 1); else an array of visualCount
    (any non-null value: aligned 4, 14034D9E0)."""
    at = elem + 0xD0
    count = _u8(s, elem + 0xB6)
    if _u8(s, elem + 0xB4) == ELEM_DECAL:
        if s.u64(at):
            p = s.align(4)
            s.put_u64(at, p)
            s.load(True, p, count * 0x18)
            for i in range(count):
                for k in range(3):                          # Load_MaterialHandleArray(false, 3)
                    _hook("material_ptr")(s, p + 0x18 * i + 8 * k)
        return
    if count < 2:
        _load_visual(s, elem, at)
        return
    if s.u64(at):
        p = s.align(4)
        s.put_u64(at, p)
        s.load(True, p, 8 * count)
        for i in range(count):
            _load_visual(s, elem, p + 8 * i)


def _load_extended(s, elem: int):
    """14034D750: FxElemDef.extended (+0x118) by type: a trail (0x30, 14034E850), spark fountain (0x34), spot light
    (0x18) or flare (0x70, 14034DBD0) when -1, aligned 4; another non-null value of those types is an offset. Any
    other type with a non-null value: one byte at the current position, unaligned."""
    at = elem + 0x118
    t = _u8(s, elem + 0xB4)
    v = s.u64(at)
    if not v:
        return
    if t in (ELEM_TRAIL, ELEM_SPARK_FOUNTAIN, ELEM_SPOT_LIGHT, ELEM_FLARE):
        if v != PTR_INLINE:
            s.put_u64(at, s.offset_to_pointer(v))
            return
        p = s.align(4)
        s.put_u64(at, p)
        if t == ELEM_TRAIL:
            s.load(True, p, 0x30)
            if s.u64(p + 0x18):                                 # verts: vertCount (+0x14) × 0x18, aligned 4
                q = s.align(4)
                s.put_u64(p + 0x18, q)
                s.load(True, q, _i32(s, p + 0x14) * 0x18)
            if s.u64(p + 0x28):                                 # inds: indCount (+0x20) × 2, aligned 2
                q = s.align(2)
                s.put_u64(p + 0x28, q)
                s.load(True, q, _i32(s, p + 0x20) * 2)
        elif t == ELEM_SPARK_FOUNTAIN:
            s.load(True, p, 0x34)
        elif t == ELEM_SPOT_LIGHT:
            s.load(True, p, 0x18)
        else:
            s.load(True, p, 0x70)
            for ptr, count in ((0x50, 0x40), (0x58, 0x44), (0x60, 0x48), (0x68, 0x4C)):
                if s.u64(p + ptr):                              # (count + 1) floats, aligned 4
                    q = s.align(4)
                    s.put_u64(p + ptr, q)
                    s.load(True, q, (_i32(s, p + count) + 1) * 4)
        return
    p = s.addr()
    s.put_u64(at, p)
    s.load(True, p, 1)


def load_elem_defs(s, at: int, count: int):
    """14034D340: count FxElemDefs (0x138): velSamples ((velIntervalCount + 1) × 0x60) and visSamples
    ((visStateIntervalCount + 1) × 0x50), each when non-null, aligned 4; the visuals; the three effect references
    (+0xF0 effectOnImpact, +0xF8 effectOnDeath, +0x100 effectEmitted); the extended definition."""
    s.load(True, at, ELEM_SIZE * count)
    for i in range(count):
        e = at + ELEM_SIZE * i
        for ptr, n, size in ((0xC0, 0xB7, 0x60), (0xC8, 0xB8, 0x50)):
            if s.u64(e + ptr):
                p = s.align(4)
                s.put_u64(e + ptr, p)
                s.load(True, p, (_u8(s, e + n) + 1) * size)
        _load_visuals(s, e)
        for off in (0xF0, 0xF8, 0x100):
            _effect_ref(s, e + off)
        _load_extended(s, e)


def load_effect(s, h: int, at_stream_start: bool = True):
    """14034D040 (Load_FxEffectDef): 0x40 bytes, in the virtual block: name, then elemDefs (+0x38, any non-null value:
    aligned 4) with elemDefCountLooping + elemDefCountOneShot + elemDefCountEmission (+0x14, +0x18, +0x1C)
    elements."""
    s.load(at_stream_start, h, EFFECT_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    if s.u64(h + 0x38):
        p = s.align(4)
        s.put_u64(h + 0x38, p)
        load_elem_defs(s, p, _i32(s, h + 0x14) + _i32(s, h + 0x18) + _i32(s, h + 0x1C))
    s.pop()


load_effect_ptr = iw6ff.asset_ptr(ASSET_FX, lambda s, h: load_effect(s, h, True))   # 14034D120


def register(asset_loaders: dict, material_ptr=None, xmodel_ptr=None, image_ptr=None):
    """Add the loaders (types 0x25, 0x1B, 0x3E) and set the asset pointer rules effects use for materials, models and
    images (material.load_material_ptr, xmodel.load_xmodel_ptr, image.load_gfx_image_ptr)."""
    asset_loaders[ASSET_FX] = load_effect_ptr
    asset_loaders[ASSET_LIGHTDEF] = load_light_def_ptr
    asset_loaders[ASSET_PARTICLE_SIM_ANIMATION] = load_particle_sim_animation_ptr
    for k, v in (("material_ptr", material_ptr), ("xmodel_ptr", xmodel_ptr), ("image_ptr", image_ptr)):
        if v is not None:
            HOOKS[k] = v


# ==== 2. reader ===================================================================================================

def _cstr(mem, a):
    if not a:
        return None
    out = bytearray()
    while True:
        b = mem.read(a, 64)
        i = b.find(b"\0")
        if i >= 0:
            return (out + b[:i]).decode("latin1")
        out += b
        a += 64


def _q(mem, a):
    return struct.unpack("<Q", mem.read(a, 8))[0]


def _asset_name(mem, p):
    """The name of the asset whose header is at p (its first field), or None."""
    return _cstr(mem, _q(mem, p)) if p else None


@dataclass
class VisualState:
    color: tuple
    unlit_hdr_scale: float
    rotation_delta: float
    rotation_total: float
    size: tuple
    scale: float


@dataclass
class Elem:
    type: int
    type_name: str
    flags: int
    flags2: int
    spawn: tuple                     # looping (intervalMsec, count) or one-shot count range
    spawn_range: tuple
    fade_in: tuple
    fade_out: tuple
    spawn_delay_msec: tuple
    life_span_msec: tuple
    spawn_origin: tuple
    spawn_offset_radius: tuple
    spawn_offset_height: tuple
    spawn_angles: tuple
    angular_velocity: tuple
    initial_rotation: tuple
    gravity: tuple
    reflection_factor: tuple
    atlas: dict
    lit_type: int
    visuals: list                    # names: materials, models, effects, sounds, lights, ...
    vel_samples: list                # per interval: ((local velocity min, max), (local delta ...), (world ...), ...)
    vis_samples: list                # per interval: (base VisualState, amplitude VisualState)
    coll_bounds: tuple
    effect_on_impact: str | None
    effect_on_death: str | None
    effect_emitted: str | None
    emit_dist: tuple
    emit_dist_variance: tuple
    extended: dict | None
    sort_order: int
    lighting_frac: int
    use_item_clip: int
    fade_info: int
    random_seed: int
    lit_max_color_change_per_sec: float
    unlit_hdr_scalar: float
    raw: bytes = b""


@dataclass
class Effect:
    name: str
    flags: int
    total_size: int
    msec_looping_life: int
    counts: tuple                    # (looping, one-shot, emission)
    elem_max_radius: float
    occlusion: dict
    elems: list = field(default_factory=list)


def _ranges(b, off, n):
    v = struct.unpack_from(f"<{2 * n}f", b, off)
    return tuple((v[2 * i], v[2 * i + 1]) for i in range(n))


def _vis_state(b, off):
    v = struct.unpack_from("<10f", b, off)
    return VisualState(v[0:4], v[4], v[5], v[6], v[7:9], v[9])


def _visual_name(mem, t, p, at=None, ref_names=None):
    """A visual's name: the material, model, effect, light def or particle animation it points at, or the sound or
    vector field name it is."""
    if t == ELEM_RUNNER and ref_names and at in ref_names:
        return ref_names[at]
    if not p:
        return None
    if t in (ELEM_SOUND, ELEM_VECTORFIELD):
        return _cstr(mem, p)
    if t == ELEM_OMNI_LIGHT:
        return None
    return _asset_name(mem, p)


def read_elem(mem, a: int, ref_names=None) -> Elem:
    b = mem.read(a, ELEM_SIZE)
    t, lit, nvis, nvel, nvs = b[0xB4], b[0xB5], b[0xB6], b[0xB7], b[0xB8]
    vis_p = struct.unpack_from("<Q", b, 0xD0)[0]
    if t == ELEM_DECAL:
        visuals = [[_asset_name(mem, _q(mem, vis_p + 0x18 * i + 8 * k)) for k in range(3)]
                   for i in range(nvis)] if vis_p else []
    elif nvis < 2:
        visuals = [_visual_name(mem, t, vis_p, a + 0xD0, ref_names)] if nvis else []
    else:
        visuals = [_visual_name(mem, t, _q(mem, vis_p + 8 * i), vis_p + 8 * i, ref_names)
                   for i in range(nvis)] if vis_p else []
    vel_p, vs_p = struct.unpack_from("<QQ", b, 0xC0)
    vel = []
    if vel_p:
        raw = mem.read(vel_p, (nvel + 1) * 0x60)
        for i in range(nvel + 1):
            f = struct.unpack_from("<24f", raw, 0x60 * i)
            vel.append(tuple((f[6 * k:6 * k + 3], f[6 * k + 3:6 * k + 6]) for k in range(4)))
    vis = []
    if vs_p:
        raw = mem.read(vs_p, (nvs + 1) * 0x50)
        vis = [(_vis_state(raw, 0x50 * i), _vis_state(raw, 0x50 * i + 0x28)) for i in range(nvs + 1)]
    refs = [(ref_names or {}).get(a + 0xF0 + 8 * k) or (_asset_name(mem, p) if p else None)
            for k, p in enumerate(struct.unpack_from("<3Q", b, 0xF0))]
    ext_p = struct.unpack_from("<Q", b, 0x118)[0]
    extended = _read_extended(mem, t, ext_p) if ext_p else None
    atlas = dict(zip(("behavior", "index", "fps", "loopCount", "colIndexBits", "rowIndexBits"), b[0xAC:0xB2]))
    atlas["entryCount"] = struct.unpack_from("<h", b, 0xB2)[0]
    flags, flags2 = struct.unpack_from("<II", b, 0)
    return Elem(
        t, ELEM_TYPE_NAMES.get(t, f"type{t}"), flags, flags2, struct.unpack_from("<ii", b, 8),
        _ranges(b, 0x10, 1)[0], _ranges(b, 0x18, 1)[0], _ranges(b, 0x20, 1)[0],
        struct.unpack_from("<ii", b, 0x2C), struct.unpack_from("<ii", b, 0x34), _ranges(b, 0x3C, 3),
        _ranges(b, 0x54, 1)[0], _ranges(b, 0x5C, 1)[0], _ranges(b, 0x64, 3), _ranges(b, 0x7C, 3),
        _ranges(b, 0x94, 1)[0], _ranges(b, 0x9C, 1)[0], _ranges(b, 0xA4, 1)[0], atlas, lit, visuals, vel, vis,
        (struct.unpack_from("<3f", b, 0xD8), struct.unpack_from("<3f", b, 0xE4)), refs[0], refs[1], refs[2],
        _ranges(b, 0x108, 1)[0], _ranges(b, 0x110, 1)[0], extended, b[0x120], b[0x121], b[0x122], b[0x123],
        struct.unpack_from("<i", b, 0x124)[0], *struct.unpack_from("<ff", b, 0x128), raw=b)


def _read_extended(mem, t, p):
    if t == ELEM_TRAIL:
        h = mem.read(p, 0x30)
        scroll, repeat, inv_split, inv_arc, inv_time, nv = struct.unpack_from("<iifffi", h, 0)
        verts_p, ni, inds_p = struct.unpack_from("<Qi4xQ", h, 0x18)
        verts = [struct.unpack_from("<6f", mem.read(verts_p + 0x18 * i, 0x18)) for i in range(nv)] if verts_p else []
        inds = list(struct.unpack(f"<{ni}H", mem.read(inds_p, 2 * ni))) if inds_p and ni > 0 else []
        return {"kind": "trail", "scrollTimeMsec": scroll, "repeatDist": repeat, "invSplitDist": inv_split,
                "invSplitArcDist": inv_arc, "invSplitTime": inv_time, "verts": verts, "inds": inds}
    if t == ELEM_SPARK_FOUNTAIN:
        v = struct.unpack("<5fi7f", mem.read(p, 0x34))
        keys = ("gravity", "bounceFrac", "bounceRand", "sparkSpacing", "sparkLength", "sparkCount", "loopTime",
                "velMin", "velMax", "velConeFrac", "restSpeed", "boostTime", "boostFactor")
        return {"kind": "spark_fountain", **dict(zip(keys, v))}
    if t == ELEM_SPOT_LIGHT:
        v = struct.unpack("<5fi", mem.read(p, 0x18))
        keys = ("fovInnerFraction", "startRadius", "endRadius", "brightness", "maxLength", "exponent")
        return {"kind": "spot_light", **dict(zip(keys, v))}
    if t == ELEM_FLARE:
        h = mem.read(p, 0x70)
        out = {"kind": "flare", "position": struct.unpack_from("<f", h, 0)[0],
               "angularRotCount": struct.unpack_from("<i", h, 4)[0], "flags": struct.unpack_from("<i", h, 8)[0],
               "depthScaleRange": _ranges(h, 0xC, 1)[0], "depthScaleValue": _ranges(h, 0x14, 1)[0],
               "radialRot": _ranges(h, 0x1C, 1)[0], "radialScaleX": _ranges(h, 0x24, 1)[0],
               "radialScaleY": _ranges(h, 0x2C, 1)[0], "dir": struct.unpack_from("<3f", h, 0x34)}
        for name, ptr, count in (("intensityX", 0x50, 0x40), ("intensityY", 0x58, 0x44),
                                 ("srcCosIntensity", 0x60, 0x48), ("srcCosScale", 0x68, 0x4C)):
            q = struct.unpack_from("<Q", h, ptr)[0]
            n = struct.unpack_from("<i", h, count)[0] + 1
            out[name] = list(struct.unpack(f"<{n}f", mem.read(q, 4 * n))) if q and n > 0 else []
        return out
    return {"kind": f"type{t}", "byte": mem.read(p, 1)[0]}


def read_effect(mem, a: int, ref_names=None) -> Effect:
    """The effect at a. ref_names: the loader's fx_ref_names, for the names of referenced effects (runners,
    effectOnImpact / OnDeath / Emitted) that the handle no longer gives."""
    h = mem.read(a, EFFECT_SIZE)
    name_p, flags, total, loop_life, n_loop, n_one, n_emit, max_r, bias, fin, fout, smin, smax, elems_p = \
        struct.unpack("<QiiiiiiffiiffQ", h)
    fx = Effect(_cstr(mem, name_p), flags, total, loop_life, (n_loop, n_one, n_emit), max_r,
                {"depthBias": bias, "fadeIn": fin, "fadeOut": fout, "scaleRange": (smin, smax)})
    if elems_p:
        fx.elems = [read_elem(mem, elems_p + ELEM_SIZE * i, ref_names) for i in range(n_loop + n_one + n_emit)]
    return fx


def to_json(effect: Effect) -> dict:
    """An Effect as plain JSON-able data (the raw element bytes left out)."""
    import dataclasses
    d = dataclasses.asdict(effect)
    for e in d["elems"]:
        e.pop("raw", None)
    return d

