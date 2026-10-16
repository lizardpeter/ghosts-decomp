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

// ---- buffers ----
// IUnknown, first in every interface (Store: ID3D11Buffer::AddRef 140630487 `call [rax+8]`, Release 1406023BC
// `call [rax+0x10]`)
enum IUnknownSlot : unsigned int
{
	UNK_AddRef = 1,
	UNK_Release = 2,
};

// ID3D11Device (Store: CreateBuffer 140601685 `call [rax+0x18]` on dx.d3d11device)
enum D3D11DeviceBufferSlot : unsigned int
{
	DEV_CreateBuffer = 3,
};

// ID3D11DeviceContext (Store: Map 140602786 `call [rax+0x70]`, Unmap 140602846 `jmp [rax+0x78]`)
enum D3D11ContextBufferSlot : unsigned int
{
	CTX_Map = 14,
	CTX_Unmap = 15,
};

// ID3D11Buffer: ID3D11DeviceChild 3-6, ID3D11Resource 7-9, then GetDesc (Store: 140602815 `call [rax+0x50]`)
enum D3D11BufferSlot : unsigned int
{
	BUF_GetDesc = 10,
};
