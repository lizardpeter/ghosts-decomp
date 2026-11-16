# Weapons, attachments, tracers and vehicles

What the Microsoft Store build loads for a weapon (WeaponCompleteDef, asset type 0x23) and the assets around it:
WeaponAttachment (0x22), TracerDef (0x31) and VehicleDef (0x32). `tools/fastfile/weapon.py` loads them, statement
for statement after the Store loaders; `src/bgame/bg_tracer_load_db.cpp` reconstructs the tracer loaders in C++.

## 1. How it was checked

- **Whole zones.** With every loader registered (`tools/fastfile/loaders.py`), the reader walks common_alien_mp
  (51 weapons, 2 vehicles), mp_conflict and mp_alien_town (44 weapons, 63 attachments, 2 vehicles) end to end, and
  every block and the asset pool equal the game's (`tests/fastfile/zone_check.py --full`; docs/fastfiles.md).
- **Single assets.** `zone_check.py` at Load_WeaponCompleteDefPtr calls 0, 1 and 20 and Load_VehicleDefPtr call 0 of
  common_alien_mp, and Load_WeaponAttachmentPtr call 0 of mp_alien_town: equal.
- **C++.** The tracer loaders (Load_TracerDef 140358530, Load_TracerDefPtr 1403585D0) match the exe in
  `tests/differential/test_misc_asset_load.py`. The weapon, attachment and vehicle loaders are not reconstructed in
  C++ yet (their full layouts, 0xA98 bytes for WeaponDef, are the remaining work).

## 2. The loaders

The layouts are the servers' PDBs' (iw6_ds_ps4), and every offset the Store loaders touch agrees with them. Offsets
below are bytes.

**WeaponCompleteDef (0x128)**, Load_WeaponCompleteDef 14035A460, in the virtual block:

| Off | Field | How |
|---|---|---|
| +0x00 | szInternalName | XString |
| +0x08 | weapDef | inline (aligned 4) when -1: Load_WeaponDef; else an offset |
| +0x10 | szDisplayName | XString |
| +0x18 | hideTags | inline: 32 script strings |
| +0x20, +0x28, +0x30 | scopes (6), underBarrels (3), others (8) | inline (aligned 8): attachment pointer arrays (Load_WeaponAttachmentPtrArray 14035A330) |
| +0x38 | szXAnims | inline (aligned 8): 0x7C animation pointers (Load_XAnimPartsPtrArray 14035D4C0) |
| +0x48 | animOverrides | numAnimOverrides (+0x40) × 0x28: two animations (+8, +0x10) |
| +0x58 | soundOverrides | numSoundOverrides (+0x50) × 0x20: two sounds |
| +0x68 | fxOverrides | numFXOverrides (+0x60) × 0x20: two effects |
| +0x78 | reloadOverrides | numReloadStateTimerOverrides (+0x70) × 0x10, plain |
| +0x88 | notetrackOverrides | any non-null value: numNotetrackOverrides (+0x80) × 0x18, two 24-string arrays each |
| +0xC0 | szAltWeaponName | XString |
| +0xD8, +0xE0 | killIcon, dpadIcon | materials |
| +0x108, +0x110 | two curves | u16 counts at +0x104, +0x106, × 8 bytes |
| +0x120 | a name | XString |

**WeaponDef (0xA98)**, Load_WeaponDef 14035AD90, inside the complete def's block: name, gun and hand models (an
XModelPtrArray of 0x40 at +8, models at +0x10..+0x20, another array of 0x40 at +0x348 and models +0x350..+0x368, one
more at +0x718 and +0xA90), materials (+0x28, +0x30, an array of 0x3F at +0x38, +0x288, +0x290, +0x370, +0x380,
+0x390, four in the ADS overlay block at +0x5B0), animation arrays of 0x7C (+0x40, +0x48), script string arrays
(+0x58, +0x60: 24; +0x68..+0x78 and +0x88: 16), effect arrays and effects (+0x80: 16; +0xB8..+0xC8, +0x260..+0x280,
+0x728, +0x730, +0x770, +0x778, +0x798, +0x978), 48 sounds (+0xD0..+0x248), two arrays of 31 sounds (+0x250,
+0x258), more sounds (+0x738, +0x740, +0x7A0, +0x970, +0x998, +0x9A0..+0x9D8 in two inline groups of four, +0x9E0,
+0x9E8), a physics collision map (+0x698), a tracer (+0x940), two script strings (+0xA24, +0xA8C), names (XStrings at
+0x50, +0x3A8, +0x3B8, +0x3D0, +0x710, +0x858, +0x860, +0x8C8, +0x8D0, +0x8F8, +0x930, +0x938, +0x980) and plain
arrays (+0x760, +0x768: 0x7C bytes; +0x868, +0x870: the complete def's two curve counts × 8; +0x928: 0x58).
weapon.load_weapon_def lists every one in the loader's order.

**WeaponAttachment (0x118)**, Load_WeaponAttachment 140359A30: internal and display names, three model arrays
(+0x20, +0x28: 0x40; +0x30: 0x10), and one pointer per settings block (+0x38..+0xD8), each inline whenever non-null:
ammo (0x20, with a tracer at +0x10), sight (9 bytes), reload (2, aligned 2), add-ons (3, unaligned), general (0x28,
two materials), aim assist (0xC), ammunition (0x18), damage (0x1C), location damage (0x4C), idle settings (0x18),
ADS settings (0x40, twice), scope drift (0x18, twice), hip spread (0x30), gun kick (0x58), view kick (0x30), ADS
overlay (0x40, four materials), UI (0x20, two materials), rumbles (0x10, two names: Load_AttRumbles 14034AEA0) and
projectile (0x90: model, effects, sounds: Load_AttProjectile 14034AD20).

**TracerDef (0x78)**, Load_TracerDef 140358530: name, material.

**VehicleDef (0x610)**, Load_VehicleDef 140358960: names, the physics block inside (+0xB8, Load_VehiclePhysDef
140359240: two names and a physics preset), effects, a turret weapon (+0x368, a WeaponCompleteDef pointer), sounds
(+0x398 on), script strings (+0x3BC: four; +0x42C, +0x454), materials and 31 more sounds (+0x4F8).

Sound fields are names resolved by Load_SndAliasCustom (1405367A0); effects, materials, models, animations, physics
assets and tracers use the asset pointer rule (an inline asset is loaded and linked; an offset is an alias).

## 3. Not established

| What | Status |
|---|---|
| C++ for WeaponCompleteDef, WeaponDef, WeaponAttachment and VehicleDef | not reconstructed |
| A reader for the weapon fields (stats, timings, kick, spread) | the loader only; values are where the servers' layout puts them |
