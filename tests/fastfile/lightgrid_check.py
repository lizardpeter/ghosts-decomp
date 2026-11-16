"""Check tools/fastfile/lightgrid.py against the game: the Store build's own loader (store_emu.py) loads a real map
zone, the decoder's lookup tables are built by the game's initialiser (1406466E0, as at startup), and the game's
R_GetLightGrid (140646380) is called on every cell of a sample of occupied blocks of the light grid tree. Its
GfxLightGridRaw (colorIndex, lightIndex, voxel) must equal lightgrid.get_light_grid's.

    python3 tests/fastfile/lightgrid_check.py <map.ff> [blocks]      (needs $IW6_ORIGINALS)

Used by tests/fastfile/test_lightgrid.py (with IW6_FASTFILES).
"""
import random
import struct
import sys
from pathlib import Path

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import iw6ff  # noqa: E402
import lightgrid  # noqa: E402
import store_emu  # noqa: E402

R_GET_LIGHT_GRID = 0x140646380
R_INIT_LIGHT_GRID_DECODER_TABLES = 0x1406466E0
ASSET_GFXWORLD = 0x1A
LIGHT_GRID = 0x138        # GfxWorld.lightGrid
TREE = 0x5D0              # GfxLightGrid.tree


class Mem:
    def __init__(self, L):
        self.L = L

    def read(self, a, n):
        return bytes(self.L.mu.mem_read(a, n))


def occupied_blocks(tree):
    """(bx, by, bz) of every leaf block of the tree, by walking the node table."""
    out = []

    def walk(index, depth, bx, by, bz):
        entry = tree.node_table[index]
        mask = entry >> 24
        bit = 1 << (tree.max_depth - depth)
        for child in range(8):
            if not mask >> child & 1:
                continue
            nx, ny, nz = bx | (bit if child & 1 else 0), by | (bit if child & 2 else 0), bz | (bit if child & 4 else 0)
            if depth < tree.max_depth:
                walk((entry & 0xFFFFFF) + lightgrid.popcount(mask & ((1 << child) - 1)), depth + 1, nx, ny, nz)
            else:
                out.append((nx, ny, nz))
    if tree.node_count:
        walk(0, 0, 0, 0, 0)
    return out


def load_world(ff: bytes, name: str):
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    L.load(ff, name)
    # the pool copies of the linked headers, in link order (headers live in a reused block, so the copy is the
    # asset's final header)
    worlds, at = [], store_emu.POOL
    for t, h, n in L.linked:
        at = (at + 15) & ~15
        if t == ASSET_GFXWORLD:
            worlds.append(at)
        at += store_emu.TYPE_SIZE[t]
    if not worlds:
        raise ValueError(f"{name}: no GfxWorld")
    return L, worlds[0]


def compare(ff: bytes, name: str, blocks: int = 500, seed: int = 1):
    """[(coord, game, reader)] of the differences, and the number of cells compared."""
    L, world = load_world(ff, name)
    mu = L.mu
    tree_at = world + LIGHT_GRID + TREE
    tree = lightgrid.read_tree(Mem(L), tree_at)
    args = store_emu.SCRATCH + 0x80000

    def call(va, *regs):
        sp = store_emu.STACK + store_emu.STACK_SIZE - 0x1000 - 8
        mu.mem_write(sp, struct.pack("<Q", store_emu.SENTINEL))
        mu.reg_write(UC_X86_REG_RSP, sp)
        for reg, v in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9), regs):
            mu.reg_write(reg, v)
        mu.emu_start(va, store_emu.SENTINEL)

    call(R_INIT_LIGHT_GRID_DECODER_TABLES)
    rng = random.Random(seed)
    sample = occupied_blocks(tree)
    sample = rng.sample(sample, min(blocks, len(sample)))
    diffs, cells = [], 0
    for bx, by, bz in sample:
        for cy in range(4):
            for cx in range(4):
                c = (tree.coord_min[0] + 4 * bx + cx, tree.coord_min[1] + 4 * by + cy, tree.coord_min[2] + bz)
                mu.mem_write(args, struct.pack("<HHH", *c) + b"\0" * 26)
                call(R_GET_LIGHT_GRID, tree_at, args, args + 0x10, 0)
                game = struct.unpack("<IHB", bytes(mu.mem_read(args + 0x10, 7)))
                mine = lightgrid.get_light_grid(tree, c)
                cells += 1
                if game != mine:
                    diffs.append((c, game, mine))
    return diffs, cells


if __name__ == "__main__":
    path = Path(sys.argv[1])
    d, n = compare(path.read_bytes(), path.stem, int(sys.argv[2]) if len(sys.argv) > 2 else 500)
    for c, g, m in d[:20]:
        print(f"{c}: game {g} reader {m}")
    print(f"{path.stem}: {n} cells, {len(d)} differences")
    sys.exit(1 if d else 0)
