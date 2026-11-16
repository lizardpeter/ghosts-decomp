#!/usr/bin/env python3
"""Weapons and vehicles in Call of Duty: Ghosts PC zones (Microsoft Store build): WeaponCompleteDef (asset type 0x23,
"weapon") with its WeaponDef, WeaponAttachment (0x22), TracerDef (0x31) and VehicleDef (0x32).

Loaders only, the Store build's statement for statement (Load_WeaponCompleteDefPtr 14035ACA0, Load_WeaponAttachmentPtr
14035A240, Load_TracerDefPtr 1403585D0, Load_VehicleDefPtr 140359150 and the functions under them);
tests/fastfile/zone_check.py checks them against the game. docs/assets/weapons.md lists what each loads.

The generated loaders follow a few rules, which the helpers below name:
- an XString (_xs), a sound alias by name (Load_SndAliasCustom, _snd), an effect, material, model, animation, physics
  or tracer asset pointer (the asset pointer rule);
- an inline array (_inline): -1 means it follows, aligned, and is loaded; any other non-null value is an offset;
- a "trusted" inline array (_any): any non-null value means it follows (no offset form).
"""
from __future__ import annotations

import struct

import iw6ff

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
BLOCK_VIRTUAL = 3
ASSET_ATTACHMENT, ASSET_WEAPON, ASSET_TRACER, ASSET_VEHICLE = 0x22, 0x23, 0x31, 0x32
HOOKS = {"material_ptr": None, "xmodel_ptr": None, "xanim_ptr": None, "fx_ptr": None, "snd": None,
         "physpreset_ptr": None, "physcollmap_ptr": None}


def _h(name):
    fn = HOOKS[name]
    if fn is None:
        raise NotImplementedError(f"weapon.HOOKS[{name!r}] is not set (register() sets it)")
    return fn


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _xs(s, at):
    s.xstring_ptr(at)


def _script_string(s, at):
    """Load_ScriptStringCustom (14037AF90)."""
    idx = s.u32(at)
    s.put_u32(at, s.u64(s.string_table + 8 * idx) & 0xFFFFFFFF)


def _script_strings(s, at, count):
    for i in range(count):
        _script_string(s, at + 4 * i)


def _inline(s, at, align, body):
    """-1: aligned, then body(address); another non-null value: an offset (DB_ConvertOffsetToPointer)."""
    v = s.u64(at)
    if not v:
        return
    if v != PTR_INLINE:
        s.put_u64(at, s.offset_to_pointer(v))
        return
    p = s.align(align)
    s.put_u64(at, p)
    body(p)


def _any(s, at, align, body):
    """Any non-null value: the data follows (aligned)."""
    if s.u64(at):
        p = s.align(align)
        s.put_u64(at, p)
        body(p)


def _plain(size):
    return lambda s, p: s.load(True, p, size)


def _ptr_array(rule):
    """Load_<T>PtrArray (Load_XModelPtrArray 14035E620, the animation 14035D4C0, attachment 14035A330 and effect
    14034D210 arrays): the pointers (loaded with the array), then each by the asset pointer rule."""
    def load(s, p, count):
        s.load(True, p, 8 * count)
        for i in range(count):
            rule(s, p + 8 * i)
    return load


def _strings_array(count):
    def body(s, p):
        s.load(True, p, 4 * count)
        _script_strings(s, p, count)
    return body


# ==== tracers =====================================================================================================

def load_tracer(s, h: int, at_stream_start: bool = True):
    """140358530 (Load_TracerDef): 0x78 bytes, in the virtual block: name, material (+8)."""
    s.load(at_stream_start, h, 0x78)
    s.push(BLOCK_VIRTUAL)
    _xs(s, h)
    _h("material_ptr")(s, h + 8)
    s.pop()


load_tracer_ptr = iw6ff.asset_ptr(ASSET_TRACER, lambda s, h: load_tracer(s, h, True))   # 1403585D0


# ==== attachments =================================================================================================

def _four_materials(s, p):
    """14034A080: a 0x38-byte block (already loaded) with four material handles at +0, +8, +0x10, +0x18."""
    for k in range(4):
        _h("material_ptr")(s, p + 8 * k)


def _attachment_ammo_names(s, p):
    """14034AEA0: 0x10 bytes, two XStrings."""
    s.load(True, p, 0x10)
    _xs(s, p)
    _xs(s, p + 8)


def _attachment_effects(s, p):
    """14034AD20: 0x90 bytes: name (+0x20), model (+0x28), effects and sounds."""
    s.load(True, p, 0x90)
    _xs(s, p + 0x20)
    _h("xmodel_ptr")(s, p + 0x28)
    _h("fx_ptr")(s, p + 0x38)
    _h("snd")(s, p + 0x48)
    _h("fx_ptr")(s, p + 0x50)
    _h("snd")(s, p + 0x58)
    _h("fx_ptr")(s, p + 0x70)
    _h("fx_ptr")(s, p + 0x80)
    _h("snd")(s, p + 0x88)


def load_attachment(s, h: int, at_stream_start: bool = True):
    """140359A30 (Load_WeaponAttachment): 0x118 bytes, in the virtual block."""
    s.load(at_stream_start, h, 0x118)
    s.push(BLOCK_VIRTUAL)
    _xs(s, h)
    _xs(s, h + 8)
    models = _ptr_array(_h("xmodel_ptr"))
    for off, n in ((0x20, 0x40), (0x28, 0x40), (0x30, 0x10)):
        _inline(s, h + off, 8, lambda p, n=n: models(s, p, n))

    def tracer_block(p):
        s.load(True, p, 0x20)
        load_tracer_ptr(s, p + 0x10)
    _any(s, h + 0x38, 4, tracer_block)
    _any(s, h + 0x40, 4, lambda p: s.load(True, p, 9))
    _any(s, h + 0x48, 2, lambda p: s.load(True, p, 2))
    if s.u64(h + 0x50):                                   # unaligned
        p = s.addr()
        s.put_u64(h + 0x50, p)
        s.load(True, p, 3)

    def two_materials(base, size):
        def body(p):
            s.load(True, p, size)
            _h("material_ptr")(s, p + base)
            _h("material_ptr")(s, p + base + 8)
        return body
    _any(s, h + 0x58, 4, two_materials(8, 0x28))
    for off, size in ((0x60, 0xC), (0x68, 0x18), (0x70, 0x1C), (0x78, 0x4C), (0x80, 0x18), (0x88, 0x40),
                      (0x90, 0x40), (0x98, 0x18), (0xA0, 0x18), (0xA8, 0x30), (0xB0, 0x58), (0xB8, 0x30)):
        _any(s, h + off, 4, lambda p, size=size: s.load(True, p, size))

    def materials_block(p):
        s.load(True, p, 0x40)
        _four_materials(s, p)
    _any(s, h + 0xC0, 4, materials_block)
    _any(s, h + 0xC8, 4, two_materials(0, 0x20))
    _any(s, h + 0xD0, 4, lambda p: _attachment_ammo_names(s, p))
    _any(s, h + 0xD8, 4, lambda p: _attachment_effects(s, p))
    s.pop()


load_attachment_ptr = iw6ff.asset_ptr(ASSET_ATTACHMENT, lambda s, h: load_attachment(s, h, True))   # 14035A240


# ==== weapons =====================================================================================================

def load_weapon_def(s, d: int, complete: int, at_stream_start: bool = True):
    """14035AD90 (Load_WeaponDef): 0xA98 bytes (the block is the complete def's: no push). `complete` is the
    WeaponCompleteDef being loaded: two arrays here take their counts from it (+0x104, +0x106)."""
    s.load(at_stream_start, d, 0xA98)
    material, xmodel, fx, snd = _h("material_ptr"), _h("xmodel_ptr"), _h("fx_ptr"), _h("snd")
    models, anims = _ptr_array(xmodel), _ptr_array(_h("xanim_ptr"))
    q = lambda k: d + 8 * k  # noqa: E731  (the loader's qword indices)
    _xs(s, q(0))
    _inline(s, q(1), 8, lambda p: models(s, p, 0x40))
    for k in (2, 3, 4):
        xmodel(s, q(k))
    material(s, q(5))
    material(s, q(6))

    def material_array(p):
        s.load(True, p, 8 * 0x3F)                         # Load_MaterialHandleArray(true, 0x3F)
        for i in range(0x3F):
            material(s, p + 8 * i)
    _inline(s, q(7), 8, material_array)
    _inline(s, q(8), 8, lambda p: anims(s, p, 0x7C))
    _inline(s, q(9), 8, lambda p: anims(s, p, 0x7C))
    _xs(s, q(10))
    _inline(s, q(0xB), 4, lambda p: _strings_array(0x18)(s, p))
    _inline(s, q(0xC), 4, lambda p: _strings_array(0x18)(s, p))
    for k in (0xD, 0xE, 0xF):
        _inline(s, q(k), 4, lambda p: _strings_array(0x10)(s, p))
    _inline(s, q(0x10), 8, lambda p: _ptr_array(fx)(s, p, 0x10))
    _inline(s, q(0x11), 4, lambda p: _strings_array(0x10)(s, p))
    for k in (0x17, 0x18, 0x19):
        fx(s, q(k))
    for k in range(0x1A, 0x4A):
        snd(s, q(k))

    def sound_array(p):
        s.load(True, p, 8 * 0x1F)
        for i in range(0x1F):
            snd(s, p + 8 * i)
    _inline(s, q(0x4A), 8, sound_array)
    _inline(s, q(0x4B), 8, sound_array)
    for k in range(0x4C, 0x51):
        fx(s, q(k))
    material(s, q(0x51))
    material(s, q(0x52))
    _inline(s, q(0x69), 8, lambda p: models(s, p, 0x40))
    for k in range(0x6A, 0x6E):
        xmodel(s, q(k))
    for k in (0x6E, 0x70, 0x72):
        material(s, q(k))
    for k in (0x75, 0x77, 0x7A):
        _xs(s, q(k))
    _four_materials(s, q(0xB6))                           # 14034A080(false): inside the def
    _h("physcollmap_ptr")(s, q(0xD3))
    _xs(s, q(0xE2))
    xmodel(s, q(0xE3))
    fx(s, q(0xE5))
    fx(s, q(0xE6))
    snd(s, q(0xE7))
    snd(s, q(0xE8))
    _inline(s, q(0xEC), 4, _plain_at(s, 0x7C))
    _inline(s, q(0xED), 4, _plain_at(s, 0x7C))
    for k in (0xEE, 0xEF, 0xF3):
        fx(s, q(k))
    snd(s, q(0xF4))
    _xs(s, q(0x10B))
    _inline(s, q(0x10D), 4, _plain_at(s, 8 * _u16(s, complete + 0x104)))
    _xs(s, q(0x10C))
    _inline(s, q(0x10E), 4, _plain_at(s, 8 * _u16(s, complete + 0x106)))
    for k in (0x119, 0x11A, 0x11F):
        _xs(s, q(k))
    _inline(s, q(0x125), 4, _plain_at(s, 0x58))
    _xs(s, q(0x126))
    _xs(s, q(0x127))
    load_tracer_ptr(s, q(0x128))
    snd(s, q(0x12E))
    fx(s, q(0x12F))
    _xs(s, q(0x130))
    snd(s, q(0x133))
    for k in range(0x134, 0x13C):                         # two inline arrays of 4 sounds
        snd(s, q(k))
    snd(s, q(0x13C))
    snd(s, q(0x13D))
    _script_string(s, d + 0xA24)
    _script_string(s, d + 0xA8C)
    xmodel(s, q(0x152))


def _plain_at(s, size):
    return lambda p: s.load(True, p, size)


def load_weapon(s, h: int, at_stream_start: bool = True):
    """14035A460 (Load_WeaponCompleteDef): 0x128 bytes, in the virtual block."""
    s.load(at_stream_start, h, 0x128)
    s.push(BLOCK_VIRTUAL)
    q = lambda k: h + 8 * k  # noqa: E731
    _xs(s, q(0))
    _inline(s, q(1), 4, lambda p: load_weapon_def(s, p, h, True))
    _xs(s, q(2))
    _inline(s, q(3), 4, lambda p: _strings_array(0x20)(s, p))
    attachments = _ptr_array(load_attachment_ptr)
    for k, n in ((4, 6), (5, 3), (6, 8)):
        _inline(s, q(k), 8, lambda p, n=n: attachments(s, p, n))
    _inline(s, q(7), 8, lambda p: _ptr_array(_h("xanim_ptr"))(s, p, 0x7C))

    def overrides(size, body):
        def load(p, count):
            s.load(True, p, size * count)
            for i in range(count):
                body(p + size * i)
        return load
    anim_override = overrides(0x28, lambda e: (_h("xanim_ptr")(s, e + 8), _h("xanim_ptr")(s, e + 0x10)))
    sound_override = overrides(0x20, lambda e: (_h("snd")(s, e + 8), _h("snd")(s, e + 0x10)))
    fx_override = overrides(0x20, lambda e: (_h("fx_ptr")(s, e + 8), _h("fx_ptr")(s, e + 0x10)))
    _inline(s, q(9), 4, lambda p: anim_override(p, _u32(s, q(8))))
    _inline(s, q(0xB), 4, lambda p: sound_override(p, _u32(s, q(0xA))))
    _inline(s, q(0xD), 4, lambda p: fx_override(p, _u32(s, q(0xC))))
    _inline(s, q(0xF), 4, lambda p: s.load(True, p, 0x10 * _u32(s, q(0xE))))

    def reload_overrides(p):                               # 140354C50 per 0x18 entry: two arrays of 24 strings
        n = _u32(s, q(0x10))
        s.load(True, p, 0x18 * n)
        for i in range(n):
            e = p + 0x18 * i
            _inline(s, e + 8, 4, lambda r: _strings_array(0x18)(s, r))
            _inline(s, e + 0x10, 4, lambda r: _strings_array(0x18)(s, r))
    _any(s, q(0x11), 4, reload_overrides)
    _xs(s, q(0x18))
    _h("material_ptr")(s, q(0x1B))
    _h("material_ptr")(s, q(0x1C))
    _inline(s, q(0x21), 4, lambda p: s.load(True, p, 8 * _u16(s, h + 0x104)))
    _inline(s, q(0x22), 4, lambda p: s.load(True, p, 8 * _u16(s, h + 0x106)))
    _xs(s, q(0x24))
    s.pop()


load_weapon_ptr = iw6ff.asset_ptr(ASSET_WEAPON, lambda s, h: load_weapon(s, h, True))   # 14035ACA0


# ==== vehicles ====================================================================================================

def load_vehicle(s, h: int, at_stream_start: bool = True):
    """140358960 (Load_VehicleDef): 0x610 bytes, in the virtual block."""
    s.load(at_stream_start, h, 0x610)
    s.push(BLOCK_VIRTUAL)
    fx, snd, material = _h("fx_ptr"), _h("snd"), _h("material_ptr")
    q = lambda k: h + 8 * k  # noqa: E731
    _xs(s, q(0))
    _xs(s, q(2))
    phys = q(0x17)                                        # 140359240: VehiclePhysDef (200 bytes, inside)
    _xs(s, phys + 8)
    _h("physpreset_ptr")(s, phys + 0x10)
    _xs(s, phys + 0x18)
    fx(s, q(0x44))
    fx(s, q(0x45))
    _xs(s, q(0x6C))
    load_weapon_ptr(s, q(0x6D))
    snd(s, q(0x73))
    snd(s, q(0x74))
    _script_strings(s, h + 0x3BC, 4)
    fx(s, q(0x7A))
    fx(s, q(0x7B))
    for k in range(0x7C, 0x80):
        material(s, q(k))
    for k in range(0x81, 0x85):
        snd(s, q(k))
    _script_string(s, h + 0x42C)
    for k in range(0x86, 0x8A):
        snd(s, q(k))
    _script_string(s, h + 0x454)
    for k in (0x8B, 0x8C, 0x8D, 0x8F, 0x90, 0x91, 0x92, 0x94, 0x96, 0x98, 0x9A, 0x9C):
        snd(s, q(k))
    _xs(s, q(0x9E))
    for k in range(0x9F, 0x9F + 0x1F):
        snd(s, q(k))
    _xs(s, q(0xC0))
    s.pop()


load_vehicle_ptr = iw6ff.asset_ptr(ASSET_VEHICLE, lambda s, h: load_vehicle(s, h, True))   # 140359150


def register(asset_loaders: dict, **hooks):
    """Add the loaders (types 0x22, 0x23, 0x31, 0x32) and set the asset pointer rules they call: material_ptr,
    xmodel_ptr, xanim_ptr, fx_ptr, snd (Load_SndAliasCustom), physpreset_ptr, physcollmap_ptr."""
    asset_loaders[ASSET_ATTACHMENT] = load_attachment_ptr
    asset_loaders[ASSET_WEAPON] = load_weapon_ptr
    asset_loaders[ASSET_TRACER] = load_tracer_ptr
    asset_loaders[ASSET_VEHICLE] = load_vehicle_ptr
    for k, v in hooks.items():
        if k not in HOOKS:
            raise KeyError(k)
        if v is not None:
            HOOKS[k] = v
