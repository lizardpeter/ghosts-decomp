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

// ==== BEGIN states ====
// Pipeline state objects: the blend, depth-stencil, rasterizer and sampler states the renderer creates from its
// packed state bits, at start-up and per zone. Names are unknown unless given; the Xbox One server PDB
// (iw6_ds_xb3) has the rasterizer part as R_InitStateTables (gfx_d3d/r_init.cpp:2422) with an inline
// R_HW_CreateRasterizerState (gfx_d3d/r_setstate_d3d.h:562).

#include <iw6_static.h>

#include "gfx_d3d/r_state_d3d11.h"
#include "qcommon/dvar.h"

#ifndef IW6_SOURCE
#define IW6_SOURCE "gfx_d3d/r_state.cpp"
#endif

extern const dvar_t *r_polygonOffsetBias;
extern const dvar_t *r_polygonOffsetScale;
extern const dvar_t *r_polygonOffsetClamp;
extern const dvar_t *sm_polygonOffsetBias;
extern const dvar_t *sm_polygonOffsetScale;
extern const dvar_t *sm_polygonOffsetClamp;

// State-bit lookup tables (.rdata; names unknown)
IW6_STATIC const int unk_14089CFF0[16] IW6_AT("", "unk_14089CFF0")  // colour blend factor -> D3D11_BLEND
	IW6_INIT(= {1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0x10, 0x11, 0x12, 0x13, 0});
IW6_STATIC const int unk_14089D030[16] IW6_AT("", "unk_14089D030")  // alpha blend factor -> D3D11_BLEND
	IW6_INIT(= {1, 1, 2, 5, 6, 5, 6, 7, 8, 7, 8, 0x12, 0x13, 0x12, 0x13, 0});
IW6_STATIC const int unk_14089D070[6] IW6_AT("", "unk_14089D070")   // blend op -> D3D11_BLEND_OP, read with & 7
	IW6_INIT(= {1, 1, 2, 3, 4, 5});
IW6_STATIC const int unk_14089D088[4] IW6_AT("", "unk_14089D088")   // cull -> D3D11_CULL_MODE
	IW6_INIT(= {1, 1, 3, 2});
IW6_STATIC const int unk_1408A94B0[4] IW6_AT("", "unk_1408A94B0")   // depth test -> D3D11_COMPARISON_FUNC
	IW6_INIT(= {8, 5, 3, 7});
IW6_STATIC const int unk_1408A94C0[8] IW6_AT("", "unk_1408A94C0")   // stencil op -> D3D11_STENCIL_OP
	IW6_INIT(= {1, 2, 3, 4, 5, 6, 7, 8});
IW6_STATIC const int unk_1408A94E0[8] IW6_AT("", "unk_1408A94E0")   // stencil func -> D3D11_COMPARISON_FUNC
	IW6_INIT(= {1, 2, 3, 4, 5, 6, 7, 8});

// Sampler state bits per filter combination, built by 1406635E0 from the texture filter dvars
extern unsigned int unk_14B2DA0F0[32];

// APEX (NVIDIA GameWorks) module object and the sampler state created for it
extern void *unk_1430D5C48;
extern ID3D11SamplerState *unk_1430D5C28;

extern "C" int SetDllDirectoryA(const char *lpPathName);

// Store 1406321C0 (name unknown): one render target's blend description from its 32 state bits. With
// forceEnable, a target without blending gets blending enabled as ONE * src + ZERO * dest.
void sub_1406321C0(unsigned int blendBits, D3D11_RENDER_TARGET_BLEND_DESC *desc, bool forceEnable)
{
	if (forceEnable && !(blendBits & 0x700))
	{
		desc->BlendEnable = 1;
		desc->BlendOp = D3D11_BLEND_OP_ADD;
		desc->SrcBlend = D3D11_BLEND_ONE;
		desc->DestBlend = D3D11_BLEND_ZERO;
	}
	else
	{
		desc->BlendEnable = (blendBits & 0x700) != 0;
		desc->BlendOp = unk_14089D070[(blendBits >> 8) & 7];
		desc->SrcBlend = unk_14089CFF0[blendBits & 0xF];
		desc->DestBlend = unk_14089CFF0[(blendBits >> 4) & 0xF];
	}
	if (blendBits & 0x700000)
	{
		desc->DestBlendAlpha = unk_14089D030[(blendBits >> 16) & 0xF];
		desc->SrcBlendAlpha = unk_14089D030[(blendBits >> 12) & 0xF];
		desc->BlendOpAlpha = unk_14089D070[(blendBits >> 20) & 7];
	}
	else
	{
		desc->DestBlendAlpha = unk_14089D030[(blendBits >> 4) & 0xF];
		desc->SrcBlendAlpha = unk_14089D030[blendBits & 0xF];
		desc->BlendOpAlpha = unk_14089D070[(blendBits >> 8) & 7];
	}
	desc->RenderTargetWriteMask = (blendBits >> 24) & 0xF;
}

// Store 140630A70 (name unknown): a blend state for rtCount render targets. Independent blending is on when the
// targets' bits differ, and then a first target without blending is forced to ONE/ZERO if any target blends.
// Targets past rtCount get the defaults; more than 8 would write past the description (callers pass 1).
ID3D11BlendState *sub_140630A70(const unsigned int *blendBits, unsigned int rtCount)
{
	D3D11_BLEND_DESC desc;
	ID3D11BlendState *state;
	bool anyBlend = (blendBits[0] & 0x700) != 0;
	bool independent = false;
	unsigned int rtIndex;

	for (rtIndex = 1; rtIndex < rtCount; rtIndex++)
	{
		if (anyBlend || (blendBits[rtIndex] & 0x700))
			anyBlend = true;
		if (blendBits[rtIndex] != blendBits[0])
			independent = true;
	}
	desc.AlphaToCoverageEnable = 0;
	desc.IndependentBlendEnable = independent;
	sub_1406321C0(blendBits[0], &desc.RenderTarget[0], anyBlend && independent);
	rtIndex = 1;
	if (independent)
	{
		for (; rtIndex < rtCount; rtIndex++)
			sub_1406321C0(blendBits[rtIndex], &desc.RenderTarget[rtIndex], false);
	}
	for (; rtIndex < 8; rtIndex++)
	{
		desc.RenderTarget[rtIndex].BlendEnable = 0;
		desc.RenderTarget[rtIndex].SrcBlend = D3D11_BLEND_ONE;
		desc.RenderTarget[rtIndex].DestBlend = D3D11_BLEND_ZERO;
		desc.RenderTarget[rtIndex].BlendOp = D3D11_BLEND_OP_ADD;
		desc.RenderTarget[rtIndex].SrcBlendAlpha = D3D11_BLEND_ONE;
		desc.RenderTarget[rtIndex].DestBlendAlpha = D3D11_BLEND_ZERO;
		desc.RenderTarget[rtIndex].BlendOpAlpha = D3D11_BLEND_OP_ADD;
		desc.RenderTarget[rtIndex].RenderTargetWriteMask = 0;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateBlendState, (const D3D11_BLEND_DESC *)&desc, &state);
	return state;
}

// Store 140631250 (name unknown): creates a zone's blend states, one render target each, and registers the table
void sub_140631250(unsigned char zoneIndex, GfxZoneTableEntry *table, const unsigned int *blendBits,
                   unsigned int count)
{
	for (unsigned int index = 0; index < count; index++)
		table[index].blendState = sub_140630A70(&blendBits[index], 1);
	dx.blendStateTables[zoneIndex] = table;
	dx.blendStateCounts[zoneIndex] = count;
}

// Store 14065BED0 (name unknown): a depth-stencil state from 64 state bits
ID3D11DepthStencilState *sub_14065BED0(unsigned long long stateBits)
{
	D3D11_DEPTH_STENCIL_DESC desc;
	ID3D11DepthStencilState *state;

	desc.StencilReadMask = (unsigned char)(stateBits >> 32);
	desc.StencilWriteMask = (unsigned char)(stateBits >> 40);
	desc.DepthWriteMask = stateBits & 1;
	desc.DepthEnable = ~(stateBits >> 1) & 1;
	desc.DepthFunc = unk_1408A94B0[(stateBits >> 2) & 3];
	desc.StencilEnable = (stateBits & 0xC0) != 0;
	desc.FrontFace.StencilPassOp = unk_1408A94C0[(stateBits >> 8) & 7];
	desc.FrontFace.StencilFailOp = unk_1408A94C0[(stateBits >> 11) & 7];
	desc.FrontFace.StencilDepthFailOp = unk_1408A94C0[(stateBits >> 14) & 7];
	desc.BackFace.StencilPassOp = unk_1408A94C0[(stateBits >> 20) & 7];
	desc.BackFace.StencilFailOp = unk_1408A94C0[(stateBits >> 23) & 7];
	desc.BackFace.StencilDepthFailOp = unk_1408A94C0[(stateBits >> 26) & 7];
	desc.FrontFace.StencilFunc = unk_1408A94E0[(stateBits >> 17) & 7];
	desc.BackFace.StencilFunc = unk_1408A94E0[(stateBits >> 29) & 7];
	ComCall<long>(dx.d3d11device, DEV_CreateDepthStencilState, (const D3D11_DEPTH_STENCIL_DESC *)&desc, &state);
	return state;
}

// Store 1406314C0 (name unknown): creates a zone's depth-stencil states and registers the table
void sub_1406314C0(unsigned char zoneIndex, GfxZoneTableEntry *table, const unsigned long long *stateBits,
                   unsigned int count)
{
	for (unsigned int index = 0; index < count; index++)
		table[index].depthStencilState = sub_14065BED0(stateBits[index]);
	dx.depthStencilStateTables[zoneIndex] = table;
	dx.depthStencilStateCounts[zoneIndex] = count;
}

// gfx_d3d/r_setstate_d3d.h:562 (xb3 PDB), inlined. rasterBits: bit 5 solid (else wireframe), bits 3-4 cull;
// polygonOffset bits 4-5: 0..2 times the r_polygonOffset dvars, or 3 for the shadow maps' sm_polygonOffset dvars.
static ID3D11RasterizerState *R_HW_CreateRasterizerState(unsigned int rasterBits, unsigned int polygonOffset)
{
	D3D11_RASTERIZER_DESC desc = {};
	ID3D11RasterizerState *state;
	int bias;
	float scale;
	float clamp;

	if (polygonOffset == 0x30)
	{
		bias = sm_polygonOffsetBias->current.integer;
		scale = sm_polygonOffsetScale->current.value;
		clamp = sm_polygonOffsetClamp->current.value;
	}
	else
	{
		unsigned int count = polygonOffset >> 4;
		bias = count * r_polygonOffsetBias->current.integer;
		scale = (float)count * r_polygonOffsetScale->current.value;
		clamp = (float)count * r_polygonOffsetClamp->current.value;
	}
	desc.FrontCounterClockwise = 0;
	desc.DepthBias = -bias;
	desc.FillMode = (~(rasterBits >> 5) & 1) | D3D11_FILL_WIREFRAME;
	desc.CullMode = unk_14089D088[(rasterBits >> 3) & 3];
	desc.DepthBiasClamp = -clamp;
	desc.SlopeScaledDepthBias = -scale;
	desc.DepthClipEnable = 1;
	desc.ScissorEnable = 1;
	desc.MultisampleEnable = 0;
	desc.AntialiasedLineEnable = 0;
	ComCall<long>(dx.d3d11device, DEV_CreateRasterizerState, (const D3D11_RASTERIZER_DESC *)&desc, &state);
	return state;
}

// Store 1406310F0 (name unknown): the rasterizer states of the xb3 PDB's R_InitStateTables (gfx_d3d/r_init.cpp:2422):
// 4 cull modes x 4 polygon offsets x solid/wireframe. The Store build sets the default depth-stencil and blend
// tables in the caller (14062F700) instead.
void sub_1406310F0()
{
	for (unsigned char stateIndex = 0; stateIndex < 32; stateIndex++)
	{
		dx.rasterizerStates[stateIndex] =
			R_HW_CreateRasterizerState(((stateIndex & 3) << 3) | ((stateIndex & 0x10) * 2), (stateIndex & 0xC) << 2);
	}
}

// Store 140662850 (name unknown): a sampler description from sampler state bits. Bits 8-11 min filter (4 =
// anisotropic), 12-15 mip filter, 16-19 mag filter, 20-21/22-23/24-25 address U/V/W, 27 comparison, 0-7 anisotropy.
void sub_140662850(D3D11_SAMPLER_DESC *desc, unsigned int samplerBits)
{
	int filter;

	if ((samplerBits & 0xF00) == 0x400)
		filter = D3D11_FILTER_ANISOTROPIC;
	else
		filter = ((samplerBits & 0xF00) == 0x100 ? 0x10 : 0) | ((samplerBits & 0xF0000) == 0x10000) |
		         ((samplerBits & 0xF000) == 0x1000 ? 4 : 0);
	desc->Filter = ((samplerBits >> 20) & 0x80) | filter;
	desc->AddressU = (samplerBits >> 20) & 3;
	desc->AddressV = (samplerBits >> 22) & 3;
	desc->AddressW = (samplerBits >> 24) & 3;
	desc->MinLOD = 0;
	desc->MaxLOD = D3D11_FLOAT32_MAX;
	desc->MipLODBias = dx.mipBias;
	desc->BorderColor[0] = 0;
	desc->BorderColor[1] = 0;
	desc->BorderColor[2] = 0;
	desc->BorderColor[3] = 0;
	desc->MaxAnisotropy = (samplerBits & 0xFF) > 1 ? (samplerBits & 0xFF) : 1;
	desc->ComparisonFunc = D3D11_COMPARISON_GREATER;
}

// Store 14065FE60 (name unknown): (re)creates dx.samplerStates. Index bits 0-4 pick the filter (24 of 32 used),
// bits 5-7 clamp U/V/W instead of wrapping; index 24 alone is a black-border sampler, the rest stay NULL.
void sub_14065FE60()
{
	D3D11_SAMPLER_DESC desc;

	for (int samplerIndex = 0; samplerIndex < 256; samplerIndex++)
	{
		ID3D11SamplerState **state = &dx.samplerStates[samplerIndex];
		if (*state)
			ComCall<unsigned long>(*state, UNK_Release);
		*state = nullptr;
		if ((samplerIndex & 0x18) == 0x18)
		{
			if (samplerIndex < 0x19)
			{
				sub_140662850(&desc, unk_14B2DA0F0[1] | 0x1500000);
				desc.AddressU = D3D11_TEXTURE_ADDRESS_BORDER;
				desc.AddressV = D3D11_TEXTURE_ADDRESS_BORDER;
				desc.AddressW = D3D11_TEXTURE_ADDRESS_BORDER;
				desc.BorderColor[0] = 0;
				desc.BorderColor[1] = 0;
				desc.BorderColor[2] = 0;
				desc.BorderColor[3] = 0;
				ComCall<long>(dx.d3d11device, DEV_CreateSamplerState, (const D3D11_SAMPLER_DESC *)&desc,
				              &dx.samplerStates[samplerIndex]);
			}
		}
		else if ((samplerIndex & 0x1F) < 0x18)
		{
			unsigned int clampBits =
				(((((samplerIndex & 0x80) | 0x54) * 2 | (samplerIndex & 0x40)) * 2) | (samplerIndex & 0x20)) << 16;
			sub_140662850(&desc, clampBits | unk_14B2DA0F0[samplerIndex & 0x1F]);
			ComCall<long>(dx.d3d11device, DEV_CreateSamplerState, (const D3D11_SAMPLER_DESC *)&desc, state);
		}
	}
}

// Store 1401AAB70 (name unknown): APEX start-up on the device (its DLLs load from APEX\), then the sampler state it
// uses: trilinear, border/border/clamp, white border.
void sub_1401AAB70()
{
	SetDllDirectoryA("APEX");
	ComCall<void>(unk_1430D5C48, 26, dx.d3d11device, 3);
	SetDllDirectoryA(nullptr);
	if (!unk_1430D5C28)
	{
		D3D11_SAMPLER_DESC desc;
		desc.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
		desc.AddressU = D3D11_TEXTURE_ADDRESS_BORDER;
		desc.AddressV = D3D11_TEXTURE_ADDRESS_BORDER;
		desc.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
		desc.MipLODBias = 0;
		desc.MaxAnisotropy = 1;
		desc.ComparisonFunc = D3D11_COMPARISON_GREATER;
		desc.BorderColor[0] = 1.0f;
		desc.BorderColor[1] = 1.0f;
		desc.BorderColor[2] = 1.0f;
		desc.BorderColor[3] = 1.0f;
		desc.MinLOD = 0;
		desc.MaxLOD = D3D11_FLOAT32_MAX;
		ComCall<long>(dx.d3d11device, DEV_CreateSamplerState, (const D3D11_SAMPLER_DESC *)&desc, &unk_1430D5C28);
	}
}
// ==== END states ====

// ==== BEGIN per-frame ====
// The per-frame state cache (xb3 PDB gfx_d3d/r_state.cpp): what is bound to one context (GfxCmdBufState, the
// immediate context's or a worker's deferred one) and the draw calls. Every setter compares with the cache first.
// Names and order from the xb3 server, whose code for these is complete; the Store build's differences are noted.

#include "gfx_d3d/r_buffers.h"
#include "gfx_d3d/r_state.h"
#include "qcommon/qcommon.h"

extern "C" void *memset(void *dst, int c, unsigned long long n);

struct GfxSceneDef;
struct GfxViewParms;

// xb3 PDB: the output of R_DrawCall's caller (a worker's or the immediate command buffer); only the context is used
struct GfxDrawCallOutput
{
	ID3D11DeviceContext *device;
};

void R_BeginView(GfxCmdBufSourceState *source, const GfxSceneDef *sceneDef, const GfxViewParms *viewParms);
HRESULT R_CreateBufferInternal(const D3D11_BUFFER_DESC *pDesc, const D3D11_SUBRESOURCE_DATA *pInitialData,
                               ID3D11Buffer **ppBuffer);

// The cache's "nothing dirty" values: first > last
#define SAMPLER_DIRTY_NONE 16
#define TEXTURE_DIRTY_NONE 128

// Store 140663410 (xb3 PDB gfx_d3d/r_state.cpp:2527). stateBits are the pass's GfxStateBits::loadBits with the
// caller's changes; refStateBits->rasterizerState, depthStencilState[mode] and blendState index the state object
// tables built at load (gfx_d3d/r_state.cpp, `states` above). Bit 0 of stateBits[1] forces depth writes for the
// first three depth-stencil modes (the next three entries of the table, GFX_DEPTH_STENCIL_FIRST_FORCE_DEPTH); bits 8
// to 15 of stateBits[0] are the stencil reference.
void R_SetState(GfxCmdBufContext context, const unsigned int *const stateBits, const GfxStateBits *refStateBits)
{
	GfxCmdBufState *state = context.state;
	unsigned int blendBits = stateBits[2];
	unsigned int oldBlendBits = state->refStateBits[2];
	unsigned int changed1 = stateBits[1] ^ state->refStateBits[1];
	unsigned int changed0 = state->refStateBits[0] ^ stateBits[0];
	if (changed0 & 0x40)
		R_HW_SetGammaWriteEnable(state, stateBits[0]);
	if ((changed0 & 0x38) || (changed1 & 0x30))
	{
		ID3D11RasterizerState *rasterizerState = dx.rasterizerStates[refStateBits->rasterizerState & 0x1F];
		ComCall<void>(state->prim.device, CTX_RSSetState, rasterizerState);
		state->deviceState.rasterizerState = rasterizerState;
	}
	if ((changed1 & 0xFFFFFFCF) || (changed0 & 0xFF00) || state->depthStencilMode != context.source->depthStencilMode)
	{
		int mode;
		if (!(stateBits[1] & 1) || (int)context.source->depthStencilMode > 2)
			mode = context.source->depthStencilMode;
		else
			mode = context.source->depthStencilMode + GFX_DEPTH_STENCIL_MODE_FORCE_DEPTH_WRITE;
		state->depthStencilMode = (GfxDepthStencilMode)mode;
		ID3D11DepthStencilState *depthStencilState =
			dx.depthStencilStateTables[refStateBits->zone][refStateBits->depthStencilState[mode]].depthStencilState;
		if ((changed0 & 0xFF00) || depthStencilState != state->deviceState.depthStencilState)
		{
			ComCall<void>(state->prim.device, CTX_OMSetDepthStencilState, depthStencilState,
			              (unsigned int)((const unsigned char *)stateBits)[1]);
			state->deviceState.depthStencilState = depthStencilState;
		}
	}
	if ((blendBits ^ oldBlendBits) & 0xF7FF7FF)
	{
		ID3D11BlendState *blendState = dx.blendStateTables[refStateBits->zone][refStateBits->blendState].blendState;
		ComCall<void>(state->prim.device, CTX_OMSetBlendState, blendState,
		              (const float *)state->deviceState.blendFactor, state->deviceState.sampleMask);
		state->deviceState.blendState = blendState;
	}
	state->refStateBits[0] = stateBits[0];
	state->refStateBits[1] = stateBits[1];
	state->refStateBits[2] = stateBits[2];
}

// Store 140662A00 (xb3 PDB gfx_d3d/r_state.cpp:4506): unbinds the rasterizer, blend and depth-stencil states (the
// device defaults) and sets gamma writes from stateBits[0]
void R_SetCompleteState(GfxCmdBufState *state, const unsigned int *const stateBits)
{
	ComCall<void>(state->prim.device, CTX_RSSetState, (ID3D11RasterizerState *)nullptr);
	state->deviceState.rasterizerState = nullptr;
	ComCall<void>(state->prim.device, CTX_OMSetBlendState, (ID3D11BlendState *)nullptr,
	              (const float *)state->deviceState.blendFactor, state->deviceState.sampleMask);
	state->deviceState.blendState = nullptr;
	ComCall<void>(state->prim.device, CTX_OMSetDepthStencilState, (ID3D11DepthStencilState *)nullptr,
	              (unsigned int)((const unsigned char *)stateBits)[1]);
	state->deviceState.depthStencilState = nullptr;
	R_HW_SetGammaWriteEnable(state, stateBits[0]);
}

// The three stages' sampler and texture slots are flushed the same way: the dirty range [first, last] is bound in one
// call (slots in between that did not change are sent again) and the range is reset.
template <unsigned int SetSamplers>
static inline void R_FlushSamplers(GfxCmdBufState *state, const unsigned char *samplerState, int *first, int *last)
{
	unsigned int start = (unsigned int)*first;
	if ((int)start <= *last)
	{
		ID3D11SamplerState *samplers[16];
		ID3D11DeviceContext *device = state->prim.device;
		unsigned int count = *last - start + 1;
		for (unsigned int i = 0; i < count; i++)
			samplers[i] = dx.samplerStates[samplerState[start + i]];
		ComCall<void>(device, SetSamplers, start, count, (ID3D11SamplerState *const *)samplers);
		*first = SAMPLER_DIRTY_NONE;
		*last = -1;
	}
}

template <unsigned int SetShaderResources>
static inline void R_FlushTextures(GfxCmdBufState *state, const GfxTexture *const *textures, int *first, int *last)
{
	unsigned int start = (unsigned int)*first;
	if ((int)start <= *last)
	{
		ID3D11ShaderResourceView *views[128];
		ID3D11DeviceContext *device = state->prim.device;
		unsigned int count = *last - start + 1;
		for (unsigned int i = 0; i < count; i++)
		{
			const GfxTexture *texture = textures[start + i];
			views[i] = texture ? texture->shaderView : nullptr;
		}
		ComCall<void>(device, SetShaderResources, (unsigned long long)start, count,
		              (ID3D11ShaderResourceView *const *)views);
		*first = TEXTURE_DIRTY_NONE;
		*last = -1;
	}
}

// Store 140661B00 (xb3 PDB gfx_d3d/r_state.cpp:3034). The xb3 server only resets the texture ranges; the Store build
// binds them (VS, DS and PS shader resources). Hull shaders get no samplers or textures here.
void R_FlushTextureState(GfxCmdBufState *state)
{
	R_FlushSamplers<CTX_VSSetSamplers>(state, state->vertexSamplerState, &state->firstVertexSamplerDirty,
	                                   &state->lastVertexSamplerDirty);
	R_FlushSamplers<CTX_DSSetSamplers>(state, state->domainSamplerState, &state->firstDomainSamplerDirty,
	                                   &state->lastDomainSamplerDirty);
	R_FlushSamplers<CTX_PSSetSamplers>(state, state->pixelSamplerState, &state->firstPixelSamplerDirty,
	                                   &state->lastPixelSamplerDirty);
	R_FlushTextures<CTX_VSSetShaderResources>(state, state->vertexTexture, &state->firstVertexTextureDirty,
	                                          &state->lastVertexTextureDirty);
	R_FlushTextures<CTX_DSSetShaderResources>(state, state->domainTexture, &state->firstDomainTextureDirty,
	                                          &state->lastDomainTextureDirty);
	R_FlushTextures<CTX_PSSetShaderResources>(state, state->pixelTexture, &state->firstPixelTextureDirty,
	                                          &state->lastPixelTextureDirty);
}

// Store 140660EE0 (xb3 PDB gfx_d3d/r_state.cpp:3127): unbinds one domain shader texture right away
void R_ClearDomainTexture(GfxCmdBufState *state, unsigned int index)
{
	if (state->domainTexture[index])
	{
		state->domainTexture[index] = nullptr;
		ID3D11ShaderResourceView *view = nullptr;
		ComCall<void>(state->prim.device, CTX_DSSetShaderResources, index, 1u, &view);
	}
}

// R_ClearAll*Textures: every bound slot is cleared and marked dirty; R_FlushTextureState unbinds them
static inline void R_ClearAllTextures(const GfxTexture **textures, int *first, int *last)
{
	for (int index = 0; index < 128; index++)
	{
		if (textures[index])
		{
			textures[index] = nullptr;
			*first = index <= *first ? index : *first;
			*last = *last <= index ? index : *last;
		}
	}
}

// Store 140660B00 (xb3 PDB gfx_d3d/r_state.cpp)
void R_ClearAllVertexTextures(GfxCmdBufState *state)
{
	R_ClearAllTextures(state->vertexTexture, &state->firstVertexTextureDirty, &state->lastVertexTextureDirty);
}

// Store 140660270 (xb3 PDB gfx_d3d/r_state.cpp)
void R_ClearAllDomainTextures(GfxCmdBufState *state)
{
	R_ClearAllTextures(state->domainTexture, &state->firstDomainTextureDirty, &state->lastDomainTextureDirty);
}

// Store 140660650 (xb3 PDB gfx_d3d/r_state.cpp)
void R_ClearAllPixelTextures(GfxCmdBufState *state)
{
	R_ClearAllTextures(state->pixelTexture, &state->firstPixelTextureDirty, &state->lastPixelTextureDirty);
}

// Store 140663F00 (xb3 PDB gfx_d3d/r_state.cpp): unbinds an image from every texture slot it is bound to (before it
// becomes a render target), right away, slot by slot
void R_UnbindImage(GfxCmdBufState *state, const GfxImage *image)
{
	const GfxTexture *texture = &image->texture;
	for (unsigned int index = 0; index < 128; index++)
	{
		if (state->vertexTexture[index] == texture && state->vertexTexture[index])
		{
			state->vertexTexture[index] = nullptr;
			ID3D11ShaderResourceView *view = nullptr;
			ComCall<void>(state->prim.device, CTX_VSSetShaderResources, index, 1u, &view);
		}
	}
	for (unsigned int index = 0; index < 128; index++)
	{
		if (state->domainTexture[index] == texture && state->domainTexture[index])
		{
			state->domainTexture[index] = nullptr;
			ID3D11ShaderResourceView *view = nullptr;
			ComCall<void>(state->prim.device, CTX_DSSetShaderResources, index, 1u, &view);
		}
	}
	for (unsigned int index = 0; index < 128; index++)
	{
		if (state->pixelTexture[index] == texture && state->pixelTexture[index])
		{
			state->pixelTexture[index] = nullptr;
			ID3D11ShaderResourceView *view = nullptr;
			ComCall<void>(state->prim.device, CTX_PSSetShaderResources, index, 1u, &view);
		}
	}
	R_FlushTextureState(state);
}

// Store 140660A30 (xb3 PDB gfx_d3d/r_state.cpp)
void R_ClearAllStreamSources(GfxCmdBufPrimState *primState)
{
	R_SetStreams(primState, nullptr, 0, 0);
}

// Store 140662ED0 (xb3 PDB gfx_d3d/r_state.cpp:2039). primType is a D3D11_PRIMITIVE_TOPOLOGY.
void R_SetPrimType(GfxCmdBufPrimState *primState, unsigned int primType)
{
	if (primState->primType != primType)
	{
		primState->primType = primType;
		ComCall<void>(primState->device, CTX_IASetPrimitiveTopology, primType);
	}
}

// Indices per primitive for the topologies the game draws: line list, triangle list, 3-point patch list, 16-point
// patch list (others draw nothing)
static inline int R_IndexCountForPrims(unsigned int primType, int primCount)
{
	if (primType == 2)
		return primCount * 2;
	if (primType == 4 || primType == 0x23)
		return primCount * 3;
	if (primType == 0x30)
		return primCount * 16;
	return 0;
}

// Store 1406616D0 (xb3 PDB gfx_d3d/r_state.cpp:2108)
void R_DrawIndexedPrimitive(GfxCmdBufPrimState *primState, const GfxDrawPrimArgs *args)
{
	int indexCount = R_IndexCountForPrims(primState->primType, args->primCount);
	ComCall<void>(primState->device, CTX_DrawIndexed, (unsigned int)indexCount, (unsigned int)args->baseIndex,
	              args->vertIndexBase);
}

// Store 140661720 (xb3 PDB gfx_d3d/r_state.cpp:2279)
void R_DrawInstancedIndexedPrimitive(GfxCmdBufPrimState *primState, const GfxDrawPrimArgs *args,
                                     unsigned int instanceCount)
{
	int indexCount = R_IndexCountForPrims(primState->primType, args->primCount);
	ComCall<void>(primState->device, CTX_DrawIndexedInstanced, (unsigned int)indexCount, instanceCount,
	              (unsigned int)args->baseIndex, args->vertIndexBase, 0u);
}

// Store 140662CD0 (xb3 PDB gfx_d3d/r_state.cpp): a static mesh's index buffer and its vertex buffer as stream 0.
// `streamIndex` (xb3's third argument) is not used by the Store build.
void R_SetMeshStream(GfxCmdBufState *state, GfxMeshData *mesh, unsigned int streamIndex)
{
	ID3D11Buffer *indexBuffer = *(ID3D11Buffer **)((char *)mesh + 0x08);  // GfxMeshData::ib
	if (state->prim.indexBuffer != indexBuffer)
	{
		state->prim.indexBuffer = indexBuffer;
		ComCall<void>(state->prim.device, CTX_IASetIndexBuffer, indexBuffer, (unsigned int)DXGI_FORMAT_R16_UINT_VALUE, 0u);
	}
	// GfxMeshData::vb.buffer (the Store build's GfxVertexBufferState is 0x30 bytes) and ::vertSize
	R_SetStreams(&state->prim, *(ID3D11Buffer **)((char *)mesh + 0x20), 0, *(unsigned int *)((char *)mesh + 0x48));
}

// Store 140663D90 (xb3 PDB gfx_d3d/r_state.cpp:1196): unbinds the index buffer, the vertex streams and every texture
void R_ShutdownCmdBufState(GfxCmdBufState *state)
{
	if (state->prim.indexBuffer)
	{
		state->prim.indexBuffer = nullptr;
		ComCall<void>(state->prim.device, CTX_IASetIndexBuffer, (ID3D11Buffer *)nullptr,
		              (unsigned int)DXGI_FORMAT_R16_UINT_VALUE, 0u);
	}
	R_ClearAllStreamSources(&state->prim);
	R_ClearAllVertexTextures(state);
	R_ClearAllDomainTextures(state);
	R_ClearAllPixelTextures(state);
	R_FlushTextureState(state);
}

// Store 1406600C0 (xb3 PDB gfx_d3d/r_state.cpp): the viewport's depth range for the scene, the view model (the gun,
// drawn in front: with reversed depth it gets 0.984..1), everything at the near or far plane, or the full range, and
// sets the viewport again
void R_ChangeDepthRange(GfxCmdBufState *state, GfxDepthRangeType depthRangeType)
{
	state->depthRangeType = depthRangeType;
	float minDepth;
	float maxDepth;
	switch (depthRangeType)
	{
	case GFX_DEPTH_RANGE_FULL:
		minDepth = 0.0f;
		maxDepth = 1.0f;
		break;
	case GFX_DEPTH_RANGE_SCENE:
		maxDepth = 0.984375f;
		minDepth = 0.0f;
		break;
	case GFX_DEPTH_RANGE_VIEWMODEL:
		minDepth = 0.984375f;
		maxDepth = 1.0f;
		break;
	case GFX_DEPTH_RANGE_FORCE_NEAR:
		minDepth = 1.0f;
		maxDepth = 1.0f;
		break;
	case GFX_DEPTH_RANGE_FORCE_FAR:
		minDepth = 0.0f;
		maxDepth = 0.0f;
		break;
	default:
		minDepth = 0.0f;
		maxDepth = 1.0f;
		break;
	}
	state->depthRangeNear = maxDepth;
	state->depthRangeFar = minDepth;
	D3D11_VIEWPORT viewport;
	viewport.TopLeftX = (float)state->viewport.x;
	viewport.TopLeftY = (float)state->viewport.y;
	viewport.Width = (float)state->viewport.width;
	viewport.Height = (float)state->viewport.height;
	viewport.MinDepth = minDepth;
	viewport.MaxDepth = maxDepth;
	ComCall<void>(state->prim.device, CTX_RSSetViewports, 1u, (const D3D11_VIEWPORT *)&viewport);
}

// The full-screen scissor rectangle (8192 x 8192), set when scissoring is "off": the rasterizer states all have
// ScissorEnable on.
static inline void R_HW_DisableScissorInternal(GfxCmdBufState *state)
{
	if (state->scissorX != 0 || state->scissorY != 0 || state->scissorW != 0x2000 || state->scissorH != 0x2000)
	{
		D3D11_RECT rect;
		rect.left = 0;
		rect.top = 0;
		rect.right = 0x2000;
		rect.bottom = 0x2000;
		ComCall<void>(state->prim.device, CTX_RSSetScissorRects, 1u, (const D3D11_RECT *)&rect);
		state->scissorW = 0x2000;
		state->scissorX = 0;
		state->scissorY = 0;
		state->scissorH = 0x2000;
	}
}

// Store 140662780 (xb3 PDB gfx_d3d/r_state.cpp: R_HW_DisableScissor2D)
void R_HW_DisableScissor2D(GfxCmdBufState *state)
{
	R_HW_DisableScissorInternal(state);
}

// Store 140662700 (name unknown): the same code as R_HW_DisableScissor2D, not folded with it
void sub_140662700(GfxCmdBufState *state)
{
	R_HW_DisableScissorInternal(state);
}

// Store 140662940 (xb3 PDB gfx_d3d/r_state.cpp)
void R_HW_SetScissor(GfxCmdBufState *state, const GfxViewport *scissor)
{
	if (state->scissorX != scissor->x || state->scissorY != scissor->y || state->scissorW != scissor->width ||
	    state->scissorH != scissor->height)
	{
		D3D11_RECT rect;
		rect.left = scissor->x;
		rect.top = scissor->y;
		rect.right = scissor->x + scissor->width;
		rect.bottom = scissor->height + scissor->y;
		ComCall<void>(state->prim.device, CTX_RSSetScissorRects, 1u, (const D3D11_RECT *)&rect);
		state->scissorX = scissor->x;
		state->scissorY = scissor->y;
		state->scissorW = scissor->width;
		state->scissorH = scissor->height;
	}
}

// Store 140663BE0 (xb3 PDB gfx_d3d/r_state.cpp; R_ForceSetViewportAndScissorSeparate is inlined)
void R_SetViewportAndScissorSeparate(GfxCmdBufState *state, const GfxViewport *viewport, const GfxViewport *scissor)
{
	if (viewport->x != state->viewport.x || viewport->y != state->viewport.y ||
	    viewport->width != state->viewport.width || viewport->height != state->viewport.height ||
	    scissor->x != state->scissorX || scissor->y != state->scissorY || scissor->width != state->scissorW ||
	    scissor->height != state->scissorH)
	{
		state->viewport = *viewport;
		D3D11_VIEWPORT d3dViewport;
		d3dViewport.TopLeftX = (float)viewport->x;
		d3dViewport.TopLeftY = (float)viewport->y;
		d3dViewport.Width = (float)viewport->width;
		d3dViewport.Height = (float)viewport->height;
		d3dViewport.MinDepth = state->depthRangeFar;
		d3dViewport.MaxDepth = state->depthRangeNear;
		ComCall<void>(state->prim.device, CTX_RSSetViewports, 1u, (const D3D11_VIEWPORT *)&d3dViewport);
		R_HW_SetScissor(state, scissor);
	}
}

// Store 140660F20 (xb3 PDB gfx_d3d/r_state.cpp:R_ClearScreenInternal): clears the bound colour target
// (whichToClear bit 2) and the depth and stencil (bits 0 and 1: D3D11_CLEAR_DEPTH, D3D11_CLEAR_STENCIL). The views
// come from OMGetRenderTargets, which adds a reference to each. `viewport` only selects between two copies of the
// same code.
void R_ClearScreenInternal(GfxCmdBufState *state, unsigned char whichToClear, const float *const color, float depth,
                           unsigned char stencil, const GfxViewport *viewport)
{
	ID3D11DeviceContext *device = state->prim.device;
	ID3D11RenderTargetView *colorView;
	ID3D11DepthStencilView *depthView;
	ComCall<void>(device, CTX_OMGetRenderTargets, 1u, &colorView, &depthView);
	if ((whichToClear & 4) && colorView)
		ComCall<void>(device, CTX_ClearRenderTargetView, colorView, color);
	if ((whichToClear & 3) && depthView)
		ComCall<void>(device, CTX_ClearDepthStencilView, depthView, (unsigned int)(whichToClear & 3), depth, stencil);
	if (colorView)
		ComCall<unsigned long>(colorView, UNK_Release);
	if (depthView)
		ComCall<unsigned long>(depthView, UNK_Release);
}

// Store 140663020 (xb3 PDB gfx_d3d/r_state.cpp:3986). The Store build picks the target's multisampled surfaces when
// the source state is multisampled and the target has a multisampled colour view, and inlines R_HW_SetRenderTarget.
void R_SetRenderTarget(GfxCmdBufContext context, GfxRenderTargetId newTargetId)
{
	GfxCmdBufState *state = context.state;
	if (newTargetId == state->renderTargetId)
		return;
	if (state->refStateBits[0] & 0x40)
	{
		state->refStateBits[0] &= ~0x40u;
		R_HW_SetGammaWriteEnable(state, 0);
	}
	GfxCmdBufSourceState *source = context.source;
	unsigned int msaa = 0;
	if (source->multiSampled)
		msaa = gfxRenderTargets[newTargetId].imageAndSurfaces[1].surface.color != nullptr;
	state->msaaTarget = (bool)msaa;
	if (gfxRenderTargets[newTargetId].imageAndSurfaces[msaa].image)
		R_UnbindImage(state, gfxRenderTargets[newTargetId].imageAndSurfaces[msaa].image);
	R_HW_SetRenderTarget(state, newTargetId);
	state->renderTargetId = newTargetId;
	state->renderTargetSuiteId = R_RENDERTARGET_SUITE_NONE_STORE;
	source->viewMode = 0;  // VIEW_MODE_NONE
	source->flags |= GFX_SOURCE_VIEWPORT_IS_DIRTY;
}

// Store 140663210 (xb3 PDB gfx_d3d/r_state.cpp:4100): binds a suite's two colour targets together, with the depth
// view of the last one that has one. Gamma writes are off with a suite.
void R_SetRenderTargetSuite(GfxCmdBufContext context, GfxRenderTargetSuiteId suiteId)
{
	GfxCmdBufSourceState *source = context.source;
	GfxCmdBufState *state = context.state;
	const int *targets = source->input.renderTargetSuites[suiteId];
	if (state->renderTargetSuiteId == suiteId)
		return;
	if (state->refStateBits[0] & 0x40)
	{
		state->refStateBits[0] &= ~0x40u;
		R_HW_SetGammaWriteEnable(state, 0);
	}
	state->msaaTarget = source->multiSampled
	                        ? gfxRenderTargets[targets[0]].imageAndSurfaces[1].surface.color != nullptr
	                        : false;
	unsigned int msaa = state->msaaTarget;
	for (int i = 0; i < 2; i++)
	{
		if (targets[i] != R_RENDERTARGET_NONE_STORE && gfxRenderTargets[targets[i]].imageAndSurfaces[msaa].image)
			R_UnbindImage(state, gfxRenderTargets[targets[i]].imageAndSurfaces[msaa].image);
	}
	msaa = state->msaaTarget;
	ID3D11DepthStencilView *depthStencil = nullptr;
	ID3D11RenderTargetView *colors[2];
	state->deviceState.srgbRenderTarget = false;
	unsigned int count;
	state->renderTargetSuite[0] = targets[0];
	if (targets[0] == R_RENDERTARGET_NONE_STORE)
		colors[0] = nullptr;
	else
	{
		const GfxRenderTargetSurface *surface = &gfxRenderTargets[targets[0]].imageAndSurfaces[msaa].surface;
		colors[0] = surface->color;
		if (surface->depthStencil)
			depthStencil = surface->depthStencil;
	}
	state->renderTargetSuite[1] = targets[1];
	if (targets[1] == R_RENDERTARGET_NONE_STORE)
	{
		colors[1] = nullptr;
		count = 1;
	}
	else
	{
		count = 2;
		const GfxRenderTargetSurface *surface = &gfxRenderTargets[targets[1]].imageAndSurfaces[msaa].surface;
		colors[1] = surface->color;
		if (surface->depthStencil)
			depthStencil = surface->depthStencil;
	}
	ComCall<void>(state->prim.device, CTX_OMSetRenderTargets, count, (ID3D11RenderTargetView *const *)colors,
	              depthStencil);
	state->renderTargetId = R_RENDERTARGET_NONE_STORE;
	state->renderTargetSuiteId = suiteId;
	source->viewMode = 0;  // VIEW_MODE_NONE
	source->flags |= GFX_SOURCE_VIEWPORT_IS_DIRTY;
}

// Store 140661470 (xb3 PDB gfx_d3d/r_state.cpp:4610): runs one draw callback on a fresh state for `output`'s context
// (the immediate one is locked meanwhile), then unbinds everything the callback left bound. The constant caches
// start invalid (all ones).
void R_DrawCall(void (*callback)(const void *, GfxCmdBufContext), const void *userData, GfxCmdBufSourceState *source,
                const GfxSceneDef *sceneDef, const GfxViewParms *viewParms, GfxDrawCallOutput *output)
{
	GfxCmdBufState state;
	R_BeginView(source, sceneDef, viewParms);
	state.prim.device = output->device;
	if (state.prim.device == dx.immediateContext)
		R_LockImmediateContext();
	R_InitCmdBufState(&state);
	memset(state.perPrimConstantState, 0xFF, sizeof(state.perPrimConstantState));
	memset(state.perObjectConstantState, 0xFF, sizeof(state.perObjectConstantState));
	memset(state.stableConstantState, 0xFF, sizeof(state.stableConstantState));
	GfxCmdBufContext context;
	context.source = source;
	context.state = &state;
	callback(userData, context);
	R_ShutdownCmdBufState(&state);
	if (state.prim.device == dx.immediateContext)
		R_UnlockImmediateContext();
}

// Store 14065FDD0 (name unknown; the xb3 server has no code for it): creates dx.reactiveTurbulenceEffectorBuffer
// (0x300 bytes of zeros, dynamic) and binds it as pixel shader constant buffer 10
void sub_14065FDD0(GfxCmdBufState *state)
{
	ID3D11DeviceContext *device = state->prim.device;
	unsigned char zeros[0x300];
	memset(zeros, 0, sizeof(zeros));
	D3D11_SUBRESOURCE_DATA initialData;
	initialData.pSysMem = zeros;
	initialData.SysMemPitch = 0x300;
	initialData.SysMemSlicePitch = 0;
	D3D11_BUFFER_DESC desc;
	desc.ByteWidth = 0x300;
	desc.Usage = (D3D11_USAGE)D3D11_USAGE_DYNAMIC;
	desc.BindFlags = 4;           // D3D11_BIND_CONSTANT_BUFFER
	desc.CPUAccessFlags = 0x10000;  // D3D11_CPU_ACCESS_WRITE
	desc.MiscFlags = 0;
	// StructureByteStride is left unset (stack garbage in the original too; ignored for a constant buffer)
	R_CreateBufferInternal(&desc, &initialData, &dx.reactiveTurbulenceEffectorBuffer);
	ComCall<void>(device, CTX_PSSetConstantBuffers, 10u, 1u, (ID3D11Buffer *const *)&dx.reactiveTurbulenceEffectorBuffer);
}
// R_Set{Vertex,Domain,Pixel}{Texture,Sampler} only change the cache and widen the stage's dirty range; the next
// R_FlushTextureState binds it.
static inline void R_MarkDirty(int *first, int *last, unsigned int index)
{
	*first = (int)index <= *first ? (int)index : *first;
	*last = *last <= (int)index ? (int)index : *last;
}

// Store 140663BA0 (xb3 PDB gfx_d3d/r_state.cpp)
void R_SetVertexTexture(GfxCmdBufState *state, unsigned int index, const GfxImage *image)
{
	if (state->vertexTexture[index] != &image->texture)
	{
		state->vertexTexture[index] = &image->texture;
		R_MarkDirty(&state->firstVertexTextureDirty, &state->lastVertexTextureDirty, index);
	}
}

// Store 140662AD0 (xb3 PDB gfx_d3d/r_state.cpp)
void R_SetDomainTexture(GfxCmdBufState *state, unsigned int index, const GfxImage *image)
{
	if (state->domainTexture[index] != &image->texture)
	{
		state->domainTexture[index] = &image->texture;
		R_MarkDirty(&state->firstDomainTextureDirty, &state->lastDomainTextureDirty, index);
	}
}

// Store 140662E80 (xb3 PDB gfx_d3d/r_state.cpp:3277). An image without a shader view (not loaded) is cached as
// NULL, so it compares different again on every set and is marked dirty each time.
void R_SetPixelTexture(GfxCmdBufState *state, unsigned int index, const GfxImage *image)
{
	if (state->pixelTexture[index] != &image->texture)
	{
		state->pixelTexture[index] = &image->texture;
		if (!image->texture.shaderView)
			state->pixelTexture[index] = nullptr;
		R_MarkDirty(&state->firstPixelTextureDirty, &state->lastPixelTextureDirty, index);
	}
}

// Store 140663B60 (xb3 PDB gfx_d3d/r_state.cpp)
void R_SetVertexSampler(GfxCmdBufState *state, unsigned int index, unsigned char samplerState)
{
	if (state->vertexSamplerState[index] != samplerState)
	{
		state->vertexSamplerState[index] = samplerState;
		R_MarkDirty(&state->firstVertexSamplerDirty, &state->lastVertexSamplerDirty, index);
	}
}

// Store 140662A90 (xb3 PDB gfx_d3d/r_state.cpp)
void R_SetDomainSampler(GfxCmdBufState *state, unsigned int index, unsigned char samplerState)
{
	if (state->domainSamplerState[index] != samplerState)
	{
		state->domainSamplerState[index] = samplerState;
		R_MarkDirty(&state->firstDomainSamplerDirty, &state->lastDomainSamplerDirty, index);
	}
}

// Store 140662E40 (xb3 PDB gfx_d3d/r_state.cpp)
void R_SetPixelSampler(GfxCmdBufState *state, unsigned int index, unsigned char samplerState)
{
	if (state->pixelSamplerState[index] != samplerState)
	{
		state->pixelSamplerState[index] = samplerState;
		R_MarkDirty(&state->firstPixelSamplerDirty, &state->lastPixelSamplerDirty, index);
	}
}

// Store 140662610 (xb3 MAP R_GetTextureFromCode, r_state.obj): one of the frame's code textures (shadow maps, the
// resolved scene, ...) and its sampler state
const GfxImage *R_GetTextureFromCode(GfxCmdBufSourceState *source, unsigned int codeTexture, unsigned char *samplerState)
{
	*samplerState = source->input.codeImageSamplerStates[codeTexture];
	return source->input.codeImages[codeTexture];
}

extern const char *unk_14A37D2D8[];  // the code textures' names, for the error below

// Store 140663EE0 (xb3 MAP R_TextureFromCodeError, r_state.obj): a material asks for a code texture the frame has not
// set
void R_TextureFromCodeError(GfxCmdBufSourceState *source, unsigned int codeTexture)
{
	Com_Error(ERR_DROP, "Tried to use '%s' when it isn't valid\n", unk_14A37D2D8[codeTexture]);
}
// GfxViewportBehavior (xb3 PDB): GFX_USE_VIEWPORT_FOR_VIEW = 0, GFX_USE_VIEWPORT_FULL = 1
#define GFX_USE_VIEWPORT_FULL 1
#define VIEW_MODE_2D 2

// Store 140662630 (xb3 PDB gfx_d3d/r_state.cpp:3712): the whole render target or the scene viewport, shrunk about
// its centre by g_drawConsts.scaleViewport except for 2D
void R_GetViewport(const GfxCmdBufSourceState *source, GfxViewport *viewport)
{
	if (source->viewportBehavior == GFX_USE_VIEWPORT_FULL)
	{
		viewport->x = 0;
		viewport->y = 0;
		viewport->width = source->renderTargetWidth;
		viewport->height = source->renderTargetHeight;
	}
	else
	{
		*viewport = source->sceneViewport;
	}
	if (source->viewMode != VIEW_MODE_2D && g_drawConsts.scaleViewport != 1.0f)
	{
		viewport->x += (int)((1.0f - g_drawConsts.scaleViewport) * (float)viewport->width * 0.5f);
		viewport->y += (int)((1.0f - g_drawConsts.scaleViewport) * (float)viewport->height * 0.5f);
		int width = (int)((float)viewport->width * g_drawConsts.scaleViewport);
		if (width < 2)
			width = 1;
		viewport->width = width;
		int height = (int)((float)viewport->height * g_drawConsts.scaleViewport);
		if (height < 2)
			height = 1;
		viewport->height = height;
	}
}

// The code constants R_UpdateViewport writes (indices into GfxCmdBufInput::consts, Store numbering)
#define CONST_RENDER_TARGET_SIZE 0x60
#define CONST_CLIP_SPACE_LOOKUP_SCALE 0x104
#define CONST_CLIP_SPACE_LOOKUP_OFFSET 0x105

// Store 140664010 (xb3 PDB gfx_d3d/r_state.cpp): the viewport is now set: clears the dirty flag and updates the code
// constants that depend on it (render target size and its reciprocal; the scale and offset from clip space to the
// viewport's texture coordinates), bumping their versions so the shader arguments are uploaded again
void R_UpdateViewport(GfxCmdBufSourceState *source, const GfxViewport *viewport)
{
	source->flags &= ~GFX_SOURCE_VIEWPORT_IS_DIRTY;
	int width = viewport->width;
	int height = viewport->height;
	int y = viewport->y;
	int x = viewport->x;
	float *size = source->input.consts[CONST_RENDER_TARGET_SIZE];
	size[0] = (float)source->renderTargetWidth;
	size[1] = (float)source->renderTargetHeight;
	float invWidth = 1.0f / (float)source->renderTargetWidth;
	float invHeight = 1.0f / (float)source->renderTargetHeight;
	size[2] = invWidth;
	size[3] = invHeight;
	source->constVersions[CONST_RENDER_TARGET_SIZE]++;
	float *scale = source->input.consts[CONST_CLIP_SPACE_LOOKUP_SCALE];
	float *offset = source->input.consts[CONST_CLIP_SPACE_LOOKUP_OFFSET];
	scale[2] = 0.0f;
	scale[3] = 1.0f;
	float halfHeight = (float)height * invHeight * 0.5f;
	float halfWidth = (float)width * invWidth * 0.5f;
	scale[0] = halfWidth;
	scale[1] = -halfHeight;
	source->constVersions[CONST_CLIP_SPACE_LOOKUP_SCALE]++;
	offset[1] = (float)y * invHeight + halfHeight;
	offset[2] = 0.0f;
	offset[3] = 0.0f;
	offset[0] = (float)x * invWidth + halfWidth;
	source->constVersions[CONST_CLIP_SPACE_LOOKUP_OFFSET]++;
}
// ==== END per-frame ====
