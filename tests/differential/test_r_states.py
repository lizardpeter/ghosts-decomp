"""Differential cases for the Store build's pipeline states, shaders, input layouts and queries:
gfx_d3d/r_state.cpp (`states` block), gfx_d3d/r_shader.cpp and gfx_d3d/rb_query.cpp.

The device, the immediate context, queries and the APEX object are COM model objects (com.py). Every description a
create method receives is logged field by field (struct padding left out: it is uninitialized stack in both
builds), with where its out pointer points (a global's address, a buffer's, or "stack"); results vary per input:
failing HRESULTs, NULL objects, S_FALSE runs from GetData. Out objects are written through the harness's journaled
writes, so a create into a global (dx.samplerStates, dx.fencePool, ...) is compared like any global write. Win32
imports the code reaches (thread priority, SetDllDirectoryA, the immediate context mutex, Sleep) are logged with
their arguments and given results. State bits, dvars and the DxGlobals tables are random per input.
"""
import random
import struct

from com import OBJ_SIZE, OBJECTS, ComModel
from harness import STACK, STACK_SIZE
from syms import va
from unicorn.x86_const import (UC_X86_REG_R8, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP,
                               UC_X86_REG_XMM2, UC_X86_REG_XMM3)

STORE = "iw6mp64_MSStore_ship"
DEV, CTX, QUERY, STATE, SHADER, LAYOUT, UNK = ("ID3D11Device", "ID3D11DeviceContext", "ID3D11Query", "ID3D11State",
                                              "ID3D11Shader", "ID3D11InputLayout", "IUnknown")
E_INVALIDARG = 0x80070057
DEVICE_REMOVED = 0x887A0005
M = {}  # the machine of the current call


# ---- helpers --------------------------------------------------------------------------------------------------

def _rec(*entry):
    M["m"].observed.append(entry)


def _where(a):
    """Where a pointer points, comparable across the two builds: stack frames differ, everything else doesn't."""
    if a == 0:
        return 0
    if STACK <= a < STACK + STACK_SIZE:
        return "stack"
    return a


def _u32s(mu, a, n):
    return struct.unpack(f"<{n}I", bytes(mu.mem_read(a, 4 * n)))


def _put_ptr(a, value):
    if a:
        M["m"]._emulated_write(a, struct.pack("<Q", value))


def _dvar(w, current: bytes):
    """A scratch dvar_t with `current` (up to 8 bytes) at +0x10."""
    return w.alloc(bytes(0x10) + current.ljust(8, b"\0") + bytes(0x48))


def _dvar_int(w, v):
    return _dvar(w, struct.pack("<i", v))


def _dvar_float_bits(w, bits):
    return _dvar(w, struct.pack("<I", bits & 0xFFFFFFFF))


def _float_bits(r):
    """A float's bits: ordinary values most of the time, now and then zeroes, infinities and NaNs."""
    k = r.random()
    if k < 0.1:
        return r.choice((0, 0x80000000, 0x7F800000, 0xFF800000, 0x7FC00001, 0xFFC12345, 0x00000001))
    return struct.unpack("<I", struct.pack("<f", r.uniform(-8, 8)))[0]


def _creator(r, kind, out_index, log_desc=None, fail=0.2, null_on_fail=True):
    """A create method: logs the description, then creates an object of `kind` or fails. A failing D3D11 create
    sets the out pointer to NULL; with null_on_fail=False it leaves it alone, so a caller that uses the out value
    without checking the HRESULT shows."""
    def fn(call):
        if log_desc:
            _rec("desc", *log_desc(call))
        out = call.arg(out_index)
        _rec("out", _where(out))
        if r.random() < fail:
            if null_on_fail:
                _put_ptr(out, 0)
            return r.choice((E_INVALIDARG, DEVICE_REMOVED, 0x80004005))
        obj = call.model.new(kind, call.mu)
        _put_ptr(out, obj)
        return r.choice((0, 0, 0, 1))  # S_OK, now and then S_FALSE
    return fn


def _import_logger(name, nargs, result=None):
    """Log an import's first integer arguments (handle in rcx, then a 32-bit value in rdx) and give it a result."""
    def fn(mu):
        args = (mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF)[:nargs]
        _rec(name, *args)
        if result is not None:
            mu.reg_write(UC_X86_REG_RAX, result() & 0xFFFFFFFFFFFFFFFF)
    return fn


def _thread_priority_imports(w, r):
    prio = r.choice((-15, -2, -1, 0, 1, 2, 15))
    m = w.m
    m.on_import("kernel32.dll!GetCurrentThread", _import_logger("GetCurrentThread", 0, lambda: 0xFFFFFFFFFFFFFFFE))
    m.on_import("kernel32.dll!GetThreadPriority", _import_logger("GetThreadPriority", 1, lambda: prio))
    m.on_import("kernel32.dll!SetThreadPriority", _import_logger("SetThreadPriority", 2, lambda: 1))


def _lock_imports(w, r):
    m = w.m
    tid = r.getrandbits(32)
    m.on_import("kernel32.dll!WaitForSingleObject", _import_logger("WaitForSingleObject", 2, lambda: 0))
    m.on_import("kernel32.dll!GetCurrentThreadId", _import_logger("GetCurrentThreadId", 0, lambda: tid))
    m.on_import("kernel32.dll!ReleaseMutex", _import_logger("ReleaseMutex", 1, lambda: 1))
    m.on_import("kernel32.dll!Sleep", _import_logger("Sleep", 1))


def _install(w, sigs, results):
    M["m"] = w.m
    model = ComModel(sigs, results)
    model.install(w.m)
    return model


def _dx(offset):
    return va("dx") + offset


def _recorder(name):
    def fn(mu):
        _rec(name)
        return None
    return fn


# ---- descriptions -------------------------------------------------------------------------------------------------

def _blend_desc(call):
    mu, a = call.mu, call.arg(0)
    head = _u32s(mu, a, 2)
    rts = []
    for i in range(8):
        rt = a + 8 + 32 * i
        rts.append((*_u32s(mu, rt, 7), bytes(mu.mem_read(rt + 0x1C, 1))[0]))
    return head, tuple(rts)


def _dss_desc(call):
    mu, a = call.mu, call.arg(0)
    return _u32s(mu, a, 4), bytes(mu.mem_read(a + 0x10, 2)), _u32s(mu, a + 0x14, 8)


def _raster_desc(call):
    return _u32s(call.mu, call.arg(0), 10)


def _sampler_desc(call):
    return _u32s(call.mu, call.arg(0), 13)


def _query_desc(call):
    return _u32s(call.mu, call.arg(0), 2)


def _shader_args(call):
    # bytecode pointer (raw: never dereferenced), length, class linkage
    return call.arg(0), call.arg(1), call.arg(2)


def _layout_desc(call):
    mu, a, n = call.mu, call.arg(0), call.arg(1)
    elems = []
    for i in range(min(n, 64)):
        e = a + 32 * i
        name = struct.unpack("<Q", bytes(mu.mem_read(e, 8)))[0]
        elems.append((M["m"].read_cstr(name) if name else None, *_u32s(mu, e + 8, 6)))
    return n, tuple(elems), call.arg(2), call.arg(3)


DEV_SIGS = {(DEV, 11 * 8): "pipqp", (DEV, 12 * 8): "pqpp", (DEV, 15 * 8): "pqpp", (DEV, 16 * 8): "pqpp",
            (DEV, 17 * 8): "pqpp", (DEV, 18 * 8): "pqpp", (DEV, 20 * 8): "pp", (DEV, 21 * 8): "pp",
            (DEV, 22 * 8): "pp", (DEV, 23 * 8): "pp", (DEV, 24 * 8): "pp",
            (CTX, 27 * 8): "p", (CTX, 28 * 8): "p", (CTX, 29 * 8): "ppii", (QUERY, 7 * 8): "", (STATE, 2 * 8): "",
            (UNK, 26 * 8): "pi"}


def _device(w, results):
    model = _install(w, DEV_SIGS, results)
    w.u64(_dx(0x08), model.new(DEV))
    return model


# ---- r_state.cpp: blend -----------------------------------------------------------------------------------------

def _blend_bits(r):
    v = r.getrandbits(32)
    if r.random() < 0.4:
        v &= ~0x700
    if r.random() < 0.4:
        v &= ~0x700000
    if r.random() < 0.15:
        v = r.choice((0, 0x0F000000, 0x00000100, 0x07000000 | 0x21))
    return v


def _rt_desc_inputs(seed, n=300):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        out.append({"args": [_blend_bits(r), bytes(r.getrandbits(8) for _ in range(32)), r.choice((0, 1))]})
    return out


def _create_blend_input(r, seed):
    count = r.choice((0, 1, 1, 2, 3, 4, 5, 6, 7, 8))
    base = _blend_bits(r)
    bits = [base if r.random() < 0.5 else _blend_bits(r) for _ in range(8)]

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 20 * 8): _creator(rr, STATE, 1, _blend_desc)})
    return {"args": [b"".join(struct.pack("<I", b) for b in bits), count], "setup": setup}


def _blend_table_input(r, seed):
    count = r.choice((0, 1, 2, 3, 5))
    bits = [_blend_bits(r) for _ in range(count)]
    zone = r.getrandbits(32) if r.random() < 0.3 else r.randrange(0, 81)
    table = bytes(r.getrandbits(8) for _ in range(8 * max(count, 1)))

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 20 * 8): _creator(rr, STATE, 1, _blend_desc)})
    return {"args": [zone, table, b"".join(struct.pack("<I", b) for b in bits) or bytes(4), count], "setup": setup}


# ---- r_state.cpp: depth-stencil ---------------------------------------------------------------------------------

def _dss_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 21 * 8): _creator(rr, STATE, 1, _dss_desc)})
    return {"args": [r.getrandbits(64)], "setup": setup}


def _dss_table_input(r, seed):
    count = r.choice((0, 1, 2, 4))
    bits = [r.getrandbits(64) for _ in range(count)]
    zone = r.getrandbits(32) if r.random() < 0.3 else r.randrange(0, 81)
    table = bytes(r.getrandbits(8) for _ in range(8 * max(count, 1)))

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 21 * 8): _creator(rr, STATE, 1, _dss_desc)})
    return {"args": [zone, table, b"".join(struct.pack("<Q", b) for b in bits) or bytes(8), count], "setup": setup}


# ---- r_state.cpp: rasterizer --------------------------------------------------------------------------------------

POLYGON_DVARS = ("r_polygonOffsetBias", "r_polygonOffsetScale", "r_polygonOffsetClamp", "sm_polygonOffsetBias",
                 "sm_polygonOffsetScale", "sm_polygonOffsetClamp")


def _raster_input(r, seed):
    ints = {name: r.randrange(-100000, 100000) for name in ("r_polygonOffsetBias", "sm_polygonOffsetBias")}
    floats = {name: _float_bits(r) for name in ("r_polygonOffsetScale", "r_polygonOffsetClamp",
                                                "sm_polygonOffsetScale", "sm_polygonOffsetClamp")}
    old = [r.getrandbits(64) for _ in range(32)]

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 22 * 8): _creator(rr, STATE, 1, _raster_desc)})
        for name, v in ints.items():
            w.u64(va(name), _dvar_int(w, v))
        for name, v in floats.items():
            w.u64(va(name), _dvar_float_bits(w, v))
        for i, v in enumerate(old):
            w.u64(_dx(0x2660 + 8 * i), v)
    return {"args": [], "setup": setup}


# ---- r_state.cpp: samplers ----------------------------------------------------------------------------------------

def _sampler_bits(r):
    v = r.getrandbits(32)
    k = r.random()
    if k < 0.2:
        v = (v & ~0xF00) | 0x400
    elif k < 0.4:
        v = (v & ~0xF00) | 0x100
    if r.random() < 0.3:
        v = (v & ~0xF0000) | 0x10000
    if r.random() < 0.3:
        v = (v & ~0xF000) | 0x1000
    if r.random() < 0.2:
        v &= ~0xFF
    return v


def _sampler_desc_input(r, seed):
    bias = _float_bits(r)

    def setup(w):
        _install(w, {}, {})
        w.u32(_dx(0x7D2C), bias)
    return {"args": [bytes(r.getrandbits(8) for _ in range(0x34)), _sampler_bits(r)], "setup": setup}


def _samplers_input(r, seed):
    bias = _float_bits(r)
    table = [_sampler_bits(r) for _ in range(32)]
    existing = [r.random() < 0.5 for _ in range(256)]

    def setup(w):
        rr = random.Random(seed)
        model = _device(w, {(DEV, 23 * 8): _creator(rr, STATE, 1, _sampler_desc, fail=0.05)})
        w.u32(_dx(0x7D2C), bias)
        for i, v in enumerate(table):
            w.u32(va("unk_14B2DA0F0") + 4 * i, v)
        for i, e in enumerate(existing):
            w.u64(_dx(0x3368 + 8 * i), model.new(STATE) if e else 0)
    return {"args": [], "setup": setup}


def _apex_input(r, seed):
    has_state = r.random() < 0.4

    def setup(w):
        rr = random.Random(seed)
        model = _device(w, {(DEV, 23 * 8): _creator(rr, STATE, 1, _sampler_desc)})
        w.u64(va("unk_1430D5C48"), model.new(UNK))
        w.u64(va("unk_1430D5C28"), model.new(STATE) if has_state else 0)

        def set_dll_directory(mu):
            a = mu.reg_read(UC_X86_REG_RCX)
            _rec("SetDllDirectoryA", M["m"].read_cstr(a) if a else None)
            mu.reg_write(UC_X86_REG_RAX, 1)
        w.m.on_import("kernel32.dll!SetDllDirectoryA", set_dll_directory)
    return {"args": [], "setup": setup}


# ---- r_shader.cpp -------------------------------------------------------------------------------------------------

SHADER_SLOTS = {"compute": 18, "domain": 17, "hull": 16, "pixel": 15, "vertex": 12}


def _shader_struct(r, program, renderer):
    size = r.choice((0, 4, 0x1234, r.getrandbits(32)))
    return struct.pack("<QQQIHH", r.getrandbits(64), r.getrandbits(64), program, size, renderer, r.getrandbits(16))


def _shader_input(r, seed, kind, reload):
    in_use = r.choice((0, 1, 2, 0x10001, -0x7FFF))  # -0x7FFF: equal to loadForRenderer 0x8001 only if sign-extended
    renderer = in_use & 0xFFFF if r.random() < 0.6 else r.getrandbits(16)
    data_ptr = 0 if r.random() < 0.2 else 0x7000000 + r.getrandbits(20)
    program = 0 if r.random() < 0.2 else 0x8000000 + r.getrandbits(20)
    shader = _shader_struct(r, program, renderer)
    load_for_renderer = r.choice((0, 1, 1, 1))

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, SHADER_SLOTS[kind] * 8): _creator(rr, SHADER, 3, _shader_args)})
        w.u64(va("r_loadForRenderer"), _dvar(w, bytes([load_for_renderer])))
        w.u64(va("r_rendererInUse"), _dvar_int(w, in_use))
        _thread_priority_imports(w, rr)
    if reload:
        # Material_Reload*(XAssetHeader, void *): the header is the shader, passed in rcx
        return {"args": [shader, r.getrandbits(64)], "setup": setup}
    return {"args": [struct.pack("<Q", data_ptr), shader], "setup": setup}


def _source_table(r):
    entries = []
    for _ in range(23):
        stream = 0xFF if r.random() < 0.1 else r.randrange(0, 4)
        entries.append(struct.pack("<BBBBI", stream, r.getrandbits(8), r.getrandbits(8), r.getrandbits(8),
                                   r.getrandbits(32)))
    return struct.pack("<I", r.getrandbits(32)) + b"".join(entries)


def _routing(r, n):
    return b"".join(bytes([r.randrange(0, 23), r.randrange(0, 32), r.getrandbits(8)]) for _ in range(n))


def _vertex_shader(r):
    return struct.pack("<QQQIHH", 0, 0, 0x9000000 + r.getrandbits(20), r.getrandbits(32), 0, 0)


def _build_decl_input(r, seed):
    count = r.choice((0, 1, 2, 3, 5, 8, 16, 31))

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 11 * 8): _creator(rr, LAYOUT, 4, _layout_desc)})
    return {"args": [_routing(r, count) or bytes(3), count, _source_table(r), _vertex_shader(r)], "setup": setup}


def _build_decls_input(r, seed):
    count = r.choice((0, 1, 2, 3, 4))
    routing = _routing(r, 31) + bytes(r.getrandbits(8) for _ in range(0x828 - 93))
    load_for_renderer = r.choice((0, 1, 1, 1))

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 11 * 8): _creator(rr, LAYOUT, 4, _layout_desc)})
        w.u64(va("r_loadForRenderer"), _dvar(w, bytes([load_for_renderer])))
    return {"args": [routing, count, _vertex_shader(r)], "setup": setup}


# ---- rb_query.cpp -------------------------------------------------------------------------------------------------

def _get_data_results(r):
    """GetData: S_FALSE a few times, then S_OK or an error."""
    left = [r.choice((0, 0, 1, 2, 5))]

    def fn(call):
        if call.arg(1):
            M["m"]._emulated_write(call.arg(1), struct.pack("<I", r.getrandbits(32)))
        if left[0] > 0:
            left[0] -= 1
            return 1
        return r.choice((0, 0, DEVICE_REMOVED))
    return fn


def _occlusion_create_input(r, seed):
    array = bytes(r.getrandbits(8) for _ in range(32 * 0x58))

    def setup(w):
        rr = random.Random(seed)
        _device(w, {(DEV, 24 * 8): _creator(rr, QUERY, 1, _query_desc, null_on_fail=False)})
        w.write(va("occlusionQueryArray"), array)
    return {"args": [], "setup": setup}


def _swap_fence_input(r, seed):
    flag = r.choice((0, 1, 1))  # a bool

    def setup(w):
        rr = random.Random(seed)
        model = _install(w, DEV_SIGS, {(CTX, 29 * 8): _get_data_results(rr)})
        w.u64(_dx(0x10), model.new(CTX))
        w.u64(_dx(0x7CF8), model.new(QUERY))
        w.write(_dx(0x7D00), bytes([flag]))
    return {"args": [], "setup": setup}


def _lock_state(w, r):
    w.u64(_dx(0x3B68), r.getrandbits(64))         # immediateContextMutex
    w.u32(_dx(0x18), r.choice((0, 0, 1, 2)))      # immediateContextLockCount
    w.u32(_dx(0x1C), r.getrandbits(32))           # immediateContextThreadId


def _insert_fence_input(r, seed):
    next_fence = r.randrange(0, 32)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w, DEV_SIGS, {(CTX, 29 * 8): _get_data_results(rr)})
        w.u64(_dx(0x10), model.new(CTX))
        for i in range(32):
            w.u64(_dx(0x7B98 + 8 * i), model.new(QUERY))
        w.u32(_dx(0x7C98), next_fence)
        _lock_state(w, rr)
        _lock_imports(w, rr)
    return {"args": [bytes(8)], "setup": setup}


def _wait_query_input(r, seed):
    flag = r.choice((0, 1, 1, 1, -1))
    has_query = r.random() < 0.85

    def setup(w):
        rr = random.Random(seed)
        model = _install(w, DEV_SIGS, {(CTX, 29 * 8): _get_data_results(rr)})
        w.u64(_dx(0x10), model.new(CTX))
        w.u32(va("unk_14A346A00"), flag)
        w.u64(va("unk_14A346A08"), model.new(QUERY) if has_query else 0)
        _lock_state(w, rr)
        _lock_imports(w, rr)
    return {"args": [], "setup": setup}


INIT_CALLEES = ("?R_BuildSubDomainRangeConstantBuffers@@YAXXZ", "?sub_1401B6130@@YAXXZ", "?sub_140640510@@YAXXZ",
                "?sub_1406310F0@@YAXXZ", "?sub_1406508E0@@YAXXZ", "?sub_14068C300@@YAXXZ",
                "?R_InitRenderBuffers@@YAXXZ", "?sub_14063EBD0@@YAXXZ", "?sub_1401B1400@@YAXXZ",
                "?R_CreateDynamicBuffers@@YAXXZ", "?R_SetupPrecompiledConstantBuffer@@YAXXZ", "?R_InitDefaultDepthImage@@YAXXZ",
                "?R_InitDaltonize@@YAXXZ", "?sub_14068EAE0@@YAXXZ", "?R_CreateParticleCloudBuffer@@YAXXZ", "?sub_14068BC80@@YAXXZ",
                "?sub_14068D600@@YAXXZ", "?sub_1401AAEF0@@YAXXZ", "?sub_1401AB1C0@@YAXXZ")
CREATE_BUFFER = ("?R_CreateBufferInternal@@YAJPEBUD3D11_BUFFER_DESC@@PEBUD3D11_SUBRESOURCE_DATA@@"
                 "PEAPEAUID3D11Buffer@@@Z")


def _create_buffer(mu):
    desc, init, out = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    rr = M["init_rand"]
    _rec("R_CreateBufferInternal", _u32s(mu, desc, 6), init, _where(out))
    _put_ptr(out, rr.choice((0, 0x5000000 + rr.getrandbits(16))))
    return rr.choice((0, E_INVALIDARG))


def _init_input(r, seed):
    minimal = r.choice((0, 0, 1))
    is_reset = r.choice((0, 0, 1, 2, 0x80000000, 0x100000000))
    fail = r.choice((0.0, 0.0, 0.01, 0.05, 0.3))

    def setup(w):
        rr = random.Random(seed)
        M["init_rand"] = rr
        event = _creator(rr, QUERY, 1, _query_desc, fail=fail, null_on_fail=False)
        occlusion = _creator(rr, QUERY, 1, _query_desc, fail=0.5, null_on_fail=False)
        _device(w, {(DEV, 24 * 8): lambda call: (occlusion if _query_desc(call)[0] == 1 else event)(call)})
        w.write(va("g_allocateMinimalResources"), bytes([minimal]))
        # uninitialized locals read 0xCC in both builds (a failed CreateQuery leaves its out pointer alone)
        w.m.mu.mem_write(STACK + STACK_SIZE - 0x4100, b"\xcc" * 0x4000)
        w.write(_dx(0x7D00), bytes([1]))
    return {"args": [is_reset], "setup": setup}


# ---- rb_query.cpp: occlusion query update -------------------------------------------------------------------------

def _query_data_results(r, budget):
    """GetData for occlusion queries: S_FALSE runs (bounded), errors, sample counts (small, large, -2, -3)."""
    left = [budget]

    def fn(call):
        if left[0] > 0 and r.random() < 0.35:
            left[0] -= 1
            return 1
        value = r.choice((0, 1, 7, 100, 255, 256, 257, 2048, r.getrandbits(64), 0xFFFFFFFFFFFFFFFD,
                          0xFFFFFFFFFFFFFFFE if left[0] > 0 else 3))
        if value == 0xFFFFFFFFFFFFFFFE:
            left[0] -= 1
        if call.arg(1):
            M["m"]._emulated_write(call.arg(1), struct.pack("<Q", value))
        return r.choice((0, 0, 0, 0, DEVICE_REMOVED))
    return fn


def _occlusion_entry(r, model, local_client):
    pos = struct.pack("<3I", *(_float_bits(r) for _ in range(3)))
    queries = [model.new(QUERY) if r.random() < 0.85 else 0 for _ in range(4)]
    prev = r.choice((0, 5, 300, r.getrandbits(64), 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFE))
    return (bytes([r.random() < 0.8, r.random() < 0.3, r.random() < 0.5, r.random() < 0.8]) + pos +
            struct.pack("<II", _float_bits(r), _float_bits(r)) +
            struct.pack("<ii", local_client if r.random() < 0.8 else local_client + 1, r.getrandbits(31)) +
            bytes([q != 0 and r.random() < 0.6 for q in queries]) + bytes(4) +  # an issued query exists
            struct.pack("<4Q", *queries) +
            struct.pack("<iI", r.choice((0, 0, 1, 2, 3, 4)), 0) + struct.pack("<Q", prev))


def _occlusion_update_input(r, seed):
    local_client = r.randrange(0, 2)
    msaa = r.choice((0, 1))
    view = bytearray(r.getrandbits(8) for _ in range(0x18B8))
    view[0x1820:0x1824] = struct.pack("<i", local_client)
    view[0x18B4] = msaa
    # a negative frame counter (after 2^31 frames) makes the index negative and the original loop forever
    frame = r.getrandbits(31)
    samples = r.choice((0, 1, 2, 4, 8))
    flush = r.choice((0, 1))

    def setup(w):
        rr = random.Random(seed)
        model = _install(w, DEV_SIGS, {(CTX, 29 * 8): _query_data_results(rr, 40)})
        w.u64(_dx(0x10), model.new(CTX))
        w.write(va("occlusionQueryArray"), b"".join(_occlusion_entry(rr, model, local_client) for _ in range(32)))
        w.u32(va("unk_14A37D598"), frame)
        w.u32(_dx(0x7C9C), samples)
        w.u64(va("unk_14A34B488"), rr.getrandbits(64))
        w.u32(va("unk_14BACB0CC"), flush)
        w.m.on_import("kernel32.dll!Sleep", _import_logger("Sleep", 1))
    return {"args": [bytes(view)], "setup": setup}


def _query_result_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w, DEV_SIGS, {(CTX, 29 * 8): _query_data_results(rr, 3)})
        w.u64(_dx(0x10), model.new(CTX))
        M["query"] = model.new(QUERY)
    return {"args": [OBJECTS + OBJ_SIZE], "setup": setup}  # the second model object: the query


def _sprite_fake(mu):
    """sub_14068CAC0(position, isWorldPos, width, height, color, depthBias): log everything, the stack args too."""
    rsp = mu.reg_read(UC_X86_REG_RSP)
    color, bias = struct.unpack("<II", bytes(mu.mem_read(rsp + 0x28, 4)) + bytes(mu.mem_read(rsp + 0x30, 4)))
    _rec("sub_14068CAC0", mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX) & 0xFF,
         mu.reg_read(UC_X86_REG_XMM2) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_XMM3) & 0xFFFFFFFF, color, bias)


def _warn_fake(mu):
    _rec("R_WarnOncePerFrame", mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_RDX),
         mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF)


OCCLUSION_FAKES = {
    "?sub_140675180@@YAXXZ": _recorder("sub_140675180"),
    "?sub_14068D350@@YAXXZ": _recorder("sub_14068D350"),
    "?sub_14068CE80@@YAXPEAUOcclusionQuery@@@Z": lambda mu: _rec("sub_14068CE80", mu.reg_read(UC_X86_REG_RCX)),
    "?sub_14068D370@@YAXPEAXHH@Z": lambda mu: _rec("sub_14068D370", mu.reg_read(UC_X86_REG_RCX),
                                                   mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF,
                                                   mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF),
    "?sub_14068CAC0@@YAXPEBM_NMMIM@Z": _sprite_fake,
    "?sub_14068D360@@YAXPEAX@Z": lambda mu: _rec("sub_14068D360", mu.reg_read(UC_X86_REG_RCX)),
    "?R_WarnOncePerFrame@@YAXW4GfxWarningType@@ZZ": _warn_fake,
}


# ---- cases --------------------------------------------------------------------------------------------------------

def _inputs(fn, seed, n):
    r = random.Random(seed)
    return [fn(r, seed * 1000 + i) for i in range(n)]


def _case(symbol, ret, inputs, **extra):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs, **extra}


SHADER_SYMBOLS = {
    ("compute", False): "?Load_CreateComputeShader@@YAXPEAPEAEPEAUComputeShader@@@Z",
    ("domain", False): "?Load_CreateMaterialDomainShader@@YAXPEAPEAEPEAUMaterialDomainShader@@@Z",
    ("hull", False): "?Load_CreateMaterialHullShader@@YAXPEAPEAEPEAUMaterialHullShader@@@Z",
    ("pixel", False): "?Load_CreateMaterialPixelShader@@YAXPEAPEAEPEAUMaterialPixelShader@@@Z",
    ("vertex", False): "?Load_CreateMaterialVertexShader@@YAXPEAPEAEPEAUMaterialVertexShader@@@Z",
    ("compute", True): "?Material_ReloadComputeShader@@YAXTXAssetHeader@@PEAX@Z",
    ("domain", True): "?Material_ReloadDomainShader@@YAXTXAssetHeader@@PEAX@Z",
    ("hull", True): "?Material_ReloadHullShader@@YAXTXAssetHeader@@PEAX@Z",
    ("pixel", True): "?Material_ReloadPixelShader@@YAXTXAssetHeader@@PEAX@Z",
    ("vertex", True): "?Material_ReloadVertexShader@@YAXTXAssetHeader@@PEAX@Z",
}

CRITSECT_OBSERVE = {"?Sys_EnterCriticalSection@@YAXW4CriticalSection@@@Z": "i",
                    "?Sys_LeaveCriticalSection@@YAXW4CriticalSection@@@Z": "i"}


CASES = [
    _case("?sub_1406321C0@@YAXIPEAUD3D11_RENDER_TARGET_BLEND_DESC@@_N@Z", "void", _rt_desc_inputs(0x21C0)),
    _case("?sub_140630A70@@YAPEAUID3D11BlendState@@PEBII@Z", "int64", _inputs(_create_blend_input, 0xA70, 200)),
    _case("?sub_140631250@@YAXEPEATGfxZoneTableEntry@@PEBII@Z", "void", _inputs(_blend_table_input, 0x1250, 100)),
    _case("?sub_14065BED0@@YAPEAUID3D11DepthStencilState@@_K@Z", "int64", _inputs(_dss_input, 0xBED0, 200)),
    _case("?sub_1406314C0@@YAXEPEATGfxZoneTableEntry@@PEB_KI@Z", "void", _inputs(_dss_table_input, 0x14C0, 100)),
    _case("?sub_1406310F0@@YAXXZ", "void", _inputs(_raster_input, 0x10F0, 40)),
    _case("?sub_140662850@@YAXPEAUD3D11_SAMPLER_DESC@@I@Z", "void", _inputs(_sampler_desc_input, 0x2850, 300)),
    _case("?sub_14065FE60@@YAXXZ", "void", _inputs(_samplers_input, 0xFE60, 25)),
    _case("?sub_1401AAB70@@YAXXZ", "void", _inputs(_apex_input, 0xAB70, 40)),
    *[_case(sym, "void", _inputs(lambda r, s, k=kind, rl=reload: _shader_input(r, s, k, rl),
                                 0x3A00 + 16 * list(SHADER_SLOTS).index(kind) + reload, 120),
            observe={"?Sys_TempPriorityAtLeastNormalBegin@@YAXPEAUTempPriority@@@Z": "",
                     "?Sys_TempPriorityEnd@@YAXPEAUTempPriority@@@Z": ""})
      for (kind, reload), sym in SHADER_SYMBOLS.items()],
    _case("?Material_BuildVertexDecl@@YAPEAUID3D11InputLayout@@PEBUMaterialStreamRouting@@IPEBUGfxVertexDeclSources@@"
          "PEBUMaterialVertexShader@@@Z", "int64", _inputs(_build_decl_input, 0x5180, 200)),
    _case("?sub_1406650E0@@YAXPEAUMaterialVertexStreamRouting@@IPEBUMaterialVertexShader@@@Z", "void",
          _inputs(_build_decls_input, 0x50E0, 30),
          observe={"?Material_BuildVertexDecl@@YAPEAUID3D11InputLayout@@PEBUMaterialStreamRouting@@IPEBU"
                   "GfxVertexDeclSources@@PEBUMaterialVertexShader@@@Z": "qiqq"}),
    _case("?sub_14068BC80@@YAXXZ", "void", _inputs(_occlusion_create_input, 0xBC80, 25), observe=CRITSECT_OBSERVE),
    _case("?R_FinishGpuFence@@YAXXZ", "void", _inputs(_swap_fence_input, 0xBE70, 60)),
    # the Store build inlines the lock here (its imports are logged)
    _case("?sub_14067D210@@YAXPEAPEAUID3D11Query@@@Z", "void", _inputs(_insert_fence_input, 0xD210, 60)),
    _case("?sub_14062DFF0@@YAHXZ", "int", _inputs(_wait_query_input, 0xDFF0, 60),
          fakes={"?Sys_CheckQuitRequest@@YAXXZ": _recorder("Sys_CheckQuitRequest")},
          observe={"?R_LockImmediateContextWithPumpOnMain@@YAXXZ": ""}),
    _case("?R_CreateForInitOrReset@@YA_NH@Z", "char", _inputs(_init_input, 0xF700, 80),
          fakes={**{s: _recorder(s) for s in INIT_CALLEES}, CREATE_BUFFER: _create_buffer}),
    _case("?sub_14068C260@@YA_KPEAUID3D11Query@@@Z", "int64", _inputs(_query_result_input, 0xC260, 80)),
    _case("?sub_14068BE20@@YAXPEAUOcclusionViewData@@@Z", "void", _inputs(_occlusion_update_input, 0xBE20, 80),
          fakes=OCCLUSION_FAKES),
]
