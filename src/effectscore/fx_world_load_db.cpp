// effectscore/fx_world_load_db.cpp (Store build): the zone loaders of a map's glass (GlassWorld, FxWorld) and of the
// effect tables (FxImpactTable, SurfaceFxTable), with the effect handle array they share.
//
// Generated loader functions (database/db_load.cpp includes them; the servers' PDB places them in
// gfx_d3d/r_material_load_db.h). The code is the Store build's, tagged with Store addresses; where the Store build
// gives an array's element its own function (G_GlassName, FxGlassDef) the server inlines it, and the reverse.
// tools/fastfile/mapfx.py is the same logic in Python, checked against the game on real zones
// (docs/assets/map_assets.md).

#include "effectscore/fx_world.h"
#include "effectscore/fx_types.h"

void Load_MaterialHandle(bool atStreamStart);                         // Store 140353700
void Load_PhysPresetPtr(bool atStreamStart);                          // Store 1403555F0
void Load_FxEffectDef(bool atStreamStart);                            // Store 14034D040
void Load_FxEffectDefHandle(bool atStreamStart);                      // Store 14034D120
void Load_FxEffectDefAsset(FxEffectDef **effectDef);                  // Store 140371E10
void Load_SndAliasCustom(snd_alias_list_t **var);                     // Store 1405367A0
void Load_ScriptStringCustom(scr_string_t *var);                      // Store 14037AF90
void Load_GlassWorldAsset(GlassWorld **glassWorld);                   // Store 1403722F0
void Load_FxWorldAsset(FxWorld **fxWorld);                            // Store 140372080
void Load_FxImpactTableAsset(FxImpactTable **table);                  // Store 140371F00
void Load_SurfaceFxTableAsset(SurfaceFxTable **table);                // Store 140373A00

extern const FxEffectDef **varFxEffectDefHandle;                     // Store 1444260F8
extern FxEffectDef *varFxEffectDef;                                  // Store 1444261A8
extern Material **varMaterialHandle;                                 // Store 144425D20
extern PhysPreset **varPhysPresetPtr;                                // Store 144426758
extern snd_alias_list_t **varsnd_alias_list_name;                    // Store 144426680
extern GlassWorld **varGlassWorldPtr;                                // Store 144425B90
extern GlassWorld *varGlassWorld;                                    // Store 144425B88
extern G_GlassData *varG_GlassData;                                  // Store 144425AB0
extern G_GlassPiece *varG_GlassPiece;                                // Store 144425AA0
extern G_GlassName *varG_GlassName;                                  // Store 144425AA8
extern unsigned short *varushort;                                    // Store 144424D18
extern FxWorld **varFxWorldPtr;                                      // Store 144426DC0
extern FxWorld *varFxWorld;                                          // Store 144426DB8
extern FxGlassSystem *varFxGlassSystem;                              // Store 144426CE8
extern FxGlassDef *varFxGlassDef;                                    // Store 144426CB8
extern FxGlassPiecePlace *varFxGlassPiecePlace;                      // Store 144426CC8
extern FxGlassPieceState *varFxGlassPieceState;                      // Store 144426CD0
extern FxGlassPieceDynamics *varFxGlassPieceDynamics;                // Store 144426CE0
extern FxGlassGeometryData *varFxGlassGeometryData;                  // Store 144426CB0
extern unsigned int *varraw_uint;                                    // Store 144424BF8
extern unsigned char *varraw_byte16;                                 // Store 144424C38
extern float (*varraw_vec3_t)[3];                                    // Store 144424BD8
extern float *varraw_float16;                                        // Store 144424BC8
extern unsigned short *varuint16_t;                                  // Store 144424D48
extern FxGlassInitPieceState *varFxGlassInitPieceState;              // Store 144426CD8
extern FxGlassGeometryData *varraw_FxGlassGeometryData;              // Store 144426CA8
extern FxImpactTable **varFxImpactTablePtr;                          // Store 144425AE0
extern FxImpactTable *varFxImpactTable;                              // Store 144425AD8
extern FxImpactEntry *varFxImpactEntry;                              // Store 144425AD0
extern SurfaceFxTable **varSurfaceFxTablePtr;                        // Store 144425AF8
extern SurfaceFxTable *varSurfaceFxTable;                            // Store 144425AF0
extern SurfaceFxEntry *varSurfaceFxEntry;                            // Store 144425AE8

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

static inline void LoadXStringField()
{
	if (*varXString)
	{
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
}

// ---- effect handle arrays ---------------------------------------------------------------------------------------

// Store 14034D210
// Each handle by the asset pointer rule (Load_FxEffectDefHandle's body, inline).
void Load_FxEffectDefHandleArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varFxEffectDefHandle, count * sizeof(FxEffectDef *));
	const FxEffectDef **handles = varFxEffectDefHandle;
	for (; count; count--, handles++)
	{
		varFxEffectDefHandle = handles;
		Load_Stream(false, handles, sizeof(FxEffectDef *));
		DB_PushStreamPos(XFILE_BLOCK_TEMP);
		FxEffectDef **handle = (FxEffectDef **)varFxEffectDefHandle;
		unsigned long long value = (unsigned long long)*varFxEffectDefHandle;
		if (value)
		{
			if (DB_PTR_IS_INLINE(value))
			{
				ALIGN_POS(4);
				*varFxEffectDefHandle = (FxEffectDef *)g_streamPos;
				varFxEffectDef = (FxEffectDef *)g_streamPos;
				unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
				Load_FxEffectDef(true);
				Load_FxEffectDefAsset(handle);
				if (inserted)
					*(FxEffectDef **)inserted = *handle;
			}
			else
			{
				DB_ConvertOffsetToAlias((unsigned long long *)varFxEffectDefHandle);
			}
		}
		DB_PopStreamPos();
	}
}

// ---- GlassWorld ---------------------------------------------------------------------------------------------------

// Store 14034EBA0
void Load_G_GlassName(bool atStreamStart)
{
	Load_Stream(atStreamStart, varG_GlassName, sizeof(G_GlassName));
	varXString = (const char **)&varG_GlassName->nameStr;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	varscr_string_t = &varG_GlassName->name;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	if (varG_GlassName->pieceIndices)
	{
		ALIGN_POS(2);
		varG_GlassName->pieceIndices = (unsigned short *)g_streamPos;
		varushort = (unsigned short *)g_streamPos;
		Load_Stream(true, varushort, (unsigned long long)varG_GlassName->pieceCount * 2);
	}
}

// Store 14034EAA0
// Any non-null pointer here is inline.
void Load_G_GlassData(bool atStreamStart)
{
	Load_Stream(atStreamStart, varG_GlassData, sizeof(G_GlassData));
	if (varG_GlassData->glassPieces)
	{
		ALIGN_POS(4);
		varG_GlassData->glassPieces = (G_GlassPiece *)g_streamPos;
		varG_GlassPiece = (G_GlassPiece *)g_streamPos;
		Load_Stream(true, varG_GlassPiece, (unsigned long long)varG_GlassData->pieceCount * sizeof(G_GlassPiece));
	}
	if (varG_GlassData->glassNames)
	{
		ALIGN_POS(4);
		varG_GlassData->glassNames = (G_GlassName *)g_streamPos;
		varG_GlassName = (G_GlassName *)g_streamPos;
		unsigned long long count = varG_GlassData->glassNameCount;
		Load_Stream(true, varG_GlassName, count * sizeof(G_GlassName));
		G_GlassName *name = varG_GlassName;
		for (; count; count--, name++)
		{
			varG_GlassName = name;
			Load_G_GlassName(false);
		}
	}
}

// Store 140351FE0
void Load_GlassWorld(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGlassWorld, sizeof(GlassWorld));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varGlassWorld->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	if (varGlassWorld->g_glassData)
	{
		ALIGN_POS(4);
		varGlassWorld->g_glassData = (G_GlassData *)g_streamPos;
		varG_GlassData = (G_GlassData *)g_streamPos;
		Load_G_GlassData(true);
	}
	DB_PopStreamPos();
}

// Store 1403520B0
void Load_GlassWorldPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGlassWorldPtr, sizeof(GlassWorld *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	GlassWorld **ptr = varGlassWorldPtr;
	unsigned long long value = (unsigned long long)*varGlassWorldPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varGlassWorldPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varGlassWorldPtr = (GlassWorld *)g_streamPos;
		varGlassWorld = (GlassWorld *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_GlassWorld(true);
		Load_GlassWorldAsset(ptr);
		if (inserted)
			*(GlassWorld **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// ---- FxWorld --------------------------------------------------------------------------------------------------------

// Store 14034DD30
void Load_FxGlassDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxGlassDef, sizeof(FxGlassDef));
	varPhysPresetPtr = (PhysPreset **)&varFxGlassDef->physPreset;
	Load_PhysPresetPtr(false);
	varMaterialHandle = &varFxGlassDef->material;
	Load_MaterialHandle(false);
	varMaterialHandle = &varFxGlassDef->materialShattered;
	Load_MaterialHandle(false);
	varFxEffectDefHandle = &varFxGlassDef->pieceBreakEffect;
	Load_FxEffectDefHandle(false);
	varFxEffectDefHandle = &varFxGlassDef->shatterEffect;
	Load_FxEffectDefHandle(false);
	varFxEffectDefHandle = &varFxGlassDef->shatterSmallEffect;
	Load_FxEffectDefHandle(false);
	varFxEffectDefHandle = &varFxGlassDef->crackDecalEffect;
	Load_FxEffectDefHandle(false);
	varsnd_alias_list_name = &varFxGlassDef->damagedSound;
	Load_Stream(false, varsnd_alias_list_name, 8);
	Load_SndAliasCustom(varsnd_alias_list_name);
	varsnd_alias_list_name = &varFxGlassDef->destroyedSound;
	Load_Stream(false, varsnd_alias_list_name, 8);
	Load_SndAliasCustom(varsnd_alias_list_name);
	varsnd_alias_list_name = &varFxGlassDef->destroyedQuietSound;
	Load_Stream(false, varsnd_alias_list_name, 8);
	Load_SndAliasCustom(varsnd_alias_list_name);
}

// Store 14034DE80
// The glass definitions, the per-piece state arrays in the runtime block (allocated, not read), then the initial
// pieces. Any non-null pointer is inline.
void Load_FxGlassSystem(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxGlassSystem, sizeof(FxGlassSystem));
	if (varFxGlassSystem->defs)
	{
		ALIGN_POS(4);
		varFxGlassSystem->defs = (FxGlassDef *)g_streamPos;
		varFxGlassDef = (FxGlassDef *)g_streamPos;
		unsigned long long count = varFxGlassSystem->defCount;
		Load_Stream(true, varFxGlassDef, count * sizeof(FxGlassDef));
		FxGlassDef *def = varFxGlassDef;
		for (; count; count--, def++)
		{
			varFxGlassDef = def;
			Load_FxGlassDef(false);
		}
	}
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->piecePlaces)
	{
		ALIGN_POS(4);
		varFxGlassSystem->piecePlaces = (FxGlassPiecePlace *)g_streamPos;
		varFxGlassPiecePlace = (FxGlassPiecePlace *)g_streamPos;
		Load_Stream(true, varFxGlassPiecePlace, (unsigned long long)varFxGlassSystem->pieceLimit << 5);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->pieceStates)
	{
		ALIGN_POS(4);
		varFxGlassSystem->pieceStates = (FxGlassPieceState *)g_streamPos;
		varFxGlassPieceState = (FxGlassPieceState *)g_streamPos;
		Load_Stream(true, varFxGlassPieceState, (unsigned long long)varFxGlassSystem->pieceLimit << 5);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->pieceDynamics)
	{
		ALIGN_POS(4);
		varFxGlassSystem->pieceDynamics = (FxGlassPieceDynamics *)g_streamPos;
		varFxGlassPieceDynamics = (FxGlassPieceDynamics *)g_streamPos;
		Load_Stream(true, varFxGlassPieceDynamics, (unsigned long long)varFxGlassSystem->pieceLimit * 0x30);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->geoData)
	{
		ALIGN_POS(4);
		varFxGlassSystem->geoData = (FxGlassGeometryData *)g_streamPos;
		varFxGlassGeometryData = (FxGlassGeometryData *)g_streamPos;
		Load_Stream(true, varFxGlassGeometryData, (unsigned long long)varFxGlassSystem->geoDataLimit << 2);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->isInUse)
	{
		ALIGN_POS(4);
		varFxGlassSystem->isInUse = (unsigned int *)g_streamPos;
		varraw_uint = (unsigned int *)g_streamPos;
		Load_Stream(true, varraw_uint, (unsigned long long)varFxGlassSystem->pieceWordCount << 2);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->cellBits)
	{
		ALIGN_POS(4);
		varFxGlassSystem->cellBits = (unsigned int *)g_streamPos;
		varraw_uint = (unsigned int *)g_streamPos;
		unsigned int words = (unsigned int)varFxGlassSystem->cellCount * (unsigned int)varFxGlassSystem->pieceWordCount;
		Load_Stream(true, varraw_uint, (unsigned long long)words << 2);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->visData)
	{
		ALIGN_POS(16);
		varFxGlassSystem->visData = g_streamPos;
		varraw_byte16 = g_streamPos;
		Load_Stream(true, varraw_byte16, (varFxGlassSystem->pieceLimit + 0xF) & 0xFFFFFFF0u);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->linkOrg)
	{
		ALIGN_POS(4);
		varFxGlassSystem->linkOrg = (float (*)[3])g_streamPos;
		varraw_vec3_t = (float (*)[3])g_streamPos;
		Load_Stream(true, varraw_vec3_t, (unsigned long long)varFxGlassSystem->pieceLimit * 0xC);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varFxGlassSystem->halfThickness)
	{
		ALIGN_POS(16);
		varFxGlassSystem->halfThickness = (float *)g_streamPos;
		varraw_float16 = (float *)g_streamPos;
		long long floats = (int)(varFxGlassSystem->pieceLimit + 3);
		Load_Stream(true, varraw_float16, ((unsigned long long)floats & 0xFFFFFFFCull) << 2);
	}
	DB_PopStreamPos();
	if (varFxGlassSystem->lightingHandles)
	{
		ALIGN_POS(2);
		varFxGlassSystem->lightingHandles = (unsigned short *)g_streamPos;
		varuint16_t = (unsigned short *)g_streamPos;
		Load_Stream(true, varuint16_t, (unsigned long long)varFxGlassSystem->initPieceCount * 2);
	}
	if (varFxGlassSystem->initPieceStates)
	{
		ALIGN_POS(4);
		varFxGlassSystem->initPieceStates = (FxGlassInitPieceState *)g_streamPos;
		varFxGlassInitPieceState = (FxGlassInitPieceState *)g_streamPos;
		Load_Stream(true, varFxGlassInitPieceState, (unsigned long long)varFxGlassSystem->initPieceCount * 0x38);
	}
	if (varFxGlassSystem->initGeoData)
	{
		ALIGN_POS(4);
		varFxGlassSystem->initGeoData = (FxGlassGeometryData *)g_streamPos;
		varraw_FxGlassGeometryData = (FxGlassGeometryData *)g_streamPos;
		Load_Stream(true, varraw_FxGlassGeometryData, (unsigned long long)varFxGlassSystem->initGeoDataCount << 2);
	}
}

// Store 14034E910
void Load_FxWorld(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxWorld, sizeof(FxWorld));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varFxWorld->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	varFxGlassSystem = &varFxWorld->glassSys;
	Load_FxGlassSystem(false);
	DB_PopStreamPos();
}

// Store 14034E9B0
void Load_FxWorldPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxWorldPtr, sizeof(FxWorld *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	FxWorld **ptr = varFxWorldPtr;
	unsigned long long value = (unsigned long long)*varFxWorldPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varFxWorldPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varFxWorldPtr = (FxWorld *)g_streamPos;
		varFxWorld = (FxWorld *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_FxWorld(true);
		Load_FxWorldAsset(ptr);
		if (inserted)
			*(FxWorld **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// ---- effect tables ---------------------------------------------------------------------------------------------------

// Store 14034E380
// 15 entries (surface types): 31 non-flesh and 7 flesh impact effects each. Any non-null table is inline.
void Load_FxImpactTable(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxImpactTable, sizeof(FxImpactTable));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varFxImpactTable->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	if (varFxImpactTable->table)
	{
		ALIGN_POS(4);
		varFxImpactTable->table = (FxImpactEntry *)g_streamPos;
		varFxImpactEntry = (FxImpactEntry *)g_streamPos;
		Load_Stream(true, varFxImpactEntry, 15 * sizeof(FxImpactEntry));
		FxImpactEntry *entry = varFxImpactEntry;
		for (int i = 15; i; i--, entry++)
		{
			varFxImpactEntry = entry;
			Load_Stream(false, entry, sizeof(FxImpactEntry));
			varFxEffectDefHandle = varFxImpactEntry->nonflesh;
			Load_FxEffectDefHandleArray(false, 31);
			varFxEffectDefHandle = varFxImpactEntry->flesh;
			Load_FxEffectDefHandleArray(false, 7);
		}
	}
	DB_PopStreamPos();
}

// Store 14034E4E0
void Load_FxImpactTablePtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxImpactTablePtr, sizeof(FxImpactTable *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	FxImpactTable **ptr = varFxImpactTablePtr;
	unsigned long long value = (unsigned long long)*varFxImpactTablePtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varFxImpactTablePtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varFxImpactTablePtr = (FxImpactTable *)g_streamPos;
		varFxImpactTable = (FxImpactTable *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_FxImpactTable(true);
		Load_FxImpactTableAsset(ptr);
		if (inserted)
			*(FxImpactTable **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// Store 140358180
// 6 entries of 31 surface effects. Any non-null table is inline.
void Load_SurfaceFxTable(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSurfaceFxTable, sizeof(SurfaceFxTable));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varSurfaceFxTable->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	if (varSurfaceFxTable->table)
	{
		ALIGN_POS(4);
		varSurfaceFxTable->table = (SurfaceFxEntry *)g_streamPos;
		varSurfaceFxEntry = (SurfaceFxEntry *)g_streamPos;
		Load_Stream(true, varSurfaceFxEntry, 6 * sizeof(SurfaceFxEntry));
		SurfaceFxEntry *entry = varSurfaceFxEntry;
		for (int i = 6; i; i--, entry++)
		{
			varSurfaceFxEntry = entry;
			Load_Stream(false, entry, sizeof(SurfaceFxEntry));
			varFxEffectDefHandle = varSurfaceFxEntry->surfaceEffect;
			Load_FxEffectDefHandleArray(false, 31);
		}
	}
	DB_PopStreamPos();
}

// Store 1403582C0
void Load_SurfaceFxTablePtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSurfaceFxTablePtr, sizeof(SurfaceFxTable *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	SurfaceFxTable **ptr = varSurfaceFxTablePtr;
	unsigned long long value = (unsigned long long)*varSurfaceFxTablePtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varSurfaceFxTablePtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varSurfaceFxTablePtr = (SurfaceFxTable *)g_streamPos;
		varSurfaceFxTable = (SurfaceFxTable *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_SurfaceFxTable(true);
		Load_SurfaceFxTableAsset(ptr);
		if (inserted)
			*(SurfaceFxTable **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
