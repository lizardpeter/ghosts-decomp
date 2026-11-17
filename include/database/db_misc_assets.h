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
