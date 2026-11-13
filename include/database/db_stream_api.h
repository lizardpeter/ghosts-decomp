// database/db_stream_api.h: the zone stream functions the asset loaders call (Store build).
//
// These belong to the fastfile pipeline (database/db_stream.cpp and db_stream_load.cpp in the PS4 PDB), which is
// documented in docs/fastfiles.md; they are declared here so the per-asset Load_* functions can be built and tested
// against the Store build. The prototypes are the PS4 MAP's decorated names.
//
// The loader contract, as every Load_* function in this build uses it:
// - g_streamPos is the write position in the current block. Load_Stream(true, ptr, size) reads `size` bytes of the
//   zone into ptr (which is g_streamPos) and advances g_streamPos; Load_Stream(false, ...) does nothing (the bytes
//   were read as part of an enclosing struct).
// - A pointer field holds 0 (null), DB_PTR_FOLLOWING (the data follows inline in the stream: align g_streamPos,
//   point the field at it, load it), DB_PTR_INSERT (as FOLLOWING, and also reserve a slot with DB_InsertPointer that
//   later aliases resolve to), or anything else: a packed (block, offset) that DB_ConvertOffsetToPointer turns into
//   an address (DB_ConvertOffsetToAlias for asset pointers: the address of a pointer to the asset).
// - DB_PushStreamPos(block) switches the current block (3: XFILE_BLOCK_VIRTUAL for asset headers' contents, 0:
//   XFILE_BLOCK_TEMP for asset pointers); DB_PopStreamPos() switches back.
#pragma once

#define DB_PTR_FOLLOWING 0xFDFDFDFFFFFFFFFFull  // -1 in the 32-bit IW engines' zones
#define DB_PTR_INSERT 0xFDFDFDFFFFFFFFFEull     // -2

// True for a pointer field that marks inline data (FOLLOWING or INSERT); the generated code tests this as
// `p - DB_PTR_INSERT < 2` (unsigned).
#define DB_PTR_IS_INLINE(p) ((unsigned long long)(p) - DB_PTR_INSERT < 2)

enum XFILE_BLOCK_TYPES
{
	XFILE_BLOCK_TEMP = 0,
	XFILE_BLOCK_PHYSICAL = 1,
	XFILE_BLOCK_RUNTIME = 2,
	XFILE_BLOCK_VIRTUAL = 3,
	XFILE_BLOCK_LARGE = 4,
	XFILE_BLOCK_CALLBACK = 5,
	XFILE_BLOCK_SCRIPT = 6,
};

enum scr_string_t : int
{
};

extern unsigned char *g_streamPos;

void Load_Stream(bool atStreamStart, void *ptr, unsigned long long size);  // Store 1403749E0
void DB_PushStreamPos(unsigned int index);                                 // Store 1403748D0
void DB_PopStreamPos();                                                    // Store 140374850
void DB_ConvertOffsetToPointer(unsigned long long *data);                  // Store 1403749A0
void DB_ConvertOffsetToAlias(unsigned long long *data);                    // Store 140374960
unsigned char *DB_InsertPointer();                                         // Store 140374750
void Load_XStringCustom(const char **str);                                 // Store 140374AC0
void Load_scr_string_tArray(bool atStreamStart, unsigned long long count); // Store 140361EA0

// Shared by every loader that reads a string or a primitive array.
extern const char **varXString;
extern const char *varConstChar;
extern scr_string_t *varscr_string_t;
extern unsigned char *varbyte;
extern short *varshort;
extern float *varfloat;
