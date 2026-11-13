// gfx_d3d/r_xsurface.h: XSurface, the renderable mesh piece of a model LOD, and the data hanging off it
// (Store-build layouts).
//
// The servers' PDBs (iw6_ds_ps4, iw6_ds_xb3: identical) give XSurface as 0xC8 bytes; the Store build's is 0xE8
// (Load_XSurface 14035EAF0 reads 0xE8 and touches every pointer below). It adds a second blend table for GPU
// skinning with its raw buffer and view (+0x50..+0x60) and subdivision surface data (+0x80); byte +7, padding in
// the servers, is the subdivision level count. Names of members the servers lack are this project's (the debug
// names the Store build gives the buffers made from them where there is one), marked "Store only".
// docs/assets/models.md has every field with its evidence.
#pragma once

#include "gfx_d3d/r_buffers.h"

// ---- vertices ------------------------------------------------------------------------------------------------

// A unit vector packed in 32 bits (decoding: docs/assets/models.md, "Packed vertex formats").
union PackedUnitVec
{
	unsigned int packed;
};

// Two half floats (u, v).
union PackedTexCoords
{
	unsigned int packed;
};

union GfxColor
{
	unsigned char array[4];
	unsigned int packed;
};

// The vertex format of every model surface in the Store build: Load_GfxPackedVertexUnion and its motion twin load
// vertCount * 0x20 bytes (XSurfaceGetVert0Size returns 0x20).
struct GfxPackedVertex
{
	float xyz[3];
	float binormalSign;
	GfxColor color;
	PackedTexCoords texCoord;
	PackedUnitVec normal;
	PackedUnitVec tangent;
};
static_assert(sizeof(GfxPackedVertex) == 0x20, "GfxPackedVertex");

// The same size, for surfaces with flag 0x8 (XSURFACE_FLAG_MOTION_VERTS): the color slot holds a piece index and the
// binormal sign also carries a height.
struct GfxPackedMotionVertex
{
	float xyz[3];
	float binormalSignAndHeight;
	GfxColor pieceIndex;
	PackedTexCoords texCoord;
	PackedUnitVec normal;
	PackedUnitVec tangent;
};
static_assert(sizeof(GfxPackedMotionVertex) == 0x20, "GfxPackedMotionVertex");

struct GfxQuantizedNoColorVertex;
struct GfxQuantizedNoColorMotionVertex;
struct GfxQuantizedVertex;
struct GfxQuantizedMotionVertex;

union GfxVertexUnion0
{
	GfxQuantizedNoColorVertex *quantizedNoColorVerts0;
	GfxQuantizedNoColorMotionVertex *quantizedNoColorMotionVerts0;
	GfxQuantizedVertex *quantizedVerts0;
	GfxQuantizedMotionVertex *quantizedMotionVerts0;
	GfxPackedVertex *packedVerts0;
	GfxPackedMotionVertex *packedMotionVerts0;
	void *verts0;
};

#define XSURFACE_FLAG_MOTION_VERTS 0x8  // Load_XSurface: picks GfxPackedMotionVertex over GfxPackedVertex

// ---- collision tree (per rigid vertex list) --------------------------------------------------------------------

struct XSurfaceCollisionAabb
{
	unsigned short mins[3];
	unsigned short maxs[3];
};

struct XSurfaceCollisionNode
{
	XSurfaceCollisionAabb aabb;
	unsigned short childBeginIndex;
	unsigned short childCount;
};
static_assert(sizeof(XSurfaceCollisionNode) == 0x10, "XSurfaceCollisionNode");

struct XSurfaceCollisionLeaf
{
	unsigned short triangleBeginIndex;
};

struct XSurfaceCollisionTree
{
	float trans[3];
	float scale[3];
	unsigned int nodeCount;
	XSurfaceCollisionNode *nodes;  // always inline when non-null
	unsigned int leafCount;
	XSurfaceCollisionLeaf *leafs;  // always inline when non-null
};
static_assert(sizeof(XSurfaceCollisionTree) == 0x38, "XSurfaceCollisionTree");
static_assert(__builtin_offsetof(XSurfaceCollisionTree, nodes) == 0x20, "XSurfaceCollisionTree");
static_assert(__builtin_offsetof(XSurfaceCollisionTree, leafs) == 0x30, "XSurfaceCollisionTree");

// The vertices and triangles of a surface bound rigidly to one bone.
struct XRigidVertList
{
	unsigned short boneOffset;
	unsigned short vertCount;
	unsigned short triOffset;
	unsigned short triCount;
	XSurfaceCollisionTree *collisionTree;  // inline or an offset
};
static_assert(sizeof(XRigidVertList) == 0x10, "XRigidVertList");

// ---- subdivision surfaces (Store only) ---------------------------------------------------------------------------

// One level of a subdivision surface. Store only: no server has the type; the names of the arrays are the debug
// names of the buffers sub_1401B4100 creates from them, the counts are named after what they size.
struct XSurfaceSubdivLevel
{
	void *rigidVertLists;                 // +0x00 XSurface::rigidVertListCount entries of 16 bytes
	unsigned int faceCount;               // +0x08 faceIndices: 6 indices per face
	unsigned int regularPatchCount;       // +0x0C regularPatchIndices (16 each), Flags (1), Cones (8 floats)
	unsigned int regularPatchOffset;      // +0x10 not read by the loader or sub_1401B4100
	unsigned int facePointCount;          // +0x14 not read by the loader
	unsigned int facePointValence4Count;  // +0x18 not read by the loader
	unsigned int facePointBufferSize;     // +0x1C bytes of facePoints (rounded down to 4)
	unsigned int edgePointCount;          // +0x20 edgePoints: 2 uints each
	unsigned int edgePointSmoothEnd;      // +0x24 not read by the loader
	unsigned int edgePointUVBorderEnd;    // +0x28 not read by the loader
	unsigned int vertexPointCount;        // +0x2C not read by the loader
	unsigned int vertexPointValence4Count;  // +0x30 not read by the loader
	unsigned int vertexPointBufferSize;   // +0x34 bytes of vertexPoints (rounded down to 4)
	unsigned int normalCount;             // +0x38 nonzero: sub_1401B4100 makes the normals buffer
	unsigned int normalBufferSize;        // +0x3C bytes of normals (rounded down to 4)
	unsigned int transitionPointCount;    // +0x40 transitionPoints: 1 uint each
	unsigned int vertCount;               // +0x44 not read by the loader
	unsigned int vertOffset;              // +0x48 not read by the loader
	unsigned short *faceIndices;          // +0x50
	unsigned short *regularPatchIndices;  // +0x58
	unsigned int *regularPatchFlags;      // +0x60
	unsigned int *facePoints;             // +0x68
	unsigned int *edgePoints;             // +0x70
	unsigned int *vertexPoints;           // +0x78
	unsigned int *normals;                // +0x80
	unsigned int *transitionPoints;       // +0x88
	float *regularPatchCones;             // +0x90
	ID3D11Buffer *regularPatchIndexBuffer;                 // +0x98
	ID3D11Buffer *faceIndexBuffer;                         // +0xA0
	ID3D11ShaderResourceView *regularPatchIndexBufferView;  // +0xA8
	ID3D11ShaderResourceView *regularPatchFlagsView;       // +0xB0
	ID3D11ShaderResourceView *facePointsView;              // +0xB8
	ID3D11ShaderResourceView *edgePointsView;              // +0xC0
	ID3D11ShaderResourceView *vertexPointsView;            // +0xC8
	ID3D11ShaderResourceView *normalsView;                 // +0xD0
	ID3D11ShaderResourceView *transitionPointsView;        // +0xD8
	ID3D11ShaderResourceView *regularPatchConesView;       // +0xE0
};
static_assert(sizeof(XSurfaceSubdivLevel) == 0xE8, "XSurfaceSubdivLevel (Store only)");
static_assert(__builtin_offsetof(XSurfaceSubdivLevel, faceIndices) == 0x50, "XSurfaceSubdivLevel");
static_assert(__builtin_offsetof(XSurfaceSubdivLevel, regularPatchIndexBuffer) == 0x98, "XSurfaceSubdivLevel");

// Store only: a GPU scratch buffer for the subdivided vertices, made by sub_1401B3D60 ("subdivCache",
// "subdivCacheView": a DEFAULT VERTEX|SHADER_RESOURCE|UNORDERED_ACCESS buffer of `size` bytes and a UAV).
struct GfxSubdivCache
{
	unsigned int size;
	ID3D11Buffer *subdivCacheBuffer;
	ID3D11UnorderedAccessView *subdivCacheView;
};
static_assert(sizeof(GfxSubdivCache) == 0x18, "GfxSubdivCache (Store only)");

// Store only. flags bit 2 (0x4): the regular patch flags were converted (sub_1401B4100 does it once).
struct XSurfaceSubdivInfo
{
	XSurfaceSubdivLevel *levels;  // XSurface::subdivLevelCount entries; always inline when non-null
	unsigned int flags;           // +0x08
	unsigned char unknown0C[0x14];  // +0x0C not read by the loader or sub_1401B4100
	GfxSubdivCache cache;         // +0x20
};
static_assert(sizeof(XSurfaceSubdivInfo) == 0x38, "XSurfaceSubdivInfo (Store only)");

// ---- the surface ---------------------------------------------------------------------------------------------------

struct XSurface
{
	unsigned short flags;           // +0x00 XSURFACE_FLAG_*
	unsigned short vertCount;       // +0x02
	unsigned short triCount;        // +0x04
	unsigned char rigidVertListCount;  // +0x06
	unsigned char subdivLevelCount;    // +0x07 Store only (padding in the servers)
	short blendVertCounts[8];       // +0x08 vertices blended from 1..8 bones (sizes blendVerts, tensionData)
	GfxVertexUnion0 verts0;         // +0x18 vertCount packed vertices
	unsigned short *triIndices;     // +0x20 triCount * 3 indices
	ID3D11Buffer *vb0;              // +0x28
	ID3D11ShaderResourceView *vb0View;     // +0x30 "vb0View"
	ID3D11Buffer *indexBuffer;      // +0x38
	XRigidVertList *rigidVertLists; // +0x40 rigidVertListCount entries
	unsigned short *blendVerts;     // +0x48 XBlendInfo: bone indices and weights, see docs
	unsigned char *blendVertsTable; // +0x50 Store only: vertCount * 0x20 bytes, the GPU skinning table
	ID3D11Buffer *blendVertsBuffer; // +0x58 Store only: raw buffer "blendVerts"
	ID3D11ShaderResourceView *blendVertsView;  // +0x60 Store only: "blendVertsView"
	float (*lmapUnwrap)[2];         // +0x68 vertCount (u, v) pairs
	ID3D11Buffer *vblmap;           // +0x70
	ID3D11ShaderResourceView *vblmapView;  // +0x78 "vblmapView"
	XSurfaceSubdivInfo *subdiv;     // +0x80 Store only; always inline when non-null
	float *tensionData;             // +0x88 one float per blended vertex
	unsigned short *tensionAccumTable;  // +0x90 vertCount * 16 indices
	ID3D11Buffer *tensionAccumTableBuffer;  // +0x98 "tensionAccumTable"
	ID3D11ShaderResourceView *tensionAccumTableView;  // +0xA0 "tensionAccumTableView"
	ID3D11Buffer *tensionDataBuffer;  // +0xA8 "tensionData"
	ID3D11ShaderResourceView *tensionDataView;  // +0xB0 "tensionDataView"
	ID3D11ShaderResourceView *indexBufferView;  // +0xB8 "indexBufferView"
	unsigned int vertexLightingIndex;  // +0xC0 by position (servers); not read by the loader
	int partBits[8];                // +0xC4 by position (servers); not read by the loader
};
static_assert(sizeof(XSurface) == 0xE8, "XSurface (Store build)");
static_assert(__builtin_offsetof(XSurface, verts0) == 0x18, "XSurface");
static_assert(__builtin_offsetof(XSurface, rigidVertLists) == 0x40, "XSurface");
static_assert(__builtin_offsetof(XSurface, lmapUnwrap) == 0x68, "XSurface");
static_assert(__builtin_offsetof(XSurface, subdiv) == 0x80, "XSurface");
static_assert(__builtin_offsetof(XSurface, indexBufferView) == 0xB8, "XSurface");

// ---- loaders and the stream variables they use -------------------------------------------------------------------

void Load_XSurface(bool atStreamStart);
void Load_XRigidVertListArray(bool atStreamStart, unsigned long long count);  // inlined in the Store build
void Load_XSurfaceCollisionTree(bool atStreamStart);
void Load_GfxPackedVertexUnion(bool atStreamStart);
void Load_GfxPackedMotionVertexUnion(bool atStreamStart);
void sub_14035F3A0(bool atStreamStart);                           // Load_XSurfaceSubdivInfo by convention
void sub_14035F430(bool atStreamStart, unsigned long long count);  // Load_XSurfaceSubdivLevelArray by convention
int XSurfaceGetVert0Size(const XSurface *surf);                   // gfx_d3d/r_xsurface.cpp

// Renderer side of subdivision (gfx_d3d, names unknown)
void sub_1401B3D60(GfxSubdivCache *cache);                         // creates the subdiv cache buffer and UAV
void sub_1401B3DC0(XSurfaceSubdivInfo **subdiv, XSurface *surf);   // creates the per-level GPU buffers
void sub_1401B4100(XSurface *surf);

// D3D11 buffer loaders (gfx_d3d/r_buffers.cpp, src/gfx_d3d/r_buffers.cpp)
void Load_VertexBuffer(ID3D11Buffer **vb, void *bufferData, int sizeInBytes);
void Load_IndexBuffer(ID3D11Buffer **ib, void *bufferData, int indexCount);
void Load_VertexBufferView(ID3D11ShaderResourceView **view, ID3D11Buffer *vb, unsigned int size, const char *name);
void Load_IndexBufferView(ID3D11ShaderResourceView **view, ID3D11Buffer *ib, unsigned int size, const char *name);
void Load_RawDataBuffer(ID3D11Buffer **buffer, void *data, unsigned int totalBufferSize, const char *bufName);
void Load_RawDataBufferView(ID3D11ShaderResourceView **view, ID3D11Buffer *buffer, void *data, unsigned int size,
                            const char *name);

extern XSurface *varXSurface;
extern GfxVertexUnion0 *varGfxVertexUnion0;
extern GfxPackedVertex **varGfxPackedVertexUnion;
extern GfxPackedMotionVertex **varGfxPackedMotionVertexUnion;
extern GfxPackedVertex *varGfxPackedVertex;
extern GfxPackedMotionVertex *varGfxPackedMotionVertex;
extern unsigned short *varr_index16_t;
extern ID3D11Buffer **varGfxVertexBuffer;
extern ID3D11Buffer **varGfxIndexBuffer;
extern ID3D11Buffer **varGfxBuffer;
extern ID3D11ShaderResourceView **varGfxShaderView;
extern XRigidVertList *varXRigidVertList;
extern XSurfaceCollisionTree *varXSurfaceCollisionTree;
extern XSurfaceCollisionNode *varXSurfaceCollisionNode;
extern XSurfaceCollisionLeaf *varXSurfaceCollisionLeaf;
extern unsigned short *varXBlendInfo;
extern float (*varalignVertBufVec2_t)[2];
extern float *varalignCompBufFloat_t;
extern unsigned short *varalignCompBufUShort_t;
extern unsigned short *varalignIndBufUShort_t;
extern unsigned int *varalignCompBufUInt_t;
// Store only, names unknown
extern unsigned char *unk_144425058;           // XSurface::blendVertsTable
extern XSurfaceSubdivInfo *unk_144425090;      // the XSurfaceSubdivInfo being loaded
extern GfxSubdivCache *unk_144425088;          // its cache
extern XSurfaceSubdivLevel *unk_144425080;     // the level being loaded
extern unsigned char *unk_144425078;           // a level's rigid vertex lists
