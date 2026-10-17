"""The frame-latency wait (enhanced/gfx_d3d/r_init.cpp, records/patches.tsv P0004).

What must hold:
- the flip-model swap chain is created with FRAME_LATENCY_WAITABLE_OBJECT; its IDXGISwapChain2 gets
  SetMaximumFrameLatency(1) and hands out the waitable object, which replaces (and closes) the previous one, and the
  counts start again; without IDXGISwapChain2 or the flag there is no object and nothing waits;
- a lost device's new swap chain gets a new object the same way;
- each successful present on the render thread is counted while there is an object; a present sent to the window
  procedure isn't, and makes the next frame take every pending signal instead;
- R_SyncGpu, after the lost-device check and its first clock read, waits once for each present counted since the last
  wait, with a timeout of two refresh periods (at least 50 ms, at most 1 s), alertable, repeating a wait an APC ended;
  a timed-out wait stops the waits and makes the next frame take every pending signal; otherwise R_SyncGpu does
  exactly what the original does (compared call for call with the Store build's R_SyncGpu on the differential test's
  inputs).
"""
import struct

import test_frame_pacing as pacing
import test_present as present
from frame_model import MAIN_THREAD, log
from syms import va
from win32_display import u32

SYNC = "?R_SyncGpu@@YAXP6AH_K@Z@Z"
SWAPCHAIN2 = bytes.fromhex("c42abea8" "9f19" "4649") + bytes([0xB3, 0x31, 0x79, 0x59, 0x9F, 0xB9, 0x8D, 0xE7])
SET_LATENCY2, GET_WAITABLE = 31 * 8, 33 * 8
WAITABLE = present.WAITABLE
WAIT_OBJECT_0, WAIT_TIMEOUT, WAIT_IO_COMPLETION = 0, 0x102, 0xC0
VID_FREQUENCY = 0x18  # vidConfig.displayFrequency


def _u32(written, address, default=0):
    raw = b"".join(written.get(address + i, bytes([(default >> (8 * i)) & 0xFF])) for i in range(4))
    return struct.unpack("<I", raw)[0]


def _u64(written, address, default=0):
    return _u32(written, address, default & 0xFFFFFFFF) | _u32(written, address + 4, default >> 32) << 32


# ---- Creating the swap chain ---------------------------------------------------------------------------------

def test_waitable_object_acquired(env):
    value, descs, written, observed = present._create_device(env)
    assert value == 1 and descs == [(2, 1, 4, 0x842)], descs
    coms = [(o[1], o[2]) for o in observed if o[0] == "com"]
    create = coms.index((present.FAC, present.CREATE_SWAP_CHAIN))
    qi = coms.index((present.SWC, present.QI))
    assert create < qi < coms.index((present.UNK, SET_LATENCY2)) < coms.index((present.UNK, GET_WAITABLE)), coms
    swc_qi = present._coms(observed, present.SWC, present.QI)
    assert swc_qi[0][4] == ("bytes", SWAPCHAIN2), swc_qi
    assert present._coms(observed, present.UNK, SET_LATENCY2)[0][4] == 1
    releases = [i for i, c in enumerate(coms) if c == (present.UNK, present.RELEASE)]
    assert any(i > coms.index((present.UNK, GET_WAITABLE)) for i in releases), coms  # IDXGISwapChain2 released
    assert _u64(written, env.data("s_frameLatencyWaitable")) == WAITABLE
    # the counts start again (the setup left 7, 6 and a pending resync)
    assert _u32(written, env.data("s_presentCount"), 7) == 0
    assert _u32(written, env.data("s_waitedPresentCount"), 6) == 0
    assert written.get(env.data("s_resyncFrameLatency"), b"\x01") == b"\x00"
    assert not [o for o in observed if o[:2] == ("import", "CloseHandle")]


def test_previous_waitable_object_closed(env):
    _, _, written, observed = present._create_device(env, old_waitable=0x5550)
    assert [o for o in observed if o[:2] == ("import", "CloseHandle")] == [("import", "CloseHandle", 0x5550)]
    assert _u64(written, env.data("s_frameLatencyWaitable"), 0x5550) == WAITABLE


def test_no_waitable_object_without_swapchain2(env):
    _, descs, written, observed = present._create_device(env, swapchain2=False, old_waitable=0x5550)
    assert descs == [(2, 1, 4, 0x842)]
    assert _u64(written, env.data("s_frameLatencyWaitable"), 0x5550) == 0
    assert not present._coms(observed, present.UNK, GET_WAITABLE)


def test_no_waitable_object_when_flag_refused(env):
    for kwargs in ({"waitable_ok": False}, {"flip_ok": False}):
        _, _, written, observed = present._create_device(env, old_waitable=0x5550, **kwargs)
        assert _u64(written, env.data("s_frameLatencyWaitable"), 0x5550) == 0, kwargs
        assert not present._coms(observed, present.SWC, present.QI), kwargs


def test_lost_device_gets_new_waitable_object(env):
    descs, order, written, observed = present._recover(env, old_waitable=0x5550)
    assert descs == [(2, 1, 4, 0x842)]
    create = order.index("create swap chain")
    assert create < order.index(present.QI) < order.index(GET_WAITABLE), order
    assert ("import", "CloseHandle", 0x5550) in observed
    assert _u64(written, env.data("s_frameLatencyWaitable"), 0x5550) == WAITABLE


# ---- Counting presents ---------------------------------------------------------------------------------------

def _counted(env, waitable, **kwargs):
    extra = {"s_frameLatencyWaitable": ("q", waitable), "s_presentCount": ("i", 41), "s_resyncFrameLatency": ("b", 0)}
    _, written = present._swap(env, extra=extra, written=True, **kwargs)
    return _u32(written, env.data("s_presentCount"), 41), written.get(env.data("s_resyncFrameLatency"), b"\x00")


def test_present_is_counted(env):
    assert _counted(env, WAITABLE) == (42, b"\x00")
    assert _counted(env, WAITABLE, vsync=1, tearing=False) == (42, b"\x00")


def test_present_not_counted_without_waitable_object(env):
    assert _counted(env, 0) == (41, b"\x00")


def test_window_procedure_present_resyncs(env):
    # the swap chain is fullscreen, r_displayMode windowed: the window procedure presents (WM_USER)
    assert _counted(env, WAITABLE, fullscreen=True, display_mode=2) == (41, b"\x01")
    assert _counted(env, WAITABLE, fullscreen=True) == (42, b"\x00")  # matching: presents here


# ---- R_SyncGpu -----------------------------------------------------------------------------------------------

def _original(env, symbol, inp):
    hooks = {}
    for s, fn in inp["fakes"].items():
        for a in (env.dll.exports.get(s), env.table.get(s)):
            if a:
                hooks[a] = fn
    return env.machine.call(env.table[symbol], inp["args"], "void", inp["setup"], hooks)


def _enhanced(env, inp, state=None, waits=None, frequency=(60, 1)):
    """The enhanced R_SyncGpu on a pacing input, with the wait state `state` and WaitForSingleObjectEx's results."""
    results = list(waits or [])
    base = inp["setup"]

    def wait_ex(mu):
        from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX
        log("import", "WaitForSingleObjectEx", mu.reg_read(UC_X86_REG_RCX), u32(mu.reg_read(UC_X86_REG_RDX)),
            u32(mu.reg_read(UC_X86_REG_R8)))
        mu.reg_write(UC_X86_REG_RAX, results.pop(0) if results else WAIT_OBJECT_0)

    def setup(w):
        base(w)
        w.m.on_import("kernel32.dll!WaitForSingleObjectEx", wait_ex)
        w.write(va("vidConfig") + VID_FREQUENCY, struct.pack("<II", *frequency))
        s = dict({"waitable": 0, "presented": 0, "waited": 0, "resync": 0}, **(state or {}))
        w.u64(env.data("s_frameLatencyWaitable"), s["waitable"])
        w.u32(env.data("s_presentCount"), s["presented"])
        w.u32(env.data("s_waitedPresentCount"), s["waited"])
        w.write(env.data("s_resyncFrameLatency"), bytes([s["resync"]]))
    return env.call(SYNC, inp["args"], "void", setup=setup, fakes=inp["fakes"])


def _names(env):
    """Function addresses of either image by name, so pointers passed as arguments compare across the two."""
    if not hasattr(env, "_fn_names"):
        names = {v: s for s, v in env.table.items()}
        names.update({v: s for s, v in env.dll.exports.items()})
        env._fn_names = names
    return env._fn_names


def _normalized(env, observed):
    names = _names(env)
    return [tuple(names.get(x, x) if isinstance(x, int) and x > 0x100000000 else x for x in o) for o in observed]


def _waits(observed):
    return [o[2:] for o in observed if o[:2] == ("import", "WaitForSingleObjectEx")]


def _without_waits(observed):
    return [o for o in observed if o[:2] != ("import", "WaitForSingleObjectEx")]


def _inputs(seed, n):
    return pacing._inputs(seed, n=n, args=lambda r: [r.choice([0, pacing.CALLBACK, pacing.CALLBACK])],
                          thread=MAIN_THREAD)


def _dll_static(env, address):
    return env.dll.base <= address < env.dll.base + 0x10000000


def _exe_writes(env, written):
    return {a: v for a, v in written.items() if not _dll_static(env, a)}


def test_sync_gpu_is_the_original_otherwise(env):
    """With no waitable object, and with one but no present since the last wait, R_SyncGpu is the Store build's."""
    for i, inp in enumerate(_inputs(0xE4, 160)):
        state = None if i % 2 else {"waitable": WAITABLE, "presented": 9, "waited": 9}
        want = _original(env, SYNC, inp)
        got = _enhanced(env, inp, state)
        assert not _waits(got[3]), (i, got[3])
        assert got[0] == want[0], (i, got[0], want[0])
        assert _exe_writes(env, got[2]) == want[2], (i, sorted(set(got[2]) ^ set(want[2])))
        assert _normalized(env, got[3]) == _normalized(env, want[3]), (i, got[3], want[3])


def test_sync_gpu_waits_once_per_present_first(env):
    frames = 0
    for i, inp in enumerate(_inputs(0xE5, 60)):
        want = _original(env, SYNC, inp)
        got = _enhanced(env, inp, {"waitable": WAITABLE, "presented": 5, "waited": 3})
        if not [o for o in want[3] if o == ("call", "Sys_Milliseconds")]:
            # the lost-device check failed (no device, or a lost one): no frame, no wait
            assert not _waits(got[3]), (i, got[3])
            assert _u32(got[2], env.data("s_waitedPresentCount"), 3) == 3
            continue
        assert _waits(got[3]) == [(WAITABLE, 50, 1)] * 2, (i, _waits(got[3]))
        # the waits come right after the frame's first clock read, before anything else R_SyncGpu does
        first = got[3].index(("call", "Sys_Milliseconds"))
        assert got[3][first + 1][:2] == ("import", "WaitForSingleObjectEx") and got[3][first + 2][1] == \
            "WaitForSingleObjectEx", got[3][first:first + 4]
        assert _normalized(env, _without_waits(got[3])) == _normalized(env, want[3]), i
        assert _exe_writes(env, got[2]) == want[2], i
        assert _u32(got[2], env.data("s_waitedPresentCount"), 3) == 5
        frames += 1
    assert frames >= 30, frames


def _usable(env):
    """An R_SyncGpu input on a usable device (the lost-device check passes)."""
    for inp in _inputs(0xE6, 60):
        want = _original(env, SYNC, inp)
        if ("call", "Sys_Milliseconds") in want[3]:
            return inp
    raise AssertionError("no input with a usable device")


def test_wait_timeout_from_refresh_rate(env):
    inp = _usable(env)
    for frequency, timeout in (((60, 1), 50), ((30, 1), 67), ((144, 1), 50), ((60000, 1001), 50),
                               ((24000, 1001), 84), ((0, 0), 50), ((1, 1), 1000)):
        got = _enhanced(env, inp, {"waitable": WAITABLE, "presented": 1, "waited": 0}, frequency=frequency)
        assert _waits(got[3]) == [(WAITABLE, timeout, 1)], (frequency, _waits(got[3]))


def test_apc_repeats_the_wait(env):
    inp = _usable(env)
    got = _enhanced(env, inp, {"waitable": WAITABLE, "presented": 2, "waited": 1},
                    waits=[WAIT_IO_COMPLETION, WAIT_IO_COMPLETION, WAIT_OBJECT_0])
    assert _waits(got[3]) == [(WAITABLE, 50, 1)] * 3
    assert _u32(got[2], env.data("s_waitedPresentCount"), 1) == 2
    assert got[2].get(env.data("s_resyncFrameLatency"), b"\x00") == b"\x00"


def test_timeout_stops_and_resyncs(env):
    inp = _usable(env)
    got = _enhanced(env, inp, {"waitable": WAITABLE, "presented": 7, "waited": 3},
                    waits=[WAIT_OBJECT_0, WAIT_TIMEOUT, WAIT_OBJECT_0])
    assert _waits(got[3]) == [(WAITABLE, 50, 1)] * 2, _waits(got[3])
    assert _u32(got[2], env.data("s_waitedPresentCount"), 3) == 7
    assert got[2][env.data("s_resyncFrameLatency")] == b"\x01"
    want = _original(env, SYNC, inp)
    assert _normalized(env, _without_waits(got[3])) == _normalized(env, want[3])


def test_resync_takes_every_pending_signal(env):
    inp = _usable(env)
    got = _enhanced(env, inp, {"waitable": WAITABLE, "presented": 12, "waited": 4, "resync": 1},
                    waits=[WAIT_OBJECT_0, WAIT_IO_COMPLETION, WAIT_OBJECT_0, WAIT_TIMEOUT, WAIT_OBJECT_0])
    assert _waits(got[3]) == [(WAITABLE, 0, 1)] * 4, _waits(got[3])
    assert _u32(got[2], env.data("s_waitedPresentCount"), 4) == 12
    assert got[2][env.data("s_resyncFrameLatency")] == b"\x00"


def test_no_wait_without_waitable_object_even_with_presents(env):
    inp = _usable(env)
    got = _enhanced(env, inp, {"waitable": 0, "presented": 5, "waited": 0, "resync": 1})
    assert not _waits(got[3])

