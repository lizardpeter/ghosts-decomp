// effectscore/fx_types.h: effects (FxEffectDef, asset type 0x25) and the asset types only effects use, GfxLightDef
// (0x1B) and FxParticleSimAnimation (0x3E), Store-build layouts.
//
// The layouts are the servers' PDBs' (iw6_ds_ps4, iw6_ds_xb3), and every offset the Store loaders touch agrees with
// them. The element type numbers do not: the Store build has two more types after the particle simulation animation,
// so from the cloud on its numbers are the servers' + 2 (FxElemType below). tools/fastfile/fx.py is the same loader
// in Python, checked against the game on real zones. docs/assets/effects.md.
#pragma once

#include "database/db_stream_api.h"
#include "universal/com_math.h"

struct Material;
struct XModel;
struct GfxImage;

// FxElemDef.elemType in the Store build (by what its loaders do with each value; 6 and 7 are not identified)
enum FxElemType : unsigned char
{
	FX_ELEM_TYPE_SPRITE_BILLBOARD = 0,
	FX_ELEM_TYPE_SPRITE_ORIENTED = 1,
	FX_ELEM_TYPE_TAIL = 2,
	FX_ELEM_TYPE_TRAIL = 3,
	FX_ELEM_TYPE_FLARE = 4,
	FX_ELEM_TYPE_PARTICLE_SIM_ANIMATION = 5,
	FX_ELEM_TYPE_CLOUD = 8,
	FX_ELEM_TYPE_SPARK_CLOUD = 9,
	FX_ELEM_TYPE_SPARK_FOUNTAIN = 10,
	FX_ELEM_TYPE_MODEL = 11,
	FX_ELEM_TYPE_OMNI_LIGHT = 12,
	FX_ELEM_TYPE_SPOT_LIGHT = 13,
	FX_ELEM_TYPE_SOUND = 14,
	FX_ELEM_TYPE_DECAL = 15,
	FX_ELEM_TYPE_RUNNER = 16,
	FX_ELEM_TYPE_VECTORFIELD = 17,
};

struct FxFloatRange
{
	float base;
	float amplitude;
};

struct FxIntRange
{
	int base;
	int amplitude;
};

struct FxSpawnDefLooping
{
	int intervalMsec;
	int count;
};

struct FxSpawnDefOneShot
{
	FxIntRange count;
};

union FxSpawnDef
{
	FxSpawnDefLooping looping;
	FxSpawnDefOneShot oneShot;
};

struct FxElemAtlas
{
	unsigned char behavior;
	unsigned char index;
	unsigned char fps;
	unsigned char loopCount;
	unsigned char colIndexBits;
	unsigned char rowIndexBits;
	short entryCount;
};

struct FxElemVec3Range
{
	float base[3];
	float amplitude[3];
};

struct FxElemVelStateInFrame
{
	FxElemVec3Range velocity;
	FxElemVec3Range totalDelta;
};

struct FxElemVelStateSample
{
	FxElemVelStateInFrame local;
	FxElemVelStateInFrame world;
};
static_assert(sizeof(FxElemVelStateSample) == 0x60, "FxElemVelStateSample");

struct FxElemVisualState
{
	float color[4];
	float unlitHDRScale;
	float rotationDelta;
	float rotationTotal;
	float size[2];
	float scale;
};

struct FxElemVisStateSample
{
	FxElemVisualState base;
	FxElemVisualState amplitude;
};
static_assert(sizeof(FxElemVisStateSample) == 0x50, "FxElemVisStateSample");

struct FxEffectDef;
struct GfxLightDef;
struct FxParticleSimAnimation;

union FxEffectDefRef
{
	const FxEffectDef *handle;
	const char *name;
};

union FxElemVisuals
{
	const void *anonymous;
	Material *material;
	XModel *model;
	FxEffectDefRef effectDef;
	const char *soundName;
	const char *vectorFieldName;
	GfxLightDef *lightDef;
	FxParticleSimAnimation *particleSimAnimation;
};

struct FxElemMarkVisuals
{
	Material *materials[3];
};
static_assert(sizeof(FxElemMarkVisuals) == 0x18, "FxElemMarkVisuals");

union FxElemDefVisuals
{
	FxElemMarkVisuals *markArray;
	FxElemVisuals *array;
	FxElemVisuals instance;
};

struct FxTrailVertex
{
	float pos[2];
	float normal[2];
	float texCoord[2];
};
static_assert(sizeof(FxTrailVertex) == 0x18, "FxTrailVertex");

struct FxTrailDef
{
	int scrollTimeMsec;
	int repeatDist;
	float invSplitDist;
	float invSplitArcDist;
	float invSplitTime;
	int vertCount;
	FxTrailVertex *verts;
	int indCount;
	unsigned short *inds;
};
static_assert(sizeof(FxTrailDef) == 0x30, "FxTrailDef");

struct FxSparkFountainDef
{
	float gravity;
	float bounceFrac;
	float bounceRand;
	float sparkSpacing;
	float sparkLength;
	int sparkCount;
	float loopTime;
	float velMin;
	float velMax;
	float velConeFrac;
	float restSpeed;
	float boostTime;
	float boostFactor;
};
static_assert(sizeof(FxSparkFountainDef) == 0x34, "FxSparkFountainDef");

struct FxSpotLightDef
{
	float fovInnerFraction;
	float startRadius;
	float endRadius;
	float brightness;
	float maxLength;
	int exponent;
};
static_assert(sizeof(FxSpotLightDef) == 0x18, "FxSpotLightDef");

struct FxFlareDef
{
	float position;
	int angularRotCount;
	int flags;
	FxFloatRange depthScaleRange;
	FxFloatRange depthScaleValue;
	FxFloatRange radialRot;
	FxFloatRange radialScaleX;
	FxFloatRange radialScaleY;
	float dir[3];
	int intensityXIntervalCount;
	int intensityYIntervalCount;
	int srcCosIntensityIntervalCount;
	int srcCosScaleIntervalCount;
	float *intensityX;
	float *intensityY;
	float *srcCosIntensity;
	float *srcCosScale;
};
static_assert(sizeof(FxFlareDef) == 0x70, "FxFlareDef");

union FxElemExtendedDefPtr
{
	FxTrailDef *trailDef;
	FxSparkFountainDef *sparkFountainDef;
	FxSpotLightDef *spotLightDef;
	FxFlareDef *flareDef;
	void *unknownDef;
};

struct FxElemDef
{
	int flags;                                  // +0x000
	int flags2;                                 // +0x004
	FxSpawnDef spawn;                           // +0x008
	FxFloatRange spawnRange;                    // +0x010
	FxFloatRange fadeInRange;                   // +0x018
	FxFloatRange fadeOutRange;                  // +0x020
	float spawnFrustumCullRadius;               // +0x028
	FxIntRange spawnDelayMsec;                  // +0x02C
	FxIntRange lifeSpanMsec;                    // +0x034
	FxFloatRange spawnOrigin[3];                // +0x03C
	FxFloatRange spawnOffsetRadius;             // +0x054
	FxFloatRange spawnOffsetHeight;             // +0x05C
	FxFloatRange spawnAngles[3];                // +0x064
	FxFloatRange angularVelocity[3];            // +0x07C
	FxFloatRange initialRotation;               // +0x094
	FxFloatRange gravity;                       // +0x09C
	FxFloatRange reflectionFactor;              // +0x0A4
	FxElemAtlas atlas;                          // +0x0AC
	unsigned char elemType;                     // +0x0B4 FxElemType
	unsigned char elemLitType;                  // +0x0B5
	unsigned char visualCount;                  // +0x0B6
	unsigned char velIntervalCount;             // +0x0B7
	unsigned char visStateIntervalCount;        // +0x0B8
	const FxElemVelStateSample *velSamples;     // +0x0C0 velIntervalCount + 1
	const FxElemVisStateSample *visSamples;     // +0x0C8 visStateIntervalCount + 1
	FxElemDefVisuals visuals;                   // +0x0D0
	Bounds collBounds;                          // +0x0D8
	FxEffectDefRef effectOnImpact;              // +0x0F0
	FxEffectDefRef effectOnDeath;               // +0x0F8
	FxEffectDefRef effectEmitted;               // +0x100
	FxFloatRange emitDist;                      // +0x108
	FxFloatRange emitDistVariance;              // +0x110
	FxElemExtendedDefPtr extended;              // +0x118
	unsigned char sortOrder;                    // +0x120
	unsigned char lightingFrac;                 // +0x121
	unsigned char useItemClip;                  // +0x122
	unsigned char fadeInfo;                     // +0x123
	int randomSeed;                             // +0x124
	float litMaxColorChangePerSec;              // +0x128
	float unlitHDRScalar;                       // +0x12C
	int pad130[2];                              // +0x130 (the servers' PDB lists nothing more; the size is 0x138)
};
static_assert(sizeof(FxElemDef) == 0x138, "FxElemDef");
static_assert(__builtin_offsetof(FxElemDef, velSamples) == 0xC0, "FxElemDef");
static_assert(__builtin_offsetof(FxElemDef, effectOnImpact) == 0xF0, "FxElemDef");
static_assert(__builtin_offsetof(FxElemDef, extended) == 0x118, "FxElemDef");

struct FxEffectDef
{
	const char *name;                           // +0x00
	int flags;                                  // +0x08
	int totalSize;                              // +0x0C
	int msecLoopingLife;                        // +0x10
	int elemDefCountLooping;                    // +0x14
	int elemDefCountOneShot;                    // +0x18
	int elemDefCountEmission;                   // +0x1C
	float elemMaxRadius;                        // +0x20
	float occlusionQueryDepthBias;              // +0x24
	int occlusionQueryFadeIn;                   // +0x28
	int occlusionQueryFadeOut;                  // +0x2C
	FxFloatRange occlusionQueryScaleRange;      // +0x30
	const FxElemDef *elemDefs;                  // +0x38 looping + one-shot + emission
};
static_assert(sizeof(FxEffectDef) == 0x40, "FxEffectDef");

struct GfxLightImage
{
	GfxImage *image;
	unsigned char samplerState;
};
static_assert(sizeof(GfxLightImage) == 0x10, "GfxLightImage");

struct GfxLightDef
{
	const char *name;
	GfxLightImage attenuation;
	GfxLightImage cucoloris;
	int lmapLookupStart;
};
static_assert(sizeof(GfxLightDef) == 0x30, "GfxLightDef");

struct FxParticleSimAnimationHeader
{
	float playbackRate;
	float duration;
	unsigned int frameCount;
	float minX;
	float minY;
	float minZ;
	float boundsXDelta;
	float boundsYDelta;
	float boundsZDelta;
	float maxWidth;
	float maxHeight;
	unsigned int colorTableSize;
	unsigned int particleDataCount;
	bool evalVisStatePerParticle;
	bool sortParticlesAtRuntime;
};
static_assert(sizeof(FxParticleSimAnimationHeader) == 0x38, "FxParticleSimAnimationHeader");

struct FxParticleSimAnimationParticleData
{
	unsigned char data[0x20];
};

struct FxParticleSimAnimationFrame
{
	unsigned int particleDataOffset;
	unsigned int numActiveParticles;
};

struct GfxColorFloat
{
	float array[4];
};

struct FxParticleSimAnimation
{
	const char *name;                                   // +0x00
	Material *material;                                 // +0x08
	FxParticleSimAnimationHeader header;                // +0x10
	FxParticleSimAnimationParticleData *particleData;   // +0x48 header.particleDataCount, aligned 32
	FxParticleSimAnimationFrame *frames;                // +0x50 header.frameCount
	GfxColorFloat *colorTable;                          // +0x58 header.colorTableSize
};
static_assert(sizeof(FxParticleSimAnimation) == 0x60, "FxParticleSimAnimation");
