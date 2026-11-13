// database/db_stringtable_load.cpp (Store build)

#include "database/db_local.h"

// Store 14037AF90 (PS4 PDB database/db_stringtable_load.cpp:29): a script string field holds an index into the
// zone's script string list; it becomes that entry's handle (Load_TempStringCustom put it there).
void Load_ScriptStringCustom(scr_string_t *var)
{
	*var = (scr_string_t)(unsigned int)(unsigned long long)varXAssetList->stringList.strings[(int)*var];
}
