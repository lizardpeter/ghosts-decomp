// effectscore/fx_world.h: a map's breakable glass, Store-build layouts: GlassWorld (asset type 0x15, the server-side
// glass state) and FxWorld (0x19, the client's glass system), and the effect tables FxImpactTable (0x26) and
// SurfaceFxTable (0x27). The layouts are the servers' PDBs' except FxGlassDef, which is 8 bytes longer in the Store
// build (0x78; the loader steps by it). docs/assets/map_assets.md.
#pragma once

#include "database/db_stream_api.h"

struct Material;
struct PhysPreset;
struct FxEffectDef;
struct snd_alias_list_t;

struct G_GlassPiece
{
	unsigned short damageTaken;
	unsigned short collapseTime;
	int lastStateChangeTime;
	unsigned char impactDir;
	unsigned char impactPos[2];
};
static_assert(sizeof(G_GlassPiece) == 0xC, "G_GlassPiece");

struct G_GlassName
{
	char *nameStr;                  // +0x00
	scr_string_t name;              // +0x08
	unsigned short pieceCount;      // +0x0C
	unsigned short *pieceIndices;   // +0x10
};
static_assert(sizeof(G_GlassName) == 0x18, "G_GlassName");

struct G_GlassData
{
	G_GlassPiece *glassPieces;      // +0x00
	unsigned int pieceCount;        // +0x08
	unsigned short damageToWeaken;
	unsigned short damageToDestroy;
	unsigned int glassNameCount;    // +0x10
	G_GlassName *glassNames;        // +0x18
	unsigned char pad[108];
};
static_assert(sizeof(G_GlassData) == 0x90, "G_GlassData");

struct GlassWorld
{
	const char *name;
	G_GlassData *g_glassData;
};
static_assert(sizeof(GlassWorld) == 0x10, "GlassWorld");

struct FxGlassDef
{
	float halfThickness;
	float texVecs[2][2];
	unsigned int color;
	Material *material;                     // +0x18
	Material *materialShattered;            // +0x20
	const PhysPreset *physPreset;           // +0x28
	const FxEffectDef *pieceBreakEffect;    // +0x30
	const FxEffectDef *shatterEffect;       // +0x38
	const FxEffectDef *shatterSmallEffect;  // +0x40
	const FxEffectDef *crackDecalEffect;    // +0x48
	snd_alias_list_t *damagedSound;         // +0x50
	snd_alias_list_t *destroyedSound;       // +0x58
	snd_alias_list_t *destroyedQuietSound;  // +0x60
	int numCrackRings;                      // +0x68
	bool isOpaque;                          // +0x6C
	unsigned char storeOnly70[8];           // +0x70 (Store build only; not read by its loader)
};
static_assert(sizeof(FxGlassDef) == 0x78, "FxGlassDef (Store build)");

// The per-piece arrays: only their sizes matter to the loader.
union FxGlassPiecePlace { unsigned char data[0x20]; };
struct FxGlassPieceState { unsigned char data[0x20]; };
struct FxGlassPieceDynamics { unsigned char data[0x30]; };
union FxGlassGeometryData { unsigned char data[4]; };
struct FxGlassInitPieceState { unsigned char data[0x38]; };

struct FxGlassSystem
{
	int time;                                  // +0x00
	int prevTime;
	unsigned int defCount;                     // +0x08
	unsigned int pieceLimit;                   // +0x0C
	unsigned int pieceWordCount;               // +0x10
	unsigned int initPieceCount;               // +0x14
	unsigned int cellCount;                    // +0x18
	unsigned int activePieceCount;
	unsigned int firstFreePiece;
	unsigned int geoDataLimit;                 // +0x24
	unsigned int geoDataCount;
	unsigned int initGeoDataCount;             // +0x2C
	FxGlassDef *defs;                          // +0x30
	FxGlassPiecePlace *piecePlaces;            // +0x38
	FxGlassPieceState *pieceStates;            // +0x40
	FxGlassPieceDynamics *pieceDynamics;       // +0x48
	FxGlassGeometryData *geoData;              // +0x50
	unsigned int *isInUse;                     // +0x58
	unsigned int *cellBits;                    // +0x60
	unsigned char *visData;                    // +0x68
	float (*linkOrg)[3];                       // +0x70
	float *halfThickness;                      // +0x78
	unsigned short *lightingHandles;           // +0x80
	FxGlassInitPieceState *initPieceStates;    // +0x88
	FxGlassGeometryData *initGeoData;          // +0x90
	bool needToCompactData;
	unsigned char initCount;
	float effectChanceAccum;
	int lastPieceDeletionTime;
};
static_assert(sizeof(FxGlassSystem) == 0xA8, "FxGlassSystem");
static_assert(__builtin_offsetof(FxGlassSystem, defs) == 0x30, "FxGlassSystem");

struct FxWorld
{
	const char *name;
	FxGlassSystem glassSys;
};
static_assert(sizeof(FxWorld) == 0xB0, "FxWorld");

struct FxImpactEntry
{
	const FxEffectDef *nonflesh[31];
	const FxEffectDef *flesh[7];
};
static_assert(sizeof(FxImpactEntry) == 0x130, "FxImpactEntry");

struct FxImpactTable
{
	const char *name;
	FxImpactEntry *table;   // 15 entries (surface types)
};

struct SurfaceFxEntry
{
	const FxEffectDef *surfaceEffect[31];
};
static_assert(sizeof(SurfaceFxEntry) == 0xF8, "SurfaceFxEntry");

struct SurfaceFxTable
{
	const char *name;
	SurfaceFxEntry *table;  // 6 entries
};
