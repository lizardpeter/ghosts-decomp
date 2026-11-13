// xanim/xmodel.h: XModel, its LODs and XModelSurfs (Store-build layouts).
//
// The servers' PDBs (iw6_ds_ps4, iw6_ds_xb3: identical) give XModel as 0x228 bytes and XModelLodInfo as 0x38; the
// Store build's are 0x258 and 0x40 (Load_XModel 14035E020 reads 0x258 bytes and 6 LODs of 0x40). Everything after
// numReactiveMotionParts moved: the evidence for each offset is in docs/assets/models.md (the loader for pointers,
// the Store build's accessors for the rest). Members marked "unverified" are placed by the servers' order and
// sizes, with nothing in the Store build found reading them yet.
#pragma once

#include "database/db_stream_api.h"
#include "gfx_d3d/r_xsurface.h"
#include "physics/physpreset.h"
#include "universal/com_math.h"

struct Material;

// A bone's base pose (model space): rotation quaternion and translation; transWeight is 2 / |quat|^2.
struct DObjAnimMat
{
	float quat[4];
	float trans[3];
	float transWeight;
};
static_assert(sizeof(DObjAnimMat) == 0x20, "DObjAnimMat");

struct ReactiveMotionModelPart
{
	float center[3];
	float stiffness;
};
static_assert(sizeof(ReactiveMotionModelPart) == 0x10, "ReactiveMotionModelPart");

// A model-space box (from the bone's hit volume) per bone.
struct XBoneInfo
{
	Bounds bounds;
	union
	{
		float radiusSquared;
		unsigned int radiusSquaredAsInt;
	};
};
static_assert(sizeof(XBoneInfo) == 0x1C, "XBoneInfo");

struct XModelCollSurf_s
{
	Bounds bounds;
	int boneIdx;
	int contents;
	int surfFlags;
};
static_assert(sizeof(XModelCollSurf_s) == 0x24, "XModelCollSurf_s");

// A LOD's surfaces as their own asset (ASSET_TYPE_XMODEL_SURFS): shared by name between models.
struct XModelSurfs
{
	const char *name;
	XSurface *surfs;          // numsurfs entries; always inline when non-null
	unsigned short numsurfs;
	int partBits[8];          // the bones the LOD's surfaces use (bit per bone)
};
static_assert(sizeof(XModelSurfs) == 0x38, "XModelSurfs");
static_assert(__builtin_offsetof(XModelSurfs, partBits) == 0x14, "XModelSurfs");

struct XModelLodInfo
{
	float dist;                // switch to the next LOD beyond this distance (XModelGetLodForDist)
	unsigned short numsurfs;   // copied from modelSurfs->numsurfs at link time (DB_XModelSurfsFixup)
	unsigned short surfIndex;  // first surface's index into XModel::materialHandles (DB_XModelSurfsFixup)
	XModelSurfs *modelSurfs;   // an asset pointer (inline, insert or alias)
	int partBits[8];           // copied from modelSurfs (Load_XModelSurfsFixup)
	XSurface *surfs;           // copied from modelSurfs (Load_XModelSurfsFixup)
	unsigned char unknown38[8];  // Store only, not read by the loader
};
static_assert(sizeof(XModelLodInfo) == 0x40, "XModelLodInfo (Store build)");
static_assert(__builtin_offsetof(XModelLodInfo, modelSurfs) == 0x08, "XModelLodInfo");
static_assert(__builtin_offsetof(XModelLodInfo, partBits) == 0x10, "XModelLodInfo");
static_assert(__builtin_offsetof(XModelLodInfo, surfs) == 0x30, "XModelLodInfo");

#define XMODEL_FLAG_DEFAULT_SURFS 0x2  // DB_XModelSurfsFixup: a LOD uses g_defaultSurfs

struct XModel
{
	const char *name;                         // +0x000
	unsigned char numBones;                   // +0x008
	unsigned char numRootBones;               // +0x009 bones without a parent come first
	unsigned char numsurfs;                   // +0x00A total over the LODs (DB_XModelSurfsFixup)
	unsigned char numReactiveMotionParts;     // +0x00B
	// The servers have lodRampType (u8, +0xC), scale (+0x10) and noScalePartBits[8] (+0x14); the Store build is 8
	// bytes shorter here. scale: 1.0 at +0xC in a real zone (docs); noScalePartBits by size; no lodRampType.
	float scale;                              // +0x00C
	unsigned int noScalePartBits[8];          // +0x010
	scr_string_t *boneNames;                  // +0x030 numBones
	unsigned char *parentList;                // +0x038 numBones - numRootBones: parent index offsets
	short *quats;                             // +0x040 (numBones - numRootBones) * 4: packed base-pose rotations
	float *trans;                             // +0x048 (numBones - numRootBones) * 3: base-pose translations
	unsigned char *partClassification;        // +0x050 numBones: hit location per bone
	DObjAnimMat *baseMat;                     // +0x058 numBones (XModelGetBasePose)
	ReactiveMotionModelPart *reactiveMotionParts;  // +0x060 numReactiveMotionParts
	Material **materialHandles;               // +0x068 numsurfs (XModelGetSkins), always inline when non-null
	XModelLodInfo lodInfo[6];                 // +0x070
	char maxLoadedLod;                        // +0x1F0 first LOD XModelGetLodForDist considers
	char numLods;                             // +0x1F1
	char collLod;                             // +0x1F2 unverified (by position)
	unsigned char flags;                      // +0x1F3 XMODEL_FLAG_*
	int numCollSurfs;                         // +0x1F4
	XModelCollSurf_s *collSurfs;              // +0x1F8 numCollSurfs; always inline when non-null
	int contents;                             // +0x200 (XModelGetContents)
	XBoneInfo *boneInfo;                      // +0x208 numBones; always inline when non-null
	float radius;                             // +0x210 (XModelGetRadius)
	Bounds bounds;                            // +0x214 (XModelGetBounds)
	int memUsage;                             // +0x22C unverified (by position)
	unsigned short *unknown230;               // +0x230 Store only: numsurfs entries, always inline when non-null
	bool bad;                                 // +0x238 unverified (by position)
	PhysPreset *physPreset;                   // +0x240
	PhysCollmap *physCollmap;                 // +0x248
	float quantization;                       // +0x250 unverified (by position)
};
static_assert(sizeof(XModel) == 0x258, "XModel (Store build)");
static_assert(__builtin_offsetof(XModel, scale) == 0x0C, "XModel");
static_assert(__builtin_offsetof(XModel, boneNames) == 0x30, "XModel");
static_assert(__builtin_offsetof(XModel, materialHandles) == 0x68, "XModel");
static_assert(__builtin_offsetof(XModel, lodInfo) == 0x70, "XModel");
static_assert(__builtin_offsetof(XModel, maxLoadedLod) == 0x1F0, "XModel");
static_assert(__builtin_offsetof(XModel, flags) == 0x1F3, "XModel");
static_assert(__builtin_offsetof(XModel, numCollSurfs) == 0x1F4, "XModel");
static_assert(__builtin_offsetof(XModel, contents) == 0x200, "XModel");
static_assert(__builtin_offsetof(XModel, boneInfo) == 0x208, "XModel");
static_assert(__builtin_offsetof(XModel, radius) == 0x210, "XModel");
static_assert(__builtin_offsetof(XModel, bounds) == 0x214, "XModel");
static_assert(__builtin_offsetof(XModel, unknown230) == 0x230, "XModel");
static_assert(__builtin_offsetof(XModel, physPreset) == 0x240, "XModel");
static_assert(__builtin_offsetof(XModel, physCollmap) == 0x248, "XModel");

union XAssetHeader
{
	XModel *model;
	XModelSurfs *modelSurfs;
	PhysPreset *physPreset;
	PhysCollmap *physCollmap;
	void *data;
};

void Load_XModel(bool atStreamStart);
void Load_XModelPtr(bool atStreamStart);
void Load_XModelPtrArray(bool atStreamStart, unsigned long long count);
void Load_XModelSurfs(bool atStreamStart);
void Load_XModelSurfsPtr(bool atStreamStart);
void Load_MaterialHandleArray(bool atStreamStart, unsigned long long count);  // gfx_d3d/r_material_load_db.h
void Load_XModelAsset(XModel **model);                                        // database/db_registry.cpp
void Load_XModelSurfsAsset(XModelSurfs **modelSurfs);                         // database/db_registry.cpp
void Load_XModelSurfsFixup(XModelSurfs **modelSurfs, XModelLodInfo *lodInfo); // database/db_registry.cpp
void DB_XModelSurfsFixup(XAssetHeader header, void *data);                    // database/db_registry.cpp

extern XModel *varXModel;
extern XModel **varXModelPtr;
extern XModelSurfs *varXModelSurfs;
extern XModelSurfs **varXModelSurfsPtr;
extern XModelLodInfo *varXModelLodInfo;
extern XModelCollSurf_s *varXModelCollSurf;
extern XBoneInfo *varXBoneInfo;
extern DObjAnimMat *varDObjAnimMat;
extern ReactiveMotionModelPart *varReactiveMotionModelPart;
extern Material **varMaterialHandle;
extern unsigned short *unk_144424D18;  // Store only: XModel::unknown230 being loaded
extern const XSurface *g_defaultSurfs;
