"""tools/fastfile/lightgrid.py on hand-built streams (no game data). The decoder is checked against the game's own
R_GetLightGrid by tests/fastfile/lightgrid_check.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import lightgrid as LG  # noqa: E402


class Writer:
    """Bits least significant first, as Com_BitStreamRead reads them."""

    def __init__(self):
        self.bits = []

    def put(self, value, n):
        self.bits += [(value >> i) & 1 for i in range(n)]

    def align(self):
        while len(self.bits) % 8:
            self.bits.append(0)

    def data(self):
        self.align()
        return bytes(sum(b << i for i, b in enumerate(self.bits[k:k + 8])) for k in range(0, len(self.bits), 8))


class BitStream(unittest.TestCase):
    def test_lsb_first_across_bytes(self):
        bs = LG.BitStream(bytes([0b10110100, 0b00000011]))
        self.assertEqual(bs.read(3), 0b100)
        self.assertEqual(bs.read(7), 0b1110110)   # 5 bits of byte 0, 2 of byte 1
        self.assertEqual(bs.bit_index, 10)
        bs.align()
        self.assertEqual(bs.bit_index, 16)

    def test_bit_count_for(self):
        self.assertEqual([LG.bit_count_for(n) for n in (0, 1, 2, 3, 4, 5, 16, 17)], [0, 1, 1, 2, 2, 3, 4, 5])


class Masks(unittest.TestCase):
    def test_index_mask(self):
        w = Writer()
        w.put(0, 1); w.put(0xBEEF, 16)                      # literal
        w.put(1, 1); w.put(9, 4); w.put(0, 1); w.put(0b0101, 4)   # code 9 = cells (1, 4, 3, 6): bits 0, 2
        w.put(1, 1); w.put(0, 4); w.put(1, 1); w.put(0b1111, 4)   # code 0 inverted: all but 0, 1, 4, 5
        bs = LG.BitStream(w.data())
        self.assertEqual(LG.decode_index_mask(bs), 0xBEEF)
        self.assertEqual(LG.decode_index_mask(bs), (1 << 1) | (1 << 3))
        self.assertEqual(LG.decode_index_mask(bs), 0xFFFF & ~0b110011)

    def test_voxel_mask(self):
        w = Writer()
        w.put(1, 2)                                        # all cells
        w.put(2, 2); w.put(15, 4); w.put(0b1000, 4)        # code 15: cell 15
        w.put(3, 2); w.put(15, 4); w.put(0b1000, 4)        # inverted
        bs = LG.BitStream(w.data())
        self.assertEqual(LG.decode_voxel_mask(bs), 0xFFFF)
        self.assertEqual(LG.decode_voxel_mask(bs), 1 << 15)
        self.assertEqual(LG.decode_voxel_mask(bs), 0x7FFF)


class Tree(unittest.TestCase):
    def one_block_tree(self, colors, voxel_hi):
        """Depth 0, one block at the origin: node format 0, one leaf of nonzero size; the block lists 16 colour
        values (command 0, stored + 1 as the encoding has 0 = none) and a high voxel mask."""
        w = Writer()
        w.put(0, 8)               # node format: no min / default / table
        w.put(1, 6)               # leafSize[0]
        w.align()
        w.put(0x04 | 0x80, 8)     # block format: colour commands, high voxel mask
        w.put(0, 2)               # command 0: all 16 values, 16 bits each
        for c in colors:
            w.put(c + 1, 16)
        w.put(0, 2); w.put(voxel_hi, 16)
        leaves = w.data()
        return LG.Tree(0, 1, 1, (0, 0, 0), (3, 3, 0), (2, 2, 1), 16, 8, ((0x01 << 24) | 0,), leaves)

    def test_block(self):
        colors = [100 + i for i in range(16)]
        tree = self.one_block_tree(colors, 0x8001)
        for y in range(4):
            for x in range(4):
                cell = LG.CELL_ORDER[x + 4 * y]
                ci, li, vox = LG.get_light_grid(tree, (x, y, 0))
                self.assertEqual(ci, colors[cell])
                self.assertEqual(li, 0)
                self.assertEqual(vox, 2 if cell in (0, 15) else 0)

    def test_outside_and_empty(self):
        tree = self.one_block_tree([1] * 16, 0)
        self.assertEqual(LG.get_light_grid(tree, (4, 0, 0)), (0, 0, 0))
        empty = LG.Tree(0, 1, 0, (0, 0, 0), (7, 7, 1), (4, 4, 1), 16, 8, ((0x01 << 24),), b"")
        self.assertEqual(LG.get_light_grid(empty, (5, 5, 1)), (0, 0, 0))   # child 7 not in the mask


class RealMaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.maps = [p for p in sorted(Path(folder).glob("mp_*.ff")) if p.stat().st_size > 20 << 20]
        if not cls.maps:
            raise unittest.SkipTest("no map zone in IW6_FASTFILES")

    def test_reader_equals_game(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import lightgrid_check
        for path in self.maps:
            diffs, cells = lightgrid_check.compare(path.read_bytes(), path.stem, blocks=200)
            self.assertGreater(cells, 0, path.name)
            self.assertEqual(diffs, [], path.name)


if __name__ == "__main__":
    unittest.main()
