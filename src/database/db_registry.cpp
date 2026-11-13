// database/db_registry.cpp (Store build): the image stream table that Load_ImageStream fills while a zone loads.
//
// The servers' Load_ImageStream (database/db_registry.cpp:2909 in the PS4 PDB) takes a GfxImage and does nothing
// the Store build does: the Store build streams image data from imagefile paks (docs/assets/images.md). Its body
// (140374E70) is reached through a function pointer (140993968) with the image's index in the image pool
// (14036CC90), from the link of every new image (Load_GfxImageAsset).

#define IW6_SOURCE "database/db_registry.cpp"
#include <iw6_static.h>
#include "database/db_local.h"
#include "gfx_d3d/r_image.h"

IW6_STATIC DBImageStreamLevel unk_145FB8200[][4] IW6_AT("", "unk_145FB8200");  // per pool image: its stream levels
IW6_STATIC unsigned int unk_14604C200[] IW6_AT("", "unk_14604C200");           // per pool image: flags & 0x10, a bit
IW6_STATIC float unk_145F94D80[] IW6_AT("", "unk_145F94D80");                  // per pool image: the diagonal
IW6_STATIC void *unk_14604CA10[0x60] IW6_AT("", "unk_14604CA10");              // open image pak handles, by N
IW6_STATIC DBImageFile unk_14604CFE0[0x60] IW6_AT("", "unk_14604CFE0");        // image paks, by N

StreamImageRow *sub_1403492E0();
DBFile *sub_1403497F0();
void Com_sprintf(char *dest, int size, const char *fmt, ...);
void *sub_140548160(void **handles, int count, int imageFiles, unsigned int fileIndex, unsigned int localized);
void sub_1403710C0();
void DB_DirtyDiscError();
void sub_14062E430(GfxImage *image, Picmip *picmip);

// Store 140374E70 (database/db_registry.cpp, Load_ImageStream): a streamed image takes the next four rows of the
// fastfile's streamed-image table, one per stream level (smallest first), opening each pak on first use; it also
// keeps the image's flag 0x10 in a bit set and the length of its diagonal at stream level 0 (+0x40, +0x42).
void Load_ImageStream(unsigned int imageIndex, GfxImage *image)
{
	DBImageStreamLevel *levels = unk_145FB8200[imageIndex];
	if (!image->streaming)
		return;
	unsigned int bit = 0x80000000u >> (imageIndex & 0x1f);
	if (image->flags & IMG_FLAG_STREAM_HINT)
		unk_14604C200[imageIndex >> 5] |= bit;
	else
		unk_14604C200[imageIndex >> 5] &= ~bit;
	for (int i = 0; i < 4; i++)
	{
		StreamImageRow *row = sub_1403492E0();
		DBFile *file;
		levels[i].offset = row->offset;
		levels[i].end = row->end;
		if (!row->end)
		{
			file = nullptr;
		}
		else if (!row->fileIndex)
		{
			file = sub_1403497F0();
		}
		else
		{
			DBImageFile *pak = &unk_14604CFE0[row->fileIndex];
			if (!unk_14604CA10[row->fileIndex])
			{
				Com_sprintf(pak->file.name, sizeof(pak->file.name), "imagefile%d", row->fileIndex);
				pak->fileIndex = row->fileIndex;
				pak->localized = row->localized;
				pak->file.handle = sub_140548160(unk_14604CA10, 0x60, 1, row->fileIndex, row->localized);
				if (!pak->file.handle)
				{
					sub_1403710C0();
					DB_DirtyDiscError();
				}
			}
			pak->used = true;
			file = &pak->file;
		}
		levels[i].file = file;
	}
	float width = (float)image->streamLevels[0].width;
	float height = (float)image->streamLevels[0].height;
	unk_145F94D80[imageIndex] = __builtin_sqrtf(height * height + width * width);
}

// Store 1403723B0 (name unknown): run on a GfxImage after it is loaded from a zone (Load_GfxImage)
void sub_1403723B0(GfxImage *image)
{
	sub_14062E430(image, &image->picmip);
}
