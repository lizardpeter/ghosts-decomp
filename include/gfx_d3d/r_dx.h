// gfx_d3d/r_dx.h: the renderer's Direct3D globals (DxGlobals), Store-build layout.
//
// The Xbox One server PDB (iw6_ds_xb3) has DxGlobals (0x7d38 bytes); the Store build's starts the same way
// (verified: D3D11CreateDevice stores the device at +0x08 and the feature level at +0x38, CreateDXGIFactory the
// factory at +0x20). Only the fields reconstructed code uses are spelled out.
#pragma once

#include "gfx_d3d/r_dxgi.h"

struct ID3D11Device;
struct ID3D11DeviceContext;
struct IDXGIFactory;
struct IDXGIAdapter;
struct IDXGIOutput;

// ==== BEGIN device ====
struct ID3D11Buffer;
struct ID3D11DepthStencilState;
struct ID3D11BlendState;
struct ID3D11RasterizerState;
struct ID3D11SamplerState;

// An entry of the renderer's state and constant buffer tables (XB3 PDB)
union GfxZoneTableEntry
{
	void *voidPtr;
	ID3D11Buffer *buffer;
	ID3D11DepthStencilState *depthStencilState;
	ID3D11BlendState *blendState;
};

// One window the device presents to (XB3 PDB GfxWindowTarget; the Store build uses the same layout).
struct GfxWindowTarget
{
	struct HWND__ *hwnd;
	IDXGISwapChain *swapChain;
	ID3D11Texture2D *depthStencilTex;
	int width;
	int height;
};
// ==== END device ====

struct DxGlobals
{
	void *hinst;
	ID3D11Device *d3d11device;
	ID3D11DeviceContext *immediateContext;
	int immediateContextLockCount;
	unsigned int immediateContextThreadId;
	IDXGIFactory *dxgiFactory;
	IDXGIAdapter *dxgiAdapter;
	IDXGIOutput *dxgiOutput;
	int d3d11FeatureLevel;
	// ==== BEGIN device ====
	// Store-build offsets, checked by gfx_d3d/r_init.cpp's static_asserts. Names and types are the XB3 PDB's; the
	// Store build has 8 more bytes than the XB3 server after 0x58 and 0x18 more after the fence pool.
	ID3D11Buffer *reactiveTurbulenceEffectorBuffer;           // 0x40
	ID3D11Buffer *smodelWorldMatrixConstantBuffer;            // 0x48
	ID3D11Buffer *smodelLightingOrAmbientConstantBuffer;      // 0x50
	char unk_0058[8];                                         // Store build only
	unsigned int constantBufferCounts[3][81];                 // 0x60
	const GfxZoneTableEntry *constantBufferTables[3][81];     // 0x430
	unsigned int depthStencilStateCounts[81];                 // 0xBC8
	unsigned int blendStateCounts[81];                        // 0xD0C
	const GfxZoneTableEntry *depthStencilStateTables[81];     // 0xE50
	const GfxZoneTableEntry *blendStateTables[81];            // 0x10D8
	GfxZoneTableEntry defaultDepthStencilStates[256];         // 0x1360
	GfxZoneTableEntry defaultBlendStates[64];                 // 0x1B60
	unsigned long long defaultDepthStencilStateBits[256];     // 0x1D60
	unsigned int defaultBlendStateBits[64][1];                // 0x2560
	ID3D11RasterizerState *rasterizerStates[32];              // 0x2660
	GfxZoneTableEntry defaultConstantBuffers[3][128];         // 0x2760
	ID3D11Buffer *precompiledConstantBuffer;                  // 0x3360
	ID3D11SamplerState *samplerStates[256];                   // 0x3368
	void *immediateContextMutex;            // 0x3B68
	unsigned int adapterIndex;              // 0x3B70
	bool adapterNativeIsValid;              // 0x3B74
	int adapterNativeWidth;                 // 0x3B78
	int adapterNativeHeight;                // 0x3B7C
	unsigned int displayModeCount;          // 0x3B80
	DXGI_MODE_DESC displayModes[256];       // 0x3B84
	const char *resolutionNameTable[257];   // 0x5788
	const char *refreshRateNameTable[257];  // 0x5F90
	char modeText[5120];                    // 0x6798
	ID3D11Query *fencePool[32];             // 0x7B98
	unsigned int nextFence;                 // 0x7C98
	int multiSampleType;                    // 0x7C9C: the MSAA sample count, 0 without MSAA
	char unk_7CA0[0x7CC8 - 0x7CA0];
	volatile bool deviceLost;               // 0x7CC8
	int targetWindowIndex;                  // 0x7CCC
	bool forceWindow;                       // 0x7CD0
	bool forceFullscreen;                   // 0x7CD1
	int windowCount;                        // 0x7CD4
	GfxWindowTarget windows[1];             // 0x7CD8
	ID3D11Query *flushGpuFence;             // 0x7CF8
	bool flushGpuFenceIssued;               // 0x7D00
	// ==== END device ====
	// the rest is not needed yet
};

extern DxGlobals dx;  // gfx_d3d/r_init.cpp

// ==== BEGIN device ====
// The immediate context's lock: a mutex (dx.immediateContextMutex, created with the device) that is recursive for
// the thread holding it. The Store build inlines it everywhere (more than 60 functions); the names are ours.
extern "C" {
unsigned long WaitForSingleObject(void *hHandle, unsigned long dwMilliseconds);
int ReleaseMutex(void *hMutex);
unsigned long GetCurrentThreadId(void);
}

static inline void R_LockImmediateContext()
{
	WaitForSingleObject(dx.immediateContextMutex, 0xFFFFFFFF);
	if (dx.immediateContextLockCount == 0)
		dx.immediateContextThreadId = GetCurrentThreadId();
	++dx.immediateContextLockCount;
}

static inline void R_UnlockImmediateContext()
{
	if (--dx.immediateContextLockCount == 0)
		dx.immediateContextThreadId = 0xFFFFFFFF;
	ReleaseMutex(dx.immediateContextMutex);
}
// ==== END device ====
