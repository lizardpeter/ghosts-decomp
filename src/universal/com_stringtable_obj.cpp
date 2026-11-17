// universal/com_stringtable_obj.cpp (Store build): lookups in string tables. tools/fastfile/strings.py is the same in
// Python (read_string_table, StringTable.find_row).

#include "universal/com_stringtable.h"
#include "qcommon/qcommon.h"

extern "C" int tolower(int c);

// Store 140536D10. The bytes are signed chars: one from 0x80 adds a negative value (tolower leaves it).
int StringTable_HashString(const char *string)
{
	unsigned int hash = 0;
	int c = tolower(*string);
	while (c)
	{
		string++;
		hash = hash * 31 + (unsigned int)c;
		c = tolower(*string);
	}
	return (int)hash;
}

// Store 140536C50: the last row whose cell in comparisonColumn is `value` (same hash, then I_stricmp), or -1.
int StringTable_LookupRowNumForValue(const StringTable *table, int comparisonColumn, const char *value)
{
	int hash = StringTable_HashString(value);
	if (!table->columnCount)
		return -1;
	if (comparisonColumn >= table->columnCount)
		Com_Error(ERR_DROP, "Unable to compare against column number %i - there are only %i columns", comparisonColumn,
		          table->columnCount);
	for (int row = table->rowCount - 1; row >= 0; row--)
	{
		const StringTableCell *cell = &table->values[row * table->columnCount + comparisonColumn];
		if (cell->hash == hash && cell->string && !I_stricmp(value, cell->string))
			return row;
	}
	return -1;
}
