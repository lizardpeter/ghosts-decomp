"""Differential cases for src/database/db_misc_load_db.cpp (Lua files, sound driver globals, reverb presets, vector
fields, leaderboards, compute shaders) against the Store build: random headers (every pointer null, inline, insert or
an offset; counts of 0, 1 and more) with dbstream.py's logged stream fakes and logged fakes for the nested loaders,
the asset linkers and Load_CreateComputeShader. tools/fastfile/misc_assets.py is the same logic, checked against the
game on real zones (docs/assets/misc.md)."""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
M64 = 2 ** 64 - 1

FAKES = {
    **ds.STREAM_FAKES,
    "?Load_LuaFileAsset@@YAXPEAPEAULuaFile@@@Z": ds.asset_linker("Load_LuaFileAsset"),
    "?Load_SndDriverGlobalsAsset@@YAXPEAPEAUSndDriverGlobals@@@Z": ds.asset_linker("Load_SndDriverGlobalsAsset"),
    "?Load_ReverbPresetAsset@@YAXPEAPEAUReverbPreset@@@Z": ds.asset_linker("Load_ReverbPresetAsset"),
    "?Load_VectorFieldAsset@@YAXPEAPEAUVectorField@@@Z": ds.asset_linker("Load_VectorFieldAsset"),
    "?Load_LeaderboardDefAsset@@YAXPEAPEAULeaderboardDef@@@Z": ds.asset_linker("Load_LeaderboardDefAsset"),
    "?Load_ComputeShaderAsset@@YAXPEAPEAUComputeShader@@@Z": ds.asset_linker("Load_ComputeShaderAsset"),
    "?Load_CreateComputeShader@@YAXPEAPEAEPEAUComputeShader@@@Z":
        ds.recorder("Load_CreateComputeShader", "qq", ("varbyte4",)),
    "?Load_LuaFile@@YAX_N@Z": ds.recorder("Load_LuaFile", "b", ("varLuaFile", "g_streamPos")),
    "?Load_SndDriverGlobals@@YAX_N@Z": ds.recorder("Load_SndDriverGlobals", "b", ("varSndDriverGlobals", "g_streamPos")),
    "?Load_ReverbPreset@@YAX_N@Z": ds.recorder("Load_ReverbPreset", "b", ("varReverbPreset", "g_streamPos")),
    "?Load_VectorField@@YAX_N@Z": ds.recorder("Load_VectorField", "b", ("varVectorField", "g_streamPos")),
    "?Load_LeaderboardDef@@YAX_N@Z": ds.recorder("Load_LeaderboardDef", "b", ("varLeaderboardDef", "g_streamPos")),
    "?Load_LbColumnDef@@YAX_N@Z": ds.recorder("Load_LbColumnDef", "b", ("varLbColumnDef", "g_streamPos")),
    "?Load_ComputeShader@@YAX_N@Z": ds.recorder("Load_ComputeShader", "b", ("varComputeShader", "g_streamPos")),
    "?Load_GfxComputeShaderLoadDef@@YAX_N@Z":
        ds.recorder("Load_GfxComputeShaderLoadDef", "b", ("varGfxComputeShaderLoadDef", "g_streamPos")),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    return {"symbol": symbol, "build": STORE, "ret": "void",
            "fakes": {k: v for k, v in FAKES.items() if k != symbol}, "inputs": [make(rnd) for _ in range(n)]}


def _loader(size, var, fill, feed=0x2000, extra=()):
    """A header of `size` random bytes with `fill` applied, at var; `extra` names more globals to point into the
    buffer (var, offset into the header)."""
    def make(r):
        b = bytearray(r.randbytes(size))
        struct.pack_into("<Q", b, 0, ds.pointer(r) & M64)
        fill(r, b)
        flag = r.random() < 0.5
        buf = bytearray(r.randbytes(ds.BUF_SIZE))
        buf[OFF_STRUCT:OFF_STRUCT + size] = b
        zone = ds.Zone(r, (bytes(b) if flag else b"") + r.randbytes(feed))

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            for v, off in extra:
                w.u64(va(v), HEAP + OFF_STRUCT + off)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _any(r):
    return r.choice([0, 1, FOLLOWING, r.getrandbits(64)])


def _lua(r, b):
    struct.pack_into("<i", b, 8, r.choice([0, 1, 7, 33, -1, -0x40, r.randint(0, 0x400)]))
    struct.pack_into("<Q", b, 0x10, _any(r))


def _snd(r, b):
    struct.pack_into("<Q", b, 0x10, _any(r))


def _vector_field(r, b):
    struct.pack_into("<Q", b, 8, ds.pointer(r) & M64)
    struct.pack_into("<3I", b, 0x34, *(r.choice([0, 1, 2, 3, 5]) for _ in range(3)))


def _leaderboard(r, b):
    struct.pack_into("<i", b, 0xC, r.choice([0, 1, 2, r.randint(0, 6)]))
    struct.pack_into("<Q", b, 0x18, _any(r))


def _column(r, b):
    struct.pack_into("<Q", b, 0x18, ds.pointer(r) & M64)


def _compute_shader(r, b):
    struct.pack_into("<Q", b, 0x10, ds.pointer(r) & M64)
    struct.pack_into("<I", b, 0x18, r.choice([0, 4, 0x40, r.randint(0, 0x800)]))


def _load_def(r, b):
    struct.pack_into("<Q", b, 0, ds.pointer(r) & M64)
    struct.pack_into("<I", b, 8, r.choice([0, 4, 0x40, 0x80000000 | r.getrandbits(4), r.randint(0, 0x800)]))


def _handle(var, inner):
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        struct.pack_into("<Q", buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            w.u64(va(inner), HEAP + 0x30000 + r.getrandbits(8))
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _ptr_case(name, seed):
    return case(f"?Load_{name}Ptr@@YAX_N@Z", seed, _handle(f"var{name}Ptr", f"var{name}"))


CASES = [
    case("?Load_LuaFile@@YAX_N@Z", 0x2A50, _loader(0x18, "varLuaFile", _lua)),
    _ptr_case("LuaFile", 0x2B20),
    case("?Load_SndDriverGlobals@@YAX_N@Z", 0x6EC0, _loader(0x18, "varSndDriverGlobals", _snd)),
    _ptr_case("SndDriverGlobals", 0x6F90),
    case("?Load_ReverbPreset@@YAX_N@Z", 0x5A90, _loader(0x48, "varReverbPreset", lambda r, b: None)),
    _ptr_case("ReverbPreset", 0x5B20),
    case("?Load_VectorField@@YAX_N@Z", 0x8770, _loader(0x50, "varVectorField", _vector_field)),
    _ptr_case("VectorField", 0x8870),
    case("?Load_LbColumnDef@@YAX_N@Z", 0x2280, _loader(0x38, "varLbColumnDef", _column)),
    case("?Load_LeaderboardDef@@YAX_N@Z", 0x2360, _loader(0x28, "varLeaderboardDef", _leaderboard)),
    _ptr_case("LeaderboardDef", 0x2470),
    case("?Load_GfxComputeShaderLoadDef@@YAX_N@Z", 0xEF40,
         _loader(0x10, "varGfxComputeShaderLoadDef", _load_def, extra=(("varComputeShader", 0x100),))),
    case("?Load_ComputeShader@@YAX_N@Z", 0xBE80, _loader(0x20, "varComputeShader", _compute_shader)),
    _ptr_case("ComputeShader", 0xBF40),
]


# ==== vehicle tracks, structured data, equipment sounds, add-on map entities ========================================
# Arrays and their elements come from the zone, so the zone bytes are laid out in the order each loader reads them
# (an inline XString as the fake reads it: a length byte and the letters); nested loaders that are fakes read nothing.

def _rec(name, spec, *globals_):
    return ds.recorder(name, spec, globals_)


FAKES.update({
    "?Load_VehicleTrackAsset@@YAXPEAPEAUVehicleTrack@@@Z": ds.asset_linker("Load_VehicleTrackAsset"),
    "?Load_StructuredDataDefAsset@@YAXPEAPEAUStructuredDataDefSet@@@Z": ds.asset_linker("Load_StructuredDataDefAsset"),
    "?Load_EquipmentSoundTableAsset@@YAXPEAPEAUEquipmentSoundTable@@@Z":
        ds.asset_linker("Load_EquipmentSoundTableAsset"),
    "?Load_AddonMapEntsAsset@@YAXPEAPEAUAddonMapEnts@@@Z": ds.asset_linker("Load_AddonMapEntsAsset"),
    "?Load_VehicleTrack@@YAX_N@Z": _rec("Load_VehicleTrack", "b", "varVehicleTrack", "g_streamPos"),
    "?Load_VehicleTrackSegment@@YAX_N@Z": _rec("Load_VehicleTrackSegment", "b", "varVehicleTrackSegment", "g_streamPos"),
    "?Load_VehicleTrackSegment_ptrArray@@YAX_N_K@Z":
        _rec("Load_VehicleTrackSegment_ptrArray", "bq", "varVehicleTrackSegment_ptr", "g_streamPos"),
    "?Load_VehicleTrackSegmentArray@@YAX_N_K@Z":
        _rec("Load_VehicleTrackSegmentArray", "bq", "varVehicleTrackSegment", "g_streamPos"),
    "?Load_StructuredDataDefSet@@YAX_N@Z":
        _rec("Load_StructuredDataDefSet", "b", "varStructuredDataDefSet", "g_streamPos"),
    "?Load_StructuredDataDefArray@@YAX_N_K@Z":
        _rec("Load_StructuredDataDefArray", "bq", "varStructuredDataDef", "g_streamPos"),
    "?Load_StructuredDataEnum@@YAX_N@Z": _rec("Load_StructuredDataEnum", "b", "varStructuredDataEnum", "g_streamPos"),
    "?Load_StructuredDataStruct@@YAX_N@Z":
        _rec("Load_StructuredDataStruct", "b", "varStructuredDataStruct", "g_streamPos"),
    "?Load_ScriptStringCustom@@YAXPEAW4scr_string_t@@@Z": _rec("Load_ScriptStringCustom", "q", "varscr_string_t"),
    "?Load_EquipmentSoundTable@@YAX_N@Z":
        _rec("Load_EquipmentSoundTable", "b", "varEquipmentSoundTable", "g_streamPos"),
    "?Load_EquipmentSoundSetArray@@YAX_N_K@Z":
        _rec("Load_EquipmentSoundSetArray", "bq", "varEquipmentSoundSet", "g_streamPos"),
    "?Load_EquipSoundSetMoveTypesArray@@YAX_N_K@Z":
        _rec("Load_EquipSoundSetMoveTypesArray", "bq", "varEquipSoundSetMoveTypes", "g_streamPos"),
    "?Load_EquipmentChanceRattleTypesArray@@YAX_N_K@Z":
        _rec("Load_EquipmentChanceRattleTypesArray", "bq", "varEquipmentChanceRattleTypes", "g_streamPos"),
    "?Load_SndAliasCustom@@YAXPEAPEAUsnd_alias_list_t@@@Z":
        _rec("Load_SndAliasCustom", "q", "varsnd_alias_list_name", "varEquipmentSoundSet"),
    "?Load_AddonMapEnts@@YAX_N@Z": _rec("Load_AddonMapEnts", "b", "varAddonMapEnts", "g_streamPos"),
    "?Load_MapTriggers@@YAX_N@Z": _rec("Load_MapTriggers", "b", "varMapTriggers", "g_streamPos"),
    "?Load_ClipInfo@@YAX_N@Z": _rec("Load_ClipInfo", "b", "varClipInfo", "g_streamPos", "varcmodel2_t"),
})


def _small(r, top=3):
    return r.choice([0, 1, r.randint(0, top), top])


def _nonnull(r, null=0.25):
    return 0 if r.random() < null else r.choice([FOLLOWING, r.getrandbits(64) | 1])


def _xs(r, value):
    """The zone bytes the XString fake reads for a pointer field holding `value`."""
    if value != FOLLOWING:
        return b""
    n = r.randrange(24)
    return bytes([n]) + r.randbytes(n)


def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & M64)


def _get_q(b, off):
    return struct.unpack_from("<Q", b, off)[0]


def _get_u(b, off):
    return struct.unpack_from("<I", b, off)[0]


def _input(r, struct_bytes, feed, var_values, flag=None, aux=None):
    """The structure at OFF_STRUCT (`aux` at OFF_AUX); the zone is the structure when the loader is called with
    atStreamStart, then `feed`. var_values: global -> offset into the buffer."""
    flag = r.random() < 0.5 if flag is None else flag
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    if aux is not None:
        buf[ds.OFF_AUX:ds.OFF_AUX + len(aux)] = aux
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + bytes(feed) + r.randbytes(0x80))

    def setup(w):
        zone.start(w)
        for name, off in var_values.items():
            w.u64(va(name), HEAP + off)
    return {"args": [flag, bytes(buf)], "setup": setup}


def _array_input(r, element, var, aux=None, aux_var=None, top=3):
    """An array loader's input: (atStreamStart, count) with count small elements built by `element(r)` ->
    (bytes, feed after all elements)."""
    count = _small(r, top)
    elems = [element(r) for _ in range(count)]
    data = b"".join(e[0] for e in elems)
    feed = b"".join(e[1] for e in elems)
    inp = _input(r, data, feed, {var: OFF_STRUCT, **({aux_var: ds.OFF_AUX} if aux_var else {})}, aux=aux)
    inp["args"].insert(1, count)
    return inp


# ---- vehicle tracks ----

def _sector(r):
    s = bytearray(r.randbytes(0x48))
    _q(s, 0x38, _nonnull(r))
    struct.pack_into("<I", s, 0x40, _small(r, 4))
    return bytes(s)


def _segment(r):
    """(the segment's bytes, what its body reads after them)."""
    s = bytearray(r.randbytes(0x48))
    _q(s, 0, ds.pointer(r))
    _q(s, 8, _nonnull(r))
    struct.pack_into("<I", s, 0x10, _small(r, 3))
    for off in (0x18, 0x28):
        _q(s, off, _nonnull(r))
        struct.pack_into("<I", s, off + 8, _small(r, 3))
    feed = _xs(r, _get_q(s, 0))
    if _get_q(s, 8):
        sectors = [_sector(r) for _ in range(_get_u(s, 0x10))]
        feed += b"".join(sectors)
        for x in sectors:
            if _get_q(x, 0x38):
                feed += r.randbytes(0xC * _get_u(x, 0x40))
    return bytes(s), feed


def _segment_input(r):
    s, feed = _segment(r)
    return _input(r, s, feed, {"varVehicleTrackSegment": OFF_STRUCT})


def _segment_ptr_input(r):
    count = _small(r, 4)
    slots = b"".join(struct.pack("<Q", ds.pointer(r) & M64) for _ in range(count))
    inp = _input(r, slots, b"", {"varVehicleTrackSegment_ptr": OFF_STRUCT})
    inp["args"].insert(1, count)
    return inp


def _vehicle_track(r):
    b = bytearray(r.randbytes(0x18))
    _q(b, 0, ds.pointer(r))
    _q(b, 8, ds.pointer(r))
    struct.pack_into("<I", b, 0x10, r.choice([0, 1, 3, 0x80000001]))
    return _input(r, b, _xs(r, _get_q(b, 0)), {"varVehicleTrack": OFF_STRUCT})


# ---- structured data ----

def _counted(size, count_off, ptr_off, item, top=4):
    def make(r):
        b = bytearray(r.randbytes(size))
        struct.pack_into("<i", b, count_off, r.choice([0, 1, _small(r, top), top]))
        _q(b, ptr_off, _nonnull(r))
        n = struct.unpack_from("<i", b, count_off)[0]
        return bytes(b), (r.randbytes(item * n) if _get_q(b, ptr_off) else b"")
    return make


_enum = _counted(0x10, 0, 8, 8)
_struct = _counted(0x18, 0, 8, 0x14)


def _plain_input(element, var):
    def make(r):
        b, feed = element(r)
        return _input(r, b, feed, {var: OFF_STRUCT})
    return make


def _def(r):
    b = bytearray(r.randbytes(0x58))
    feed = b""
    for count_off, ptr_off, item in ((8, 0x10, 0x10), (0x18, 0x20, 0x18), (0x28, 0x30, 0x10), (0x38, 0x40, 0x10)):
        n = r.choice([0, 1, _small(r, 3), 3])
        struct.pack_into("<i", b, count_off, n)
        _q(b, ptr_off, _nonnull(r))
        if _get_q(b, ptr_off):
            feed += r.randbytes(item * n)
    return bytes(b), feed


def _def_set(r):
    b = bytearray(r.randbytes(0x18))
    _q(b, 0, ds.pointer(r))
    struct.pack_into("<I", b, 8, r.choice([0, 1, 2, 0x80000000]))
    _q(b, 0x10, _nonnull(r))
    return _input(r, b, _xs(r, _get_q(b, 0)), {"varStructuredDataDefSet": OFF_STRUCT})


# ---- equipment sounds ----

def _table_aux(r):
    t = bytearray(r.randbytes(0x58))
    struct.pack_into("<3I", t, 8, _small(r, 3), _small(r, 3), _small(r, 4))
    return t


def _equip_array(element):
    def make(r):
        t = _table_aux(r)
        return _array_input(r, lambda rr: element(rr, t), "", aux=t, aux_var="varEquipmentSoundTable")
    return make


def _sound_set(r, t):
    return r.randbytes(0x10), b""


def _move_types(r, t):
    return struct.pack("<Q", _nonnull(r) & M64), b""


def _chance_rattle(r, t):
    v = _nonnull(r)
    feed = b""
    if v:
        inner = [_nonnull(r) for _ in range(_get_u(t, 0xC))]
        feed += b"".join(struct.pack("<Q", x & M64) for x in inner)
        for x in inner:
            if x:
                feed += r.randbytes(0xC * _get_u(t, 0x10))
    return struct.pack("<Q", v & M64), feed


def _equip_array_input(element, var):
    def make(r):
        t = _table_aux(r)
        return _array_input(r, lambda rr: element(rr, t), var, aux=t, aux_var="varEquipmentSoundTable")
    return make


def _equip_table(r):
    b = _table_aux(r)
    _q(b, 0, ds.pointer(r))
    for off in (0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50):
        _q(b, off, _nonnull(r))
    clothes, rattles = _get_u(b, 8), _get_u(b, 0xC)
    feed = _xs(r, _get_q(b, 0))
    for off, count, size in ((0x18, clothes, 8), (0x20, rattles, 0x10)):
        if _get_q(b, off):
            elems = []
            for _ in range(count):
                e = bytearray(r.randbytes(size))
                _q(e, 0, ds.pointer(r))
                elems.append(e)
            feed += b"".join(elems) + b"".join(_xs(r, _get_q(e, 0)) for e in elems)
    if _get_q(b, 0x50):
        feed += r.randbytes(0xE0 * clothes)
    return _input(r, b, feed, {"varEquipmentSoundTable": OFF_STRUCT})


# ---- add-on map entities ----

def _addon(r):
    b = bytearray(r.randbytes(0x68))
    _q(b, 0, ds.pointer(r))
    _q(b, 8, _nonnull(r))
    struct.pack_into("<i", b, 0x10, r.choice([0, 1, 9, 40]))
    _q(b, 0x48, ds.pointer(r))
    struct.pack_into("<I", b, 0x50, _small(r, 3))
    _q(b, 0x58, _nonnull(r))
    _q(b, 0x60, _nonnull(r))
    feed = _xs(r, _get_q(b, 0))
    if _get_q(b, 8):
        feed += r.randbytes(struct.unpack_from("<i", b, 0x10)[0])
    if _get_q(b, 0x58):
        for _ in range(_get_u(b, 0x50)):
            m = bytearray(r.randbytes(0x50))
            _q(m, 0x20, ds.pointer(r))
            feed += m
    return _input(r, b, feed, {"varAddonMapEnts": OFF_STRUCT})


CASES += [
    case("?Load_VehicleTrackSegment@@YAX_N@Z", 0x9520, _segment_input),
    case("?Load_VehicleTrackSegment_ptrArray@@YAX_N_K@Z", 0x9970, _segment_ptr_input),
    case("?Load_VehicleTrackSegmentArray@@YAX_N_K@Z", 0x9720,
         lambda r: _array_input(r, _segment, "varVehicleTrackSegment")),
    case("?Load_VehicleTrack@@YAX_N@Z", 0x9340, _vehicle_track),
    _ptr_case("VehicleTrack", 0x9430),
    case("?Load_StructuredDataEnum@@YAX_N@Z", 0x7FC0, _plain_input(_enum, "varStructuredDataEnum")),
    case("?Load_StructuredDataStruct@@YAX_N@Z", 0x80A0, _plain_input(_struct, "varStructuredDataStruct")),
    case("?Load_StructuredDataDefArray@@YAX_N_K@Z", 0x7BF0, lambda r: _array_input(r, _def, "varStructuredDataDef")),
    case("?Load_StructuredDataDefSet@@YAX_N@Z", 0x7E00, _def_set),
    case("?Load_StructuredDataDefSetPtr@@YAX_N@Z", 0x7ED0,
         _handle("varStructuredDataDefSetPtr", "varStructuredDataDefSet")),
    case("?Load_EquipmentSoundSetArray@@YAX_N_K@Z", 0xC5C0, _equip_array_input(_sound_set, "varEquipmentSoundSet")),
    case("?Load_EquipSoundSetMoveTypesArray@@YAX_N_K@Z", 0xC3B0,
         _equip_array_input(_move_types, "varEquipSoundSetMoveTypes")),
    case("?Load_EquipmentChanceRattleTypesArray@@YAX_N_K@Z", 0xC460,
         _equip_array_input(_chance_rattle, "varEquipmentChanceRattleTypes")),
    case("?Load_EquipmentSoundTable@@YAX_N@Z", 0xC670, _equip_table),
    _ptr_case("EquipmentSoundTable", 0xCB70),
    case("?Load_AddonMapEnts@@YAX_N@Z", 0xA100, _addon),
    _ptr_case("AddonMapEnts", 0xA370),
]
