// gfx_d3d/r_state_d3d11.h: what the state, shader, input-layout and query code needs from Direct3D 11 and from
// DxGlobals (Store build).
//
// The D3D11 descriptions are declared by hand (the reconstruction is built without the Windows SDK) with the
// public API's layout; enums are plain ints. Sizes and the offsets the Store build writes are asserted below.
//
// DxGlobalsStates continues r_dx.h's DxGlobals at the Store build's offsets. The Store build's DxGlobals is the
// Xbox One server PDB's (iw6_ds_xb3) with 8 more bytes somewhere in 0x58..0x430 (constantBufferTables, the depth-
// stencil and blend tables, rasterizerStates, samplerStates, immediateContextMutex, fencePool and nextFence all sit
// 8 bytes later), and with the swap fence moved behind flushGpuFenceIssued (with a bool after it), which puts the
// filter fields and mipBias 0x18 bytes later than in the server.
#pragma once

#include "gfx_d3d/r_dx.h"

struct ID3D11BlendState;
struct ID3D11DepthStencilState;
struct ID3D11RasterizerState;
struct ID3D11SamplerState;
struct ID3D11Buffer;
struct ID3D11Query;
struct ID3D11InputLayout;
struct ID3D11VertexShader;
struct ID3D11PixelShader;
struct ID3D11HullShader;
struct ID3D11DomainShader;
struct ID3D11ComputeShader;
struct D3D11_SUBRESOURCE_DATA;

// ---- D3D11 descriptions -------------------------------------------------------------------------------------------

struct D3D11_RENDER_TARGET_BLEND_DESC
{
	int BlendEnable;
	int SrcBlend;
	int DestBlend;
	int BlendOp;
	int SrcBlendAlpha;
	int DestBlendAlpha;
	int BlendOpAlpha;
	unsigned char RenderTargetWriteMask;
};

struct D3D11_BLEND_DESC
{
	int AlphaToCoverageEnable;
	int IndependentBlendEnable;
	D3D11_RENDER_TARGET_BLEND_DESC RenderTarget[8];
};

struct D3D11_DEPTH_STENCILOP_DESC
{
	int StencilFailOp;
	int StencilDepthFailOp;
	int StencilPassOp;
	int StencilFunc;
};

struct D3D11_DEPTH_STENCIL_DESC
{
	int DepthEnable;
	int DepthWriteMask;
	int DepthFunc;
	int StencilEnable;
	unsigned char StencilReadMask;
	unsigned char StencilWriteMask;
	D3D11_DEPTH_STENCILOP_DESC FrontFace;
	D3D11_DEPTH_STENCILOP_DESC BackFace;
};

struct D3D11_RASTERIZER_DESC
{
	int FillMode;
	int CullMode;
	int FrontCounterClockwise;
	int DepthBias;
	float DepthBiasClamp;
	float SlopeScaledDepthBias;
	int DepthClipEnable;
	int ScissorEnable;
	int MultisampleEnable;
	int AntialiasedLineEnable;
};

struct D3D11_SAMPLER_DESC
{
	int Filter;
	int AddressU;
	int AddressV;
	int AddressW;
	float MipLODBias;
	unsigned int MaxAnisotropy;
	int ComparisonFunc;
	float BorderColor[4];
	float MinLOD;
	float MaxLOD;
};

struct D3D11_QUERY_DESC
{
	int Query;
	unsigned int MiscFlags;
};

struct D3D11_INPUT_ELEMENT_DESC
{
	const char *SemanticName;
	unsigned int SemanticIndex;
	int Format;
	unsigned int InputSlot;
	unsigned int AlignedByteOffset;
	int InputSlotClass;
	unsigned int InstanceDataStepRate;
};

struct D3D11_BUFFER_DESC
{
	unsigned int ByteWidth;
	int Usage;
	unsigned int BindFlags;
	unsigned int CPUAccessFlags;
	unsigned int MiscFlags;
	unsigned int StructureByteStride;
};

// the values the Store build passes
#define D3D11_BLEND_ZERO 1
#define D3D11_BLEND_ONE 2
#define D3D11_BLEND_OP_ADD 1
#define D3D11_FILL_WIREFRAME 2
#define D3D11_FILTER_ANISOTROPIC 0x55
#define D3D11_FILTER_MIN_MAG_MIP_LINEAR 0x15
#define D3D11_TEXTURE_ADDRESS_CLAMP 3
#define D3D11_TEXTURE_ADDRESS_BORDER 4
#define D3D11_COMPARISON_GREATER 5
#define D3D11_QUERY_EVENT 0
#define D3D11_QUERY_OCCLUSION 1
#define D3D11_USAGE_DYNAMIC 2
#define D3D11_BIND_CONSTANT_BUFFER 0x4
#define D3D11_CPU_ACCESS_WRITE 0x10000
#define D3D11_FLOAT32_MAX 3.402823466e+38f
#define S_FALSE 1

static_assert(sizeof(D3D11_RENDER_TARGET_BLEND_DESC) == 0x20, "D3D11_RENDER_TARGET_BLEND_DESC");
static_assert(__builtin_offsetof(D3D11_RENDER_TARGET_BLEND_DESC, RenderTargetWriteMask) == 0x1C, "write mask");
static_assert(sizeof(D3D11_BLEND_DESC) == 0x108, "D3D11_BLEND_DESC");
static_assert(sizeof(D3D11_DEPTH_STENCIL_DESC) == 0x34, "D3D11_DEPTH_STENCIL_DESC");
static_assert(__builtin_offsetof(D3D11_DEPTH_STENCIL_DESC, StencilWriteMask) == 0x11, "stencil write mask");
static_assert(__builtin_offsetof(D3D11_DEPTH_STENCIL_DESC, BackFace) == 0x24, "back face");
static_assert(sizeof(D3D11_RASTERIZER_DESC) == 0x28, "D3D11_RASTERIZER_DESC");
static_assert(sizeof(D3D11_SAMPLER_DESC) == 0x34, "D3D11_SAMPLER_DESC");
static_assert(__builtin_offsetof(D3D11_SAMPLER_DESC, BorderColor) == 0x1C, "border color");
static_assert(sizeof(D3D11_QUERY_DESC) == 8, "D3D11_QUERY_DESC");
static_assert(sizeof(D3D11_INPUT_ELEMENT_DESC) == 0x20, "D3D11_INPUT_ELEMENT_DESC");
static_assert(sizeof(D3D11_BUFFER_DESC) == 0x18, "D3D11_BUFFER_DESC");

// ---- game side ------------------------------------------------------------------------------------------------

union GfxZoneTableEntry
{
	void *voidPtr;
	ID3D11Buffer *buffer;
	ID3D11DepthStencilState *depthStencilState;
	ID3D11BlendState *blendState;
};

struct DxGlobalsStates
{
	DxGlobals head;                                         // r_dx.h, 0x00..0x40
	ID3D11Buffer *reactiveTurbulenceEffectorBuffer;          // 0x40
	ID3D11Buffer *smodelWorldMatrixConstantBuffer;           // 0x48
	ID3D11Buffer *smodelLightingOrAmbientConstantBuffer;     // 0x50
	unsigned char unknown_58[0x430 - 0x58];                  // constantBufferCounts[3][81] and 8 unknown bytes
	const GfxZoneTableEntry *constantBufferTables[3][81];    // 0x430
	unsigned int depthStencilStateCounts[81];                // 0xBC8
	unsigned int blendStateCounts[81];                       // 0xD0C
	const GfxZoneTableEntry *depthStencilStateTables[81];    // 0xE50
	const GfxZoneTableEntry *blendStateTables[81];           // 0x10D8
	GfxZoneTableEntry defaultDepthStencilStates[256];        // 0x1360
	GfxZoneTableEntry defaultBlendStates[64];                // 0x1B60
	unsigned long long defaultDepthStencilStateBits[256];    // 0x1D60
	unsigned int defaultBlendStateBits[64][1];               // 0x2560
	ID3D11RasterizerState *rasterizerStates[32];             // 0x2660
	GfxZoneTableEntry defaultConstantBuffers[3][128];        // 0x2760
	ID3D11Buffer *precompiledConstantBuffer;                 // 0x3360
	ID3D11SamplerState *samplerStates[256];                  // 0x3368
	void *immediateContextMutex;                             // 0x3B68
	unsigned char unknown_3b70[0x7B98 - 0x3B70];             // adapter and display modes
	ID3D11Query *fencePool[32];                              // 0x7B98
	unsigned int nextFence;                                  // 0x7C98
	unsigned int multiSampleType;                            // 0x7C9C
	unsigned char unknown_7ca0[0x7CF8 - 0x7CA0];             // ... flushGpuFence 0x7CE8, flushGpuFenceIssued 0x7CF0
	ID3D11Query *swapFence;                                  // 0x7CF8 (0x7D30 in the server)
	bool unk_7D00;                                           // name unknown: set while swapFence is in flight
	unsigned char unknown_7d01[0x7D2C - 0x7D01];             // the filter fields
	float mipBias;                                           // 0x7D2C: copied bit for bit into MipLODBias
};

#define dxs (*(DxGlobalsStates *)&dx)

static_assert(sizeof(DxGlobals) == 0x40, "DxGlobals head");
static_assert(__builtin_offsetof(DxGlobalsStates, smodelWorldMatrixConstantBuffer) == 0x48, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, constantBufferTables) == 0x430, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, depthStencilStateCounts) == 0xBC8, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, blendStateCounts) == 0xD0C, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, depthStencilStateTables) == 0xE50, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, blendStateTables) == 0x10D8, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, defaultDepthStencilStates) == 0x1360, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, defaultBlendStates) == 0x1B60, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, rasterizerStates) == 0x2660, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, defaultConstantBuffers) == 0x2760, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, samplerStates) == 0x3368, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, immediateContextMutex) == 0x3B68, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, fencePool) == 0x7B98, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, nextFence) == 0x7C98, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, multiSampleType) == 0x7C9C, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, swapFence) == 0x7CF8, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, unk_7D00) == 0x7D00, "DxGlobals layout");
static_assert(__builtin_offsetof(DxGlobalsStates, mipBias) == 0x7D2C, "DxGlobals layout");
