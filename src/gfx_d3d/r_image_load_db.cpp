// gfx_d3d/r_image_load_db.h (Store build): the zone loaders of GfxImage.
//
// Generated loader functions of gfx_d3d/r_image_load_db.h (included into database/db_load.cpp; the PS4/xb3 servers'
// PDBs give the names and lines). The servers' GfxImage is 0x38 bytes and has no pixels in the zone; the Store
// build's is 0x68 (include/gfx_d3d/r_image.h) and Load_GfxTextureLoad reads an in-zone image's pixels, which
// Load_Texture turns into the texture at once. docs/assets/images.md has the formats.

#include "gfx_d3d/r_image.h"
#include "database/db_stream_api.h"

extern GfxImage *varGfxImage;               // Store 144425860
extern GfxImage **varGfxImagePtr;            // Store 144425868
extern GfxImageLoadDef **varGfxTextureLoad;  // Store 144425850: &varGfxImage->loadDef (the servers' GfxTexture *)

void Load_GfxImageAsset(GfxImage **image);  // Store 140372150 (database/db_registry.cpp:2982 in the PS4 PDB)
void Load_Texture(GfxImageLoadDef **remoteLoadDef, GfxImage *image);  // Store 14062BA80 (src/gfx_d3d/r_image.cpp)
void sub_1403723B0(GfxImage *image);        // Store 1403723B0 (src/database/db_registry.cpp)

// Store 14034F1D0 (gfx_d3d/r_image_load_db.h:3420 in the PS4 PDB, Load_GfxTextureLoad): the pixels of an image
// that isn't streamed, in the temp block. The water image has a 1-byte placeholder; any other image has
// cardMemory.platform[0] bytes.
void Load_GfxTextureLoad(bool atStreamStart)
{
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	GfxImageLoadDef **loadDefPtr = varGfxTextureLoad;
	unsigned long long value = (unsigned long long)*varGfxTextureLoad;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varGfxTextureLoad);
			DB_PopStreamPos();
			return;
		}
		*varGfxTextureLoad = (GfxImageLoadDef *)g_streamPos;
		varbyte = g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		if (varGfxImage->semantic == TS_WATER_MAP)
			Load_Stream(true, varbyte, 1);
		else
			Load_Stream(true, varbyte, (long long)varGfxImage->cardMemory.platform[0]);
		Load_Texture(loadDefPtr, varGfxImage);
		if (inserted)
			*(GfxImageLoadDef **)inserted = *loadDefPtr;
	}
	DB_PopStreamPos();
}

// Store 14034F120 (gfx_d3d/r_image_load_db.h:6196 in the PS4 PDB)
void Load_GfxImage(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxImage, sizeof(GfxImage));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varGfxImage->name;
	Load_Stream(false, varXString, sizeof(const char *));
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
	varGfxTextureLoad = &varGfxImage->loadDef;
	Load_GfxTextureLoad(false);
	DB_PopStreamPos();
	sub_1403723B0(varGfxImage);
}

// Store 14034F380 (gfx_d3d/r_image_load_db.h:6617 in the PS4 PDB)
void Load_GfxImagePtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxImagePtr, sizeof(GfxImage *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	GfxImage **imagePtr = varGfxImagePtr;
	unsigned long long value = (unsigned long long)*varGfxImagePtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varGfxImagePtr);
			DB_PopStreamPos();
			return;
		}
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		*varGfxImagePtr = (GfxImage *)g_streamPos;
		varGfxImage = (GfxImage *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_GfxImage(true);
		Load_GfxImageAsset(imagePtr);
		if (inserted)
			*(GfxImage **)inserted = *imagePtr;
	}
	DB_PopStreamPos();
}
