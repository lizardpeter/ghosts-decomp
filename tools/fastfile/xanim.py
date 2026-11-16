#!/usr/bin/env python3
"""Animations in Call of Duty: Ghosts PC zones (Microsoft Store build): XAnimParts (asset type 2, "xanim").

Three layers, as tools/fastfile/xmodel.py (docs/assets/animations.md has the format with its evidence):

1. Loader (load_xanim_parts, load_xanim_parts_ptr): the Store build's Load_XAnimParts (14035D040) and its helpers
   statement for statement; tests/fastfile/xanim_check.py checks it against the game's own loader on a map zone.
2. Reader and evaluator: read_xanim (an XAnimParts in memory -> plain Python lists of its data streams) and
   calc_parts, the Store build's XAnimCalcParts (14055EE30 for under 256 frames, 140560280 from 256) and
   XAnimCalcNonLoopEnd (140563620, the last frame) in float32 arithmetic, operation for operation:
   tests/fastfile/xanim_check.py runs the game's functions on every animation of a zone and compares bit for bit.
   sample() turns that into per-bone local rotations and translations.
3. Converter: add_to_gltf adds an animation to a glTF document made by xmodel.to_gltf (the model's skeleton).

The format in short: an animation's bones are split into ten groups (boneCount[0..8], [9] is the total), in this
order: no rotation, 2D rotation (z, w of the quaternion) and full rotation with keys, 2D and full rotation with one
key, small translation (8-bit keys), translation (16-bit keys), one translation, no translation. Rotation groups
cover bones 0.. in name order; translation groups name their bone with a byte. Keyed groups give a key count, the
frame number of each key (the frame index table) and the keys; values between keys are linear, rotations are
normalised afterwards. The deltaPart is the root motion (tag_origin): a translation and a 2D or full rotation.
"""
from __future__ import annotations

import struct
from bisect import bisect_right
from dataclasses import dataclass, field

import numpy as np

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
PTR_INSERT = 0xFDFDFDFFFFFFFFFE
XFILE_BLOCK_TEMP, XFILE_BLOCK_VIRTUAL = 0, 3
ASSET_XANIMPARTS = 0x02
XANIMPARTS_SIZE = 0x88

# boneCount groups (the PART_TYPE_* order)
NO_QUAT, HALF_QUAT, FULL_QUAT, HALF_QUAT_NO_SIZE, FULL_QUAT_NO_SIZE, SMALL_TRANS, TRANS, TRANS_NO_SIZE, NO_TRANS, \
    ALL = range(10)
PART_NAMES = ("no_quat", "half_quat", "full_quat", "half_quat_no_size", "full_quat_no_size", "small_trans", "trans",
              "trans_no_size", "no_trans", "all")

F32 = np.float32
QUAT_SCALE = F32(3.051851e-05)       # 1/32767 as the game's float constant
COARSE = 0x40                        # 16-bit index tables from this many keys are split (coarse table + indices)


# ==== 1. loader (Store Load_XAnimParts 14035D040 and helpers) ======================================================

def _u8(s, a):
    return s.read(a, 1)[0]


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _script_string(s, a):
    """Load_ScriptStringCustom (14037AF90)."""
    idx = _u32(s, a)
    s.put_u32(a, s.u64(s.string_table + 8 * idx) & 0xFFFFFFFF)


def _inline(s, field_address: int, alignment: int):
    """A pointer with no offset form: any non-zero value means the data follows (aligned). Returns the address or
    None."""
    if not s.u64(field_address):
        return None
    p = s.align(alignment) if alignment > 1 else s.addr()
    s.put_u64(field_address, p)
    return p


def _dynamic_indices(s, parts: int, at: int, count: int):
    """Load_XAnimDynamicIndices* (14035CD90, 14035CE10, 14035CE90): count + 1 frame numbers, bytes while the
    animation has under 256 frames, else u16 (no alignment: they follow the frames header)."""
    if _u16(s, parts + 0x12) < 0x100:
        s.load(False, at, 0)
        s.load(True, at, count + 1)
    else:
        s.load(False, at, 0)
        s.load(True, at, 2 * count + 2)


def _delta_trans(s, parts: int, at: int):
    """14035CFA0 (Load_XAnimPartTrans): size (u16, keys - 1), smallTrans (u8), then the frame0 vec3 when size is 0,
    else mins, size, frames pointer (0x20), the frame indices and the keys (14035CCE0)."""
    s.load(True, at, 8)
    size = _u16(s, at)
    if not size:
        s.load(True, at + 8, 0xC)
        return
    s.load(True, at + 8, 0x20)
    _dynamic_indices(s, parts, at + 0x28, size)
    frames = at + 0x20
    if not s.u64(frames):
        return
    if _u8(s, at + 2):                       # smallTrans: 3 bytes per key, unaligned
        p = s.addr()
        s.put_u64(frames, p)
        s.load(True, p, 3 * (size + 1))
    else:                                    # 3 u16 per key, aligned 4
        p = s.align(4)
        s.put_u64(frames, p)
        s.load(True, p, 6 * (size + 1))


def _delta_quat(s, parts: int, at: int, components: int):
    """14035CBA0 / 14035CC40 (Load_XAnimDeltaPartQuat2 / Quat): size (u16) and padding, then the frame0 (2 or 4
    shorts) when size is 0, else the frames pointer, the frame indices and the keys (aligned 4)."""
    s.load(True, at, 8)
    size = _u16(s, at)
    if not size:
        s.load(True, at + 8, 2 * components)
        return
    s.load(True, at + 8, 8)
    _dynamic_indices(s, parts, at + 0x10, size)
    if not s.u64(at + 8):
        return
    p = s.align(4)
    s.put_u64(at + 8, p)
    s.load(True, p, 2 * components * (size + 1))


def _delta_part(s, parts: int, at: int):
    """14035CA20 (Load_XAnimDeltaPart): trans, quat2 (2D rotation), quat, each always inline when set."""
    s.load(True, at, 0x18)
    p = _inline(s, at, 4)
    if p is not None:
        _delta_trans(s, parts, p)
    p = _inline(s, at + 8, 4)
    if p is not None:
        _delta_quat(s, parts, p, 2)
    p = _inline(s, at + 0x10, 4)
    if p is not None:
        _delta_quat(s, parts, p, 4)


def load_xanim_parts(s, at: int, at_stream_start: bool = True):
    """Load_XAnimParts (14035D040)."""
    s.load(at_stream_start, at, XANIMPARTS_SIZE)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    p = _inline(s, at + 0x38, 4)                                   # names: Load_scr_string_tArray(boneCount[9])
    if p is not None:
        n = _u8(s, at + 0x1E)
        s.load(True, p, 4 * n)
        for i in range(n):
            _script_string(s, p + 4 * i)
    p = _inline(s, at + 0x78, 4)                                   # notify: notifyCount × {name, time}
    if p is not None:
        n = _u8(s, at + 0x1F)
        s.load(True, p, 8 * n)
        for i in range(n):
            _script_string(s, p + 8 * i)
    p = _inline(s, at + 0x80, 4)                                   # deltaPart
    if p is not None:
        _delta_part(s, at, p)
    p = _inline(s, at + 0x40, 1)                                   # dataByte
    if p is not None:
        s.load(True, p, _u16(s, at + 8))
    p = _inline(s, at + 0x48, 2)                                   # dataShort
    if p is not None:
        s.load(True, p, 2 * _u16(s, at + 0xA))
    p = _inline(s, at + 0x50, 4)                                   # dataInt
    if p is not None:
        s.load(True, p, 4 * _u16(s, at + 0xC))
    p = _inline(s, at + 0x58, 2)                                   # randomDataShort
    if p is not None:
        s.load(True, p, 2 * _u32(s, at + 0x24))
    p = _inline(s, at + 0x60, 1)                                   # randomDataByte
    if p is not None:
        s.load(True, p, _u16(s, at + 0xE))
    p = _inline(s, at + 0x68, 4)                                   # randomDataInt
    if p is not None:
        s.load(True, p, 4 * _u16(s, at + 0x10))
    if s.u64(at + 0x70):                                           # indices (14035CF10)
        if _u16(s, at + 0x12) < 0x100:
            p = s.addr()
            s.put_u64(at + 0x70, p)
            s.load(True, p, _u32(s, at + 0x28))
        else:
            p = s.align(2)
            s.put_u64(at + 0x70, p)
            s.load(True, p, 2 * _u32(s, at + 0x28))
    s.pop()


def load_xanim_parts_ptr(s, varptr: int):
    """Load_XAnimPartsPtr (14035D3D0)."""
    s.push(XFILE_BLOCK_TEMP)
    v = s.u64(varptr)
    if v:
        if v not in (PTR_INLINE, PTR_INSERT):
            s.put_u64(varptr, s.offset_to_alias(v))
        else:
            h = s.align(4)
            s.put_u64(varptr, h)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            load_xanim_parts(s, h, True)
            s.put_u64(varptr, s.link(ASSET_XANIMPARTS, h))
            if slot is not None:
                s.put_u64(slot, s.u64(varptr))
    s.pop()


# ---- animation classes (asset type 0x20, "animclass") -----------------------------------------------------------

ASSET_ANIMCLASS = 0x20
HOOKS = {"scriptable_ptr": None, "fx_ptr": None}


def _ss(s, at):
    """Load_ScriptStringCustom (14037AF90)."""
    idx = s.u32(at)
    s.put_u32(at, s.u64(s.string_table + 8 * idx) & 0xFFFFFFFF)


def _following(s, at, align, body):
    """-1: aligned, then body(address); another non-null value: an offset."""
    v = s.u64(at)
    if not v:
        return
    if v != 0xFDFDFDFFFFFFFFFF:
        s.put_u64(at, s.offset_to_pointer(v))
        return
    p = s.align(align)
    s.put_u64(at, p)
    body(p)


def _scr_strings(s, p, count):
    """Load_scr_string_tArray (140361EA0)."""
    s.load(True, p, 4 * count)
    for i in range(count):
        _ss(s, p + 4 * i)


def _anim_aim_set(s, t, at_stream_start):
    """14034A460 (Load_AnimationAimSet): 0x70 bytes: name and rootName script strings, then eight animation names
    (+8)."""
    s.load(at_stream_start, t, 0x70)
    _ss(s, t)
    _ss(s, t + 4)
    for i in range(8):
        _ss(s, t + 8 + 4 * i)


def _anim_states(s, p, count):
    """14034A970 (Load_AnimationStateArray): count AnimationState (0x28): name and notify script strings, an aim set
    (+0x10), entryCount (byte +0xD) AnimationEntry {alias, animName} (+0x18) and as many 8-byte animIndices in the
    runtime block (+0x20, zero-filled)."""
    s.load(True, p, 0x28 * count)
    for i in range(count):
        e = p + 0x28 * i
        _ss(s, e)
        _ss(s, e + 4)
        _following(s, e + 0x10, 4, lambda t: _anim_aim_set(s, t, True))

        def pairs(q, e=e):
            n = s.read(e + 0xD, 1)[0]
            s.load(True, q, 8 * n)
            for k in range(n):
                _ss(s, q + 8 * k)
                _ss(s, q + 8 * k + 4)
        _following(s, e + 0x18, 4, pairs)
        s.push(2)                                         # XFILE_BLOCK_RUNTIME
        if s.u64(e + 0x20):
            q = s.align(4)
            s.put_u64(e + 0x20, q)
            s.load(True, q, 8 * s.read(e + 0xD, 1)[0])
        s.pop()


def _anim_state_machine(s, m):
    """14034ABE0 (Load_AnimationStateMachine): 0x18 bytes: name, the states (+8, stateCount u16 +4) and aim sets
    (+0x10, aimSetCount u16 +6, × 0x70)."""
    s.load(True, m, 0x18)
    _ss(s, m)
    _following(s, m + 8, 4, lambda p: _anim_states(s, p, struct.unpack("<H", s.read(m + 4, 2))[0]))

    def transitions(p):
        n = struct.unpack("<H", s.read(m + 6, 2))[0]
        s.load(True, p, 0x70 * n)
        for i in range(n):
            _anim_aim_set(s, p + 0x70 * i, False)
    _following(s, m + 0x10, 4, transitions)


def load_animation_class(s, h: int, at_stream_start: bool = True):
    """14034A550 (Load_AnimationClass): 0x58 bytes, in the virtual block: className, the state machine (+8), animTree
    (+0x14), the scriptable (+0x18), soundNotes / soundNames / soundOptions (+0x28, +0x30, +0x38: soundCount u16
    +0x20), effectNotes (+0x40), effectDefs (+0x48) and effectTags (+0x50) (effectCount u16 +0x22)."""
    s.load(at_stream_start, h, 0x58)
    s.push(3)                                             # XFILE_BLOCK_VIRTUAL
    s.xstring_ptr(h)
    _following(s, h + 8, 4, lambda p: _anim_state_machine(s, p))
    _ss(s, h + 0x14)
    HOOKS["scriptable_ptr"](s, h + 0x18)
    n1 = struct.unpack("<H", s.read(h + 0x20, 2))[0]
    n2 = struct.unpack("<H", s.read(h + 0x22, 2))[0]
    for off in (0x28, 0x30, 0x38):
        _following(s, h + off, 4, lambda p: _scr_strings(s, p, n1))
    _following(s, h + 0x40, 4, lambda p: _scr_strings(s, p, n2))

    def effects(p):
        s.load(True, p, 8 * n2)
        for i in range(n2):
            HOOKS["fx_ptr"](s, p + 8 * i)
    _following(s, h + 0x48, 8, effects)
    _following(s, h + 0x50, 4, lambda p: _scr_strings(s, p, n2))
    s.pop()


def load_animation_class_ptr(s, varptr: int):
    """Load_AnimationClassPtr (14034A880); Load_AnimationClassAsset (140371730) links it as 0x20."""
    import iw6ff
    iw6ff.asset_ptr(ASSET_ANIMCLASS, lambda s_, h: load_animation_class(s_, h, True))(s, varptr)


def register(asset_loaders: dict, scriptable_ptr=None, fx_ptr=None):
    asset_loaders[ASSET_XANIMPARTS] = load_xanim_parts_ptr
    if scriptable_ptr is not None and fx_ptr is not None:
        HOOKS["scriptable_ptr"], HOOKS["fx_ptr"] = scriptable_ptr, fx_ptr
        asset_loaders[ASSET_ANIMCLASS] = load_animation_class_ptr


# ==== 2. reader and evaluator ======================================================================================

@dataclass
class DeltaPart:
    trans: dict | None            # {"frame0": vec3} or {"mins", "size", "small", "indices", "keys"}
    quat2: dict | None            # {"frame0": (z, w)} or {"indices", "keys"} (shorts)
    quat: dict | None             # {"frame0": (x, y, z, w)} or {"indices", "keys"}


@dataclass
class XAnim:
    name: str
    numframes: int
    framerate: float
    frequency: float
    flags: int
    asset_type: int
    ik_type: int
    bone_count: tuple
    names: list                   # script string ids (or names, with a resolver), boneCount[9] entries
    notify: list                  # (name id, time)
    data_byte: bytes
    data_short: list              # u16
    data_int: bytes               # floats
    random_data_short: list       # i16 (read as u16 for translation keys)
    random_data_byte: bytes
    random_data_int: bytes
    indices: list                 # u8 or u16
    delta: DeltaPart | None
    raw: dict = field(default_factory=dict)


def _cstr(mem, a):
    out = bytearray()
    while a:
        c = mem.read(a, 1)[0]
        if not c:
            break
        out.append(c)
        a += 1
    return out.decode("latin1")


def _read_delta(mem, p, big: bool):
    def u16(a):
        return struct.unpack("<H", mem.read(a, 2))[0]

    def idx(a, n):
        return list(mem.read(a, n + 1)) if not big else list(struct.unpack(f"<{n + 1}H", mem.read(a, 2 * n + 2)))
    trans = quat2 = quat = None
    t = struct.unpack("<Q", mem.read(p, 8))[0]
    if t:
        size, small = u16(t), mem.read(t + 2, 1)[0]
        if not size:
            trans = {"frame0": struct.unpack("<3f", mem.read(t + 8, 12))}
        else:
            mins = struct.unpack("<3f", mem.read(t + 8, 12))
            sz = struct.unpack("<3f", mem.read(t + 0x14, 12))
            fp = struct.unpack("<Q", mem.read(t + 0x20, 8))[0]
            keys = list(mem.read(fp, 3 * (size + 1))) if small else \
                list(struct.unpack(f"<{3 * (size + 1)}H", mem.read(fp, 6 * (size + 1))))
            trans = {"mins": mins, "size": sz, "small": bool(small), "indices": idx(t + 0x28, size), "keys": keys}
    for off, comps in ((8, 2), (0x10, 4)):
        q = struct.unpack("<Q", mem.read(p + off, 8))[0]
        if not q:
            continue
        size = u16(q)
        if not size:
            d = {"frame0": struct.unpack(f"<{comps}h", mem.read(q + 8, 2 * comps))}
        else:
            fp = struct.unpack("<Q", mem.read(q + 8, 8))[0]
            d = {"indices": idx(q + 0x10, size),
                 "keys": list(struct.unpack(f"<{comps * (size + 1)}h", mem.read(fp, 2 * comps * (size + 1))))}
        if comps == 2:
            quat2 = d
        else:
            quat = d
    return DeltaPart(trans, quat2, quat)


def read_xanim(mem, a: int, script_string=None) -> XAnim:
    """An XAnimParts at `a` in a memory image (mem.read(address, n))."""
    h = mem.read(a, XANIMPARTS_SIZE)
    (name_p, dbc, dsc, dic, rdbc, rdic, numframes, flags) = struct.unpack_from("<QHHHHHHB", h, 0)
    bone_count = tuple(h[0x15:0x1F])
    notify_count, asset_type, ik_type = h[0x1F], h[0x20], h[0x21]
    rdsc, index_count = struct.unpack_from("<II", h, 0x24)
    framerate, frequency = struct.unpack_from("<ff", h, 0x2C)
    ptrs = struct.unpack_from("<10Q", h, 0x38)
    names_p, db_p, ds_p, di_p, rds_p, rdb_p, rdi_p, ind_p, notify_p, delta_p = ptrs[:10]
    big = numframes >= 0x100

    def arr(p, n, unit, fmt=None):
        if not p or n <= 0:
            return b"" if fmt is None else []
        data = mem.read(p, n * unit)
        return data if fmt is None else list(struct.unpack(f"<{n}{fmt}", data))
    names = arr(names_p, bone_count[ALL], 4, "I")
    if script_string is not None:
        names = [script_string(x) for x in names]
    notify = []
    for i in range(notify_count if notify_p else 0):
        nid, t = struct.unpack("<If", mem.read(notify_p + 8 * i, 8))
        notify.append((script_string(nid) if script_string else nid, t))
    return XAnim(
        name=_cstr(mem, name_p), numframes=numframes, framerate=framerate, frequency=frequency, flags=flags,
        asset_type=asset_type, ik_type=ik_type, bone_count=bone_count, names=names, notify=notify,
        data_byte=arr(db_p, dbc, 1),
        data_short=arr(ds_p, dsc, 2, "H"), data_int=arr(di_p, dic, 4),
        random_data_short=arr(rds_p, rdsc, 2, "h"), random_data_byte=arr(rdb_p, rdbc, 1),
        random_data_int=arr(rdi_p, rdic, 4),
        indices=arr(ind_p, index_count, 2 if big else 1, "H" if big else "B"),
        delta=_read_delta(mem, delta_p, big) if delta_p else None,
        raw={"address": a})


def _find(table, frame):
    """The key whose interval holds `frame`: the largest i < len - 1 with table[i] <= frame (the game's searches
    over sorted tables give this)."""
    i = bisect_right(table, frame) - 1
    return max(0, min(i, len(table) - 2))


class _Cursor:
    """The evaluator's read positions in the animation's streams."""

    def __init__(self, anim: XAnim):
        self.a = anim
        self.db = 0       # dataByte
        self.ds = 0       # dataShort
        self.di = 0       # dataInt (bytes)
        self.rs = 0       # randomDataShort
        self.rb = 0       # randomDataByte
        self.ix = 0       # indices

    def byte(self):
        v = self.a.data_byte[self.db]
        self.db += 1
        return v

    def short(self):
        v = self.a.data_short[self.ds]
        self.ds += 1
        return v

    def floats(self, n):
        v = struct.unpack_from(f"<{n}f", self.a.data_int, self.di)
        self.di += 4 * n
        return [F32(x) for x in v]


def _interval(c: _Cursor, n: int, frame: int, frame_f, last: bool):
    """Consumes a keyed part's frame index table (n + 1 entries, n = keys - 1) and returns (key, lerp fraction).
    Under 256 frames: n + 1 bytes of dataByte. From 256: in dataShort, n + 1 u16 when n < 0x40; else a coarse table
    of every 256th frame number (((n - 1) >> 8) + 2 entries) in dataShort, the full table (n + 1) in indices.
    `last` (XAnimCalcNonLoopEnd) skips the table and takes the last key."""
    a = c.a
    if a.numframes < 0x100:
        table = list(a.data_byte[c.db:c.db + n + 1])
        c.db += n + 1
    elif n < COARSE:
        table = a.data_short[c.ds:c.ds + n + 1]
        c.ds += n + 1
    else:
        m = ((n - 1) >> 8) + 2
        coarse = a.data_short[c.ds:c.ds + m]
        c.ds += m
        full = a.indices[c.ix:c.ix + n + 1]
        c.ix += n + 1
        if last:
            return n, None
        j = _find(coarse, frame)
        f2 = (frame_f - F32(coarse[j])) / F32(int(coarse[j + 1]) - int(coarse[j]))  # noqa: F841 (the game's guess)
        fine = full[256 * j:256 * j + min(n - 256 * j, 256) + 1]
        k = _find(fine, frame)
        lo, hi = fine[k], fine[k + 1]
        return 256 * j + k, (frame_f - F32(lo)) / F32(int(hi) - int(lo))
    if last:
        return n, None
    i = _find(table, frame)
    return i, (frame_f - F32(table[i])) / F32(int(table[i + 1]) - int(table[i]))


def calc_parts(anim: XAnim, t: float, weight: float = 1.0, bones: int | None = None, anim_to_model=None):
    """XAnimCalcParts / XAnimCalcNonLoopEnd for one animation into a fresh rotTransArray: per model bone a
    DObjAnimMat-like [quat x, y, z, w, trans x, y, z, transWeight] of float32, accumulated as the game does
    (rotations not yet normalised). `t` is the normalised time (0..1); t == 1 or numframes == 0 takes the last
    frame. anim_to_model maps animation part i to a model bone (identity by default)."""
    total = anim.bone_count[ALL]
    if anim_to_model is None:
        anim_to_model = list(range(total))
    out = np.zeros((bones if bones is not None else max(anim_to_model, default=-1) + 1, 8), dtype=F32)
    w = F32(weight)
    last = t == 1.0 or anim.numframes == 0
    tf = F32(t)
    frame_f = F32(anim.numframes) * tf
    frame = int(frame_f)
    c = _Cursor(anim)
    bc = anim.bone_count
    part = 0

    def bone_of(i):
        return anim_to_model[i]

    for _ in range(bc[NO_QUAT]):
        b = bone_of(part)
        out[b, 3] = w + out[b, 3]
        part += 1
    for group, comps in ((HALF_QUAT, 2), (FULL_QUAT, 4)):
        for _ in range(bc[group]):
            b = bone_of(part)
            n = c.short()
            i, f = _interval(c, n, frame, frame_f, last)
            keys = anim.random_data_short[c.rs:c.rs + comps * (n + 1)]
            c.rs += comps * (n + 1)
            k0 = [F32(x) * QUAT_SCALE for x in keys[comps * i:comps * i + comps]]
            if last:
                v = k0
            else:
                k1 = [F32(x) * QUAT_SCALE for x in keys[comps * (i + 1):comps * (i + 1) + comps]]
                v = [(k1[j] - k0[j]) * f + k0[j] for j in range(comps)]
            if comps == 2:
                zero = F32(0.0) if last else f * F32(0.0) + F32(0.0)
                v = [zero, zero] + v
            for j in range(4):
                out[b, j] = v[j] * w + out[b, j]
            part += 1
    for group, comps in ((HALF_QUAT_NO_SIZE, 2), (FULL_QUAT_NO_SIZE, 4)):
        for _ in range(bc[group]):
            b = bone_of(part)
            v = [F32(struct.unpack("<h", struct.pack("<H", c.short()))[0]) * QUAT_SCALE for _ in range(comps)]
            if comps == 2:
                for j in range(2):
                    out[b, j] = w * F32(0.0) + out[b, j]
                out[b, 2] = v[0] * w + out[b, 2]
                out[b, 3] = v[1] * w + out[b, 3]
            else:
                for j in range(4):
                    out[b, j] = v[j] * w + out[b, j]
            part += 1
    for group in (SMALL_TRANS, TRANS):
        for _ in range(bc[group]):
            b = bone_of(c.byte())
            n = c.short()
            i, f = _interval(c, n, frame, frame_f, last)
            mins = c.floats(3)
            size = c.floats(3)
            if group == SMALL_TRANS:
                keys = list(anim.random_data_byte[c.rb:c.rb + 3 * (n + 1)])
                c.rb += 3 * (n + 1)
            else:
                keys = [x & 0xFFFF for x in anim.random_data_short[c.rs:c.rs + 3 * (n + 1)]]
                c.rs += 3 * (n + 1)
            k0 = [F32(x) for x in keys[3 * i:3 * i + 3]]
            if last:
                v = [k0[j] * size[j] + mins[j] for j in range(3)]
            else:
                k1 = [F32(x) for x in keys[3 * (i + 1):3 * (i + 1) + 3]]
                v = [((k1[j] - k0[j]) * f + k0[j]) * size[j] + mins[j] for j in range(3)]
            for j in range(3):
                out[b, 4 + j] = v[j] * w + out[b, 4 + j]
            out[b, 7] = F32(1.0) * w + out[b, 7]
    for _ in range(bc[TRANS_NO_SIZE]):
        b = bone_of(c.byte())
        v = c.floats(3)
        for j in range(3):
            out[b, 4 + j] = v[j] * w + out[b, 4 + j]
        out[b, 7] = F32(1.0) * w + out[b, 7]
    for _ in range(bc[NO_TRANS]):
        b = bone_of(c.byte())
        out[b, 7] = w + out[b, 7]
    return out


def sample(anim: XAnim, t: float):
    """Per animation bone: (unit quaternion (x, y, z, w) or None, translation offset or None) at normalised time t.
    The rotation is the bone's local rotation; the translation is added to the bone's base local translation."""
    mats = calc_parts(anim, t)
    out = []
    for i in range(anim.bone_count[ALL]):
        q = [float(x) for x in mats[i, :4]]
        n = sum(x * x for x in q) ** 0.5
        q = tuple(x / n for x in q) if n > 0 else None
        tw = float(mats[i, 7])
        tr = tuple(float(x) / tw for x in mats[i, 4:7]) if tw > 0 else None
        out.append((q, tr))
    return out


FLAG_DELTA_2D, FLAG_DELTA_3D = 2, 4   # XAnimParts.flags: the root motion has a 2D (yaw) or a 3D rotation


def _delta_key(d: dict, frame: int, frame_f):
    """(key, lerp fraction) in a deltaPart part's frame index table (the game's search over sorted tables)."""
    table = d["indices"]
    i = _find(table, frame)
    return i, (frame_f - F32(table[i])) / F32(int(table[i + 1]) - int(table[i]))


def _delta_rot(anim: XAnim, t: float, comps: int):
    """XAnim_CalcRotDeltaDuring / XAnim_CalcRotDelta3DDuring and the end case of XAnim_CalcDeltaForTime /
    XAnim_CalcDelta3DForTime: the root rotation's (z, w) or (x, y, z, w) as unscaled shorts in float32."""
    d = (anim.delta.quat2 if comps == 2 else anim.delta.quat) if anim.delta else None
    if d is None:
        return [F32(0.0)] * (comps - 1) + [F32(32767.0)]
    if "frame0" in d:
        return [F32(x) for x in d["frame0"]]
    keys, n = d["keys"], len(d["indices"]) - 1
    if t == 1.0 or anim.numframes == 0:
        return [F32(x) for x in keys[comps * n:comps * n + comps]]
    frame_f = F32(anim.numframes) * F32(t)
    i, f = _delta_key(d, int(frame_f), frame_f)
    k0, k1 = keys[comps * i:comps * i + comps], keys[comps * (i + 1):comps * (i + 1) + comps]
    return [F32(int(k1[j]) - int(k0[j])) * f + F32(k0[j]) for j in range(comps)]


def _delta_pos(anim: XAnim, t: float):
    """XAnim_CalcPosDeltaDuring / XAnim_CalcPosDeltaEntire: the root translation."""
    d = anim.delta.trans if anim.delta else None
    if d is None:
        return [F32(0.0)] * 3
    if "frame0" in d:
        return [F32(x) for x in d["frame0"]]
    keys, n = d["keys"], len(d["indices"]) - 1
    mins, size = [F32(x) for x in d["mins"]], [F32(x) for x in d["size"]]
    if t == 1.0 or anim.numframes == 0:
        return [size[j] * F32(keys[3 * n + j]) + mins[j] for j in range(3)]
    frame_f = F32(anim.numframes) * F32(t)
    i, f = _delta_key(d, int(frame_f), frame_f)
    k0, k1 = keys[3 * i:3 * i + 3], keys[3 * (i + 1):3 * (i + 1) + 3]
    return [((F32(k1[j]) - F32(k0[j])) * f + F32(k0[j])) * size[j] + mins[j] for j in range(3)]


def calc_abs_delta(anim: XAnim, t: float, weight: float = 1.0):
    """XAnimCalcAbsDeltaParts (Store 140559750) into a fresh XAnimRotPos: [rot x, y, z, w, posWeight, pos x, y, z]
    of float32, the root motion from the animation's start to time t (rotation not normalised). Animations whose
    flags have neither a 2D nor a 3D root rotation add nothing."""
    out = np.zeros(8, dtype=F32)
    w = F32(weight)
    if anim.flags & FLAG_DELTA_2D:
        rot = [None, None] + _delta_rot(anim, t, 2)
    elif anim.flags & FLAG_DELTA_3D:
        rot = _delta_rot(anim, t, 4)
        for j in range(2):
            out[j] = rot[j] * w * QUAT_SCALE + out[j]
    else:
        return out
    for j in (2, 3):
        out[j] = rot[j] * w * QUAT_SCALE + out[j]
    out[4] = w + out[4]
    pos = _delta_pos(anim, t)
    for j in range(3):
        out[5 + j] = w * pos[j] + out[5 + j]
    return out


def sample_delta(anim: XAnim, t: float):
    """The root motion at time t: (unit quaternion (x, y, z, w), translation), or None for an animation without."""
    d = calc_abs_delta(anim, t)
    if not d[4]:
        return None
    q = [float(x) for x in d[:4]]
    n = sum(x * x for x in q) ** 0.5 or 1.0
    return tuple(x / n for x in q), tuple(float(x) / float(d[4]) for x in d[5:8])


# ==== 3. glTF ======================================================================================================

def add_to_gltf(doc: dict, binary: bytearray, anim: XAnim, bone_nodes: dict, scale: float = 1.0,
                bone_name=lambda x: x, fps: float | None = None, root_motion: str | None = None):
    """Add `anim` to a glTF document as an animation over the model's bone nodes (bone_nodes: bone name -> node
    index, from xmodel.to_gltf). Rotations replace the node rotation (the game uses the animation's local rotation
    as it is); translations are offsets the game adds to the bone's base local translation (CalcSkelNonRootBones),
    so the channel holds base + offset × scale. With root_motion (the name of the model's root bone, normally
    tag_origin) the animation's root motion (calc_abs_delta: how far the entity moves and turns from the start) drives
    that bone, so a run cycle moves forward; without it the animation plays in place."""
    rate = fps or anim.framerate or 30.0
    frames = anim.numframes + 1
    times = [i / rate for i in range(frames)]
    samples = [sample(anim, i / anim.numframes if anim.numframes else 1.0) for i in range(frames)]
    acc = doc.setdefault("accessors", [])
    views = doc.setdefault("bufferViews", [])

    def put(values, comps, kind):
        while len(binary) % 4:
            binary.append(0)
        off = len(binary)
        flat = [x for v in values for x in (v if isinstance(v, (tuple, list)) else (v,))]
        binary.extend(struct.pack(f"<{len(flat)}f", *flat))
        views.append({"buffer": 0, "byteOffset": off, "byteLength": 4 * len(flat)})
        a = {"bufferView": len(views) - 1, "componentType": 5126, "count": len(values), "type": kind}
        if kind == "SCALAR":
            a["min"], a["max"] = [min(values)], [max(values)]
        acc.append(a)
        return len(acc) - 1
    tacc = put(times, 1, "SCALAR")
    channels, samplers = [], []
    for i, nm in enumerate(anim.names):
        node = bone_nodes.get(bone_name(nm))
        if node is None:
            continue
        rots = [s[i][0] for s in samples]
        if all(r is not None for r in rots):
            samplers.append({"input": tacc, "output": put(rots, 4, "VEC4"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})
        trs = [s[i][1] for s in samples]
        if all(t is not None for t in trs):
            # the animation's translation is added to the bone's base local translation (CalcSkelNonRootBones:
            # model->trans + scale * anim trans)
            base = doc["nodes"][node].get("translation", [0.0, 0.0, 0.0])
            trs = [tuple(b + x * scale for b, x in zip(base, t)) for t in trs]
            samplers.append({"input": tacc, "output": put(trs, 3, "VEC3"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "translation"}})
    node = bone_nodes.get(root_motion) if root_motion else None
    targets = {(c["target"]["node"], c["target"]["path"]) for c in channels}
    deltas = [sample_delta(anim, i / anim.numframes if anim.numframes else 1.0) for i in range(frames)]
    if node is not None and all(d is not None for d in deltas):
        base = doc["nodes"][node].get("translation", [0.0, 0.0, 0.0])
        if (node, "rotation") not in targets:
            samplers.append({"input": tacc, "output": put([d[0] for d in deltas], 4, "VEC4"),
                             "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})
        if (node, "translation") not in targets:
            trs = [tuple(b + x * scale for b, x in zip(base, d[1])) for d in deltas]
            samplers.append({"input": tacc, "output": put(trs, 3, "VEC3"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "translation"}})
    doc.setdefault("animations", []).append({"name": anim.name, "channels": channels, "samplers": samplers})
    doc["buffers"][0]["byteLength"] = len(binary)
