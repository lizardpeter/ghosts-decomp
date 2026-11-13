"""Tests of tools/fastfile/image.py (GfxImage loaders, stream-level assembly, DDS) and tools/fastfile/bcn.py.

Synthetic streams check that the loaders consume the zone as the Store build's Load_GfxImagePtr / Load_GfxImage /
Load_GfxTextureLoad / Load_ImageStream do (those are differential-tested against the exe:
tests/differential/test_image_load.py). Real zones: with IW6_FASTFILES set (a folder of .ff files, optionally
with imagefile<N>.pak files), every image of every zone the readers can walk is checked against the invariants in
docs/assets/images.md; otherwise those tests skip. No game data is part of this file.
"""
import os
import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))

import bcn  # noqa: E402
import image as I  # noqa: E402
import iw6ff  # noqa: E402

FOLLOWING, INSERT = I.PTR_INLINE, I.PTR_INSERT


def header(name_ptr=FOLLOWING, pixels_ptr=FOLLOWING, fmt=71, map_type=I.MAPTYPE_2D, semantic=2,
           flags=0, card=0, w=8, h=8, depth=1, elements=1, levels=1, streaming=0, stream_levels=()):
    b = bytearray(I.GFX_IMAGE_SIZE)
    struct.pack_into("<IBBBBBBB", b, 0x18, fmt, map_type, semantic, 3, flags, 0, 0, 0)
    struct.pack_into("<ii", b, 0x24, card, card)
    struct.pack_into("<HHHHBB", b, 0x2C, w, h, depth, elements, levels, streaming)
    struct.pack_into("<Q", b, 0x38, pixels_ptr)
    for k, (lw, lh, lc, lcount) in enumerate(stream_levels):
        struct.pack_into("<HHI", b, 0x40 + 8 * k, lw, lh, (lcount << 26) | lc)
    struct.pack_into("<Q", b, 0x60, name_ptr)
    return bytes(b)


def stream_for(zone_bytes, rows=()):
    s = iw6ff.Stream(bytes(iw6ff.XFILE_SIZE) + zone_bytes, [1 << 20] * 7)  # the stream starts after the XFile
    I.state_of(s).rows = list(rows)
    s.push(iw6ff.XFILE_BLOCK_VIRTUAL)
    slot = s.align(8)
    s.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
    return s, slot


class Row:
    def __init__(self, path, offset, end):
        self.path, self.offset, self.end = path, offset, end


class Loaders(unittest.TestCase):
    def test_inline_image_with_pixels(self):
        pixels = bytes(range(32))
        zone = header(card=len(pixels), semantic=2) + b"tex\0" + pixels
        s, slot = stream_for(zone)
        s.put_u64(slot, FOLLOWING)
        I.load_gfx_image_ptr(s, slot)
        st = I.state_of(s)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        linked = s.u64(slot)
        self.assertEqual(st.order, [linked])
        self.assertEqual(st.pixels_by_link[linked], pixels)
        info = I.read_image(s, linked)
        self.assertEqual((info.name, info.format_name, info.width, info.streamed), ("tex", "BC1_UNORM", 8, False))

    def test_water_image_has_one_byte(self):
        zone = header(card=4096, semantic=I.TS_WATER_MAP) + b"water\0" + b"\x77"
        s, slot = stream_for(zone)
        s.put_u64(slot, FOLLOWING)
        I.load_gfx_image_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        self.assertEqual(I.state_of(s).pixels_by_link[s.u64(slot)], b"\x77")

    def test_streamed_image_takes_four_rows(self):
        rows = [Row("imagefile1.pak", 16 * k, 16 * k + 8) for k in range(8)]
        zone = header(pixels_ptr=0, streaming=1, w=1, h=1, stream_levels=[(4, 4, 8, 3), (8, 8, 40, 4)]) + b"a\0"
        zone += header(pixels_ptr=0, streaming=1, w=1, h=1) + b"b\0"
        s, slot = stream_for(zone, rows)
        s.put_u64(slot, FOLLOWING)
        I.load_gfx_image_ptr(s, slot)
        first = s.u64(slot)
        s.put_u64(slot, FOLLOWING)
        I.load_gfx_image_ptr(s, slot)
        st = I.state_of(s)
        self.assertEqual(st.cursor, 8)
        self.assertEqual(st.streams[first], rows[:4])
        self.assertEqual(st.streams[s.u64(slot)], rows[4:])

    def test_not_streamed_takes_no_rows(self):
        zone = header(pixels_ptr=0) + b"c\0"
        s, slot = stream_for(zone, [Row("imagefile1.pak", 0, 1)] * 4)
        s.put_u64(slot, FOLLOWING)
        I.load_gfx_image_ptr(s, slot)
        self.assertEqual(I.state_of(s).cursor, 0)

    def test_alias_and_null(self):
        s, slot = stream_for(b"")
        s.put_u64(slot, 0)
        I.load_gfx_image_ptr(s, slot)
        self.assertEqual(s.u64(slot), 0)
        self.assertEqual(I.state_of(s).order, [])

    def test_insert_fills_the_slot(self):
        zone = header(pixels_ptr=0) + b"d\0"
        s, slot = stream_for(zone)
        s.put_u64(slot, INSERT)
        I.load_gfx_image_ptr(s, slot)
        self.assertEqual(s.u64(s.inserts[0]), s.u64(slot))


class Layout(unittest.TestCase):
    def test_level_sizes(self):
        self.assertEqual(I.level_size(71, 1024, 1024), 524288)          # BC1
        self.assertEqual(I.level_size(77, 3, 3), 16)                     # BC3: one block
        self.assertEqual(I.level_size(28, 5, 3), 60)                     # RGBA8
        chain = I.mip_layout(71, I.MAPTYPE_2D, 128, 128, 1, 1, 8)
        self.assertEqual(sum(c[6] for c in chain), 10936)                # measured: dog_a_head_a_col level 0

    def test_cube_and_array_faces(self):
        info = I.GfxImageInfo(0, "", 71, I.MAPTYPE_CUBE, 0, 0, 0, (0, 0), 0, (0, 0), 4, 4, 1, 1, 1, False, [])
        self.assertEqual(info.faces, 6)
        info.map_type, info.num_elements = I.MAPTYPE_ARRAY, 3
        self.assertEqual(info.faces, 3)

    def _info(self, levels):
        return I.GfxImageInfo(0, "x", 71, I.MAPTYPE_2D, 2, 3, 0, (0, 0), 0, (0, 0), 1, 1, 1, 1, 1, True,
                              [I.StreamLevel(*lv) for lv in levels])

    def test_assemble_streamed(self):
        # level 0: 16x16 with 5 mips; levels 1, 2: the top mip only (as measured on common_bots_mp.ff)
        chain0 = sum(c[6] for c in I.mip_layout(71, I.MAPTYPE_2D, 16, 16, 1, 1, 5))
        info = self._info([(16, 16, chain0, 5), (32, 32, chain0 + 512, 6), (64, 64, chain0 + 512 + 2048, 7),
                           (0, 0, 0, 0)])
        l0, l1, l2 = b"\x00" * chain0, b"\x01" * 512, b"\x02" * 2048
        w, h, n, px = I.assemble_streamed(info, [l0, l1, l2, None])
        self.assertEqual((w, h, n), (64, 64, 7))
        self.assertEqual(px, l2 + l1 + l0)
        self.assertEqual(len(px), sum(c[6] for c in I.mip_layout(71, I.MAPTYPE_2D, 64, 64, 1, 1, 7)))
        with self.assertRaises(ValueError):
            I.assemble_streamed(info, [l0, l1[:-1], l2, None])
        with self.assertRaises(ValueError):
            I.assemble_streamed(info, [l0, None, l2, None])

    def test_dds_header(self):
        info = self._info([])
        info.width = info.height = 8
        info.level_count = 4
        info.streamed = False
        px = bytes(sum(c[6] for c in I.mip_layout(71, I.MAPTYPE_2D, 8, 8, 1, 1, 4)))
        dds = I.to_dds(info, px)
        self.assertEqual(dds[:4], b"DDS ")
        size, flags, height, width = struct.unpack_from("<IIII", dds, 4)
        self.assertEqual((size, height, width), (124, 8, 8))
        self.assertEqual(struct.unpack_from("<I", dds, 28)[0], 4)        # mip count
        self.assertEqual(dds[84:88], b"DX10")
        self.assertEqual(struct.unpack_from("<II", dds, 128), (71, 3))   # DXGI format, TEXTURE2D
        self.assertEqual(len(dds), 148 + len(px))


class BCn(unittest.TestCase):
    def test_bc1_block(self):
        # c0 = pure red, c1 = pure blue, indices: 0, 1, 2, 3 in the first row
        blk = struct.pack("<HHI", 0xF800, 0x001F, 0b11100100)
        rgba = bcn.decode("BC1_UNORM", blk, 4, 4)
        self.assertEqual(rgba[0:4], bytes((255, 0, 0, 255)))
        self.assertEqual(rgba[4:8], bytes((0, 0, 255, 255)))
        self.assertEqual(rgba[8:12], bytes((170, 0, 85, 255)))

    def test_bc4_block(self):
        blk = bytes((200, 100)) + bytes(6)
        self.assertEqual(bcn.decode("BC4_UNORM", blk, 4, 4)[0:4], bytes((200, 200, 200, 255)))

    def test_png(self):
        png = bcn.png(bytes(4 * 4), 2, 2)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")


class RealZones(unittest.TestCase):
    """Invariants on every image of every zone in $IW6_FASTFILES that the readers can walk (docs/assets/images.md)."""

    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder:
            raise unittest.SkipTest("IW6_FASTFILES not set")
        cls.folder = folder
        cls.zones = sorted(p for p in Path(folder).glob("*.ff"))

    def test_images(self):
        checked = streamed = assembled = 0
        reader = I.folder_pak_reader(self.folder)
        for path in self.zones:
            try:
                prefix, result, s = I.walk_images(str(path))
            except iw6ff.FastFileError:
                continue   # a variant the pipeline's reader doesn't open yet (docs/fastfiles.md)
            st = I.state_of(s)
            self.assertEqual(st.cursor % 4, 0, path.name)
            self.assertLessEqual(st.cursor, len(prefix.stream_images), path.name)
            if result[4]:
                self.assertEqual(st.cursor, len(prefix.stream_images), path.name)
            for addr in st.order:
                info = I.read_image(s, addr)
                if info.streamed:
                    streamed += 1
                    levels = [lv for lv in info.stream_levels if lv.width]
                    self.assertTrue(levels, info.name)
                    for k, lv in enumerate(levels):
                        chain = I.mip_layout(info.format, info.map_type, lv.width, lv.height, max(1, info.depth),
                                             info.faces, lv.level_count)
                        self.assertEqual(sum(c[6] for c in chain), lv.card_memory, info.name)
                        if k:
                            self.assertEqual((lv.width, lv.level_count), (levels[k - 1].width * 2,
                                                                          levels[k - 1].level_count + 1), info.name)
                    got = I.image_pixels(s, addr, reader)
                    if got:
                        w, h, n, px = got
                        self.assertEqual(len(px), levels[-1].card_memory if len(levels) == sum(
                            1 for r in st.streams[addr] if r.end) else len(px), info.name)
                        assembled += 1
                elif addr in st.pixels_by_link:
                    px = st.pixels_by_link[addr]
                    if info.semantic == I.TS_WATER_MAP:
                        self.assertEqual(len(px), 1)
                    else:
                        self.assertEqual(len(px), info.card_memory[0], info.name)
                        chain = I.mip_layout(info.format, info.map_type, info.width, info.height,
                                             max(1, info.depth), info.faces, info.level_count)
                        self.assertEqual(sum(c[6] for c in chain), len(px), info.name)
                checked += 1
        if not checked:
            self.skipTest("no zone in IW6_FASTFILES has images the readers reach")


if __name__ == "__main__":
    unittest.main()
