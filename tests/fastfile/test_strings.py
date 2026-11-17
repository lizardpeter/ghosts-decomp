"""tools/fastfile/strings.py: StringTable and LocalizeEntry loaders on small hand-made streams, the game's string
hash, the lookups and CSV output. With IW6_FASTFILES, a real zone's tables. No game data is part of this file."""
import os
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import iw6ff  # noqa: E402
import strings  # noqa: E402
from test_zone import FOLLOWING, stream  # noqa: E402


class Hash(unittest.TestCase):
    def test_case_insensitive_times_31(self):
        self.assertEqual(strings.string_hash("ab"), ord("a") * 31 + ord("b"))
        self.assertEqual(strings.string_hash("SNOW"), strings.string_hash("snow"))
        self.assertEqual(strings.string_hash(""), 0)

    def test_high_bytes_are_signed_chars(self):
        self.assertEqual(strings.string_hash(b"\xe9"), -23)
        self.assertEqual(strings.string_hash(b"a\xe9"), 97 * 31 - 23)

    def test_wraps_to_32_bit_signed(self):
        h = strings.string_hash("z" * 20)
        self.assertTrue(-(1 << 31) <= h < (1 << 31))


class Loaders(unittest.TestCase):
    def test_string_table(self):
        h = struct.pack("<QiiQ", FOLLOWING, 2, 2, FOLLOWING)
        cells = b"".join(struct.pack("<Qi4x", FOLLOWING if s else 0, strings.string_hash(s or ""))
                         for s in ("0", "snow", "1", None))
        zone = h + b"mp/t.csv\0" + cells + b"0\0snow\0" + b"1\0"
        s, slot = stream(zone)
        strings.load_string_table_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))            # alignment takes no zone bytes
        t = strings.read_string_table(s, s.u64(slot))
        self.assertEqual((t.name, t.columns, t.rows), ("mp/t.csv", 2, 2))
        self.assertEqual(t.cells, [["0", "snow"], ["1", None]])
        self.assertEqual(t.bad_hashes, 0)
        self.assertEqual(t.value(1, 1), "")
        self.assertEqual(t.value(0, 5), "")
        self.assertEqual(t.find_row(1, "SNOW"), 0)
        self.assertEqual(t.find_row(1, "brush"), -1)
        self.assertEqual(strings.to_csv(t), "0,snow\n1,\n")

    def test_localize(self):
        zone = struct.pack("<QQ", FOLLOWING, FOLLOWING) + b"Head shot\0CGAME_HEAD_SHOT\0"
        s, slot = stream(zone)
        strings.load_localize_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        self.assertEqual(strings.read_localize(s, s.u64(slot)), ("CGAME_HEAD_SHOT", "Head shot"))


class RealZone(unittest.TestCase):
    def test_extinction_tables(self):
        folder = os.environ.get("IW6_FASTFILES")
        zone = Path(folder or ".") / "english" / "eng_common_alien_mp.ff"
        if not folder or not zone.exists():
            self.skipTest("needs english/eng_common_alien_mp.ff in IW6_FASTFILES")
        import loaders
        loaders.register_all()
        z = iw6ff.read_fastfile(zone.read_bytes(), zone.stem)
        self.assertTrue(z.complete)
        tables = [strings.read_string_table(z.stream, a.header) for a in z.assets
                  if a.type == strings.ASSET_STRINGTABLE and a.header]
        self.assertGreater(len(tables), 5)
        for t in tables:
            self.assertEqual(t.bad_hashes, 0, t.name)
            self.assertTrue(t.name.endswith(".csv"))


if __name__ == "__main__":
    unittest.main()
