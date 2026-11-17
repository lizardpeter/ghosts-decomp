# String tables and localized text (StringTable, LocalizeEntry)

The game's CSV files and the text it shows, as the Microsoft Store build loads them. `tools/fastfile/strings.py`
loads and reads them and writes them out (every table as CSV, the localized text as JSON);
`src/universal/com_stringtable_load_db.cpp` and `src/universal/com_stringtable_obj.cpp` reconstruct the loaders and
the lookups in C++, each matching the exe in `tests/differential/test_stringtable_load.py`.

| Type | Name | Size | Store loader |
|---|---|---|---|
| 0x2E | stringtable | 0x18 | Load_StringTablePtr 140357B00 → Load_StringTable 140357980 |
| 0x21 | localize | 0x10 | Load_LocalizeEntryPtr 1403527E0 → Load_LocalizeEntry 1403526F0 |

**StringTable (0x18):** name (+0, the file's path, `mp/camotable.csv`), columnCount (+8), rowCount (+0xC), values
(+0x10): rowCount rows of columnCount cells, row-major (cell `row * columnCount + column`), each 0x10 bytes: the
string (+0) and its hash (+8). The loader loads the cells whenever values is set (no test for -1; the count is an
int product), then each cell's string as an XString; the hash stays as stored.

The hash is StringTable_HashString (140536D10): `h = h * 31 + tolower(c)` over the string's bytes as signed chars,
in 32-bit arithmetic (a byte from 0x80 adds a negative value; tolower leaves it). Every cell of the 227 tables read
has its stored hash equal to that. The lookups:

- StringTable_GetColumnValueForRow (140536B00): the cell's string, or "" outside the table or for a null string.
- StringTable_LookupRowNumForValue (140536C50): the last row whose cell in the column has the value's hash and is
  equal to it ignoring case (I_stricmp), or -1; a column past the table is Com_Error(ERR_DROP, "Unable to compare
  against column number %i - there are only %i columns") and the search then reads past the row.

**LocalizeEntry (0x10):** the text (+0) and its reference (+8, `MPUI_NONE`, `CGAME_HEAD_SHOT`), two XStrings.

## Where they are

| Zone | String tables | Localized strings |
|---|---|---|
| english/eng_code_post_gfx_mp.ff | 139: the multiplayer tables (attachments, camos, classes, challenges, ranks, killstreaks, perks, unlocks, the in-game store), the sound tables | none |
| english/eng_common_mp.ff | 6 | 132 (CGAME_ messages and the like) |
| english/eng_common_alien_mp.ff | 14: Extinction (attachments, presets, perks, ranks, spawns, collectibles) | none |
| english/eng_patch_code_post_gfx_mp.ff | 68: the patched versions of the multiplayer tables | 8104: the menus', maps', weapons' and camos' names and descriptions (`LUA_MENU_CAMO_SNOW` "Snow", `PRESENCE_MP_ALIEN_TOWN` "Point of Contact", `WEAPON_HONEYBADGER` "Honey Badger") |
| english/eng_ui_mp.ff | none | 85 |

The patch's mp/camotable.csv has 47 rows (the DLC and seasonal camos added), still six columns; see records/bugs.tsv
B0084 for the code that reads a seventh.

## How it was checked

- **Whole zones.** english/eng_common_mp.ff (4427 assets: sounds, 6 tables, 132 localized strings),
  english/eng_patch_code_post_gfx_mp.ff (8174 assets: 68 tables, 8104 localized strings) and
  english/eng_common_alien_mp.ff (23 assets) walked by `tools/fastfile/loaders.py` equal the game's
  (`tests/fastfile/zone_check.py --full`).
- **Single assets.** english/eng_code_post_gfx_mp.ff stops at its fonts (type 0x1D, no loader yet), so its tables
  were checked one at a time: Load_StringTablePtr calls 0, 50, 100 and 138 equal the game's.
- **C++.** The six functions above match the exe on random structures and strings; nine mutations (the hash
  multiplier, the string step, the alignment, the cell count, the field order, the insert slot, the search start,
  the hash test, the comparison) each fail a test. The CRT's tolower is an import the emulator doesn't have; the test
  plays it as the C locale has it.

## Not established

| What | Status |
|---|---|
| Fonts (0x1D) and the rest of eng_code_post_gfx_mp.ff | no loader yet |
