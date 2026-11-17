// gfx_d3d/r_font_load_db.cpp (Store build): the zone loaders of fonts (Font_s, asset type 0x1D). Generated loader
// code (the servers' PDB places it in gfx_d3d/r_material_load_db.h), tagged with Store addresses.
// tools/fastfile/font.py is the same in Python, checked against the game on real zones (docs/assets/fonts.md);
// tests/differential/test_font_load.py checks this file against the exe.

#include "gfx_d3d/r_font.h"
#include "database/db_stream_api.h"

void Load_MaterialHandle(bool atStreamStart);             // Store 140353700
void Load_FontAsset(Font_s **font);                       // Store 140371D50

extern Material **varMaterialHandle;                      // Store 144425D20
extern Font_s **varFontHandle;                            // Store 1444252D0
extern Font_s *varFont;                                   // Store 1444252C8
extern Glyph *varGlyph;                                   // Store 1444252C0

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// Store 14034CE20
void Load_Font(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFont, sizeof(Font_s));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varFont->fontName;
	Load_Stream(false, varFont, 8);
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
	varMaterialHandle = &varFont->material;
	Load_MaterialHandle(false);
	varMaterialHandle = &varFont->glowMaterial;
	Load_MaterialHandle(false);
	if (varFont->glyphs)
	{
		if ((unsigned long long)varFont->glyphs == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varFont->glyphs = (Glyph *)g_streamPos;
			varGlyph = (Glyph *)g_streamPos;
			Load_Stream(true, g_streamPos, (long long)varFont->glyphCount * sizeof(Glyph));
			DB_PopStreamPos();
			return;
		}
		DB_ConvertOffsetToPointer((unsigned long long *)&varFont->glyphs);
	}
	DB_PopStreamPos();
}

// Store 14034CF50
void Load_FontHandle(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFontHandle, sizeof(Font_s *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	Font_s **ptr = varFontHandle;
	unsigned long long value = (unsigned long long)*varFontHandle;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varFontHandle);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varFontHandle = (Font_s *)g_streamPos;
		varFont = (Font_s *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_Font(true);
		Load_FontAsset(ptr);
		if (inserted)
			*(Font_s **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
