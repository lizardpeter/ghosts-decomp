"""Images (GfxImage) from a decompressed zone and the image paks (Store build), and their conversion to DDS.

Two layers, like tools/fastfile/material.py and xmodel.py:

1. Loaders do what the Store build's Load_* functions do (src/database/db_image_load.cpp, docs/assets/images.md)
   on the fastfile pipeline's Stream (tools/fastfile/iw6ff.py):
     load_gfx_image_ptr    Load_GfxImagePtr (14034F380): the asset pointer rule (temp block, alias / inline)
     load_gfx_image        Load_GfxImage (14034F120): the 0x68-byte header, its name, its pixels
     load_texture_pixels   Load_GfxImageLoadDefPixels (14034F1D0): the in-zone pixel data (temp block)
     load_image_stream     Load_ImageStream (140374E70): four streamed-image rows per streamed image
   The pixel data of an in-zone image lives in the temp block, which the next asset reuses; the game creates the
   texture from it at once (Load_Texture 14062BA80). The loader does the same: it copies the bytes out
   (`ImageState.pixels[address]`) while they are valid.
2. Readers and converters: read_image (header -> GfxImageInfo), mip_layout (where each face and mip level is in a
   pixel block, as Load_Texture walks it), read_stream_level (a streamed level from an imagefile pak: one zlib
   stream), and to_dds (a DDS file with the DX10 header, any DXGI format).
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
PTR_INSERT = 0xFDFDFDFFFFFFFFFE
BLOCK_TEMP, BLOCK_VIRTUAL = 0, 3
ASSET_TYPE_IMAGE = 0x0D
GFX_IMAGE_SIZE = 0x68
STREAM_LEVELS = 4          # rows per streamed image (GfxImage::streamLevels, one per picmip)
TS_WATER_MAP = 0x0B        # GfxImage::semantic of the water image: its pixels are not in the zone (1 byte)

# GfxImage::mapType
MAPTYPE_1D, MAPTYPE_2D, MAPTYPE_3D, MAPTYPE_CUBE, MAPTYPE_ARRAY = 2, 3, 4, 5, 6
MAPTYPE_NAMES = {2: "1D", 3: "2D", 4: "3D", 5: "cube", 6: "array"}
IMG_CATEGORY_WATER = 5

# DXGI formats: (name, bytes per block, block size). The Store build's Image_GetCardMemoryAmountForMipLevel
# (docs/assets/images.md) sizes a level as ceil(w/b) * ceil(h/b) * depth * bytes.
DXGI = {
    2: ("R32G32B32A32_FLOAT", 16, 1), 10: ("R16G16B16A16_FLOAT", 8, 1), 11: ("R16G16B16A16_UNORM", 8, 1),
    16: ("R32G32_FLOAT", 8, 1), 24: ("R10G10B10A2_UNORM", 4, 1), 26: ("R11G11B10_FLOAT", 4, 1),
    28: ("R8G8B8A8_UNORM", 4, 1), 29: ("R8G8B8A8_UNORM_SRGB", 4, 1), 34: ("R16G16_FLOAT", 4, 1),
    35: ("R16G16_UNORM", 4, 1), 41: ("R32_FLOAT", 4, 1), 49: ("R8G8_UNORM", 2, 1), 54: ("R16_FLOAT", 2, 1),
    56: ("R16_UNORM", 2, 1), 61: ("R8_UNORM", 1, 1), 65: ("A8_UNORM", 1, 1),
    71: ("BC1_UNORM", 8, 4), 72: ("BC1_UNORM_SRGB", 8, 4), 74: ("BC2_UNORM", 16, 4), 75: ("BC2_UNORM_SRGB", 16, 4),
    77: ("BC3_UNORM", 16, 4), 78: ("BC3_UNORM_SRGB", 16, 4), 80: ("BC4_UNORM", 8, 4), 81: ("BC4_SNORM", 8, 4),
    83: ("BC5_UNORM", 16, 4), 84: ("BC5_SNORM", 16, 4), 85: ("B5G6R5_UNORM", 2, 1), 87: ("B8G8R8A8_UNORM", 4, 1),
    88: ("B8G8R8X8_UNORM", 4, 1), 91: ("B8G8R8A8_UNORM_SRGB", 4, 1), 95: ("BC6H_UF16", 16, 4),
    96: ("BC6H_SF16", 16, 4), 98: ("BC7_UNORM", 16, 4), 99: ("BC7_UNORM_SRGB", 16, 4),
}


def level_size(fmt: int, width: int, height: int, depth: int = 1) -> int:
    """Image_GetCardMemoryAmountForMipLevel for the formats in DXGI."""
    _, nbytes, block = DXGI[fmt]
    return ((width + block - 1) // block) * ((height + block - 1) // block) * depth * nbytes


# ==== 1. loaders ===================================================================================================

@dataclass
class ImageState:
    """What the image loaders keep per stream: in-zone pixels by header address (copied when loaded, as the temp
    block is reused), the streamed-image rows handed out so far (sub_1403492E0's cursor) and each linked image's
    four rows (Load_ImageStream's 0x60-byte entry)."""
    rows: list = field(default_factory=list)          # Prefix.stream_images
    cursor: int = 0
    pixels: dict = field(default_factory=dict)        # temp-block header address -> bytes
    pixels_by_link: dict = field(default_factory=dict)  # linked (pool) header address -> bytes
    streams: dict = field(default_factory=dict)       # linked header address -> [row, row, row, row]
    order: list = field(default_factory=list)         # linked header addresses, in load order


def state_of(s) -> ImageState:
    st = getattr(s, "image_state", None)
    if st is None:
        st = ImageState()
        s.image_state = st
    return st


def load_texture_pixels(s, image: int):
    """Load_GfxImageLoadDefPixels (14034F1D0): the pointer at +0x38, in the temp block. NULL stays; an offset is an
    alias (DB_ConvertOffsetToAlias); -1/-2 are inline: the data follows at the current position (no alignment),
    -2 also reserving an alias slot. The water image (semantic TS_WATER_MAP) has a 1-byte placeholder; any other
    image has cardMemory.platform[0] (+0x24) bytes. Then Load_Texture (14062BA80) creates the texture from them."""
    field_at = image + 0x38
    s.push(BLOCK_TEMP)
    v = s.u64(field_at)
    if v:
        if v not in (PTR_INLINE, PTR_INSERT):
            s.put_u64(field_at, s.offset_to_alias(v))
        else:
            at = s.addr()
            s.put_u64(field_at, at)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            size = 1 if s.read(image + 0x1D, 1)[0] == TS_WATER_MAP else struct.unpack(
                "<i", s.read(image + 0x24, 4))[0]
            s.load(True, at, size)
            state_of(s).pixels[image] = s.read(at, size)
            if slot is not None:
                s.put_u64(slot, s.u64(field_at))
    s.pop()


def load_gfx_image(s, image: int, at_stream_start: bool = True):
    """Load_GfxImage (14034F120): the header (0x68 bytes), then in the virtual block its name (XString at +0x60)
    and its pixels (load_texture_pixels)."""
    s.load(at_stream_start, image, GFX_IMAGE_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(image + 0x60)
    load_texture_pixels(s, image)
    s.pop()


def load_image_stream(s, linked: int):
    """Load_ImageStream (140374E70), run for each newly linked image: a streamed image (byte +0x35 set) takes the
    next four rows of the fastfile's streamed-image table (sub_1403492E0), one per stream level."""
    st = state_of(s)
    if s.read(linked + 0x35, 1)[0]:
        rows = st.rows[st.cursor:st.cursor + STREAM_LEVELS]
        st.cursor += STREAM_LEVELS
        st.streams[linked] = rows


def load_gfx_image_ptr(s, field_at: int):
    """Load_GfxImagePtr (14034F380): in the temp block, NULL stays, an offset aliases an earlier image, -1/-2 load
    the image inline (aligned to 4; -2 reserving an alias slot), then DB_AddXAsset links it (14036D830 through
    140372150), which runs the type's stream hook, Load_ImageStream."""
    s.push(BLOCK_TEMP)
    v = s.u64(field_at)
    if v:
        if v not in (PTR_INLINE, PTR_INSERT):
            s.put_u64(field_at, s.offset_to_alias(v))
        else:
            h = s.align(4)
            s.put_u64(field_at, h)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            load_gfx_image(s, h, True)
            linked = s.link(ASSET_TYPE_IMAGE, h)
            s.put_u64(field_at, linked)
            st = state_of(s)
            if h in st.pixels:
                st.pixels_by_link[linked] = st.pixels.pop(h)
            st.order.append(linked)
            load_image_stream(s, linked)
            if slot is not None:
                s.put_u64(slot, linked)
    s.pop()


def register(asset_loaders: dict, material_module=None, rows=None):
    """Add the image loader: as the XAsset list's type 0x0D entry and as material.HOOKS["image_ptr"] (materials
    load their images inline). `rows`: the fastfile's streamed-image table (Prefix.stream_images)."""
    asset_loaders[ASSET_TYPE_IMAGE] = load_gfx_image_ptr
    if material_module is not None:
        material_module.HOOKS["image_ptr"] = load_gfx_image_ptr
        material_module.HOOKS["image_name"] = lambda s, p: image_name(s, p) or f"{p:#x}"


# ==== 2. readers and converters ====================================================================================

@dataclass
class StreamLevel:
    width: int
    height: int
    card_memory: int      # low 26 bits of GfxImageStreamLevel::cardMemoryAndLevelCount
    level_count: int      # top 6 bits


@dataclass
class GfxImageInfo:
    address: int
    name: str
    format: int
    map_type: int
    semantic: int
    category: int
    flags: int
    picmip: tuple
    track: int
    card_memory: tuple
    width: int
    height: int
    depth: int
    num_elements: int
    level_count: int
    streamed: bool
    stream_levels: list

    @property
    def format_name(self) -> str:
        return DXGI.get(self.format, (f"DXGI_{self.format}",))[0]

    @property
    def faces(self) -> int:
        """Load_Texture: 6 for a cube map, numElements for an array, else 1."""
        return 6 if self.map_type == MAPTYPE_CUBE else self.num_elements if self.map_type == MAPTYPE_ARRAY else 1


def image_name(s, address: int):
    try:
        p = s.u64(address + 0x60)
        return s.cstr(p).decode("latin1") if p else None
    except Exception:
        return None


def read_image(s, address: int) -> GfxImageInfo:
    raw = s.read(address, GFX_IMAGE_SIZE)
    (fmt, map_type, semantic, category, flags, pm0, pm1, track, cm0, cm1, width, height, depth, num_elements,
     level_count, streamed) = struct.unpack_from("<IBBBBBBBxiiHHHHBB", raw, 0x18)
    levels = []
    for i in range(STREAM_LEVELS):
        w, h, packed = struct.unpack_from("<HHI", raw, 0x40 + 8 * i)
        levels.append(StreamLevel(w, h, packed & 0x3FFFFFF, packed >> 26))
    return GfxImageInfo(address, image_name(s, address) or "", fmt, map_type, semantic, category, flags, (pm0, pm1),
                        track, (cm0, cm1), width, height, depth, num_elements, level_count, bool(streamed), levels)


def mip_layout(fmt: int, map_type: int, width: int, height: int, depth: int, faces: int, levels: int):
    """Load_Texture's walk of a pixel block: for each face (in the order the data has them), every mip level one after
    the other; a level is max(1, size >> mip) in each dimension. Returns [(face, mip, offset, w, h, d, size)].
    For a cube map the stored face order is Image_CubemapFace's: data face i is D3D face Image_CubemapFace(i)."""
    out, off = [], 0
    for f in range(faces):
        for m in range(levels):
            w, h, d = max(1, width >> m), max(1, height >> m), max(1, depth >> m)
            n = level_size(fmt, w, h, d)
            out.append((f, m, off, w, h, d, n))
            off += n
    return out


def read_stream_level(pak: bytes | None, row, pak_reader=None) -> bytes:
    """A streamed level's data: the byte range [row.offset, row.end) of the imagefile pak, one zlib stream
    (measured: docs/fastfiles.md 11), inflated."""
    data = pak_reader(row) if pak_reader else pak[row.offset:row.end]
    return zlib.decompress(data)


def assemble_streamed(info: GfxImageInfo, levels: list) -> tuple:
    """The full image of a streamed GfxImage from its stream levels' inflated data (`levels[k]` for
    streamLevels[k], None where the level has no row or wasn't read). The levels grow from 0 (smallest): level 0 is
    every face's complete mip chain at streamLevels[0]'s size; a level k > 0 is every face's top mip only, at
    streamLevels[k]'s size (sub_14062B580 uploads one mip for k > 0, the whole chain for k = 0, and the smaller
    mips come from the texture of level k - 1, 14062AB70). The highest level present gives the size; returns
    (width, height, level_count, pixels) with pixels laid out as Load_Texture reads an in-zone image."""
    top = max(k for k, d in enumerate(levels) if d is not None)
    if any(levels[k] is None for k in range(top + 1)):
        raise ValueError("a stream level below the highest one is missing")
    faces = info.faces
    per_face = [b""] * faces
    for k in range(top, 0, -1):
        lv = info.stream_levels[k]
        n = level_size(info.format, lv.width, lv.height, max(1, info.depth))
        if len(levels[k]) != n * faces:
            raise ValueError(f"stream level {k}: {len(levels[k])} bytes, expected {n * faces}")
        for f in range(faces):
            per_face[f] += levels[k][f * n:(f + 1) * n]
    lv0 = info.stream_levels[0]
    chain = mip_layout(info.format, info.map_type, lv0.width, lv0.height, max(1, info.depth), faces, lv0.level_count)
    if len(levels[0]) != sum(c[6] for c in chain):
        raise ValueError(f"stream level 0: {len(levels[0])} bytes, expected {sum(c[6] for c in chain)}")
    for f, m, off, w, h, d, n in chain:
        per_face[f] += levels[0][off:off + n]
    lv = info.stream_levels[top]
    return lv.width, lv.height, lv0.level_count + top, b"".join(per_face)


def to_dds(info: GfxImageInfo, pixels: bytes, width=None, height=None, levels=None) -> bytes:
    """A DDS file (DX10 extended header) holding `pixels` laid out as Load_Texture reads them: faces, each with its
    mip chain. Cube faces are written in D3D order (+X, -X, +Y, -Y, +Z, -Z) as DDS requires."""
    width = width or info.width
    height = height or info.height
    levels = levels or info.level_count
    faces = info.faces
    layout = mip_layout(info.format, info.map_type, width, height, info.depth, faces, levels)
    chunks = {}
    for f, m, off, w, h, d, n in layout:
        chunks.setdefault(f, []).append(pixels[off:off + n])
    order = range(faces)
    if info.map_type == MAPTYPE_CUBE:
        # data face i holds D3D face CUBEMAP_FACE[i]; write in D3D order
        inverse = {CUBEMAP_FACE[i]: i for i in range(6)}
        order = [inverse[d3d] for d3d in range(6)]
    body = b"".join(b"".join(chunks[f]) for f in order)
    _, nbytes, block = DXGI.get(info.format, ("", 4, 1))
    pitch = ((width + block - 1) // block) * nbytes
    DDSD = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | (0x80000 if block > 1 else 0x8)
    caps = 0x1000 | (0x400000 | 0x8 if levels > 1 else 0) | (0x8 if faces > 1 else 0)
    caps2 = 0xFE00 if info.map_type == MAPTYPE_CUBE else (0x200000 if info.map_type == MAPTYPE_3D else 0)
    hdr = struct.pack("<4sIIIIIII44x", b"DDS ", 124, DDSD, height, width,
                      level_size(info.format, width, height) if block > 1 else pitch,
                      info.depth if info.map_type == MAPTYPE_3D else 0, levels)
    hdr += struct.pack("<II4sIIIII", 32, 0x4, b"DX10", 0, 0, 0, 0, 0)
    hdr += struct.pack("<IIIII", caps, caps2, 0, 0, 0)
    dim = {MAPTYPE_1D: 2, MAPTYPE_3D: 4}.get(info.map_type, 3)
    misc = 0x4 if info.map_type == MAPTYPE_CUBE else 0
    array = 1 if info.map_type == MAPTYPE_CUBE else max(1, faces)
    hdr += struct.pack("<IIIII", info.format, dim, misc, array, 0)
    return hdr + body


# Image_CubemapFace (14062E0F0, src/gfx_d3d/r_image_load_common.cpp): the D3D face of the i-th face in the data.
# The Store build's is the identity (a cube face is an array slice in Direct3D 11).
CUBEMAP_FACE = [0, 1, 2, 3, 4, 5]


# ==== 3. a whole zone ==============================================================================================

def walk_images(path, zone_name=None):
    """Read a fastfile and load it with every asset loader this folder has (the pipeline's, materials, models,
    images), stopping at the first asset type without one. Returns (prefix, walk result, stream); the images loaded
    so far are image.state_of(stream).order (linked addresses), with their in-zone pixels and stream rows."""
    import os
    try:
        from . import iw6ff, material, xmodel
    except ImportError:  # run as a script
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import iw6ff
        import material
        import xmodel
    data = open(path, "rb").read()
    name = zone_name or os.path.splitext(os.path.basename(path))[0]
    prefix = iw6ff.read_prefix(data)
    zone = iw6ff.decompress(data, prefix, name)
    zone = zone[0] if isinstance(zone, tuple) else zone
    loaders, saved = iw6ff.ASSET_LOADERS, dict(iw6ff.ASSET_LOADERS)
    loaders.update({t: material.asset_ptr(t, f) for t, f in material.ASSET_LOADERS.items()})
    xmodel.register(loaders, material_loader=material.load_material_ptr)
    register(loaders, material)
    init = iw6ff.Stream.__init__

    def stream_init(self, *a, **k):
        init(self, *a, **k)
        state_of(self).rows = prefix.stream_images
    iw6ff.Stream.__init__ = stream_init
    try:
        result = iw6ff.walk_zone(zone)
    finally:
        iw6ff.Stream.__init__ = init
        loaders.clear()
        loaders.update(saved)
    return prefix, result, result[1]


def image_pixels(s, address, pak_reader=None):
    """(width, height, level_count, pixels) of a loaded image at full size: the in-zone pixels, or the streamed
    levels assembled, reading each row's range with pak_reader(row) -> bytes (None when the pak isn't there)."""
    st = state_of(s)
    info = read_image(s, address)
    if address in st.pixels_by_link:
        return info.width, info.height, info.level_count, st.pixels_by_link[address]
    rows = st.streams.get(address)
    if not rows or pak_reader is None:
        return None
    levels = []
    for row in rows:
        raw = pak_reader(row) if row.end else None
        levels.append(zlib.decompress(raw) if raw is not None else None)
    while levels and levels[-1] is None:
        levels.pop()
    if not levels or any(v is None for v in levels):
        return None
    return assemble_streamed(info, levels)


def folder_pak_reader(folder):
    """pak_reader for a folder holding imagefile<N>.pak (and <lang>_imagefile<N>.pak) files."""
    import os

    def read(row):
        if not row.path:
            return None
        p = os.path.join(folder, row.path)
        if not os.path.exists(p):
            return None
        with open(p, "rb") as f:
            f.seek(row.offset)
            return f.read(row.end - row.offset)
    return read


def main(argv=None):
    import argparse
    import json
    import os
    ap = argparse.ArgumentParser(description="List and export the images of a Ghosts PC fastfile (Store build).")
    ap.add_argument("fastfile")
    ap.add_argument("--paks", help="folder with the imagefile<N>.pak files (streamed images)")
    ap.add_argument("--out", help="write <name>.dds for every image whose data is available")
    ap.add_argument("--png", action="store_true", help="also write the top mip as PNG (BC1-BC5 and RGBA8 formats)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    prefix, result, s = walk_images(a.fastfile)
    st = state_of(s)
    reader = folder_pak_reader(a.paks) if a.paks else None
    listing = []
    for addr in st.order:
        info = read_image(s, addr)
        rows = st.streams.get(addr, [])
        entry = {"name": info.name, "format": info.format_name, "type": MAPTYPE_NAMES.get(info.map_type),
                 "semantic": info.semantic, "category": info.category, "flags": info.flags,
                 "streamed": info.streamed,
                 "size": [info.width, info.height, info.depth], "levels": info.level_count,
                 "stream_levels": [[lv.width, lv.height, lv.level_count, lv.card_memory]
                                   for lv in info.stream_levels if lv.width],
                 "rows": [[r.path, r.offset, r.end] for r in rows if r.end]}
        if a.out:
            got = image_pixels(s, addr, reader)
            if got:
                w, h, n, px = got
                os.makedirs(a.out, exist_ok=True)
                safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in info.name)
                with open(os.path.join(a.out, safe + ".dds"), "wb") as f:
                    f.write(to_dds(info, px, w, h, n))
                entry["exported"] = [w, h, n]
                fmt = info.format_name
                if a.png and info.faces == 1 and (fmt.startswith(("BC1", "BC2", "BC3", "BC4", "BC5")) or
                                                  fmt.startswith("R8G8B8A8")):
                    try:
                        from . import bcn
                    except ImportError:  # run as a script (walk_images put this folder on the path)
                        import bcn
                    top = px[:level_size(info.format, w, h)]
                    rgba = top if fmt.startswith("R8G8B8A8") else bcn.decode(fmt, top, w, h)
                    with open(os.path.join(a.out, safe + ".png"), "wb") as f:
                        f.write(bcn.png(rgba, w, h))
        listing.append(entry)
    complete, stopped = result[4], result[5]
    if a.json:
        print(json.dumps({"complete": complete, "stopped_at": stopped, "images": listing}, indent=1))
    else:
        for e in listing:
            print(f"{e['name']:48s} {e['format']:20s} {e['type']:5s} "
                  f"{'x'.join(map(str, e['stream_levels'][-1][:2] if e['streamed'] and e['stream_levels'] else e['size'][:2])):>10s}"
                  f" {'streamed' if e['streamed'] else 'in zone':8s} {'exported' if 'exported' in e else ''}")
        if not complete:
            print(f"(stopped at asset {stopped}: a type without a decoder yet)")


if __name__ == "__main__":
    main()
