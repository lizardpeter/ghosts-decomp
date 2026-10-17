// gfx_d3d/r_init.cpp (Store build)

// ==== BEGIN images ====
// The adapter's memory sizes (DXGI_ADAPTER_DESC), which the image code budgets textures against. Names unknown.

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"
#include "qcommon/dvar.h"

extern "C" const GUID IID_IDXGIDevice;  // dxguid
extern const dvar_t *r_amdGPU;
extern const dvar_t *r_amdGPUVideoMemoryScale;

// Store 140630CA0 (name unknown): the adapter's shared system memory
unsigned long long sub_140630CA0()
{
	IDXGIDevice *dxgiDevice;
	IDXGIAdapter *adapter;
	DXGI_ADAPTER_DESC desc;

	ComCall<long>(dx.d3d11device, UNK_QueryInterface, &IID_IDXGIDevice, &dxgiDevice);
	ComCall<long>(dxgiDevice, DXGIDEVICE_GetAdapter, &adapter);
	ComCall<long>(adapter, DXGIADAPTER_GetDesc, &desc);
	ComCall<unsigned long>(dxgiDevice, UNK_Release);
	ComCall<unsigned long>(adapter, UNK_Release);
	return desc.SharedSystemMemory;
}

// Store 140630D20 (name unknown): the adapter's dedicated video and system memory, scaled by
// r_amdGPUVideoMemoryScale when r_amdGPU is set
unsigned long long sub_140630D20()
{
	IDXGIDevice *dxgiDevice;
	IDXGIAdapter *adapter;
	DXGI_ADAPTER_DESC desc;

	ComCall<long>(dx.d3d11device, UNK_QueryInterface, &IID_IDXGIDevice, &dxgiDevice);
	ComCall<long>(dxgiDevice, DXGIDEVICE_GetAdapter, &adapter);
	ComCall<long>(adapter, DXGIADAPTER_GetDesc, &desc);
	ComCall<unsigned long>(dxgiDevice, UNK_Release);
	ComCall<unsigned long>(adapter, UNK_Release);
	unsigned long long memory = desc.DedicatedSystemMemory + desc.DedicatedVideoMemory;
	if (r_amdGPU->current.enabled)
		return (unsigned long long)((float)memory * r_amdGPUVideoMemoryScale->current.value);
	return memory;
}

static_assert(sizeof(DXGI_ADAPTER_DESC) == 0x130, "DXGI_ADAPTER_DESC");
static_assert(__builtin_offsetof(DXGI_ADAPTER_DESC, DedicatedVideoMemory) == 0x110, "DXGI_ADAPTER_DESC");
static_assert(__builtin_offsetof(DXGI_ADAPTER_DESC, SharedSystemMemory) == 0x120, "DXGI_ADAPTER_DESC");
// ==== END images ====
