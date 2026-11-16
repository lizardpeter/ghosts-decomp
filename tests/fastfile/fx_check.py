"""Check tools/fastfile/fx.py's loaders against the game, and list what a zone's effects are made of.

1. Loader: as world_check.py does for the GfxWorld: at a chosen call of Load_FxEffectDefHandle (14034D120) the stream
   state is handed to fx.load_effect_ptr, and the game's state when the call returns must be the same (zone and
   block positions, block memory, asset pool).
2. Survey: after the game loaded the zone, every effect is read (fx.read_effect) and its elements counted by type.

    python3 tests/fastfile/fx_check.py <zone.ff> [effect calls, e.g. 0,10,100]
"""
import collections
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import fx  # noqa: E402
import image  # noqa: E402
import iw6ff  # noqa: E402
import material  # noqa: E402
import store_emu  # noqa: E402
import world_check  # noqa: E402
import xmodel  # noqa: E402

LOAD_FX_HANDLE, VAR_FX_HANDLE = 0x14034D120, 0x1444260F8

fx.register({}, material_ptr=material.load_material_ptr,
            xmodel_ptr=lambda s, f: xmodel.load_xmodel_ptr(s, f, material.load_material_ptr),
            image_ptr=image.load_gfx_image_ptr)


class Mem:
    def __init__(self, mu):
        self.mu = mu

    def read(self, a, n):
        return bytes(self.mu.mem_read(a, n))


def compare_effect(ff, name, occurrence=0):
    return world_check.compare(ff, name, LOAD_FX_HANDLE, VAR_FX_HANDLE, fx.load_effect_ptr, occurrence=occurrence,
                               at_return=True)


LOAD_FX_FROM_NAME = 0x140371ED0


def load_zone(ff, name):
    """The zone as the game loads it, and the names Load_FxEffectDefFromName (140371ED0) saw (field address ->
    name): the emulator registers no assets by name, so the handles it leaves are default entries."""
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    L.ref_names = {}

    def from_name(loader):
        from unicorn.x86_const import UC_X86_REG_RCX
        field = loader.mu.reg_read(UC_X86_REG_RCX)
        p = struct.unpack("<Q", bytes(loader.mu.mem_read(field, 8)))[0]
        if p:
            loader.ref_names[field] = fx._cstr(Mem(loader.mu), p)
    L.load(ff, name, hooks={LOAD_FX_FROM_NAME: from_name})
    assets, at = [], store_emu.POOL
    for t, h, n in L.linked:
        at = (at + 15) & ~15
        assets.append((t, at, n))
        at += store_emu.TYPE_SIZE[t]
    return L, assets


def survey(ff, name):
    L, assets = load_zone(ff, name)
    mem = Mem(L.mu)
    return L, [fx.read_effect(mem, a, L.ref_names) for t, a, n in assets if t == fx.ASSET_FX]


if __name__ == "__main__":
    path = Path(sys.argv[1])
    ff = path.read_bytes()
    bad = False
    if len(sys.argv) > 2 and sys.argv[2]:
        for occ in map(int, sys.argv[2].split(",")):
            d, st = compare_effect(ff, path.stem, occ)
            print(f"effect call {occ}: " + ("; ".join(d[:5]) if d else "reader == game"), flush=True)
            bad |= bool(d)
    L, effects = survey(ff, path.stem)
    types = collections.Counter(e.type_name for f in effects for e in f.elems)
    ext = collections.Counter(e.extended["kind"] for f in effects for e in f.elems if e.extended)
    print(f"{len(effects)} effects, {sum(len(f.elems) for f in effects)} elements; types {dict(types)}; "
          f"extended {dict(ext)}")
    sys.exit(1 if bad else 0)
