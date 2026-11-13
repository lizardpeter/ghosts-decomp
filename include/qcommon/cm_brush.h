// qcommon/cm_brush.h: collision brushes as physics collision maps carry them (BrushWrapper), Store-build layouts.
//
// Layouts are the servers' PDBs' (iw6_ds_ps4, iw6_ds_xb3, identical); every offset below that a Store loader touches
// is checked against it (Load_BrushWrapper 14034AF80, Load_cbrushWrapper_t 14035F860, Load_cbrushside_tArray
// 14035FA50). See docs/assets/models.md.
#pragma once

#include "universal/com_math.h"  // Bounds

struct cplane_s
{
	float normal[3];
	float dist;
	unsigned char type;  // 0..2: axial plane on x/y/z, 3: not axial
	unsigned char pad[3];
};
static_assert(sizeof(cplane_s) == 0x14, "cplane_s");

struct cbrushside_t
{
	cplane_s *plane;  // inline (DB_PTR_FOLLOWING) or an offset
	unsigned short materialNum;
	unsigned char firstAdjacentSideOffset;
	unsigned char edgeCount;
};
static_assert(sizeof(cbrushside_t) == 0x10, "cbrushside_t");

struct cbrush_t
{
	unsigned short numsides;
	unsigned short glassPieceIndex;
	cbrushside_t *sides;               // numsides entries; always inline when non-null
	unsigned char *baseAdjacentSide;   // BrushWrapper::totalEdgeCount bytes; always inline when non-null
	short axialMaterialNum[2][3];
	unsigned char firstAdjacentSideOffsets[2][3];
	unsigned char edgeCount[2][3];
};
static_assert(sizeof(cbrush_t) == 0x30, "cbrush_t");
static_assert(__builtin_offsetof(cbrush_t, sides) == 0x08, "cbrush_t");
static_assert(__builtin_offsetof(cbrush_t, baseAdjacentSide) == 0x10, "cbrush_t");

struct BrushWrapper
{
	Bounds bounds;
	cbrush_t brush;
	int totalEdgeCount;
	cplane_s *planes;  // brush.numsides entries; inline or an offset
};
static_assert(sizeof(BrushWrapper) == 0x58, "BrushWrapper");
static_assert(__builtin_offsetof(BrushWrapper, brush) == 0x18, "BrushWrapper");
static_assert(__builtin_offsetof(BrushWrapper, totalEdgeCount) == 0x48, "BrushWrapper");
static_assert(__builtin_offsetof(BrushWrapper, planes) == 0x50, "BrushWrapper");

void Load_BrushWrapper(bool atStreamStart);
void Load_cbrushWrapper_t(bool atStreamStart);
void Load_cbrushside_tArray(bool atStreamStart, unsigned long long count);

extern BrushWrapper *varBrushWrapper;
extern cbrush_t *varcbrushWrapper_t;
extern cbrushside_t *varcbrushside_t;
extern cplane_s *varcplane_t;
extern unsigned char *varcbrushedge_t;
