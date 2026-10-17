// gfx_d3d/r_buffers.cpp (Store build)
//
// Vertex, index, constant and dynamic buffers, from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with
// Store addresses. The servers' PDBs have the file (iw6_ds_xb3: gfx_d3d/r_buffers.cpp) but stub most of it, so
// the code comes from the Store build. Names: the xb3/PS4 PDBs where they have the function, else Black Ops'
// r_buffers.cpp (black-ops-1-decomp, CoDMPServer); the Store build keeps this object's functions in alphabetical
// order (every name the PDBs give falls in place), which places the rest. Unknown names are sub_<VA>.
//
// What every buffer goes through: R_CreateBufferInternal (ID3D11Device::CreateBuffer; E_OUTOFMEMORY is fatal
// through Sys_OutOfMemErrorInternal, a created buffer's size is added to a running total by sub_1401AFFE0), most
// callers inline it. With r_loadForRenderer off nothing is created and the buffer pointer is cleared.
//
// R_GetConstantBufferHandleOfSize and R_GetPerPrimConstantBufferOfSize are gfx_d3d/r_init.cpp's (PS4 PDB) and are
// kept at the end of this file; R_InitConstantBuffers is inlined into its caller in the Store build (14062F700).

#include <iw6_static.h>

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_buffers.h"
#include "gfx_d3d/r_dx.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "gfx_d3d/r_buffers.cpp"

extern "C"
{
	int rand(void);
	void qsort(void *base, unsigned long long count, unsigned long long size, int (*compare)(const void *, const void *));
	unsigned long WaitForSingleObject(void *handle, unsigned long milliseconds);
	unsigned long GetCurrentThreadId(void);
	int ReleaseMutex(void *mutex);
	char *va(const char *format, ...);
}

extern const dvar_t *r_loadForRenderer;
extern const dvar_t *r_SkinnedCacheSize;

void Sys_OutOfMemErrorInternal(int type);                      // win32/win_main.cpp
const char *R_ErrorDescription(HRESULT hr);                    // gfx_d3d/r_init.cpp
void R_FatalInitError(const char *msg);                        // Store: a thunk to Sys_DirectXFatalError
void R_FatalLockError(HRESULT hr);                             // Store: a thunk to Sys_DirectXFatalError
void R_InitReactiveMotionConstantBufferState(GfxReactiveMotionBufferState *state);  // gfx_d3d/r_reactive_motion.cpp
void R_AssignNullBuffer(ID3D11Buffer **buffer);                // gfx_d3d/r_compute.cpp

// Video memory accounting (names unknown): add or subtract a buffer's ByteWidth to/from the total at 14A385390.
void sub_1401AFFE0(ID3D11Buffer *buffer);
void sub_1401B0000(ID3D11Buffer *buffer);
void sub_1401B0020(ID3D11Buffer *buffer, unsigned int bytes);
// gfx_d3d/r_compute.cpp (names unknown)
void sub_1401AC0E0(ID3D11ShaderResourceView **view);           // *view = NULL
void sub_1401AC310(unsigned int bytes, unsigned int bindFlags, D3D11_USAGE usage, const void *data, const char *name,
                   ID3D11Buffer **buffer);                     // a raw (byte address) buffer
HRESULT sub_1401AC380(ID3D11Buffer *buffer, const char *name, ID3D11UnorderedAccessView **view);  // raw R32 UAV
HRESULT sub_1401AC3F0(ID3D11Buffer *buffer, const char *name, ID3D11ShaderResourceView **view);   // raw R32 SRV
void sub_1401B1EC0(GfxReactiveMotionBufferState *state);      // releases the reactive motion constant buffers
bool sub_140631780(ID3D11Device *device, ID3D11Buffer *buffer);  // gfx_d3d/r_init.cpp area: a driver hint
void R_UnlockSkinnedCache();                                          // unlocks the skinned vertex cache

HRESULT R_CreateBufferInternal(const D3D11_BUFFER_DESC *pDesc, const D3D11_SUBRESOURCE_DATA *pInitialData,
                               ID3D11Buffer **ppBuffer);
void *R_AllocDynamicIndexBuffer(ID3D11Buffer **ib, int sizeInBytes, const char *trackName);
void *R_AllocStaticIndexBuffer(ID3D11Buffer **ib, int sizeInBytes, const char *trackName);
void *R_AllocStaticVertexBuffer(ID3D11Buffer **vb, int sizeInBytes, const char *trackName);
int SortVerticesByDistanceToOrigin_CompareFunc(const void *a, const void *b);

// Store 140601620 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void Load_IndexBuffer(ID3D11Buffer **ib, void *bufferData, int indexCount)
{
	if (!r_loadForRenderer->current.enabled)
	{
		*ib = nullptr;
		return;
	}
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = 2 * indexCount;
	desc.Usage = D3D11_USAGE_IMMUTABLE;
	desc.BindFlags = D3D11_BIND_INDEX_BUFFER | D3D11_BIND_SHADER_RESOURCE;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS;  // StructureByteStride is left uninitialised
	D3D11_SUBRESOURCE_DATA data;
	data.pSysMem = bufferData;
	data.SysMemPitch = 0;
	data.SysMemSlicePitch = 0;
	R_CreateBufferInternal(&desc, &data, ib);
}

// Store 1406016C0 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void Load_IndexBufferView(ID3D11ShaderResourceView **view, ID3D11Buffer *buffer, unsigned int size, const char *name)
{
	if (buffer && size)
		sub_1401AC3F0(buffer, name, view);
	else
		sub_1401AC0E0(view);
}

// Store 1406016E0 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void Load_RawDataBuffer(ID3D11Buffer **buffer, void *data, unsigned int totalBufferSize, const char *bufName)
{
	if (data)
		sub_1401AC310(totalBufferSize, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE, data, bufName, buffer);
	else
		R_AssignNullBuffer(buffer);
}

// Store 140601720 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void Load_RawDataBufferView(ID3D11ShaderResourceView **view, ID3D11Buffer *buffer, void *data, unsigned int size,
                            const char *name)
{
	if (data && size)
		sub_1401AC3F0(buffer, name, view);
	else
		sub_1401AC0E0(view);
}

// Store 140601750 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void Load_VertexBuffer(ID3D11Buffer **vb, void *bufferData, int sizeInBytes)
{
	if (!bufferData || !r_loadForRenderer->current.enabled)
	{
		*vb = nullptr;
		return;
	}
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = sizeInBytes;
	desc.Usage = D3D11_USAGE_IMMUTABLE;
	desc.BindFlags = D3D11_BIND_VERTEX_BUFFER | D3D11_BIND_SHADER_RESOURCE;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS;
	D3D11_SUBRESOURCE_DATA data;
	data.pSysMem = bufferData;
	data.SysMemPitch = 0;
	data.SysMemSlicePitch = 0;
	R_CreateBufferInternal(&desc, &data, vb);
}

// Store 1406017F0 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void Load_VertexBufferView(ID3D11ShaderResourceView **view, ID3D11Buffer *vb, unsigned int size, const char *name)
{
	if (vb && size)
		sub_1401AC3F0(vb, name, view);
	else
		sub_1401AC0E0(view);
}

// Store 140601810 (xb3 PDB: inlined there). Creates the buffer only; nothing is locked, so it returns NULL.
void *R_AllocDynamicIndexBuffer(ID3D11Buffer **ib, int sizeInBytes, const char *trackName)
{
	if (r_loadForRenderer->current.enabled)
	{
		D3D11_BUFFER_DESC desc;
		desc.ByteWidth = sizeInBytes;
		desc.Usage = D3D11_USAGE_DYNAMIC;
		desc.BindFlags = D3D11_BIND_INDEX_BUFFER;
		desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
		desc.MiscFlags = 0;
		R_CreateBufferInternal(&desc, nullptr, ib);
	}
	return nullptr;
}

// Store 140601890 (name from Black Ops). A dynamic buffer mapped for writing, which the caller fills and unmaps. The
// map is attempted even when the buffer wasn't created; when it fails the buffer is released but *ib keeps
// pointing at it.
void *R_AllocStaticIndexBuffer(ID3D11Buffer **ib, int sizeInBytes, const char *trackName)
{
	if (!r_loadForRenderer->current.enabled)
		return nullptr;
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = sizeInBytes;
	desc.Usage = D3D11_USAGE_DYNAMIC;
	desc.BindFlags = D3D11_BIND_INDEX_BUFFER;
	desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	desc.MiscFlags = 0;
	R_CreateBufferInternal(&desc, nullptr, ib);
	D3D11_MAPPED_SUBRESOURCE mapped;
	if (ComCall<HRESULT>(dx.immediateContext, CTX_Map, (ID3D11Resource *)*ib, 0u, D3D11_MAP_WRITE_DISCARD, 0u,
	                     &mapped) < 0)
	{
		R_ReleaseBuffer(*ib);
		return nullptr;
	}
	return mapped.pData;
}

// Store 140601970 (name unknown): an immutable index buffer from data, also readable as a raw shader resource
void sub_140601970(ID3D11Buffer **ib, int sizeInBytes, const void *bufferData)
{
	if (!r_loadForRenderer->current.enabled)
	{
		*ib = nullptr;
		return;
	}
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = sizeInBytes;
	desc.Usage = D3D11_USAGE_IMMUTABLE;
	desc.BindFlags = D3D11_BIND_INDEX_BUFFER | D3D11_BIND_SHADER_RESOURCE;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS;
	D3D11_SUBRESOURCE_DATA data;
	data.pSysMem = bufferData;
	data.SysMemPitch = 0;
	data.SysMemSlicePitch = 0;
	R_CreateBufferInternal(&desc, &data, ib);
}

// Store 140601A00 (name from Black Ops; its "DirectX didn't lock a vertex buffer" message)
void *R_AllocStaticVertexBuffer(ID3D11Buffer **vb, int sizeInBytes, const char *trackName)
{
	if (!r_loadForRenderer->current.enabled)
		return nullptr;
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = sizeInBytes;
	desc.Usage = D3D11_USAGE_DYNAMIC;
	desc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
	desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	desc.MiscFlags = 0;
	R_CreateBufferInternal(&desc, nullptr, vb);
	D3D11_MAPPED_SUBRESOURCE mapped;
	HRESULT hr = ComCall<HRESULT>(dx.immediateContext, CTX_Map, (ID3D11Resource *)*vb, 0u, D3D11_MAP_WRITE_DISCARD, 0u,
	                              &mapped);
	if (hr < 0)
		R_FatalInitError(va("DirectX didn't lock a vertex buffer: %s\n", R_ErrorDescription(hr)));
	return mapped.pData;
}

// Store 140601AD0 (name unknown): an immutable vertex buffer from data, also readable as a raw shader resource
void sub_140601AD0(ID3D11Buffer **vb, int sizeInBytes, const void *bufferData)
{
	if (!r_loadForRenderer->current.enabled)
	{
		*vb = nullptr;
		return;
	}
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = sizeInBytes;
	desc.Usage = D3D11_USAGE_IMMUTABLE;
	desc.BindFlags = D3D11_BIND_VERTEX_BUFFER | D3D11_BIND_SHADER_RESOURCE;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS;
	D3D11_SUBRESOURCE_DATA data;
	data.pSysMem = bufferData;
	data.SysMemPitch = 0;
	data.SysMemSlicePitch = 0;
	R_CreateBufferInternal(&desc, &data, vb);
}

// Store 140601B60 (xb3 PDB gfx_d3d/r_buffers.cpp:1788). The Store build adds the accounting call.
HRESULT R_CreateBufferInternal(const D3D11_BUFFER_DESC *pDesc, const D3D11_SUBRESOURCE_DATA *pInitialData,
                               ID3D11Buffer **ppBuffer)
{
	HRESULT hr = ComCall<HRESULT>(dx.d3d11device, DEV_CreateBuffer, pDesc, pInitialData, ppBuffer);
	if (hr == E_OUTOFMEMORY)
	{
		Sys_OutOfMemErrorInternal(0x1B);
		return hr;
	}
	if (hr >= 0)
		sub_1401AFFE0(*ppBuffer);
	return hr;
}

// inlined into R_CreateDynamicBuffers (Black Ops' R_InitDynamicIndexBufferState)
static void R_InitDynamicIndexBufferState(GfxIndexBufferState *ib, int indexCount)
{
	ib->used = 0;
	ib->total = indexCount;
	R_AllocDynamicIndexBuffer(&ib->buffer, 2 * indexCount, nullptr);
}

// Store 140601BC0 (xb3 PDB gfx_d3d/r_buffers.cpp:1367)
void R_CreateDynamicBuffers()
{
	R_InitDynamicVertexBufferState(gfxBuf.dynamicVertexBufferPool, 0x100000, false);
	gfxBuf.dynamicVertexBuffer = gfxBuf.dynamicVertexBufferPool;
	int skinnedCacheBytes = r_SkinnedCacheSize->current.integer << 5;
	for (int i = 0; i < 3; ++i)
		R_InitDynamicVertexBufferState(&gfxBuf.skinnedCacheVbPool[i], skinnedCacheBytes, true);
	R_InitDynamicIndexBufferState(gfxBuf.dynamicIndexBufferPool, 0x100000);
	gfxBuf.dynamicIndexBuffer = gfxBuf.dynamicIndexBufferPool;
	for (int i = 0; i < 2; ++i)
		R_InitReactiveMotionConstantBufferState(&gfxBuf.reactiveMotionCbPool[i]);
}

// Store 140601D70 (name unknown; between R_CreateDynamicBuffers and R_CreateParticleCloudBuffer): a dynamic
// constant buffer, its size rounded up to 16 bytes. The name is not used. Same code as sub_1401AC2B0.
void sub_140601D70(unsigned int size, const char *name, ID3D11Buffer **constantBuffer)
{
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = (size + 15) & ~15u;
	desc.Usage = D3D11_USAGE_DYNAMIC;
	desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
	desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	desc.MiscFlags = 0;
	desc.StructureByteStride = 0;
	ID3D11Buffer *buffer;
	R_CreateBufferInternal(&desc, nullptr, &buffer);
	*constantBuffer = buffer;
}

// Store 140601E00 (xb3 PDB gfx_d3d/r_buffers.cpp:1561). 8 x 8 x 16 randomly jittered quads in [-1,1]^3 (four
// 20-byte vertices each, xyz + uv) and the same points as 8-vertex spark strips, each array sorted by distance to
// the origin. The four Alloc calls can return NULL (r_loadForRenderer off, or a failed map), which this writes
// through.
void R_CreateParticleCloudBuffer()
{
	short sparkQuadIndices[18] = {0, 2, 1, 1, 2, 3, 2, 4, 3, 3, 4, 5, 4, 6, 5, 5, 6, 7};

	WaitForSingleObject(dx.immediateContextMutex, 0xFFFFFFFF);
	if (!dx.immediateContextLockCount)
		dx.immediateContextThreadId = GetCurrentThreadId();
	++dx.immediateContextLockCount;

	float *verts = (float *)R_AllocStaticVertexBuffer(&g_drawConsts.particleCloudVertexBuffer, 0x14000,
	                                                  "Particle Cloud Verts");
	unsigned short *indices = (unsigned short *)R_AllocStaticIndexBuffer(&g_drawConsts.particleCloudIndexBuffer,
	                                                                     0x3000, "Particle Cloud Indices");
	unsigned short *sparkIndices = (unsigned short *)R_AllocStaticIndexBuffer(
		&g_drawConsts.particleCloudSparkIndexBuffer, 0x9000, "Particle Spark Cloud Indices");
	float *sparkVerts = (float *)R_AllocStaticVertexBuffer(&g_drawConsts.particleCloudSparkVertexBuffer, 0x28000,
	                                                       "Particle Spark Cloud Verts");
	float *vertsBase = verts;
	float *sparkVertsBase = sparkVerts;

	for (int x = 0; x < 8; ++x)
	{
		for (int y = 0; y < 8; ++y)
		{
			for (int z = 0; z < 16; ++z)
			{
				unsigned short quad = (unsigned short)(x * 128 + y * 16 + z);
				float px = ((float)rand() / 32767.0f + (float)x) * 0.25f - 1.0f;
				float py = ((float)rand() / 32767.0f + (float)y) * 0.25f - 1.0f;
				float pz = ((float)rand() / 32767.0f + (float)z) * 0.125f - 1.0f;

				static const float cornerTexCoords[4][2] = {{0.0f, 0.0f}, {0.0f, 1.0f}, {1.0f, 0.0f}, {1.0f, 1.0f}};
				for (int i = 0; i < 4; ++i)
				{
					verts[0] = px;
					verts[1] = py;
					verts[2] = pz;
					verts[3] = cornerTexCoords[i][0];
					verts[4] = cornerTexCoords[i][1];
					verts += 5;
				}
				unsigned short base = (unsigned short)(quad << 2);
				indices[0] = base;
				indices[1] = base + 1;
				indices[2] = base + 2;
				indices[3] = base + 2;
				indices[4] = base + 1;
				indices[5] = base + 3;
				indices += 6;

				static const float sparkCornerTexCoords[8][2] = {{0.0f, 0.0f},    {1.0f, 0.0f},    {0.0f, 0.3333f},
				                                                 {1.0f, 0.3333f}, {0.0f, 0.6667f}, {1.0f, 0.6667f},
				                                                 {0.0f, 1.0f},    {1.0f, 1.0f}};
				for (int i = 0; i < 8; ++i)
				{
					sparkVerts[0] = px;
					sparkVerts[1] = py;
					sparkVerts[2] = pz;
					sparkVerts[3] = sparkCornerTexCoords[i][0];
					sparkVerts[4] = sparkCornerTexCoords[i][1];
					sparkVerts += 5;
				}
				unsigned short sparkBase = (unsigned short)(quad << 3);
				for (int i = 0; i < 18; ++i)
					*sparkIndices++ = (unsigned short)(sparkBase + sparkQuadIndices[i]);
			}
		}
	}

	qsort(vertsBase, 0x400, 0x50, SortVerticesByDistanceToOrigin_CompareFunc);
	qsort(sparkVertsBase, 0x400, 0xA0, SortVerticesByDistanceToOrigin_CompareFunc);
	ComCall<void>(dx.immediateContext, CTX_Unmap, (ID3D11Resource *)g_drawConsts.particleCloudIndexBuffer, 0u);
	ComCall<void>(dx.immediateContext, CTX_Unmap, (ID3D11Resource *)g_drawConsts.particleCloudVertexBuffer, 0u);
	ComCall<void>(dx.immediateContext, CTX_Unmap, (ID3D11Resource *)g_drawConsts.particleCloudSparkIndexBuffer, 0u);
	ComCall<void>(dx.immediateContext, CTX_Unmap, (ID3D11Resource *)g_drawConsts.particleCloudSparkVertexBuffer, 0u);

	if (!--dx.immediateContextLockCount)
		dx.immediateContextThreadId = 0xFFFFFFFF;
	ReleaseMutex(dx.immediateContextMutex);
}

// Store 140602360 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void R_DestroyDynamicBuffers()
{
	R_UnlockSkinnedCache();
	if (gfxBuf.dynamicIndexBufferPool[0].buffer)
	{
		sub_1401B0000(gfxBuf.dynamicIndexBufferPool[0].buffer);
		ComCall<unsigned long>(gfxBuf.dynamicIndexBufferPool[0].buffer, UNK_Release);
		gfxBuf.dynamicIndexBufferPool[0].buffer = nullptr;
	}
	for (int i = 0; i < 3; ++i)
		R_DestroyDynamicVertexBufferState(&gfxBuf.skinnedCacheVbPool[i]);
	R_DestroyDynamicVertexBufferState(gfxBuf.dynamicVertexBufferPool);
	for (int i = 0; i < 2; ++i)
		sub_1401B1EC0(&gfxBuf.reactiveMotionCbPool[i]);
}

// Store 1406024D0 (xb3 PDB gfx_d3d/r_material.cpp:1928 by line table; PS4 MAP name)
void R_DestroyDynamicVertexBufferState(GfxVertexBufferState *vb)
{
	if (vb->buffer)
	{
		sub_1401B0000(vb->buffer);
		ComCall<unsigned long>(vb->buffer, UNK_Release);
		vb->buffer = nullptr;
	}
	if (vb->rawUav)
	{
		ComCall<unsigned long>(vb->rawUav, UNK_Release);
		vb->rawUav = nullptr;
	}
	if (vb->rawView)
	{
		ComCall<unsigned long>(vb->rawView, UNK_Release);
		vb->rawView = nullptr;
	}
	if (vb->rawBuffer)
	{
		sub_1401B0000(vb->rawBuffer);
		ComCall<unsigned long>(vb->rawBuffer, UNK_Release);
		vb->rawBuffer = nullptr;
	}
}

// Store 140602550 (xb3 PDB gfx_d3d/r_buffers.cpp:1710)
void R_DestroyParticleCloudBuffer()
{
	ID3D11Buffer *buffer = g_drawConsts.particleCloudVertexBuffer;
	if (buffer)
	{
		sub_1401B0000(buffer);
		ComCall<unsigned long>(buffer, UNK_Release);
		g_drawConsts.particleCloudVertexBuffer = nullptr;
	}
	buffer = g_drawConsts.particleCloudIndexBuffer;
	if (buffer)
	{
		sub_1401B0000(buffer);
		ComCall<unsigned long>(buffer, UNK_Release);
		g_drawConsts.particleCloudIndexBuffer = nullptr;
	}
	buffer = g_drawConsts.particleCloudSparkVertexBuffer;
	if (buffer)
	{
		sub_1401B0000(buffer);
		ComCall<unsigned long>(buffer, UNK_Release);
		g_drawConsts.particleCloudSparkVertexBuffer = nullptr;
	}
	buffer = g_drawConsts.particleCloudSparkIndexBuffer;
	if (buffer)
	{
		sub_1401B0000(buffer);
		ComCall<unsigned long>(buffer, UNK_Release);
		g_drawConsts.particleCloudSparkIndexBuffer = nullptr;
	}
}

// Store 140602600 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void R_FreeStaticVertexBuffer(ID3D11Buffer *vb)
{
	sub_1401B0000(vb);
	ComCall<unsigned long>(vb, UNK_Release);
}

// Store 140602620 (name unknown): a buffer's ByteWidth, for the accounting functions
unsigned int sub_140602620(ID3D11Buffer *buffer)
{
	D3D11_BUFFER_DESC desc;
	ComCall<void>(buffer, BUF_GetDesc, &desc);
	return desc.ByteWidth;
}

// Store 140602640 (xb3 PDB gfx_d3d/r_buffers.cpp:1212). The Store build creates the buffer here (the servers only
// clear the state) and, for compute, a raw copy with a shader resource view and an unordered access view.
void R_InitDynamicVertexBufferState(GfxVertexBufferState *vb, int bytes, bool compute)
{
	vb->used = 0;
	vb->total = 0;
	vb->buffer = nullptr;
	vb->verts = nullptr;
	vb->rawBuffer = nullptr;
	vb->rawView = nullptr;
	vb->rawUav = nullptr;
	vb->used = 0;
	vb->total = bytes;
	if (r_loadForRenderer->current.enabled)
	{
		D3D11_BUFFER_DESC desc;
		desc.ByteWidth = bytes;
		desc.Usage = D3D11_USAGE_DYNAMIC;
		desc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
		desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
		desc.MiscFlags = 0;
		R_CreateBufferInternal(&desc, nullptr, &vb->buffer);
	}
	vb->verts = nullptr;
	if (compute)
	{
		sub_1401AC310(bytes, D3D11_BIND_VERTEX_BUFFER | D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_UNORDERED_ACCESS,
		              D3D11_USAGE_DEFAULT, nullptr, "Dynamic Vertex Raw Buffer", &vb->rawBuffer);
		sub_140631780(dx.d3d11device, vb->rawBuffer);
		sub_1401AC3F0(vb->rawBuffer, "Dynamic Vertex Buffer View", &vb->rawView);
		sub_1401AC380(vb->rawBuffer, "Dynamic Vertex Buffer View", &vb->rawUav);
	}
}

// Store 140602760 (xb3 PDB gfx_d3d/r_buffers.cpp, stubbed there). `bytes` is not used: the whole buffer is mapped.
void *R_LockIndexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle, int offset, int bytes, D3D11_MAP lockFlags)
{
	D3D11_MAPPED_SUBRESOURCE mapped;
	HRESULT hr = ComCall<HRESULT>(device, CTX_Map, (ID3D11Resource *)handle, 0u, lockFlags, 0u, &mapped);
	if (hr < 0)
		R_FatalLockError(hr);
	return (unsigned char *)mapped.pData + offset;
}

// Store 1406027B0 (xb3 PDB gfx_d3d/r_buffers.cpp, stubbed there)
void *R_LockVertexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle, int offset, int bytes, D3D11_MAP lockFlags)
{
	D3D11_MAPPED_SUBRESOURCE mapped;
	HRESULT hr = ComCall<HRESULT>(device, CTX_Map, (ID3D11Resource *)handle, 0u, lockFlags, 0u, &mapped);
	if (hr < 0)
		R_FatalLockError(hr);
	return (unsigned char *)mapped.pData + offset;
}

// Store 140602800 (xb3 PDB gfx_d3d/r_buffers.cpp:1825). Returns the reference count Release returned.
HRESULT R_ReleaseBuffer(ID3D11Buffer *buffer)
{
	D3D11_BUFFER_DESC desc;
	ComCall<void>(buffer, BUF_GetDesc, &desc);
	HRESULT refs = ComCall<HRESULT>(buffer, UNK_Release);
	if (!refs)
		sub_1401B0020(buffer, desc.ByteWidth);
	return refs;
}

// Store 140602840 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void R_UnlockIndexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle)
{
	ComCall<void>(device, CTX_Unmap, (ID3D11Resource *)handle, 0u);
}

// Store 140602850 (xb3 PDB gfx_d3d/r_buffers.cpp:1117, stubbed there)
void R_UnlockVertexBuffer(ID3D11DeviceContext *device, ID3D11Buffer *handle)
{
	ComCall<void>(device, CTX_Unmap, (ID3D11Resource *)handle, 0u);
}

// Store 140602860 (xb3 PDB gfx_d3d/r_buffers.cpp:1529, a file static there)
int SortVerticesByDistanceToOrigin_CompareFunc(const void *a, const void *b)
{
	const float *va = (const float *)a;
	const float *vb = (const float *)b;
	float da = va[0] * va[0] + va[1] * va[1] + va[2] * va[2];
	float db = vb[0] * vb[0] + vb[1] * vb[1] + vb[2] * vb[2];
	if (da < db)
		return -1;
	if (da == db)
		return 0;
	return 1;
}

// ---- gfx_d3d/r_init.cpp (PS4 PDB) ---------------------------------------------------------------------------
#undef IW6_SOURCE
#define IW6_SOURCE "gfx_d3d/r_init.cpp"

// Store 140630360 (PS4 PDB gfx_d3d/r_init.cpp:1664). The handle of a default constant buffer of `size` bytes for
// `type` (0 per primitive, 1 per object, 2 stable): an existing default one, else a new default entry that shares a
// zone's buffer of that size (AddRef) or a newly created one. The index into a zone's table is a byte, so a zone
// with more than 255 buffers of other sizes loops forever.
unsigned char R_GetConstantBufferHandleOfSize(unsigned int type, unsigned int size)
{
	IW6_STATIC const char *constantBufferNames[3] IW6_AT("R_GetConstantBufferHandleOfSize", "constantBufferNames");

	if (!size)
		return 0;
	bool found = false;
	unsigned char zone;
	unsigned char index;
	for (zone = 0; zone < 80; ++zone)
	{
		unsigned int count = dx.constantBufferCounts[type][zone];
		if (!count)
			continue;
		for (index = 0; index < count; ++index)
		{
			D3D11_BUFFER_DESC desc;
			ComCall<void>(dx.constantBufferTables[type][zone][index].buffer, BUF_GetDesc, &desc);
			if (desc.ByteWidth == size)
			{
				found = true;
				if (!zone)
					return index;
				goto add;
			}
		}
	}
add:
	unsigned char handle = (unsigned char)dx.constantBufferCounts[type][0];
	if (handle >= 0x80)
		Com_Error(ERR_FATAL, "Out of %s constant buffer size configurations", constantBufferNames[type]);
	dx.constantBufferCounts[type][0] = handle + 1;
	if (found)
	{
		ID3D11Buffer *buffer = dx.constantBufferTables[type][zone][index].buffer;
		dx.defaultConstantBuffers[type][handle].buffer = buffer;
		ComCall<unsigned long>(buffer, UNK_AddRef);
	}
	else
	{
		D3D11_BUFFER_DESC desc;
		desc.ByteWidth = size;
		desc.Usage = D3D11_USAGE_DYNAMIC;
		desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
		desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
		desc.MiscFlags = 0;
		desc.StructureByteStride = 0;
		ID3D11Buffer *buffer;
		R_CreateBufferInternal(&desc, nullptr, &buffer);
		dx.defaultConstantBuffers[type][handle].buffer = buffer;
	}
	return handle;
}

// Store 140630520 (PS4 PDB gfx_d3d/r_init.cpp:1788)
ID3D11Buffer *R_GetPerPrimConstantBufferOfSize(unsigned int size)
{
	if (!size)
		return nullptr;
	return dx.defaultConstantBuffers[0][R_GetConstantBufferHandleOfSize(0, size)].buffer;
}
