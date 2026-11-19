"""Differential cases for the Store build's tessellation buffer (gfx_d3d/rb_shade.cpp), R_SetVertexData
(gfx_d3d/r_shade.cpp) and the viewport functions R_GetViewport and R_UpdateViewport (gfx_d3d/r_state.cpp).

The back end draws `tess` with its own state (gfxCmdBufState) on a model context (d3dctx.py). Callees that are
tested on their own elsewhere are faked where their inputs would need a whole material system (the pass setup in
R_DrawTessTechnique, the drawing in RB_EndTessSurface's callers); the uploads (Map, the copied bytes, Unmap) run
for real.
"""
import random
import struct

from d3dctx import RES
from harness import SCRATCH
from syms import va
from test_r_state_cmdbuf import M, _install, _new_state, _put, _rec, _source_va, _state_va
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RCX, UC_X86_REG_RDX

STORE = "iw6mp64_MSStore_ship"
TESS_INDEX_COUNT = 0x22A948
TESS_INDICES = 0x2A940


def _dx(off):
    return va("dx") + off


def _tess():
    return va("tess")


def _vb_state(w, rr, model, used, total):
    vb = w.alloc(struct.pack("<iiQ", used, total, model.new(RES)) + bytes(0x20))
    w.u64(va("gfxBuf") + 0x1BF9F0, vb)
    return vb


# ---- R_SetVertexData ----------------------------------------------------------------------------------------------

def _vertex_data_input(r, seed):
    count, size = r.choice(((0, 0x20), (1, 0x20), (4, 0x20), (r.randrange(1, 48), 0x20), (3, 12), (r.randrange(9), 16)))
    data = bytes(r.getrandbits(8) for _ in range(max(1, count * size)))
    used = r.choice((0, 0, 0x40, r.getrandbits(16)))

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        w.u64(_dx(0x10), model.ctx)
        _vb_state(w, rr, model, used, 0x100000)
        w.write(_state_va(), bytes(_new_state(model)))
    return {"args": [_state_va(), data, count, size], "setup": setup}


# ---- viewport ------------------------------------------------------------------------------------------------------

SCALES = (1.0, 1.0, 0.5, 0.8, 0.0, 1.25, 0.999)


def _source_viewport(w, rr):
    s = _source_va()
    w.u32(s + 0x2CE0, rr.choice((0, 1, 1, 2)))
    w.write(s + 0x2CE4, struct.pack("<ii", rr.choice((1280, 1920, 1, 7)), rr.choice((720, 1080, 1, 3))))
    w.write(s + 0x2CC0, struct.pack("<4i", *(rr.randrange(-50, 2000) for _ in range(4))))
    w.u32(s + 0x2C84, rr.choice((0, 1, 2, 2, 3)))


def _get_viewport_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        _source_viewport(w, rr)
        w.write(va("g_drawConsts") + 0x60, struct.pack("<f", rr.choice(SCALES)))
    return {"args": [_source_va(), bytes(16)], "setup": setup}


def _update_viewport_input(r, seed):
    vp = struct.pack("<4i", *(r.randrange(-50, 2000) for _ in range(4)))

    def setup(w):
        rr = random.Random(seed)
        _source_viewport(w, rr)
        w.write(_source_va() + 0x2CFC, bytes([rr.getrandbits(8)]))
        w.write(_source_va() + 0x2900, bytes(rr.getrandbits(8) for _ in range(0x246)))
    return {"args": [_source_va(), vp], "setup": setup}


# ---- RB_SetTessTechnique, RB_TessOverflow, RB_EndTessSurface ---------------------------------------------------------

def _flush_fake(mu):
    """sub_14068D2A0 (draws tess): logged with its scissor argument and what tess holds."""
    _rec("sub_14068D2A0", mu.reg_read(UC_X86_REG_RCX),
         bytes(mu.mem_read(_tess() + TESS_INDEX_COUNT, 16)))


def _material(w, rr, n_tech=8):
    """A Material whose techniqueSet (at +0x1D0) has n_tech technique pointers; returns (material, techniques)."""
    techniques = [w.alloc(bytes(0x10)) for _ in range(n_tech)]
    tset = w.alloc(bytes(0x10) + struct.pack(f"<{n_tech}Q", *techniques))
    mat = bytearray(0x3A8)
    _put(mat, 0x1D0, "Q", tset)
    return w.alloc(bytes(mat)), techniques


def _set_tess_technique_input(r, seed):
    tech = r.randrange(8)
    target = r.choice((5, 7, 0))

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        mat, _ = _material(w, rr)
        other, _ = _material(w, rr)
        s = _new_state(model)
        _put(s, 0x10, "i", rr.choice((0, 3, 17)))
        _put(s, 0x1B90, "Qi", rr.choice((mat, mat, other)), rr.choice((tech, tech, rr.randrange(8))))
        w.write(_state_va(), bytes(s))
        w.write(_tess() + TESS_INDEX_COUNT, struct.pack("<4I", rr.choice((0, 6)), rr.choice((0, 0, 4)),
                                                         rr.getrandbits(16), rr.getrandbits(16)))
    return {"args": ["MATERIAL", tech, target], "setup": setup}


def _overflow_input(r, seed):
    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        mat, _ = _material(w, rr)
        s = _new_state(model)
        _put(s, 0x10, "i", rr.choice((0, 3, 17)))
        _put(s, 0x1B90, "Qi", mat, rr.randrange(8))
        w.write(_state_va(), bytes(s))
        w.write(_tess() + TESS_INDEX_COUNT, struct.pack("<4I", 6, 4, rr.getrandbits(16), rr.getrandbits(16)))
    return {"args": [], "setup": setup}


def _end_tess_input(r, seed):
    def setup(w):
        M["m"] = w.m
        w.write(_tess() + TESS_INDEX_COUNT, struct.pack("<4I", 6, 4, 1, 2))
    return {"args": [], "setup": setup}


# ---- sub_14068D2A0 (RB_EndTessSurface with a scissor) ---------------------------------------------------------------

def _draw_tess_fake(mu):
    ctx, args = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    _rec("R_DrawTessTechnique", bytes(mu.mem_read(ctx, 16)), bytes(mu.mem_read(args, 12)))


def _end_tess_scissor_input(r, seed):
    scissor = r.choice((0, 0, SCRATCH))
    tris = r.choice((0, 1, 2, r.randrange(1, 60)))
    indices = bytes(r.getrandbits(8) for _ in range(6 * tris))

    def setup(w):
        rr = random.Random(seed)
        sc = w.alloc(struct.pack("<4i", *(rr.randrange(-10, 1500) for _ in range(4))))
        assert sc == SCRATCH
        model = _install(w)
        w.u64(_dx(0x10), model.ctx)
        ib = w.alloc(struct.pack("<iiQQ", rr.choice((0, 0x30)), 0x100000, model.new(RES), 0))
        w.u64(va("gfxBuf") + 0x20, ib)
        _source_viewport(w, rr)
        w.write(_source_va() + 0x2CFC, bytes([rr.getrandbits(8)]))
        w.write(va("g_drawConsts") + 0x60, struct.pack("<f", rr.choice(SCALES)))
        s = _new_state(model)
        _put(s, 0x2344, "4i", *(rr.randrange(0, 1500) for _ in range(4)))
        _put(s, 0x2354, "4i", *(rr.randrange(0, 1500) for _ in range(4)))
        _put(s, 0x1BB8, "ff", 1.0, 0.0)
        w.write(_state_va(), bytes(s))
        if indices:
            w.write(_tess() + TESS_INDICES, indices)
        w.write(_tess() + TESS_INDEX_COUNT, struct.pack("<II", 3 * tris + rr.choice((0, 0, 1, 2)), rr.getrandbits(12)))
    return {"args": [scissor], "setup": setup}


# ---- R_DrawTessTechnique ---------------------------------------------------------------------------------------------

def _pass_fake(name, with_index=False):
    def fn(mu):
        ctx = mu.reg_read(UC_X86_REG_RCX)
        # a GfxCmdBufContext copy (by reference) or a GfxCmdBufState; R_SetupPass also gets the pass index
        _rec(name, bytes(mu.mem_read(ctx, 16)), *([mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF] if with_index else []))
    return fn


def _draw_tess_input(r, seed):
    passes = r.choice((0, 1, 2, 3))
    verts = r.choice((0, 1, 4, r.randrange(1, 40)))
    prim = struct.pack("<3i", r.randrange(20), r.randrange(100), 0)
    context = struct.pack("<QQ", _source_va(), _state_va())

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        w.u64(_dx(0x10), model.ctx)
        total = rr.choice((0x100000, 0x400, 0x20 * verts + 0x40))
        _vb_state(w, rr, model, rr.choice((0, 0, 0x40, total - 0x20 * verts, total - 0x20 * verts + 1)), total)
        tech = w.alloc(bytes(0xA) + struct.pack("<H", passes) + bytes(0x4))
        s = _new_state(model)
        _put(s, 0x1BA0, "Q", tech)
        _put(s, 0x14, "I", rr.choice((4, 2, 0x23)))
        for i in range(3):
            if rr.random() < 0.5:
                _put(s, 0x28 + 8 * i, "Q", model.new(RES))
                _put(s, 0x40 + 4 * i, "I", rr.getrandbits(8))
                _put(s, 0x18 + 4 * i, "I", rr.choice((0, 0x20)))
        w.write(_state_va(), bytes(s))
        w.write(_tess(), bytes(rr.getrandbits(8) for _ in range(0x20 * verts)))
        w.write(_tess() + TESS_INDEX_COUNT, struct.pack("<II", rr.getrandbits(8), verts))
    return {"args": [context, prim], "setup": setup}


# ---- cases ----------------------------------------------------------------------------------------------------------

def _inputs(fn, seed, n):
    r = random.Random(seed)
    return [fn(r, seed * 1000 + i) for i in range(n)]


def _case(symbol, ret, inputs, **extra):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs, **extra}


def _material_args(inputs):
    """RB_SetTessTechnique's material: the first scratch allocation of _material (its techniques come first)."""
    for inp in inputs:
        inp["args"][0] = SCRATCH + 0x10 * 8 + 0x50  # 8 techniques (0x10 each), then the set (0x50)
    return inputs


FLUSH = "?sub_14068D2A0@@YAXPEBUGfxViewport@@@Z"
DRAW_TESS = "?R_DrawTessTechnique@@YAXUGfxCmdBufContext@@PEBUGfxDrawPrimArgs@@@Z"
PASS_FAKES = {
    "?R_SetupPass@@YAXUGfxCmdBufContext@@I@Z": _pass_fake("R_SetupPass", True),
    "?R_UpdateVertexDecl@@YAXPEAUGfxCmdBufState@@@Z": _pass_fake("R_UpdateVertexDecl"),
    "?sub_14065D5A0@@YAXUGfxCmdBufContext@@@Z": _pass_fake("sub_14065D5A0"),
    "?R_SetupPassPerObjectArgs@@YAXUGfxCmdBufContext@@@Z": _pass_fake("R_SetupPassPerObjectArgs"),
    "?R_SetupPassPerPrimArgs@@YAXUGfxCmdBufContext@@@Z": _pass_fake("R_SetupPassPerPrimArgs"),
}

CASES = [
    _case("?R_SetVertexData@@YAHPEAUGfxCmdBufState@@PEBXHH@Z", "int", _inputs(_vertex_data_input, 61, 120)),
    _case("?R_GetViewport@@YAXPEBUGfxCmdBufSourceState@@PEAUGfxViewport@@@Z", "void", _inputs(_get_viewport_input, 62, 200)),
    _case("?R_UpdateViewport@@YAXPEAUGfxCmdBufSourceState@@PEBUGfxViewport@@@Z", "void",
          _inputs(_update_viewport_input, 63, 150)),
    _case("?RB_SetTessTechnique@@YAXPEBUMaterial@@W4MaterialTechniqueType@@W4GfxPrimStatsTarget@@@Z", "void",
          _material_args(_inputs(_set_tess_technique_input, 64, 120)), fakes={FLUSH: _flush_fake}),
    _case("?RB_TessOverflow@@YAXXZ", "void", _inputs(_overflow_input, 65, 30), fakes={FLUSH: _flush_fake}),
    _case("?RB_EndTessSurface@@YAXXZ", "void", _inputs(_end_tess_input, 66, 20), fakes={FLUSH: _flush_fake}),
    _case(FLUSH, "void", _inputs(_end_tess_scissor_input, 67, 150), fakes={DRAW_TESS: _draw_tess_fake}),
    _case(DRAW_TESS, "void", _inputs(_draw_tess_input, 68, 150), fakes=PASS_FAKES),
]
