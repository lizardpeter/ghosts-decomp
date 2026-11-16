"""tools/fastfile/xanim.py: the evaluator on hand-made animations, and the loader and evaluator against the game on
real zones (tests/fastfile/xanim_check.py, with IW6_FASTFILES and IW6_ORIGINALS)."""
import os
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import xanim as XA  # noqa: E402


def make(numframes, bone_count, data_byte=b"", data_short=(), data_int=(), random_short=(), random_byte=b"",
         indices=()):
    """An animation over sum(rotation groups) bones (the translation groups cover the same bones again)."""
    return XA.XAnim(name="test", numframes=numframes, framerate=30.0, frequency=1.0, flags=0, asset_type=0,
                    ik_type=0, bone_count=tuple(bone_count) + (sum(bone_count[:5]),), names=list(range(sum(bone_count[:5]))),
                    notify=[], data_byte=bytes(data_byte), data_short=list(data_short),
                    data_int=struct.pack(f"<{len(data_int)}f", *data_int), random_data_short=list(random_short),
                    random_data_byte=bytes(random_byte), random_data_int=b"", indices=list(indices), delta=None)


def counts(**kw):
    out = [0] * 9
    for k, v in kw.items():
        out[getattr(XA, k.upper())] = v
    return out


class Evaluate(unittest.TestCase):
    def test_full_quat_interpolates_between_keys(self):
        # 10 frames, keys at frames 0 and 10: identity -> (0, 0, 1, 0) / 32767 scale
        a = make(10, counts(full_quat=1), data_byte=bytes([0, 10]), data_short=[1],
                 random_short=[0, 0, 0, 32767, 0, 0, 32767, 0])
        out = XA.calc_parts(a, 0.5)
        self.assertAlmostEqual(float(out[0, 2]), 0.5, places=5)
        self.assertAlmostEqual(float(out[0, 3]), 0.5, places=5)
        q, _ = XA.sample(a, 0.5)[0]
        self.assertAlmostEqual(q[2], q[3], places=6)
        self.assertAlmostEqual(sum(x * x for x in q), 1.0, places=6)

    def test_last_frame_takes_last_key(self):
        a = make(10, counts(half_quat=1), data_byte=bytes([0, 4, 10]), data_short=[2],
                 random_short=[0, 32767, 100, 200, 32767, 0])
        out = XA.calc_parts(a, 1.0)
        self.assertEqual(out[0, :4].tolist(), [0.0, 0.0, np.float32(32767) * XA.QUAT_SCALE, 0.0])

    def test_translation_groups_name_their_bone(self):
        # part 0 has no rotation; small translation on part 0; one translation on part 1; part 2 no translation
        a = make(4, counts(no_quat=3, small_trans=1, trans_no_size=1, no_trans=1),
                 data_byte=bytes([0, 0, 4, 1, 2]), data_short=[1],
                 data_int=[1.0, 2.0, 3.0, 0.5, 0.5, 0.5, 7.0, 8.0, 9.0], random_byte=bytes([0, 0, 0, 10, 20, 30]))
        out = XA.calc_parts(a, 0.5)
        self.assertEqual(out[0, 4:].tolist(), [1.0 + 2.5, 2.0 + 5.0, 3.0 + 7.5, 1.0])
        self.assertEqual(out[1, 4:].tolist(), [7.0, 8.0, 9.0, 1.0])
        self.assertEqual(out[2, 4:].tolist(), [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(out[:, 3].tolist(), [1.0, 1.0, 1.0])

    def test_split_index_table(self):
        # 300 frames, 0x41 keys (n = 0x40): coarse table in dataShort, the full table in indices
        n = 0x40
        table = [round(i * 300 / n) for i in range(n + 1)]
        coarse = [table[0], table[n]]
        keys = []
        for i in range(n + 1):
            keys += [0, 0, i * 100, 30000]
        a = make(300, counts(full_quat=1), data_short=[n] + coarse, random_short=keys, indices=table)
        t = 0.37
        out = XA.calc_parts(a, t)
        frame = np.float32(300) * np.float32(t)
        i = max(k for k in range(n) if table[k] <= int(frame))
        f = (frame - np.float32(table[i])) / np.float32(table[i + 1] - table[i])
        k0, k1 = np.float32(i * 100) * XA.QUAT_SCALE, np.float32((i + 1) * 100) * XA.QUAT_SCALE
        self.assertEqual(float(out[0, 2]), float((k1 - k0) * f + k0))


class RootMotion(unittest.TestCase):
    def test_keyed_translation_and_yaw(self):
        a = make(10, counts(no_quat=1))
        a.flags = XA.FLAG_DELTA_2D
        a.delta = XA.DeltaPart(
            trans={"mins": (0.0, 0.0, 0.0), "size": (2.0, 1.0, 1.0), "small": True, "indices": [0, 10],
                   "keys": [0, 0, 0, 100, 0, 0]},
            quat2={"indices": [0, 10], "keys": [0, 32767, 32767, 0]}, quat=None)
        d = XA.calc_abs_delta(a, 0.5)
        self.assertEqual(d[5:].tolist(), [100.0, 0.0, 0.0])
        self.assertEqual(float(d[4]), 1.0)
        q, t = XA.sample_delta(a, 1.0)
        self.assertAlmostEqual(q[2], 1.0, places=5)
        self.assertEqual(t, (200.0, 0.0, 0.0))

    def test_no_root_motion_without_flags(self):
        a = make(10, counts(no_quat=1))
        self.assertIsNone(XA.sample_delta(a, 0.5))


class RealZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.zones = [p for p in sorted(Path(folder).glob("mp_alien_*.ff"))][:1]
        if not cls.zones:
            raise unittest.SkipTest("no Extinction map zone in IW6_FASTFILES")

    def test_loader_and_evaluator_equal_game(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import xanim_check
        for path in self.zones:
            ff = path.read_bytes()
            diffs, _ = xanim_check.compare_loader(ff, path.stem, 0)
            self.assertEqual(diffs, [], path.name)
            calc, pairs = xanim_check.compare_calc(ff, path.stem)
            self.assertGreater(pairs, 0)
            self.assertEqual([(d[0], d[1]) for d in calc], [], path.name)


if __name__ == "__main__":
    unittest.main()
