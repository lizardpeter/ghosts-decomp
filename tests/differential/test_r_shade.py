"""Differential cases for the Store build's gfx_d3d/r_shade.cpp: setting up a material pass on a context (shaders,
input layout, state bits, constant buffers and their uploads) and the dynamic index buffer.

The state is the game's gfxCmdBufState on a model context (d3dctx.py). Shaders, passes, techniques and materials are
built in scratch memory; the blocks a function gets as arguments are allocated first, so their addresses
(SCRATCH + 0x30 * i) are known when the arguments are chosen. The shader argument walkers
(R_SetPassShader{Prim,Object,Stable}Arguments) are faked: they log what they are given, write random constants into
the pass's shadow array and say whether anything changed, so the upload that follows (Map, the copy, Unmap) is
compared byte for byte.
"""
import random
import struct

from d3dctx import RES, SHADER, VIEW
from harness import SCRATCH
from syms import va
from test_r_state_cmdbuf import (M, _dirty_ranges, _install, _new_state, _objects, _put, _rec, _sampler_bytes,
                                 _samplers, _source_va, _state_tables, _state_va, _texture_arrays, _textures)
from unicorn.x86_const import (UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX,
                               UC_X86_REG_RSP)

STORE = "iw6mp64_MSStore_ship"
BLOCK = 0x30  # a shader block in scratch (0x28 bytes, allocations are 16-aligned)


def _dx(off):
    return va("dx") + off


def _block(i):
    return SCRATCH + BLOCK * i


def _shaders(w, rr, model, n, prefix, null_object=0.05):
    """n Material*Shaders at _block(0.._block(n-1)): name, then the D3D object (NULL now and then)."""
    addrs = [w.alloc(bytes(0x28)) for _ in range(n)]
    assert addrs[0] == SCRATCH
    for i, a in enumerate(addrs):
        obj = model.new("ID3D11Shader") if rr.random() >= null_object else 0
        w.write(a, struct.pack("<QQ", w.cstr(f"{prefix}{i}"), obj))
    return addrs


def _pick(r, n, p_null=0.2):
    return 0 if r.random() < p_null else _block(r.randrange(n))


# ---- shaders ---------------------------------------------------------------------------------------------------------

def _single_shader_input(offset, allow_null):
    def make(r, seed):
        arg = _pick(r, 3, 0.2 if allow_null else 0)

        def setup(w):
            rr = random.Random(seed)
            model = _install(w)
            _shaders(w, rr, model, 3, "shader")
            s = _new_state(model)
            _put(s, offset, "Q", arg if rr.random() < 0.3 else _pick(rr, 3, 0.2 if allow_null else 0))
            w.write(_state_va(), bytes(s))
        return {"args": [_state_va(), arg], "setup": setup}
    return make


def _hs_ds_input(r, seed):
    hs, ds = _pick(r, 4, 0.4), _pick(r, 4, 0.4)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _shaders(w, rr, model, 4, "hsds")
        s = _new_state(model)
        k = rr.random()
        _put(s, 0x2328, "QQ", hs if k < 0.3 else _pick(rr, 4, 0.4), ds if k < 0.5 else _pick(rr, 4, 0.4))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), hs, ds], "setup": setup}


# ---- R_SetIndexData ----------------------------------------------------------------------------------------------

def _index_data_input(r, seed):
    tris = r.choice((0, 1, 2, 7, r.randrange(1, 200)))
    indices = bytes(r.getrandbits(8) for _ in range(6 * tris))
    total = r.choice((0x100000, 0x400, 30))
    used = r.choice((0, 0, r.randrange(total + 1), total - 3 * tris, total - 3 * tris + 1))

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        ib = model.new(RES)
        w.u64(_dx(0x10), model.ctx if rr.random() < 0.7 else model.new("ID3D11DeviceContext"))
        state_ib = w.alloc(struct.pack("<iiQQ", used, total, ib, 0))
        w.u64(va("gfxBuf") + 0x20, state_ib)
        s = _new_state(model)
        _put(s, 0x8, "Q", ib if rr.random() < 0.5 else 0)
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), indices or b"\0", tris], "setup": setup}


def _maybe(r, p, value, other=0):
    return value if r.random() < p else other


# ---- constant buffers ----------------------------------------------------------------------------------------------

def _pass_bytes(r, hull=None, domain=None, ps=0, vs=0, decl=0, args=0):
    """A MaterialPass (0x48 bytes)."""
    p = bytearray(0x48)
    hull = hull if hull is not None else _maybe(r, 0.3, 0x4000)
    domain = domain if domain is not None else _maybe(r, 0.3, 0x5000)
    _put(p, 0, "QQQQQ", vs, decl, hull, domain, ps)
    p[0x28] = r.getrandbits(8)
    p[0x29:0x2C] = bytes(r.choice((0, 0, 1, 3, 10)) for _ in range(3))
    _put(p, 0x2C, "HHH", *(r.choice((0, 0x10, 0x100, 0x580, r.randrange(0x581) & ~0xF)) for _ in range(3)))
    p[0x32] = r.randrange(4)                       # zone
    p[0x33:0x36] = bytes(r.randrange(8) for _ in range(3))
    _put(p, 0x38, "I", r.choice((0, 0x2000, r.getrandbits(32))))
    _put(p, 0x40, "Q", args)
    return p


def _constant_tables(w, model, zone_count=4):
    """dx.constantBufferTables[3][zone]: 8 buffers each, all model objects."""
    tables = {}
    for slot in range(3):
        for zone in range(zone_count):
            objs = _objects(model, RES, 8)
            w.u64(_dx(0x430) + 8 * (81 * slot + zone), w.alloc(struct.pack("<8Q", *objs)))
            tables[(slot, zone)] = objs
    return tables


def _stable_buffer_input(r, seed):
    p = _pass_bytes(r)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        tables = _constant_tables(w, model)
        s = _new_state(model)
        pool = tables[(2, p[0x32])] + [0]
        _put(s, 0xF00, "QQ", rr.choice(pool), rr.choice(pool))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va(), bytes(p)], "setup": setup}


# ---- R_SetupPass*Args ------------------------------------------------------------------------------------------------

def _walker_fake(name, shadow_offset):
    def fn(mu):
        ctx = mu.reg_read(UC_X86_REG_RCX)
        source, state = struct.unpack("<QQ", bytes(mu.mem_read(ctx, 16)))
        args, count = mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF
        _rec(name, source, state, args, count)
        r = M["walker_rng"]
        mu.mem_write(state + shadow_offset, bytes(r.getrandbits(8) for _ in range(0x580)))
        mu.reg_write(UC_X86_REG_RAX, 1 if r.random() < 0.5 else 0)  # a bool: 0 or 1
    return fn


def _setup_args_input(r, seed):
    p = _pass_bytes(r, args=0x9000)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        _samplers(w, model)
        tables = _constant_tables(w, model)
        textures = _textures(w, rr, model)
        pass_va = w.alloc(bytes(p))
        s = _new_state(model)
        _sampler_bytes(s, rr)
        _dirty_ranges(s, rr)
        _texture_arrays(s, rr, textures, 0.05)
        _put(s, 0x1BA8, "Q", pass_va)
        for off, slot in ((0xEE0, 0), (0xEF0, 1), (0xF00, 2)):
            pool = tables[(slot, p[0x32])] + [0]
            _put(s, off, "QQ", rr.choice(pool), rr.choice(pool))
        w.write(_state_va(), bytes(s))
        M["walker_rng"] = random.Random(seed + 7)
    context = struct.pack("<QQ", _source_va(), _state_va())
    return {"args": [context], "setup": setup}


# ---- R_SetupPass ----------------------------------------------------------------------------------------------------

def _setup_pass_input(r, seed):
    pass_index = r.randrange(3)
    tech_type = r.randrange(0x19C)

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        ps = _shaders(w, rr, model, 3, "ps")
        hs = [w.alloc(struct.pack("<QQ", 0, model.new(SHADER))) for _ in range(2)]
        ds = [w.alloc(struct.pack("<QQ", 0, model.new(SHADER))) for _ in range(2)]
        zone = rr.randrange(4)
        raster, dss, blend = _state_tables(w, rr, model, zone)
        # technique: name, flags, passCount, 3 passes
        tech = bytearray(0x10 + 3 * 0x48)
        _put(tech, 0xA, "H", 3)
        for i in range(3):
            pb = _pass_bytes(rr, hull=rr.choice(hs + [0, 0]), domain=rr.choice(ds + [0, 0]), ps=rr.choice(ps + [0]))
            tech[0x10 + 0x48 * i:0x58 + 0x48 * i] = pb
        tech_va = w.alloc(bytes(tech))
        # state bits table: 8 entries
        bits = bytearray()
        for _ in range(8):
            sb = bytearray(0x1C)
            _put(sb, 0, "III", *(rr.getrandbits(32) for _ in range(3)))
            sb[0xC] = zone
            sb[0xD:0x18] = bytes(rr.randrange(16) for _ in range(11))
            sb[0x18], sb[0x19] = rr.randrange(16), rr.getrandbits(8)
            bits += sb
        bits_va = w.alloc(bytes(bits))
        cbdefs = bytearray()
        for _ in range(2):
            d = bytearray(0x80)
            _put(d, 0x60, "4Q", *(rr.choice(_objects(model, RES, 2) + [0]) for _ in range(4)))
            cbdefs += d
        cbdefs_va = w.alloc(bytes(cbdefs))
        material = bytearray(0x3A8)
        material[0x28 + tech_type] = rr.randrange(6)
        _put(material, 0x1E8, "Q", bits_va)
        material[0x1F0 + tech_type] = rr.choice((0, 1, 0xFF))
        _put(material, 0x390, "Q", cbdefs_va)
        material[0x398] = rr.choice((0, 1, 2))
        material_va = w.alloc(bytes(material))
        # the hull shader resource: backEndData + 0x150C40 -> an object whose +0x20 is a view
        holder = w.alloc(bytes(0x20) + struct.pack("<Q", model.new(VIEW)))
        field = w.alloc(struct.pack("<Q", holder))
        w.u64(_source_va() + 0x2698, field - 0x150C40)
        w.u32(_source_va() + 0x2CD0, rr.randrange(8))
        w.write(_source_va() + 0x2CFC, bytes([rr.getrandbits(8)]))
        s = _new_state(model)
        _put(s, 0x1B90, "QiI", material_va, tech_type, 0)
        _put(s, 0x1BA0, "Q", tech_va)
        _put(s, 0x2318, "Q", rr.choice(ps + [0]))
        _put(s, 0x2328, "QQ", rr.choice(hs + [0]), rr.choice(ds + [0]))
        _put(s, 0x2308, "III", *(rr.getrandbits(32) for _ in range(3)))
        _put(s, 0x236C, "i", rr.choice((0, 1, 2)))  # a suite: gamma writes need no render targets
        _put(s, 0x2300, "i", rr.randrange(11))
        _put(s, 0xF10, "4Q", *(rr.choice(_objects(model, RES, 2) + [0]) for _ in range(4)))
        w.write(_state_va(), bytes(s))
    context = struct.pack("<QQ", _source_va(), _state_va())
    return {"args": [context, pass_index], "setup": setup}


# ---- R_UpdateVertexDecl ----------------------------------------------------------------------------------------------

def _vertex_decl_input(r, seed):
    decl_type = r.choice((0, 1, 248, r.randrange(249)))

    def setup(w):
        rr = random.Random(seed)
        model = _install(w)
        vs = _shaders(w, rr, model, 3, "vs", null_object=0)
        layouts = _objects(model, "ID3D11InputLayout", 3)
        decl = bytearray(0x838)
        for i in range(249):
            if rr.random() < 0.8:
                _put(decl, 0x70 + 8 * i, "Q", rr.choice(layouts))
        decl_va = w.alloc(bytes(decl)) if rr.random() < 0.8 else 0
        pass_va = w.alloc(struct.pack("<QQ", rr.choice(vs), decl_va) + bytes(0x38))
        material_va = w.alloc(struct.pack("<Q", w.cstr("some/material")))
        s = _new_state(model)
        _put(s, 0x10, "i", decl_type)
        _put(s, 0x50, "Q", rr.choice(layouts + [0]))
        _put(s, 0x1B90, "Q", material_va)
        _put(s, 0x1BA8, "Q", pass_va)
        _put(s, 0x2320, "Q", rr.choice(vs + [0]))
        w.write(_state_va(), bytes(s))
    return {"args": [_state_va()], "setup": setup}


def _com_error(mu):
    """Com_Error(code, fmt, vertDeclType, vertex shader name, material name): logged, then returns (as the faked
    error does in both builds), so what follows the error is compared too."""
    m = M["m"]
    rsp = mu.reg_read(UC_X86_REG_RSP)
    material_name = struct.unpack("<Q", bytes(mu.mem_read(rsp + 0x28, 8)))[0]
    _rec("Com_Error", mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, m.read_cstr(mu.reg_read(UC_X86_REG_RDX)),
         mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF, m.read_cstr(mu.reg_read(UC_X86_REG_R9)), m.read_cstr(material_name))


# ---- cases ----------------------------------------------------------------------------------------------------------

def _inputs(fn, seed, n):
    r = random.Random(seed)
    return [fn(r, seed * 1000 + i) for i in range(n)]


def _case(symbol, ret, inputs, **extra):
    return {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs, **extra}


WALKERS = {
    "prim": ("?R_SetPassShaderPrimArguments@@YA_NUGfxCmdBufContext@@PEIBUMaterialShaderArgument@@I@Z", 0x60),
    "object": ("?R_SetPassShaderObjectArguments@@YA_NUGfxCmdBufContext@@PEIBUMaterialShaderArgument@@I@Z", 0x560),
    "stable": ("?R_SetPassShaderStableArguments@@YA_NUGfxCmdBufContext@@PEIBUMaterialShaderArgument@@I@Z", 0x960),
}


def _walker_fakes(kind):
    sym, shadow = WALKERS[kind]
    return {sym: _walker_fake(kind, shadow)}


COM_ERROR = "?Com_Error@@YAXW4errorParm_t@@PEBDZZ"

CASES = [
    _case("?R_SetHullAndDomainShaders@@YAXPEAUGfxCmdBufState@@PEBUMaterialHullShader@@PEBUMaterialDomainShader@@@Z",
          "void", _inputs(_hs_ds_input, 31, 150)),
    _case("?R_SetIndexData@@YAHPEAUGfxCmdBufPrimState@@PEBGH@Z", "int", _inputs(_index_data_input, 32, 150)),
    _case("?R_SetPixelShader@@YAXPEAUGfxCmdBufState@@PEBUMaterialPixelShader@@@Z", "void",
          _inputs(_single_shader_input(0x2318, True), 33, 80)),
    _case("?R_SetVertexShader@@YAXPEAUGfxCmdBufState@@PEBUMaterialVertexShader@@@Z", "void",
          _inputs(_single_shader_input(0x2320, False), 34, 80)),
    _case("?R_SetStableConstantBuffer@@YA_NPEAUGfxCmdBufState@@PEBUMaterialPass@@@Z", "char",
          _inputs(_stable_buffer_input, 35, 200)),
    _case("?R_SetupPass@@YAXUGfxCmdBufContext@@I@Z", "void", _inputs(_setup_pass_input, 36, 300)),
    *[_case(f"?{name}@@YAXUGfxCmdBufContext@@@Z", "void", _inputs(_setup_args_input, seed, 200),
            fakes=_walker_fakes(kind))
      for name, kind, seed in (("sub_14065D5A0", "stable", 37), ("sub_14065DA20", "stable", 38),
                               ("sub_14065DB20", "stable", 39), ("R_SetupPassPerObjectArgs", "object", 40),
                               ("R_SetupPassPerPrimArgs", "prim", 41))],
    _case("?R_UpdateVertexDecl@@YAXPEAUGfxCmdBufState@@@Z", "void", _inputs(_vertex_decl_input, 42, 200),
          fakes={COM_ERROR: _com_error}),
]
