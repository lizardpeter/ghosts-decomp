// gfx_d3d/r_state_d3d11.h: what the state, shader, input-layout and query code needs from Direct3D 11 and from
// DxGlobals (Store build).
//
// The D3D11 descriptions are declared by hand (the reconstruction is built without the Windows SDK) with the
// public API's layout; enums are plain ints. Sizes and the offsets the Store build writes are asserted below.
//
// The DxGlobals fields this code uses are in gfx_d3d/r_dx.h.
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

// GfxZoneTableEntry and the DxGlobals members used here are in gfx_d3d/r_dx.h.
