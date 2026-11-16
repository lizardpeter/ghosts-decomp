"""tools/fastfile/skin.py: the skeleton and dual quaternion skinning on hand-made bones, and against the game's
CalcSkel* and R_SkinXModelCmd on a real model (tests/fastfile/skin_check.py, with IW6_FASTFILES and IW6_ORIGINALS)."""
import math
import os
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import skin  # noqa: E402

F32 = np.float32


def quat_axis(axis, angle):
    s = math.sin(angle / 2)
    return [axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle / 2)]


def qmul(a, b):
    """Hamilton product a * b, (x, y, z, w)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def rotate(q, v):
    x, y, z, w = q
    m = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return m @ np.asarray(v, float)


def mat(q, t):
    m = np.zeros(8, F32)
    m[:4], m[4:7] = q, t
    return m


class Skeleton(unittest.TestCase):
    def test_chain_composes_rotations_and_offsets(self):
        # root at the origin turned 90° about z; child 10 along x from it, turned 90° about x, offset (1, 2, 3)
        qr, qc = quat_axis((0, 0, 1), math.pi / 2), quat_axis((1, 0, 0), math.pi / 2)
        mats = np.stack([mat(qr, (0, 0, 0)), mat(qc, (1, 2, 3))])
        mats[0, 4:7] = (5, 6, 7)
        skin.calc_skel(mats, 1, [1], [(10, 0, 0)], 1.0)
        q = qmul(qr, qc)
        sign = 1 if q[3] * mats[1, 3] >= 0 else -1
        np.testing.assert_allclose(mats[1, :4] * sign, q, atol=1e-6)
        np.testing.assert_allclose(mats[1, 4:7], rotate(qr, (11, 2, 3)) + (5, 6, 7), atol=1e-5)
        self.assertAlmostEqual(float(mats[0, 7]), 2.0, places=5)   # 2 / |q|²
        self.assertAlmostEqual(float(mats[1, 7]), 2.0, places=5)

    def test_scale_and_no_scale_bones(self):
        mats = np.stack([mat((0, 0, 0, 1), (0, 0, 0)), mat((0, 0, 0, 1), (1, 1, 1))])
        a = skin.calc_skel(mats.copy(), 1, [1], [(0, 0, 0)], 2.0)
        b = skin.calc_skel(mats.copy(), 1, [1], [(0, 0, 0)], 2.0, no_scale=[False, True])
        np.testing.assert_allclose(a[1, 4:7], (2, 2, 2))
        np.testing.assert_allclose(b[1, 4:7], (1, 1, 1))

    def test_degenerate_quaternion_becomes_identity(self):
        mats = np.zeros((1, 8), F32)
        skin.calc_skel(mats, 1, [], [], 1.0)
        self.assertEqual(list(mats[0, [3, 7]]), [1.0, 2.0])

    def test_base_local_and_normalize(self):
        m = skin.base_local(3, 1, [(0, 0, 0, 32767), (0, 0, 23170, 23170)])
        self.assertEqual(list(m[0, :4]), [0, 0, 0, 1])
        np.testing.assert_allclose(m[2, 2:4], (23170 * 3.051851e-05,) * 2, rtol=1e-6)
        m[2, :4] *= 3
        m[2, 4:8] = (2, 4, 6, 2)
        skin.normalize_rot_trans(m)
        # the 0x5f3759df estimate with one Newton step: within 0.2%, as in the game
        self.assertAlmostEqual(float(np.linalg.norm(m[2, :4])), 1.0, delta=2e-3)
        np.testing.assert_allclose(m[2, 4:8], (1, 2, 3, 1))


class Skinning(unittest.TestCase):
    def setUp(self):
        q = quat_axis((0.6, 0.8, 0), 0.7)
        base = np.stack([mat(q, (1, 2, 3)), mat((0, 0, 0, 1), (0, 0, 0))])
        for m in base:
            m[7] = 2.0 / float(np.dot(m[:4], m[:4]))
        self.base = base

    def test_bind_pose_is_identity(self):
        skel, dq = skin.skin_matrices(self.base, self.base)
        np.testing.assert_allclose(skel[0], np.eye(4), atol=1e-6)
        np.testing.assert_allclose(abs(dq[0, 0, 3]), 1.0, atol=1e-6)
        np.testing.assert_allclose(dq[0, 1], 0.0, atol=1e-6)

    def test_pose_moves_vertices_rigidly(self):
        # bone 0 posed: turned 90° about z more, then moved by (10, 0, 0)
        turn = quat_axis((0, 0, 1), math.pi / 2)
        pose = self.base.copy()
        pose[0, :4] = qmul(turn, list(self.base[0, :4]))
        pose[0, 4:7] = rotate(turn, self.base[0, 4:7]) + (10, 0, 0)
        skel, dq = skin.skin_matrices(self.base, pose)
        p = (4.0, -1.0, 2.0)
        want = rotate(turn, p) + (10, 0, 0)
        normal = skin.pack_1010102([F32(1), F32(0), F32(0)])
        vert = struct.pack("<4f4I", *p, 1.0, 0xFFFFFFFF, 0, normal, normal)
        # one vertex of bone 0 alone, one of bones 0 and 1 (bone 1 unposed) half and half... and all of bone 0 by DQB
        one = skin.skin_vertices(vert, [1, 0, 0, 0, 0, 0, 0, 0], [0], skel, dq)
        np.testing.assert_allclose(struct.unpack_from("<3f", one), want, atol=1e-4)
        n = skin.unpack_1010102(struct.unpack_from("<I", one, 0x18)[0])
        np.testing.assert_allclose(n, rotate(turn, (1, 0, 0)), atol=4e-3)
        dqb = skin.skin_vertices(vert, [0, 1, 0, 0, 0, 0, 0, 0], [0, 64, 0], skel, dq)   # bone 1 weight 0
        np.testing.assert_allclose(struct.unpack_from("<3f", dqb), want, atol=1e-4)

    def test_pack_round_trip(self):
        for n in ([1, 0, 0], [0, -1, 0], [0.6, 0.0, -0.8], [0.123, 0.456, -0.789]):
            v = skin.unpack_1010102(skin.pack_1010102([F32(x) for x in n]))
            np.testing.assert_allclose(v, n, atol=2.5e-3)


class Game(unittest.TestCase):
    """The game's skeleton (bit for bit) and skinned vertices (to float rounding) on an Extinction alien."""

    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.zone = Path(folder) / "mp_alien_town.ff"
        if not cls.zone.exists():
            raise unittest.SkipTest("no mp_alien_town.ff in IW6_FASTFILES")

    def test_alien_goon(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import skin_check
        res = skin_check.check(self.zone.read_bytes(), self.zone.stem, {"alien_goon"}, times=(0.37,))
        self.assertGreater(len(res), 1)
        for name, label, t, skel_equal, pos, pack, verts in res:
            self.assertTrue(skel_equal, label)
            self.assertLess(pos, 1e-3, label)
            self.assertLessEqual(pack, 1, label)


class OriginalSkeleton(unittest.TestCase):
    """skin.calc_skel against the Store build's CalcSkel functions (emulated) on the random models of
    tests/differential/test_dobj_skel.py, control and world-control bones included: bit for bit."""

    def test_random_models(self):
        if not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_ORIGINALS")
        import random
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "differential"))
        import test_dobj_skel as T
        from harness import HEAP, Image, Machine, original_exe
        m = Machine(Image(original_exe("iw6mp64_MSStore_ship")))
        r = random.Random(5)
        for _ in range(60):
            nb = r.randint(2, 255)
            nr = r.randint(1, min(nb, 4))
            buf = T._model(r, nb, nr, nr)
            struct.pack_into("<8i", buf, T.OFF_CALC, *[-1] * 8)
            out = m.call(0x140556990, [bytes(buf), HEAP + T.OFF_SKEL, 0, HEAP + T.OFF_CALC], "void")[1][0]
            out = m.call(0x1405561D0, [out, HEAP + T.OFF_SKEL, nr, HEAP + T.OFF_CALC, HEAP + T.OFF_CONTROL,
                                       HEAP + T.OFF_WORLD], "void")[1][0]

            def bits(off):
                return [bool(struct.unpack_from("<I", buf, off + 4 * (i >> 5))[0] & (0x80000000 >> (i & 31)))
                        for i in range(nb)]
            mats = np.frombuffer(bytes(buf[T.OFF_MATS:T.OFF_MATS + 32 * nb]), np.float32).reshape(nb, 8).copy()
            trans = [struct.unpack_from("<3f", buf, T.OFF_TRANS + 12 * j) for j in range(nb - nr)]
            with np.errstate(all="ignore"):
                skin.calc_skel(mats, nr, list(buf[T.OFF_PARENTS:T.OFF_PARENTS + nb - nr]), trans,
                               struct.unpack_from("<f", buf, 0xC)[0], bits(0x10), bits(T.OFF_CONTROL),
                               bits(T.OFF_WORLD))
            self.assertEqual(mats.tobytes(), out[T.OFF_MATS:T.OFF_MATS + 32 * nb])


if __name__ == "__main__":
    unittest.main()
