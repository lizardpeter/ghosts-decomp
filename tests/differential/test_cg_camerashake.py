"""Differential cases for cgame/cg_camerashake.cpp and cgame_mp/cg_ents_mp.cpp against the Store build.

CG_UpdateCameraShake: a shake started before, at or after cg.time (negative, zero and past-the-end ages), random
lengths, scales and radii (0, negative, NaN), sources near and far from the view origin.

CG_ShakeCamera: four random shakes in s_cameraShakeSet (some over, one dominant, sizes above 1), cg.time over a long
range (the sine arguments), the view origin and the view angles it adds to, and the phase; with no live shake it
re-randomises the phase (crandom, through the CRT's rand import).

CG_SetFrameInterpolation: cg.snap and cg.nextSnap in scratch memory with server times 50 ms apart, equal, reversed or
far apart, and cg.time before, between and after them."""
import random
import struct

from syms import static, va

STORE = "iw6mp64_MSStore_ship"
CG_TIME, CG_VIEWORG, CG_VIEWANGLES = 0x71890, 0x718E0, 0xA9A90
SNAP, NEXT_SNAP = 0x520000, 0x560000  # scratch snapshot_s (serverTime at +0x3C7C)


def _shake(r, now):
    start = now - r.choice([0, 1, 50, 299, 300, 301, 1000, 4999, -1, -100, r.randint(-500, 6000)])
    length = r.choice([300.0, 1000.0, 5000.0, 0.0, -100.0, float("nan"), r.uniform(0, 6000)])
    scale = r.choice([1.0, 0.5, 2.0, 0.0, -1.0, float("nan"), r.uniform(0, 3)])
    radius = r.choice([0.0, 0.0, -5.0, 500.0, 2000.0, float("nan"), r.uniform(0, 3000)])
    src = [r.choice([0.0, 100.0, r.uniform(-2000, 2000)]) for _ in range(3)]
    junk = [r.uniform(-2, 2), r.uniform(-2, 2)]
    return struct.pack("<Ifff3fff", start & 0xFFFFFFFF, scale, length, radius, *src, *junk)


def _view(r):
    return struct.pack("<3f", *(r.choice([0.0, 50.0, r.uniform(-2000, 2000)]) for _ in range(3)))


def _update(r):
    now = r.choice([0, 1000, 123456, 0x7FFFFF00, r.getrandbits(31)])
    view = _view(r)

    def setup(w):
        cg = va("cgArray")
        w.u32(cg + CG_TIME, now)
        w.write(cg + CG_VIEWORG, view)
    return {"args": [0, va("cgArray"), _shake(r, now)], "setup": setup}


def _shake_camera(r):
    now = r.choice([0, 600, 1000, 123456, 9999999, r.getrandbits(24), r.getrandbits(31)])
    shakes = b"".join(_shake(r, now) if r.random() < 0.7 else bytes(0x24) for _ in range(4))
    phase = r.choice([0.0, 1.0, -3.0, r.uniform(-3.2, 3.2)])
    view, angles = _view(r), struct.pack("<3f", *(r.uniform(-90, 90) for _ in range(3)))

    def setup(w):
        cg = va("cgArray")
        w.u32(cg + CG_TIME, now)
        w.write(cg + CG_VIEWORG, view)
        w.write(cg + CG_VIEWANGLES, angles)
        w.write(static("cgame/cg_camerashake.cpp", "s_cameraShakeSet"), shakes + struct.pack("<f", phase))
    return {"args": [0], "setup": setup}


def _frame_interpolation(r):
    snap = r.choice([0, 1000, 50000, 0x7FFFFF00, r.getrandbits(31)])
    gap = r.choice([50, 50, 0, -50, 1, 100, 1000, 0x7FFFFFFF, r.randint(-100, 100)])
    now = snap + r.choice([0, 1, 25, 49, 50, 51, 120, -1, -30, r.randint(-60, 160)])
    junk = r.uniform(-2, 2)

    def setup(w):
        cg = va("cgArray")
        w.m.mu.mem_write(SNAP + 0x3C7C, struct.pack("<I", snap & 0xFFFFFFFF))
        w.m.mu.mem_write(NEXT_SNAP + 0x3C7C, struct.pack("<I", (snap + gap) & 0xFFFFFFFF))
        w.write(cg + 0x3388, struct.pack("<QQ", SNAP, NEXT_SNAP))
        w.write(cg + 0x71888, struct.pack("<f", junk))
        w.u32(cg + CG_TIME, now)
    return {"args": [0], "setup": setup}


CASES = [
    {"symbol": "?CG_UpdateCameraShake@@YAHW4LocalClientNum_t@@PEBUcg_s@@PEAUCameraShake@@@Z", "build": STORE,
     "ret": "int", "inputs": [_update(r) for r in [random.Random(75)] for _ in range(3000)]},
    {"symbol": "?CG_ShakeCamera@@YAXW4LocalClientNum_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [_shake_camera(r) for r in [random.Random(139)] for _ in range(2000)]},
    {"symbol": "?CG_SetFrameInterpolation@@YAXW4LocalClientNum_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [_frame_interpolation(r) for r in [random.Random(1038)] for _ in range(2000)]},
]
