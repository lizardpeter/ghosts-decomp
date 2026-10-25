"""The ramp (enhanced/cgame_mp/cg_draw_mp.cpp: sub_1402AA2A0 and CG_RampTick; docs/cgame-frame.md 4.11).

- Outside the tick loop the enhanced sub_1402AA2A0 is the Store build's (800 of the differential test's inputs).
- CG_RampTick with a frame time is the Store build's function with cls.frametime set to it.
(The ramp in the ticks at 5 ms: test_tick.py's stage-3 (a) test.)
"""
import random
import struct

import test_cg_draw as d
from syms import va

SYMBOL = "?sub_1402AA2A0@@YAXW4LocalClientNum_t@@@Z"
TICK = "?CG_RampTick@@YAXW4LocalClientNum_t@@H@Z"


def _hooks(env, fakes):
    hooks = {}
    for s, fn in fakes.items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return hooks


def test_ramp_is_the_original(env):
    r = random.Random(1402)
    lo, hi = env.dll.base, env.dll.base + env.dll.size
    for n in range(800):
        case = d._ramp_input(r)
        theirs = env.machine.call(env.table[SYMBOL], [0], "void", case["setup"], _hooks(env, case["fakes"]), {})
        mine = env.machine.call(env.dll.exports[SYMBOL], [0], "void", case["setup"], _hooks(env, case["fakes"]), {})
        assert mine[3] == theirs[3], n
        assert {a: v for a, v in mine[2].items() if not lo <= a < hi} == theirs[2], n
        msec = r.choice([5, 1, 16])

        def setup(w, case=case, msec=msec):
            case["setup"](w)
            w.write(va("cls") + 0x118, struct.pack("<i", msec))
        theirs = env.machine.call(env.table[SYMBOL], [0], "void", setup, _hooks(env, case["fakes"]), {})
        mine = env.machine.call(env.dll.exports[TICK], [0, msec], "void", case["setup"], _hooks(env, case["fakes"]), {})
        assert mine[3] == theirs[3], n
        assert {a: v for a, v in mine[2].items() if not lo <= a < hi} == theirs[2], n
