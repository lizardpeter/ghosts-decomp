// bgame/bg_tracer_load_db.cpp (Store build): the zone loaders of tracers (TracerDef, asset type 0x31).
//
// Generated loader functions (database/db_load.cpp includes them; the servers' PDB places them in
// gfx_d3d/r_material_load_db.h). The code is the Store build's, tagged with Store addresses; tools/fastfile/weapon.py
// is the same logic in Python, checked against the game on real zones (docs/assets/weapons.md).

#include "database/db_stream_api.h"

struct Material;

struct TracerDef
{
	const char *name;       // +0x00
	Material *material;     // +0x08
	unsigned int drawInterval;
	float speed;
	float beamLength;
	float beamWidth;
	float screwRadius;
	float screwDist;
	float colors[5][4];
};
static_assert(sizeof(TracerDef) == 0x78, "TracerDef");

void Load_MaterialHandle(bool atStreamStart);           // Store 140353700
void Load_TracerDefAsset(TracerDef **tracerDef);         // Store 140373B80

extern TracerDef **varTracerDefPtr;                     // Store 144425F98
extern TracerDef *varTracerDef;                         // Store 144425F90
extern Material **varMaterialHandle;                    // Store 144425D20

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// Store 140358530
void Load_TracerDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varTracerDef, sizeof(TracerDef));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varTracerDef->name;
	Load_Stream(false, varXString, 8);
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
	varMaterialHandle = &varTracerDef->material;
	Load_MaterialHandle(false);
	DB_PopStreamPos();
}

// Store 1403585D0
void Load_TracerDefPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varTracerDefPtr, sizeof(TracerDef *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	TracerDef **ptr = varTracerDefPtr;
	unsigned long long value = (unsigned long long)*varTracerDefPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varTracerDefPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varTracerDefPtr = (TracerDef *)g_streamPos;
		varTracerDef = (TracerDef *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_TracerDef(true);
		Load_TracerDefAsset(ptr);
		if (inserted)
			*(TracerDef **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
