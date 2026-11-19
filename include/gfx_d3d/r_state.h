// gfx_d3d/r_state.h: the back end's command buffer state, Store-build layout.
//
// Names and order are the Xbox One server PDB's (iw6_ds_xb3: GfxCmdBufPrimState 0xF30, GfxCmdBufState 0x23B0,
// GfxCmdBufSourceState 0x29E0). The Store build's GfxCmdBufState has the same size and offsets, except that
// renderTargetSuiteId moved 4 bytes up to make room for msaaTarget (checked against R_SetRenderTarget,
// R_SetRenderTargetSuite and R_HW_SetGammaWriteEnable). Its GfxCmdBufSourceState is bigger (0x2D10): the code
// constants grew from 276 to 291 vectors. Only the source-state fields reconstructed code uses are spelled out,
// each checked against the Store code that reads it.
//
// The state is the renderer's cache of what is bound to one ID3D11DeviceContext (prim.device: the immediate
// context or a worker's deferred context). Every setter compares with it and only calls Direct3D on a change.
#pragma once

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"
#include "gfx_d3d/r_material.h"

struct ID3D11InputLayout;
struct GfxMeshData;
struct ID3D11ShaderResourceView;

// R_RENDERTARGET_NONE and R_RENDERTARGET_SUITE_NONE in the Store build (0x181 and 3 in the xb3 server)
#define R_RENDERTARGET_NONE_STORE 0x184

#define DXGI_FORMAT_R16_UINT_VALUE 57  // the index format of every index buffer
#define R_RENDERTARGET_SUITE_NONE_STORE 4

enum GfxDepthRangeType  // xb3 PDB
{
	GFX_DEPTH_RANGE_SCENE = 0x0,
	GFX_DEPTH_RANGE_VIEWMODEL = 0x1,
	GFX_DEPTH_RANGE_FORCE_NEAR = 0x2,
	GFX_DEPTH_RANGE_FORCE_FAR = 0x3,
	GFX_DEPTH_RANGE_FULL = -1,  // what R_InitCmdBufState leaves
};

// xb3 PDB: R_RENDERTARGET_SUITE_LIT, _POST_OPAQUE, then _COUNT = 2 and _NONE = 3. The Store build has one more suite
// (NONE is 4, and GfxCmdBufInput has room for three pairs); its name is unknown.
enum GfxRenderTargetSuiteId
{
	R_RENDERTARGET_SUITE_LIT = 0,
	R_RENDERTARGET_SUITE_POST_OPAQUE = 1,
};

struct D3D11_VIEWPORT
{
	float TopLeftX;
	float TopLeftY;
	float Width;
	float Height;
	float MinDepth;
	float MaxDepth;
};

struct D3D11_RECT
{
	long left;
	long top;
	long right;
	long bottom;
};

struct GfxViewport
{
	int x;
	int y;
	int width;
	int height;
};

struct GfxDrawPrimArgs
{
	int primCount;
	int baseIndex;
	int vertIndexBase;  // xb3 PDB: vertexCount there; DrawIndexed's BaseVertexLocation here
};

struct GfxCmdBufPrimState  // 0xF30
{
	ID3D11DeviceContext *device;
	ID3D11Buffer *indexBuffer;
	int vertDeclType;  // MaterialVertexDeclType: the index into a pass's routing.decl[]
	unsigned int primType;  // D3D11_PRIMITIVE_TOPOLOGY
	unsigned int streamStrides[3];
	ID3D11Buffer *streamBuffers[3];
	unsigned int streamOffsets[3];
	ID3D11InputLayout *vertexDecl;
	unsigned char padding[8];
	alignas(16) float perPrimConstantShadow[80][4];  // __m128 in the PDB: the structs are 16-byte aligned
	float perObjectConstantShadow[64][4];
	float stableConstantShadow[88][4];
	ID3D11Buffer *perPrimVSPSConstantBuffer;
	ID3D11Buffer *perPrimHSDSConstantBuffer;
	ID3D11Buffer *perObjectVSPSConstantBuffer;
	ID3D11Buffer *perObjectHSDSConstantBuffer;
	ID3D11Buffer *stableVSPSConstantBuffer;
	ID3D11Buffer *stableHSDSConstantBuffer;
	ID3D11Buffer *perMaterialVSConstantBuffer;
	ID3D11Buffer *perMaterialHSConstantBuffer;
	ID3D11Buffer *perMaterialDSConstantBuffer;
	ID3D11Buffer *perMaterialPSConstantBuffer;
};
static_assert(sizeof(GfxCmdBufPrimState) == 0xF30, "GfxCmdBufPrimState");
static_assert(__builtin_offsetof(GfxCmdBufPrimState, streamBuffers) == 0x28, "GfxCmdBufPrimState");
static_assert(__builtin_offsetof(GfxCmdBufPrimState, vertexDecl) == 0x50, "GfxCmdBufPrimState");
static_assert(__builtin_offsetof(GfxCmdBufPrimState, perObjectConstantShadow) == 0x560, "GfxCmdBufPrimState");
static_assert(__builtin_offsetof(GfxCmdBufPrimState, stableConstantShadow) == 0x960, "GfxCmdBufPrimState");
static_assert(__builtin_offsetof(GfxCmdBufPrimState, perPrimVSPSConstantBuffer) == 0xEE0, "GfxCmdBufPrimState");

struct GfxDeviceState  // 0x30
{
	float blendFactor[4];
	unsigned int sampleMask;
	bool srgbWrite;
	bool srgbRenderTarget;
	ID3D11RasterizerState *rasterizerState;
	ID3D11BlendState *blendState;
	ID3D11DepthStencilState *depthStencilState;
};
static_assert(sizeof(GfxDeviceState) == 0x30, "GfxDeviceState");

struct GfxCmdBufState  // 0x23B0
{
	GfxCmdBufPrimState prim;
	unsigned char vertexSamplerState[16];
	unsigned char domainSamplerState[16];
	unsigned char pixelSamplerState[16];
	const GfxTexture *vertexTexture[128];
	const GfxTexture *domainTexture[128];
	const GfxTexture *pixelTexture[128];
	int firstVertexSamplerDirty;
	int lastVertexSamplerDirty;
	int firstDomainSamplerDirty;
	int lastDomainSamplerDirty;
	int firstPixelSamplerDirty;
	int lastPixelSamplerDirty;
	int firstVertexTextureDirty;
	int lastVertexTextureDirty;
	int firstDomainTextureDirty;
	int lastDomainTextureDirty;
	int firstPixelTextureDirty;
	int lastPixelTextureDirty;
	const Material *material;
	MaterialTechniqueType techType;
	const MaterialTechnique *technique;
	const MaterialPass *pass;
	unsigned int passIndex;
	GfxDepthRangeType depthRangeType;
	float depthRangeNear;  // RSSetViewports' MaxDepth
	float depthRangeFar;   // RSSetViewports' MinDepth (the game uses reversed depth)
	unsigned long long perPrimConstantState[80];
	unsigned long long perObjectConstantState[64];
	unsigned long long stableConstantState[88];
	GfxDepthStencilMode depthStencilMode;
	bool forceNoDepthHack;
	unsigned int refStateBits[3];
	const MaterialPixelShader *pixelShader;
	const MaterialVertexShader *vertexShader;
	const MaterialHullShader *hullShader;
	const MaterialDomainShader *domainShader;
	const void *computeShader;
	int shaderMode;
	int scissorX;
	int scissorY;
	int scissorW;
	int scissorH;
	GfxViewport viewport;
	int renderTargetId;              // GfxRenderTargetId; R_RENDERTARGET_NONE_STORE when a suite is bound
	bool msaaTarget;                 // Store: the bound target's multisampled surfaces (imageAndSurfaces[1]) are used
	int renderTargetSuiteId;         // GfxRenderTargetSuiteId; R_RENDERTARGET_SUITE_NONE_STORE when a target is bound
	int renderTargetSuite[2];
	GfxDeviceState deviceState;
};
static_assert(sizeof(GfxCmdBufState) == 0x23B0, "GfxCmdBufState (Store build)");
static_assert(__builtin_offsetof(GfxCmdBufState, vertexTexture) == 0xF60, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, firstVertexSamplerDirty) == 0x1B60, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, material) == 0x1B90, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, pass) == 0x1BA8, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, depthRangeType) == 0x1BB4, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, perPrimConstantState) == 0x1BC0, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, depthStencilMode) == 0x2300, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, refStateBits) == 0x2308, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, pixelShader) == 0x2318, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, scissorX) == 0x2344, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, viewport) == 0x2354, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, renderTargetId) == 0x2364, "GfxCmdBufState");
static_assert(__builtin_offsetof(GfxCmdBufState, renderTargetSuiteId) == 0x236C, "GfxCmdBufState (Store)");
static_assert(__builtin_offsetof(GfxCmdBufState, deviceState) == 0x2378, "GfxCmdBufState");

struct GfxBackEndData;

// GfxCmdBufInput, Store layout (0x14A0; 0x11A0 in the xb3 server)
struct GfxCmdBufInput
{
	float consts[291][4];
	const GfxImage *codeImages[65];              // 0x1230: R_GetTextureFromCode
	unsigned char codeImageSamplerStates[65];    // 0x1438
	bool noLitPrepass;
	bool noLightMapPrepass;
	int renderTargetSuites[3][2];                // per GfxRenderTargetSuiteId: its two targets (R_SetRenderTargetSuite)
	unsigned char unknown1494[4];
	const GfxBackEndData *data;
};
static_assert(sizeof(GfxCmdBufInput) == 0x14A0, "GfxCmdBufInput (Store build)");
static_assert(__builtin_offsetof(GfxCmdBufInput, codeImageSamplerStates) == 0x1438, "GfxCmdBufInput (Store build)");
static_assert(__builtin_offsetof(GfxCmdBufInput, renderTargetSuites) == 0x147C, "GfxCmdBufInput (Store build)");

// GfxCmdBufSourceState, Store layout (0x2D10). Fields named from the xb3 PDB where the Store code reads them the same
// way.
struct GfxCmdBufSourceState
{
	unsigned char matrices[0x1200];               // GfxCodeMatrices
	GfxCmdBufInput input;                         // 0x1200
	unsigned char unknown26A0[0x2900 - 0x26A0];   // viewParms, eyeOffset, shadowLookupMatrix
	unsigned short constVersions[291];            // 0x2900
	unsigned char unknown2B46[0x2C84 - 0x2B46];   // matrixVersions, ..., cameraView
	int viewMode;                                 // 0x2C84 (GfxViewMode)
	unsigned char unknown2C88[0x2CD0 - 0x2C88];   // sceneDef, sceneViewport
	GfxDepthStencilMode depthStencilMode;         // 0x2CD0
	bool multiSampled;                            // 0x2CD4 (Store): R_InitCmdBufSourceState's flags bit 1
	unsigned char unknown2CD5[0x2CFC - 0x2CD5];   // materialTime, ..., renderTargetHeight, scene lights
	unsigned char flags;                          // 0x2CFC: bit 0 viewportIsDirty, bit 4 noPrepass (xb3 bitfields)
	unsigned char unknown2CFD[0x2D10 - 0x2CFD];
};
static_assert(sizeof(GfxCmdBufSourceState) == 0x2D10, "GfxCmdBufSourceState (Store build)");
static_assert(__builtin_offsetof(GfxCmdBufSourceState, input.data) == 0x2698, "GfxCmdBufSourceState");
static_assert(__builtin_offsetof(GfxCmdBufSourceState, input.renderTargetSuites) == 0x267C, "GfxCmdBufSourceState");

#define GFX_SOURCE_VIEWPORT_IS_DIRTY 0x01
#define GFX_SOURCE_NO_PREPASS 0x10

struct GfxCmdBufContext
{
	GfxCmdBufSourceState *source;
	GfxCmdBufState *state;
};

// The render targets (gfx_d3d/r_rendertarget.cpp; GfxRenderTarget is in gfx_d3d/r_image.h)
extern GfxRenderTarget gfxRenderTargets[];

// ---- gfx_d3d/r_setstate_d3d.cpp ---------------------------------------------------------------------------------
void R_InitializeDefaultDeviceStates(GfxCmdBufState *state);
void R_HW_SetGammaWriteEnable(GfxCmdBufState *state, unsigned int stateBits0);

// ---- gfx_d3d/r_state.cpp (per-frame part) -------------------------------------------------------------------------
void R_SetState(GfxCmdBufContext context, const unsigned int *const stateBits, const GfxStateBits *refStateBits);
void R_SetCompleteState(GfxCmdBufState *state, const unsigned int *const stateBits);
void R_FlushTextureState(GfxCmdBufState *state);
void R_UnbindImage(GfxCmdBufState *state, const GfxImage *image);
void R_ClearAllStreamSources(GfxCmdBufPrimState *primState);
void R_SetPrimType(GfxCmdBufPrimState *primState, unsigned int primType);

void R_ClearAllVertexTextures(GfxCmdBufState *state);
void R_ClearAllDomainTextures(GfxCmdBufState *state);
void R_ClearAllPixelTextures(GfxCmdBufState *state);
void R_ShutdownCmdBufState(GfxCmdBufState *state);
void R_HW_SetScissor(GfxCmdBufState *state, const GfxViewport *scissor);

// ---- gfx_d3d/r_state_utils.cpp -----------------------------------------------------------------------------------
void R_InitCmdBufState(GfxCmdBufState *state);

// ---- gfx_d3d/r_shade.cpp ----------------------------------------------------------------------------------------
void R_SetHullAndDomainShaders(GfxCmdBufState *state, const MaterialHullShader *hullShader,
                               const MaterialDomainShader *domainShader);
bool R_SetStableConstantBuffer(GfxCmdBufState *state, const MaterialPass *pass);

// ---- gfx_d3d/r_state.h inlines ------------------------------------------------------------------------------------

// xb3 PDB: R_HW_SetRenderTarget (gfx_d3d/r_state.h:2204), inlined everywhere in the Store build. Binds one target's
// colour view (the sRGB one when the state asks for gamma writes and the format has one) and its depth view, unless
// the same pair is bound already. Floating-point formats (R16G16B16A16_FLOAT, R11G11B10_FLOAT, R16_FLOAT) have no sRGB
// view, so gamma writes are ignored for them.
static inline void R_HW_SetRenderTarget(GfxCmdBufState *state, int newTargetId)
{
	if (newTargetId == R_RENDERTARGET_NONE_STORE)
		return;
	ID3D11DeviceContext *device = state->prim.device;
	bool srgb = false;
	if (state->deviceState.srgbWrite)
	{
		unsigned int format = (unsigned int)gfxRenderTargets[newTargetId].format;
		srgb = !(format < 0x37 && ((0x40000004000400ull >> (format & 0x3F)) & 1));
	}
	unsigned int msaa = state->msaaTarget;
	const GfxRenderTargetSurface *surface = &gfxRenderTargets[newTargetId].imageAndSurfaces[msaa].surface;
	bool wasSrgb = state->deviceState.srgbRenderTarget;
	ID3D11DepthStencilView *depthStencil = surface->depthStencil;
	state->deviceState.srgbRenderTarget = srgb;
	ID3D11RenderTargetView *color = srgb ? surface->colorGamma : surface->color;
	int oldTargetId = state->renderTargetId;
	if (oldTargetId != R_RENDERTARGET_NONE_STORE)
	{
		const GfxRenderTargetSurface *old = &gfxRenderTargets[oldTargetId].imageAndSurfaces[msaa].surface;
		if (depthStencil == old->depthStencil && color == (wasSrgb ? old->colorGamma : old->color))
			return;
	}
	ComCall<void>(device, CTX_OMSetRenderTargets, 1u, &color, depthStencil);
}
