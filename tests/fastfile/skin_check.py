"""Check tools/fastfile/skin.py against the game's skeleton and skinning code on real models.

The Store build loads a zone in the emulator (store_emu.py). For each chosen XModel and each of a few poses (the
base pose, and every animation of the zone that drives the model, at a few times):

1. the bones' local pose is built in Python (skin.base_local, xanim.calc_parts, skin.normalize_rot_trans);
2. the game's CalcSkelRootBonesNoParentOrDuplicate (140556990) and CalcSkelNonRootBones (1405561D0) turn it into the
   model-space skeleton in emulated memory, and skin.calc_skel in Python: equal bit for bit;
3. the game's R_SkinXModelCmd (1406408A0) skins every surface of LOD 0 with that skeleton (its per-bone transforms
   and R_SkinXSurfaceWeightDQB, 1406436F0), and skin.skin_matrices + skin.skin_vertices in Python: positions equal
   to float rounding (the blend's rsqrtps), packed normals and tangents within one step per component.

    python3 tests/fastfile/skin_check.py <zone.ff> <model name>[,<model name>...]   (needs $IW6_ORIGINALS)
"""
import struct
import sys
from pathlib import Path

import numpy as np
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import iw6ff  # noqa: E402
import skin  # noqa: E402
import store_emu  # noqa: E402
import xanim  # noqa: E402

CALC_SKEL_ROOT = 0x140556990
CALC_SKEL_NON_ROOT = 0x1405561D0
R_SKIN_XMODEL_CMD = 0x1406408A0
DEVICE_LOST = 0x14A3852E8          # dx.deviceLost (byte)
SKINNED_CACHE = 0x14A107BF8        # gfxBuf.skinnedCacheLockAddr
ASSET_XMODEL = 4
WORK = 0x60000000
WORK_SIZE = 0x04000000


class Mem:
    def __init__(self, mu):
        self.mu = mu

    def read(self, a, n):
        return bytes(self.mu.mem_read(a, n))

    def u64(self, a):
        return struct.unpack("<Q", self.read(a, 8))[0]


def _call(mu, va, args, stack_args=()):
    sp = store_emu.STACK + store_emu.STACK_SIZE - 0x1000 - 8
    mu.mem_write(sp, struct.pack("<Q", store_emu.SENTINEL) + bytes(0x20) +
                 b"".join(struct.pack("<Q", a) for a in stack_args))
    for reg, v in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9), args):
        mu.reg_write(reg, v)
    mu.reg_write(UC_X86_REG_RSP, sp)
    mu.emu_start(va, store_emu.SENTINEL)


def load_zone(ff: bytes, name: str):
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    L = store_emu.StoreLoader(max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF))
    L.load(ff, name)
    L.init_vector_constants()
    L.mu.mem_map(WORK, WORK_SIZE)
    assets, at = [], store_emu.POOL
    for t, h, n in L.linked:
        at = (at + 15) & ~15
        assets.append((t, at, n))
        at += store_emu.TYPE_SIZE[t]
    return L, assets


def model_info(mem, a):
    nb, nr = mem.read(a + 8, 2)
    scale = struct.unpack("<f", mem.read(a + 0xC, 4))[0]
    no_scale_words = struct.unpack("<8I", mem.read(a + 0x10, 32))
    no_scale = [bool(no_scale_words[i >> 5] & (0x80000000 >> (i & 31))) for i in range(nb)]
    names = struct.unpack(f"<{nb}I", mem.read(mem.u64(a + 0x30), 4 * nb))
    n = nb - nr
    parents = list(mem.read(mem.u64(a + 0x38), n))
    quats = [struct.unpack_from("<4h", mem.read(mem.u64(a + 0x40), 8 * n), 8 * j) for j in range(n)]
    trans = [struct.unpack_from("<3f", mem.read(mem.u64(a + 0x48), 12 * n), 12 * j) for j in range(n)]
    base_p = mem.u64(a + 0x58)
    base = np.frombuffer(mem.read(base_p, 0x20 * nb), np.float32).reshape(nb, 8).copy()
    return {"bones": nb, "roots": nr, "scale": scale, "no_scale": no_scale, "names": names, "parents": parents,
            "quats": quats, "trans": trans, "base": base, "base_p": base_p}


def lod0_surfaces(mem, a):
    """(XSurface address, vertCount, blendVertCounts, verts bytes, blendVerts u16) of LOD 0."""
    model_surfs = mem.u64(a + 0x70 + 8)                     # lodInfo[0].modelSurfs
    surfs_p = mem.u64(model_surfs + 8)
    count = struct.unpack("<H", mem.read(model_surfs + 0x10, 2))[0]
    out = []
    for i in range(count):
        s = surfs_p + i * XSURFACE_SIZE
        vc = struct.unpack("<H", mem.read(s + 2, 2))[0]
        counts = struct.unpack("<8h", mem.read(s + 8, 16))
        verts = mem.read(mem.u64(s + 0x18), 0x20 * vc)
        n16 = sum(c * (1 + 2 * k) for k, c in enumerate(counts))
        blend = list(struct.unpack(f"<{n16}H", mem.read(mem.u64(s + 0x48), 2 * n16))) if n16 else []
        out.append((s, vc, counts, verts, blend))
    return out


XSURFACE_SIZE = 0xE8


def local_pose(info, anim=None, t=0.0):
    mats = skin.base_local(info["bones"], info["roots"], info["quats"])
    if anim is not None:
        index = {n: i for i, n in enumerate(info["names"])}
        to_model = [index.get(n, 255) for n in anim.names]
        acc = xanim.calc_parts(anim, t, bones=256, anim_to_model=to_model)[:info["bones"]]
        animated = [i in set(to_model) for i in range(info["bones"])]
        for i in range(info["bones"]):
            if animated[i]:
                mats[i] = acc[i]
        skin.normalize_rot_trans(mats, 1.0, ignore=[not x for x in animated])
    return mats


def game_calc_skel(L, info, a, local):
    mu = L.mu
    nb = info["bones"]
    mats_p, dskel, bits = WORK, WORK + 0x10000, WORK + 0x10200
    mu.mem_write(mats_p, local.astype(np.float32).tobytes())
    mu.mem_write(dskel, bytes(0x100) + struct.pack("<Q", mats_p))
    mu.mem_write(dskel + 0x88, struct.pack("<Q", mats_p))
    words = [0] * 8
    for i in range(nb):
        words[i >> 5] |= 0x80000000 >> (i & 31)
    zeros = WORK + 0x10300
    mu.mem_write(zeros, bytes(64))
    mu.mem_write(bits, struct.pack("<8I", *words))
    _call(mu, CALC_SKEL_ROOT, (a, dskel, 0, bits))        # clears the root bones' bits, as in the game
    _call(mu, CALC_SKEL_NON_ROOT, (a, dskel, info["roots"], bits), (zeros, zeros + 32))
    return np.frombuffer(bytes(mu.mem_read(mats_p, 0x20 * nb)), np.float32).reshape(nb, 8).copy()


def game_skin(L, info, surfaces, pose):
    mu = L.mu
    nb = info["bones"]
    pose_p, cmd, entries, out = WORK + 0x20000, WORK + 0x30000, WORK + 0x31000, WORK + 0x100000
    mu.mem_write(pose_p, pose.astype(np.float32).tobytes())
    blob, offsets, off = bytearray(), [], 0
    for s, vc, counts, verts, blend in surfaces:
        e = bytearray(0x38)
        struct.pack_into("<iQ", e, 0, off, 0)
        struct.pack_into("<Q", e, 8, info["base_p"])
        e[0x10], e[0x11] = 0, nb
        struct.pack_into("<Q", e, 0x28, s)
        blob += e
        offsets.append(off)
        off += 0x20 * vc
    mu.mem_write(entries, bytes(blob))
    mu.mem_write(cmd, struct.pack("<QQ", entries, pose_p) + b"\xff" * 32 + struct.pack("<H", len(surfaces)))
    mu.mem_write(DEVICE_LOST, b"\0")
    mu.mem_write(SKINNED_CACHE, struct.pack("<Q", out))
    mu.mem_write(out, bytes(off))
    _call(mu, R_SKIN_XMODEL_CMD, (cmd,))
    return [bytes(mu.mem_read(out + o, 0x20 * s[1])) for o, s in zip(offsets, surfaces)]


def compare_vertices(game: bytes, mine: bytes):
    """(max position difference, max packed component difference, vertex count)."""
    n = len(game) // 0x20
    g = np.frombuffer(game, np.float32).reshape(n, 8)
    m = np.frombuffer(mine, np.float32).reshape(n, 8)
    dpos = float(np.max(np.abs(g[:, :4] - m[:, :4]))) if n else 0.0
    gu = np.frombuffer(game, np.uint32).reshape(n, 8)[:, 4:]
    mu = np.frombuffer(mine, np.uint32).reshape(n, 8)[:, 4:]
    dpack = 0
    for mask, shift in ((0x3FF, 0), (0xFFC00, 10), (0x3FF00000, 20), (0xC0000000, 30)):
        d = np.abs(((gu & mask) >> shift).astype(np.int64) - ((mu & mask) >> shift).astype(np.int64))
        dpack = max(dpack, int(d.max()) if n else 0)
    return dpos, dpack, n


def check(ff: bytes, zone: str, model_names, times=(0.0, 0.37, 0.81)):
    L, assets = load_zone(ff, zone)
    mem = Mem(L.mu)
    anims = [xanim.read_xanim(mem, a) for t, a, n in assets if t == xanim.ASSET_XANIMPARTS]
    results = []
    for t, a, n in assets:
        if t != ASSET_XMODEL:
            continue
        name = n.decode("latin-1") if isinstance(n, bytes) else str(n)
        if name not in model_names:
            continue
        info = model_info(mem, a)
        bone_names = set(info["names"])
        mine_anims = [an for an in anims if an.names and sum(x in bone_names for x in an.names) >= 0.9 * len(an.names)]
        surfaces = lod0_surfaces(mem, a)
        poses = [("base", None, 0.0)] + [(an.name, an, tt) for an in mine_anims for tt in times]
        for label, an, tt in poses:
            local = local_pose(info, an, tt)
            game = game_calc_skel(L, info, a, local)
            mine = skin.calc_skel(local.copy(), info["roots"], info["parents"], info["trans"], info["scale"],
                                  info["no_scale"])
            skel_equal = game.tobytes() == mine.tobytes()
            gverts = game_skin(L, info, surfaces, game)
            skel, dq = skin.skin_matrices(info["base"], game)
            worst_pos = worst_pack = verts = 0
            for (s, vc, counts, verts_raw, blend), gv in zip(surfaces, gverts):
                mv = skin.skin_vertices(verts_raw, counts, blend, skel, dq)
                dp, dk, nv = compare_vertices(gv, mv)
                worst_pos, worst_pack, verts = max(worst_pos, dp), max(worst_pack, dk), verts + nv
            results.append((name, label, tt, skel_equal, worst_pos, worst_pack, verts))
            print(f"{name} {label} t={tt}: skeleton {'==' if skel_equal else '!='} game; {verts} vertices: "
                  f"position {worst_pos:.3g}, packed {worst_pack}", flush=True)
    return results


if __name__ == "__main__":
    path = Path(sys.argv[1])
    res = check(path.read_bytes(), path.stem, set(sys.argv[2].split(",")))
    bad = [r for r in res if not r[3] or r[4] > 1e-3 or r[5] > 1]
    print(f"{len(res)} poses, {len(bad)} outside the tolerance")
    sys.exit(1 if bad else 0)
