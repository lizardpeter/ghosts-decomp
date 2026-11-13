"""Materials, technique sets, shaders and vertex declarations from a decompressed zone (Store build).

Two layers, like the game:

1. Loaders (load_material, load_techset, ...) do what the Store build's Load_* functions do
   (src/gfx_d3d/r_material_load_db.cpp, docs/assets/materials.md), step for step, on a zone stream object: the
   fastfile pipeline's Stream (tools/fastfile/iw6ff.py: load, align, push, pop, insert_pointer, offset_to_pointer,
   offset_to_alias, xstring_ptr, link, read/u64/put_u64), so the memory they leave behind is laid out as the game's.
   `at` is the address of the object being loaded, which the caller has aligned and allocated, as the generated
   code's var<Type> globals are set before each call.
2. Readers (read_material, read_techset, ...) turn that memory into plain Python objects (dicts and lists),
   following pointers. Converters (material_json, techset_json, export_shaders) produce JSON and .dxbc files.

What the loaders do not do: create D3D objects (shaders, input layouts, constant buffers: Load_Create*,
Load_MaterialVertexStreamRouting and Load_InitMaterialConstantBuffer have no effect on the zone memory a decoder
reads) and load images: an image pointer is handed to HOOKS["image_ptr"] (the image loader's Load_GfxImagePtr), which
by default resolves offsets and refuses inline images.
"""
import hashlib
import struct

try:
    from . import material_tables as T  # noqa: F401
    from . import dxbc
except ImportError:  # run as a script from tools/fastfile
    import material_tables as T
    import dxbc

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
PTR_INSERT = 0xFDFDFDFFFFFFFFFE
BLOCK_TEMP, BLOCK_VIRTUAL = 0, 3

ASSET_TYPE_MATERIAL, ASSET_TYPE_VERTEXSHADER, ASSET_TYPE_HULLSHADER = 5, 7, 8
ASSET_TYPE_DOMAINSHADER, ASSET_TYPE_PIXELSHADER, ASSET_TYPE_VERTEXDECL, ASSET_TYPE_TECHNIQUE_SET = 9, 10, 11, 12
ASSET_TYPE_IMAGE = 13
# DB_GetXAssetTypeSize for the types here (what Load_<Type>Asset copies into the pool)
ASSET_SIZES = {ASSET_TYPE_MATERIAL: 0x3A8, ASSET_TYPE_VERTEXSHADER: 0x28, ASSET_TYPE_HULLSHADER: 0x20,
               ASSET_TYPE_DOMAINSHADER: 0x20, ASSET_TYPE_PIXELSHADER: 0x28, ASSET_TYPE_VERTEXDECL: 0x838,
               ASSET_TYPE_TECHNIQUE_SET: 0xCF0}
TECHNIQUE_COUNT = 0x19C
TS_WATER_MAP = 0xB
MTL_ARG_LITERAL_CONST = 4


def _i32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _default_image_ptr(s, field):
    """Load_GfxImagePtr for images this module doesn't load: NULL stays, an offset is an alias."""
    s.push(BLOCK_TEMP)
    v = s.u64(field)
    if v in (PTR_INLINE, PTR_INSERT):
        s.pop()
        raise NotImplementedError("inline image: register the image loader in material.HOOKS['image_ptr']")
    if v:
        s.put_u64(field, s.offset_to_alias(v))
    s.pop()


def _default_xstring_array(s, at, count):
    """Load_XStringArray (14035E9C0): count pointers, each an XString."""
    s.load(True, at, 8 * count)
    for i in range(count):
        s.xstring_ptr(at + 8 * i)


HOOKS = {"image_ptr": _default_image_ptr, "xstring_array": _default_xstring_array}


def _inline_or_offset(s, field, align):
    """The generated rule for a non-asset pointer: NULL, inline (aligned, returns the address) or an offset."""
    v = s.u64(field)
    if not v:
        return None
    if v == PTR_INLINE:
        at = s.align(align)
        s.put_u64(field, at)
        return at
    s.put_u64(field, s.offset_to_pointer(v))
    return None


def _nonnull_inline(s, field, align):
    """Members the generator treats as always inline: any non-NULL value."""
    if not s.u64(field):
        return None
    at = s.align(align)
    s.put_u64(field, at)
    return at


def asset_ptr(asset_type, loader):
    """Load_<Type>Ptr: in the temp block, NULL stays, an offset aliases an earlier asset, -1/-2 load the asset
    inline (aligned to 4), -2 also reserving an alias slot that receives the registered pointer."""
    def load(s, field):
        s.push(BLOCK_TEMP)
        v = s.u64(field)
        if v:
            if v not in (PTR_INLINE, PTR_INSERT):
                s.put_u64(field, s.offset_to_alias(v))
            else:
                h = s.align(4)
                s.put_u64(field, h)
                slot = s.insert_pointer() if v == PTR_INSERT else None
                loader(s, h, True)
                s.put_u64(field, s.link(asset_type, h))
                if slot:
                    s.put_u64(slot, s.u64(field))
        s.pop()
    return load


# ---- loaders (Store build Load_*) ---------------------------------------------------------------------------------

def load_material_info(s, at, at_stream_start=True):
    """Load_MaterialInfo (140353AD0)."""
    s.load(at_stream_start, at, 0x28)
    s.xstring_ptr(at)


def load_gfx_state_bits(s, at, at_stream_start=False):
    """Load_GfxStateBits (14034FCE0): nothing to fix up; the zone byte (+0xC) becomes the loading zone's index,
    which a decoder has no use for."""
    s.load(at_stream_start, at, 0x1C)


def load_water(s, at, at_stream_start=True):
    """Load_water_t (1403624D0)."""
    s.load(at_stream_start, at, 0x58)
    m, n = struct.unpack("<ii", s.read(at + 0x20, 8))
    for field in (at + 8, at + 0x10, at + 0x18):
        p = _nonnull_inline(s, field, 4)
        if p is not None:
            s.load(True, p, (_i32(n * m) * 4) & (2 ** 64 - 1))
    HOOKS["image_ptr"](s, at + 0x48)
    HOOKS["image_ptr"](s, at + 0x50)


def load_texture_def_info(s, def_at):
    """Load_MaterialTextureDefInfo (140354220) for the def at def_at."""
    if s.read(def_at + 7, 1)[0] != TS_WATER_MAP:
        HOOKS["image_ptr"](s, def_at + 8)
        return
    p = _inline_or_offset(s, def_at + 8, 4)
    if p is not None:
        load_water(s, p, True)


def load_constant_buffer_defs(s, at, count, at_stream_start=True):
    """Load_MaterialConstantBufferDefArray (1403532A0)."""
    s.load(at_stream_start, at, count * 0x80)
    for i in range(count):
        d = at + 0x80 * i
        sizes = struct.unpack("<8I", s.read(d, 32))
        for k in range(4):
            p = _nonnull_inline(s, d + 0x20 + 8 * k, 16)
            if p is not None:
                s.load(True, p, sizes[k])
        for k in range(4):
            p = _nonnull_inline(s, d + 0x40 + 8 * k, 2)
            if p is not None:
                s.load(True, p, sizes[4 + k] * 2)


def load_material(s, at, at_stream_start=True):
    """Load_Material (140352F90)."""
    s.load(at_stream_start, at, 0x3A8)
    s.push(BLOCK_VIRTUAL)
    load_material_info(s, at, False)
    load_techset_ptr(s, at + 0x1D0)
    texture_count, constant_count, state_bits_count = s.read(at + 0x1C4, 3)
    p = _inline_or_offset(s, at + 0x1D8, 4)
    if p is not None:
        s.load(True, p, 16 * texture_count)
        for i in range(texture_count):
            load_texture_def_info(s, p + 16 * i)
    p = _inline_or_offset(s, at + 0x1E0, 16)
    if p is not None:
        s.load(True, p, 32 * constant_count)
    p = _inline_or_offset(s, at + 0x1E8, 4)
    if p is not None:
        s.load(True, p, 0x1C * state_bits_count)
    cb_count = s.read(at + 0x398, 1)[0]
    p = _inline_or_offset(s, at + 0x390, 4)
    if p is not None:
        load_constant_buffer_defs(s, p, cb_count, True)
    p = _nonnull_inline(s, at + 0x3A0, 8)
    if p is not None:
        HOOKS["xstring_array"](s, p, s.read(at + 0x1CA, 1)[0])
    s.pop()


def _load_shader(size):
    def load(s, at, at_stream_start=True):
        """Load_Material<Stage>Shader and Load_Gfx<Stage>ShaderLoadDef (Store 140354490 and the others)."""
        s.load(at_stream_start, at, size)
        s.push(BLOCK_VIRTUAL)
        s.xstring_ptr(at)
        loaddef = at + 0x10
        p = _inline_or_offset(s, loaddef, 4)
        if p is not None:
            s.load(True, p, struct.unpack("<i", s.read(loaddef + 8, 4))[0] & (2 ** 64 - 1))
        s.pop()
    return load


load_vertex_shader = _load_shader(0x28)
load_pixel_shader = _load_shader(0x28)
load_hull_shader = _load_shader(0x20)
load_domain_shader = _load_shader(0x20)


def load_vertex_decl(s, at, at_stream_start=True):
    """Load_MaterialVertexDeclaration (1403542D0); the input layouts it builds are not part of the zone."""
    s.load(at_stream_start, at, 0x838)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    s.pop()


load_vertex_shader_ptr = asset_ptr(ASSET_TYPE_VERTEXSHADER, load_vertex_shader)
load_pixel_shader_ptr = asset_ptr(ASSET_TYPE_PIXELSHADER, load_pixel_shader)
load_hull_shader_ptr = asset_ptr(ASSET_TYPE_HULLSHADER, load_hull_shader)
load_domain_shader_ptr = asset_ptr(ASSET_TYPE_DOMAINSHADER, load_domain_shader)
load_vertex_decl_ptr = asset_ptr(ASSET_TYPE_VERTEXDECL, load_vertex_decl)


def load_pass_array(s, at, count, at_stream_start=True):
    """Load_MaterialPassArray (140353B50)."""
    s.load(at_stream_start, at, count * 0x48)
    for i in range(count):
        p = at + 0x48 * i
        load_vertex_shader_ptr(s, p)
        load_vertex_decl_ptr(s, p + 8)
        load_hull_shader_ptr(s, p + 0x10)
        load_domain_shader_ptr(s, p + 0x18)
        load_pixel_shader_ptr(s, p + 0x20)
        args = _nonnull_inline(s, p + 0x40, 4)
        if args is None:
            continue
        n = sum(s.read(p + 0x29, 3))
        s.load(True, args, 16 * n)
        for k in range(n):
            a = args + 16 * k
            if s.read(a, 1)[0] == MTL_ARG_LITERAL_CONST:
                lit = _inline_or_offset(s, a + 8, 4)
                if lit is not None:
                    s.load(True, lit, 16)


def load_technique(s, at, at_stream_start=True):
    """Load_MaterialTechnique (140353F50): the header, the passes, then the name."""
    s.load(at_stream_start, at, 0x10)
    load_pass_array(s, at + 0x10, struct.unpack("<H", s.read(at + 0xA, 2))[0], True)
    s.xstring_ptr(at)


def load_techset(s, at, at_stream_start=True):
    """Load_MaterialTechniqueSet (140353FF0)."""
    s.load(at_stream_start, at, 0xCF0)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    for i in range(TECHNIQUE_COUNT):
        p = _inline_or_offset(s, at + 0x10 + 8 * i, 4)
        if p is not None:
            load_technique(s, p, True)
    s.pop()


load_techset_ptr = asset_ptr(ASSET_TYPE_TECHNIQUE_SET, load_techset)
load_material_ptr = asset_ptr(ASSET_TYPE_MATERIAL, load_material)

# Load_XAsset's per-type header loaders, for the pipeline's dispatch: type -> loader(s, at, at_stream_start)
ASSET_LOADERS = {ASSET_TYPE_MATERIAL: load_material, ASSET_TYPE_VERTEXSHADER: load_vertex_shader,
                 ASSET_TYPE_HULLSHADER: load_hull_shader, ASSET_TYPE_DOMAINSHADER: load_domain_shader,
                 ASSET_TYPE_PIXELSHADER: load_pixel_shader, ASSET_TYPE_VERTEXDECL: load_vertex_decl,
                 ASSET_TYPE_TECHNIQUE_SET: load_techset}


# ---- readers: memory -> plain objects ---------------------------------------------------------------------------

def _u8(s, a):
    return s.read(a, 1)[0]


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _ptr(s, a):
    return s.u64(a)


def _str(s, a):
    p = s.u64(a)
    if not p:
        return None
    try:
        return s.cstr(p).decode("latin1")
    except Exception:
        return f"<unresolved {p:#x}>"


def _readable(s, p):
    try:
        s.read(p, 1)
        return True
    except Exception:
        return False


def read_shader(s, at, stage):
    """A vertex/pixel (0x28) or hull/domain (0x20) shader: name, load def and the DXBC program."""
    p, size, load_for_renderer = _ptr(s, at + 0x10), _u32(s, at + 0x18), _u16(s, at + 0x1C)
    program = s.read(p, size) if p and _readable(s, p) else None
    out = {"name": _str(s, at), "stage": stage, "programSize": size, "loadForRenderer": load_for_renderer,
           "program": program}
    if stage in ("vertex", "pixel"):
        out["microCodeCrc"] = _u32(s, at + 0x20)
    return out


def read_vertex_decl(s, at):
    count = _u8(s, at + 8)
    routing = []
    for i in range(min(count, 31)):
        src, dst, mask = s.read(at + 0x10 + 3 * i, 3)
        routing.append({"source": src, "dest": dst, "mask": mask})
    return {"name": _str(s, at), "streamCount": count, "hasOptionalSource": bool(_u8(s, at + 9)),
            "routing": routing}


def read_args(s, at, count):
    out = []
    for i in range(count):
        a = at + 16 * i
        typ, stage, dest = s.read(a, 1)[0], s.read(a + 1, 1)[0], _u16(s, a + 2)
        u = s.read(a + 8, 8)
        arg = {"type": typ, "shader": stage, "dest": dest}
        if typ == MTL_ARG_LITERAL_CONST:
            p = struct.unpack("<Q", u)[0]
            arg["literal"] = list(struct.unpack("<4f", s.read(p, 16))) if p and _readable(s, p) else None
        elif typ == 0:
            index, first, rows = struct.unpack("<HBB", u[:4])
            arg.update(index=index, firstRow=first, rowCount=rows)
        elif typ in (1, 2):
            arg["codeSampler"] = struct.unpack("<I", u[:4])[0]
        else:
            arg["nameHash"] = struct.unpack("<I", u[:4])[0]
        out.append(arg)
    return out


def read_pass(s, at, cache):
    def shader(field, stage, fn):
        p = _ptr(s, field)
        if not p or not _readable(s, p):
            return None if not p else {"unresolved": p}
        key = (stage, p)
        if key not in cache:
            cache[key] = fn(s, p, stage) if fn is read_shader else fn(s, p)
        return cache[key]
    counts = s.read(at + 0x29, 3)
    args_p = _ptr(s, at + 0x40)
    return {
        "vertexShader": shader(at, "vertex", read_shader),
        "vertexDecl": shader(at + 8, "decl", read_vertex_decl),
        "hullShader": shader(at + 0x10, "hull", read_shader),
        "domainShader": shader(at + 0x18, "domain", read_shader),
        "pixelShader": shader(at + 0x20, "pixel", read_shader),
        "pixelOutputMask": _u8(s, at + 0x28),
        "perPrimArgCount": counts[0], "perObjArgCount": counts[1], "stableArgCount": counts[2],
        "perPrimArgSize": _u16(s, at + 0x2C), "perObjArgSize": _u16(s, at + 0x2E), "stableArgSize": _u16(s, at + 0x30),
        "perPrimConstantBuffer": _u8(s, at + 0x33), "perObjConstantBuffer": _u8(s, at + 0x34),
        "stableConstantBuffer": _u8(s, at + 0x35), "customBufferFlags": _u32(s, at + 0x38),
        "customSamplerFlags": _u8(s, at + 0x3C), "precompiledIndex": _u8(s, at + 0x3D),
        "stageConfig": _u8(s, at + 0x3E),
        "args": read_args(s, args_p, sum(counts)) if args_p and _readable(s, args_p) else [],
    }


def read_technique(s, at, cache):
    count = _u16(s, at + 0xA)
    return {"name": _str(s, at), "flags": _u16(s, at + 8), "passes": [read_pass(s, at + 0x10 + 0x48 * i, cache)
                                                                       for i in range(count)]}


def read_techset(s, at, cache=None):
    cache = {} if cache is None else cache
    techniques = {}
    for i in range(TECHNIQUE_COUNT):
        p = _ptr(s, at + 0x10 + 8 * i)
        if p and _readable(s, p):
            if ("tech", p) not in cache:
                cache[("tech", p)] = read_technique(s, p, cache)
            techniques[i] = cache[("tech", p)]
        elif p:
            techniques[i] = {"unresolved": p}
    return {"name": _str(s, at), "flags": _u16(s, at + 8), "worldVertFormat": _u8(s, at + 0xA),
            "preDisplacementOnlyCount": _u8(s, at + 0xB), "techniques": techniques}


def read_material(s, at):
    info = s.read(at, 0x28)
    tex_count, const_count, bits_count = s.read(at + 0x1C4, 3)
    flags = s.read(at + 0x1C7, 5)
    m = {
        "name": _str(s, at),
        "gameFlags": info[8], "sortKey": info[9], "textureAtlasRowCount": info[10],
        "textureAtlasColumnCount": info[11], "textureAtlasFrameBlend": info[12], "textureAtlasAsArray": info[13],
        "renderFlags": info[14], "drawSurf": list(struct.unpack("<QQ", info[0x10:0x20])),
        "surfaceTypeBits": struct.unpack("<I", info[0x20:0x24])[0],
        "hashIndex": struct.unpack("<H", info[0x24:0x26])[0],
        "stateBitsEntry": list(s.read(at + 0x28, TECHNIQUE_COUNT)),
        "stateFlags": flags[0], "cameraRegion": flags[1], "materialType": flags[2], "layerCount": flags[3],
        "assetFlags": flags[4],
        "constantBufferIndex": list(s.read(at + 0x1F0, TECHNIQUE_COUNT)),
        "techniqueSet": None, "textures": [], "constants": [], "stateBits": [], "constantBuffers": [],
        "subMaterials": [],
    }
    ts = _ptr(s, at + 0x1D0)
    if ts and _readable(s, ts):
        m["techniqueSet"] = read_techset(s, ts)
    p = _ptr(s, at + 0x1D8)
    if p and _readable(s, p):
        for i in range(tex_count):
            d = s.read(p + 16 * i, 16)
            u = struct.unpack("<Q", d[8:])[0]
            tex = {"nameHash": struct.unpack("<I", d[:4])[0], "nameStart": chr(d[4]), "nameEnd": chr(d[5]),
                   "samplerState": d[6], "semantic": d[7]}
            if d[7] == TS_WATER_MAP:
                tex["water"] = read_water(s, u) if u and _readable(s, u) else None
            else:
                tex["image"] = _image_name(s, u)
            m["textures"].append(tex)
    p = _ptr(s, at + 0x1E0)
    if p and _readable(s, p):
        for i in range(const_count):
            d = s.read(p + 32 * i, 32)
            m["constants"].append({"nameHash": struct.unpack("<I", d[:4])[0],
                                   "name": d[4:16].split(b"\0", 1)[0].decode("latin1"),
                                   "literal": list(struct.unpack("<4f", d[16:]))})
    p = _ptr(s, at + 0x1E8)
    if p and _readable(s, p):
        for i in range(bits_count):
            d = s.read(p + 0x1C * i, 0x1C)
            m["stateBits"].append({"loadBits": list(struct.unpack("<3I", d[:12])),
                                   "depthStencilState": list(d[13:24]), "blendState": d[24],
                                   "rasterizerState": d[25]})
    p = _ptr(s, at + 0x390)
    if p and _readable(s, p):
        for i in range(_u8(s, at + 0x398)):
            m["constantBuffers"].append(read_constant_buffer(s, p + 0x80 * i))
    p = _ptr(s, at + 0x3A0)
    if p and _readable(s, p):
        m["subMaterials"] = [_str(s, p + 8 * i) for i in range(m["layerCount"])]
    return m


def _image_name(s, p):
    """An image pointer as far as this module can tell: its name if it points at a loaded GfxImage (whose name
    the image module knows), else the address."""
    if not p:
        return None
    return HOOKS.get("image_name", lambda s, p: f"{p:#x}")(s, p)


def read_water(s, at):
    m, n = struct.unpack("<ii", s.read(at + 0x20, 8))
    out = {"M": m, "N": n}
    for key, off in (("H0X", 8), ("H0Y", 0x10), ("wTerm", 0x18)):
        p = _ptr(s, at + off)
        out[key] = list(struct.unpack(f"<{m * n}f", s.read(p, 4 * m * n))) if p and _readable(s, p) else None
    out["image"] = _image_name(s, _ptr(s, at + 0x48))
    out["imageAlt"] = _image_name(s, _ptr(s, at + 0x50))
    return out


def read_constant_buffer(s, at):
    sizes = struct.unpack("<8I", s.read(at, 32))
    out = {}
    for k, stage in enumerate(("vs", "hs", "ds", "ps")):
        p = _ptr(s, at + 0x20 + 8 * k)
        out[stage + "Data"] = s.read(p, sizes[k]) if p and _readable(s, p) else None
        q = _ptr(s, at + 0x40 + 8 * k)
        n = sizes[4 + k]
        out[stage + "OffsetData"] = list(struct.unpack(f"<{n}H", s.read(q, 2 * n))) if q and _readable(s, q) else None
    return out


# ---- state bits -------------------------------------------------------------------------------------------------

# gfx_d3d/r_state.cpp tables (Store 14089CFF0, 14089D030, 14089D070, 1408A94B0, 1408A94C0, 1408A94E0)
D3D11_BLEND = {0: "0", 1: "ZERO", 2: "ONE", 3: "SRC_COLOR", 4: "INV_SRC_COLOR", 5: "SRC_ALPHA", 6: "INV_SRC_ALPHA",
               7: "DEST_ALPHA", 8: "INV_DEST_ALPHA", 9: "DEST_COLOR", 10: "INV_DEST_COLOR", 16: "SRC1_COLOR",
               17: "INV_SRC1_COLOR", 18: "SRC1_ALPHA", 19: "INV_SRC1_ALPHA"}
COLOR_BLEND = [1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0x10, 0x11, 0x12, 0x13, 0]
ALPHA_BLEND = [1, 1, 2, 5, 6, 5, 6, 7, 8, 7, 8, 0x12, 0x13, 0x12, 0x13, 0]
BLEND_OP = {0: "disabled", 1: "ADD", 2: "SUBTRACT", 3: "REV_SUBTRACT", 4: "MIN", 5: "MAX"}
DEPTH_FUNC = ["ALWAYS", "GREATER", "EQUAL", "GREATER_EQUAL"]   # reversed depth: GFXS1 LESS -> GREATER
STENCIL_OP = ["KEEP", "ZERO", "REPLACE", "INCR_SAT", "DECR_SAT", "INVERT", "INCR", "DECR"]
STENCIL_FUNC = ["NEVER", "LESS", "EQUAL", "LESS_EQUAL", "GREATER", "NOT_EQUAL", "GREATER_EQUAL", "ALWAYS"]
CULL = ["NONE", "NONE", "BACK", "FRONT"]


def decode_blend_bits(bits):
    """32 blend bits as gfx_d3d/r_state.cpp's sub_1406321C0 turns them into a D3D11 render target blend."""
    enabled = bool(bits & 0x700)
    out = {"enable": enabled, "srcBlend": D3D11_BLEND[COLOR_BLEND[bits & 0xF]],
           "destBlend": D3D11_BLEND[COLOR_BLEND[(bits >> 4) & 0xF]], "blendOp": BLEND_OP.get((bits >> 8) & 7, "?"),
           "writeMask": "".join(c for k, c in enumerate("RGBA") if bits >> (24 + k) & 1)}
    if bits & 0x700000:
        out.update(srcBlendAlpha=D3D11_BLEND[ALPHA_BLEND[(bits >> 12) & 0xF]],
                   destBlendAlpha=D3D11_BLEND[ALPHA_BLEND[(bits >> 16) & 0xF]],
                   blendOpAlpha=BLEND_OP.get((bits >> 20) & 7, "?"))
    else:
        out.update(srcBlendAlpha=D3D11_BLEND[ALPHA_BLEND[bits & 0xF]],
                   destBlendAlpha=D3D11_BLEND[ALPHA_BLEND[(bits >> 4) & 0xF]],
                   blendOpAlpha=BLEND_OP.get((bits >> 8) & 7, "?"))
    return out


def decode_depth_stencil_bits(bits):
    """64 depth-stencil bits as r_state.cpp's sub_14065BED0 turns them into a D3D11 depth-stencil description."""
    face = lambda shift: {"pass": STENCIL_OP[(bits >> shift) & 7], "fail": STENCIL_OP[(bits >> (shift + 3)) & 7],
                          "depthFail": STENCIL_OP[(bits >> (shift + 6)) & 7],
                          "func": STENCIL_FUNC[(bits >> (shift + 9)) & 7]}
    return {"depthEnable": not bits >> 1 & 1, "depthWrite": bool(bits & 1), "depthFunc": DEPTH_FUNC[(bits >> 2) & 3],
            "stencilEnable": bool(bits & 0xC0), "front": face(8), "back": face(20),
            "stencilReadMask": (bits >> 32) & 0xFF, "stencilWriteMask": (bits >> 40) & 0xFF}


def decode_rasterizer_index(index):
    """dx.rasterizerStates[index] as r_state.cpp's sub_1406310F0 creates them: bits 0-1 cull, 2-3 polygon offset
    (3: the shadow map dvars), 4 wireframe."""
    return {"cull": ["NONE", "NONE", "BACK", "FRONT"][index & 3], "polygonOffset": (index >> 2) & 3,
            "fill": "WIREFRAME" if index & 0x10 else "SOLID"}


def decode_load_bits(bits):
    """GfxStateBits.loadBits by the servers' GFXS0_/GFXS1_/GFXS_ enums. The D3D11 states the renderer binds come
    from the zone's state tables, indexed by depthStencilState/blendState/rasterizerState; these are the packed
    bits the tools derived them from."""
    b0, b1, b2 = bits
    return {
        "alphaTest": "disabled" if b0 & 1 else ["none", "gt0", "lt128", "ge128"][(b0 >> 1) & 3],
        "cull": ["?", "none", "back", "front"][(b0 >> 3) & 3],
        "polygonLine": bool(b0 & 0x20), "gammaWrite": bool(b0 & 0x40), "stencilRef": (b0 >> 8) & 0xFF,
        "depthWrite": bool(b1 & 1),
        "depthTest": "disabled" if b1 & 2 else ["always", "less", "equal", "lessequal"][(b1 >> 2) & 3],
        "polygonOffset": (b1 >> 4) & 3, "stencilFront": bool(b1 & 0x40), "stencilBack": bool(b1 & 0x80),
        "blend": decode_blend_bits(b2),
    }


# ---- converters ---------------------------------------------------------------------------------------------------

def shader_hash(program):
    return hashlib.sha1(program).hexdigest() if program else None


def _shader_json(sh):
    if sh is None or "unresolved" in sh:
        return sh
    out = {k: v for k, v in sh.items() if k != "program"}
    out["sha1"] = shader_hash(sh["program"])
    if sh["program"]:
        try:
            d = dxbc.describe(sh["program"])
            out["dxbc"] = {"chunks": d["chunks"], "program": d.get("program")}
        except Exception as e:  # not a container (synthetic data, or unexpected content)
            out["dxbc"] = {"error": str(e)}
    return out


def _arg_json(a):
    out = {"type": T.ARG_TYPES[a["type"]] if a["type"] < len(T.ARG_TYPES) else a["type"],
           "shader": T.SHADER_STAGES[a["shader"]] if a["shader"] < len(T.SHADER_STAGES) else a["shader"],
           "dest": a["dest"]}
    if "index" in a:
        name = T.CODE_CONSTANT_NAMES[a["index"]] if a["index"] < len(T.CODE_CONSTANT_NAMES) else None
        out.update(codeConst=name or a["index"], firstRow=a["firstRow"], rowCount=a["rowCount"])
    elif "codeSampler" in a:
        c = a["codeSampler"]
        out["codeTexture"] = T.CODE_TEXTURE_NAMES[c] if c < len(T.CODE_TEXTURE_NAMES) else c
    elif "literal" in a:
        out["literal"] = a["literal"]
    else:
        out["nameHash"] = f"{a['nameHash']:08x}"
    return out


def _decl_json(d):
    if d is None or "unresolved" in d:
        return d
    rows = [{"source": T.STREAM_SRC_NAMES[r["source"]] if r["source"] < len(T.STREAM_SRC_NAMES) else r["source"],
             "dest": T.STREAM_DST_NAMES[r["dest"]] if r["dest"] < len(T.STREAM_DST_NAMES) else r["dest"],
             "mask": r["mask"]} for r in d["routing"]]
    return {**d, "routing": rows}


def techset_json(ts):
    techniques = {}
    for slot, tech in sorted(ts["techniques"].items()):
        key = T.TECHNIQUE_NAMES[slot]
        if "unresolved" in tech:
            techniques[key] = tech
            continue
        techniques[key] = {"name": tech["name"], "flags": tech["flags"], "passes": [
            {**{k: v for k, v in p.items() if k not in ("vertexShader", "hullShader", "domainShader", "pixelShader",
                                                         "vertexDecl", "args")},
             "vertexShader": _shader_json(p["vertexShader"]), "hullShader": _shader_json(p["hullShader"]),
             "domainShader": _shader_json(p["domainShader"]), "pixelShader": _shader_json(p["pixelShader"]),
             "vertexDecl": _decl_json(p["vertexDecl"]), "args": [_arg_json(a) for a in p["args"]]}
            for p in tech["passes"]]}
    return {"name": ts["name"], "flags": ts["flags"], "worldVertFormat": ts["worldVertFormat"],
            "preDisplacementOnlyCount": ts["preDisplacementOnlyCount"], "techniques": techniques}


def material_json(m):
    """A material as JSON-ready data: info, flags, textures, constants, state bits decoded per technique, constant
    buffers and its technique set."""
    tech = m["techniqueSet"]
    by_tech = {}
    if tech:
        for slot, t in tech["techniques"].items():
            first = m["stateBitsEntry"][slot]
            n = len(t.get("passes", []))
            by_tech[T.TECHNIQUE_NAMES[slot]] = {"stateBits": list(range(first, first + n)),
                                                "constantBuffer": m["constantBufferIndex"][slot]}
    sem = lambda k: T.TEXTURE_SEMANTICS[k] if k < len(T.TEXTURE_SEMANTICS) else k
    return {
        "name": m["name"],
        "info": {k: m[k] for k in ("gameFlags", "sortKey", "textureAtlasRowCount", "textureAtlasColumnCount",
                                   "textureAtlasFrameBlend", "textureAtlasAsArray", "renderFlags", "surfaceTypeBits",
                                   "hashIndex")},
        "drawSurf": [f"{w:016x}" for w in m["drawSurf"]],
        "stateFlags": m["stateFlags"],
        "cameraRegion": T.CAMERA_REGIONS[m["cameraRegion"]] if m["cameraRegion"] < 9 else m["cameraRegion"],
        "materialType": m["materialType"], "assetFlags": m["assetFlags"],
        "subMaterials": m["subMaterials"],
        "textures": [{**{k: v for k, v in t.items() if k not in ("semantic",)}, "nameHash": f"{t['nameHash']:08x}",
                      "semantic": sem(t["semantic"]), "sampler": decode_sampler_state(t["samplerState"])}
                     for t in m["textures"]],
        "constants": [{**c, "nameHash": f"{c['nameHash']:08x}"} for c in m["constants"]],
        "stateBits": [{"loadBits": [f"{b:08x}" for b in sb["loadBits"]], "decoded": decode_load_bits(sb["loadBits"]),
                       "depthStencilState": dict(zip(T.DEPTH_STENCIL_MODES, sb["depthStencilState"])),
                       "blendState": sb["blendState"], "rasterizerState": sb["rasterizerState"],
                       "rasterizer": decode_rasterizer_index(sb["rasterizerState"] & 0x1F)}
                      for sb in m["stateBits"]],
        "techniques": by_tech,
        "constantBuffers": [{k: (v.hex() if isinstance(v, bytes) else v) for k, v in cb.items()}
                            for cb in m["constantBuffers"]],
        "techniqueSet": techset_json(tech) if tech else None,
    }


def decode_sampler_state(state):
    """MaterialTextureDef.samplerState by the servers' SAMPLER_* bits: filter (0-2), mip (3-4), clamp U/V/W
    (5-7). The D3D11 sampler is dx.samplerStates[state] (r_state.cpp's sub_14065FE60 builds 256 of them)."""
    filt = ["disabled", "nearest", "linear", "aniso2x", "aniso4x", "cmp", "aniso16x", "?"][state & 7]
    mip = ["disabled", "nearest", "linear", "bespoke"][(state >> 3) & 3]
    return {"filter": filt, "mip": mip, "clampU": bool(state & 0x20), "clampV": bool(state & 0x40),
            "clampW": bool(state & 0x80)}


def iter_shaders(ts):
    """Every distinct shader of a technique set (read_techset output)."""
    seen = set()
    for tech in ts["techniques"].values():
        for p in tech.get("passes", []):
            for key in ("vertexShader", "hullShader", "domainShader", "pixelShader"):
                sh = p[key]
                if sh and sh.get("program") and id(sh) not in seen:
                    seen.add(id(sh))
                    yield sh


def export_shaders(ts, directory, listing=True):
    """Write each shader's DXBC as <stage>_<sha1>.dxbc (and a .asm listing when it parses); returns the names."""
    from pathlib import Path
    out = []
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    for sh in iter_shaders(ts):
        base = f"{sh['stage']}_{shader_hash(sh['program'])}"
        (d / f"{base}.dxbc").write_bytes(sh["program"])
        if listing:
            try:
                text = "\n".join([f"// {sh['name']}"] + dxbc.disassemble(sh["program"])) + "\n"
                (d / f"{base}.asm").write_text(text)
            except Exception:
                pass
        out.append(base)
    return out
