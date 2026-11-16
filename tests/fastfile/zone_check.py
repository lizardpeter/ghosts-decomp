"""Check tools/fastfile's loaders against the game, one asset at a time or a whole zone.

1. One asset: at the occurrence-th call of a type's Load_*Ptr the stream state is handed to the Python loader, and the
   game's state when the call returns must be the same (world_check.compare): zone and block positions, block memory,
   asset pool.
2. Whole zone: the game loads the zone in the emulator; iw6ff.read_fastfile, with every loader (loaders.register_all)
   and the game's block bases, walks the same zone; every block's memory and the asset pool must then be the same.

    python3 tests/fastfile/zone_check.py <zone.ff> <type>:<calls> ...   e.g. 0x39:0 0x3a:0,1
    python3 tests/fastfile/zone_check.py <zone.ff> --full
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import iw6ff  # noqa: E402
import loaders  # noqa: E402
import mapfx  # noqa: E402
import postfx  # noqa: E402
import sound_check  # noqa: E402
import store_emu  # noqa: E402
import weapon  # noqa: E402
import xanim  # noqa: E402
import world_check  # noqa: E402

register = loaders.register_all
register()

# type -> (Store Load_*Ptr, its var<Type>Ptr, the Python loader)
TYPES = {
    0x38: (0x14034B8C0, 0x1444253D8, postfx.load_colorization_ptr),
    0x39: (0x14034BAD0, 0x1444253E8, postfx.load_colorization_set_ptr),
    0x3A: (0x140358440, 0x1444253F8, postfx.load_tone_mapping_ptr),
    0x22: (0x14035A240, 0x144426350, weapon.load_attachment_ptr),
    0x23: (0x14035ACA0, 0x144426BF8, weapon.load_weapon_ptr),
    0x31: (0x1403585D0, 0x144425F98, weapon.load_tracer_ptr),
    0x32: (0x140359150, 0x144425460, weapon.load_vehicle_ptr),
    0x20: (0x14034A880, 0x1444254D0, xanim.load_animation_class_ptr),
    0x15: (0x1403520B0, 0x144425B90, mapfx.load_glass_world_ptr),
    0x19: (0x14034E9B0, 0x144426DC0, mapfx.load_fx_world_ptr),
    0x26: (0x14034E4E0, 0x144425AE0, mapfx.load_impact_table_ptr),
    0x27: (0x1403582C0, 0x144425AF8, mapfx.load_surface_fx_table_ptr),
}


def compare_asset(ff, name, asset_type, occurrence=0):
    entry, var, load = TYPES[asset_type]
    return world_check.compare(ff, name, entry, var, load, occurrence=occurrence, at_return=True)


def _resolve(mine, game, n, copies, L, out):
    """Markers sound.load_xa2_sound stored for the engine's copies -> the game's address, if its copy matches."""
    import numpy as np
    words = np.frombuffer(bytes(mine[:n]), np.uint64)
    for k in np.nonzero((words >> np.uint64(32)) == np.uint64(sound_check.MARK >> 32))[0]:
        j, v = 8 * int(k), int(words[k])
        if v - sound_check.MARK >= len(copies):
            continue
        g = int.from_bytes(game[j:j + 8], "little")
        data = copies[v - sound_check.MARK]
        heap = store_emu.CRT_HEAP <= g < store_emu.CRT_HEAP + store_emu.CRT_HEAP_SIZE
        if heap and bytes(L.mu.mem_read(g, len(data))) == data:
            mine[j:j + 8] = game[j:j + 8]
        else:
            out.append(f"loaded sound data at {j:#x}: the game's {g:#x} is no copy of the loaded data")


def full(ff, name):
    """Differences between the whole zone as the game loaded it and as iw6ff.read_fastfile walks it (with the game's
    block bases); and the walk's Zone."""
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    L.load(ff, name)
    game = world_check.Capture(L, store_emu.SCRATCH + 0x100, 0)
    bases = [d or ((i + 1) << 40) for i, (d, _) in enumerate(game.blocks)]
    # loaded sounds: the engine copies their data to memory it allocates (sound_check.py); the reader stores a
    # marker, resolved below to the game's address when the game's copy holds the same bytes
    copies = []

    def engine_copy(at, temp, size, s=None):
        copies.append(bytes(z_stream[0].read(temp, size)))
        return sound_check.MARK | (len(copies) - 1)
    z_stream = [None]
    init = iw6ff.Stream.__init__

    def stream_init(self, *a, **k):
        init(self, *a, **k)
        z_stream[0] = self
        self.engine_copy = engine_copy
    iw6ff.Stream.__init__ = stream_init
    try:
        z = iw6ff.read_fastfile(ff, name, bases=bases, pool_base=store_emu.POOL)
    finally:
        iw6ff.Stream.__init__ = init
    out = []
    s = z.stream
    for i in range(7):
        n = min(len(s.mem[i]), len(game.mem[i])) // 8 * 8
        _resolve(s.mem[i], game.mem[i], n, copies, L, out)
    _resolve(s.pool, game.pool, min(len(s.pool), len(game.pool)) // 8 * 8, copies, L, out)
    if not z.complete:
        out.append(f"the reader stopped at asset {z.stopped_at} of {len(z.assets)} "
                   f"(type {z.assets[z.stopped_at].type:#x})")
    for i in range(7):
        if s.pos[i] != game.pos[i]:
            out.append(f"{iw6ff.BLOCK_NAMES[i]} position: reader {s.pos[i]:#x} game {game.pos[i]:#x}")
        hi = max(s.pos[i], game.pos[i])
        bad = world_check._differences(bytes(s.mem[i][:hi]), game.mem[i][:hi], 0, L.com)
        if bad:
            out.append(f"{iw6ff.BLOCK_NAMES[i]} block differs at {bad[0]:#x} ({len(bad)} words): " + ", ".join(
                f"{w:#x} reader {bytes(s.mem[i][w:w + 8]).hex()} game {game.mem[i][w:w + 8].hex()}" for w in bad[:4]))
    # XModel pool copies: DB_XModelSurfsFixup (link time) rewrites numsurfs (+0xA), the flags (+0x1F3) and each LOD's
    # counts and surface pointers; the emulator's stand-in link leaves the fixup to the zone copy (world_check), so the
    # game's pool copy keeps the zone's values. They agree unless a model's XModelSurfs is another zone's, which the
    # reader cannot see (it counts 0 surfaces); those fields are taken from the reader.
    game_pool = bytearray(game.pool)
    for t, addr in s.links:
        if t == 4:
            o = addr - store_emu.POOL
            fields = [(0xA, 1), (0x1F3, 1)] + [(0x70 + 0x40 * k + 4, 4) for k in range(6)] + \
                     [(0x70 + 0x40 * k + 0x10, 0x28) for k in range(6)]
            for off, n in fields:
                if o + off + n <= min(len(game_pool), len(s.pool)):
                    game_pool[o + off:o + off + n] = s.pool[o + off:o + off + n]
    bad = world_check._differences(bytes(s.pool), bytes(game_pool), 0, L.com)
    if bad:
        out.append(f"asset pool differs at {bad[0]:#x} ({len(bad)} words; reader {len(s.pool):#x} bytes, "
                   f"game {len(game.pool):#x}): " + ", ".join(
                       f"{w:#x} reader {bytes(s.pool[w:w + 8]).hex()} game {bytes(game_pool[w:w + 8]).hex()}"
                       for w in bad[:6]))
    return out, z


if __name__ == "__main__":
    path = Path(sys.argv[1])
    ff = path.read_bytes()
    bad = False
    for arg in sys.argv[2:]:
        if arg == "--full":
            d, z = full(ff, path.stem)
            print(f"whole zone ({len(z.assets)} assets): " + ("; ".join(d[:6]) if d else "reader == game"), flush=True)
            bad |= bool(d)
            continue
        t, calls = arg.split(":")
        for occ in map(int, calls.split(",")):
            d, _ = compare_asset(ff, path.stem, int(t, 16), occ)
            print(f"type {t} call {occ}: " + ("; ".join(d[:5]) if d else "reader == game"), flush=True)
            bad |= bool(d)
    sys.exit(1 if bad else 0)
