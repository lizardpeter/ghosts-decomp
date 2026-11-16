"""tools/fastfile/fx.py: the effect loader on a hand-made zone (what it consumes, where pointers go, what the reader
gives back), and the loader against the game on a real zone (tests/fastfile/fx_check.py, with IW6_FASTFILES and
IW6_ORIGINALS). No game data is part of this file."""
import os
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import fx  # noqa: E402
import iw6ff  # noqa: E402

FOLLOWING = fx.PTR_INLINE


def elem(elem_type, visual_count=0, vel_count=0, vis_count=0, vel=False, vis=False, visuals=0, impact=0,
         extended=0):
    b = bytearray(fx.ELEM_SIZE)
    struct.pack_into("<II", b, 0, 0x11, 0x22)
    struct.pack_into("<ff", b, 0x10, 1.5, 2.5)                      # spawnRange
    struct.pack_into("<ii", b, 0x34, 100, 200)                       # lifeSpanMsec
    b[0xB4], b[0xB6], b[0xB7], b[0xB8] = elem_type, visual_count, vel_count, vis_count
    struct.pack_into("<QQQ", b, 0xC0, FOLLOWING if vel else 0, FOLLOWING if vis else 0, visuals)
    struct.pack_into("<Q", b, 0xF0, impact)
    struct.pack_into("<Q", b, 0x118, extended)
    struct.pack_into("<i", b, 0x124, 1234)
    return bytes(b)


def effect(counts):
    b = bytearray(fx.EFFECT_SIZE)
    struct.pack_into("<Qiii", b, 0, FOLLOWING, 7, 0x1000, 3000)
    struct.pack_into("<iii", b, 0x14, *counts)
    struct.pack_into("<Q", b, 0x38, FOLLOWING)
    return bytes(b)


class Loader(unittest.TestCase):
    def setUp(self):
        self.materials = []
        fx.HOOKS["material_ptr"] = lambda s, at: self.materials.append(s.u64(at))

    def tearDown(self):
        fx.HOOKS["material_ptr"] = None

    def test_effect_with_samples_trail_decal_and_unknown_extension(self):
        trail = bytearray(0x30)
        struct.pack_into("<iifffi", trail, 0, 50, 10, 0.5, 0.25, 0.125, 2)
        struct.pack_into("<Q", trail, 0x18, FOLLOWING)
        struct.pack_into("<i", trail, 0x20, 3)
        struct.pack_into("<Q", trail, 0x28, FOLLOWING)
        verts = struct.pack("<12f", *range(12))
        inds = struct.pack("<3H", 0, 1, 1)
        vel = struct.pack("<48f", *[float(i) for i in range(48)])
        vis = struct.pack("<20f", *[float(i) / 10 for i in range(20)])
        zone = (effect((1, 2, 1)) + b"fx/test\0" +
                elem(0, 1, vel_count=1, vis_count=0, vel=True, vis=True, impact=FOLLOWING) +
                elem(fx.ELEM_TRAIL, extended=FOLLOWING) +
                elem(fx.ELEM_DECAL, 1, visuals=FOLLOWING) +
                elem(7, extended=5) +
                vel + vis[:0x50] + b"fx/hit\0" +            # element 0: samples, then its effectOnImpact name
                bytes(trail) + verts + inds +                 # element 1: the trail
                bytes(0x18) +                                 # element 2: one mark visual of 3 null materials
                b"\x99")                                      # element 3: the one byte of an unknown extension
        s = iw6ff.Stream(bytes(iw6ff.XFILE_SIZE) + zone, [1 << 20] * 7)
        s.push(iw6ff.XFILE_BLOCK_VIRTUAL)
        slot = s.align(8)
        s.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
        s.put_u64(slot, FOLLOWING)
        fx.load_effect_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        self.assertEqual(self.materials, [0, 0, 0, 0, 0, 0])   # one visual each (0, 1, 3), the decal's three
        f = fx.read_effect(s, s.u64(slot))
        self.assertEqual((f.name, f.flags, f.total_size, f.msec_looping_life, f.counts), ("fx/test", 7, 0x1000, 3000,
                                                                                         (1, 2, 1)))
        e0, e1, e2, e3 = f.elems
        self.assertEqual((e0.flags, e0.flags2, e0.spawn_range, e0.life_span_msec, e0.random_seed),
                         (0x11, 0x22, (1.5, 2.5), (100, 200), 1234))
        self.assertEqual(len(e0.vel_samples), 2)
        self.assertEqual(e0.vel_samples[1][0], ((24.0, 25.0, 26.0), (27.0, 28.0, 29.0)))
        self.assertEqual(len(e0.vis_samples), 1)
        self.assertAlmostEqual(e0.vis_samples[0][1].scale, 1.9, places=6)
        self.assertIsNone(e0.effect_on_impact)                  # not in this zone: the handle is 0 here
        named = fx.read_effect(s, s.u64(slot), s.fx_ref_names)  # the name the loader saw
        self.assertEqual(named.elems[0].effect_on_impact, "fx/hit")
        self.assertEqual(e1.extended["kind"], "trail")
        self.assertEqual((e1.extended["scrollTimeMsec"], e1.extended["inds"]), (50, [0, 1, 1]))
        self.assertEqual(e1.extended["verts"][1], (6.0, 7.0, 8.0, 9.0, 10.0, 11.0))
        self.assertEqual(e2.type_name, "decal")
        self.assertEqual(e2.visuals, [[None, None, None]])
        self.assertEqual(e3.extended, {"kind": "type7", "byte": 0x99})
        self.assertEqual(fx.to_json(f)["elems"][1]["extended"]["inds"], [0, 1, 1])

    def test_alias_and_offset_pointers(self):
        """elemDefs takes any non-null value as inline; an extended trail that isn't -1 is an offset."""
        zone = effect((1, 0, 0)) + b"a\0" + elem(fx.ELEM_TRAIL, extended=0x3_0000_0010)   # block 3, offset 0x10-1
        s = iw6ff.Stream(bytes(iw6ff.XFILE_SIZE) + zone, [1 << 20] * 7)
        s.push(iw6ff.XFILE_BLOCK_VIRTUAL)
        slot = s.align(8)
        s.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
        s.put_u64(slot, FOLLOWING)
        fx.load_effect_ptr(s, slot)
        self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
        f = s.u64(slot)
        e = s.u64(f + 0x38)
        self.assertEqual(s.u64(e + 0x118), s.offset_to_pointer(0x3_0000_0010))


class Game(unittest.TestCase):
    """The loader against the game on the Extinction aliens' shared zone."""

    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.zone = Path(folder) / "common_alien_mp.ff"
        if not cls.zone.exists():
            raise unittest.SkipTest("no common_alien_mp.ff in IW6_FASTFILES")

    def test_loader_equals_game(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import fx_check
        ff = self.zone.read_bytes()
        for occ in (0, 100):
            d, _ = fx_check.compare_effect(ff, self.zone.stem, occ)
            self.assertEqual(d, [], occ)


if __name__ == "__main__":
    unittest.main()
