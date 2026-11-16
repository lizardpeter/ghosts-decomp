#!/usr/bin/env python3
"""A map's glass and effect tables in Call of Duty: Ghosts PC zones (Microsoft Store build): GlassWorld (asset type
0x15, "glass_map"), FxWorld (0x19, "fx_map": the breakable glass system), FxImpactTable (0x26, "impactfx") and
SurfaceFxTable (0x27, "surfacefx").

Loaders only, the Store build's statement for statement (Load_GlassWorldPtr 1403520B0, Load_FxWorldPtr 14034E9B0,
Load_FxImpactTablePtr 14034E4E0, Load_SurfaceFxTablePtr 1403582C0 and the functions under them);
tests/fastfile/zone_check.py checks them against the game. docs/assets/map_assets.md.
"""
from __future__ import annotations

import struct

import iw6ff

BLOCK_RUNTIME, BLOCK_VIRTUAL = 2, 3
ASSET_GLASS_WORLD, ASSET_FX_WORLD, ASSET_IMPACT_FX, ASSET_SURFACE_FX = 0x15, 0x19, 0x26, 0x27
HOOKS = {"material_ptr": None, "fx_ptr": None, "snd": None, "physpreset_ptr": None}


def _h(name):
    fn = HOOKS[name]
    if fn is None:
        raise NotImplementedError(f"mapfx.HOOKS[{name!r}] is not set (register() sets it)")
    return fn


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _any(s, at, align, size):
    """Any non-null value: `size` bytes follow, aligned. Returns the address or 0."""
    if not s.u64(at):
        return 0
    p = s.align(align) if align > 1 else s.addr()
    s.put_u64(at, p)
    s.load(True, p, size)
    return p


def _script_string(s, at):
    """Load_ScriptStringCustom (14037AF90)."""
    idx = s.u32(at)
    s.put_u32(at, s.u64(s.string_table + 8 * idx) & 0xFFFFFFFF)


# ==== glass ==================================================================================================

def load_glass_world(s, h: int, at_stream_start: bool = True):
    """140351FE0 (Load_GlassWorld): 0x10 bytes, in the virtual block: name, then the GlassData (+8, any non-null
    value: 0x90 bytes, 14034EAA0): glass pieces (+0, count u32 +8, × 0xC) and glass defs (+0x18, count u32 +0x10,
    × 0x18, 14034EBA0: name, a script string (+8), and +0x10: u16 count +0xC × 2, aligned 2)."""
    s.load(at_stream_start, h, 0x10)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    d = _any(s, h + 8, 4, 0x90)
    if d:
        _any(s, d, 4, 0xC * _u32(s, d + 8))
        n = _u32(s, d + 0x10)
        p = _any(s, d + 0x18, 4, 0x18 * n)
        for i in range(n if p else 0):
            e = p + 0x18 * i
            s.xstring_ptr(e)
            _script_string(s, e + 8)
            _any(s, e + 0x10, 2, 2 * _u16(s, e + 0xC))
    s.pop()


load_glass_world_ptr = iw6ff.asset_ptr(ASSET_GLASS_WORLD, lambda s, h: load_glass_world(s, h, True))  # 1403520B0


# ==== the map's breakable glass system (fx_map) =============================================================

def _glass_def(s, e):
    """14034DD30 (Load_FxGlassDef), 0x78 bytes (already loaded): physics preset (+0x28), two materials (+0x18,
    +0x20), four effects (+0x30..+0x48), three sounds (+0x50..+0x60)."""
    _h("physpreset_ptr")(s, e + 0x28)
    _h("material_ptr")(s, e + 0x18)
    _h("material_ptr")(s, e + 0x20)
    for off in (0x30, 0x38, 0x40, 0x48):
        _h("fx_ptr")(s, e + off)
    for off in (0x50, 0x58, 0x60):
        _h("snd")(s, e + off)


def _runtime(s, at, align, size):
    s.push(BLOCK_RUNTIME)
    _any(s, at, align, size)
    s.pop()


def load_glass_system(s, g: int):
    """14034DE80 (Load_FxGlassSystem), 0xA8 bytes inside the FxWorld (already loaded): the glass defs (+0x30, count
    u32 +8, × 0x78), the per-piece state arrays in the runtime block (zero-filled; counts from +0xC, +0x24, +0x10
    and +0x18), then the initial pieces (+0x80, u16 × count +0x14; +0x88, 0x38 × count +0x14) and +0x90 (u32 ×
    count +0x2C)."""
    n = _u32(s, g + 8)
    p = _any(s, g + 0x30, 4, 0x78 * n)
    for i in range(n if p else 0):
        _glass_def(s, p + 0x78 * i)
    pieces = _u32(s, g + 0xC)
    _runtime(s, g + 0x38, 4, pieces << 5)
    _runtime(s, g + 0x40, 4, pieces << 5)
    _runtime(s, g + 0x48, 4, pieces * 0x30)
    _runtime(s, g + 0x50, 4, _u32(s, g + 0x24) << 2)
    _runtime(s, g + 0x58, 4, _u32(s, g + 0x10) << 2)
    _runtime(s, g + 0x60, 4, ((_i32(s, g + 0x18) * _i32(s, g + 0x10)) & 0xFFFFFFFF) << 2)
    _runtime(s, g + 0x68, 16, (_i32(s, g + 0xC) + 0xF) & 0xFFFFFFF0)
    _runtime(s, g + 0x70, 4, pieces * 0xC)
    _runtime(s, g + 0x78, 16, (((_i32(s, g + 0xC) + 3) & 0xFFFFFFFFFFFFFFFF) & 0xFFFFFFFC) << 2)
    _any(s, g + 0x80, 2, 2 * _u32(s, g + 0x14))
    _any(s, g + 0x88, 4, 0x38 * _u32(s, g + 0x14))
    _any(s, g + 0x90, 4, _u32(s, g + 0x2C) << 2)


def load_fx_world(s, h: int, at_stream_start: bool = True):
    """14034E910 (Load_FxWorld): 0xB0 bytes, in the virtual block: name, the FxGlassSystem (+8)."""
    s.load(at_stream_start, h, 0xB0)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    load_glass_system(s, h + 8)
    s.pop()


load_fx_world_ptr = iw6ff.asset_ptr(ASSET_FX_WORLD, lambda s, h: load_fx_world(s, h, True))   # 14034E9B0


# ==== impact and surface effect tables =======================================================================

def _effect_table(table_bytes, entries, entry_size, arrays):
    """A name and, behind +8 (any non-null value, aligned 4), `entries` fixed entries of effect handle arrays."""
    def load(s, h, at_stream_start=True):
        s.load(at_stream_start, h, 0x10)
        s.push(BLOCK_VIRTUAL)
        s.xstring_ptr(h)
        p = _any(s, h + 8, 4, entries * entry_size)
        for i in range(entries if p else 0):
            e = p + entry_size * i
            for off, count in arrays:
                for k in range(count):
                    _h("fx_ptr")(s, e + off + 8 * k)
        s.pop()
    return load


# 14034E380 (Load_FxImpactTable): 15 surfaces × 0x130: 31 effects (+0), 7 more (+0xF8)
load_impact_table = _effect_table(0x10, 15, 0x130, ((0, 0x1F), (0xF8, 7)))
# 140358180 (Load_SurfaceFxTable): 6 entries × 0xF8: 31 effects
load_surface_fx_table = _effect_table(0x10, 6, 0xF8, ((0, 0x1F),))
load_impact_table_ptr = iw6ff.asset_ptr(ASSET_IMPACT_FX, lambda s, h: load_impact_table(s, h, True))  # 14034E4E0
load_surface_fx_table_ptr = iw6ff.asset_ptr(ASSET_SURFACE_FX,
                                            lambda s, h: load_surface_fx_table(s, h, True))  # 1403582C0


def register(asset_loaders: dict, **hooks):
    asset_loaders[ASSET_GLASS_WORLD] = load_glass_world_ptr
    asset_loaders[ASSET_FX_WORLD] = load_fx_world_ptr
    asset_loaders[ASSET_IMPACT_FX] = load_impact_table_ptr
    asset_loaders[ASSET_SURFACE_FX] = load_surface_fx_table_ptr
    for k, v in hooks.items():
        if k not in HOOKS:
            raise KeyError(k)
        if v is not None:
            HOOKS[k] = v
