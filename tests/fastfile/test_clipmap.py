"""tools/fastfile/clipmap.py: the readers on hand-made data, and the loader against the game on real maps
(tests/fastfile/clipmap_check.py, with IW6_FASTFILES and IW6_ORIGINALS)."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import clipmap as CM  # noqa: E402


class Entities(unittest.TestCase):
    def test_parse(self):
        text = '{\n"classname" "worldspawn"\n"sunlight" "1.2"\n}\n{\n"classname" "mp_tdm_spawn"\n"origin" "1 2 3"\n}\n'
        self.assertEqual(CM.parse_entity_string(text),
                         [{"classname": "worldspawn", "sunlight": "1.2"},
                          {"classname": "mp_tdm_spawn", "origin": "1 2 3"}])

    def test_pc_numeric_keys(self):
        text = '{\n97 "worldspawn"\n0 "aomindist" "16"\n34185 "1"\n430 "0 0 0"\n}\n'
        self.assertEqual(CM.parse_entity_string(text),
                         [{"classname": "worldspawn", "aomindist": "16", "#34185": "1", "origin": "0 0 0"}])


class Brushes(unittest.TestCase):
    def test_box(self):
        b = CM.Brush((0, 0, 0), (2, 4, 8), [], 1, [])
        faces = CM.brush_faces(b)
        self.assertEqual(len(faces), 6)
        for poly, _ in faces:
            self.assertEqual(len(poly), 4)
            for p in poly:
                for k, (lo, hi) in enumerate(zip(b.mins, b.maxs)):
                    self.assertTrue(lo - 1e-3 <= p[k] <= hi + 1e-3)

    def test_cut_corner(self):
        # a unit cube cut by x + y <= 1: a prism with a triangular cross-section
        n = (2 ** -0.5, 2 ** -0.5, 0.0)
        b = CM.Brush((0, 0, 0), (1, 1, 1), [(n, 2 ** -0.5)], 1, [0])
        faces = CM.brush_faces(b)
        tags = sorted(t for _, t in faces)
        self.assertEqual(tags, [-6, -5, -3, -1, 0])          # +x and +y faces are cut away entirely
        top = next(p for p, t in faces if t == -6)
        self.assertEqual(len(top), 3)


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
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import clipmap_check
        for path in self.maps:
            diffs, _ = clipmap_check.compare(path.read_bytes(), path.stem)
            self.assertEqual(diffs, [], path.name)


if __name__ == "__main__":
    unittest.main()
