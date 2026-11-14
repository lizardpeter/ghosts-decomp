"""The world's render geometry (GfxWorld, asset type gfx_map) of a Ghosts PC zone (Store build), and its export.

1. Loaders: the Store build's Load_GfxWorld (14034FF30) and the functions it calls, statement for statement, on the
   fastfile pipeline's Stream (tools/fastfile/iw6ff.py). They consume the zone exactly as the game does and leave
   the GfxWorld in the stream's block memory with its pointers resolved; D3D11 objects the game creates while
   loading are stored as 0, as with r_loadForRenderer off. Checked against the game's own loader run on a real map
   zone in the emulator (tests/fastfile/test_gfxworld.py). docs/assets/world.md has the layout.
2. Readers: read_world(memory, address) -> GfxWorldInfo with the vertices, indices, surfaces (with their material
   names), static model placements, cells, lightmaps and reflection probes, from any memory image (the stream's,
   or the game's after loading).
3. Converters: to_gltf(world) -> a glTF 2.0 document of the world surfaces (one primitive per material, the
   lightmap UVs as TEXCOORD_1, vertex colours) with every static model placement as a node naming its XModel.

Field names are the servers' PDB names where the Store layout matches theirs; the Store-only ones are described.
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field

try:
    from . import image as image_mod
    from . import material as material_mod
    from . import xmodel as xmodel_mod
except ImportError:  # run from this folder
    import image as image_mod
    import material as material_mod
    import xmodel as xmodel_mod

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
PTR_INSERT = 0xFDFDFDFFFFFFFFFE
BLOCK_TEMP, BLOCK_RUNTIME, BLOCK_VIRTUAL = 0, 2, 3
ASSET_GFXWORLD = 0x1A
GFXWORLD_SIZE = 0xA30
GFXWORLDVERTEX_SIZE = 0x2C
GFXSURFACE_SIZE = 0x28
SMODEL_DRAW_INST_SIZE = 0xB0


# ==== 1. loaders ===================================================================================================

def _array(s, field_at: int, align: int, size: int, at_start: bool = True):
    """The generated rule for an inline array behind a pointer that is always inline when set: non-zero -> align,
    the pointer becomes the current position, `size` bytes are loaded there. Returns the array's address or 0."""
    if not s.u64(field_at):
        return 0
    p = s.align(align) if align > 1 else s.addr()
    s.put_u64(field_at, p)
    s.load(at_start, p, size)
    return p


def _runtime_array(s, field_at: int, align: int, size: int):
    """The same in the runtime block (DB_PushStreamPos(XFILE_BLOCK_RUNTIME) ... DB_PopStreamPos): zero-filled
    memory the game fills while it runs; nothing is read from the zone."""
    s.push(BLOCK_RUNTIME)
    p = _array(s, field_at, align, size)
    s.pop()
    return p


def _buffer(s, field_at: int):
    """A D3D11 buffer or view created from data just loaded (R_CreateVertexBuffer 140601750 and the like): the
    8-byte field is loaded with atStreamStart false (nothing read) and set by the creator; 0 here."""
    s.put_u64(field_at, 0)


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def load_dpvs_planes(s, world: int, at: int):
    """Load_GfxWorldDpvsPlanes (140350CA0): planes (-1: inline, else an offset to an earlier copy), nodes, and the
    runtime sceneEntCellBits (cellCount << 9 words)."""
    v = s.u64(at + 0x08)
    if v:
        if v == PTR_INLINE:
            p = s.align(4)
            s.put_u64(at + 0x08, p)
            s.load(True, p, _i32(s, world + 0x14) * 0x14)            # planeCount cplane_s
        else:
            s.put_u64(at + 0x08, s.offset_to_pointer(v))
    _array(s, at + 0x10, 2, _i32(s, world + 0x18) * 2)              # nodes: nodeCount u16
    _runtime_array(s, at + 0x18, 4, (_i32(s, at) << 9) * 4)        # sceneEntCellBits


def load_cell_tree(s, world: int, at: int):
    """Load_GfxCellTree (14034EE10): the cell's GfxAabbTree array, aabbTreeCounts[cell] trees of 0x38 bytes; each
    tree's smodelIndexes (-1: inline u16 array, else an offset)."""
    if not s.u64(at):
        return
    p = s.align(4)
    s.put_u64(at, p)
    cell = (at - s.u64(world + 0x78)) >> 3
    count = _i32(s, s.u64(world + 0x70) + 4 * cell)
    s.load(True, p, count * 0x38)
    for i in range(count):
        tree = p + 0x38 * i
        v = s.u64(tree + 0x28)
        if v:
            if v == PTR_INLINE:
                q = s.align(2)
                s.put_u64(tree + 0x28, q)
                s.load(True, q, _u16(s, tree + 0x20) * 2)
            else:
                s.put_u64(tree + 0x28, s.offset_to_pointer(v))


def load_cell(s, at: int):
    """Load_GfxCell (14034EC90): portals (0x50 each, their vertices 12 bytes each), the reflection probe indexes
    and reference indexes (bytes, no alignment)."""
    portals = _array(s, at + 0x20, 4, _i32(s, at + 0x18) * 0x50)
    for i in range(_i32(s, at + 0x18) if portals else 0):
        portal = portals + 0x50 * i
        _array(s, portal + 0x28, 4, s.read(portal + 0x34, 1)[0] * 0xC)
    _array(s, at + 0x30, 1, s.read(at + 0x28, 1)[0])
    _array(s, at + 0x40, 1, s.read(at + 0x38, 1)[0])


def load_world_vertex_data(s, draw: int, at: int):
    """Load_GfxWorldVertexData0 (140351E00): vertexCount GfxWorldVertex (0x2C bytes) and the vertex buffer."""
    _array(s, at, 4, _u32(s, draw + 0x6C) * GFXWORLDVERTEX_SIZE)
    _buffer(s, at + 8)


def load_world_vertex_layer_data(s, draw: int, at: int):
    """Load_GfxWorldVertexLayerData (140351EB0): vertexLayerDataSize bytes (no alignment) and their buffer."""
    _array(s, at, 1, _u32(s, draw + 0x80))
    _buffer(s, at + 8)


def load_world_draw(s, at: int, image_ptr):
    """Load_GfxWorldDraw (140351830), 0xB0 bytes at GfxWorld + 0x88."""
    probe_count = _u32(s, at)
    p = _array(s, at + 0x08, 8, probe_count * 8)                     # reflectionProbes: GfxImage *
    for i in range(probe_count if p else 0):
        image_ptr(s, p + 8 * i)
    p = _array(s, at + 0x10, 4, probe_count * 0x20)                  # reflectionProbeOrigins
    for i in range(probe_count if p else 0):
        probe = p + 0x20 * i
        _array(s, probe + 0x10, 4, _u32(s, probe + 0x18) * 0x60)     # probeVolumes
    _runtime_array(s, at + 0x18, 4, probe_count * 0x18)              # reflectionProbeTextures
    ref_count = _u32(s, at + 0x20)
    _array(s, at + 0x28, 4, ref_count * 0xC)                         # reflectionProbeReferenceOrigins
    _array(s, at + 0x30, 1, ref_count)                               # reflectionProbeReferences
    lightmaps = _i32(s, at + 0x38)
    p = _array(s, at + 0x40, 4, lightmaps * 0x10)                    # lightmaps: {primary, secondary}
    for i in range(lightmaps if p else 0):
        image_ptr(s, p + 0x10 * i)
        image_ptr(s, p + 0x10 * i + 8)
    _runtime_array(s, at + 0x48, 4, lightmaps * 0x18)                # lightmapPrimaryTextures
    _runtime_array(s, at + 0x50, 4, lightmaps * 0x18)                # lightmapSecondaryTextures
    image_ptr(s, at + 0x58)                                          # lightmapOverridePrimary
    image_ptr(s, at + 0x60)                                          # lightmapOverrideSecondary
    load_world_vertex_data(s, at, at + 0x70)
    load_world_vertex_layer_data(s, at, at + 0x88)
    _array(s, at + 0xA0, 2, _u32(s, at + 0x98) * 2)                  # indices
    _buffer(s, at + 0xA8)                                            # indexBuffer (R_CreateIndexBuffer 140601620)


def load_light_grid(s, at: int):
    """Load_GfxLightGrid (14034F650), 0x620 bytes at GfxWorld + 0x138, then its tree (14034F8A0) at +0x5D0."""
    row_axis = _u32(s, at + 0x14)
    rows = _u16(s, at + 0x0E + 2 * row_axis) - _u16(s, at + 0x08 + 2 * row_axis) + 1
    _array(s, at + 0x20, 2, rows * 2)                                # rowDataStart
    _array(s, at + 0x30, 1, _u32(s, at + 0x28))                      # rawRowData
    _array(s, at + 0x40, 4, _u32(s, at + 0x38) * 8)                  # entries
    _array(s, at + 0x50, 4, _u32(s, at + 0x48) * 0xA8)               # colors
    _array(s, at + 0x68, 4, s.read(at + 0x67, 1)[0] * 4)             # stageLightingContrastGain
    _array(s, at + 0x78, 4, _u32(s, at + 0x70) * 4)                  # paletteEntryAddress
    _array(s, at + 0x88, 1, _u32(s, at + 0x80))                      # paletteBitstream
    tree = at + 0x5D0
    _array(s, tree + 0x38, 4, _i32(s, tree + 4) * 4)                 # p_nodeTable
    _array(s, tree + 0x48, 1, _i32(s, tree + 0x40))                  # p_leafTable


def load_shadow_geometry(s, at: int, count: int):
    """Load_GfxShadowGeometryArray (14034FBD0): count × 0x18 {u16 surfaceCount, u16 smodelCount, u32 *, u16 *}."""
    s.load(True, at, count * 0x18)
    for i in range(count):
        g = at + 0x18 * i
        _array(s, g + 0x08, 4, _u16(s, g) * 4)
        _array(s, g + 0x10, 2, _u16(s, g + 2) * 2)


def load_light_region(s, at: int):
    """Load_GfxLightRegion (14034F950): hulls (0x58 each), each with its axes (0x14 each)."""
    count = _u32(s, at)
    p = _array(s, at + 8, 4, count * 0x58)
    for i in range(count if p else 0):
        hull = p + 0x58 * i
        _array(s, hull + 0x50, 4, _u32(s, hull + 0x48) * 0x14)


def load_smodel_lighting(s, at: int):
    """Load_GfxStaticModelVertexLightingInfo (14034FD70), 0x38 bytes: numLightingValues (+0x34) entries of 0x14
    bytes, their buffer (+8) and shader view (+0x10, "lightingValuesView"), and a runtime 0x18-byte field (+0x18,
    1401B3D60)."""
    _array(s, at, 4, _u32(s, at + 0x34) * 0x14)
    _buffer(s, at + 0x08)
    _buffer(s, at + 0x10)


def load_byte_ptr_array(s, at: int, count: int):
    """140361E10: count pointers, each non-null one pointing at 1 byte loaded right there (no alignment)."""
    s.load(True, at, count * 8)
    for i in range(count):
        _array(s, at + 8 * i, 1, 1)


def load_dpvs_static(s, world: int, at: int, material_ptr, xmodel_ptr):
    """Load_GfxWorldDpvsStatic (140350DD0), 0x118 bytes at GfxWorld + 0x8A0."""
    smodels, static_surfs = _u32(s, at), _u32(s, at + 4)
    smodel_vis, surface_vis = _u32(s, at + 0x30), _u32(s, at + 0x34)
    for off in (0x38, 0x40, 0x48):                                    # smodelVisData[3]
        _runtime_array(s, at + off, 128, smodel_vis * 4)
    for off in (0x50, 0x58, 0x60):                                    # surfaceVisData[3]
        _runtime_array(s, at + off, 128, surface_vis * 4)
    for off in (0x68, 0x70, 0x78):                                    # Store only: smodelVisDataCount + 1 words
        _runtime_array(s, at + off, 128, (smodel_vis + 1) * 4)
    for off in (0x80, 0x88, 0x90):                                    # tessellationCutoffVisData[3]
        _runtime_array(s, at + off, 128, surface_vis * 4)
    _array(s, at + 0x98, 4, (smodels + 1) * 4)                        # Store only: smodelCount + 1 words
    for off in (0xA0, 0xA8, 0xB0):                                    # Store only: surfaceVisDataCount words
        _runtime_array(s, at + off, 128, surface_vis * 4)
    _array(s, at + 0xB8, 4, static_surfs * 4)                         # sortedSurfIndex
    _array(s, at + 0xC0, 4, smodels * 0x24)                           # smodelInsts
    surface_count = _u32(s, world + 0x1C)
    p = _array(s, at + 0xC8, 4, surface_count * GFXSURFACE_SIZE)      # surfaces
    for i in range(surface_count if p else 0):
        material_ptr(s, p + GFXSURFACE_SIZE * i + 0x18)
    _array(s, at + 0xD0, 4, surface_count * 0x24)                     # surfacesBounds (0x24 bytes on PC)
    p = _array(s, at + 0xD8, 4, smodels * SMODEL_DRAW_INST_SIZE)      # smodelDrawInsts
    for i in range(smodels if p else 0):
        inst = p + SMODEL_DRAW_INST_SIZE * i
        xmodel_ptr(s, inst + 0x38)
        load_smodel_lighting(s, inst + 0x50)
    _runtime_array(s, at + 0xE0, 8, surface_count * 0x10)             # surfaceMaterials (GfxDrawSurf)
    _runtime_array(s, at + 0xE8, 128, surface_vis * 4)                # surfaceCastsSunShadow
    _runtime_array(s, at + 0xF8, 128, _u32(s, at + 0xF4) * _u32(s, at + 0xF0) * 4)  # surfaceCastsSunShadowOpt
    for off in (0x100, 0x108):                                        # constantBuffersLit / Ambient
        s.push(BLOCK_RUNTIME)
        if s.u64(at + off):
            p = s.align(8)
            s.put_u64(at + off, p)
            load_byte_ptr_array(s, p, smodels)
        s.pop()


def load_dpvs_dynamic(s, world: int, at: int):
    """Load_GfxWorldDpvsDynamic (140350990), 0x50 bytes at GfxWorld + 0x9B8: all runtime."""
    words = (_u32(s, at), _u32(s, at + 4))
    cells = _i32(s, world + 0x50)
    _runtime_array(s, at + 0x10, 4, (cells * words[0] & 0xFFFFFFFF) * 4)   # dynEntCellBits[0]
    _runtime_array(s, at + 0x18, 4, (cells * words[1] & 0xFFFFFFFF) * 4)   # dynEntCellBits[1]
    for off, k in ((0x20, 0), (0x38, 1), (0x28, 0), (0x40, 1), (0x30, 0), (0x48, 1)):  # dynEntVisData[2][3]
        _runtime_array(s, at + off, 16, words[k] << 5)


def load_gfx_world(s, w: int, at_stream_start: bool = True, image_ptr=None, material_ptr=None, xmodel_ptr=None):
    """Load_GfxWorld (14034FF30)."""
    image_ptr = image_ptr or image_mod.load_gfx_image_ptr
    material_ptr = material_ptr or material_mod.load_material_ptr
    xmodel_ptr = xmodel_ptr or (lambda s_, f: xmodel_mod.load_xmodel_ptr(s_, f, material_mod.load_material_ptr))
    s.load(at_stream_start, w, GFXWORLD_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(w + 0x00)                                           # name
    s.xstring_ptr(w + 0x08)                                           # baseName
    sky_count = _i32(s, w + 0x20)
    p = _array(s, w + 0x28, 4, sky_count * 0x20)                      # skies
    for i in range(sky_count if p else 0):
        sky = p + 0x20 * i
        _array(s, sky + 0x08, 4, _i32(s, sky) * 4)                    # skyStartSurfs
        image_ptr(s, sky + 0x10)                                      # skyImage
    load_dpvs_planes(s, w, w + 0x50)
    cells = _i32(s, w + 0x50)
    _array(s, w + 0x70, 4, cells * 4)                                 # aabbTreeCounts
    p = _array(s, w + 0x78, 128, cells * 8)                           # aabbTrees
    for i in range(cells if p else 0):
        load_cell_tree(s, w, p + 8 * i)
    p = _array(s, w + 0x80, 4, cells * 0x48)                          # cells
    for i in range(cells if p else 0):
        load_cell(s, p + 0x48 * i)
    load_world_draw(s, w + 0x88, image_ptr)
    load_light_grid(s, w + 0x138)
    _array(s, w + 0x760, 4, _i32(s, w + 0x758) * 0x3C)                # models (GfxBrushModel)
    count = _i32(s, w + 0x784)
    p = _array(s, w + 0x788, 4, count * 0x10)                         # materialMemory
    for i in range(count if p else 0):
        material_ptr(s, p + 0x10 * i)
    material_ptr(s, w + 0x798)                                        # sun.spriteMaterial
    material_ptr(s, w + 0x7A0)                                        # sun.flareMaterial
    image_ptr(s, w + 0x840)                                           # outdoorImage
    last_sun, lights = _u32(s, w + 0x30), _u32(s, w + 0x34)
    dyn_models, dyn_brushes = _u32(s, w + 0x9C0), _u32(s, w + 0x9C4)
    _runtime_array(s, w + 0x848, 4, (((cells + 31) >> 5) * cells) * 4)   # cellCasterBits
    _runtime_array(s, w + 0x850, 4, ((cells + 31) >> 5) * 4)              # cellHasSunLitSurfsBits
    _runtime_array(s, w + 0x858, 4, dyn_models * 6)                       # sceneDynModel
    _runtime_array(s, w + 0x860, 4, dyn_brushes * 4)                      # sceneDynBrush
    _runtime_array(s, w + 0x868, 4, (((lights - last_sun) * 0x2000 - 0x2000) & 0xFFFFFFFF) * 4)
    _runtime_array(s, w + 0x870, 4, (((lights - last_sun - 1) * dyn_models) & 0xFFFFFFFF) * 4)
    _runtime_array(s, w + 0x878, 4, (((lights - last_sun - 1) * dyn_brushes) & 0xFFFFFFFF) * 4)
    _runtime_array(s, w + 0x880, 2, dyn_models * 2)                       # nonSunPrimaryLightForModelDynEnt
    for off in (0x888, 0x890):                                            # shadowGeom, shadowGeomOptimized
        if s.u64(w + off):
            p = s.align(4)
            s.put_u64(w + off, p)
            load_shadow_geometry(s, p, lights)
    p = _array(s, w + 0x898, 4, lights * 0x10)                            # lightRegion
    for i in range(lights if p else 0):
        load_light_region(s, p + 0x10 * i)
    load_dpvs_static(s, w, w + 0x8A0, material_ptr, xmodel_ptr)
    load_dpvs_dynamic(s, w, w + 0x9B8)
    _array(s, w + 0xA10, 4, _u32(s, w + 0xA0C) * 0x44)                    # heroOnlyLights
    tome = _array(s, w + 0xA20, 16, _u32(s, w + 0xA1C))                   # Store only: the Umbra tome
    umbra_tome_ptr(s, w + 0xA28, tome, _u32(s, w + 0xA1C))
    s.pop()


def umbra_tome(data: bytes, address: int, size: int) -> int:
    """1406B8020 (Umbra's tome check): 0 when the data is a valid tome (magic 0xD600 and version 0x12 in the first
    word, 16-byte aligned, its size (+8) within `size`), else Umbra's error code."""
    if not address:
        return 1
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic & 0xFFFF0000 != 0xD6000000:
        return 5 if ((magic >> 8 & 0xFF) | (magic & 0xFF) << 8) == 0xD600 else 2
    if magic & 0xFFFF > 0x12:
        return 4
    if magic & 0xFFFF < 0x12:
        return 3
    if address & 0xF:
        return 6
    if struct.unpack_from("<I", data, 8)[0] > size:
        return 7
    return 0


def umbra_tome_ptr(s, field_at: int, tome: int, size: int):
    """1401B7180: the tome pointer (+0xA28) is the data (+0xA20) when it is a valid tome; null data -> null; an
    invalid tome leaves the field as loaded."""
    if not tome:
        s.put_u64(field_at, 0)
    elif umbra_tome(s.read(tome, 16), tome, size) == 0:
        s.put_u64(field_at, tome)


def load_gfx_world_ptr(s, varptr: int, **loaders):
    """Load_GfxWorldPtr (140351D10): the asset pointer rule (temp block, aligned to 4), then Load_GfxWorldAsset
    (140372210) links it as type 0x1A."""
    s.push(BLOCK_TEMP)
    v = s.u64(varptr)
    if v:
        if v not in (PTR_INLINE, PTR_INSERT):
            s.put_u64(varptr, s.offset_to_alias(v))
        else:
            h = s.align(4)
            s.put_u64(varptr, h)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            load_gfx_world(s, h, True, **loaders)
            s.put_u64(varptr, s.link(ASSET_GFXWORLD, h))
            if slot is not None:
                s.put_u64(slot, s.u64(varptr))
    s.pop()


ASSET_COMWORLD = 0x14


def load_com_world(s, c: int, at_stream_start: bool = True):
    """Load_ComWorld (14034BBC0): name, primaryLightCount (+0xC) lights of 0x78 bytes (each with its defName XString
    at +0x70), primaryLightEnvCount (+0x18) envs of 10 bytes."""
    s.load(at_stream_start, c, 0x28)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(c)
    count = _u32(s, c + 0x0C)
    p = _array(s, c + 0x10, 4, count * 0x78)
    for i in range(count if p else 0):
        s.xstring_ptr(p + 0x78 * i + 0x70)
    _array(s, c + 0x20, 4, _u32(s, c + 0x18) * 10)
    s.pop()


def load_com_world_ptr(s, varptr: int):
    """Load_ComWorldPtr (14034BD90), then Load_ComWorldAsset (140371A40) links it as type 0x14."""
    s.push(BLOCK_TEMP)
    v = s.u64(varptr)
    if v:
        if v not in (PTR_INLINE, PTR_INSERT):
            s.put_u64(varptr, s.offset_to_alias(v))
        else:
            h = s.align(4)
            s.put_u64(varptr, h)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            load_com_world(s, h, True)
            s.put_u64(varptr, s.link(ASSET_COMWORLD, h))
            if slot is not None:
                s.put_u64(slot, s.u64(varptr))
    s.pop()


LIGHT_TYPES = {1: "sun", 2: "spot", 3: "omni"}


@dataclass
class PrimaryLight:
    type: int
    can_use_shadow_map: int
    exponent: int
    color: tuple
    dir: tuple
    up: tuple
    origin: tuple
    radius: float
    cos_half_fov_outer: float
    cos_half_fov_inner: float
    def_name: str


def read_com_world(mem, c: int) -> list:
    """The primary lights of a loaded ComWorld."""
    count = struct.unpack("<I", mem.read(c + 0x0C, 4))[0]
    p = mem.u64(c + 0x10)
    out = []
    for i in range(count if p else 0):
        a = p + 0x78 * i
        t, shadow, exp_ = mem.read(a, 3)
        f = struct.unpack("<15f", mem.read(a + 4, 60))
        out.append(PrimaryLight(t, shadow, exp_, f[0:3], f[3:6], f[6:9], f[9:12], f[12], f[13], f[14],
                                _cstr(mem, mem.u64(a + 0x70))))
    return out


def register(asset_loaders: dict):
    asset_loaders[ASSET_GFXWORLD] = load_gfx_world_ptr
    asset_loaders[ASSET_COMWORLD] = load_com_world_ptr


# ==== 2. readers ===================================================================================================

@dataclass
class WorldSurface:
    material: str
    first_vertex: int
    vertex_count: int
    tri_count: int
    base_index: int
    vertex_layer_data: int
    flags: int                 # GfxSurfaceLightingAndFlags (packed): lightmap index, reflection probe, flags


@dataclass
class StaticModel:
    model: str
    origin: tuple
    axis: tuple                # three rows: forward, left, up
    scale: float
    flags: int
    lightmap_index: int
    cull_dist: int


@dataclass
class GfxWorldInfo:
    name: str
    base_name: str
    vertices: bytes            # vertexCount × 0x2C (GfxWorldVertex)
    vertex_count: int
    indices: list
    surfaces: list
    static_models: list
    cell_count: int
    lightmaps: list            # (primary image name, secondary image name)
    reflection_probes: list    # (image name, origin)
    sky_images: list
    bounds: tuple
    sun_materials: tuple
    hero_lights: int
    umbra_tome_size: int


def _cstr(mem, p):
    return mem.cstr(p).decode("latin1") if p else ""


def _asset_name(mem, header, name_off=0):
    return _cstr(mem, mem.u64(header + name_off)) if header else ""


def read_world(mem, w: int) -> GfxWorldInfo:
    """A loaded GfxWorld (the stream's memory, or any object with u64/read/cstr) as plain Python data."""
    u32 = lambda a: struct.unpack("<I", mem.read(a, 4))[0]
    i32 = lambda a: struct.unpack("<i", mem.read(a, 4))[0]
    draw = w + 0x88
    nverts = u32(draw + 0x6C)
    verts = mem.read(mem.u64(draw + 0x70), nverts * GFXWORLDVERTEX_SIZE) if nverts else b""
    nidx = u32(draw + 0x98)
    idx = list(struct.unpack(f"<{nidx}H", mem.read(mem.u64(draw + 0xA0), 2 * nidx))) if nidx else []
    dpvs = w + 0x8A0
    surfaces = []
    sp = mem.u64(dpvs + 0xC8)
    for i in range(u32(w + 0x1C) if sp else 0):
        a = sp + GFXSURFACE_SIZE * i
        layer, first, _, vcount, tris, base = struct.unpack("<IIfHHI", mem.read(a, 0x14))
        surfaces.append(WorldSurface(_asset_name(mem, mem.u64(a + 0x18)), first, vcount, tris, base, layer,
                                     mem.u64(a + 0x20)))
    smodels = []
    mp = mem.u64(dpvs + 0xD8)
    for i in range(u32(dpvs) if mp else 0):
        a = mp + SMODEL_DRAW_INST_SIZE * i
        f = struct.unpack("<13f", mem.read(a, 0x34))
        # after the 0x38-byte vertex lighting info (+0x50): modelLightmapInfo (+0x88, lightmapIndex +0x98),
        # lightingHandle, cullDist (+0x9E), flags (+0xA0): the servers' order with the Store sizes (*unverified*)
        lightmap = struct.unpack("<I", mem.read(a + 0x98, 4))[0]
        cull, flags = struct.unpack("<HH", mem.read(a + 0x9E, 4))
        smodels.append(StaticModel(_asset_name(mem, mem.u64(a + 0x38)), f[0:3], (f[3:6], f[6:9], f[9:12]), f[12],
                                   flags, lightmap, cull))
    lightmaps = []
    lp = mem.u64(draw + 0x40)
    for i in range(i32(draw + 0x38) if lp else 0):
        lightmaps.append((_asset_name(mem, mem.u64(lp + 16 * i), 0x60), _asset_name(mem, mem.u64(lp + 16 * i + 8), 0x60)))
    probes = []
    pp, op = mem.u64(draw + 0x08), mem.u64(draw + 0x10)
    for i in range(u32(draw) if pp else 0):
        origin = struct.unpack("<3f", mem.read(op + 0x20 * i, 12)) if op else None
        probes.append((_asset_name(mem, mem.u64(pp + 8 * i), 0x60), origin))
    skies = []
    kp = mem.u64(w + 0x28)
    for i in range(i32(w + 0x20) if kp else 0):
        skies.append(_asset_name(mem, mem.u64(kp + 0x20 * i + 0x10), 0x60))
    bounds = struct.unpack("<6f", mem.read(w + 0x768, 24))
    return GfxWorldInfo(_cstr(mem, mem.u64(w)), _cstr(mem, mem.u64(w + 8)), verts, nverts, idx, surfaces, smodels,
                        i32(w + 0x50), lightmaps, probes, skies, bounds,
                        (_asset_name(mem, mem.u64(w + 0x798)), _asset_name(mem, mem.u64(w + 0x7A0))),
                        u32(w + 0xA0C), u32(w + 0xA1C))


def world_vertex(raw: bytes, i: int):
    """GfxWorldVertex (0x2C): xyz, binormalSign, colour (RGBA8), texCoord, lmapCoord, normal and tangent
    (PackedUnitVec 10:10:10:2)."""
    x, y, z, sign = struct.unpack_from("<4f", raw, i * 0x2C)
    color = raw[i * 0x2C + 0x10:i * 0x2C + 0x14]
    u, v, lu, lv = struct.unpack_from("<4f", raw, i * 0x2C + 0x14)
    n, t = struct.unpack_from("<II", raw, i * 0x2C + 0x24)
    return (x, y, z), sign, color, (u, v), (lu, lv), xmodel_mod.unpack_unit_vec(n)[0], xmodel_mod.unpack_unit_vec(t)[0]


def decode_lightmap(pixels: bytes, width: int, height: int):
    """The secondary lightmap (R16G16B16A16_FLOAT, top mip, `height` rows) as numpy float32 arrays over the lightmap
    coordinates ((height / 2, width, 3) each): ambient, directional and the direction (unit, tangent space). The world
    pixel shaders sample the top half at (u, v / 2) and the bottom half at (u, v / 2 + 1/2): top.rgb is the ambient
    term, bottom.rgb the directional one, (top.a, bottom.a) the direction's x and y, z = sqrt(1 - x² - y²)."""
    import numpy as np
    a = np.frombuffer(pixels[:width * height * 8], np.float16).astype(np.float32).reshape(height, width, 4)
    top, bottom = a[:height // 2], a[height // 2:]
    z = np.sqrt(np.clip(1 - top[..., 3] ** 2 - bottom[..., 3] ** 2, 0, 1))
    return top[..., :3], bottom[..., :3], np.stack([top[..., 3], bottom[..., 3], z], -1)


def lightmap_lighting(ambient, directional, direction, normal=(0.0, 0.0, 1.0)):
    """The baked diffuse lighting the shaders compute for a tangent-space `normal` (a 3-vector, or an array
    broadcasting against `direction`): ambient * normal.z + directional * saturate(dot(normal, direction)). The
    pixel colour is albedo * this + specular; the sun comes on top in the LIT_DIR techniques, scaled by the primary
    lightmap (BC4: sun visibility) and the sun colour."""
    import numpy as np
    n = np.asarray(normal, np.float32)
    nz = n[..., 2:3] if n.ndim > 1 else n[2]
    return ambient * nz + directional * np.clip((direction * n).sum(-1, keepdims=True), 0, 1)


# ==== 3. glTF ======================================================================================================

def _model_mesh(b, model, materials: list, material_index: dict):
    """LOD 0 of an XModel (tools/fastfile/xmodel.py's XModel) as a glTF mesh, or None."""
    FLOAT, UINT, UBYTE = 5126, 5125, 5121
    if not model.lods or not model.lods[0].surfs:
        return None
    lod = model.lods[0]
    prims = []
    for k, surf in enumerate(lod.surfs.surfaces):
        if not surf.vertices or not surf.triangles:
            continue
        mname = model.materials[lod.surf_index + k] if lod.surf_index + k < len(model.materials) else ""
        mname = mname if isinstance(mname, str) else f"{mname:#x}"
        if mname not in material_index:
            material_index[mname] = len(materials)
            materials.append({"name": mname, "extras": {"game_material": mname}})
        pos = [v.position for v in surf.vertices]
        lo = [min(p[i] for p in pos) for i in range(3)]
        hi = [max(p[i] for p in pos) for i in range(3)]
        idx = [i for tri in surf.triangles for i in tri]
        prims.append({"attributes": {
            "POSITION": b.add(b"".join(struct.pack("<3f", *p) for p in pos), len(pos), FLOAT, "VEC3", 34962, (lo, hi)),
            "NORMAL": b.add(b"".join(struct.pack("<3f", *xmodel_mod._normalize(v.normal)) for v in surf.vertices),
                            len(pos), FLOAT, "VEC3", 34962),
            "TEXCOORD_0": b.add(b"".join(struct.pack("<2f", *v.uv) for v in surf.vertices), len(pos), FLOAT, "VEC2",
                                34962),
            "COLOR_0": b.add(b"".join(bytes(v.color) for v in surf.vertices), len(pos), UBYTE, "VEC4", 34962,
                             normalized=True)},
            "material": material_index[mname],
            "indices": b.add(struct.pack(f"<{len(idx)}I", *idx), len(idx), UINT, "SCALAR", 34963)})
    return {"name": model.name or "xmodel", "primitives": prims} if prims else None


def _look_quat(d):
    """The rotation turning glTF's light direction (-Z) into d (normalised)."""
    import math
    x, y, z = xmodel_mod._normalize(d)
    # rotate (0, 0, -1) to (x, y, z): axis = (0,0,-1) x d, angle = acos(-z)
    ax, ay, az = y, -x, 0.0
    s = math.sqrt(ax * ax + ay * ay)
    if s < 1e-9:
        return [0.0, 0.0, 0.0, 1.0] if z < 0 else [1.0, 0.0, 0.0, 0.0]
    angle = math.acos(max(-1.0, min(1.0, -z)))
    k = math.sin(angle / 2) / s
    return [ax * k, ay * k, az * k, math.cos(angle / 2)]


def to_gltf(world: GfxWorldInfo, z_up_to_y_up: bool = True, scale: float = 1.0, models: dict | None = None,
            material_images: dict | None = None, lightmap_images: dict | None = None, lights: list | None = None):
    """A glTF 2.0 document and its binary buffer.

    The world surfaces are one mesh with a primitive per (material, lightmap): POSITION, NORMAL, TEXCOORD_0,
    TEXCOORD_1 (the lightmap coordinates as stored: the secondary lightmap's two halves are sampled at (u, v / 2) and
    (u, v / 2 + 1/2), the primary at (u, v)), COLOR_0 (the packed vertex colour as stored: most likely layer weights on
    blended surfaces, not a tint (*unverified*), so viewers that multiply it into the base colour show false colours),
    indices made absolute. Every static model placement is a node
    named after its XModel (extras: model, scale), with that model's LOD 0 as mesh when `models` (name ->
    xmodel.XModel) has it. Materials are named after the game materials; with `material_images` ({material:
    {"base"|"normal"|"specular": uri}}) the base colour is the glTF base colour texture and the others are listed in
    extras, and with `lightmap_images` ({lightmap index: {name: uri}}) each world material's extras name its lightmap
    images. `lights` (read_com_world) become KHR_lights_punctual lights: the sun directional, spots and omnis at their
    origins (colour normalised, the largest component as intensity; *unverified* units). Coordinates stay the game's
    (inches, Z up) under a root node that rotates Z up to Y up and scales by `scale`."""
    import math
    b = xmodel_mod._Bin()
    FLOAT, UINT, UBYTE = 5126, 5125, 5121
    material_images = material_images or {}
    lightmap_images = lightmap_images or {}
    images, textures, image_index = [], [], {}

    def texture(uri):
        if uri not in image_index:
            images.append({"uri": uri})
            textures.append({"source": len(images) - 1, "sampler": 0})
            image_index[uri] = len(textures) - 1
        return image_index[uri]

    def make_material(name, lightmap=None):
        m = {"name": name if lightmap is None else f"{name}@lm{lightmap}", "extras": {"game_material": name}}
        imgs = material_images.get(name, {})
        pbr = {"metallicFactor": 0.0, "roughnessFactor": 1.0}
        if "base" in imgs:
            pbr["baseColorTexture"] = {"index": texture(imgs["base"]), "texCoord": 0}
        m["pbrMetallicRoughness"] = pbr
        if imgs:
            m["extras"]["textures"] = imgs
        if lightmap is not None:
            m["extras"]["lightmap"] = lightmap
            if lightmap in lightmap_images:
                m["extras"]["lightmap_images"] = lightmap_images[lightmap]
        return m

    by_key = {}
    for s_ in world.surfaces:
        by_key.setdefault((s_.material, s_.flags & 0xFF), []).append(s_)
    materials, prims = [], []
    for (mname, lm), surfs in by_key.items():
        remap, pos, nrm, uv0, uv1, col, out_idx = {}, [], [], [], [], [], []
        for s_ in surfs:
            for k in range(s_.tri_count * 3):
                vi = s_.first_vertex + world.indices[s_.base_index + k]
                j = remap.get(vi)
                if j is None:
                    j = remap[vi] = len(pos)
                    p, _, c, t0, t1, n, _ = world_vertex(world.vertices, vi)
                    pos.append(p), nrm.append(xmodel_mod._normalize(n)), uv0.append(t0), uv1.append(t1)
                    col.append(c)
                out_idx.append(j)
        if not out_idx:
            continue
        lo = [min(p[k] for p in pos) for k in range(3)]
        hi = [max(p[k] for p in pos) for k in range(3)]
        attrs = {
            "POSITION": b.add(b"".join(struct.pack("<3f", *p) for p in pos), len(pos), FLOAT, "VEC3", 34962, (lo, hi)),
            "NORMAL": b.add(b"".join(struct.pack("<3f", *n) for n in nrm), len(nrm), FLOAT, "VEC3", 34962),
            "TEXCOORD_0": b.add(b"".join(struct.pack("<2f", *t) for t in uv0), len(uv0), FLOAT, "VEC2", 34962),
            "TEXCOORD_1": b.add(b"".join(struct.pack("<2f", *t) for t in uv1), len(uv1), FLOAT, "VEC2", 34962),
            "COLOR_0": b.add(b"".join(col), len(col), UBYTE, "VEC4", 34962, normalized=True),
        }
        materials.append(make_material(mname, lm if lm != 0xFF else None))
        prims.append({"attributes": attrs, "material": len(materials) - 1,
                      "indices": b.add(struct.pack(f"<{len(out_idx)}I", *out_idx), len(out_idx), UINT, "SCALAR", 34963)})
    nodes = [{"name": world.name or "world", "children": []}]
    if z_up_to_y_up:
        nodes[0]["rotation"] = [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]
    if scale != 1.0:
        nodes[0]["scale"] = [scale] * 3
    meshes = []
    if prims:
        meshes.append({"name": "world_surfaces", "primitives": prims})
        nodes.append({"name": "world_surfaces", "mesh": 0})
        nodes[0]["children"].append(len(nodes) - 1)
    material_index = {m["name"]: i for i, m in enumerate(materials)}
    model_materials = []
    model_mesh = {}
    for i, m in enumerate(world.static_models):
        f, l, u = m.axis
        s = m.scale
        matrix = [f[0] * s, f[1] * s, f[2] * s, 0, l[0] * s, l[1] * s, l[2] * s, 0, u[0] * s, u[1] * s, u[2] * s, 0,
                  m.origin[0], m.origin[1], m.origin[2], 1]
        node = {"name": f"{m.model}#{i}", "matrix": matrix, "extras": {"xmodel": m.model, "scale": s}}
        if models and m.model in models:
            if m.model not in model_mesh:
                mesh = _model_mesh(b, models[m.model], model_materials, {})
                model_mesh[m.model] = None
                if mesh:
                    for prim in mesh["primitives"]:     # the model's materials, with textures, after the world's
                        name = model_materials[prim["material"]]["name"]
                        if name not in material_index:
                            materials.append(make_material(name))
                            material_index[name] = len(materials) - 1
                        prim["material"] = material_index[name]
                    meshes.append(mesh)
                    model_mesh[m.model] = len(meshes) - 1
            if model_mesh[m.model] is not None:
                node["mesh"] = model_mesh[m.model]
        nodes.append(node)
        nodes[0]["children"].append(len(nodes) - 1)
    doc_lights = []
    for i, light in enumerate(lights or []):
        kind = LIGHT_TYPES.get(light.type)
        if not kind:
            continue
        peak = max(light.color) or 1.0
        entry = {"name": light.def_name or f"light{i}", "color": [c / peak for c in light.color], "intensity": peak,
                 "type": {"sun": "directional", "spot": "spot", "omni": "point"}[kind],
                 "extras": {"game_type": kind, "index": i, "exponent": light.exponent,
                            "canUseShadowMap": light.can_use_shadow_map}}
        if kind != "sun":
            entry["range"] = light.radius * scale     # glTF ranges ignore node scale
        if kind == "spot":
            outer = math.acos(max(-1.0, min(1.0, light.cos_half_fov_outer)))
            inner = math.acos(max(-1.0, min(1.0, light.cos_half_fov_inner)))
            entry["spot"] = {"innerConeAngle": min(inner, outer), "outerConeAngle": outer}
        doc_lights.append(entry)
        node = {"name": entry["name"], "extensions": {"KHR_lights_punctual": {"light": len(doc_lights) - 1}}}
        if kind == "sun":
            # ComPrimaryLight::dir of the sun points towards the sun (*unverified*: the shaders' use); the light shines
            # the other way
            node["rotation"] = _look_quat(tuple(-c for c in light.dir))
        else:
            node["translation"] = list(light.origin)
            if kind == "spot":
                node["rotation"] = _look_quat(light.dir)
        nodes.append(node)
        nodes[0]["children"].append(len(nodes) - 1)
    doc = {"asset": {"version": "2.0", "generator": "ghosts-decomp tools/fastfile/gfxworld.py"},
           "scene": 0, "scenes": [{"nodes": [0]}], "nodes": nodes, "meshes": meshes, "materials": materials,
           "accessors": b.accessors, "bufferViews": b.views,
           "extras": {"map": world.name, "lightmaps": world.lightmaps, "lightmap_images": lightmap_images,
                      "sky": world.sky_images, "reflection_probes": [p[0] for p in world.reflection_probes]}}
    if images:
        doc["images"], doc["textures"] = images, textures
        doc["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
    if doc_lights:
        doc["extensionsUsed"] = ["KHR_lights_punctual"]
        doc["extensions"] = {"KHR_lights_punctual": {"lights": doc_lights}}
    return doc, bytes(b.data)


def main(argv=None):
    """python3 tools/fastfile/gfxworld.py <map.ff> --out <dir>: load the zone up to and including its GfxWorld with
    this folder's readers and write <map>.glb. A zone whose assets before the GfxWorld include a type this folder
    has no reader for can't be walked yet; tests/fastfile/world_check.py uses the game's own loader to get there."""
    import argparse
    import os
    import sys
    ap = argparse.ArgumentParser(description=main.__doc__.split("\\n")[0])
    ap.add_argument("fastfile")
    ap.add_argument("--out", default=".")
    ap.add_argument("--scale", type=float, default=0.0254, help="game units (inches) to metres by default")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import iw6ff
    register(iw6ff.ASSET_LOADERS)
    prefix, result, s = image_mod.walk_images(a.fastfile)
    worlds = [h for t, h in s.links if t == ASSET_GFXWORLD]
    if not worlds:
        print("no GfxWorld reached (stopped at asset %s)" % (result[5],))
        return 1
    world = read_world(s, worlds[0])
    doc, binary = to_gltf(world, scale=a.scale)
    os.makedirs(a.out, exist_ok=True)
    out = os.path.join(a.out, (world.base_name or "world").replace("/", "_") + ".glb")
    open(out, "wb").write(xmodel_mod.write_glb(doc, binary))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
