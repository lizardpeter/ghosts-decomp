#!/usr/bin/env python3
"""Tests of tools/fastfile/xmodel.py (the XModel / XSurface / physics decoder and its glTF converter).

    python3 tests/fastfile/test_xmodel.py

Synthetic: a zone stream is built by hand in the order docs/assets/models.md gives (what each Load_* reads, where
each pointer marker sends the data), with a small stream (SynthStream) that follows the pipeline's rules (blocks,
alignment in memory only, the temp block's push/pop reuse, offsets as block << 32 | offset + 1, links into a pool).
The decoder must consume exactly the bytes built, leave the asset where the rules put it, and read back the values
the builder put in. Real zones: with IW6_FASTFILES set (a folder of .ff files) and the pipeline's reader
(tools/fastfile/iw6ff.py) present, every XModel of the zones listed in IW6_XMODEL_ZONES (default mp_head_aa_tr.ff)
is decoded and checked for invariants; otherwise those tests skip. No game data is part of this file.
"""
import json
import math
import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "fastfile"))
import xmodel as X  # noqa: E402

INLINE, INSERT = X.PTR_INLINE, X.PTR_INSERT
BLOCK_SIZE = 0x40000


class SynthStream:
    """The stream rules of docs/fastfiles.md, small: what tools/fastfile/iw6ff.py's Stream does."""

    def __init__(self, zone: bytes):
        self.zone, self.cursor = zone, 0
        self.bases = [(i + 1) << 40 for i in range(8)]   # block 7: the asset pool (links)
        self.mem = [bytearray(BLOCK_SIZE) for _ in range(8)]
        self.pos = [0] * 8
        self.index = X.XFILE_BLOCK_VIRTUAL
        self.stack = []
        self.links = []

    def _loc(self, a):
        for i, b in enumerate(self.bases):
            if b <= a < b + BLOCK_SIZE:
                return i, a - b
        raise ValueError(f"{a:#x} is in no block")

    def read(self, a, n):
        i, o = self._loc(a)
        return bytes(self.mem[i][o:o + n])

    def write(self, a, data):
        i, o = self._loc(a)
        self.mem[i][o:o + len(data)] = data

    def u64(self, a):
        return struct.unpack("<Q", self.read(a, 8))[0]

    def put_u64(self, a, v):
        self.write(a, struct.pack("<Q", v & (2 ** 64 - 1)))

    def addr(self):
        return self.bases[self.index] + self.pos[self.index]

    def load(self, at_stream_start, a, size):
        if not at_stream_start or not size:
            return
        data = self.zone[self.cursor:self.cursor + size]
        if len(data) != size:
            raise EOFError("read past the end of the zone")
        self.cursor += size
        self.write(a, data)
        self.pos[self.index] += size

    def align(self, n):
        self.pos[self.index] = (self.pos[self.index] + n - 1) & ~(n - 1)
        return self.addr()

    def push(self, i):
        self.stack.append((self.pos[i], self.index))
        self.index = i

    def pop(self):
        saved, index = self.stack.pop()
        if self.index == X.XFILE_BLOCK_TEMP:
            self.pos[X.XFILE_BLOCK_TEMP] = saved
        self.index = index

    def insert_pointer(self):
        self.push(X.XFILE_BLOCK_VIRTUAL)
        slot = self.align(8)
        self.pos[X.XFILE_BLOCK_VIRTUAL] += 8
        self.pop()
        return slot

    def offset_to_pointer(self, v):
        return self.bases[(v >> 32) & 0xF] + (v & 0xFFFFFFFF) - 1

    def offset_to_alias(self, v):
        return self.u64(self.offset_to_pointer(v))

    def xstring_ptr(self, field_address):
        v = self.u64(field_address)
        if v == INLINE:
            start = self.addr()
            self.put_u64(field_address, start)
            end = self.zone.index(b"\0", self.cursor) + 1
            self.load(True, start, end - self.cursor)
        elif v:
            self.put_u64(field_address, self.offset_to_pointer(v))

    def link(self, asset_type, header):
        size = {X.ASSET_XMODEL: X.XMODEL_SIZE, X.ASSET_XMODELSURFS: X.XMODELSURFS_SIZE,
                X.ASSET_PHYSPRESET: X.PHYSPRESET_SIZE, X.ASSET_PHYSCOLLMAP: X.PHYSCOLLMAP_SIZE}[asset_type]
        at = (self.pos[7] + 15) & ~15
        self.mem[7][at:at + size] = self.read(header, size)
        self.pos[7] = at + size
        self.links.append((asset_type, self.bases[7] + at))
        return self.bases[7] + at


def pack_unit(x, y, z, w=3):
    q = [max(0, min(1023, round((c + 1) / 2 * 1023))) for c in (x, y, z)]
    return q[0] | q[1] << 10 | q[2] << 20 | w << 30


def pack_uv(u, v):
    return struct.unpack("<H", struct.pack("<e", u))[0] | struct.unpack("<H", struct.pack("<e", v))[0] << 16


def vertex(xyz, sign=1.0, color=(255, 128, 0, 255), uv=(0.25, 0.75), n=(0, 0, 1), t=(1, 0, 0)):
    return struct.pack("<4f4B2I I", *xyz, sign, *color, pack_uv(*uv), pack_unit(*n), pack_unit(*t, 0))


def surface_header(flags, verts, tris, rigid, subdiv, counts, ptrs):
    """ptrs: XSurface pointer fields by offset (absent: 0)."""
    h = bytearray(X.XSURFACE_SIZE)
    struct.pack_into("<HHHBB8h", h, 0, flags, verts, tris, rigid, subdiv, *counts)
    for off, v in ptrs.items():
        struct.pack_into("<Q", h, off, v)
    struct.pack_into("<I8i", h, 0xC0, 77, -(1 << 31), 0, 0, 0, 0, 0, 0, 5)
    return bytes(h)


class Model:
    """A small XModel zone: 3 bones (1 root), LOD 0 with two surfaces (rigid with a collision tree; blended with a
    GPU blend table, tension data and one subdivision level), aliased materials, a PhysPreset and a PhysCollmap with
    one brush. The bytes are appended in the order the Store loaders read them (docs/assets/models.md)."""

    MATERIAL_SLOTS = 0x100   # in block 4: two Material pointers the handles alias

    def __init__(self):
        z = bytearray()
        # XModel header
        h = bytearray(X.XMODEL_SIZE)
        struct.pack_into("<Q4Bf8I", h, 0, INLINE, 3, 1, 2, 0, 1.0, *range(8))
        for off in (0x30, 0x38, 0x40, 0x48, 0x50, 0x58):
            struct.pack_into("<Q", h, off, INLINE)
        struct.pack_into("<Q", h, 0x68, 1)                       # materialHandles: inline (any non-zero)
        struct.pack_into("<fHHQ", h, 0x70, 500.0, 0, 0, INLINE)   # LOD 0: its XModelSurfs follows
        struct.pack_into("<bbbB", h, 0x1F0, 0, 1, -1, 0x41)
        struct.pack_into("<Q", h, 0x208, 9)                       # boneInfo: inline
        struct.pack_into("<f6f", h, 0x210, 42.0, 1, 2, 3, 4, 5, 6)
        struct.pack_into("<Q", h, 0x230, 1)                       # the Store-only array: inline
        struct.pack_into("<QQf", h, 0x240, INLINE, INLINE, 1.0)
        z += h
        z += b"test_model_ab\0"                                   # name (XString), 14 bytes
        z += struct.pack("<3I", 11, 12, 13)                       # boneNames
        z += bytes([1, 1])                                        # parentList: bone1 -> 0, bone2 -> 1
        self.quats = [(0, 0, 0, 32767), (0, 0, 23170, 23170)]     # bone 2: 90 degrees about z
        z += b"".join(struct.pack("<4h", *q) for q in self.quats)
        self.trans = [(10.0, 0.0, 0.0), (5.0, 0.0, 0.0)]
        z += b"".join(struct.pack("<3f", *t) for t in self.trans)
        z += bytes([2, 3, 4])                                     # partClassification: head, neck, torso_upper
        r = math.sqrt(0.5)
        self.base = [((0, 0, 0, 1), (0, 0, 0)), ((0, 0, 0, 1), (10, 0, 0)), ((0, 0, r, r), (15, 0, 0))]
        z += b"".join(struct.pack("<8f", *q, *t, 2.0) for q, t in self.base)
        z += struct.pack("<2Q", 4 << 32 | (self.MATERIAL_SLOTS + 1), 4 << 32 | (self.MATERIAL_SLOTS + 9))
        # LOD 0: XModelSurfs header (read into the temp block), name, 2 XSurface headers
        z += struct.pack("<QQH2x8i4x", INLINE, INLINE, 2, *([0x40000000] + [0] * 7))
        z += b"test_model_lod0\0"
        z += surface_header(0x2, 3, 1, 1, 0, [0] * 8, {0x18: INLINE, 0x20: INLINE, 0x40: INLINE, 0x68: INLINE})
        z += surface_header(0x6, 4, 1, 0, 1, [2, 1, 0, 0, 0, 0, 0, 0],   # 4 vertices, 3 of them blended
                            {0x18: INLINE, 0x20: INLINE, 0x48: INLINE, 0x50: INLINE, 0x80: 1, 0x88: INLINE,
                             0x90: INLINE})
        # surface 0: vertices, triangle, rigid list (bone 1) with its collision tree, lightmap UVs
        z += vertex((0, 0, 0)) + vertex((1, 0, 0), -1.0) + vertex((0, 1, 0))
        z += struct.pack("<3H", 0, 1, 2)
        z += struct.pack("<4HQ", 64, 3, 0, 1, INLINE)
        z += struct.pack("<3f3fI4xQI4xQ", 1, 2, 3, 0.5, 0.5, 0.5, 1, 1, 1, 1)
        z += struct.pack("<8H", 0, 0, 0, 100, 100, 100, 0, 1)
        z += struct.pack("<H", 0)
        z += struct.pack("<6f", 0, 0, 1, 0, 0, 1)
        # surface 1: vertices, triangle, blendVerts (2 one-bone, 1 two-bone), blend table, subdivision, tension
        z += vertex((0, 0, 5)) + vertex((1, 0, 5)) + vertex((0, 1, 5)) + vertex((1, 1, 5))
        z += struct.pack("<3H", 2, 1, 0)
        z += struct.pack("<5H", 0, 128, 64, 128, 16384)          # v0: bone1; v1: bone2; v2: bone1 .75, bone2 .25
        z += struct.pack("<16H", 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
        z += struct.pack("<16H", 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
        z += struct.pack("<16H", 1, 2, 0, 0, 0, 0, 0, 0, 16384, 0, 0, 0, 0, 0, 0, 2)
        z += bytes(32)                                            # v3: no bones
        info = bytearray(X.SUBDIVINFO_SIZE)
        struct.pack_into("<QI", info, 0, 1, 4)
        struct.pack_into("<I", info, 0x20, 0x1000)
        z += info
        level = bytearray(X.SUBDIVLEVEL_SIZE)
        struct.pack_into("<17I", level, 8, 1, 1, 0, 2, 0, 9, 1, 0, 0, 1, 0, 6, 1, 4, 1, 3, 0)
        for off in range(0x50, 0x98, 8):
            struct.pack_into("<Q", level, off, 1)
        z += level
        z += struct.pack("<6H", 0, 1, 2, 2, 1, 0)                 # faceIndices
        z += struct.pack("<16H", *range(16))                      # regularPatchIndices
        z += struct.pack("<I", 0x300)                             # regularPatchFlags
        z += struct.pack("<2I", 7, 8)                             # facePoints: 9 bytes rounded down to 8
        z += struct.pack("<2I", 9, 10)                            # edgePoints
        z += struct.pack("<I", 11)                                # vertexPoints: 6 bytes rounded down to 4
        z += struct.pack("<I", 12)                                # normals
        z += struct.pack("<I", 13)                                # transitionPoints
        z += struct.pack("<8f", *range(8))                        # regularPatchCones
        z += struct.pack("<3f", 0.1, 0.2, 0.3)                    # tensionData
        z += struct.pack("<64H", *range(64))                      # tensionAccumTable
        # back in Load_XModel: boneInfo, the Store-only array
        z += b"".join(struct.pack("<7f", *([i] * 6), 4.0) for i in range(3))
        z += struct.pack("<2H", 7, 8)
        # PhysPreset
        pp = bytearray(X.PHYSPRESET_SIZE)
        struct.pack_into("<Qi5fQ8f2i2?", pp, 0, INLINE, 1, 2.0, 0.5, 0.25, 1, 1, INLINE, *([0.0] * 8), 0, 1, True, False)
        z += pp + b"preset\0" + b"snd_prefix\0"
        # PhysCollmap with one brush geom (2 sides)
        cm = bytearray(X.PHYSCOLLMAP_SIZE)
        struct.pack_into("<QI4xQ", cm, 0, INLINE, 1, 1)
        z += cm + b"collmap\0"
        geom = bytearray(X.PHYSGEOMINFO_SIZE)
        struct.pack_into("<Qi", geom, 0, 1, 3)
        z += geom
        wrapper = bytearray(X.BRUSHWRAPPER_SIZE)
        struct.pack_into("<HH4xQQ", wrapper, 0x18, 2, 0, 1, 1)
        struct.pack_into("<i4xQ", wrapper, 0x48, 3, INLINE)
        z += wrapper
        z += struct.pack("<QHBB4x", INLINE, 1, 0, 2) + struct.pack("<QHBB4x", 0x400000001, 2, 1, 1)
        z += struct.pack("<4fB3x", 1, 0, 0, 8, 0)                 # side 0's plane
        z += bytes([0, 1, 0])                                     # baseAdjacentSide (totalEdgeCount 3)
        z += struct.pack("<4fB3x", 1, 0, 0, 8, 0) + struct.pack("<4fB3x", -1, 0, 0, 8, 0)
        self.zone = bytes(z)

    def load(self):
        s = SynthStream(self.zone)
        mats = s.bases[4] + self.MATERIAL_SLOTS
        s.write(mats, struct.pack("<QQ", s.bases[4] + 0x1000, s.bases[4] + 0x2000))
        s.write(s.bases[4] + 0x1000, struct.pack("<Q", s.bases[4] + 0x1100))
        s.write(s.bases[4] + 0x1100, b",mtl_a\0")
        s.write(s.bases[4] + 0x2000, struct.pack("<Q", s.bases[4] + 0x2100))
        s.write(s.bases[4] + 0x2100, b"mtl_b\0")
        varptr = s.bases[6] + 0x10
        s.put_u64(varptr, INLINE)
        X.load_xmodel_ptr(s, varptr)
        return s, s.u64(varptr)


class SyntheticModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = Model()
        cls.s, cls.header = cls.built.load()
        names = {11: "tag_origin", 12: "j_a", 13: "j_b"}
        mem = X.Memory(cls.s)
        cls.model = X.read_xmodel(cls.s, cls.header, names.get, lambda p: mem.cstr(mem.q(p)))

    def test_whole_zone_consumed(self):
        self.assertEqual(self.s.cursor, len(self.built.zone))

    def test_memory_layout(self):
        """Where every array lands in the virtual block: the alignment rules, worked out by hand from the order."""
        s, h, v = self.s, self.header, self.s.bases[X.XFILE_BLOCK_VIRTUAL]
        q = s.u64
        self.assertEqual([q(h + off) - v for off in (0x00, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58, 0x68)],
                         [0, 16, 28, 30, 48, 72, 76, 176])
        surfs = q(q(h + 0x78) + 8)
        self.assertEqual(surfs - v, 208)
        s0, s1 = surfs, surfs + X.XSURFACE_SIZE
        rigid = q(s0 + 0x40)
        self.assertEqual([q(s0 + 0x18) - v, q(s0 + 0x20) - v, rigid - v, q(rigid + 8) - v, q(q(rigid + 8) + 0x20) - v,
                          q(q(rigid + 8) + 0x30) - v, q(s0 + 0x68) - v], [672, 768, 776, 792, 848, 864, 868])
        info = q(s1 + 0x80)
        level = q(info)
        self.assertEqual([q(s1 + 0x18) - v, q(s1 + 0x20) - v, q(s1 + 0x48) - v, q(s1 + 0x50) - v, info - v, level - v],
                         [896, 1024, 1030, 1040, 1168, 1224])
        self.assertEqual([q(level + off) - v for off in range(0x50, 0x98, 8)],
                         [1456, 1468, 1500, 1504, 1512, 1520, 1524, 1528, 1532])
        self.assertEqual([q(s1 + 0x88) - v, q(s1 + 0x90) - v, q(h + 0x208) - v, q(h + 0x230) - v], [1564, 1576, 1704, 1788])
        collmap = q(h + 0x248)
        wrapper = q(q(collmap + 0x10))
        self.assertEqual([q(collmap) - v, q(collmap + 0x10) - v, wrapper - v, q(wrapper + 0x20) - v,
                          q(wrapper + 0x28) - v, q(wrapper + 0x50) - v], [1810, 1820, 1892, 1980, 2032, 2036])
        self.assertEqual(s.pos[X.XFILE_BLOCK_VIRTUAL], 2076)
        self.assertEqual(s.pos[X.XFILE_BLOCK_TEMP], 0)   # the temp block is given back after the asset

    def test_links(self):
        self.assertEqual([t for t, _ in self.s.links],
                         [X.ASSET_XMODELSURFS, X.ASSET_PHYSPRESET, X.ASSET_PHYSCOLLMAP, X.ASSET_XMODEL])
        self.assertEqual(self.header, self.s.links[-1][1])

    def test_header(self):
        m = self.model
        self.assertEqual(m.name, "test_model_ab")
        self.assertEqual((m.scale, m.radius, m.bounds), (1.0, 42.0, (1, 2, 3, 4, 5, 6)))
        self.assertEqual((m.max_loaded_lod, m.coll_lod, len(m.lods)), (0, -1, 1))
        self.assertEqual(m.flags, 0x41)                       # flag 2 cleared, no default surfaces
        self.assertEqual(m.materials, [",mtl_a", "mtl_b"])
        self.assertEqual(m.unknown230, [7, 8])
        self.assertEqual(m.raw["noScalePartBits"], tuple(range(8)))

    def test_lod_fixups(self):
        lod = self.model.lods[0]
        self.assertEqual((lod.dist, lod.surf_index), (500.0, 0))
        self.assertEqual(lod.part_bits, (0x40000000, 0, 0, 0, 0, 0, 0, 0))   # Load_XModelSurfsFixup
        self.assertEqual(lod.surfs.name, "test_model_lod0")
        self.assertEqual(struct.unpack("<H", self.s.read(self.header + 0x74, 2))[0], 2)  # DB_XModelSurfsFixup
        self.assertEqual(self.s.read(self.header + 0xA, 1)[0], 2)

    def test_bones(self):
        b = self.model.bones
        self.assertEqual([x.name for x in b], ["tag_origin", "j_a", "j_b"])
        self.assertEqual([x.parent for x in b], [-1, 0, 1])
        self.assertEqual([x.hit_location for x in b], ["head", "neck", "torso_upper"])
        self.assertAlmostEqual(b[2].local_quat[2], 23170 / 32767)
        self.assertEqual(b[1].local_trans, (10.0, 0.0, 0.0))
        self.assertEqual(b[2].base_trans, (15.0, 0.0, 0.0))
        self.assertEqual(b[1].bounds, ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)))

    def test_rigid_surface(self):
        s0 = self.model.lods[0].surfs.surfaces[0]
        self.assertEqual((s0.vert_count, s0.tri_count, s0.triangles), (3, 1, [(0, 1, 2)]))
        self.assertEqual(s0.vertices[1].position, (1.0, 0.0, 0.0))
        self.assertEqual(s0.vertices[1].binormal_sign, -1.0)
        self.assertEqual(s0.vertices[0].color, (255, 128, 0, 255))
        self.assertEqual(s0.vertices[0].uv, (0.25, 0.75))
        n, w = s0.vertices[0].normal, s0.vertices[0].normal_w
        self.assertLess(max(abs(n[0]), abs(n[1]), abs(n[2] - 1)), 2e-3)
        self.assertEqual(w, 1.0)
        self.assertEqual(s0.skin, [[(1, 1.0)]] * 3)
        rl = s0.rigid_vert_lists[0]
        self.assertEqual((rl.bone, rl.vert_count, rl.tri_count), (1, 3, 1))
        self.assertEqual(rl.collision_tree.nodes, [((0, 0, 0), (100, 100, 100), 0, 1)])
        self.assertEqual(rl.collision_tree.leafs, [0])
        self.assertEqual(s0.lmap_unwrap, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)])
        self.assertEqual((s0.vertex_lighting_index, s0.part_bits[0]), (77, -(1 << 31)))

    def test_blended_surface(self):
        s1 = self.model.lods[0].surfs.surfaces[1]
        self.assertEqual(s1.blend_verts, [0, 128, 64, 128, 16384])
        self.assertEqual(s1.skin, [[(0, 1.0)], [(2, 1.0)], [(1, 0.75), (2, 0.25)], []])
        self.assertEqual(s1.blend_table[2], ((1, 2, 0, 0, 0, 0, 0, 0), (16384, 0, 0, 0, 0, 0, 0), 2))
        for (bones, weights, count), sk in zip(s1.blend_table, s1.skin):
            self.assertEqual(count, len(sk))
        self.assertEqual([round(x, 6) for x in s1.tension_data], [0.1, 0.2, 0.3])
        self.assertEqual(s1.tension_accum_table[2], tuple(range(32, 48)))

    def test_subdivision(self):
        sd = self.model.lods[0].surfs.surfaces[1].subdiv
        self.assertEqual((sd["flags"], sd["cacheSize"]), (4, 0x1000))
        lv = sd["levels"][0]
        self.assertEqual(lv["faceIndices"], [0, 1, 2, 2, 1, 0])
        self.assertEqual(lv["regularPatchIndices"], list(range(16)))
        self.assertEqual((lv["regularPatchFlags"], lv["facePoints"], lv["edgePoints"]), ([0x300], [7, 8], [9, 10]))
        self.assertEqual((lv["vertexPoints"], lv["normals"], lv["transitionPoints"]), ([11], [12], [13]))
        self.assertEqual(lv["regularPatchCones"], [float(i) for i in range(8)])

    def test_gpu_handles_cleared(self):
        surfs = self.model.lods[0].surfs
        at = struct.unpack("<Q", self.s.read(self.s.u64(self.header + 0x78) + 8, 8))[0]
        for off in (0x28, 0x30, 0x38, 0x58, 0x60, 0x70, 0x78, 0x98, 0xA0, 0xA8, 0xB0, 0xB8):
            self.assertEqual(self.s.u64(at + off), 0)
        self.assertEqual(len(surfs.surfaces), 2)

    def test_physics(self):
        pp, cm = self.model.phys_preset, self.model.phys_collmap
        self.assertEqual((pp.name, pp.fields["sndAliasPrefix"], pp.fields["mass"]), ("preset", "snd_prefix", 2.0))
        self.assertEqual((pp.fields["pitchType"], pp.fields["tempDefaultToCylinder"]), (1, True))
        self.assertEqual((cm.name, len(cm.geoms), cm.geoms[0].type), ("collmap", 1, "brush"))
        br = cm.geoms[0].brush
        self.assertEqual(len(br["sides"]), 2)
        self.assertEqual(br["sides"][0]["plane"], (1.0, 0.0, 0.0, 8.0, 0))
        self.assertEqual(br["sides"][1]["plane"], (0.0, 0.0, 0.0, 0.0, 0))  # an offset: block 4 + 0 (zeroes)
        self.assertEqual(br["baseAdjacentSide"], [0, 1, 0])
        self.assertEqual([p[:4] for p in br["planes"]], [(1.0, 0.0, 0.0, 8.0), (-1.0, 0.0, 0.0, 8.0)])


class Gltf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s, header = Model().load()
        names = {11: "tag_origin", 12: "j_a", 13: "j_b"}
        mem = X.Memory(s)
        cls.model = X.read_xmodel(s, header, names.get, lambda p: mem.cstr(mem.q(p)))
        cls.doc, cls.bin = X.to_gltf(cls.model)

    def accessor(self, i):
        a = self.doc["accessors"][i]
        v = self.doc["bufferViews"][a["bufferView"]]
        comps = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        fmt = {5126: "f", 5123: "H", 5121: "B", 5125: "I"}[a["componentType"]]
        data = self.bin[v["byteOffset"]:v["byteOffset"] + v["byteLength"]]
        flat = struct.unpack("<%d%s" % (a["count"] * comps, fmt), data)
        return [flat[i:i + comps] for i in range(0, len(flat), comps)]

    def test_structure(self):
        d = self.doc
        self.assertEqual(d["asset"]["version"], "2.0")
        self.assertEqual(len(d["meshes"]), 1)
        self.assertEqual(len(d["skins"][0]["joints"]), 3)
        self.assertEqual([m["name"] for m in d["materials"]], [",mtl_a", "mtl_b"])
        for v in d["bufferViews"]:
            self.assertEqual(v["byteOffset"] % 4, 0)
            self.assertLessEqual(v["byteOffset"] + v["byteLength"], len(self.bin))
        json.dumps(d)

    def test_inverse_bind_matrices(self):
        ibm = self.accessor(self.doc["skins"][0]["inverseBindMatrices"])
        for bone, inv in zip(self.model.bones, ibm):
            bind = X._quat_to_matrix(bone.base_quat, bone.base_trans)
            prod = [sum(bind[k * 4 + r] * inv[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]
            for i, x in enumerate(prod):
                self.assertAlmostEqual(x, 1.0 if i % 5 == 0 else 0.0, places=5)

    def test_primitives(self):
        prims = self.doc["meshes"][0]["primitives"]
        self.assertEqual(len(prims), 2)
        for p in prims:
            self.assertEqual(self.accessor(p["indices"]), [(0,), (1,), (2,)] if p is prims[0] else [(2,), (1,), (0,)])
            for w in self.accessor(p["attributes"]["WEIGHTS_0"]):
                self.assertAlmostEqual(sum(w), 1.0, places=6)
            for t in self.accessor(p["attributes"]["TANGENT"]):
                self.assertIn(t[3], (1.0, -1.0))
        self.assertEqual(self.accessor(prims[1]["attributes"]["JOINTS_0"])[2], (1, 2, 0, 0))

    def test_glb(self):
        glb = X.write_glb(self.doc, self.bin)
        magic, version, length = struct.unpack_from("<III", glb, 0)
        self.assertEqual((magic, version, length), (0x46546C67, 2, len(glb)))
        jlen, jtype = struct.unpack_from("<II", glb, 12)
        self.assertEqual(jtype, 0x4E4F534A)
        doc = json.loads(glb[20:20 + jlen])
        self.assertEqual(doc["buffers"][0]["byteLength"], len(self.bin))


class Packing(unittest.TestCase):
    def test_unit_vec(self):
        self.assertEqual(X.unpack_unit_vec(0x3FF | 0x1FF << 10 | 0 << 20 | 3 << 30)[1], 1.0)
        v, w = X.unpack_unit_vec(0x3FF | 0 << 20)
        self.assertEqual((v[0], v[2], w), (1.0, -1.0, 0.0))

    def test_tex_coords(self):
        self.assertEqual(X.unpack_tex_coords(0x3C00 | 0x3800 << 16), (1.0, 0.5))

    def test_blend_skin_groups(self):
        skin = X.blend_skin((1, 0, 1, 0, 0, 0, 0, 0), [64, 0, 64, 32768, 128, 16384], [], 2)
        self.assertEqual(skin, [[(1, 1.0)], [(0, 0.25), (1, 0.5), (2, 0.25)]])


def _real_zones():
    folder = os.environ.get("IW6_FASTFILES")
    if not folder:
        return None, "IW6_FASTFILES is not set"
    try:
        import iw6ff  # noqa: F401  (tools/fastfile/iw6ff.py, the pipeline's reader)
    except ImportError:
        return None, "tools/fastfile/iw6ff.py (the pipeline's reader) is not present"
    names = os.environ.get("IW6_XMODEL_ZONES", "mp_head_aa_tr.ff").split(",")
    paths = [Path(folder) / n for n in names if (Path(folder) / n).exists()]
    return (paths, "") if paths else (None, f"none of {names} in {folder}")


class RealZones(unittest.TestCase):
    def test_xmodels(self):
        paths, why = _real_zones()
        if not paths:
            self.skipTest(why)
        import iw6ff
        X.register(iw6ff.ASSET_LOADERS)
        for path in paths:
            zone = iw6ff.read_fastfile(path.read_bytes(), path.stem)
            models = [a for a in zone.assets if a.type == X.ASSET_XMODEL and a.header]
            if not zone.complete and not models:
                self.skipTest(f"{path.name}: the walk stopped at asset {zone.stopped_at} (a type without a loader)")
            for a in models:
                m = X.read_xmodel(zone.stream, a.header)
                self.assertTrue(m.lods)
                for lod in m.lods:
                    for s in lod.surfs.surfaces:
                        self.assertTrue(all(i < s.vert_count for t in s.triangles for i in t))
                        self.assertTrue(all(abs(sum(w for _, w in sk) - 1) < 1e-6 for sk in s.skin))
                X.to_gltf(m)


if __name__ == "__main__":
    unittest.main()
