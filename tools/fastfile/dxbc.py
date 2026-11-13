"""DXBC (Direct3D 11 shader bytecode) containers: chunks, reflection, signatures and a shader model 4/5 disassembler.

Standard library only. The shaders the game loads (MaterialVertexShader and the others, docs/assets/materials.md)
are complete DXBC containers, exactly what ID3D11Device::Create*Shader takes. This module reads what a DXBC to
SPIR-V translator needs from them:

- the container: "DXBC", a 16-byte checksum, version 1, total size, chunk count and offsets; each chunk is a
  four-character code, a size and its data;
- RDEF: constant buffers (name, size, variables with offsets, sizes and types) and resource bindings (textures,
  samplers, constant buffers with their bind points), i.e. the register layout the material's arguments fill;
- ISGN/OSGN/PCSG (and the ISG1/OSG1/OSG5 forms): the input and output signatures (semantic name and index,
  register, component mask, system value, component type), which match the vertex declaration's semantics
  (s_streamDestInfo) and connect the stages;
- SHDR/SHEX: the program tokens, decoded here into an assembly listing in the usual fxc style;
- STAT and others are listed but not decoded.

The opcode numbering is the public D3D10/D3D11 tokenized program format (d3d10tokenizedprogramformat.hpp,
d3d11tokenizedprogramformat.hpp). The checksum is not verified (D3D checks it at creation; a translator doesn't
need it).
"""
import struct

SHADER_TYPES = {0: "ps", 1: "vs", 2: "gs", 3: "hs", 4: "ds", 5: "cs"}

OPCODES = """add and break breakc call callc case continue continuec cut default deriv_rtx deriv_rty discard div dp2
dp3 dp4 else emit emit_then_cut endif endloop endswitch eq exp frc ftoi ftou ge iadd if ieq ige ilt imad imax imin imul
ine ineg ishl ishr itof label ld ld_ms log loop lt mad min max customdata mov movc mul ne nop not or resinfo ret retc
round_ne round_ni round_pi round_z rsq sample sample_c sample_c_lz sample_l sample_d sample_b sqrt switch sincos udiv
ult uge umul umad umax umin ushr utof xor dcl_resource dcl_constantbuffer dcl_sampler dcl_index_range
dcl_outputtopology dcl_inputprimitive dcl_maxout dcl_input dcl_input_sgv dcl_input_siv dcl_input_ps dcl_input_ps_sgv
dcl_input_ps_siv dcl_output dcl_output_sgv dcl_output_siv dcl_temps dcl_indexableTemp dcl_globalFlags reserved_107 lod
gather4 sample_pos sample_info reserved_112 hs_decls hs_control_point_phase hs_fork_phase hs_join_phase emit_stream
cut_stream emit_then_cut_stream fcall bufinfo deriv_rtx_coarse deriv_rtx_fine deriv_rty_coarse deriv_rty_fine
gather4_c gather4_po gather4_po_c rcp f32tof16 f16tof32 uaddc usubb countbits firstbit_hi firstbit_lo firstbit_shi
ubfe ibfe bfi bfrev swapc dcl_stream dcl_function_body dcl_function_table dcl_interface
dcl_input_control_point_count dcl_output_control_point_count dcl_tessellator_domain dcl_tessellator_partitioning
dcl_tessellator_output_primitive dcl_hs_max_tessfactor dcl_hs_fork_phase_instance_count
dcl_hs_join_phase_instance_count dcl_thread_group dcl_uav_typed dcl_uav_raw dcl_uav_structured dcl_tgsm_raw
dcl_tgsm_structured dcl_resource_raw dcl_resource_structured ld_uav_typed store_uav_typed ld_raw store_raw
ld_structured store_structured atomic_and atomic_or atomic_xor atomic_cmp_store atomic_iadd atomic_imax atomic_imin
atomic_umax atomic_umin imm_atomic_alloc imm_atomic_consume imm_atomic_iadd imm_atomic_and imm_atomic_or
imm_atomic_xor imm_atomic_exch imm_atomic_cmp_exch imm_atomic_imax imm_atomic_imin imm_atomic_umax imm_atomic_umin
sync dadd dmax dmin dmul deq dge dlt dne dmov dmovc dtof ftod eval_snapped eval_sample_index eval_centroid
dcl_gsinstances abort debug_break reserved_209 ddiv dfma drcp msad dtoi dtou itod utod""".split()
OP = {name: i for i, name in enumerate(OPCODES)}

# operand types (D3D10_SB_OPERAND_TYPE / D3D11_SB_OPERAND_TYPE)
OPERAND_TYPES = {0: "r", 1: "v", 2: "o", 3: "x", 6: "s", 7: "t", 8: "cb", 9: "icb", 10: "label", 11: "vPrim",
                 12: "oDepth", 13: "null", 14: "rasterizer", 15: "oMask", 16: "m", 17: "fb", 18: "ft", 19: "fp",
                 20: "fi", 21: "fo", 22: "vOutputControlPointID", 23: "vForkInstanceID", 24: "vJoinInstanceID",
                 25: "vicp", 26: "vocp", 27: "vpc", 28: "vDomain", 29: "this", 30: "u", 31: "g", 32: "vThreadID",
                 33: "vThreadGroupID", 34: "vThreadIDInGroup", 35: "vCoverage", 36: "vThreadIDInGroupFlattened",
                 37: "vGSInstanceID", 38: "oDepthGE", 39: "oDepthLE", 40: "vCycleCounter", 41: "oStencilRef",
                 42: "vInnerCoverage"}
RESOURCE_DIMS = {0: "unknown", 1: "buffer", 2: "texture1d", 3: "texture2d", 4: "texture2dms", 5: "texture3d",
                 6: "texturecube", 7: "texture1darray", 8: "texture2darray", 9: "texture2dmsarray",
                 10: "texturecubearray", 11: "raw_buffer", 12: "structured_buffer"}
RETURN_TYPES = {1: "unorm", 2: "snorm", 3: "sint", 4: "uint", 5: "float", 6: "mixed", 7: "double", 8: "continued",
                9: "unused"}
SYSTEM_VALUES = {0: "undefined", 1: "position", 2: "clip_distance", 3: "cull_distance", 4: "rendertarget_array_index",
                 5: "viewport_array_index", 6: "vertex_id", 7: "primitive_id", 8: "instance_id", 9: "is_front_face",
                 10: "sampleIndex", 11: "finalQuadUeq0EdgeTessFactor", 12: "finalQuadVeq0EdgeTessFactor",
                 13: "finalQuadUeq1EdgeTessFactor", 14: "finalQuadVeq1EdgeTessFactor",
                 15: "finalQuadUInsideTessFactor", 16: "finalQuadVInsideTessFactor",
                 17: "finalTriUeq0EdgeTessFactor", 18: "finalTriVeq0EdgeTessFactor", 19: "finalTriWeq0EdgeTessFactor",
                 20: "finalTriInsideTessFactor", 21: "finalLineDetailTessFactor", 22: "finalLineDensityTessFactor",
                 64: "target", 65: "depth", 66: "coverage", 67: "depth_greater_equal", 68: "depth_less_equal"}
INTERPOLATION = {0: "undefined", 1: "constant", 2: "linear", 3: "linear centroid", 4: "linear noperspective",
                 5: "linear noperspective centroid", 6: "linear sample", 7: "linear noperspective sample"}
# D3D_NAME, the system values of signature elements (numbered differently from the instructions' D3D10_SB_NAME)
SIGNATURE_SYSTEM_VALUES = {0: "undefined", 1: "position", 2: "clip_distance", 3: "cull_distance",
                           4: "rendertarget_array_index", 5: "viewport_array_index", 6: "vertex_id", 7: "primitive_id",
                           8: "instance_id", 9: "is_front_face", 10: "sample_index", 11: "final_quad_edge_tessfactor",
                           12: "final_quad_inside_tessfactor", 13: "final_tri_edge_tessfactor",
                           14: "final_tri_inside_tessfactor", 15: "final_line_detail_tessfactor",
                           16: "final_line_density_tessfactor", 64: "target", 65: "depth", 66: "coverage",
                           67: "depth_greater_equal", 68: "depth_less_equal"}
COMPONENT_TYPES = {0: "unknown", 1: "uint", 2: "int", 3: "float"}
TESS_DOMAIN = {0: "undefined", 1: "isoline", 2: "tri", 3: "quad"}
TESS_PARTITIONING = {0: "undefined", 1: "integer", 2: "pow2", 3: "fractional_odd", 4: "fractional_even"}
TESS_OUTPUT = {0: "undefined", 1: "point", 2: "line", 3: "triangle_cw", 4: "triangle_ccw"}
SV_NAMES = {0: "", 1: "SV_Position", 2: "SV_ClipDistance", 3: "SV_CullDistance", 4: "SV_RenderTargetArrayIndex",
            5: "SV_ViewportArrayIndex", 6: "SV_VertexID", 7: "SV_PrimitiveID", 8: "SV_InstanceID",
            9: "SV_IsFrontFace", 10: "SV_SampleIndex"}
COMP = "xyzw"
# instructions whose operands are integers (immediates printed as integers, not floats)
INT_OPS = {"and", "or", "xor", "not", "iadd", "imul", "imad", "imax", "imin", "ineg", "ishl", "ishr", "ieq", "ige",
           "ilt", "ine", "uge", "ult", "udiv", "umul", "umad", "umax", "umin", "ushr", "itof", "utof", "ubfe", "ibfe",
           "bfi", "bfrev", "countbits", "firstbit_hi", "firstbit_lo", "firstbit_shi", "uaddc", "usubb", "switch",
           "case", "ld", "ld_ms", "ld_raw", "ld_structured", "store_raw", "store_structured", "ld_uav_typed",
           "store_uav_typed", "swapc", "movc", "if", "breakc", "continuec", "retc", "callc"}


class DxbcError(Exception):
    pass


# ---- container ------------------------------------------------------------------------------------------------

def parse_container(blob: bytes):
    """[(fourcc, data)] of a DXBC container."""
    if len(blob) < 32 or blob[:4] != b"DXBC":
        raise DxbcError("not a DXBC container")
    version, total, count = struct.unpack_from("<III", blob, 20)
    if total > len(blob):
        raise DxbcError(f"container says {total} bytes, have {len(blob)}")
    chunks = []
    for i in range(count):
        off = struct.unpack_from("<I", blob, 32 + 4 * i)[0]
        fourcc = blob[off:off + 4].decode("latin1")
        size = struct.unpack_from("<I", blob, off + 4)[0]
        chunks.append((fourcc, blob[off + 8:off + 8 + size]))
    return chunks


def chunk(blob: bytes, *names):
    for fourcc, data in parse_container(blob):
        if fourcc in names:
            return fourcc, data
    return None, None


def _cstr(data, off):
    end = data.index(b"\0", off)
    return data[off:end].decode("latin1")


# ---- RDEF -----------------------------------------------------------------------------------------------------

SHADER_INPUT_TYPES = {0: "cbuffer", 1: "tbuffer", 2: "texture", 3: "sampler", 4: "uav_rwtyped", 5: "structured",
                      6: "uav_rwstructured", 7: "byteaddress", 8: "uav_rwbyteaddress", 9: "uav_append_structured",
                      10: "uav_consume_structured", 11: "uav_rwstructured_with_counter"}
VARIABLE_CLASSES = {0: "scalar", 1: "vector", 2: "matrix_rows", 3: "matrix_columns", 4: "object", 5: "struct",
                    6: "interface_class", 7: "interface_pointer"}
VARIABLE_TYPES = {0: "void", 1: "bool", 2: "int", 3: "float", 4: "string", 5: "texture", 6: "texture1d",
                  7: "texture2d", 8: "texture3d", 9: "texturecube", 10: "sampler", 19: "uint", 20: "uint8",
                  39: "double"}


def parse_rdef(data: bytes) -> dict:
    cb_count, cb_off, bind_count, bind_off, minor, major, prog_type, flags, creator_off = struct.unpack_from(
        "<IIIIBBHII", data, 0)
    out = {"target": f"{SHADER_TYPES.get(prog_type & 0xF, prog_type)}_{major}_{minor}", "flags": flags,
           "creator": _cstr(data, creator_off), "constant_buffers": [], "bindings": []}
    rd11 = data[28:32] == b"RD11"
    var_size = 40 if rd11 else 24
    for i in range(bind_count):
        name_off, typ, ret, dim, samples, point, count, bflags = struct.unpack_from("<8I", data, bind_off + 32 * i)
        out["bindings"].append({"name": _cstr(data, name_off), "type": SHADER_INPUT_TYPES.get(typ, typ),
                                "return_type": RETURN_TYPES.get(ret, ret), "dimension": RESOURCE_DIMS.get(dim, dim),
                                "samples": samples, "bind_point": point, "bind_count": count, "flags": bflags})
    for i in range(cb_count):
        name_off, var_count, var_off, size, cflags, ctype = struct.unpack_from("<6I", data, cb_off + 24 * i)
        cb = {"name": _cstr(data, name_off), "size": size, "flags": cflags, "type": ctype, "variables": []}
        for j in range(var_count):
            v = var_off + var_size * j
            vname, voff, vsize, vflags, vtype, vdefault = struct.unpack_from("<6I", data, v)
            vclass, vt, rows, cols, elems, members = struct.unpack_from("<HHHHHH", data, vtype)
            cb["variables"].append({"name": _cstr(data, vname), "offset": voff, "size": vsize,
                                    "used": bool(vflags & 2), "class": VARIABLE_CLASSES.get(vclass, vclass),
                                    "type": VARIABLE_TYPES.get(vt, vt), "rows": rows, "columns": cols,
                                    "elements": elems})
        out["constant_buffers"].append(cb)
    return out


# ---- signatures -----------------------------------------------------------------------------------------------

def parse_signature(fourcc: str, data: bytes) -> list:
    """ISGN/OSGN/PCSG (24-byte elements), OSG5 (28: stream first), ISG1/OSG1/PSG1 (32: stream first, precision
    last)."""
    count, _ = struct.unpack_from("<II", data, 0)
    size = {"OSG5": 28, "ISG1": 32, "OSG1": 32, "PSG1": 32}.get(fourcc, 24)
    out = []
    for i in range(count):
        e = 8 + size * i
        stream = 0
        if size != 24:
            stream = struct.unpack_from("<I", data, e)[0]
            e += 4
        name_off, index, sv, ctype, reg = struct.unpack_from("<5I", data, e)
        mask, rw = data[e + 20], data[e + 21]
        out.append({"semantic": _cstr(data, name_off), "index": index, "register": reg,
                    "system_value": SIGNATURE_SYSTEM_VALUES.get(sv, sv),
                    "component_type": COMPONENT_TYPES.get(ctype, ctype),
                    "mask": "".join(c for k, c in enumerate(COMP) if mask >> k & 1),
                    "used": "".join(c for k, c in enumerate(COMP) if rw >> k & 1), "stream": stream})
    return out


# ---- program --------------------------------------------------------------------------------------------------

def _float(bits):
    f = struct.unpack("<f", struct.pack("<I", bits))[0]
    if f != f or f in (float("inf"), float("-inf")):
        return f"0x{bits:08x}"
    r = repr(f)
    return r[:-2] if r.endswith(".0") else r


class Program:
    """A decoded SHDR/SHEX chunk: shader type, version and instructions."""

    def __init__(self, data: bytes):
        self.tokens = struct.unpack_from(f"<{len(data) // 4}I", data, 0)
        version, length = self.tokens[0], self.tokens[1]
        self.type = SHADER_TYPES.get(version >> 16, version >> 16)
        self.major, self.minor = (version >> 4) & 0xF, version & 0xF
        self.length = length
        self.instructions = []  # (opcode name, opcode token, [tokens of the instruction])
        i = 2
        end = min(length, len(self.tokens))
        while i < end:
            tok = self.tokens[i]
            opcode = tok & 0x7FF
            if opcode == OP["customdata"]:
                n = self.tokens[i + 1]
            else:
                n = (tok >> 24) & 0x7F
            if n == 0:
                raise DxbcError(f"zero-length instruction at token {i}")
            self.instructions.append((OPCODES[opcode] if opcode < len(OPCODES) else f"op_{opcode}", tok,
                                      self.tokens[i:i + n]))
            i += n

    def listing(self) -> list:
        lines = [f"{self.type}_{self.major}_{self.minor}"]
        depth = 0
        for name, tok, toks in self.instructions:
            text = _instruction(name, tok, toks)
            if name in ("endif", "endloop", "endswitch", "else", "case", "default"):
                depth = max(depth - 1, 0)
            lines.append("  " * depth + text)
            if name in ("if", "loop", "switch", "else", "case", "default"):
                depth += 1
        return lines


class _Operands:
    def __init__(self, toks, at):
        self.toks, self.i = toks, at

    def more(self):
        return self.i < len(self.toks)

    def word(self):
        v = self.toks[self.i]
        self.i += 1
        return v

    def operand(self, ints=False):
        tok = self.word()
        ncomp = tok & 3
        mode = (tok >> 2) & 3
        sel = (tok >> 4) & 0xFF
        otype = (tok >> 12) & 0xFF
        dims = (tok >> 20) & 3
        reps = [(tok >> (22 + 3 * k)) & 7 for k in range(3)]
        prefix, suffix = "", ""
        ext = tok >> 31
        while ext:
            e = self.word()
            ext = e >> 31
            if e & 0x3F == 1:  # modifier
                mod = (e >> 6) & 0xFF
                if mod == 1:
                    prefix = "-"
                elif mod == 2:
                    prefix, suffix = "|", "|"
                elif mod == 3:
                    prefix, suffix = "-|", "|"
        if otype == 4 or otype == 5:  # immediate32 / immediate64
            count = 1 if ncomp == 1 else 4
            if otype == 4:
                vals = [self.word() for _ in range(count)]
                fmt = (lambda v: str(v if v < 0x80000000 else v - 0x100000000)) if ints else _float
                body = ", ".join(fmt(v) for v in vals)
            else:
                vals = [self.word() | self.word() << 32 for _ in range(count)]
                body = ", ".join(f"0x{v:016x}" for v in vals)
            return f"{prefix}l({body}){suffix}"
        name = OPERAND_TYPES.get(otype, f"op{otype}")
        idx = []
        for k in range(dims):
            rep = reps[k]
            if rep == 0:
                idx.append(str(self.word()))
            elif rep == 1:
                idx.append(str(self.word() << 32 | self.word()))
            elif rep == 2:
                idx.append(self.operand(True))
            elif rep == 3:
                imm = self.word()
                idx.append(f"{self.operand(True)} + {imm}")
            else:
                imm = self.word() << 32 | self.word()
                idx.append(f"{self.operand(True)} + {imm}")
        if name in ("r", "v", "o", "x", "s", "t", "u", "g", "m", "cb") and idx and reps[0] == 0:
            text = name + idx[0] + "".join(f"[{x}]" for x in idx[1:])  # fxc style: r0, cb2[27], x0[r1.x + 2]
        else:
            text = name + "".join(f"[{x}]" for x in idx)
        if ncomp == 2:
            if mode == 0:
                text += "." + "".join(c for k, c in enumerate(COMP) if sel >> k & 1) if sel & 0xF else ""
            elif mode == 1:
                text += "." + "".join(COMP[(sel >> (2 * k)) & 3] for k in range(4))
            else:
                text += "." + COMP[sel & 3]
        return prefix + text + suffix


def _instruction(name, tok, toks):
    ops = _Operands(toks, 1)
    ext = tok >> 31
    while ext:
        e = ops.word()
        ext = e >> 31
    sat = "_sat" if tok >> 13 & 1 and not name.startswith("dcl") else ""
    if name == "customdata":
        cls = (tok >> 11) & 0x1FFFFF
        if cls == 3:
            vals = toks[2:]
            rows = ["{ " + ", ".join(_float(v) for v in vals[k:k + 4]) + " }" for k in range(0, len(vals), 4)]
            return "dcl_immediateConstantBuffer { " + ", ".join(rows) + " }"
        return f"customdata class {cls}, {len(toks) - 2} dwords"
    if name == "dcl_temps":
        return f"dcl_temps {ops.word()}"
    if name == "dcl_indexableTemp":
        return f"dcl_indexableTemp x{ops.word()}[{ops.word()}], {ops.word()}"
    if name == "dcl_globalFlags":
        flags = (tok >> 11) & 0x1FFF
        names = ["refactoringAllowed", "enableDoublePrecisionFloatOps", "forceEarlyDepthStencil",
                 "enableRawAndStructuredBuffers", "skipOptimization", "enableMinimumPrecision",
                 "enable11_1DoubleExtensions", "enable11_1ShaderExtensions"]
        return "dcl_globalFlags " + " | ".join(n for k, n in enumerate(names) if flags >> k & 1)
    if name == "dcl_constantbuffer":
        text = ops.operand()
        return f"dcl_constantbuffer {text}, {'dynamicIndexed' if tok >> 11 & 1 else 'immediateIndexed'}"
    if name == "dcl_sampler":
        mode = ["default", "comparison", "mono"][(tok >> 11) & 3] if (tok >> 11) & 3 < 3 else "?"
        return f"dcl_sampler {ops.operand()}, mode_{mode}"
    if name == "dcl_resource":
        dim = RESOURCE_DIMS.get((tok >> 11) & 0x1F, "?")
        text = ops.operand()
        ret = ops.word() if ops.more() else 0
        rt = ",".join(RETURN_TYPES.get(ret >> (4 * k) & 0xF, "?") for k in range(4))
        return f"dcl_resource_{dim} ({rt}) {text}"
    if name in ("dcl_input_siv", "dcl_input_sgv", "dcl_output_siv", "dcl_output_sgv", "dcl_input_ps_siv",
                "dcl_input_ps_sgv"):
        interp = f" {INTERPOLATION.get((tok >> 11) & 0xF, '?')}" if name.startswith("dcl_input_ps") else ""
        text = ops.operand()
        sv = ops.word()
        return f"{name}{interp} {text}, {SYSTEM_VALUES.get(sv, sv)}"
    if name == "dcl_input_ps":
        return f"dcl_input_ps {INTERPOLATION.get((tok >> 11) & 0xF, '?')} {ops.operand()}"
    if name in ("dcl_input_control_point_count", "dcl_output_control_point_count"):
        return f"{name} {(tok >> 11) & 0x3F}"
    if name == "dcl_tessellator_domain":
        return f"{name} domain_{TESS_DOMAIN.get((tok >> 11) & 3, '?')}"
    if name == "dcl_tessellator_partitioning":
        return f"{name} partitioning_{TESS_PARTITIONING.get((tok >> 11) & 7, '?')}"
    if name == "dcl_tessellator_output_primitive":
        return f"{name} output_{TESS_OUTPUT.get((tok >> 11) & 7, '?')}"
    if name == "dcl_hs_max_tessfactor":
        return f"{name} l({_float(ops.word())})"
    if name in ("dcl_hs_fork_phase_instance_count", "dcl_hs_join_phase_instance_count", "dcl_gsinstances",
                "dcl_maxout"):
        return f"{name} {ops.word()}"
    if name == "dcl_thread_group":
        return f"dcl_thread_group {ops.word()}, {ops.word()}, {ops.word()}"
    if name in ("dcl_resource_structured", "dcl_uav_structured", "dcl_tgsm_structured"):
        text = ops.operand()
        rest = [str(ops.word()) for _ in range(len(toks) - ops.i)]
        return f"{name} {text}, " + ", ".join(rest)
    if name in ("sync",):
        flags = (tok >> 11) & 0xF
        parts = [n for k, n in enumerate(("_t", "_g", "_ugroup", "_uglobal")) if flags >> k & 1]
        return "sync" + "".join(parts)
    if name == "resinfo":
        rt = ["", "_rcpFloat", "_uint"][(tok >> 11) & 3] if (tok >> 11) & 3 < 3 else ""
        name += rt
    test = ""
    if name in ("if", "breakc", "continuec", "retc", "discard", "callc"):
        test = "_nz" if tok >> 18 & 1 else "_z"
    operands = []
    ints = name in INT_OPS
    while ops.more():
        operands.append(ops.operand(ints))
    text = name + test + sat
    return text + (" " + ", ".join(operands) if operands else "")


def disassemble(blob: bytes) -> list:
    """The listing of a DXBC container's program, preceded by its reflection and signatures as comments."""
    out = []
    for fourcc, data in parse_container(blob):
        if fourcc == "RDEF":
            r = parse_rdef(data)
            out.append(f"// {r['target']}, {r['creator']}")
            for cb in r["constant_buffers"]:
                out.append(f"// cbuffer {cb['name']} ({cb['size']} bytes)")
                for v in cb["variables"]:
                    out.append(f"//   {v['type']} {v['name']}  offset {v['offset']} size {v['size']}"
                               + ("" if v["used"] else "  [unused]"))
            for b in r["bindings"]:
                out.append(f"// binding {b['name']}: {b['type']} {b['dimension']} slot {b['bind_point']}"
                           + (f" x{b['bind_count']}" if b["bind_count"] != 1 else ""))
        elif fourcc in ("ISGN", "OSGN", "PCSG", "ISG1", "OSG1", "OSG5", "PSG1"):
            out.append(f"// {fourcc}")
            for e in parse_signature(fourcc, data):
                reg = "-" if e["register"] == 0xFFFFFFFF else e["register"]
                out.append(f"//   {e['semantic']}{e['index']}  reg {reg}.{e['mask']}  "
                           f"{e['component_type']}  {e['system_value']}")
    _, prog = chunk(blob, "SHEX", "SHDR")
    if prog is not None:
        out += Program(prog).listing()
    return out


def describe(blob: bytes) -> dict:
    """What a translator needs, as plain data: chunks, reflection, signatures, shader type and instruction count."""
    chunks = parse_container(blob)
    out = {"chunks": [(c, len(d)) for c, d in chunks]}
    for fourcc, data in chunks:
        if fourcc == "RDEF":
            out["reflection"] = parse_rdef(data)
        elif fourcc in ("ISGN", "OSGN", "PCSG", "ISG1", "OSG1", "OSG5", "PSG1"):
            out.setdefault("signatures", {})[fourcc] = parse_signature(fourcc, data)
        elif fourcc in ("SHEX", "SHDR"):
            p = Program(data)
            out["program"] = {"type": p.type, "version": f"{p.major}.{p.minor}", "tokens": p.length,
                              "instructions": len(p.instructions)}
    return out
