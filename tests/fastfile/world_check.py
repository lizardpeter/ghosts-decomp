"""Check tools/fastfile/gfxworld.py against the game: the Store build's own loader (store_emu.py) loads a real map
zone; when it reaches Load_GfxWorldPtr (140351D10) the stream state (zone position, block positions, the stream
position stack, the block memory and the asset pool so far) is handed to the Python reader, which loads the
GfxWorld; the game's state when Load_GfxWorldPtr returns must then be the same: the zone position, every block
position, every byte of block memory and the linked pool header.

    python3 tests/fastfile/world_check.py <map.ff>      (needs $IW6_ORIGINALS)

Used by tests/fastfile/test_gfxworld.py (with IW6_FASTFILES) and by hand while mapping the format.
"""
import struct
import sys
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RDX, UC_X86_REG_RSP

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import iw6ff  # noqa: E402
import store_emu  # noqa: E402

LOAD_GFXWORLD_PTR = 0x140351D10
AFTER_LOAD_XASSET = 0x1403495DE      # the instruction after Load_XAsset's call in the asset loop
DB_READ_XFILE = 0x140349B80
G_STREAM_POS = 0x145F06610
G_STREAM_POS_INDEX = 0x145F06650
G_STREAM_POS_STACK = 0x145F06660
G_STREAM_POS_STACK_INDEX = 0x145F06A60
VAR_GFXWORLD_PTR = 0x144426920
G_STREAM_ROW_CURSOR = 0x144310BF4   # sub_1403492E0's index into the streamed-image rows


class Capture:
    """The game's stream state at a point of the run."""

    def __init__(self, L, zonemem, read_total, var=VAR_GFXWORLD_PTR):
        mu = L.mu
        u64 = L.u64
        self.blocks = [struct.unpack_from("<QQ", bytes(mu.mem_read(zonemem + 16 * i, 16))) for i in range(7)]
        self.index = struct.unpack("<I", bytes(mu.mem_read(G_STREAM_POS_INDEX, 4)))[0]
        cur = u64(G_STREAM_POS)
        arr = [u64(store_emu.G_STREAM_POS_ARRAY + 8 * i) for i in range(7)]
        arr[self.index] = cur
        self.pos = [(a - d) if d else 0 for a, (d, _) in zip(arr, self.blocks)]
        depth = struct.unpack("<I", bytes(mu.mem_read(G_STREAM_POS_STACK_INDEX, 4)))[0]
        self.stack = [struct.unpack_from("<QI", bytes(mu.mem_read(G_STREAM_POS_STACK + 16 * k, 12)))
                      for k in range(depth)]
        self.mem = [bytes(mu.mem_read(d, size)) if d else b"" for d, size in self.blocks]
        self.pool = bytes(mu.mem_read(store_emu.POOL, L.pool_next - store_emu.POOL))
        self.read_total = read_total
        self.varptr = u64(var)
        self.rows_used = struct.unpack("<I", bytes(mu.mem_read(G_STREAM_ROW_CURSOR, 4)))[0]
        self.string_table = u64(store_emu.G_VAR_XASSET_LIST + 8)   # XAssetList.stringList.strings
        # the assets linked so far, as (type, pool copy) in link order (the pool copies are 16-byte aligned, one
        # after another, as Stream.link places them)
        self.links, at = [], store_emu.POOL
        for t, _, _ in L.linked:
            at = (at + 15) & ~15
            self.links.append((t, at))
            at += store_emu.TYPE_SIZE[t]


def run_game(ff: bytes, name: str, entry: int = LOAD_GFXWORLD_PTR, var: int = VAR_GFXWORLD_PTR, occurrence: int = 0,
             at_return: bool = False):
    """Load the zone in the emulator; returns (capture at the occurrence-th call of the asset's Load_*Ptr `entry`,
    whose pointer variable is `var`, capture when it returns, loader). With at_return the second capture is taken at
    the call's own return address (for an asset loaded from inside another asset's loader), else when Load_XAsset
    returns."""
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    zonemem = store_emu.SCRATCH + 0x100
    state = {"read": 0, "before": None, "after": None, "ret": None, "seen": 0}

    def on_read(L_):
        state["read"] += L_.mu.reg_read(UC_X86_REG_RDX)

    def on_world(L_):
        state["seen"] += 1
        if state["before"] is None and state["seen"] == occurrence + 1:
            state["before"] = Capture(L_, zonemem, state["read"], var)
            if at_return:   # the asset's Load_*Ptr may be called from another asset's loader: stop at its return
                rsp = L_.mu.reg_read(UC_X86_REG_RSP)
                ret = L_.u64(rsp)

                def on_ret(mu, address, size, user):
                    if state["after"] is None and mu.reg_read(UC_X86_REG_RSP) == rsp + 8:
                        state["after"] = Capture(L_, zonemem, state["read"], var)
                L_.mu.hook_add(UC_HOOK_CODE, on_ret, begin=ret, end=ret)
                L_.mu.ctl_remove_cache(ret, ret + 1)   # code already translated there wouldn't see the new hook

    def on_next(L_):
        # Load_XAsset tail-jumps to the type's Load_*Ptr, which returns here (in Load_XAssetListCustom)
        if state["after"] is None and state["before"] is not None and not at_return:
            state["after"] = Capture(L_, zonemem, state["read"], var)

    L.load(ff, name, assets=True, hooks={DB_READ_XFILE: on_read, entry: on_world, AFTER_LOAD_XASSET: on_next})
    return state["before"], state["after"], L


def run_reader(ff: bytes, name: str, before: Capture, load=None):
    """The Python reader `load(stream, varptr)` (default gfxworld.load_gfx_world_ptr) from the game's state at the
    asset's Load_*Ptr."""
    import gfxworld
    import image
    import material
    image.register({}, material)
    prefix = iw6ff.read_prefix(ff)
    zone, _ = iw6ff.decompress(ff, prefix, name)
    sizes = [size for _, size in before.blocks]
    bases = [d or ((i + 1) << 40) for i, (d, _) in enumerate(before.blocks)]
    s = iw6ff.Stream(zone, sizes, bases=bases, pool_base=store_emu.POOL)
    s.cursor = before.read_total
    for i, m in enumerate(before.mem):
        s.mem[i][:len(m)] = m
    s.pos = list(before.pos)
    s.index = before.index
    # g_streamPosStack entries: {pos (an address in the block switched to), index (the block switched from)}
    s.stack = []
    for pos, idx in before.stack:
        blk = next((i for i, (d, size) in enumerate(before.blocks) if d and d <= pos <= d + size), None)
        s.stack.append(((pos - before.blocks[blk][0]) if blk is not None else 0, idx))
    s.pool = bytearray(before.pool)
    s.links = list(before.links)
    s.string_table = before.string_table
    st = image.state_of(s)
    st.rows, st.cursor = prefix.stream_images, before.rows_used
    (load or gfxworld.load_gfx_world_ptr)(s, before.varptr)
    return s


def _differences(a: bytes, b: bytes, base: int, com: int):
    """Offsets (from `base`) of the 8-byte words that differ, except D3D11 objects: words where the game stored its
    device object (the emulator's single COM object, store_emu.py) and the reader 0. The game creates some objects
    (material constant buffers) even with r_loadForRenderer off; the reader stores every GPU object as 0."""
    if a == b:
        return []
    n = max(len(a), len(b))
    a, b = bytearray(a.ljust(n, b"\0")), bytearray(b.ljust(n, b"\0"))
    obj = com.to_bytes(8, "little")
    j = b.find(obj)
    while j >= 0:                      # any alignment: some structs keep a pointer at a 4-byte offset
        if a[j:j + 8] == bytes(8):
            b[j:j + 8] = bytes(8)
        j = b.find(obj, j + 1)
    # DB_FindXAssetHeader (sound aliases of scriptables): the emulator's stand-in link registers no names, so the
    # game's lookup always ends in a default entry (store_emu.DEFAULTS); the reader resolves aliases this zone has
    # linked (a pool address) and leaves the others 0. Pointers can sit at 4-byte offsets.
    lo_d, hi_d = store_emu.DEFAULTS, store_emu.DEFAULTS + store_emu.DEFAULTS_SIZE
    lo_p, hi_p = store_emu.POOL, store_emu.POOL + store_emu.POOL_SIZE
    j = (4 - base % 4) % 4
    while j + 8 <= n:
        v = int.from_bytes(b[j:j + 8], "little")
        r = int.from_bytes(a[j:j + 8], "little")
        if lo_d <= v < hi_d and (r == 0 or lo_p <= r < hi_p):
            b[j:j + 8] = a[j:j + 8]
            j += 8
            continue
        j += 4
    out = []
    for w in range(base & ~7, base + n, 8):
        lo, hi = max(w, base) - base, min(w + 8, base + n) - base
        if a[lo:hi] != b[lo:hi]:
            out.append(max(w, base))
    return out


def compare(ff: bytes, name: str, entry: int = LOAD_GFXWORLD_PTR, var: int = VAR_GFXWORLD_PTR, load=None,
            occurrence: int = 0, at_return: bool = False):
    """The reader against the game for one asset of the zone (default the GfxWorld; the occurrence-th call of its
    Load_*Ptr): differences, and the states."""
    before, after, L = run_game(ff, name, entry, var, occurrence, at_return)
    compare.loader = L
    if before is None:
        return [f"the zone has no asset loaded by {entry:09X}"], None
    s = run_reader(ff, name, before, load)
    return differences(before, after, s, L), (before, after, s)


def differences(before, after, s, L):
    """What differs between the reader's state `s` and the game's `after` (both from `before`)."""
    out = []
    if s.cursor != after.read_total:
        out.append(f"zone position: reader {s.cursor:#x} game {after.read_total:#x} (start {before.read_total:#x})")
    for i in range(7):
        if s.pos[i] != after.pos[i]:
            out.append(f"{iw6ff.BLOCK_NAMES[i]} position: reader {s.pos[i]:#x} game {after.pos[i]:#x} "
                       f"(start {before.pos[i]:#x})")
        lo = before.pos[i]
        hi = max(after.pos[i], s.pos[i])
        a, b = bytes(s.mem[i][lo:hi]), after.mem[i][lo:hi]
        bad = _differences(a, b, lo, L.com)
        if bad:
            first = bad[0]
            out.append(f"{iw6ff.BLOCK_NAMES[i]} block differs at {first:#x} ({len(bad)} words; "
                       f"reader {a[first - lo:first - lo + 8].hex()} game {b[first - lo:first - lo + 8].hex()})")
    if len(s.pool) != len(after.pool):
        out.append(f"asset pool: reader {len(s.pool):#x} bytes, game {len(after.pool):#x}")
    # XModel flags (+0x1F3): the real DB_LinkXAssetEntry1 (14036D830) writes the pool copy back through its
    # argument, so Load_XModelAsset's DB_XModelSurfsFixup (1403712F0) updates the pool copy, as the reader does; the
    # emulator's stand-in link doesn't write back, so there the fixup changes the zone copy and the pool keeps the
    # flag byte from the zone. Compare the pool with those bytes taken from the reader.
    game_pool = bytearray(after.pool)
    for t, addr in s.links:
        if t == 4:
            o = addr - store_emu.POOL + 0x1F3
            if o < len(game_pool):
                game_pool[o] = s.pool[o]
    bad = _differences(bytes(s.pool), bytes(game_pool), 0, L.com)
    if bad:
        out.append(f"asset pool differs at {bad[0]:#x} ({len(bad)} words)")
    return out


if __name__ == "__main__":
    path = Path(sys.argv[1])
    diffs, st = compare(path.read_bytes(), path.stem)
    if st:
        before, after, s = st
        print(f"GfxWorld: zone {before.read_total:#x} -> {after.read_total:#x}, "
              f"virtual {before.pos[3]:#x} -> {after.pos[3]:#x}, runtime {before.pos[2]:#x} -> {after.pos[2]:#x}")
    print("\n".join(diffs) if diffs else "reader == game")
