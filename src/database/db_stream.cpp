// database/db_stream.cpp (Store build)
//
// The zone stream's block positions: seven blocks (XFILE_BLOCK_*), the position in the current one (g_streamPos),
// the saved positions of the others (g_streamPosArray) and a stack of pushes. Names and layout: the PS4/Xbox One
// server PDBs (database/db_stream.cpp); the Store build's code is the same. docs/fastfiles.md describes the rules.

#include <iw6_static.h>

#include "database/db_local.h"

#define IW6_SOURCE "database/db_stream.cpp"

IW6_STATIC StreamPosInfo g_streamPosStack[64] IW6_AT("", "g_streamPosStack");
IW6_STATIC unsigned int g_streamPosStackIndex IW6_AT("", "g_streamPosStackIndex");

// Empty in the Store build (and folded with empty destructors in the servers); DB_PopStreamPos calls it when it
// leaves the temp block. Name unknown.
void sub_140374950();

// Store 1403746E0 (PS4 PDB database/db_stream.cpp:30)
void DB_InitStreams(XZoneMemory *mem)
{
	g_streamZoneMem = mem;
	g_streamPos = mem->blocks[XFILE_BLOCK_TEMP].data;
	g_streamPosIndex = XFILE_BLOCK_TEMP;
	g_streamPosStackIndex = 0;
	for (int i = 0; i < MAX_XFILE_COUNT; ++i)
		g_streamPosArray[i] = mem->blocks[i].data;
}

// Store 1403748D0 (PS4 PDB database/db_stream.cpp:60)
void DB_PushStreamPos(unsigned int index)
{
	unsigned int top = g_streamPosStackIndex++;
	g_streamPosStack[top].index = g_streamPosIndex;
	if (index != g_streamPosIndex)
	{
		g_streamPosArray[g_streamPosIndex] = g_streamPos;
		g_streamPos = g_streamPosArray[index];
		g_streamPosIndex = index;
	}
	g_streamPosStack[top].pos = g_streamPos;
}

// Store 140374850 (PS4 PDB database/db_stream.cpp:75)
void DB_PopStreamPos()
{
	--g_streamPosStackIndex;
	if (g_streamPosIndex == XFILE_BLOCK_TEMP)
	{
		// temp memory is reused: back to where the push found it
		g_streamPos = g_streamPosStack[g_streamPosStackIndex].pos;
		sub_140374950();
	}
	unsigned int index = g_streamPosStack[g_streamPosStackIndex].index;
	if (index != g_streamPosIndex)
	{
		g_streamPosArray[g_streamPosIndex] = g_streamPos;
		g_streamPos = g_streamPosArray[index];
		g_streamPosIndex = index;
	}
}

// Store 140374750 (PS4 PDB database/db_stream.cpp:118): an 8-byte, 8-aligned slot in the virtual block, for an
// alias to the asset being loaded. The Store build inlines DB_PushStreamPos and DB_PopStreamPos here (the pop's
// temp-block branch can't be taken: the slot's push is always to the virtual block).
unsigned char *DB_InsertPointer()
{
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	unsigned char *pos = (unsigned char *)(((unsigned long long)g_streamPos + 7) & ~7ull);
	g_streamPos = pos + 8;
	DB_PopStreamPos();
	return pos;
}
