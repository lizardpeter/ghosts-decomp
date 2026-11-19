"""Differential cases for the Store build's per-frame state cache: gfx_d3d/r_state.cpp (`per-frame` block),
gfx_d3d/r_setstate_d3d.cpp and gfx_d3d/r_state_utils.cpp.

The state lives where the game keeps it (gfxCmdBufState, gfxCmdBufSourceState), so everything a function writes
into it is compared; its context is a model object (d3dctx.py), so every context call is compared with its arguments
by content. The state tables in `dx` (rasterizer, depth-stencil and blend tables, samplers) and the render targets
(gfxRenderTargets) hold model objects too, so a test sees which one was bound. Inputs mix "already bound" (the cache
matches, nothing is called) with changes in each field the functions compare.
"""
import random
import struct

import d3dctx
from com import OBJ_SIZE, OBJECTS
from d3dctx import CTX, RES, STATE, VIEW
from harness import SCRATCH
from syms import va
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX

STORE = "iw6mp64_MSStore_ship"
STATE_SIZE = 0x23B0
NONE_TARGET = 0x184
NONE_SUITE = 4
TARGET_IDS = (1, 3, 6, 13, 72, 0x100)
M = {}


def _rec(*entry):
    M["m"].observed.append(entry)


def _dx(off):
    return va("dx") + off


def _state_va():
    return va("gfxCmdBufState")


def _source_va():
    return va("gfxCmdBufSourceState")


def _put(buf, off, fmt, *v):
    struct.pack_into("<" + fmt, buf, off, *v)


def _install(w):
    M["m"] = w.m
    return d3dctx.install(w)


def _objects(model, kind, n):
    return [model.new(kind) for _ in range(n)]


def _maybe(r, p, value, other=0):
    return value if r.random() < p else other


# ---- render targets, samplers and textures --------------------------------------------------------------------

FORMATS = (10, 26, 54, 10, 26, 54, 28, 29, 87, 2, 0x60, 0x37, 0x36)  # the three float formats twice as often


def _render_targets(w, r, model, images=None):
    """Fills gfxRenderTargets[TARGET_IDS]: the image, colour, depth and gamma views of both surfaces (sometimes
    shared between targets, sometimes the gamma view is the colour view) and the format."""
    rtvs = _objects(model, VIEW, 5)
    dsvs = _objects(model, VIEW, 3) + [0]
    images = images or [0]
    for tid in TARGET_IDS:
        entry = bytearray(0x50)
        for s in range(2):
            color = r.choice(rtvs)
            gamma = color if r.random() < 0.3 else r.choice(rtvs)
            _put(entry, 0x20 * s, "QQQQ", r.choice(images + [0]), color, r.choice(dsvs), gamma)
        _put(entry, 0x40, "III", r.getrandbits(12), r.getrandbits(12), r.choice(FORMATS))
        w.write(va("gfxRenderTargets") + 0x50 * tid, bytes(entry))


def _samplers(w, model):
    objs = _objects(model, STATE, 256)
    w.write(_dx(0x3368), struct.pack("<256Q", *objs))
    return objs


def _textures(w, r, model, n=8):
    """n GfxTextures in scratch memory (basemap, shaderView: an object or NULL)."""
    views = _objects(model, VIEW, n)
    return [w.alloc(struct.pack("<QQQ", 0, _maybe(r, 0.9, v), 0)) for v in views]


def _dirty(r, limit):
    k = r.random()
    if k < 0.3:
        return limit, -1
    if k < 0.4:
        return r.randrange(limit), r.randrange(-1, limit)  # either order
    a = r.randrange(limit)
    return a, r.randrange(a, limit)


def _texture_arrays(s, r, textures, density=0.1):
    for base in (0xF60, 0x1360, 0x1760):
        for i in range(128):
            if r.random() < density:
                _put(s, base + 8 * i, "Q", r.choice(textures))


def _sampler_bytes(s, r):
    for base in (0xF30, 0xF40, 0xF50):
        s[base:base + 16] = bytes(r.getrandbits(8) for _ in range(16))


def _dirty_ranges(s, r):
    for i, limit in enumerate((16, 16, 16, 128, 128, 128)):
        _put(s, 0x1B60 + 8 * i, "ii", *_dirty(r, limit))


def _new_state(model):
    s = bytearray(STATE_SIZE)
    _put(s, 0, "Q", model.ctx)
    return s


# ---- r_setstate_d3d.cpp -----------------------------------------------------------------------------------------

def _gamma_fields(s, r):
    _put(s, 0x236C, "i", r.choice((NONE_SUITE, NONE_SUITE, NONE_SUITE, 0, 1, 2)))
    s[0x238C] = r.getrandbits(1)                       # srgbWrite
    s[0x238D] = r.getrandbits(1)                       # srgbRenderTarget
    s[0x2368] = r.getrandbits(1)                       # msaaTarget
    _put(s, 0x2364, "i", r.choice(TARGET_IDS + (NONE_TARGET,)))


def _default_states_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        s = _new_state(model)
        s[0x2378:0x23B0] = bytes(rr.getrandbits(8) for _ in range(0x38))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va()], "setup": setup}


def _gamma_input(r, seed):
    bits = r.getrandbits(32)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _render_targets(w, rr, model)
        s = _new_state(model)
        _gamma_fields(s, rr)
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), bits], "setup": setup}


# ---- r_state.cpp: state bits ---------------------------------------------------------------------------------------

STATE_BIT_FLIPS = (0, 0x40, 0x38, 0x08, 0xFF00, 0x100, 0x30 << 32, 0x01 << 32, 0x200 << 32, 0x40 << 32,
                   0x0F7FF7FF << 64, 0x08000800 << 64, 0x1 << 64)


def _state_bits(r):
    ref = r.getrandbits(96)
    k = r.random()
    if k < 0.15:
        bits = ref
    elif k < 0.7:
        bits = ref ^ r.choice(STATE_BIT_FLIPS) ^ (r.choice(STATE_BIT_FLIPS) if r.random() < 0.3 else 0)
    else:
        bits = r.getrandbits(96)
    split = lambda v: [(v >> (32 * i)) & 0xFFFFFFFF for i in range(3)]
    return split(ref), split(bits)


def _state_tables(w, r, model, zone):
    """dx.rasterizerStates and one zone's depth-stencil and blend tables, all model objects."""
    raster = _objects(model, STATE, 32)
    w.write(_dx(0x2660), struct.pack("<32Q", *raster))
    dss = _objects(model, STATE, 16)
    blend = _objects(model, STATE, 16)
    w.u64(_dx(0xE50) + 8 * zone, w.alloc(struct.pack("<16Q", *dss)))
    w.u64(_dx(0x10D8) + 8 * zone, w.alloc(struct.pack("<16Q", *blend)))
    return raster, dss, blend


def _set_state_input(r, seed):
    ref, bits = _state_bits(r)
    zone = r.randrange(4)
    sb = bytearray(0x1C)
    _put(sb, 0, "III", *(r.getrandbits(32) for _ in range(3)))
    sb[0xC] = zone
    sb[0xD:0x18] = bytes(r.randrange(16) for _ in range(11))
    sb[0x18] = r.randrange(16)
    sb[0x19] = r.getrandbits(8)
    context = struct.pack("<QQ", _source_va(), _state_va())

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        raster, dss, blend = _state_tables(w, rr, model, zone)
        _render_targets(w, rr, model)
        s = _new_state(model)
        _gamma_fields(s, rr)
        _put(s, 0x2308, "III", *ref)
        _put(s, 0x2300, "i", rr.randrange(11))
        _put(s, 0x2390, "QQQ", rr.choice(raster), rr.choice(blend), rr.choice(dss))
        _put(s, 0x2378, "4I", *(rr.getrandbits(32) for _ in range(4)))
        _put(s, 0x2388, "I", rr.getrandbits(32))
        w.write(_state_va(), bytes(s))
        w.u32(_source_va() + 0x2CD0, rr.randrange(11))
    return {"args": [context, struct.pack("<3I", *bits), bytes(sb)], "setup": setup}


def _complete_state_input(r, seed):
    bits = [r.getrandbits(32) for _ in range(3)]

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _render_targets(w, rr, model)
        s = _new_state(model)
        _gamma_fields(s, rr)
        s[0x2378:0x23A8] = bytes(rr.getrandbits(8) for _ in range(0x30))
        s[0x238C], s[0x238D] = rr.getrandbits(1), rr.getrandbits(1)  # bools: the game only stores 0 and 1
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), struct.pack("<3I", *bits)], "setup": setup}


# ---- r_state.cpp: textures and samplers ------------------------------------------------------------------------------

def _texture_state_setup(seed, extra=None, density=0.1):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _samplers(w, model)
        textures = _textures(w, rr, model)
        s = _new_state(model)
        _sampler_bytes(s, rr)
        _dirty_ranges(s, rr)
        _texture_arrays(s, rr, textures, density)
        if extra:
            extra(w, rr, model, s, textures)
        w.write(_state_va(), bytes(s))
    return setup


def _flush_input(r, seed):
    return {"args": [_state_va()], "setup": _texture_state_setup(seed, density=r.choice((0, 0.05, 0.3, 0.9)))}


def _clear_domain_input(r, seed):
    index = r.choice((0, 1, 127, r.randrange(128), r.randrange(128)))
    return {"args": [_state_va(), index], "setup": _texture_state_setup(seed, density=r.choice((0.1, 0.5, 1.0)))}


def _clear_all_input(r, seed):
    return {"args": [_state_va()], "setup": _texture_state_setup(seed, density=r.choice((0, 0.02, 0.2, 1.0)))}


def _unbind_input(r, seed):
    # the image: the first GfxTexture _textures allocates (the first scratch allocation), or NULL
    image = SCRATCH if r.random() < 0.8 else 0

    def extra(w, rr, model, s, textures):
        assert textures[0] == SCRATCH
        for base in (0xF60, 0x1360, 0x1760):
            for i in range(128):
                if rr.random() < 0.05:
                    _put(s, base + 8 * i, "Q", image)
    return {"args": [_state_va(), image], "setup": _texture_state_setup(seed, extra)}


# ---- r_state.cpp: streams and draws ------------------------------------------------------------------------------

def _streams(s, r, buffers):
    for i in range(3):
        if r.random() < 0.5:
            continue
        _put(s, 0x28 + 8 * i, "Q", r.choice(buffers + [0]))
        _put(s, 0x40 + 4 * i, "I", r.choice((0, 0, r.getrandbits(16))))
        _put(s, 0x18 + 4 * i, "I", r.choice((0, 0, 4, 32, r.getrandbits(8))))


def _streams_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        s = _new_state(model)
        _streams(s, rr, _objects(model, RES, 3))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va()], "setup": setup}


TOPOLOGIES = (0, 1, 2, 3, 4, 5, 0x23, 0x30, 0x24)


def _prim_type_input(r, seed):
    current, new = r.choice(TOPOLOGIES), r.choice(TOPOLOGIES)

    def setup(w):
        model = _install(w)
        s = _new_state(model)
        _put(s, 0x14, "I", current)
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), new], "setup": setup}


def _draw_input(r, seed, instanced):
    prim = r.choice(TOPOLOGIES)
    args = struct.pack("<3i", r.getrandbits(20), r.getrandbits(20), r.randrange(-1000, 1 << 20))

    def setup(w):
        model = _install(w)
        s = _new_state(model)
        _put(s, 0x14, "I", prim)
        w.write(_state_va(), bytes(s))
    extra = [r.getrandbits(16)] if instanced else []
    return {"args": [_state_va(), args, *extra], "setup": setup}


def _mesh_input(r, seed):
    # the GfxMeshData is the first scratch allocation
    def setup(w):
        rr = random.Random(seed)
        mesh_va = w.alloc(bytes(0x50))
        assert mesh_va == SCRATCH
        model = _install(w)
        buffers = _objects(model, RES, 3)
        s = _new_state(model)
        _streams(s, rr, buffers)
        _put(s, 0x8, "Q", rr.choice(buffers + [0]))
        w.write(_state_va(), bytes(s))
        mesh = bytearray(0x50)
        _put(mesh, 0x8, "Q", rr.choice(buffers + [0]))
        _put(mesh, 0x20, "Q", rr.choice(buffers + [0]))
        _put(mesh, 0x48, "I", rr.choice((0, 4, 32, rr.getrandbits(8))))
        w.write(mesh_va, bytes(mesh))
    return {"args": [_state_va(), SCRATCH, r.getrandbits(32)], "setup": setup}


def _shutdown_input(r, seed):
    def extra(w, rr, model, s, textures):
        buffers = _objects(model, RES, 3)
        _streams(s, rr, buffers)
        _put(s, 0x8, "Q", _maybe(rr, 0.6, buffers[0]))
    return {"args": [_state_va()], "setup": _texture_state_setup(seed, extra, density=0.1)}


# ---- r_state.cpp: viewport and scissor --------------------------------------------------------------------------

def _rect(r):
    return [r.choice((0, 0, r.getrandbits(12), r.randrange(-100, 100))) for _ in range(2)] + \
        [r.choice((0x2000, r.getrandbits(13), 0)) for _ in range(2)]


def _depth_range_input(r, seed):
    kind = r.choice((-1, 0, 1, 2, 3, 4, 7, -2))

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        s = _new_state(model)
        _put(s, 0x2354, "4i", *(rr.randrange(-5000, 5000) for _ in range(4)))
        _put(s, 0x1BB4, "III", rr.getrandbits(32), rr.getrandbits(32), rr.getrandbits(32))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), kind], "setup": setup}


def _scissor_state(s, r):
    k = r.random()
    if k < 0.3:
        _put(s, 0x2344, "4i", 0, 0, 0x2000, 0x2000)
    elif k < 0.6:
        v = [0, 0, 0x2000, 0x2000]
        v[r.randrange(4)] = r.getrandbits(13)
        _put(s, 0x2344, "4i", *v)
    else:
        _put(s, 0x2344, "4i", *_rect(r))


def _disable_scissor_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        s = _new_state(model)
        _scissor_state(s, rr)
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va()], "setup": setup}


def _set_scissor_input(r, seed):
    vp = _rect(r)
    same = r.random() < 0.3

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        s = _new_state(model)
        if same:
            _put(s, 0x2344, "4i", *vp)
        else:
            _scissor_state(s, rr)
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), struct.pack("<4i", *vp)], "setup": setup}


def _viewport_scissor_input(r, seed):
    vp, sc = _rect(r), _rect(r)
    k = r.random()

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        s = _new_state(model)
        _put(s, 0x2354, "4i", *(vp if k < 0.5 else _rect(rr)))
        _put(s, 0x2344, "4i", *(sc if k < 0.25 or k > 0.75 else _rect(rr)))
        if 0.5 <= k < 0.6:
            v = list(vp)
            v[rr.randrange(4)] ^= 1
            _put(s, 0x2354, "4i", *v)
        _put(s, 0x1BB8, "II", rr.getrandbits(32), rr.getrandbits(32))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), struct.pack("<4i", *vp), struct.pack("<4i", *sc)], "setup": setup}


def _clear_screen_input(r, seed):
    which = r.getrandbits(8)
    color = struct.pack("<4I", *(r.getrandbits(32) for _ in range(4)))
    depth = r.choice((0.0, 1.0, r.uniform(-2, 2)))
    stencil = r.getrandbits(8)
    viewport = r.choice((0, struct.pack("<4i", *_rect(r))))
    rtv_on, dsv_on = r.random() < 0.7, r.random() < 0.7

    def setup(w):
        model = _install(w)
        rtv, dsv = model.new(VIEW), model.new(VIEW)
        model.bound_rtv = rtv if rtv_on else 0
        model.bound_dsv = dsv if dsv_on else 0
        w.write(_state_va(), bytes(_new_state(model)))
    return {"args": [_state_va(), which, color, ("f", depth), stencil, viewport], "setup": setup}


# ---- r_state.cpp: render targets ------------------------------------------------------------------------------------

def _render_target_setup(seed, suite):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _samplers(w, model)
        textures = _textures(w, rr, model)
        _render_targets(w, rr, model, images=textures[:4])
        s = _new_state(model)
        _sampler_bytes(s, rr)
        _dirty_ranges(s, rr)
        _texture_arrays(s, rr, textures, 0.05)
        _gamma_fields(s, rr)
        _put(s, 0x2308, "I", rr.getrandbits(32))
        if suite is not None and rr.random() < 0.2:
            _put(s, 0x236C, "i", suite)
        w.write(_state_va(), bytes(s))
        w.write(_source_va() + 0x2CD4, bytes([rr.getrandbits(1)]))
        w.write(_source_va() + 0x2CFC, bytes([rr.getrandbits(8)]))
        w.u32(_source_va() + 0x2C84, rr.getrandbits(32))
        for i in range(3):
            pair = [rr.choice(TARGET_IDS + (NONE_TARGET,)) for _ in range(2)]
            w.write(_source_va() + 0x267C + 8 * i, struct.pack("<2i", *pair))
    return setup


def _set_render_target_input(r, seed):
    target = r.choice(TARGET_IDS)
    context = struct.pack("<QQ", _source_va(), _state_va())
    return {"args": [context, target], "setup": _render_target_setup(seed, None)}


def _set_suite_input(r, seed):
    suite = r.randrange(3)
    context = struct.pack("<QQ", _source_va(), _state_va())
    return {"args": [context, suite], "setup": _render_target_setup(seed, suite)}


# ---- r_state.cpp: R_DrawCall and the reactive turbulence buffer -----------------------------------------------------

def _lock_imports(w, r):
    tid = r.getrandbits(32)

    def log(name, n):
        return lambda mu: _rec(name, *[mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF][:n])

    def thread_id(mu):
        _rec("GetCurrentThreadId")
        mu.reg_write(UC_X86_REG_RAX, tid)
    w.m.on_import("kernel32.dll!WaitForSingleObject", log("WaitForSingleObject", 2))
    w.m.on_import("kernel32.dll!ReleaseMutex", log("ReleaseMutex", 1))
    w.m.on_import("kernel32.dll!GetCurrentThreadId", thread_id)


def _draw_call_callback(mu):
    """The draw callback: logs its arguments and leaves things bound for R_DrawCall to clean up."""
    user = mu.reg_read(UC_X86_REG_RCX)
    ctx = mu.reg_read(UC_X86_REG_RDX)
    source, state = struct.unpack("<QQ", bytes(mu.mem_read(ctx, 16)))
    _rec("callback", user, source, bytes(mu.mem_read(state, STATE_SIZE)))
    r = M["callback_rng"]
    objs = M["callback_objs"]
    s = bytearray(mu.mem_read(state, STATE_SIZE))
    _put(s, 0x8, "Q", r.choice(objs + [0]))
    _streams(s, r, objs)
    for base in (0xF60, 0x1360, 0x1760):
        for i in range(128):
            if r.random() < 0.05:
                _put(s, base + 8 * i, "Q", r.choice(M["callback_textures"]))
    _dirty_ranges(s, r)
    mu.mem_write(state, bytes(s))


def _begin_view_fake(mu):
    _rec("R_BeginView", mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8))


def _draw_call_input(r, seed):
    # objects are created in order: the immediate context (OBJECTS), then a deferred one
    immediate = r.random() < 0.5
    device = OBJECTS if immediate else OBJECTS + OBJ_SIZE
    user = r.getrandbits(64)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        deferred = model.new(CTX)
        assert model.ctx == OBJECTS and deferred == OBJECTS + OBJ_SIZE
        _samplers(w, model)
        w.u64(_dx(0x10), model.ctx)
        w.u64(_dx(0x48), model.new(RES))
        w.u64(_dx(0x50), model.new(RES))
        w.u64(_dx(0x3B68), 0x1234)
        w.u32(_dx(0x18), rr.choice((0, 0, 1, 3)))
        _lock_imports(w, rr)
        M["callback_rng"] = random.Random(seed + 1)
        M["callback_objs"] = _objects(model, RES, 3)
        M["callback_textures"] = _textures(w, rr, model)
    # the callback is any original function address, faked (DRAW_CALL_FAKES)
    return {"args": [va(CALLBACK), user, _source_va(), 0x5000, 0x6000, struct.pack("<Q", device)], "setup": setup}


def _init_state_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _samplers(w, model)
        w.u64(_dx(0x48), model.new(RES))
        w.u64(_dx(0x50), model.new(RES))
        s = bytearray(rr.getrandbits(8) for _ in range(STATE_SIZE))
        _put(s, 0, "Q", model.ctx)
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va()], "setup": setup}


def _create_buffer_fake(mu):
    desc, init, out = (mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8))
    d = struct.unpack("<5I", bytes(mu.mem_read(desc, 20)))  # StructureByteStride is never set
    sysmem, pitch, slice_ = struct.unpack("<QII", bytes(mu.mem_read(init, 16)))
    _rec("R_CreateBufferInternal", d, bytes(mu.mem_read(sysmem, 0x300)), pitch, slice_, out)
    obj = M["created"]
    M["m"]._emulated_write(out, struct.pack("<Q", obj))
    return 0


def _turbulence_input(r, seed):
    def setup(w):
        model = _install(w)
        M["created"] = model.new(RES)
        w.write(_state_va(), bytes(_new_state(model)))
    return {"args": [_state_va()], "setup": setup}


# ---- r_state.cpp: the texture and sampler setters, code textures ------------------------------------------------

def _texture_setter_input(base, null_view):
    def make(r, seed):
        index = r.choice((0, 127, r.randrange(128)))
        image = SCRATCH + 0x20 * r.randrange(3)  # one of three GfxTextures allocated first

        def setup(w):
            rr = random.Random(seed)
            model = _install(w)
            images = [w.alloc(struct.pack("<QQQ", 0, _maybe(rr, 0.7 if null_view else 1.0, model.new(VIEW)), 0)
                              + bytes(8)) for _ in range(3)]
            assert images[0] == SCRATCH and images[1] == SCRATCH + 0x20
            s = _new_state(model)
            _dirty_ranges(s, rr)
            for i in range(128):
                if rr.random() < 0.3:
                    _put(s, base + 8 * i, "Q", rr.choice(images + [0]))
            if rr.random() < 0.3:
                _put(s, base + 8 * index, "Q", image)
            w.write(_state_va(), bytes(s))
        return {"args": [_state_va(), index, image], "setup": setup}
    return make


def _sampler_setter_input(base):
    def make(r, seed):
        index = r.choice((0, 15, r.randrange(16)))
        value = r.choice((0, 1, r.getrandbits(8)))

        def setup(w):
            rr = random.Random(seed)
            model = _install(w)
            s = _new_state(model)
            _sampler_bytes(s, rr)
            _dirty_ranges(s, rr)
            if rr.random() < 0.3:
                s[base + index] = value
            w.write(_state_va(), bytes(s))
        return {"args": [_state_va(), index, value], "setup": setup}
    return make


def _code_texture_input(r, seed):
    index = r.randrange(65)

    def setup(w):
        rr = random.Random(seed)
        w.write(_source_va() + 0x2430, struct.pack("<65Q", *(rr.getrandbits(64) for _ in range(65))))
        w.write(_source_va() + 0x2638, bytes(rr.getrandbits(8) for _ in range(65)))
    return {"args": [_source_va(), index, b"\x5a"], "setup": setup}


def _texture_error_fake(mu):
    _rec("Com_Error", mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, M["m"].read_cstr(mu.reg_read(UC_X86_REG_RDX)),
         M["m"].read_cstr(mu.reg_read(UC_X86_REG_R8)))


def _texture_error_input(r, seed):
    def setup(w):
        M["m"] = w.m
    return {"args": [_source_va(), r.randrange(65)], "setup": setup}


CALLBACK = "?R_InitCmdBufSourceState@@YAXPEAUGfxCmdBufSourceState@@PEBUGfxCmdBufInput@@I@Z"

# ---- cases ----------------------------------------------------------------------------------------------------------

def _inputs(fn, seed, n):
    r = random.Random(seed)
    return [fn(r, seed * 1000 + i) for i in range(n)]


def _case(symbol, ret, inputs, **extra):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs, **extra}


BEGIN_VIEW = "?R_BeginView@@YAXPEAUGfxCmdBufSourceState@@PEBUGfxSceneDef@@PEBUGfxViewParms@@@Z"
CREATE_BUFFER = "?R_CreateBufferInternal@@YAJPEBUD3D11_BUFFER_DESC@@PEBUD3D11_SUBRESOURCE_DATA@@PEAPEAUID3D11Buffer@@@Z"

CASES = [
    _case("?R_InitializeDefaultDeviceStates@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_default_states_input, 1, 20)),
    _case("?R_HW_SetGammaWriteEnable@@YAXPEAUGfxCmdBufState@@I@Z", "void", _inputs(_gamma_input, 2, 300)),
    _case("?R_SetState@@YAXUGfxCmdBufContext@@QEBIPEBUGfxStateBits@@@Z", "void", _inputs(_set_state_input, 3, 400)),
    _case("?R_SetCompleteState@@YAXPEAUGfxCmdBufState@@QEBI@Z", "void", _inputs(_complete_state_input, 4, 80)),
    _case("?R_FlushTextureState@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_flush_input, 5, 150)),
    _case("?R_ClearDomainTexture@@YAXPEAUGfxCmdBufState@@I@Z", "void", _inputs(_clear_domain_input, 6, 80)),
    *[_case(f"?R_ClearAll{stage}Textures@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_clear_all_input, 7 + i, 80))
      for i, stage in enumerate(("Vertex", "Domain", "Pixel"))],
    _case("?R_UnbindImage@@YAXPEAUGfxCmdBufState@@PEBUGfxImage@@@Z", "void", _inputs(_unbind_input, 10, 100)),
    _case("?R_ClearAllStreamSources@@YAXPEAUGfxCmdBufPrimState@@@Z", "void", _inputs(_streams_input, 11, 150)),
    _case("?R_SetPrimType@@YAXPEAUGfxCmdBufPrimState@@I@Z", "void", _inputs(_prim_type_input, 12, 80)),
    _case("?R_DrawIndexedPrimitive@@YAXPEAUGfxCmdBufPrimState@@PEBUGfxDrawPrimArgs@@@Z", "void",
          _inputs(lambda r, s: _draw_input(r, s, False), 13, 80)),
    _case("?R_DrawInstancedIndexedPrimitive@@YAXPEAUGfxCmdBufPrimState@@PEBUGfxDrawPrimArgs@@I@Z", "void",
          _inputs(lambda r, s: _draw_input(r, s, True), 14, 80)),
    _case("?R_SetMeshStream@@YAXPEAUGfxCmdBufState@@PEAUGfxMeshData@@I@Z", "void", _inputs(_mesh_input, 15, 150)),
    _case("?R_ShutdownCmdBufState@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_shutdown_input, 16, 100)),
    _case("?R_ChangeDepthRange@@YAXPEAUGfxCmdBufState@@W4GfxDepthRangeType@@@Z", "void",
          _inputs(_depth_range_input, 17, 100)),
    _case("?R_HW_DisableScissor2D@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_disable_scissor_input, 18, 80)),
    _case("?sub_140662700@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_disable_scissor_input, 19, 80)),
    _case("?R_HW_SetScissor@@YAXPEAUGfxCmdBufState@@PEBUGfxViewport@@@Z", "void", _inputs(_set_scissor_input, 20, 100)),
    _case("?R_SetViewportAndScissorSeparate@@YAXPEAUGfxCmdBufState@@PEBUGfxViewport@@1@Z", "void",
          _inputs(_viewport_scissor_input, 21, 150)),
    _case("?R_ClearScreenInternal@@YAXPEAUGfxCmdBufState@@EQEBMMEPEBUGfxViewport@@@Z", "void",
          _inputs(_clear_screen_input, 22, 100)),
    _case("?R_SetRenderTarget@@YAXUGfxCmdBufContext@@W4GfxRenderTargetId@@@Z", "void",
          _inputs(_set_render_target_input, 23, 250)),
    _case("?R_SetRenderTargetSuite@@YAXUGfxCmdBufContext@@W4GfxRenderTargetSuiteId@@@Z", "void",
          _inputs(_set_suite_input, 24, 250)),
    _case("?R_DrawCall@@YAXP6AXPEBXUGfxCmdBufContext@@@Z0PEAUGfxCmdBufSourceState@@PEBUGfxSceneDef@@PEBUGfxViewParms@@"
          "PEAUGfxDrawCallOutput@@@Z", "void", _inputs(_draw_call_input, 25, 40),
          fakes={CALLBACK: _draw_call_callback, BEGIN_VIEW: _begin_view_fake}),
    _case("?R_InitCmdBufState@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_init_state_input, 26, 30)),
    _case("?sub_14065FDD0@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_turbulence_input, 27, 20),
          fakes={CREATE_BUFFER: _create_buffer_fake}),
    *[_case(f"?R_Set{stage}Texture@@YAXPEAUGfxCmdBufState@@IPEBUGfxImage@@@Z", "void",
            _inputs(_texture_setter_input(base, stage == "Pixel"), 50 + i, 120))
      for i, (stage, base) in enumerate((("Vertex", 0xF60), ("Domain", 0x1360), ("Pixel", 0x1760)))],
    *[_case(f"?R_Set{stage}Sampler@@YAXPEAUGfxCmdBufState@@IE@Z", "void", _inputs(_sampler_setter_input(base), 53 + i, 120))
      for i, (stage, base) in enumerate((("Vertex", 0xF30), ("Domain", 0xF40), ("Pixel", 0xF50)))],
    _case("?R_GetTextureFromCode@@YAPEBUGfxImage@@PEAUGfxCmdBufSourceState@@IPEAE@Z", "int64",
          _inputs(_code_texture_input, 56, 60)),
    _case("?R_TextureFromCodeError@@YAXPEAUGfxCmdBufSourceState@@I@Z", "void", _inputs(_texture_error_input, 57, 30),
          fakes={"?Com_Error@@YAXW4errorParm_t@@PEBDZZ": _texture_error_fake}),
]
