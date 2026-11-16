"""The light grid (GfxLightGrid, GfxWorld + 0x138): the lighting the game samples for static models and dynamic
objects (docs/assets/world.md, "Light grid").

The grid is a set of points in "grid space" (integer coordinates). A compressed tree (GfxLightGridTree, light grid
+0x5D0) maps a point to a GfxLightGridRaw: a colour index, a light index (the primary light environment) and two
voxel bits. This module is a reference decoder written from the game's own functions (gfx_d3d/r_pointlights.cpp; the
Xbox One server's code, with the Store build's table initialisation), one Python function per original:

    R_GetLightGrid                      get_light_grid            Store 140646380
    R_DecodeLightGridBlock              decode_block              Store 140644F00
    R_LoadLightGridNodeBitStream        load_node_bitstream       Store 140647520
    R_DecodeNodeRawIndex                decode_node_raw_index     Store 140645890
    R_LoadLightGridBlockBitStream       load_block_bitstream      Store 140646E60
    R_LoadLightGridBlockIndexBitStream  load_block_index_bitstream Store 1406471A0
    R_ExecLeafIndexEncodedCommand       exec_leaf_index_command   Store 1406462A0
    R_DecodeLeafIndexRaw                decode_leaf_raw_index     Store 140644A60
    R_DecodeLightGridIndexMask          decode_index_mask
    R_DecodeLightGridVoxelMask          decode_voxel_mask         Store 140645770
    Com_BitStreamRead / ReadArray       BitStream.read / read_array  Store 140643920

The game also keeps a 509-entry cache of decoded blocks; it changes nothing in the result and is not modelled.
"""
import struct
from dataclasses import dataclass, field

# R_GetLightGrid: the cell of a 4 x 4 block a point's (x & 3, y & 3) selects
CELL_ORDER = (0, 1, 4, 5, 2, 3, 6, 7, 8, 9, 12, 13, 10, 11, 14, 15)

# The voxel and index mask tables (the Store builds them in 1406466E0; both are the same 16 entries): the four cells
# of a block each 4-bit code selects, in bit order.
MASK_TABLE = (
    (0, 1, 4, 5), (2, 3, 6, 7), (8, 9, 12, 13), (10, 11, 14, 15),
    (0, 2, 8, 10), (1, 3, 9, 11), (4, 6, 12, 14), (5, 7, 13, 15),
    (0, 1, 2, 3), (1, 4, 3, 6), (4, 5, 6, 7), (2, 3, 8, 9),
    (6, 7, 12, 13), (8, 9, 10, 11), (9, 12, 11, 14), (12, 13, 14, 15),
)


def bit_count_for(n: int) -> int:
    """The bits that hold values below n, as the decoder computes them: 0 for 0, else bit length of max(n - 1, 1)."""
    return 0 if n == 0 else max(n - 1, 1).bit_length()


def popcount(v: int) -> int:
    return bin(v & 0xFFFFFFFF).count("1")


class BitStream:
    """Com_BitStream: bits are read least significant first, byte by byte."""

    def __init__(self, data: bytes, byte_index: int = 0):
        self.data = data
        self.bit_index = byte_index * 8

    def read(self, n: int) -> int:
        v, got = 0, 0
        while got < n:
            i, sh = self.bit_index >> 3, self.bit_index & 7
            take = min(8 - sh, n - got)
            byte = self.data[i] if i < len(self.data) else 0
            v |= ((byte >> sh) & ((1 << take) - 1)) << got
            got += take
            self.bit_index += take
        return v

    def read_array(self, n: int, count: int):
        return [self.read(n) for _ in range(max(count, 0))]

    def align(self):
        self.bit_index = (self.bit_index + 7) & ~7


@dataclass
class NodeIndexEncoded:          # LightGridNodeIndexEncoded
    bit_count: int = 0
    table_size: int = 0
    table_size_bit_count: int = 0
    min: int = 0
    default: int = 0
    table: list = field(default_factory=lambda: [0] * 15)


@dataclass
class NodeEncoded:               # LightGridNodeEncoded
    format: int = 0
    leaf_size: list = field(default_factory=lambda: [0] * 8)
    color: NodeIndexEncoded = field(default_factory=NodeIndexEncoded)
    light: NodeIndexEncoded = field(default_factory=NodeIndexEncoded)


@dataclass
class NodeIndexRaw:              # LightGridNodeIndexRaw
    bit_count: int = 0
    table_size: int = 0
    table_size_bit_count: int = 0
    min: int = 0
    default: int = 0
    table: list = field(default_factory=lambda: [0] * 15)


@dataclass
class LeafIndexEncoded:          # LightGridLeafIndexEncoded
    default: int = 0
    min: int = 0
    index: list = field(default_factory=lambda: [0] * 16)
    bit_count: int = 0


@dataclass
class LeafEncoded:               # LightGridLeafEncoded
    format: int = 0
    color: LeafIndexEncoded = field(default_factory=LeafIndexEncoded)
    light: LeafIndexEncoded = field(default_factory=LeafIndexEncoded)
    voxels: int = 0


@dataclass
class BlockCommand:              # LightGridBlockCommand
    command: int = 0
    block_size: int = 0
    mask: int = 0
    data: list = field(default_factory=lambda: [0] * 16)


@dataclass
class Tree:                      # GfxLightGridTree (0x50)
    max_depth: int
    node_count: int
    leaf_count: int
    coord_min: tuple
    coord_max: tuple
    coord_half_size: tuple
    default_color_index_bit_count: int
    default_light_index_bit_count: int
    node_table: tuple
    leaf_table: bytes


def read_tree(mem, at: int) -> Tree:
    """A GfxLightGridTree from memory (`mem.read`, `mem.u64`), e.g. light grid + 0x5D0."""
    h = mem.read(at, 0x50)
    max_depth = h[0]
    node_count, leaf_count = struct.unpack_from("<ii", h, 4)
    vals = struct.unpack_from("<9i", h, 0x0C)
    cbits, lbits = struct.unpack_from("<ii", h, 0x30)
    nodes_p, = struct.unpack_from("<Q", h, 0x38)
    leaf_size, = struct.unpack_from("<i", h, 0x40)
    leaf_p, = struct.unpack_from("<Q", h, 0x48)
    nodes = struct.unpack(f"<{node_count}I", mem.read(nodes_p, 4 * node_count)) if node_count and nodes_p else ()
    leaves = mem.read(leaf_p, leaf_size) if leaf_size > 0 and leaf_p else b""
    return Tree(max_depth, node_count, leaf_count, vals[0:3], vals[3:6], vals[6:9], cbits, lbits, nodes, leaves)


def load_node_bitstream(child_mask: int, color_bits: int, light_bits: int, bs: BitStream) -> NodeEncoded:
    """R_LoadLightGridNodeBitStream: the node header of a block group (byte aligned at both ends)."""
    bs.align()
    n = NodeEncoded()
    n.format = bs.read(8)
    n.leaf_size[:popcount(child_mask & 0xFF)] = bs.read_array(6, popcount(child_mask & 0xFF))
    for idx, (f_min, f_def, f_tab, bits, plain_bits) in ((n.color, (1, 2, 4, color_bits, 16)),
                                                          (n.light, (8, 0x10, 0x20, light_bits, 1))):
        if n.format & f_min:
            idx.min = bs.read(bits)
            idx.bit_count = (bs.read(bit_count_for(bits)) + 1) & 0xFF
        else:
            idx.min, idx.bit_count = 0, plain_bits
        idx.default = bs.read(idx.bit_count) if n.format & f_def else 0
        if n.format & f_tab:
            size = (bs.read(4) + 1) & 0xFF
            idx.table_size = size
            idx.table_size_bit_count = bit_count_for(size)
            idx.table[1:size] = bs.read_array(idx.bit_count, size - 1)
            idx.table[0] = 0
    bs.align()
    return n


def decode_node_raw_index(enc: NodeIndexEncoded) -> NodeIndexRaw:
    """R_DecodeNodeRawIndex: table entries and the default as absolute indices (0 stays 0, else min - 1 + value)."""
    raw = NodeIndexRaw(bit_count=enc.bit_count, table_size=enc.table_size, min=enc.min)
    if enc.table_size:
        raw.table_size_bit_count = bit_count_for(enc.table_size)
        for i in range(enc.table_size):
            e = enc.table[i] if i < 15 else 0
            raw.table[i] = 0 if e == 0 else (enc.min - 1 + e) & 0xFFFFFFFF
        raw.default = raw.table[enc.default] if enc.default < 15 else 0
    else:
        raw.default = 0 if enc.default == 0 else (raw.min - 1 + enc.default) & 0xFFFFFFFF
    return raw


def decode_index_mask(bs: BitStream) -> int:
    """R_DecodeLightGridIndexMask: 16 cells, either literal or a table code, optionally inverted."""
    if bs.read(1) == 0:
        return bs.read(16)
    code = bs.read(4)
    invert = bs.read(1)
    bits = bs.read(4)
    m = 0
    for i, cell in enumerate(MASK_TABLE[code]):
        if bits >> i & 1:
            m |= 1 << cell
    return ~m & 0xFFFF if invert else m


def decode_voxel_mask(bs: BitStream) -> int:
    """R_DecodeLightGridVoxelMask: 0 literal, 1 all cells, 2 table code, 3 inverted table code."""
    kind = bs.read(2)
    if kind == 0:
        return bs.read(16)
    if kind == 1:
        return 0xFFFF
    code = bs.read(4)
    bits = bs.read(4)
    m = 0
    for i, cell in enumerate(MASK_TABLE[code]):
        if bits >> i & 1:
            m |= 1 << cell
    return ~m & 0xFFFF if kind == 3 else m


def load_block_index_bitstream(idx: LeafIndexEncoded, bs: BitStream) -> list:
    """R_LoadLightGridBlockIndexBitStream: the commands that fill a block's 16 encoded indices."""
    cmds = []
    while True:
        c = BlockCommand(block_size=16)
        c.command = bs.read(2)
        if c.command == 0:            # all 16 values
            c.mask = 0xFFFF
            c.data[:16] = bs.read_array(idx.bit_count, 16)
            more = 0
        elif c.command == 1:          # 2 or 3 cells, one value
            c.block_size = bs.read(1) + 2
            cells = bs.read_array(4, c.block_size)
            c.mask = 0
            for cell in cells:
                c.mask |= 1 << cell
            c.data[0] = bs.read(idx.bit_count)
            more = bs.read(1)
        elif c.command == 2:          # masked cells, one value each
            c.mask = decode_index_mask(bs)
            n = popcount(c.mask)
            c.data[:n] = bs.read_array(idx.bit_count, n)
            more = 0
        else:                         # masked cells, one value
            c.mask = decode_index_mask(bs)
            c.data[0] = bs.read(idx.bit_count)
            more = bs.read(1)
        cmds.append(c)
        if not more:
            return cmds


def load_block_bitstream(node_raw_color: NodeIndexRaw, node_raw_light: NodeIndexRaw, node: NodeEncoded, bs: BitStream,
                         leaf_size: int):
    """R_LoadLightGridBlockBitStream: one block's header, index commands and voxel masks."""
    bs.align()
    leaf = LeafEncoded()
    commands = {"color": [], "light": []}
    if leaf_size:
        leaf.format = bs.read(8)
    for name, idx, nidx, raw, (f_min, f_def, f_cmd) in (
            ("color", leaf.color, node.color, node_raw_color, (1, 2, 4)),
            ("light", leaf.light, node.light, node_raw_light, (8, 0x10, 0x20))):
        from_table = False
        if leaf.format & f_min:
            bc = nidx.bit_count
            idx.min = bs.read(bc)
            bc = (bs.read(bit_count_for(bc)) + 1) & 0xFF
        elif nidx.table_size_bit_count == 0:
            idx.min = int(nidx.min != 0)
            bc = nidx.bit_count
        else:
            idx.min = 1
            bc = nidx.table_size_bit_count
            from_table = True
        idx.bit_count = bc
        if leaf.format & f_def:
            idx.default = bs.read(bc)
        elif from_table:
            idx.default = nidx.default
        else:
            base = 0 if idx.min == 0 else (idx.min - 1 + raw.min) & 0xFFFFFFFF
            idx.default = 0 if raw.default == 0 else (raw.default - base + 1) & 0xFFFFFFFF
        if leaf.format & f_cmd:
            commands[name] = load_block_index_bitstream(idx, bs)
    if leaf.format & 0x40:
        leaf.voxels |= decode_voxel_mask(bs)
    if leaf.format & 0x80:
        leaf.voxels |= decode_voxel_mask(bs) << 16
    bs.align()
    return leaf, commands


def exec_leaf_index_command(commands: list, idx: LeafIndexEncoded):
    """R_ExecLeafIndexEncodedCommand: every cell gets the default, then each command writes its cells."""
    idx.index = [idx.default] * 16
    for c in commands:
        if c.block_size < 2:
            idx.index[(c.mask & 0xFFFFFFFF).bit_length() - 1] = c.data[0]
        elif c.command in (0, 2):
            k = 0
            for cell in range(16):
                if c.mask >> cell & 1:
                    idx.index[cell] = c.data[k]
                    k += 1
        else:
            for cell in range(16):
                if c.mask >> cell & 1:
                    idx.index[cell] = c.data[0]


def decode_leaf_raw_index(node_raw: NodeIndexRaw, idx: LeafIndexEncoded):
    """R_DecodeLeafIndexRaw: a block's 16 indices as absolute indices, through the node's table when it has one."""
    if node_raw.table_size_bit_count and node_raw.table_size_bit_count <= idx.bit_count:
        look = lambda e: node_raw.table[e] if e < 15 else 0
        return look(idx.default), [look(e) for e in idx.index]
    base = 0 if idx.min == 0 else (idx.min - 1 + node_raw.min) & 0xFFFFFFFF
    rel = lambda e: 0 if e == 0 else (e - 1 + base) & 0xFFFFFFFF
    return rel(idx.default), [rel(e) for e in idx.index]


def decode_block(tree: Tree, child_mask: int, child: int, leaf_offset: int):
    """R_DecodeLightGridBlock: (color indices[16], light indices[16], voxels) of one 4 x 4 block."""
    bs = BitStream(tree.leaf_table, leaf_offset)
    node = load_node_bitstream(child_mask, tree.default_color_index_bit_count, tree.default_light_index_bit_count, bs)
    raw_c, raw_l = decode_node_raw_index(node.color), decode_node_raw_index(node.light)
    k = popcount(child_mask & ((1 << child) - 1))
    bs.bit_index += sum(node.leaf_size[:k]) * 8
    leaf, commands = load_block_bitstream(raw_c, raw_l, node, bs, node.leaf_size[k] if k < 8 else 0)
    exec_leaf_index_command(commands["color"], leaf.color)
    exec_leaf_index_command(commands["light"], leaf.light)
    _, colors = decode_leaf_raw_index(raw_c, leaf.color)
    _, lights = decode_leaf_raw_index(raw_l, leaf.light)
    return colors, lights, leaf.voxels


def get_light_grid(tree: Tree, coord):
    """R_GetLightGrid: (colorIndex, lightIndex, voxel) at a grid-space point (u16 x, y, z), (0, 0, 0) outside the
    tree or in an empty block."""
    x, y, z = coord
    if not all(tree.coord_min[i] <= coord[i] <= tree.coord_max[i] for i in range(3)):
        return 0, 0, 0
    bz = z - tree.coord_min[2]
    by = (y - tree.coord_min[1]) >> 2
    bx = (x - tree.coord_min[0]) >> 2
    cell = CELL_ORDER[(x & 3) + (y & 3) * 4]
    bit = 1 << tree.max_depth
    index, leaf_offset, mask, child = 0, -1, 0, 0
    for depth in range(tree.max_depth + 1):
        child = (4 if bz & bit else 0) | (2 if by & bit else 0) | (1 if bx & bit else 0)
        entry = tree.node_table[index]
        mask = entry >> 24
        if not mask >> child & 1:
            break
        if depth < tree.max_depth:
            index = (entry & 0xFFFFFF) + popcount(mask & ((1 << child) - 1))
        else:
            leaf_offset = entry & 0xFFFFFF
        bit >>= 1
    if leaf_offset < 0 or not mask >> child & 1:
        return 0, 0, 0
    colors, lights, voxels = decode_block(tree, mask, child, leaf_offset)
    voxel = (2 if voxels >> (cell + 16) & 1 else 0) | (voxels >> cell & 1)
    return colors[cell], lights[cell] & 0xFFFF, voxel


# ==== colours: spherical harmonics in the palette

@dataclass
class LightGrid:                 # GfxLightGrid (0x620), the parts the decoder uses
    mins: tuple
    maxs: tuple
    range_exponents: tuple       # rangeExponent8/12/16BitsEncoding (+0x64)
    palette_entry_address: tuple # +0x78, paletteEntryCount (+0x70) of them
    palette: bytes               # paletteBitstream (+0x88), paletteBitstreamSize (+0x80) bytes
    tree: Tree


def read_light_grid(mem, at: int) -> LightGrid:
    """GfxLightGrid at `at` (GfxWorld + 0x138)."""
    h = mem.read(at, 0x90)
    mins, maxs = struct.unpack_from("<3H", h, 0x08), struct.unpack_from("<3H", h, 0x0E)
    exps = struct.unpack_from("<3b", h, 0x64)
    count, = struct.unpack_from("<I", h, 0x70)
    addr_p, = struct.unpack_from("<Q", h, 0x78)
    size, = struct.unpack_from("<I", h, 0x80)
    pal_p, = struct.unpack_from("<Q", h, 0x88)
    addrs = struct.unpack(f"<{count}i", mem.read(addr_p, 4 * count)) if count and addr_p else ()
    pal = mem.read(pal_p, size) if size and pal_p else b""
    return LightGrid(mins, maxs, exps, addrs, pal, read_tree(mem, at + 0x5D0))


def decode_spherical_harmonics(range_exponents, data: bytes, offset: int = 0):
    """R_DecodeLightGridSphericalHarmonics (Store 1406452D0, the coefficient decoders inlined): 9 coefficients per
    colour channel, as float32 [9][3] (numpy), and the record's size in bytes (even).

    A u16 header holds a 5-bit exponent per channel (r: bits 10-14, g: 5-9, b: 0-4), each minus 8; the scale is
    2^exponent. The exponent selects the channel's encoding through the grid's range exponents: up to the 8-bit one
    9 bytes, up to the 12-bit one 14 bytes (2-byte aligned), else 18 bytes (2-byte aligned). Coefficient 0 maps to
    [0, scale), the others to [-scale, scale)."""
    import numpy as np
    f32 = np.float32
    head, = struct.unpack_from("<H", data, offset)
    exps = ((head >> 10 & 0x1F) - 8, (head >> 5 & 0x1F) - 8, (head & 0x1F) - 8)
    out = np.zeros((9, 3), np.float32)
    pos = 2
    for ch, e in enumerate(exps):
        bits = 8 if e <= range_exponents[0] else (12 if e <= range_exponents[1] else 16)
        scale = f32(1.0) / f32(1 << -e) if e < 0 else f32(1 << e)
        neg = -scale
        p = offset + pos
        if bits == 8:
            b = data[p:p + 9]
            step = scale * f32(2.0) * f32(0.00390625)
            out[0, ch] = scale * f32(0.00390625) * f32(b[0])
            for i in range(1, 9):
                out[i, ch] = f32(b[i]) * step + neg
            pos += 9
        else:
            pos += pos & 1
            p = offset + pos
            b = data[p:p + (14 if bits == 12 else 18)]
            out[0, ch] = scale * f32(1.5258789e-05) * f32(struct.unpack_from("<H", b, 0)[0])
            if bits == 12:
                step = scale * f32(2.0) * f32(0.00024414062)
                nib = (b[9] >> 4, b[10] & 15, b[10] >> 4, b[11] & 15, b[11] >> 4, b[12] & 15, b[12] >> 4, b[13] & 15)
                for i in range(1, 9):
                    out[i, ch] = f32(b[1 + i] << 4 | nib[i - 1]) * step + neg
                pos += 14
            else:
                step = scale * f32(2.0) * f32(1.5258789e-05)
                for i in range(1, 9):
                    out[i, ch] = f32(struct.unpack_from("<H", b, 2 * i)[0]) * step + neg
                pos += 18
    return out, pos + (pos & 1)


def palette_sh(grid: LightGrid, color_index: int):
    """The spherical harmonics of a colour index (R_BlendLightGridColorsSH with one sample)."""
    return decode_spherical_harmonics(grid.range_exponents, grid.palette, grid.palette_entry_address[color_index])[0]


def evaluate_sh(coeffs, direction):
    """The light from a unit direction (x, y, z), linear RGB, as R_SphericalHarmonicsToColorsLDR (Store: the 2-band
    branch, r_lightGridSHBands 0) evaluates it: c0 + c1 x + c2 y + c3 z + c4 zx + c5 zy + c6 xy + c7 (3z² - 1)
    + c8 (x² - y²), the basis constants folded into the coefficients. The game's 8-bit grid colours are
    min(255, 127.5 sqrt(max(L, 2^-18))): 1.0 is the middle of the range, 4.0 the top."""
    import numpy as np
    x, y, z = (float(v) for v in direction)
    basis = np.array([1, x, y, z, z * x, z * y, x * y, 3 * z * z - 1, x * x - y * y], np.float32)
    return basis @ np.asarray(coeffs, np.float32)


def world_to_grid(pos):
    """A world position as the grid point below it and the fractions towards the next one
    (R_LightGridLookup_Compressed): 32 units per step in x and y, 64 in z, origin at -131072."""
    import math
    g, f = [], []
    for v, shift, unit in ((pos[0], 5, 0.03125), (pos[1], 5, 0.03125), (pos[2], 6, 0.015625)):
        i = (int(math.floor(v)) + 0x20000) >> shift
        g.append(i)
        f.append((v + 131072.0) * unit - i)
    return tuple(g), tuple(f)


def sample_sh(grid: LightGrid, pos):
    """The spherical harmonics at a world position: the 8 grid points around it, trilinear weights (corner i is
    (i >> 2, i >> 1 & 1, i & 1) in x, y, z, as the game orders them), samples without colour dropped and the rest
    renormalised. An approximation of GetLightingAtPoint: the game also tests each sample's visibility
    (R_IsValidLightGridSample, the voxel bits, the light environment), which is not modelled. None where no corner
    has colour."""
    import numpy as np
    (gx, gy, gz), (fx, fy, fz) = world_to_grid(pos)
    acc, total = np.zeros((9, 3), np.float32), 0.0
    for i in range(8):
        dx, dy, dz = i >> 2, i >> 1 & 1, i & 1
        w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
        if w <= 0:
            continue
        ci, _, _ = get_light_grid(grid.tree, (gx + dx, gy + dy, gz + dz))
        if ci == 0 or ci >= len(grid.palette_entry_address):
            continue
        acc += np.float32(w) * palette_sh(grid, ci)
        total += w
    return acc / np.float32(total) if total > 0 else None
