# The remaining asset types

`tools/fastfile/misc_assets.py` has a loader for each of the ten asset types that had none. Each one follows the
Microsoft Store build's own loader, statement for statement. With these, every asset type that the Store build's
Load_XAssetHeader dispatches has a loader in tools/fastfile. `python3 tools/fastfile/misc_assets.py <zone.ff>` lists
these assets. Add `--out <folder>` to also write each Lua chunk to a file.

| Type | Name | Size | Store loader | What it holds | Checked against the game in |
|---|---|---|---|---|---|
| 0x06 | computeshader | 0x20 | 14034BF40 → 14034BE80, 14034EF40 | name, then a shader load definition (+0x10: the program, -1 for inline, aligned 4; else an offset), as the other shader stages are | code_post_gfx_mp (38), patch_code_post_gfx (31) |
| 0x17 | vehicle_track | 0x18 | 140359430 → 140359340, 140359720, 140359970, 140359520 | segments (0x48: name; sectors of 0x48, each with obstacles of 0xC; next and previous segment pointers, each either -1 with the segment following, or an offset) | satfarm (1) |
| 0x24 | snddriverglobals | 0x18 | 140356F90 → 140356EC0 | name and 0x5B0 bytes of settings | code_post_gfx_mp (1) |
| 0x2F | leaderboarddef | 0x28 | 140352470 → 140352360, 140352280 | name and columns (0x38 each: two strings, the shown name first) | code_post_gfx_mp (41) |
| 0x30 | structureddatadef | 0x18 | 140357ED0 → 140357E00, 140357BF0, 140357FC0, 1403580A0 | the save and stats layouts: definitions (0x58) of enums, structs, indexed and enumed arrays; enum entries and struct properties are script strings | code_post_gfx_mp (9) |
| 0x33 | addon_map_ents | 0x68 | 14034A370 → 14034A100 | an entity string, map triggers, a ClipInfo and sub-models, with clipmap.py's loaders | no zone examined has one |
| 0x35 | reverbpreset | 0x48 | 140355B20 → 140355A90 | name and plain values | code_post_gfx_mp (25), satfarm (6) |
| 0x36 | luafile | 0x18 | 140352B20 → 140352A50 | name, length and the chunk (aligned 16): compiled HavokScript, starting with `\x1bLuaQ` | patch_code_post_gfx (84: `ui/lui/*.lua`), development_mp (1) |
| 0x3B | equipsndtable | 0x58 | 14034CB70 → 14034C670, 14034C460, 14034C3B0, 14034C5C0 | cloth and weapon-rattle types; rattle chances; movement, accent and mantle sounds, all named sound aliases looked up as weapons do | common (1: `soundaliases/equipment_snd.def`) |
| 0x3C | vectorfield | 0x50 | 140358870 → 140358770 | name and x × y × z cells of 0x10 (counts at +0x34, +0x38, +0x3C) | no zone examined has one |

Pointers in these structures come in two forms:

- "Any non-null value": the data follows. Buffers, column and sector arrays, and the equipment table's arrays use
  this form.
- "-1": the data follows; any other value is an offset to data loaded earlier. Shader programs, vector field cells,
  vehicle track segments and the ClipInfos of add-on entities use this form.

The game finds the equipment table's sounds by name (Load_SndAliasCustom, 1405367A0).

## C++

`src/database/db_misc_load_db.cpp` reconstructs every loader in this file: 31 functions, each with its Load_*Ptr.
Each one matches the exe in `tests/differential/test_misc_load.py`, and mutation checks confirm the tests catch
changes. Details where these loaders differ from their neighbours:

- Load_VectorFieldPtr aligns the header to 16.
- Load_GfxComputeShaderLoadDef zero-extends the program size, where the material shader loaders sign-extend it.
- Counts passed to the array loaders (segments, branches, structured data defs, the equipment arrays) are
  zero-extended. Counts the loaders read for themselves (enum entries, struct properties, leaderboard columns,
  entity characters) are sign-extended.
- Load_VehicleTrackSegmentArray, Load_EquipmentSoundTable and Load_AddonMapEnts inline their element loaders
  (segments, mantle sound sets, sub-models). Load_StructuredDataDefArray inlines the enum and struct arrays but
  calls Load_StructuredDataEnum and Load_StructuredDataStruct for each element.

## How it was checked

`tests/fastfile/zone_check.py <zone.ff> --full` compares each zone below with the game, loaded in the emulator, and
each one matches:

- development_mp, code_post_gfx_mp and common.
- patch_code_post_gfx (unsigned).
- satfarm. This is a 387 MB single-player level. The multiplayer Store build's loaders read it completely.

`tests/fastfile/test_misc_assets.py` covers the Lua, leaderboard, vector field and vehicle track loaders on
hand-made streams. With IW6_FASTFILES set, it also checks the interface Lua and the leaderboards of real zones.

These zones were surveyed and have none of the new types except the ones in the table:

- The 102 small zones (under 400 KB) of the dump.
- Seven single-player levels: satfarm, nml, loki, flood, homecoming, skyway and carrier. Each has a vehicle track,
  and loki has a Lua file.
- mp_ca_behemoth and mp_fahrenheit.

## Not established

| What | Status |
|---|---|
| addon_map_ents and vectorfield | transcribed but not exercised against the game: no zone examined carries one |
| The structured data and equipment table field names beyond those above | read as layouts; no reader yet |
| Decompiling the HavokScript chunks | out of scope; the chunks are extracted as they are |
