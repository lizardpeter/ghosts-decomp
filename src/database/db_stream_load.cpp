// database/db_stream_load.cpp (Store build)
//
// Reading the zone stream into block memory, and turning stored offsets back into pointers. Names: the PS4/Xbox
// One server PDBs (database/db_stream_load.cpp); docs/fastfiles.md has the rules.

#include <iw6_static.h>

#include "database/db_local.h"

#define IW6_SOURCE "database/db_stream_load.cpp"

extern "C" void *memset(void *dst, int c, unsigned long long n);

// Store 1403749E0 (PS4 PDB database/db_stream_load.cpp:24): at the start of an object, `size` bytes of the stream
// go to ptr (the current position) and the position moves on. The runtime block is zero-filled, never read.
void Load_Stream(bool atStreamStart, void *ptr, unsigned long long size)
{
	if (!atStreamStart || !size)
		return;
	if (g_streamPosIndex == XFILE_BLOCK_RUNTIME)
	{
		memset(ptr, 0, size);
		g_streamPos += size;
		return;
	}
	DB_ReadXFile((unsigned char *)ptr, size, 0);
	g_streamPos += size;
}

// Store 140374960 (PS4 PDB database/db_stream_load.cpp:137): the pointer stored at a packed offset (an alias:
// the slot DB_InsertPointer reserved for an earlier asset).
void DB_ConvertOffsetToAlias(unsigned long long *data)
{
	unsigned int blockIndex;
	unsigned long long offset;
	DB_GetPackedOffsetStreamPos(*data, &blockIndex, &offset);
	*data = *(unsigned long long *)(g_streamZoneMem->blocks[blockIndex].data + offset);
}

// Store 1403749A0 (PS4 PDB database/db_stream_load.cpp:178)
void DB_ConvertOffsetToPointer(unsigned long long *data)
{
	unsigned int blockIndex;
	unsigned long long offset;
	DB_GetPackedOffsetStreamPos(*data, &blockIndex, &offset);
	*data = (unsigned long long)(g_streamZoneMem->blocks[blockIndex].data + offset);
}

// Store 140374AC0 (PS4 PDB database/db_stream_load.cpp:216): a NUL-terminated string at *str (the current
// position), read one byte at a time.
void Load_XStringCustom(const char **str)
{
	char *s = (char *)*str;
	char *p = s;
	DB_ReadXFile((unsigned char *)p, 1, 0);
	while (*p)
	{
		++p;
		DB_ReadXFile((unsigned char *)p, 1, 0);
	}
	g_streamPos += p - s + 1;
}

// Store 140374A30 (PS4 PDB database/db_stream_load.cpp:238): a string that only lives until SL_GetString has
// made it a script string; the pointer becomes the script string's handle. The Store build inlines
// Load_XStringCustom.
void Load_TempStringCustom(const char **str)
{
	Load_XStringCustom(str);
	if (*str)
		*str = (const char *)(unsigned long long)(unsigned int)SL_GetString(*str, 4);
	else
		*str = nullptr;
}
