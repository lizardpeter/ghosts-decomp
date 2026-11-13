// database/db_memory.cpp (Store build)
//
// Allocating a zone's seven blocks: each block belongs to one of four memory types (g_block_mem_type: temp,
// runtime and callback in type 3, physical in 1, virtual and large in 0, script in 2; docs/fastfiles.md); the
// blocks of a type share one allocation, each rounded up to the type's alignment. Names: the PS4/Xbox One server PDBs
// (database/db_memory.cpp). The Store build adds a bump allocator over the callback block (sub_140369230).

#include <iw6_static.h>

#include "database/db_local.h"

#define IW6_SOURCE "database/db_memory.cpp"

enum PMem_Source
{
};

struct XZoneMemoryTypeInfo  // 0xC
{
	unsigned int alignment;
	unsigned int physicalType;
	PMem_Source physicalSource;
};

IW6_STATIC const unsigned int g_block_mem_type[MAX_XFILE_COUNT] IW6_AT("", "g_block_mem_type");
IW6_STATIC const XZoneMemoryTypeInfo g_memoryTypeInfo[4] IW6_AT("", "g_memoryTypeInfo");
IW6_STATIC unsigned char *unk_144427248 IW6_AT("", "unk_144427248");      // the callback block's memory
IW6_STATIC unsigned long long unk_144427250 IW6_AT("", "unk_144427250");  // how much of it is used

void *PMem_AllocFromSource_NoDebug(unsigned long long size, unsigned long long alignment, unsigned int type,
                                   PMem_Source source);

// Store 1403692F0 (PS4 PDB database/db_memory.cpp:70)
void DB_AllocXZoneMemoryInternal(unsigned long long *const blockSize, const char *filename, XZoneMemory *zoneMem,
                                 unsigned int type)
{
	unsigned long long mask = (unsigned int)(g_memoryTypeInfo[type].alignment - 1);
	unsigned long long total = 0;
	for (int i = 0; i < MAX_XFILE_COUNT; ++i)
	{
		if (g_block_mem_type[i] == type)
			total += (blockSize[i] + mask) & ~mask;
	}
	if (!total)
		return;
	unsigned char *mem = (unsigned char *)PMem_AllocFromSource_NoDebug(total, g_memoryTypeInfo[type].alignment,
	                                                                  g_memoryTypeInfo[type].physicalType,
	                                                                  g_memoryTypeInfo[type].physicalSource);
	for (int i = 0; i < MAX_XFILE_COUNT - 1; ++i)
	{
		if (g_block_mem_type[i] == type && blockSize[i])
		{
			zoneMem->blocks[i].data = mem;
			zoneMem->blocks[i].size = blockSize[i];
			mem += (blockSize[i] + mask) & ~mask;
		}
	}
	if (g_block_mem_type[MAX_XFILE_COUNT - 1] == type && blockSize[MAX_XFILE_COUNT - 1])
	{
		zoneMem->blocks[MAX_XFILE_COUNT - 1].data = mem;
		zoneMem->blocks[MAX_XFILE_COUNT - 1].size = blockSize[MAX_XFILE_COUNT - 1];
	}
}

// Store 140369260 (PS4 PDB database/db_memory.cpp:142): types 1, 0, 3, 2 in that order; the Store build then
// points its callback allocator at block 5.
void DB_AllocXZoneMemory(unsigned long long *const blockSize, const char *filename, XZoneMemory *zoneMem)
{
	DB_AllocXZoneMemoryInternal(blockSize, filename, zoneMem, 1);
	DB_AllocXZoneMemoryInternal(blockSize, filename, zoneMem, 0);
	DB_AllocXZoneMemoryInternal(blockSize, filename, zoneMem, 3);
	DB_AllocXZoneMemoryInternal(blockSize, filename, zoneMem, 2);
	unk_144427248 = zoneMem->blocks[XFILE_BLOCK_CALLBACK].data;
	unk_144427250 = 0;
}

// Store 140369230 (name unknown): `size` bytes of the callback block, aligned.
unsigned char *sub_140369230(unsigned long long size, unsigned long long alignment)
{
	unsigned long long at = (unk_144427250 + (alignment - 1)) & ~(alignment - 1);
	unk_144427250 = at + size;
	return unk_144427248 + at;
}
