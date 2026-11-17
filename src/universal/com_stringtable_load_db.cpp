// universal/com_stringtable_load_db.cpp (Store build): the zone loaders of string tables (StringTable, asset type
// 0x2E) and localized strings (LocalizeEntry, 0x21). Generated loader code (the servers' PDB places it in
// gfx_d3d/r_material_load_db.h), tagged with Store addresses. tools/fastfile/strings.py is the same in Python, checked
// against the game on real zones (docs/assets/strings.md); tests/differential/test_stringtable_load.py checks this
// file against the exe.

#include "universal/com_stringtable.h"
#include "database/db_stream_api.h"

void Load_StringTableAsset(StringTable **table);          // Store 140373870
void Load_LocalizeEntryAsset(LocalizeEntry **entry);      // Store 140372600

extern StringTable **varStringTablePtr;                   // Store 144425B50
extern StringTable *varStringTable;                       // Store 144425B48
extern StringTableCell *varStringTableCell;               // Store 144425B40
extern LocalizeEntry **varLocalizeEntryPtr;               // Store 144425A48
extern LocalizeEntry *varLocalizeEntry;                   // Store 144425A40

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

static inline void LoadXString(const char **field)
{
	varXString = field;
	Load_Stream(false, varXString, 8);
	if (*varXString)
	{
		if ((unsigned long long)*varXString == DB_PTR_FOLLOWING)
		{
			*varXString = (const char *)g_streamPos;
			varConstChar = (const char *)g_streamPos;
			Load_XStringCustom(varXString);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varXString);
		}
	}
}

// Store 140357980. The cells follow whenever values is set (no test for -1).
void Load_StringTable(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStringTable, sizeof(StringTable));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varStringTable->name);
	if (varStringTable->values)
	{
		ALIGN_POS(4);
		varStringTable->values = (StringTableCell *)g_streamPos;
		varStringTableCell = (StringTableCell *)g_streamPos;
		long long count = varStringTable->rowCount * varStringTable->columnCount;
		Load_Stream(true, g_streamPos, count * sizeof(StringTableCell));
		StringTableCell *cell = varStringTableCell;
		for (; count; count--)
		{
			varStringTableCell = cell;
			Load_Stream(false, cell, sizeof(StringTableCell));
			LoadXString(&varStringTableCell->string);
			cell++;
		}
	}
	DB_PopStreamPos();
}

// Store 140357B00
void Load_StringTablePtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStringTablePtr, sizeof(StringTable *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	StringTable **ptr = varStringTablePtr;
	unsigned long long value = (unsigned long long)*varStringTablePtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varStringTablePtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varStringTablePtr = (StringTable *)g_streamPos;
		varStringTable = (StringTable *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_StringTable(true);
		Load_StringTableAsset(ptr);
		if (inserted)
			*(StringTable **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// Store 1403526F0
void Load_LocalizeEntry(bool atStreamStart)
{
	Load_Stream(atStreamStart, varLocalizeEntry, sizeof(LocalizeEntry));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varLocalizeEntry->value);
	LoadXString(&varLocalizeEntry->name);
	DB_PopStreamPos();
}

// Store 1403527E0
void Load_LocalizeEntryPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varLocalizeEntryPtr, sizeof(LocalizeEntry *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	LocalizeEntry **ptr = varLocalizeEntryPtr;
	unsigned long long value = (unsigned long long)*varLocalizeEntryPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varLocalizeEntryPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varLocalizeEntryPtr = (LocalizeEntry *)g_streamPos;
		varLocalizeEntry = (LocalizeEntry *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_LocalizeEntry(true);
		Load_LocalizeEntryAsset(ptr);
		if (inserted)
			*(LocalizeEntry **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
