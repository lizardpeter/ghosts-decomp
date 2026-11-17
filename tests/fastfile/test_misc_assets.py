"""tools/fastfile/misc_assets.py: Lua files, leaderboards, vector fields and vehicle tracks on small hand-made streams,
and, with IW6_FASTFILES, the Lua files of patch_code_post_gfx.ff and the leaderboards of code_post_gfx_mp.ff. No
game data is part of this file."""
import os
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import iw6ff  # noqa: E402
import misc_assets as misc  # noqa: E402
from test_zone import FOLLOWING, stream  # noqa: E402


def _walk(type_, zone):
    s, slot = stream(zone)
    misc.PTRS[type_](s, slot)
    return s, s.u64(slot)


class Loaders(unittest.TestCase):
    def test_lua_file(self):
        zone = struct.pack("<QiiQ", FOLLOWING, 5, 0, 1) + b"ui/a.lua\0" + b"\x1bLuaQ"
        s, h = _walk(0x36, zone)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        self.assertEqual(misc.read_lua_file(s, h), ("ui/a.lua", b"\x1bLuaQ"))
        self.assertEqual(s.u64(h + 0x10) % 16, 0)                         # the chunk is aligned to 16

    def test_leaderboard(self):
        h = bytearray(0x28)
        struct.pack_into("<Q", h, 0, FOLLOWING)
        struct.pack_into("<i", h, 0xC, 2)
        struct.pack_into("<Q", h, 0x18, 1)
        cols = bytearray(0x70)
        for i in range(2):
            struct.pack_into("<Q", cols, 0x38 * i, FOLLOWING)
            struct.pack_into("<Q", cols, 0x38 * i + 0x18, FOLLOWING)
        zone = bytes(h) + b"LB_TEST\0" + bytes(cols) + b"Rank\0rank\0Score\0score\0"
        s, a = _walk(0x2F, zone)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        self.assertEqual(misc.read_name(s, a), "LB_TEST")
        self.assertEqual(misc.read_leaderboard_columns(s, a), ["Rank", "Score"])

    def test_vector_field(self):
        h = bytearray(0x50)
        struct.pack_into("<QQ", h, 0, FOLLOWING, FOLLOWING)
        struct.pack_into("<3i", h, 0x34, 2, 3, 1)
        zone = bytes(h) + b"wind\0" + bytes(range(6 * 16))
        s, a = _walk(0x3C, zone)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        self.assertEqual(s.read(s.u64(a + 8), 96), bytes(range(96)))

    def test_vehicle_track_with_a_nested_segment(self):
        h = struct.pack("<QQi4x", FOLLOWING, FOLLOWING, 1)
        seg = bytearray(0x48)
        struct.pack_into("<QQI", seg, 0, FOLLOWING, 1, 1)                 # name, one sector
        struct.pack_into("<Qi", seg, 0x18, 1, 1)                          # one next segment
        sector = bytearray(0x48)
        struct.pack_into("<QI", sector, 0x38, 1, 2)                       # two obstacles
        nested = bytearray(0x48)
        struct.pack_into("<Q", nested, 0, FOLLOWING)
        zone = (h + b"track\0" + bytes(seg) + b"seg0\0" + bytes(sector) + bytes(24)
                + struct.pack("<Q", FOLLOWING) + bytes(nested) + b"seg1\0")
        s, a = _walk(0x17, zone)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        seg0 = s.u64(a + 8)
        nxt = s.u64(s.u64(seg0 + 0x18))
        self.assertEqual((misc.read_name(s, seg0), misc.read_name(s, nxt)), ("seg0", "seg1"))


class RealZone(unittest.TestCase):
    def _zone(self, name):
        folder = os.environ.get("IW6_FASTFILES")
        zone = Path(folder or ".") / name
        if not folder or not zone.exists():
            self.skipTest(f"needs {name} in IW6_FASTFILES")
        import loaders
        loaders.register_all()
        z = iw6ff.read_fastfile(zone.read_bytes(), zone.stem)
        self.assertTrue(z.complete)
        return z

    def test_ui_lua(self):
        z = self._zone("patch_code_post_gfx.ff")
        chunks = dict(misc.read_lua_file(z.stream, a.header) for a in z.assets if a.type == 0x36)
        self.assertIn("ui/lui/lui.lua", chunks)
        self.assertTrue(all(c.startswith(b"\x1bLua") for c in chunks.values()))

    def test_leaderboards(self):
        z = self._zone("code_post_gfx_mp.ff")
        boards = {misc.read_name(z.stream, a.header): a.header for a in z.assets if a.type == 0x2F}
        self.assertEqual(misc.read_leaderboard_columns(z.stream, boards["DEFAULT_LB"]), ["Rank", "Gamer Name"])


if __name__ == "__main__":
    unittest.main()
