// physics/physpreset_load_db.h (Store build): the zone loaders of PhysPreset and PhysCollmap.
//
// Generated loader functions of physics/physpreset_load_db.h, included into database/db_load.cpp (db_load.obj in
// the PS4/xb3 servers, whose PDBs give names and lines). The code is the Store build's, tagged with Store addresses;
// the statements are the servers' in the same order. Load_PhysGeomInfoArray is inlined into Load_PhysCollmap in the
// Store build.

#include "xanim/xmodel.h"

// Store 140355500 (physics/physpreset_load_db.h:671 in the PS4 PDB)
void Load_PhysPreset(bool atStreamStart)
{
	Load_Stream(atStreamStart, varPhysPreset, sizeof(PhysPreset));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varPhysPreset->name;
	Load_Stream(false, varPhysPreset, sizeof(const char *));
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
	varXString = &varPhysPreset->sndAliasPrefix;
	Load_Stream(false, varXString, sizeof(const char *));
	if (*varXString)
	{
		if ((unsigned long long)*varXString == DB_PTR_FOLLOWING)
		{
			*varXString = (const char *)g_streamPos;
			varConstChar = (const char *)g_streamPos;
			Load_XStringCustom(varXString);
			DB_PopStreamPos();
			return;
		}
		DB_ConvertOffsetToPointer((unsigned long long *)varXString);
	}
	DB_PopStreamPos();
}

// Store 1403555F0 (physics/physpreset_load_db.h:1038 in the PS4 PDB)
void Load_PhysPresetPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varPhysPresetPtr, sizeof(PhysPreset *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	PhysPreset **presetPtr = varPhysPresetPtr;
	unsigned long long value = (unsigned long long)*varPhysPresetPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varPhysPresetPtr);
			DB_PopStreamPos();
			return;
		}
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		*varPhysPresetPtr = (PhysPreset *)g_streamPos;
		varPhysPreset = (PhysPreset *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_PhysPreset(true);
		Load_PhysPresetAsset(presetPtr);
		if (inserted)
			*(PhysPreset **)inserted = *presetPtr;
	}
	DB_PopStreamPos();
}

// Inlined into Load_PhysCollmap in the Store build (physics/physpreset_load_db.h:1345 in the PS4 PDB)
void Load_PhysGeomInfoArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varPhysGeomInfo, sizeof(PhysGeomInfo) * count);
	PhysGeomInfo *geom = varPhysGeomInfo;
	for (; count; count--)
	{
		varPhysGeomInfo = geom;
		Load_Stream(false, geom, sizeof(PhysGeomInfo));
		if (varPhysGeomInfo->brushWrapper)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varPhysGeomInfo->brushWrapper = (BrushWrapper *)g_streamPos;
			varBrushWrapper = (BrushWrapper *)g_streamPos;
			Load_BrushWrapper(true);
		}
		geom++;
	}
}

// Store 1403552B0 (physics/physpreset_load_db.h:1385 in the PS4 PDB)
void Load_PhysCollmap(bool atStreamStart)
{
	Load_Stream(atStreamStart, varPhysCollmap, sizeof(PhysCollmap));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varPhysCollmap->name;
	Load_Stream(false, varPhysCollmap, sizeof(const char *));
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
	if (varPhysCollmap->geoms)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		varPhysCollmap->geoms = (PhysGeomInfo *)g_streamPos;
		varPhysGeomInfo = (PhysGeomInfo *)g_streamPos;
		Load_PhysGeomInfoArray(true, varPhysCollmap->count);
	}
	DB_PopStreamPos();
}

// Store 140355410 (physics/physpreset_load_db.h:1536 in the PS4 PDB)
void Load_PhysCollmapPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varPhysCollmapPtr, sizeof(PhysCollmap *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	PhysCollmap **collmapPtr = varPhysCollmapPtr;
	unsigned long long value = (unsigned long long)*varPhysCollmapPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varPhysCollmapPtr);
			DB_PopStreamPos();
			return;
		}
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		*varPhysCollmapPtr = (PhysCollmap *)g_streamPos;
		varPhysCollmap = (PhysCollmap *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_PhysCollmap(true);
		Load_PhysCollmapAsset(collmapPtr);
		if (inserted)
			*(PhysCollmap **)inserted = *collmapPtr;
	}
	DB_PopStreamPos();
}
