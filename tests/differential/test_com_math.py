"""Hand-written differential cases for universal/com_math.cpp functions that auto-generated inputs can't test.

- LinearTrackAngle / DiffTrackAngle: the original wraps tgt into (cur - 180, cur + 180] with `tgt -= 360` loops,
  which never end when tgt - cur is infinite or so large that subtracting 360 doesn't change tgt (original
  behaviour). The harness stops such calls at its instruction limit and compares whatever is in xmm0 then, so
  the inputs here keep tgt and cur finite and moderate (NaN still included: it skips the loops).
- VecNCompareCustomEpsilon: coordCount must fit the 256-byte buffers (at most 64 floats); a huge count walks off
  the buffer or runs into the instruction limit.
"""
import random
import struct

SPECIAL = [0.0, -0.0, 1.0, -1.0, 0.5, -0.5, 180.0, -180.0, 360.0, -360.0, 179.999, 540.0, float("nan")]


def _f(r):
    x = r.random()
    if x < 0.3:
        return r.choice(SPECIAL)
    if x < 0.6:
        return r.uniform(-2.0, 2.0)
    return r.uniform(-1e4, 1e4)


def _rate(r):
    x = r.random()
    if x < 0.2:
        return r.choice([0.0, 1.0, -1.0, 1e30, float("inf"), float("-inf"), float("nan"), 1e-30])
    return r.uniform(-1e3, 1e3) if x < 0.5 else r.uniform(-2.0, 2.0)


def _track_inputs(seed, n=300):
    r = random.Random(seed)
    return [[("f", _f(r)), ("f", _f(r)), ("f", _rate(r)), ("f", _rate(r))] for _ in range(n)]


def _vecn_inputs(seed, n=300):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        count = r.choice([0, 1, 2, 3, 4, 16, 64, -1, r.randint(0, 64)])
        a = [_f(r) for _ in range(64)]
        # make many coordinates close so the epsilon test is exercised both ways
        b = [x + r.uniform(-0.1, 0.1) if r.random() < 0.8 else _f(r) for x in a]
        eps = r.choice([0.0, -0.0, 0.01, 0.05, 0.1, 1.0, -0.05, 1e30, float("inf"), float("nan"), r.uniform(0, 0.2)])
        out.append([struct.pack("<64f", *a), struct.pack("<64f", *b), ("f", eps), count])
    return out


CASES = [
    {"symbol": "?LinearTrackAngle@@YAMMMMM@Z", "va": 0x14022E2B0, "ret": "float", "inputs": _track_inputs(446)},
    {"symbol": "?DiffTrackAngle@@YAMMMMM@Z", "va": 0x14022DC80, "ret": "float", "inputs": _track_inputs(490)},
    {"symbol": "?VecNCompareCustomEpsilon@@YAHQEBM0MH@Z", "va": 0x1402304C0, "ret": "int",
     "inputs": _vecn_inputs(675)},
]
