# Collision and map entities (clipMap_t, col_map_mp)

The collision map (asset type 0x13, `col_map_mp`) holds everything a map needs besides its rendering: brush and
terrain collision, the collision tree, brush models (doors, movers), static model placements, and, through it, the
map entities (MapEnts: the entity text, triggers, spawn and spline records), stages, dynamic entities and
scriptables. `tools/fastfile/clipmap.py` loads it from the zone the way the game does and reads it;
`tests/fastfile/clipmap_check.py` checks the loader against the game's own.

## 1. How it was checked

The Store build's own loader runs in the emulator (`tests/fastfile/store_emu.py`) on a whole map zone. At
`Load_clipMap_ptr` (14035FB10) the stream state is handed to the Python loader; when the game's call returns, the
zone position, every block position, every byte of block memory and the asset pool must be the same (the same
comparison as the GfxWorld's, `world_check.py`). Equal on Dynasty (mp_conflict: 5.6 MB of zone data), Point of
Contact (mp_alien_town) and mp_alien_armory.

One allowance: sound aliases of scriptable events are found by name (`DB_FindXAssetHeader`). The emulator's link
stand-in registers no names, so there the game always gets a default entry; the reader resolves aliases the zone
itself has linked (`Stream.find_asset`) and leaves the others 0, and the check accepts either for those fields.

## 2. clipMap_t (0x280 bytes; Load_clipMap_t 14035FC00)

| offset | field | data |
|---|---|---|
| +0x00 | name | XString |
| +0x08 | isInUse | set to 1 by Load_ClipMapAsset (1403717F0) before linking |
| +0x10 | info | ClipInfo (0x80, below) |
| +0x90 | pInfo | a second ClipInfo: inline (aligned 4) or an alias; after loading it inline the game points the field at a global ClipInfo (0x1469C8A10) |
| +0x98 / +0xA0 | numStaticModels / staticModelList | cStaticModel_s × 0x50: XModel (pointer rule), origin, invScaledAxis[3][3], absBounds (mid, half) |
| +0xA8 / +0xB0 | numNodes / nodes | cNode_t × 0x10: plane (0x14, inline or offset), children |
| +0xB8 / +0xC0 | numLeafs / leafs | cLeaf_t × 0x28 |
| +0xC8 / +0xD0 | vertCount / verts | float[3] |
| +0xD8 / +0xE0 | triCount / triIndices | u16 × 3 per triangle, aligned 2 |
| +0xE8 | triEdgeIsWalkable | ((triCount × 3 + 31) >> 3) & ~3 bytes, unaligned |
| +0xF0 / +0xF8 | borderCount / borders | CollisionBorder × 0x1C |
| +0x100 / +0x108 | partitionCount / partitions | CollisionPartition × 0x10: borders (+8: 0x1C, inline or offset) |
| +0x110 / +0x118 | aabbTreeCount / aabbTrees | CollisionAabbTree × 0x20, aligned 16 |
| +0x120 / +0x128 | numSubModels / cmodels | cmodel_t × 0x50: bounds, radius, info (+0x20: ClipInfo, inline or alias), leaf |
| +0x130 | mapEnts | MapEnts (asset pointer rule; linked as type 0x18) |
| +0x138 / +0x140 | stages / stageCount (u8) | Stage × 0x18: name, origin, triggerIndex, sunPrimaryLightIndex |
| +0x148 | stageTrigger | MapTriggers (0x30) |
| +0x178 / +0x180 | PC only | u16 count, × 0x1C |
| +0x188, +0x18A | dynEntCount[2] | u16 |
| +0x190, +0x198 | dynEntDefList[2] | DynEntityDef × 0x78: xModel (+0x20), destroyFx (+0x30), physPreset (+0x38), 0x2C (+0x40) and 0x1C (+0x48) inline blocks |
| +0x1A0..+0x1C8 | dynEntPoseList, dynEntClientList, dynEntCollList [2] | runtime block: × 0x20, 0x28, 0x14 |
| +0x1D0 / +0x1D8 | count / script strings | u32 each |
| +0x1E0 | ScriptableMapEnts (0x30) | instances (count +4, × 0x78 at +0x10), animation entries (count +0x18, × 0x10 at +0x20) |

**ClipInfo** (0x80; Load_ClipInfo 14034B360): planes (count +0, × 0x14 at +8), materials (+0x10/+0x18: ClipMaterial
× 0x10: name, surfaceFlags, contents), brushsides (+0x20/+0x28: × 0x10: plane, materialNum, firstAdjacentSideOffset,
edgeCount), brushEdges (+0x30/+0x38, bytes), leafbrushNodes (+0x40/+0x48, × 0x18; a node with leafBrushCount (+2)
> 0 has its brushes at +8), leafbrushes (+0x50/+0x58, u16), brushes (u16 count +0x60, × 0x30 at +0x68, aligned 128:
cbrush_t: numsides, glassPieceIndex, sides (+8), baseAdjacentSide (+0x10), axialMaterialNum, …), brushBounds (+0x70,
× 0x18, aligned 128: mid, half), brushContents (+0x78, × 4). Most pointers are inline or an offset into data loaded
before (DB_ConvertOffsetToPointer).

A **brush** is its bounds (brushBounds) cut by the planes of its non-axial sides: `clipmap.brush_faces` turns one
into convex polygons. Contents: Dynasty's 8009 brushes are mostly 0x8000001 (5011), 0x2080 (1059) and 0x8031640.

## 3. MapEnts (0x100; Load_MapEnts 140352C10)

| offset | field |
|---|---|
| +0x00 | name |
| +0x08 / +0x10 | entityString / numEntityChars (unaligned) |
| +0x18 | trigger: MapTriggers (0x30: models × 8, hulls × 0x20, slabs × 0x14, u32 counts) |
| +0x48 | clientTrigger: ClientTriggers (0x88: a MapTriggers, then per-trigger arrays) |
| +0xD0 | u16 count, × 0x1C (14034B030) |
| +0xE0 | spawn records: u16 count, SpawnPointEntityRecord × 0x28 (index, name, target, script_noteworthy as script strings, origin, angles) |
| +0xF0 | spline records: u16 count, × 0x10 lists (u16 count, × 0x48 points: 0x40, 0x30 and 0x24-byte parts) |

**The entity text.** PC zones write each key as its canonical string id: `97 "worldspawn"`; a key without an id as
0 and the key: `0 "aomindist" "16"`. Ids below 0x95A1 are built-in strings (`SL_GetCanonicalString` numbers strings
added at run time from 0x95A1 up). The game keeps no text for most built-in ids; the names `clipmap.CANONICAL_NAMES`
gives (119, among them classname 97, origin 430, angles 47, model 392, targetname 642, target 640, spawnflags 542,
script_noteworthy 506) come from the Xbox One server's data: a pointer to a `scr_const` member next to its id, as in
the entity field tables (ent_field_t). Other keys read as `#<id>`.

Dynasty: 1482 entities (1032 path nodes, 151 script structs, 64 + 64 traversal nodes, 52 script origins, 39 brush
models, triggers, the intermission camera …) and 189 spawn records (mp_tdm_spawn_allies_start, …).

## 4. Scriptables

A scriptable instance (0x78; 140356770) has its ScriptableDef (asset pointer rule, linked as type 0x37), a byte
array sized by the def (+0x3A), a script string (+0x28), and runtime data (a model, × def+0x35 × 4, def+0x39 bytes).
ScriptableDef (0x40; 140355FE0): name, model (+8), two names, parts (+0x20, count byte +0x35, × 0x10: states (count
+0xC, × 0x18: two script strings, events (count +0x10, × 0x28))), notetracks (+0x28, count +0x38, × 0x18). Event
types (1403564A0): 0 model, 1 effect and a script string, 2 sound (by name, Load_SndAliasCustom 1405367A0), 3
animation name, 6 physics model, 7 light settings name (+0x10), 9 shake name; 4, 5, 8 and 10 carry nothing to load.
Dynasty has 159 instances.

## 5. Not done

- Effects referenced from collision (dynamic entity destroy effects, scriptable events) are loaded by alias only; an
  inline FxEffectDef raises (none on the three maps).
- Load_ClipMapAsset's post-link fix (140371370) swaps the x and y extents of one brush model with particular bounds;
  it counts brush models from the global ClipInfo, which is 0 while a zone loads in the emulator, and is not
  modelled.
- The collision tree (nodes, leafs, partitions, AABB trees) is loaded but not read; the readers give brushes and
  triangles directly.
- C reconstructions of these loaders.
