// universal/com_stringtable.h: string tables (StringTable, asset type 0x2E, the game's CSV files) and localized
// strings (LocalizeEntry, 0x21). Layouts from the PS4 server PDB (analysis/iw6_ds_ps4/pdb/types.h); the Store
// build's loaders use the same (src/universal/com_stringtable_load_db.cpp).
#pragma once

#include <stddef.h>

struct StringTableCell
{
	const char *string;                  // +0x0
	int hash;                            // +0x8: StringTable_HashString of the string
};
static_assert(sizeof(StringTableCell) == 0x10, "StringTableCell");

struct StringTable
{
	const char *name;                    // +0x0
	int columnCount;                     // +0x8
	int rowCount;                        // +0xC
	StringTableCell *values;             // +0x10: rowCount rows of columnCount cells
};
static_assert(sizeof(StringTable) == 0x18, "StringTable");
static_assert(offsetof(StringTable, values) == 0x10, "StringTable::values");

struct LocalizeEntry
{
	const char *value;                   // +0x0: the text
	const char *name;                    // +0x8: its reference, e.g. MPUI_NONE
};
static_assert(sizeof(LocalizeEntry) == 0x10, "LocalizeEntry");

int StringTable_HashString(const char *string);
int StringTable_LookupRowNumForValue(const StringTable *table, int comparisonColumn, const char *value);

void Load_StringTable(bool atStreamStart);
void Load_StringTablePtr(bool atStreamStart);
void Load_LocalizeEntry(bool atStreamStart);
void Load_LocalizeEntryPtr(bool atStreamStart);
