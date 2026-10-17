// gfx_d3d/com_call.h: calling Direct3D 11 / DXGI COM methods from reconstructed code.
//
// Build environment, not game source: the reconstruction is built without the Windows SDK, so instead of
// d3d11.h it calls methods through the object's vtable by slot number. The behaviour is the same as the
// original's `ctx->lpVtbl->Method(ctx, ...)`: load the vtable from the object, call the slot with the object as
// the first argument. Slot numbers are the methods' positions in the public interfaces, named in the enums
// below as each one is needed (each verified against a call in the Store build).
#pragma once

struct IUnknownObject;  // any COM object: its first member is the vtable pointer

template <typename R, typename... A>
inline R ComCall(const void *object, unsigned int slot, A... args)
{
	typedef R (*Method)(const void *, A...);
	return ((Method)(*(void *const *const *)object)[slot])(object, args...);
}

// ID3D11DeviceContext
enum D3D11ContextSlot : unsigned int
{
	CTX_PSSetShader = 9,
	CTX_IASetInputLayout = 17,
	CTX_VSSetShader = 11,
	CTX_HSSetShader = 60,
	CTX_DSSetShader = 64,
};

// ---- device ----
// Slots used by the device and swap chain code (gfx_d3d/r_init.cpp); each checked against a call in the Store build.
enum ComUnknownSlot : unsigned int
{
	UNKNOWN_Release = 2,
};

// IDXGIFactory
enum DXGIFactorySlot : unsigned int
{
	FACTORY_EnumAdapters = 7,
	FACTORY_MakeWindowAssociation = 8,
	FACTORY_CreateSwapChain = 10,
};

// IDXGIAdapter
enum DXGIAdapterSlot : unsigned int
{
	ADAPTER_EnumOutputs = 7,
	ADAPTER_GetDesc = 8,
};

// IDXGIOutput
enum DXGIOutputSlot : unsigned int
{
	OUTPUT_GetDesc = 7,
	OUTPUT_GetDisplayModeList = 8,
};

// IDXGISwapChain
enum DXGISwapChainSlot : unsigned int
{
	SWAPCHAIN_Present = 8,
	SWAPCHAIN_GetBuffer = 9,
	SWAPCHAIN_SetFullscreenState = 10,
	SWAPCHAIN_GetFullscreenState = 11,
	SWAPCHAIN_GetDesc = 12,
};

// ID3D11Device
enum D3D11DeviceLifecycleSlot : unsigned int
{
	DEVICE_CreateQuery = 24,
	DEVICE_CreateDeferredContext = 27,
	DEVICE_CheckMultisampleQualityLevels = 30,
	DEVICE_GetDeviceRemovedReason = 39,
};

// ID3D11DeviceContext
enum D3D11ContextLifecycleSlot : unsigned int
{
	CTX_End = 28,
	CTX_GetData = 29,
	CTX_ClearState = 110,
	CTX_Flush = 111,
};

// ID3D11Query (ID3D11Asynchronous)
enum D3D11QuerySlot : unsigned int
{
	QUERY_GetDataSize = 7,
};
