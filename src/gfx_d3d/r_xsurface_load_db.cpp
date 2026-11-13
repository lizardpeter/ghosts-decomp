// gfx_d3d/r_xsurface_load_db.h (Store build): the zone loaders of XSurface and the data hanging off it.
//
// Generated loader functions of gfx_d3d/r_xsurface_load_db.h, included into database/db_load.cpp (db_load.obj in
// the PS4/xb3 servers, whose PDBs give names and lines). The code is the Store build's (iw6mp64_MSStore_ship),
// tagged with Store addresses. Where the servers stub the renderer (their Load_* buffer calls are folded into an
// empty function), the Store build creates the vertex, index and raw buffers and their views right after loading
// the data (src/gfx_d3d/r_buffers.cpp). The Store XSurface is 0xE8 bytes, the servers' 0xC8: the blend table at
// +0x50 and the subdivision data at +0x80 are Store only, and so are their loaders (sub_14035F3A0, sub_14035F430,
// named here after the generator's convention, Load_XSurfaceSubdivInfo and Load_XSurfaceSubdivLevelArray).
// Load_XRigidVertListArray is inlined into Load_XSurface in the Store build.

#include "xanim/xmodel.h"

// Store 14034FAC0 (no server has it as a function: inlined into the xb3/PS4 Load_XSurface)
void Load_GfxPackedVertexUnion(bool atStreamStart)
{
	GfxPackedVertex **verts = varGfxPackedVertexUnion;
	if (!*verts)
		return;
	if ((unsigned long long)*verts == DB_PTR_FOLLOWING)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 15) & ~15ull);
		*verts = (GfxPackedVertex *)g_streamPos;
		varGfxPackedVertex = (GfxPackedVertex *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(GfxPackedVertex) * (unsigned long long)varXSurface->vertCount);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxPackedVertexUnion);
}

// Store 14034FA50 (inlined into the xb3/PS4 Load_XSurface)
void Load_GfxPackedMotionVertexUnion(bool atStreamStart)
{
	GfxPackedMotionVertex **verts = varGfxPackedMotionVertexUnion;
	if (!*verts)
		return;
	if ((unsigned long long)*verts == DB_PTR_FOLLOWING)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 15) & ~15ull);
		*verts = (GfxPackedMotionVertex *)g_streamPos;
		varGfxPackedMotionVertex = (GfxPackedMotionVertex *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(GfxPackedMotionVertex) * (unsigned long long)varXSurface->vertCount);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varGfxPackedMotionVertexUnion);
}

// Inlined into Load_XSurface in the Store build (gfx_d3d/r_xsurface_load_db.h:6876 in the PS4 PDB)
void Load_XRigidVertListArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varXRigidVertList, sizeof(XRigidVertList) * count);
	XRigidVertList *list = varXRigidVertList;
	for (; count; count--)
	{
		varXRigidVertList = list;
		Load_Stream(false, list, sizeof(XRigidVertList));
		if (varXRigidVertList->collisionTree)
		{
			if ((unsigned long long)varXRigidVertList->collisionTree == DB_PTR_FOLLOWING)
			{
				g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
				varXRigidVertList->collisionTree = (XSurfaceCollisionTree *)g_streamPos;
				varXSurfaceCollisionTree = (XSurfaceCollisionTree *)g_streamPos;
				Load_XSurfaceCollisionTree(true);
			}
			else
			{
				DB_ConvertOffsetToPointer((unsigned long long *)&varXRigidVertList->collisionTree);
			}
		}
		list++;
	}
}

// Store 14035EAF0 (gfx_d3d/r_xsurface_load_db.h:12686 in the PS4 PDB)
void Load_XSurface(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXSurface, sizeof(XSurface));
	varGfxVertexUnion0 = &varXSurface->verts0;
	if ((varXSurface->flags >> 3) & 1)  // XSURFACE_FLAG_MOTION_VERTS
	{
		varGfxPackedMotionVertexUnion = &varGfxVertexUnion0->packedMotionVerts0;
		Load_GfxPackedMotionVertexUnion(false);
	}
	else
	{
		varGfxPackedVertexUnion = &varGfxVertexUnion0->packedVerts0;
		Load_GfxPackedVertexUnion(false);
	}
	if (varXSurface->triIndices)
	{
		if ((unsigned long long)varXSurface->triIndices == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 15) & ~15ull);
			varXSurface->triIndices = (unsigned short *)g_streamPos;
			varr_index16_t = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(unsigned short) * 3 * (unsigned long long)varXSurface->triCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->triIndices);
		}
	}
	ID3D11Buffer **vb0 = &varXSurface->vb0;
	varGfxVertexBuffer = vb0;
	Load_Stream(false, vb0, sizeof(ID3D11Buffer *));
	Load_VertexBuffer(vb0, varXSurface->verts0.verts0, XSurfaceGetVert0Size(varXSurface) * varXSurface->vertCount);
	ID3D11ShaderResourceView **vb0View = &varXSurface->vb0View;
	varGfxShaderView = vb0View;
	Load_Stream(false, vb0View, sizeof(ID3D11ShaderResourceView *));
	Load_VertexBufferView(vb0View, varXSurface->vb0, XSurfaceGetVert0Size(varXSurface) * varXSurface->vertCount,
	                      "vb0View");
	ID3D11Buffer **indexBuffer = &varXSurface->indexBuffer;
	varGfxIndexBuffer = indexBuffer;
	Load_Stream(false, indexBuffer, sizeof(ID3D11Buffer *));
	Load_IndexBuffer(indexBuffer, varXSurface->triIndices, 3 * varXSurface->triCount);
	if (varXSurface->rigidVertLists)
	{
		if ((unsigned long long)varXSurface->rigidVertLists == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varXSurface->rigidVertLists = (XRigidVertList *)g_streamPos;
			varXRigidVertList = (XRigidVertList *)g_streamPos;
			Load_XRigidVertListArray(true, varXSurface->rigidVertListCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->rigidVertLists);
		}
	}
	if (varXSurface->blendVerts)
	{
		if ((unsigned long long)varXSurface->blendVerts == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
			varXSurface->blendVerts = (unsigned short *)g_streamPos;
			varXBlendInfo = (unsigned short *)g_streamPos;
			const short *counts = varXSurface->blendVertCounts;
			// a vertex blended from n bones has 2n - 1 entries: n bone offsets and n - 1 weights (docs)
			Load_Stream(true, g_streamPos,
			            sizeof(unsigned short) * (counts[0] + 3 * counts[1] + 5 * counts[2] + 7 * counts[3] +
			                                      9 * counts[4] + 11 * counts[5] + 13 * counts[6] + 15 * counts[7]));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->blendVerts);
		}
	}
	if (varXSurface->blendVertsTable)
	{
		if ((unsigned long long)varXSurface->blendVertsTable == DB_PTR_FOLLOWING)
		{
			varXSurface->blendVertsTable = g_streamPos;
			unk_144425058 = g_streamPos;
			Load_Stream(true, g_streamPos, 32 * (unsigned long long)varXSurface->vertCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->blendVertsTable);
		}
	}
	ID3D11Buffer **blendVertsBuffer = &varXSurface->blendVertsBuffer;
	varGfxBuffer = blendVertsBuffer;
	Load_Stream(false, blendVertsBuffer, sizeof(ID3D11Buffer *));
	Load_RawDataBuffer(blendVertsBuffer, varXSurface->blendVertsTable, 32 * varXSurface->vertCount, "blendVerts");
	ID3D11ShaderResourceView **blendVertsView = &varXSurface->blendVertsView;
	varGfxShaderView = blendVertsView;
	Load_Stream(false, blendVertsView, sizeof(ID3D11ShaderResourceView *));
	Load_RawDataBufferView(blendVertsView, varXSurface->blendVertsBuffer, varXSurface->blendVertsTable,
	                       32 * varXSurface->vertCount, "blendVertsView");
	if (varXSurface->lmapUnwrap)
	{
		if ((unsigned long long)varXSurface->lmapUnwrap == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varXSurface->lmapUnwrap = (float (*)[2])g_streamPos;
			varalignVertBufVec2_t = (float (*)[2])g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(float[2]) * (unsigned long long)varXSurface->vertCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->lmapUnwrap);
		}
	}
	ID3D11Buffer **vblmap = &varXSurface->vblmap;
	varGfxVertexBuffer = vblmap;
	Load_Stream(false, vblmap, sizeof(ID3D11Buffer *));
	Load_VertexBuffer(vblmap, varXSurface->lmapUnwrap, 8 * varXSurface->vertCount);
	ID3D11ShaderResourceView **vblmapView = &varXSurface->vblmapView;
	varGfxShaderView = vblmapView;
	Load_Stream(false, vblmapView, sizeof(ID3D11ShaderResourceView *));
	Load_VertexBufferView(vblmapView, varXSurface->vblmap, 8 * varXSurface->vertCount, "vblmapView");
	XSurface *surf = varXSurface;
	if (surf->subdiv)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		surf->subdiv = (XSurfaceSubdivInfo *)g_streamPos;
		unk_144425090 = (XSurfaceSubdivInfo *)g_streamPos;
		sub_14035F3A0(true);
		sub_1401B3DC0(&surf->subdiv, varXSurface);
	}
	if (varXSurface->tensionData)
	{
		if ((unsigned long long)varXSurface->tensionData == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varXSurface->tensionData = (float *)g_streamPos;
			varalignCompBufFloat_t = (float *)g_streamPos;
			const short *counts = varXSurface->blendVertCounts;
			Load_Stream(true, g_streamPos,
			            sizeof(float) * (counts[7] + counts[6] + counts[5] + counts[4] + counts[3] + counts[2] +
			                             counts[1] + counts[0]));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->tensionData);
		}
	}
	if (varXSurface->tensionAccumTable)
	{
		if ((unsigned long long)varXSurface->tensionAccumTable == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
			varXSurface->tensionAccumTable = (unsigned short *)g_streamPos;
			varalignCompBufUShort_t = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, 32 * (unsigned long long)varXSurface->vertCount);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXSurface->tensionAccumTable);
		}
	}
	ID3D11Buffer **tensionAccumTableBuffer = &varXSurface->tensionAccumTableBuffer;
	varGfxBuffer = tensionAccumTableBuffer;
	Load_Stream(false, tensionAccumTableBuffer, sizeof(ID3D11Buffer *));
	Load_RawDataBuffer(tensionAccumTableBuffer, varXSurface->tensionAccumTable, 32 * varXSurface->vertCount,
	                   "tensionAccumTable");
	ID3D11ShaderResourceView **tensionAccumTableView = &varXSurface->tensionAccumTableView;
	varGfxShaderView = tensionAccumTableView;
	Load_Stream(false, tensionAccumTableView, sizeof(ID3D11ShaderResourceView *));
	Load_RawDataBufferView(tensionAccumTableView, varXSurface->tensionAccumTableBuffer, varXSurface->tensionAccumTable,
	                       32 * varXSurface->vertCount, "tensionAccumTableView");
	ID3D11Buffer **tensionDataBuffer = &varXSurface->tensionDataBuffer;
	varGfxBuffer = tensionDataBuffer;
	Load_Stream(false, tensionDataBuffer, sizeof(ID3D11Buffer *));
	Load_RawDataBuffer(tensionDataBuffer, varXSurface->tensionData, 4 * varXSurface->vertCount, "tensionData");
	ID3D11ShaderResourceView **tensionDataView = &varXSurface->tensionDataView;
	varGfxShaderView = tensionDataView;
	Load_Stream(false, tensionDataView, sizeof(ID3D11ShaderResourceView *));
	Load_RawDataBufferView(tensionDataView, varXSurface->tensionDataBuffer, varXSurface->tensionData,
	                       4 * varXSurface->vertCount, "tensionDataView");
	ID3D11ShaderResourceView **indexBufferView = &varXSurface->indexBufferView;
	varGfxShaderView = indexBufferView;
	Load_Stream(false, indexBufferView, sizeof(ID3D11ShaderResourceView *));
	Load_IndexBufferView(indexBufferView, varXSurface->indexBuffer, 2 * (3 * varXSurface->triCount),
	                     "indexBufferView");
}

// Store 14035F2E0 (gfx_d3d/r_xsurface_load_db.h:6593 in the PS4 PDB)
void Load_XSurfaceCollisionTree(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXSurfaceCollisionTree, sizeof(XSurfaceCollisionTree));
	if (varXSurfaceCollisionTree->nodes)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 15) & ~15ull);
		varXSurfaceCollisionTree->nodes = (XSurfaceCollisionNode *)g_streamPos;
		varXSurfaceCollisionNode = (XSurfaceCollisionNode *)g_streamPos;
		Load_Stream(true, g_streamPos,
		            sizeof(XSurfaceCollisionNode) * (unsigned long long)varXSurfaceCollisionTree->nodeCount);
	}
	if (varXSurfaceCollisionTree->leafs)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
		varXSurfaceCollisionTree->leafs = (XSurfaceCollisionLeaf *)g_streamPos;
		varXSurfaceCollisionLeaf = (XSurfaceCollisionLeaf *)g_streamPos;
		Load_Stream(true, g_streamPos,
		            sizeof(XSurfaceCollisionLeaf) * (unsigned long long)varXSurfaceCollisionTree->leafCount);
	}
}

// Store 14035F3A0 (Store only; Load_XSurfaceSubdivInfo by the generator's naming, name unconfirmed)
void sub_14035F3A0(bool atStreamStart)
{
	Load_Stream(atStreamStart, unk_144425090, sizeof(XSurfaceSubdivInfo));
	if (unk_144425090->levels)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		unk_144425090->levels = (XSurfaceSubdivLevel *)g_streamPos;
		unk_144425080 = (XSurfaceSubdivLevel *)g_streamPos;
		sub_14035F430(true, varXSurface->subdivLevelCount);
	}
	GfxSubdivCache *cache = &unk_144425090->cache;
	unk_144425088 = cache;
	Load_Stream(false, cache, sizeof(GfxSubdivCache));
	sub_1401B3D60(cache);
}

// Store 14035F430 (Store only; Load_XSurfaceSubdivLevelArray by the generator's naming, name unconfirmed)
void sub_14035F430(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, unk_144425080, sizeof(XSurfaceSubdivLevel) * count);
	XSurfaceSubdivLevel *level = unk_144425080;
	for (; count; count--)
	{
		unk_144425080 = level;
		Load_Stream(false, level, sizeof(XSurfaceSubdivLevel));
		if (unk_144425080->rigidVertLists)
		{
			if ((unsigned long long)unk_144425080->rigidVertLists == DB_PTR_FOLLOWING)
			{
				g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
				unk_144425080->rigidVertLists = g_streamPos;
				unk_144425078 = g_streamPos;
				Load_Stream(true, g_streamPos, 16 * (unsigned long long)varXSurface->rigidVertListCount);
			}
			else
			{
				DB_ConvertOffsetToPointer((unsigned long long *)&unk_144425080->rigidVertLists);
			}
		}
		if (unk_144425080->faceIndices)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
			unk_144425080->faceIndices = (unsigned short *)g_streamPos;
			varalignIndBufUShort_t = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(unsigned short) * (6 * unk_144425080->faceCount));
		}
		if (unk_144425080->regularPatchIndices)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
			unk_144425080->regularPatchIndices = (unsigned short *)g_streamPos;
			varalignIndBufUShort_t = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(unsigned short) * (16 * unk_144425080->regularPatchCount));
		}
		if (unk_144425080->regularPatchFlags)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->regularPatchFlags = (unsigned int *)g_streamPos;
			varalignCompBufUInt_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(unsigned int) * (unsigned long long)unk_144425080->regularPatchCount);
		}
		if (unk_144425080->facePoints)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->facePoints = (unsigned int *)g_streamPos;
			varalignCompBufUInt_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)unk_144425080->facePointBufferSize & ~3ull);
		}
		if (unk_144425080->edgePoints)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->edgePoints = (unsigned int *)g_streamPos;
			varalignCompBufUInt_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(unsigned int) * (2 * unk_144425080->edgePointCount));
		}
		if (unk_144425080->vertexPoints)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->vertexPoints = (unsigned int *)g_streamPos;
			varalignCompBufUInt_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)unk_144425080->vertexPointBufferSize & ~3ull);
		}
		if (unk_144425080->normals)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->normals = (unsigned int *)g_streamPos;
			varalignCompBufUInt_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)unk_144425080->normalBufferSize & ~3ull);
		}
		if (unk_144425080->transitionPoints)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->transitionPoints = (unsigned int *)g_streamPos;
			varalignCompBufUInt_t = (unsigned int *)g_streamPos;
			Load_Stream(true, g_streamPos,
			            sizeof(unsigned int) * (unsigned long long)unk_144425080->transitionPointCount);
		}
		if (unk_144425080->regularPatchCones)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			unk_144425080->regularPatchCones = (float *)g_streamPos;
			varalignCompBufFloat_t = (float *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(float) * (8 * unk_144425080->regularPatchCount));
		}
		level++;
	}
}

// Store 14066CD30 (gfx_d3d/r_xsurface.cpp in the PS4 PDB): every Store model surface uses 32-byte packed vertices
int XSurfaceGetVert0Size(const XSurface *surf)
{
	return sizeof(GfxPackedVertex);
}
