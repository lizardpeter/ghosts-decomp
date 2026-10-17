"""Differential cases for gfx_d3d/r_rendercmds.cpp (issuing a frame to the render thread, ownership of the device,
the loading screen's remote updates) against the Store build.

Inputs vary the thread (frame_model.Kernel), r_glob (ownership, render thread started, remote updates), the dvars
that choose the render thread (r_smp_backend, sys_smp_allowed), dx.deviceLost, the hand-off state in
qcommon/threads.cpp and frontEndDataOut (one of the two s_backEndData buffers, or NULL), whose issue state is
compared after the call. Callees outside the file are logged fakes, so the calls, their order and their arguments must
match too; the reconstructed qcommon/threads.cpp functions run for real against the kernel model.
"""
import random
import struct

from frame_model import (MAIN_THREAD, OTHER_THREAD, RENDER_THREAD, WAIT_TIMEOUT, Kernel, emulated_u32, fake,
                         write_thread_state, RENDERER_RUNNING, RENDER_PAUSED)
from syms import static, va
from win32_display import CURRENT

STORE = "iw6mp64_MSStore_ship"
BACKEND_DATA = (0x14A3AE200, 0x14A3AE200 + 0x645080)  # s_backEndData[2]
ISSUE = 0x151448
DX_DEVICE_LOST = 0x7CC8


def dvar(w, raw):
    p = w.alloc(bytes(0x60))
    w.write(p + 0x10, raw)
    return p


def _r_glob(r):
    owner, started = r.random() < 0.5, r.random() < 0.8
    remote = r.random() < 0.3
    unk04, unk08 = r.choice([0, 1, -1, 5]), r.choice([0, 1])
    notify = r.choice([0, 0, 1])
    nesting = r.choice([0, 0, 1, 1, 2, 3])
    frames = r.getrandbits(16)
    return struct.pack("<??xxii?xxxiii", owner, started, unk04, unk08, remote, notify, nesting, frames)


def _issue_state(r):
    return struct.pack("<9I", *(r.choice([0, 1, 2, 3, r.getrandbits(32)]) for _ in range(9)))


def _setup(r, thread=None, glob=None, data=True):
    thread = thread or r.choice([MAIN_THREAD, MAIN_THREAD, RENDER_THREAD, OTHER_THREAD])
    glob = glob or _r_glob(r)
    buf = r.choice(BACKEND_DATA) if data else 0
    state = _issue_state(r)
    used = r.choice([0, 1, 0x7FFFF, 0x100000, 0x1FFFFF, 0x3FFFFF, r.getrandbits(32)])
    cache_size = r.choice([0, 1, 0x8000, 0x10000, 0x20000, r.getrandbits(20)])
    threshold = r.choice([0.0, 0.5, 0.75, 0.95, 1.0, r.random()])
    backend, allowed = r.random() < 0.7, r.random() < 0.8
    lost = r.random() < 0.2
    count, smp = r.choice([0, 1, 2]), r.choice([0, 0, BACKEND_DATA[0]])
    ready2, db_ready2 = r.choice([0, 1]), r.choice([0, 0, 1])
    cache_flag = r.choice([0, 1, 7])
    waits = {RENDERER_RUNNING: [WAIT_TIMEOUT] * r.choice([0, 1]),
             RENDER_PAUSED: [WAIT_TIMEOUT] * r.choice([0, 1, 3])}

    def setup(w):
        Kernel(thread, waits).install(w.m)
        write_thread_state(w, count, smp, ready2)
        w.write(va("r_glob"), glob)
        w.u64(va("frontEndDataOut"), buf)
        if buf:
            w.write(buf + ISSUE, state)
            w.u64(buf + 0x150C40, buf + 0x150C48)  # the skinned cache's use, a u32
            w.u32(buf + 0x150C48, used)
        w.u64(va("r_smp_backend"), dvar(w, bytes([backend])))
        w.u64(va("sys_smp_allowed"), dvar(w, bytes([allowed])))
        w.u64(va("r_SkinnedCacheSize"), dvar(w, struct.pack("<i", cache_size)))
        w.u64(va("r_SkinnedCacheThreshold"), dvar(w, struct.pack("<f", threshold)))
        w.write(va("dx") + DX_DEVICE_LOST, bytes([lost]))
        w.u32(static("gfx_d3d/r_rendercmds.cpp", "g_databaseReady2"), db_ready2)
        w.u32(va("unk_14A37D504"), cache_flag)
    return setup


def _fakes(r):
    return {
        "?R_ProcessWorkerCmdsWithTimeout@@YAXP6AHXZH@Z": fake("R_ProcessWorkerCmdsWithTimeout", "qi"),
        "?R_RegisterRenderFrame@@YAXXZ": fake("R_RegisterRenderFrame"),
        "?sub_14066C920@@YAXXZ": fake("sub_14066C920"),
        "?R_UnlockSkinnedCache@@YAXXZ": fake("R_UnlockSkinnedCache"),
        "?R_CheckLostDevice@@YA_NXZ": fake("R_CheckLostDevice", "", r.choice([0, 1, 1])),
        "?sub_1406700E0@@YAXPEAUGfxBackEndData@@@Z": fake("sub_1406700E0", "q"),
        "?sub_140670A10@@YAXXZ": fake("sub_140670A10"),
        "?sub_140670450@@YAXXZ": fake("sub_140670450"),
        "?sub_140673B60@@YAXI@Z": fake("sub_140673B60", "i"),
        "?sub_1406791E0@@YAXXZ": fake("sub_1406791E0"),
        "?sub_140676A10@@YAXXZ": fake("sub_140676A10"),
        "?Sys_LoadingKeepAlive@@YAXXZ": fake("Sys_LoadingKeepAlive"),
        "?Sys_CheckQuitRequest@@YAXXZ": fake("Sys_CheckQuitRequest"),
    }


def _inputs(seed, n=200, args=lambda r: [], data=lambda r: r.random() < 0.9):
    r = random.Random(seed)
    return [{"args": args(r), "setup": _setup(r, data=data(r)), "fakes": _fakes(r)} for _ in range(n)]


# ---- R_PopRemoteScreenUpdate: the render thread's notifications arrive while the main thread sleeps ----------

def _pop_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        thread = r.choice([MAIN_THREAD, MAIN_THREAD, MAIN_THREAD, RENDER_THREAD])
        started = r.random() < 0.9
        nesting = r.choice([0, 1, 1, 2, 3, 5]) if thread == MAIN_THREAD and started else 0
        notify = r.choice([0, 0, 1])
        glob = struct.pack("<??xxii?xxxiii", r.random() < 0.5, started, 3, 0, r.random() < 0.3, notify, nesting,
                           r.getrandbits(16))
        # the render thread sets screenUpdateNotify after some of the main thread's sleeps
        after = sorted(r.sample(range(1, 12), 2))
        blocked = r.getrandbits(8)

        def on_sleep(m, k, after=after):
            if k in after:
                emulated_u32(m, va("r_glob") + 0x10, 1)

        def setup(w, thread=thread, glob=glob, on_sleep=on_sleep, blocked=blocked):
            Kernel(thread, on_sleep=on_sleep).install(w.m)
            write_thread_state(w)
            w.write(va("r_glob"), glob)
            w.u32(va("g_mainThreadBlocked"), blocked)
        out.append({"args": [], "setup": setup, "fakes": _fakes(r)})
    return out


# ---- R_ToggleSmpFrame: flips the GfxBackEndData buffers -------------------------------------------------------

GFX_BUF = 0x14A107B40
SKINNED_FRAME, REACTIVE_FRAME = 0x1BF9F8, 0x1BF9FC


def _toggle_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        base = _setup(r)
        smp_frame = r.choice([0, 1, 1, 2, 0xFFFFFFFF, r.getrandbits(32)])
        frame_index = r.choice([0, 0, 1])
        skinned, reactive = r.choice([0, 1, 2, -1, 4]), r.choice([0, 1, -1, -2, 3])
        consts = struct.pack("<4I", *(r.choice([0, 0, 1, r.getrandbits(32)]) for _ in range(4)))
        dvars = [r.random() < 0.5 for _ in range(3)]
        count = r.getrandbits(32)
        pending = [r.choice([0, 0, r.getrandbits(64)]) for _ in range(2)]

        def setup(w, base=base, smp_frame=smp_frame, frame_index=frame_index, skinned=skinned, reactive=reactive,
                  consts=consts, dvars=dvars, count=count, pending=pending):
            base(w)
            w.u32(static("gfx_d3d/r_rendercmds.cpp", "s_smpFrame"), smp_frame)
            w.u32(static("gfx_d3d/r_rendercmds.cpp", "g_frameIndex"), frame_index)
            w.u32(GFX_BUF + SKINNED_FRAME, skinned)
            w.u32(GFX_BUF + REACTIVE_FRAME, reactive)
            w.u32(GFX_BUF, count)
            w.write(va("unk_14A37D4E0"), consts)
            for name, on in zip(("r_asyncCompute", "r_useComputeSkinning", "r_subdiv"), dvars):
                w.u64(va(name), dvar(w, bytes([on])))
            # the data each buffer would have from its last frame
            for i, buf in enumerate(BACKEND_DATA):
                w.u64(buf + 0x150C50, pending[i])
                w.write(buf + 0x150D28, b"\x5a" * 0x104)
        fakes = {**_fakes(r), **TOGGLE_FAKES}
        if r.random() < 0.3:  # a callee moves g_frameIndex on: R_ToggleSmpFrame reads it again at its end
            def bump(mu):
                m = CURRENT["m"]
                m.observed.append(("call", "sub_14063D540"))
                emulated_u32(m, static("gfx_d3d/r_rendercmds.cpp", "g_frameIndex"), 1)
            fakes["?sub_14063D540@@YAXXZ"] = bump
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


TOGGLE_FAKES = {
    "?sub_14063F270@@YAXXZ": fake("sub_14063F270"),
    "?sub_1401B28E0@@YAXXZ": fake("sub_1401B28E0"),
    "?sub_1401B3720@@YAXXZ": fake("sub_1401B3720"),
    "?sub_1401B14D0@@YAXXZ": fake("sub_1401B14D0"),
    "?sub_14063D540@@YAXXZ": fake("sub_14063D540"),
    "?sub_14063D210@@YAXPEAX@Z": fake("sub_14063D210", "q"),
    "?sub_1401AC1B0@@YAXPEAX@Z": fake("sub_1401AC1B0", "q"),
}


def case(symbol, ret, inputs):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs}


CASES = [
    case("?R_SyncRenderThread@@YAXXZ", "void", _inputs(984)),
    case("?R_ReleaseThreadOwnership@@YAXXZ", "void", _inputs(1127)),
    case("?R_IssueRenderCommandsBegin@@YAXI@Z", "void",
         _inputs(1233, args=lambda r: [r.choice([0, 1, 2, 3, 3, 3, 4, 6, r.getrandbits(32)])], data=lambda r: True)),
    case("?R_IssueRenderCommandsShadow@@YAXXZ", "void", _inputs(1271, data=lambda r: True)),
    case("?R_IssueRenderCommandsOpaque@@YAXXZ", "void", _inputs(1280, data=lambda r: True)),
    case("?R_IssueRenderCommandsEmissive@@YAXXZ", "void", _inputs(1289, data=lambda r: True)),
    case("?sub_14064D030@@YAXXZ", "void", _inputs(0xD030, n=400, data=lambda r: True)),
    case("?R_PreAbortRenderCommands@@YAXXZ", "void", _inputs(1417)),
    case("?R_IsInRemoteScreenUpdate@@YAHXZ", "int", _inputs(4114)),
    case("?R_PushRemoteScreenUpdate@@YAXH@Z", "void",
         _inputs(4081, args=lambda r: [r.choice([0, 1, 1, 2, 3, 4])])),
    case("?R_PopRemoteScreenUpdate@@YAHXZ", "int", _pop_inputs(4095)),
    case("?R_ToggleSmpFrame@@YAXXZ", "void", _toggle_inputs(1433)),
]
