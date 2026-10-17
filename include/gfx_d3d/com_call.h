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

// ---- images ----
// IUnknown (every interface)
enum ComUnknownSlot : unsigned int
{
	UNK_QueryInterface = 0,
	UNK_AddRef = 1,
	UNK_Release = 2,
};

// ID3D11Device
enum D3D11DeviceSlot : unsigned int
{
	DEV_CreateTexture1D = 4,
	DEV_CreateTexture2D = 5,
	DEV_CreateTexture3D = 6,
	DEV_CreateShaderResourceView = 7,
	DEV_CreateUnorderedAccessView = 8,
	DEV_CreateRenderTargetView = 9,
	DEV_CreateDepthStencilView = 10,
};

// ID3D11DeviceContext (images)
enum D3D11ContextImageSlot : unsigned int
{
	CTX_CopySubresourceRegion = 46,
	CTX_UpdateSubresource = 48,
};

// ID3D11View, ID3D11RenderTargetView, ID3D11Buffer
enum D3D11ObjectSlot : unsigned int
{
	VIEW_GetResource = 7,
	RTV_GetDesc = 8,
	BUFFER_GetDesc = 10,
};

// IDXGIDevice, IDXGIAdapter, IDXGISwapChain
enum DXGIObjectSlot : unsigned int
{
	DXGIDEVICE_GetAdapter = 7,
	DXGIADAPTER_GetDesc = 8,
	SWAPCHAIN_GetBuffer = 9,
};
