"""The doppler pitch smoothed with a time constant (enhanced/sound/snd.cpp: sub_1406AD9E0; B0067;
docs/cgame-frame.md 4.11).

- With no smoothing (snd_dopplerSmoothing and the parameters' 0) the enhanced function is the Store build's: the
  same calls and writes for 400 of the differential test's inputs.
- A source approaching a still listener at a constant speed: from pitch 1, the enhanced pitch over time is the same
  at 60 fps (16/17 ms updates), 144 Hz and 500 fps (2 ms), the closed form c + (1 - c) * (k / (k + 1))^(t / 16.667)
  within float rounding; the original's at 500 fps has settled long before its 60 fps one (B0067).
"""
import random
import struct

import test_snd as d
from frame_sim import World, rd, wmem
from syms import va
from win32_display import arg

SYMBOL = d.SYMBOL


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def test_original_without_smoothing(env):
    r = random.Random(3368)
    lo, hi = env.dll.base, env.dll.base + env.dll.size
    for n in range(400):
        case = d._input(r, smoothing=0.0)
        theirs = env.machine.call(env.table[SYMBOL], case["args"], "void", case["setup"], _hooks(env, case["fakes"]), {})
        mine = env.machine.call(env.dll.exports[SYMBOL], case["args"], "void", case["setup"], _hooks(env, case["fakes"]),
                                {})
        assert mine[3] == theirs[3], n
        assert {a: v for a, v in mine[2].items() if not lo <= a < hi} == theirs[2], n


def _approach(env, pattern, total, original=False, k=7.0):
    """Channel 8 (the first) with doppler (the dvars' parameters: snd_dopplerAuditionEnable on), its source at x = 1000 - 100 t (units, seconds) towards a listener at 0:
    [(t ms, pitch)] after every update."""
    w = World(env)
    w.poke(va("cg_entitiesArray") + 0x18, struct.pack("<3f", 0.0, 0.0, 0.0))
    w.poke(va("unk_14BAF3368"), struct.pack("<i", 0))
    w.poke(va("unk_14BAF34F8"), struct.pack("<32f", *([1.0] * 32)))
    w.poke(va("unk_14BAF3378"), struct.pack("<3f", 1000.0 - 0.1 * pattern[0], 0.0, 0.0))  # where the first update is
    base = va("unk_14BAEC804")
    for i in range(32):
        w.poke(base + 0xF8 * i + 0x74, struct.pack("<Q", d.ALIASES if i == 0 else 0))
    out, t, i = [], 0, 0
    while t < total:
        msec = pattern[i % len(pattern)]
        i += 1
        t += msec

        def setup(m, msec=msec):
            mu = m.m.mu
            names = ["snd_dopplerEnable", "snd_dopplerAuditionEnable", "snd_dopplerBaseSpeedOfSound",
                     "snd_dopplerPlayerVelocityScale", "snd_dopplerPitchMin", "snd_dopplerPitchMax",
                     "snd_dopplerSmoothing"]
            values = [b"\1\0\0\0", b"\1\0\0\0"] + [struct.pack("<f", v) for v in (500.0, 1.0, 0.5, 2.0, k)]
            for j, (n, v) in enumerate(zip(names, values)):
                mu.mem_write(d.DVARS + 0x40 * j + 0x10, v)
                m.u64(va(n), d.DVARS + 0x40 * j)
            m.u64(va("unk_14BAF3578"), 0)
            alias = bytearray(0xC8)
            alias[0xB8] = 1
            mu.mem_write(d.ALIASES, bytes(alias))
            w.apply(m)

        def source(mu, t=t):
            mu.mem_write(arg(mu, 1), struct.pack("<3f", 1000.0 - 0.1 * t, 0.0, 0.0))
            return None
        fakes = {"?sub_1402C0600@@YAXHPEAMPEAX@Z": source, "?sub_1404DC1A0@@YA_NH@Z": lambda mu: 0}
        target = env.table[SYMBOL] if original else env.dll.exports[SYMBOL]
        _, _, written, _ = env.machine.call(target, [msec], "void", setup, _hooks(env, fakes), {})
        w.mem.update(written)
        out.append((t, struct.unpack("<f", w.read(va("unk_14BAF34F8"), 4))[0]))
    return out


def test_same_smoothing_over_time_at_every_frame_rate(env):
    c, k = 500.0 / 400.0, 7.0
    runs = {name: _approach(env, pattern, 400) for name, pattern in
            (("60 fps", [17, 16, 17]), ("144 Hz", [7, 7, 7, 6, 7, 7]), ("500 fps", [2]))}
    for name, run in runs.items():
        for t, pitch in run[1:]:   # the first update only records the positions
            first = run[0][0]
            want = c + (1.0 - c) * (k / (k + 1)) ** ((t - first) / (1000 / 60))
            assert abs(pitch - want) < 2e-3, (name, t, pitch, want)
    orig_fast = dict(_approach(env, [2], 120, original=True))
    orig_slow = dict(_approach(env, [17, 16, 17], 120, original=True))
    assert abs(orig_fast[100] - c) < 1e-3 and abs(orig_slow[100] - c) > 0.05, (orig_fast[100], orig_slow[100])
