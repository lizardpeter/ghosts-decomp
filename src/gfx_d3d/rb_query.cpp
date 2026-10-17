// gfx_d3d/rb_query.cpp (Store build)
//
// Direct3D 11 queries from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses: the GPU
// fences (event queries: dx.fencePool, the swap fence) and the occlusion queries (occlusionQueryArray, from the
// servers' gfx_d3d/rb_query.cpp, whose query code is stubbed there). Also the device-resource set-up that creates
// them (14062F700, Black Ops' R_CreateForInitOrReset). Names are unknown unless given; line numbers are unknown.
//
// Queries are polled with GetData(query, NULL, 0, 0) until it stops returning S_FALSE; every poll is preceded by a
// GetDataSize() call whose result is unused (an inline helper's leftover).

#include <iw6_static.h>

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_state_d3d11.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "gfx_d3d/rb_query.cpp"

// Sys_EnterCriticalSection's index for the occlusion queries: one more than the PS4 server's
// CRITSECT_OCCLUSION_QUERY (0x29), as the Store build's enum has another entry before it
#define CRITSECT_OCCLUSION_QUERY_STORE ((CriticalSection)0x2A)

struct OcclusionQuery  // xb3 PDB
{
	bool enabled;
	bool error;
	bool isWorldPos;
	bool isValidPos;
	float position[3];
	float depthBias;
	float lastVisibility;
	int localClientNum;
	int hitNum;
	bool issued[4];
	ID3D11Query *query[4];
	int nextQueryIndexPlusOne;
	unsigned long long prevQueryData;
};

static_assert(sizeof(OcclusionQuery) == 0x58, "OcclusionQuery layout");
static_assert(__builtin_offsetof(OcclusionQuery, query) == 0x28, "OcclusionQuery layout");

extern OcclusionQuery occlusionQueryArray[32];
extern bool g_allocateMinimalResources;
extern ID3D11Query *unk_14A346A98;  // an occlusion query 14062F700 creates (Black Ops: gfxAssets.pixelCountQuery)
extern int unk_14A346A00;           // set while unk_14A346A08 is in flight
extern ID3D11Query *unk_14A346A08;

extern "C" {
int ReleaseMutex(void *hMutex);
void Sleep(unsigned long dwMilliseconds);
}

void Sys_CheckQuitRequest();
void R_LockImmediateContextWithPumpOnMain();
long R_CreateBufferInternal(const D3D11_BUFFER_DESC *desc, const D3D11_SUBRESOURCE_DATA *initialData,
                            ID3D11Buffer **buffer);
void R_BuildSubDomainRangeConstantBuffers();
void R_InitRenderBuffers();
void R_SetupPrecompiledConstantBuffer();
void R_InitDefaultDepthImage();
void R_InitDaltonize();
void sub_1401B6130();
void sub_140640510();
void sub_1406310F0();  // r_state.cpp: the rasterizer states
void sub_1406508E0();
void sub_14068C300();
void sub_14063EBD0();
void sub_1401B1400();
void sub_140601BC0();
void sub_14068EAE0();
void sub_140601E00();
void sub_14068D600();
void sub_1401AAEF0();
void sub_1401AB1C0();

// R_LockImmediateContextWithPumpOnMain's counterpart, inline in the original (gfx_d3d/r_globals_d3d.h)
static inline void R_UnlockImmediateContext()
{
	if (--dx.immediateContextLockCount == 0)
		dx.immediateContextThreadId = 0xFFFFFFFF;
	ReleaseMutex(dxs.immediateContextMutex);
}

// Store 14068BC80 (name unknown): creates the four occlusion queries of every occlusionQueryArray entry; a query
// that fails to create stays NULL.
void sub_14068BC80()
{
	Sys_EnterCriticalSection(CRITSECT_OCCLUSION_QUERY_STORE);
	for (int queryIndex = 0; queryIndex < 32; queryIndex++)
	{
		for (int gpuIndex = 0; gpuIndex < 4; gpuIndex++)
		{
			D3D11_QUERY_DESC desc;
			ID3D11Query *query;
			desc.Query = D3D11_QUERY_OCCLUSION;
			desc.MiscFlags = 0;
			long hr = ComCall<long>(dx.d3d11device, DEV_CreateQuery, (const D3D11_QUERY_DESC *)&desc, &query);
			occlusionQueryArray[queryIndex].query[gpuIndex] = hr < 0 ? nullptr : query;
			occlusionQueryArray[queryIndex].issued[gpuIndex] = false;
		}
	}
	Sys_LeaveCriticalSection(CRITSECT_OCCLUSION_QUERY_STORE);
}

// Store 14065BE70 (name unknown): waits for the swap fence while it is in flight
void sub_14065BE70()
{
	while (dxs.unk_7D00)
	{
		ID3D11Query *fence = dxs.swapFence;
		ComCall<unsigned int>(fence, ASYNC_GetDataSize);
		if (ComCall<long>(dx.immediateContext, CTX_GetData, fence, (void *)nullptr, 0u, 0u) != S_FALSE)
		{
			dxs.unk_7D00 = false;
			break;
		}
	}
}

// Store 14067D210 (name unknown): takes the next fence of dx.fencePool, waits until its previous use has
// signalled, and ends it again (inserts it into the command stream). The immediate context lock is inlined.
void sub_14067D210(ID3D11Query **fence)
{
	R_LockImmediateContextWithPumpOnMain();
	*fence = dxs.fencePool[dxs.nextFence];
	dxs.nextFence = (dxs.nextFence + 1) & 31;
	ID3D11Query *query;
	do
	{
		query = *fence;
		ComCall<unsigned int>(query, ASYNC_GetDataSize);
	} while (ComCall<long>(dx.immediateContext, CTX_GetData, query, (void *)nullptr, 0u, 0u) == S_FALSE);
	ComCall<void>(dx.immediateContext, CTX_End, *fence);
	R_UnlockImmediateContext();
}

// Store 14062DFF0 (name unknown): when unk_14A346A08 has been issued, waits for it, sleeping 1 ms between polls
// and checking for a quit request; returns whether it had to wait.
int sub_14062DFF0()
{
	if (!unk_14A346A00)
		return 0;
	int waited = 0;
	unk_14A346A00 = 0;
	while (unk_14A346A08)
	{
		unsigned int data;
		R_LockImmediateContextWithPumpOnMain();
		ID3D11Query *query = unk_14A346A08;
		ComCall<unsigned int>(query, ASYNC_GetDataSize);
		long hr = ComCall<long>(dx.immediateContext, CTX_GetData, query, (void *)&data, 4u, 0u);
		R_UnlockImmediateContext();
		if (hr != S_FALSE)
			break;
		waited = 1;
		Sys_CheckQuitRequest();
		Sleep(1);
	}
	return waited;
}

// Store 14062F700 (name unknown; Black Ops' R_CreateForInitOrReset, gfx_d3d/r_init.cpp): creates the renderer's
// device resources after the device is created or reset. With isReset, the GPU fences, the occlusion queries and
// the resources a reset keeps are left alone. Returns false when a fence can't be created.
bool sub_14062F700(int isReset)
{
	D3D11_BUFFER_DESC bufferDesc;
	ID3D11Buffer *buffer;

	dxs.constantBufferTables[0][0] = dxs.defaultConstantBuffers[0];
	dxs.constantBufferTables[1][0] = dxs.defaultConstantBuffers[1];
	dxs.constantBufferTables[2][0] = dxs.defaultConstantBuffers[2];
	R_BuildSubDomainRangeConstantBuffers();
	sub_1401B6130();
	bufferDesc.ByteWidth = 0x2000;
	bufferDesc.Usage = D3D11_USAGE_DYNAMIC;
	bufferDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
	bufferDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	bufferDesc.MiscFlags = 0;
	bufferDesc.StructureByteStride = 0;
	R_CreateBufferInternal(&bufferDesc, nullptr, &buffer);
	dxs.smodelWorldMatrixConstantBuffer = buffer;
	bufferDesc.ByteWidth = 0x800;
	bufferDesc.Usage = D3D11_USAGE_DYNAMIC;
	bufferDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
	bufferDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	bufferDesc.MiscFlags = 0;
	bufferDesc.StructureByteStride = 0;
	R_CreateBufferInternal(&bufferDesc, nullptr, &buffer);
	dxs.smodelLightingOrAmbientConstantBuffer = buffer;
	sub_140640510();
	sub_1406310F0();
	dxs.depthStencilStateTables[0] = dxs.defaultDepthStencilStates;
	dxs.blendStateTables[0] = dxs.defaultBlendStates;
	sub_1406508E0();
	sub_14068C300();
	if (!g_allocateMinimalResources)
	{
		R_InitRenderBuffers();
		if (!isReset)
		{
			sub_14063EBD0();
			sub_1401B1400();
		}
	}
	sub_140601BC0();
	R_SetupPrecompiledConstantBuffer();
	R_InitDefaultDepthImage();
	R_InitDaltonize();
	sub_14068EAE0();
	if (!g_allocateMinimalResources)
		sub_140601E00();
	dxs.unk_7D00 = false;
	if (!isReset)
	{
		D3D11_QUERY_DESC queryDesc;
		queryDesc.Query = D3D11_QUERY_EVENT;
		queryDesc.MiscFlags = 0;
		if (ComCall<long>(dx.d3d11device, DEV_CreateQuery, (const D3D11_QUERY_DESC *)&queryDesc, &dxs.swapFence) < 0)
			return false;
		dxs.nextFence = 0;
		for (unsigned int fenceIter = 0; fenceIter < 32; fenceIter++)
		{
			queryDesc.Query = D3D11_QUERY_EVENT;
			queryDesc.MiscFlags = 0;
			if (ComCall<long>(dx.d3d11device, DEV_CreateQuery, (const D3D11_QUERY_DESC *)&queryDesc,
			                  &dxs.fencePool[fenceIter]) < 0)
				return false;
		}
	}
	if (!g_allocateMinimalResources && !isReset)
	{
		sub_14068BC80();
		sub_14068D600();
		D3D11_QUERY_DESC queryDesc;
		ID3D11Query *query;
		queryDesc.Query = D3D11_QUERY_OCCLUSION;
		queryDesc.MiscFlags = 0;
		long hr = ComCall<long>(dx.d3d11device, DEV_CreateQuery, (const D3D11_QUERY_DESC *)&queryDesc, &query);
		unk_14A346A98 = hr < 0 ? nullptr : query;
		sub_1401AAEF0();
	}
	else
	{
		sub_1401AAEF0();
		if (isReset)
			sub_1401AB1C0();
	}
	return true;
}

// ---- occlusion queries --------------------------------------------------------------------------------------------

enum GfxWarningType
{
	R_WARN_OCCLUSION_QUERY = 0x43,  // xb3 PDB
};

// What sub_14068BE20 reads from the structure it is given (name and type unknown; the caller is 14067BAD0)
struct OcclusionViewData
{
	unsigned char unknown_0[0x170];
	unsigned char unk_170[0x1820 - 0x170];  // passed to 14068D360, which draws the queried sprites
	int localClientNum;                     // 0x1820
	unsigned char unknown_1824[0x18B4 - 0x1824];
	bool unk_18B4;                          // multisampled: the sample limit is dx.multiSampleType * 256
};

static_assert(__builtin_offsetof(OcclusionViewData, localClientNum) == 0x1820, "OcclusionViewData layout");
static_assert(__builtin_offsetof(OcclusionViewData, unk_18B4) == 0x18B4, "OcclusionViewData layout");

extern int unk_14A37D598;   // frame counter: its low two bits pick one of an occlusion query's four D3D queries
extern void *unk_14A34B488; // the material 14068D370 is given for the query sprites
extern int unk_14BACB0CC;   // set when something is batched that 14068D350 flushes

void R_WarnOncePerFrame(GfxWarningType warnType, ...);
void sub_140675180();
void sub_14068CE80(OcclusionQuery *query);
void sub_14068D370(void *material, int techType, int unknown);
void sub_14068CAC0(const float *position, bool isWorldPos, float width, float height, unsigned int color,
                   float depthBias);
void sub_14068D360(void *input);
void sub_14068D350();

// Store 14068C260 (name unknown): an occlusion query's sample count; -2 while it isn't ready (S_FALSE), -1 when
// GetData fails
unsigned long long sub_14068C260(ID3D11Query *query)
{
	unsigned long long samples;
	ComCall<unsigned int>(query, ASYNC_GetDataSize);
	long hr = ComCall<long>(dx.immediateContext, CTX_GetData, query, (void *)&samples, 8u, 0u);
	if (hr == S_FALSE)
		return (unsigned long long)-2;
	return hr < 0 ? (unsigned long long)-1 : samples;
}

// Store 14068BE20 (name unknown; the servers' rb_query.cpp has the rest of the occlusion query code): once a frame,
// for each enabled occlusion query of this view's local client with a position: read the samples of the queries
// issued in earlier frames (waiting, with Sleep(0), for the oldest when nothing newer is known), turn them into
// lastVisibility (samples / 256, or / (multiSampleType * 256) multisampled, at most 1; 0 when this frame's query
// was never issued), then issue this frame's query around a 16 x 16 sprite at the position. Four D3D queries per
// occlusion query, one per frame in flight.
void sub_14068BE20(OcclusionViewData *view)
{
	int localClientNum = view->localClientNum;
	sub_140675180();
	for (OcclusionQuery *query = occlusionQueryArray; query < &occlusionQueryArray[32]; query++)
	{
		if (!query->enabled || query->localClientNum != localClientNum)
			continue;
		if (query->isValidPos)
		{
			int gpuIndex = unk_14A37D598 % 4;
			if (!query->query[gpuIndex])
			{
				sub_14068CE80(query);
			}
			else
			{
				float visibility;
				sub_140675180();
				sub_14068D370(unk_14A34B488, 2, 5);
				sub_14068CAC0(query->position, query->isWorldPos, 16.0f, 16.0f, 0xFF000000, query->depthBias);
				if (!query->issued[gpuIndex])
				{
					visibility = 0.0f;
				}
				else
				{
					unsigned long long samples;
					int queryIndex;
					if (query->nextQueryIndexPlusOne && query->nextQueryIndexPlusOne != gpuIndex + 1)
					{
						samples = query->prevQueryData;
						queryIndex = query->nextQueryIndexPlusOne - 1;
					}
					else
					{
						samples = sub_14068C260(query->query[gpuIndex]);
						while (samples == (unsigned long long)-2)
						{
							unsigned long long data;
							long hr;
							do
							{
								Sleep(0);
								ID3D11Query *d3dQuery = query->query[gpuIndex];
								ComCall<unsigned int>(d3dQuery, ASYNC_GetDataSize);
								hr = ComCall<long>(dx.immediateContext, CTX_GetData, d3dQuery, (void *)&data, 8u, 0u);
							} while (hr == S_FALSE);
							samples = hr < 0 ? (unsigned long long)-1 : data;
						}
						queryIndex = (gpuIndex + 1) % 4;
					}
					if (samples != (unsigned long long)-1)
					{
						while (queryIndex != gpuIndex)
						{
							if (query->issued[queryIndex])
							{
								unsigned long long data;
								ID3D11Query *d3dQuery = query->query[queryIndex];
								ComCall<unsigned int>(d3dQuery, ASYNC_GetDataSize);
								long hr = ComCall<long>(dx.immediateContext, CTX_GetData, d3dQuery, (void *)&data, 8u, 0u);
								if (hr == S_FALSE)
									break;
								unsigned long long result = hr < 0 ? (unsigned long long)-1 : data;
								if (result > (unsigned long long)-3)
									break;
								samples = result;
							}
							queryIndex = (queryIndex + 1) % 4;
						}
					}
					query->prevQueryData = samples;
					query->nextQueryIndexPlusOne = queryIndex + 1;
					if (samples == (unsigned long long)-1)
						query->error = true;
					unsigned int maxSamples = view->unk_18B4 ? dxs.multiSampleType << 8 : 0x100;
					if (samples > maxSamples)
					{
						query->error = true;
						R_WarnOncePerFrame(R_WARN_OCCLUSION_QUERY, samples, maxSamples);
					}
					visibility = (float)samples / (float)maxSamples;
					if (!(visibility <= 1.0f))  // NaN (0 / 0) becomes 1 too
						visibility = 1.0f;
				}
				if (!query->error)
					query->lastVisibility = visibility;
				query->error = false;
				ComCall<void>(dx.immediateContext, CTX_Begin, query->query[gpuIndex]);
				sub_14068D360(view->unk_170);
				ComCall<void>(dx.immediateContext, CTX_End, query->query[gpuIndex]);
				query->issued[gpuIndex] = true;
			}
		}
		if (unk_14BACB0CC)
			sub_14068D350();
	}
}
