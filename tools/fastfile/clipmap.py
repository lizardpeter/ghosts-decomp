"""The collision map (clipMap_t, asset type col_map_mp, 0x13) of a Ghosts PC zone (Store build): brushes, terrain
triangles, the collision tree, brush models, static model placements, and the map entities (MapEnts: the entity
string, triggers, spawn and spline records), stages, dynamic entities and scriptables it carries.

1. Loaders: the Store build's Load_clipMap_ptr (14035FB10), Load_clipMap_t (14035FC00) and the functions they call,
   statement for statement, on the fastfile pipeline's Stream (tools/fastfile/iw6ff.py). Checked against the game's
   own loader on real map zones (tests/fastfile/clipmap_check.py). docs/assets/collision.md has the layout.
2. Readers: read_clipmap(memory, address) -> the parts an importer needs.

Field names are the servers' PDB names where the Store layout matches theirs.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

try:
    from . import iw6ff
    from . import material as material_mod
    from . import xmodel as xmodel_mod
except ImportError:  # run from this folder
    import iw6ff
    import material as material_mod
    import xmodel as xmodel_mod

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
PTR_INSERT = 0xFDFDFDFFFFFFFFFE
BLOCK_TEMP, BLOCK_RUNTIME, BLOCK_VIRTUAL = 0, 2, 3
ASSET_CLIPMAP = 0x13
CLIPMAP_SIZE = 0x280
CLIPINFO_SIZE = 0x80
MAPENTS_SIZE = 0x100
CM_INFO_GLOBAL = 0x1469C8A10      # Load_clipMap_t points clipMap.pInfo here after loading it inline (see below)


# ==== 1. loaders ===================================================================================================

def _u32(s, a):
    return struct.unpack("<I", s.read(a, 4))[0]


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _i16(s, a):
    return struct.unpack("<h", s.read(a, 2))[0]


def _plain(s, field_at: int, align: int, size: int, offset_form: bool = True):
    """A pointer to plain data: null stays null; inline (-1) -> align, point the field at the stream, load `size`
    bytes; anything else -> DB_ConvertOffsetToPointer (only where the field has an offset form). Returns the array's
    address when it was loaded here, else 0."""
    v = s.u64(field_at)
    if not v:
        return 0
    if offset_form and v != PTR_INLINE:
        s.put_u64(field_at, s.offset_to_pointer(v))
        return 0
    p = s.align(align) if align > 1 else s.addr()
    s.put_u64(field_at, p)
    s.load(True, p, size & 0xFFFFFFFFFFFFFFFF)
    return p


def _array(s, field_at: int, align: int, size: int):
    """A pointer that is always inline when set (no offset form)."""
    return _plain(s, field_at, align, size, offset_form=False)


def _runtime(s, field_at: int, align: int, size: int):
    """The same in the runtime block (zero-filled; nothing read from the zone)."""
    s.push(BLOCK_RUNTIME)
    p = _array(s, field_at, align, size)
    s.pop()
    return p


def _script_string(s, at: int):
    iw6ff._script_string(s, at)


def load_brushside_array(s, at: int, count: int, at_stream_start: bool):
    """Load_cbrushside_tArray (14035FA50): count × 0x10, each plane (+0) a 0x14-byte cplane_s (inline, aligned to 4,
    or an offset)."""
    s.load(at_stream_start, at, count * 0x10)
    for i in range(count):
        _plain(s, at + 0x10 * i, 4, 0x14)


def load_brush(s, at: int):
    """14035F900 (Load_cbrush_t): 0x30 bytes; sides (+8): one side (14035F9D0: 0x10 bytes and its plane) inline or
    an offset; baseAdjacentSide (+0x10): 1 byte, unaligned, or an offset."""
    v = s.u64(at + 8)
    if v:
        if v == PTR_INLINE:
            p = s.align(4)
            s.put_u64(at + 8, p)
            load_brushside_array(s, p, 1, True)
        else:
            s.put_u64(at + 8, s.offset_to_pointer(v))
    _plain(s, at + 0x10, 1, 1)


def load_clip_info(s, ci: int, at_stream_start: bool):
    """Load_ClipInfo (14034B360), 0x80 bytes."""
    s.load(at_stream_start, ci, CLIPINFO_SIZE)
    _plain(s, ci + 0x08, 4, _i32(s, ci) * 0x14)                        # planes
    count = _u32(s, ci + 0x10)
    v = s.u64(ci + 0x18)                                                # materials (ClipMaterial, name first)
    if v == PTR_INLINE:
        p = s.align(4)
        s.put_u64(ci + 0x18, p)
        s.load(True, p, count * 0x10)
        for i in range(count):
            s.xstring_ptr(p + 0x10 * i)
    elif v:
        s.put_u64(ci + 0x18, s.offset_to_pointer(v))
    v = s.u64(ci + 0x28)                                                # brushsides
    if v == PTR_INLINE:
        p = s.align(4)
        s.put_u64(ci + 0x28, p)
        load_brushside_array(s, p, _u32(s, ci + 0x20), True)
    elif v:
        s.put_u64(ci + 0x28, s.offset_to_pointer(v))
    _plain(s, ci + 0x38, 1, _u32(s, ci + 0x30))                        # brushEdges
    count = _u32(s, ci + 0x40)
    v = s.u64(ci + 0x48)                                                # leafbrushNodes (cLeafBrushNode_s, 0x18)
    if v == PTR_INLINE:
        p = s.align(4)
        s.put_u64(ci + 0x48, p)
        s.load(True, p, count * 0x18)
        for i in range(count):
            node = p + 0x18 * i
            n = _i16(s, node + 2)
            if n > 0:                                                    # 14035F7D0: data.leaf.brushes
                _plain(s, node + 8, 2, n * 2)
    elif v:
        s.put_u64(ci + 0x48, s.offset_to_pointer(v))
    _plain(s, ci + 0x58, 2, _u32(s, ci + 0x50) * 2)                    # leafbrushes
    nb = _u16(s, ci + 0x60)
    v = s.u64(ci + 0x68)                                                # brushes (cbrush_t, 0x30)
    if v == PTR_INLINE:
        p = s.align(128)
        s.put_u64(ci + 0x68, p)
        s.load(True, p, nb * 0x30)
        for i in range(nb):
            load_brush(s, p + 0x30 * i)
    elif v:
        s.put_u64(ci + 0x68, s.offset_to_pointer(v))
    _plain(s, ci + 0x70, 128, nb * 0x18)                               # brushBounds
    _plain(s, ci + 0x78, 4, nb * 4)                                    # brushContents


def load_map_triggers(s, at: int, at_stream_start: bool):
    """140352E40 (Load_MapTriggers), 0x30: models (count +0, ×8 at +8), hulls (+0x10, ×0x20 at +0x18), slabs
    (+0x20, ×0x14 at +0x28)."""
    s.load(at_stream_start, at, 0x30)
    _plain(s, at + 0x08, 4, _u32(s, at) * 8)
    _plain(s, at + 0x18, 4, _u32(s, at + 0x10) * 0x20)
    _plain(s, at + 0x28, 4, _u32(s, at + 0x20) * 0x14)


def load_client_triggers(s, at: int, at_stream_start: bool):
    """14034B0A0 (Load_ClientTriggers), 0x88: a MapTriggers, then per-trigger arrays."""
    s.load(at_stream_start, at, 0x88)
    load_map_triggers(s, at, False)
    n = _u32(s, at)
    _array(s, at + 0x38, 4, _u16(s, at + 0x30) * 0x1C)
    _array(s, at + 0x48, 1, _u32(s, at + 0x40))
    _array(s, at + 0x50, 2, n * 2)
    _array(s, at + 0x58, 1, n)
    _array(s, at + 0x60, 4, n * 0xC)
    _array(s, at + 0x68, 4, n * 4)
    _array(s, at + 0x70, 2, n * 2)
    _array(s, at + 0x78, 2, n * 2)
    _array(s, at + 0x80, 2, n * 2)


def load_map_ents(s, me: int, at_stream_start: bool):
    """Load_MapEnts (140352C10), 0x100: name, entityString (+8, numEntityChars +0x10, unaligned), trigger (+0x18),
    clientTrigger (+0x48), and three record lists (u16 count, pointer at +8): +0xD0 (14034B030: ×0x1C), +0xE0
    (1403571A0: spawn records ×0x28, three script strings each), +0xF0 (140357460: spline lists ×0x10, each
    1403573B0: ×0x48 points)."""
    s.load(at_stream_start, me, MAPENTS_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(me)
    _array(s, me + 0x08, 1, _i32(s, me + 0x10))
    load_map_triggers(s, me + 0x18, False)
    load_client_triggers(s, me + 0x48, False)
    _array(s, me + 0xD8, 4, _u16(s, me + 0xD0) * 0x1C)
    n = _u16(s, me + 0xE0)
    p = _array(s, me + 0xE8, 4, n * 0x28)
    for i in range(n if p else 0):
        for off in (4, 8, 0xC):
            _script_string(s, p + 0x28 * i + off)
    n = _u16(s, me + 0xF0)
    p = _array(s, me + 0xF8, 4, n * 0x10)
    for i in range(n if p else 0):
        lst = p + 0x10 * i
        m = _u16(s, lst)
        q = _array(s, lst + 8, 4, m * 0x48)
        for j in range(m if q else 0):
            pt = q + 0x48 * j                                          # 1403572D0
            _array(s, pt + 0x08, 1, 0x40)
            _array(s, pt + 0x38, 4, 0x30)
            _array(s, pt + 0x40, 4, 0x24)
    s.pop()


def load_map_ents_ptr(s, varptr: int):
    """Load_MapEntsPtr (140352D50); Load_MapEntsAsset (140372840) links it as type 0x18 (map_ents)."""
    iw6ff.asset_ptr(0x18, lambda s_, h: load_map_ents(s_, h, True))(s, varptr)


def _asset_ptr_alias_only(kind: str):
    """An asset pointer the maps measured only ever reference by alias; an inline asset raises (its loader is not
    written yet)."""
    def load(s, varptr: int):
        s.push(BLOCK_TEMP)
        v = s.u64(varptr)
        if v in (PTR_INLINE, PTR_INSERT):
            raise NotImplementedError(f"inline {kind} in a collision map")
        if v:
            s.put_u64(varptr, s.offset_to_alias(v))
        s.pop()
    return load


load_fx_effect_def_handle = _asset_ptr_alias_only("FxEffectDef (14034D120)")
ASSET_SOUND = 0x0E
ASSET_SCRIPTABLEDEF = 0x37


def load_xstring_ptr(s, field_at: int):
    """14035EA70 (Load_XStringPtr): a pointer to a string pointer: inline -> aligned to 8, the 8-byte string pointer
    loaded there (14035E950) with the XString rule; else an offset."""
    v = s.u64(field_at)
    if not v:
        return
    if v != PTR_INLINE:
        s.put_u64(field_at, s.offset_to_pointer(v))
        return
    p = s.align(8)
    s.put_u64(field_at, p)
    s.load(True, p, 8)
    s.xstring_ptr(p)


def load_snd_alias_custom(s, field_at: int):
    """1405367A0 (Load_SndAliasCustom): the alias name (Load_XStringPtr), then DB_FindXAssetHeader(sound, name)
    replaces the field: the alias list if this zone has linked it; else 0 here (the game finds it in another zone
    or makes a default entry)."""
    if not s.u64(field_at):
        return
    load_xstring_ptr(s, field_at)
    name = s.cstr(s.u64(s.u64(field_at)))
    s.put_u64(field_at, s.find_asset(ASSET_SOUND, name))


def load_scriptable_event(s, ev: int, xmodel_ptr):
    """1403564A0 (Load_ScriptableEventDef), 0x28: type (+0), its data at +8."""
    t = _i32(s, ev)
    d = ev + 8
    if t == 0:                       # model
        xmodel_ptr(s, d)
    elif t == 1:                     # effect (1403565A0): handle, then a script string
        load_fx_effect_def_handle(s, d)
        _script_string(s, d + 8)
    elif t == 2:                     # sound (140356730)
        load_snd_alias_custom(s, d)
    elif t == 3:                     # animation (140356420): name
        s.xstring_ptr(d)
    elif t == 6:                     # physics (140356680): model
        xmodel_ptr(s, d)
    elif t == 7:                     # light settings (140356600): name at +0x10
        s.xstring_ptr(d + 0x10)
    elif t == 9:                     # shake (1403566B0): name
        s.xstring_ptr(d)


def load_scriptable_def(s, h: int, xmodel_ptr):
    """140355FE0 (Load_ScriptableDef), 0x40: name, model (+8), two names (+0x10, +0x18), parts (+0x20, count byte
    +0x35, ×0x10: states (count byte +0xC, ×0x18: two script strings, events (count byte +0x10, ×0x28)), a script
    string at +8), notetracks (+0x28, count byte +0x38, ×0x18: a script string, type (+4): 0 effect + script
    string, 1 sound)."""
    s.load(True, h, 0x40)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    xmodel_ptr(s, h + 8)
    s.xstring_ptr(h + 0x10)
    s.xstring_ptr(h + 0x18)
    v = s.u64(h + 0x20)
    if v == PTR_INLINE:
        n = s.read(h + 0x35, 1)[0]
        p = s.align(4)
        s.put_u64(h + 0x20, p)
        s.load(True, p, n * 0x10)
        for i in range(n):                                              # 140356A40
            part = p + 0x10 * i
            v2 = s.u64(part)
            if v2 == PTR_INLINE:
                m = s.read(part + 0xC, 1)[0]
                q = s.align(4)
                s.put_u64(part, q)
                s.load(True, q, m * 0x18)
                for j in range(m):                                      # 140356B30
                    st = q + 0x18 * j
                    _script_string(s, st)
                    _script_string(s, st + 4)
                    v3 = s.u64(st + 8)
                    if v3 == PTR_INLINE:
                        k = s.read(st + 0x10, 1)[0]
                        r = s.align(4)
                        s.put_u64(st + 8, r)
                        s.load(True, r, k * 0x28)
                        for e in range(k):
                            load_scriptable_event(s, r + 0x28 * e, xmodel_ptr)
                    elif v3:
                        s.put_u64(st + 8, s.offset_to_pointer(v3))
            elif v2:
                s.put_u64(part, s.offset_to_pointer(v2))
            _script_string(s, part + 8)
    elif v:
        s.put_u64(h + 0x20, s.offset_to_pointer(v))
    v = s.u64(h + 0x28)
    if v == PTR_INLINE:
        n = s.read(h + 0x38, 1)[0]
        p = s.align(4)
        s.put_u64(h + 0x28, p)
        s.load(True, p, n * 0x18)
        for i in range(n):
            nt = p + 0x18 * i
            _script_string(s, nt)
            kind = _i32(s, nt + 4)
            if kind == 0:
                load_fx_effect_def_handle(s, nt + 8)
                _script_string(s, nt + 0x10)
            elif kind == 1:
                load_snd_alias_custom(s, nt + 8)
    elif v:
        s.put_u64(h + 0x28, s.offset_to_pointer(v))
    s.pop()


def load_scriptable_def_ptr(s, varptr: int, xmodel_ptr=None):
    """140356330 (Load_ScriptableDefPtr); Load_ScriptableDefAsset (140373630) links it as 0x37."""
    iw6ff.asset_ptr(ASSET_SCRIPTABLEDEF, lambda s_, h: load_scriptable_def(s_, h, xmodel_ptr))(s, varptr)


def load_dyn_entity_defs(s, at: int, count: int, xmodel_ptr, physpreset_ptr):
    """14034C240 (Load_DynEntityDefArray): count × 0x78: xModel (+0x20), destroyFx (+0x30), physPreset (+0x38),
    two inline blocks (+0x40: 0x2C, +0x48: 0x1C)."""
    s.load(True, at, count * 0x78)
    for i in range(count):
        d = at + 0x78 * i
        xmodel_ptr(s, d + 0x20)
        load_fx_effect_def_handle(s, d + 0x30)
        physpreset_ptr(s, d + 0x38)
        _plain(s, d + 0x40, 4, 0x2C)
        _plain(s, d + 0x48, 4, 0x1C)


def load_scriptable_map_ents(s, at: int, xmodel_ptr):
    """140356920 (Load_ScriptableMapEnts), 0x30: instances (count +4, ×0x78 at +0x10), animation entries (count
    +0x18, ×0x10 at +0x20)."""
    s.load(False, at, 0x30)
    n = _u32(s, at + 4)
    p = _array(s, at + 0x10, 4, n * 0x78)
    for i in range(n if p else 0):                                     # 140356770
        inst = p + 0x78 * i
        load_scriptable_def_ptr(s, inst, xmodel_ptr)
        d = s.u64(inst)
        if s.u64(inst + 8):
            q = s.addr()
            s.put_u64(inst + 8, q)
            s.load(True, q, s.read(d + 0x3A, 1)[0])
        _script_string(s, inst + 0x28)
        s.push(BLOCK_RUNTIME)
        xmodel_ptr(s, inst + 0x38)
        s.pop()
        _runtime(s, inst + 0x40, 4, s.read(d + 0x35, 1)[0] * 4)
        if s.u64(inst + 0x48):
            s.push(BLOCK_RUNTIME)
            q = s.addr()
            s.put_u64(inst + 0x48, q)
            s.load(True, q, s.read(d + 0x39, 1)[0])
            s.pop()
        for _ in range(4):
            s.push(BLOCK_RUNTIME)
            s.pop()
    n = _u32(s, at + 0x18)
    p = _array(s, at + 0x20, 4, n * 0x10)
    for i in range(n if p else 0):                                     # 140355F40
        s.xstring_ptr(p + 0x10 * i)
        s.push(BLOCK_RUNTIME)
        s.pop()


def load_clipmap(s, c: int, at_stream_start: bool = True, xmodel_ptr=None, physpreset_ptr=None):
    """Load_clipMap_t (14035FC00), 0x280 bytes."""
    xmodel_ptr = xmodel_ptr or (lambda s_, f: xmodel_mod.load_xmodel_ptr(s_, f, material_mod.load_material_ptr))
    physpreset_ptr = physpreset_ptr or (lambda s_, f: xmodel_mod.asset_ptr(
        s_, f, xmodel_mod.ASSET_PHYSPRESET, xmodel_mod.load_physpreset))
    s.load(at_stream_start, c, CLIPMAP_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(c)                                                    # name
    load_clip_info(s, c + 0x10, False)                                  # info
    s.push(BLOCK_TEMP)                                                  # pInfo
    v = s.u64(c + 0x90)
    if v:
        if v in (PTR_INLINE, PTR_INSERT):
            p = s.align(4)
            s.put_u64(c + 0x90, p)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            load_clip_info(s, p, True)
            s.put_u64(c + 0x90, CM_INFO_GLOBAL)    # 140437F30(&pInfo, 0x1469C8A10): the game's global ClipInfo
            if slot is not None:
                s.put_u64(slot, s.u64(c + 0x90))
        else:
            s.put_u64(c + 0x90, s.offset_to_alias(v))
    s.pop()
    n = _u32(s, c + 0x98)                                               # staticModelList (cStaticModel_s, 0x50)
    p = _array(s, c + 0xA0, 4, n * 0x50)
    for i in range(n if p else 0):
        xmodel_ptr(s, p + 0x50 * i)
    n = _u32(s, c + 0xA8)                                               # nodes (cNode_t, 0x10: plane, children)
    p = _array(s, c + 0xB0, 4, n * 0x10)
    for i in range(n if p else 0):
        _plain(s, p + 0x10 * i, 4, 0x14)
    _array(s, c + 0xC0, 4, _u32(s, c + 0xB8) * 0x28)                   # leafs
    _array(s, c + 0xD0, 4, _u32(s, c + 0xC8) * 0xC)                    # verts
    tris = _i32(s, c + 0xD8)
    _array(s, c + 0xE0, 2, tris * 3 * 2)                               # triIndices
    _array(s, c + 0xE8, 1, ((tris * 3 + 31) >> 3) & ~3)                # triEdgeIsWalkable
    _array(s, c + 0xF8, 4, _i32(s, c + 0xF0) * 0x1C)                   # borders
    n = _i32(s, c + 0x100)
    p = _array(s, c + 0x108, 4, n * 0x10)                               # partitions (0x10: borders at +8)
    for i in range(n if p else 0):
        _plain(s, p + 0x10 * i + 8, 4, 0x1C)
    _array(s, c + 0x118, 16, _i32(s, c + 0x110) * 0x20)                # aabbTrees
    n = _u32(s, c + 0x120)
    p = _array(s, c + 0x128, 4, n * 0x50)                               # cmodels (cmodel_t, 0x50)
    for i in range(n if p else 0):                                      # 140360750
        cm = p + 0x50 * i
        s.push(BLOCK_TEMP)
        v = s.u64(cm + 0x20)                                            # info (ClipInfo *)
        if v:
            if v in (PTR_INLINE, PTR_INSERT):
                q = s.align(4)
                s.put_u64(cm + 0x20, q)
                slot = s.insert_pointer() if v == PTR_INSERT else None
                load_clip_info(s, q, True)
                if slot is not None:
                    s.put_u64(slot, s.u64(cm + 0x20))
            else:
                s.put_u64(cm + 0x20, s.offset_to_alias(v))
        s.pop()
    _array(s, c + 0x180, 4, _u16(s, c + 0x178) * 0x1C)                 # PC only
    load_map_ents_ptr(s, c + 0x130)                                     # mapEnts
    n = s.read(c + 0x140, 1)[0]
    p = _array(s, c + 0x138, 4, n * 0x18)                               # stages (name first)
    for i in range(n if p else 0):
        s.xstring_ptr(p + 0x18 * i)
    load_map_triggers(s, c + 0x148, False)                              # stageTrigger
    for count_at, field_at in ((0x188, 0x190), (0x18A, 0x198)):         # dynEntDefList[2]
        if s.u64(c + field_at):
            q = s.align(4)
            s.put_u64(c + field_at, q)
            load_dyn_entity_defs(s, q, _u16(s, c + count_at), xmodel_ptr, physpreset_ptr)
    for field_at, count_at, size in ((0x1A0, 0x188, 0x20), (0x1A8, 0x18A, 0x20),   # dynEntPoseList
                                     (0x1B0, 0x188, 0x28), (0x1B8, 0x18A, 0x28),   # dynEntClientList
                                     (0x1C0, 0x188, 0x14), (0x1C8, 0x18A, 0x14)):  # dynEntCollList
        _runtime(s, c + field_at, 4, _u16(s, c + count_at) * size)
    n = _i32(s, c + 0x1D0)
    p = _array(s, c + 0x1D8, 4, n * 4)                                 # script strings (140361EA0)
    for i in range(n if p else 0):
        _script_string(s, p + 4 * i)
    load_scriptable_map_ents(s, c + 0x1E0, xmodel_ptr)
    s.pop()
    # Load_ClipMapAsset (1403717F0) sets isInUse (+8) before linking; after linking, 140371370 swaps the x and y
    # extents of one brush model with particular bounds, counting brush models from the global ClipInfo (0x1469C8B20),
    # which is 0 while a zone loads: nothing to do here.
    s.put_u32(c + 8, 1)


def load_clipmap_ptr(s, varptr: int, **loaders):
    """Load_clipMap_ptr (14035FB10): the asset pointer rule, Load_ClipMapAsset (1403717F0) links it as 0x13."""
    iw6ff.asset_ptr(ASSET_CLIPMAP, lambda s_, h: load_clipmap(s_, h, True, **loaders))(s, varptr)


def register(asset_loaders: dict):
    asset_loaders[ASSET_CLIPMAP] = load_clipmap_ptr


# ==== 2. readers ===================================================================================================

@dataclass
class Brush:
    mins: tuple
    maxs: tuple
    planes: list                  # the non-axial sides: (normal, dist), the solid is n·p <= dist for each
    contents: int
    side_materials: list          # material index per non-axial side


@dataclass
class StaticModelPlacement:
    model: str
    origin: tuple
    inv_scaled_axis: tuple        # 3 rows
    mins: tuple
    maxs: tuple


@dataclass
class SpawnRecord:
    index: int
    name: str
    target: str
    script_noteworthy: str
    origin: tuple
    angles: tuple


@dataclass
class ClipMapInfo:
    name: str
    materials: list               # (name, surfaceFlags, contents)
    brushes: list
    verts: list                   # terrain / mesh collision vertices
    tris: list                    # (a, b, c) into verts
    static_models: list
    submodels: list               # (mins, maxs, ClipInfo address): brush models (doors, movers)
    entities: list                # the entity string as dicts
    spawns: list
    stages: list                  # (name, origin)


def _f(mem, a, n):
    return struct.unpack(f"<{n}f", mem.read(a, 4 * n))


def _cstr(mem, p):
    return mem.cstr(p).decode("latin-1") if p else ""


# Built-in canonical strings (ids below 0x95A1; SL_GetCanonicalString numbers strings added at run time from 0x95A1)
# whose names the game's own data proves: in the Xbox One server's .rdata and .data, a pointer to a scr_const member
# (named by the PDB) with the id 8 bytes after it (the ent_field_t layout: name, canonicalString). 119 ids, each with
# one name and each name with one id. The other built-in ids have no text in the game files.
CANONICAL_NAMES = {
    20: 'agenthealth',
    21: 'agentname',
    22: 'agentteam',
    32: 'alignx',
    33: 'aligny',
    37: 'allowjump',
    38: 'allowladders',
    40: 'alpha',
    47: 'angles',
    52: 'animscript',
    53: 'archived',
    54: 'archivetime',
    57: 'assists',
    58: 'attackeraccuracy',
    78: 'birthtime',
    97: 'classname',
    99: 'code_classname',
    103: 'color',
    149: 'deaths',
    158: 'dmg',
    159: 'dodamagetoall',
    178: 'enemy',
    190: 'extrascore0',
    191: 'extrascore1',
    192: 'playercardpatch',
    194: 'playercardbackground',
    221: 'font',
    222: 'fontscale',
    227: 'forcespectatorclient',
    229: 'foreground',
    242: 'game_extrainfo',
    244: 'glowalpha',
    245: 'glowcolor',
    268: 'hasradar',
    269: 'headicon',
    270: 'headiconteam',
    271: 'health',
    273: 'showinkillcam',
    274: 'hidein3rdperson',
    275: 'hidewhendead',
    277: 'enablehudlighting',
    278: 'hidewheninmenu',
    281: 'hindlegstraceoffset',
    283: 'horzalign',
    286: 'ignoreall',
    287: 'ignoreclosefoliage',
    290: 'ignoreme',
    291: 'ignorerandombulletdamage',
    297: 'insolid',
    303: 'isradarblocked',
    316: 'jumpcost',
    324: 'killcamentity',
    325: 'killcamentitylookat',
    326: 'kills',
    328: 'label',
    332: 'lastattacker',
    343: 'lookahead',
    349: 'looktarget',
    352: 'lowresbackground',
    361: 'maxhealth',
    362: 'maxsightdistsqrd',
    363: 'maxvisibledist',
    371: 'minusedistsq',
    392: 'model',
    396: 'name',
    408: 'node',
    427: 'onlygoodnearestnodes',
    428: 'oriented',
    430: 'origin',
    433: 'owner',
    438: 'parentname',
    450: 'pers',
    463: 'prevnode',
    471: 'psoffsettime',
    473: 'radarmode',
    474: 'radarshowenemydirection',
    475: 'radarstrength',
    497: 'runcost',
    501: 'score',
    504: 'script_linkname',
    506: 'script_noteworthy',
    524: 'sessionstate',
    525: 'sessionteam',
    526: 'sharpturnnotifydist',
    529: 'slidevelocity',
    538: 'sort',
    542: 'spawnflags',
    543: 'spectatekillcam',
    546: 'speed',
    555: 'statelocked',
    556: 'statusicon',
    560: 'stopsoonnotifydist',
    567: 'surfacetype',
    568: 'surprisedbymedistsq',
    570: 'syncedmeleetarget',
    640: 'target',
    642: 'targetname',
    643: 'team',
    651: 'threatbias',
    652: 'threatbiasgroup',
    660: 'traversecost',
    661: 'traversesoonnotifydist',
    677: 'turretinvulnerability',
    680: 'type',
    688: 'veh_brake',
    693: 'veh_pathdir',
    694: 'veh_pathspeed',
    695: 'veh_pathtype',
    697: 'veh_speed',
    698: 'veh_throttle',
    699: 'veh_topspeed',
    700: 'veh_transmission',
    704: 'vertalign',
    731: 'x',
    732: 'y',
    733: 'z',
    736: 'allowprone',
    2483: 'adrenaline',
    2976: 'allowcrouch',
}


def parse_entity_string(text: str, names: dict | None = None) -> list:
    """The map's entity text as a list of dicts. PC zones write a key as its canonical string id (`97 "worldspawn"`)
    or, for a key with no id, as 0 and the key (`0 "aomindist" "16"`); quoted keys (`"classname" "x"`) are read too.
    Ids are named from `names` (default CANONICAL_NAMES); the others become "#<id>"."""
    import re
    names = CANONICAL_NAMES if names is None else names
    ents = []
    for block in re.findall(r"\{([^{}]*)\}", text):
        ent = {}
        for num, key, value in re.findall(r'(?m)^\s*(?:(\d+)\s+)?(?:"([^"]*)"\s+)?"([^"]*)"\s*$', block):
            if num and num != "0" and not key:
                key = names.get(int(num), f"#{num}")
            ent[key] = value
        ents.append(ent)
    return ents


def read_clip_info(mem, ci: int):
    """(materials, brushes) of a ClipInfo."""
    u32 = lambda a: struct.unpack("<I", mem.read(a, 4))[0]
    u64 = lambda a: struct.unpack("<Q", mem.read(a, 8))[0]
    mats = []
    mp = u64(ci + 0x18)
    for i in range(u32(ci + 0x10) if mp else 0):
        m = mp + 0x10 * i
        flags, contents = struct.unpack("<ii", mem.read(m + 8, 8))
        mats.append((_cstr(mem, u64(m)), flags, contents))
    nb = struct.unpack("<H", mem.read(ci + 0x60, 2))[0]
    bp, bounds, cont = u64(ci + 0x68), u64(ci + 0x70), u64(ci + 0x78)
    brushes = []
    for i in range(nb if bp and bounds else 0):
        b = bp + 0x30 * i
        numsides = struct.unpack("<H", mem.read(b, 2))[0]
        sides = u64(b + 8)
        mid, half = _f(mem, bounds + 0x18 * i, 3), _f(mem, bounds + 0x18 * i + 12, 3)
        planes, smats = [], []
        for k in range(numsides if sides else 0):
            sd = sides + 0x10 * k
            pl = u64(sd)
            n4 = _f(mem, pl, 4)
            planes.append((n4[:3], n4[3]))
            smats.append(struct.unpack("<H", mem.read(sd + 8, 2))[0])
        brushes.append(Brush(tuple(m - h for m, h in zip(mid, half)), tuple(m + h for m, h in zip(mid, half)),
                             planes, struct.unpack("<i", mem.read(cont + 4 * i, 4))[0] if cont else 0, smats))
    return mats, brushes


def read_clipmap(mem, c: int) -> ClipMapInfo:
    """A loaded clipMap_t (e.g. the asset pool copy) from any memory image with read(address, n) and cstr."""
    u32 = lambda a: struct.unpack("<I", mem.read(a, 4))[0]
    i32 = lambda a: struct.unpack("<i", mem.read(a, 4))[0]
    u16 = lambda a: struct.unpack("<H", mem.read(a, 2))[0]
    u64 = lambda a: struct.unpack("<Q", mem.read(a, 8))[0]
    mats, brushes = read_clip_info(mem, c + 0x10)
    nv, vp = u32(c + 0xC8), u64(c + 0xD0)
    verts = [_f(mem, vp + 12 * i, 3) for i in range(nv if vp else 0)]
    nt, tp = i32(c + 0xD8), u64(c + 0xE0)
    raw = struct.unpack(f"<{nt * 3}H", mem.read(tp, nt * 6)) if nt > 0 and tp else ()
    tris = [raw[3 * i:3 * i + 3] for i in range(nt if raw else 0)]
    sms = []
    sp = u64(c + 0xA0)
    for i in range(u32(c + 0x98) if sp else 0):
        a = sp + 0x50 * i
        xm = u64(a)
        mid, half = _f(mem, a + 0x38, 3), _f(mem, a + 0x44, 3)
        f = _f(mem, a + 0x14, 9)
        sms.append(StaticModelPlacement(_cstr(mem, u64(xm)) if xm else "", _f(mem, a + 8, 3),
                                        (f[0:3], f[3:6], f[6:9]), tuple(m - h for m, h in zip(mid, half)),
                                        tuple(m + h for m, h in zip(mid, half))))
    subs = []
    cp = u64(c + 0x128)
    for i in range(u32(c + 0x120) if cp else 0):
        a = cp + 0x50 * i
        mid, half = _f(mem, a, 3), _f(mem, a + 12, 3)
        subs.append((tuple(m - h for m, h in zip(mid, half)), tuple(m + h for m, h in zip(mid, half)), u64(a + 0x20)))
    ents, spawns = [], []
    me = u64(c + 0x130)
    if me:
        n, sp = i32(me + 0x10), u64(me + 8)
        if sp and n > 0:
            ents = parse_entity_string(mem.read(sp, n).split(b"\0")[0].decode("latin-1"))
        rp = u64(me + 0xE8)
        for i in range(u16(me + 0xE0) if rp else 0):
            a = rp + 0x28 * i
            names = [getattr(mem, "script_string", lambda v: str(v))(u32(a + o)) for o in (4, 8, 0xC)]
            spawns.append(SpawnRecord(u16(a), *names, _f(mem, a + 0x10, 3), _f(mem, a + 0x1C, 3)))
    stages = []
    stp = u64(c + 0x138)
    for i in range(mem.read(c + 0x140, 1)[0] if stp else 0):
        a = stp + 0x18 * i
        stages.append((_cstr(mem, u64(a)), _f(mem, a + 8, 3)))
    return ClipMapInfo(_cstr(mem, u64(c)), mats, brushes, verts, tris, sms, subs, ents, spawns, stages)


def brush_faces(brush: Brush, eps: float = 1e-3):
    """The brush as convex polygons: the six bounds planes and its side planes, each face clipped by all the others.
    Returns [(polygon vertices, plane index)]; index -1..-6 for the bounds faces."""
    planes = [((-1, 0, 0), -brush.mins[0], -1), ((1, 0, 0), brush.maxs[0], -2),
              ((0, -1, 0), -brush.mins[1], -3), ((0, 1, 0), brush.maxs[1], -4),
              ((0, 0, -1), -brush.mins[2], -5), ((0, 0, 1), brush.maxs[2], -6)]
    planes += [(n, d, i) for i, (n, d) in enumerate(brush.planes)]
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    faces = []
    for n, d, tag in planes:
        # a big quad on the plane
        ax = (1, 0, 0) if abs(n[0]) < 0.9 else (0, 1, 0)
        u = (n[1] * ax[2] - n[2] * ax[1], n[2] * ax[0] - n[0] * ax[2], n[0] * ax[1] - n[1] * ax[0])
        ul = dot(u, u) ** 0.5
        u = tuple(x / ul for x in u)
        v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0])
        c = tuple(x * d for x in n)
        big = 1 << 17
        poly = [tuple(c[k] + big * (su * u[k] + sv * v[k]) for k in range(3))
                for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for n2, d2, tag2 in planes:
            if tag2 == tag or not poly:
                continue
            out = []
            for i in range(len(poly)):
                a, b = poly[i], poly[(i + 1) % len(poly)]
                da, db = dot(n2, a) - d2, dot(n2, b) - d2
                if da <= eps:
                    out.append(a)
                if (da <= eps) != (db <= eps):
                    t = da / (da - db)
                    out.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(3)))
            poly = out
        clean = []
        for p in poly:                         # drop repeated points
            if not clean or max(abs(p[k] - clean[-1][k]) for k in range(3)) > eps:
                clean.append(p)
        if len(clean) > 1 and max(abs(clean[0][k] - clean[-1][k]) for k in range(3)) <= eps:
            clean.pop()
        if len(clean) < 3:
            continue
        area = [0.0, 0.0, 0.0]                 # drop slivers (faces the other planes cut down to an edge)
        for i in range(1, len(clean) - 1):
            a = [clean[i][k] - clean[0][k] for k in range(3)]
            b = [clean[i + 1][k] - clean[0][k] for k in range(3)]
            area[0] += a[1] * b[2] - a[2] * b[1]
            area[1] += a[2] * b[0] - a[0] * b[2]
            area[2] += a[0] * b[1] - a[1] * b[0]
        if dot(area, area) ** 0.5 > eps:
            faces.append((clean, tag))
    return faces
