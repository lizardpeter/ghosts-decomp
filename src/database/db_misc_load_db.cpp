// database/db_misc_load_db.cpp (Store build): the zone loaders of Lua files (0x36), the sound driver globals (0x24),
// reverb presets (0x35), vector fields (0x3C), leaderboards (0x2F) and compute shaders (0x06). Generated loader code
// (the servers' PDB places it in gfx_d3d/r_material_load_db.h), tagged with Store addresses; the names and var
// globals are the Xbox One server's. tools/fastfile/misc_assets.py is the same in Python, checked against the game on
// real zones (docs/assets/misc.md); tests/differential/test_misc_load.py checks this file against the exe.

#include "database/db_misc_assets.h"
#include "database/db_stream_api.h"

// database/db_registry.cpp: register a loaded asset (DB_LinkXAssetEntry)
void Load_LuaFileAsset(LuaFile **asset);                           // Store 140372780
void Load_SndDriverGlobalsAsset(SndDriverGlobals **asset);         // Store 1403737B0
void Load_ReverbPresetAsset(ReverbPreset **asset);                 // Store 1403734B0
void Load_VectorFieldAsset(VectorField **asset);                   // Store 140373C40
void Load_LeaderboardDefAsset(LeaderboardDef **asset);             // Store 1403723C0
void Load_ComputeShaderAsset(ComputeShader **asset);               // Store 140371B10
// gfx_d3d: creates the D3D11 compute shader from the loaded program
void Load_CreateComputeShader(unsigned char **program, ComputeShader *shader);  // Store 14063AC20

extern unsigned char *varraw_byte16;                               // Store 144424C38
extern unsigned char *varbyte4;                                    // Store 144424B18
extern vec4_t *varvec4_t;                                          // Store 144424C98
extern LuaFile *varLuaFile;                                        // Store 1444253B0
extern LuaFile **varLuaFilePtr;                                    // Store 1444253B8
extern SndDriverGlobals *varSndDriverGlobals;                      // Store 1444264D0
extern SndDriverGlobals **varSndDriverGlobalsPtr;                  // Store 1444264D8
extern XaReverbSettings *varXaReverbSettings;                      // Store 1444264C0
extern ReverbPreset *varReverbPreset;                              // Store 1444252F0
extern ReverbPreset **varReverbPresetPtr;                          // Store 1444252F8
extern VectorField *varVectorField;                                // Store 144425798
extern VectorField **varVectorFieldPtr;                            // Store 1444257A0
extern LeaderboardDef *varLeaderboardDef;                          // Store 144426460
extern LeaderboardDef **varLeaderboardDefPtr;                      // Store 144426468
extern LbColumnDef *varLbColumnDef;                                // Store 144426458
extern ComputeShader *varComputeShader;                            // Store 144425C28
extern ComputeShader **varComputeShaderPtr;                        // Store 144425C30
extern ComputeShaderProgram *varComputeShaderProgram;              // Store 144425BF0
extern GfxComputeShaderLoadDef *varGfxComputeShaderLoadDef;        // Store 144425BD0

static inline unsigned char *AlignStreamPos(unsigned long long mask)
{
	g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + mask) & ~mask);
	return g_streamPos;
}

// An XString field (varXString), as every loader here inlines it
static inline void LoadXString(const char **field)
{
	varXString = field;
	Load_Stream(false, field, 8);
	if (!*varXString)
		return;
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

// The generated Load_<T>Ptr: in the temp block, null stays null, an offset is an alias, -1 and -2 mean the asset
// follows (aligned), -2 also reserving an alias slot that receives the linked header.
#define LOAD_ASSET_PTR(T, alignMask)                                                    \
	void Load_##T##Ptr(bool atStreamStart)                                              \
	{                                                                                   \
		Load_Stream(atStreamStart, var##T##Ptr, sizeof(T *));                           \
		DB_PushStreamPos(XFILE_BLOCK_TEMP);                                             \
		T **ptr = var##T##Ptr;                                                          \
		unsigned long long value = (unsigned long long)*var##T##Ptr;                    \
		if (value)                                                                      \
		{                                                                               \
			if (!DB_PTR_IS_INLINE(value))                                               \
			{                                                                           \
				DB_ConvertOffsetToAlias((unsigned long long *)var##T##Ptr);             \
				DB_PopStreamPos();                                                      \
				return;                                                                 \
			}                                                                           \
			*var##T##Ptr = (T *)AlignStreamPos(alignMask);                              \
			var##T = (T *)g_streamPos;                                                  \
			unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr; \
			Load_##T(true);                                                             \
			Load_##T##Asset(ptr);                                                       \
			if (inserted)                                                               \
				*(T **)inserted = *ptr;                                                 \
		}                                                                               \
		DB_PopStreamPos();                                                              \
	}

// ---- Lua files ----------------------------------------------------------------------------------------------------

// Store 140352A50
void Load_LuaFile(bool atStreamStart)
{
	Load_Stream(atStreamStart, varLuaFile, sizeof(LuaFile));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varLuaFile->name);
	if (varLuaFile->buffer)
	{
		varLuaFile->buffer = AlignStreamPos(15);
		varraw_byte16 = g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varLuaFile->len);
	}
	DB_PopStreamPos();
}

// Store 140352B20
LOAD_ASSET_PTR(LuaFile, 3)

// ---- sound driver globals and reverb presets ------------------------------------------------------------------------

// Store 140356EC0
void Load_SndDriverGlobals(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSndDriverGlobals, sizeof(SndDriverGlobals));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varSndDriverGlobals->name);
	if (varSndDriverGlobals->reverbSettings)
	{
		varSndDriverGlobals->reverbSettings = (XaReverbSettings *)AlignStreamPos(3);
		varXaReverbSettings = (XaReverbSettings *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(XaReverbSettings));
	}
	DB_PopStreamPos();
}

// Store 140356F90
LOAD_ASSET_PTR(SndDriverGlobals, 3)

// Store 140355A90
void Load_ReverbPreset(bool atStreamStart)
{
	Load_Stream(atStreamStart, varReverbPreset, sizeof(ReverbPreset));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varReverbPreset->p_name);
	DB_PopStreamPos();
}

// Store 140355B20
LOAD_ASSET_PTR(ReverbPreset, 3)

// ---- vector fields ------------------------------------------------------------------------------------------------

// Store 140358770
void Load_VectorField(bool atStreamStart)
{
	Load_Stream(atStreamStart, varVectorField, sizeof(VectorField));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varVectorField->name);
	if (varVectorField->linearData)
	{
		if ((unsigned long long)varVectorField->linearData == DB_PTR_FOLLOWING)
		{
			varVectorField->linearData = (vec4_t *)AlignStreamPos(3);
			varvec4_t = (vec4_t *)g_streamPos;
			unsigned int cells = varVectorField->numEntries[2] * varVectorField->numEntries[1] *
			                     varVectorField->numEntries[0];
			Load_Stream(true, g_streamPos, (unsigned long long)cells << 4);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varVectorField->linearData);
		}
	}
	DB_PopStreamPos();
}

// Store 140358870: the only one of these aligned to 16
LOAD_ASSET_PTR(VectorField, 15)

// ---- leaderboards -------------------------------------------------------------------------------------------------

// Store 140352280
void Load_LbColumnDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varLbColumnDef, sizeof(LbColumnDef));
	LoadXString(&varLbColumnDef->name);
	LoadXString(&varLbColumnDef->statName);
}

// Store 140352360
void Load_LeaderboardDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varLeaderboardDef, sizeof(LeaderboardDef));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varLeaderboardDef->name);
	if (varLeaderboardDef->columns)
	{
		varLeaderboardDef->columns = (LbColumnDef *)AlignStreamPos(3);
		varLbColumnDef = (LbColumnDef *)g_streamPos;
		long long count = varLeaderboardDef->columnCount;
		Load_Stream(true, g_streamPos, count * sizeof(LbColumnDef));
		LbColumnDef *column = varLbColumnDef;    // Load_LbColumnDefArray, inlined
		for (; count; --count)
		{
			varLbColumnDef = column;
			Load_LbColumnDef(false);
			++column;
		}
	}
	DB_PopStreamPos();
}

// Store 140352470
LOAD_ASSET_PTR(LeaderboardDef, 3)

// ---- compute shaders ----------------------------------------------------------------------------------------------

// Store 14034EF40
void Load_GfxComputeShaderLoadDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxComputeShaderLoadDef, sizeof(GfxComputeShaderLoadDef));
	GfxComputeShaderLoadDef *loadDef = varGfxComputeShaderLoadDef;
	if (!loadDef->program)
		return;
	if ((unsigned long long)loadDef->program == DB_PTR_FOLLOWING)
	{
		loadDef->program = AlignStreamPos(3);
		varbyte4 = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxComputeShaderLoadDef->programSize);  // zero-extended, unlike the material shaders' (int)
		Load_CreateComputeShader(&loadDef->program, varComputeShader);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxComputeShaderLoadDef);
}

// Store 14034BE80
void Load_ComputeShader(bool atStreamStart)
{
	Load_Stream(atStreamStart, varComputeShader, sizeof(ComputeShader));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varComputeShader->name);
	varComputeShaderProgram = &varComputeShader->prog;
	Load_Stream(false, varComputeShaderProgram, sizeof(ComputeShaderProgram));
	varGfxComputeShaderLoadDef = &varComputeShaderProgram->loadDef;
	Load_GfxComputeShaderLoadDef(false);
	DB_PopStreamPos();
}

// Store 14034BF40
LOAD_ASSET_PTR(ComputeShader, 3)
