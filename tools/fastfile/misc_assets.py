#!/usr/bin/env python3
"""The remaining small asset types of Call of Duty: Ghosts PC zones (Microsoft Store build), loaders statement for
statement after the Store build's (each function names its address):

| Type | Name | Store loader |
|---|---|---|
| 0x06 | computeshader | Load_ComputeShaderPtr 14034BF40 → 14034BE80, 14034EF40 |
| 0x17 | vehicle_track | Load_VehicleTrackPtr 140359430 → 140359340, 140359720, 140359970, 140359520 |
| 0x24 | snddriverglobals | Load_SndDriverGlobalsPtr 140356F90 → 140356EC0 |
| 0x2F | leaderboarddef | Load_LeaderboardDefPtr 140352470 → 140352360, 140352280 |
| 0x30 | structureddatadef | Load_StructuredDataDefSetPtr 140357ED0 → 140357E00, 140357BF0, 140357FC0, 1403580A0 |
| 0x33 | addon_map_ents | Load_AddonMapEntsPtr 14034A370 → 14034A100 (and clipmap.py's ClipInfo and triggers) |
| 0x35 | reverbpreset | Load_ReverbPresetPtr 140355B20 → 140355A90 |
| 0x36 | luafile | Load_LuaFilePtr 140352B20 → 140352A50 |
| 0x3B | equipsndtable | Load_EquipmentSoundTablePtr 14034CB70 → 14034C670, 14034C460, 14034C3B0, 14034C5C0 |
| 0x3C | vectorfield | Load_VectorFieldPtr 140358870 → 140358770 |

tests/fastfile/zone_check.py checks the ones real zones carry against the game; docs/assets/misc.md lists what each
holds. With these, every asset type the Store build's Load_XAssetHeader dispatches has a loader.
"""
from __future__ import annotations

import struct

import iw6ff

BLOCK_VIRTUAL = 3
HOOKS = {"snd": None}


def _h(name):
    fn = HOOKS[name]
    if fn is None:
        raise NotImplementedError(f"misc_assets.HOOKS[{name!r}] is not set (register() sets it)")
    return fn


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _follow(s, at, align):
    """Any non-null value: the data follows, aligned (no test for -1)."""
    if not s.u64(at):
        return 0
    p = s.align(align) if align > 1 else s.addr()
    s.put_u64(at, p)
    return p


def _inline_or_offset(s, at, align):
    v = s.u64(at)
    if not v:
        return 0
    if v == iw6ff.PTR_INLINE:
        p = s.align(align)
        s.put_u64(at, p)
        return p
    s.put_u64(at, s.offset_to_pointer(v))
    return 0


def _xstring(s, at):
    s.load(False, at, 8)
    s.xstring_ptr(at)


def _named(size, body=None):
    """A header with its name first, in the virtual block, then `body`."""
    def load(s, h, at_stream_start=True):
        s.load(at_stream_start, h, size)
        s.push(BLOCK_VIRTUAL)
        _xstring(s, h)
        if body:
            body(s, h)
        s.pop()
    return load


# ==== luafile, snddriverglobals, reverbpreset, vectorfield, leaderboarddef ========================================

def _lua(s, h):
    """140352A50 (Load_LuaFile): 0x18: name, len (+8), strip/flags, buffer (+0x10, any non-null value: len bytes,
    aligned 16)."""
    p = _follow(s, h + 0x10, 16)
    if p:
        s.load(True, p, _i32(s, h + 8))


def _snd_driver_globals(s, h):
    """140356EC0: 0x18: name, then +0x10 (any non-null value: 0x5B0 bytes, aligned 4)."""
    p = _follow(s, h + 0x10, 4)
    if p:
        s.load(True, p, 0x5B0)


def _vector_field(s, h):
    """140358770: 0x50: name, then the field (+8, -1: 0x10-byte cells, x (+0x34) by y (+0x38) by z (+0x3C) as a
    32-bit product, aligned 4)."""
    p = _inline_or_offset(s, h + 8, 4)
    if p:
        n = (_i32(s, h + 0x3C) * _i32(s, h + 0x38) * _i32(s, h + 0x34)) & 0xFFFFFFFF
        s.load(True, p, n << 4)


def _leaderboard(s, h):
    """140352360: 0x28: name, columnCount (+0xC) columns of 0x38 (+0x18, any non-null value, aligned 4), each
    (140352280) with two strings (+0, +0x18)."""
    p = _follow(s, h + 0x18, 4)
    if p:
        n = _i32(s, h + 0xC)
        s.load(True, p, n * 0x38)
        for i in range(n):
            c = p + 0x38 * i
            s.load(False, c, 0x38)
            _xstring(s, c)
            _xstring(s, c + 0x18)


load_lua_file = _named(0x18, _lua)
load_snd_driver_globals = _named(0x18, _snd_driver_globals)
load_reverb_preset = _named(0x48)                               # 140355A90: 0x48, a name and plain values
load_vector_field = _named(0x50, _vector_field)
load_leaderboard = _named(0x28, _leaderboard)


# ==== structured data (the save and stats layouts) ================================================================

def _struct_def_set(s, h):
    """140357E00: 0x18: name, defCount (+8) defs of 0x58 (+0x10, any non-null value, aligned 4; 140357BF0): enums
    (+0x10, count +8, 0x10 each: indices (+8, count +0) of 8 bytes whose first 4 are a script string), structs
    (+0x20, count +0x18, 0x18 each: properties (+8, count +0) of 0x14 whose first 4 are a script string), indexed
    arrays (+0x30, count +0x28, 0x10 each) and enumed arrays (+0x40, count +0x38, 0x10 each)."""
    p = _follow(s, h + 0x10, 4)
    if not p:
        return
    n = _i32(s, h + 8)
    s.load(True, p, n * 0x58)
    for i in range(n):
        d = p + 0x58 * i
        s.load(False, d, 0x58)
        for table, count_at, entry, item, item_size in ((0x10, 8, 0x10, 8, 8), (0x20, 0x18, 0x18, 8, 0x14)):
            q = _follow(s, d + table, 4)
            if not q:
                continue
            m = _i32(s, d + count_at)
            s.load(True, q, m * entry)
            for j in range(m):
                e = q + entry * j
                s.load(False, e, entry)                         # 140357FC0 / 1403580A0
                r = _follow(s, e + item, 4)
                if r:
                    k = _i32(s, e)
                    s.load(True, r, k * item_size)
                    for x in range(k):
                        s.load(False, r + item_size * x, item_size)
                        s.load(False, r + item_size * x, 4)
                        iw6ff._script_string(s, r + item_size * x)
        for table, count_at in ((0x30, 0x28), (0x40, 0x38)):
            q = _follow(s, d + table, 4)
            if q:
                s.load(True, q, _i32(s, d + count_at) << 4)


load_structured_data_def_set = _named(0x18, _struct_def_set)


# ==== equipment sounds ============================================================================================

def _sound_pairs(s, at, count, at_stream_start):
    """14034C5C0: count EquipmentSoundSets (0x10: the player's and others' sound, by name)."""
    s.load(at_stream_start, at, count << 4)
    for i in range(count):
        e = at + 0x10 * i
        s.load(False, e, 0x10)
        _h("snd")(s, e)
        _h("snd")(s, e + 8)


def _move_type_sets(s, at, count, table):
    """14034C3B0: count pointers (any non-null value, aligned 4) to numMoveTypes (+0x10) sound sets."""
    s.load(True, at, count * 8)
    for i in range(count):
        slot = at + 8 * i
        s.load(False, slot, 8)
        p = _follow(s, slot, 4)
        if p:
            _sound_pairs(s, p, _u32(s, table + 0x10), True)


def _chance_types(s, at, count, table):
    """14034C460: count pointers, each to numWeaponRattleTypes (+0xC) pointers, each to numMoveTypes (+0x10) x 0xC
    bytes; any non-null value: aligned 4."""
    s.load(True, at, count * 8)
    for i in range(count):
        slot = at + 8 * i
        s.load(False, slot, 8)
        p = _follow(s, slot, 4)
        if not p:
            continue
        m = _u32(s, table + 0xC)
        s.load(True, p, m * 8)
        for j in range(m):
            inner = p + 8 * j
            s.load(False, inner, 8)
            q = _follow(s, inner, 4)
            if q:
                s.load(True, q, _u32(s, table + 0x10) * 0xC)


def _equip_snd_table(s, h):
    """14034C670: 0x58: name; cloth type names (+0x18, numClothTypes +8, XString pointers); weapon rattle types
    (+0x20, numWeaponRattleTypes +0xC, 0x10 each with a name at +0); the player's and others' rattle chances (+0x28,
    +0x30); cloth and rattle movement sounds (+0x38, +0x40); accent sounds (+0x48); mantle sounds (+0x50, 0xE0 per
    cloth type: 14 sound sets). Arrays are any non-null value, aligned 4."""
    clothes, rattles = _u32(s, h + 8), _u32(s, h + 0xC)
    p = _follow(s, h + 0x18, 4)
    if p:
        s.load(True, p, clothes * 8)
        for i in range(clothes):
            s.load(False, p + 8 * i, 8)
            _xstring(s, p + 8 * i)
    p = _follow(s, h + 0x20, 4)
    if p:
        s.load(True, p, rattles << 4)
        for i in range(rattles):
            s.load(False, p + 0x10 * i, 0x10)
            _xstring(s, p + 0x10 * i)
    for off in (0x28, 0x30):
        p = _follow(s, h + off, 4)
        if p:
            _chance_types(s, p, _i32(s, h + 8), h)
    p = _follow(s, h + 0x38, 4)
    if p:
        _move_type_sets(s, p, _i32(s, h + 8), h)
    p = _follow(s, h + 0x40, 4)
    if p:
        _move_type_sets(s, p, _i32(s, h + 0xC), h)
    s.load(False, h + 0x48, 8)
    p = _follow(s, h + 0x48, 4)
    if p:
        _sound_pairs(s, p, _i32(s, h + 0x10), True)
    p = _follow(s, h + 0x50, 4)
    if p:
        n = _u32(s, h + 8)
        s.load(True, p, n * 0xE0)
        for i in range(n):
            m = p + 0xE0 * i
            s.load(False, m, 0xE0)
            s.load(False, m, 0xE0)
            for k in range(14):
                e = m + 0x10 * k
                s.load(False, e, 0x10)
                _h("snd")(s, e)
                _h("snd")(s, e + 8)


load_equip_snd_table = _named(0x58, _equip_snd_table)


# ==== vehicle tracks ==============================================================================================

def _track_segment(s, seg, at_stream_start):
    """140359520 (Load_VehicleTrackSegment): 0x48: name, sectors (+8, count u32 +0x10, 0x48 each, any non-null
    value, aligned 4; each with obstacles at +0x38, count u32 +0x40, 0xC each), next and previous segments (+0x18,
    count +0x20; +0x28, count +0x30: segment pointer arrays, aligned 8)."""
    s.load(at_stream_start, seg, 0x48)
    _xstring(s, seg)
    p = _follow(s, seg + 8, 4)
    if p:
        n = _u32(s, seg + 0x10)
        s.load(True, p, n * 0x48)
        for i in range(n):
            sec = p + 0x48 * i
            s.load(False, sec, 0x48)
            q = _follow(s, sec + 0x38, 4)
            if q:
                s.load(True, q, _u32(s, sec + 0x40) * 0xC)
    for arr, count_at in ((0x18, 0x20), (0x28, 0x30)):
        p = _follow(s, seg + arr, 8)
        if p:
            _segment_ptrs(s, p, _i32(s, seg + count_at))


def _segment_ptrs(s, at, count):
    """140359970: count segment pointers: -1: the segment follows (aligned 4), else an offset."""
    s.load(True, at, count * 8)
    for i in range(count):
        slot = at + 8 * i
        s.load(False, slot, 8)
        p = _inline_or_offset(s, slot, 4)
        if p:
            _track_segment(s, p, True)


def _vehicle_track(s, h):
    """140359340: 0x18: name, segments (+8, -1: segmentCount (+0x10) segments of 0x48, aligned 4; 140359720 loads
    each in place with 140359520's body)."""
    p = _inline_or_offset(s, h + 8, 4)
    if p:
        n = _i32(s, h + 0x10)
        s.load(True, p, n * 0x48)
        for i in range(n):
            _track_segment(s, p + 0x48 * i, False)


load_vehicle_track = _named(0x18, _vehicle_track)


# ==== add-on map entities =========================================================================================

def _addon_map_ents(s, h):
    """14034A100: 0x68: name; the entity string (+8, any non-null value: numEntityChars (+0x10) bytes, unaligned);
    triggers (+0x18, clipmap.load_map_triggers); a ClipInfo (+0x48, -1: aligned 4); numSubModels (+0x50) cmodels of
    0x50 (+0x58, any non-null value, aligned 4) each with a ClipInfo (+0x20, -1); and 0x3C bytes per sub model
    (+0x60)."""
    import clipmap
    p = _follow(s, h + 8, 1)
    if p:
        s.load(True, p, _i32(s, h + 0x10))
    clipmap.load_map_triggers(s, h + 0x18, False)
    p = _inline_or_offset(s, h + 0x48, 4)
    if p:
        clipmap.load_clip_info(s, p, True)
    n = _u32(s, h + 0x50)
    p = _follow(s, h + 0x58, 4)
    if p:
        s.load(True, p, n * 0x50)
        for i in range(n):
            m = p + 0x50 * i
            s.load(False, m, 0x50)
            q = _inline_or_offset(s, m + 0x20, 4)
            if q:
                clipmap.load_clip_info(s, q, True)
    p = _follow(s, h + 0x60, 4)
    if p:
        s.load(True, p, n * 0x3C)


load_addon_map_ents = _named(0x68, _addon_map_ents)


# ==== registration ================================================================================================

TYPES = {
    0x17: load_vehicle_track, 0x24: load_snd_driver_globals, 0x2F: load_leaderboard,
    0x30: load_structured_data_def_set, 0x33: load_addon_map_ents, 0x35: load_reverb_preset, 0x36: load_lua_file,
    0x3B: load_equip_snd_table, 0x3C: load_vector_field,
}
PTRS = {t: iw6ff.asset_ptr(t, (lambda f: lambda s, h: f(s, h, True))(f), 16 if t == 0x3C else 4)
        for t, f in TYPES.items()}     # Load_VectorFieldPtr (140358870) aligns the header to 16, the others to 4


def register(asset_loaders: dict, snd=None, compute_shader=None):
    asset_loaders.update(PTRS)
    if compute_shader is not None:
        asset_loaders[0x06] = compute_shader
    if snd is not None:
        HOOKS["snd"] = snd


NAMES = {0x06: "computeshader", 0x17: "vehicle_track", 0x24: "snddriverglobals", 0x2F: "leaderboarddef",
         0x30: "structureddatadef", 0x33: "addon_map_ents", 0x35: "reverbpreset", 0x36: "luafile",
         0x3B: "equipsndtable", 0x3C: "vectorfield"}


def _cstr(mem, a, limit=1024):
    if not a:
        return None
    out = bytearray()
    while len(out) < limit:
        chunk = mem.read(a + len(out), 64)
        i = chunk.find(b"\0")
        if i >= 0:
            return (out + chunk[:i]).decode("latin1")
        out += chunk
    return out.decode("latin1")


def read_name(mem, h):
    """Every one of these types has its name first."""
    return _cstr(mem, struct.unpack("<Q", mem.read(h, 8))[0])


def read_lua_file(mem, h):
    """(name, the chunk's bytes). Retail chunks are compiled HavokScript (they start with b"\x1bLuaQ")."""
    name_p, size = struct.unpack("<Qi", mem.read(h, 12))
    buf = struct.unpack("<Q", mem.read(h + 0x10, 8))[0]
    return _cstr(mem, name_p), (mem.read(buf, size) if buf and size > 0 else b"")


def read_leaderboard_columns(mem, h):
    """The column names (the first string of each 0x38-byte column) of a LeaderboardDef."""
    n = struct.unpack("<i", mem.read(h + 0xC, 4))[0]
    cols = struct.unpack("<Q", mem.read(h + 0x18, 8))[0]
    if not cols or n <= 0:
        return []
    return [_cstr(mem, struct.unpack("<Q", mem.read(cols + 0x38 * i, 8))[0]) for i in range(n)]


def main(argv=None) -> int:
    import argparse
    import os
    import sys
    ap = argparse.ArgumentParser(description="List a Ghosts PC zone's Lua files, compute shaders, leaderboards, "
                                             "structured data, reverb presets, sound tables, vehicle tracks and "
                                             "vector fields; --out writes each Lua chunk to a file.")
    ap.add_argument("fastfile")
    ap.add_argument("--out")
    opts = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loaders
    loaders.register_all()
    with open(opts.fastfile, "rb") as f:
        zone = iw6ff.read_fastfile(f.read(), os.path.basename(opts.fastfile).rsplit(".", 1)[0])
    if not zone.complete:
        print(f"the reader stopped at asset {zone.stopped_at} (type {zone.assets[zone.stopped_at].type:#x})")
    m, written = zone.stream, 0
    for a in zone.assets:
        if a.type not in NAMES or not a.header:
            continue
        name = read_name(m, a.header)
        extra = ""
        if a.type == 0x36:
            _, chunk = read_lua_file(m, a.header)
            extra = f"{len(chunk)} bytes"
            if opts.out:
                path = os.path.join(opts.out, *name.replace("\\", "/").split("/"))
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(chunk)
                written += 1
        elif a.type == 0x2F:
            extra = ", ".join(c or "" for c in read_leaderboard_columns(m, a.header))
        print(f"{NAMES[a.type]:18} {name}  {extra}".rstrip())
    if opts.out:
        print(f"{written} Lua chunks written to {opts.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
