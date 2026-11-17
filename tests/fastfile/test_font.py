"""tools/fastfile/font.py: the Font_s loader on a small hand-made stream, and the glyph reader. No game data is part of
this file."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import font  # noqa: E402
import iw6ff  # noqa: E402
from test_zone import FOLLOWING, stream  # noqa: E402


class Loader(unittest.TestCase):
    def test_font_with_inline_glyphs(self):
        materials = []
        font.HOOKS["material_ptr"] = lambda s, at: materials.append(s.u64(at))
        try:
            h = struct.pack("<QiiQQQ", FOLLOWING, 35, 2, 0, 0, FOLLOWING)
            glyphs = (struct.pack("<HbbBBBx4f", ord("A"), 1, -20, 18, 16, 22, 0.0, 0.0, 0.5, 0.25)
                      + struct.pack("<HbbBBBx4f", 0xE9, 0, -21, 15, 14, 23, 0.5, 0.0, 1.0, 0.25))
            zone = h + b"fonts/test\0" + glyphs
            s, slot = stream(zone)
            font.load_font_ptr(s, slot)
            self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
            self.assertEqual(materials, [0, 0])                 # material, then glow material
            f = font.read_font(s, s.u64(slot))
            self.assertEqual((f.name, f.pixel_height, len(f.glyphs)), ("fonts/test", 35, 2))
            g = f.glyphs[0]
            self.assertEqual((chr(g.letter), g.x0, g.y0, g.dx, g.width, g.height), ("A", 1, -20, 18, 16, 22))
            self.assertEqual((g.s1, g.t1), (0.5, 0.25))
            self.assertEqual(f.glyphs[1].letter, 0xE9)
        finally:
            font.HOOKS["material_ptr"] = None


if __name__ == "__main__":
    unittest.main()
