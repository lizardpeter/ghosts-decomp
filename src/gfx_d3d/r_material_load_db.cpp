// gfx_d3d/r_material_load_db.h (Store build): the fastfile loaders of materials, technique sets, shaders and vertex
// declarations.
//
// The servers' PDBs place these generated Load_* functions in gfx_d3d/r_material_load_db.h, compiled into
// database/db_registry.cpp. Their bodies there load only what a dedicated server keeps (a material's info and
// constant buffers, a technique set's name), so the Store build's disassembly is the source here; names, the var*
// globals and the shape of the code are the servers' (and Black Ops' for the functions the servers inline away:
// Load_MaterialTechnique, Load_MaterialPassArray, Load_MaterialTextureDefInfo, Load_GfxStateBits).
//
// How the generated loaders work (docs/assets/materials.md has the full stream layout):
// - Each type has a var<Type> global pointing at the object being loaded. Load_<Type>(atStreamStart) first reads the
//   object itself (Load_Stream copies it from the zone when atStreamStart, i.e. when it was not already read as
//   part of its parent), then fixes up its pointers one by one.
// - A pointer field holds 0 (NULL), DB_PTR_FOLLOWING (the data follows inline in the stream: it is aligned,
//   allocated at g_streamPos and loaded), DB_PTR_INSERT (asset pointers only: as FOLLOWING, and the address is also
//   recorded with DB_InsertPointer so later references can alias it), or an offset into an already loaded block
//   (DB_ConvertOffsetToPointer; DB_ConvertOffsetToAlias for asset pointers).
// - DB_PushStreamPos(block) / DB_PopStreamPos switch the block that inline data is allocated in: 3 for an asset's
//   own data, 0 (temp) around asset pointers.
// - Assets are registered with Load_<Type>Asset (DB_AddXAsset), which may replace the pointer with an existing
//   asset of the same name.
//
// The stream functions (Load_Stream, DB_*StreamPos, DB_Convert*, DB_InsertPointer, Load_XString*) belong to the
// fastfile pipeline (database/db_stream_load.cpp); they are declared here until that has its own header.

#include "gfx_d3d/r_material.h"

// ---- database/db_stream_load.cpp ----------------------------------------------------------------------------------

#define DB_PTR_FOLLOWING 0xFDFDFDFFFFFFFFFFull  // the data follows inline
#define DB_PTR_INSERT 0xFDFDFDFFFFFFFFFEull     // follows inline, and later pointers may alias it

extern unsigned char *g_streamPos;

void Load_Stream(bool atStreamStart, void *ptr, unsigned long long size);
void DB_PushStreamPos(unsigned int index);
void DB_PopStreamPos();
void DB_ConvertOffsetToPointer(unsigned long long *data);
void DB_ConvertOffsetToAlias(unsigned long long *data);
unsigned char *DB_InsertPointer();
void Load_XStringCustom(const char **str);
void Load_XStringArray(bool atStreamStart, unsigned long long count);
void Load_GfxImagePtr(bool atStreamStart);
void Load_PicmipWater(water_t **water);

// database/db_registry.cpp: register a loaded asset (DB_AddXAsset); may point *header at an existing one
void Load_MaterialAsset(Material **material);
void Load_MaterialTechniqueSetAsset(MaterialTechniqueSet **techniqueSet);
void Load_MaterialVertexShaderAsset(MaterialVertexShader **shader);
void Load_MaterialPixelShaderAsset(MaterialPixelShader **shader);
void Load_MaterialHullShaderAsset(MaterialHullShader **shader);
void Load_MaterialDomainShaderAsset(MaterialDomainShader **shader);
void Load_MaterialVertexDeclAsset(MaterialVertexDeclaration **decl);

// Store 140372140 (name unknown): stores the loading zone's index into a zone handle
void sub_140372140(unsigned char *zoneHandle);
// Store 14063AEF0 (name unknown): an empty function (`ret 0`) the loader calls on each GfxStateBits' load bits,
// like the servers' folded Load_* stubs
void sub_14063AEF0(unsigned int *loadBits, GfxStateBits *stateBits);

// ---- the var globals (servers' MAP names; Store addresses in records/names.tsv) -------------------------------

extern const char **varXString;
extern const char *varConstChar;
extern unsigned char *varbyte;
extern unsigned char *varbyte4;
extern unsigned char *varbyte16;
extern unsigned short *varushort;
extern unsigned int *varuint;
extern float *varfloat;
extern unsigned char *varXZoneHandle;
extern GfxImage **varGfxImagePtr;
extern water_t *varwater_t;

extern Material *varMaterial;
extern Material **varMaterialHandle;
extern MaterialInfo *varMaterialInfo;
extern MaterialTextureDef *varMaterialTextureDef;
extern MaterialTextureDefInfo *varMaterialTextureDefInfo;
extern MaterialConstantDef *varMaterialConstantDef;
extern GfxStateBits *varGfxStateBits;
extern MaterialConstantBufferDef *varMaterialConstantBufferDef;
extern MaterialTechniqueSet *varMaterialTechniqueSet;
extern MaterialTechniqueSet **varMaterialTechniqueSetPtr;
extern MaterialTechnique *varMaterialTechnique;
extern MaterialTechnique **varMaterialTechniquePtr;
extern MaterialPass *varMaterialPass;
extern MaterialShaderArgument *varMaterialShaderArgument;
extern MaterialArgumentDef *varMaterialArgumentDef;
extern MaterialVertexShader *varMaterialVertexShader;
extern MaterialVertexShader **varMaterialVertexShaderPtr;
extern MaterialVertexShaderProgram *varMaterialVertexShaderProgram;
extern GfxVertexShaderLoadDef *varGfxVertexShaderLoadDef;
extern MaterialPixelShader *varMaterialPixelShader;
extern MaterialPixelShader **varMaterialPixelShaderPtr;
extern MaterialPixelShaderProgram *varMaterialPixelShaderProgram;
extern GfxPixelShaderLoadDef *varGfxPixelShaderLoadDef;
extern MaterialHullShader *varMaterialHullShader;
extern MaterialHullShader **varMaterialHullShaderPtr;
extern MaterialHullShaderProgram *varMaterialHullShaderProgram;
extern GfxHullShaderLoadDef *varGfxHullShaderLoadDef;
extern MaterialDomainShader *varMaterialDomainShader;
extern MaterialDomainShader **varMaterialDomainShaderPtr;
extern MaterialDomainShaderProgram *varMaterialDomainShaderProgram;
extern GfxDomainShaderLoadDef *varGfxDomainShaderLoadDef;
extern MaterialVertexDeclaration *varMaterialVertexDeclaration;
extern MaterialVertexDeclaration **varMaterialVertexDeclarationPtr;
extern MaterialVertexStreamRouting *varMaterialVertexStreamRouting;

// AllocLoad_<align>: align the stream position and hand it out
static inline unsigned char *DB_AlignStreamPos(unsigned long long mask)
{
	g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + mask) & ~mask);
	return g_streamPos;
}

static inline bool DB_IsInlineOrInsert(unsigned long long ptr)
{
	return ptr + 0x0202020000000002ull <= 1;  // DB_PTR_FOLLOWING or DB_PTR_INSERT
}

// An XString field: NULL, inline (follows in the stream), or an offset
static inline void Load_XStringField(const char **field)
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

// ---- material ---------------------------------------------------------------------------------------------------

// Store 140353AD0 (servers: renderer/tr_types_load_db.h)
void Load_MaterialInfo(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialInfo, 0x28);
	Load_XStringField(&varMaterialInfo->name);
}

// Store 14034FCE0 (Black Ops' AllocLoad_GfxStateBits/Load_GfxStateBitsArray; the servers don't load state bits)
void Load_GfxStateBits(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxStateBits, 0x1C);
	unsigned int *loadBits = varGfxStateBits->loadBits;
	varuint = loadBits;
	Load_Stream(false, loadBits, 0xC);
	sub_14063AEF0(loadBits, varGfxStateBits);
	varXZoneHandle = &varGfxStateBits->zone;
	Load_Stream(false, varXZoneHandle, 1);
	unsigned char *zone = varXZoneHandle;
	varbyte = zone;
	Load_Stream(false, zone, 1);
	sub_140372140(zone);
}

// Store 140354220 (Black Ops' Load_MaterialTextureDefInfo): a water map's water_t, any other semantic's image
void Load_MaterialTextureDefInfo(bool atStreamStart)
{
	if (varMaterialTextureDef->semantic != TS_WATER_MAP)
	{
		varGfxImagePtr = &varMaterialTextureDefInfo->image;
		Load_GfxImagePtr(atStreamStart);
		return;
	}
	MaterialTextureDefInfo *info = varMaterialTextureDefInfo;
	if (!info->water)
		return;
	if ((unsigned long long)info->water == DB_PTR_FOLLOWING)
	{
		info->water = (water_t *)DB_AlignStreamPos(3);
		varwater_t = (water_t *)g_streamPos;
		Load_water_t(true);
		Load_PicmipWater(&info->water);
	}
	else
	{
		DB_ConvertOffsetToPointer((unsigned long long *)info);
	}
}

// Store 1403532A0
void Load_MaterialConstantBufferDefArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varMaterialConstantBufferDef, count << 7);
	MaterialConstantBufferDef *def = varMaterialConstantBufferDef;
	for (; count; count--, def++)
	{
		varMaterialConstantBufferDef = def;
		Load_Stream(false, def, 0x80);
		if (varMaterialConstantBufferDef->vsData)
		{
			varMaterialConstantBufferDef->vsData = DB_AlignStreamPos(15);
			varbyte16 = g_streamPos;
			Load_Stream(true, g_streamPos, varMaterialConstantBufferDef->vsDataSize);
		}
		if (varMaterialConstantBufferDef->hsData)
		{
			varMaterialConstantBufferDef->hsData = DB_AlignStreamPos(15);
			varbyte16 = g_streamPos;
			Load_Stream(true, g_streamPos, varMaterialConstantBufferDef->hsDataSize);
		}
		if (varMaterialConstantBufferDef->dsData)
		{
			varMaterialConstantBufferDef->dsData = DB_AlignStreamPos(15);
			varbyte16 = g_streamPos;
			Load_Stream(true, g_streamPos, varMaterialConstantBufferDef->dsDataSize);
		}
		if (varMaterialConstantBufferDef->psData)
		{
			varMaterialConstantBufferDef->psData = DB_AlignStreamPos(15);
			varbyte16 = g_streamPos;
			Load_Stream(true, g_streamPos, varMaterialConstantBufferDef->psDataSize);
		}
		if (varMaterialConstantBufferDef->vsOffsetData)
		{
			varMaterialConstantBufferDef->vsOffsetData = (unsigned short *)DB_AlignStreamPos(1);
			varushort = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMaterialConstantBufferDef->vsOffsetDataSize * 2);
		}
		if (varMaterialConstantBufferDef->hsOffsetData)
		{
			varMaterialConstantBufferDef->hsOffsetData = (unsigned short *)DB_AlignStreamPos(1);
			varushort = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMaterialConstantBufferDef->hsOffsetDataSize * 2);
		}
		if (varMaterialConstantBufferDef->dsOffsetData)
		{
			varMaterialConstantBufferDef->dsOffsetData = (unsigned short *)DB_AlignStreamPos(1);
			varushort = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMaterialConstantBufferDef->dsOffsetDataSize * 2);
		}
		if (varMaterialConstantBufferDef->psOffsetData)
		{
			varMaterialConstantBufferDef->psOffsetData = (unsigned short *)DB_AlignStreamPos(1);
			varushort = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMaterialConstantBufferDef->psOffsetDataSize * 2);
		}
	}
}

// Store 140352F90. The texture, constant and state bits arrays (Load_MaterialTextureDefArray and the others) are
// inlined.
void Load_Material(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterial, 0x3A8);
	DB_PushStreamPos(3);
	varMaterialInfo = &varMaterial->info;
	Load_MaterialInfo(false);
	varMaterialTechniqueSetPtr = &varMaterial->techniqueSet;
	Load_MaterialTechniqueSetPtr(false);

	if (varMaterial->textureTable)
	{
		if ((unsigned long long)varMaterial->textureTable == DB_PTR_FOLLOWING)
		{
			varMaterial->textureTable = (MaterialTextureDef *)DB_AlignStreamPos(3);
			varMaterialTextureDef = (MaterialTextureDef *)g_streamPos;
			unsigned long long count = varMaterial->textureCount;
			Load_Stream(true, varMaterialTextureDef, count << 4);
			MaterialTextureDef *def = varMaterialTextureDef;
			for (; count; count--, def++)
			{
				varMaterialTextureDef = def;
				Load_Stream(false, def, 0x10);
				varMaterialTextureDefInfo = &varMaterialTextureDef->u;
				Load_MaterialTextureDefInfo(false);
			}
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMaterial->textureTable);
		}
	}

	if (varMaterial->constantTable)
	{
		if ((unsigned long long)varMaterial->constantTable == DB_PTR_FOLLOWING)
		{
			varMaterial->constantTable = (MaterialConstantDef *)DB_AlignStreamPos(15);
			varMaterialConstantDef = (MaterialConstantDef *)g_streamPos;
			Load_Stream(true, varMaterialConstantDef, (unsigned long long)varMaterial->constantCount << 5);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMaterial->constantTable);
		}
	}

	if (varMaterial->stateBitsTable)
	{
		if ((unsigned long long)varMaterial->stateBitsTable == DB_PTR_FOLLOWING)
		{
			varMaterial->stateBitsTable = (GfxStateBits *)DB_AlignStreamPos(3);
			varGfxStateBits = (GfxStateBits *)g_streamPos;
			unsigned long long count = varMaterial->stateBitsCount;
			Load_Stream(true, varGfxStateBits, count * 0x1C);
			GfxStateBits *bits = varGfxStateBits;
			for (; count; count--, bits++)
			{
				varGfxStateBits = bits;
				Load_GfxStateBits(false);
			}
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMaterial->stateBitsTable);
		}
	}

	if (varMaterial->constantBufferTable)
	{
		if ((unsigned long long)varMaterial->constantBufferTable == DB_PTR_FOLLOWING)
		{
			varMaterial->constantBufferTable = (MaterialConstantBufferDef *)DB_AlignStreamPos(3);
			varMaterialConstantBufferDef = (MaterialConstantBufferDef *)g_streamPos;
			Load_MaterialConstantBufferDefArray(true, varMaterial->constantBufferCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMaterial->constantBufferTable);
		}
	}

	unsigned char *constantBufferCount = &varMaterial->constantBufferCount;
	varbyte = constantBufferCount;
	Load_Stream(false, constantBufferCount, 1);
	Load_InitMaterialConstantBuffer(constantBufferCount, varMaterial);

	// PC only: the layer names; any non-NULL value means inline (no offset form)
	if (varMaterial->subMaterials)
	{
		varMaterial->subMaterials = (const char **)DB_AlignStreamPos(7);
		varXString = (const char **)g_streamPos;
		Load_XStringArray(true, varMaterial->layerCount);
	}
	DB_PopStreamPos();
}

// Load_MaterialHandle and Load_MaterialHandleArray inline the same asset pointer handling
static inline void Load_MaterialHandleBody()
{
	Material **handle = varMaterialHandle;
	unsigned long long ptr = (unsigned long long)*handle;
	if (!ptr)
		return;
	if (!DB_IsInlineOrInsert(ptr))
	{
		DB_ConvertOffsetToAlias((unsigned long long *)varMaterialHandle);
		return;
	}
	*varMaterialHandle = (Material *)DB_AlignStreamPos(3);
	varMaterial = (Material *)g_streamPos;
	if (ptr == DB_PTR_INSERT)
	{
		unsigned char *insert = DB_InsertPointer();
		Load_Material(true);
		Load_MaterialAsset(handle);
		if (insert)
			*(Material **)insert = *handle;
	}
	else
	{
		Load_Material(true);
		Load_MaterialAsset(handle);
	}
}

// Store 140353700
void Load_MaterialHandle(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialHandle, 8);
	DB_PushStreamPos(0);
	Load_MaterialHandleBody();
	DB_PopStreamPos();
}

// Store 1403537F0
void Load_MaterialHandleArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varMaterialHandle, count * 8);
	Material **handle = varMaterialHandle;
	for (; count; count--, handle++)
	{
		varMaterialHandle = handle;
		Load_Stream(false, handle, 8);
		DB_PushStreamPos(0);
		Load_MaterialHandleBody();
		DB_PopStreamPos();
	}
}

// Store 1403624D0 (Black Ops' Load_water_t). Three M * N float arrays, then the water's two images.
void Load_water_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varwater_t, 0x58);
	if (varwater_t->H0X)
	{
		varwater_t->H0X = (float *)DB_AlignStreamPos(3);
		varfloat = (float *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)(varwater_t->N * varwater_t->M) << 2);
	}
	if (varwater_t->H0Y)
	{
		varwater_t->H0Y = (float *)DB_AlignStreamPos(3);
		varfloat = (float *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)(varwater_t->N * varwater_t->M) << 2);
	}
	if (varwater_t->wTerm)
	{
		varwater_t->wTerm = (float *)DB_AlignStreamPos(3);
		varfloat = (float *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)(varwater_t->N * varwater_t->M) << 2);
	}
	varGfxImagePtr = &varwater_t->image;
	Load_GfxImagePtr(false);
	varGfxImagePtr = &varwater_t->imageAlt;
	Load_GfxImagePtr(false);
}

// ---- shaders ----------------------------------------------------------------------------------------------------

// Store 14034FE90. The program is aligned to 4 and read inline; the shader is then created from it.
void Load_GfxVertexShaderLoadDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxVertexShaderLoadDef, 0x18);
	GfxVertexShaderLoadDef *loadDef = varGfxVertexShaderLoadDef;
	if (!loadDef->program)
		return;
	if ((unsigned long long)loadDef->program == DB_PTR_FOLLOWING)
	{
		loadDef->program = DB_AlignStreamPos(3);
		varbyte4 = g_streamPos;
		Load_Stream(true, g_streamPos, (int)varGfxVertexShaderLoadDef->programSize);
		Load_CreateMaterialVertexShader(&loadDef->program, varMaterialVertexShader);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxVertexShaderLoadDef);
}

// Store 14034FB30
void Load_GfxPixelShaderLoadDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxPixelShaderLoadDef, 0x18);
	GfxPixelShaderLoadDef *loadDef = varGfxPixelShaderLoadDef;
	if (!loadDef->program)
		return;
	if ((unsigned long long)loadDef->program == DB_PTR_FOLLOWING)
	{
		loadDef->program = DB_AlignStreamPos(3);
		varbyte4 = g_streamPos;
		Load_Stream(true, g_streamPos, (int)varGfxPixelShaderLoadDef->programSize);
		Load_CreateMaterialPixelShader(&loadDef->program, varMaterialPixelShader);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxPixelShaderLoadDef);
}

// Store 14034F080
void Load_GfxHullShaderLoadDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxHullShaderLoadDef, 0x10);
	GfxHullShaderLoadDef *loadDef = varGfxHullShaderLoadDef;
	if (!loadDef->program)
		return;
	if ((unsigned long long)loadDef->program == DB_PTR_FOLLOWING)
	{
		loadDef->program = DB_AlignStreamPos(3);
		varbyte4 = g_streamPos;
		Load_Stream(true, g_streamPos, (int)varGfxHullShaderLoadDef->programSize);
		Load_CreateMaterialHullShader(&loadDef->program, varMaterialHullShader);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxHullShaderLoadDef);
}

// Store 14034EFE0
void Load_GfxDomainShaderLoadDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxDomainShaderLoadDef, 0x10);
	GfxDomainShaderLoadDef *loadDef = varGfxDomainShaderLoadDef;
	if (!loadDef->program)
		return;
	if ((unsigned long long)loadDef->program == DB_PTR_FOLLOWING)
	{
		loadDef->program = DB_AlignStreamPos(3);
		varbyte4 = g_streamPos;
		Load_Stream(true, g_streamPos, (int)varGfxDomainShaderLoadDef->programSize);
		Load_CreateMaterialDomainShader(&loadDef->program, varMaterialDomainShader);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxDomainShaderLoadDef);
}

// Store 140354490
void Load_MaterialVertexShader(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialVertexShader, 0x28);
	DB_PushStreamPos(3);
	Load_XStringField(&varMaterialVertexShader->name);
	varMaterialVertexShaderProgram = &varMaterialVertexShader->prog;
	Load_Stream(false, varMaterialVertexShaderProgram, 0x20);
	varGfxVertexShaderLoadDef = &varMaterialVertexShaderProgram->loadDef;
	Load_GfxVertexShaderLoadDef(false);
	DB_PopStreamPos();
}

// Store 140353DA0
void Load_MaterialPixelShader(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialPixelShader, 0x28);
	DB_PushStreamPos(3);
	Load_XStringField(&varMaterialPixelShader->name);
	varMaterialPixelShaderProgram = &varMaterialPixelShader->prog;
	Load_Stream(false, varMaterialPixelShaderProgram, 0x20);
	varGfxPixelShaderLoadDef = &varMaterialPixelShaderProgram->loadDef;
	Load_GfxPixelShaderLoadDef(false);
	DB_PopStreamPos();
}

// Store 140353920
void Load_MaterialHullShader(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialHullShader, 0x20);
	DB_PushStreamPos(3);
	Load_XStringField(&varMaterialHullShader->name);
	varMaterialHullShaderProgram = &varMaterialHullShader->prog;
	Load_Stream(false, varMaterialHullShaderProgram, 0x18);
	varGfxHullShaderLoadDef = &varMaterialHullShaderProgram->loadDef;
	Load_GfxHullShaderLoadDef(false);
	DB_PopStreamPos();
}

// Store 140353550
void Load_MaterialDomainShader(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialDomainShader, 0x20);
	DB_PushStreamPos(3);
	Load_XStringField(&varMaterialDomainShader->name);
	varMaterialDomainShaderProgram = &varMaterialDomainShader->prog;
	Load_Stream(false, varMaterialDomainShaderProgram, 0x18);
	varGfxDomainShaderLoadDef = &varMaterialDomainShaderProgram->loadDef;
	Load_GfxDomainShaderLoadDef(false);
	DB_PopStreamPos();
}

// The asset pointer functions: an offset aliases an asset loaded earlier; inline data is loaded and registered.
#define LOAD_ASSET_PTR(Type, LoadType, LoadAsset)                                                                \
	Load_Stream(atStreamStart, var##Type##Ptr, 8);                                                                \
	DB_PushStreamPos(0);                                                                                          \
	Type **handle = var##Type##Ptr;                                                                               \
	unsigned long long ptr = (unsigned long long)*handle;                                                         \
	if (ptr)                                                                                                      \
	{                                                                                                             \
		if (!DB_IsInlineOrInsert(ptr))                                                                            \
		{                                                                                                         \
			DB_ConvertOffsetToAlias((unsigned long long *)handle);                                                \
			DB_PopStreamPos();                                                                                    \
			return;                                                                                               \
		}                                                                                                         \
		*handle = (Type *)DB_AlignStreamPos(3);                                                                   \
		var##Type = (Type *)g_streamPos;                                                                          \
		if (ptr == DB_PTR_INSERT)                                                                                 \
		{                                                                                                         \
			unsigned char *insert = DB_InsertPointer();                                                           \
			LoadType(true);                                                                                       \
			LoadAsset(handle);                                                                                    \
			if (insert)                                                                                           \
			{                                                                                                     \
				*(Type **)insert = *handle;                                                                       \
				DB_PopStreamPos();                                                                                \
				return;                                                                                           \
			}                                                                                                     \
		}                                                                                                         \
		else                                                                                                      \
		{                                                                                                         \
			LoadType(true);                                                                                       \
			LoadAsset(handle);                                                                                    \
		}                                                                                                         \
	}                                                                                                             \
	DB_PopStreamPos();

// Store 140354550
void Load_MaterialVertexShaderPtr(bool atStreamStart)
{
	LOAD_ASSET_PTR(MaterialVertexShader, Load_MaterialVertexShader, Load_MaterialVertexShaderAsset)
}

// Store 140353E60
void Load_MaterialPixelShaderPtr(bool atStreamStart)
{
	LOAD_ASSET_PTR(MaterialPixelShader, Load_MaterialPixelShader, Load_MaterialPixelShaderAsset)
}

// Store 1403539E0
void Load_MaterialHullShaderPtr(bool atStreamStart)
{
	LOAD_ASSET_PTR(MaterialHullShader, Load_MaterialHullShader, Load_MaterialHullShaderAsset)
}

// Store 140353610
void Load_MaterialDomainShaderPtr(bool atStreamStart)
{
	LOAD_ASSET_PTR(MaterialDomainShader, Load_MaterialDomainShader, Load_MaterialDomainShaderAsset)
}

// ---- vertex declarations ----------------------------------------------------------------------------------------

// Store 1403542D0. The input layouts are built against the vertex shader of the pass being loaded, so a vertex
// declaration is only ever loaded inline from a pass, after that pass's vertex shader.
void Load_MaterialVertexDeclaration(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialVertexDeclaration, 0x838);
	DB_PushStreamPos(3);
	Load_XStringField(&varMaterialVertexDeclaration->name);
	MaterialVertexStreamRouting *routing = &varMaterialVertexDeclaration->routing;
	varMaterialVertexStreamRouting = routing;
	Load_Stream(false, routing, 0x828);
	Load_MaterialVertexStreamRouting(routing, varMaterialVertexDeclaration->streamCount,
	                                 varMaterialPass->vertexShader);
	DB_PopStreamPos();
}

// Store 1403543A0
void Load_MaterialVertexDeclarationPtr(bool atStreamStart)
{
	LOAD_ASSET_PTR(MaterialVertexDeclaration, Load_MaterialVertexDeclaration, Load_MaterialVertexDeclAsset)
}

// ---- techniques -------------------------------------------------------------------------------------------------

// Store 140353B50 (Black Ops' Load_MaterialPassArray, with Load_MaterialPass and the argument array inlined)
void Load_MaterialPassArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varMaterialPass, count * 0x48);
	MaterialPass *pass = varMaterialPass;
	for (; count; count--, pass++)
	{
		varMaterialPass = pass;
		Load_Stream(false, pass, 0x48);
		varMaterialVertexShaderPtr = &varMaterialPass->vertexShader;
		Load_MaterialVertexShaderPtr(false);
		varMaterialVertexDeclarationPtr = &varMaterialPass->vertexDecl;
		Load_MaterialVertexDeclarationPtr(false);
		varMaterialHullShaderPtr = &varMaterialPass->hullShader;
		Load_MaterialHullShaderPtr(false);
		varMaterialDomainShaderPtr = &varMaterialPass->domainShader;
		Load_MaterialDomainShaderPtr(false);
		varMaterialPixelShaderPtr = &varMaterialPass->pixelShader;
		Load_MaterialPixelShaderPtr(false);

		varXZoneHandle = &varMaterialPass->zone;
		Load_Stream(false, varXZoneHandle, 1);
		unsigned char *zone = varXZoneHandle;
		varbyte = zone;
		Load_Stream(false, zone, 1);
		sub_140372140(zone);

		// any non-NULL value means inline
		if (varMaterialPass->args)
		{
			varMaterialPass->args = (MaterialShaderArgument *)DB_AlignStreamPos(3);
			varMaterialShaderArgument = (MaterialShaderArgument *)g_streamPos;
			unsigned long long argCount = (unsigned long long)varMaterialPass->stableArgCount +
			                              varMaterialPass->perObjArgCount + varMaterialPass->perPrimArgCount;
			Load_Stream(true, varMaterialShaderArgument, argCount << 4);
			MaterialShaderArgument *arg = varMaterialShaderArgument;
			for (; argCount; argCount--, arg++)
			{
				varMaterialShaderArgument = arg;
				Load_Stream(false, arg, 0x10);
				MaterialArgumentDef *def = &varMaterialShaderArgument->u;
				varMaterialArgumentDef = def;
				if (varMaterialShaderArgument->type != MTL_ARG_LITERAL_CONST || !def->literalConst)
					continue;
				if ((unsigned long long)def->literalConst == DB_PTR_FOLLOWING)
				{
					varfloat = (float *)DB_AlignStreamPos(3);
					def->literalConst = varfloat;
					Load_Stream(true, varfloat, 0x10);
				}
				else
				{
					DB_ConvertOffsetToPointer((unsigned long long *)def);
				}
			}
		}
	}
}

// Store 140353F50 (Black Ops' Load_MaterialTechnique). Always read at the stream start: the technique's size depends
// on its pass count. The name follows the passes.
void Load_MaterialTechnique(bool atStreamStart)
{
	MaterialPass *passArray = varMaterialTechnique->passArray;
	Load_Stream(atStreamStart, varMaterialTechnique, 0x10);
	varMaterialPass = passArray;
	Load_MaterialPassArray(true, varMaterialTechnique->passCount);
	Load_XStringField(&varMaterialTechnique->name);
}

// Store 140353FF0
void Load_MaterialTechniqueSet(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMaterialTechniqueSet, 0xCF0);
	DB_PushStreamPos(3);
	Load_XStringField(&varMaterialTechniqueSet->name);
	MaterialTechnique **techniques = varMaterialTechniqueSet->techniques;
	varMaterialTechniquePtr = techniques;
	Load_Stream(false, techniques, 0xCE0);
	for (int techType = 0; techType < TECHNIQUE_COUNT; techType++, techniques++)
	{
		varMaterialTechniquePtr = techniques;
		Load_Stream(false, techniques, 8);
		if (!*varMaterialTechniquePtr)
			continue;
		if ((unsigned long long)*varMaterialTechniquePtr == DB_PTR_FOLLOWING)
		{
			*varMaterialTechniquePtr = (MaterialTechnique *)DB_AlignStreamPos(3);
			varMaterialTechnique = (MaterialTechnique *)g_streamPos;
			Load_MaterialTechnique(true);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varMaterialTechniquePtr);
		}
	}
	DB_PopStreamPos();
}

// Store 140354130
void Load_MaterialTechniqueSetPtr(bool atStreamStart)
{
	LOAD_ASSET_PTR(MaterialTechniqueSet, Load_MaterialTechniqueSet, Load_MaterialTechniqueSetAsset)
}
