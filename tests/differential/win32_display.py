"""A model of the display, window and synchronisation calls the renderer's device code makes, for differential tests.

The renderer's device set-up and shutdown (gfx_d3d/r_init.cpp) call user32 (monitors, windows), kernel32 (the
immediate-context mutex), the CRT (qsort, sscanf, sprintf) and the two Direct3D entry points (CreateDXGIFactory,
D3D11CreateDevice). Each test input builds a `Display` (monitors, the primary work area, screen metrics, the
results the entry points return) and installs it from its setup, next to a COM model (com.py) for the objects.
Every call is logged with its arguments into the machine's observed calls, so the original and the reconstruction
must make the same calls in the same order with the same arguments.

Out parameters are written with the machine's journaled write (Machine._emulated_write), so a pointer stored into a
global (dx.dxgiFactory, dx.d3d11device...) counts as a global write and is compared and rolled back.

Callbacks: EnumDisplayMonitors and qsort call back into the program (a MONITORENUMPROC, a comparison function).
`Callbacks` runs such an import as a Python generator that yields (function, arguments) and gets the function's
return value back: the import's stub redirects execution into the function with a return address on a
continuation stub, whose hook resumes the generator; when the generator finishes, execution returns to the
import's caller. The callback is the program's own code (the original's, or the reconstruction's own copy), so
callbacks are tested by the run, not modelled.

Fakes with logged arguments: `logged_fake` replaces an original function (as the harness's `fakes`) and logs its
arguments, including those passed on the stack, which the harness's `observe` (four registers) can't see.
"""
import struct
from dataclasses import dataclass, field

from unicorn import UC_HOOK_CODE, UcError
from unicorn.x86_const import (UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX,
                               UC_X86_REG_RIP, UC_X86_REG_RSP, UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2,
                               UC_X86_REG_XMM3)

CB_REGION, CB_SIZE = 0x00A00000, 0x10000
CONT = CB_REGION              # continuation stub (int3), hooked
CB_DATA = CB_REGION + 0x1000  # memory handed to callbacks (RECTs, ...)
STACK_LO, STACK_HI = 0x00100000, 0x00200000  # harness stack
INT_REGS = (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)
XMM_REGS = (UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2, UC_X86_REG_XMM3)
MASK64 = (1 << 64) - 1

CURRENT = {}  # the machine of the call in progress (set by `install`), for fakes that log

HMONITOR_BASE = 0x6D0000
HWND_BASE = 0x7A0000
MUTEX = 0x4D00
THREAD_ID = 0x1A2C


def u32(v):
    return v & 0xFFFFFFFF


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _ret(mu, v):
    mu.reg_write(UC_X86_REG_RAX, v & MASK64)


def arg(mu, i):
    """Integer argument i of a function at its entry (RSP at the return address) or at an import stub's ret."""
    if i < 4:
        return mu.reg_read(INT_REGS[i])
    rsp = mu.reg_read(UC_X86_REG_RSP)
    return struct.unpack("<Q", bytes(mu.mem_read(rsp + 0x28 + 8 * (i - 4), 8)))[0]


def farg(mu, i):
    """Float argument i (bits) at entry: XMM0-3 by position, then the stack."""
    if i < 4:
        return mu.reg_read(XMM_REGS[i]) & 0xFFFFFFFF
    return arg(mu, i) & 0xFFFFFFFF


def log_value(mu, letter, i):
    """An argument as logged: i/b/q integer, f float bits, s C string, p pointer (stack and heap addresses as
    'ptr', since they differ between the two runs; image and model addresses as they are)."""
    if letter == "f":
        return farg(mu, i)
    v = arg(mu, i)
    if letter == "i":
        return v & 0xFFFFFFFF
    if letter == "b":
        return v & 0xFF
    if letter == "s":
        try:
            return bytes(mu.mem_read(v, 256)).split(b"\0", 1)[0] if v else None
        except UcError:
            return ("unreadable", v)
    if letter == "p" and v and STACK_LO <= v < STACK_HI:
        return "ptr"
    return v


def logged_fake(name, sig, result=None):
    """A fake that logs ("call", name, args...) by `sig` and returns `result` (a value, or fn(mu) -> value)."""
    def run(mu):
        m = CURRENT.get("m")
        if m is not None:
            m.observed.append(("call", name, *(log_value(mu, c, i) for i, c in enumerate(sig))))
        return result(mu) if callable(result) else result
    return run


class Callbacks:
    """Imports that call back into the program (see the module docstring)."""

    def __init__(self, m):
        self.m = m
        self.stack = []  # (generator, rsp at the import's ret, return address)
        if not getattr(m, "_cb_ready", False):
            try:
                m.mu.mem_map(CB_REGION, CB_SIZE)
            except UcError:
                pass
            m.mu.mem_write(CONT, b"\xcc")
            m.mu.hook_add(UC_HOOK_CODE, _on_cont, user_data=m, begin=CONT, end=CONT)
            m._cb_ready = True
        m.mu.mem_write(CB_DATA, bytes(CB_SIZE - 0x1000))
        m._callbacks = self

    def run(self, mu, gen):
        rsp = mu.reg_read(UC_X86_REG_RSP)
        ret = struct.unpack("<Q", bytes(mu.mem_read(rsp, 8)))[0]
        self.stack.append((gen, rsp, ret))
        self.step(mu, None)

    def step(self, mu, value):
        gen, rsp, ret = self.stack[-1]
        try:
            fn, args = gen.send(value)
        except StopIteration as stop:
            self.stack.pop()
            _ret(mu, stop.value or 0)
            mu.reg_write(UC_X86_REG_RSP, rsp + 8)
            mu.reg_write(UC_X86_REG_RIP, ret)
            return
        sp = ((rsp - 0x2000) & ~0xF) - 8
        mu.mem_write(sp, struct.pack("<Q", CONT))
        for i, a in enumerate(args):
            if i < 4:
                mu.reg_write(INT_REGS[i], a & MASK64)
            else:
                mu.mem_write(sp + 0x28 + 8 * (i - 4), struct.pack("<Q", a & MASK64))
        mu.reg_write(UC_X86_REG_RSP, sp)
        mu.reg_write(UC_X86_REG_RIP, fn)


def _on_cont(mu, address, size, m):
    cb = getattr(m, "_callbacks", None)
    if cb is None or not cb.stack:
        return
    # the callback returned: RSP is one above the continuation's slot
    cb.step(mu, mu.reg_read(UC_X86_REG_RAX))


@dataclass
class Monitor:
    rect: tuple            # rcMonitor: left, top, right, bottom
    work: tuple            # rcWork
    primary: bool = False


@dataclass
class Display:
    monitors: list = field(default_factory=lambda: [Monitor((0, 0, 1920, 1080), (0, 0, 1920, 1040), True)])
    info_fails: bool = False          # GetMonitorInfoA fails
    screen: tuple = (1920, 1080)      # GetSystemMetrics SM_CXSCREEN, SM_CYSCREEN
    remote_session: int = 0           # GetSystemMetrics SM_REMOTESESSION
    factory_hr: int = 0               # CreateDXGIFactory
    device_hr: int = 0                # D3D11CreateDevice
    feature_level: int = 0xB000       # what D3D11CreateDevice reports
    device_objects: bool = True       # D3D11CreateDevice creates a device and context when asked
    device_for: object = None         # fn(adapter object id or None) -> (hr, feature level), else the two above
    mutex: int = MUTEX                # CreateMutexA's handle
    wait_results: list = field(default_factory=list)  # WaitForSingleObject results in order, then 0
    windows: set = field(default_factory=set)         # IsWindow is true for these
    create_window: int = 0x10010                      # what CreateWindowExA returns
    messages: dict = field(default_factory=dict)      # FormatMessageA: message id -> text
    com: object = None                # the COM model the entry points create objects in

    def hmonitor(self, i):
        return HMONITOR_BASE + 0x10 * i

    def index(self, h):
        i = (h - HMONITOR_BASE) // 0x10
        return i if h >= HMONITOR_BASE and (h - HMONITOR_BASE) % 0x10 == 0 and i < len(self.monitors) else None

    def install(self, m):
        """Make the imports behave like the real ones on this state (call once per run, from the setup)."""
        s = self
        CURRENT["m"] = m
        cb = Callbacks(m)
        waits = list(self.wait_results)

        def log(name, *args):
            m.observed.append(("import", name, *args))

        def monitor_from_point(mu):
            raw = mu.reg_read(UC_X86_REG_RCX)
            x, y = s32(raw), s32(raw >> 32)
            flags = u32(mu.reg_read(UC_X86_REG_RDX))
            log("MonitorFromPoint", x, y, flags)
            found = None
            for i, mon in enumerate(s.monitors):
                if mon.rect[0] <= x < mon.rect[2] and mon.rect[1] <= y < mon.rect[3]:
                    found = i
                    break
            if found is None and s.monitors and flags == 1:     # MONITOR_DEFAULTTOPRIMARY
                found = next((i for i, mon in enumerate(s.monitors) if mon.primary), 0)
            elif found is None and s.monitors and flags == 2:   # MONITOR_DEFAULTTONEAREST
                def dist(mon):
                    dx = max(mon.rect[0] - x, 0, x - (mon.rect[2] - 1))
                    dy = max(mon.rect[1] - y, 0, y - (mon.rect[3] - 1))
                    return dx * dx + dy * dy
                found = min(range(len(s.monitors)), key=lambda i: dist(s.monitors[i]))
            _ret(mu, 0 if found is None else s.hmonitor(found))

        def get_monitor_info(mu):
            h, p = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
            cb_size = struct.unpack("<I", bytes(mu.mem_read(p, 4)))[0]
            log("GetMonitorInfoA", h, cb_size)
            i = s.index(h)
            if s.info_fails or i is None or cb_size < 0x28:
                _ret(mu, 0)
                return
            mon = s.monitors[i]
            m._emulated_write(p + 4, struct.pack("<4i4iI", *mon.rect, *mon.work, 1 if mon.primary else 0))
            _ret(mu, 1)

        def enum_display_monitors(mu):
            hdc, clip, proc, data = (mu.reg_read(r) for r in INT_REGS)
            log("EnumDisplayMonitors", hdc, clip, data if not STACK_LO <= data < STACK_HI else "ptr")

            def run():
                for i, mon in enumerate(s.monitors):
                    rect = CB_DATA + 0x10 * i
                    mu.mem_write(rect, struct.pack("<4i", *mon.rect))
                    more = yield proc, [s.hmonitor(i), 0, rect, data]
                    if not more & 0xFFFFFFFF:
                        break
                return 1
            cb.run(mu, run())

        def system_parameters_info(mu):
            action, param, p, winini = (mu.reg_read(r) for r in INT_REGS)
            log("SystemParametersInfoA", u32(action), u32(param), u32(winini))
            if u32(action) == 0x30 and p:  # SPI_GETWORKAREA: the primary monitor's work area
                prim = next((mon for mon in s.monitors if mon.primary), None)
                work = prim.work if prim else (0, 0) + s.screen
                m._emulated_write(p, struct.pack("<4i", *work))
            _ret(mu, 1)

        def get_system_metrics(mu):
            n = s32(mu.reg_read(UC_X86_REG_RCX))
            log("GetSystemMetrics", n)
            _ret(mu, {0: s.screen[0], 1: s.screen[1], 0x1000: s.remote_session}.get(n, 0))

        def create_dxgi_factory(mu):
            riid, out = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
            log("CreateDXGIFactory", bytes(mu.mem_read(riid, 16)))
            if s32(s.factory_hr) >= 0 and s.com is not None and out:
                m._emulated_write(out, struct.pack("<Q", s.com.new("IDXGIFactory", mu)))
            _ret(mu, s.factory_hr)

        def d3d11_create_device(mu):
            adapter, driver, software, flags = (arg(mu, i) for i in range(4))
            levels, nlevels, sdk, pdevice, plevel, pctx = (arg(mu, i) for i in range(4, 10))
            obj = s.com.objects.get(adapter) if s.com else None
            level_list = struct.unpack(f"<{u32(nlevels)}I", bytes(mu.mem_read(levels, 4 * u32(nlevels)))) \
                if levels and 0 < u32(nlevels) < 16 else None
            log("D3D11CreateDevice", ("obj", obj[1]) if obj else adapter, u32(driver), software, u32(flags),
                level_list, u32(nlevels), u32(sdk), bool(pdevice), bool(plevel), bool(pctx))
            hr, level = s.device_for(obj[1] if obj else None) if s.device_for else (s.device_hr, s.feature_level)
            if s32(hr) >= 0:
                if pdevice and s.device_objects:
                    m._emulated_write(pdevice, struct.pack("<Q", s.com.new("ID3D11Device", mu)))
                if pctx and s.device_objects:
                    m._emulated_write(pctx, struct.pack("<Q", s.com.new("ID3D11DeviceContext", mu)))
                if plevel:
                    m._emulated_write(plevel, struct.pack("<I", level))
            _ret(mu, hr)

        def create_mutex(mu):
            log("CreateMutexA", mu.reg_read(UC_X86_REG_RCX), u32(mu.reg_read(UC_X86_REG_RDX)),
                mu.reg_read(UC_X86_REG_R8))
            _ret(mu, s.mutex)

        def wait(mu):
            log("WaitForSingleObject", mu.reg_read(UC_X86_REG_RCX), u32(mu.reg_read(UC_X86_REG_RDX)))
            _ret(mu, waits.pop(0) if waits else 0)

        def release_mutex(mu):
            log("ReleaseMutex", mu.reg_read(UC_X86_REG_RCX))
            _ret(mu, 1)

        def thread_id(mu):
            log("GetCurrentThreadId")
            _ret(mu, THREAD_ID)

        def close_handle(mu):
            log("CloseHandle", mu.reg_read(UC_X86_REG_RCX))
            _ret(mu, 1)

        def is_window(mu):
            h = mu.reg_read(UC_X86_REG_RCX)
            log("IsWindow", h)
            _ret(mu, 1 if h in s.windows else 0)

        def destroy_window(mu):
            h = mu.reg_read(UC_X86_REG_RCX)
            log("DestroyWindow", h)
            s.windows.discard(h)
            _ret(mu, 1)

        def adjust_window_rect(mu):
            p, style, menu, ex_style = (arg(mu, i) for i in range(4))
            rect = struct.unpack("<4i", bytes(mu.mem_read(p, 16)))
            log("AdjustWindowRectEx", rect, u32(style), u32(menu), u32(ex_style))
            if u32(style) & 0x00C00000:  # WS_CAPTION: the frame and the title bar
                rect = (rect[0] - 3, rect[1] - 26, rect[2] + 3, rect[3] + 3)
            m._emulated_write(p, struct.pack("<4i", *rect))
            _ret(mu, 1)

        def get_module_handle(mu):
            log("GetModuleHandleA", arg(mu, 0))
            _ret(mu, 0x140000000)

        def create_window(mu):
            a = [arg(mu, i) for i in range(12)]
            text = [bytes(mu.mem_read(p, 64)).split(b"\0", 1)[0] if p else None for p in a[1:3]]
            log("CreateWindowExA", u32(a[0]), *text, u32(a[3]), *(s32(v) for v in a[4:8]), *a[8:12])
            _ret(mu, s.create_window)

        def show_window(mu):
            log("ShowWindow", arg(mu, 0), s32(arg(mu, 1)))
            _ret(mu, 1)

        def post_message(mu):
            log("PostMessageA", arg(mu, 0), u32(arg(mu, 1)), arg(mu, 2), arg(mu, 3))
            _ret(mu, 1)

        def format_message(mu):
            flags, source, msg_id, lang, buf, size = (arg(mu, i) for i in range(6))
            log("FormatMessageA", u32(flags), source, u32(msg_id), u32(lang), u32(size), arg(mu, 6))
            text = s.messages.get(u32(msg_id))
            # FORMAT_MESSAGE_ALLOCATE_BUFFER: the message goes to a buffer the call allocates (NULL when none)
            ptr = 0
            if text is not None:
                ptr = CB_DATA + 0x8000
                mu.mem_write(ptr, text + b"\0")
            m._emulated_write(buf, struct.pack("<Q", ptr))
            _ret(mu, len(text) if text is not None else 0)

        def local_free(mu):
            log("LocalFree", arg(mu, 0))
            _ret(mu, 0)

        def strncpy(mu):
            dst, src, n = arg(mu, 0), arg(mu, 1), arg(mu, 2)
            data = bytes(mu.mem_read(src, n)).split(b"\0", 1)[0][:n]
            m._emulated_write(dst, (data + b"\0" * n)[:n])
            _ret(mu, dst)

        def qsort(mu):
            base, n, size, compare = (mu.reg_read(r) for r in INT_REGS)
            log("qsort", base if not STACK_LO <= base < STACK_HI else "ptr", n, size)

            def run():
                # a merge sort through the program's comparison function; elements stay in place until the end
                order = list(range(n))
                width = 1
                while width < n:
                    merged = []
                    for lo in range(0, n, 2 * width):
                        a, b = order[lo:lo + width], order[lo + width:lo + 2 * width]
                        while a and b:
                            c = yield compare, [base + size * a[0], base + size * b[0]]
                            merged.append(b.pop(0) if s32(c) > 0 else a.pop(0))
                        merged += a + b
                    order = merged
                    width *= 2
                data = [bytes(mu.mem_read(base + size * i, size)) for i in order]
                if data:
                    m._emulated_write(base, b"".join(data))
                return 0
            cb.run(mu, run())

        for name, fn in {"user32.dll!MonitorFromPoint": monitor_from_point,
                         "user32.dll!GetMonitorInfoA": get_monitor_info,
                         "user32.dll!EnumDisplayMonitors": enum_display_monitors,
                         "user32.dll!SystemParametersInfoA": system_parameters_info,
                         "user32.dll!GetSystemMetrics": get_system_metrics,
                         "user32.dll!IsWindow": is_window,
                         "user32.dll!AdjustWindowRectEx": adjust_window_rect,
                         "kernel32.dll!GetModuleHandleA": get_module_handle,
                         "user32.dll!CreateWindowExA": create_window,
                         "user32.dll!ShowWindow": show_window,
                         "user32.dll!PostMessageA": post_message,
                         "kernel32.dll!FormatMessageA": format_message,
                         "kernel32.dll!LocalFree": local_free,
                         "api-ms-win-crt-string-l1-1-0.dll!strncpy": strncpy,
                         "user32.dll!DestroyWindow": destroy_window,
                         "dxgi.dll!CreateDXGIFactory": create_dxgi_factory,
                         "d3d11.dll!D3D11CreateDevice": d3d11_create_device,
                         "kernel32.dll!CreateMutexA": create_mutex,
                         "kernel32.dll!WaitForSingleObject": wait,
                         "kernel32.dll!ReleaseMutex": release_mutex,
                         "kernel32.dll!GetCurrentThreadId": thread_id,
                         "kernel32.dll!CloseHandle": close_handle,
                         "api-ms-win-crt-utility-l1-1-0.dll!qsort": qsort,
                         "api-ms-win-crt-stdio-l1-1-0.dll!__stdio_common_vsscanf": _vsscanf(m, log),
                         "api-ms-win-crt-stdio-l1-1-0.dll!__stdio_common_vsprintf": _vsprintf(m, log)}.items():
            m.on_import(name, fn)


def _directives(fmt):
    """A printf/scanf format as a list of literal byte strings and conversion letters (only %i/%d/%s/%x/%u)."""
    out, i = [], 0
    while i < len(fmt):
        if fmt[i:i + 1] == b"%" and i + 1 < len(fmt):
            if fmt[i + 1:i + 2] == b"%":
                out.append(b"%")
            else:
                out.append(chr(fmt[i + 1]))
            i += 2
        else:
            out.append(fmt[i:i + 1])
            i += 1
    return out


def _vsscanf(m, log):
    """__stdio_common_vsscanf(options, buffer, count, format, locale, arglist): the %i/%d subset the game uses."""
    def run(mu):
        buf, fmt, va = arg(mu, 1), arg(mu, 3), arg(mu, 5)
        text = bytes(mu.mem_read(buf, 256)).split(b"\0", 1)[0] if buf else b""
        form = bytes(mu.mem_read(fmt, 64)).split(b"\0", 1)[0]
        log("sscanf", text, form)
        pos, n, k = 0, 0, 0
        for d in _directives(form):
            if isinstance(d, bytes):
                if d.isspace():
                    while pos < len(text) and text[pos:pos + 1].isspace():
                        pos += 1
                    continue
                if text[pos:pos + 1] != d:
                    break
                pos += 1
                continue
            while pos < len(text) and text[pos:pos + 1].isspace():
                pos += 1
            start = pos
            if text[pos:pos + 1] in (b"-", b"+"):
                pos += 1
            while pos < len(text) and text[pos:pos + 1].isdigit():
                pos += 1
            if pos == start or text[start:pos] in (b"-", b"+"):
                pos = start
                break
            value = int(text[start:pos])
            target = struct.unpack("<Q", bytes(mu.mem_read(va + 8 * k, 8)))[0]
            m._emulated_write(target, struct.pack("<i", s32(value)))
            k += 1
            n += 1
        _ret(mu, n if n or pos < len(text) else -1)
    return run


def _vsprintf(m, log):
    """__stdio_common_vsprintf(options, buffer, count, format, locale, arglist): %i/%d/%u/%x/%s."""
    def run(mu):
        buf, count, fmt, va = arg(mu, 1), arg(mu, 2), arg(mu, 3), arg(mu, 5)
        form = bytes(mu.mem_read(fmt, 256)).split(b"\0", 1)[0]
        out, k = b"", 0
        for d in _directives(form):
            if isinstance(d, bytes):
                out += d
                continue
            v = struct.unpack("<Q", bytes(mu.mem_read(va + 8 * k, 8)))[0]
            k += 1
            if d in "id":
                out += str(s32(v)).encode()
            elif d == "u":
                out += str(u32(v)).encode()
            elif d == "x":
                out += f"{u32(v):x}".encode()
            elif d == "s":
                out += bytes(mu.mem_read(v, 256)).split(b"\0", 1)[0] if v else b"(null)"
        log("sprintf", form, out)
        if buf:
            m._emulated_write(buf, out + b"\0")
        _ret(mu, len(out))
    return run
