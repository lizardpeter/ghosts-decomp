// database/db_misc_assets.h: the small asset types loaded by src/database/db_misc_load_db.cpp (Lua files, the sound
// driver globals, reverb presets, vector fields, leaderboards and compute shaders). Layouts from the PS4 server PDB
// (analysis/iw6_ds_ps4/pdb/types.h); where the PC build differs (the sound driver's reverb settings) the Store
// loader's sizes are used. docs/assets/misc.md describes each type.
#pragma once

#include <stddef.h>

struct LuaFile
{
	const char *name;                    // +0x0
	int len;                             // +0x8
	unsigned char strippingType;         // +0xC
	const unsigned char *buffer;         // +0x10: the chunk, compiled HavokScript
};
static_assert(sizeof(LuaFile) == 0x18, "LuaFile");

// The PC build's reverb settings: 0x5B0 bytes (the PS4's XaReverbSettings is 0x38)
struct XaReverbSettings
{
	unsigned char data[0x5B0];
};

struct SndDriverGlobals
{
	const char *name;                    // +0x0
	float globalVolumeModifier;          // +0x8: SndGlobalSettings_t
	XaReverbSettings *reverbSettings;    // +0x10
};
static_assert(sizeof(SndDriverGlobals) == 0x18, "SndDriverGlobals");

struct ReverbPreset
{
	const char *p_name;                  // +0x0
	float values[16];                    // +0x8: earlyTime .. rearLevel
};
static_assert(sizeof(ReverbPreset) == 0x48, "ReverbPreset");

typedef float vec4_t[4];

struct VectorField
{
	const char *name;                    // +0x0
	vec4_t *linearData;                  // +0x8: numEntries[0] x [1] x [2] cells
	float worldBounds[6];                // +0x10: ExtentBounds
	float ds[3];                         // +0x28
	unsigned int numEntries[3];          // +0x34
	unsigned int flags;                  // +0x40
	int type;                            // +0x44
	unsigned int pad;                    // +0x48
};
static_assert(sizeof(VectorField) == 0x50, "VectorField");
static_assert(offsetof(VectorField, numEntries) == 0x34, "VectorField::numEntries");

struct LbColumnDef
{
	const char *name;                    // +0x0
	int id;                              // +0x8
	int propertyId;                      // +0xC
	bool hidden;                         // +0x10
	int statsGroup;                      // +0x14
	const char *statName;                // +0x18
	int type;                            // +0x20
	int precision;                       // +0x24
	int agg;                             // +0x28
	int uiCalColX;                       // +0x2C
	int uiCalColY;                       // +0x30
};
static_assert(sizeof(LbColumnDef) == 0x38, "LbColumnDef");

struct LeaderboardDef
{
	const char *name;                    // +0x0
	int id;                              // +0x8
	int columnCount;                     // +0xC
	int xpColId;                         // +0x10
	int prestigeColId;                   // +0x14
	LbColumnDef *columns;                // +0x18
	int updateType;                      // +0x20
	int trackTypes;                      // +0x24
};
static_assert(sizeof(LeaderboardDef) == 0x28, "LeaderboardDef");

struct ID3D11ComputeShader;

struct GfxComputeShaderLoadDef
{
	unsigned char *program;              // +0x0
	unsigned int programSize;            // +0x8
};
static_assert(sizeof(GfxComputeShaderLoadDef) == 0x10, "GfxComputeShaderLoadDef");

struct ComputeShaderProgram
{
	ID3D11ComputeShader *cs;             // +0x0: created at load time
	GfxComputeShaderLoadDef loadDef;     // +0x8
};

struct ComputeShader
{
	const char *name;                    // +0x0
	ComputeShaderProgram prog;           // +0x8
};
static_assert(sizeof(ComputeShader) == 0x20, "ComputeShader");

void Load_LuaFile(bool atStreamStart);
void Load_LuaFilePtr(bool atStreamStart);
void Load_SndDriverGlobals(bool atStreamStart);
void Load_SndDriverGlobalsPtr(bool atStreamStart);
void Load_ReverbPreset(bool atStreamStart);
void Load_ReverbPresetPtr(bool atStreamStart);
void Load_VectorField(bool atStreamStart);
void Load_VectorFieldPtr(bool atStreamStart);
void Load_LbColumnDef(bool atStreamStart);
void Load_LeaderboardDef(bool atStreamStart);
void Load_LeaderboardDefPtr(bool atStreamStart);
void Load_GfxComputeShaderLoadDef(bool atStreamStart);
void Load_ComputeShader(bool atStreamStart);
void Load_ComputeShaderPtr(bool atStreamStart);

// ---- vehicle tracks, structured data, equipment sounds, add-on map entities ----------------------------------------

struct VehicleTrackObstacle
{
	float origin[2];
	float radius;
};
static_assert(sizeof(VehicleTrackObstacle) == 0xC, "VehicleTrackObstacle");

struct VehicleTrackSector
{
	float edges[14];                     // +0x0: startEdgeDir .. totalFollowingLength
	VehicleTrackObstacle *obstacles;     // +0x38
	unsigned int obstacleCount;          // +0x40
};
static_assert(sizeof(VehicleTrackSector) == 0x48, "VehicleTrackSector");

struct VehicleTrackSegment
{
	const char *targetName;                       // +0x0
	VehicleTrackSector *sectors;                  // +0x8
	unsigned int sectorCount;                     // +0x10
	const VehicleTrackSegment **nextBranches;     // +0x18
	unsigned int nextBranchesCount;               // +0x20
	const VehicleTrackSegment **prevBranches;     // +0x28
	unsigned int prevBranchesCount;               // +0x30
	float endEdgeDir[2];                          // +0x34
	float endEdgeDist;                            // +0x3C
	float totalLength;                            // +0x40
};
static_assert(sizeof(VehicleTrackSegment) == 0x48, "VehicleTrackSegment");

struct VehicleTrack
{
	const char *name;                    // +0x0
	VehicleTrackSegment *segments;       // +0x8
	unsigned int segmentCount;           // +0x10
};
static_assert(sizeof(VehicleTrack) == 0x18, "VehicleTrack");

enum scr_string_t : int;

struct StructuredDataEnumEntry
{
	scr_string_t string;                 // +0x0
	unsigned short index;                // +0x4
};
static_assert(sizeof(StructuredDataEnumEntry) == 8, "StructuredDataEnumEntry");

struct StructuredDataEnum
{
	int entryCount;                      // +0x0
	int reservedEntryCount;              // +0x4
	StructuredDataEnumEntry *entries;    // +0x8
};
static_assert(sizeof(StructuredDataEnum) == 0x10, "StructuredDataEnum");

struct StructuredDataStructProperty
{
	scr_string_t name;                   // +0x0
	int type[2];                         // +0x4: StructuredDataType
	unsigned int offset;                 // +0xC
	int validation;                      // +0x10
};
static_assert(sizeof(StructuredDataStructProperty) == 0x14, "StructuredDataStructProperty");

struct StructuredDataStruct
{
	int propertyCount;                            // +0x0
	StructuredDataStructProperty *properties;     // +0x8
	int size;                                     // +0x10
	unsigned int bitOffset;                       // +0x14
};
static_assert(sizeof(StructuredDataStruct) == 0x18, "StructuredDataStruct");

struct StructuredDataIndexedArray
{
	int arraySize;                       // +0x0
	int elementType[2];                  // +0x4
	unsigned int elementSize;            // +0xC
};
static_assert(sizeof(StructuredDataIndexedArray) == 0x10, "StructuredDataIndexedArray");

struct StructuredDataEnumedArray
{
	int enumIndex;                       // +0x0
	int elementType[2];                  // +0x4
	unsigned int elementSize;            // +0xC
};
static_assert(sizeof(StructuredDataEnumedArray) == 0x10, "StructuredDataEnumedArray");

struct StructuredDataDef
{
	int version;                                  // +0x0
	unsigned int formatChecksum;                  // +0x4
	int enumCount;                                // +0x8
	StructuredDataEnum *enums;                    // +0x10
	int structCount;                              // +0x18
	StructuredDataStruct *structs;                // +0x20
	int indexedArrayCount;                        // +0x28
	StructuredDataIndexedArray *indexedArrays;    // +0x30
	int enumedArrayCount;                         // +0x38
	StructuredDataEnumedArray *enumedArrays;      // +0x40
	int rootType[2];                              // +0x48
	unsigned int size;                            // +0x50
};
static_assert(sizeof(StructuredDataDef) == 0x58, "StructuredDataDef");

struct StructuredDataDefSet
{
	const char *name;                    // +0x0
	unsigned int defCount;               // +0x8
	StructuredDataDef *defs;             // +0x10
};
static_assert(sizeof(StructuredDataDefSet) == 0x18, "StructuredDataDefSet");

struct snd_alias_list_t;

struct EquipmentSoundSet
{
	snd_alias_list_t *soundPLR;          // +0x0: by name (Load_SndAliasCustom)
	snd_alias_list_t *soundNPC;          // +0x8
};
static_assert(sizeof(EquipmentSoundSet) == 0x10, "EquipmentSoundSet");

struct EquipSoundSetMoveTypes
{
	EquipmentSoundSet *soundSets;        // numMoveTypes
};

struct EquipSoundSetMantleTypes
{
	EquipmentSoundSet soundSets[14];
};
static_assert(sizeof(EquipSoundSetMantleTypes) == 0xE0, "EquipSoundSetMantleTypes");

struct EquipmentSndChance
{
	float rattleChance;
	float accentChance;
	float silentChance;
};
static_assert(sizeof(EquipmentSndChance) == 0xC, "EquipmentSndChance");

struct EquipmentChanceMoveTypes
{
	EquipmentSndChance *chances;         // numMoveTypes
};

struct EquipmentChanceRattleTypes
{
	EquipmentChanceMoveTypes *chances;   // numWeaponRattleTypes
};

struct EquipmentClothData
{
	char *szName;
};

struct EquipmentWeaponRattleData
{
	char *szName;
	float priority;
};
static_assert(sizeof(EquipmentWeaponRattleData) == 0x10, "EquipmentWeaponRattleData");

struct EquipmentSoundTable
{
	const char *szName;                                // +0x0
	unsigned int numClothTypes;                        // +0x8
	unsigned int numWeaponRattleTypes;                 // +0xC
	unsigned int numMoveTypes;                         // +0x10
	EquipmentClothData *clothTypes;                    // +0x18
	EquipmentWeaponRattleData *weaponRattleTypes;      // +0x20
	EquipmentChanceRattleTypes *chancesPLR;            // +0x28
	EquipmentChanceRattleTypes *chancesNPC;            // +0x30
	EquipSoundSetMoveTypes *mvmtClothSoundSets;        // +0x38
	EquipSoundSetMoveTypes *mvmtRattleSoundSets;       // +0x40
	EquipSoundSetMoveTypes mvmtAccentSoundSets;        // +0x48
	EquipSoundSetMantleTypes *mvmtMantleSoundSets;     // +0x50
};
static_assert(sizeof(EquipmentSoundTable) == 0x58, "EquipmentSoundTable");

struct ClipInfo;
struct MapTriggers;

// cmodel_t (0x50): only its ClipInfo pointer (+0x20) needs fixing up
struct cmodel_t
{
	unsigned char bounds[0x20];
	ClipInfo *info;                      // +0x20
	unsigned char rest[0x28];
};
static_assert(sizeof(cmodel_t) == 0x50, "cmodel_t");

struct GfxBrushModel
{
	unsigned char data[0x3C];
};

struct AddonMapEnts
{
	const char *name;                    // +0x0
	char *entityString;                  // +0x8
	int numEntityChars;                  // +0x10
	unsigned long long trigger[6];       // +0x18: MapTriggers
	ClipInfo *info;                      // +0x48
	unsigned int numSubModels;           // +0x50
	cmodel_t *cmodels;                   // +0x58
	GfxBrushModel *models;               // +0x60
};
static_assert(sizeof(AddonMapEnts) == 0x68, "AddonMapEnts");
static_assert(offsetof(AddonMapEnts, trigger) == 0x18, "AddonMapEnts::trigger");

void Load_VehicleTrackSegment(bool atStreamStart);
void Load_VehicleTrackSegment_ptrArray(bool atStreamStart, unsigned long long count);
void Load_VehicleTrackSegmentArray(bool atStreamStart, unsigned long long count);
void Load_VehicleTrack(bool atStreamStart);
void Load_VehicleTrackPtr(bool atStreamStart);
void Load_StructuredDataEnum(bool atStreamStart);
void Load_StructuredDataStruct(bool atStreamStart);
void Load_StructuredDataDefArray(bool atStreamStart, unsigned long long count);
void Load_StructuredDataDefSet(bool atStreamStart);
void Load_StructuredDataDefSetPtr(bool atStreamStart);
void Load_EquipmentSoundSetArray(bool atStreamStart, unsigned long long count);
void Load_EquipSoundSetMoveTypesArray(bool atStreamStart, unsigned long long count);
void Load_EquipmentChanceRattleTypesArray(bool atStreamStart, unsigned long long count);
void Load_EquipmentSoundTable(bool atStreamStart);
void Load_EquipmentSoundTablePtr(bool atStreamStart);
void Load_AddonMapEnts(bool atStreamStart);
void Load_AddonMapEntsPtr(bool atStreamStart);
