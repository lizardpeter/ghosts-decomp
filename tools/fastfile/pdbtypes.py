#!/usr/bin/env python3
"""Struct layouts from the servers' PDB (analysis/iw6_ds_ps4/pdb/types.h), and a reader that walks loaded asset memory
with them.

The Store build's asset layouts are the servers' wherever its loaders have been checked (the docs of each asset type
list the exceptions), so the PDB's field names, types and enums describe what tools/fastfile's loaders leave in
memory. `read_struct(mem, address, "WeaponDef", ctx)` gives a dict of every field: numbers, enum names, strings,
script strings, the names of referenced assets, nested structs, and the arrays behind pointers whose counts are
known (`COUNTS`; the caller can add its own).

    python3 tools/fastfile/pdbtypes.py WeaponDef      # print a layout
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

TYPES_H = Path(__file__).resolve().parents[2] / "analysis" / "iw6_ds_ps4" / "pdb" / "types.h"

PRIMITIVES = {
    "char": "b", "signed char": "b", "unsigned char": "B", "bool": "?", "int8_t": "b", "uint8_t": "B",
    "int16_t": "h", "uint16_t": "H", "short": "h", "unsigned short": "H", "int32_t": "i", "uint32_t": "I",
    "int": "i", "unsigned int": "I", "long": "i", "unsigned long": "I", "int64_t": "q", "uint64_t": "Q",
    "float": "f", "double": "d", "scr_string_t": "I",
}

# Pointers to these are asset references: read as the asset's name (its header's first field, or the field the
# asset type keeps its name in).
ASSET_NAME_AT = {"XModel": 0, "Material": 0, "FxEffectDef": 0, "snd_alias_list_t": 0, "XAnimParts": 0,
                 "PhysCollmap": 0, "PhysPreset": 0, "TracerDef": 0, "WeaponAttachment": 0, "WeaponCompleteDef": 0,
                 "GfxImage": 0x60, "GfxLightDef": 0, "FxParticleSimAnimation": 0, "ScriptableDef": 0,
                 "Colorization": 0x28, "ToneMapping": 0x68, "VehicleDef": 0, "XModelSurfs": 0}


@dataclass
class Field:
    offset: int
    type: str            # base type name, without pointers or const
    pointers: int        # number of '*'
    name: str
    dims: tuple = ()     # array dimensions


@dataclass
class Struct:
    name: str
    size: int
    kind: str            # struct or union
    fields: list = field(default_factory=list)
    bases: list = field(default_factory=list)


_FIELD = re.compile(r"/\* 0x([0-9a-f]+) \*/ (.+?) ?([A-Za-z_]\w*)((?:\[\d+\])*);")


def _clean(t: str):
    t = t.replace("const ", "").replace(" const", "").strip()
    n = t.count("*")
    return t.replace("*", "").strip(), n


def parse(path: Path = TYPES_H):
    """(structs by name, enums by name: {value: label}) from a types.h of the analysis pipeline."""
    structs, enums = {}, {}
    cur = None
    enum_cur = None
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"^(struct|union) (\w+)(?: : (?:public )?([\w, ]+?))? \{ /\* Size=0x([0-9a-f]+) \*/", line)
        if m:
            cur = Struct(m.group(2), int(m.group(4), 16), m.group(1),
                         bases=[b.replace("public", "").strip() for b in (m.group(3) or "").split(",") if b.strip()])
            structs.setdefault(cur.name, cur)
            continue
        m = re.match(r"^enum (\w+)(?: : \w+)? \{", line)
        if m:
            enum_cur = enums.setdefault(m.group(1), {})
            continue
        if line.startswith("};"):
            cur = enum_cur = None
            continue
        if enum_cur is not None:
            m = re.match(r"\s+(\w+) = (-?0x[0-9a-f]+|-?\d+),", line)
            if m:
                enum_cur.setdefault(int(m.group(2), 0), m.group(1))
            continue
        if cur is not None:
            m = _FIELD.search(line)
            if m and "fields for" not in line:
                base, n = _clean(m.group(2))
                dims = tuple(int(x) for x in re.findall(r"\[(\d+)\]", m.group(4)))
                cur.fields.append(Field(int(m.group(1), 16), base, n, m.group(3), dims))
    return structs, enums


_CACHE = {}


def types():
    if "t" not in _CACHE:
        _CACHE["t"] = parse()
    return _CACHE["t"]


# Arrays behind pointers: (struct, field) -> count, or a function of the struct's memory dict.
COUNTS = {
    ("WeaponDef", "gunXModel"): 64, ("WeaponDef", "worldModel"): 64,
    ("WeaponDef", "camoMaterialTarget"): 63,
    ("WeaponDef", "szXAnimsRightHanded"): 124, ("WeaponDef", "szXAnimsLeftHanded"): 124,
    ("WeaponCompleteDef", "szXAnims"): 124,
    ("WeaponDef", "notetrackSoundMapKeys"): 24, ("WeaponDef", "notetrackSoundMapValues"): 24,
    ("WeaponDef", "notetrackRumbleMapKeys"): 16, ("WeaponDef", "notetrackRumbleMapValues"): 16,
    ("WeaponDef", "notetrackFXMapKeys"): 16, ("WeaponDef", "notetrackFXMapValues"): 16,
    ("WeaponDef", "notetrackFXMapTagValues"): 16,
    ("WeaponDef", "bounceSound"): 31, ("WeaponDef", "rollingSound"): 31,
    ("WeaponDef", "parallelBounce"): 31, ("WeaponDef", "perpendicularBounce"): 31,
    ("WeaponCompleteDef", "hideTags"): 32,
    ("WeaponCompleteDef", "scopes"): 6, ("WeaponCompleteDef", "underBarrels"): 3,
    ("WeaponCompleteDef", "others"): 8,
    ("WeaponCompleteDef", "animOverrides"): lambda d: d.get("numAnimOverrides", 0),
    ("WeaponCompleteDef", "soundOverrides"): lambda d: d.get("numSoundOverrides", 0),
    ("WeaponCompleteDef", "fxOverrides"): lambda d: d.get("numFXOverrides", 0),
    ("WeaponCompleteDef", "reloadOverrides"): lambda d: d.get("numReloadStateTimerOverrides", 0),
    ("WeaponCompleteDef", "notetrackOverrides"): lambda d: d.get("numNotetrackOverrides", 0),
    ("NoteTrackToSoundEntry", "notetrackSoundMapKeys"): 24,
    ("NoteTrackToSoundEntry", "notetrackSoundMapValues"): 24,
    ("WeaponAttachment", "worldModels"): 64, ("WeaponAttachment", "viewModels"): 64,
    ("WeaponAttachment", "reticleViewModels"): 16,
    ("VehicleDef", "turretWeapon"): 1,
    ("WeaponDef", "locationDamageMultipliers"): 22,      # HITLOC_NUM
}
# Fields types.h renders wrongly: `float* x[2][2]` that is two pointers to float pairs (vec2 arrays). Read raw; the
# asset's reader decodes them (weapon.read_weapon: the accuracy graph knots).
RAW_POINTER_PAIRS = {("WeaponCompleteDef", "accuracyGraphKnots"), ("WeaponDef", "originalAccuracyGraphKnots")}
# single structs behind a pointer (read through)
FOLLOW = {"AttAmmoGeneral", "AttSight", "AttReload", "AttAddOns", "AttGeneral", "AttAimAssist", "AttAmmunition",
          "AttDamage", "AttLocationDamage", "AttIdleSettings", "AttADSSettings", "AttScopeDriftSettings",
          "AttHipSpread", "AttGunKick", "AttViewKick", "AttADSOverlay", "AttUI", "AttRumbles", "AttProjectile",
          "WeaponDef"}


class Context:
    """What read_struct needs besides memory: the script string table (index -> text) and extra counts."""

    def __init__(self, script_string=None, counts=None, ref_names=None):
        self.script_string = script_string or (lambda v: v)
        self.ref_names = ref_names or {}     # field address -> name of a sound or effect resolved by name
        self.counts = dict(COUNTS)
        self.counts.update(counts or {})


def _cstr(mem, a):
    if not a:
        return None
    out = bytearray()
    while True:
        b = mem.read(a, 64)
        if not b:                        # past the end of memory
            return (out.decode("latin1") + "<?>") if out else None
        i = b.find(b"\0")
        if i >= 0:
            return (out + b[:i]).decode("latin1")
        out += b
        a += 64


def _q(mem, a):
    return struct.unpack("<Q", mem.read(a, 8))[0]


def _size_of(t: str):
    structs, enums = types()
    if t in PRIMITIVES:
        return struct.calcsize("<" + PRIMITIVES[t])
    if t in enums:
        return 4
    if t in structs:
        return structs[t].size
    return None


def _value(mem, a, f: Field, owner: str, ctx: Context, depth: int):
    structs, enums = types()
    t = f.type
    if f.pointers == 0:
        if t in PRIMITIVES:
            v = struct.unpack("<" + PRIMITIVES[t], mem.read(a, struct.calcsize("<" + PRIMITIVES[t])))[0]
            return ctx.script_string(v) if t == "scr_string_t" else v
        if t in enums:
            v = struct.unpack("<i", mem.read(a, 4))[0]
            return enums[t].get(v, v)
        if t in structs and depth < 6:
            return read_struct(mem, a, t, ctx, depth + 1)
        return None
    p = _q(mem, a)
    if not p:
        return ctx.ref_names.get(a) if f.pointers == 1 else None
    if f.pointers == 1:
        if t == "char":
            return _cstr(mem, p)
        if t in ASSET_NAME_AT:
            return _cstr(mem, _q(mem, p + ASSET_NAME_AT[t]))
        if t in FOLLOW and depth < 6:
            return read_struct(mem, p, t, ctx, depth + 1)
    count = ctx.counts.get((owner, f.name))
    if count is None:
        return f"<{t}{'*' * f.pointers} {p:#x}>"
    return count, p


def read_struct(mem, address: int, name: str, ctx: Context | None = None, depth: int = 0) -> dict:
    """Every field of the struct `name` at `address` (see the module's description)."""
    structs, _ = types()
    ctx = ctx or Context()
    s = structs[name]
    out = {}
    for base in s.bases:
        if base in structs:
            out.update(read_struct(mem, address, base, ctx, depth))
    pending = []
    for f in s.fields:
        a = address + f.offset
        if (name, f.name) in RAW_POINTER_PAIRS:
            out[f.name] = [_q(mem, a), _q(mem, a + 8)]
            continue
        if f.dims:
            n = 1
            for d in f.dims:
                n *= d
            size = 8 if f.pointers else _size_of(f.type)
            if size is None:
                continue
            flat = [_value(mem, a + size * i, Field(0, f.type, f.pointers, f.name), name, ctx, depth)
                    for i in range(n)]
            if f.type == "char" and not f.pointers:
                out[f.name] = bytes(x & 0xFF for x in flat).split(b"\0")[0].decode("latin1")
                continue
            out[f.name] = flat if len(f.dims) == 1 else [flat[i:i + f.dims[-1]] for i in range(0, n, f.dims[-1])]
            continue
        v = _value(mem, a, f, name, ctx, depth)
        if isinstance(v, tuple):
            pending.append((f, v))
        else:
            out[f.name] = v
    for f, (count, p) in pending:            # counts may come from fields read above
        n = count(out) if callable(count) else count
        elem = Field(0, f.type, f.pointers - 1, f.name)
        size = 8 if elem.pointers else _size_of(f.type)
        if size is None:
            out[f.name] = f"<{f.type} array {p:#x}>"
            continue
        out[f.name] = [_value(mem, p + size * i, elem, name, ctx, depth) for i in range(n)]
    return out


def enum_names(name: str) -> dict:
    return types()[1].get(name, {})


if __name__ == "__main__":
    import sys
    st, _ = types()
    s = st[sys.argv[1]]
    print(f"{s.kind} {s.name} (0x{s.size:x})")
    for f in s.fields:
        print(f"  +0x{f.offset:04x} {f.type}{'*' * f.pointers} {f.name}{''.join(f'[{d}]' for d in f.dims)}")
