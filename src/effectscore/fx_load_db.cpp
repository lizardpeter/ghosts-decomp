// effectscore/fx_load_db.cpp (Store build): the zone loaders of effects (FxEffectDef) and of the two asset types only
// effects use (GfxLightDef, FxParticleSimAnimation).
//
// Generated loader functions (database/db_load.cpp includes them; the servers' PDB places them in
// gfx_d3d/r_material_load_db.h). The code is the Store build's, tagged with Store addresses; where the Store build
// inlined a server function (Load_FxEffectDefRef, Load_FxElemMarkVisualsArray) the code is inline here too.
// tools/fastfile/fx.py is the same logic in Python, checked against the game on real zones
// (docs/assets/effects.md).

#include "effectscore/fx_types.h"

void Load_MaterialHandle(bool atStreamStart);                                  // Store 140353700
void Load_MaterialHandleArray(bool atStreamStart, unsigned long long count);   // Store 1403537F0
void Load_XModelPtr(bool atStreamStart);                                       // Store 14035E530
void Load_XString(bool atStreamStart);                                         // Store 14035E950
void Load_GfxImagePtr(bool atStreamStart);                                     // Store 14034F380
void Load_FxEffectDefAsset(FxEffectDef **effectDef);                           // Store 140371E10
void Load_FxEffectDefFromName(const char **name);                              // Store 140371ED0
void Load_GfxLightDefAsset(GfxLightDef **lightDef);                            // Store 140372480
void Load_FxParticleSimAnimationAsset(FxParticleSimAnimation **anim);          // Store 140371FC0
void Load_GfxLightDefPtr(bool atStreamStart);
void Load_FxParticleSimAnimationPtr(bool atStreamStart);

extern const FxEffectDef **varFxEffectDefHandle;                              // Store 1444260F8
extern FxEffectDef *varFxEffectDef;                                           // Store 1444261A8
extern FxElemDef *varFxElemDef;                                               // Store 1444261A0
extern FxElemVelStateSample *varFxElemVelStateSample;                         // Store 144426140
extern FxElemVisStateSample *varFxElemVisStateSample;                         // Store 144426128
extern FxElemDefVisuals *varFxElemDefVisuals;                                 // Store 144426168
extern FxElemMarkVisuals *varFxElemMarkVisuals;                               // Store 144426108
extern FxElemVisuals *varFxElemVisuals;                                       // Store 144426110
extern FxEffectDefRef *varFxEffectDefRef;                                     // Store 144426100
extern FxElemExtendedDefPtr *varFxElemExtendedDefPtr;                         // Store 144426198
extern FxTrailDef *varFxTrailDef;                                             // Store 144426178
extern FxTrailVertex *varFxTrailVertex;                                       // Store 144426170
extern FxSparkFountainDef *varFxSparkFountainDef;                             // Store 144426180
extern FxSpotLightDef *varFxSpotLightDef;                                     // Store 144426188
extern FxFlareDef *varFxFlareDef;                                             // Store 144426190
extern void *varvoid;                                                         // Store 144424A08
extern unsigned short *varushort;                                             // Store 144424D18
extern Material **varMaterialHandle;                                          // Store 144425D20
extern XModel **varXModelPtr;                                                 // Store 1444267F8
extern GfxLightDef **varGfxLightDefPtr;                                       // Store 144426D50
extern GfxLightDef *varGfxLightDef;                                           // Store 144426D48
extern GfxLightImage *varGfxLightImage;                                       // Store 144426D38
extern GfxImage **varGfxImagePtr;                                             // Store 144425868
extern FxParticleSimAnimation **varFxParticleSimAnimationPtr;                 // Store 144426090
extern FxParticleSimAnimation *varFxParticleSimAnimation;                     // Store 144426088
extern FxParticleSimAnimationParticleData *varFxParticleSimAnimationParticleData;  // Store 144426070
extern FxParticleSimAnimationFrame *varFxParticleSimAnimationFrame;           // Store 144426078
extern GfxColorFloat *varGfxColorFloat;                                       // Store 144427020

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// The XString rule on a field already read: inline (FOLLOWING) -> the string at the stream position, anything else
// non-null -> an offset.
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

// Store 14034E850
void Load_FxTrailDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxTrailDef, sizeof(FxTrailDef));
	if (varFxTrailDef->verts)
	{
		ALIGN_POS(4);
		varFxTrailDef->verts = (FxTrailVertex *)g_streamPos;
		varFxTrailVertex = (FxTrailVertex *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varFxTrailDef->vertCount * sizeof(FxTrailVertex));
	}
	if (varFxTrailDef->inds)
	{
		ALIGN_POS(2);
		varFxTrailDef->inds = (unsigned short *)g_streamPos;
		varushort = (unsigned short *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varFxTrailDef->indCount * 2);
	}
}

// Store 14034DBD0
// The four curves have intervalCount + 1 floats each.
void Load_FxFlareDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxFlareDef, sizeof(FxFlareDef));
	if (varFxFlareDef->intensityX)
	{
		ALIGN_POS(4);
		varFxFlareDef->intensityX = (float *)g_streamPos;
		varfloat = (float *)g_streamPos;
		int count = varFxFlareDef->intensityXIntervalCount + 1;
		Load_Stream(true, g_streamPos, (long long)count << 2);
	}
	if (varFxFlareDef->intensityY)
	{
		ALIGN_POS(4);
		varFxFlareDef->intensityY = (float *)g_streamPos;
		varfloat = (float *)g_streamPos;
		int count = varFxFlareDef->intensityYIntervalCount + 1;
		Load_Stream(true, g_streamPos, (long long)count << 2);
	}
	if (varFxFlareDef->srcCosIntensity)
	{
		ALIGN_POS(4);
		varFxFlareDef->srcCosIntensity = (float *)g_streamPos;
		varfloat = (float *)g_streamPos;
		int count = varFxFlareDef->srcCosIntensityIntervalCount + 1;
		Load_Stream(true, g_streamPos, (long long)count << 2);
	}
	if (varFxFlareDef->srcCosScale)
	{
		ALIGN_POS(4);
		varFxFlareDef->srcCosScale = (float *)g_streamPos;
		varfloat = (float *)g_streamPos;
		int count = varFxFlareDef->srcCosScaleIntervalCount + 1;
		Load_Stream(true, g_streamPos, (long long)count << 2);
	}
}

// Store 14034D750
// By the element's type: a trail, spark fountain, spot light or flare definition (inline, aligned 4, or an offset);
// for any other type a non-null value gets one byte at the stream position, unaligned (the generator's unknownDef).
void Load_FxElemExtendedDefPtr(bool)
{
	unsigned char elemType = varFxElemDef->elemType;
	if (elemType == FX_ELEM_TYPE_TRAIL)
	{
		if (!varFxElemExtendedDefPtr->trailDef)
			return;
		if ((unsigned long long)varFxElemExtendedDefPtr->trailDef != DB_PTR_FOLLOWING)
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varFxElemExtendedDefPtr);
			return;
		}
		ALIGN_POS(4);
		varFxElemExtendedDefPtr->trailDef = (FxTrailDef *)g_streamPos;
		varFxTrailDef = (FxTrailDef *)g_streamPos;
		Load_FxTrailDef(true);
	}
	else if (elemType == FX_ELEM_TYPE_SPARK_FOUNTAIN)
	{
		if (!varFxElemExtendedDefPtr->sparkFountainDef)
			return;
		if ((unsigned long long)varFxElemExtendedDefPtr->sparkFountainDef != DB_PTR_FOLLOWING)
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varFxElemExtendedDefPtr);
			return;
		}
		ALIGN_POS(4);
		varFxElemExtendedDefPtr->sparkFountainDef = (FxSparkFountainDef *)g_streamPos;
		varFxSparkFountainDef = (FxSparkFountainDef *)g_streamPos;
		Load_Stream(true, varFxSparkFountainDef, sizeof(FxSparkFountainDef));
	}
	else if (elemType == FX_ELEM_TYPE_SPOT_LIGHT)
	{
		if (!varFxElemExtendedDefPtr->spotLightDef)
			return;
		if ((unsigned long long)varFxElemExtendedDefPtr->spotLightDef != DB_PTR_FOLLOWING)
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varFxElemExtendedDefPtr);
			return;
		}
		ALIGN_POS(4);
		varFxElemExtendedDefPtr->spotLightDef = (FxSpotLightDef *)g_streamPos;
		varFxSpotLightDef = (FxSpotLightDef *)g_streamPos;
		Load_Stream(true, varFxSpotLightDef, sizeof(FxSpotLightDef));
	}
	else if (elemType == FX_ELEM_TYPE_FLARE)
	{
		if (!varFxElemExtendedDefPtr->flareDef)
			return;
		if ((unsigned long long)varFxElemExtendedDefPtr->flareDef != DB_PTR_FOLLOWING)
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varFxElemExtendedDefPtr);
			return;
		}
		ALIGN_POS(4);
		varFxElemExtendedDefPtr->flareDef = (FxFlareDef *)g_streamPos;
		varFxFlareDef = (FxFlareDef *)g_streamPos;
		Load_FxFlareDef(true);
	}
	else if (varFxElemExtendedDefPtr->unknownDef)
	{
		varFxElemExtendedDefPtr->unknownDef = g_streamPos;
		varvoid = g_streamPos;
		Load_Stream(true, varvoid, 1);
	}
}

// Store 14034D900
// One visual, by the element's type.
void Load_FxElemVisuals(bool atStreamStart)
{
	unsigned char elemType = varFxElemDef->elemType;
	if (elemType == FX_ELEM_TYPE_MODEL)
	{
		varXModelPtr = &varFxElemVisuals->model;
		Load_XModelPtr(atStreamStart);
		return;
	}
	if (elemType == FX_ELEM_TYPE_RUNNER)
	{
		FxElemVisuals *visuals = varFxElemVisuals;
		varFxEffectDefRef = &visuals->effectDef;
		varXString = &visuals->effectDef.name;
		Load_XString(atStreamStart);
		Load_FxEffectDefFromName(&visuals->effectDef.name);
		return;
	}
	if (elemType == FX_ELEM_TYPE_SOUND || elemType == FX_ELEM_TYPE_VECTORFIELD)
	{
		varXString = &varFxElemVisuals->soundName;
		Load_XString(atStreamStart);
		return;
	}
	if (elemType == FX_ELEM_TYPE_PARTICLE_SIM_ANIMATION)
	{
		varFxParticleSimAnimationPtr = &varFxElemVisuals->particleSimAnimation;
		Load_FxParticleSimAnimationPtr(atStreamStart);
		return;
	}
	if (elemType == FX_ELEM_TYPE_OMNI_LIGHT)
		return;
	if (elemType == FX_ELEM_TYPE_SPOT_LIGHT)
	{
		varGfxLightDefPtr = &varFxElemVisuals->lightDef;
		Load_GfxLightDefPtr(atStreamStart);
		return;
	}
	varMaterialHandle = &varFxElemVisuals->material;
	Load_MaterialHandle(atStreamStart);
}

// Store 14034D9E0
void Load_FxElemVisualsArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varFxElemVisuals, count * sizeof(FxElemVisuals));
	FxElemVisuals *visuals = varFxElemVisuals;
	for (; count; count--, visuals++)
	{
		unsigned char elemType = varFxElemDef->elemType;
		varFxElemVisuals = visuals;
		if (elemType == FX_ELEM_TYPE_MODEL)
		{
			varXModelPtr = &visuals->model;
			Load_XModelPtr(false);
		}
		else if (elemType == FX_ELEM_TYPE_RUNNER)
		{
			varXString = &visuals->effectDef.name;
			varFxEffectDefRef = &visuals->effectDef;
			Load_Stream(false, visuals, 8);
			LoadXStringField();
			Load_FxEffectDefFromName(&visuals->effectDef.name);
		}
		else if (elemType == FX_ELEM_TYPE_SOUND)
		{
			varXString = &visuals->soundName;
			Load_Stream(false, visuals, 8);
			LoadXStringField();
		}
		else if (elemType == FX_ELEM_TYPE_VECTORFIELD)
		{
			varXString = &visuals->vectorFieldName;
			Load_Stream(false, visuals, 8);
			LoadXStringField();
		}
		else if (elemType == FX_ELEM_TYPE_PARTICLE_SIM_ANIMATION)
		{
			varFxParticleSimAnimationPtr = &visuals->particleSimAnimation;
			Load_FxParticleSimAnimationPtr(false);
		}
		else if (elemType != FX_ELEM_TYPE_OMNI_LIGHT)
		{
			if (elemType == FX_ELEM_TYPE_SPOT_LIGHT)
			{
				varGfxLightDefPtr = &visuals->lightDef;
				Load_GfxLightDefPtr(false);
			}
			else
			{
				varMaterialHandle = &visuals->material;
				Load_MaterialHandle(false);
			}
		}
	}
}

// Store 14034D600
// A decal's mark visuals (any non-null value: aligned 4, visualCount entries of three material handles); one visual
// in place (visualCount 0 or 1); else an array of visualCount (any non-null value: aligned 4).
void Load_FxElemDefVisuals(bool atStreamStart)
{
	if (varFxElemDef->elemType == FX_ELEM_TYPE_DECAL)
	{
		if (!varFxElemDefVisuals->markArray)
			return;
		ALIGN_POS(4);
		varFxElemDefVisuals->markArray = (FxElemMarkVisuals *)g_streamPos;
		varFxElemMarkVisuals = (FxElemMarkVisuals *)g_streamPos;
		unsigned long long count = varFxElemDef->visualCount;
		Load_Stream(true, varFxElemMarkVisuals, count * sizeof(FxElemMarkVisuals));
		FxElemMarkVisuals *marks = varFxElemMarkVisuals;
		for (; count; count--, marks++)
		{
			varFxElemMarkVisuals = marks;
			Load_Stream(false, marks, sizeof(FxElemMarkVisuals));
			varMaterialHandle = varFxElemMarkVisuals->materials;
			Load_MaterialHandleArray(false, 3);
		}
		return;
	}
	if (varFxElemDef->visualCount <= 1)
	{
		varFxElemVisuals = &varFxElemDefVisuals->instance;
		Load_FxElemVisuals(atStreamStart);
		return;
	}
	if (!varFxElemDefVisuals->array)
		return;
	ALIGN_POS(4);
	varFxElemDefVisuals->array = (FxElemVisuals *)g_streamPos;
	varFxElemVisuals = (FxElemVisuals *)g_streamPos;
	Load_FxElemVisualsArray(true, varFxElemDef->visualCount);
}

// The effect references of an element (the servers' Load_FxEffectDefRef, inline here): the name, then the handle
// DB_FindXAssetHeader finds for it.
static inline void LoadEffectRef(FxEffectDefRef *ref)
{
	varFxEffectDefRef = ref;
	varXString = &ref->name;
	Load_Stream(false, ref, 8);
	LoadXStringField();
	Load_FxEffectDefFromName(&ref->name);
}

// Store 14034D340
void Load_FxElemDefArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varFxElemDef, count * sizeof(FxElemDef));
	FxElemDef *elem = varFxElemDef;
	for (; count; count--, elem++)
	{
		varFxElemDef = elem;
		Load_Stream(false, elem, sizeof(FxElemDef));
		if (varFxElemDef->velSamples)
		{
			ALIGN_POS(4);
			varFxElemDef->velSamples = (FxElemVelStateSample *)g_streamPos;
			varFxElemVelStateSample = (FxElemVelStateSample *)g_streamPos;
			Load_Stream(true, varFxElemVelStateSample,
			            ((unsigned long long)varFxElemDef->velIntervalCount + 1) * sizeof(FxElemVelStateSample));
		}
		if (varFxElemDef->visSamples)
		{
			ALIGN_POS(4);
			varFxElemDef->visSamples = (FxElemVisStateSample *)g_streamPos;
			varFxElemVisStateSample = (FxElemVisStateSample *)g_streamPos;
			Load_Stream(true, varFxElemVisStateSample,
			            ((unsigned long long)varFxElemDef->visStateIntervalCount + 1) * sizeof(FxElemVisStateSample));
		}
		varFxElemDefVisuals = &varFxElemDef->visuals;
		Load_FxElemDefVisuals(false);
		LoadEffectRef(&varFxElemDef->effectOnImpact);
		LoadEffectRef(&varFxElemDef->effectOnDeath);
		LoadEffectRef(&varFxElemDef->effectEmitted);
		varFxElemExtendedDefPtr = &varFxElemDef->extended;
		Load_FxElemExtendedDefPtr(false);
	}
}

// Store 14034D040
// Any non-null elemDefs is inline: looping + one-shot + emission elements.
void Load_FxEffectDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxEffectDef, sizeof(FxEffectDef));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varFxEffectDef->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	if (varFxEffectDef->elemDefs)
	{
		ALIGN_POS(4);
		varFxEffectDef->elemDefs = (FxElemDef *)g_streamPos;
		varFxElemDef = (FxElemDef *)g_streamPos;
		int count = (int)((unsigned int)varFxEffectDef->elemDefCountEmission + (unsigned int)varFxEffectDef->elemDefCountOneShot
		                  + (unsigned int)varFxEffectDef->elemDefCountLooping);
		Load_FxElemDefArray(true, (long long)count);
	}
	DB_PopStreamPos();
}

// Store 14034D120
void Load_FxEffectDefHandle(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxEffectDefHandle, sizeof(FxEffectDef *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	FxEffectDef **handle = (FxEffectDef **)varFxEffectDefHandle;
	unsigned long long value = (unsigned long long)*varFxEffectDefHandle;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varFxEffectDefHandle);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varFxEffectDefHandle = (FxEffectDef *)g_streamPos;
		varFxEffectDef = (FxEffectDef *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_FxEffectDef(true);
		Load_FxEffectDefAsset(handle);
		if (inserted)
			*(FxEffectDef **)inserted = *handle;
	}
	DB_PopStreamPos();
}

// Store 14034F470
void Load_GfxLightDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxLightDef, sizeof(GfxLightDef));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varGfxLightDef->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	varGfxLightImage = &varGfxLightDef->attenuation;
	Load_Stream(false, varGfxLightImage, sizeof(GfxLightImage));
	varGfxImagePtr = &varGfxLightImage->image;
	Load_GfxImagePtr(false);
	varGfxLightImage = &varGfxLightDef->cucoloris;
	Load_Stream(false, varGfxLightImage, sizeof(GfxLightImage));
	varGfxImagePtr = &varGfxLightImage->image;
	Load_GfxImagePtr(false);
	DB_PopStreamPos();
}

// Store 14034F560
void Load_GfxLightDefPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxLightDefPtr, sizeof(GfxLightDef *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	GfxLightDef **ptr = varGfxLightDefPtr;
	unsigned long long value = (unsigned long long)*varGfxLightDefPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varGfxLightDefPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varGfxLightDefPtr = (GfxLightDef *)g_streamPos;
		varGfxLightDef = (GfxLightDef *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_GfxLightDef(true);
		Load_GfxLightDefAsset(ptr);
		if (inserted)
			*(GfxLightDef **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// Store 14034E5D0
void Load_FxParticleSimAnimation(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxParticleSimAnimation, sizeof(FxParticleSimAnimation));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varFxParticleSimAnimation->name;
	Load_Stream(false, varXString, 8);
	LoadXStringField();
	varMaterialHandle = &varFxParticleSimAnimation->material;
	Load_MaterialHandle(false);
	if (varFxParticleSimAnimation->particleData)
	{
		ALIGN_POS(32);
		varFxParticleSimAnimation->particleData = (FxParticleSimAnimationParticleData *)g_streamPos;
		varFxParticleSimAnimationParticleData = (FxParticleSimAnimationParticleData *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varFxParticleSimAnimation->header.particleDataCount << 5);
	}
	if (varFxParticleSimAnimation->frames)
	{
		ALIGN_POS(4);
		varFxParticleSimAnimation->frames = (FxParticleSimAnimationFrame *)g_streamPos;
		varFxParticleSimAnimationFrame = (FxParticleSimAnimationFrame *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varFxParticleSimAnimation->header.frameCount << 3);
	}
	if (varFxParticleSimAnimation->colorTable)
	{
		ALIGN_POS(4);
		varFxParticleSimAnimation->colorTable = (GfxColorFloat *)g_streamPos;
		varGfxColorFloat = (GfxColorFloat *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varFxParticleSimAnimation->header.colorTableSize << 4);
	}
	DB_PopStreamPos();
}

// Store 14034E760
// The header is aligned to 32.
void Load_FxParticleSimAnimationPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varFxParticleSimAnimationPtr, sizeof(FxParticleSimAnimation *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	FxParticleSimAnimation **ptr = varFxParticleSimAnimationPtr;
	unsigned long long value = (unsigned long long)*varFxParticleSimAnimationPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varFxParticleSimAnimationPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(32);
		*varFxParticleSimAnimationPtr = (FxParticleSimAnimation *)g_streamPos;
		varFxParticleSimAnimation = (FxParticleSimAnimation *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_FxParticleSimAnimation(true);
		Load_FxParticleSimAnimationAsset(ptr);
		if (inserted)
			*(FxParticleSimAnimation **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
