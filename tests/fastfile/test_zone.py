"""Whole zones: tools/fastfile/loaders.py's loaders walk every asset of a zone, and the result equals the zone as the
game loaded it (tests/fastfile/zone_check.py, with IW6_FASTFILES and IW6_ORIGINALS). Also small hand-made streams for
the loaders of postfx.py and mapfx.py. No game data is part of this file."""
import os
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import iw6ff  # noqa: E402
import mapfx  # noqa: E402
import postfx  # noqa: E402

FOLLOWING = 0xFDFDFDFFFFFFFFFF


def stream(zone: bytes):
    s = iw6ff.Stream(bytes(iw6ff.XFILE_SIZE) + zone, [1 << 20] * 7)
    s.push(iw6ff.XFILE_BLOCK_VIRTUAL)
    slot = s.align(8)
    s.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
    s.put_u64(slot, FOLLOWING)
    return s, slot


class Loaders(unittest.TestCase):
    def test_colorization_set_with_inline_colorizations(self):
        materials = []
        postfx.HOOKS["material_ptr"] = lambda s, at: materials.append(s.u64(at))
        try:
            col = struct.pack("<10f", *range(10)) + struct.pack("<Q", FOLLOWING)    # name last
            h = bytearray(0x68)
            struct.pack_into("<Q", h, 0, FOLLOWING)
            struct.pack_into("<4f", h, 8, 0.1, 0.2, 0.3, 0.4)
            struct.pack_into("<QQ", h, 0x30, FOLLOWING, 0)                          # one colorization, one null
            h[0x60] = 5
            zone = bytes(h) + b"set\0" + col + b"grade\0"
            s, slot = stream(zone)
            postfx.load_colorization_set_ptr(s, slot)
            self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
            cs = postfx.read_colorization_set(s, s.u64(slot))
            self.assertEqual((cs.name, cs.flags, cs.colorization.name), ("set", 5, "grade"))
            self.assertEqual(cs.colorization.scale, (4.0, 5.0, 6.0))
            self.assertIsNone(cs.alternate)
            self.assertEqual(materials, [0])
        finally:
            postfx.HOOKS["material_ptr"] = None

    def test_glass_world(self):
        h = struct.pack("<QQ", FOLLOWING, 1)                    # name, g_glassData (any non-null: inline)
        data = bytearray(0x90)
        struct.pack_into("<QI", data, 0, 1, 2)                  # two pieces
        struct.pack_into("<I", data, 0x10, 1)                   # one name
        struct.pack_into("<Q", data, 0x18, 1)
        name = bytearray(0x18)
        struct.pack_into("<QIHH", name, 0, FOLLOWING, 0, 3, 0)
        struct.pack_into("<Q", name, 0x10, 1)
        s_table = struct.pack("<Q", 0x1234)
        zone = h + b"glass\0" + bytes(data) + bytes(0x18) + bytes(name) + b"win\0" + struct.pack("<3H", 4, 5, 6)
        s, slot = stream(zone)
        s.string_table = s.addr()                               # a one-entry script string table
        s.write(s.string_table, s_table)
        s.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
        mapfx.load_glass_world_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        g = s.u64(slot)
        d = s.u64(g + 8)
        n = s.u64(d + 0x18)
        self.assertEqual(s.cstr(s.u64(n)), b"win")
        self.assertEqual(s.u32(n + 8), 0x1234)
        self.assertEqual(struct.unpack("<3H", s.read(s.u64(n + 0x10), 6)), (4, 5, 6))


class WholeZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.zone = Path(folder) / "common_alien_mp.ff"
        if not cls.zone.exists():
            raise unittest.SkipTest("no common_alien_mp.ff in IW6_FASTFILES")

    def test_common_alien_mp_equals_game(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import zone_check
        diffs, z = zone_check.full(self.zone.read_bytes(), self.zone.stem)
        self.assertTrue(z.complete)
        self.assertEqual(diffs, [])


if __name__ == "__main__":
    unittest.main()
