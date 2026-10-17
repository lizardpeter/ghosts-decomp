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

// One enum per interface, by vtable position (IUnknown 0-2 come first in all of them). Each slot is checked
// against a call in the Store build; the functions using it say where.

// IUnknown
enum IUnknownSlot : unsigned int
{
	UNK_QueryInterface = 0,
	UNK_AddRef = 1,
	UNK_Release = 2,
};

// ID3D11Device
enum D3D11DeviceSlot : unsigned int
{
	DEV_CreateBuffer = 3,
	DEV_CreateTexture1D = 4,
	DEV_CreateTexture2D = 5,
	DEV_CreateTexture3D = 6,
	DEV_CreateShaderResourceView = 7,
	DEV_CreateUnorderedAccessView = 8,
	DEV_CreateRenderTargetView = 9,
	DEV_CreateDepthStencilView = 10,
	DEV_CreateInputLayout = 11,
	DEV_CreateVertexShader = 12,
	DEV_CreatePixelShader = 15,
	DEV_CreateHullShader = 16,
	DEV_CreateDomainShader = 17,
	DEV_CreateComputeShader = 18,
	DEV_CreateBlendState = 20,
	DEV_CreateDepthStencilState = 21,
	DEV_CreateRasterizerState = 22,
	DEV_CreateSamplerState = 23,
	DEV_CreateQuery = 24,
	DEV_CreateDeferredContext = 27,
	DEV_CheckMultisampleQualityLevels = 30,
	DEV_GetDeviceRemovedReason = 39,
};

// ID3D11DeviceContext
enum D3D11ContextSlot : unsigned int
{
	CTX_PSSetShader = 9,
	CTX_VSSetShader = 11,
	CTX_Map = 14,
	CTX_Unmap = 15,
	CTX_IASetInputLayout = 17,
	CTX_Begin = 27,
	CTX_End = 28,
	CTX_GetData = 29,
	CTX_CopySubresourceRegion = 46,
	CTX_UpdateSubresource = 48,
	CTX_HSSetShader = 60,
	CTX_DSSetShader = 64,
	CTX_ClearState = 110,
	CTX_Flush = 111,
};

// Device children: ID3D11Resource / ID3D11View / ID3D11Asynchronous (7), ID3D11Buffer::GetDesc and
// ID3D11RenderTargetView::GetDesc
enum D3D11ChildSlot : unsigned int
{
	VIEW_GetResource = 7,
	ASYNC_GetDataSize = 7,
	RTV_GetDesc = 8,
	BUF_GetDesc = 10,
};

// IDXGIFactory
enum DXGIFactorySlot : unsigned int
{
	FACTORY_EnumAdapters = 7,
	FACTORY_MakeWindowAssociation = 8,
	FACTORY_CreateSwapChain = 10,
};

// IDXGIDevice
enum DXGIDeviceSlot : unsigned int
{
	DXGIDEVICE_GetAdapter = 7,
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
