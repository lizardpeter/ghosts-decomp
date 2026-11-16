// gfx_d3d/r_postfx_load_db.cpp (Store build): the zone loaders of the post-processing assets (Colorization,
// ColorizationSet, ToneMapping).
//
// Generated loader functions (database/db_load.cpp includes them; the servers' PDB places them in
// gfx_d3d/r_material_load_db.h). The code is the Store build's, tagged with Store addresses; tools/fastfile/postfx.py
// is the same logic in Python, checked against the game on real zones (docs/assets/postfx.md).

#include "gfx_d3d/r_postfx.h"

void Load_MaterialHandle(bool atStreamStart);                         // Store 140353700
void Load_ColorizationAsset(Colorization **colorization);              // Store 1403718C0
void Load_ColorizationSetAsset(ColorizationSet **colorizationSet);     // Store 140371980
void Load_ToneMappingAsset(ToneMapping **toneMapping);                 // Store 140373AC0

extern Colorization **varColorizationPtr;                             // Store 1444253D8
extern Colorization *varColorization;                                 // Store 1444253D0
extern ColorizationSet **varColorizationSetPtr;                       // Store 1444253E8
extern ColorizationSet *varColorizationSet;                           // Store 1444253E0
extern ToneMapping **varToneMappingPtr;                               // Store 1444253F8
extern ToneMapping *varToneMapping;                                   // Store 1444253F0
extern Material **varMaterialHandle;                                  // Store 144425D20

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// The XString rule on varXString, already read.
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

// Store 14034B830
// The name is the last field.
void Load_Colorization(bool atStreamStart)
{
	Load_Stream(atStreamStart, varColorization, sizeof(Colorization));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varColorization->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	DB_PopStreamPos();
}

// Store 14034B8C0
void Load_ColorizationPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varColorizationPtr, sizeof(Colorization *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	Colorization **ptr = varColorizationPtr;
	unsigned long long value = (unsigned long long)*varColorizationPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varColorizationPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varColorizationPtr = (Colorization *)g_streamPos;
		varColorization = (Colorization *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_Colorization(true);
		Load_ColorizationAsset(ptr);
		if (inserted)
			*(Colorization **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// Store 14034B9B0
void Load_ColorizationSet(bool atStreamStart)
{
	Load_Stream(atStreamStart, varColorizationSet, sizeof(ColorizationSet));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varColorizationSet->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	varColorizationPtr = &varColorizationSet->colorization;
	Load_ColorizationPtr(false);
	varColorizationPtr = &varColorizationSet->colorizationAlternate;
	Load_ColorizationPtr(false);
	varColorizationPtr = &varColorizationSet->colorizationLow;
	Load_ColorizationPtr(false);
	varColorizationPtr = &varColorizationSet->colorizationMid;
	Load_ColorizationPtr(false);
	varColorizationPtr = &varColorizationSet->colorizationHigh;
	Load_ColorizationPtr(false);
	varMaterialHandle = &varColorizationSet->alternateMaskMaterial;
	Load_MaterialHandle(false);
	DB_PopStreamPos();
}

// Store 14034BAD0
void Load_ColorizationSetPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varColorizationSetPtr, sizeof(ColorizationSet *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	ColorizationSet **ptr = varColorizationSetPtr;
	unsigned long long value = (unsigned long long)*varColorizationSetPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varColorizationSetPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varColorizationSetPtr = (ColorizationSet *)g_streamPos;
		varColorizationSet = (ColorizationSet *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_ColorizationSet(true);
		Load_ColorizationSetAsset(ptr);
		if (inserted)
			*(ColorizationSet **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// Store 1403583B0
// The name is the last field.
void Load_ToneMapping(bool atStreamStart)
{
	Load_Stream(atStreamStart, varToneMapping, sizeof(ToneMapping));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varToneMapping->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	DB_PopStreamPos();
}

// Store 140358440
void Load_ToneMappingPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varToneMappingPtr, sizeof(ToneMapping *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	ToneMapping **ptr = varToneMappingPtr;
	unsigned long long value = (unsigned long long)*varToneMappingPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varToneMappingPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varToneMappingPtr = (ToneMapping *)g_streamPos;
		varToneMapping = (ToneMapping *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_ToneMapping(true);
		Load_ToneMappingAsset(ptr);
		if (inserted)
			*(ToneMapping **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
