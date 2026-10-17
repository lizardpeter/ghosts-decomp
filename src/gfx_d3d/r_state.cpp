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
	dxs.blendStateTables[zoneIndex] = table;
	dxs.blendStateCounts[zoneIndex] = count;
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
	dxs.depthStencilStateTables[zoneIndex] = table;
	dxs.depthStencilStateCounts[zoneIndex] = count;
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
		dxs.rasterizerStates[stateIndex] =
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
	desc->MipLODBias = dxs.mipBias;
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
		ID3D11SamplerState **state = &dxs.samplerStates[samplerIndex];
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
				              &dxs.samplerStates[samplerIndex]);
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
