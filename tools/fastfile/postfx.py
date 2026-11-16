#!/usr/bin/env python3
"""The post-processing assets of Call of Duty: Ghosts PC zones (Microsoft Store build): Colorization (asset type
0x38), ColorizationSet (0x39) and ToneMapping (0x3A), the colour grading and filmic tone curve a map or vision set
uses.

1. Loaders: the Store build's, statement for statement (Load_ColorizationSetPtr 14034BAD0, Load_ColorizationPtr
   14034B8C0, Load_ToneMappingPtr 140358440); tests/fastfile/zone_check.py checks them against the game.
2. Readers: read_colorization, read_colorization_set, read_tone_mapping. docs/assets/postfx.md.

The layouts are the servers' PDBs'. Colorization and ToneMapping keep their name last (+0x28, +0x68), after the
renderer's GfxColorization / GfxToneMapping constants.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import iw6ff

BLOCK_VIRTUAL = 3
ASSET_COLORIZATION, ASSET_COLORIZATION_SET, ASSET_TONE_MAPPING = 0x38, 0x39, 0x3A
HOOKS = {"material_ptr": None}


# ==== 1. loaders ==================================================================================================

def load_colorization(s, h: int, at_stream_start: bool = True):
    """14034B830 (Load_Colorization): 0x30 bytes, in the virtual block: the name XString at +0x28."""
    s.load(at_stream_start, h, 0x30)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h + 0x28)
    s.pop()


load_colorization_ptr = iw6ff.asset_ptr(ASSET_COLORIZATION, lambda s, h: load_colorization(s, h, True))  # 14034B8C0


def load_colorization_set(s, h: int, at_stream_start: bool = True):
    """14034B9B0 (Load_ColorizationSet): 0x68 bytes, in the virtual block: name, the five colorizations (+0x30..+0x50,
    Load_ColorizationPtr each), alternateMaskMaterial (+0x58, Load_MaterialHandle)."""
    s.load(at_stream_start, h, 0x68)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    for off in (0x30, 0x38, 0x40, 0x48, 0x50):
        load_colorization_ptr(s, h + off)
    if HOOKS["material_ptr"] is None:
        raise NotImplementedError("postfx.HOOKS['material_ptr'] is not set (register() sets it)")
    HOOKS["material_ptr"](s, h + 0x58)
    s.pop()


load_colorization_set_ptr = iw6ff.asset_ptr(ASSET_COLORIZATION_SET,
                                            lambda s, h: load_colorization_set(s, h, True))  # 14034BAD0


def load_tone_mapping(s, h: int, at_stream_start: bool = True):
    """1403583B0 (Load_ToneMapping): 0x70 bytes, in the virtual block: the name XString at +0x68."""
    s.load(at_stream_start, h, 0x70)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h + 0x68)
    s.pop()


load_tone_mapping_ptr = iw6ff.asset_ptr(ASSET_TONE_MAPPING, lambda s, h: load_tone_mapping(s, h, True))  # 140358440


def register(asset_loaders: dict, material_ptr=None):
    asset_loaders[ASSET_COLORIZATION] = load_colorization_ptr
    asset_loaders[ASSET_COLORIZATION_SET] = load_colorization_set_ptr
    asset_loaders[ASSET_TONE_MAPPING] = load_tone_mapping_ptr
    if material_ptr is not None:
        HOOKS["material_ptr"] = material_ptr


# ==== 2. readers ==================================================================================================

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


@dataclass
class Colorization:
    name: str
    power_and_desaturation: tuple   # GfxColorization
    scale: tuple
    bias: tuple


@dataclass
class ColorizationSet:
    name: str
    low_and_high_end_points: tuple
    mid_end_points: tuple
    alternate_depth_scale_and_bias: tuple
    colorization: Colorization | None
    alternate: Colorization | None
    low: Colorization | None
    mid: Colorization | None
    high: Colorization | None
    alternate_mask_material: str | None
    flags: int


@dataclass
class ToneMapping:
    name: str
    toe_strength: tuple             # GfxToneMapping, per channel
    toe_angle_numerator: tuple
    toe_angle_denominator: tuple
    linear_strength: tuple
    linear_angle: tuple
    shoulder_strength: tuple
    white_point: tuple
    exposure: tuple
    adaptation_rates: tuple


def read_colorization(mem, a: int) -> Colorization | None:
    if not a:
        return None
    v = struct.unpack("<10f", mem.read(a, 0x28))
    return Colorization(_cstr(mem, _q(mem, a + 0x28)), v[0:4], v[4:7], v[7:10])


def read_colorization_set(mem, a: int) -> ColorizationSet:
    h = mem.read(a, 0x68)
    f = struct.unpack_from("<10f", h, 8)
    ptrs = struct.unpack_from("<6Q", h, 0x30)
    cols = [read_colorization(mem, p) for p in ptrs[:5]]
    mat = _cstr(mem, _q(mem, ptrs[5])) if ptrs[5] else None
    return ColorizationSet(_cstr(mem, struct.unpack_from("<Q", h, 0)[0]), f[0:4], f[4:8], f[8:10], *cols, mat,
                           h[0x60])


def read_tone_mapping(mem, a: int) -> ToneMapping:
    v = struct.unpack("<26f", mem.read(a, 0x68))
    return ToneMapping(_cstr(mem, _q(mem, a + 0x68)), *(v[3 * i:3 * i + 3] for i in range(8)), v[24:26])
