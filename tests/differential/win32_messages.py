"""A model of the thread's window message queue, for the message pumps (Sys_GetEvent, Sys_LoadingKeepAlive).

Each test input builds a `Messages` state (the pending messages, in retrieval order) and installs it from its setup.
PeekMessageA, GetMessageA, TranslateMessage and DispatchMessageA then behave like the real ones on that queue for an
unfiltered pump, and every call is logged with its arguments into the machine's observed calls, so the original and
the reconstruction must make the same calls in the same order.

DispatchMessageA calls the window procedure: the Store build's own MainWndProc (140552660), run as a callback
(win32_display.Callbacks) in both runs, so a pumped WM_KEYDOWN really goes through MapKey and Sys_QueEvent into the
event queue. Only messages whose handling needs no more than the import stubs are used (input, WM_CHAR, WM_NULL,
WM_TIMER).

Also here: the CRT heap (malloc hands out zeroed blocks from a region that starts over with every install; free is
logged), since the event queue owns allocated text.
"""
import struct
from dataclasses import dataclass, field

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

from win32_display import CURRENT, STACK_HI, STACK_LO, Callbacks

MASK64 = (1 << 64) - 1
HWND_GAME = 0x10010
WNDPROC = 0x140552660        # the Store build's MainWndProc
HEAP_BLOCKS = 0x005C0000     # inside the harness's SCRATCH (cleared before every call), clear of setup allocations
WM_QUIT = 0x12


def _ret(mu, v):
    mu.reg_write(UC_X86_REG_RAX, v & MASK64)


def _ptr(v):
    return "ptr" if STACK_LO <= v < STACK_HI else v


@dataclass
class Msg:
    message: int
    wParam: int = 0
    lParam: int = 0
    time: int = 0
    hwnd: int = HWND_GAME
    pt: tuple = (0, 0)

    def pack(self):
        return struct.pack("<QI4xQQIii4x", self.hwnd, self.message, self.wParam & MASK64, self.lParam & MASK64,
                           self.time & 0xFFFFFFFF, *self.pt)


@dataclass
class Messages:
    queue: list = field(default_factory=list)
    dispatch: bool = True    # DispatchMessageA calls MainWndProc (else it only logs)
    vk_chars: dict = field(default_factory=dict)  # MapVirtualKeyA(vk, MAPVK_VK_TO_CHAR) results

    def install(self, m):
        s = self
        queue = list(self.queue)
        CURRENT["m"] = m
        cb = Callbacks(m)
        heap = [HEAP_BLOCKS]

        def log(name, *args):
            m.observed.append(("import", name, *args))

        def peek(mu):
            p, hwnd, lo, hi = (mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9))
            flags = struct.unpack("<I", bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RSP) + 0x28, 4)))[0]
            log("PeekMessageA", _ptr(p), hwnd, lo & 0xFFFFFFFF, hi & 0xFFFFFFFF, flags)
            if not queue:
                _ret(mu, 0)
                return
            m._emulated_write(p, queue[0].pack())
            if flags & 1:  # PM_REMOVE
                queue.pop(0)
            _ret(mu, 1)

        def get(mu):
            p, hwnd, lo, hi = (mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9))
            log("GetMessageA", _ptr(p), hwnd, lo & 0xFFFFFFFF, hi & 0xFFFFFFFF)
            msg = queue.pop(0) if queue else Msg(WM_QUIT)  # an empty queue would block; never reached by the pumps
            m._emulated_write(p, msg.pack())
            _ret(mu, 0 if msg.message == WM_QUIT else 1)

        def translate(mu):
            p = mu.reg_read(UC_X86_REG_RCX)
            hwnd, message, wparam, lparam, time = struct.unpack("<QI4xQQI", bytes(mu.mem_read(p, 0x24)))
            log("TranslateMessage", message, wparam, lparam, time)
            _ret(mu, 0)

        def dispatch(mu):
            p = mu.reg_read(UC_X86_REG_RCX)
            hwnd, message, wparam, lparam, time = struct.unpack("<QI4xQQI", bytes(mu.mem_read(p, 0x24)))
            log("DispatchMessageA", hwnd, message, wparam, lparam, time)
            if not s.dispatch or message == WM_QUIT:
                _ret(mu, 0)
                return

            def run():
                result = yield WNDPROC, [hwnd, message, wparam, lparam]
                return result
            cb.run(mu, run())

        def map_virtual_key(mu):
            code, kind = mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF
            log("MapVirtualKeyA", code, kind)
            _ret(mu, s.vk_chars.get(code, 0) if kind == 2 else 0)

        def malloc(mu):
            n = mu.reg_read(UC_X86_REG_RCX)
            log("malloc", n)
            block = heap[0]
            heap[0] = (block + n + 15) & ~15
            _ret(mu, block)

        def free(mu):
            log("free", mu.reg_read(UC_X86_REG_RCX))
            _ret(mu, 0)

        for name, fn in {"user32.dll!PeekMessageA": peek, "user32.dll!GetMessageA": get,
                         "user32.dll!TranslateMessage": translate, "user32.dll!DispatchMessageA": dispatch,
                         "user32.dll!MapVirtualKeyA": map_virtual_key,
                         "api-ms-win-crt-heap-l1-1-0.dll!malloc": malloc,
                         "api-ms-win-crt-heap-l1-1-0.dll!free": free}.items():
            m.on_import(name, fn)
