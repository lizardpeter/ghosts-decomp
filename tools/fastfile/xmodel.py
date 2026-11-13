#!/usr/bin/env python3
"""Models in Call of Duty: Ghosts PC zones (Microsoft Store build): XModel, XModelSurfs, XSurface, PhysPreset,
PhysCollmap. Standard library only.

Three layers, each usable on its own (docs/assets/models.md has the formats with their evidence):

1. Loaders (load_xmodel, load_xmodel_surfs, load_xsurface, load_physpreset, load_physcollmap and the *_ptr asset
   pointer rules): the Store build's Load_* functions statement for statement (src/xanim/xmodel_load_db.cpp,
   src/gfx_d3d/r_xsurface_load_db.cpp, src/physics/physpreset_load_db.cpp, src/qcommon/cm_brush_related_load_db.cpp,
   all differential-tested against the exe). They walk a zone stream and leave the asset in the stream's block
   memory exactly as the game lays it out, pointers resolved. The stream is any object with the methods of
   tools/fastfile/iw6ff.py's Stream (the pipeline's reference reader), listed in StreamProtocol below; GPU handles
   (the D3D11 buffers and views the game creates while loading) are stored as 0, as the game does with
   r_loadForRenderer off.
2. Readers (read_xmodel, read_xsurface, read_physcollmap, ...): plain Python objects (dataclasses) from a memory
   image: the stream's, or the game's own memory after it loaded the zone. Vertices are decoded (positions, normals
   and tangents from the packed 10:10:10:2 format, half-float UVs, colors, skin weights).
3. Converters: to_gltf(model) -> a glTF 2.0 document (JSON + one binary buffer, or a .glb): the skeleton as nodes
   with the bind pose, a skin, every LOD as its own mesh, each surface a primitive whose material is a named
   reference to the game material.

Material handles and other assets outside this module (materials, technique sets, images) are loaded through
`material_loader`, a callable the caller provides (the material module's Load_MaterialHandle rule); without one,
the material array must hold offsets (aliases), as it does when the materials were loaded earlier in the zone.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from dataclasses import dataclass, field
from typing import Callable, Protocol

PTR_INLINE = 0xFDFDFDFFFFFFFFFF   # DB_PTR_FOLLOWING: the data follows in the stream
PTR_INSERT = 0xFDFDFDFFFFFFFFFE   # DB_PTR_INSERT: follows, and an alias slot is reserved
XFILE_BLOCK_TEMP, XFILE_BLOCK_VIRTUAL = 0, 3

ASSET_PHYSPRESET, ASSET_PHYSCOLLMAP, ASSET_XMODELSURFS, ASSET_XMODEL = 0x00, 0x01, 0x03, 0x04
XMODEL_SIZE, LODINFO_SIZE, XMODELSURFS_SIZE, XSURFACE_SIZE = 0x258, 0x40, 0x38, 0xE8
XRIGIDVERTLIST_SIZE, COLLTREE_SIZE, SUBDIVINFO_SIZE, SUBDIVLEVEL_SIZE = 0x10, 0x38, 0x38, 0xE8
PHYSPRESET_SIZE, PHYSCOLLMAP_SIZE, PHYSGEOMINFO_SIZE = 0x58, 0x58, 0x48
BRUSHWRAPPER_SIZE, CBRUSH_SIZE, CBRUSHSIDE_SIZE, CPLANE_SIZE = 0x58, 0x30, 0x10, 0x14
MAX_LODS = 6
VERTEX_SIZE = 0x20                # XSurfaceGetVert0Size (14066CD30)
BONE_OFFSET_SCALE = 0x40          # bone references in XRigidVertList / XBlendInfo are bone index * 64
XSURFACE_FLAG_MOTION_VERTS = 0x8
XMODEL_FLAG_DEFAULT_SURFS = 0x2

HIT_LOCATIONS = ("none", "helmet", "head", "neck", "torso_upper", "torso_lower", "right_arm_upper",
                 "left_arm_upper", "right_arm_lower", "left_arm_lower", "right_hand", "left_hand",
                 "right_leg_upper", "left_leg_upper", "right_leg_lower", "left_leg_lower", "right_foot",
                 "left_foot", "gun", "shield", "armor", "soft")
PHYS_GEOM_TYPES = ("none", "box", "brushmodel", "brush", "collmap", "cylinder", "capsule", "glass")


class StreamProtocol(Protocol):
    """What the loaders need from the zone stream (tools/fastfile/iw6ff.py Stream has all of it)."""
    def load(self, at_stream_start: bool, address: int, size: int): ...   # Load_Stream
    def align(self, alignment: int) -> int: ...                            # g_streamPos alignment; new address
    def addr(self) -> int: ...                                             # g_streamPos
    def push(self, index: int): ...                                        # DB_PushStreamPos
    def pop(self): ...                                                     # DB_PopStreamPos
    def read(self, address: int, n: int) -> bytes: ...
    def u64(self, address: int) -> int: ...
    def put_u64(self, address: int, v: int): ...
    def write(self, address: int, data: bytes): ...
    def xstring_ptr(self, field_address: int): ...                         # the XString field rule
    def offset_to_pointer(self, v: int) -> int: ...                        # DB_ConvertOffsetToPointer
    def offset_to_alias(self, v: int) -> int: ...                          # DB_ConvertOffsetToAlias
    def insert_pointer(self) -> int: ...                                   # DB_InsertPointer
    def link(self, asset_type: int, header: int) -> int: ...               # Load_<Type>Asset (DB_LinkXAssetEntry)


def _u8(s, a):
    return s.read(a, 1)[0]


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _i16(s, a):
    return struct.unpack("<h", s.read(a, 2))[0]


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _wrap(v):
    """A C size computed in 64 bits (negative counts wrap, as in the game)."""
    return v & 0xFFFFFFFFFFFFFFFF


# ==== 1. loaders (the Store build's Load_* functions) =============================================================

def _inline_array(s, field_address: int, alignment: int, size: int, *, offset_form: bool = True):
    """The generated rule for a pointer to plain data: null stays null; DB_PTR_FOLLOWING (any non-zero value when
    the field has no offset form) -> align, point the field at the stream, load `size` bytes; anything else ->
    DB_ConvertOffsetToPointer."""
    v = s.u64(field_address)
    if not v:
        return
    if offset_form and v != PTR_INLINE:
        s.put_u64(field_address, s.offset_to_pointer(v))
        return
    p = s.align(alignment) if alignment > 1 else s.addr()
    s.put_u64(field_address, p)
    s.load(True, p, _wrap(size))


def asset_ptr(s, varptr: int, asset_type: int, header_loader, alignment: int = 4, after_link=None):
    """Load_<Type>Ptr (Load_XModelPtr 14035E530, Load_XModelSurfsPtr 14035E860, Load_PhysPresetPtr 1403555F0,
    Load_PhysCollmapPtr 140355410): in the temp block, an offset is an alias to an asset loaded earlier; -1/-2:
    the header follows (aligned to 4), -2 also reserving an alias slot that receives the final pointer."""
    s.push(XFILE_BLOCK_TEMP)
    v = s.u64(varptr)
    if v:
        if v not in (PTR_INLINE, PTR_INSERT):
            s.put_u64(varptr, s.offset_to_alias(v))
        else:
            h = s.align(alignment)
            s.put_u64(varptr, h)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            header_loader(s, h, True)
            s.put_u64(varptr, s.link(asset_type, h))
            if after_link is not None:
                after_link(s, s.u64(varptr))
            if slot is not None:
                s.put_u64(slot, s.u64(varptr))
    s.pop()


def load_xmodel(s, at: int, at_stream_start: bool = True, material_loader=None):
    """Load_XModel (14035E020)."""
    s.load(at_stream_start, at, XMODEL_SIZE)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    bones, roots, surfs, rmp = s.read(at + 8, 4)
    v = s.u64(at + 0x30)                                       # boneNames: Load_scr_string_tArray(numBones)
    if v:
        if v == PTR_INLINE:
            p = s.align(4)
            s.put_u64(at + 0x30, p)
            load_scr_string_array(s, p, bones)
        else:
            s.put_u64(at + 0x30, s.offset_to_pointer(v))
    _inline_array(s, at + 0x38, 1, bones - roots)              # parentList
    _inline_array(s, at + 0x40, 2, 2 * (4 * (bones - roots)))  # quats
    _inline_array(s, at + 0x48, 4, 4 * (3 * (bones - roots)))  # trans
    _inline_array(s, at + 0x50, 1, bones)                      # partClassification
    _inline_array(s, at + 0x58, 4, 0x20 * bones)               # baseMat
    _inline_array(s, at + 0x60, 16, 0x10 * rmp)                # reactiveMotionParts
    if s.u64(at + 0x68):                                       # materialHandles: always inline
        p = s.align(8)
        s.put_u64(at + 0x68, p)
        load_material_handle_array(s, p, surfs, material_loader)
    for lod in range(MAX_LODS):
        info = at + 0x70 + LODINFO_SIZE * lod
        asset_ptr(s, info + 8, ASSET_XMODELSURFS, load_xmodel_surfs)
        xmodel_surfs_fixup(s, info)                            # Load_XModelSurfsFixup (140374250)
    _inline_array(s, at + 0x1F8, 4, 0x24 * _i32(s, at + 0x1F4), offset_form=False)  # collSurfs
    _inline_array(s, at + 0x208, 4, 0x1C * bones, offset_form=False)                 # boneInfo
    _inline_array(s, at + 0x230, 2, 2 * surfs, offset_form=False)                    # Store-only array
    asset_ptr(s, at + 0x240, ASSET_PHYSPRESET, load_physpreset)
    asset_ptr(s, at + 0x248, ASSET_PHYSCOLLMAP, load_physcollmap)
    s.pop()


def load_scr_string_array(s, at: int, count: int):
    """Load_scr_string_tArray (140361EA0): count 4-byte script string indices, read as they are (the game maps them
    through the zone's script string table; tools/fastfile/iw6ff.py does that part)."""
    s.load(True, at, 4 * count)


def load_material_handle_array(s, at: int, count: int, material_loader=None):
    """Load_MaterialHandleArray (1403537F0): count 8-byte Material pointers, each an asset pointer to a material
    (the material module's rule). Without a material_loader, every handle must be null or an offset (alias)."""
    s.load(True, at, 8 * count)
    for i in range(count):
        if material_loader is not None:
            material_loader(s, at + 8 * i)
            continue
        s.push(XFILE_BLOCK_TEMP)
        v = s.u64(at + 8 * i)
        if v in (PTR_INLINE, PTR_INSERT):
            raise ValueError("an inline material needs a material_loader (the material module)")
        if v:
            s.put_u64(at + 8 * i, s.offset_to_alias(v))
        s.pop()


def xmodel_surfs_fixup(s, lod_info: int):
    """Load_XModelSurfsFixup (140374250): the LOD takes the XModelSurfs' partBits and surfs."""
    surfs = s.u64(lod_info + 8)
    if surfs:
        s.write(lod_info + 0x10, s.read(surfs + 0x14, 0x20))
        s.put_u64(lod_info + 0x30, s.u64(surfs + 8))


def db_xmodel_surfs_fixup(s, model: int, default_surfs: int = 0):
    """DB_XModelSurfsFixup (1403712F0), run when the XModel is linked (Load_XModelAsset): per LOD, partBits, surfs,
    numsurfs and surfIndex from its XModelSurfs; the total into numsurfs; flag 2 if a LOD uses g_defaultSurfs."""
    flags = _u8(s, model + 0x1F3) & ~XMODEL_FLAG_DEFAULT_SURFS
    total = 0
    num_lods = struct.unpack("<b", s.read(model + 0x1F1, 1))[0]
    for lod in range(max(num_lods, 0)):
        info = model + 0x70 + LODINFO_SIZE * lod
        surfs = s.u64(info + 8)
        s.write(info + 0x10, s.read(surfs + 0x14, 0x20))
        s.put_u64(info + 0x30, s.u64(surfs + 8))
        n = _u16(s, surfs + 0x10)
        s.write(info + 4, struct.pack("<HH", n, total & 0xFFFF))
        if s.u64(surfs + 8) == default_surfs and default_surfs:
            flags |= XMODEL_FLAG_DEFAULT_SURFS
        total += n
    s.write(model + 0x1F3, bytes([flags]))
    s.write(model + 0xA, bytes([total & 0xFF]))


def load_xmodel_surfs(s, at: int, at_stream_start: bool = True):
    """Load_XModelSurfs (14035E750)."""
    s.load(at_stream_start, at, XMODELSURFS_SIZE)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    if s.u64(at + 8):
        p = s.align(4)
        s.put_u64(at + 8, p)
        count = _u16(s, at + 0x10)
        s.load(True, p, XSURFACE_SIZE * count)
        for i in range(count):
            load_xsurface(s, p + XSURFACE_SIZE * i, False)
    s.pop()


def load_xsurface(s, at: int, at_stream_start: bool = True):
    """Load_XSurface (14035EAF0). GPU buffers and views are set to 0 (see the module docstring)."""
    s.load(at_stream_start, at, XSURFACE_SIZE)
    flags, vert_count, tri_count, rigid_count, subdiv_count = struct.unpack("<HHHBB", s.read(at, 8))
    counts = struct.unpack("<8h", s.read(at + 8, 16))
    _inline_array(s, at + 0x18, 16, VERTEX_SIZE * vert_count)       # verts0 (packed or motion vertices)
    _inline_array(s, at + 0x20, 16, 2 * 3 * tri_count)             # triIndices
    for off in (0x28, 0x30, 0x38):                                 # vb0, vb0View, indexBuffer
        s.put_u64(at + off, 0)
    v = s.u64(at + 0x40)                                           # rigidVertLists (Load_XRigidVertListArray)
    if v:
        if v == PTR_INLINE:
            p = s.align(4)
            s.put_u64(at + 0x40, p)
            s.load(True, p, XRIGIDVERTLIST_SIZE * rigid_count)
            for i in range(rigid_count):
                tree = p + XRIGIDVERTLIST_SIZE * i + 8
                t = s.u64(tree)
                if t == PTR_INLINE:
                    q = s.align(4)
                    s.put_u64(tree, q)
                    load_collision_tree(s, q)
                elif t:
                    s.put_u64(tree, s.offset_to_pointer(t))
        else:
            s.put_u64(at + 0x40, s.offset_to_pointer(v))
    blend_entries = sum((2 * i + 1) * c for i, c in enumerate(counts))
    _inline_array(s, at + 0x48, 2, 2 * blend_entries)              # blendVerts (XBlendInfo)
    _inline_array(s, at + 0x50, 1, 0x20 * vert_count)              # blendVertsTable (Store only)
    s.put_u64(at + 0x58, 0)
    s.put_u64(at + 0x60, 0)
    _inline_array(s, at + 0x68, 4, 8 * vert_count)                 # lmapUnwrap
    s.put_u64(at + 0x70, 0)
    s.put_u64(at + 0x78, 0)
    if s.u64(at + 0x80):                                           # subdiv (Store only): always inline
        p = s.align(4)
        s.put_u64(at + 0x80, p)
        load_subdiv_info(s, p, subdiv_count, rigid_count)
    _inline_array(s, at + 0x88, 4, 4 * sum(counts))                # tensionData
    _inline_array(s, at + 0x90, 2, 0x20 * vert_count)              # tensionAccumTable
    for off in (0x98, 0xA0, 0xA8, 0xB0, 0xB8):
        s.put_u64(at + off, 0)


def load_collision_tree(s, at: int):
    """Load_XSurfaceCollisionTree (14035F2E0)."""
    s.load(True, at, COLLTREE_SIZE)
    _inline_array(s, at + 0x20, 16, 0x10 * _u32(s, at + 0x18), offset_form=False)
    _inline_array(s, at + 0x30, 2, 2 * _u32(s, at + 0x28), offset_form=False)


def load_subdiv_info(s, at: int, level_count: int, rigid_count: int):
    """sub_14035F3A0 (Store only: Load_XSurfaceSubdivInfo) and sub_14035F430 (the levels)."""
    s.load(True, at, SUBDIVINFO_SIZE)
    if s.u64(at):
        p = s.align(4)
        s.put_u64(at, p)
        s.load(True, p, SUBDIVLEVEL_SIZE * level_count)
        for i in range(level_count):
            lv = p + SUBDIVLEVEL_SIZE * i
            c = struct.unpack("<17I", s.read(lv + 8, 0x44))
            face, patches, fp_size, edges, vp_size, normal_size, transitions = c[0], c[1], c[5], c[6], c[11], c[13], c[14]
            _inline_array(s, lv + 0x00, 4, 0x10 * rigid_count)
            _inline_array(s, lv + 0x50, 2, 2 * ((6 * face) & 0xFFFFFFFF), offset_form=False)
            _inline_array(s, lv + 0x58, 2, 2 * ((16 * patches) & 0xFFFFFFFF), offset_form=False)
            _inline_array(s, lv + 0x60, 4, 4 * patches, offset_form=False)
            _inline_array(s, lv + 0x68, 4, fp_size & ~3, offset_form=False)
            _inline_array(s, lv + 0x70, 4, 4 * ((2 * edges) & 0xFFFFFFFF), offset_form=False)
            _inline_array(s, lv + 0x78, 4, vp_size & ~3, offset_form=False)
            _inline_array(s, lv + 0x80, 4, normal_size & ~3, offset_form=False)
            _inline_array(s, lv + 0x88, 4, 4 * transitions, offset_form=False)
            _inline_array(s, lv + 0x90, 4, 4 * ((8 * patches) & 0xFFFFFFFF), offset_form=False)
            s.write(lv + 0x98, bytes(0x50))                        # the GPU buffers and views
    s.write(at + 0x28, bytes(0x10))                                # cache buffer and UAV (sub_1401B3D60)


def load_physpreset(s, at: int, at_stream_start: bool = True):
    """Load_PhysPreset (140355500): 0x58 bytes; the XStrings name (+0) and sndAliasPrefix (+0x20)."""
    s.load(at_stream_start, at, PHYSPRESET_SIZE)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    s.xstring_ptr(at + 0x20)
    s.pop()


def load_physcollmap(s, at: int, at_stream_start: bool = True):
    """Load_PhysCollmap (1403552B0) with Load_PhysGeomInfoArray, Load_BrushWrapper (14034AF80),
    Load_cbrushWrapper_t (14035F860) and Load_cbrushside_tArray (14035FA50)."""
    s.load(at_stream_start, at, PHYSCOLLMAP_SIZE)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    if s.u64(at + 0x10):
        p = s.align(4)
        s.put_u64(at + 0x10, p)
        count = _u32(s, at + 8)
        s.load(True, p, PHYSGEOMINFO_SIZE * count)
        for i in range(count):
            geom = p + PHYSGEOMINFO_SIZE * i
            if s.u64(geom):
                w = s.align(4)
                s.put_u64(geom, w)
                load_brush_wrapper(s, w)
    s.pop()


def load_brush_wrapper(s, at: int):
    s.load(True, at, BRUSHWRAPPER_SIZE)
    brush = at + 0x18
    numsides = _u16(s, brush)
    if s.u64(brush + 8):                                           # sides: always inline
        p = s.align(4)
        s.put_u64(brush + 8, p)
        s.load(True, p, CBRUSHSIDE_SIZE * numsides)
        for i in range(numsides):
            _inline_array(s, p + CBRUSHSIDE_SIZE * i, 4, CPLANE_SIZE)
    if s.u64(brush + 0x10):                                        # baseAdjacentSide: unaligned
        p = s.addr()
        s.put_u64(brush + 0x10, p)
        s.load(True, p, _wrap(_i32(s, at + 0x48)))
    _inline_array(s, at + 0x50, 4, CPLANE_SIZE * numsides)        # planes


def load_xmodel_ptr(s, varptr: int, material_loader=None):
    """Load_XModelPtr (14035E530): the entry point for an ASSET_TYPE_XMODEL entry of the XAsset list."""
    asset_ptr(s, varptr, ASSET_XMODEL, lambda s_, h, flag: load_xmodel(s_, h, flag, material_loader),
              after_link=db_xmodel_surfs_fixup)  # Load_XModelAsset (1403740C0) runs it on the linked header


def register(asset_loaders: dict, material_loader=None):
    """Add this module's asset loaders to tools/fastfile/iw6ff.py's ASSET_LOADERS (type -> fn(stream, varptr))."""
    asset_loaders[ASSET_XMODEL] = lambda s, varptr: load_xmodel_ptr(s, varptr, material_loader)
    asset_loaders[ASSET_XMODELSURFS] = lambda s, varptr: asset_ptr(s, varptr, ASSET_XMODELSURFS, load_xmodel_surfs)
    asset_loaders[ASSET_PHYSPRESET] = lambda s, varptr: asset_ptr(s, varptr, ASSET_PHYSPRESET, load_physpreset)
    asset_loaders[ASSET_PHYSCOLLMAP] = lambda s, varptr: asset_ptr(s, varptr, ASSET_PHYSCOLLMAP, load_physcollmap)


# ==== 2. readers (memory image -> Python objects) ===================================================================

def half(h: int) -> float:
    return struct.unpack("<e", struct.pack("<H", h))[0]


def unpack_unit_vec(packed: int) -> tuple[tuple[float, float, float], float]:
    """PackedUnitVec: 10:10:10:2 UNORM, x in the low bits, each n / 1023 * 2 - 1, the top 2 bits / 3
    (Vec3UnpackUnitVecWithAlpha, universal/com_pack.cpp in the servers; DXGI_FORMAT_R10G10B10A2_UNORM in the input
    layouts)."""
    return tuple(((packed >> sh) & 0x3FF) / 1023.0 * 2.0 - 1.0 for sh in (0, 10, 20)), (packed >> 30) / 3.0


def unpack_tex_coords(packed: int) -> tuple[float, float]:
    """PackedTexCoords: two half floats, u in the low 16 bits (DXGI_FORMAT_R16G16_FLOAT)."""
    return half(packed & 0xFFFF), half(packed >> 16)


@dataclass
class Vertex:
    position: tuple[float, float, float]
    binormal_sign: float          # GfxPackedVertex::binormalSign (the motion variant: binormalSignAndHeight)
    color: tuple[int, int, int, int]
    uv: tuple[float, float]
    normal: tuple[float, float, float]
    normal_w: float
    tangent: tuple[float, float, float]
    tangent_w: float


@dataclass
class CollisionTree:
    trans: tuple
    scale: tuple
    nodes: list            # (mins[3], maxs[3], childBeginIndex, childCount), quantized
    leafs: list            # triangleBeginIndex


@dataclass
class RigidVertList:
    bone: int              # boneOffset / 64
    vert_count: int
    tri_offset: int
    tri_count: int
    collision_tree: CollisionTree | None


@dataclass
class Surface:
    flags: int
    vert_count: int
    tri_count: int
    vertices: list[Vertex]
    triangles: list[tuple[int, int, int]]
    rigid_vert_lists: list[RigidVertList]
    blend_vert_counts: tuple
    blend_verts: list[int]                     # XBlendInfo as stored (bone offsets and 16-bit weights)
    blend_table: list | None                   # Store only: per vertex (bones[8], weights[7], count)
    skin: list[list[tuple[int, float]]]        # per vertex: (bone, weight), weights sum to 1
    lmap_unwrap: list | None
    tension_data: list | None
    tension_accum_table: list | None
    subdiv: dict | None
    vertex_lighting_index: int
    part_bits: tuple


@dataclass
class ModelSurfs:
    name: str | None
    surfaces: list[Surface]
    part_bits: tuple


@dataclass
class Lod:
    dist: float
    surf_index: int
    surfs: ModelSurfs | None
    part_bits: tuple


@dataclass
class Bone:
    name: str | int
    parent: int                 # -1 for a root bone
    local_quat: tuple           # (x, y, z, w), parent space (root bones: identity)
    local_trans: tuple          # parent space
    base_quat: tuple            # model space (DObjAnimMat)
    base_trans: tuple
    trans_weight: float
    hit_location: str
    bounds: tuple | None        # XBoneInfo: (midPoint, halfSize)
    radius_squared: float | None


@dataclass
class PhysPreset:
    name: str | None
    fields: dict


@dataclass
class PhysGeom:
    type: str
    orientation: tuple
    bounds: tuple
    brush: dict | None


@dataclass
class PhysCollmap:
    name: str | None
    geoms: list[PhysGeom]
    mass: dict
    bounds: tuple


@dataclass
class XModel:
    name: str | None
    bones: list[Bone]
    materials: list            # per surface (over all LODs, by surfIndex): material name or address
    lods: list[Lod]
    max_loaded_lod: int
    coll_lod: int
    flags: int
    coll_surfs: list
    contents: int
    radius: float
    bounds: tuple
    scale: float
    reactive_motion_parts: list
    unknown230: list | None
    phys_preset: PhysPreset | None
    phys_collmap: PhysCollmap | None
    raw: dict = field(default_factory=dict)


class Memory:
    """A memory image to read from: anything with read(address, n). Adds typed reads."""

    def __init__(self, src):
        self.src = src

    def read(self, a, n):
        return self.src.read(a, n)

    def q(self, a):
        return struct.unpack("<Q", self.read(a, 8))[0]

    def unpack(self, fmt, a):
        return struct.unpack("<" + fmt, self.read(a, struct.calcsize("<" + fmt)))

    def cstr(self, a, limit=4096):
        if not a:
            return None
        out = bytearray()
        while len(out) < limit:
            chunk = self.read(a + len(out), 64)
            i = chunk.find(b"\0")
            if i >= 0:
                return (out + chunk[:i]).decode("latin1")
            out += chunk
        return out.decode("latin1")

    def array(self, fmt, a, count):
        if not a or count <= 0:
            return []
        size = struct.calcsize("<" + fmt)
        data = self.read(a, size * count)
        return [struct.unpack_from("<" + fmt, data, size * i) for i in range(count)]


def read_vertices(m: Memory, a: int, count: int) -> list[Vertex]:
    out = []
    for x, y, z, sign, col, uv, n, t in m.array("4f4I", a, count):
        nv, nw = unpack_unit_vec(n)
        tv, tw = unpack_unit_vec(t)
        out.append(Vertex((x, y, z), sign, tuple(col.to_bytes(4, "little")), unpack_tex_coords(uv), nv, nw, tv, tw))
    return out


def blend_skin(surf_counts, blend_verts, rigid_lists, vert_count):
    """Per vertex (bone, weight) lists. Rigid vertex lists cover their vertices in order with one bone each; the
    blended vertices follow, grouped by bone count: blendVertCounts[n] vertices with n + 1 bones, each as bone0,
    then (bone_i, weight_i) for i >= 1 (bones as bone index * 64, weights / 65536; bone0 gets the rest)."""
    skin = []
    for rl in rigid_lists:
        skin += [[(rl.bone, 1.0)] for _ in range(rl.vert_count)]
    i = 0
    for n, count in enumerate(surf_counts):
        for _ in range(max(count, 0)):
            entry = blend_verts[i:i + 2 * n + 1]
            i += 2 * n + 1
            bones = [entry[0] // BONE_OFFSET_SCALE]
            weights = []
            for k in range(n):
                bones.append(entry[1 + 2 * k] // BONE_OFFSET_SCALE)
                weights.append(entry[2 + 2 * k] / 65536.0)
            skin.append(list(zip(bones, [1.0 - sum(weights)] + weights)))
    if len(skin) < vert_count:
        skin += [[] for _ in range(vert_count - len(skin))]
    return skin[:vert_count]


def read_collision_tree(m: Memory, a: int) -> CollisionTree:
    trans, scale = m.unpack("3f", a), m.unpack("3f", a + 0xC)
    node_count, nodes, leaf_count, leafs = m.unpack("I4xQI4xQ", a + 0x18)
    return CollisionTree(trans, scale,
                         [((n[0], n[1], n[2]), (n[3], n[4], n[5]), n[6], n[7]) for n in m.array("8H", nodes, node_count)],
                         [l[0] for l in m.array("H", leafs, leaf_count)])


SUBDIV_COUNTS = ("faceCount", "regularPatchCount", "regularPatchOffset", "facePointCount", "facePointValence4Count",
                 "facePointBufferSize", "edgePointCount", "edgePointSmoothEnd", "edgePointUVBorderEnd",
                 "vertexPointCount", "vertexPointValence4Count", "vertexPointBufferSize", "normalCount",
                 "normalBufferSize", "transitionPointCount", "vertCount", "vertOffset")


def read_subdiv(m: Memory, a: int, level_count: int, rigid_count: int) -> dict:
    levels_at, flags = m.unpack("QI", a)
    levels = []
    for i in range(level_count if levels_at else 0):
        lv = levels_at + SUBDIVLEVEL_SIZE * i
        c = dict(zip(SUBDIV_COUNTS, m.unpack("17I", lv + 8)))
        ptr = m.unpack("10Q", lv + 0x50)
        levels.append({
            **c,
            "rigidVertLists": [r for r in m.array("16s", m.q(lv), rigid_count)],
            "faceIndices": [x[0] for x in m.array("H", ptr[0], 6 * c["faceCount"])],
            "regularPatchIndices": [x[0] for x in m.array("H", ptr[1], 16 * c["regularPatchCount"])],
            "regularPatchFlags": [x[0] for x in m.array("I", ptr[2], c["regularPatchCount"])],
            "facePoints": [x[0] for x in m.array("I", ptr[3], c["facePointBufferSize"] // 4)],
            "edgePoints": [x[0] for x in m.array("I", ptr[4], 2 * c["edgePointCount"])],
            "vertexPoints": [x[0] for x in m.array("I", ptr[5], c["vertexPointBufferSize"] // 4)],
            "normals": [x[0] for x in m.array("I", ptr[6], c["normalBufferSize"] // 4)],
            "transitionPoints": [x[0] for x in m.array("I", ptr[7], c["transitionPointCount"])],
            "regularPatchCones": [x[0] for x in m.array("f", ptr[8], 8 * c["regularPatchCount"])],
        })
    return {"flags": flags, "cacheSize": m.unpack("I", a + 0x20)[0], "levels": levels}


def read_xsurface(m: Memory, a: int) -> Surface:
    flags, vc, tc, rc, sc = m.unpack("HHHBB", a)
    counts = m.unpack("8h", a + 8)
    p = m.unpack("Q" * 21, a + 0x18)
    verts0, tri, rigid, blend, table, lmap, subdiv, tension, accum = p[0], p[1], p[5], p[6], p[7], p[10], p[13], p[14], p[15]
    rigid_lists = []
    for bone_off, n, to, tcount, tree in m.array("4HQ", rigid, rc):
        rigid_lists.append(RigidVertList(bone_off // BONE_OFFSET_SCALE, n, to, tcount,
                                         read_collision_tree(m, tree) if tree else None))
    blend_n = sum((2 * i + 1) * c for i, c in enumerate(counts))
    blend_verts = [x[0] for x in m.array("H", blend, blend_n)]
    idx = [x[0] for x in m.array("H", tri, 3 * tc)]
    return Surface(
        flags, vc, tc, read_vertices(m, verts0, vc) if verts0 else [],
        [tuple(idx[i:i + 3]) for i in range(0, len(idx), 3)],
        rigid_lists, counts, blend_verts,
        [(e[0:8], e[8:15], e[15]) for e in m.array("16H", table, vc)] if table else None,
        blend_skin(counts, blend_verts, rigid_lists, vc),
        [tuple(x) for x in m.array("2f", lmap, vc)] if lmap else None,
        [x[0] for x in m.array("f", tension, sum(counts))] if tension else None,
        [x for x in m.array("16H", accum, vc)] if accum else None,
        read_subdiv(m, subdiv, sc, rc) if subdiv else None,
        m.unpack("I", a + 0xC0)[0], m.unpack("8i", a + 0xC4))


def read_xmodel_surfs(m: Memory, a: int) -> ModelSurfs:
    name, surfs, n = m.unpack("QQH", a)
    return ModelSurfs(m.cstr(name), [read_xsurface(m, surfs + XSURFACE_SIZE * i) for i in range(n if surfs else 0)],
                      m.unpack("8i", a + 0x14))


def read_physpreset(m: Memory, a: int) -> PhysPreset:
    v = m.unpack("Qi5fQ8f2i2?", a)
    keys = ("type", "mass", "bounce", "friction", "bulletForceScale", "explosiveForceScale", None,
            "piecesSpreadFraction", "piecesUpwardVelocity", "minMomentum", "maxMomentum", "minVolume", "maxVolume",
            "minPitch", "maxPitch", "volumeType", "pitchType", "tempDefaultToCylinder", "perSurfaceSndAlias")
    fields = {k: x for k, x in zip(keys, v[1:]) if k}
    fields["sndAliasPrefix"] = m.cstr(v[7])
    return PhysPreset(m.cstr(v[0]), fields)


def _read_brush(m: Memory, a: int) -> dict:
    bounds = m.unpack("6f", a)
    numsides, glass, sides, adjacent = m.unpack("HH4xQQ", a + 0x18)
    total_edges, planes = m.unpack("i4xQ", a + 0x48)
    side_list = []
    for plane, mat, first, edges in m.array("QHBB4x", sides, numsides):
        side_list.append({"plane": m.unpack("4fB", plane) if plane else None, "materialNum": mat,
                          "firstAdjacentSideOffset": first, "edgeCount": edges})
    return {"bounds": bounds, "glassPieceIndex": glass, "sides": side_list,
            "axialMaterialNum": m.unpack("6h", a + 0x30), "firstAdjacentSideOffsets": m.unpack("6B", a + 0x3C),
            "edgeCount": m.unpack("6B", a + 0x42), "totalEdgeCount": total_edges,
            "baseAdjacentSide": list(m.read(adjacent, total_edges)) if adjacent and total_edges > 0 else [],
            "planes": [p for p in m.array("4fB3x", planes, numsides)]}


def read_physcollmap(m: Memory, a: int) -> PhysCollmap:
    name, count, geoms = m.unpack("QI4xQ", a)
    mass = m.unpack("9f", a + 0x18)
    out = []
    for i in range(count if geoms else 0):
        g = geoms + PHYSGEOMINFO_SIZE * i
        wrapper, gtype = m.unpack("Qi", g)
        out.append(PhysGeom(PHYS_GEOM_TYPES[gtype] if 0 <= gtype < len(PHYS_GEOM_TYPES) else str(gtype),
                            m.unpack("9f", g + 0xC), m.unpack("6f", g + 0x30),
                            _read_brush(m, wrapper) if wrapper else None))
    return PhysCollmap(m.cstr(name), out, {"centerOfMass": mass[0:3], "momentsOfInertia": mass[3:6],
                                           "productsOfInertia": mass[6:9]}, m.unpack("6f", a + 0x3C))


def read_xmodel(src, a: int, script_string: Callable[[int], str] | None = None,
                material_name: Callable[[int], str] | None = None) -> XModel:
    """An XModel from a memory image (the loaders' stream, or the game's memory) at header address `a`.
    script_string maps a bone name's scr_string_t to text; material_name a Material pointer to its name."""
    m = Memory(src)
    name = m.q(a)
    bones_n, roots, nsurfs, rmp = m.unpack("4B", a + 8)
    scale = m.unpack("f", a + 0xC)[0]
    names_at, parents_at, quats_at, trans_at, parts_at, base_at, rmp_at, mats_at = m.unpack("8Q", a + 0x30)
    names = [x[0] for x in m.array("I", names_at, bones_n)]
    parents = list(m.read(parents_at, bones_n - roots)) if parents_at and bones_n > roots else []
    quats = m.array("4h", quats_at, bones_n - roots)
    trans = m.array("3f", trans_at, bones_n - roots)
    parts = list(m.read(parts_at, bones_n)) if parts_at and bones_n else [0] * bones_n
    base = m.array("8f", base_at, bones_n)
    infos_at = m.q(a + 0x208)
    infos = m.array("7f", infos_at, bones_n) if infos_at else []
    bones = []
    for i in range(bones_n):
        if i < roots or i - roots >= len(parents):
            parent, lq, lt = -1, (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
        else:
            parent = i - parents[i - roots]
            lq, lt = tuple(x / 32767.0 for x in quats[i - roots]), trans[i - roots]
        b = base[i] if i < len(base) else (0, 0, 0, 1, 0, 0, 0, 2)
        info = infos[i] if i < len(infos) else None
        bones.append(Bone(script_string(names[i]) if script_string and i < len(names) else (names[i] if i < len(names) else i),
                          parent, lq, lt, tuple(b[0:4]), tuple(b[4:7]), b[7],
                          HIT_LOCATIONS[parts[i]] if parts[i] < len(HIT_LOCATIONS) else str(parts[i]),
                          (info[0:3], info[3:6]) if info else None, info[6] if info else None))
    mats = [x[0] for x in m.array("Q", mats_at, nsurfs)]
    lods = []
    for lod in range(MAX_LODS):
        info = a + 0x70 + LODINFO_SIZE * lod
        dist, _, surf_index, surfs_at = m.unpack("fHHQ", info)
        lods.append(Lod(dist, surf_index, read_xmodel_surfs(m, surfs_at) if surfs_at else None, m.unpack("8i", info + 0x10)))
    max_lod, num_lods, coll_lod, flags, ncoll = m.unpack("bbbBi", a + 0x1F0)
    coll_at = m.q(a + 0x1F8)
    u230 = m.q(a + 0x230)
    pp, pc = m.unpack("QQ", a + 0x240)
    return XModel(
        m.cstr(name), bones, [material_name(p) if material_name and p else p for p in mats],
        lods[:max(num_lods, 0)], max_lod, coll_lod, flags,
        [(c[0:3], c[3:6], c[6], c[7], c[8]) for c in m.array("6f3i", coll_at, ncoll)] if coll_at else [],
        m.unpack("i", a + 0x200)[0], m.unpack("f", a + 0x210)[0], m.unpack("6f", a + 0x214), scale,
        m.array("4f", rmp_at, rmp) if rmp_at else [],
        [x[0] for x in m.array("H", u230, nsurfs)] if u230 else None,
        read_physpreset(m, pp) if pp else None, read_physcollmap(m, pc) if pc else None,
        {"noScalePartBits": m.unpack("8I", a + 0x10), "unknown22C": m.unpack("I", a + 0x22C)[0],
         "memUsage238": m.unpack("i", a + 0x238)[0], "unknown250": m.unpack("2I", a + 0x250)})


# ==== 3. glTF 2.0 ======================================================================================================

def _quat_to_matrix(q, t):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
            2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
            2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
            t[0], t[1], t[2], 1]   # column-major


def _invert_rigid(mtx):
    """Inverse of a column-major rotation + translation matrix."""
    r = [[mtx[c * 4 + rr] for c in range(3)] for rr in range(3)]   # r[row][col]
    t = mtx[12:15]
    rt = [[r[c][rr] for c in range(3)] for rr in range(3)]
    it = [-sum(rt[rr][c] * t[c] for c in range(3)) for rr in range(3)]
    return [rt[0][0], rt[1][0], rt[2][0], 0, rt[0][1], rt[1][1], rt[2][1], 0, rt[0][2], rt[1][2], rt[2][2], 0,
            it[0], it[1], it[2], 1]


class _Bin:
    def __init__(self):
        self.data, self.views, self.accessors = bytearray(), [], []

    def add(self, raw: bytes, count: int, comp: int, kind: str, target=None, minmax=None, normalized=False):
        while len(self.data) % 4:
            self.data.append(0)
        view = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(raw)}
        if target:
            view["target"] = target
        self.data += raw
        self.views.append(view)
        acc = {"bufferView": len(self.views) - 1, "componentType": comp, "count": count, "type": kind}
        if normalized:
            acc["normalized"] = True
        if minmax:
            acc["min"], acc["max"] = minmax
        self.accessors.append(acc)
        return len(self.accessors) - 1


def to_gltf(model: XModel, lods=None, z_up_to_y_up: bool = True, scale: float = 1.0) -> tuple[dict, bytes]:
    """A glTF 2.0 document (JSON dict) and its binary buffer. The skeleton is one node per bone with the local base
    pose; the skin's inverse bind matrices come from the model-space base pose (baseMat). Every LOD is its own
    mesh on its own node (extras: lod index and switch distance); every surface a primitive with POSITION, NORMAL,
    TANGENT (w: binormal sign), TEXCOORD_0, COLOR_0, JOINTS_0/WEIGHTS_0 (and _1 for up to 8 bones), indices.
    Materials are named references (the game material's name); no textures. Coordinates stay the game's (inches,
    Z up) under a root node that rotates Z up to Y up (z_up_to_y_up) and scales by `scale`."""
    b = _Bin()
    FLOAT, USHORT, UBYTE, UINT = 5126, 5123, 5121, 5125
    nodes, root_children = [], []
    root = {"name": model.name or "xmodel", "children": root_children}
    if z_up_to_y_up:
        root["rotation"] = [-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]
    if scale != 1.0:
        root["scale"] = [scale] * 3
    nodes.append(root)
    joint_nodes = []
    for i, bone in enumerate(model.bones):
        node = {"name": str(bone.name)}
        if any(abs(x) > 1e-9 for x in bone.local_trans):
            node["translation"] = list(bone.local_trans)
        q = bone.local_quat
        n = math.sqrt(sum(x * x for x in q)) or 1.0
        if abs(q[3] / n - 1.0) > 1e-9:
            node["rotation"] = [x / n for x in q]
        nodes.append(node)
        joint_nodes.append(len(nodes) - 1)
    for i, bone in enumerate(model.bones):
        if bone.parent >= 0:
            nodes[joint_nodes[bone.parent]].setdefault("children", []).append(joint_nodes[i])
        else:
            root_children.append(joint_nodes[i])
    skins = []
    if model.bones:
        ibm = b"".join(struct.pack("<16f", *_invert_rigid(_quat_to_matrix(bone.base_quat, bone.base_trans)))
                       for bone in model.bones)
        skins.append({"joints": joint_nodes, "inverseBindMatrices": b.add(ibm, len(model.bones), FLOAT, "MAT4"),
                      "skeleton": joint_nodes[0]})
    materials, material_index = [], {}
    meshes = []
    for li, lod in enumerate(model.lods):
        if lods is not None and li not in lods or lod.surfs is None:
            continue
        prims = []
        for si, surf in enumerate(lod.surfs.surfaces):
            if not surf.vertices:
                continue
            vs = surf.vertices
            mi_key = model.materials[lod.surf_index + si] if lod.surf_index + si < len(model.materials) else None
            if mi_key not in material_index:
                material_index[mi_key] = len(materials)
                materials.append({"name": str(mi_key) if not isinstance(mi_key, int) else f"material_{mi_key:#x}",
                                  "extras": {"game_material": mi_key}})
            pos = [v.position for v in vs]
            attrs = {
                "POSITION": b.add(b"".join(struct.pack("<3f", *p) for p in pos), len(vs), FLOAT, "VEC3", 34962,
                                  ([min(p[k] for p in pos) for k in range(3)], [max(p[k] for p in pos) for k in range(3)])),
                "NORMAL": b.add(b"".join(struct.pack("<3f", *_normalize(v.normal)) for v in vs), len(vs), FLOAT, "VEC3", 34962),
                "TANGENT": b.add(b"".join(struct.pack("<4f", *_normalize(v.tangent), 1.0 if v.binormal_sign >= 0 else -1.0)
                                          for v in vs), len(vs), FLOAT, "VEC4", 34962),
                "TEXCOORD_0": b.add(b"".join(struct.pack("<2f", *v.uv) for v in vs), len(vs), FLOAT, "VEC2", 34962),
                "COLOR_0": b.add(b"".join(bytes(v.color) for v in vs), len(vs), UBYTE, "VEC4", 34962, normalized=True),
            }
            if skins:
                width = 8 if any(len(sk) > 4 for sk in surf.skin) else 4
                joints = [[0] * width for _ in vs]
                weights = [[0.0] * width for _ in vs]
                for vi, sk in enumerate(surf.skin):
                    for k, (bone, w) in enumerate(sk[:width]):
                        joints[vi][k], weights[vi][k] = bone, w
                    if not sk:
                        weights[vi][0] = 1.0
                    total = sum(weights[vi]) or 1.0
                    weights[vi] = [w / total for w in weights[vi]]
                for set_i in range(width // 4):
                    attrs[f"JOINTS_{set_i}"] = b.add(b"".join(struct.pack("<4H", *j[4 * set_i:4 * set_i + 4]) for j in joints),
                                                     len(vs), USHORT, "VEC4", 34962)
                    attrs[f"WEIGHTS_{set_i}"] = b.add(b"".join(struct.pack("<4f", *w[4 * set_i:4 * set_i + 4]) for w in weights),
                                                      len(vs), FLOAT, "VEC4", 34962)
            idx = [i for t in surf.triangles for i in t]
            prim = {"attributes": attrs, "material": material_index[mi_key], "mode": 4,
                    "indices": b.add(struct.pack("<%dH" % len(idx), *idx), len(idx), USHORT, "SCALAR", 34963)}
            prims.append(prim)
        if prims:
            meshes.append({"name": f"{model.name}_lod{li}", "primitives": prims})
            node = {"name": f"{model.name}_lod{li}", "mesh": len(meshes) - 1, "extras": {"lod": li, "dist": lod.dist}}
            if skins:
                node["skin"] = 0
            nodes.append(node)
            root_children.append(len(nodes) - 1)
    doc = {"asset": {"version": "2.0", "generator": "ghosts-decomp tools/fastfile/xmodel.py"},
           "scene": 0, "scenes": [{"nodes": [0]}], "nodes": nodes, "meshes": meshes, "materials": materials,
           "accessors": b.accessors, "bufferViews": b.views, "buffers": [{"byteLength": len(b.data)}],
           "extras": {"xmodel": model.name, "radius": model.radius, "bounds": list(model.bounds),
                      "lod_distances": [lod.dist for lod in model.lods]}}
    if skins:
        doc["skins"] = skins
    return doc, bytes(b.data)


def _normalize(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v) if n > 1e-12 else (0.0, 0.0, 1.0)


def write_glb(doc: dict, binary: bytes) -> bytes:
    doc = dict(doc, buffers=[{"byteLength": len(binary)}])
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    binary += b"\0" * (-len(binary) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binary))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(binary), 0x004E4942) + binary
    return out


def write_gltf(doc: dict, binary: bytes, bin_name: str) -> tuple[str, bytes]:
    doc = dict(doc, buffers=[{"byteLength": len(binary), "uri": bin_name}])
    return json.dumps(doc, indent=1), binary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Decode the XModels of a Ghosts PC zone and write glTF 2.0 files.")
    ap.add_argument("fastfile")
    ap.add_argument("--out", default=".")
    opts = ap.parse_args(argv)
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import iw6ff  # the pipeline's reference reader (tools/fastfile/iw6ff.py)
    register(iw6ff.ASSET_LOADERS)
    with open(opts.fastfile, "rb") as f:
        zone = iw6ff.read_fastfile(f.read(), os.path.basename(opts.fastfile).rsplit(".", 1)[0])
    strings = zone.script_strings
    for a in zone.assets:
        if a.type != ASSET_XMODEL or not a.header:
            continue
        model = read_xmodel(zone.stream, a.header,
                            lambda i: (strings[i].decode("latin1") if 0 <= i < len(strings) and strings[i] else str(i)))
        doc, binary = to_gltf(model)
        path = os.path.join(opts.out, (model.name or "xmodel").replace("/", "_") + ".glb")
        with open(path, "wb") as f:
            f.write(write_glb(doc, binary))
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
