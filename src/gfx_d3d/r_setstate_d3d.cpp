// gfx_d3d/r_setstate_d3d.cpp (Store build)
//
// The device state the back end sets outside the material state bits: gamma (sRGB) writes and the default blend
// factor and sample mask. Names and order from the Xbox One server PDB (iw6_ds_xb3: gfx_d3d/r_setstate_d3d.cpp),
// tagged with Store addresses. R_FinishGpuFence, also from this file, is in gfx_d3d/rb_query.cpp with the other
// fences.

#include "gfx_d3d/r_state.h"

// Store 14065C110 (xb3 PDB gfx_d3d/r_setstate_d3d.cpp:108): blend factor 1,1,1,1, every sample, nothing bound
void R_InitializeDefaultDeviceStates(GfxCmdBufState *state)
{
	state->deviceState.blendFactor[0] = 1.0f;
	state->deviceState.blendFactor[1] = 1.0f;
	state->deviceState.blendFactor[2] = 1.0f;
	state->deviceState.blendFactor[3] = 1.0f;
	state->deviceState.sampleMask = 0xFFFFFFFF;
	state->deviceState.rasterizerState = nullptr;
	state->deviceState.blendState = nullptr;
	state->deviceState.depthStencilState = nullptr;
}

// Store 14065C000 (xb3 PDB gfx_d3d/r_setstate_d3d.cpp:121). Gamma writes are state bit 6 (GFXS0_GAMMAWRITE). D3D11
// has no gamma-write render state, so turning it on or off rebinds the target through its sRGB or linear colour
// view; with a suite (several targets) bound it is always off.
void R_HW_SetGammaWriteEnable(GfxCmdBufState *state, unsigned int stateBits0)
{
	if (state->renderTargetSuiteId != R_RENDERTARGET_SUITE_NONE_STORE)
	{
		state->deviceState.srgbWrite = false;
		return;
	}
	bool wasEnabled = state->deviceState.srgbWrite;
	bool enable = (stateBits0 >> 6) & 1;
	state->deviceState.srgbWrite = enable;
	if (wasEnabled != enable)
		R_HW_SetRenderTarget(state, state->renderTargetId);
}
