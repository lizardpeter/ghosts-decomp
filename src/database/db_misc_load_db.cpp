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

// ==== vehicle tracks, structured data, equipment sounds, add-on map entities ========================================

void Load_VehicleTrackAsset(VehicleTrack **asset);                 // Store 140373DC0
void Load_StructuredDataDefAsset(StructuredDataDefSet **asset);    // Store 140373930
void Load_EquipmentSoundTableAsset(EquipmentSoundTable **asset);   // Store 140371C90
void Load_AddonMapEntsAsset(AddonMapEnts **asset);                 // Store 140371670
void Load_ScriptStringCustom(scr_string_t *str);                   // Store 14037AF90
void Load_SndAliasCustom(snd_alias_list_t **name);                 // Store 1405367A0
void Load_MapTriggers(bool atStreamStart);                         // Store 140352E40
void Load_ClipInfo(bool atStreamStart);                            // Store 14034B360

extern VehicleTrack *varVehicleTrack;                              // Store 1444257E0
extern VehicleTrack **varVehicleTrackPtr;                          // Store 1444257E8
extern VehicleTrackSegment *varVehicleTrackSegment;                // Store 1444257D8
extern const VehicleTrackSegment **varVehicleTrackSegment_ptr;     // Store 1444257D0
extern VehicleTrackSector *varVehicleTrackSector;                  // Store 1444257C8
extern VehicleTrackObstacle *varVehicleTrackObstacle;              // Store 1444257C0
extern StructuredDataDefSet *varStructuredDataDefSet;              // Store 144425F10
extern StructuredDataDefSet **varStructuredDataDefSetPtr;          // Store 144425F18
extern StructuredDataDef *varStructuredDataDef;                    // Store 144425F08
extern StructuredDataEnum *varStructuredDataEnum;                  // Store 144425EC8
extern StructuredDataEnumEntry *varStructuredDataEnumEntry;        // Store 144425EC0
extern StructuredDataStruct *varStructuredDataStruct;              // Store 144425F00
extern StructuredDataStructProperty *varStructuredDataStructProperty;  // Store 144425EF8
extern StructuredDataIndexedArray *varStructuredDataIndexedArray;  // Store 144425EE8
extern StructuredDataEnumedArray *varStructuredDataEnumedArray;    // Store 144425EF0
extern EquipmentSoundTable *varEquipmentSoundTable;                // Store 144425260
extern EquipmentSoundTable **varEquipmentSoundTablePtr;            // Store 144425268
extern EquipmentClothData *varEquipmentClothData;                  // Store 144425228
extern EquipmentWeaponRattleData *varEquipmentWeaponRattleData;    // Store 144425230
extern EquipmentChanceRattleTypes *varEquipmentChanceRattleTypes;  // Store 144425248
extern EquipmentChanceMoveTypes *varEquipmentChanceMoveTypes;      // Store 144425240
extern EquipmentSndChance *varEquipmentSndChance;                  // Store 144425220
extern EquipSoundSetMoveTypes *varEquipSoundSetMoveTypes;          // Store 144425250
extern EquipmentSoundSet *varEquipmentSoundSet;                    // Store 144425238
extern EquipSoundSetMantleTypes *varEquipSoundSetMantleTypes;      // Store 144425258
extern snd_alias_list_t **varsnd_alias_list_name;                  // Store 144426680
extern AddonMapEnts *varAddonMapEnts;                              // Store 144425638
extern AddonMapEnts **varAddonMapEntsPtr;                          // Store 144425640
extern MapTriggers *varMapTriggers;                                // Store 1444255E0
extern ClipInfo *varClipInfo;                                      // Store 1444255A8
extern cmodel_t *varcmodel2_t;                                     // Store 1444255B8
extern GfxBrushModel *varGfxBrushModel;                            // Store 144427108
extern char *varchar;                                              // Store 144424A38

// ---- vehicle tracks -----------------------------------------------------------------------------------------------

// A segment after its own Load_Stream: name, sectors (Load_VehicleTrackSectorArray, inlined), next and previous
// branches. Load_VehicleTrackSegment and Load_VehicleTrackSegmentArray each carry a copy.
static inline void LoadVehicleTrackSegmentBody()
{
	LoadXString(&varVehicleTrackSegment->targetName);
	if (varVehicleTrackSegment->sectors)
	{
		varVehicleTrackSegment->sectors = (VehicleTrackSector *)AlignStreamPos(3);
		varVehicleTrackSector = (VehicleTrackSector *)g_streamPos;
		unsigned long long count = varVehicleTrackSegment->sectorCount;
		Load_Stream(true, g_streamPos, count * sizeof(VehicleTrackSector));
		VehicleTrackSector *sector = varVehicleTrackSector;
		for (; count; --count)
		{
			varVehicleTrackSector = sector;
			Load_Stream(false, sector, sizeof(VehicleTrackSector));
			if (varVehicleTrackSector->obstacles)
			{
				varVehicleTrackSector->obstacles = (VehicleTrackObstacle *)AlignStreamPos(3);
				varVehicleTrackObstacle = (VehicleTrackObstacle *)g_streamPos;
				Load_Stream(true, g_streamPos,
				            (unsigned long long)varVehicleTrackSector->obstacleCount * sizeof(VehicleTrackObstacle));
			}
			++sector;
		}
	}
	if (varVehicleTrackSegment->nextBranches)
	{
		varVehicleTrackSegment->nextBranches = (const VehicleTrackSegment **)AlignStreamPos(7);
		varVehicleTrackSegment_ptr = (const VehicleTrackSegment **)g_streamPos;
		Load_VehicleTrackSegment_ptrArray(true, varVehicleTrackSegment->nextBranchesCount);
	}
	if (varVehicleTrackSegment->prevBranches)
	{
		varVehicleTrackSegment->prevBranches = (const VehicleTrackSegment **)AlignStreamPos(7);
		varVehicleTrackSegment_ptr = (const VehicleTrackSegment **)g_streamPos;
		Load_VehicleTrackSegment_ptrArray(true, varVehicleTrackSegment->prevBranchesCount);
	}
}

// Store 140359520
void Load_VehicleTrackSegment(bool atStreamStart)
{
	Load_Stream(atStreamStart, varVehicleTrackSegment, sizeof(VehicleTrackSegment));
	LoadVehicleTrackSegmentBody();
}

// Store 140359970: each branch is -1 (the segment follows, aligned 4) or an offset
void Load_VehicleTrackSegment_ptrArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varVehicleTrackSegment_ptr, count * sizeof(VehicleTrackSegment *));
	const VehicleTrackSegment **slot = varVehicleTrackSegment_ptr;
	for (; count; --count)
	{
		varVehicleTrackSegment_ptr = slot;
		Load_Stream(false, slot, sizeof(VehicleTrackSegment *));
		if (*varVehicleTrackSegment_ptr)
		{
			if ((unsigned long long)*varVehicleTrackSegment_ptr == DB_PTR_FOLLOWING)
			{
				*varVehicleTrackSegment_ptr = (VehicleTrackSegment *)AlignStreamPos(3);
				varVehicleTrackSegment = (VehicleTrackSegment *)g_streamPos;
				Load_VehicleTrackSegment(true);
			}
			else
			{
				DB_ConvertOffsetToPointer((unsigned long long *)varVehicleTrackSegment_ptr);
			}
		}
		++slot;
	}
}

// Store 140359720
void Load_VehicleTrackSegmentArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varVehicleTrackSegment, count * sizeof(VehicleTrackSegment));
	VehicleTrackSegment *segment = varVehicleTrackSegment;
	for (; count; --count)
	{
		varVehicleTrackSegment = segment;
		Load_Stream(false, segment, sizeof(VehicleTrackSegment));
		LoadVehicleTrackSegmentBody();
		++segment;
	}
}

// Store 140359340
void Load_VehicleTrack(bool atStreamStart)
{
	Load_Stream(atStreamStart, varVehicleTrack, sizeof(VehicleTrack));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varVehicleTrack->name);
	if (varVehicleTrack->segments)
	{
		if ((unsigned long long)varVehicleTrack->segments == DB_PTR_FOLLOWING)
		{
			varVehicleTrack->segments = (VehicleTrackSegment *)AlignStreamPos(3);
			varVehicleTrackSegment = (VehicleTrackSegment *)g_streamPos;
			Load_VehicleTrackSegmentArray(true, varVehicleTrack->segmentCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varVehicleTrack->segments);
		}
	}
	DB_PopStreamPos();
}

// Store 140359430
LOAD_ASSET_PTR(VehicleTrack, 3)

// ---- structured data ----------------------------------------------------------------------------------------------

// Store 140357FC0: one enum, its entries' names script strings
void Load_StructuredDataEnum(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStructuredDataEnum, sizeof(StructuredDataEnum));
	if (!varStructuredDataEnum->entries)
		return;
	varStructuredDataEnum->entries = (StructuredDataEnumEntry *)AlignStreamPos(3);
	varStructuredDataEnumEntry = (StructuredDataEnumEntry *)g_streamPos;
	long long count = varStructuredDataEnum->entryCount;
	Load_Stream(true, g_streamPos, count * sizeof(StructuredDataEnumEntry));
	StructuredDataEnumEntry *entry = varStructuredDataEnumEntry;
	for (; count; --count)
	{
		varStructuredDataEnumEntry = entry;
		Load_Stream(false, entry, sizeof(StructuredDataEnumEntry));
		varscr_string_t = &varStructuredDataEnumEntry->string;
		Load_Stream(false, varscr_string_t, sizeof(scr_string_t));
		Load_ScriptStringCustom(varscr_string_t);
		++entry;
	}
}

// Store 1403580A0: one struct, its properties' names script strings
void Load_StructuredDataStruct(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStructuredDataStruct, sizeof(StructuredDataStruct));
	if (!varStructuredDataStruct->properties)
		return;
	varStructuredDataStruct->properties = (StructuredDataStructProperty *)AlignStreamPos(3);
	varStructuredDataStructProperty = (StructuredDataStructProperty *)g_streamPos;
	long long count = varStructuredDataStruct->propertyCount;
	Load_Stream(true, g_streamPos, count * sizeof(StructuredDataStructProperty));
	StructuredDataStructProperty *property = varStructuredDataStructProperty;
	for (; count; --count)
	{
		varStructuredDataStructProperty = property;
		Load_Stream(false, property, sizeof(StructuredDataStructProperty));
		varscr_string_t = &varStructuredDataStructProperty->name;
		Load_Stream(false, varscr_string_t, sizeof(scr_string_t));
		Load_ScriptStringCustom(varscr_string_t);
		++property;
	}
}

// Store 140357BF0: the enum and struct arrays are inlined, their elements not
void Load_StructuredDataDefArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varStructuredDataDef, count * sizeof(StructuredDataDef));
	StructuredDataDef *def = varStructuredDataDef;
	for (; count; --count)
	{
		varStructuredDataDef = def;
		Load_Stream(false, def, sizeof(StructuredDataDef));
		if (varStructuredDataDef->enums)
		{
			varStructuredDataDef->enums = (StructuredDataEnum *)AlignStreamPos(3);
			varStructuredDataEnum = (StructuredDataEnum *)g_streamPos;
			long long n = varStructuredDataDef->enumCount;
			Load_Stream(true, g_streamPos, n * sizeof(StructuredDataEnum));
			StructuredDataEnum *e = varStructuredDataEnum;
			for (; n; --n)
			{
				varStructuredDataEnum = e;
				Load_StructuredDataEnum(false);
				++e;
			}
		}
		if (varStructuredDataDef->structs)
		{
			varStructuredDataDef->structs = (StructuredDataStruct *)AlignStreamPos(3);
			varStructuredDataStruct = (StructuredDataStruct *)g_streamPos;
			long long n = varStructuredDataDef->structCount;
			Load_Stream(true, g_streamPos, n * sizeof(StructuredDataStruct));
			StructuredDataStruct *s = varStructuredDataStruct;
			for (; n; --n)
			{
				varStructuredDataStruct = s;
				Load_StructuredDataStruct(false);
				++s;
			}
		}
		if (varStructuredDataDef->indexedArrays)
		{
			varStructuredDataDef->indexedArrays = (StructuredDataIndexedArray *)AlignStreamPos(3);
			varStructuredDataIndexedArray = (StructuredDataIndexedArray *)g_streamPos;
			Load_Stream(true, g_streamPos,
			            (long long)varStructuredDataDef->indexedArrayCount * sizeof(StructuredDataIndexedArray));
		}
		if (varStructuredDataDef->enumedArrays)
		{
			varStructuredDataDef->enumedArrays = (StructuredDataEnumedArray *)AlignStreamPos(3);
			varStructuredDataEnumedArray = (StructuredDataEnumedArray *)g_streamPos;
			Load_Stream(true, g_streamPos,
			            (long long)varStructuredDataDef->enumedArrayCount * sizeof(StructuredDataEnumedArray));
		}
		++def;
	}
}

// Store 140357E00
void Load_StructuredDataDefSet(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStructuredDataDefSet, sizeof(StructuredDataDefSet));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varStructuredDataDefSet->name);
	if (varStructuredDataDefSet->defs)
	{
		varStructuredDataDefSet->defs = (StructuredDataDef *)AlignStreamPos(3);
		varStructuredDataDef = (StructuredDataDef *)g_streamPos;
		Load_StructuredDataDefArray(true, varStructuredDataDefSet->defCount);
	}
	DB_PopStreamPos();
}

// Store 140357ED0 (the asset linker is Load_StructuredDataDefAsset)
void Load_StructuredDataDefSetPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStructuredDataDefSetPtr, sizeof(StructuredDataDefSet *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	StructuredDataDefSet **ptr = varStructuredDataDefSetPtr;
	unsigned long long value = (unsigned long long)*varStructuredDataDefSetPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varStructuredDataDefSetPtr);
			DB_PopStreamPos();
			return;
		}
		*varStructuredDataDefSetPtr = (StructuredDataDefSet *)AlignStreamPos(3);
		varStructuredDataDefSet = (StructuredDataDefSet *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_StructuredDataDefSet(true);
		Load_StructuredDataDefAsset(ptr);
		if (inserted)
			*(StructuredDataDefSet **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// ---- equipment sounds ---------------------------------------------------------------------------------------------

static inline void LoadEquipmentSoundSet(EquipmentSoundSet *set)
{
	varEquipmentSoundSet = set;
	Load_Stream(false, set, sizeof(EquipmentSoundSet));
	varsnd_alias_list_name = &varEquipmentSoundSet->soundPLR;
	Load_Stream(false, varEquipmentSoundSet, 8);
	Load_SndAliasCustom(varsnd_alias_list_name);
	varsnd_alias_list_name = &varEquipmentSoundSet->soundNPC;
	Load_Stream(false, varsnd_alias_list_name, 8);
	Load_SndAliasCustom(varsnd_alias_list_name);
}

// Store 14034C5C0
void Load_EquipmentSoundSetArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varEquipmentSoundSet, count * sizeof(EquipmentSoundSet));
	EquipmentSoundSet *set = varEquipmentSoundSet;
	for (; count; --count)
		LoadEquipmentSoundSet(set++);
}

// Store 14034C3B0
void Load_EquipSoundSetMoveTypesArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varEquipSoundSetMoveTypes, count * sizeof(EquipSoundSetMoveTypes));
	EquipSoundSetMoveTypes *types = varEquipSoundSetMoveTypes;
	for (; count; --count)
	{
		varEquipSoundSetMoveTypes = types;
		Load_Stream(false, types, sizeof(EquipSoundSetMoveTypes));
		if (varEquipSoundSetMoveTypes->soundSets)
		{
			varEquipSoundSetMoveTypes->soundSets = (EquipmentSoundSet *)AlignStreamPos(3);
			varEquipmentSoundSet = (EquipmentSoundSet *)g_streamPos;
			Load_EquipmentSoundSetArray(true, varEquipmentSoundTable->numMoveTypes);
		}
		++types;
	}
}

// Store 14034C460 (Load_EquipmentChanceMoveTypesArray inlined)
void Load_EquipmentChanceRattleTypesArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varEquipmentChanceRattleTypes, count * sizeof(EquipmentChanceRattleTypes));
	EquipmentChanceRattleTypes *rattle = varEquipmentChanceRattleTypes;
	for (; count; --count)
	{
		varEquipmentChanceRattleTypes = rattle;
		Load_Stream(false, rattle, sizeof(EquipmentChanceRattleTypes));
		if (varEquipmentChanceRattleTypes->chances)
		{
			varEquipmentChanceRattleTypes->chances = (EquipmentChanceMoveTypes *)AlignStreamPos(3);
			varEquipmentChanceMoveTypes = (EquipmentChanceMoveTypes *)g_streamPos;
			unsigned long long n = varEquipmentSoundTable->numWeaponRattleTypes;
			Load_Stream(true, g_streamPos, n * sizeof(EquipmentChanceMoveTypes));
			EquipmentChanceMoveTypes *move = varEquipmentChanceMoveTypes;
			for (; n; --n)
			{
				varEquipmentChanceMoveTypes = move;
				Load_Stream(false, move, sizeof(EquipmentChanceMoveTypes));
				if (varEquipmentChanceMoveTypes->chances)
				{
					varEquipmentChanceMoveTypes->chances = (EquipmentSndChance *)AlignStreamPos(3);
					varEquipmentSndChance = (EquipmentSndChance *)g_streamPos;
					Load_Stream(true, g_streamPos,
					            (unsigned long long)varEquipmentSoundTable->numMoveTypes * sizeof(EquipmentSndChance));
				}
				++move;
			}
		}
		++rattle;
	}
}

// Store 14034C670
void Load_EquipmentSoundTable(bool atStreamStart)
{
	Load_Stream(atStreamStart, varEquipmentSoundTable, sizeof(EquipmentSoundTable));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varEquipmentSoundTable->szName);
	if (varEquipmentSoundTable->clothTypes)
	{
		varEquipmentSoundTable->clothTypes = (EquipmentClothData *)AlignStreamPos(3);
		varEquipmentClothData = (EquipmentClothData *)g_streamPos;
		unsigned long long n = varEquipmentSoundTable->numClothTypes;
		Load_Stream(true, g_streamPos, n * sizeof(EquipmentClothData));
		EquipmentClothData *cloth = varEquipmentClothData;
		for (; n; --n)
		{
			varEquipmentClothData = cloth;
			Load_Stream(false, cloth, sizeof(EquipmentClothData));
			LoadXString((const char **)&varEquipmentClothData->szName);
			++cloth;
		}
	}
	if (varEquipmentSoundTable->weaponRattleTypes)
	{
		varEquipmentSoundTable->weaponRattleTypes = (EquipmentWeaponRattleData *)AlignStreamPos(3);
		varEquipmentWeaponRattleData = (EquipmentWeaponRattleData *)g_streamPos;
		unsigned long long n = varEquipmentSoundTable->numWeaponRattleTypes;
		Load_Stream(true, g_streamPos, n * sizeof(EquipmentWeaponRattleData));
		EquipmentWeaponRattleData *rattle = varEquipmentWeaponRattleData;
		for (; n; --n)
		{
			varEquipmentWeaponRattleData = rattle;
			Load_Stream(false, rattle, sizeof(EquipmentWeaponRattleData));
			LoadXString((const char **)&varEquipmentWeaponRattleData->szName);
			++rattle;
		}
	}
	if (varEquipmentSoundTable->chancesPLR)
	{
		varEquipmentSoundTable->chancesPLR = (EquipmentChanceRattleTypes *)AlignStreamPos(3);
		varEquipmentChanceRattleTypes = (EquipmentChanceRattleTypes *)g_streamPos;
		Load_EquipmentChanceRattleTypesArray(true, varEquipmentSoundTable->numClothTypes);
	}
	if (varEquipmentSoundTable->chancesNPC)
	{
		varEquipmentSoundTable->chancesNPC = (EquipmentChanceRattleTypes *)AlignStreamPos(3);
		varEquipmentChanceRattleTypes = (EquipmentChanceRattleTypes *)g_streamPos;
		Load_EquipmentChanceRattleTypesArray(true, varEquipmentSoundTable->numClothTypes);
	}
	if (varEquipmentSoundTable->mvmtClothSoundSets)
	{
		varEquipmentSoundTable->mvmtClothSoundSets = (EquipSoundSetMoveTypes *)AlignStreamPos(3);
		varEquipSoundSetMoveTypes = (EquipSoundSetMoveTypes *)g_streamPos;
		Load_EquipSoundSetMoveTypesArray(true, varEquipmentSoundTable->numClothTypes);
	}
	if (varEquipmentSoundTable->mvmtRattleSoundSets)
	{
		varEquipmentSoundTable->mvmtRattleSoundSets = (EquipSoundSetMoveTypes *)AlignStreamPos(3);
		varEquipSoundSetMoveTypes = (EquipSoundSetMoveTypes *)g_streamPos;
		Load_EquipSoundSetMoveTypesArray(true, varEquipmentSoundTable->numWeaponRattleTypes);
	}
	varEquipSoundSetMoveTypes = &varEquipmentSoundTable->mvmtAccentSoundSets;
	Load_Stream(false, varEquipSoundSetMoveTypes, sizeof(EquipSoundSetMoveTypes));
	if (varEquipSoundSetMoveTypes->soundSets)
	{
		varEquipSoundSetMoveTypes->soundSets = (EquipmentSoundSet *)AlignStreamPos(3);
		varEquipmentSoundSet = (EquipmentSoundSet *)g_streamPos;
		Load_EquipmentSoundSetArray(true, varEquipmentSoundTable->numMoveTypes);
	}
	if (varEquipmentSoundTable->mvmtMantleSoundSets)
	{
		varEquipmentSoundTable->mvmtMantleSoundSets = (EquipSoundSetMantleTypes *)AlignStreamPos(3);
		varEquipSoundSetMantleTypes = (EquipSoundSetMantleTypes *)g_streamPos;
		unsigned long long n = varEquipmentSoundTable->numClothTypes;
		Load_Stream(true, g_streamPos, n * sizeof(EquipSoundSetMantleTypes));
		EquipSoundSetMantleTypes *mantle = varEquipSoundSetMantleTypes;
		for (; n; --n)   // Load_EquipSoundSetMantleTypesArray, inlined with its 14 sound sets
		{
			varEquipSoundSetMantleTypes = mantle;
			Load_Stream(false, mantle, sizeof(EquipSoundSetMantleTypes));
			varEquipmentSoundSet = varEquipSoundSetMantleTypes->soundSets;
			Load_Stream(false, varEquipmentSoundSet, sizeof(EquipSoundSetMantleTypes));
			EquipmentSoundSet *set = varEquipmentSoundSet;
			for (int i = 14; i; --i)
				LoadEquipmentSoundSet(set++);
			++mantle;
		}
	}
	DB_PopStreamPos();
}

// Store 14034CB70
LOAD_ASSET_PTR(EquipmentSoundTable, 3)

// ---- add-on map entities ------------------------------------------------------------------------------------------

// Store 14034A100
void Load_AddonMapEnts(bool atStreamStart)
{
	Load_Stream(atStreamStart, varAddonMapEnts, sizeof(AddonMapEnts));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varAddonMapEnts->name);
	if (varAddonMapEnts->entityString)
	{
		varAddonMapEnts->entityString = (char *)g_streamPos;    // not aligned
		varchar = (char *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varAddonMapEnts->numEntityChars);
	}
	varMapTriggers = (MapTriggers *)varAddonMapEnts->trigger;
	Load_MapTriggers(false);
	if (varAddonMapEnts->info)
	{
		if ((unsigned long long)varAddonMapEnts->info == DB_PTR_FOLLOWING)
		{
			varAddonMapEnts->info = (ClipInfo *)AlignStreamPos(3);
			varClipInfo = (ClipInfo *)g_streamPos;
			Load_ClipInfo(true);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varAddonMapEnts->info);
		}
	}
	if (varAddonMapEnts->cmodels)
	{
		varAddonMapEnts->cmodels = (cmodel_t *)AlignStreamPos(3);
		varcmodel2_t = (cmodel_t *)g_streamPos;
		unsigned long long n = varAddonMapEnts->numSubModels;
		Load_Stream(true, g_streamPos, n * sizeof(cmodel_t));
		cmodel_t *model = varcmodel2_t;
		for (; n; --n)   // Load_cmodel2_tArray, inlined
		{
			varcmodel2_t = model;
			Load_Stream(false, model, sizeof(cmodel_t));
			if (varcmodel2_t->info)
			{
				if ((unsigned long long)varcmodel2_t->info == DB_PTR_FOLLOWING)
				{
					varcmodel2_t->info = (ClipInfo *)AlignStreamPos(3);
					varClipInfo = (ClipInfo *)g_streamPos;
					Load_ClipInfo(true);
				}
				else
				{
					DB_ConvertOffsetToPointer((unsigned long long *)&varcmodel2_t->info);
				}
			}
			++model;
		}
	}
	if (varAddonMapEnts->models)
	{
		varAddonMapEnts->models = (GfxBrushModel *)AlignStreamPos(3);
		varGfxBrushModel = (GfxBrushModel *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varAddonMapEnts->numSubModels * sizeof(GfxBrushModel));
	}
	DB_PopStreamPos();
}

// Store 14034A370
LOAD_ASSET_PTR(AddonMapEnts, 3)
