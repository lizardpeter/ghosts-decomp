"""Differential cases for the doppler pitch (sound/snd.cpp: sub_1406AD9E0), against the Store build.

The update's msec (0, negative, 1, 5, 16, 50), the first update (the count 0), the listener's position (the first
entity's pose) now and at the last update, the parameters from the dvars or the override (with and without
snd_dopplerAuditionEnable), 32 channels: doppler on or off, the channel test 1404DC1A0 (faked), no alias, an alias
without doppler, an alias with its own parameters or none, the source's position (1402C0600, faked) moving towards,
away, across, standing still (closer than 0.001), and NaN; the pitch limits crossed both ways and the 1 - (r - 1)
remapping below 1; the smoothing weight 0, 1, 7.
"""
import random
import struct

from harness import SCRATCH
from syms import va
from win32_display import CURRENT, arg

STORE = "iw6mp64_MSStore_ship"
SYMBOL = "?sub_1406AD9E0@@YAXH@Z"
DVARS = SCRATCH + 0x10000
OVERRIDE = SCRATCH + 0x11000
ALIASES = SCRATCH + 0x12000
OWN = SCRATCH + 0x18000


def _f(r, *common):
    return r.choice([*common, r.uniform(-500, 500), r.uniform(-5, 5)])


def _parms(r, smoothing=None):
    k = r.choice([0.0, 1.0, 7.0])
    return struct.pack("<8x5f", r.choice([343.0, 1000.0, 50.0]), r.choice([1.0, 0.5, 0.0]),
                       r.choice([0.5, 0.8, 1.0]), r.choice([1.5, 2.0, 1.0]), k if smoothing is None else smoothing)


def _input(r, smoothing=None):
    msec = r.choice([0, -3, 1, 5, 16, 50])
    count = r.choice([0, 1, 16])
    listener = [_f(r, 0.0, 100.0) for _ in range(3)]
    last_listener = [v + r.choice([0.0, 1.0, -3.0, 20.0]) for v in listener]
    override = r.choice([0, OVERRIDE])
    flags = (r.choice([1, 1, 0]), r.choice([0, 0, 1]))
    dvar_values = [r.choice([343.0, 500.0]), r.choice([1.0, 0.25]), r.choice([0.5, 0.75]),
                   r.choice([1.5, 2.0]), r.choice([0.0, 3.0, 7.0])]
    if smoothing is not None:
        dvar_values[4] = smoothing
    channels = []
    for i in range(32):
        kind = r.choice(["none", "off", "own", "global", "global", "global"])
        alias = 0 if kind == "none" else ALIASES + 0x100 * i
        channels.append((r.choice([5, 9, 0x7FE]), alias, kind, _parms(r, smoothing)))
    free = [r.choice([0, 0, 0, 1]) for _ in range(32)]
    sources = []
    for i in range(32):
        motion = r.choice(["towards", "away", "across", "still", "same", "nan", "near"])
        base = [v + r.choice([30.0, -80.0, 500.0]) for v in listener]
        last = list(base)
        if motion == "towards":
            last = [b + (b - l) * 0.05 for b, l in zip(base, listener)]
        elif motion == "away":
            last = [b - (b - l) * 0.05 for b, l in zip(base, listener)]
        elif motion == "across":
            last = [base[0], base[1] + 9.0, base[2]]
        elif motion == "same":
            base = list(listener)
        elif motion == "near":   # closer than 0.01 but farther than 0.001
            base = [listener[0] + r.choice([0.005, 0.002, 0.0005]), listener[1], listener[2]]
            last = list(base)
        elif motion == "nan":
            base[1] = float("nan")
        sources.append((base, last))
    pitches = [r.choice([1.0, 0.9, 1.3, float("nan")]) for _ in range(32)]

    def setup(w):
        CURRENT["m"] = w.m
        mu = w.m.mu
        w.write(va("cg_entitiesArray") + 0x18, struct.pack("<3f", *listener))
        w.write(va("unk_14BAF3368"), struct.pack("<i", count))
        w.write(va("unk_14BAF336C"), struct.pack("<3f", *last_listener))
        w.write(va("unk_14BAF3378"), b"".join(struct.pack("<3f", *s[1]) for s in sources))
        w.write(va("unk_14BAF34F8"), struct.pack("<32f", *pitches))
        w.u64(va("unk_14BAF3578"), override)
        mu.mem_write(OVERRIDE, _parms(random.Random(len(channels)), smoothing))
        names = ["snd_dopplerEnable", "snd_dopplerAuditionEnable", "snd_dopplerBaseSpeedOfSound",
                 "snd_dopplerPlayerVelocityScale", "snd_dopplerPitchMin", "snd_dopplerPitchMax", "snd_dopplerSmoothing"]
        values = [bytes([flags[0]]) + bytes(3), bytes([flags[1]]) + bytes(3)] + [struct.pack("<f", v) for v in dvar_values]
        for k, (n, v) in enumerate(zip(names, values)):
            mu.mem_write(DVARS + 0x40 * k + 0x10, v)
            w.u64(va(n), DVARS + 0x40 * k)
        base = va("unk_14BAEC804")
        for i, (entity, alias, kind, parms) in enumerate(channels):
            w.write(base + 0xF8 * i, struct.pack("<i", entity))
            w.write(base + 0xF8 * i + 0x74, struct.pack("<Q", alias))
            if alias:
                a = bytearray(0xC8)
                a[0xB8] = 0 if kind == "off" else 1
                own = OWN + 0x40 * i if kind == "own" else 0
                struct.pack_into("<Q", a, 0xC0, own)
                mu.mem_write(alias, bytes(a))
                if own:
                    mu.mem_write(own, parms)

    calls = {"n": 0}

    def source(mu):
        i = calls["n"]
        calls["n"] += 1
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", "sub_1402C0600", arg(mu, 0) & 0xFFFFFFFF))
        mu.mem_write(arg(mu, 1), struct.pack("<3f", *sources[i % 32][0]))
        return None

    def reset_setup(w):
        calls["n"] = 0
        setup(w)

    def channel_test(mu):
        c = arg(mu, 0) & 0xFFFFFFFF
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", "sub_1404DC1A0", c))
        return free[(c - 8) & 31]
    return {"args": [msec], "setup": reset_setup,
            "fakes": {"?sub_1402C0600@@YAXHPEAMPEAX@Z": source, "?sub_1404DC1A0@@YA_NH@Z": channel_test}}


r = random.Random(1406)
CASES = [
    {"symbol": SYMBOL, "build": STORE, "ret": "void", "inputs": [_input(r) for _ in range(800)]},
]
