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

// ---- states ----
// ID3D11Device methods that create pipeline state objects, shaders, input layouts and queries
enum D3D11DeviceStateSlot : unsigned int
{
	DEV_CreateInputLayout = 11,       // 140665180
	DEV_CreateVertexShader = 12,      // 14063AE60, 14063BC10
	DEV_CreatePixelShader = 15,       // 14063ADD0, 14063BB80
	DEV_CreateHullShader = 16,        // 14063AD70, 14063BB10
	DEV_CreateDomainShader = 17,      // 14063AD10, 14063BAA0
	DEV_CreateComputeShader = 18,     // 14063AC20, 14063BA50
	DEV_CreateBlendState = 20,        // 140630A70
	DEV_CreateDepthStencilState = 21, // 14065BED0
	DEV_CreateRasterizerState = 22,   // 1406310F0
	DEV_CreateSamplerState = 23,      // 14065FE60, 1401AAB70
	DEV_CreateQuery = 24,             // 14062F700, 14068BC80
};

// ID3D11DeviceContext (ID3D11Asynchronous methods)
enum D3D11ContextQuerySlot : unsigned int
{
	CTX_Begin = 27,    // 14068BE20
	CTX_End = 28,      // 14067D210, 14068BE20
	CTX_GetData = 29,  // 14065BE70, 14067D210, 14062DFF0, 14068C260, 14068BE20
};

// IUnknown / ID3D11Asynchronous (ID3D11Query)
enum ComObjectStateSlot : unsigned int
{
	UNK_Release = 2,              // 14065FE60
	ASYNC_GetDataSize = 7,        // 14065BE70, 14067D210, 14062DFF0, 14068C260, 14068BE20
};
// ---- END states ----
