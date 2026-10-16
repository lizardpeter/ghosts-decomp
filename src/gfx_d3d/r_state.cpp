// gfx_d3d/r_state.cpp (Store build)
//
// The renderer's Direct3D 11 state, from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store
// addresses. The servers' PDBs (iw6_ds_ps4, iw6_ds_xb3) have gfx_d3d/r_state.cpp, but their renderer back end
// is mostly stubbed out, so the Store build is the source here; names are unknown unless given.
//
// The back end caches what is bound to the immediate context (dx.immediateContext) in globals, so it only calls
// Direct3D when something changes.

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"

// Bound-shader cache (names unknown): the shader each stage last had set through the immediate context.
extern void *unk_14BAD2778;  // pixel shader
extern void *unk_14BAD2780;  // vertex shader
extern void *unk_14BAD2788;  // hull shader
extern void *unk_14BAD2790;  // domain shader
extern void *unk_14BAD04B0;  // input layout

// Store 14068D190 (name unknown): unbinds the domain shader and forgets the cached one
void sub_14068D190()
{
	if (dx.immediateContext)
		ComCall<void>(dx.immediateContext, CTX_DSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	unk_14BAD2790 = nullptr;
}

// Store 14068D1D0 (name unknown): the same for the hull shader
void sub_14068D1D0()
{
	if (dx.immediateContext)
		ComCall<void>(dx.immediateContext, CTX_HSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	unk_14BAD2788 = nullptr;
}

// Store 14068D210 (name unknown): the same for the pixel shader
void sub_14068D210()
{
	if (dx.immediateContext)
		ComCall<void>(dx.immediateContext, CTX_PSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	unk_14BAD2778 = nullptr;
}

// Store 14068D240 (name unknown): unbinds the input layout and forgets the cached one
void sub_14068D240()
{
	if (dx.immediateContext)
		ComCall<void>(dx.immediateContext, CTX_IASetInputLayout, (void *)nullptr);
	unk_14BAD04B0 = nullptr;
}

// Store 14068D270 (name unknown): the same for the vertex shader
void sub_14068D270()
{
	if (dx.immediateContext)
		ComCall<void>(dx.immediateContext, CTX_VSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	unk_14BAD2780 = nullptr;
}

static_assert(__builtin_offsetof(DxGlobals, d3d11device) == 0x08, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobals, immediateContext) == 0x10, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobals, dxgiFactory) == 0x20, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobals, d3d11FeatureLevel) == 0x38, "DxGlobals layout");
