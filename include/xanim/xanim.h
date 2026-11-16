// xanim/xanim.h: animations (XAnimParts, asset type 2), Store-build layouts.
//
// The layouts are the servers' PDBs' (iw6_ds_xb3), and every offset the Store loaders touch agrees with them;
// tools/fastfile/xanim.py is the same loader in Python, checked against the game on real zones.
// docs/assets/animations.md.
#pragma once

#include "database/db_stream_api.h"

union XAnimIndices
{
	unsigned char *_1;
	unsigned short *_2;
	void *data;
};
static_assert(sizeof(XAnimIndices) == 8, "XAnimIndices");

struct XAnimNotifyInfo
{
	scr_string_t name;
	float time;
};
static_assert(sizeof(XAnimNotifyInfo) == 8, "XAnimNotifyInfo");

// A frame index table: size + 1 bytes (animations under 256 frames) or u16, stored inline after the frames header.
union XAnimDynamicIndices
{
	unsigned char _1[1];
	unsigned short _2[1];
};

union XAnimDynamicFrames
{
	unsigned char (*_1)[3];
	unsigned short (*_2)[3];
};

struct XAnimPartTransFrames
{
	float mins[3];
	float size[3];
	XAnimDynamicFrames frames;
	XAnimDynamicIndices indices;
};
static_assert(__builtin_offsetof(XAnimPartTransFrames, frames) == 0x18, "XAnimPartTransFrames");
static_assert(__builtin_offsetof(XAnimPartTransFrames, indices) == 0x20, "XAnimPartTransFrames");

union XAnimPartTransData
{
	XAnimPartTransFrames frames;
	float frame0[3];
};

struct XAnimPartTrans
{
	unsigned short size;
	unsigned char smallTrans;
	XAnimPartTransData u;
};
static_assert(sizeof(XAnimPartTrans) == 0x30, "XAnimPartTrans");
static_assert(__builtin_offsetof(XAnimPartTrans, u) == 8, "XAnimPartTrans");

struct XAnimDeltaPartQuatDataFrames2
{
	short (*frames)[2];
	XAnimDynamicIndices indices;
};

union XAnimDeltaPartQuatData2
{
	XAnimDeltaPartQuatDataFrames2 frames;
	short frame0[2];
};

struct XAnimDeltaPartQuat2
{
	unsigned short size;
	XAnimDeltaPartQuatData2 u;
};
static_assert(sizeof(XAnimDeltaPartQuat2) == 0x18, "XAnimDeltaPartQuat2");

struct XAnimDeltaPartQuatDataFrames
{
	short (*frames)[4];
	XAnimDynamicIndices indices;
};

union XAnimDeltaPartQuatData
{
	XAnimDeltaPartQuatDataFrames frames;
	short frame0[4];
};

struct XAnimDeltaPartQuat
{
	unsigned short size;
	XAnimDeltaPartQuatData u;
};
static_assert(sizeof(XAnimDeltaPartQuat) == 0x18, "XAnimDeltaPartQuat");

struct XAnimDeltaPart
{
	XAnimPartTrans *trans;
	XAnimDeltaPartQuat2 *quat2;
	XAnimDeltaPartQuat *quat;
};
static_assert(sizeof(XAnimDeltaPart) == 0x18, "XAnimDeltaPart");

struct XAnimParts
{
	const char *name;
	unsigned short dataByteCount;
	unsigned short dataShortCount;
	unsigned short dataIntCount;
	unsigned short randomDataByteCount;
	unsigned short randomDataIntCount;
	unsigned short numframes;
	unsigned char flags;
	unsigned char boneCount[10];
	unsigned char notifyCount;
	unsigned char assetType;
	unsigned char ikType;
	unsigned int randomDataShortCount;
	unsigned int indexCount;
	float framerate;
	float frequency;
	scr_string_t *names;
	unsigned char *dataByte;
	short *dataShort;
	int *dataInt;
	short *randomDataShort;
	unsigned char *randomDataByte;
	int *randomDataInt;
	XAnimIndices indices;
	XAnimNotifyInfo *notify;
	XAnimDeltaPart *deltaPart;
};
static_assert(sizeof(XAnimParts) == 0x88, "XAnimParts");
static_assert(__builtin_offsetof(XAnimParts, randomDataShortCount) == 0x24, "XAnimParts");
static_assert(__builtin_offsetof(XAnimParts, names) == 0x38, "XAnimParts");
static_assert(__builtin_offsetof(XAnimParts, deltaPart) == 0x80, "XAnimParts");

void Load_XAnimIndices(bool atStreamStart);
void Load_XAnimDynamicIndicesTrans(bool atStreamStart);
void Load_XAnimDynamicIndicesDeltaQuat2(bool atStreamStart);
void Load_XAnimDynamicIndicesDeltaQuat(bool atStreamStart);
void Load_XAnimDynamicFrames(bool atStreamStart);
void Load_XAnimPartTrans(bool atStreamStart);
void Load_XAnimDeltaPartQuatDataFrames2(bool atStreamStart);
void Load_XAnimDeltaPartQuatDataFrames(bool atStreamStart);
void Load_XAnimDeltaPart(bool atStreamStart);
void Load_XAnimParts(bool atStreamStart);
void Load_XAnimPartsPtr(bool atStreamStart);
void Load_XAnimPartsAsset(XAnimParts **header);  // Store 140374000 (links the asset; not reconstructed here)
