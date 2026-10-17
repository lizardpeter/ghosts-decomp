"""Differential cases for gfx_d3d/r_init.cpp (device, swap chain and window) against the Store build.

Every input builds a display (win32_display.py: monitors, work areas, screen metrics, what CreateDXGIFactory and
D3D11CreateDevice return) and COM objects (com.py: factory, adapters with their outputs, device, context, swap
chain) with varying results (failing HRESULTs, missing objects, different descriptions), random dx and vidConfig
state, and scratch dvars. Calls to the rest of the engine are faked with logged arguments (logged_fake), so the
original and the reconstruction must make the same calls, COM calls and Win32 calls with the same arguments and
leave the same globals behind.
"""
import random
import struct

from com import ComModel
from syms import static as syms_static, va
from win32_display import (HMONITOR_BASE, MUTEX, THREAD_ID, CURRENT, Display, Monitor, arg, farg, logged_fake,
                           s32, u32)

STORE = "iw6mp64_MSStore_ship"
NOT_FOUND = 0x887A0002

# dx fields (Store offsets, gfx_d3d/r_dx.h)
DEVICE, CONTEXT, LOCK_COUNT, LOCK_THREAD = 0x08, 0x10, 0x18, 0x1C
FACTORY, ADAPTER, OUTPUT, FEATURE_LEVEL = 0x20, 0x28, 0x30, 0x38
MUTEX_OFF, ADAPTER_INDEX, NATIVE_VALID, NATIVE_W, NATIVE_H = 0x3B68, 0x3B70, 0x3B74, 0x3B78, 0x3B7C
DEVICE_LOST = 0x7CC8

FAC, ADP, OUT, DEV, CTX, SWC, QRY = ("IDXGIFactory", "IDXGIAdapter", "IDXGIOutput", "ID3D11Device",
                                     "ID3D11DeviceContext", "IDXGISwapChain", "ID3D11Query")
RES, STATE = "ID3D11Resource", "ID3D11State"
RELEASE = 2 * 8
SIGS = {
    (FAC, 7 * 8): "ip", (FAC, 8 * 8): "pi", (FAC, 10 * 8): "ppp", (FAC, RELEASE): "",
    (ADP, 7 * 8): "ip", (ADP, 8 * 8): "p", (ADP, RELEASE): "",
    (OUT, 7 * 8): "p", (OUT, 8 * 8): "iipp", (OUT, RELEASE): "",
    (DEV, 24 * 8): "pp", (DEV, 27 * 8): "ip", (DEV, 30 * 8): "iip", (DEV, 39 * 8): "", (DEV, RELEASE): "",
    (CTX, 28 * 8): "p", (CTX, 29 * 8): "ppii", (CTX, 110 * 8): "", (CTX, 111 * 8): "", (CTX, RELEASE): "",
    (SWC, 8 * 8): "ii", (SWC, 9 * 8): "ipp", (SWC, 10 * 8): "ip", (SWC, 11 * 8): "pp", (SWC, 12 * 8): "p",
    (SWC, RELEASE): "",
    (QRY, 7 * 8): "", (QRY, RELEASE): "",
    (RES, RELEASE): "", (STATE, RELEASE): "",
}


def static(name):
    return syms_static("gfx_d3d/r_init.cpp", name)


def static_fn(scope, name):
    return syms_static("gfx_d3d/r_init.cpp", name, scope)


def void_fakes(*names):
    """Logged fakes for void (void) functions, by plain name (sub_<VA> or a known decorated name)."""
    out = {}
    for n in names:
        sym = n if n.startswith("?") else f"?{n}@@YAXXZ"
        out[sym] = logged_fake(sym[1:].split("@", 1)[0], "")
    return out


def out_object(model, kind):
    """A COM result that creates an object of `kind` and stores it through the call's last pointer argument with a
    journaled write (the pointer is often a global)."""
    def run(call):
        p = call.args[-1]
        if p:
            CURRENT["m"]._emulated_write(p, struct.pack("<Q", model.new(kind, call.mu)))
        return 0
    return run


def dx(off=0):
    return va("dx") + off


def dvar(w, value, fmt="<i"):
    """A scratch dvar_t whose current value is `value`."""
    p = w.alloc(bytes(0x60))
    w.write(p + 0x10, struct.pack(fmt, value))
    return p


def log(*entry):
    CURRENT["m"].observed.append(entry)


def returns(value):
    return lambda mu: value


def fake(name, sig="", result=None):
    return logged_fake(name, sig, result)


# ---- R_MonitorEnumCallback, sub_140631830 -----------------------------------------------------------------------

def _monitor_cb_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        h = r.choice([HMONITOR_BASE, HMONITOR_BASE + 0x10, 0, r.getrandbits(64)])
        index = r.choice([0, 0, 1, 2, -1, r.getrandbits(32)])
        stored = r.choice([h, 0, HMONITOR_BASE + 0x20, r.getrandbits(64)])
        data = struct.pack("<iIQ", s32(index), r.getrandbits(32), stored)
        out.append({"args": [h, r.getrandbits(64), r.getrandbits(64), data]})
    return out


# ---- sub_140632660: R_ClearAllStreamSources under the immediate-context lock -------------------------------------

LOCK_FAKES = {"?R_ClearAllStreamSources@@YAXPEAUGfxCmdBufPrimState@@@Z": fake("R_ClearAllStreamSources", "q")}


def _lock_state(r):
    """Random immediate-context lock state (mutex handle, lock count, owner thread): a setup function."""
    values = (r.choice([MUTEX, MUTEX, 0, 0x7777]), r.choice([0, 0, 0, 1, 2, -1]),
              r.choice([0xFFFFFFFF, THREAD_ID, 0, r.getrandbits(32)]))

    def setup(w):
        w.u64(dx(MUTEX_OFF), values[0])
        w.u32(dx(LOCK_COUNT), values[1])
        w.u32(dx(LOCK_THREAD), values[2])
    return setup


def _stream_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        device, lost = r.choice([0, 0x900000, r.getrandbits(64)]), r.random() < 0.3
        lock = _lock_state(r)

        def setup(w, device=device, lost=lost, lock=lock):
            Display().install(w.m)
            w.u64(dx(DEVICE), device)
            w.write(dx(DEVICE_LOST), bytes([lost]))
            lock(w)
        out.append({"args": [], "setup": setup, "fakes": LOCK_FAKES})
    return out


# ---- R_CheckLostDevice ----------------------------------------------------------------------------------------

def _check_lost_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        device, lost, main = r.choice([0, 0x900000, r.getrandbits(64)]), r.random() < 0.6, r.random() < 0.6
        pop = r.choice([0, 1, 3, r.getrandbits(32)])

        def setup(w, device=device, lost=lost):
            Display().install(w.m)
            w.u64(dx(DEVICE), device)
            w.write(dx(DEVICE_LOST), bytes([lost]))
        fakes = {
            "?Sys_IsMainThread@@YA_NXZ": fake("Sys_IsMainThread", "", main),
            "?R_WaitFrontendWorkerCmds@@YAXXZ": fake("R_WaitFrontendWorkerCmds"),
            "?R_UnlockSkinnedCache@@YAXXZ": fake("R_UnlockSkinnedCache"),
            "?R_PopRemoteScreenUpdate@@YAHXZ": fake("R_PopRemoteScreenUpdate", "", pop),
            "?R_SyncRenderThread@@YAXXZ": fake("R_SyncRenderThread"),
            "?R_RecoverLostDevice@@YA_NXZ": fake("R_RecoverLostDevice", "", r.choice([0, 1])),
            "?R_PushRemoteScreenUpdate@@YAXH@Z": fake("R_PushRemoteScreenUpdate", "i"),
        }
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


# ---- R_ChooseAdapter ------------------------------------------------------------------------------------------

def _monitors(r):
    """1-3 monitors: the primary at the origin, others to the right, left or above it."""
    w0, h0 = r.choice([(1920, 1080), (2560, 1440), (1280, 1024), (3840, 2160)])
    mons = [Monitor((0, 0, w0, h0), (0, 0, w0, h0 - r.choice([0, 40, 48])), True)]
    places = [(w0, 0), (-1280, 0), (0, -1080), (w0, r.randint(-300, 300))]
    r.shuffle(places)
    for x, y in places[:r.choice([0, 0, 1, 1, 2])]:
        w, h = r.choice([(1280, 1024), (1920, 1080), (1680, 1050)])
        if x < 0:
            x = -w
        if y < 0 and x == 0:
            y = -h
        left = r.choice([0, 0, 60])
        mons.append(Monitor((x, y, x + w, y + h), (x + left, y, x + w, y + h - r.choice([0, 40]))))
    if r.random() < 0.15:  # the primary need not come first
        r.shuffle(mons)
    return mons


def _adapters(r, nmon):
    """Adapters for EnumAdapters: D3D11CreateDevice's result and feature level, and the outputs' monitors."""
    out = []
    for _ in range(r.choice([0, 1, 1, 2, 2, 3, 4])):
        hr = r.choice([0, 0, 0, 1, 0x887A0004, 0x80004005])
        level = r.choice([0xB000, 0xB000, 0xB100, 0xA100, 0xA000, 0x9300, 0xAFFF, 0xC000])
        outputs = [r.choice(list(range(nmon)) + [nmon, 7]) for _ in range(r.choice([0, 1, 1, 2, 3]))]
        out.append((hr, level, outputs))
    return out


def _dxgi_model(display, adapters, extra_results=None):
    """A COM model whose factory enumerates `adapters` (D3D11CreateDevice results from them too)."""
    adapter_spec, output_monitor = {}, {}
    model = ComModel(SIGS)

    def enum_adapters(call):
        i = call.arg(0)
        if i >= len(adapters):
            return NOT_FOUND
        va_ = call.out_object(1, ADP)
        adapter_spec[model.objects[va_][1]] = adapters[i]
        return 0

    def enum_outputs(call):
        spec = adapter_spec.get(model.objects.get(call.obj, (None, None))[1])
        i = call.arg(0)
        if spec is None or i >= len(spec[2]):
            return NOT_FOUND
        va_ = call.out_object(1, OUT)
        output_monitor[model.objects[va_][1]] = HMONITOR_BASE + 0x10 * spec[2][i]
        return 0

    def output_desc(call):
        oid = model.objects.get(call.obj, (None, None))[1]
        name = "\\\\.\\DISPLAY{}".format(oid).encode("utf-16-le")
        desc = name.ljust(0x40, b"\0") + struct.pack("<4iii", 0, 0, 1920, 1080, 1, 1)
        call.write(call.arg(0), desc + struct.pack("<Q", output_monitor.get(oid, 0)))
        return 0

    model.results.update({(FAC, 7 * 8): enum_adapters, (ADP, 7 * 8): enum_outputs, (OUT, 7 * 8): output_desc})
    model.results.update(extra_results or {})
    display.com = model
    display.device_for = lambda aid: (adapter_spec[aid][0], adapter_spec[aid][1]) if aid in adapter_spec \
        else (display.device_hr, display.feature_level)
    return model


def _dvar_get_int(values):
    def run(mu):
        name = bytes(mu.mem_read(arg(mu, 0), 64)).split(b"\0", 1)[0].decode()
        log("call", "Dvar_GetInt", name)
        return values.get(name, 0) & 0xFFFFFFFF
    return run


CHOOSE_FAKES = {
    "?Dvar_SetInt@@YAXPEBUdvar_t@@H@Z": fake("Dvar_SetInt", "qi"),
    "?Sys_DirectXFatalError@@YAXXZ": fake("Sys_DirectXFatalError"),
}


def _choose_adapter_inputs(seed, n=400):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        mons = _monitors(r) if r.random() < 0.95 else []  # no monitor: MonitorFromPoint returns NULL
        adapters = _adapters(r, len(mons))
        mode, monitor_index = r.choice([0, 0, 1, 2]), r.choice([0, 0, 1, 2, 3, 9])
        any_mon = r.choice(mons).rect if mons else (0, 0, 1920, 1080)
        xpos = r.choice([r.randint(any_mon[0] - 100, any_mon[2] + 100), any_mon[0], any_mon[2] - 32,
                         any_mon[2] - 31, -5000, 9000])
        ypos = r.choice([r.randint(any_mon[1] - 100, any_mon[3] + 100), any_mon[1], any_mon[3] - 32,
                         any_mon[3] - 31, -5000])
        info_fails, factory_hr = r.random() < 0.1, r.choice([0] * 9 + [0x80004005])
        dvars = {"vid_xpos": xpos, "vid_ypos": ypos}
        old = [r.choice([0, r.getrandbits(64)]) for _ in range(3)] + [r.getrandbits(32)]

        def setup(w, mons=mons, adapters=adapters, mode=mode, monitor_index=monitor_index, info_fails=info_fails,
                  factory_hr=factory_hr, old=old):
            display = Display(monitors=list(mons), info_fails=info_fails, factory_hr=factory_hr)
            model = _dxgi_model(display, adapters)
            model.install(w.m)
            display.install(w.m)
            factory = model.new(FAC) if factory_hr else 0  # a failed CreateDXGIFactory leaves the old pointer
            w.u64(dx(FACTORY), factory)
            w.u64(dx(ADAPTER), old[0])
            w.u64(dx(OUTPUT), old[1])
            w.u32(dx(ADAPTER_INDEX), old[3])
            w.u64(va("r_displayMode"), dvar(w, mode))
            w.u64(va("r_monitor"), dvar(w, monitor_index))
            w.u64(va("vid_xpos"), dvar(w, xpos))
            w.u64(va("vid_ypos"), dvar(w, ypos))
        fakes = dict(CHOOSE_FAKES)
        fakes["?Dvar_GetInt@@YAHPEBD@Z"] = _dvar_get_int(dvars)
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


# ---- R_CompareDisplayModes, R_CompareRefreshRates --------------------------------------------------------------

def _rational(r):
    return r.choice([(60, 1), (59940, 1000), (60000, 1001), (144, 1), (75, 1), (120000, 1000), (0, 1),
                     (r.getrandbits(32), r.getrandbits(32)), (r.randint(1, 200), r.randint(1, 3))])


def _mode(r, size=None):
    w, h = size or r.choice([(1920, 1080), (1280, 720), (640, 480), (800, 600), (2560, 1440), (1024, 768),
                             (639, 480), (640, 479), (r.getrandbits(32), r.getrandbits(32))])
    num, den = _rational(r)
    return struct.pack("<7I", w & 0xFFFFFFFF, h & 0xFFFFFFFF, num, den, 0x1C, r.randint(0, 2), r.randint(0, 2))


def _compare_modes_inputs(seed, n=400):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        a = _mode(r)
        b = r.choice([a, _mode(r), a[:8] + _mode(r)[8:], a[:4] + _mode(r)[4:]])
        out.append({"args": [a, b]})
    return out


def _compare_rates_inputs(seed, n=200):
    r = random.Random(seed)
    vals = [0, 1, 59, 60, 144, -1, 0x7FFFFFFF, -0x80000000]
    return [{"args": [struct.pack("<i", r.choice(vals + [s32(r.getrandbits(32))])),
                      struct.pack("<i", r.choice(vals + [s32(r.getrandbits(32))]))]} for _ in range(n)]


# ---- R_EnumDisplayModes ---------------------------------------------------------------------------------------

DISPLAY_MODE_COUNT, DISPLAY_MODES, RESOLUTION_NAMES = 0x3B80, 0x3B84, 0x5788
NOT_CURRENTLY_AVAILABLE = 0x887A0022
ENUM_DVAR = 0x500F00  # what the faked Dvar_RegisterEnum returns (scratch)


def _mode_list(r):
    sizes = [(640, 480), (800, 600), (1024, 768), (1280, 720), (1280, 1024), (1600, 900), (1920, 1080),
             (2560, 1440), (3840, 2160), (320, 200), (640, 400), (720, 480), (1680, 1050)]
    rates = [(60, 1), (59940, 1000), (60000, 1001), (75, 1), (144, 1), (143998, 1000), (120, 1), (50, 1),
             (30, 1), (240, 1), (0, 1), (5994, 100), (165, 1)]
    count = r.choice([0, 1, 2, 3, 5, 8, 10, 14, 20, 30, 40] * 3 + [100, 256])
    modes = []
    for _ in range(count):
        w, h = r.choice(sizes)
        num, den = r.choice(rates)
        modes.append(struct.pack("<7I", w, h, num, den, 0x1C, r.randint(0, 2), r.randint(0, 2)))
    return modes


def _enum_modes_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        modes = _mode_list(r)
        desc_hr = r.choice([0, 0, 0, 1, 0x887A0001])
        desktop = r.choice([(0, 0, 1920, 1080), (0, 0, 2560, 1440), (-1280, 0, 0, 1024), (0, 0, 1366, 768),
                            (100, 50, 1380, 770)])
        list_hr = r.choice([0, 0, 0, NOT_CURRENTLY_AVAILABLE, 0x887A0001])
        screen = r.choice([(1920, 1080), (1280, 720), (0, 0), (-1, 768), (1024, 0)])
        remote, default_index = r.choice([0, 1]), r.choice([-1, -1, 0, 1, 2, 5])
        old_count = r.getrandbits(32)

        def setup(w, modes=modes, desc_hr=desc_hr, desktop=desktop, list_hr=list_hr, screen=screen, remote=remote,
                  default_index=default_index, old_count=old_count):
            m = w.m
            display = Display(screen=screen, remote_session=remote)

            def get_desc(call):
                desc = "\\\\.\\DISPLAY1".encode("utf-16-le").ljust(0x40, b"\0")
                call.write(call.arg(0), desc + struct.pack("<4iiiQ", *desktop, 1, 1, HMONITOR_BASE))
                return desc_hr

            def get_list(call):
                pcount, pdesc = call.arg(2), call.arg(3)
                if not pdesc:
                    m._emulated_write(pcount, struct.pack("<I", len(modes)))
                    return list_hr
                cap = struct.unpack("<I", bytes(call.mu.mem_read(pcount, 4)))[0]
                k = min(cap, len(modes))
                if k:
                    m._emulated_write(pdesc, b"".join(modes[:k]))
                m._emulated_write(pcount, struct.pack("<I", k))
                return 0 if k == len(modes) else 0x887A0003  # DXGI_ERROR_MORE_DATA

            model = ComModel(SIGS, {(OUT, 7 * 8): get_desc, (OUT, 8 * 8): get_list})
            model.install(m)
            display.com = model
            display.install(m)
            w.u64(dx(OUTPUT), model.new(OUT))
            w.u32(dx(DISPLAY_MODE_COUNT), old_count)
            w.u32(va("unk_14A346B40"), default_index)
            # stale names from an earlier enumeration in both name tables
            w.write(dx(RESOLUTION_NAMES), bytes([0x5A]) * (2 * 257 * 8))
        fakes = {
            "va": fake("va", "sii"),
            "?Sys_DirectXFatalError@@YAXXZ": fake("Sys_DirectXFatalError"),
            "?Dvar_RegisterEnum@@YAPEBUdvar_t@@PEBDQEBQEBDHI0@Z": fake("Dvar_RegisterEnum", "sqiis", ENUM_DVAR),
        }
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


# ---- R_SetWndParms --------------------------------------------------------------------------------------------

def _wnd_input(r, name_ptr):
    letterbox, force = r.random() < 0.2, r.random() < 0.15
    return struct.pack("<iiiiiiQQiBBBB", r.choice([0, 1, 1, 2]), r.choice([0, 0, 1, 2, 3, 5]),
                       r.choice([0, 1, 2, 3, 4, 5, 7, -1]), r.randint(0, 6),
                       r.choice([0, 100, -1300, 1919, 2000, -50]), r.choice([0, 30, -1, 1079, 1500]),
                       name_ptr, r.getrandbits(64), r.randint(0, 2), r.random() < 0.5, r.random() < 0.7,
                       letterbox or force, force)


def _set_wnd_parms_inputs(seed, n=600):
    r = random.Random(seed)
    names = [b"1920x1080", b"1280x720", b"640x480", b"800x600", b"1024x768", b"3840x2160", b"1680x1050",
             b"1366x768", b"1280x1024", b"2560x1080", b"1440x900", b"1x1", b"0x0", b"1600x1200",
             b"1920x1140", b"1920x1260", b"1280x880", b"1600x1100", b"1024x700", b"640x380"]  # ratios at x.5
    out = []
    for _ in range(n):
        name = r.choice(names)
        valid = r.random() < 0.7
        native = r.choice([(1920, 1080), (2560, 1440), (1280, 1024), (1680, 1050), (3440, 1440), (0, 0),
                           (1920, 1140), (1920, 1260), (1280, 880)])
        mons = _monitors(r)
        info_fails = r.random() < 0.1

        def setup(w, name=name, valid=valid, native=native, mons=mons, info_fails=info_fails):
            assert w.cstr(name) == 0x500000  # the resolution name, at the first scratch address
            Display(monitors=list(mons), info_fails=info_fails).install(w.m)
            w.write(dx(NATIVE_VALID), bytes([valid]))
            w.u32(dx(NATIVE_W), native[0])
            w.u32(dx(NATIVE_H), native[1])
        samples = {0: 1, 1: 1, 2: 2, 3: 4, 4: 1, 5: 2, 6: 4}
        fakes = {"?sub_140623E30@@YAHW4GfxAAMode@@@Z":
                 fake("sub_140623E30", "i", lambda mu: samples.get(u32(arg(mu, 0)), 1))}
        parms = bytes(r.getrandbits(8) for _ in range(0x40))
        out.append({"args": [parms, _wnd_input(r, 0x500000)], "setup": setup, "fakes": fakes})
    return out


# ---- R_CreateDevice -------------------------------------------------------------------------------------------

WINDOW0_HWND, WINDOW0_SWAPCHAIN = 0x7CD8, 0x7CE0
MULTISAMPLE = 0x7C9C


def _wide(text, n=128):
    return text.encode("utf-16-le")[:2 * n].ljust(2 * n, b"\0")


def _swap_chain_desc(mu, p):
    """DXGI_SWAP_CHAIN_DESC by field (padding left out)."""
    f = struct.unpack("<7I2III", bytes(mu.mem_read(p, 0x2C)))
    hwnd, windowed, effect, flags = struct.unpack("<QIII", bytes(mu.mem_read(p + 0x30, 0x14)))
    return ("SwapChainDesc", *f, hwnd, windowed, effect, flags)


def _create_device_inputs(seed, n=400):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        hr = r.choice([0, 0, 0, 0x887A0004, 1])
        level = r.choice([0xB000, 0xB000, 0xB100, 0xA100, 0xA000, 0x9300, 0x9200, 0x9100, 0x9400, 0xC100, 0xAFFF])
        aa = r.choice([0, 1, 2, 4, 8, 16, -1, 3])
        msaa_ok = {s: r.random() < 0.5 for s in range(2, 17)}
        vendor = r.choice([0x10DE, 0x1002, 0x1022, 0x8086, 0x1003, 0x1042, 0x1012])
        adapter_null, old_device_null = r.random() < 0.05, r.random() < 0.05
        old_level = r.choice([0, 0xB000, 0x9100])
        swap_hr = r.choice([0, 0, 0x887A0001])
        hwnd0 = r.choice([0, 0, 0x10010, 0x20020])
        crossfire, nvidia, sli_hr, afr = r.random() < 0.5, r.random() < 0.4, r.choice([0, 0, -3]), r.randint(0, 3)
        parms = struct.pack("<QIIiiifHHiiiiBBxxi", r.choice([0x10010, 0, 0x30030]),
                            *r.choice([(60, 1), (59940, 1000), (144, 1), (0, 0)]), r.randint(0, 2),
                            r.randint(-100, 100), r.randint(-100, 100), r.choice([1.6, 1.7777778, 1.3333334]),
                            r.choice([0x200, 0x300, 0x400]), r.choice([0x400, 0x600, 0x800]),
                            r.choice([1280, 1920]), r.choice([720, 1080]), r.choice([1280, 1920, 800]),
                            r.choice([720, 1080, 600]), r.randint(0, 7), r.random() < 0.2, aa)
        old_mutex = r.getrandbits(64)

        def setup(w, hr=hr, level=level, msaa_ok=msaa_ok, vendor=vendor, adapter_null=adapter_null,
                  old_device_null=old_device_null, old_level=old_level, swap_hr=swap_hr, hwnd0=hwnd0,
                  old_mutex=old_mutex):
            m = w.m
            display = Display(device_hr=hr, feature_level=level, mutex=MUTEX)

            def check_msaa(call):
                ok = msaa_ok.get(call.arg(1), False)
                if ok and call.arg(2):
                    call.write(call.arg(2), struct.pack("<I", 3))
                return 0 if ok else 0x80070057

            def adapter_desc(call):
                call.write(call.arg(0), _wide("NVIDIA GeForce RTX" if vendor == 0x10DE else "Radeon RX")
                           + struct.pack("<4I3Q2I", vendor, 0x1234, 0, 1, 1 << 30, 0, 1 << 32, 7, 0))
                return 0

            def create_swap_chain(call):
                log(_swap_chain_desc(call.mu, call.arg(1)))
                if swap_hr == 0:
                    m._emulated_write(call.arg(2), struct.pack("<Q", model.new(SWC, call.mu)))
                return swap_hr

            model = ComModel(SIGS, {(DEV, 30 * 8): check_msaa, (ADP, 8 * 8): adapter_desc,
                                    (FAC, 10 * 8): create_swap_chain})
            model.install(m)
            display.com = model
            display.install(m)
            w.u64(dx(FACTORY), model.new(FAC))
            w.u64(dx(ADAPTER), 0 if adapter_null else model.new(ADP))
            w.u64(dx(DEVICE), 0 if old_device_null else model.new(DEV))
            w.u64(dx(CONTEXT), 0)
            w.u32(dx(FEATURE_LEVEL), old_level)
            w.u64(dx(MUTEX_OFF), old_mutex)
            w.u64(dx(WINDOW0_HWND), hwnd0)
            w.u64(dx(WINDOW0_SWAPCHAIN), 0)
            w.write(dx(DEVICE_LOST), bytes([1]))
            w.write(va("unk_14A37D580"), bytes([0]))
            for name in ("r_rendererInUse", "r_amdGPU", "r_multiGPU"):
                w.u64(va(name), dvar(w, 0))

        def com_error(mu):
            fmt = bytes(mu.mem_read(arg(mu, 1), 80)).split(b"\0", 1)[0]
            extra = bytes(mu.mem_read(arg(mu, 2), 32)) if b"%s" in fmt else None
            log("call", "Com_Error", u32(arg(mu, 0)), fmt, extra)

        def sli_state(mu, sli_hr=sli_hr, afr=afr):
            p = arg(mu, 1)
            version = struct.unpack("<I", bytes(mu.mem_read(p, 4)))[0]
            log("call", "NvAPI_D3D_GetCurrentSLIState", arg(mu, 0), version)
            if sli_hr == 0:
                CURRENT["m"]._emulated_write(p + 4, struct.pack("<II", 4, afr))
            return sli_hr & 0xFFFFFFFF

        fakes = {
            "?sub_1401B0030@@YAXXZ": fake("sub_1401B0030"),
            "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": com_error,
            "?Dvar_SetInt@@YAXPEBUdvar_t@@H@Z": fake("Dvar_SetInt", "qi"),
            "?Dvar_SetBool@@YAXPEBUdvar_t@@_N@Z": fake("Dvar_SetBool", "qb"),
            "?sub_140631850@@YA_NPEAUIDXGIAdapter@@@Z": fake("sub_140631850", "q", int(crossfire)),
            "?R_IsReallyNvidiaGPU@@YA_NXZ": fake("R_IsReallyNvidiaGPU", "", int(nvidia)),
            "NvAPI_D3D_GetCurrentSLIState": sli_state,
        }
        out.append({"args": [parms], "setup": setup, "fakes": fakes})
    return out


# ---- R_FlushSwap, sub_14062EC80 -------------------------------------------------------------------------------

FENCE_FAKES = void_fakes("?R_AcquireGpuFenceLock@@YAXXZ", "?R_FinishGpuFence@@YAXXZ", "?R_InsertGpuFence@@YAXXZ",
                         "?R_ReleaseGpuFenceLock@@YAXXZ")


def _swap_frames(r):
    """g_gpuSwapFrame, g_gpuSubmitSwapFrame, g_frontEndSwapFrame: the GPU at most a few frames behind."""
    base = r.choice([0, 1, 100, 0x7FFFFFFE, 0xFFFFFFFD, r.getrandbits(32)])
    submit = (base + r.choice([0, 0, 1, 2, 3, 7])) & 0xFFFFFFFF
    front = (submit + r.choice([0, 1, 2, 5])) & 0xFFFFFFFF
    return base, submit, front


def _write_swap_frames(w, frames):
    w.u32(va("g_gpuSwapFrame"), frames[0])
    w.u32(static("g_gpuSubmitSwapFrame"), frames[1])
    w.u32(static("g_frontEndSwapFrame"), frames[2])


def _flush_swap_inputs(seed, n=100):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        frames = _swap_frames(r)
        out.append({"args": [], "setup": lambda w, frames=frames: (Display().install(w.m),
                                                                    _write_swap_frames(w, frames)),
                    "fakes": FENCE_FAKES})
    return out


def _swap_fence_inputs(seed, n=100):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        frames = _swap_frames(r)
        fences = struct.pack("<8Q", *(r.getrandbits(64) for _ in range(8)))
        out.append({"args": [r.getrandbits(64)],
                    "setup": lambda w, frames=frames, fences=fences: (_write_swap_frames(w, frames),
                                                                       w.write(static("g_gpuSwapFence"), fences))})
    return out


# ---- R_RecoverLostDevice (with R_ResetDevice) ----------------------------------------------------------------

VIDCONFIG = 0x40
WINDOW0_W, WINDOW0_H, WINDOW0_DEPTH = 0x7CF0, 0x7CF4, 0x7CE8
WINDOW_COUNT, TARGET_WINDOW = 0x7CD4, 0x7CCC
ERROR_TEXT = 0x14089D140  # any string of the original's .rdata ("%ix%i") for R_ErrorDescription to return


def _vidconfig(r):
    return struct.pack("<IIIIB?HHxxIIIIifffff", r.choice([1280, 1920, 1408, 736]), r.choice([720, 1080, 880, 460]),
                       r.choice([1280, 1920, 2560]), r.choice([720, 1080, 1440]), r.randint(0, 7),
                       r.random() < 0.3, r.choice([0x200, 0x300, 0x400]), r.choice([0x400, 0x600, 0x800]),
                       *r.choice([(60, 1), (59940, 1000), (144, 1)]), r.choice([1920, 2560]),
                       r.choice([1080, 1440]), r.randint(0, 2), r.choice([1.7777778, 1.3333334, 1.6]),
                       r.random(), r.random(), r.random(), r.random())


def _context_arg(mu):
    """R_SetRenderTarget's GfxCmdBufContext, passed by reference to a copy: its two pointers."""
    return struct.unpack("<2Q", bytes(mu.mem_read(arg(mu, 0), 16)))


def _recover_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        vid = _vidconfig(r)
        hwnd, width, height = r.choice([0x10010, 0x20020]), r.choice([1920, 1280]), r.choice([1080, 720])
        swap_hr, mwa_hr = r.choice([0, 0, 0, 0x887A0001, 0x80070057]), r.choice([0, 0, 0, 0x887A0001])
        frame_count, samples = r.getrandbits(32), r.choice([1, 2, 4])

        def setup(w, vid=vid, hwnd=hwnd, width=width, height=height, swap_hr=swap_hr, mwa_hr=mwa_hr,
                  frame_count=frame_count):
            m = w.m

            def create_swap_chain(call):
                log(_swap_chain_desc(call.mu, call.arg(1)))
                if swap_hr == 0:
                    m._emulated_write(call.arg(2), struct.pack("<Q", model.new(SWC, call.mu)))
                return swap_hr

            model = ComModel(SIGS, {(FAC, 10 * 8): create_swap_chain, (FAC, 8 * 8): returns(mwa_hr)})
            model.install(m)
            Display(com=model).install(m)
            w.u64(dx(FACTORY), model.new(FAC))
            w.u64(dx(DEVICE), model.new(DEV))
            w.write(dx(-VIDCONFIG), vid)
            w.u64(dx(WINDOW0_HWND), hwnd)
            w.u64(dx(WINDOW0_SWAPCHAIN), 0)
            w.u32(dx(WINDOW0_W), width)
            w.u32(dx(WINDOW0_H), height)
            w.write(dx(DEVICE_LOST), bytes([1]))
            w.u32(va("unk_14A37CD6C"), frame_count)

        def set_render_target(mu):
            log("call", "R_SetRenderTarget", _context_arg(mu), u32(arg(mu, 1)))

        fakes = void_fakes("?R_SyncRenderThread@@YAXXZ", "?DB_SyncXAssets@@YAXXZ",
                           "?R_Cinematic_BeginLostDevice@@YAXXZ", "?DB_BeginRecoverLostDevice@@YAXXZ",
                           "?R_ResetModelLighting@@YAXXZ", "?R_ReleaseLostImages@@YAXXZ", "?Material_ReleaseAll@@YAXXZ",
                           "?RB_InitSceneViewport@@YAXXZ", "?R_ReloadWorld@@YAXXZ", "?Material_ReloadAll@@YAXXZ",
                           "?R_ReloadLostImages@@YAXXZ", "?DB_EndRecoverLostDevice@@YAXXZ",
                           "?R_Cinematic_EndLostDevice@@YAXXZ", "?R_FlushSwap@@YAXXZ",
                           "?Sys_DirectXFatalError@@YAXXZ")
        fakes.update({
            "?R_PopRemoteScreenUpdate@@YAHXZ": fake("R_PopRemoteScreenUpdate", "", r.choice([0, 1, 2])),
            "?R_PushRemoteScreenUpdate@@YAXH@Z": fake("R_PushRemoteScreenUpdate", "i"),
            "?R_ReleaseWorld@@YAXH@Z": fake("R_ReleaseWorld", "i"),
            "?R_GetGlobalMultisampleCount@@YAIXZ": fake("R_GetGlobalMultisampleCount", "", samples),
            "?R_ReleaseForShutdownOrReset@@YAXIH@Z": fake("R_ReleaseForShutdownOrReset", "ii"),
            "?R_ErrorDescription@@YAPEBDJ@Z": fake("R_ErrorDescription", "i", ERROR_TEXT),
            "va": fake("va", "sis"),
            "?R_CreateForInitOrReset@@YA_NH@Z": fake("R_CreateForInitOrReset", "i", r.choice([1, 1, 1, 0])),
            "?R_InitCmdBufSourceState@@YAXPEAUGfxCmdBufSourceState@@PEBUGfxCmdBufInput@@I@Z":
                fake("R_InitCmdBufSourceState", "qqi"),
            "?R_InitCmdBufState@@YAXPEAUGfxCmdBufState@@@Z": fake("R_InitCmdBufState", "q"),
            "?R_SetRenderTargetSize@@YAXPEAUGfxCmdBufSourceState@@W4GfxRenderTargetId@@@Z":
                fake("R_SetRenderTargetSize", "qi"),
            "?R_SetRenderTarget@@YAXUGfxCmdBufContext@@W4GfxRenderTargetId@@@Z": set_render_target,
        })
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


# ---- R_CreateForInitOrReset ----------------------------------------------------------------------------------

FENCE_POOL, NEXT_FENCE, FLUSH_FENCE, FLUSH_ISSUED = 0x7B98, 0x7C98, 0x7CF8, 0x7D00
CB_TABLES, DS_TABLES, BLEND_TABLES = 0x430, 0xE50, 0x10D8


def _create_buffer(hr):
    def run(mu):
        desc = bytes(mu.mem_read(arg(mu, 0), 24))
        log("call", "R_CreateBufferInternal", desc, arg(mu, 1))
        width = struct.unpack("<I", desc[:4])[0]
        CURRENT["m"]._emulated_write(arg(mu, 2), struct.pack("<Q", 0x5B000000 + width))
        return hr
    return run


def _create_for_init_inputs(seed, n=300):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        reset, minimal = r.choice([0, 0, 1, 2]), r.random() < 0.25
        fail_at = r.choice([None, None, None, 0, 1, 5, 32, 33])  # the CreateQuery call that fails
        junk = [r.getrandbits(64) for _ in range(8)]
        issued, next_fence = r.random() < 0.5, r.getrandbits(32)

        def setup(w, fail_at=fail_at, minimal=minimal, junk=junk, issued=issued, next_fence=next_fence):
            m = w.m
            calls = [0]

            def create_query(call):
                desc = bytes(call.mu.mem_read(call.arg(0), 8))
                log("CreateQuery", desc)
                i = calls[0]
                calls[0] += 1
                if i == fail_at:
                    return 0x8007000E
                m._emulated_write(call.arg(1), struct.pack("<Q", model.new(QRY, call.mu)))
                return 0

            model = ComModel(SIGS, {(DEV, 24 * 8): create_query})
            model.install(m)
            Display(com=model).install(m)
            w.u64(dx(DEVICE), model.new(DEV))
            w.write(va("g_allocateMinimalResources"), bytes([minimal]))
            for i, off in enumerate((CB_TABLES, CB_TABLES + 81 * 8, CB_TABLES + 2 * 81 * 8, DS_TABLES, BLEND_TABLES,
                                     FLUSH_FENCE)):
                w.u64(dx(off), junk[i])
            w.u64(dx(0x48), junk[6])
            w.u64(dx(0x50), junk[7])
            w.write(dx(FLUSH_ISSUED), bytes([issued]))
            w.u32(dx(NEXT_FENCE), next_fence)
            w.write(dx(FENCE_POOL), bytes([0x77]) * 0x100)
            w.u64(va("gfxAssets"), junk[0])

        fakes = void_fakes("?R_BuildSubDomainRangeConstantBuffers@@YAXXZ", "sub_1401B6130", "sub_140640510",
                           "sub_1406310F0", "sub_1406508E0", "sub_14068C300", "?R_InitRenderBuffers@@YAXXZ",
                           "sub_14063EBD0", "sub_1401B1400", "sub_140601BC0", "?R_SetupPrecompiledConstantBuffer@@YAXXZ",
                           "?R_InitDefaultDepthImage@@YAXXZ", "?R_InitDaltonize@@YAXXZ", "sub_14068EAE0",
                           "sub_140601E00", "sub_14068BC80", "sub_14068D600", "sub_1401AAEF0", "sub_1401AB1C0")
        fakes["?R_CreateBufferInternal@@YAJPEBUD3D11_BUFFER_DESC@@PEBUD3D11_SUBRESOURCE_DATA@@PEAPEAUID3D11Buffer@@@Z"] = \
            _create_buffer(r.choice([0, 0, 0x80070057]))
        out.append({"args": [reset], "setup": setup, "fakes": fakes})
    return out


# ---- R_CreateGameWindow --------------------------------------------------------------------------------------

def _create_game_window_inputs(seed, n=300):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        mode = r.choice([0, 1, 1, 2])
        aspect = r.choice([1.3333334, 1.7777778, 1.6, 1.3333333, 2.3333333])
        parms = struct.pack("<QIIiiifHHiiiiB?xxi", r.getrandbits(64), *r.choice([(60, 1), (59940, 1000), (144, 1)]),
                            mode, r.randint(-100, 2000), r.randint(-50, 1200), aspect,
                            r.choice([0x200, 0x300, 0x400]), r.choice([0x400, 0x600, 0x800]),
                            r.choice([1280, 1920, 736, 0]), r.choice([720, 1080, 460, 0]),
                            r.choice([1280, 1920, 2560, 800]), r.choice([720, 1080, 1440, 600, 0]),
                            r.randint(0, 7), r.random() < 0.3, r.choice([1, 2, 4]))
        hwnd = r.choice([0x10010, 0x10010, 0x10010, 0])
        workers = [r.random() < 0.5 for _ in range(9)]
        vid, count = _vidconfig(r), r.choice([0, 0, 0, 1])
        device_ok, create_ok = r.random() < 0.9, r.random() < 0.9

        def setup(w, hwnd=hwnd, workers=workers, vid=vid, count=count):
            m = w.m
            model = ComModel(SIGS)
            model.install(m)
            Display(com=model, create_window=hwnd).install(m)
            w.u64(dx(WINDOW0_SWAPCHAIN), model.new(SWC))
            w.u32(dx(WINDOW_COUNT), count)
            w.u32(dx(TARGET_WINDOW), 7)
            w.write(dx(-VIDCONFIG), vid)
            w.u64(va("com_wideScreen"), 0x500E00)
            for i, on in enumerate(workers):
                p = dvar(w, int(on), "<B")
                w.u64(va("r_smp_worker_thread") + 8 * i, p)

        fakes = void_fakes("?RB_InitSceneViewport@@YAXXZ", "sub_140673FE0", "sub_140631540", "sub_1406038A0",
                           "sub_14068F530", "sub_140655D70", "sub_14062C100", "sub_14063B250", "sub_14066A360",
                           "sub_140634CD0", "sub_1406294D0", "sub_1406466E0", "sub_1401AB1C0", "sub_140550190")
        fakes.update({
            "?R_CreateDevice@@YA_NPEBUGfxWindowParms@@@Z": fake("R_CreateDevice", "q", int(device_ok)),
            "?R_CreateForInitOrReset@@YA_NH@Z": fake("R_CreateForInitOrReset", "i", int(create_ok)),
            "?Dvar_SetBool@@YAXPEBUdvar_t@@_N@Z": fake("Dvar_SetBool", "qb"),
            "?Dvar_ClearModified@@YAXPEBUdvar_t@@@Z": fake("Dvar_ClearModified", "q"),
            "?sub_14046F6D0@@YAXI@Z": fake("sub_14046F6D0", "i"),
        })
        out.append({"args": [parms], "setup": setup, "fakes": fakes})
    return out


# ---- R_InitRenderBuffers -------------------------------------------------------------------------------------

def _set_quad_mesh(mu):
    log("call", "R_SetQuadMesh", arg(mu, 0), *(log_float(mu, i) for i in range(1, 9)), u32(arg(mu, 9)))


def log_float(mu, i):
    return farg(mu, i)


def _alloc_index_buffer(mu):
    size = s32(arg(mu, 1))
    name = bytes(mu.mem_read(arg(mu, 2), 32)).split(b"\0", 1)[0]
    log("call", "R_AllocDynamicIndexBuffer", arg(mu, 0), size, name)
    return 0x6A000000 + (arg(mu, 0) & 0xFFFFFF)


def _init_render_buffers_inputs(seed, n=12):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        vid = _vidconfig(r)
        fail = r.random() < 0.3

        def setup(w, vid=vid, fail=fail):
            m = w.m

            def deferred(call):
                if fail and call.arg(1) & 0x10:
                    return 0x80004005
                return out_object(model, CTX)(call)

            model = ComModel(SIGS, {(DEV, 27 * 8): deferred})
            model.install(m)
            Display(com=model).install(m)
            w.u64(dx(DEVICE), model.new(DEV))
            w.write(dx(-VIDCONFIG), vid)

        fakes = {
            "?R_AllocDynamicIndexBuffer@@YAPEAXPEAPEAUID3D11Buffer@@HPEBD@Z": _alloc_index_buffer,
            "?R_InitDynamicVertexBufferState@@YAXPEAUGfxVertexBufferState@@H_N@Z":
                fake("R_InitDynamicVertexBufferState", "qib"),
            "?R_AssignNullBuffer@@YAXPEAPEAUID3D11Buffer@@@Z": fake("R_AssignNullBuffer", "q"),
            "?R_SetQuadMesh@@YAXPEAUGfxQuadMeshData@@MMMMMMMMI@Z": _set_quad_mesh,
            "?R_InitBatchedQuadMesh@@YAXPEAUGfxMeshData@@H@Z": fake("R_InitBatchedQuadMesh", "qi"),
            "?sub_14066A480@@YAPEAXIPEBD@Z": fake("sub_14066A480", "is", 0x7B000000),
            "?sub_1401ACD10@@YAXPEAUGfxComputeCmdBuf@@PEAXI@Z": fake("sub_1401ACD10", "qqi"),
        }
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


# ---- R_ReleaseForShutdownOrReset ------------------------------------------------------------------------------

CB_COUNTS, DS_COUNTS, BLEND_COUNTS = 0x60, 0xBC8, 0xD0C
DEFAULT_CB, DEFAULT_DS, DEFAULT_BLEND, DS_BITS, BLEND_BITS = 0x2760, 0x1360, 0x1B60, 0x1D60, 0x2560
RASTERIZERS, SAMPLERS = 0x2660, 0x3368


def _shutdown_zone_state(mu):
    """sub_140632700(zone): like the PS4 server's R_ShutdownZoneState, it clears the zone's state counts."""
    zone = arg(mu, 0) & 0xFF
    CURRENT["m"]._emulated_write(dx(DS_COUNTS + 4 * zone), bytes(4))
    CURRENT["m"]._emulated_write(dx(BLEND_COUNTS + 4 * zone), bytes(4))
    return None


def _release_inputs(seed, n=150):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        reset, minimal = r.choice([0, 1, 5]), r.random() < 0.3
        windows, fullscreen = r.choice([0, 1, 1]), r.random() < 0.5
        cb_counts = [r.choice([0, 1, 2, 5]) for _ in range(3)]
        ds_count, blend_count = r.choice([0, 1, 3, 9]), r.choice([0, 1, 2, 7])
        flush, query = r.random() < 0.7, r.random() < 0.6
        fences = [r.random() < 0.8 for _ in range(32)]
        samplers = [r.random() < 0.1 for _ in range(256)]
        frames = _swap_frames(r)
        lock = _lock_state(r)
        junk = bytes(r.getrandbits(8) for _ in range(0x60))

        def setup(w, reset=reset, minimal=minimal, windows=windows, fullscreen=fullscreen, cb_counts=cb_counts,
                  ds_count=ds_count, blend_count=blend_count, flush=flush, query=query, fences=fences,
                  samplers=samplers, frames=frames, lock=lock, junk=junk):
            m = w.m

            def get_fullscreen(call):
                call.write(call.arg(0), struct.pack("<i", int(fullscreen)))
                return 0

            model = ComModel(SIGS, {(SWC, 11 * 8): get_fullscreen})
            model.install(m)
            Display(com=model).install(m)
            lock(w)
            _write_swap_frames(w, frames)
            w.u32(dx(WINDOW_COUNT), windows)
            w.u64(dx(WINDOW0_SWAPCHAIN), model.new(SWC))
            w.u64(dx(WINDOW0_DEPTH), model.new(RES))
            for k, c in enumerate(cb_counts):
                w.u32(dx(CB_COUNTS + 4 * 81 * k), c)
                w.u64(dx(CB_TABLES + 8 * 81 * k), 0x1234)
                w.write(dx(DEFAULT_CB + 0x400 * k), junk[:0x40])
            w.u64(dx(0x48), model.new(RES))
            w.u64(dx(0x50), model.new(RES))
            w.u32(dx(DS_COUNTS), ds_count)
            w.u32(dx(BLEND_COUNTS), blend_count)
            w.write(dx(DEFAULT_DS), junk * 2)
            w.write(dx(DS_BITS), junk * 2)
            w.write(dx(DEFAULT_BLEND), junk)
            w.write(dx(BLEND_BITS), junk)
            for i in range(32):
                w.u64(dx(RASTERIZERS + 8 * i), model.new(STATE))
            w.u64(dx(FLUSH_FENCE), model.new(QRY) if flush else 0)
            for i, on in enumerate(fences):
                w.u64(dx(FENCE_POOL + 8 * i), model.new(QRY) if on else 0)
            w.u64(va("gfxAssets"), model.new(QRY) if query else 0)
            for i, on in enumerate(samplers):
                w.u64(dx(SAMPLERS + 8 * i), model.new(STATE) if on else 0)
            w.write(va("g_allocateMinimalResources"), bytes([minimal]))

        fakes = dict(FENCE_FAKES)
        fakes.update(void_fakes("?R_ShutdownSubDomainRangeConstantBuffers@@YAXXZ", "sub_1401B7160", "sub_140640830",
                                "sub_1401AB230", "sub_1406513F0", "sub_14063F200", "sub_1401B1390", "sub_14062C5C0",
                                "sub_1401A9990", "sub_14068F3B0", "sub_1401B7F00", "sub_140602360", "sub_140602550",
                                "sub_14064D450", "sub_14068DB60", "sub_14068C170", "sub_140663EA0", "sub_140663EB0",
                                "sub_140663D60"))
        fakes.update({
            "?R_ReleaseBuffer@@YAJPEAUID3D11Buffer@@@Z": fake("R_ReleaseBuffer", "q"),
            "?sub_1401B0000@@YAXPEAUID3D11Buffer@@@Z": fake("sub_1401B0000", "q"),
            "?sub_140632700@@YAXE@Z": fake("sub_140632700", "b", _shutdown_zone_state),
        })
        out.append({"args": [r.getrandbits(32), reset], "setup": setup, "fakes": fakes})
    return out


# ---- R_Shutdown ---------------------------------------------------------------------------------------------

def _load_xassets(mu):
    log("call", "DB_LoadXAssets", bytes(mu.mem_read(arg(mu, 0), 16)), u32(arg(mu, 1)), u32(arg(mu, 2)))


def _shutdown_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        destroy, restart = r.choice([0, 1, 1, 7]), r.choice([0, 1, 3])
        device, lost = r.random() < 0.8, r.random() < 0.3
        objects = [r.random() < 0.8 for _ in range(5)]  # context, device, output, adapter, factory
        windows, is_window = r.choice([0, 1, 1]), r.random() < 0.8
        lock = _lock_state(r)
        junk = r.getrandbits(64)

        def setup(w, device=device, lost=lost, objects=objects, windows=windows, is_window=is_window, lock=lock,
                  junk=junk):
            m = w.m
            model = ComModel(SIGS)
            model.install(m)
            Display(com=model, windows={0x10010} if is_window else set()).install(m)
            lock(w)
            for off, kind, on in zip((CONTEXT, DEVICE, OUTPUT, ADAPTER, FACTORY), (CTX, DEV, OUT, ADP, FAC), objects):
                w.u64(dx(off), model.new(kind) if on else 0)
            if not device:
                w.u64(dx(DEVICE), 0)
            w.write(dx(DEVICE_LOST), bytes([lost]))
            w.u32(dx(WINDOW_COUNT), windows)
            w.u64(dx(WINDOW0_HWND), 0x10010)
            for name in ("unk_14A34B558", "unk_14A37D5B8", "unk_14A37D5D0", "unk_14B89E280"):
                w.u64(va(name), junk)
            w.u64(va("unk_14A37D5B8") + 8, junk)
            w.u64(va("unk_14A37D5B8") + 16, junk)
            w.u64(va("unk_14A37D5D0") + 8, junk)
            w.u64(va("unk_14B89E280") + 56, junk)
            w.u32(va("unk_14A346A94"), junk)
            w.write(va("unk_14A37D581"), bytes([1]))
            for name in ("r_nvidiaGPU", "r_nvidiaGPUCount"):
                w.u64(va(name), dvar(w, 1))

        fakes = void_fakes("?R_SyncRenderThread@@YAXXZ", "sub_1401AAE90", "sub_140683F70", "sub_140634FC0",
                           "?R_ResetModelLighting@@YAXXZ", "sub_14063ECE0", "sub_1406652E0",
                           "?R_UnlockSkinnedCache@@YAXXZ", "sub_140316750", "sub_14018F210", "sub_140460B90",
                           "?DB_ShutdownXAssets@@YAXXZ", "sub_140603D50", "sub_14064D7E0", "sub_14062EB40",
                           "sub_140605130")
        fakes.update({
            "?R_ClearAllStreamSources@@YAXPEAUGfxCmdBufPrimState@@@Z": fake("R_ClearAllStreamSources", "q"),
            "?sub_140600CB0@@YAXH@Z": fake("sub_140600CB0", "i"),
            "?DB_LoadXAssets@@YAXPEAUXZoneInfo@@IW4DBSyncMode@@@Z": _load_xassets,
            "?R_ReleaseForShutdownOrReset@@YAXIH@Z": fake("R_ReleaseForShutdownOrReset", "ii"),
            "?Dvar_SetBool@@YAXPEBUdvar_t@@_N@Z": fake("Dvar_SetBool", "qb"),
            "?Dvar_SetInt@@YAXPEBUdvar_t@@H@Z": fake("Dvar_SetInt", "qi"),
        })
        out.append({"args": [destroy, restart], "setup": setup, "fakes": fakes})
    return out


# ---- RB_SwapBuffers -------------------------------------------------------------------------------------------

def _com_error(mu):
    fmt = bytes(mu.mem_read(arg(mu, 1), 80)).split(b"\0", 1)[0]
    args = []
    for i, conv in enumerate(c for c in fmt.split(b"%")[1:] if c):
        v = arg(mu, 2 + i)
        args.append(bytes(mu.mem_read(v, 40)).split(b"\0", 1)[0] if conv[:1] == b"s" else u32(v))
    log("call", "Com_Error", u32(arg(mu, 0)), fmt, *args)


def _swap_buffers_inputs(seed, n=300):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        vsync, mode = r.choice([-2, 0, 1, 2, 4, 5, 9]), r.choice([0, 0, 1, 2])
        alt, capture = r.random() < 0.08, r.random() < 0.08
        fullscreen, activated = r.choice([0, 1]), r.random() < 0.2
        present_hr = r.choice([0, 0, 0, 0x087A0001, 0x887A0005, 0x887A0005, 0x887A0001, 0x80070057])
        reason = r.choice([0x887A0001, 0x887A0005, 0x887A0006, 0x887A0007, 0x887A0020, 0, 0x887A0002])
        device = r.random() < 0.9
        main, waits = r.random() < 0.5, r.choice([0, 0, 1, 3])
        busy = r.choice([0, 0, 1, 2, 5])
        next_fence = r.choice([0, 5, 30, 31])
        lock = _lock_state(r)
        frames = _swap_frames(r)
        target = r.choice([0, 0, 0x10000])

        def setup(w, vsync=vsync, mode=mode, alt=alt, fullscreen=fullscreen, activated=activated,
                  present_hr=present_hr, reason=reason, device=device, waits=waits, busy=busy,
                  next_fence=next_fence, lock=lock, frames=frames, target=target):
            m = w.m
            pending = [busy]

            def get_fullscreen(call):
                call.write(call.arg(0), struct.pack("<i", fullscreen))
                return 0

            def get_data(call):
                if pending[0]:
                    pending[0] -= 1
                    return 1
                return 0

            model = ComModel(SIGS, {(SWC, 11 * 8): get_fullscreen, (SWC, 8 * 8): returns(present_hr),
                                    (DEV, 39 * 8): returns(reason), (CTX, 29 * 8): get_data})
            model.install(m)
            Display(com=model, wait_results=[0] + [0x102] * waits + [0]).install(m)
            lock(w)
            _write_swap_frames(w, frames)
            w.u64(va("r_vsync"), dvar(w, vsync))
            w.u64(va("r_displayMode"), dvar(w, mode))
            w.u32(va("unk_14A37D568"), int(alt))
            w.u32(va("unk_149D62D6C"), int(activated))
            w.u64(va("unk_14B07F658"), 0x7E0000)
            w.u32(dx(TARGET_WINDOW), target)
            w.u64(dx(WINDOW0_HWND), 0x10010)
            w.u64(dx(WINDOW0_SWAPCHAIN), model.new(SWC))
            w.u64(dx(CONTEXT), model.new(CTX))
            w.u64(dx(DEVICE), model.new(DEV) if device else 0)
            for i in range(32):
                w.u64(dx(FENCE_POOL + 8 * i), model.new(QRY))
            w.u32(dx(NEXT_FENCE), next_fence)
            w.u64(va("unk_14A107B60"), va("unk_14B89E280"))
            w.u32(va("unk_14B89E280"), 0x5555)

        fakes = {
            "?sub_1406968F0@@YA_NXZ": fake("sub_1406968F0", "", int(capture)),
            "?sub_1406967E0@@YAXPEAUID3D11DeviceContext@@PEAUID3D11RenderTargetView@@@Z": fake("sub_1406967E0", "qq"),
            "?sub_140696900@@YAXPEAUID3D11DeviceContext@@PEAUID3D11RenderTargetView@@@Z": fake("sub_140696900", "qq"),
            "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _com_error,
            "?R_ErrorDescription@@YAPEBDJ@Z": fake("R_ErrorDescription", "i", ERROR_TEXT),
            "?Sys_IsMainThread@@YA_NXZ": fake("Sys_IsMainThread", "", int(main)),
            "?Sys_LoadingKeepAlive@@YAXXZ": fake("Sys_LoadingKeepAlive"),
        }
        out.append({"args": [], "setup": setup, "fakes": fakes})
    return out


# ---- R_ErrorDescription, R_ComErrorCleanup -------------------------------------------------------------------

MESSAGES = {0x80070057: b"The parameter is incorrect.\r\n", 0x887A0005: b"The GPU device instance has been suspended.",
            0x8007000E: b"Not enough memory resources are available to complete this operation." * 20}


def _error_description_inputs(seed, n=60):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        hr = r.choice(list(MESSAGES) + [0x887A0001, 0, 0x80004005, r.getrandbits(32)])
        old = bytes(r.getrandbits(8) for _ in range(16))
        out.append({"args": [hr], "setup": lambda w, old=old: (Display(messages=MESSAGES).install(w.m),
                                                                 w.write(static_fn("R_ErrorDescription", "buffer"),
                                                                         old))})
    return out


def _com_error_cleanup_inputs(seed, n=100):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        force, data, pending = r.choice([0, 0, 1, 2]), r.random() < 0.7, r.choice([0, 0, 1, 0x100])
        device, lock = r.random() < 0.8, _lock_state(r)

        def setup(w, data=data, pending=pending, device=device, lock=lock):
            Display().install(w.m)
            lock(w)
            flag = va("unk_14B89E280")
            w.u32(flag, pending)
            w.u64(va("frontEndDataOut"), flag - 0x151464 if data else 0)
            w.u64(dx(DEVICE), 0x900000 if device else 0)
        fakes = void_fakes("?CG_HudLighting_ComErrorCleanup@@YAXXZ", "?R_AbortRenderCommands@@YAXXZ",
                           "?R_SyncRenderThread@@YAXXZ", "?R_FlushSwap@@YAXXZ")
        fakes["?RB_SetUploadShaderFastMode@@YAXH@Z"] = fake("RB_SetUploadShaderFastMode", "i")
        out.append({"args": [force], "setup": setup, "fakes": fakes})
    return out


CASES = [
    {"symbol": "?R_ErrorDescription@@YAPEBDJ@Z", "build": STORE, "ret": "cstr",
     "inputs": _error_description_inputs(603)},
    {"symbol": "?R_ComErrorCleanup@@YAXH@Z", "build": STORE, "ret": "void", "inputs": _com_error_cleanup_inputs(7684)},
    {"symbol": "?R_FlushSwap@@YAXXZ", "build": STORE, "ret": "void", "inputs": _flush_swap_inputs(3699)},
    {"symbol": "?sub_14062EC80@@YAXPEAUID3D11Query@@@Z", "build": STORE, "ret": "void",
     "inputs": _swap_fence_inputs(2780)},
    {"symbol": "?R_RecoverLostDevice@@YA_NXZ", "build": STORE, "ret": "char", "inputs": _recover_inputs(7525)},
    {"symbol": "?R_CreateForInitOrReset@@YA_NH@Z", "build": STORE, "ret": "char",
     "inputs": _create_for_init_inputs(1265)},
    {"symbol": "?R_CreateGameWindow@@YA_NPEAUGfxWindowParms@@@Z", "build": STORE, "ret": "char",
     "inputs": _create_game_window_inputs(2272)},
    {"symbol": "?R_InitRenderBuffers@@YAXXZ", "build": STORE, "ret": "void",
     "inputs": _init_render_buffers_inputs(657)},
    {"symbol": "?R_ReleaseForShutdownOrReset@@YAXIH@Z", "build": STORE, "ret": "void",
     "inputs": _release_inputs(2572)},
    {"symbol": "?R_Shutdown@@YAXHH@Z", "build": STORE, "ret": "void", "inputs": _shutdown_inputs(1117)},
    {"symbol": "?RB_SwapBuffers@@YAXXZ", "build": STORE, "ret": "void", "inputs": _swap_buffers_inputs(5189)},
    {"symbol": "?R_CompareDisplayModes@@YAHPEBX0@Z", "build": STORE, "ret": "int",
     "inputs": _compare_modes_inputs(1439)},
    {"symbol": "?R_CompareRefreshRates@@YAHPEBX0@Z", "build": STORE, "ret": "int",
     "inputs": _compare_rates_inputs(1477)},
    {"symbol": "?R_EnumDisplayModes@@YAXXZ", "build": STORE, "ret": "void", "inputs": _enum_modes_inputs(1501)},
    {"symbol": "?R_SetWndParms@@YAXPEAUGfxWindowParms@@PEBUGfxWindowInput@@@Z", "build": STORE, "ret": "void",
     "inputs": _set_wnd_parms_inputs(2357)},
    {"symbol": "?R_CreateDevice@@YA_NPEBUGfxWindowParms@@@Z", "build": STORE, "ret": "char",
     "inputs": _create_device_inputs(2000)},
    {"symbol": "?R_MonitorEnumCallback@@YAHPEAUHMONITOR__@@PEAUHDC__@@PEAUtagRECT@@_J@Z", "build": STORE,
     "ret": "int", "inputs": _monitor_cb_inputs(1676)},
    {"symbol": "?sub_140631830@@YAHPEAUHMONITOR__@@PEAUHDC__@@PEAUtagRECT@@_J@Z", "build": STORE, "ret": "int",
     "inputs": _monitor_cb_inputs(1830)},
    {"symbol": "?sub_140632660@@YAXXZ", "build": STORE, "ret": "void", "inputs": _stream_inputs(2660)},
    {"symbol": "?R_CheckLostDevice@@YA_NXZ", "build": STORE, "ret": "char", "inputs": _check_lost_inputs(7628)},
    {"symbol": "?R_ChooseAdapter@@YAXXZ", "build": STORE, "ret": "void", "inputs": _choose_adapter_inputs(1713)},
]
