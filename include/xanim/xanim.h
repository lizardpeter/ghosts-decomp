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

// ---- animation classes (asset type 0x20, "animclass"): the servers' PDBs' layouts ------------------------------

struct ScriptableDef;
struct FxEffectDef;

struct AnimationEntry
{
	scr_string_t alias;
	scr_string_t animName;
};

struct AnimationAimSet
{
	scr_string_t name;          // +0x00
	scr_string_t rootName;      // +0x04
	scr_string_t animName[8];   // +0x08
	unsigned char rest[0x48];   // +0x28 (no pointers)
};
static_assert(sizeof(AnimationAimSet) == 0x70, "AnimationAimSet");

struct AnimationState
{
	scr_string_t name;                  // +0x00
	scr_string_t notify;                // +0x04
	float blendTime;                    // +0x08
	unsigned char flags;                // +0x0C
	unsigned char entryCount;           // +0x0D
	AnimationAimSet *aimSet;            // +0x10
	AnimationEntry *animEntries;        // +0x18
	unsigned long long *animIndices;    // +0x20 (runtime block)
};
static_assert(sizeof(AnimationState) == 0x28, "AnimationState");

struct AnimationStateMachine
{
	scr_string_t name;                  // +0x00
	unsigned short stateCount;          // +0x04
	unsigned short aimSetCount;         // +0x06
	AnimationState *states;             // +0x08
	AnimationAimSet *aimSets;           // +0x10
};
static_assert(sizeof(AnimationStateMachine) == 0x18, "AnimationStateMachine");

struct AnimationClass
{
	const char *className;                  // +0x00
	AnimationStateMachine *stateMachine;    // +0x08
	int animCtrl;                           // +0x10
	scr_string_t animTree;                  // +0x14
	ScriptableDef *scriptable;              // +0x18
	unsigned short soundCount;              // +0x20
	unsigned short effectCount;             // +0x22
	scr_string_t *soundNotes;               // +0x28
	scr_string_t *soundNames;               // +0x30
	scr_string_t *soundOptions;             // +0x38
	scr_string_t *effectNotes;              // +0x40
	const FxEffectDef **effectDefs;         // +0x48
	scr_string_t *effectTags;               // +0x50
};
static_assert(sizeof(AnimationClass) == 0x58, "AnimationClass");

void Load_AnimationAimSet(bool atStreamStart);
void Load_AnimationStateArray(bool atStreamStart, unsigned long long count);
void Load_AnimationStateMachine(bool atStreamStart);
void Load_AnimationClass(bool atStreamStart);
void Load_AnimationClassPtr(bool atStreamStart);
