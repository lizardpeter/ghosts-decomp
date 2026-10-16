"""Differential cases for gfx_d3d/r_buffers.cpp (and r_init.cpp's constant buffer handles) against the Store build.

The device, the immediate context and every buffer are COM model objects (com.py). A plan drawn per input decides
what each method returns, in call order: CreateBuffer succeeds (a new buffer, its ByteWidth remembered for GetDesc)
or fails with E_OUTOFMEMORY, E_INVALIDARG or DXGI_ERROR_DEVICE_REMOVED (writing NULL, as D3D11 does), Map succeeds
(a zeroed block of the buffer's size) or fails, Release and AddRef return varying counts. Descriptions are compared
by content; the bytes of a mapped buffer are compared when it is unmapped. r_loadForRenderer is on or off.

Engine callees are faked and their arguments recorded (Sys_OutOfMemErrorInternal, R_ErrorDescription, va, the
fatal errors, the r_compute.cpp buffer and view creators, the reactive motion pools); the video memory accounting
functions (sub_1401AFFE0 and co.) run for real on the model's GetDesc, so their total (14A385390) is compared too.
"""
import math
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

from com import ComModel
from syms import va

STORE = "iw6mp64_MSStore_ship"
DEV, CTX, RES, VIEW = "ID3D11Device", "ID3D11DeviceContext", "ID3D11Resource", "ID3D11View"
CREATE_BUFFER, MAP, UNMAP, ADDREF, RELEASE, GETDESC = 3 * 8, 14 * 8, 15 * 8, 1 * 8, 2 * 8, 10 * 8
SIGS = {(DEV, CREATE_BUFFER): "ppp", (CTX, MAP): "piiip", (CTX, UNMAP): "pi", (RES, ADDREF): "", (RES, RELEASE): "",
        (RES, GETDESC): "p", (VIEW, RELEASE): ""}
E_OUTOFMEMORY, E_INVALIDARG, DEVICE_REMOVED = 0x8007000E, 0x80070057, 0x887A0005
DX = 0x14A37D620
DX_DEVICE, DX_CONTEXT, DX_LOCKCOUNT, DX_THREADID, DX_MUTEX = 0x08, 0x10, 0x18, 0x1C, 0x3B68
DX_CB_COUNTS, DX_CB_TABLES, DX_CB_DEFAULTS = 0x60, 0x430, 0x2760
DRAWCONSTS_CLOUD = 0x14B89E2E8  # g_drawConsts.particleCloudVertexBuffer .. SparkIndexBuffer (4 pointers)
ERROR_TEXT = 0x5FF000           # R_ErrorDescription's fake result (scratch memory, written by setup)
VA_TEXT = 0x5FF100              # va's fake result

M = {}  # the machine of the current call, for fakes that record


def _rec(*entry):
    M["m"].observed.append(entry)


def _u32(mu, a):
    return struct.unpack("<I", bytes(mu.mem_read(a, 4)))[0]


def _u64(mu, a):
    return struct.unpack("<Q", bytes(mu.mem_read(a, 8)))[0]


def _cstr(a):
    return M["m"].read_cstr(a) if a else None


def _stack(mu, i):
    """Argument i (0-based, i >= 4) of a call, read at the callee's first instruction."""
    return _u64(mu, mu.reg_read(UC_X86_REG_RSP) + 8 + 8 * i)


# --- the COM model with D3D11 buffer behaviour -------------------------------------------------------------------

class Plan:
    """What the model's methods do, drawn per input; each method takes its outcomes in call order."""

    def __init__(self, r, fail=0.25):
        def pick(choices, n=64):
            return [r.choice(choices) for _ in range(n)]
        ok = [0] * 6 + [1]  # S_OK, sometimes S_FALSE
        bad = [E_OUTOFMEMORY, E_INVALIDARG, DEVICE_REMOVED]
        self.lists = {
            "create": [r.choice(bad) if r.random() < fail else r.choice(ok) for _ in range(64)],
            "map": [r.choice([E_INVALIDARG, DEVICE_REMOVED, 0x887A000A]) if r.random() < fail else 0 for _ in range(64)],
            "release": pick([0, 0, 1, 2, 7]),
            "addref": pick([1, 2, 3, 9]),
            "stale": pick([0, 0x7FF012340000, 0xDEAD0000]),
        }
        self.pos = {}

    def next(self, kind):
        i = self.pos.get(kind, 0)
        self.pos[kind] = i + 1
        lst = self.lists[kind]
        return lst[i % len(lst)]


class Gpu:
    def __init__(self, w, plan, desc_bytes=0x14, record_unmap=False):
        self.plan, self.sizes, self.mapped, self.record_unmap = plan, {}, {}, record_unmap
        plan.pos = {}  # the same plan for both runs
        results = {(DEV, CREATE_BUFFER): self.create, (RES, GETDESC): self.getdesc, (RES, RELEASE): self.release,
                   (RES, ADDREF): self.addref, (CTX, MAP): self.map, (CTX, UNMAP): self.unmap,
                   (VIEW, RELEASE): self.release}
        # StructureByteStride is left uninitialised by most callers: compare the description without it
        self.model = ComModel(SIGS, results, {(DEV, CREATE_BUFFER): {0: desc_bytes, 1: 0x10}})
        self.model.install(w.m)
        M["m"] = w.m
        self.device = self.model.new(DEV)
        self.context = self.model.new(CTX)
        w.u64(DX + DX_DEVICE, self.device)
        w.u64(DX + DX_CONTEXT, self.context)

    def buffer(self, size):
        obj = self.model.new(RES)
        self.sizes[obj] = size
        return obj

    def create(self, call):
        hr = self.plan.next("create")
        if hr < 0x80000000:
            obj = call.out_object(2, RES)
            self.sizes[obj] = _u32(call.mu, call.arg(0))
        elif call.arg(2):
            call.write(call.arg(2), bytes(8))
        return hr

    def getdesc(call_self, call):
        size = call_self.sizes.get(call.obj, 0x40)
        call.write(call.arg(0), struct.pack("<6I", size, 2, 1, 0x10000, 0, 0))

    def release(self, call):
        return self.plan.next("release")

    def addref(self, call):
        return self.plan.next("addref")

    def map(self, call):
        hr = self.plan.next("map")
        out = call.args[4]
        if hr:
            # what a failed Map leaves in the description varies: NULL or a stale pointer
            call.write(out, struct.pack("<QII", self.plan.next("stale"), 0, 0))
            return hr
        size = self.sizes.get(call.arg(0), 0x40)
        data = self.model.alloc(bytes(size))
        self.mapped[call.arg(0)] = (data, size)
        call.write(out, struct.pack("<QII", data, size, size))
        return 0

    def unmap(self, call):
        if self.record_unmap and call.arg(0) in self.mapped:
            data, size = self.mapped[call.arg(0)]
            _rec("contents", self.model.objects.get(call.arg(0), (None, call.arg(0)))[1], bytes(call.mu.mem_read(data, size)))


def _dvar(w, name, value):
    """A scratch dvar_t whose current value is `value` (bool or int), installed as `name`."""
    dvar = w.alloc(struct.pack("<QIBB2x", 0, 0, 0, 0) + struct.pack("<I", value & 0xFFFFFFFF) + bytes(0x50))
    w.u64(va(name), dvar)


def _load_for_renderer(w, on):
    _dvar(w, "r_loadForRenderer", 1 if on else 0)


# --- fakes -------------------------------------------------------------------------------------------------------

def _fake_record(name, spec):
    """A fake that records its arguments: spec letters q (64-bit), i (32-bit), s (C string), per argument."""
    regs = (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)

    def fake(mu):
        got = []
        for i, kind in enumerate(spec):
            v = mu.reg_read(regs[i]) if i < 4 else _stack(mu, i)
            got.append(_cstr(v) if kind == "s" else v & (0xFFFFFFFF if kind == "i" else 0xFFFFFFFFFFFFFFFF))
        _rec(name, *got)
        return 0
    return fake


def _fake_error_description(mu):
    _rec("R_ErrorDescription", mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF)
    return ERROR_TEXT


def _fake_va(mu):
    _rec("va", _cstr(mu.reg_read(UC_X86_REG_RCX)), _cstr(mu.reg_read(UC_X86_REG_RDX)))
    mu.mem_write(VA_TEXT, b"formatted\0")
    return VA_TEXT


FAKES = {
    "?Sys_OutOfMemErrorInternal@@YAXH@Z": _fake_record("Sys_OutOfMemErrorInternal", "i"),
    "?R_ErrorDescription@@YAPEBDJ@Z": _fake_error_description,
    "va": _fake_va,
    "?R_FatalInitError@@YAXPEBD@Z": _fake_record("R_FatalInitError", "s"),
    "?R_FatalLockError@@YAXJ@Z": _fake_record("R_FatalLockError", "i"),
    "?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _fake_record("Com_Error", "iss"),
    "?sub_1401AC310@@YAXIIW4D3D11_USAGE@@PEBXPEBDPEAPEAUID3D11Buffer@@@Z": _fake_record("sub_1401AC310", "iiiqsq"),
    "?sub_1401AC380@@YAJPEAUID3D11Buffer@@PEBDPEAPEAUID3D11UnorderedAccessView@@@Z": _fake_record("sub_1401AC380", "qsq"),
    "?sub_1401AC3F0@@YAJPEAUID3D11Buffer@@PEBDPEAPEAUID3D11ShaderResourceView@@@Z": _fake_record("sub_1401AC3F0", "qsq"),
    "?sub_140631780@@YA_NPEAUID3D11Device@@PEAUID3D11Buffer@@@Z": _fake_record("sub_140631780", "qq"),
    "?R_InitReactiveMotionConstantBufferState@@YAXPEAUGfxReactiveMotionBufferState@@@Z":
        _fake_record("R_InitReactiveMotionConstantBufferState", "q"),
    "?sub_1401B1EC0@@YAXPEAUGfxReactiveMotionBufferState@@@Z": _fake_record("sub_1401B1EC0", "q"),
    "?sub_14063DB80@@YAXXZ": _fake_record("sub_14063DB80", ""),
}
# the accounting functions run for real; their arguments are compared too
OBSERVE = {"?sub_1401AFFE0@@YAXPEAUID3D11Buffer@@@Z": "q", "?sub_1401B0000@@YAXPEAUID3D11Buffer@@@Z": "q",
           "?sub_1401B0020@@YAXPEAUID3D11Buffer@@I@Z": "qi"}


def _common(w, r_on, total):
    _load_for_renderer(w, r_on)
    w.write(ERROR_TEXT, b"(error text)\0")
    w.u64(0x14A385390, total)  # the accounting total


def case(symbol, seed, make, n=200, ret="void"):
    rnd = random.Random(seed)
    return {"symbol": symbol, "build": STORE, "ret": ret, "fakes": FAKES, "observe": OBSERVE,
            "inputs": [make(rnd) for _ in range(n)]}


def _size(r):
    return r.choice([0, 1, 16, 0x40, 0x100, 0x1000, 0x7FF0, r.randint(1, 0x10000)])


def _total(r):
    return r.choice([0, 0x10000000, r.getrandbits(40)])


# --- Load_* and the allocators ------------------------------------------------------------------------------------

def _load_buffer(r, data_may_be_null=False):
    plan, on, total = Plan(r), r.random() < 0.8, _total(r)
    data = 0 if data_may_be_null and r.random() < 0.2 else r.choice([0x5F0000, r.getrandbits(47)])
    count = _size(r)

    def setup(w):
        _common(w, on, total)
        Gpu(w, plan)
    return {"args": [struct.pack("<Q", r.getrandbits(64)), data, count], "setup": setup}


def _first_object():
    """The first object a fresh model creates after the device and the context (com.py OBJECTS)."""
    from com import OBJECTS, OBJ_SIZE
    return OBJECTS + 2 * OBJ_SIZE


def _view_input(r, five=False):
    has_buffer, total = r.random() < 0.8, _total(r)
    size = r.choice([0, 0, 4, 0x100, r.getrandbits(32)])
    data = r.choice([0, 0x5F0000, 0x5F0000])

    def setup(w):
        _common(w, True, total)
        g = Gpu(w, Plan(random.Random(1)))
        w.cstr("name")
        g.buffer(0x100)
    args = [struct.pack("<Q", r.getrandbits(64)), _first_object() if has_buffer else 0]
    args += [data, size, 0x500000] if five else [size, 0x500000]
    return {"args": args, "setup": setup}


def _load_raw(r):
    on, total = r.random() < 0.8, _total(r)
    data = r.choice([0, 0x5F0000, r.getrandbits(47)])

    def setup(w):
        _common(w, on, total)
        Gpu(w, Plan(random.Random(2)))
        w.cstr("raw name")
    return {"args": [struct.pack("<Q", r.getrandbits(64)), data, _size(r), 0x500000], "setup": setup}


def _alloc(r, fail=0.25):
    plan, on, total = Plan(r, fail), r.random() < 0.8, _total(r)

    def setup(w):
        _common(w, on, total)
        Gpu(w, plan)
        w.cstr("track name")
    return {"args": [struct.pack("<Q", r.getrandbits(64)), _size(r), 0x500000], "setup": setup}


def _create_internal(r):
    plan, total = Plan(r, 0.4), _total(r)
    desc = struct.pack("<6I", _size(r), r.randint(0, 3), r.getrandbits(8), r.choice([0, 0x10000, 0x20000]),
                       r.choice([0, 0x20, 0x30]), r.choice([0, 4, 16]))
    init = r.choice([0, struct.pack("<QII", r.getrandbits(47), r.getrandbits(16), 0)])

    def setup(w):
        _common(w, True, total)
        g = Gpu(w, plan, desc_bytes=0x18)
    return {"args": [desc, init, struct.pack("<Q", r.getrandbits(64))], "setup": setup}


def _constant_buffer(r):
    plan, total, r_on = Plan(r, 0.3), _total(r), r.random() < 0.8

    def setup(w):
        _common(w, r_on, total)
        Gpu(w, plan, desc_bytes=0x18)
        w.cstr("Subdiv Patch Constants")
    size = r.choice([0, 1, 15, 16, 17, 0xF0, 0x20, r.getrandbits(32)])
    return {"args": [size, 0x500000, struct.pack("<Q", r.getrandbits(64))], "setup": setup}


# --- dynamic buffer states ----------------------------------------------------------------------------------------

def _vb_state(r, objects):
    """A GfxVertexBufferState (0x30 bytes): buffer, raw buffer, view and UAV are model objects or NULL."""
    return struct.pack("<iiQQQQQ", r.getrandbits(31), r.getrandbits(31), objects[0], r.getrandbits(64), *objects[1:])


def _init_vb_state(r):
    plan, on, total = Plan(r), r.random() < 0.8, _total(r)
    compute = r.random() < 0.5
    state = bytes(r.getrandbits(8) for _ in range(0x30))

    def setup(w):
        _common(w, on, total)
        Gpu(w, plan)
    return {"args": [state, r.choice([0, 0x100000, 0x6000, r.getrandbits(31)]), compute], "setup": setup}


def _destroy_vb_state(r):
    present = [r.random() < 0.7 for _ in range(4)]
    total = _total(r)
    plan = Plan(r)
    # objects are created in setup in a fixed order: buffer, raw buffer (resources), view, UAV (views)
    from com import OBJECTS, OBJ_SIZE
    addrs = [OBJECTS + (2 + i) * OBJ_SIZE for i in range(4)]
    objs = [a if p else 0 for a, p in zip(addrs, present)]
    state = _vb_state(r, [objs[0], objs[1], objs[2], objs[3]])
    r_sizes = [_size(r), _size(r)]

    def setup(w):
        _common(w, True, total)
        g = Gpu(w, plan)
        g.buffer(r_sizes[0])
        g.buffer(r_sizes[1])
        g.model.new(VIEW)
        g.model.new(VIEW)
    return {"args": [state], "setup": setup}


GFXBUF = 0x14A107B40
GB_INDEX_POOL, GB_INDEX_PTR, GB_SKINNED, GB_LOCKADDR = 0x8, 0x20, 0x28, 0xB8
GB_VERTEX_POOL, GB_VERTEX_PTR = 0x1BF9C0, 0x1BF9F0


def _gfxbuf_junk(r, w):
    w.write(GFXBUF, bytes(r.getrandbits(8) for _ in range(0xC0)))
    w.write(GFXBUF + GB_VERTEX_POOL, bytes(r.getrandbits(8) for _ in range(0x40)))


def _create_dynamic(r):
    plan, on, total = Plan(r, 0.2), r.random() < 0.8, _total(r)
    skinned = r.choice([0, 1, 0x100, 0x2000, r.getrandbits(32)])
    junk = random.Random(r.getrandbits(32))

    def setup(w):
        _common(w, on, total)
        Gpu(w, plan)
        _dvar(w, "r_SkinnedCacheSize", skinned)
        _gfxbuf_junk(random.Random(junk.getrandbits(32)), w)
    return {"args": [], "setup": setup}


def _destroy_dynamic(r):
    plan, total = Plan(r), _total(r)
    seed = r.getrandbits(32)

    def setup(w):
        rr = random.Random(seed)
        _common(w, True, total)
        g = Gpu(w, plan)
        _gfxbuf_junk(rr, w)

        def obj(kind_view=False):
            if rr.random() < 0.3:
                return 0
            return g.model.new(VIEW) if kind_view else g.buffer(_size(rr))
        w.u64(GFXBUF + GB_INDEX_POOL + 8, obj())
        for base in [GFXBUF + GB_SKINNED + 0x30 * i for i in range(3)] + [GFXBUF + GB_VERTEX_POOL]:
            w.u64(base + 0x08, obj())
            w.u64(base + 0x18, obj())
            w.u64(base + 0x20, obj(True))
            w.u64(base + 0x28, obj(True))
    return {"args": [], "setup": setup}


def _destroy_cloud(r):
    plan, total = Plan(r), _total(r)
    present = [r.random() < 0.75 for _ in range(4)]
    sizes = [_size(r) for _ in range(4)]

    def setup(w):
        _common(w, True, total)
        g = Gpu(w, plan)
        for i in range(4):
            w.u64(DRAWCONSTS_CLOUD + 8 * i, g.buffer(sizes[i]) if present[i] else 0)
    return {"args": [], "setup": setup}


# --- particle cloud -----------------------------------------------------------------------------------------------

def _rand(mu):
    """rand(): the n-th value of a fixed sequence for the n-th rand() of the current call (the same in both runs)."""
    n = sum(name.endswith("!rand") for name in M["m"].imports_called)
    from unicorn.x86_const import UC_X86_REG_RAX
    mu.reg_write(UC_X86_REG_RAX, (n * 2654435761 >> 7) & 0x7FFF)


def _qsort(mu):
    """Records the arguments, and the immediate-context lock while the cloud is built (count, owning thread)."""
    _rec("qsort", mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8),
         mu.reg_read(UC_X86_REG_R9), _u32(mu, DX + DX_LOCKCOUNT), _u32(mu, DX + DX_THREADID))


def _wait(mu):
    _rec("WaitForSingleObject", mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF)


def _thread_id(mu):
    from unicorn.x86_const import UC_X86_REG_RAX
    mu.reg_write(UC_X86_REG_RAX, 0x1A2C)


def _release_mutex(mu):
    _rec("ReleaseMutex", mu.reg_read(UC_X86_REG_RCX))


def _cloud(r):
    plan = Plan(r, 0.03)
    on, total = r.random() < 0.95, _total(r)
    lock = (r.choice([0, 0, 1, 3]), r.getrandbits(32), r.getrandbits(47))
    r_junk = [r.getrandbits(64) for _ in range(4)]

    def setup(w):
        _common(w, on, total)
        Gpu(w, plan, record_unmap=True)
        w.u32(DX + DX_LOCKCOUNT, lock[0])
        w.u32(DX + DX_THREADID, lock[1])
        w.u64(DX + DX_MUTEX, lock[2])
        m = w.m
        m.on_import("api-ms-win-crt-utility-l1-1-0.dll!rand", _rand)
        m.on_import("api-ms-win-crt-utility-l1-1-0.dll!qsort", _qsort)
        m.on_import("kernel32.dll!WaitForSingleObject", _wait)
        m.on_import("kernel32.dll!GetCurrentThreadId", _thread_id)
        m.on_import("kernel32.dll!ReleaseMutex", _release_mutex)
        for i in range(4):
            w.u64(DRAWCONSTS_CLOUD + 8 * i, r_junk[i])
    return {"args": [], "setup": setup}


# --- lock, unlock, release ----------------------------------------------------------------------------------------

def _lock(r):
    plan, total = Plan(r, 0.3), _total(r)
    offset = r.choice([0, 4, 0x100, -16, r.getrandbits(31), -r.getrandbits(31)])
    flags = r.choice([1, 2, 3, 4, 5])
    size = _size(r)

    def setup(w):
        _common(w, True, total)
        g = Gpu(w, plan)
        g.buffer(size)
    return {"args": [_first_object() - 0x40, _first_object(), offset, r.getrandbits(31), flags], "setup": setup}


def _unlock(r):
    def setup(w):
        g = Gpu(w, Plan(random.Random(3)))
        g.buffer(0x100)
    return {"args": [_first_object() - 0x40, r.choice([_first_object(), 0])], "setup": setup}


def _release(r):
    plan, total, size = Plan(r), _total(r), _size(r)

    def setup(w):
        _common(w, True, total)
        g = Gpu(w, plan)
        g.buffer(size)
    return {"args": [_first_object()], "setup": setup}


def _compare(r):
    def vert():
        vals = [r.choice([0.0, -0.0, 1.0, -1.0, 0.5, 1e-20, 3e19, math.inf, -math.inf, math.nan,
                          r.uniform(-2, 2), r.uniform(-2, 2)]) for _ in range(3)]
        return struct.pack("<5f", *vals, r.random(), r.random())
    a = vert()
    b = a if r.random() < 0.15 else vert()
    if r.random() < 0.15:  # same distance, different point
        x, y, z = struct.unpack("<3f", a[:12])
        b = struct.pack("<3f", -x, z, y) + b[12:]
    return [a, b]


# --- constant buffer handles --------------------------------------------------------------------------------------

CB_SIZES = [16, 32, 48, 64, 128, 256, 0x400]


def _cb_tables(r):
    """Constant buffer counts and tables of the three types: zone 0 is the default table (sometimes full, so a new
    handle is out of range), a few other zones have buffers of random sizes."""
    layout = []
    for t in range(3):
        zones = {0: [r.choice(CB_SIZES) for _ in range(r.choice([0, 0, 1, 3, 6, 128]))]}
        for _ in range(r.choice([0, 1, 2, 4])):
            zones[r.randint(1, 79)] = [r.choice(CB_SIZES) for _ in range(r.randint(0, 5))]
        count0 = r.choice([0x7F, 0x80, 0xFF]) if len(zones[0]) == 128 else len(zones[0])
        layout.append((zones, count0))
    return layout


def _cb_setup(layout, plan, total):
    def setup(w):
        _common(w, True, total)
        g = Gpu(w, plan, desc_bytes=0x18)
        for t, (zones, count0) in enumerate(layout):
            for zone, sizes in zones.items():
                objs = [g.buffer(s) for s in sizes]
                table = w.alloc(b"".join(struct.pack("<Q", o) for o in objs) + bytes(8)) if zone else \
                    DX + DX_CB_DEFAULTS + t * 0x400
                if not zone:
                    w.write(table, b"".join(struct.pack("<Q", o) for o in objs))
                w.u32(DX + DX_CB_COUNTS + (t * 81 + zone) * 4, count0 if not zone else len(sizes))
                w.u64(DX + DX_CB_TABLES + (t * 81 + zone) * 8, table)
    return setup


def _cb_handle(r):
    layout = _cb_tables(r)
    t = r.randint(0, 2)
    size = r.choice(CB_SIZES + [0, 0, 80, 0x2000])
    return {"args": [t, size], "setup": _cb_setup(layout, Plan(r, 0.2), _total(r))}


def _cb_perprim(r):
    layout = _cb_tables(r)
    size = r.choice(CB_SIZES + [0, 80, 0x2000])
    return {"args": [size], "setup": _cb_setup(layout, Plan(r, 0.2), _total(r))}


CASES = [
    case("?Load_IndexBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXH@Z", 620, _load_buffer),
    case("?Load_VertexBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXH@Z", 750, lambda r: _load_buffer(r, True)),
    case("?sub_140601970@@YAXPEAPEAUID3D11Buffer@@HPEBX@Z", 970, _load_buffer),
    case("?sub_140601AD0@@YAXPEAPEAUID3D11Buffer@@HPEBX@Z", 0xAD0, _load_buffer),
    case("?Load_IndexBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@IPEBD@Z", 0x6C0, _view_input),
    case("?Load_VertexBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@IPEBD@Z", 0x7F0, _view_input),
    case("?Load_RawDataBufferView@@YAXPEAPEAUID3D11ShaderResourceView@@PEAUID3D11Buffer@@PEAXIPEBD@Z", 0x720,
         lambda r: _view_input(r, True)),
    case("?Load_RawDataBuffer@@YAXPEAPEAUID3D11Buffer@@PEAXIPEBD@Z", 0x6E0, _load_raw),
    case("?R_AllocDynamicIndexBuffer@@YAPEAXPEAPEAUID3D11Buffer@@HPEBD@Z", 0x810, _alloc, ret="int64"),
    case("?R_AllocStaticIndexBuffer@@YAPEAXPEAPEAUID3D11Buffer@@HPEBD@Z", 0x890, _alloc, ret="int64"),
    case("?R_AllocStaticVertexBuffer@@YAPEAXPEAPEAUID3D11Buffer@@HPEBD@Z", 0xA00, _alloc, ret="int64"),
    case("?R_CreateBufferInternal@@YAJPEBUD3D11_BUFFER_DESC@@PEBUD3D11_SUBRESOURCE_DATA@@PEAPEAUID3D11Buffer@@@Z",
         0xB60, _create_internal, ret="int"),
    case("?R_CreateDynamicBuffers@@YAXXZ", 0xBC0, _create_dynamic, n=120),
    case("?sub_140601D70@@YAXIPEBDPEAPEAUID3D11Buffer@@@Z", 0xD70, _constant_buffer),
    case("?R_CreateParticleCloudBuffer@@YAXXZ", 0xE00, _cloud, n=30),
    case("?R_DestroyDynamicBuffers@@YAXXZ", 0x2360, _destroy_dynamic, n=120),
    case("?R_DestroyDynamicVertexBufferState@@YAXPEAUGfxVertexBufferState@@@Z", 0x24D0, _destroy_vb_state),
    case("?R_DestroyParticleCloudBuffer@@YAXXZ", 0x2550, _destroy_cloud),
    case("?R_FreeStaticVertexBuffer@@YAXPEAUID3D11Buffer@@@Z", 0x2600, _release),
    case("?sub_140602620@@YAIPEAUID3D11Buffer@@@Z", 0x2620, _release, ret="int"),
    case("?R_InitDynamicVertexBufferState@@YAXPEAUGfxVertexBufferState@@H_N@Z", 0x2640, _init_vb_state),
    case("?R_LockIndexBuffer@@YAPEAXPEAUID3D11DeviceContext@@PEAUID3D11Buffer@@HHW4D3D11_MAP@@@Z", 0x2760, _lock,
         ret="int64"),
    case("?R_LockVertexBuffer@@YAPEAXPEAUID3D11DeviceContext@@PEAUID3D11Buffer@@HHW4D3D11_MAP@@@Z", 0x27B0, _lock,
         ret="int64"),
    case("?R_ReleaseBuffer@@YAJPEAUID3D11Buffer@@@Z", 0x2800, _release, ret="int"),
    case("?R_UnlockIndexBuffer@@YAXPEAUID3D11DeviceContext@@PEAUID3D11Buffer@@@Z", 0x2840, _unlock, n=40),
    case("?R_UnlockVertexBuffer@@YAXPEAUID3D11DeviceContext@@PEAUID3D11Buffer@@@Z", 0x2850, _unlock, n=40),
    case("?SortVerticesByDistanceToOrigin_CompareFunc@@YAHPEBX0@Z", 0x2860, lambda r: _compare(r), n=600, ret="int"),
    case("?R_GetConstantBufferHandleOfSize@@YAEII@Z", 0x30360, _cb_handle, n=400, ret="char"),
    case("?R_GetPerPrimConstantBufferOfSize@@YAPEAUID3D11Buffer@@I@Z", 0x30520, _cb_perprim, n=300, ret="int64"),
]
