"""Differential cases for win32/win_shared.cpp: Sys_Milliseconds and Sys_SnapVector, against both builds.

Sys_Milliseconds: timeGetTime is scripted (a random time, near the 32-bit wrap too, advancing between the two calls
of a first call) and logged; the time bases start initialized or not, with random values. rdtsc is the harness's
deterministic counter, so the stored sys_counterBase is compared too.

Sys_SnapVector: vectors of halves (positive and negative, so the halves-up rounding shows), values just below and
above .5, integers, huge values beyond 2^23, signed zeros, infinities and NaNs, through the CRT's floorf.
"""
import math
import random
import struct

from syms import va
from win32_display import CURRENT


def _clock(r):
    start = r.choice([0, 1, 1000, 0x7FFFFFFF, 0xFFFFFFF0, r.getrandbits(32)])
    steps = [r.choice([0, 0, 1, 2, 15, 1000]) for _ in range(3)]

    def run(m):
        state = {"now": start, "i": 0}

        def time_get_time(mu):
            m.observed.append(("import", "timeGetTime"))
            v = state["now"]
            state["now"] = (v + steps[state["i"] % 3]) & 0xFFFFFFFF
            state["i"] += 1
            from unicorn.x86_const import UC_X86_REG_RAX
            mu.reg_write(UC_X86_REG_RAX, v)
        m.on_import("winmm.dll!timeGetTime", time_get_time)
    return run


def _ms_input(r):
    initialized = r.choice([0, 0, 1, 1, 2, -1])
    base = r.choice([0, 1, 1000, 0x7FFFFFFF, r.getrandbits(32)])
    counter = r.getrandbits(64)
    clock = _clock(r)

    def setup(w):
        CURRENT["m"] = w.m
        clock(w.m)
        w.write(va("sys_timeBasesInitialized"), struct.pack("<i", initialized))
        w.u64(va("sys_counterBase"), counter)
        w.u32(va("sys_timeBase"), base)
    return {"args": [], "setup": setup}


def _component(r):
    return r.choice([0.0, -0.0, 0.5, -0.5, 1.5, -1.5, 2.5, -2.5, 0.49999997, 0.50000006, -0.49999997, 249.8,
                     243.4, -6.4, 190.0, 8388607.5, 8388608.0, 1e10, -1e10, float("inf"), float("-inf"),
                     float("nan"), r.uniform(-1000, 1000), r.uniform(-2, 2), round(r.uniform(-500, 500)) + 0.5])


def _snap_input(r):
    return [struct.pack("<3f", *(_component(r) for _ in range(3)))]


r = random.Random(51)
CASES = [
    {"symbol": "?Sys_Milliseconds@@YAHXZ", "ret": "int", "inputs": [_ms_input(r) for _ in range(300)]},
    {"symbol": "?Sys_SnapVector@@YAXPEAM@Z", "ret": "void", "inputs": [_snap_input(r) for _ in range(1000)]},
]
