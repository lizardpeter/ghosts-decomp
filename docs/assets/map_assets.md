# A map's other assets: glass, effect tables, entities, scriptables, animation classes

The smaller asset types a map zone carries besides its world (docs/assets/world.md) and collision
(docs/assets/collision.md), as the Microsoft Store build loads them. Whole real zones with every loader are equal to
the game (docs/fastfiles.md, section 12).

| Type | Name | Header | Python | C++ |
|---|---|---|---|---|
| 0x15 | glass_map (GlassWorld) | 0x10 | mapfx.py | src/effectscore/fx_world_load_db.cpp |
| 0x18 | map_ents (MapEnts) | 0x100 | clipmap.py | src/qcommon/cm_load_db.cpp |
| 0x19 | fx_map (FxWorld) | 0xB0 | mapfx.py | src/effectscore/fx_world_load_db.cpp |
| 0x20 | animclass (AnimationClass) | 0x58 | xanim.py | src/xanim/xanim_load_db.cpp |
| 0x26 | impactfx (FxImpactTable) | 0x10 | mapfx.py | src/effectscore/fx_world_load_db.cpp |
| 0x27 | surfacefx (SurfaceFxTable) | 0x10 | mapfx.py | src/effectscore/fx_world_load_db.cpp |
| 0x37 | scriptable (ScriptableDef) | 0x40 | clipmap.py | not reconstructed |

Every C++ loader listed matches the exe in `tests/differential/test_misc_asset_load.py` (glass, effect tables,
animation classes) or the collision tests; mutations of each are caught.

## GlassWorld (0x15): the server's glass state

Load_GlassWorld 140351FE0: name, then G_GlassData (+8; any non-null value is inline: Load_G_GlassData 14034EAA0,
0x90 bytes): glassPieces (+0, pieceCount +8, × 0xC: damageTaken, collapseTime, lastStateChangeTime, impact
direction and position) and glassNames (+0x18, glassNameCount +0x10, × 0x18, Load_G_GlassName 14034EBA0: nameStr,
the script string name, pieceCount and pieceIndices (u16, aligned 2)).

## FxWorld (0x19): the client's breakable glass system

Load_FxWorld 14034E910: name, then the FxGlassSystem inside (+8, 0xA8 bytes, Load_FxGlassSystem 14034DE80):

- **defs** (+0x30, defCount +8): FxGlassDef, 0x78 bytes in the Store build (the servers' is 0x70; the loader steps by
  0x78): halfThickness, texture vectors, colour, material and shattered material (+0x18, +0x20), physics preset
  (+0x28), break, shatter, small shatter and crack decal effects (+0x30..+0x48), damaged, destroyed and quiet destroyed
  sounds (+0x50..+0x60), numCrackRings, isOpaque. Load_FxGlassDef 14034DD30.
- **Per-piece state in the runtime block** (allocated and zero-filled, not read from the zone): piecePlaces and
  pieceStates (pieceLimit × 0x20 each), pieceDynamics (pieceLimit × 0x30), geoData (geoDataLimit × 4), isInUse
  (pieceWordCount × 4), cellBits (cellCount × pieceWordCount × 4), visData (pieceLimit rounded up to 16, aligned 16),
  linkOrg (pieceLimit × 12), halfThickness (pieceLimit rounded up to 4 floats, aligned 16).
- **The initial pieces**, in the zone: lightingHandles (initPieceCount × u16), initPieceStates (initPieceCount ×
  0x38) and initGeoData (initGeoDataCount × 4).

## FxImpactTable (0x26) and SurfaceFxTable (0x27)

A name and a fixed table (any non-null value is inline). Impact: 15 entries (surface types) of 31 non-flesh and 7
flesh effects (0x130 each; Load_FxImpactTable 14034E380). Surface: 6 entries of 31 effects (0xF8 each;
Load_SurfaceFxTable 140358180). Each effect is a handle (Load_FxEffectDefHandleArray 14034D210, the asset pointer
rule per element; docs/assets/effects.md).

## AnimationClass (0x20)

Load_AnimationClass 14034A550 (0x58): className; the state machine (+8, Load_AnimationStateMachine 14034ABE0: a
name, stateCount AnimationStates (0x28 each, Load_AnimationStateArray 14034A970: name, notify, blend time, flags, an
aim set, entryCount AnimationEntry {alias, animName} and as many 8-byte animation indices in the runtime block) and
aimSetCount aim sets (0x70 each, Load_AnimationAimSet 14034A460: name, root name, eight animation names)); animTree
(+0x14, a script string); the scriptable (+0x18); soundNotes, soundNames, soundOptions (+0x28..+0x38, soundCount
+0x20); effectNotes, effectDefs (aligned 8) and effectTags (+0x40..+0x50, effectCount +0x22). Pointers are inline
when -1, else offsets. The layouts are the servers' PDBs'.

## MapEnts (0x18) and ScriptableDef (0x37)

Their loaders were written with the collision map (docs/assets/collision.md: map entities, triggers, client
triggers, scriptable map entities); they are now also registered as the asset types of their own, so a zone's
top-level map_ents and scriptable assets load.

## Not established

| What | Status |
|---|---|
| FxGlassDef's 8 Store-only bytes (+0x70) | not read by the loader; meaning unknown |
| How the glass system and effect tables are used at run time | not reconstructed |
| ScriptableDef in C++ | not reconstructed |
