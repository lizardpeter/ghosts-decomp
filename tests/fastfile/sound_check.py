"""Check tools/fastfile/sound.py's loaders against the game, and list what a zone's sounds are.

1. Loader: as world_check.py does for the GfxWorld: at a chosen call of Load_snd_alias_list_ptr (140361F10) or
   Load_LoadedSoundPtr (140352600) the stream state is handed to sound.py's loader, and the game's state when the
   call returns must be the same (zone and block positions, block memory, asset pool).
2. Survey: after the game loaded the zone, every alias list is read (sound.read_alias_list) and the sound files
   counted by kind and pak.

    python3 tests/fastfile/sound_check.py <zone.ff> [alias-list calls, e.g. 0,10] [loaded-sound calls]
    python3 tests/fastfile/sound_check.py <zone.ff> --extract <out dir> [<soundfile pak dir>]
"""
import collections
import struct
import sys

import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import iw6ff  # noqa: E402
import sound  # noqa: E402
import store_emu  # noqa: E402
import world_check  # noqa: E402

LOAD_ALIAS_LIST_PTR, VAR_ALIAS_LIST_PTR = 0x140361F10, 0x144426678
LOAD_LOADED_SOUND_PTR, VAR_LOADED_SOUND_PTR = 0x140352600, 0x1444265E8


class Mem:
    def __init__(self, mu):
        self.mu = mu

    def read(self, a, n):
        return bytes(self.mu.mem_read(a, n))


MARK = 0x5EC0_0000_0000_0000


def _compare(ff, name, entry, var, load, occurrence):
    """The game's XA2Sound data pointer is its own copy in memory the engine allocated (in the emulator, its CRT
    heap): an address no reader can predict. The reader stores a marker there and keeps the bytes it loaded; a
    marker the game has a heap address for, whose bytes there are the same, is taken as the game's address."""
    copies = []

    def wrapped(s, *args, **kw):
        def copy(at, temp, size):
            copies.append(s.read(temp, size))
            return MARK | (len(copies) - 1)
        s.engine_copy = copy
        return load(s, *args, **kw)

    d, st = world_check.compare(ff, name, entry, var, wrapped, occurrence=occurrence, at_return=True)
    if st is None:
        return d, st
    before, after, s = st
    mu = world_check.compare.loader.mu
    bad = []

    def resolve(mine: bytearray, game: bytes):
        n = len(mine) // 8
        words = np.frombuffer(bytes(mine[:8 * n]), np.uint64)
        for k in np.nonzero((words >> np.uint64(32)) == np.uint64(MARK >> 32))[0]:
            j, v = 8 * int(k), int(words[k])
            if v - MARK >= len(copies):
                continue
            g = int.from_bytes(game[j:j + 8], "little")
            data = copies[v - MARK]
            heap = store_emu.CRT_HEAP <= g < store_emu.CRT_HEAP + store_emu.CRT_HEAP_SIZE
            if heap and bytes(mu.mem_read(g, len(data))) == data:
                mine[j:j + 8] = game[j:j + 8]
            else:
                bad.append(f"XA2Sound data: the game's {g:#x} is no copy of the loaded data")
    for i in range(7):
        if isinstance(s.mem[i], bytearray):
            resolve(s.mem[i], bytes(after.mem[i]).ljust(len(s.mem[i]), b"\0"))
    resolve(s.pool, bytes(after.pool).ljust(len(s.pool), b"\0"))
    return world_check.differences(before, after, s, world_check.compare.loader) + bad, st


def compare_alias_list(ff, name, occurrence=0):
    return _compare(ff, name, LOAD_ALIAS_LIST_PTR, VAR_ALIAS_LIST_PTR, sound.load_alias_list_ptr, occurrence)


def compare_loaded_sound(ff, name, occurrence=0):
    return _compare(ff, name, LOAD_LOADED_SOUND_PTR, VAR_LOADED_SOUND_PTR, sound.load_loaded_sound_ptr, occurrence)


def load_zone(ff, name):
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    L.load(ff, name)
    assets, at = [], store_emu.POOL
    for t, h, n in L.linked:
        at = (at + 15) & ~15
        assets.append((t, at, n))
        at += store_emu.TYPE_SIZE[t]
    return L, assets


def survey(ff, name):
    L, assets = load_zone(ff, name)
    mem = Mem(L.mu)
    lists = []
    for t, a, n in assets:
        if t == sound.ASSET_SOUND:
            lists.append(sound.read_alias_list(mem, a))
    return L, lists


def extract(ff, name, out_dir, pak_dir=None):
    """sound.extract on the zone as the game loaded it (all of a zone: tools/fastfile's reader doesn't load every
    asset type yet)."""
    L, assets = load_zone(ff, name)
    return sound.extract(Mem(L.mu), [a for t, a, n in assets if t == sound.ASSET_SOUND], out_dir, pak_dir)


if __name__ == "__main__":
    path = Path(sys.argv[1])
    ff = path.read_bytes()
    if len(sys.argv) > 3 and sys.argv[2] == "--extract":
        written, missing = extract(ff, path.stem, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
        paks = collections.Counter(m[1].pak for m in missing if m[1] is not None and m[1].pak)
        print(f"{len(written)} files written; {len(missing)} aliases' audio elsewhere; paks needed {dict(paks)}")
        sys.exit(0)
    bad = False
    for arg, fn, what in ((2, compare_alias_list, "alias list"), (3, compare_loaded_sound, "loaded sound")):
        if len(sys.argv) > arg and sys.argv[arg]:
            for occ in map(int, sys.argv[arg].split(",")):
                d, st = fn(ff, path.stem, occ)
                print(f"{what} call {occ}: " + ("; ".join(d[:5]) if d else "reader == game"), flush=True)
                bad |= bool(d)
    L, lists = survey(ff, path.stem)
    kinds = collections.Counter(a.file.kind if a.file else None for _, aliases in lists for a in aliases)
    paks = collections.Counter(a.file.pak for _, aliases in lists for a in aliases if a.file and a.file.pak)
    print(f"{len(lists)} alias lists, {sum(len(x) for _, x in lists)} aliases; files {dict(kinds)}; paks {dict(paks)}")
    sys.exit(1 if bad else 0)
