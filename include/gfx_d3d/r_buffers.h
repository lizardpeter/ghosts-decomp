// gfx_d3d/r_buffers.h: vertex, index, constant and dynamic buffers (Store-build layouts).
//
// The D3D11 declarations below are the few the buffer code uses, written by hand from the public interface (the
// reconstruction is built without the Windows SDK); each layout is checked against the Store build's code.
// Game structures come from the Xbox One server PDB (iw6_ds_xb3) where the Store build agrees with it, and say
// where it doesn't.
#pragma once

#include "gfx_d3d/r_dx.h"

typedef long HRESULT;

struct ID3D11Buffer;
struct ID3D11Resource;
struct ID3D11ShaderResourceView;
struct ID3D11UnorderedAccessView;

// ---- D3D11 (d3d11.h) ----------------------------------------------------------------------------------------

#define E_OUTOFMEMORY ((HRESULT)0x8007000E)

enum D3D11_USAGE
{
	D3D11_USAGE_DEFAULT = 0,
	D3D11_USAGE_IMMUTABLE = 1,
	D3D11_USAGE_DYNAMIC = 2,
	D3D11_USAGE_STAGING = 3,
};

enum D3D11_BIND_FLAG
{
	D3D11_BIND_VERTEX_BUFFER = 0x1,
	D3D11_BIND_INDEX_BUFFER = 0x2,
	D3D11_BIND_CONSTANT_BUFFER = 0x4,
	D3D11_BIND_SHADER_RESOURCE = 0x8,
	D3D11_BIND_UNORDERED_ACCESS = 0x80,
};

enum D3D11_CPU_ACCESS_FLAG
{
	D3D11_CPU_ACCESS_WRITE = 0x10000,
};

enum D3D11_RESOURCE_MISC_FLAG
{
	D3D11_RESOURCE_MISC_DRAWINDIRECT_ARGS = 0x10,
	D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS = 0x20,
};

enum D3D11_MAP
{
	D3D11_MAP_READ = 1,
	D3D11_MAP_WRITE = 2,
	D3D11_MAP_READ_WRITE = 3,
	D3D11_MAP_WRITE_DISCARD = 4,
	D3D11_MAP_WRITE_NO_OVERWRITE = 5,
};

struct D3D11_BUFFER_DESC
{
	unsigned int ByteWidth;
	D3D11_USAGE Usage;
	unsigned int BindFlags;
	unsigned int CPUAccessFlags;
	unsigned int MiscFlags;
	unsigned int StructureByteStride;
};
static_assert(sizeof(D3D11_BUFFER_DESC) == 0x18, "D3D11_BUFFER_DESC");  // Load_IndexBuffer: fields at +0..+0x10

struct D3D11_SUBRESOURCE_DATA
{
	const void *pSysMem;
	unsigned int SysMemPitch;
	unsigned int SysMemSlicePitch;
};
static_assert(sizeof(D3D11_SUBRESOURCE_DATA) == 0x10, "D3D11_SUBRESOURCE_DATA");  // Load_IndexBuffer

struct D3D11_MAPPED_SUBRESOURCE
{
	void *pData;
	unsigned int RowPitch;
	unsigned int DepthPitch;
};
static_assert(sizeof(D3D11_MAPPED_SUBRESOURCE) == 0x10, "D3D11_MAPPED_SUBRESOURCE");  // R_LockIndexBuffer: pData at +0

// ---- game structures ----------------------------------------------------------------------------------------

// A dynamic vertex buffer. The Store build's is 0x30 bytes, the servers' 0x18: R_InitDynamicVertexBufferState adds
// a raw (byte address) copy of the buffer with a shader resource view and an unordered access view for compute
// shaders (the skinned-vertex cache). Names of the three new members are unknown.
struct GfxVertexBufferState
{
	volatile int used;
	int total;
	ID3D11Buffer *buffer;
	unsigned char *verts;
	ID3D11Buffer *rawBuffer;                // "Dynamic Vertex Raw Buffer"
	ID3D11ShaderResourceView *rawView;      // "Dynamic Vertex Buffer View"
	ID3D11UnorderedAccessView *rawUav;      // "Dynamic Vertex Buffer View"
};
static_assert(sizeof(GfxVertexBufferState) == 0x30, "GfxVertexBufferState (Store build)");
static_assert(__builtin_offsetof(GfxVertexBufferState, rawUav) == 0x28, "GfxVertexBufferState (Store build)");

struct GfxIndexBufferState
{
	volatile int used;
	int total;
	ID3D11Buffer *buffer;
	unsigned short *indices;
};
static_assert(sizeof(GfxIndexBufferState) == 0x18, "GfxIndexBufferState");

// Store build: 0xD90 constant buffers of 0x100 bytes each (R_InitReactiveMotionConstantBufferState, 1401B1F10),
// after 0xD9000 bytes of constants.
struct GfxReactiveMotionBufferState
{
	unsigned char constants[0xD9000];
	ID3D11Buffer *cbs[0xD90];
};
static_assert(sizeof(GfxReactiveMotionBufferState) == 0xDFC80, "GfxReactiveMotionBufferState (Store build)");

// The servers' layout with the Store build's larger members: gfxBuf is at 14A107B40, its index buffer pool at +8,
// the skinned cache pool at +0x28 (3 x 0x30), the reactive motion pools at +0xC0 (2 x 0xDFC80) and the dynamic
// vertex buffer pool at +0x1BF9C0 (R_CreateDynamicBuffers, R_DestroyDynamicBuffers).
struct GfxBuffers
{
	unsigned int skinnedCacheFrameCount;
	GfxIndexBufferState dynamicIndexBufferPool[1];
	GfxIndexBufferState *dynamicIndexBuffer;
	GfxVertexBufferState skinnedCacheVbPool[3];
	unsigned char *skinnedCacheLockAddr;
	GfxReactiveMotionBufferState reactiveMotionCbPool[2];
	GfxVertexBufferState dynamicVertexBufferPool[1];
	GfxVertexBufferState *dynamicVertexBuffer;
	int skinnedCacheVbPoolFrame;
	int reactiveMotionCbPoolFrame;
};
static_assert(__builtin_offsetof(GfxBuffers, dynamicIndexBuffer) == 0x20, "GfxBuffers (Store build)");
static_assert(__builtin_offsetof(GfxBuffers, skinnedCacheVbPool) == 0x28, "GfxBuffers (Store build)");
static_assert(__builtin_offsetof(GfxBuffers, skinnedCacheLockAddr) == 0xB8, "GfxBuffers (Store build)");
static_assert(__builtin_offsetof(GfxBuffers, reactiveMotionCbPool) == 0xC0, "GfxBuffers (Store build)");
static_assert(__builtin_offsetof(GfxBuffers, dynamicVertexBufferPool) == 0x1BF9C0, "GfxBuffers (Store build)");
static_assert(__builtin_offsetof(GfxBuffers, dynamicVertexBuffer) == 0x1BF9F0, "GfxBuffers (Store build)");

// Only the particle cloud buffers are used here (the servers' layout up to them; Store: g_drawConsts 14B89E280).
struct GfxDrawConsts
{
	unsigned char outdoorLookupMatrixToScaleViewport[0x68];  // outdoorLookupMatrix, identityPlacement, scaleViewport
	ID3D11Buffer *particleCloudVertexBuffer;
	ID3D11Buffer *particleCloudIndexBuffer;
	ID3D11Buffer *particleCloudSparkVertexBuffer;
	ID3D11Buffer *particleCloudSparkIndexBuffer;
};
static_assert(__builtin_offsetof(GfxDrawConsts, particleCloudVertexBuffer) == 0x68, "GfxDrawConsts");

union GfxZoneTableEntry
{
	void *voidPtr;
	ID3D11Buffer *buffer;
};

// DxGlobals members past the ones gfx_d3d/r_dx.h spells out, at their Store offsets (xb3 PDB names; the Store
// build has 8 more bytes before constantBufferCounts than the servers: 0x60, not 0x58). Reached through `dxb` so
// this file doesn't change the shared struct; they belong in DxGlobals.
struct DxGlobalsBuffers
{
	unsigned char head[0x48];
	ID3D11Buffer *smodelWorldMatrixConstantBuffer;
	ID3D11Buffer *smodelLightingOrAmbientConstantBuffer;
	unsigned char unknown58[8];
	unsigned int constantBufferCounts[3][81];
	const GfxZoneTableEntry *constantBufferTables[3][81];
	unsigned char states[0x2760 - 0xBC8];
	GfxZoneTableEntry defaultConstantBuffers[3][128];
	unsigned char samplers[0x3B68 - 0x3360];
	void *immediateContextMutex;
};
static_assert(__builtin_offsetof(DxGlobalsBuffers, smodelWorldMatrixConstantBuffer) == 0x48, "DxGlobals (Store)");
static_assert(__builtin_offsetof(DxGlobalsBuffers, constantBufferCounts) == 0x60, "DxGlobals (Store)");
static_assert(__builtin_offsetof(DxGlobalsBuffers, constantBufferTables) == 0x430, "DxGlobals (Store)");
static_assert(__builtin_offsetof(DxGlobalsBuffers, defaultConstantBuffers) == 0x2760, "DxGlobals (Store)");
static_assert(__builtin_offsetof(DxGlobalsBuffers, immediateContextMutex) == 0x3B68, "DxGlobals (Store)");
#define dxb (*(DxGlobalsBuffers *)&dx)

extern GfxBuffers gfxBuf;
extern GfxDrawConsts g_drawConsts;

// ---- gfx_d3d/r_buffers.cpp ----------------------------------------------------------------------------------

HRESULT R_CreateBufferInternal(const D3D11_BUFFER_DESC *pDesc, const D3D11_SUBRESOURCE_DATA *pInitialData,
                               ID3D11Buffer **ppBuffer);
HRESULT R_ReleaseBuffer(ID3D11Buffer *buffer);
void *R_LockIndexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle, int offset, int bytes, D3D11_MAP lockFlags);
void *R_LockVertexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle, int offset, int bytes, D3D11_MAP lockFlags);
void R_UnlockIndexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle);
void R_UnlockVertexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle);
void R_InitDynamicVertexBufferState(GfxVertexBufferState *vb, int bytes, bool compute);
void R_DestroyDynamicVertexBufferState(GfxVertexBufferState *vb);
