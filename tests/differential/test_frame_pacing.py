"""Differential cases for the frame pacing between the front end, the back end and the GPU (gfx_d3d/r_init.cpp:
R_RegisterRenderFrame, R_SyncGpu and their helpers) and the client's per-frame entry points
(client_mp/cl_main_mp.cpp: CL_SyncGpu, sub_140316290) against the Store build.

Inputs vary the swap frame counters (g_frontEndSwapFrame, g_gpuSubmitSwapFrame, g_gpuSwapFrame, near the int wrap
too), the frames the render thread has to finish (g_renderWaitCount), the com_maxfps remainder (g_maxFpsWaitTime),
the present timestamps, the catch-up timing, a pending sound update and the device state. Sys_Milliseconds is a
scripted clock and the work callback a scripted Python function, both reset for each run; worker command processing
is a logged fake that leaves behind what its predicate would have (the catch-up times, the back end's progress).
"""
import random
import struct

from frame_model import (MAIN_THREAD, RENDER_THREAD, OTHER_THREAD, Kernel, emulated_u32, fake, r_init,
                         write_thread_state)
from syms import va
from win32_display import CURRENT, arg

STORE = "iw6mp64_MSStore_ship"
CALLBACK = 0x140223CE0  # any original function the test fakes: R_SyncGpu's work callback
DX_DEVICE, DX_DEVICE_LOST = 0x08, 0x7CC8


class Clock:
    """Sys_Milliseconds: a start time and the step of each call, replayed identically in both runs."""

    def __init__(self, r):
        self.start = r.choice([0, 1000, 0x7FFFFFF0, -50, r.getrandbits(31)])
        self.steps = [r.choice([0, 0, 1, 1, 2, 5, 16, 40]) for _ in range(64)]
        self.reset()

    def reset(self):
        self.now, self.i = self.start, 0

    def advance(self, ms):
        self.now = (self.now + ms) & 0xFFFFFFFF

    def __call__(self, mu):
        v = self.now
        self.advance(self.steps[self.i % len(self.steps)])
        self.i += 1
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", "Sys_Milliseconds"))
        return v


class Callback:
    """The work callback: logs its deadline, returns scripted results, lets time pass and the back end progress."""

    def __init__(self, r, clock):
        self.results = [r.choice([1, 1, 1, 0]) for _ in range(r.choice([0, 1, 3, 8, 40]))]
        self.clock = clock
        self.progress = r.random() < 0.5
        self.reset()

    def reset(self):
        self.i = 0

    def __call__(self, mu):
        m = CURRENT["m"]
        m.observed.append(("call", "WorkCallback", arg(mu, 0)))
        self.clock.advance(1)
        if self.progress:  # the back end presents a frame
            submit = r_init("g_gpuSubmitSwapFrame")
            v = struct.unpack("<I", bytes(mu.mem_read(submit, 4)))[0]
            emulated_u32(m, submit, v + 1)
        r = self.results[self.i] if self.i < len(self.results) else 0
        self.i += 1
        return r


def _swap_frames(r):
    base = r.choice([0, 5, 100, 0x7FFFFFFE, 0xFFFFFFFD, r.getrandbits(32)])
    gpu = base
    submit = (gpu + r.choice([0, 0, 1, 2, 3])) & 0xFFFFFFFF
    front = (submit + r.choice([0, 0, 1, 1, 2, 3, 4, -1])) & 0xFFFFFFFF
    return gpu, submit, front


def _write_swap_frames(w, frames):
    w.u32(va("g_gpuSwapFrame"), frames[0])
    w.u32(r_init("g_gpuSubmitSwapFrame"), frames[1])
    w.u32(r_init("g_frontEndSwapFrame"), frames[2])


def _pacing_state(r):
    """The present timestamps, g_gpuFrameWait, the catch-up times and R_SyncGpu's end time."""
    t = r.choice([0, 1000, 0x7FFFFFF0, r.getrandbits(31)])
    m = 0xFFFFFFFF
    smp = (t - r.choice([0, 5, 16, 33]), t - r.choice([16, 33, 50]), r.choice([0, 1, 1]), t - r.choice([0, 3, 10, 40]),
           r.choice([0, 1, 1, 2]))
    wait = (t + r.choice([-5, 0, 5, 20]), r.choice([-1, -1, 0, 1, t]), r.choice([-1, 0, t, t + 7]))
    return struct.pack("<5I", *(v & m for v in smp)), struct.pack("<3I", *(v & m for v in wait))


def _write_pacing(w, state):
    smp, wait = state
    w.write(r_init("s_beginSmpFrameTime"), smp)  # s_beginSmpFrameTime .. g_gpuFrameWait are consecutive
    w.write(r_init("g_waitRendererTime"), wait)  # g_waitRendererTime, s_gpuStartCatchUpTime, s_gpuEndCatchUpTime


def _base(r, thread=None):
    """State every case here starts from; returns (setup function, clock, callback, the R_SyncGpu fakes)."""
    thread = thread or r.choice([MAIN_THREAD, MAIN_THREAD, RENDER_THREAD, OTHER_THREAD])
    clock = Clock(r)
    cb = Callback(r, clock)
    frames = _swap_frames(r)
    pacing = _pacing_state(r)
    count = r.choice([0, 0, 1, 1, 2, 3])
    max_fps = r.choice([0, 0, 1, 5, 11, 16, -3])
    sound = r.choice([0, 0, 1])
    device, lost = r.random() < 0.9, r.random() < 0.15
    tick = r.choice([1 / 3.0e6, 1 / 2.4e6, 1 / 1.0e7, 0.001, 1.0, 2.0e-4])
    frame_msec, frame_time = r.getrandbits(8), r.getrandbits(31)
    old_frame = (frame_time - r.choice([0, 1, 16, 199, 200, 201, -5, r.getrandbits(31)])) & 0xFFFFFFFF
    flags = (r.random() < 0.5, r.random() < 0.5)
    first_frame = r.choice([0, 1, 1])
    pop = r.choice([0, 1, 2])
    after_wait = {"catch": (r.choice([-1, -1, 0, 3, 20]), r.choice([0, 4, 25])), "back": r.choice([0, 1, 2]),
                  "takes": r.choice([0, 1, 2, 9]), "zero": r.random() < 0.1}

    def worker_cmds(mu):
        # R_ProcessWorkerCmdsWithTimeout(isDone, timeout): logged; leaves the state its predicate would have
        m = CURRENT["m"]
        m.observed.append(("call", "R_ProcessWorkerCmdsWithTimeout", arg(mu, 0), arg(mu, 1) & 0xFFFFFFFF))
        start, length = after_wait["catch"]
        if after_wait["zero"]:  # the catch-up began at time 0 (s_gpuStartCatchUpTime == 0)
            emulated_u32(m, r_init("s_gpuStartCatchUpTime"), 0)
            emulated_u32(m, r_init("s_gpuEndCatchUpTime"), length)
        elif start >= 0:
            emulated_u32(m, r_init("s_gpuStartCatchUpTime"), clock.now - length - start)
            emulated_u32(m, r_init("s_gpuEndCatchUpTime"), clock.now - start)
        if after_wait["back"]:
            submit = r_init("g_gpuSubmitSwapFrame")
            v = struct.unpack("<I", bytes(mu.mem_read(submit, 4)))[0]
            emulated_u32(m, submit, v + after_wait["back"])
        clock.advance(after_wait["takes"])
        return None

    def setup(w):
        clock.reset()
        cb.reset()
        Kernel(thread).install(w.m)
        write_thread_state(w, count)
        _write_swap_frames(w, frames)
        _write_pacing(w, pacing)
        w.u32(va("g_maxFpsWaitTime"), max_fps)
        w.u32(va("unk_14B2C59A0"), sound)
        w.u64(va("dx") + DX_DEVICE, 0x900000 if device else 0)
        w.write(va("dx") + DX_DEVICE_LOST, bytes([lost]))
        w.write(va("msecPerRawTimerTick"), struct.pack("<d", tick))
        w.u32(va("frame_msec"), frame_msec)
        w.u32(va("old_com_frameTime"), old_frame)
        w.u32(va("com_frameTime"), frame_time)
        w.write(va("cls") + 0x124, bytes(flags))
        w.u32(va("unk_1442B98E0"), first_frame)
    fakes = {
        "?Sys_Milliseconds@@YAHXZ": clock,
        "?R_ProcessWorkerCmdsWithTimeout@@YAXP6AHXZH@Z": worker_cmds,
        "?sub_140316AD0@@YAXH@Z": fake("sub_140316AD0", "i"),
        "?sub_140223CE0@@YAXXZ": cb,
        # R_CheckLostDevice (inlined in the original R_SyncGpu) and what it calls
        "?R_WaitFrontendWorkerCmds@@YAXXZ": fake("R_WaitFrontendWorkerCmds"),
        "?R_UnlockSkinnedCache@@YAXXZ": fake("R_UnlockSkinnedCache"),
        "?R_PopRemoteScreenUpdate@@YAHXZ": fake("R_PopRemoteScreenUpdate", "", pop),
        "?R_SyncRenderThread@@YAXXZ": fake("R_SyncRenderThread"),
        "?R_RecoverLostDevice@@YA_NXZ": fake("R_RecoverLostDevice", "", 1),
        "?R_PushRemoteScreenUpdate@@YAXH@Z": fake("R_PushRemoteScreenUpdate", "i"),
        # sub_140316290's callees
        "?R_SyncGpu@@YAXP6AH_K@Z@Z": None,
        "?IN_Frame@@YAXXZ": fake("IN_Frame"),
        "?sub_14054B4B0@@YAXH@Z": fake("sub_14054B4B0", "i"),
        "?sub_14017A6C0@@YAXPEAUDataValidation@@H@Z": fake("sub_14017A6C0", "qi"),
        "?sub_140191F80@@YAXXZ": fake("sub_140191F80"),
        "?sub_14018F6C0@@YAXXZ": fake("sub_14018F6C0"),
        "?Sys_LoadingKeepAlive@@YAXXZ": fake("Sys_LoadingKeepAlive"),
    }
    return setup, clock, cb, fakes


def _inputs(seed, n=300, args=lambda r: [], fake_sync=False, thread=None, extra=None):
    """fake_sync: R_SyncGpu itself is a logged fake (for its callers); otherwise it runs."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        setup, clock, cb, fakes = _base(r, thread)
        if fake_sync:
            fakes["?R_SyncGpu@@YAXP6AH_K@Z@Z"] = fake("R_SyncGpu", "q")
            fakes["?sub_140223CE0@@YAXXZ"] = fake("sub_140223CE0")
        else:
            del fakes["?R_SyncGpu@@YAXP6AH_K@Z@Z"]
        if extra:
            setup = extra(r, setup)
        out.append({"args": args(r), "setup": setup, "fakes": fakes})
    return out


def _register_extra(r, setup):
    """R_RegisterRenderFrame sleeps until the back end catches up: each Sleep presents a frame (or not)."""
    presents = [r.choice([0, 1, 1, 2]) for _ in range(12)] + [5]
    buf = r.choice([0, 0x14A3AE200, 0x14A3AE200 + 0x645080])
    stamp = r.getrandbits(32)

    def on_sleep(m, k):
        submit = r_init("g_gpuSubmitSwapFrame")
        v = struct.unpack("<I", bytes(m.mu.mem_read(submit, 4)))[0]
        emulated_u32(m, submit, v + presents[min(k - 1, len(presents) - 1)])

    def run(w):
        setup(w)
        Kernel(MAIN_THREAD, on_sleep=on_sleep).install(w.m)
        w.u64(va("frontEndDataOut"), buf)
        if buf:
            w.u32(buf + 0x151468, stamp)
    return run


def case(symbol, ret, inputs):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs}


CASES = [
    case("?sub_140632BC0@@YAXXZ", "void", _inputs(0xBC0, n=150)),
    case("?R_RegisterRenderFrame@@YAXXZ", "void", _inputs(7319, extra=_register_extra)),
    case("?sub_1406301A0@@YAHXZ", "int", _inputs(0x1A0)),
    case("?sub_140630210@@YAHXZ", "int", _inputs(0x210)),
    case("?sub_1406302D0@@YAHXZ", "int", _inputs(0x2D0)),
    case("?sub_140632160@@YAXXZ", "void", _inputs(0x160, n=150)),
    case("?sub_140632190@@YAXXZ", "void", _inputs(0x190, n=150)),
    case("?sub_1406321B0@@YAXH@Z", "void", _inputs(0x1B0, n=100, args=lambda r: [r.choice([0, 1, 2, -1])])),
    case("?R_SyncGpu@@YAXP6AH_K@Z@Z", "void",
         _inputs(3559, n=600, args=lambda r: [r.choice([0, CALLBACK, CALLBACK])], thread=MAIN_THREAD)),
    case("?CL_SyncGpu@@YAXP6AH_K@Z@Z", "void",
         _inputs(8303, n=100, args=lambda r: [r.choice([0, CALLBACK])], fake_sync=True)),
    case("?sub_140316290@@YAXHM@Z", "void",
         _inputs(0x290, n=300, args=lambda r: [r.choice([0, 1, 16, 50, 250]), ("f", r.choice([0.0, 0.016, 0.05]))],
                 fake_sync=True)),
]
