// gfx_d3d/r_material_load_db.h (Store build): the zone loaders of GfxWorld (asset type 0x1A).
//
// Generated loader functions (included into database/db_load.cpp). The servers keep only Load_GfxWorldPtr,
// Load_GfxWorld (stripped to the name) and Load_GfxWorldAsset; everything below is the Store build's, named after the
// generator's Load_<Type> convention for the struct each one loads (docs/assets/world.md). GPU buffers are created
// right after their data is loaded (src/gfx_d3d/r_buffers.cpp). tools/fastfile/gfxworld.py is the same logic in
// Python, checked against the game on real maps.

#include "gfx_d3d/r_gfx_world.h"
#include "gfx_d3d/r_xsurface.h"

extern GfxWorld *varGfxWorld;                        // Store 144426918
extern GfxWorld **varGfxWorldPtr;                    // Store 144426920
extern GfxSky *varGfxSky;                            // Store 144426900
extern int *varint;                                  // Store 144424A88
extern GfxWorldDpvsPlanes *varGfxWorldDpvsPlanes;    // Store 1444268F8
extern cplane_s *varcplane_t;                        // Store 144424980
extern unsigned int *varraw_uint;                    // Store 144424BF8
extern GfxCellTree *varGfxCellTree;                  // Store 144426858
extern GfxAabbTree *varGfxAabbTree;                  // Store 144426848
extern unsigned short *varGfxAabbTreeSmodelIndexes;  // Store 144426840
extern GfxCellTreeCount *varGfxCellTreeCount;        // Store 144426850
extern GfxCell *varGfxCell;                          // Store 144426860
extern GfxPortal *varGfxPortal;                      // Store 144426868
extern float (*varvec3_t)[3];                        // Store 144424C88
extern GfxWorldDraw *varGfxWorldDraw;                // Store 144426910
extern GfxReflectionProbe *varGfxReflectionProbe;    // Store 144426780
extern GfxReflectionProbeVolumeData *varGfxReflectionProbeVolumeData;  // Store 144426778
extern GfxTexture *varGfxRawTexture;                 // Store 144425840
extern GfxReflectionProbeReferenceOrigin *varGfxReflectionProbeReferenceOrigin;  // Store 144426788
extern GfxReflectionProbeReference *varGfxReflectionProbeReference;  // Store 144426790
extern GfxLightmapArray *varGfxLightmapArray;        // Store 144427200
extern GfxWorldVertexData0 *varGfxWorldVertexData0;  // Store 144426890
extern GfxWorldVertex *varGfxWorldVertex0;           // Store 144427038
extern GfxWorldVertexLayerData *varGfxWorldVertexLayerData;  // Store 144426898
extern unsigned char *varGfxWorldVertexLayerBytes;   // Store 144425048
extern GfxLightGrid *varGfxLightGrid;                // Store 1444268A8
extern GfxLightGridEntry *varGfxLightGridEntry;      // Store 144426870
extern GfxLightGridColors *varGfxLightGridColors;    // Store 144426878
extern GfxLightGridTree *varGfxLightGridTree;        // Store 1444268A0
extern GfxBrushModel *varGfxBrushModel;              // Store 144427108
extern MaterialMemory *varMaterialMemory;            // Store 144426888
extern sunflare_t *varsunflare_t;                    // Store 144426768
extern GfxSceneDynModel *varGfxSceneDynModel;        // Store 1444268B0
extern GfxSceneDynBrush *varGfxSceneDynBrush;        // Store 1444268B8
extern unsigned short *varraw_ushort;                // Store 144424BE8
extern GfxShadowGeometry *varGfxShadowGeometry;      // Store 1444268C8
extern unsigned int *varuint_t;                      // Store 144427008
extern GfxLightRegion *varGfxLightRegion;            // Store 1444268E0
extern GfxLightRegionHull *varGfxLightRegionHull;    // Store 1444268D8
extern GfxLightRegionAxis *varGfxLightRegionAxis;    // Store 1444268D0
extern GfxWorldDpvsStatic *varGfxWorldDpvsStatic;    // Store 1444268F0
extern unsigned int *varraw_uint128;                 // Store 144424C18
extern GfxStaticModelInst *varGfxStaticModelInst;    // Store 144426590
extern GfxSurface *varGfxSurface;                    // Store 1444271F8
extern GfxSurfaceBounds *varGfxSurfaceBounds;        // Store 1444271D8
extern GfxStaticModelDrawInst *varGfxStaticModelDrawInst;  // Store 144426588
extern GfxStaticModelVertexLightingInfo *varGfxStaticModelVertexLightingInfo;  // Store 144426578
extern GfxStaticModelVertexLighting *varGfxStaticModelVertexLighting;  // Store 144427028
extern GfxDrawSurf *varGfxDrawSurf;                  // Store 1444268C0
extern unsigned char **varGfxConstantBufferPtr;      // Store 144424C58
extern unsigned char *varGfxConstantBufferByte;      // Store 144424A08
extern GfxWorldDpvsDynamic *varGfxWorldDpvsDynamic;  // Store 1444268E8
extern unsigned char *varraw_byte16;                 // Store 144424C38
extern GfxHeroOnlyLight *varGfxHeroOnlyLight;        // Store 144426808
extern unsigned char *varbyte16;                     // Store 144424B08
extern void **varUmbraTome;                          // Store 144426828
extern ID3D11ShaderResourceView **varGfxShaderView;  // Store 144425028
extern GfxSubdivCache *unk_144425088;                // Store 144425088
extern ID3D11Buffer **varGfxVertexBuffer;            // Store 144425020
extern ID3D11Buffer **varGfxIndexBuffer;             // Store 1444250B0
extern unsigned short *varalignIndBufUShort_t;       // Store 144425040
extern unsigned short *varushort;                    // Store 144424D18
extern unsigned int *varuint;                        // Store 144424B68
extern float *varfloat;                              // Store 144424B98
extern unsigned char *varbyte;                       // Store 144424A18
extern GfxImage **varGfxImagePtr;                    // Store 144425868
extern Material **varMaterialHandle;                 // Store 144425D20
extern XModel **varXModelPtr;                        // Store 1444267F8

void Load_GfxImagePtr(bool atStreamStart);
void Load_MaterialHandle(bool atStreamStart);
void Load_XModelPtr(bool atStreamStart);
void sub_1401B3D60(GfxSubdivCache *cache);
int sub_1406B8020(void **tome, void *data, unsigned long long size);  // Store 1406B8020 (Umbra)

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// Store 140350CA0
void Load_GfxWorldDpvsPlanes(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxWorldDpvsPlanes, sizeof(GfxWorldDpvsPlanes));
	if (varGfxWorldDpvsPlanes->planes)
	{
		if ((unsigned long long)varGfxWorldDpvsPlanes->planes == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varGfxWorldDpvsPlanes->planes = (cplane_s *)g_streamPos;
			varcplane_t = (cplane_s *)g_streamPos;
			Load_Stream(true, g_streamPos, (long long)varGfxWorld->planeCount * 0x14);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varGfxWorldDpvsPlanes->planes);
		}
	}
	if (varGfxWorldDpvsPlanes->nodes)
	{
		ALIGN_POS(2);
		varGfxWorldDpvsPlanes->nodes = (unsigned short *)g_streamPos;
		varushort = (unsigned short *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxWorld->nodeCount * 2);
	}
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varGfxWorldDpvsPlanes->sceneEntCellBits)
	{
		ALIGN_POS(4);
		varGfxWorldDpvsPlanes->sceneEntCellBits = (unsigned int *)g_streamPos;
		varraw_uint = (unsigned int *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)(varGfxWorldDpvsPlanes->cellCount << 9) * 4);
	}
	DB_PopStreamPos();
}

// Store 14034EE10
void Load_GfxCellTree(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxCellTree, sizeof(GfxCellTree));
	if (!varGfxCellTree->aabbTree)
		return;
	ALIGN_POS(4);
	varGfxCellTree->aabbTree = (GfxAabbTree *)g_streamPos;
	varGfxAabbTree = (GfxAabbTree *)g_streamPos;
	long long index = varGfxCellTree - varGfxWorld->aabbTrees;
	long long count = varGfxWorld->aabbTreeCounts[index].aabbTreeCount;
	Load_Stream(true, g_streamPos, count * sizeof(GfxAabbTree));
	GfxAabbTree *tree = varGfxAabbTree;
	for (; count; count--)
	{
		varGfxAabbTree = tree;
		Load_Stream(false, tree, sizeof(GfxAabbTree));
		if (varGfxAabbTree->smodelIndexes)
		{
			if ((unsigned long long)varGfxAabbTree->smodelIndexes == DB_PTR_FOLLOWING)
			{
				ALIGN_POS(2);
				varGfxAabbTree->smodelIndexes = (unsigned short *)g_streamPos;
				varGfxAabbTreeSmodelIndexes = (unsigned short *)g_streamPos;
				Load_Stream(true, g_streamPos, (unsigned long long)varGfxAabbTree->smodelIndexCount * 2);
			}
			else
			{
				DB_ConvertOffsetToPointer((unsigned long long *)&varGfxAabbTree->smodelIndexes);
			}
		}
		tree++;
	}
}

// Store 14034EC90
void Load_GfxCell(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxCell, sizeof(GfxCell));
	if (varGfxCell->portals)
	{
		ALIGN_POS(4);
		varGfxCell->portals = (GfxPortal *)g_streamPos;
		varGfxPortal = (GfxPortal *)g_streamPos;
		long long count = varGfxCell->portalCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxPortal));
		GfxPortal *portal = varGfxPortal;
		for (; count; count--)
		{
			varGfxPortal = portal;
			Load_Stream(false, portal, sizeof(GfxPortal));
			if (varGfxPortal->vertices)
			{
				ALIGN_POS(4);
				varGfxPortal->vertices = (float (*)[3])g_streamPos;
				varvec3_t = (float (*)[3])g_streamPos;
				Load_Stream(true, g_streamPos, (unsigned long long)varGfxPortal->vertexCount * 0xC);
			}
			portal++;
		}
	}
	if (varGfxCell->reflectionProbes)
	{
		varGfxCell->reflectionProbes = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxCell->reflectionProbeCount);
	}
	if (varGfxCell->reflectionProbeReferences)
	{
		varGfxCell->reflectionProbeReferences = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxCell->reflectionProbeReferenceCount);
	}
}

// Store 140351E00
void Load_GfxWorldVertexData0(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxWorldVertexData0, sizeof(GfxWorldVertexData0));
	if (varGfxWorldVertexData0->vertices)
	{
		ALIGN_POS(4);
		varGfxWorldVertexData0->vertices = (GfxWorldVertex *)g_streamPos;
		varGfxWorldVertex0 = (GfxWorldVertex *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxWorldDraw->vertexCount * sizeof(GfxWorldVertex));
	}
	ID3D11Buffer **vb = &varGfxWorldVertexData0->worldVb;
	varGfxVertexBuffer = vb;
	Load_Stream(false, vb, 8);
	Load_VertexBuffer(vb, varGfxWorldVertexData0->vertices, (int)varGfxWorldDraw->vertexCount * (int)sizeof(GfxWorldVertex));
}

// Store 140351EB0
void Load_GfxWorldVertexLayerData(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxWorldVertexLayerData, sizeof(GfxWorldVertexLayerData));
	if (varGfxWorldVertexLayerData->data)
	{
		varGfxWorldVertexLayerData->data = g_streamPos;
		varGfxWorldVertexLayerBytes = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxWorldDraw->vertexLayerDataSize);
	}
	ID3D11Buffer **vb = &varGfxWorldVertexLayerData->layerVb;
	varGfxVertexBuffer = vb;
	Load_Stream(false, vb, 8);
	Load_VertexBuffer(vb, varGfxWorldDraw->vld.data, (int)varGfxWorldDraw->vertexLayerDataSize);
}

// Store 140351830
void Load_GfxWorldDraw(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxWorldDraw, sizeof(GfxWorldDraw));
	if (varGfxWorldDraw->reflectionProbes)
	{
		ALIGN_POS(8);
		varGfxWorldDraw->reflectionProbes = (GfxImage **)g_streamPos;
		varGfxImagePtr = (GfxImage **)g_streamPos;
		unsigned long long count = varGfxWorldDraw->reflectionProbeCount;
		Load_Stream(true, g_streamPos, count * 8);
		GfxImage **image = varGfxImagePtr;
		for (; count; count--)
		{
			varGfxImagePtr = image;
			Load_GfxImagePtr(false);
			image++;
		}
	}
	if (varGfxWorldDraw->reflectionProbeOrigins)
	{
		ALIGN_POS(4);
		varGfxWorldDraw->reflectionProbeOrigins = (GfxReflectionProbe *)g_streamPos;
		varGfxReflectionProbe = (GfxReflectionProbe *)g_streamPos;
		unsigned int count = varGfxWorldDraw->reflectionProbeCount;
		Load_Stream(true, g_streamPos, (unsigned long long)count * sizeof(GfxReflectionProbe));
		GfxReflectionProbe *probe = varGfxReflectionProbe;
		for (unsigned long long left = count; left; left--)
		{
			varGfxReflectionProbe = probe;
			Load_Stream(false, probe, sizeof(GfxReflectionProbe));
			if (varGfxReflectionProbe->probeVolumes)
			{
				ALIGN_POS(4);
				varGfxReflectionProbe->probeVolumes = (GfxReflectionProbeVolumeData *)g_streamPos;
				varGfxReflectionProbeVolumeData = (GfxReflectionProbeVolumeData *)g_streamPos;
				Load_Stream(true, g_streamPos,
				            (unsigned long long)varGfxReflectionProbe->probeVolumeCount * sizeof(GfxReflectionProbeVolumeData));
			}
			probe++;
		}
	}
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varGfxWorldDraw->reflectionProbeTextures)
	{
		ALIGN_POS(4);
		varGfxWorldDraw->reflectionProbeTextures = (GfxTexture *)g_streamPos;
		varGfxRawTexture = (GfxTexture *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxWorldDraw->reflectionProbeCount * sizeof(GfxTexture));
	}
	DB_PopStreamPos();
	if (varGfxWorldDraw->reflectionProbeReferenceOrigins)
	{
		ALIGN_POS(4);
		varGfxWorldDraw->reflectionProbeReferenceOrigins = (GfxReflectionProbeReferenceOrigin *)g_streamPos;
		varGfxReflectionProbeReferenceOrigin = (GfxReflectionProbeReferenceOrigin *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxWorldDraw->reflectionProbeReferenceCount * 0xC);
	}
	if (varGfxWorldDraw->reflectionProbeReferences)
	{
		varGfxWorldDraw->reflectionProbeReferences = (GfxReflectionProbeReference *)g_streamPos;
		varGfxReflectionProbeReference = (GfxReflectionProbeReference *)g_streamPos;
		Load_Stream(true, g_streamPos, varGfxWorldDraw->reflectionProbeReferenceCount);
	}
	if (varGfxWorldDraw->lightmaps)
	{
		ALIGN_POS(4);
		varGfxWorldDraw->lightmaps = (GfxLightmapArray *)g_streamPos;
		varGfxLightmapArray = (GfxLightmapArray *)g_streamPos;
		long long count = varGfxWorldDraw->lightmapCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxLightmapArray));
		GfxLightmapArray *lightmap = varGfxLightmapArray;
		for (; count; count--)
		{
			varGfxLightmapArray = lightmap;
			Load_Stream(false, lightmap, sizeof(GfxLightmapArray));
			varGfxImagePtr = &varGfxLightmapArray->primary;
			Load_GfxImagePtr(false);
			varGfxImagePtr = &varGfxLightmapArray->secondary;
			Load_GfxImagePtr(false);
			lightmap++;
		}
	}
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varGfxWorldDraw->lightmapPrimaryTextures)
	{
		ALIGN_POS(4);
		varGfxWorldDraw->lightmapPrimaryTextures = (GfxTexture *)g_streamPos;
		varGfxRawTexture = (GfxTexture *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxWorldDraw->lightmapCount * sizeof(GfxTexture));
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (varGfxWorldDraw->lightmapSecondaryTextures)
	{
		ALIGN_POS(4);
		varGfxWorldDraw->lightmapSecondaryTextures = (GfxTexture *)g_streamPos;
		varGfxRawTexture = (GfxTexture *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxWorldDraw->lightmapCount * sizeof(GfxTexture));
	}
	DB_PopStreamPos();
	varGfxImagePtr = &varGfxWorldDraw->lightmapOverridePrimary;
	Load_GfxImagePtr(false);
	varGfxImagePtr = &varGfxWorldDraw->lightmapOverrideSecondary;
	Load_GfxImagePtr(false);
	varGfxWorldVertexData0 = &varGfxWorldDraw->vd;
	Load_GfxWorldVertexData0(false);
	varGfxWorldVertexLayerData = &varGfxWorldDraw->vld;
	Load_GfxWorldVertexLayerData(false);
	if (varGfxWorldDraw->indices)
	{
		ALIGN_POS(2);
		varGfxWorldDraw->indices = (unsigned short *)g_streamPos;
		varalignIndBufUShort_t = (unsigned short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxWorldDraw->indexCount * 2);
	}
	ID3D11Buffer **ib = &varGfxWorldDraw->indexBuffer;
	varGfxIndexBuffer = ib;
	Load_Stream(false, ib, 8);
	Load_IndexBuffer(ib, varGfxWorldDraw->indices, (int)varGfxWorldDraw->indexCount);
}

// Store 14034F8A0
void Load_GfxLightGridTree(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxLightGridTree, sizeof(GfxLightGridTree));
	if (varGfxLightGridTree->p_nodeTable)
	{
		ALIGN_POS(4);
		varGfxLightGridTree->p_nodeTable = (unsigned int *)g_streamPos;
		varuint = (unsigned int *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxLightGridTree->nodeCount * 4);
	}
	if (varGfxLightGridTree->p_leafTable)
	{
		varGfxLightGridTree->p_leafTable = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxLightGridTree->leafTableSize);
	}
}

// Store 14034F650
void Load_GfxLightGrid(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxLightGrid, sizeof(GfxLightGrid));
	if (varGfxLightGrid->rowDataStart)
	{
		ALIGN_POS(2);
		varGfxLightGrid->rowDataStart = (unsigned short *)g_streamPos;
		varushort = (unsigned short *)g_streamPos;
		unsigned int axis = varGfxLightGrid->rowAxis;
		Load_Stream(true, g_streamPos,
		            (long long)(int)((unsigned int)varGfxLightGrid->maxs[axis] - (unsigned int)varGfxLightGrid->mins[axis] + 1) * 2);
	}
	if (varGfxLightGrid->rawRowData)
	{
		varGfxLightGrid->rawRowData = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxLightGrid->rawRowDataSize);
	}
	if (varGfxLightGrid->entries)
	{
		ALIGN_POS(4);
		varGfxLightGrid->entries = (GfxLightGridEntry *)g_streamPos;
		varGfxLightGridEntry = (GfxLightGridEntry *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxLightGrid->entryCount * sizeof(GfxLightGridEntry));
	}
	if (varGfxLightGrid->colors)
	{
		ALIGN_POS(4);
		varGfxLightGrid->colors = (GfxLightGridColors *)g_streamPos;
		varGfxLightGridColors = (GfxLightGridColors *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxLightGrid->colorCount * sizeof(GfxLightGridColors));
	}
	if (varGfxLightGrid->stageLightingContrastGain)
	{
		ALIGN_POS(4);
		varGfxLightGrid->stageLightingContrastGain = (float *)g_streamPos;
		varfloat = (float *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxLightGrid->stageCount * 4);
	}
	if (varGfxLightGrid->paletteEntryAddress)
	{
		ALIGN_POS(4);
		varGfxLightGrid->paletteEntryAddress = (int *)g_streamPos;
		varint = (int *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxLightGrid->paletteEntryCount * 4);
	}
	if (varGfxLightGrid->paletteBitstream)
	{
		varGfxLightGrid->paletteBitstream = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxLightGrid->paletteBitstreamSize);
	}
	varGfxLightGridTree = &varGfxLightGrid->tree;
	Load_GfxLightGridTree(false);
}

// Store 14034FBD0
void Load_GfxShadowGeometryArray(bool atStreamStart, unsigned long long count)
{
	unsigned long long left = count;
	Load_Stream(atStreamStart, varGfxShadowGeometry, left * sizeof(GfxShadowGeometry));
	GfxShadowGeometry *geom = varGfxShadowGeometry;
	for (; left; left--)
	{
		varGfxShadowGeometry = geom;
		Load_Stream(false, geom, sizeof(GfxShadowGeometry));
		if (varGfxShadowGeometry->sortedSurfIndex)
		{
			ALIGN_POS(4);
			varGfxShadowGeometry->sortedSurfIndex = (unsigned int *)g_streamPos;
			varuint_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varGfxShadowGeometry->surfaceCount * 4);
		}
		if (varGfxShadowGeometry->smodelIndex)
		{
			ALIGN_POS(2);
			varGfxShadowGeometry->smodelIndex = (unsigned short *)g_streamPos;
			varushort = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varGfxShadowGeometry->smodelCount * 2);
		}
		geom++;
	}
}

// Store 14034F950
void Load_GfxLightRegion(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxLightRegion, sizeof(GfxLightRegion));
	if (!varGfxLightRegion->hulls)
		return;
	ALIGN_POS(4);
	varGfxLightRegion->hulls = (GfxLightRegionHull *)g_streamPos;
	varGfxLightRegionHull = (GfxLightRegionHull *)g_streamPos;
	unsigned long long count = varGfxLightRegion->hullCount;
	Load_Stream(true, g_streamPos, count * sizeof(GfxLightRegionHull));
	GfxLightRegionHull *hull = varGfxLightRegionHull;
	for (; count; count--)
	{
		varGfxLightRegionHull = hull;
		Load_Stream(false, hull, sizeof(GfxLightRegionHull));
		if (varGfxLightRegionHull->axis)
		{
			ALIGN_POS(4);
			varGfxLightRegionHull->axis = (GfxLightRegionAxis *)g_streamPos;
			varGfxLightRegionAxis = (GfxLightRegionAxis *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varGfxLightRegionHull->axisCount * sizeof(GfxLightRegionAxis));
		}
		hull++;
	}
}

// Store 14034FD70
void Load_GfxStaticModelVertexLightingInfo(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxStaticModelVertexLightingInfo, sizeof(GfxStaticModelVertexLightingInfo));
	if (varGfxStaticModelVertexLightingInfo->lightingValues)
	{
		ALIGN_POS(4);
		varGfxStaticModelVertexLightingInfo->lightingValues = (GfxStaticModelVertexLighting *)g_streamPos;
		varGfxStaticModelVertexLighting = (GfxStaticModelVertexLighting *)g_streamPos;
		Load_Stream(true, g_streamPos,
		            (unsigned long long)varGfxStaticModelVertexLightingInfo->numLightingValues * sizeof(GfxStaticModelVertexLighting));
	}
	ID3D11Buffer **vb = &varGfxStaticModelVertexLightingInfo->lightingValuesVb;
	varGfxVertexBuffer = vb;
	Load_Stream(false, vb, 8);
	Load_VertexBuffer(vb, varGfxStaticModelVertexLightingInfo->lightingValues,
	                  (int)varGfxStaticModelVertexLightingInfo->numLightingValues * (int)sizeof(GfxStaticModelVertexLighting));
	ID3D11ShaderResourceView **view = &varGfxStaticModelVertexLightingInfo->lightingValuesView;
	varGfxShaderView = view;
	Load_Stream(false, view, 8);
	Load_VertexBufferView(view, varGfxStaticModelVertexLightingInfo->lightingValuesVb,
	                      varGfxStaticModelVertexLightingInfo->numLightingValues * (unsigned int)sizeof(GfxStaticModelVertexLighting),
	                      "lightingValuesView");
	GfxSubdivCache *cache = (GfxSubdivCache *)varGfxStaticModelVertexLightingInfo->subdivCache;
	unk_144425088 = cache;
	Load_Stream(false, cache, 0x18);
	sub_1401B3D60(cache);
}

// Store 140361E10 (name unknown): count pointers, each non-null one to 1 byte loaded where it points
void sub_140361E10(bool atStreamStart, unsigned long long count)
{
	unsigned long long left = count;
	Load_Stream(atStreamStart, varGfxConstantBufferPtr, left * 8);
	unsigned char **ptr = varGfxConstantBufferPtr;
	for (; left; left--)
	{
		varGfxConstantBufferPtr = ptr;
		Load_Stream(false, ptr, 8);
		if (*varGfxConstantBufferPtr)
		{
			*varGfxConstantBufferPtr = g_streamPos;
			varGfxConstantBufferByte = g_streamPos;
			Load_Stream(true, g_streamPos, 1);
		}
		ptr++;
	}
}

#define RUNTIME_ARRAY(field, var, type, align, bytes)                     \
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);                               \
	if (field)                                                           \
	{                                                                    \
		ALIGN_POS(align);                                                \
		field = (type *)g_streamPos;                                     \
		var = (type *)g_streamPos;                                       \
		Load_Stream(true, g_streamPos, (bytes));                         \
	}                                                                    \
	DB_PopStreamPos()

// Store 140350DD0
void Load_GfxWorldDpvsStatic(bool atStreamStart)
{
	GfxWorldDpvsStatic *&d = varGfxWorldDpvsStatic;
	Load_Stream(atStreamStart, d, sizeof(GfxWorldDpvsStatic));
	RUNTIME_ARRAY(d->smodelVisData[0], varraw_uint128, unsigned int, 128, (unsigned long long)d->smodelVisDataCount * 4);
	RUNTIME_ARRAY(d->smodelVisData[1], varraw_uint128, unsigned int, 128, (unsigned long long)d->smodelVisDataCount * 4);
	RUNTIME_ARRAY(d->smodelVisData[2], varraw_uint128, unsigned int, 128, (unsigned long long)d->smodelVisDataCount * 4);
	RUNTIME_ARRAY(d->surfaceVisData[0], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->surfaceVisData[1], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->surfaceVisData[2], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->smodelVisDataPC[0], varraw_uint128, unsigned int, 128, (unsigned long long)(d->smodelVisDataCount + 1) * 4);
	RUNTIME_ARRAY(d->smodelVisDataPC[1], varraw_uint128, unsigned int, 128, (unsigned long long)(d->smodelVisDataCount + 1) * 4);
	RUNTIME_ARRAY(d->smodelVisDataPC[2], varraw_uint128, unsigned int, 128, (unsigned long long)(d->smodelVisDataCount + 1) * 4);
	RUNTIME_ARRAY(d->tessellationCutoffVisData[0], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->tessellationCutoffVisData[1], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->tessellationCutoffVisData[2], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	if (d->smodelWordsPC)
	{
		ALIGN_POS(4);
		d->smodelWordsPC = (unsigned int *)g_streamPos;
		varuint = (unsigned int *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)(d->smodelCount + 1) * 4);
	}
	RUNTIME_ARRAY(d->surfaceVisDataPC[0], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->surfaceVisDataPC[1], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->surfaceVisDataPC[2], varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	if (d->sortedSurfIndex)
	{
		ALIGN_POS(4);
		d->sortedSurfIndex = (unsigned int *)g_streamPos;
		varuint_t = (unsigned int *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)d->staticSurfaceCount * 4);
	}
	if (d->smodelInsts)
	{
		ALIGN_POS(4);
		d->smodelInsts = (GfxStaticModelInst *)g_streamPos;
		varGfxStaticModelInst = (GfxStaticModelInst *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)d->smodelCount * sizeof(GfxStaticModelInst));
	}
	if (d->surfaces)
	{
		ALIGN_POS(4);
		d->surfaces = (GfxSurface *)g_streamPos;
		varGfxSurface = (GfxSurface *)g_streamPos;
		unsigned long long count = varGfxWorld->surfaceCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxSurface));
		GfxSurface *surface = varGfxSurface;
		for (; count; count--)
		{
			varGfxSurface = surface;
			Load_Stream(false, surface, sizeof(GfxSurface));
			varMaterialHandle = &varGfxSurface->material;
			Load_MaterialHandle(false);
			surface++;
		}
	}
	if (d->surfacesBounds)
	{
		ALIGN_POS(4);
		d->surfacesBounds = (GfxSurfaceBounds *)g_streamPos;
		varGfxSurfaceBounds = (GfxSurfaceBounds *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxWorld->surfaceCount * sizeof(GfxSurfaceBounds));
	}
	if (d->smodelDrawInsts)
	{
		ALIGN_POS(4);
		d->smodelDrawInsts = (GfxStaticModelDrawInst *)g_streamPos;
		varGfxStaticModelDrawInst = (GfxStaticModelDrawInst *)g_streamPos;
		unsigned long long count = d->smodelCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxStaticModelDrawInst));
		GfxStaticModelDrawInst *inst = varGfxStaticModelDrawInst;
		for (; count; count--)
		{
			varGfxStaticModelDrawInst = inst;
			Load_Stream(false, inst, sizeof(GfxStaticModelDrawInst));
			varXModelPtr = &varGfxStaticModelDrawInst->model;
			Load_XModelPtr(false);
			varGfxStaticModelVertexLightingInfo = &varGfxStaticModelDrawInst->vertexLightingInfo;
			Load_GfxStaticModelVertexLightingInfo(false);
			inst++;
		}
	}
	RUNTIME_ARRAY(d->surfaceMaterials, varGfxDrawSurf, GfxDrawSurf, 8, (unsigned long long)varGfxWorld->surfaceCount * sizeof(GfxDrawSurf));
	RUNTIME_ARRAY(d->surfaceCastsSunShadow, varraw_uint128, unsigned int, 128, (unsigned long long)d->surfaceVisDataCount * 4);
	RUNTIME_ARRAY(d->surfaceCastsSunShadowOpt, varraw_uint128, unsigned int, 128,
	              (unsigned long long)(d->sunSurfVisDataCount * d->sunShadowOptCount) * 4);
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (d->constantBuffersLit)
	{
		ALIGN_POS(8);
		d->constantBuffersLit = (unsigned char **)g_streamPos;
		varGfxConstantBufferPtr = (unsigned char **)g_streamPos;
		sub_140361E10(true, d->smodelCount);
	}
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_RUNTIME);
	if (d->constantBuffersAmbient)
	{
		ALIGN_POS(8);
		d->constantBuffersAmbient = (unsigned char **)g_streamPos;
		varGfxConstantBufferPtr = (unsigned char **)g_streamPos;
		sub_140361E10(true, d->smodelCount);
	}
	DB_PopStreamPos();
}

// Store 140350990
void Load_GfxWorldDpvsDynamic(bool atStreamStart)
{
	GfxWorldDpvsDynamic *&d = varGfxWorldDpvsDynamic;
	Load_Stream(atStreamStart, d, sizeof(GfxWorldDpvsDynamic));
	RUNTIME_ARRAY(d->dynEntCellBits[0], varraw_uint, unsigned int, 4,
	              (unsigned long long)(unsigned int)(varGfxWorld->dpvsPlanes.cellCount * d->dynEntClientWordCount[0]) * 4);
	RUNTIME_ARRAY(d->dynEntCellBits[1], varraw_uint, unsigned int, 4,
	              (unsigned long long)(unsigned int)(varGfxWorld->dpvsPlanes.cellCount * d->dynEntClientWordCount[1]) * 4);
	RUNTIME_ARRAY(d->dynEntVisData[0][0], varraw_byte16, unsigned char, 16, (unsigned long long)d->dynEntClientWordCount[0] << 5);
	RUNTIME_ARRAY(d->dynEntVisData[1][0], varraw_byte16, unsigned char, 16, (unsigned long long)d->dynEntClientWordCount[1] << 5);
	RUNTIME_ARRAY(d->dynEntVisData[0][1], varraw_byte16, unsigned char, 16, (unsigned long long)d->dynEntClientWordCount[0] << 5);
	RUNTIME_ARRAY(d->dynEntVisData[1][1], varraw_byte16, unsigned char, 16, (unsigned long long)d->dynEntClientWordCount[1] << 5);
	RUNTIME_ARRAY(d->dynEntVisData[0][2], varraw_byte16, unsigned char, 16, (unsigned long long)d->dynEntClientWordCount[0] << 5);
	RUNTIME_ARRAY(d->dynEntVisData[1][2], varraw_byte16, unsigned char, 16, (unsigned long long)d->dynEntClientWordCount[1] << 5);
}

// Store 1401B7180 (name unknown): the Umbra tome pointer from the tome data, null without data
void sub_1401B7180(void **tome, void *data, unsigned int size)
{
	if (data)
	{
		sub_1406B8020(tome, data, size);
		return;
	}
	*tome = nullptr;
}

// Store 14034FF30
void Load_GfxWorld(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxWorld, sizeof(GfxWorld));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varGfxWorld->name;
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
	varXString = &varGfxWorld->baseName;
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
	if (varGfxWorld->skies)
	{
		ALIGN_POS(4);
		varGfxWorld->skies = (GfxSky *)g_streamPos;
		varGfxSky = (GfxSky *)g_streamPos;
		long long count = varGfxWorld->skyCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxSky));
		GfxSky *sky = varGfxSky;
		for (; count; count--)
		{
			varGfxSky = sky;
			Load_Stream(false, sky, sizeof(GfxSky));
			if (varGfxSky->skyStartSurfs)
			{
				ALIGN_POS(4);
				varGfxSky->skyStartSurfs = (int *)g_streamPos;
				varint = (int *)g_streamPos;
				Load_Stream(true, g_streamPos, (long long)varGfxSky->skySurfCount * 4);
			}
			varGfxImagePtr = &varGfxSky->skyImage;
			Load_GfxImagePtr(false);
			sky++;
		}
	}
	varGfxWorldDpvsPlanes = &varGfxWorld->dpvsPlanes;
	Load_GfxWorldDpvsPlanes(false);
	if (varGfxWorld->aabbTreeCounts)
	{
		ALIGN_POS(4);
		varGfxWorld->aabbTreeCounts = (GfxCellTreeCount *)g_streamPos;
		varGfxCellTreeCount = (GfxCellTreeCount *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxWorld->dpvsPlanes.cellCount * 4);
	}
	if (varGfxWorld->aabbTrees)
	{
		ALIGN_POS(128);
		varGfxWorld->aabbTrees = (GfxCellTree *)g_streamPos;
		varGfxCellTree = (GfxCellTree *)g_streamPos;
		long long count = varGfxWorld->dpvsPlanes.cellCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxCellTree));
		GfxCellTree *tree = varGfxCellTree;
		for (; count; count--)
		{
			varGfxCellTree = tree;
			Load_GfxCellTree(false);
			tree++;
		}
	}
	if (varGfxWorld->cells)
	{
		ALIGN_POS(4);
		varGfxWorld->cells = (GfxCell *)g_streamPos;
		varGfxCell = (GfxCell *)g_streamPos;
		long long count = varGfxWorld->dpvsPlanes.cellCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxCell));
		GfxCell *cell = varGfxCell;
		for (; count; count--)
		{
			varGfxCell = cell;
			Load_GfxCell(false);
			cell++;
		}
	}
	varGfxWorldDraw = &varGfxWorld->draw;
	Load_GfxWorldDraw(false);
	varGfxLightGrid = &varGfxWorld->lightGrid;
	Load_GfxLightGrid(false);
	if (varGfxWorld->models)
	{
		ALIGN_POS(4);
		varGfxWorld->models = (GfxBrushModel *)g_streamPos;
		varGfxBrushModel = (GfxBrushModel *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varGfxWorld->modelCount * sizeof(GfxBrushModel));
	}
	if (varGfxWorld->materialMemory)
	{
		ALIGN_POS(4);
		varGfxWorld->materialMemory = (MaterialMemory *)g_streamPos;
		varMaterialMemory = (MaterialMemory *)g_streamPos;
		long long count = varGfxWorld->materialMemoryCount;
		Load_Stream(true, g_streamPos, count * sizeof(MaterialMemory));
		MaterialMemory *memory = varMaterialMemory;
		for (; count; count--)
		{
			varMaterialMemory = memory;
			Load_Stream(false, memory, sizeof(MaterialMemory));
			varMaterialHandle = &varMaterialMemory->material;
			Load_MaterialHandle(false);
			memory++;
		}
	}
	varsunflare_t = &varGfxWorld->sun;
	Load_Stream(false, varsunflare_t, sizeof(sunflare_t));
	varMaterialHandle = &varsunflare_t->spriteMaterial;
	Load_MaterialHandle(false);
	varMaterialHandle = &varsunflare_t->flareMaterial;
	Load_MaterialHandle(false);
	varGfxImagePtr = &varGfxWorld->outdoorImage;
	Load_GfxImagePtr(false);
	int cells = varGfxWorld->dpvsPlanes.cellCount;
	RUNTIME_ARRAY(varGfxWorld->cellCasterBits, varraw_uint, unsigned int, 4,
	              (long long)(((varGfxWorld->dpvsPlanes.cellCount + 31) >> 5) * varGfxWorld->dpvsPlanes.cellCount) * 4);
	RUNTIME_ARRAY(varGfxWorld->cellHasSunLitSurfsBits, varraw_uint, unsigned int, 4,
	              (long long)((varGfxWorld->dpvsPlanes.cellCount + 31) >> 5) * 4);
	(void)cells;
	RUNTIME_ARRAY(varGfxWorld->sceneDynModel, varGfxSceneDynModel, GfxSceneDynModel, 4,
	              (unsigned long long)varGfxWorld->dpvsDyn.dynEntClientCount[0] * sizeof(GfxSceneDynModel));
	RUNTIME_ARRAY(varGfxWorld->sceneDynBrush, varGfxSceneDynBrush, GfxSceneDynBrush, 4,
	              (unsigned long long)varGfxWorld->dpvsDyn.dynEntClientCount[1] * sizeof(GfxSceneDynBrush));
	RUNTIME_ARRAY(varGfxWorld->primaryLightEntityShadowVis, varraw_uint, unsigned int, 4,
	              (unsigned long long)(unsigned int)((varGfxWorld->primaryLightCount - varGfxWorld->lastSunPrimaryLightIndex) * 0x2000 - 0x2000) << 2);
	RUNTIME_ARRAY(varGfxWorld->primaryLightDynEntShadowVis[0], varraw_uint, unsigned int, 4,
	              (unsigned long long)(unsigned int)((varGfxWorld->primaryLightCount - varGfxWorld->lastSunPrimaryLightIndex - 1) *
	                                                 varGfxWorld->dpvsDyn.dynEntClientCount[0]) << 2);
	RUNTIME_ARRAY(varGfxWorld->primaryLightDynEntShadowVis[1], varraw_uint, unsigned int, 4,
	              (unsigned long long)(unsigned int)((varGfxWorld->primaryLightCount - varGfxWorld->lastSunPrimaryLightIndex - 1) *
	                                                 varGfxWorld->dpvsDyn.dynEntClientCount[1]) << 2);
	RUNTIME_ARRAY(varGfxWorld->nonSunPrimaryLightForModelDynEnt, varraw_ushort, unsigned short, 2,
	              (unsigned long long)varGfxWorld->dpvsDyn.dynEntClientCount[0] * 2);
	if (varGfxWorld->shadowGeom)
	{
		ALIGN_POS(4);
		varGfxWorld->shadowGeom = (GfxShadowGeometry *)g_streamPos;
		varGfxShadowGeometry = (GfxShadowGeometry *)g_streamPos;
		Load_GfxShadowGeometryArray(true, varGfxWorld->primaryLightCount);
	}
	if (varGfxWorld->shadowGeomOptimized)
	{
		ALIGN_POS(4);
		varGfxWorld->shadowGeomOptimized = (GfxShadowGeometry *)g_streamPos;
		varGfxShadowGeometry = (GfxShadowGeometry *)g_streamPos;
		Load_GfxShadowGeometryArray(true, varGfxWorld->primaryLightCount);
	}
	if (varGfxWorld->lightRegion)
	{
		ALIGN_POS(4);
		varGfxWorld->lightRegion = (GfxLightRegion *)g_streamPos;
		varGfxLightRegion = (GfxLightRegion *)g_streamPos;
		unsigned long long count = varGfxWorld->primaryLightCount;
		Load_Stream(true, g_streamPos, count * sizeof(GfxLightRegion));
		GfxLightRegion *region = varGfxLightRegion;
		for (; count; count--)
		{
			varGfxLightRegion = region;
			Load_GfxLightRegion(false);
			region++;
		}
	}
	varGfxWorldDpvsStatic = &varGfxWorld->dpvs;
	Load_GfxWorldDpvsStatic(false);
	varGfxWorldDpvsDynamic = &varGfxWorld->dpvsDyn;
	Load_GfxWorldDpvsDynamic(false);
	if (varGfxWorld->heroOnlyLights)
	{
		ALIGN_POS(4);
		varGfxWorld->heroOnlyLights = (GfxHeroOnlyLight *)g_streamPos;
		varGfxHeroOnlyLight = (GfxHeroOnlyLight *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varGfxWorld->heroOnlyLightCount * sizeof(GfxHeroOnlyLight));
	}
	if (varGfxWorld->umbraTomeData)
	{
		ALIGN_POS(16);
		varGfxWorld->umbraTomeData = g_streamPos;
		varbyte16 = g_streamPos;
		Load_Stream(true, g_streamPos, varGfxWorld->umbraTomeSize);
	}
	void **tome = &varGfxWorld->umbraTome;
	varUmbraTome = tome;
	Load_Stream(false, tome, 8);
	sub_1401B7180(tome, varGfxWorld->umbraTomeData, varGfxWorld->umbraTomeSize);
	DB_PopStreamPos();
}

// Store 140351D10 (gfx_d3d/r_material_load_db.h in the PS4 PDB)
void Load_GfxWorldPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varGfxWorldPtr, sizeof(GfxWorld *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	GfxWorld **worldPtr = varGfxWorldPtr;
	unsigned long long value = (unsigned long long)*varGfxWorldPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varGfxWorldPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varGfxWorldPtr = (GfxWorld *)g_streamPos;
		varGfxWorld = (GfxWorld *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_GfxWorld(true);
		Load_GfxWorldAsset(worldPtr);
		if (inserted)
			*(GfxWorld **)inserted = *worldPtr;
	}
	DB_PopStreamPos();
}

// --- ComWorld (asset type 0x14) ------------------------------------------------------------------------------------

extern ComWorld *varComWorld;                 // Store 1444267C8
extern ComWorld **varComWorldPtr;             // Store 1444267D0
extern ComPrimaryLight *varComPrimaryLight;   // Store 1444267B8
extern ComPrimaryLightEnv *varComPrimaryLightEnv;  // Store 1444267C0

// Store 14034BBC0 (gfx_d3d/r_material_load_db.h in the PS4 PDB; Load_ComPrimaryLightArray is inlined here)
void Load_ComWorld(bool atStreamStart)
{
	Load_Stream(atStreamStart, varComWorld, sizeof(ComWorld));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varComWorld->name;
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
	if (varComWorld->primaryLights)
	{
		ALIGN_POS(4);
		varComWorld->primaryLights = (ComPrimaryLight *)g_streamPos;
		varComPrimaryLight = (ComPrimaryLight *)g_streamPos;
		unsigned long long count = varComWorld->primaryLightCount;
		Load_Stream(true, g_streamPos, count * sizeof(ComPrimaryLight));
		ComPrimaryLight *light = varComPrimaryLight;
		for (; count; count--)
		{
			varComPrimaryLight = light;
			Load_Stream(false, light, sizeof(ComPrimaryLight));
			varXString = &varComPrimaryLight->defName;
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
			light++;
		}
	}
	if (varComWorld->primaryLightEnvs)
	{
		ALIGN_POS(4);
		varComWorld->primaryLightEnvs = (ComPrimaryLightEnv *)g_streamPos;
		varComPrimaryLightEnv = (ComPrimaryLightEnv *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varComWorld->primaryLightEnvCount * sizeof(ComPrimaryLightEnv));
	}
	DB_PopStreamPos();
}

// Store 14034BD90 (gfx_d3d/r_material_load_db.h in the PS4 PDB)
void Load_ComWorldPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varComWorldPtr, sizeof(ComWorld *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	ComWorld **worldPtr = varComWorldPtr;
	unsigned long long value = (unsigned long long)*varComWorldPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varComWorldPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varComWorldPtr = (ComWorld *)g_streamPos;
		varComWorld = (ComWorld *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_ComWorld(true);
		Load_ComWorldAsset(worldPtr);
		if (inserted)
			*(ComWorld **)inserted = *worldPtr;
	}
	DB_PopStreamPos();
}
