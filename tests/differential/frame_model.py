"""A model of the kernel calls the frame loop makes between the main thread and the render thread, for differential
tests of qcommon/threads.cpp, gfx_d3d/r_rendercmds.cpp and the frame pacing in gfx_d3d/r_init.cpp.

`Kernel` makes the synchronisation imports (WaitForSingleObject, SetEvent, ResetEvent, Sleep, GetCurrentThreadId)
behave like the real ones on scripted state and logs every call with its arguments into the machine's observed
calls, so the original and the reconstruction must make the same calls in the same order:

- WaitForSingleObject returns the next scripted result for that handle (WAIT_OBJECT_0 when the script is empty);
- GetCurrentThreadId returns the thread the input runs on (main, render or another);
- Sleep runs an optional hook, which can end a wait loop by writing a global (a journaled write, so it is compared
  and rolled back like the program's own writes).

Each run installs a fresh Kernel from its setup, so scripted results are consumed the same way by both runs.
"""
import struct

from syms import static, va
from win32_display import CURRENT, logged_fake, u32

MAIN_THREAD, RENDER_THREAD, OTHER_THREAD = 0x1A2C, 0x1B3C, 0x1C4C
WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 0x102

# event handles written into qcommon/threads.cpp's statics
RENDER_PAUSED, NO_OWNERSHIP, RENDERER_RUNNING, BACKEND0, BACKEND1 = 0xE100, 0xE200, 0xE300, 0xE400, 0xE500


def threads(name):
    return static("qcommon/threads.cpp", name)


def r_init(name):
    return static("gfx_d3d/r_init.cpp", name)


def log(*entry):
    CURRENT["m"].observed.append(entry)


class Kernel:
    def __init__(self, thread=MAIN_THREAD, waits=None, on_sleep=None, on_wait=None):
        self.thread = thread
        self.waits = {h: list(r) for h, r in (waits or {}).items()}
        self.on_sleep = on_sleep    # fn(machine, sleep count) after each Sleep
        self.on_wait = on_wait      # fn(machine, handle, timeout) -> result or None (then the script)
        self.sleeps = 0

    def install(self, m):
        CURRENT["m"] = m
        k = self

        def ret(mu, v):
            from unicorn.x86_const import UC_X86_REG_RAX
            mu.reg_write(UC_X86_REG_RAX, v & 0xFFFFFFFFFFFFFFFF)

        def args(mu, n):
            from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX
            return [mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)[:n]]

        def wait(mu):
            h, ms = args(mu, 2)
            log("import", "WaitForSingleObject", h, u32(ms))
            r = k.on_wait(m, h, u32(ms)) if k.on_wait else None
            if r is None:
                script = k.waits.get(h)
                r = script.pop(0) if script else WAIT_OBJECT_0
            ret(mu, r)

        def set_event(mu):
            log("import", "SetEvent", args(mu, 1)[0])
            ret(mu, 1)

        def reset_event(mu):
            log("import", "ResetEvent", args(mu, 1)[0])
            ret(mu, 1)

        def sleep(mu):
            log("import", "Sleep", u32(args(mu, 1)[0]))
            k.sleeps += 1
            if k.on_sleep:
                k.on_sleep(m, k.sleeps)
            ret(mu, 0)

        def thread_id(mu):
            log("import", "GetCurrentThreadId")
            ret(mu, k.thread)

        for name, fn in {"kernel32.dll!WaitForSingleObject": wait, "kernel32.dll!SetEvent": set_event,
                         "kernel32.dll!ResetEvent": reset_event, "kernel32.dll!Sleep": sleep,
                         "kernel32.dll!GetCurrentThreadId": thread_id}.items():
            m.on_import(name, fn)


def write_thread_state(w, render_wait_count=0, smp_data=0, database_ready2=0):
    """threadId[0..1], the events and the render-thread hand-off state."""
    w.write(va("threadId"), struct.pack("<II", MAIN_THREAD, RENDER_THREAD))
    w.u64(threads("renderPausedEvent"), RENDER_PAUSED)
    w.u64(threads("noThreadOwnershipEvent"), NO_OWNERSHIP)
    w.u64(threads("rendererRunningEvent"), RENDERER_RUNNING)
    w.write(threads("backendEvent"), struct.pack("<QQ", BACKEND0, BACKEND1))
    w.u64(threads("smpData"), smp_data)
    w.u32(threads("g_renderWaitCount"), render_wait_count)
    w.u32(threads("databaseCompletedEvent2"), database_ready2)


def emulated_u32(m, address, value):
    """A write made on the program's behalf by a hook (journaled: compared and rolled back)."""
    m._emulated_write(address, struct.pack("<I", value & 0xFFFFFFFF))


def fake(name, sig="", result=None):
    return logged_fake(name, sig, result)
