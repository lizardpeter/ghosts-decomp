"""Differential cases for the Store build's material, technique set, shader and vertex declaration loaders
(gfx_d3d/r_material_load_db.cpp) and Load_InitMaterialConstantBuffer (gfx_d3d/r_material.cpp).

The loaders are checked on their own, without the fastfile pipeline: the stream functions they call are logged
fakes (both runs reach the same Python), fed by a synthetic stream (tools/fastfile/material_synth.py) that exercises
every pointer form:

- Load_Stream(atStreamStart, ptr, size) copies the next `size` stream bytes to ptr and advances g_streamPos when
  atStreamStart (blocks are not modelled: DB_PushStreamPos/DB_PopStreamPos only log);
- Load_XStringCustom copies the next NUL-terminated string to *str and advances g_streamPos;
- DB_ConvertOffsetToPointer / DB_ConvertOffsetToAlias log the field and its value and replace it with a marked value;
- DB_InsertPointer hands out slots at the end of the buffer (now and then NULL);
- the Load_<Type>Asset registrations, the shader and constant buffer creators, Load_MaterialVertexStreamRouting,
  Load_GfxImagePtr, Load_PicmipWater and Load_XStringArray log their arguments (the asset ones also mark the
  pointer, so what a caller copies afterwards is checked).

Everything the loaders write lands in one buffer (the call's last argument, read back and compared), the var*
globals and g_streamPos are compared as globals, and every logged call with its arguments must match.
"""
import random
import struct
import sys
from pathlib import Path

from harness import HEAP, HEAP_SIZE, ROOT
from syms import va
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX

sys.path.insert(0, str(ROOT / "tools" / "fastfile"))
import material_synth as ms  # noqa: E402

STORE = "iw6mp64_MSStore_ship"
BUF = HEAP                 # the first bytes argument: all loaded memory
BUF_SIZE = 0x20000
INSERT_SLOTS = BUF + BUF_SIZE - 0x1000
SCRATCH_PASS = BUF + BUF_SIZE - 0x2000  # a zeroed MaterialPass for vertex declarations loaded on their own
M = {}
MASK = 2 ** 64 - 1


def _rec(*entry):
    M["m"].observed.append(entry)


def _u64(mu, a):
    return struct.unpack("<Q", bytes(mu.mem_read(a, 8)))[0]


def _write(mu, a, data):
    """Write for the program: journaled in an image, clipped to the buffer otherwise."""
    m = M["m"]
    for img in m.images:
        if img.base <= a < img.base + img.size:
            m._emulated_write(a, data)
            return
    if HEAP <= a < HEAP + HEAP_SIZE:
        mu.mem_write(a, bytes(data[:HEAP + HEAP_SIZE - a]))
        return
    _rec("unmapped write", a, len(data))


def _advance(mu, n):
    pos = va("g_streamPos")
    _write(mu, pos, struct.pack("<Q", (_u64(mu, pos) + n) & MASK))


# ---- stream fakes -------------------------------------------------------------------------------------------------

def _load_stream(mu):
    flag, ptr, size = mu.reg_read(UC_X86_REG_RCX) & 0xFF, mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    _rec("Load_Stream", flag, ptr, size)
    if flag and size:
        src, cur = M["src"], M["cur"]
        n = min(size, BUF_SIZE)
        data = src[cur:cur + n]
        data += bytes(n - len(data))
        M["cur"] = cur + n
        _write(mu, ptr, data)
        _advance(mu, size)


def _xstring(mu):
    field = mu.reg_read(UC_X86_REG_RCX)
    start = _u64(mu, field)
    src, cur = M["src"], M["cur"]
    end = src.find(b"\0", cur)
    text = (src[cur:] + b"\0") if end < 0 else src[cur:end + 1]
    M["cur"] = cur + len(text)
    _rec("Load_XStringCustom", field, start, bytes(text))
    _write(mu, start, text)
    _advance(mu, len(text))


def _convert(name, mark):
    def fn(mu):
        field = mu.reg_read(UC_X86_REG_RCX)
        v = _u64(mu, field)
        _rec(name, field, v)
        _write(mu, field, struct.pack("<Q", mark | (v & 0xFFFFFFFFF)))
    return fn


def _insert(mu):
    n = M["inserts"]
    M["inserts"] = n + 1
    slot = 0 if n in M["null_inserts"] else INSERT_SLOTS + 8 * n
    _rec("DB_InsertPointer", slot)
    mu.reg_write(UC_X86_REG_RAX, slot)


def _logger(name, regs="q"):
    def fn(mu):
        vals = [mu.reg_read(r) & (0xFF if k == "b" else (0xFFFFFFFF if k == "i" else MASK))
                for r, k in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8), regs)]
        _rec(name, *vals)
    return fn


def _asset(name, asset_type):
    def fn(mu):
        field = mu.reg_read(UC_X86_REG_RCX)
        v = _u64(mu, field)
        _rec(name, field, v)
        _write(mu, field, struct.pack("<Q", (0x7200000000000000 | asset_type << 48 | (v & 0xFFFFFFFFFFF)) & MASK))
    return fn


def _create_shader(name):
    def fn(mu):
        data, shader = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
        _rec(name, data, _u64(mu, data), shader)
    return fn


STREAM_FAKES = {
    "?Load_Stream@@YAX_NPEAX_K@Z": _load_stream,
    "?DB_PushStreamPos@@YAXI@Z": _logger("DB_PushStreamPos", "i"),
    "?DB_PopStreamPos@@YAXXZ": _logger("DB_PopStreamPos", ""),
    "?DB_ConvertOffsetToPointer@@YAXPEA_K@Z": _convert("DB_ConvertOffsetToPointer", 0x7000000000000000),
    "?DB_ConvertOffsetToAlias@@YAXPEA_K@Z": _convert("DB_ConvertOffsetToAlias", 0x7100000000000000),
    "?DB_InsertPointer@@YAPEAEXZ": _insert,
    "?Load_XStringCustom@@YAXPEAPEBD@Z": _xstring,
    "?Load_XStringArray@@YAX_N_K@Z": _logger("Load_XStringArray", "bq"),
    "?Load_GfxImagePtr@@YAX_N@Z": _logger("Load_GfxImagePtr", "b"),
    "?Load_PicmipWater@@YAXPEAPEAUwater_t@@@Z": _logger("Load_PicmipWater", "q"),
    "?Load_MaterialAsset@@YAXPEAPEAUMaterial@@@Z": _asset("Load_MaterialAsset", 5),
    "?Load_MaterialVertexShaderAsset@@YAXPEAPEAUMaterialVertexShader@@@Z": _asset("Load_MaterialVertexShaderAsset", 7),
    "?Load_MaterialHullShaderAsset@@YAXPEAPEAUMaterialHullShader@@@Z": _asset("Load_MaterialHullShaderAsset", 8),
    "?Load_MaterialDomainShaderAsset@@YAXPEAPEAUMaterialDomainShader@@@Z": _asset("Load_MaterialDomainShaderAsset", 9),
    "?Load_MaterialPixelShaderAsset@@YAXPEAPEAUMaterialPixelShader@@@Z": _asset("Load_MaterialPixelShaderAsset", 10),
    "?Load_MaterialVertexDeclAsset@@YAXPEAPEAUMaterialVertexDeclaration@@@Z":
        _asset("Load_MaterialVertexDeclAsset", 11),
    "?Load_MaterialTechniqueSetAsset@@YAXPEAPEAUMaterialTechniqueSet@@@Z": _asset("Load_MaterialTechniqueSetAsset", 12),
    "?Load_CreateMaterialVertexShader@@YAXPEAPEAEPEAUMaterialVertexShader@@@Z": _create_shader("CreateVS"),
    "?Load_CreateMaterialPixelShader@@YAXPEAPEAEPEAUMaterialPixelShader@@@Z": _create_shader("CreatePS"),
    "?Load_CreateMaterialHullShader@@YAXPEAPEAEPEAUMaterialHullShader@@@Z": _create_shader("CreateHS"),
    "?Load_CreateMaterialDomainShader@@YAXPEAPEAEPEAUMaterialDomainShader@@@Z": _create_shader("CreateDS"),
    "?Load_MaterialVertexStreamRouting@@YAXPEAUMaterialVertexStreamRouting@@IPEAUMaterialVertexShader@@@Z":
        _logger("Load_MaterialVertexStreamRouting", "qiq"),
    "?Load_InitMaterialConstantBuffer@@YAXPEAEPEAUMaterial@@@Z": _logger("Load_InitMaterialConstantBuffer", "qq"),
}


# ---- inputs -------------------------------------------------------------------------------------------------------

def _input(r, at_start, build, var, extra_args=(), extra_setup=None):
    """build(gen) writes the object's stream and returns its header; `var` is the var global the loader starts
    from. At the stream start the header is read from the stream; otherwise it is already in memory at var."""
    g = ms.Gen(r)
    header = build(g)
    src = bytes(g.out)
    obj_off = 0x100 + r.randrange(16)
    pos_off = obj_off if at_start else 0x8000 + r.randrange(16)
    if not at_start:
        src = src[len(header):]
    buf = bytearray(BUF_SIZE)
    if not at_start:
        buf[obj_off:obj_off + len(header)] = header
    zone = r.randrange(256)
    null_inserts = {i for i in range(64) if r.random() < 0.2}

    def setup(w):
        M.update(m=w.m, src=src, cur=0, inserts=0, null_inserts=null_inserts)
        w.u64(va("g_streamPos"), BUF + pos_off)
        w.u64(va(var), BUF + obj_off)
        w.write(0x145CBB1A8, bytes([zone]))  # g_zoneIndex (byte read by 140372140)
        w.u64(va("varMaterialPass"), SCRATCH_PASS)
        if extra_setup:
            extra_setup(w, r)
    return {"args": [int(at_start), *extra_args, bytes(buf)], "setup": setup}


def _inputs(seed, n, make):
    r = random.Random(seed)
    return [make(r, i % 2 == 0) for i in range(n)]


def _case(sym, inputs, fakes=None, **kw):
    return {"symbol": sym, "build": STORE, "ret": "void", "inputs": inputs, "fakes": {**STREAM_FAKES, **(fakes or {})},
            **kw}


def _header_only(size, tail=None):
    def build(g):
        h = g.raw(size)
        if tail:
            tail(g, h)
        g.out += h
        return h
    return build


def _ptr_build(emit_name):
    """Load_<Type>Ptr: an 8-byte pointer, then the asset when inline."""
    def build(g):
        v, e = g.asset_ptr(getattr(g, emit_name))
        g.out += v
        e()
        return v
    return build


def _handle_array_input(r, at_start):
    count = r.randrange(4)

    def build(g):
        ptrs, emits = bytearray(), []
        for _ in range(count):
            v, e = g.asset_ptr(g.material)
            ptrs += v
            emits.append(e)
        g.out += ptrs
        for e in emits:
            e()
        return ptrs
    return _input(r, at_start, build, "varMaterialHandle", (count,))


def _cb_array_input(r, at_start):
    count = r.randrange(4)

    def build(g):
        return g.constant_buffer_defs(count)
    return _input(r, at_start, build, "varMaterialConstantBufferDef", (count,))


def _pass_array_input(r, at_start):
    count = r.randrange(3)

    def build(g):
        return g.passes(count)
    return _input(r, at_start, build, "varMaterialPass", (count,))


def _info_input(r, at_start):
    def build(g):
        h = g.raw(0x28)
        tail = g.xstring(h, 0, "mtl")
        g.out += h
        tail()
        return h
    return _input(r, at_start, build, "varMaterialInfo")


def _texdefinfo_input(r, at_start):
    """Load_MaterialTextureDefInfo loads the u of the def at varMaterialTextureDef (only its semantic is read): a
    water map's water_t from the stream, any other semantic through Load_GfxImagePtr (faked)."""
    water = r.random() < 0.7
    def_off = 0x40

    def build(g):
        form, v = g.ptr()
        info = struct.pack("<Q", v)
        g.out += info
        if form == "follow":
            g.water()
        return info

    def extra(w, r2):
        w.u64(va("varMaterialTextureDef"), BUF + def_off)
    inp = _input(r, False, build, "varMaterialTextureDefInfo", extra_setup=extra)
    buf = bytearray(inp["args"][-1])
    d = bytearray(r.getrandbits(8) for _ in range(8))
    d[7] = ms.TS_WATER_MAP if water else r.choice([x for x in range(256) if x != ms.TS_WATER_MAP])
    buf[def_off:def_off + 8] = d
    inp["args"] = [int(at_start), bytes(buf)]
    return inp


def _shader_obj_input(kind, var, ptr=False):
    def make(r, at_start):
        build = _ptr_build(kind) if ptr else (lambda g: getattr(g, kind)())
        return _input(r, at_start, build, var)
    return make


def _loaddef_input(size, shader_var):
    def make(r, at_start):
        def build(g):
            h = g.raw(size)
            form, v = g.ptr()
            h[0:8] = struct.pack("<Q", v)
            n = r.randrange(0, 0x60)
            h[8:12] = struct.pack("<I", n)
            g.out += h
            if form == "follow":
                g.out += g.raw(n)
            return h

        def extra(w, r2):
            w.u64(va(shader_var), BUF + 0x20)
        return _input(r, at_start, build, "varGfx" + shader_var[len("varMaterial"):] + "LoadDef", extra_setup=extra)
    return make


def _technique_input(r, at_start):
    return _input(r, True, lambda g: g.technique(), "varMaterialTechnique")


SHADERS = (("VertexShader", "vertex_shader", 0x18), ("PixelShader", "pixel_shader", 0x18),
           ("HullShader", "hull_shader", 0x10), ("DomainShader", "domain_shader", 0x10))

CASES = [
    _case("?Load_MaterialInfo@@YAX_N@Z", _inputs(0x1001, 40, _info_input)),
    _case("?Load_Material@@YAX_N@Z", _inputs(0x1002, 60, lambda r, s: _input(r, s, lambda g: g.material(),
                                                                             "varMaterial"))),
    _case("?Load_MaterialHandle@@YAX_N@Z", _inputs(0x1003, 40, lambda r, s: _input(r, s, _ptr_build("material"),
                                                                                   "varMaterialHandle"))),
    _case("?Load_MaterialHandleArray@@YAX_N_K@Z", _inputs(0x1004, 30, _handle_array_input)),
    _case("?Load_MaterialTextureDefInfo@@YAX_N@Z", _inputs(0x1005, 60, _texdefinfo_input)),
    _case("?Load_GfxStateBits@@YAX_N@Z", _inputs(0x1006, 30, lambda r, s: _input(r, s, _header_only(0x1C),
                                                                                 "varGfxStateBits"))),
    _case("?Load_MaterialConstantBufferDefArray@@YAX_N_K@Z", _inputs(0x1007, 40, _cb_array_input)),
    _case("?Load_MaterialTechniqueSet@@YAX_N@Z", _inputs(0x1008, 30, lambda r, s: _input(r, s, lambda g: g.techset(),
                                                                                         "varMaterialTechniqueSet"))),
    _case("?Load_MaterialTechniqueSetPtr@@YAX_N@Z", _inputs(0x1009, 30, lambda r, s: _input(
        r, s, _ptr_build("techset"), "varMaterialTechniqueSetPtr"))),
    # the only caller passes true, and the Store build's code reads the header unconditionally
    _case("?Load_MaterialTechnique@@YAX_N@Z", _inputs(0x100A, 40, _technique_input)),
    _case("?Load_MaterialPassArray@@YAX_N_K@Z", _inputs(0x100B, 50, _pass_array_input)),
    _case("?Load_MaterialVertexDeclaration@@YAX_N@Z", _inputs(0x100C, 30, _shader_obj_input(
        "vertex_decl", "varMaterialVertexDeclaration"))),
    _case("?Load_MaterialVertexDeclarationPtr@@YAX_N@Z", _inputs(0x100D, 30, _shader_obj_input(
        "vertex_decl", "varMaterialVertexDeclarationPtr", True))),
    _case("?Load_water_t@@YAX_N@Z", _inputs(0x100E, 40, lambda r, s: _input(r, s, lambda g: g.water(), "varwater_t"))),
    *[_case(f"?Load_Material{name}@@YAX_N@Z", _inputs(0x1010 + i, 40, _shader_obj_input(gen, f"varMaterial{name}")))
      for i, (name, gen, _) in enumerate(SHADERS)],
    *[_case(f"?Load_Material{name}Ptr@@YAX_N@Z", _inputs(0x1020 + i, 40, _shader_obj_input(
        gen, f"varMaterial{name}Ptr", True))) for i, (name, gen, _) in enumerate(SHADERS)],
    *[_case(f"?Load_Gfx{name}LoadDef@@YAX_N@Z", _inputs(0x1030 + i, 40, _loaddef_input(size, f"varMaterial{name}")))
      for i, (name, _, size) in enumerate(SHADERS)],
]


# ---- Load_InitMaterialConstantBuffer ------------------------------------------------------------------------------

def _create_buffer(mu):
    desc, data, out = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    d = struct.unpack("<6I", bytes(mu.mem_read(desc, 24)))
    s = struct.unpack("<QII", bytes(mu.mem_read(data, 16)))
    n = M["buffers"]
    M["buffers"] = n + 1
    _rec("R_CreateBufferInternal", d, s, out)
    _write(mu, out, struct.pack("<Q", 0xB0000000 + n))
    mu.reg_write(UC_X86_REG_RAX, M["results"][n % len(M["results"])])


def _init_cb_input(r, _):
    blob = bytearray(r.getrandbits(8) for _ in range(0x1000))
    count = r.randrange(0, 6)
    blob[0x398] = count
    table = 0x400 + r.randrange(0, 8) * 8
    blob[0x390:0x398] = struct.pack("<Q", BUF + table)
    for i in range(count):
        d = table + 0x80 * i
        sizes = [r.choice((0, 0, r.getrandbits(32), r.randrange(1, 0x400))) for _ in range(4)]
        blob[d:d + 16] = struct.pack("<4I", *sizes)
    results = [r.choice((0, 0, 1, 0x80070057)) for _ in range(8)]

    def setup(w):
        M.update(m=w.m, buffers=0, results=results)
    return {"args": [BUF + 0x398, bytes(blob)], "setup": setup}


CASES.append({"symbol": "?Load_InitMaterialConstantBuffer@@YAXPEAEPEAUMaterial@@@Z", "build": STORE, "ret": "void",
              "inputs": [_init_cb_input(random.Random(0x1100 + i), None) for i in range(40)],
              "fakes": {"?R_CreateBufferInternal@@YAJPEBUD3D11_BUFFER_DESC@@PEBUD3D11_SUBRESOURCE_DATA@@PEAPEAU"
                        "ID3D11Buffer@@@Z": _create_buffer}})
