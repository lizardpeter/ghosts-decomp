"""Tests of tools/fastfile/material.py and tools/fastfile/dxbc.py on synthetic data (no game data).

    python3 -m unittest tests/fastfile/test_material.py

- The decoder's loaders run on streams from tools/fastfile/material_synth.py through a minimal stand-in for the
  pipeline's Stream (same methods and rules as tools/fastfile/iw6ff.py's), must consume every byte the generator
  wrote, and the readers must give back what was generated (names, programs, counts, pass contents).
- With the Store exe available ($IW6_ORIGINALS, as for the differential tests), the generator itself is checked
  against the game: the original Load_Material/Load_MaterialTechniqueSet and the shader and vertex declaration
  loaders, run in the emulator with the stream functions faked, must read exactly the generated streams. That ties
  the decoder's stream layout to the Store build's code until the real-zone check (docs/assets/materials.md).
- dxbc.py parses a hand-assembled container and disassembles its program.
"""
import os
import random
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "fastfile"))
import dxbc  # noqa: E402
import material as mat  # noqa: E402
import material_synth as ms  # noqa: E402

PTR_INLINE, PTR_INSERT = ms.FOLLOW, ms.INSERT


class MiniStream:
    """The pipeline Stream's interface and rules (tools/fastfile/iw6ff.py), without a zone file around it: blocks
    at (i + 1) << 40, the runtime block (2) zero-filled, temp (0) reused after a pop, inserts in the virtual block."""

    def __init__(self, data: bytes, size=1 << 22):
        self.zone, self.cursor = data, 0
        self.bases = [(i + 1) << 40 for i in range(7)]
        self.mem = [bytearray(size) for _ in range(7)]
        self.pos = [0] * 7
        self.index = 0
        self.stack = []
        self.pool, self.pool_base = bytearray(), 0xF << 40
        self.links = []

    def read_file(self, n):
        if self.cursor + n > len(self.zone):
            raise EOFError(f"read past the end ({self.cursor + n:#x} > {len(self.zone):#x})")
        b = self.zone[self.cursor:self.cursor + n]
        self.cursor += n
        return b

    def addr(self):
        return self.bases[self.index] + self.pos[self.index]

    def locate(self, a):
        for i, b in enumerate(self.bases):
            if b <= a < b + len(self.mem[i]):
                return self.mem[i], a - b
        if self.pool_base <= a < self.pool_base + len(self.pool):
            return self.pool, a - self.pool_base
        raise KeyError(f"{a:#x}")

    def write(self, a, data):
        r, off = self.locate(a)
        r[off:off + len(data)] = data

    def read(self, a, n):
        r, off = self.locate(a)
        return bytes(r[off:off + n])

    def u64(self, a):
        return struct.unpack("<Q", self.read(a, 8))[0]

    def put_u64(self, a, v):
        self.write(a, struct.pack("<Q", v & (2 ** 64 - 1)))

    def cstr(self, a):
        r, off = self.locate(a)
        return bytes(r[off:r.index(0, off)])

    def load(self, at_stream_start, a, size):
        if not at_stream_start or not size:
            return
        self.write(a, b"\0" * size if self.index == 2 else self.read_file(size))
        self.pos[self.index] += size

    def align(self, alignment):
        self.pos[self.index] = (self.pos[self.index] + alignment - 1) & ~(alignment - 1)
        return self.addr()

    def push(self, index):
        self.stack.append((self.pos[index], self.index))
        self.index = index

    def pop(self):
        saved, index = self.stack.pop()
        if self.index == 0:
            self.pos[0] = saved
        self.index = index

    def insert_pointer(self):
        self.push(3)
        self.pos[3] = (self.pos[3] + 7) & ~7
        slot = self.addr()
        self.pos[3] += 8
        self.pop()
        return slot

    def offset_to_pointer(self, v):
        return (self.bases[(v >> 32) & 0xF] + (v & 0xFFFFFFFF) - 1) & (2 ** 64 - 1)

    def offset_to_alias(self, v):
        try:
            return self.u64(self.offset_to_pointer(v))
        except KeyError:
            return 0xA11A5 << 40 | (v & 0xFFFFFFFF)  # synthetic offsets point anywhere: keep a marker

    def xstring_ptr(self, field):
        v = self.u64(field)
        if v == 0:
            return
        if v == PTR_INLINE:
            self.put_u64(field, self.addr())
            n = self.zone.index(b"\0", self.cursor) - self.cursor + 1
            self.write(self.addr(), self.read_file(n))
            self.pos[self.index] += n
        else:
            self.put_u64(field, self.offset_to_pointer(v))

    def link(self, asset_type, header):
        size = mat.ASSET_SIZES[asset_type]
        at = (len(self.pool) + 15) & ~15
        self.pool += b"\0" * (at - len(self.pool)) + self.read(header, size)
        self.links.append(asset_type)
        return self.pool_base + at


def _load(stream_bytes, loader):
    s = MiniStream(stream_bytes)
    s.push(3)
    at = s.align(4)
    loader(s, at, True)
    return s, at


class Decoder(unittest.TestCase):
    def test_materials_consume_their_stream(self):
        for seed in range(300):
            g = ms.Gen(random.Random(seed), xstring_arrays=True)
            g.material()
            s, at = _load(bytes(g.out), mat.load_material)
            self.assertEqual(s.cursor, len(g.out), f"seed {seed}")
            m = mat.read_material(s, at)
            j = mat.material_json(m)
            self.assertEqual(len(j["textures"]), len(m["textures"]))
            import json
            json.dumps(j)

    def test_techsets_consume_their_stream(self):
        for seed in range(300):
            g = ms.Gen(random.Random(1000 + seed), max_techniques=6)
            g.techset()
            s, at = _load(bytes(g.out), mat.load_techset)
            self.assertEqual(s.cursor, len(g.out), f"seed {seed}")
            ts = mat.read_techset(s, at)
            mat.techset_json(ts)

    def test_round_trip_values(self):
        """A hand-built technique set: one technique, one pass, an inline vertex shader with a program, an inline
        pixel shader alias slot, a literal constant and a code constant argument."""
        program = bytes(range(40))
        out = bytearray()
        ts = bytearray(0xCF0)
        ts[0:8] = struct.pack("<Q", PTR_INLINE)
        ts[8:10] = struct.pack("<H", 0x41)
        ts[0x10 + 8 * 0x3:0x18 + 8 * 0x3] = struct.pack("<Q", PTR_INLINE)  # TECHNIQUE_EMISSIVE
        out += ts + b"my_techset\0"
        tech = bytearray(0x10)
        tech[0:8] = struct.pack("<Q", PTR_INLINE)
        tech[0xA:0xC] = struct.pack("<H", 1)
        out += tech
        p = bytearray(0x48)
        p[0:8] = struct.pack("<Q", PTR_INLINE)
        p[0x20:0x28] = struct.pack("<Q", PTR_INSERT)
        p[0x29:0x2C] = bytes([1, 0, 1])
        p[0x40:0x48] = struct.pack("<Q", 1)
        out += p
        vs = bytearray(0x28)
        vs[0:8] = struct.pack("<Q", PTR_INLINE)
        vs[0x10:0x18] = struct.pack("<Q", PTR_INLINE)
        vs[0x18:0x1C] = struct.pack("<I", len(program))
        vs[0x1C:0x1E] = struct.pack("<H", 1)
        out += vs + b"vs_main\0" + program
        ps = bytearray(0x28)
        ps[0:8] = struct.pack("<Q", PTR_INLINE)
        out += ps + b"ps_main\0"
        a0 = struct.pack("<BBHI", 4, 4, 7, 0) + struct.pack("<Q", PTR_INLINE)
        a1 = struct.pack("<BBH", 0, 1, 3) + b"\0" * 4 + struct.pack("<HBB", 0x123, 0, 4) + b"\0" * 4
        out += a0 + a1 + struct.pack("<4f", 1.0, 0.5, -2.0, 0.25)
        out += b"emissive_tech\0"
        s, at = _load(bytes(out), mat.load_techset)
        self.assertEqual(s.cursor, len(out))
        r = mat.read_techset(s, at)
        self.assertEqual(r["name"], "my_techset")
        t = r["techniques"][3]
        self.assertEqual(t["name"], "emissive_tech")
        p0 = t["passes"][0]
        self.assertEqual(p0["vertexShader"]["name"], "vs_main")
        self.assertEqual(p0["vertexShader"]["program"], program)
        self.assertEqual(p0["pixelShader"]["name"], "ps_main")
        self.assertEqual(p0["args"][0]["literal"], [1.0, 0.5, -2.0, 0.25])
        j = mat.techset_json(r)
        tj = j["techniques"]["TECHNIQUE_EMISSIVE"]
        self.assertEqual(tj["passes"][0]["args"][1]["codeConst"], "CONST_SRC_CODE_VIEW_MATRIX")
        self.assertEqual(tj["passes"][0]["args"][1]["rowCount"], 4)
        self.assertEqual(s.links, [mat.ASSET_TYPE_VERTEXSHADER, mat.ASSET_TYPE_PIXELSHADER])

    def test_state_bits(self):
        # ONE * src + INV_SRC_ALPHA * dest, add; alpha the same; RGBA written
        bits = 2 | (6 << 4) | (1 << 8) | (0xF << 24)
        d = mat.decode_blend_bits(bits)
        self.assertEqual((d["enable"], d["srcBlend"], d["destBlend"], d["blendOp"], d["writeMask"]),
                         (True, "ONE", "INV_SRC_ALPHA", "ADD", "RGBA"))
        self.assertEqual(d["destBlendAlpha"], "INV_SRC_ALPHA")
        ds = mat.decode_depth_stencil_bits(0x1 | (1 << 2))
        self.assertEqual((ds["depthEnable"], ds["depthWrite"], ds["depthFunc"]), (True, True, "GREATER"))
        self.assertEqual(mat.decode_rasterizer_index(0x12)["cull"], "BACK")
        self.assertEqual(mat.decode_rasterizer_index(0x12)["fill"], "WIREFRAME")


# ---- DXBC ---------------------------------------------------------------------------------------------------------

def _operand(otype, ncomp=2, mode=0, sel=0xF, dims=1, idx=(0,)):
    tok = ncomp | mode << 2 | sel << 4 | otype << 12 | dims << 20
    return [tok, *idx]


def _ins(opcode, *operand_tokens, extra=0, tail=()):
    body = [t for op in operand_tokens for t in op] + list(tail)
    return [opcode | extra | (1 + len(body)) << 24, *body]


def build_container(program_tokens, shader_type=1):
    shex = struct.pack("<II", shader_type << 16 | 5 << 4 | 0, 2 + len(program_tokens)) + struct.pack(
        f"<{len(program_tokens)}I", *program_tokens)
    names = b"POSITION\0"
    isgn = struct.pack("<II", 1, 8) + struct.pack("<5IBBH", 8 + 24, 0, 0, 3, 0, 0xF, 0xF, 0) + names
    chunks = [(b"ISGN", isgn), (b"SHEX", shex)]
    head = 32 + 4 * len(chunks)
    body, offs = b"", []
    for fourcc, data in chunks:
        offs.append(head + len(body))
        body += fourcc + struct.pack("<I", len(data)) + data
    total = head + len(body)
    return b"DXBC" + b"\0" * 16 + struct.pack("<III", 1, total, len(chunks)) + struct.pack(
        f"<{len(offs)}I", *offs) + body


class Dxbc(unittest.TestCase):
    def test_disassemble(self):
        swz = lambda x, y, z, w: x | y << 2 | z << 4 | w << 6
        prog = []
        prog += _ins(dxbc.OP["dcl_input"], _operand(1, sel=0xF, idx=(0,)))
        prog += _ins(dxbc.OP["dcl_output_siv"], _operand(2, sel=0xF, idx=(0,)), tail=[1])
        prog += _ins(dxbc.OP["dcl_temps"], tail=[2])
        prog += _ins(dxbc.OP["mul"], _operand(0, sel=0xF, idx=(0,)), _operand(1, mode=1, sel=swz(0, 1, 2, 3)),
                     [2 | 4 << 12, *struct.unpack("<4I", struct.pack("<4f", 2, 2, 2, 1))])
        prog += _ins(dxbc.OP["mov"], _operand(2, sel=0xF, idx=(0,)), _operand(0, mode=1, sel=swz(0, 1, 2, 3)),
                     extra=1 << 13)
        prog += _ins(dxbc.OP["ret"])
        blob = build_container(prog)
        lines = dxbc.disassemble(blob)
        text = "\n".join(lines)
        self.assertIn("vs_5_0", text)
        self.assertIn("dcl_input v0.xyzw", text)
        self.assertIn("dcl_output_siv o0.xyzw, position", text)
        self.assertIn("dcl_temps 2", text)
        self.assertIn("mul r0.xyzw, v0.xyzw, l(2, 2, 2, 1)", text)
        self.assertIn("mov_sat o0.xyzw, r0.xyzw", text)
        self.assertEqual(lines[-1], "ret")
        sig = dxbc.parse_signature("ISGN", dxbc.chunk(blob, "ISGN")[1])
        self.assertEqual(sig[0]["semantic"], "POSITION")
        self.assertEqual(dxbc.describe(blob)["program"]["instructions"], 6)


# ---- the generator against the game ---------------------------------------------------------------------------

STORE = "iw6mp64_MSStore_ship"
EXE = Path(os.environ.get("IW6_ORIGINALS", ROOT / ".work" / "originals")) / f"{STORE}.exe"


@unittest.skipUnless(EXE.exists(), "needs the Store exe ($IW6_ORIGINALS)")
class GeneratorAgainstStoreBuild(unittest.TestCase):
    """The original loaders must read exactly the bytes the generator wrote (and the decoder reads)."""

    def test_original_consumes_generated_streams(self):
        sys.path.insert(0, str(ROOT / "tests" / "differential"))
        import harness
        import syms
        syms.BUILD = STORE
        import test_r_material_load as t
        sys.path.insert(0, str(ROOT / "tools"))
        import symbols
        table = symbols.table(STORE)
        m = harness.Machine(harness.Image(harness.original_exe(STORE)))
        fakes = {table[k][0]: fn for k, fn in t.STREAM_FAKES.items()}
        loaders = {"Load_Material": ("varMaterial", lambda g: g.material()),
                   "Load_MaterialTechniqueSet": ("varMaterialTechniqueSet", lambda g: g.techset()),
                   "Load_MaterialVertexShader": ("varMaterialVertexShader", lambda g: g.vertex_shader()),
                   "Load_MaterialHullShader": ("varMaterialHullShader", lambda g: g.hull_shader()),
                   "Load_MaterialVertexDeclaration": ("varMaterialVertexDeclaration", lambda g: g.vertex_decl()),
                   "Load_water_t": ("varwater_t", lambda g: g.water())}
        for name, (var, build) in loaders.items():
            target = table[f"?{name}@@YAX_N@Z"][0]
            for seed in range(25):
                r = random.Random(seed)
                inp = t._input(r, True, build, var)
                ret = m.call(target, inp["args"], "void", inp["setup"], fakes)
                self.assertFalse(isinstance(ret[0], str), f"{name} seed {seed}: {ret[0]}")
                self.assertEqual(t.M["cur"], len(t.M["src"]), f"{name} seed {seed}")


if __name__ == "__main__":
    unittest.main()
