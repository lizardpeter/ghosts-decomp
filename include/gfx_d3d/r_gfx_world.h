// GfxWorld, the world's render data (asset type 0x1A), as the Store build (PC) lays it out. docs/assets/world.md.
//
// Field names are the servers' (PS4/xb3 PDB types) where the PC layout matches theirs; PC-only fields are named
// after what loads or uses them, and bytes no PC code reads by name stay unknown arrays. Sizes and the offsets the
// loaders use are checked below.
#pragma once

#include <stddef.h>

#include "database/db_stream_api.h"
#include "gfx_d3d/r_image.h"

struct Material;
struct XModel;
struct ID3D11Buffer;
struct ID3D11ShaderResourceView;
struct GfxSubdivCache;

struct cplane_s;  // 0x14 bytes

struct GfxSky  // 0x20
{
	int skySurfCount;
	int *skyStartSurfs;  // +0x08
	GfxImage *skyImage;  // +0x10
	unsigned char skySamplerState;
	unsigned char pad19[7];
};

struct GfxWorldDpvsPlanes  // 0x20
{
	int cellCount;
	cplane_s *planes;                // +0x08: planeCount, or an offset to an earlier copy
	unsigned short *nodes;           // +0x10: nodeCount
	unsigned int *sceneEntCellBits;  // +0x18: runtime, cellCount << 9 words
};

struct GfxAabbTree  // 0x38
{
	float bounds[6];
	unsigned short childCount;
	unsigned short surfaceCount;
	unsigned int startSurfIndex;
	unsigned short smodelIndexCount;  // +0x20
	unsigned short *smodelIndexes;    // +0x28
	int childrenOffset;
};

struct GfxCellTree  // 8
{
	GfxAabbTree *aabbTree;
};

struct GfxCellTreeCount  // 4
{
	int aabbTreeCount;
};

struct GfxPortal  // 0x50
{
	unsigned char writable[0x18];
	float plane[4];
	float (*vertices)[3];  // +0x28: vertexCount
	unsigned short cellIndex;
	unsigned short closeDistance;
	unsigned char vertexCount;  // +0x34
	unsigned char pad35[3];
	float hullAxis[2][3];
};

struct GfxCell  // 0x48
{
	float bounds[6];
	int portalCount;  // +0x18
	GfxPortal *portals;
	unsigned char reflectionProbeCount;  // +0x28
	unsigned char *reflectionProbes;
	unsigned char reflectionProbeReferenceCount;  // +0x38
	unsigned char *reflectionProbeReferences;
};

struct GfxReflectionProbeVolumeData  // 0x60
{
	float volumePlanes[6][4];
};

struct GfxReflectionProbe  // 0x20
{
	float origin[3];
	GfxReflectionProbeVolumeData *probeVolumes;  // +0x10
	unsigned int probeVolumeCount;               // +0x18
};

struct GfxReflectionProbeReferenceOrigin  // 0xC
{
	float origin[3];
};

struct GfxReflectionProbeReference  // 1
{
	unsigned char index;
};

struct GfxLightmapArray  // 0x10
{
	GfxImage *primary;
	GfxImage *secondary;
};

struct GfxWorldVertex  // 0x2C
{
	unsigned char bytes[0x2C];
};

struct GfxWorldVertexData0  // 0x10
{
	GfxWorldVertex *vertices;
	ID3D11Buffer *worldVb;
};

struct GfxWorldVertexLayerData  // 0x10
{
	unsigned char *data;
	ID3D11Buffer *layerVb;
};

struct GfxWorldDraw  // 0xB0
{
	unsigned int reflectionProbeCount;
	GfxImage **reflectionProbes;                    // +0x08
	GfxReflectionProbe *reflectionProbeOrigins;    // +0x10
	GfxTexture *reflectionProbeTextures;           // +0x18 (runtime)
	unsigned int reflectionProbeReferenceCount;    // +0x20
	GfxReflectionProbeReferenceOrigin *reflectionProbeReferenceOrigins;  // +0x28
	GfxReflectionProbeReference *reflectionProbeReferences;              // +0x30
	int lightmapCount;                             // +0x38
	GfxLightmapArray *lightmaps;                   // +0x40
	GfxTexture *lightmapPrimaryTextures;           // +0x48 (runtime)
	GfxTexture *lightmapSecondaryTextures;         // +0x50 (runtime)
	GfxImage *lightmapOverridePrimary;             // +0x58
	GfxImage *lightmapOverrideSecondary;           // +0x60
	unsigned int trisType;
	unsigned int vertexCount;                      // +0x6C
	GfxWorldVertexData0 vd;                        // +0x70
	unsigned int vertexLayerDataSize;              // +0x80
	GfxWorldVertexLayerData vld;                   // +0x88
	unsigned int indexCount;                       // +0x98
	unsigned short *indices;                       // +0xA0
	ID3D11Buffer *indexBuffer;                     // +0xA8
};

struct GfxLightGridEntry  // 8
{
	unsigned int colorsIndex;
	unsigned short primaryLightEnvIndex;
	unsigned char unused;
	unsigned char needsTrace;
};

struct GfxLightGridColors  // 0xA8
{
	unsigned char rgb[56][3];
};

struct GfxLightGridTree  // 0x50
{
	unsigned char maxDepth;
	int nodeCount;  // +0x04
	int leafCount;
	int coordMinGridSpace[3];
	int coordMaxGridSpace[3];
	int coordHalfSizeGridSpace[3];
	int defaultColorIndexBitCount;
	int defaultLightIndexBitCount;
	unsigned int *p_nodeTable;    // +0x38
	int leafTableSize;            // +0x40
	unsigned char *p_leafTable;   // +0x48
};

struct GfxLightGrid  // 0x620
{
	bool hasLightRegions;
	bool useSkyForLowZ;
	unsigned int lastSunPrimaryLightIndex;
	unsigned short mins[3];        // +0x08
	unsigned short maxs[3];        // +0x0E
	unsigned int rowAxis;          // +0x14
	unsigned int colAxis;
	unsigned short *rowDataStart;  // +0x20
	unsigned int rawRowDataSize;   // +0x28
	unsigned char *rawRowData;     // +0x30
	unsigned int entryCount;       // +0x38
	GfxLightGridEntry *entries;    // +0x40
	unsigned int colorCount;       // +0x48
	GfxLightGridColors *colors;    // +0x50
	unsigned int missingGridColorIndex;
	int tableVersion;
	int paletteVersion;
	char rangeExponent8BitsEncoding;
	char rangeExponent12BitsEncoding;
	char rangeExponent16BitsEncoding;
	unsigned char stageCount;            // +0x67
	float *stageLightingContrastGain;    // +0x68
	unsigned int paletteEntryCount;      // +0x70
	int *paletteEntryAddress;            // +0x78
	unsigned int paletteBitstreamSize;   // +0x80
	unsigned char *paletteBitstream;     // +0x88
	float skyLightGridColors[56][3];     // +0x90
	float defaultLightGridColors[56][3]; // +0x330
	GfxLightGridTree tree;               // +0x5D0
};

struct GfxBrushModel  // 0x3C
{
	unsigned char bytes[0x3C];
};

struct MaterialMemory  // 0x10
{
	Material *material;
	int memory;
};

struct sunflare_t  // 0x70
{
	bool hasValidData;
	Material *spriteMaterial;  // +0x08
	Material *flareMaterial;   // +0x10
	unsigned char rest[0x58];
};

struct GfxSceneDynModel  // 6
{
	unsigned char bytes[6];
};

struct GfxSceneDynBrush  // 4
{
	unsigned char bytes[4];
};

struct GfxShadowGeometry  // 0x18
{
	unsigned short surfaceCount;
	unsigned short smodelCount;
	unsigned int *sortedSurfIndex;  // +0x08
	unsigned short *smodelIndex;    // +0x10
};

struct GfxLightRegionAxis  // 0x14
{
	float dir[3];
	float midPoint;
	float halfSize;
};

struct GfxLightRegionHull  // 0x58
{
	float kdopMidPoint[9];
	float kdopHalfSize[9];
	unsigned int axisCount;     // +0x48
	GfxLightRegionAxis *axis;   // +0x50
};

struct GfxLightRegion  // 0x10
{
	unsigned int hullCount;
	GfxLightRegionHull *hulls;  // +0x08
};

struct GfxStaticModelInst  // 0x24
{
	unsigned char bytes[0x24];
};

struct GfxSurface  // 0x28
{
	unsigned int vertexLayerData;
	unsigned int firstVertex;
	float maxEdgeLength;
	unsigned short vertexCount;
	unsigned short triCount;
	unsigned int baseIndex;
	Material *material;           // +0x18
	unsigned long long laf;       // +0x20
};

struct GfxSurfaceBounds  // 0x24 on PC (0x1C in the servers)
{
	unsigned char bytes[0x24];
};

struct GfxStaticModelVertexLighting  // 0x14 on PC
{
	unsigned char bytes[0x14];
};

struct GfxStaticModelVertexLightingInfo  // 0x38 on PC (0x18 in the servers)
{
	GfxStaticModelVertexLighting *lightingValues;
	ID3D11Buffer *lightingValuesVb;                // +0x08
	ID3D11ShaderResourceView *lightingValuesView;  // +0x10
	unsigned char subdivCache[0x18];               // +0x18 (sub_1401B3D60)
	unsigned int pad30;
	unsigned int numLightingValues;                // +0x34
};

struct GfxStaticModelDrawInst  // 0xB0 on PC (0x90 in the servers)
{
	float placement[13];                                // origin, axis[3][3], scale
	XModel *model;                                      // +0x38
	float groundLighting[4];                            // +0x40
	GfxStaticModelVertexLightingInfo vertexLightingInfo; // +0x50
	unsigned char rest[0x28];                           // +0x88
};

struct GfxDrawSurf  // 0x10
{
	unsigned char bytes[0x10];
};

struct GfxWorldDpvsStatic  // 0x118 on PC (0xE0 in the servers)
{
	unsigned int smodelCount;
	unsigned int staticSurfaceCount;
	unsigned int beginEnd[10];
	unsigned int smodelVisDataCount;      // +0x30
	unsigned int surfaceVisDataCount;     // +0x34
	unsigned int *smodelVisData[3];       // +0x38
	unsigned int *surfaceVisData[3];      // +0x50
	unsigned int *smodelVisDataPC[3];     // +0x68: PC only, smodelVisDataCount + 1 words (runtime)
	unsigned int *tessellationCutoffVisData[3];  // +0x80
	unsigned int *smodelWordsPC;          // +0x98: PC only, smodelCount + 1 words (in the zone)
	unsigned int *surfaceVisDataPC[3];    // +0xA0: PC only, surfaceVisDataCount words (runtime)
	unsigned int *sortedSurfIndex;        // +0xB8
	GfxStaticModelInst *smodelInsts;      // +0xC0
	GfxSurface *surfaces;                 // +0xC8
	GfxSurfaceBounds *surfacesBounds;     // +0xD0
	GfxStaticModelDrawInst *smodelDrawInsts;  // +0xD8
	GfxDrawSurf *surfaceMaterials;        // +0xE0
	unsigned int *surfaceCastsSunShadow;  // +0xE8
	unsigned int sunShadowOptCount;       // +0xF0
	unsigned int sunSurfVisDataCount;     // +0xF4
	unsigned int *surfaceCastsSunShadowOpt;  // +0xF8
	unsigned char **constantBuffersLit;   // +0x100
	unsigned char **constantBuffersAmbient;  // +0x108
	int usageCount;                       // +0x110
	unsigned int pad114;
};

struct GfxWorldDpvsDynamic  // 0x50
{
	unsigned int dynEntClientWordCount[2];
	unsigned int dynEntClientCount[2];      // +0x08
	unsigned int *dynEntCellBits[2];        // +0x10
	unsigned char *dynEntVisData[2][3];     // +0x20
};

struct GfxHeroOnlyLight  // 0x44
{
	unsigned char bytes[0x44];
};

struct GfxWorld  // 0xA30 on PC (0x9E8 in the servers)
{
	const char *name;
	const char *baseName;
	unsigned int bspVersion;
	int planeCount;                 // +0x14
	int nodeCount;                  // +0x18
	unsigned int surfaceCount;      // +0x1C
	int skyCount;                   // +0x20
	GfxSky *skies;                  // +0x28
	unsigned int lastSunPrimaryLightIndex;  // +0x30
	unsigned int primaryLightCount;         // +0x34
	unsigned int primaryLightEnvCount;
	unsigned int sortKeys[5];
	GfxWorldDpvsPlanes dpvsPlanes;          // +0x50
	GfxCellTreeCount *aabbTreeCounts;       // +0x70
	GfxCellTree *aabbTrees;                 // +0x78
	GfxCell *cells;                         // +0x80
	GfxWorldDraw draw;                      // +0x88
	GfxLightGrid lightGrid;                 // +0x138
	int modelCount;                         // +0x758
	GfxBrushModel *models;                  // +0x760
	unsigned char bounds[0x18];             // +0x768
	unsigned int checksum;
	int materialMemoryCount;                // +0x784
	MaterialMemory *materialMemory;         // +0x788
	sunflare_t sun;                         // +0x790
	float outdoorLookupMatrix[4][4];        // +0x800
	GfxImage *outdoorImage;                 // +0x840
	unsigned int *cellCasterBits;           // +0x848
	unsigned int *cellHasSunLitSurfsBits;   // +0x850
	GfxSceneDynModel *sceneDynModel;        // +0x858
	GfxSceneDynBrush *sceneDynBrush;        // +0x860
	unsigned int *primaryLightEntityShadowVis;      // +0x868
	unsigned int *primaryLightDynEntShadowVis[2];   // +0x870
	unsigned short *nonSunPrimaryLightForModelDynEnt;  // +0x880
	GfxShadowGeometry *shadowGeom;          // +0x888
	GfxShadowGeometry *shadowGeomOptimized; // +0x890
	GfxLightRegion *lightRegion;            // +0x898
	GfxWorldDpvsStatic dpvs;                // +0x8A0
	GfxWorldDpvsDynamic dpvsDyn;            // +0x9B8
	unsigned int mapVtxChecksum;            // +0xA08
	unsigned int heroOnlyLightCount;        // +0xA0C
	GfxHeroOnlyLight *heroOnlyLights;       // +0xA10
	unsigned char fogTypesAllowed;          // +0xA18
	unsigned char padA19[3];
	unsigned int umbraTomeSize;             // +0xA1C: PC only
	unsigned char *umbraTomeData;           // +0xA20: PC only, 16-aligned
	void *umbraTome;                        // +0xA28: PC only, the tome (1406B8020)
};

static_assert(sizeof(GfxSky) == 0x20, "GfxSky");
static_assert(sizeof(GfxAabbTree) == 0x38, "GfxAabbTree");
static_assert(sizeof(GfxPortal) == 0x50, "GfxPortal");
static_assert(sizeof(GfxCell) == 0x48, "GfxCell");
static_assert(sizeof(GfxWorldDraw) == 0xB0, "GfxWorldDraw");
static_assert(sizeof(GfxLightGrid) == 0x620, "GfxLightGrid");
static_assert(offsetof(GfxLightGrid, stageCount) == 0x67, "stageCount");
static_assert(sizeof(GfxLightGridTree) == 0x50, "GfxLightGridTree");
static_assert(sizeof(GfxBrushModel) == 0x3C, "GfxBrushModel");
static_assert(sizeof(sunflare_t) == 0x70, "sunflare_t");
static_assert(sizeof(GfxLightRegionHull) == 0x58, "GfxLightRegionHull");
static_assert(sizeof(GfxStaticModelVertexLightingInfo) == 0x38, "GfxStaticModelVertexLightingInfo");
static_assert(sizeof(GfxStaticModelDrawInst) == 0xB0, "GfxStaticModelDrawInst");
static_assert(sizeof(GfxSurface) == 0x28, "GfxSurface");
static_assert(sizeof(GfxWorldDpvsStatic) == 0x118, "GfxWorldDpvsStatic");
static_assert(sizeof(GfxWorldDpvsDynamic) == 0x50, "GfxWorldDpvsDynamic");
static_assert(offsetof(GfxWorld, draw) == 0x88, "draw");
static_assert(offsetof(GfxWorld, lightGrid) == 0x138, "lightGrid");
static_assert(offsetof(GfxWorld, materialMemoryCount) == 0x784, "materialMemoryCount");
static_assert(offsetof(GfxWorld, outdoorImage) == 0x840, "outdoorImage");
static_assert(offsetof(GfxWorld, dpvs) == 0x8A0, "dpvs");
static_assert(offsetof(GfxWorld, dpvsDyn) == 0x9B8, "dpvsDyn");
static_assert(offsetof(GfxWorld, umbraTomeSize) == 0xA1C, "umbraTomeSize");
static_assert(sizeof(GfxWorld) == 0xA30, "GfxWorld");

// ComWorld (asset type 0x14, com_map): the map's primary lights. Same layout as the servers'.
struct ComPrimaryLight  // 0x78
{
	unsigned char type;           // 1 sun, 2 spot, 3 omni (docs/assets/world.md)
	unsigned char canUseShadowMap;
	unsigned char exponent;
	unsigned char unused;
	float color[3];               // +0x04
	float dir[3];                 // +0x10
	float up[3];                  // +0x1C
	float origin[3];              // +0x28
	float radius;                 // +0x34
	float cosHalfFovOuter;
	float cosHalfFovInner;
	float cosHalfFovExpanded;
	float rotationLimit;
	float translationLimit;
	float cucRotationOffsetRad;
	float cucRotationSpeedRad;
	float cucScrollVector[2];
	float cucScaleVector[2];
	float cucTransVector[2];
	const char *defName;          // +0x70
};

struct ComPrimaryLightEnv  // 0xA
{
	unsigned short primaryLightIndices[4];
	unsigned char numIndices;
	unsigned char pad;
};

struct ComWorld  // 0x28
{
	const char *name;
	int isInUse;
	unsigned int primaryLightCount;        // +0x0C
	ComPrimaryLight *primaryLights;        // +0x10
	unsigned int primaryLightEnvCount;     // +0x18
	ComPrimaryLightEnv *primaryLightEnvs;  // +0x20
};

static_assert(sizeof(ComPrimaryLight) == 0x78, "ComPrimaryLight");
static_assert(sizeof(ComPrimaryLightEnv) == 0xA, "ComPrimaryLightEnv");
static_assert(sizeof(ComWorld) == 0x28, "ComWorld");

void Load_ComWorld(bool atStreamStart);
void Load_ComWorldPtr(bool atStreamStart);
void Load_ComWorldAsset(ComWorld **world);

// gfx_d3d/r_gfx_world_load_db.cpp
void Load_GfxWorldDpvsPlanes(bool atStreamStart);
void Load_GfxCellTree(bool atStreamStart);
void Load_GfxCell(bool atStreamStart);
void Load_GfxWorldDraw(bool atStreamStart);
void Load_GfxWorldVertexData0(bool atStreamStart);
void Load_GfxWorldVertexLayerData(bool atStreamStart);
void Load_GfxLightGrid(bool atStreamStart);
void Load_GfxLightGridTree(bool atStreamStart);
void Load_GfxShadowGeometryArray(bool atStreamStart, unsigned long long count);
void Load_GfxLightRegion(bool atStreamStart);
void Load_GfxStaticModelVertexLightingInfo(bool atStreamStart);
void sub_140361E10(bool atStreamStart, unsigned long long count);
void Load_GfxWorldDpvsStatic(bool atStreamStart);
void Load_GfxWorldDpvsDynamic(bool atStreamStart);
void Load_GfxWorld(bool atStreamStart);
void Load_GfxWorldPtr(bool atStreamStart);
void Load_GfxWorldAsset(GfxWorld **world);
void sub_1401B7180(void **tome, void *data, unsigned int size);
