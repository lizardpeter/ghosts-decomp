// gfx_d3d/r_postfx.h: the post-processing assets (Store-build layouts, which are the servers' PDBs'): Colorization
// (asset type 0x38), ColorizationSet (0x39), ToneMapping (0x3A). docs/assets/postfx.md.
#pragma once

#include "database/db_stream_api.h"

struct Material;

struct GfxColorization
{
	float powerAndDesaturation[4];
	float scale[3];
	float bias[3];
};

struct Colorization : GfxColorization
{
	const char *name;  // +0x28
};
static_assert(sizeof(Colorization) == 0x30, "Colorization");

struct ColorizationSet
{
	const char *name;                     // +0x00
	float lowAndHighEndPoints[4];         // +0x08
	float midEndPoints[4];                // +0x18
	float alternateDepthScaleAndBias[2];  // +0x28
	Colorization *colorization;           // +0x30
	Colorization *colorizationAlternate;  // +0x38
	Colorization *colorizationLow;        // +0x40
	Colorization *colorizationMid;        // +0x48
	Colorization *colorizationHigh;       // +0x50
	Material *alternateMaskMaterial;      // +0x58
	unsigned char flags;                  // +0x60
};
static_assert(sizeof(ColorizationSet) == 0x68, "ColorizationSet");

struct GfxToneMapping
{
	float toeStrength[3];
	float toeAngleNumerator[3];
	float toeAngleDenominator[3];
	float linearStrength[3];
	float linearAngle[3];
	float shoulderStrength[3];
	float whitePoint[3];
	float exposure[3];
	float adaptationRates[2];
};

struct ToneMapping : GfxToneMapping
{
	const char *name;  // +0x68
};
static_assert(sizeof(ToneMapping) == 0x70, "ToneMapping");
