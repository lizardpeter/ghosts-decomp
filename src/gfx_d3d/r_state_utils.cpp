// gfx_d3d/r_state_utils.cpp (Store build)
//
// Setting up a command buffer state for a context. Names from the Xbox One server PDB (iw6_ds_xb3:
// gfx_d3d/r_state_utils.cpp), tagged with Store addresses.

#include "gfx_d3d/r_state.h"

extern "C" void *memset(void *dst, int c, unsigned long long n);

void sub_1401ABDC0(GfxCmdBufState *state);  // binds hull shader constant buffer 5 (middleware, near the APEX code)

// Store 140664940 (xb3 PDB gfx_d3d/r_state_utils.cpp): clears the cache for prim.device, then puts the context in a
// known state to match it: default rasterizer/blend/depth states, triangle lists, no shaders, every sampler slot
// dx.samplerStates[1], and the static model constant buffers in vertex shader slots 6 and 7. The cached pixel
// shader, input layout and streams are set to values no real one has (0xFFFFFFFF, -1), so the first set always
// reaches the context; the other shaders are cached as NULL, which is what was just bound.
void R_InitCmdBufState(GfxCmdBufState *state)
{
	ID3D11DeviceContext *device = state->prim.device;
	memset(state, 0, sizeof(*state));
	R_InitializeDefaultDeviceStates(state);
	state->prim.device = device;
	state->depthStencilMode = GFX_DEPTH_STENCIL_MODE_DEFAULT;
	state->msaaTarget = false;
	state->refStateBits[0] = 0;
	state->refStateBits[1] = 0;
	state->depthRangeType = GFX_DEPTH_RANGE_FULL;
	state->depthRangeNear = 1.0f;
	state->depthRangeFar = 0.0f;
	state->renderTargetId = R_RENDERTARGET_NONE_STORE;
	state->renderTargetSuiteId = R_RENDERTARGET_SUITE_NONE_STORE;
	R_SetCompleteState(state, state->refStateBits);
	R_SetPrimType(&state->prim, 4);  // D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST
	ComCall<void>(device, CTX_VSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	ComCall<void>(device, CTX_HSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	ComCall<void>(device, CTX_DSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);
	ComCall<void>(device, CTX_PSSetShader, (void *)nullptr, (void *const *)nullptr, 0u);

	ID3D11SamplerState *samplers[16];
	for (int i = 0; i < 16; i++)
		state->vertexSamplerState[i] = 1;
	for (int i = 0; i < 16; i++)
		samplers[i] = dx.samplerStates[1];
	ComCall<void>(device, CTX_VSSetSamplers, 0u, 16u, (ID3D11SamplerState *const *)samplers);
	for (int i = 0; i < 16; i++)
		state->domainSamplerState[i] = 1;
	for (int i = 0; i < 16; i++)
		samplers[i] = dx.samplerStates[1];
	ComCall<void>(device, CTX_DSSetSamplers, 0u, 16u, (ID3D11SamplerState *const *)samplers);
	for (int i = 0; i < 16; i++)
		state->pixelSamplerState[i] = 1;
	for (int i = 0; i < 16; i++)
		samplers[i] = dx.samplerStates[1];
	ComCall<void>(device, CTX_PSSetSamplers, 0u, 16u, (ID3D11SamplerState *const *)samplers);

	state->firstVertexSamplerDirty = 16;
	state->pixelShader = (const MaterialPixelShader *)(unsigned long long)0xFFFFFFFFu;
	state->lastVertexSamplerDirty = -1;
	state->firstDomainSamplerDirty = 16;
	state->lastDomainSamplerDirty = -1;
	state->firstPixelSamplerDirty = 16;
	state->lastPixelSamplerDirty = -1;
	state->firstVertexTextureDirty = 128;
	state->lastVertexTextureDirty = -1;
	state->firstDomainTextureDirty = 128;
	state->lastDomainTextureDirty = -1;
	state->firstPixelTextureDirty = 128;
	state->lastPixelTextureDirty = -1;
	state->prim.vertexDecl = (ID3D11InputLayout *)-1ll;
	state->prim.streamBuffers[0] = (ID3D11Buffer *)-1ll;
	state->prim.streamBuffers[1] = (ID3D11Buffer *)-1ll;
	state->prim.streamBuffers[2] = (ID3D11Buffer *)-1ll;
	state->scissorW = 0x2000;
	state->scissorH = 0x2000;
	sub_1401ABDC0(state);
	ComCall<void>(device, CTX_VSSetConstantBuffers, 6u, 1u, (ID3D11Buffer *const *)&dx.smodelWorldMatrixConstantBuffer);
	ComCall<void>(device, CTX_VSSetConstantBuffers, 7u, 1u,
	              (ID3D11Buffer *const *)&dx.smodelLightingOrAmbientConstantBuffer);
}
