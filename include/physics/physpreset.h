// physics/physpreset.h: PhysPreset and PhysCollmap, the physics assets an XModel references (Store-build layouts).
//
// Both are the servers' layouts (iw6_ds_ps4/iw6_ds_xb3 PDBs, identical); the Store loaders (Load_PhysPreset
// 140355500, Load_PhysCollmap 1403552B0) read the same sizes and pointer offsets. docs/assets/models.md.
#pragma once

#include "qcommon/cm_brush.h"

enum PhysPresetScaling : int
{
	PHYSPRESET_SCALING_LINEAR = 0,
	PHYSPRESET_SCALING_QUADRATIC = 1,
	PHYSPRESET_SCALING_COUNT = 2,
};

struct PhysPreset
{
	const char *name;
	int type;
	float mass;
	float bounce;
	float friction;
	float bulletForceScale;
	float explosiveForceScale;
	const char *sndAliasPrefix;
	float piecesSpreadFraction;
	float piecesUpwardVelocity;
	float minMomentum;
	float maxMomentum;
	float minVolume;
	float maxVolume;
	float minPitch;
	float maxPitch;
	PhysPresetScaling volumeType;
	PhysPresetScaling pitchType;
	bool tempDefaultToCylinder;
	bool perSurfaceSndAlias;
};
static_assert(sizeof(PhysPreset) == 0x58, "PhysPreset");
static_assert(__builtin_offsetof(PhysPreset, sndAliasPrefix) == 0x20, "PhysPreset");
static_assert(__builtin_offsetof(PhysPreset, volumeType) == 0x48, "PhysPreset");

struct PhysMass
{
	float centerOfMass[3];
	float momentsOfInertia[3];
	float productsOfInertia[3];
};
static_assert(sizeof(PhysMass) == 0x24, "PhysMass");

// One collision primitive of a PhysCollmap. type: PHYS_GEOM_* (box, brushmodel, brush, cylinder, capsule, ...);
// only brushes carry a BrushWrapper.
struct PhysGeomInfo
{
	BrushWrapper *brushWrapper;  // always inline when non-null (no offset form)
	int type;
	float orientation[3][3];
	Bounds bounds;
};
static_assert(sizeof(PhysGeomInfo) == 0x48, "PhysGeomInfo");
static_assert(__builtin_offsetof(PhysGeomInfo, orientation) == 0x0C, "PhysGeomInfo");
static_assert(__builtin_offsetof(PhysGeomInfo, bounds) == 0x30, "PhysGeomInfo");

struct PhysCollmap
{
	const char *name;
	unsigned int count;
	PhysGeomInfo *geoms;  // count entries; always inline when non-null
	PhysMass mass;
	Bounds bounds;
};
static_assert(sizeof(PhysCollmap) == 0x58, "PhysCollmap");
static_assert(__builtin_offsetof(PhysCollmap, geoms) == 0x10, "PhysCollmap");
static_assert(__builtin_offsetof(PhysCollmap, mass) == 0x18, "PhysCollmap");
static_assert(__builtin_offsetof(PhysCollmap, bounds) == 0x3C, "PhysCollmap");

void Load_PhysPreset(bool atStreamStart);
void Load_PhysPresetPtr(bool atStreamStart);
void Load_PhysCollmap(bool atStreamStart);
void Load_PhysCollmapPtr(bool atStreamStart);
void Load_PhysPresetAsset(PhysPreset **preset);     // database/db_registry.cpp
void Load_PhysCollmapAsset(PhysCollmap **collmap);  // database/db_registry.cpp

extern PhysPreset *varPhysPreset;
extern PhysPreset **varPhysPresetPtr;
extern PhysCollmap *varPhysCollmap;
extern PhysCollmap **varPhysCollmapPtr;
extern PhysGeomInfo *varPhysGeomInfo;
