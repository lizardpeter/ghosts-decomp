"""Synthetic zone streams for materials, technique sets, shaders and vertex declarations.

Writes the bytes the Store build's loaders (src/gfx_d3d/r_material_load_db.cpp, docs/assets/materials.md) read, in
the order they read them, with every pointer form the loaders handle chosen at random: NULL, inline (-1), inline
with an alias slot (-2, asset pointers only) and offsets into earlier data. Used by the differential tests (which
feed it to the original and reconstructed loaders through a faked Load_Stream) and by the decoder's tests. Nothing
here comes from game data.

Images (Load_GfxImagePtr) and layer name arrays (Load_XStringArray) belong to other loaders: images are only ever
NULL or offsets here, and the layer names are written only when `xstring_arrays` is set (the decoder reads them,
the differential tests fake that loader).
"""
import random
import struct

FOLLOW = 0xFDFDFDFFFFFFFFFF
INSERT = 0xFDFDFDFFFFFFFFFE
TECHNIQUE_COUNT = 0x19C
TS_WATER_MAP = 0xB
MTL_ARG_LITERAL_CONST = 4

SIZES = {"Material": 0x3A8, "MaterialTechniqueSet": 0xCF0, "MaterialPass": 0x48, "MaterialVertexShader": 0x28,
         "MaterialPixelShader": 0x28, "MaterialHullShader": 0x20, "MaterialDomainShader": 0x20,
         "MaterialVertexDeclaration": 0x838, "GfxStateBits": 0x1C, "MaterialConstantBufferDef": 0x80,
         "water_t": 0x58, "MaterialInfo": 0x28}


def q(v):
    return struct.pack("<Q", v & (2 ** 64 - 1))


class Gen:
    """Builds one stream. `out` collects the bytes in load order."""

    def __init__(self, r: random.Random, xstring_arrays=False, max_techniques=3, max_passes=3, small=True):
        self.r = r
        self.out = bytearray()
        self.xstring_arrays = xstring_arrays
        self.max_techniques = max_techniques
        self.max_passes = max_passes
        self.small = small

    # ---- pointer forms -------------------------------------------------------------------------------------
    def offset(self):
        """A packed offset: block in bits 32-35, offset + 1 in the low 32 bits."""
        return (self.r.randrange(7) << 32) | self.r.randrange(1, 1 << 20)

    def ptr(self, forms=("null", "follow", "offset"), weights=None):
        form = self.r.choices(forms, weights)[0]
        return form, {"null": 0, "follow": FOLLOW, "insert": INSERT, "offset": None}[form] or (
            self.offset() if form == "offset" else 0)

    def raw(self, n):
        return bytearray(self.r.getrandbits(8) for _ in range(n))

    def name(self, prefix):
        return (prefix + "_" + "".join(self.r.choice("abcdefghijklmnopqrstuvwxyz0123456789_")
                                       for _ in range(self.r.randrange(0, 12)))).encode()

    def xstring(self, header, at, prefix="name", forms=("null", "follow", "offset")):
        """An XString field: returns a callable that writes its tail (the string, if inline)."""
        form, v = self.ptr(forms)
        header[at:at + 8] = q(v)
        text = self.name(prefix) if form == "follow" else None

        def tail():
            if text is not None:
                self.out += text + b"\0"
        return tail

    # ---- assets ---------------------------------------------------------------------------------------------
    def asset_ptr(self, emit, forms=("null", "follow", "insert", "offset"), weights=None):
        """An asset pointer (8 bytes) and a callable writing the asset if inline."""
        form, v = self.ptr(forms, weights)
        return q(v), (emit if form in ("follow", "insert") else (lambda: None))

    def material_info(self, header=None, at=0):
        h = header if header is not None else self.raw(0x28)
        return self.xstring(h, at, "mtl")

    def material(self, emit_header=True):
        h = self.raw(0x3A8)
        info_tail = self.material_info(h, 0)
        tech_ptr, tech_emit = self.asset_ptr(self.techset)
        h[0x1D0:0x1D8] = tech_ptr
        n_tex, n_const, n_bits, n_cb, n_layer = (self.r.randrange(5) for _ in range(5))
        h[0x1C4], h[0x1C5], h[0x1C6], h[0x398], h[0x1CA] = n_tex, n_const, n_bits, n_cb, n_layer
        forms = {}
        for at, key in ((0x1D8, "tex"), (0x1E0, "const"), (0x1E8, "bits"), (0x390, "cb")):
            form, v = self.ptr()
            h[at:at + 8] = q(v)
            forms[key] = form
        layers = self.r.random() < 0.5
        h[0x3A0:0x3A8] = q(self.r.getrandbits(64) | 1 if layers else 0)
        if emit_header:
            self.out += h
        info_tail()
        tech_emit()
        if forms["tex"] == "follow":
            defs = [self.texture_def() for _ in range(n_tex)]
            for d, _ in defs:
                self.out += d
            for _, tail in defs:
                tail()
        if forms["const"] == "follow":
            self.out += self.raw(32 * n_const)
        if forms["bits"] == "follow":
            self.out += self.raw(0x1C * n_bits)
        if forms["cb"] == "follow":
            self.constant_buffer_defs(n_cb)
        if layers and self.xstring_arrays:
            ptrs, tails = bytearray(), []
            for _ in range(n_layer):
                p = bytearray(8)
                tails.append(self.xstring(p, 0, "layer"))
                ptrs += p
            self.out += ptrs
            for t in tails:
                t()
        return h

    def texture_def(self):
        d = self.raw(0x10)
        water = self.r.random() < 0.3
        d[7] = TS_WATER_MAP if water else self.r.choice([x for x in range(256) if x != TS_WATER_MAP])
        if water:
            form, v = self.ptr()
            d[8:16] = q(v)
            return d, (self.water if form == "follow" else (lambda: None))
        d[8:16] = q(self.r.choice((0, self.offset())))  # images: NULL or an offset (Load_GfxImagePtr is not ours)
        return d, (lambda: None)

    def water(self, emit_header=True):
        h = self.raw(0x58)
        m, n = self.r.randrange(1, 5), self.r.randrange(1, 5)
        h[0x20:0x28] = struct.pack("<ii", m, n)
        present = [self.r.random() < 0.7 for _ in range(3)]
        for i, p in enumerate(present):
            h[8 + 8 * i:16 + 8 * i] = q(self.r.getrandbits(64) | 1 if p else 0)
        for at in (0x48, 0x50):
            h[at:at + 8] = q(self.r.choice((0, self.offset())))
        if emit_header:
            self.out += h
        for p in present:
            if p:
                self.out += self.raw(4 * m * n)
        return h

    def constant_buffer_defs(self, count, emit_header=True):
        defs = []
        for _ in range(count):
            d = self.raw(0x80)
            sizes = [self.r.randrange(0, 48) for _ in range(8)]
            d[0:32] = struct.pack("<8I", *sizes)
            present = [self.r.random() < 0.6 for _ in range(8)]
            for i, p in enumerate(present):
                d[0x20 + 8 * i:0x28 + 8 * i] = q(self.r.getrandbits(64) | 1 if p else 0)
            defs.append((d, sizes, present))
        if emit_header:
            for d, _, _ in defs:
                self.out += d
        for d, sizes, present in defs:
            for i in range(4):
                if present[i]:
                    self.out += self.raw(sizes[i])
            for i in range(4, 8):
                if present[i]:
                    self.out += self.raw(2 * sizes[i])
        return b"".join(d for d, _, _ in defs)

    def state_bits(self):
        return self.raw(0x1C)

    # ---- technique sets ---------------------------------------------------------------------------------------
    def techset(self, emit_header=True):
        h = self.raw(0xCF0)
        name_tail = self.xstring(h, 0, "techset")
        slots = [0] * TECHNIQUE_COUNT
        chosen = self.r.sample(range(TECHNIQUE_COUNT), self.r.randrange(self.max_techniques + 1))
        for i in range(TECHNIQUE_COUNT):
            v = 0
            if i in chosen:
                form, v = self.ptr(("follow", "offset"), (3, 1))
                slots[i] = form
            h[0x10 + 8 * i:0x18 + 8 * i] = q(v)
        if emit_header:
            self.out += h
        name_tail()
        for form in slots:
            if form == "follow":
                self.technique()
        return h

    def technique(self, emit_header=True):
        h = self.raw(0x10)
        name_tail = self.xstring(h, 0, "tech")
        n = self.r.randrange(self.max_passes + 1)
        h[0xA:0xC] = struct.pack("<H", n)
        if emit_header:
            self.out += h
        self.passes(n)
        name_tail()
        return h

    def passes(self, n, emit_header=True):
        hs = []
        for _ in range(n):
            p = self.raw(0x48)
            emits = []
            for at, emit in ((0, self.vertex_shader), (8, self.vertex_decl), (0x10, self.hull_shader),
                             (0x18, self.domain_shader), (0x20, self.pixel_shader)):
                v, e = self.asset_ptr(emit, weights=(2, 3, 1, 2))
                p[at:at + 8] = v
                emits.append(e)
            counts = [self.r.randrange(4) for _ in range(3)]
            p[0x29:0x2C] = bytes(counts)
            has_args = self.r.random() < 0.8
            p[0x40:0x48] = q(self.r.getrandbits(64) | 1 if has_args else 0)
            hs.append((p, emits, has_args, sum(counts)))
        if emit_header:
            for p, _, _, _ in hs:
                self.out += p
        for p, emits, has_args, nargs in hs:
            for e in emits:
                e()
            if has_args:
                args = []
                for _ in range(nargs):
                    a = self.raw(0x10)
                    a[0] = self.r.choice((MTL_ARG_LITERAL_CONST, MTL_ARG_LITERAL_CONST, 0, 1, 2, 3, 5, 6, 7, 0xFF))
                    form = "none"
                    if a[0] == MTL_ARG_LITERAL_CONST:
                        form, v = self.ptr()
                        a[8:16] = q(v)
                    args.append((a, form))
                for a, _ in args:
                    self.out += a
                for _, form in args:
                    if form == "follow":
                        self.out += self.raw(16)
        return b"".join(p for p, _, _, _ in hs)

    def _shader(self, size, loaddef_at, emit_header):
        h = self.raw(size)
        name_tail = self.xstring(h, 0, "shader")
        form, v = self.ptr()
        h[loaddef_at:loaddef_at + 8] = q(v)
        program_size = self.r.randrange(0, 0x60)
        h[loaddef_at + 8:loaddef_at + 12] = struct.pack("<I", program_size)
        if emit_header:
            self.out += h
        name_tail()
        if form == "follow":
            self.out += self.raw(program_size)
        return h

    def vertex_shader(self, emit_header=True):
        return self._shader(0x28, 0x10, emit_header)

    def pixel_shader(self, emit_header=True):
        return self._shader(0x28, 0x10, emit_header)

    def hull_shader(self, emit_header=True):
        return self._shader(0x20, 0x10, emit_header)

    def domain_shader(self, emit_header=True):
        return self._shader(0x20, 0x10, emit_header)

    def vertex_decl(self, emit_header=True):
        h = self.raw(0x838)
        name_tail = self.xstring(h, 0, "decl")
        h[8] = self.r.randrange(0, 32)
        if emit_header:
            self.out += h
        name_tail()
        return h


def asset_ptr_stream(g: Gen, emit, forms=("null", "follow", "insert", "offset")):
    """An 8-byte asset pointer followed by the asset when inline: what Load_<Type>Ptr(true) reads."""
    v, e = g.asset_ptr(emit, forms)
    g.out += v
    e()
