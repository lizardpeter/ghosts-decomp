"""Differential cases for database/db_load.cpp (the generated top of the zone loader): the script string list, the
XGlobals pointer, the XAsset array's place, Load_XAsset and its type dispatch.

As in test_db_stream.py, block memory is an extra buffer argument and DB_ReadXFile is faked: here its source is
built per input as the stream the function expects (a string table of inline, null and offset entries followed by
the strings; an XGlobals; an XAsset). The 58 Load_<Type>Ptr functions and Load_XGfxGlobals are faked for both runs
and record the variable they were given and their atStreamStart.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX

import test_db_stream as S
from harness import HEAP
from syms import va

INLINE = 0xFDFDFDFFFFFFFFFF

PTR_LOADERS = [
    ( 0, "?Load_PhysPresetPtr@@YAX_N@Z"),
    ( 1, "?Load_PhysCollmapPtr@@YAX_N@Z"),
    ( 2, "?Load_XAnimPartsPtr@@YAX_N@Z"),
    ( 3, "?Load_XModelSurfsPtr@@YAX_N@Z"),
    ( 4, "?Load_XModelPtr@@YAX_N@Z"),
    ( 5, "?Load_MaterialHandle@@YAX_N@Z"),
    ( 6, "?Load_ComputeShaderPtr@@YAX_N@Z"),
    (10, "?Load_MaterialPixelShaderPtr@@YAX_N@Z"),
    ( 7, "?Load_MaterialVertexShaderPtr@@YAX_N@Z"),
    ( 8, "?Load_MaterialHullShaderPtr@@YAX_N@Z"),
    ( 9, "?Load_MaterialDomainShaderPtr@@YAX_N@Z"),
    (11, "?Load_MaterialVertexDeclarationPtr@@YAX_N@Z"),
    (12, "?Load_MaterialTechniqueSetPtr@@YAX_N@Z"),
    (13, "?Load_GfxImagePtr@@YAX_N@Z"),
    (14, "?Load_snd_alias_list_ptr@@YAX_N@Z"),
    (15, "?Load_SndCurvePtr@@YAX_N@Z"),
    (16, "?Load_LpfCurvePtr@@YAX_N@Z"),
    (17, "?Load_ReverbCurvePtr@@YAX_N@Z"),
    (18, "?Load_LoadedSoundPtr@@YAX_N@Z"),
    (19, "?Load_clipMap_ptr@@YAX_N@Z"),
    (20, "?Load_ComWorldPtr@@YAX_N@Z"),
    (21, "?Load_GlassWorldPtr@@YAX_N@Z"),
    (22, "?Load_PathDataPtr@@YAX_N@Z"),
    (23, "?Load_VehicleTrackPtr@@YAX_N@Z"),
    (24, "?Load_MapEntsPtr@@YAX_N@Z"),
    (25, "?Load_FxWorldPtr@@YAX_N@Z"),
    (26, "?Load_GfxWorldPtr@@YAX_N@Z"),
    (27, "?Load_GfxLightDefPtr@@YAX_N@Z"),
    (29, "?Load_FontHandle@@YAX_N@Z"),
    (30, "?Load_MenuListPtr@@YAX_N@Z"),
    (31, "?Load_menuDef_ptr@@YAX_N@Z"),
    (32, "?Load_AnimationClassPtr@@YAX_N@Z"),
    (33, "?Load_LocalizeEntryPtr@@YAX_N@Z"),
    (34, "?Load_WeaponAttachmentPtr@@YAX_N@Z"),
    (35, "?Load_WeaponCompleteDefPtr@@YAX_N@Z"),
    (36, "?Load_SndDriverGlobalsPtr@@YAX_N@Z"),
    (37, "?Load_FxEffectDefHandle@@YAX_N@Z"),
    (38, "?Load_FxImpactTablePtr@@YAX_N@Z"),
    (39, "?Load_SurfaceFxTablePtr@@YAX_N@Z"),
    (44, "?Load_RawFilePtr@@YAX_N@Z"),
    (45, "?Load_ScriptFilePtr@@YAX_N@Z"),
    (46, "?Load_StringTablePtr@@YAX_N@Z"),
    (47, "?Load_LeaderboardDefPtr@@YAX_N@Z"),
    (48, "?Load_StructuredDataDefSetPtr@@YAX_N@Z"),
    (49, "?Load_TracerDefPtr@@YAX_N@Z"),
    (50, "?Load_VehicleDefPtr@@YAX_N@Z"),
    (51, "?Load_AddonMapEntsPtr@@YAX_N@Z"),
    (52, "?Load_NetConstStringsPtr@@YAX_N@Z"),
    (53, "?Load_ReverbPresetPtr@@YAX_N@Z"),
    (54, "?Load_LuaFilePtr@@YAX_N@Z"),
    (55, "?Load_ScriptableDefPtr@@YAX_N@Z"),
    (56, "?Load_ColorizationPtr@@YAX_N@Z"),
    (57, "?Load_ColorizationSetPtr@@YAX_N@Z"),
    (58, "?Load_ToneMappingPtr@@YAX_N@Z"),
    (59, "?Load_EquipmentSoundTablePtr@@YAX_N@Z"),
    (60, "?Load_VectorFieldPtr@@YAX_N@Z"),
    (61, "?Load_DopplerPresetPtr@@YAX_N@Z"),
    (62, "?Load_FxParticleSimAnimationPtr@@YAX_N@Z"),
]


def _rec_ptr(name):
    def fn(mu):
        var = {"?Load_XGfxGlobals@@YAX_N@Z": "varXGfxGlobals"}.get(name)
        S.M["m"].observed.append((name, mu.reg_read(UC_X86_REG_RCX) & 0xFF))
        return 0
    return fn


FAKES = {**S.FAKES, **{sym: _rec_ptr(sym) for _, sym in PTR_LOADERS},
         "?Load_XGfxGlobals@@YAX_N@Z": _rec_ptr("?Load_XGfxGlobals@@YAX_N@Z")}


def inputs(seed, build, n=200):
    """build(r, mem) -> (args, source bytes, extra setup(w) or None)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        mem = S.memory(r)
        args, source, extra = build(r, mem)
        state_seed = r.getrandbits(32)

        def setup(w, state_seed=state_seed, source=source, extra=extra):
            S.M["m"], S.M["source"], S.M["cursor"] = w.m, source + b"\0", 0
            S.stream_state(random.Random(state_seed), w, random.Random(state_seed).choice([0, 3, 3, 3, 2]))
            if extra:
                extra(w)
        out.append({"args": [*args, *([0] * (4 - len(args))), bytes(mem)], "setup": setup})
    return out


def var_in_mem(mem, at, value_bytes):
    mem[at - HEAP:at - HEAP + len(value_bytes)] = value_bytes
    return at


def script_string_list(r, mem):
    count = r.choice([0, 1, 2, 5, 9])
    has = r.random() < 0.85
    lst = HEAP + 0x200
    var_in_mem(mem, lst, struct.pack("<iiQ", count, 0, INLINE if has else 0))
    at_start = r.random() < 0.3
    entries, strings = [], b""
    for _ in range(count):
        k = r.random()
        if k < 0.6:
            entries.append(INLINE)
            strings += bytes(r.choice(b"abc_xyz") for _ in range(r.randrange(0, 9))) + b"\0"
        elif k < 0.8:
            entries.append(0)
        else:
            entries.append(S.packed_offset(r))
    table = struct.pack(f"<{count}Q", *entries)
    # with atStreamStart the list itself is read first
    source = (struct.pack("<iiQ", count, 0, INLINE if has else 0) if at_start else b"") + table + strings

    def extra(w, lst=lst):
        w.u64(va("varScriptStringList"), lst)
    return [int(at_start)], source, extra


def xglobals_ptr(r, mem):
    slot = HEAP + 0x210
    var_in_mem(mem, slot, struct.pack("<Q", r.choice([0, INLINE, 1, r.getrandbits(64)])))
    at_start = r.random() < 0.3
    source = (struct.pack("<Q", r.choice([0, INLINE])) if at_start else b"") + struct.pack(
        "<Q", r.choice([0, 0, INLINE, r.getrandbits(64)]))

    def extra(w, slot=slot):
        w.u64(va("varXGlobalsPtr"), slot)
    return [int(at_start)], source, extra


def xasset(r, mem, read=True):
    asset = HEAP + 0x220
    t = r.choice([t for t, _ in PTR_LOADERS] + [0x1C, 0x28, 0x2B, 0x3F, 0x40, -1])
    var_in_mem(mem, asset, struct.pack("<iiQ", t, 0, INLINE))
    at_start = read and r.random() < 0.5
    t2 = r.choice([t for t, _ in PTR_LOADERS] + [0x2A])
    source = struct.pack("<iiQ", t2, 0, INLINE) if at_start else b""

    def extra(w, asset=asset):
        w.u64(va("varXAsset"), asset)
        w.u64(va("varXAssetHeader"), asset + 8)
    return [int(at_start) if read else r.choice([0, 1])], source, extra


CASES = [
    {"symbol": "?Load_ScriptStringList@@YAX_N@Z", "ret": "void", "fakes": FAKES, "inputs": inputs(0x3A0, script_string_list)},
    {"symbol": "?Load_XGlobalsPtr@@YAX_N@Z", "ret": "void", "fakes": FAKES, "inputs": inputs(0x3A1, xglobals_ptr)},
    {"symbol": "?AllocLoad_XAsset@@YAPEAUXAsset@@XZ", "ret": "int64", "fakes": FAKES,
     "inputs": inputs(0x3A2, lambda r, mem: ([], b"", None))},
    {"symbol": "?Load_XAsset@@YAX_N@Z", "ret": "void", "fakes": FAKES, "inputs": inputs(0x3A3, xasset, n=300)},
    {"symbol": "?Load_XAssetHeader@@YAX_N@Z", "ret": "void", "fakes": FAKES,
     "inputs": inputs(0x3A4, lambda r, mem: xasset(r, mem, read=False), n=300)},
]
