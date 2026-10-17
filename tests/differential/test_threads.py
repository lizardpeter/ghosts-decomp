"""Differential cases for qcommon/threads.cpp (the hand-off between the main thread and the render thread) against
the Store build.

Every input runs on a random thread (main, render or another) with random hand-off state (g_renderWaitCount,
smpData, databaseCompletedEvent2) and scripted results for each event wait (frame_model.Kernel), so the original and
the reconstruction must make the same kernel calls with the same arguments and leave the same statics behind.
"""
import random

from frame_model import (BACKEND0, BACKEND1, MAIN_THREAD, NO_OWNERSHIP, OTHER_THREAD, RENDER_PAUSED, RENDER_THREAD,
                         RENDERER_RUNNING, WAIT_TIMEOUT, Kernel, fake, write_thread_state)

STORE = "iw6mp64_MSStore_ship"
HANDLES = (RENDER_PAUSED, NO_OWNERSHIP, RENDERER_RUNNING, BACKEND0, BACKEND1)


def _waits(r):
    """Scripted results: a few timeouts (or failures) before each event is signalled."""
    out = {}
    for h in HANDLES:
        out[h] = [r.choice([WAIT_TIMEOUT, WAIT_TIMEOUT, 0xFFFFFFFF, 0x80]) for _ in range(r.choice([0, 0, 1, 2, 5]))]
    return out


def _inputs(seed, n=150, args=lambda r: []):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        thread = r.choice([MAIN_THREAD, MAIN_THREAD, RENDER_THREAD, OTHER_THREAD])
        count = r.choice([0, 0, 1, 1, 2, 3, -1, 0x7FFFFFFF, r.getrandbits(32)])
        smp = r.choice([0, 0, 0x14A3AE200, r.getrandbits(64)])
        ready2 = r.choice([0, 1, 2, r.getrandbits(32)])
        waits = _waits(r)

        def setup(w, thread=thread, count=count, smp=smp, ready2=ready2, waits=waits):
            Kernel(thread, waits).install(w.m)
            write_thread_state(w, count, smp, ready2)
        out.append({"args": args(r), "setup": setup})
    return out


FAKES = {"?Sys_LoadingKeepAlive@@YAXXZ": fake("Sys_LoadingKeepAlive")}


def case(symbol, ret, seed, args=lambda r: []):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": _inputs(seed, args=args), "fakes": FAKES}


CASES = [
    case("?Sys_IsMainThread@@YA_NXZ", "char", 2959),
    case("?Sys_IsRenderThread@@YA_NXZ", "char", 2931),
    case("?Sys_FrontEndSleep@@YAXXZ", "void", 2075),
    case("?sub_14046F5C0@@YAHXZ", "int", 0x5C0),
    case("?Sys_IsRendererReady@@YAHXZ", "int", 2108),
    case("?Sys_IsDatabaseReady2@@YAHXZ", "int", 2838),
    case("?Sys_NotifyRenderer@@YAXXZ", "void", 2163),
    case("?Sys_ReleaseThreadOwnership@@YAXXZ", "void", 3379),
    case("?Sys_RenderCompleted@@YAXXZ", "void", 1508),
    case("?Sys_RendererSleep@@YAPEAXXZ", "int64", 1486),
    case("?sub_14046F320@@YAHXZ", "int", 0x320),
    case("?sub_14046F570@@YAHXZ", "int", 0x570),
    case("?sub_14046FB70@@YAXXZ", "void", 0xB70),
    case("?sub_14046FB80@@YAXXZ", "void", 0xB80),
    case("?sub_14046FFD0@@YAXXZ", "void", 0xFD0),
    case("?Sys_WakeRenderer@@YAXPEAX@Z", "void", 2132,
         args=lambda r: [r.choice([0, 0x14A3AE200, 0x14AA33280, r.getrandbits(64)])]),
]
