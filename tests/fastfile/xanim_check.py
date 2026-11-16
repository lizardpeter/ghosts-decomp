"""Check tools/fastfile/xanim.py against the game.

1. Loader: the Store build's own loader (store_emu.py) loads a real zone; at the n-th Load_XAnimPartsPtr (14035D3D0)
   the stream state is handed to xanim.load_xanim_parts_ptr, and the game's state when the call returns must be the
   same (zone and block positions, block memory, asset pool), as world_check.py does for the GfxWorld.
2. Evaluator: after the game loaded the zone, its XAnimCalcAbsDeltaParts (140559750, the root motion), XAnimCalcParts (14055EE30 under 256 frames, 140560280 from 256)
   and XAnimCalcNonLoopEnd (140563620, the last frame) are called on every animation at a set of times, and what
   they accumulate must equal xanim.calc_abs_delta's and xanim.calc_parts's bit for bit.

    python3 tests/fastfile/xanim_check.py <zone.ff> [loader occurrences, e.g. 0,5]   (needs $IW6_ORIGINALS)

Used by tests/fastfile/test_xanim.py (with IW6_FASTFILES).
"""
import random
import struct
import sys
from pathlib import Path

import numpy as np
from unicorn.x86_const import (UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP,
                               UC_X86_REG_XMM1, UC_X86_REG_XMM2, UC_X86_REG_XMM3)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import iw6ff  # noqa: E402
import store_emu  # noqa: E402
import world_check  # noqa: E402
import xanim  # noqa: E402

LOAD_XANIMPARTS_PTR = 0x14035D3D0
VAR_XANIMPARTS_PTR = 0x144425998
XANIM_CALC_PARTS_U8 = 0x14055EE30
XANIM_CALC_PARTS_U16 = 0x140560280
XANIM_CALC_NON_LOOP_END = 0x140563620
XANIM_CALC_ABS_DELTA_PARTS = 0x140559750
TIMES = (0.0, 0.25, 0.5, 0.999, 1.0)
# g_keepXYZ (the servers' universal/com_vector4_const.cpp): {~0, ~0, ~0, 0}, set by a dynamic initializer at startup,
# which the emulator doesn't run; the translation code masks with it
G_KEEP_XYZ = 0x149B76820


class Mem:
    def __init__(self, L):
        self.L = L

    def read(self, a, n):
        return bytes(self.L.mu.mem_read(a, n))


def compare_loader(ff: bytes, name: str, occurrence: int = 0):
    """The reader against the game for the occurrence-th animation the zone loads inline."""
    return world_check.compare(ff, name, LOAD_XANIMPARTS_PTR, VAR_XANIMPARTS_PTR, xanim.load_xanim_parts_ptr,
                               occurrence=occurrence, at_return=True)


def load_zone(ff: bytes, name: str):
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    L.load(ff, name)
    anims, at = [], store_emu.POOL
    for t, h, n in L.linked:
        at = (at + 15) & ~15
        if t == xanim.ASSET_XANIMPARTS:
            anims.append(at)
        at += store_emu.TYPE_SIZE[t]
    return L, anims


def compare_calc(ff: bytes, name: str, extra_times: int = 3, seed: int = 1):
    """[(animation, time, game, reader)] of the differences, and the number of (animation, time) pairs compared."""
    L, anims = load_zone(ff, name)
    mu = L.mu
    mem = Mem(L)
    work = store_emu.SCRATCH + 0x80000
    to_model, mats, ignore = work, work + 0x100, work + 0x100 + 0x2000
    mu.mem_write(to_model, bytes(range(256)))
    mu.mem_write(ignore, bytes(32))
    mu.mem_write(G_KEEP_XYZ, struct.pack("<4I", 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0))
    rng = random.Random(seed)
    diffs, pairs = [], 0
    for a in anims:
        anim = xanim.read_xanim(mem, a)
        total = anim.bone_count[xanim.ALL]
        times = list(TIMES) + [rng.random() for _ in range(extra_times)]
        for t in times:
            mu.mem_write(mats, bytes(0x20 * 256))
            sp = store_emu.STACK + store_emu.STACK_SIZE - 0x1000 - 8
            last = t == 1.0 or anim.numframes == 0
            mu.reg_write(UC_X86_REG_RCX, a)
            mu.reg_write(UC_X86_REG_RDX, to_model)
            if last:   # XAnimCalcNonLoopEnd(parts, animToModel, weight, rotTransArray, ignorePartBits)
                mu.mem_write(sp, struct.pack("<Q", store_emu.SENTINEL) + bytes(0x20) + struct.pack("<Q", ignore))
                mu.reg_write(UC_X86_REG_XMM2, struct.unpack("<I", struct.pack("<f", 1.0))[0])
                mu.reg_write(UC_X86_REG_R9, mats)
                va = XANIM_CALC_NON_LOOP_END
            else:      # XAnimCalcParts<T>(parts, animToModel, time, weight, rotTransArray, ignorePartBits)
                mu.mem_write(sp, struct.pack("<Q", store_emu.SENTINEL) + bytes(0x20) + struct.pack("<QQ", mats, ignore))
                mu.reg_write(UC_X86_REG_XMM2, struct.unpack("<I", struct.pack("<f", t))[0])
                mu.reg_write(UC_X86_REG_XMM3, struct.unpack("<I", struct.pack("<f", 1.0))[0])
                va = XANIM_CALC_PARTS_U8 if anim.numframes < 0x100 else XANIM_CALC_PARTS_U16
            mu.reg_write(UC_X86_REG_RSP, sp)
            mu.emu_start(va, store_emu.SENTINEL)
            game = np.frombuffer(bytes(mu.mem_read(mats, 0x20 * 256)), np.float32).reshape(256, 8)
            mine = xanim.calc_parts(anim, float(np.float32(t)), bones=256)
            pairs += 1
            if game.tobytes() != mine.tobytes():
                diffs.append((anim.name, t, game[:total], mine[:total]))
            # XAnimCalcAbsDeltaParts(parts, weight, time, XAnimRotPos *): the root motion
            mu.mem_write(mats, bytes(0x20))
            mu.mem_write(sp, struct.pack("<Q", store_emu.SENTINEL))
            mu.reg_write(UC_X86_REG_RCX, a)
            mu.reg_write(UC_X86_REG_XMM1, struct.unpack("<I", struct.pack("<f", 1.0))[0])
            mu.reg_write(UC_X86_REG_XMM2, struct.unpack("<I", struct.pack("<f", t))[0])
            mu.reg_write(UC_X86_REG_R9, mats)
            mu.reg_write(UC_X86_REG_RSP, sp)
            mu.emu_start(XANIM_CALC_ABS_DELTA_PARTS, store_emu.SENTINEL)
            game = np.frombuffer(bytes(mu.mem_read(mats, 0x20)), np.float32).reshape(1, 8)
            mine = xanim.calc_abs_delta(anim, float(np.float32(t))).reshape(1, 8)
            pairs += 1
            if game.tobytes() != mine.tobytes():
                diffs.append((anim.name + " (root motion)", t, game, mine))
    return diffs, pairs


if __name__ == "__main__":
    path = Path(sys.argv[1])
    ff = path.read_bytes()
    bad = False
    if len(sys.argv) > 2:
        for occ in map(int, sys.argv[2].split(",")):
            d, st = compare_loader(ff, path.stem, occ)
            print(f"loader, animation {occ}: " + ("; ".join(d) if d else "reader == game"))
            bad |= bool(d)
    d, n = compare_calc(ff, path.stem)
    for name, t, g, m in d[:10]:
        rows = np.nonzero((g != m).any(axis=1))[0]
        r = rows[0]
        print(f"{name} t={t}: {len(rows)} bones differ; bone {r}: game {g[r].tolist()} reader {m[r].tolist()}")
    print(f"{path.stem}: {n} (animation, time) pairs, {len(d)} differences")
    sys.exit(1 if bad or d else 0)
