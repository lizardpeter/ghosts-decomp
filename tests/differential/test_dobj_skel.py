"""Differential cases for the skeleton functions of src/xanim/dobj_skel.cpp against the Store build.

One buffer holds everything the functions read and write (passed as the first argument, so all of it is compared
afterwards): the XModel header with its parentList and trans arrays, the DSkel and its 256 bone matrices, and the
three part-bit masks. Models have 1..255 bones, a few root bones, random parents (earlier bones, and offset 0: the
bone itself), random and degenerate quaternions (|q|^2 on both sides of 1e-6, in float and in double), scales and
noScalePartBits, and calc/control/world-control bits from none to all. tools/fastfile/skin.py is the same in Python,
checked against the game on real models (tests/fastfile/skin_check.py).
"""
import random
import struct

from harness import HEAP

STORE = "iw6mp64_MSStore_ship"
OFF_PARENTS, OFF_TRANS, OFF_SKEL, OFF_MATS = 0x300, 0x400, 0x1000, 0x1100
OFF_CALC, OFF_CONTROL, OFF_WORLD = 0x3100, 0x3120, 0x3140
SIZE = 0x3200


def _float(r):
    return r.choice([0.0, 1.0, -1.0, r.uniform(-1, 1), r.uniform(-100, 100), r.uniform(-1e4, 1e4)])


def _quat(r):
    k = r.random()
    if k < 0.08:
        return [0.0] * 4
    if k < 0.16:   # |q|^2 near 1e-6: 1e-6 as a float is below 1e-6 as a double
        s = (1e-6 * r.choice([0.999999, 1.0, 1.0000001, 0.9999999, 1.000001])) ** 0.5
        return [s, 0.0, 0.0, 0.0]
    q = [r.gauss(0, 1) for _ in range(4)]
    if r.random() < 0.7:
        n = sum(x * x for x in q) ** 0.5 or 1.0
        q = [x / n for x in q]
    return q


def _bits(r, nb):
    k = r.random()
    if k < 0.2:
        return [-1] * 8
    if k < 0.3:
        return [0] * 8
    return [r.getrandbits(32) - (1 << 31) for _ in range(8)]


def _model(r, nb, nr, min_bone):
    buf = bytearray(SIZE)
    buf[8], buf[9] = nb, nr
    struct.pack_into("<f", buf, 0xC, r.choice([1.0, 1.0, r.uniform(0.1, 3.0)]))
    struct.pack_into("<8i", buf, 0x10, *_bits(r, nb))
    struct.pack_into("<Q", buf, 0x38, HEAP + OFF_PARENTS)
    struct.pack_into("<Q", buf, 0x48, HEAP + OFF_TRANS)
    for j in range(nb - nr):
        bone = min_bone + j
        buf[OFF_PARENTS + j] = min(r.choice([1, 1, r.randint(0, bone)]), bone, 255)
        struct.pack_into("<3f", buf, OFF_TRANS + 12 * j, *(_float(r) for _ in range(3)))
    struct.pack_into("<Q", buf, OFF_SKEL + 0x88, HEAP + OFF_MATS)
    for i in range(256):
        struct.pack_into("<8f", buf, OFF_MATS + 0x20 * i, *_quat(r), *(_float(r) for _ in range(3)),
                         r.choice([2.0, r.uniform(0, 4)]))
    struct.pack_into("<8i", buf, OFF_CALC, *_bits(r, nb))
    struct.pack_into("<8i", buf, OFF_CONTROL, *(_bits(r, nb) if r.random() < 0.5 else [0] * 8))
    struct.pack_into("<8i", buf, OFF_WORLD, *(_bits(r, nb) if r.random() < 0.3 else [0] * 8))
    return buf


def _root(r):
    nb = r.randint(1, 255)
    nr = r.randint(0, min(nb, 5))
    min_bone = r.choice([0, 0, r.randint(0, 256 - max(nr, 1))])
    buf = _model(r, nb, nr, min_bone)
    return {"args": [bytes(buf), HEAP + OFF_SKEL, min_bone, HEAP + OFF_CALC]}


def _non_root(r):
    nb = r.randint(1, 255)
    nr = r.randint(0, min(nb, 5))
    min_bone = r.choice([nr, nr, r.randint(0, nr)])
    buf = _model(r, nb, nr, min_bone)
    return {"args": [bytes(buf), HEAP + OFF_SKEL, min_bone, HEAP + OFF_CALC, HEAP + OFF_CONTROL, HEAP + OFF_WORLD]}


CASES = [
    {"symbol": "?CalcSkelRootBonesNoParentOrDuplicate@@YAXPEBUXModel@@PEAUDSkel@@HQEAH@Z", "build": STORE,
     "ret": "void", "inputs": [_root(r) for r in [random.Random(0x6990)] for _ in range(400)]},
    {"symbol": "?CalcSkelNonRootBones@@YAXPEBUXModel@@PEAUDSkel@@HQEAHQEBH3@Z", "build": STORE,
     "ret": "void", "inputs": [_non_root(r) for r in [random.Random(0x61D0)] for _ in range(400)]},
]
