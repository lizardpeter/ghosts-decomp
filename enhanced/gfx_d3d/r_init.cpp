// enhanced/gfx_d3d/r_init.cpp: flip-model presentation with at most one frame queued (records/patches.tsv P0003).
//
// Replaces R_CreateDevice, R_RecoverLostDevice (with the R_ResetDevice it inlines) and RB_SwapBuffers of
// src/gfx_d3d/r_init.cpp, and the DXGI factory's creation:
// - the swap chain is DXGI_SWAP_EFFECT_FLIP_DISCARD (two buffers), which lets Windows hand the game's buffers straight
//   to the display (independent flip) in fullscreen and in a borderless window covering the monitor, instead of
//   copying them through the compositor;
// - tearing is allowed when the system supports it, so r_vsync 0 runs uncapped or with VRR;
// - the device queues at most one frame (IDXGIDevice1::SetMaximumFrameLatency);
// - a system that can't create a flip-model swap chain gets the original one.
//
// The frame-latency waitable object (waiting at the start of a frame, then reading input) comes once the frame loop
// is mapped: it has to be waited on exactly once per presented frame.

#include <windows.h>

#include "client/client.h"
#include "enhanced/dxgi_flip.h"
#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"
#include "gfx_d3d/r_init.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

static bool s_flipModel = true;  // false once the system refused a flip-model swap chain
static bool s_allowTearing;

// DXGI 1.1: the factory supports flip-model swap chains (the original's CreateDXGIFactory gives a DXGI 1.0 factory,
// and DXGI doesn't allow mixing the two). Replaces the import for src's R_ChooseAdapter.
extern "C" HRESULT CreateDXGIFactory(const GUID &riid, void **ppFactory)
{
	return CreateDXGIFactory1(riid, ppFactory);
}

// ---- callees of the functions below (as declared in src/gfx_d3d/r_init.cpp) ----
extern const dvar_t *r_displayMode;
extern const dvar_t *r_rendererInUse;
extern const dvar_t *r_amdGPU;
extern const dvar_t *r_multiGPU;
extern const dvar_t *r_vsync;
void Dvar_SetBool(const dvar_t *dvar, bool value);
void Sys_DirectXFatalError();
bool Sys_IsMainThread();
void Sys_LoadingKeepAlive();
bool R_IsReallyNvidiaGPU();
void sub_1401B0030();
bool sub_140631850(IDXGIAdapter *adapter);
struct NV_GET_CURRENT_SLI_STATE
{
	unsigned int version;
	unsigned int maxNumAFRGroups;
	unsigned int numAFRGroups;
};
extern "C" int NvAPI_D3D_GetCurrentSLIState(void *pDevice, NV_GET_CURRENT_SLI_STATE *pSliState);
extern "C" void *CreateMutexA(void *lpMutexAttributes, BOOL bInitialOwner, const char *lpName);
extern bool unk_14A37D580;
int R_PopRemoteScreenUpdate();
void R_SyncRenderThread();
void R_PushRemoteScreenUpdate(int remoteScreenUpdateNesting);
void DB_SyncXAssets();
void DB_BeginRecoverLostDevice();
void DB_EndRecoverLostDevice();
void R_Cinematic_BeginLostDevice();
void R_Cinematic_EndLostDevice();
void R_ResetModelLighting();
void R_ReleaseLostImages();
void R_ReloadLostImages();
void Material_ReleaseAll();
void Material_ReloadAll();
void R_ReleaseWorld(int);
void R_ReloadWorld();
unsigned int R_GetGlobalMultisampleCount();
const char *R_ErrorDescription(HRESULT hr);
bool R_CreateForInitOrReset(int reset);
void R_FlushSwap();
void R_ReleaseForShutdownOrReset(unsigned int frontEndFrameCount, int resetOnly);
const char *va(const char *format, ...);
struct GfxCmdBufState;
struct GfxCmdBufSourceState;
struct GfxCmdBufInput;
struct GfxCmdBufContext
{
	GfxCmdBufSourceState *source;
	GfxCmdBufState *state;
};
extern GfxCmdBufState gfxCmdBufState;
extern GfxCmdBufSourceState gfxCmdBufSourceState;
extern GfxCmdBufInput gfxCmdBufInput;
extern const GfxCmdBufContext gfxCmdBufContext;
void R_InitCmdBufSourceState(GfxCmdBufSourceState *source, const GfxCmdBufInput *input, unsigned int cameraView);
void R_InitCmdBufState(GfxCmdBufState *state);
void RB_InitSceneViewport();
void R_SetRenderTargetSize(GfxCmdBufSourceState *source, GfxRenderTargetId newTargetId);
void R_SetRenderTarget(GfxCmdBufContext context, GfxRenderTargetId newTargetId);
extern unsigned int unk_14A37CD6C;
extern int unk_14A37D568;
extern ID3D11RenderTargetView *unk_14B07F658;
extern int unk_149D62D6C;
extern ID3D11Query *unk_14A385398;
extern int *unk_14A107B60;
bool sub_1406968F0();
void sub_1406967E0(ID3D11DeviceContext *context, ID3D11RenderTargetView *view);
void sub_140696900(ID3D11DeviceContext *context, ID3D11RenderTargetView *view);
void sub_14062EC80(ID3D11Query *fence);

#define WAIT_TIMEOUT 0x102
#define WM_USER 0x0400

// The original description (src: R_SetD3DPresentParameters), for the fallback when the system can't create a flip-model
// swap chain:
// the swap chain of a window. Two R8G8B8A8 buffers, no MSAA (the multisampled targets are separate), windowed (the
// fullscreen state is switched later with SetFullscreenState), DXGI_SWAP_EFFECT_DISCARD, mode switches allowed.
static void R_SetD3DPresentParameters(DXGI_SWAP_CHAIN_DESC *swapChainDesc, const GfxWindowParms *wndParms)
{
	swapChainDesc->BufferDesc.Width = wndParms->displayWidth;
	swapChainDesc->BufferDesc.Height = wndParms->displayHeight;
	swapChainDesc->BufferDesc.RefreshRate.Numerator = wndParms->hz.Numerator;
	swapChainDesc->BufferDesc.RefreshRate.Denominator = wndParms->hz.Denominator;
	swapChainDesc->BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
	swapChainDesc->BufferDesc.ScanlineOrdering = 0;
	swapChainDesc->BufferDesc.Scaling = 0;
	swapChainDesc->SampleDesc.Count = 1;
	swapChainDesc->SampleDesc.Quality = 0;
	swapChainDesc->BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
	swapChainDesc->BufferCount = 2;
	swapChainDesc->OutputWindow = wndParms->hwnd;
	swapChainDesc->Windowed = 1;
	swapChainDesc->SwapEffect = 0;
	swapChainDesc->Flags = DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH;
}

// The swap chain description (src: R_SetD3DPresentParameters, inlined in the Store build), flip model: two buffers,
// DXGI_SWAP_EFFECT_FLIP_DISCARD, tearing allowed when the system supports it (for an uncapped or VRR present).
// The fullscreen state is still switched later with SetFullscreenState, as in the original.
static void R_SetFlipPresentParameters(DXGI_SWAP_CHAIN_DESC *swapChainDesc, const GfxWindowParms *wndParms)
{
	swapChainDesc->BufferDesc.Width = wndParms->displayWidth;
	swapChainDesc->BufferDesc.Height = wndParms->displayHeight;
	swapChainDesc->BufferDesc.RefreshRate.Numerator = wndParms->hz.Numerator;
	swapChainDesc->BufferDesc.RefreshRate.Denominator = wndParms->hz.Denominator;
	swapChainDesc->BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
	swapChainDesc->BufferDesc.ScanlineOrdering = 0;
	swapChainDesc->BufferDesc.Scaling = 0;
	swapChainDesc->SampleDesc.Count = 1;
	swapChainDesc->SampleDesc.Quality = 0;
	swapChainDesc->BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
	swapChainDesc->BufferCount = 2;
	swapChainDesc->OutputWindow = wndParms->hwnd;
	swapChainDesc->Windowed = 1;
	swapChainDesc->SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
	swapChainDesc->Flags = DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH
	                       | (s_allowTearing ? DXGI_SWAP_CHAIN_FLAG_ALLOW_TEARING : 0u);
}

// Whether DXGI can present with tearing (IDXGIFactory5::CheckFeatureSupport, PRESENT_ALLOW_TEARING); false when the
// factory is older than DXGI 1.5.
static bool R_CheckTearingSupport()
{
	void *factory5 = nullptr;
	BOOL allowTearing = 0;
	if (ComCall<HRESULT>(dx.dxgiFactory, UNK_QueryInterface, &IID_IDXGIFactory5_Enhanced, &factory5) >= 0 && factory5)
	{
		if (ComCall<HRESULT>(factory5, FACTORY5_CheckFeatureSupport, DXGI_FEATURE_PRESENT_ALLOW_TEARING, &allowTearing,
		                     (unsigned int)sizeof(allowTearing)) < 0)
			allowTearing = 0;
		ComCall<unsigned long>(factory5, UNK_Release);
	}
	return allowTearing != 0;
}

// At most one frame queued for the display (IDXGIDevice1::SetMaximumFrameLatency(1)): Present waits instead of letting
// the CPU run further ahead of the GPU.
static void R_LimitFrameLatency()
{
	void *dxgiDevice1 = nullptr;
	if (ComCall<HRESULT>(dx.d3d11device, UNK_QueryInterface, &IID_IDXGIDevice1_Enhanced, &dxgiDevice1) >= 0 &&
	    dxgiDevice1)
	{
		ComCall<HRESULT>(dxgiDevice1, DXGIDEVICE1_SetMaximumFrameLatency, 1u);
		ComCall<unsigned long>(dxgiDevice1, UNK_Release);
	}
}

// The window's swap chain: flip model, or the original blit model if the system can't create one (before Windows 10).
static HRESULT R_CreateSwapChain(const GfxWindowParms *wndParms)
{
	DXGI_SWAP_CHAIN_DESC swapChainDesc;
	HRESULT hr;

	if (s_flipModel)
	{
		R_SetFlipPresentParameters(&swapChainDesc, wndParms);
		hr = ComCall<HRESULT>(dx.dxgiFactory, FACTORY_CreateSwapChain, dx.d3d11device, &swapChainDesc,
		                      &dx.windows[0].swapChain);
		if (hr >= 0)
			return hr;
		s_flipModel = false;
		s_allowTearing = false;
	}
	R_SetD3DPresentParameters(&swapChainDesc, wndParms);
	return ComCall<HRESULT>(dx.dxgiFactory, FACTORY_CreateSwapChain, dx.d3d11device, &swapChainDesc,
	                        &dx.windows[0].swapChain);
}

// src: Store 14062F420 R_CreateDevice. Enhanced: the swap chain is flip model when the system supports it, with tearing
// allowed when DXGI does, and the device queues at most one frame.
bool R_CreateDevice(const GfxWindowParms *wndParms)
{
	D3D_FEATURE_LEVEL featureLevels[6] = {D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_1, D3D_FEATURE_LEVEL_10_0,
	                                      D3D_FEATURE_LEVEL_9_3, D3D_FEATURE_LEVEL_9_2, D3D_FEATURE_LEVEL_9_1};
	DXGI_ADAPTER_DESC adapterDesc;
	DXGI_ADAPTER_DESC vendorDesc;
	NV_GET_CURRENT_SLI_STATE sliState;
	unsigned int qualityLevels;
	int sampleCount;
	int rendererInUse;
	bool multiGpu;

	multiGpu = false;
	D3D11CreateDevice(dx.dxgiAdapter, D3D_DRIVER_TYPE_UNKNOWN, nullptr,
	                  D3D11_CREATE_DEVICE_PREVENT_ALTERING_LAYER_SETTINGS_FROM_REGISTRY, featureLevels, 6,
	                  D3D11_SDK_VERSION, &dx.d3d11device, (D3D_FEATURE_LEVEL *)&dx.d3d11FeatureLevel,
	                  &dx.immediateContext);
	sub_1401B0030();
	if (dx.d3d11FeatureLevel < D3D_FEATURE_LEVEL_11_0)
	{
		if (dx.dxgiAdapter)
		{
			ComCall<HRESULT>(dx.dxgiAdapter, ADAPTER_GetDesc, &adapterDesc);
			// the description is a wide string: %s prints its first character
			Com_Error(ERR_FATAL, "You are using %s.  It does not support DX11!", adapterDesc.Description);
		}
		else
		{
			Com_Error(ERR_FATAL, "Primary adapter does not support DX11!");
		}
	}
	for (sampleCount = wndParms->aaSamples; sampleCount > 1; --sampleCount)
	{
		dx.multiSampleType = sampleCount;
		if (ComCall<HRESULT>(dx.d3d11device, DEV_CheckMultisampleQualityLevels, DXGI_FORMAT_R8G8B8A8_UNORM,
		                     (unsigned int)sampleCount, &qualityLevels) >= 0)
			break;
	}
	if (sampleCount <= 1)
		dx.multiSampleType = 0;
	s_allowTearing = R_CheckTearingSupport();
	R_CreateSwapChain(wndParms);
	R_LimitFrameLatency();
	// dx.windows[0].hwnd is set by the caller after this returns: at the first creation it is still NULL
	ComCall<HRESULT>(dx.dxgiFactory, FACTORY_MakeWindowAssociation, dx.windows[0].hwnd, DXGI_MWA_NO_WINDOW_CHANGES);
	switch (dx.d3d11FeatureLevel)
	{
	case D3D_FEATURE_LEVEL_9_1:
	case D3D_FEATURE_LEVEL_9_2:
	case D3D_FEATURE_LEVEL_9_3:
		rendererInUse = 0;
		break;
	case D3D_FEATURE_LEVEL_10_0:
	case D3D_FEATURE_LEVEL_10_1:
		rendererInUse = 1;
		break;
	default:
		rendererInUse = 2;
		break;
	}
	Dvar_SetInt(r_rendererInUse, rendererInUse);
	Dvar_SetInt(r_rendererInUse, 0);
	ComCall<HRESULT>(dx.dxgiAdapter, ADAPTER_GetDesc, &vendorDesc);
	if (vendorDesc.VendorId == 0x1002 || vendorDesc.VendorId == 0x1022)
	{
		Dvar_SetBool(r_amdGPU, true);
		multiGpu = sub_140631850(dx.dxgiAdapter);
	}
	dx.immediateContextMutex = CreateMutexA(nullptr, 0, nullptr);
	unk_14A37D580 = true;
	dx.deviceLost = false;
	if (R_IsReallyNvidiaGPU())
	{
		sliState.version = 0x1001C;  // NV_GET_CURRENT_SLI_STATE_VER
		multiGpu = NvAPI_D3D_GetCurrentSLIState(dx.d3d11device, &sliState) == 0 && sliState.numAFRGroups > 1;
	}
	Dvar_SetBool(r_multiGPU, multiGpu);
	return true;
}

// src: R_ResetDevice (inlined into R_RecoverLostDevice). Enhanced: the new swap chain is made like R_CreateDevice's.
// A window can have only one flip-model swap chain, and DXGI destroys the old one only once the context lets go of
// it, so the context is cleared and flushed first.
static void R_ResetDevice()
{
	GfxWindowParms wndParms;
	HRESULT hr;

	wndParms.hwnd = dx.windows[0].hwnd;
	wndParms.hz.Numerator = vidConfig.displayFrequency[0];
	wndParms.hz.Denominator = vidConfig.displayFrequency[1];
	wndParms.displayMode = (GfxDisplayMode)vidConfig.displayMode;
	wndParms.x = 0;
	wndParms.y = 0;
	wndParms.aspectRatioWindow = vidConfig.windowAspectRatio;
	wndParms.shadowTileResSmall = vidConfig.shadowTileResSmall;
	wndParms.shadowTileResLarge = vidConfig.shadowTileResLarge;
	wndParms.sceneWidth = vidConfig.sceneWidth;
	wndParms.sceneHeight = vidConfig.sceneHeight;
	wndParms.displayWidth = dx.windows[0].width;
	wndParms.displayHeight = dx.windows[0].height;
	wndParms.omitRTFlags = vidConfig.omitRTFlags;
	wndParms.letterbox4x3 = vidConfig.letterbox4x3;
	wndParms.aaSamples = R_GetGlobalMultisampleCount();
	R_ReleaseForShutdownOrReset(unk_14A37CD6C, 1);
	ComCall<void>(dx.immediateContext, CTX_ClearState);
	ComCall<void>(dx.immediateContext, CTX_Flush);
	hr = R_CreateSwapChain(&wndParms);
	if (hr < 0)
	{
		// the message is lost: Sys_DirectXFatalError takes none
		va("Couldn't reset a lost Direct3D device - IDXGIFactory::CreateSwapChain returned 0x%08x (%s)", hr,
		   R_ErrorDescription(hr));
		Sys_DirectXFatalError();
	}
	hr = ComCall<HRESULT>(dx.dxgiFactory, FACTORY_MakeWindowAssociation, dx.windows[0].hwnd,
	                      DXGI_MWA_NO_WINDOW_CHANGES);
	if (hr < 0)
	{
		va("Couldn't reset a lost Direct3D device - IDXGIFactory::MakeWindowAssociation returned 0x%08x (%s)", hr,
		   R_ErrorDescription(hr));
		Sys_DirectXFatalError();
	}
	dx.deviceLost = false;
	if (!R_CreateForInitOrReset(1))
		Sys_DirectXFatalError();
	R_InitCmdBufSourceState(&gfxCmdBufSourceState, &gfxCmdBufInput, 0);
	R_InitCmdBufState(&gfxCmdBufState);
	RB_InitSceneViewport();
	R_SetRenderTargetSize(&gfxCmdBufSourceState, R_RENDERTARGET_FRAME_BUFFER);
	R_SetRenderTarget(gfxCmdBufContext, R_RENDERTARGET_FRAME_BUFFER);
}

// src: Store 140631A80 R_RecoverLostDevice, unchanged but for the R_ResetDevice it inlines
bool R_RecoverLostDevice()
{
	int remoteScreenUpdateNesting;

	remoteScreenUpdateNesting = R_PopRemoteScreenUpdate();
	R_SyncRenderThread();
	DB_SyncXAssets();
	R_SyncRenderThread();
	R_Cinematic_BeginLostDevice();
	DB_BeginRecoverLostDevice();
	R_ResetModelLighting();
	R_ReleaseLostImages();
	Material_ReleaseAll();
	R_ReleaseWorld(1);
	R_ResetDevice();
	R_ReloadWorld();
	Material_ReloadAll();
	R_ReloadLostImages();
	DB_EndRecoverLostDevice();
	R_Cinematic_EndLostDevice();
	R_PushRemoteScreenUpdate(remoteScreenUpdateNesting);
	R_FlushSwap();
	return true;
}

// Present, keeping the render targets bound across it (flip model unbinds the back buffer)
static HRESULT R_Present(IDXGISwapChain *swapChain, unsigned int syncInterval, int fullscreen)
{
	ID3D11RenderTargetView *renderTarget = nullptr;
	ID3D11DepthStencilView *depthStencil = nullptr;
	unsigned int flags;
	HRESULT hr;

	flags = s_allowTearing && syncInterval == 0 && !fullscreen ? DXGI_PRESENT_ALLOW_TEARING : 0u;
	if (s_flipModel)
		ComCall<void>(dx.immediateContext, CTX_OMGetRenderTargets, 1u, &renderTarget, &depthStencil);
	hr = ComCall<HRESULT>(swapChain, SWAPCHAIN_Present, syncInterval, flags);
	if (s_flipModel)
	{
		ComCall<void>(dx.immediateContext, CTX_OMSetRenderTargets, 1u, (ID3D11RenderTargetView *const *)&renderTarget,
		              depthStencil);
		if (renderTarget)
			ComCall<unsigned long>(renderTarget, UNK_Release);
		if (depthStencil)
			ComCall<unsigned long>(depthStencil, UNK_Release);
	}
	return hr;
}

// src: Store 140675C50 RB_SwapBuffers. Enhanced: with tearing allowed and r_vsync 0, the windowed present tears (for an
// uncapped or VRR display; fullscreen tears with sync interval 0 anyway). A flip-model present unbinds the back buffer,
// so whatever render targets were bound before it are bound again after it: the renderer's state cache still believes
// they are.
void RB_SwapBuffers()
{
	int syncInterval;
	HRESULT hr;
	HRESULT removedReason;
	int fullscreen;
	const char *reason;
	ID3D11Query *fence;

	syncInterval = r_vsync->current.integer;
	if (syncInterval >= 4)
		syncInterval = 4;
	if (syncInterval <= 0)
		syncInterval = 0;
	R_LockImmediateContext();
	if (unk_14A37D568)
	{
		sub_1406967E0(dx.immediateContext, unk_14B07F658);
	}
	else if (sub_1406968F0())
	{
		sub_140696900(dx.immediateContext, unk_14B07F658);
	}
	else
	{
		hr = 0;
		ComCall<HRESULT>(dx.windows[(unsigned short)dx.targetWindowIndex].swapChain, SWAPCHAIN_GetFullscreenState,
		                 &fullscreen, (IDXGIOutput **)nullptr);
		if (!unk_149D62D6C && (r_displayMode->current.integer == GFX_DISPLAY_MODE_FULLSCREEN) == fullscreen)
		{
			hr = R_Present(dx.windows[dx.targetWindowIndex].swapChain, (unsigned int)syncInterval, fullscreen);
		}
		else
		{
			PostMessageA(dx.windows[dx.targetWindowIndex].hwnd, WM_USER, dx.targetWindowIndex, syncInterval);
			unk_149D62D6C = 0;
		}
		if (hr < 0)
		{
			if (hr == DXGI_ERROR_DEVICE_REMOVED && dx.d3d11device)
			{
				removedReason = ComCall<HRESULT>(dx.d3d11device, DEV_GetDeviceRemovedReason);
				if (removedReason == (HRESULT)0x887A0001)
					reason = "DXGI_ERROR_INVALID_CALL";
				else if (removedReason == hr)
					reason = "DXGI_ERROR_DEVICE_REMOVED";
				else if (removedReason == (HRESULT)0x887A0006)
					reason = "DXGI_ERROR_DEVICE_HUNG";
				else if (removedReason == (HRESULT)0x887A0007)
					reason = "DXGI_ERROR_DEVICE_RESET";
				else if (removedReason == (HRESULT)0x887A0020)
					reason = "DXGI_ERROR_DRIVER_INTERNAL_ERROR";
				else
					reason = "Unknown";
				Com_Error(ERR_FATAL, "Direct3DDevice::Present failed (DEVICE REMOVED) : %s (%d)\n", reason,
				          DXGI_ERROR_DEVICE_REMOVED);
			}
			else
			{
				Com_Error(ERR_FATAL, "Direct3DDevice::Present failed: %s\n", R_ErrorDescription(hr));
			}
		}
	}
	// the lock again, keeping the loading screen alive while the main thread waits for it
	if (Sys_IsMainThread())
	{
		while (WaitForSingleObject(dx.immediateContextMutex, 1) == WAIT_TIMEOUT)
			Sys_LoadingKeepAlive();
	}
	else
	{
		WaitForSingleObject(dx.immediateContextMutex, 0xFFFFFFFF);
	}
	if (dx.immediateContextLockCount == 0)
		dx.immediateContextThreadId = GetCurrentThreadId();
	++dx.immediateContextLockCount;
	unk_14A385398 = dx.fencePool[dx.nextFence];
	dx.nextFence = (dx.nextFence + 1) & 31;
	do
	{
		fence = unk_14A385398;
		ComCall<unsigned int>(fence, ASYNC_GetDataSize);
	} while (ComCall<HRESULT>(dx.immediateContext, CTX_GetData, fence, (void *)nullptr, 0u, 0u) == 1);
	ComCall<void>(dx.immediateContext, CTX_End, unk_14A385398);
	R_UnlockImmediateContext();
	sub_14062EC80(unk_14A385398);
	R_UnlockImmediateContext();
	*unk_14A107B60 = 0;
}
