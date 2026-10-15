"""Hand-written inputs for the culling functions of universal/com_math.cpp.

Generated inputs (auto.py) give random cones and boxes, which nearly always land on the first early-out (culled).
These cases build realistic geometry instead: a unit cone direction, a half-angle between 3 and 80 degrees, and
boxes or spheres placed near the cone's surface (in front of, behind and around the apex), so every path is taken:
culled by the sphere test, culled by the plane through the apex, centre inside the cone, and the final
nearest-surface-direction test with both outcomes. The generated inputs are appended to keep NaN/inf coverage.
"""
import math
import random
import struct
import zlib

from auto import auto_case


def _pack(*vals, size=64):
    vals = list(vals) + [0.0] * (size - len(vals))
    return struct.pack(f"<{size}f", *vals)


def _unit(r):
    while True:
        v = [r.uniform(-1.0, 1.0) for _ in range(3)]
        n = math.sqrt(sum(x * x for x in v))
        if 0.1 < n <= 1.0:
            return [x / n for x in v]


def _perp(r, d):
    a = _unit(r)
    dot = sum(x * y for x, y in zip(a, d))
    p = [x - dot * y for x, y in zip(a, d)]
    n = math.sqrt(sum(x * x for x in p)) or 1.0
    return [x / n for x in p]


def _cone(r):
    org = [r.uniform(-2000.0, 2000.0) for _ in range(3)]
    d = _unit(r)
    half = math.radians(r.uniform(3.0, 80.0))
    return org, d, half


def _near_surface(r, org, d, half):
    """A point around the cone's surface: along the axis at t, offset sideways by about the cone radius at t."""
    t = r.uniform(-300.0, 1500.0)
    p = _perp(r, d)
    side = abs(t) * math.tan(half) * r.uniform(0.0, 2.0) + r.uniform(-50.0, 50.0)
    return [o + t * x + side * y for o, x, y in zip(org, d, p)]


def _box(r, org, d, half):
    mid = _near_surface(r, org, d, half)
    hs = [r.uniform(0.5, 120.0) for _ in range(3)]
    return _pack(*mid, *hs)


def _merge(symbol, va, inputs):
    auto, _ = auto_case(symbol, va)
    return {"symbol": symbol, "va": va, "ret": auto["ret"], "inputs": inputs + auto["inputs"]}


def _cull_box_from_cone(n=400):
    r = random.Random(zlib.crc32(b"CullBoxFromCone"))
    out = []
    for _ in range(n):
        org, d, half = _cone(r)
        out.append([_pack(*org), _pack(*d), ("f", math.cos(half)), _box(r, org, d, half)])
    return out


def _cull_box_from_sphere(n=400):
    r = random.Random(zlib.crc32(b"CullBoxFromSphere"))
    out = []
    for _ in range(n):
        mid = [r.uniform(-2000.0, 2000.0) for _ in range(3)]
        hs = [r.uniform(0.5, 120.0) for _ in range(3)]
        radius = r.uniform(1.0, 400.0)
        # sphere centre near the box: inside, touching a face, edge or corner, or clear of it
        org = [m + s * r.uniform(-1.0, 1.0) * r.choice([0.5, 1.0, 1.5]) + r.uniform(-radius, radius) * 1.3
               for m, s in zip(mid, hs)]
        out.append([_pack(*org), ("f", radius), _pack(*mid, *hs)])
    return out


def _cull_box_from_conic_section_of_sphere(n=400):
    r = random.Random(zlib.crc32(b"CullBoxFromConicSectionOfSphere"))
    out = []
    for _ in range(n):
        org, d, half = _cone(r)
        box = _box(r, org, d, half)
        mid = struct.unpack("<3f", box[:12])
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(mid, org)))
        radius = dist * r.uniform(0.3, 1.6) + r.uniform(0.0, 100.0)
        out.append([_pack(*org), _pack(*d), ("f", math.cos(half)), ("f", radius), box])
    return out


def _cull_sphere_from_cone(n=400):
    r = random.Random(zlib.crc32(b"CullSphereFromCone"))
    out = []
    for _ in range(n):
        org, d, half = _cone(r)
        center = _near_surface(r, org, d, half)
        out.append([_pack(*org), _pack(*d), ("f", math.cos(half)), _pack(*center), ("f", r.uniform(1.0, 200.0))])
    return out


def _distance_from_cone_to_point(n=400):
    # cosHalfFov in [0, 1] (otherwise sqrtf of a negative, on which the original CRT faults in the harness)
    r = random.Random(zlib.crc32(b"DistanceFromConeToPoint"))
    out = []
    for _ in range(n):
        org, d, half = _cone(r)
        out.append([_pack(*org), _pack(*d), ("f", math.cos(half)), _pack(*_near_surface(r, org, d, half))])
    return out


def _trajectory(r):
    """A reachable throw: start, end, launch speed above the minimum, gravity (positive magnitude)."""
    start = [r.uniform(-2000.0, 2000.0) for _ in range(3)]
    end = [s + r.uniform(-1500.0, 1500.0) for s in start[:2]] + [start[2] + r.uniform(-300.0, 300.0)]
    g = r.choice([800.0, 386.0889, r.uniform(100.0, 1200.0)])
    x = math.hypot(end[0] - start[0], end[1] - start[1])
    y = end[2] - start[2]
    vmin = math.sqrt(g * (y + math.hypot(x, y)))
    return start, end, vmin * r.uniform(1.0001, 2.5), g, x, y


def _trajectory_exit_angle(n=400):
    r = random.Random(zlib.crc32(b"TrajectoryCalculateExitAngle"))
    out = []
    for _ in range(n):
        _, _, v, g, x, y = _trajectory(r)
        out.append([("f", v), ("f", g), ("f", x), ("f", y)])
    return out


def _trajectory_in_air_time(n=400):
    r = random.Random(zlib.crc32(b"TrajectoryEstimateDesiredInAirTime"))
    out = []
    for _ in range(n):
        start, end, v, g, _, _ = _trajectory(r)
        out.append([_pack(*start), _pack(*end), ("f", v), ("f", g)])
    return out


CASES = [
    _merge("?DistanceFromConeToPoint@@YAMQEBM0M0@Z", 0x14022DE10, _distance_from_cone_to_point()),
    _merge("?TrajectoryCalculateExitAngle@@YAMMMMM@Z", 0x14022FD20, _trajectory_exit_angle()),
    _merge("?TrajectoryEstimateDesiredInAirTime@@YAMQEBM0MM@Z", 0x14022FEF0, _trajectory_in_air_time()),
    _merge("?CullBoxFromCone@@YA_NQEBM0MPEBUBounds@@@Z", 0x14022D480, _cull_box_from_cone()),
    _merge("?CullBoxFromSphere@@YA_NQEBMMPEBUBounds@@@Z", 0x14022DA40, _cull_box_from_sphere()),
    _merge("?CullBoxFromConicSectionOfSphere@@YA_NQEBM0MMPEBUBounds@@@Z", 0x14022D720,
           _cull_box_from_conic_section_of_sphere()),
    _merge("?CullSphereFromCone@@YA_NQEBM0M0M@Z", 0x14022DAF0, _cull_sphere_from_cone()),
]
