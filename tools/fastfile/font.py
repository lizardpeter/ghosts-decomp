#!/usr/bin/env python3
"""Fonts in Call of Duty: Ghosts PC zones (Microsoft Store build): Font_s (asset type 0x1D, "font"): a bitmap font's
glyphs in a texture atlas (the material's image).

1. Loaders, the Store build's statement for statement: Load_FontHandle (14034CF50) and Load_Font (14034CE20).
   tests/fastfile/zone_check.py checks them against the game; src/gfx_d3d/r_font_load_db.cpp is the same in C++.
2. A reader: read_font (name, pixel height, materials, glyphs with their atlas rectangles).

    python3 tools/fastfile/font.py <zone.ff> [--out <folder>]    # every font's glyphs as JSON

docs/assets/fonts.md has the format.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import iw6ff

BLOCK_VIRTUAL = 3
ASSET_FONT = 0x1D
FONT_SIZE, GLYPH_SIZE = 0x28, 0x18
HOOKS = {"material_ptr": None}


def _h(name):
    fn = HOOKS[name]
    if fn is None:
        raise NotImplementedError(f"font.HOOKS[{name!r}] is not set (register() sets it)")
    return fn


def load_font(s, h: int, at_stream_start: bool = True):
    """14034CE20 (Load_Font): 0x28 bytes, in the virtual block: name (+0), the material (+0x10) and glow material
    (+0x18), and glyphCount (+0xC) glyphs of 0x18 bytes (+0x20, -1: aligned 4)."""
    s.load(at_stream_start, h, FONT_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    _h("material_ptr")(s, h + 0x10)
    _h("material_ptr")(s, h + 0x18)
    v = s.u64(h + 0x20)
    if v:
        if v == iw6ff.PTR_INLINE:
            p = s.align(4)
            s.put_u64(h + 0x20, p)
            n = struct.unpack("<i", s.read(h + 0xC, 4))[0]
            s.load(True, p, n * GLYPH_SIZE)
        else:
            s.put_u64(h + 0x20, s.offset_to_pointer(v))
    s.pop()


load_font_ptr = iw6ff.asset_ptr(ASSET_FONT, lambda s, h: load_font(s, h, True))   # 14034CF50 (Load_FontHandle)


def register(asset_loaders: dict, material_ptr=None):
    asset_loaders[ASSET_FONT] = load_font_ptr
    if material_ptr is not None:
        HOOKS["material_ptr"] = material_ptr


@dataclass
class Glyph:
    letter: int          # the character (UCS-2)
    x0: int              # offset from the pen position to the glyph's top left, in pixels
    y0: int
    dx: int              # advance
    width: int
    height: int
    s0: float            # the glyph's rectangle in the atlas, 0..1
    t0: float
    s1: float
    t1: float


@dataclass
class Font:
    name: str
    pixel_height: int
    material: str | None
    glow_material: str | None
    glyphs: list


def _cstr(mem, a):
    if not a:
        return None
    out = bytearray()
    while True:
        chunk = mem.read(a + len(out), 64)
        i = chunk.find(b"\0")
        if i >= 0:
            return (out + chunk[:i]).decode("latin1")
        out += chunk


def read_font(mem, a: int) -> Font:
    name_p, height, count, mat, glow, glyphs_p = struct.unpack("<QiiQQQ", mem.read(a, FONT_SIZE))
    raw = mem.read(glyphs_p, count * GLYPH_SIZE) if glyphs_p and count > 0 else b""
    glyphs = [Glyph(*struct.unpack_from("<HbbBBBx4f", raw, GLYPH_SIZE * i)) for i in range(len(raw) // GLYPH_SIZE)]
    material = (lambda p: _cstr(mem, mem.u64(p)) if p else None)
    return Font(_cstr(mem, name_p), height, material(mat), material(glow), glyphs)


def main(argv=None) -> int:
    import argparse
    import dataclasses
    import json
    import os
    import sys
    ap = argparse.ArgumentParser(description="Write a Ghosts PC zone's fonts as JSON.")
    ap.add_argument("fastfile")
    ap.add_argument("--out", default=".")
    opts = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loaders
    loaders.register_all()
    with open(opts.fastfile, "rb") as f:
        zone = iw6ff.read_fastfile(f.read(), os.path.basename(opts.fastfile).rsplit(".", 1)[0])
    if not zone.complete:
        print(f"the reader stopped at asset {zone.stopped_at} (type {zone.assets[zone.stopped_at].type:#x})")
    os.makedirs(opts.out, exist_ok=True)
    n = 0
    for a in zone.assets:
        if a.type == ASSET_FONT and a.header:
            font = read_font(zone.stream, a.header)
            path = os.path.join(opts.out, font.name.replace("/", "__") + ".json")
            with open(path, "w") as f:
                json.dump(dataclasses.asdict(font), f, indent=1)
            print(f"{font.name}: {font.pixel_height} px, {len(font.glyphs)} glyphs, material {font.material}")
            n += 1
    print(f"{n} fonts written to {opts.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
