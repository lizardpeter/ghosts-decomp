#!/usr/bin/env python3
"""How Call of Duty: Ghosts (PC, Microsoft Store build) poses and skins a model, in float32 numpy.

Four steps, each the Store build's code (tests/fastfile/skin_check.py runs the game's own functions on real models and
compares; docs/assets/models.md, "Posing and skinning in the game"):

1. local_pose: the bones' local rotations and translation offsets before the skeleton is built: the model's base pose
   (DObjCalcBaseAnim: root bones identity, the others their packed base rotation), the animation on top
   (xanim.calc_parts, weight 1) and XAnimNormalizeRotScaleTransArray (rotations normalised with the fast inverse
   square root, translations divided by their weight).
2. calc_skel: the model-space skeleton, CalcSkelRootBonesNoParentOrDuplicate (Store 140556990) and
   CalcSkelNonRootBones (1405561D0; src/xanim/dobj_skel.cpp in C++): rotation = parent × local, translation =
   parent applied to (base translation + scale × animation offset), and transWeight = 2 / |q|².
3. skin_matrices: per bone the skinning transform from the bind pose to the posed bone (R_SkinXModelCmd, 1406408A0):
   inverse(baseMat) × pose as a matrix (R_MultiplySkelMat 140640610), and as a unit dual quaternion (Axis4ToQuat
   14052EDA0 for the rotation).
4. skin_vertices: the vertices (R_SkinXSurfaceWeightDQB 1406436F0): vertices of one bone take the matrix
   (R_SkinXSurfaceWeight0 140641010); vertices of 2 to 8 bones blend the dual quaternions (dual quaternion
   skinning, R_SkinXSurfaceWeight1DQB..7DQB 140641260..140643050), weights in 1/65536, each bone's quaternion
   sign-matched to the first bone's, the blend normalised and applied to the position, normal and tangent. Normals
   and tangents are 10:10:10:2 packed; colour and texture coordinates pass through.

The game normalises the blend with rsqrtps (an approximation whose low bits differ between CPUs) refined by one
Newton step; this module uses 1/sqrt there, so its results equal the game's to float rounding, not bit for bit.
glTF skinning (linear blend of matrices) is not dual quaternion skinning: twisting joints differ (docs).
"""
from __future__ import annotations

import struct

import numpy as np

F32 = np.float32
QUAT_SCALE = F32(3.051851e-05)
WEIGHT_SCALE = F32(1.5258789e-05)   # 1/65536


# ---- 1. local pose ------------------------------------------------------------------------------------------------

def _fast_inv_sqrt(x):
    """The 0x5f3759df inverse square root with one Newton step, as XAnimNormalizeRotScaleTransArray computes it."""
    i = np.asarray(x, dtype=F32).view(np.int32)
    y = (np.int32(0x5F3759DF) - (i >> 1)).view(F32)
    return (F32(1.5) - x * F32(0.5) * y * y) * y


def normalize_rot_trans(mats: np.ndarray, weight: float = 1.0, ignore=None):
    """XAnimNormalizeRotScaleTransArray (in place) on an (n, 8) float32 array [quat, trans, transWeight]."""
    w = F32(weight)
    for i in range(len(mats)):
        if ignore is not None and ignore[i]:
            continue
        m = mats[i]
        q2 = m[0] * m[0] + m[1] * m[1] + m[2] * m[2] + m[3] * m[3]
        if q2 != 0:
            f = _fast_inv_sqrt(q2) * w
            m[0], m[1], m[2], m[3] = m[0] * f, f * m[1], f * m[2], f * m[3]
        if m[7] != 0:
            f = w / m[7]
            m[4], m[5], m[6] = f * m[4], f * m[5], f * m[6]
            m[7] = w
    return mats


def base_local(num_bones: int, num_root: int, quats_s16) -> np.ndarray:
    """DObjCalcBaseAnim: root bones identity, other bones their base local rotation (shorts / 32767), no offset."""
    mats = np.zeros((num_bones, 8), dtype=F32)
    mats[:num_root, 3] = 1.0
    for j, q in enumerate(quats_s16):
        mats[num_root + j, :4] = [F32(int(x)) * QUAT_SCALE for x in q]
    return mats


# ---- 2. skeleton --------------------------------------------------------------------------------------------------

def _trans_weight(m):
    q2 = m[0] * m[0] + m[1] * m[1] + m[2] * m[2] + m[3] * m[3]
    if not float(q2) > 1e-06:          # in double precision (CVTPS2PD, COMISD, JBE: NaN too)
        m[3] = F32(1.0)
        m[7] = F32(2.0)
    else:
        m[7] = F32(2.0) / q2


def calc_skel(mats: np.ndarray, num_root: int, parent_list, trans, scale: float = 1.0, no_scale=None,
              control=None, world_control=None):
    """CalcSkelRootBonesNoParentOrDuplicate + CalcSkelNonRootBones (in place): (n, 8) local mats -> model space.
    parent_list[j] is bone (num_root + j)'s distance back to its parent; trans[j] its base translation.
    control / world_control: per bone, as DSkelPartBits.control / worldCtrl (a control bone's local rotation is in
    the root's frame; a world-control bone's rotation is kept). src/xanim/dobj_skel.cpp is the same in C++."""
    s = F32(scale)
    for i in range(num_root):
        _trans_weight(mats[i])
    for j in range(len(mats) - num_root):
        i = num_root + j
        c, p = mats[i], mats[i - int(parent_list[j])]
        if not (world_control is not None and world_control[i]):
            p0, p1, p2, p3 = p[0], p[1], p[2], p[3]
            c0, c1, c2, c3 = c[0], c[1], c[2], c[3]
            if control is not None and control[i]:
                r = mats[0]
                r0, r1, r2, r3 = r[0], r[1], r[2], r[3]
                a0 = ((p0 * r3 - r0 * p3) - p2 * r1) + p1 * r2
                a1 = ((p2 * r0 + p1 * r3) - r1 * p3) - r2 * p0
                a2 = ((p2 * r3 - p1 * r0) + r1 * p0) - r2 * p3
                a3 = ((r0 * p0 + p3 * r3) + p1 * r1) + r2 * p2
                p0, p1, p2, p3 = r0, r1, r2, r3
                c0, c1, c2, c3 = (((c0 * a3 + a0 * c3) + c1 * a2) - c2 * a1, ((c3 * a1 - c0 * a2) + c1 * a3) + a0 * c2,
                                  ((c3 * a2 + c0 * a1) - a0 * c1) + c2 * a3, ((c3 * a3 - a0 * c0) - c1 * a1) - c2 * a2)
                c[0], c[1], c[2], c[3] = c0, c1, c2, c3
                p0, p1, p2, p3 = r[0], r[1], r[2], r[3]      # reread: the root may be this bone
                c[0] = ((c0 * p3 + p0 * c3) + p1 * c2) - c1 * p2
                c[1] = ((c1 * p3 - p0 * c2) + p1 * c3) + c0 * p2
                c[3] = ((p3 * c3 - c0 * p0) - c1 * p1) - p2 * c2
                c[2] = ((c1 * p0 + p3 * c2) - c0 * p1) + p2 * c3
            else:
                c[0] = ((p0 * c3 + c0 * p3) + c2 * p1) - c1 * p2
                c[1] = ((c1 * p3 - c2 * p0) + p1 * c3) + p2 * c0
                c[3] = ((c3 * p3 - p0 * c0) - c1 * p1) - p2 * c2
                c[2] = ((c1 * p0 + c2 * p3) - p1 * c0) + p2 * c3
        _trans_weight(c)
        p0, p1, p2, p3 = p[0], p[1], p[2], p[3]      # (the parent may be this bone)
        k = F32(1.0) if no_scale is not None and no_scale[i] else s
        x = k * c[4] + F32(trans[j][0])
        z = k * c[6] + F32(trans[j][2])
        y = k * c[5] + F32(trans[j][1])
        ptw = p[7]
        a = p1 * ptw
        b = p0 * ptw
        d = p3 * (p2 * ptw)
        e = b * p0
        g = (p2 * ptw) * p2
        c[4] = (F32(1.0) - (g + a * p1)) * x + (p1 * b - d) * y + (p3 * a + p2 * b) * z + p[4]
        c[5] = (F32(1.0) - (g + e)) * y + (d + p1 * b) * x + (p2 * a - p3 * b) * z + p[5]
        c[6] = (p2 * b - p3 * a) * x + (p2 * a + p3 * b) * y + (F32(1.0) - (a * p1 + e)) * z + p[6]
    return mats


# ---- 3. skinning transforms ---------------------------------------------------------------------------------------

def _axis4_to_quat(m):
    """Axis4ToQuat (14052EDA0) on a 4x4 (rows: axis 0..2, origin) float32 matrix."""
    m0, m1, m2 = m[0, 0], m[0, 1], m[0, 2]
    m4, m5, m6 = m[1, 0], m[1, 1], m[1, 2]
    m8, m9, m10 = m[2, 0], m[2, 1], m[2, 2]
    one = F32(1.0)
    v12 = m1 - m4
    v10 = m6 - m9
    v11 = m8 - m2
    v13 = m0 + m5 + m10 + one
    n = v10 * v10 + v11 * v11 + v12 * v12 + v13 * v13
    out = (v10, v11, v12, v13)
    if n < one:
        v9 = m9 + m6
        v4 = m2 + m8
        v8 = ((m10 - m5) - m0) + one
        n = v4 * v4 + v9 * v9 + v8 * v8 + v12 * v12
        out = (v4, v9, v8, v12)
        if n < one:
            v7 = m1 + m4
            v5 = ((m0 - m5) - m10) + one
            n = v5 * v5 + v7 * v7 + v4 * v4 + v10 * v10
            out = (v5, v7, v4, v10)
            if n < one:
                v6 = ((m5 - m0) - m10) + one
                n = v6 * v6 + v7 * v7 + v9 * v9 + v11 * v11
                out = (v7, v6, v9, v11)
    r = one / F32(np.sqrt(n))
    return tuple(x * r for x in out)


def skin_matrices(base: np.ndarray, pose: np.ndarray):
    """R_SkinXModelCmd's per-bone part: (skel (n, 4, 4) float32 matrices, dq (n, 2, 4) float32 dual quaternions)
    taking a bind-pose (baseMat) vertex to the posed bone."""
    n = len(pose)
    skel = np.zeros((n, 4, 4), dtype=F32)
    dq = np.zeros((n, 2, 4), dtype=F32)
    one = F32(1.0)
    for i in range(n):
        b, p = base[i], pose[i]
        q0, q1, q2, q3, t0, t1, t2, tw = b
        f19 = q1 * tw
        f22 = q0 * tw
        f20 = f22 * q0
        f17 = (q2 * tw) * q2
        inv = np.zeros((4, 4), dtype=F32)
        inv[0, 2] = f19 * q3 + f22 * q2
        a8 = (q2 * tw) * q3
        inv[2, 0] = f22 * q2 - f19 * q3
        inv[0, 0] = one - (f17 + f19 * q1)
        inv[0, 1] = f22 * q1 - a8
        inv[1, 1] = one - (f17 + f20)
        inv[1, 0] = a8 + f22 * q1
        inv[2, 2] = one - (f19 * q1 + f20)
        inv[2, 1] = f19 * q2 + f22 * q3
        inv[1, 2] = f19 * q2 - f22 * q3
        inv[3, 0] = -(t1 * inv[1, 0] + t0 * inv[0, 0] + t2 * inv[2, 0])
        inv[3, 1] = -(t1 * inv[1, 1] + t0 * inv[0, 1] + t2 * inv[2, 1])
        inv[3, 2] = -(t1 * inv[1, 2] + t0 * inv[0, 2] + t2 * inv[2, 2])
        p0, p1, p2, p3, pt0, pt1, pt2, ptw = p
        e22 = p0 * ptw
        e23 = p0 * e22
        e18 = p1 * ptw
        e21 = (p2 * p2) * ptw
        e8 = (p3 * p2) * ptw
        mat = np.zeros((4, 4), dtype=F32)
        mat[0] = [one - (e21 + p1 * e18), e8 + p1 * e22, p2 * e22 - p3 * e18, 0]
        mat[1] = [p1 * e22 - e8, one - (e21 + e23), p2 * e18 + p3 * e22, 0]
        mat[2] = [p3 * e18 + p2 * e22, p2 * e18 - p3 * e22, one - (p1 * e18 + e23), 0]
        mat[3] = [pt0, pt1, pt2, 0]
        s = skel[i]
        # R_MultiplySkelMat (140640610): s = inv * mat, the operand order of the Store build
        for r in range(3):
            s[r, 0] = inv[r, 0] * mat[0, 0] + mat[1, 0] * inv[r, 1] + inv[r, 2] * mat[2, 0] if r == 0 else \
                inv[r, 1] * mat[1, 0] + inv[r, 0] * mat[0, 0] + inv[r, 2] * mat[2, 0] if r == 1 else \
                mat[1, 0] * inv[r, 1] + mat[0, 0] * inv[r, 0] + inv[r, 2] * mat[2, 0]
            for c in (1, 2):
                if r == 1:
                    s[r, c] = inv[r, 1] * mat[1, c] + inv[r, 0] * mat[0, c] + inv[r, 2] * mat[2, c]
                else:
                    s[r, c] = mat[1, c] * inv[r, 1] + mat[0, c] * inv[r, 0] + mat[2, c] * inv[r, 2]
        for c in range(3):
            s[3, c] = inv[3, 1] * mat[1, c] + inv[3, 0] * mat[0, c] + inv[3, 2] * mat[2, c] + mat[3, c]
        s[3, 3] = one
        qx, qy, qz, qw = _axis4_to_quat(s)
        o0, o1, o2 = s[3, 0], s[3, 1], s[3, 2]
        dq[i, 0] = [qx, qy, qz, qw]
        dq[i, 1, 3] = (o0 * qx + o1 * qy + qz * o2) * F32(-0.5)
        dq[i, 1, 0] = ((o0 * qw + o1 * qz) - qy * o2) * F32(0.5)
        dq[i, 1, 1] = ((o1 * qw - o0 * qz) + qx * o2) * F32(0.5)
        dq[i, 1, 2] = ((o0 * qy - o1 * qx) + qw * o2) * F32(0.5)
    return skel, dq


# ---- 4. vertices ----------------------------------------------------------------------------------------------------

PACK_MASK = (0x3FF, 0xFFC00, 0x3FF00000)
PACK_ADD = (F32(-511.5), F32(-523776.0), F32(-5.3634662e+08))
PACK_MUL = (F32(0.0019550342), F32(1.909213e-06), F32(1.864466e-09))
UNPACK_MUL = (F32(511.5), F32(523776.0), F32(5.3634662e+08))
PACK_OR = 0xC0000000


def unpack_1010102(v: int):
    return [(F32(int(v & PACK_MASK[k])) + PACK_ADD[k]) * PACK_MUL[k] for k in range(3)]


def pack_1010102(n) -> int:
    out = PACK_OR
    for k in range(3):
        x = min(max(n[k], F32(-1.0)), F32(1.0))
        out |= int(np.trunc((x + F32(1.0)) * UNPACK_MUL[k])) & PACK_MASK[k]
    return out


def _rotate(q, v):
    """v + 2 q × (q × v + w v), with the Store build's operation order."""
    qx, qy, qz, qw = q
    z = F32(-0.0)
    tx = ((v[2] * qy + z) - v[1] * qz) + qw * v[0]
    ty = ((v[0] * qz + z) - v[2] * qx) + qw * v[1]
    tz = ((v[1] * qx + z) - v[0] * qy) + qw * v[2]
    two = F32(2.0)
    return [((tz * qy + z) - ty * qz) * two + v[0],
            ((tx * qz + z) - tz * qx) * two + v[1],
            ((ty * qx + z) - tx * qy) * two + v[2]]


def _dqb_vertex(bones, weights, dq):
    """Blend the dual quaternions of `bones` (first bone weight 1 - sum of the others): (unit real, dual)."""
    r0 = dq[bones[0], 0]
    real = r0 * (F32(1.0) - sum(weights, F32(0.0)))
    dual = dq[bones[0], 1] * (F32(1.0) - sum(weights, F32(0.0)))
    for b, w in zip(bones[1:], weights):
        r = dq[b, 0]
        dot = (r[0] * r0[0] + r[1] * r0[1]) + (r[2] * r0[2] + r[3] * r0[3])
        sw = w * (F32(-1.0) if np.signbit(dot) else F32(1.0))
        real = real + r * sw
        dual = dual + dq[b, 1] * sw
    n2 = (real[0] * real[0] + real[1] * real[1]) + (real[2] * real[2] + real[3] * real[3])
    y = F32(1.0) / F32(np.sqrt(n2))
    y = (F32(1.0) - y * y * n2) * y * F32(0.5) + y
    return real * y, dual * y


def skin_vertices(verts: bytes, blend_counts, blend: list, skel, dq) -> bytes:
    """R_SkinXSurfaceWeightDQB: the surface's packed vertices (0x20 bytes each: position, binormal sign, colour,
    texture coordinates, normal, tangent) skinned. blend_counts: XSurface.blendVertCounts (vertices of 1..8 bones);
    blend: XSurface.blendVerts as u16 (bone byte offsets of 64 per bone, weights in 1/65536)."""
    out = bytearray(len(verts))
    v, k = 0, 0
    z = F32(-0.0)
    two = F32(2.0)
    for extra, count in enumerate(blend_counts):
        for _ in range(count):
            p = [F32(x) for x in struct.unpack_from("<4f", verts, 0x20 * v)]
            color, uv, normal, tangent = struct.unpack_from("<4I", verts, 0x20 * v + 0x10)
            bones = [blend[k] // 64]
            weights = []
            k += 1
            for _ in range(extra):
                bones.append(blend[k] // 64)
                weights.append(F32(blend[k + 1]) * WEIGHT_SCALE)
                k += 2
            n, t = unpack_1010102(normal), unpack_1010102(tangent)
            if extra == 0:
                m = skel[bones[0]]
                pos = [p[2] * m[2, c] + m[3, c] + p[1] * m[1, c] + p[0] * m[0, c] for c in range(3)]
                n2 = [n[2] * m[2, c] + z + n[1] * m[1, c] + n[0] * m[0, c] for c in range(3)]
                t2 = [t[2] * m[2, c] + z + t[1] * m[1, c] + t[0] * m[0, c] for c in range(3)]
            else:
                q, d = _dqb_vertex(bones, weights, dq)
                qx, qy, qz, qw = q
                dx, dy, dz, dw = d
                ax = ((p[2] * qy + z) - p[1] * qz) + qw * p[0]
                ay = ((p[0] * qz + z) - p[2] * qx) + qw * p[1]
                az = ((p[1] * qx + z) - p[0] * qy) + qw * p[2]
                pos = [(((dz * qy + z) - dy * qz) + (qw * dx - dw * qx)) * two + ((az * qy * two + z) - ay * qz * two)
                       + p[0],
                       (((dx * qz + z) - dz * qx) + (qw * dy - dw * qy)) * two + ((ax * qz * two + z) - az * qx * two)
                       + p[1],
                       (((dy * qx + z) - dx * qy) + (qw * dz - dw * qz)) * two + ((ay * qx * two + z) - ax * qy * two)
                       + p[2]]
                n2, t2 = _rotate(q, n), _rotate(q, t)
            struct.pack_into("<4f4I", out, 0x20 * v, pos[0], pos[1], pos[2], p[3], color, uv, pack_1010102(n2),
                             pack_1010102(t2))
            v += 1
    return bytes(out)
