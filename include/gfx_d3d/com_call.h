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
