"""Flip-model presentation (enhanced/gfx_d3d/r_init.cpp, records/patches.tsv P0003).

What must hold:
- the factory comes from CreateDXGIFactory1 (DXGI 1.1), whatever interface is asked for;
- R_CreateDevice creates a DXGI_SWAP_EFFECT_FLIP_DISCARD swap chain with two buffers, with ALLOW_TEARING exactly
  when IDXGIFactory5 reports tearing support and FRAME_LATENCY_WAITABLE_OBJECT (P0004, tests in
  test_frame_wait.py), and limits the device to one queued frame;
- when the system refuses the waitable flag, the flip-model swap chain is made without it; when it refuses a
  flip-model swap chain, the original description is used and nothing else changes;
- RB_SwapBuffers presents with DXGI_PRESENT_ALLOW_TEARING only for a windowed sync interval 0 with tearing allowed,
  and binds the render targets that were bound before the present again after it (flip model unbinds the back
  buffer), releasing the references it took;
- a lost device's new swap chain is made the same way, after the context is cleared and flushed.
"""
import struct

from com import ComModel
from syms import va
from win32_display import MUTEX, Display, logged_fake

FAC, DEV, CTX, SWC, QRY, ADP, UNK = ("IDXGIFactory", "ID3D11Device", "ID3D11DeviceContext", "IDXGISwapChain",
                                     "ID3D11Query", "IDXGIAdapter", "IUnknown")
VIEW = "ID3D11View"
QI, RELEASE = 0, 2 * 8
CREATE_SWAP_CHAIN, MWA = 10 * 8, 8 * 8
CHECK_FEATURE, SET_LATENCY = 28 * 8, 12 * 8
PRESENT, GET_FULLSCREEN = 8 * 8, 11 * 8
OM_SET, OM_GET = 33 * 8, 89 * 8
CLEAR_STATE, FLUSH = 110 * 8, 111 * 8
GET_DATA, END = 29 * 8, 28 * 8

FACTORY5 = bytes.fromhex("f5e13276" "65ee" "ca4d") + bytes([0x87, 0xFD, 0x84, 0xCD, 0x75, 0xF8, 0x83, 0x8D])
DEVICE1 = bytes.fromhex("0f97db77" "7662" "ba48") + bytes([0xBA, 0x28, 0x07, 0x01, 0x43, 0xB4, 0x39, 0x2C])

SIGS = {
    (FAC, QI): "pp", (FAC, CREATE_SWAP_CHAIN): "ppp", (FAC, MWA): "pi", (FAC, RELEASE): "",
    (DEV, QI): "pp", (DEV, 30 * 8): "iip", (DEV, RELEASE): "",
    (ADP, 8 * 8): "p",
    (UNK, CHECK_FEATURE): "ipi", (UNK, SET_LATENCY): "i", (UNK, RELEASE): "",
    (SWC, PRESENT): "ii", (SWC, GET_FULLSCREEN): "pp", (SWC, QI): "pp",
    (UNK, 31 * 8): "i", (UNK, 33 * 8): "",  # IDXGISwapChain2: SetMaximumFrameLatency, GetFrameLatencyWaitableObject
    (CTX, OM_GET): "ipp", (CTX, OM_SET): "ipp", (CTX, CLEAR_STATE): "", (CTX, FLUSH): "",
    (CTX, GET_DATA): "ppii", (CTX, END): "p",
    (QRY, 7 * 8): "",
    (VIEW, RELEASE): "",
}
DUMPS = {(FAC, QI): {0: 16}, (DEV, QI): {0: 16}, (SWC, QI): {0: 16}}

# dx fields (gfx_d3d/r_dx.h)
DEVICE, CONTEXT, LOCK_COUNT, FACTORY, ADAPTER = 0x08, 0x10, 0x18, 0x20, 0x28
MUTEX_OFF, FENCE_POOL, NEXT_FENCE = 0x3B68, 0x7B98, 0x7C98
TARGET_WINDOW, WINDOW0_HWND, WINDOW0_SWAPCHAIN = 0x7CCC, 0x7CD8, 0x7CE0


def dx(off):
    return va("dx") + off


def _desc(mu, p):
    """(BufferCount, Windowed, SwapEffect, Flags) of a DXGI_SWAP_CHAIN_DESC."""
    count = struct.unpack_from("<I", bytes(mu.mem_read(p + 0x28, 4)))[0]
    windowed, effect, flags = struct.unpack("<III", bytes(mu.mem_read(p + 0x38, 12)))
    return count, windowed, effect, flags


def _scratch_dvar(w, value):
    p = w.alloc(bytes(0x60))
    w.write(p + 0x10, struct.pack("<i", value))
    return p


# ---- R_CreateDevice ------------------------------------------------------------------------------------------

WAITABLE = 0xABC0  # the handle GetFrameLatencyWaitableObject returns


def _create_device(env, tearing=True, factory5=True, flip_ok=True, device1=True, waitable_ok=True, swapchain2=True,
                   old_waitable=0):
    descs = []

    def setup(w):
        m = w.m

        def qi_factory(call):
            if not factory5:
                return 0x80004002  # E_NOINTERFACE
            return call.out_object(1, UNK) and 0

        def check_feature(call):
            call.write(call.arg(1), struct.pack("<I", int(tearing)))
            return 0

        def qi_device(call):
            if not device1:
                return 0x80004002
            return call.out_object(1, UNK) and 0

        def create_swap_chain(call):
            descs.append(_desc(call.mu, call.arg(1)))
            if not flip_ok and descs[-1][2] == 4:
                return 0x887A0001  # DXGI_ERROR_INVALID_CALL
            if not waitable_ok and descs[-1][3] & 0x40:
                return 0x887A0001
            m._emulated_write(call.arg(2), struct.pack("<Q", model.new(SWC, call.mu)))
            return 0

        def qi_swap_chain(call):
            if not swapchain2:
                return 0x80004002
            return call.out_object(1, UNK) and 0

        def adapter_desc(call):
            call.write(call.arg(0), bytes(0x100) + struct.pack("<I", 0x10DE) + bytes(0x2C))
            return 0

        model = ComModel(SIGS, {(FAC, QI): qi_factory, (UNK, CHECK_FEATURE): check_feature, (DEV, QI): qi_device,
                                (FAC, CREATE_SWAP_CHAIN): create_swap_chain, (ADP, 8 * 8): adapter_desc,
                                (SWC, QI): qi_swap_chain, (UNK, 33 * 8): lambda call: WAITABLE}, DUMPS)
        model.install(m)
        display = Display(mutex=MUTEX)
        display.com = model
        display.install(m)
        w.u64(dx(FACTORY), model.new(FAC))
        w.u64(dx(ADAPTER), model.new(ADP))
        w.u64(dx(WINDOW0_HWND), 0x10010)
        for name in ("r_rendererInUse", "r_amdGPU", "r_multiGPU"):
            w.u64(va(name), _scratch_dvar(w, 0))
        w.write(env.data("s_flipModel"), b"\x01")
        w.write(env.data("s_allowTearing"), b"\x00")
        w.write(env.data("s_latencyWaitable"), b"\x01")
        w.u64(env.data("s_frameLatencyWaitable"), old_waitable)
        w.u32(env.data("s_presentCount"), 7)
        w.u32(env.data("s_waitedPresentCount"), 6)
        w.write(env.data("s_resyncFrameLatency"), b"\x01")

    parms = struct.pack("<QIIiiifHHiiiiBBxxi", 0x10010, 60, 1, 0, 0, 0, 1.7777778, 0x200, 0x400, 1920, 1080,
                        1920, 1080, 0, 0, 0)
    fakes = {
        "?sub_1401B0030@@YAXXZ": logged_fake("sub_1401B0030", ""),
        "?Dvar_SetInt@@YAXPEBUdvar_t@@H@Z": logged_fake("Dvar_SetInt", "qi"),
        "?Dvar_SetBool@@YAXPEBUdvar_t@@_N@Z": logged_fake("Dvar_SetBool", "qb"),
        "?R_IsReallyNvidiaGPU@@YA_NXZ": logged_fake("R_IsReallyNvidiaGPU", "", 0),
    }
    value, _, written, observed = env.call("?R_CreateDevice@@YA_NPEBUGfxWindowParms@@@Z", [parms], "char",
                                           setup=setup, fakes=fakes)
    return value, descs, written, observed


def _coms(observed, kind=None, offset=None):
    return [o for o in observed if o[0] == "com" and (kind is None or o[1] == kind)
            and (offset is None or o[2] == offset)]


def test_flip_swap_chain_with_tearing(env):
    value, descs, written, observed = _create_device(env, tearing=True)
    assert value == 1, value
    # two buffers, windowed, FLIP_DISCARD, ALLOW_MODE_SWITCH | ALLOW_TEARING | FRAME_LATENCY_WAITABLE_OBJECT
    assert descs == [(2, 1, 4, 0x842)], descs
    qi = _coms(observed, FAC, QI)
    assert qi and qi[0][4] == ("bytes", FACTORY5), qi
    assert _coms(observed, UNK, CHECK_FEATURE)[0][4:6] == (0, ("ptr",))
    assert _coms(observed, DEV, QI)[0][4] == ("bytes", DEVICE1)
    assert _coms(observed, UNK, SET_LATENCY) and _coms(observed, UNK, SET_LATENCY)[0][4] == 1
    assert written[env.data("s_allowTearing")] == b"\x01"


def test_flip_swap_chain_without_tearing(env):
    for kwargs in ({"tearing": False}, {"factory5": False}):
        value, descs, written, observed = _create_device(env, **kwargs)
        assert descs == [(2, 1, 4, 0x42)], (kwargs, descs)
        # stays false (the harness reports 8 bytes from each changed address, so compare the value)
        assert written.get(env.data("s_allowTearing"), b"\x00") == b"\x00", kwargs


def test_no_frame_latency_call_without_dxgi_device1(env):
    _, descs, _, observed = _create_device(env, device1=False)
    assert descs == [(2, 1, 4, 0x842)]
    assert not _coms(observed, UNK, SET_LATENCY)


def test_original_swap_chain_when_flip_is_refused(env):
    value, descs, written, observed = _create_device(env, flip_ok=False)
    assert value == 1
    # flip with and without the waitable object, then the original: DISCARD, ALLOW_MODE_SWITCH
    assert descs == [(2, 1, 4, 0x842), (2, 1, 4, 0x802), (2, 1, 0, 0x2)], descs
    assert written[env.data("s_flipModel")] == b"\x00"
    assert written.get(env.data("s_allowTearing"), b"\x00") == b"\x00"


def test_flip_without_waitable_when_refused(env):
    value, descs, written, observed = _create_device(env, waitable_ok=False)
    assert value == 1
    assert descs == [(2, 1, 4, 0x842), (2, 1, 4, 0x802)], descs
    assert written[env.data("s_latencyWaitable")] == b"\x00"
    assert written.get(env.data("s_flipModel"), b"\x01") == b"\x01"


def test_factory_is_dxgi_1_1(env):
    calls = []

    def setup(w):
        w.m.on_import("dxgi.dll!CreateDXGIFactory1", lambda mu: calls.append("CreateDXGIFactory1"))
    env.call("CreateDXGIFactory", [0x1000, 0x2000], "int", setup=setup)
    assert calls == ["CreateDXGIFactory1"], calls


# ---- RB_SwapBuffers ------------------------------------------------------------------------------------------

def _swap(env, flip=True, tearing=True, vsync=0, fullscreen=False, bound=True, extra=None, written=False,
          display_mode=None):
    """extra: {static name: (format letter, value)} written before the call; written: also return the writes."""
    def setup(w):
        m = w.m

        def om_get(call):
            if bound:
                call.write(call.arg(1), struct.pack("<Q", model.new(VIEW, call.mu)))
                call.write(call.arg(2), struct.pack("<Q", model.new(VIEW, call.mu)))
            else:
                call.write(call.arg(1), struct.pack("<Q", 0))
                call.write(call.arg(2), struct.pack("<Q", 0))
            return None

        def fullscreen_state(call):
            call.write(call.arg(0), struct.pack("<i", int(fullscreen)))
            return 0

        model = ComModel(SIGS, {(CTX, OM_GET): om_get, (SWC, GET_FULLSCREEN): fullscreen_state})
        model.install(m)
        display = Display(mutex=MUTEX)
        display.com = model
        display.install(m)
        w.u64(dx(CONTEXT), model.new(CTX))
        w.u64(dx(DEVICE), model.new(DEV))
        w.u64(dx(WINDOW0_SWAPCHAIN), model.new(SWC))
        w.u64(dx(WINDOW0_HWND), 0x10010)
        w.u32(dx(TARGET_WINDOW), 0)
        w.u64(dx(MUTEX_OFF), MUTEX)
        w.u32(dx(LOCK_COUNT), 0)
        w.u32(dx(NEXT_FENCE), 0)
        w.u64(dx(FENCE_POOL), model.new(QRY))
        w.u64(va("r_vsync"), _scratch_dvar(w, vsync))
        w.u64(va("r_displayMode"), _scratch_dvar(w, display_mode if display_mode is not None else
                                                     0 if fullscreen else 2))
        w.u32(va("unk_14A37D568"), 0)
        w.u32(va("unk_149D62D6C"), 0)
        w.u64(va("unk_14A107B60"), w.alloc(bytes(8)))
        w.write(env.data("s_flipModel"), bytes([flip]))
        w.write(env.data("s_allowTearing"), bytes([tearing]))
        w.u64(env.data("s_frameLatencyWaitable"), 0)
        for name, (fmt, value) in (extra or {}).items():
            w.write(env.data(name), struct.pack("<" + fmt.replace("i", "I").replace("b", "B").replace("q", "Q"),
                                                value))

    fakes = {
        "?sub_1406968F0@@YA_NXZ": logged_fake("sub_1406968F0", "", 0),
        "?Sys_IsMainThread@@YA_NXZ": logged_fake("Sys_IsMainThread", "", 0),
        "?sub_14062EC80@@YAXPEAUID3D11Query@@@Z": logged_fake("sub_14062EC80", "q"),
    }
    _, _, writes, observed = env.call("?RB_SwapBuffers@@YAXXZ", [], setup=setup, fakes=fakes)
    calls = [o for o in observed if o[0] == "com" and o[2] in (OM_GET, OM_SET, PRESENT, RELEASE)]
    return (calls, writes) if written else calls


def test_present_rebinds_render_targets(env):
    calls = _swap(env)
    kinds = [(o[1], o[2]) for o in calls]
    assert kinds == [(CTX, OM_GET), (SWC, PRESENT), (CTX, OM_SET), (VIEW, RELEASE), (VIEW, RELEASE)], kinds
    get, present, set_ = calls[0], calls[1], calls[2]
    assert get[4] == 1 and set_[4] == 1
    assert present[4:6] == (0, 0x200), present  # sync interval 0, DXGI_PRESENT_ALLOW_TEARING
    assert set_[6] == ("obj", 6), set_  # the depth-stencil view OMGetRenderTargets returned (object 6)


def test_present_with_nothing_bound(env):
    calls = _swap(env, bound=False)
    kinds = [(o[1], o[2]) for o in calls]
    assert kinds == [(CTX, OM_GET), (SWC, PRESENT), (CTX, OM_SET)], kinds
    assert calls[2][6] == 0


def test_tearing_flag_only_windowed_with_sync_interval_zero(env):
    for kwargs, flags in (({"vsync": 1}, 0), ({"fullscreen": True}, None), ({"tearing": False}, 0),
                          ({"vsync": 0}, 0x200)):
        calls = _swap(env, **kwargs)
        presents = [o for o in calls if o[1] == SWC and o[2] == PRESENT]
        if flags is None:
            # a fullscreen state that doesn't match r_displayMode goes to the window procedure: no present here
            continue
        assert presents and presents[0][5] == flags, (kwargs, presents)


def test_original_present_without_flip(env):
    calls = _swap(env, flip=False, tearing=False)
    kinds = [(o[1], o[2]) for o in calls]
    assert kinds == [(SWC, PRESENT)], kinds
    assert calls[0][4:6] == (0, 0)


# ---- R_RecoverLostDevice -------------------------------------------------------------------------------------

RECOVER_CALLEES = ("?R_PopRemoteScreenUpdate@@YAHXZ", "?R_SyncRenderThread@@YAXXZ", "?DB_SyncXAssets@@YAXXZ",
                   "?R_Cinematic_BeginLostDevice@@YAXXZ", "?DB_BeginRecoverLostDevice@@YAXXZ",
                   "?R_ResetModelLighting@@YAXXZ", "?R_ReleaseLostImages@@YAXXZ", "?Material_ReleaseAll@@YAXXZ",
                   "?R_ReleaseWorld@@YAXH@Z", "?R_ReloadWorld@@YAXXZ", "?Material_ReloadAll@@YAXXZ",
                   "?R_ReloadLostImages@@YAXXZ", "?DB_EndRecoverLostDevice@@YAXXZ",
                   "?R_Cinematic_EndLostDevice@@YAXXZ", "?R_PushRemoteScreenUpdate@@YAXH@Z", "?R_FlushSwap@@YAXXZ",
                   "?R_ReleaseForShutdownOrReset@@YAXIH@Z", "?R_GetGlobalMultisampleCount@@YAIXZ",
                   "?R_InitCmdBufSourceState@@YAXPEAUGfxCmdBufSourceState@@PEBUGfxCmdBufInput@@I@Z",
                   "?R_InitCmdBufState@@YAXPEAUGfxCmdBufState@@@Z", "?RB_InitSceneViewport@@YAXXZ",
                   "?R_SetRenderTargetSize@@YAXPEAUGfxCmdBufSourceState@@W4GfxRenderTargetId@@@Z",
                   "?R_SetRenderTarget@@YAXUGfxCmdBufContext@@W4GfxRenderTargetId@@@Z")


def _recover(env, flip=True, tearing=True, old_waitable=None):
    """old_waitable: also returns (written, observed), with that waitable object before the call."""
    descs = []

    def setup(w):
        m = w.m

        def create_swap_chain(call):
            descs.append(_desc(call.mu, call.arg(1)))
            m.observed.append(("create swap chain",))
            m._emulated_write(call.arg(2), struct.pack("<Q", model.new(SWC, call.mu)))
            return 0

        model = ComModel(SIGS, {(FAC, CREATE_SWAP_CHAIN): create_swap_chain,
                                (SWC, QI): lambda call: call.out_object(1, UNK) and 0,
                                (UNK, 33 * 8): lambda call: WAITABLE}, DUMPS)
        model.install(m)
        display = Display(mutex=MUTEX)
        display.com = model
        display.install(m)
        w.u64(dx(FACTORY), model.new(FAC))
        w.u64(dx(DEVICE), model.new(DEV))
        w.u64(dx(CONTEXT), model.new(CTX))
        w.u64(dx(WINDOW0_HWND), 0x10010)
        w.write(env.data("s_flipModel"), bytes([flip]))
        w.write(env.data("s_allowTearing"), bytes([tearing]))
        w.write(env.data("s_latencyWaitable"), bytes([flip]))
        w.u64(env.data("s_frameLatencyWaitable"), old_waitable or 0)

    fakes = {s: logged_fake(s[1:].split("@", 1)[0], "") for s in RECOVER_CALLEES}
    fakes["?R_CreateForInitOrReset@@YA_NH@Z"] = logged_fake("R_CreateForInitOrReset", "i", 1)
    _, _, written, observed = env.call("?R_RecoverLostDevice@@YA_NXZ", [], "char", setup=setup, fakes=fakes)
    order = [o[1] if o[0] == "call" else (o[2] if o[0] == "com" else o[0]) for o in observed]
    if old_waitable is not None:
        return descs, order, written, observed
    return descs, order


def test_lost_device_clears_context_before_new_swap_chain(env):
    descs, order = _recover(env)
    assert descs == [(2, 1, 4, 0x842)], descs
    release = order.index("R_ReleaseForShutdownOrReset")
    clear, flush, create = order.index(CLEAR_STATE), order.index(FLUSH), order.index("create swap chain")
    assert release < clear < flush < create, order


def test_lost_device_without_flip_uses_original_swap_chain(env):
    descs, order = _recover(env, flip=False, tearing=False)
    assert descs == [(2, 1, 0, 0x2)], descs
