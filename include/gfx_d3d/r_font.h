// gfx_d3d/r_font.h: bitmap fonts (Font_s, asset type 0x1D). Layouts from the PS4 server PDB
// (analysis/iw6_ds_ps4/pdb/types.h); the Store build's loaders use the same (src/gfx_d3d/r_font_load_db.cpp).
#pragma once

#include <stddef.h>

struct Material;

struct Glyph
{
	unsigned short letter;               // +0x0: the character (UCS-2)
	char x0;                             // +0x2: offset from the pen to the glyph's top left, pixels
	char y0;                             // +0x3
	unsigned char dx;                    // +0x4: advance
	unsigned char pixelWidth;            // +0x5
	unsigned char pixelHeight;           // +0x6
	float s0;                            // +0x8: the glyph's rectangle in the atlas, 0..1
	float t0;                            // +0xC
	float s1;                            // +0x10
	float t1;                            // +0x14
};
static_assert(sizeof(Glyph) == 0x18, "Glyph");
static_assert(offsetof(Glyph, s0) == 0x8, "Glyph::s0");

struct Font_s
{
	const char *fontName;                // +0x0
	int pixelHeight;                     // +0x8
	int glyphCount;                      // +0xC
	Material *material;                  // +0x10: the atlas
	Material *glowMaterial;              // +0x18
	Glyph *glyphs;                       // +0x20
};
static_assert(sizeof(Font_s) == 0x28, "Font_s");

void Load_Font(bool atStreamStart);
void Load_FontHandle(bool atStreamStart);
