// database/db_fastfile_pointer.cpp (Store build)

#include "database/db_local.h"

// Store 1401905A0 (PS4 PDB database/db_fastfile_pointer.cpp:174): a stored offset is the block index in bits 32-35
// and the offset plus one in the low 32 bits (0 stays the null pointer).
void DB_GetPackedOffsetStreamPos(unsigned long long packed, unsigned int *__restrict blockIndex,
                                 unsigned long long *__restrict offset)
{
	*offset = (packed & 0xFFFFFFFF) - 1;
	*blockIndex = (unsigned int)(packed >> 32) & 0xF;
}
