"""Tests of tools/fastfile/gfxworld.py.

Synthetic: small GfxWorlds built here check the loader's consumption and pointer rules, the Umbra tome check, the
reader and the glTF export. Real: with IW6_FASTFILES (a folder of .ff files) and IW6_ORIGINALS set, every map zone
in the folder (a zone whose name starts with mp_ and is larger than 20 MB) is loaded by the Store build's own code
in the emulator, and the reader must load its GfxWorld to exactly the game's state (world_check.py). No game data is
part of this file.
"""
import os
import struct
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import gfxworld as G  # noqa: E402
import iw6ff  # noqa: E402

INLINE = G.PTR_INLINE


def stream_for(zone_bytes):
    s = iw6ff.Stream(bytes(iw6ff.XFILE_SIZE) + zone_bytes, [1 << 22] * 7)
    s.push(iw6ff.XFILE_BLOCK_VIRTUAL)
    slot = s.align(8)
    s.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
    return s, slot


def header(**fields):
    h = bytearray(G.GFXWORLD_SIZE)
    struct.pack_into("<Q", h, 0, INLINE)                 # name
    struct.pack_into("<Q", h, 8, INLINE)                 # baseName
    for off, fmt, value in fields.values():
        struct.pack_into(fmt, h, off, *value) if isinstance(value, tuple) else struct.pack_into(fmt, h, off, value)
    return bytes(h)


class Loader(unittest.TestCase):
    def test_empty_world(self):
        zone = header() + b"maps/mp/x.d3dbsp\0x\0"
        s, slot = stream_for(zone)
        s.put_u64(slot, INLINE)
        G.load_gfx_world_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        w = s.u64(slot)
        self.assertEqual(s.links, [(G.ASSET_GFXWORLD, w)])
        info = G.read_world(s, w)
        self.assertEqual((info.name, info.base_name, info.vertex_count, info.surfaces), ("maps/mp/x.d3dbsp", "x", 0, []))

    def test_vertices_indices_and_runtime_arrays(self):
        verts = b"".join(struct.pack("<4f4B4fII", i, 2 * i, 3 * i, 1, 255, 128, 0, 255, 0.5, 0.25, 0, 0,
                                     0x1FF7FDFF, 0) for i in range(3))
        h = header(vc=(0x88 + 0x6C, "<I", 3), vp=(0x88 + 0x70, "<Q", 1), ic=(0x88 + 0x98, "<I", 3),
                   ip=(0x88 + 0xA0, "<Q", 1), cells=(0x50, "<i", 2), bits=(0x848, "<Q", 1))
        zone = h + b"n\0b\0" + verts + struct.pack("<3H", 0, 1, 2)
        s, slot = stream_for(zone)
        s.put_u64(slot, INLINE)
        before = s.pos[iw6ff.XFILE_BLOCK_RUNTIME]
        G.load_gfx_world_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        # cellCasterBits: ((2 + 31) >> 5) * 2 words in the runtime block, nothing read from the zone
        self.assertEqual(s.pos[iw6ff.XFILE_BLOCK_RUNTIME] - before, 8)
        info = G.read_world(s, s.u64(slot))
        self.assertEqual(info.indices, [0, 1, 2])
        p, sign, color, uv, lmap, n, t = G.world_vertex(info.vertices, 2)
        self.assertEqual((p, uv, bytes(color)), ((2.0, 4.0, 6.0), (0.5, 0.25), bytes((255, 128, 0, 255))))

    def test_planes_offset_is_converted(self):
        h = header(planes=(0x58, "<Q", (1 << 32) | 0x11), cells=(0x50, "<i", 0))
        zone = h + b"n\0b\0"
        s, slot = stream_for(zone)
        s.put_u64(slot, INLINE)
        G.load_gfx_world_ptr(s, slot)
        w = s.u64(slot)
        self.assertEqual(s.u64(w + 0x58), s.bases[1] + 0x10)   # DB_ConvertOffsetToPointer: block 1, offset 0x10


class Umbra(unittest.TestCase):
    def test_tome_check(self):
        good = struct.pack("<III", 0xD6000012, 0, 64) + bytes(4)
        self.assertEqual(G.umbra_tome(good, 0x1000, 64), 0)
        self.assertEqual(G.umbra_tome(good, 0x1008, 64), 6)                     # not 16-byte aligned
        self.assertEqual(G.umbra_tome(good, 0x1000, 32), 7)                     # larger than the data
        self.assertEqual(G.umbra_tome(struct.pack("<I", 0xD6000013) + bytes(12), 0x1000, 64), 4)
        self.assertEqual(G.umbra_tome(struct.pack("<I", 0x120000D6) + bytes(12), 0x1000, 64), 5)   # the other byte order
        self.assertEqual(G.umbra_tome(bytes(16), 0, 0), 1)


class Gltf(unittest.TestCase):
    def test_export(self):
        verts = b"".join(struct.pack("<4f4B4fII", x, y, 0, 1, 255, 255, 255, 255, 0, 0, 0, 0, 0x1FF7FDFF, 0)
                         for x, y in ((0, 0), (1, 0), (0, 1)))
        world = G.GfxWorldInfo("w", "w", verts, 3, [0, 1, 2], [G.WorldSurface("mtl", 0, 3, 1, 0, 0, 0)],
                               [G.StaticModel("m", (1, 2, 3), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), 2.0, 0, -1, 0)],
                               1, [], [], [], (), ("", ""), 0, 0)
        doc, binary = G.to_gltf(world)
        self.assertEqual([m["name"] for m in doc["materials"]], ["mtl"])
        self.assertEqual(doc["nodes"][2]["matrix"][12:15], [1, 2, 3])
        self.assertEqual(doc["nodes"][2]["matrix"][0], 2.0)
        self.assertEqual(doc["accessors"][doc["meshes"][0]["primitives"][0]["indices"]]["count"], 3)


class RealMaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.maps = [p for p in sorted(Path(folder).glob("mp_*.ff")) if p.stat().st_size > 20 << 20]
        if not cls.maps:
            raise unittest.SkipTest("no map zone in IW6_FASTFILES")

    def test_reader_equals_game(self):
        import world_check
        for path in self.maps:
            diffs, _ = world_check.compare(path.read_bytes(), path.stem)
            self.assertEqual(diffs, [], path.name)


if __name__ == "__main__":
    unittest.main()
