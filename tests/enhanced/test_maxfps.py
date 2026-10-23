"""com_maxfps up to 1000 (enhanced/qcommon/common.cpp).

What must hold: the enhanced Com_InitDvars makes exactly the Store build's registrations, in the same order, with the
same names, defaults, limits, flags and descriptions, and stores the same dvar pointers, except that com_maxfps'
maximum is 1000 instead of 100 (its default stays 85, its minimum 0: uncapped).
"""
from test_common_dvars import Registry

SYMBOL = "?Com_InitDvars@@YAXXZ"


def _run(env, original, cpus):
    reg = Registry(cpus)
    fakes = reg.fakes()
    if original:
        hooks = {}
        for s, fn in fakes.items():
            for a in (env.dll.exports.get(s), env.table.get(s)):
                if a:
                    hooks[a] = fn
        _, _, written, observed = env.machine.call(env.table[SYMBOL], [], "void", reg.setup, hooks)
    else:
        _, _, written, observed = env.call(SYMBOL, [], setup=reg.setup, fakes=fakes)
    return written, observed


def test_only_the_maximum_changes(env):
    for cpus in (0, 1, 2, 16):
        want_w, want = _run(env, True, cpus)
        got_w, got = _run(env, False, cpus)
        assert len(got) == len(want) > 20, (len(got), len(want))
        maxfps = [i for i, o in enumerate(want) if o[:3] == ("call", "Int", b"com_maxfps")]
        assert len(maxfps) == 1, want
        i = maxfps[0]
        assert want[i][3:6] == (85, 0, 100), want[i]
        assert got[i][:6] == ("call", "Int", b"com_maxfps", 85, 0, 1000), got[i]
        assert got[i][6:] == want[i][6:]  # flags and description
        assert got[:i] + got[i + 1:] == want[:i] + want[i + 1:], cpus
        assert got_w == want_w, cpus  # the same dvar pointers stored in the same globals
