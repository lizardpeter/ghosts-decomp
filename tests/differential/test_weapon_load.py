"""Differential cases for the weapon, attachment and vehicle zone loaders (src/bgame/bg_weapons_load_db.cpp) against
the Store build.

The stream functions are dbstream.py's logged fakes; each loader's callees (the nested Load_* functions, the asset
pointer loaders of materials, models, animations, effects, physics assets and tracers, Load_SndAliasCustom,
Load_ScriptStringCustom and the Load_<T>Asset linkers) are logged fakes recording the stream variables they see.
Structures are random: every pointer field null, inline, insert or an offset, override and knot counts of 0, 1 and
more. The pointer fields come from the PDB's layouts (tools/fastfile/pdbtypes.py). tools/fastfile/weapon.py is the
same logic, checked against the game on real zones (docs/assets/weapons.md).
"""
import random
import struct
import sys
from pathlib import Path

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_AUX, OFF_STRUCT
from harness import HEAP
from syms import va

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import pdbtypes  # noqa: E402

STORE = "iw6mp64_MSStore_ship"


def _rec(name, spec, *globals_):
    return ds.recorder(name, spec, globals_)


def _ptr_rec(name, var):
    return _rec(name, "b", var)


def _snd(mu):
    p = ds.arg(mu, 0)
    ds.log("Load_SndAliasCustom", p, ds.u64(mu, p) if ds.in_buffer(p, 8) else None)


def _script_string(mu):
    p = ds.arg(mu, 0)
    v = ds.u32(mu, p) if ds.in_buffer(p, 4) else None
    ds.log("Load_ScriptStringCustom", p, v)
    if v is not None:
        ds.write(p, struct.pack("<I", (v * 7 + 1) & 0xFFFFFFFF))


ASSET = {
    "WeaponAttachment": "?Load_WeaponAttachmentAsset@@YAXPEAPEAUWeaponAttachment@@@Z",
    "WeaponCompleteDef": "?Load_WeaponCompleteDefAsset@@YAXPEAPEAUWeaponCompleteDef@@@Z",
    "VehicleDef": "?Load_VehicleDefAsset@@YAXPEAPEAUVehicleDef@@@Z",
    "XAnimParts": "?Load_XAnimPartsAsset@@YAXPEAPEAUXAnimParts@@@Z",
}

FAKES = {
    **ds.STREAM_FAKES,
    **{sym: ds.asset_linker(f"Load_{k}Asset") for k, sym in ASSET.items()},
    "?Load_MaterialHandle@@YAX_N@Z": _ptr_rec("Load_MaterialHandle", "varMaterialHandle"),
    "?Load_MaterialHandleArray@@YAX_N_K@Z": _rec("Load_MaterialHandleArray", "bq", "varMaterialHandle", "g_streamPos"),
    "?Load_XModelPtr@@YAX_N@Z": _ptr_rec("Load_XModelPtr", "varXModelPtr"),
    "?Load_XModelPtrArray@@YAX_N_K@Z": _rec("Load_XModelPtrArray", "bq", "varXModelPtr", "g_streamPos"),
    "?Load_XAnimParts@@YAX_N@Z": _rec("Load_XAnimParts", "b", "varXAnimParts", "g_streamPos"),
    "?Load_XAnimPartsPtr@@YAX_N@Z": _ptr_rec("Load_XAnimPartsPtr", "varXAnimPartsPtr"),
    "?Load_XAnimPartsPtrArray@@YAX_N_K@Z": _rec("Load_XAnimPartsPtrArray", "bq", "varXAnimPartsPtr", "g_streamPos"),
    "?Load_FxEffectDefHandle@@YAX_N@Z": _ptr_rec("Load_FxEffectDefHandle", "varFxEffectDefHandle"),
    "?Load_FxEffectDefHandleArray@@YAX_N_K@Z": _rec("Load_FxEffectDefHandleArray", "bq", "varFxEffectDefHandle",
                                                   "g_streamPos"),
    "?Load_PhysCollmapPtr@@YAX_N@Z": _ptr_rec("Load_PhysCollmapPtr", "varPhysCollmapPtr"),
    "?Load_PhysPresetPtr@@YAX_N@Z": _ptr_rec("Load_PhysPresetPtr", "varPhysPresetPtr"),
    "?Load_TracerDefPtr@@YAX_N@Z": _ptr_rec("Load_TracerDefPtr", "varTracerDefPtr"),
    "?Load_SndAliasCustom@@YAXPEAPEAUsnd_alias_list_t@@@Z": _snd,
    "?Load_ScriptStringCustom@@YAXPEAW4scr_string_t@@@Z": _script_string,
    "?Load_ADSOverlay@@YAX_N@Z": _rec("Load_ADSOverlay", "b", "varADSOverlay", "g_streamPos"),
    "?Load_AttRumbles@@YAX_N@Z": _rec("Load_AttRumbles", "b", "varAttRumbles", "g_streamPos"),
    "?Load_AttProjectile@@YAX_N@Z": _rec("Load_AttProjectile", "b", "varAttProjectile", "g_streamPos"),
    "?Load_NoteTrackToSoundEntry@@YAX_N@Z": _rec("Load_NoteTrackToSoundEntry", "b", "varNoteTrackToSoundEntry",
                                                "g_streamPos"),
    "?Load_WeaponDef@@YAX_N@Z": _rec("Load_WeaponDef", "b", "varWeaponDef", "g_streamPos"),
    "?Load_WeaponAttachment@@YAX_N@Z": _rec("Load_WeaponAttachment", "b", "varWeaponAttachment", "g_streamPos"),
    "?Load_WeaponAttachmentPtr@@YAX_N@Z": _ptr_rec("Load_WeaponAttachmentPtr", "varWeaponAttachmentPtr"),
    "?Load_WeaponAttachmentPtrArray@@YAX_N_K@Z": _rec("Load_WeaponAttachmentPtrArray", "bq",
                                                     "varWeaponAttachmentPtr", "g_streamPos"),
    "?Load_WeaponCompleteDef@@YAX_N@Z": _rec("Load_WeaponCompleteDef", "b", "varWeaponCompleteDef", "g_streamPos"),
    "?Load_WeaponCompleteDefPtr@@YAX_N@Z": _ptr_rec("Load_WeaponCompleteDefPtr", "varWeaponCompleteDefPtr"),
    "?Load_VehiclePhysDef@@YAX_N@Z": _rec("Load_VehiclePhysDef", "b", "varVehiclePhysDef", "g_streamPos"),
    "?Load_VehicleDef@@YAX_N@Z": _rec("Load_VehicleDef", "b", "varVehicleDef", "g_streamPos"),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    fakes = {k: v for k, v in FAKES.items() if k != symbol}
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": fakes, "inputs": [make(rnd) for _ in range(n)]}


def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & 0xFFFFFFFFFFFFFFFF)


def _pointer_offsets(name):
    """Every pointer field of the PDB's struct, arrays of pointers included."""
    out = []
    for f in pdbtypes.types()[0][name].fields:
        if f.pointers:
            n = 1
            for d in f.dims:
                n *= d
            if (name, f.name) in pdbtypes.RAW_POINTER_PAIRS:
                n = 2
            out += [f.offset + 8 * i for i in range(n)]
    return out


def _struct(r, name, size, counts=()):
    b = bytearray(r.randbytes(size))
    for off in _pointer_offsets(name):
        _q(b, off, ds.pointer(r, inline=0.45, insert=0.1))
    for off, fmt, top in counts:          # loop counts kept small: a huge one only times out
        struct.pack_into("<" + fmt, b, off, r.choice([0, 1, 2, r.randint(0, top)]))
    return b


def _input(r, struct_bytes, var_values, aux=None, feed=0x2000, extra_args=()):
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    if aux is not None:
        buf[OFF_AUX:OFF_AUX + len(aux)] = aux
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + r.randbytes(feed))

    def setup(w):
        zone.start(w)
        for name, value in var_values.items():
            w.u64(va(name), value)
    return {"args": [flag, *extra_args, bytes(buf)], "setup": setup}


KNOT_COUNTS = ((0x104, "H", 40), (0x106, "H", 40))
OVERRIDE_COUNTS = ((0x40, "I", 5), (0x50, "I", 5), (0x60, "I", 5), (0x70, "I", 5), (0x80, "I", 4))


def _body(var, name, size, counts=(), aux_var=None, aux_name=None, aux_size=0, aux_counts=()):
    def make(r):
        values = {var: HEAP + OFF_STRUCT}
        aux = None
        if aux_var:
            aux = _struct(r, aux_name, aux_size, aux_counts)
            values[aux_var] = HEAP + OFF_AUX
        return _input(r, _struct(r, name, size, counts), values, aux=aux)
    return make


def _handle_ptr(var, inner):
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        _q(buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))
        stale = HEAP + 0x30000 + r.getrandbits(8)

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            w.u64(va(inner), stale)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _ptr_array(var, top=6):
    def make(r):
        n = r.choice([0, 1, 2, r.randint(0, top)])
        b = bytearray()
        for _ in range(n):
            b += struct.pack("<Q", ds.pointer(r, inline=0.45, insert=0.15) & 0xFFFFFFFFFFFFFFFF)
        return _input(r, bytes(b), {var: HEAP + OFF_STRUCT}, extra_args=(n,))
    return make


CASES = [
    case("?Load_ADSOverlay@@YAX_N@Z", 0xA080, _body("varADSOverlay", "ADSOverlay", 0x38)),
    case("?Load_AttRumbles@@YAX_N@Z", 0xAEA0, _body("varAttRumbles", "AttRumbles", 0x10)),
    case("?Load_AttProjectile@@YAX_N@Z", 0xAD20, _body("varAttProjectile", "AttProjectile", 0x90)),
    case("?Load_NoteTrackToSoundEntry@@YAX_N@Z", 0x4C50,
         _body("varNoteTrackToSoundEntry", "NoteTrackToSoundEntry", 0x18)),
    case("?Load_XAnimPartsPtrArray@@YAX_N_K@Z", 0xD4C0, _ptr_array("varXAnimPartsPtr")),
    case("?Load_WeaponAttachment@@YAX_N@Z", 0x9A30, _body("varWeaponAttachment", "WeaponAttachment", 0x118)),
    case("?Load_WeaponAttachmentPtr@@YAX_N@Z", 0xA240, _handle_ptr("varWeaponAttachmentPtr", "varWeaponAttachment")),
    case("?Load_WeaponAttachmentPtrArray@@YAX_N_K@Z", 0xA330, _ptr_array("varWeaponAttachmentPtr")),
    case("?Load_WeaponDef@@YAX_N@Z", 0xAD90,
         _body("varWeaponDef", "WeaponDef", 0xA98, aux_var="varWeaponCompleteDef", aux_name="WeaponCompleteDef",
               aux_size=0x128, aux_counts=KNOT_COUNTS)),
    case("?Load_WeaponCompleteDef@@YAX_N@Z", 0xA460,
         _body("varWeaponCompleteDef", "WeaponCompleteDef", 0x128, KNOT_COUNTS + OVERRIDE_COUNTS)),
    case("?Load_WeaponCompleteDefPtr@@YAX_N@Z", 0xACA0,
         _handle_ptr("varWeaponCompleteDefPtr", "varWeaponCompleteDef")),
    case("?Load_VehiclePhysDef@@YAX_N@Z", 0x9240, _body("varVehiclePhysDef", "VehiclePhysDef", 0xC8)),
    case("?Load_VehicleDef@@YAX_N@Z", 0x8960, _body("varVehicleDef", "VehicleDef", 0x610)),
    case("?Load_VehicleDefPtr@@YAX_N@Z", 0x9150, _handle_ptr("varVehicleDefPtr", "varVehicleDef")),
]
