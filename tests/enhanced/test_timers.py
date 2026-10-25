"""The timed repeats on the microsecond clock (enhanced/cgame/cg_weapons.cpp: sub_1402FB790; B0079;
docs/cgame-frame.md 4.11).

- With a timescale of 1 and the clock on whole milliseconds the enhanced function is the Store build's: the same
  calls with the same arguments and the same writes, for 500 of the differential test's inputs.
- At a timescale of 0.5 the repeats advance by the same scaled milliseconds over the same time at 1 ms and at
  16/17 ms frames, and queue the same number of events (the original advances them by 0 at 1 ms frames: they would
  never run out at 1000 fps).
"""
import struct

import test_cg_weapons as d
from frame_sim import World, rd, wmem
from syms import va

SYMBOL = "?sub_1402FB790@@YAXXZ"
US = "?Sys_Microseconds@@YA_JXZ"


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def test_original_at_timescale_1_on_whole_milliseconds(env):
    import random
    r = random.Random(1402)
    clock = env.data("s_repeatClock")
    lo, hi = env.dll.base, env.dll.base + env.dll.size
    for n in range(500):
        case = d._repeat_input(r, scale=1.0)
        now, last = case["now"], case["last"]
        if (now - last) & 0xFFFFFFFF > 0x7FFFFFFF:
            last_signed = last - (1 << 32)
        else:
            last_signed = last

        def setup(w, case=case, last=last_signed):
            case["setup"](w)
            w.write(clock, struct.pack("<qdi", last * 1000, 0.0, 1))
        fakes = dict(case["fakes"])
        fakes[US] = lambda mu, now=now: now * 1000
        theirs = env.machine.call(env.table[SYMBOL], [], "void", setup, _hooks(env, fakes), {})
        mine = env.machine.call(env.dll.exports[SYMBOL], [], "void", setup, _hooks(env, fakes), {})
        assert mine[3] == theirs[3], n
        assert {a: v for a, v in mine[2].items() if not lo <= a < hi} == theirs[2], n


def _repeats_run(env, pattern, total, original=False):
    """One active repeat (interval 40 ms, no count limit) driven frame by frame at timescale 0.5: (its elapsed ms,
    the events queued)."""
    w = World(env)
    clock = env.data("s_repeatClock")
    repeats, queue = va("unk_143E8EF80"), va("unk_143E8E580")
    w.poke(repeats, bytes(0x40 * 64))
    w.poke(queue, bytes(0x28 * 64))
    entry = bytearray(0x40)
    struct.pack_into("<IIIIiii", entry, 0x20, 0, 0, 40, 0, 1, 0, 1)
    w.poke(repeats, bytes(entry))
    w.poke(va("unk_143E8FF84"), struct.pack("<i", 1000))
    w.poke(clock, struct.pack("<qdi", 1000 * 1000, 0.0, 1))
    queued, t, i = [], 1000, 0
    dvar = 0x00500000 + 0xD9000
    while t < 1000 + total:
        t += pattern[i % len(pattern)]
        i += 1

        def scale(mu):
            from unicorn.x86_const import UC_X86_REG_XMM0
            mu.reg_write(UC_X86_REG_XMM0, struct.unpack("<I", struct.pack("<f", 0.5))[0])
            return None

        def handler(mu):
            queued.append(t)
            return None
        fakes = {"?Sys_Milliseconds@@YAHXZ": lambda mu, t=t: t, US: lambda mu, t=t: t * 1000,
                 "?sub_140460E10@@YAMXZ": scale, "?sub_14028EEA0@@YAIH_N@Z": lambda mu: 0,
                 "?sub_1402F6560@@YAXH_KHH_N111H@Z": handler}

        def setup(m):
            m.m.mu.mem_write(dvar + 0x10, struct.pack("<i", 0))
            m.u64(va("cl_paused"), dvar)
            w.apply(m)
        if original:
            _, _, written, _ = env.machine.call(env.table[SYMBOL], [], "void", setup, _hooks(env, fakes), {})
        else:
            _, _, written, _ = env.call(SYMBOL, [], "void", setup, fakes)
        w.mem.update(written)
    elapsed = struct.unpack("<I", w.read(repeats + 0x20, 4))[0]
    return elapsed, queued


def test_same_scaled_time_at_every_frame_rate(env):
    fast = _repeats_run(env, [1], 200)
    slow = _repeats_run(env, [16, 17, 17], 200)
    assert fast[0] == 100, fast[0]                       # 0.5 x 200 ms
    assert abs(slow[0] - fast[0]) <= 9, (slow[0], fast[0])   # within the last 60 fps frame
    assert len(fast[1]) == 2 and len(slow[1]) == 2, (fast[1], slow[1])
    original = _repeats_run(env, [1], 200, original=True)
    assert original[0] == 0 and not original[1], original   # B0079: the original never advances at 1 ms frames
