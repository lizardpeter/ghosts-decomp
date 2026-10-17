// gfx_d3d/r_init.cpp (Store build): the Direct3D 11 device, its swap chain and the game window.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names come
// from the PS4 server PDB (iw6_ds_ps4: R_CheckLostDevice, R_RecoverLostDevice, R_ResetDevice, R_Shutdown, with
// their callees), else from Black Ops' D3D9 r_init.cpp (lineage), else sub_<VA>. The Store build inlines a lot:
// R_ResetDevice into R_RecoverLostDevice, R_ChooseMonitor into R_ChooseAdapter, R_CreateWindow and R_InitHardware
// into R_CreateGameWindow, R_ShutdownDirect3D into R_Shutdown.
//
// Device life cycle: R_InitGraphicsApi creates the DXGI factory and picks the adapter and output (R_ChooseAdapter),
// lists the output's display modes (R_EnumDisplayModes), derives the window parameters from the dvars
// (R_SetWndParms) and creates the window, the device and the swap chain (R_CreateGameWindow -> R_CreateDevice).
// A lost device (deviceLost) is recovered on the main thread by R_CheckLostDevice -> R_RecoverLostDevice, which
// releases everything that depends on the swap chain and creates a new swap chain on the same device.

#include <windows.h>

#include <iw6_static.h>

#include "client/client.h"
#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"
#include "gfx_d3d/r_init.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "gfx_d3d/r_init.cpp"

// File statics (PS4 PDB names): the swap frame counters and the swap fences
IW6_STATIC volatile long g_frontEndSwapFrame IW6_AT("", "g_frontEndSwapFrame");
IW6_STATIC volatile int g_gpuSubmitSwapFrame IW6_AT("", "g_gpuSubmitSwapFrame");
IW6_STATIC ID3D11Query *g_gpuSwapFence[8] IW6_AT("", "g_gpuSwapFence");

// ---- Win32 (imports of the Store build) ----
typedef struct HMONITOR__ *HMONITOR;
typedef struct HDC__ *HDC;

struct MONITORINFO
{
	unsigned int cbSize;
	RECT rcMonitor;
	RECT rcWork;
	unsigned int dwFlags;
};

#define MONITOR_DEFAULTTOPRIMARY 1
#define MONITOR_DEFAULTTONEAREST 2
#define SPI_GETWORKAREA 0x30
#define SM_CXSCREEN 0
#define SM_CYSCREEN 1
#define SM_REMOTESESSION 0x1000

#define DXGI_ERROR_NOT_CURRENTLY_AVAILABLE ((HRESULT)0x887A0022)
#define DXGI_MODE_SCANLINE_ORDER_PROGRESSIVE 1
#define DXGI_MODE_SCALING_CENTERED 1

extern "C" {
typedef BOOL (*MONITORENUMPROC)(HMONITOR, HDC, RECT *, LPARAM);
BOOL EnumDisplayMonitors(HDC hdc, const RECT *lprcClip, MONITORENUMPROC lpfnEnum, LPARAM dwData);
HMONITOR MonitorFromPoint(POINT pt, unsigned int dwFlags);
BOOL GetMonitorInfoA(HMONITOR hMonitor, MONITORINFO *lpmi);
BOOL SystemParametersInfoA(unsigned int uiAction, unsigned int uiParam, void *pvParam, unsigned int fWinIni);
int GetSystemMetrics(int nIndex);
void *CreateMutexA(void *lpMutexAttributes, BOOL bInitialOwner, const char *lpName);
// CRT: qsort is imported; sscanf and sprintf are the UCRT's inline wrappers compiled into the exe
void qsort(void *base, unsigned long long num, unsigned long long width, int (*compare)(const void *, const void *));
int sscanf(const char *buffer, const char *format, ...);
int sprintf(char *buffer, const char *format, ...);
void *memset(void *dst, int value, unsigned long long n);
double floor(double x);
const char *va(const char *format, ...);
}

// ---- elsewhere in the game ----
extern const dvar_t *r_displayMode;     // 0 = fullscreen, 1 = windowed without border, 2 = windowed
extern const dvar_t *r_monitor;         // "Index of the monitor to use in a multi monitor system"
extern const dvar_t *vid_xpos;
extern const dvar_t *vid_ypos;
extern const dvar_t *r_rendererInUse;
extern const dvar_t *r_amdGPU;
extern const dvar_t *r_multiGPU;
extern const dvar_t *r_mode;
extern const dvar_t *r_displayRefresh;

extern int unk_14A346B40;  // a resolution index R_EnumDisplayModes takes as r_mode's default (name unknown)

void Dvar_SetBool(const dvar_t *dvar, bool value);
const dvar_t *Dvar_RegisterEnum(const char *dvarName, const char *const valueList[], int defaultIndex,
                                unsigned int flags, const char *description);
void Sys_DirectXFatalError();
bool Sys_IsMainThread();
bool R_IsReallyNvidiaGPU();                       // gfx_d3d/r_dvars.cpp
int sub_140623E30(GfxAAMode aaMode);              // gfx_d3d/r_dvars.cpp?: the MSAA sample count of an r_aaMode
void sub_1401B0030();                             // clears dx+0x7D70 (name unknown)
bool sub_140631850(IDXGIAdapter *adapter);        // AMD CrossFire: more than one GPU behind the adapter (AGS)
void R_WaitFrontendWorkerCmds();
void R_UnlockSkinnedCache();
int R_PopRemoteScreenUpdate();
void R_SyncRenderThread();
void R_PushRemoteScreenUpdate(int remoteScreenUpdateNesting);
struct GfxCmdBufPrimState;
void R_ClearAllStreamSources(GfxCmdBufPrimState *primState);
struct GfxCmdBufState;
extern GfxCmdBufState gfxCmdBufState;             // its primitive state (prim) comes first

struct NV_GET_CURRENT_SLI_STATE
{
	unsigned int version;
	unsigned int maxNumAFRGroups;
	unsigned int numAFRGroups;
	// the rest is not read
};
extern "C" int NvAPI_D3D_GetCurrentSLIState(void *pDevice, NV_GET_CURRENT_SLI_STATE *pSliState);

extern bool unk_14A37D580;  // set when the device is created (name unknown)
#define WAIT_TIMEOUT 0x102
#define WM_USER 0x0400
#define SW_SHOW 5

extern "C" {
BOOL IsWindow(HWND hWnd);
BOOL DestroyWindow(HWND hWnd);
BOOL CloseHandle(void *hObject);
BOOL AdjustWindowRectEx(RECT *lpRect, unsigned int dwStyle, BOOL bMenu, unsigned int dwExStyle);
HINSTANCE GetModuleHandleA(const char *lpModuleName);
HWND CreateWindowExA(unsigned int dwExStyle, const char *lpClassName, const char *lpWindowName, unsigned int dwStyle,
                     int X, int Y, int nWidth, int nHeight, HWND hWndParent, void *hMenu, HINSTANCE hInstance,
                     void *lpParam);
BOOL ShowWindow(HWND hWnd, int nCmdShow);
long _InterlockedCompareExchange(long volatile *destination, long exchange, long comparand);
}

// R_RecoverLostDevice and R_ResetDevice (callees as in the PS4 server's)
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
void R_AcquireGpuFenceLock();
void R_FinishGpuFence();
void R_InsertGpuFence();
void R_ReleaseGpuFenceLock();

struct GfxCmdBufSourceState;
struct GfxCmdBufInput;
struct GfxCmdBufContext
{
	GfxCmdBufSourceState *source;
	GfxCmdBufState *state;
};
extern GfxCmdBufSourceState gfxCmdBufSourceState;
extern GfxCmdBufInput gfxCmdBufInput;
extern const GfxCmdBufContext gfxCmdBufContext;  // {&gfxCmdBufSourceState, &gfxCmdBufState}
void R_InitCmdBufSourceState(GfxCmdBufSourceState *source, const GfxCmdBufInput *input, unsigned int cameraView);
void R_InitCmdBufState(GfxCmdBufState *state);
void RB_InitSceneViewport();
void R_SetRenderTargetSize(GfxCmdBufSourceState *source, GfxRenderTargetId newTargetId);
void R_SetRenderTarget(GfxCmdBufContext context, GfxRenderTargetId newTargetId);

extern unsigned int unk_14A37CD6C;  // passed where the PS4's R_ResetDevice passes rg.frontEndFrameCount
extern volatile long g_gpuSwapFrame;
extern bool g_allocateMinimalResources;

struct GfxAssets
{
	ID3D11Query *pixelCountQuery;
};
extern GfxAssets gfxAssets;

// R_CreateForInitOrReset: D3D11_BUFFER_DESC is in gfx_d3d/r_dxgi.h
struct D3D11_SUBRESOURCE_DATA;
struct D3D11_QUERY_DESC
{
	int Query;
	unsigned int MiscFlags;
};
#define D3D11_QUERY_EVENT 0
#define D3D11_QUERY_OCCLUSION 1
HRESULT R_CreateBufferInternal(const D3D11_BUFFER_DESC *desc, const D3D11_SUBRESOURCE_DATA *initialData,
                               ID3D11Buffer **buffer);
void R_BuildSubDomainRangeConstantBuffers();
void R_SetupPrecompiledConstantBuffer();
void R_InitDefaultDepthImage();
void R_InitDaltonize();
void sub_14068EAE0();  // the matcher's R_InitRandomRotationTexture(GfxImage *); the Store's takes no argument
void sub_1401B6130();
void sub_140640510();
void sub_1406310F0();
void sub_1406508E0();
void sub_14068C300();
void sub_14063EBD0();
void sub_1401B1400();
void R_CreateDynamicBuffers();
void R_CreateParticleCloudBuffer();
void sub_14068BC80();
void sub_14068D600();
void sub_1401AAEF0();
void sub_1401AB1C0();

// R_CreateGameWindow
extern const dvar_t *com_wideScreen;              // "wideScreen"
extern const dvar_t *r_smp_worker_thread[9];
void Dvar_ClearModified(const dvar_t *dvar);
void sub_14046F6D0(unsigned int thread);          // resumes thread `thread` (ResumeThread)
void sub_140673FE0();
void sub_140631540();
void sub_1406038A0();
void sub_14068F530();
void sub_140655D70();
void sub_14062C100();
void sub_14063B250();
void sub_14066A360();
void sub_140634CD0();
void sub_1406294D0();
void sub_1406466E0();
void sub_140550190();
void sub_140632660();                             // this file

// R_InitRenderBuffers (Store layouts: GfxVertexBufferState is 0x30 bytes, the servers' 0x18)
struct GfxVertexBufferState
{
	unsigned char opaque[0x30];
};

struct GfxMeshData
{
	unsigned int indexCount;
	unsigned int totalIndexCount;
	ID3D11Buffer *ib;
	unsigned short *indices;
	GfxVertexBufferState vb;
	unsigned int vertSize;
};

struct GfxQuadMeshData
{
	float x;
	float y;
	float width;
	float height;
	GfxMeshData meshData;
};

struct GfxMeshGlobals
{
	GfxQuadMeshData fullSceneViewMesh[6];
	GfxQuadMeshData spotShadowViewMeshSmall;
	GfxQuadMeshData spotShadowViewMeshLarge;
	GfxMeshData spotShadowBatchedQuadMesh[6][4];
	GfxMeshData sunShadowBatchedQuadMesh[6][2][9];
	GfxQuadMeshData sunShadowCacheQuadMesh[6][2][9];
};

// A compute command buffer (name unknown): sub_1401ACD10 sets it up
struct GfxComputeCmdBuf
{
	void *data;
	unsigned int size;
	unsigned int used;
	unsigned int unk10;
};

// The part of each of the two back-end data sets that R_InitRenderBuffers sets up (names unknown; the servers'
// GfxBackEndData has mesh[6] the same way)
struct GfxBackEndDynamicData
{
	GfxMeshData mesh[6];                        // 0x000
	char unk_1E0[0x370 - 0x1E0];
	GfxComputeCmdBuf computeCmdBuf;             // 0x370
	char unk_388[0x390 - 0x388];
	ID3D11DeviceContext *computeContext;        // 0x390
	char unk_398[0x550 - 0x398];
	struct
	{
		ID3D11DeviceContext *context;
		char unk_08[0x10];
	} workerContexts[65];                       // 0x550: deferred contexts
	char unk_B68[0x645080 - 0xB68];
};

// The flare surface lists (name unknown; the servers have s_flareSurfList[1].flareMesh)
struct GfxFlareSurfList
{
	GfxMeshData flareMesh;
	char unk_50[0x4858 - 0x50];
};

extern GfxMeshGlobals gfxMeshGlob;
extern GfxBackEndDynamicData unk_14A4FEAE0[2];
extern GfxFlareSurfList unk_14B076500[2];
void *R_AllocDynamicIndexBuffer(ID3D11Buffer **ib, int sizeInBytes, const char *name);
void R_InitDynamicVertexBufferState(GfxVertexBufferState *vb, int bytes, bool dynamic);
void R_AssignNullBuffer(ID3D11Buffer **buffer);
void R_SetQuadMesh(GfxQuadMeshData *quadMesh, float x, float y, float width, float height, float s0, float t0,
                   float s1, float t1, unsigned int color);
void R_InitBatchedQuadMesh(GfxMeshData *mesh, int quadCount);
void *sub_14066A480(unsigned int size, const char *name);  // jumps to Z_VirtualAllocInternal(size)
void sub_1401ACD10(GfxComputeCmdBuf *cmdBuf, void *data, unsigned int size);

// R_ReleaseForShutdownOrReset
HRESULT R_ReleaseBuffer(ID3D11Buffer *buffer);
void R_ShutdownSubDomainRangeConstantBuffers();
void sub_1401B0000(ID3D11Buffer *buffer);        // takes the buffer's size off the tracked buffer memory
void sub_1401B7160();
void sub_140640830();
void sub_140632700(unsigned char zoneIndex);     // releases a zone's depth-stencil and blend states (the PS4's R_ShutdownZoneState?)
void sub_1401AB230();
void sub_1406513F0();
void sub_14063F200();
void sub_1401B1390();
void sub_14062C5C0();
void sub_1401A9990();
void sub_14068F3B0();
void sub_1401B7F00();
void R_DestroyDynamicBuffers();
void R_DestroyParticleCloudBuffer();
void sub_14064D450();
void sub_14068DB60();
void sub_14068C170();
void sub_140663EA0();
void sub_140663EB0();
void sub_140663D60();

// R_Shutdown
enum DBSyncMode : int
{
	DB_LOAD_ASYNC_FORCE_FREE = 3,
};
struct XZoneInfo
{
	const char *name;
	int allocFlags;
	int freeFlags;
};
extern const dvar_t *r_nvidiaGPU;
extern const dvar_t *r_nvidiaGPUCount;
extern bool unk_14A37D581;
extern void *unk_14A34B558;
extern unsigned long long unk_14A37D5B8[3];
extern int unk_14A346A94;
extern unsigned long long unk_14A37D5D0[2];
extern unsigned long long unk_14B89E280[8];
void DB_LoadXAssets(XZoneInfo *zoneInfo, unsigned int zoneCount, DBSyncMode syncMode);
void DB_ShutdownXAssets();
void sub_1401AAE90();
void sub_140683F70();
void sub_140634FC0();
void sub_140600CB0(int isRestart);
void sub_14063ECE0();
void sub_1406652E0();
void sub_140316750();
void sub_14018F210();
void sub_140460B90();
void sub_140603D50();
void sub_14064D7E0();
void sub_14062EB40();
void sub_140605130();

// RB_SwapBuffers
struct ID3D11RenderTargetView;
extern const dvar_t *r_vsync;
extern int unk_14A37D568;
extern ID3D11RenderTargetView *unk_14B07F658;  // the frame buffer's render target view (set by 14064F420)
extern int unk_149D62D6C;                       // set by the window procedure on WM_ACTIVATE/WM_ACTIVATEAPP
extern ID3D11Query *unk_14A385398;              // the swap fence of the frame
extern int *unk_14A107B60;
bool sub_1406968F0();
void sub_1406967E0(ID3D11DeviceContext *context, ID3D11RenderTargetView *view);
void sub_140696900(ID3D11DeviceContext *context, ID3D11RenderTargetView *view);
void Sys_LoadingKeepAlive();

// R_ErrorDescription, R_ComErrorCleanup
extern "C" {
unsigned int FormatMessageA(unsigned int dwFlags, const void *lpSource, unsigned int dwMessageId,
                            unsigned int dwLanguageId, char *lpBuffer, unsigned int nSize, void *Arguments);
void *LocalFree(void *hMem);
}
#define FORMAT_MESSAGE_ALLOCATE_BUFFER 0x100
#define FORMAT_MESSAGE_IGNORE_INSERTS 0x200
#define FORMAT_MESSAGE_FROM_SYSTEM 0x1000
#define MAKELANGID(primary, sub) (((sub) << 10) | (primary))
#define LANG_NEUTRAL 0
#define SUBLANG_DEFAULT 1
void I_strncpyz(char *dest, const char *src, int destsize);
int Com_sprintf(char *dest, int size, const char *fmt, ...);
struct GfxBackEndData;
extern GfxBackEndData *frontEndDataOut;
void CG_HudLighting_ComErrorCleanup();
void RB_SetUploadShaderFastMode(int fastMode);
void R_AbortRenderCommands();

// ---- this file ----

// Store 140631810 (lineage: Black Ops' R_MonitorEnumCallback, r_init.cpp:1676): finds the monitor of a given index
struct GfxMonitorByIndex
{
	int index;
	HMONITOR monitor;
};

BOOL R_MonitorEnumCallback(HMONITOR monitorHandle, HDC hdc, RECT *rect, LPARAM userData)
{
	GfxMonitorByIndex *enumData = (GfxMonitorByIndex *)userData;

	if (!enumData->index)
	{
		enumData->monitor = monitorHandle;
		return 0;
	}
	--enumData->index;
	return 1;
}

// Store 140631830 (name unknown): counts the monitors before a given one
BOOL sub_140631830(HMONITOR monitorHandle, HDC hdc, RECT *rect, LPARAM userData)
{
	GfxMonitorByIndex *enumData = (GfxMonitorByIndex *)userData;

	if (enumData->monitor == monitorHandle)
		return 0;
	++enumData->index;
	return 1;
}

// Store 14062EEF0 (lineage: Black Ops' R_ChooseAdapter with R_ChooseMonitor, r_init.cpp:1690-1713). Creates the
// DXGI factory, then picks the monitor: in fullscreen the r_monitor'th one, else (or when there is no such monitor)
// the one at vid_xpos/vid_ypos, after moving the window into the work area. The adapter is the first one with an
// output on that monitor; failing that, the first adapter that supports feature level 11_0, with its first output.
void R_ChooseAdapter()
{
	bool foundAdapter;
	IDXGIAdapter *adapter;
	IDXGIOutput *output;
	HMONITOR monitor;
	unsigned int adapterIndex;
	unsigned int outputIndex;
	D3D_FEATURE_LEVEL featureLevel;
	DXGI_OUTPUT_DESC outputDesc;

	CreateDXGIFactory(IID_IDXGIFactory, (void **)&dx.dxgiFactory);
	foundAdapter = false;
	adapter = nullptr;
	dx.dxgiAdapter = nullptr;
	dx.adapterIndex = 0;
	dx.dxgiOutput = nullptr;
	monitor = nullptr;
	if (r_displayMode->current.integer == GFX_DISPLAY_MODE_FULLSCREEN)
	{
		GfxMonitorByIndex enumData;
		enumData.index = r_monitor->current.integer;
		enumData.monitor = nullptr;
		EnumDisplayMonitors(nullptr, nullptr, R_MonitorEnumCallback, (LPARAM)&enumData);
		monitor = enumData.monitor;
	}
	if (!monitor)
	{
		POINT pos;
		POINT corner;
		RECT workArea;
		MONITORINFO mi;
		bool moved;

		pos.x = Dvar_GetInt("vid_xpos");
		pos.y = Dvar_GetInt("vid_ypos");
		corner.x = pos.x + 32;
		corner.y = pos.y + 32;
		monitor = MonitorFromPoint(corner, MONITOR_DEFAULTTONEAREST);
		mi.cbSize = sizeof(mi);
		mi.rcMonitor.left = 0;
		mi.rcMonitor.top = 0;
		mi.rcMonitor.right = 0;
		mi.rcMonitor.bottom = 0;
		mi.rcWork.left = 0;
		mi.rcWork.top = 0;
		mi.rcWork.right = 0;
		mi.rcWork.bottom = 0;
		mi.dwFlags = 0;
		if (monitor && GetMonitorInfoA(monitor, &mi))
			workArea = mi.rcWork;
		else
			SystemParametersInfoA(SPI_GETWORKAREA, 0, &workArea, 0);
		moved = false;
		if (pos.x < workArea.left)
		{
			moved = true;
			pos.x = workArea.left;
		}
		if (pos.y < workArea.top)
		{
			moved = true;
			pos.y = workArea.top;
		}
		if (pos.x + 32 > workArea.right || pos.y + 32 > workArea.bottom)
		{
			pos.x = workArea.left;
			pos.y = workArea.top;
			moved = true;
		}
		if (moved)
		{
			Dvar_SetInt(vid_xpos, pos.x);
			Dvar_SetInt(vid_ypos, pos.y);
		}
		GfxMonitorByIndex findData;
		findData.monitor = MonitorFromPoint(pos, MONITOR_DEFAULTTOPRIMARY);
		findData.index = 0;
		EnumDisplayMonitors(nullptr, nullptr, sub_140631830, (LPARAM)&findData);
		Dvar_SetInt(r_monitor, findData.index);
		monitor = MonitorFromPoint(pos, MONITOR_DEFAULTTOPRIMARY);
	}
	adapterIndex = 0;
	if (ComCall<HRESULT>(dx.dxgiFactory, FACTORY_EnumAdapters, 0u, &adapter) != DXGI_ERROR_NOT_FOUND)
	{
		do
		{
			if (D3D11CreateDevice(adapter, D3D_DRIVER_TYPE_UNKNOWN, nullptr,
			                      D3D11_CREATE_DEVICE_PREVENT_ALTERING_LAYER_SETTINGS_FROM_REGISTRY, nullptr, 0,
			                      D3D11_SDK_VERSION, nullptr, &featureLevel, nullptr) >= 0)
			{
				if (featureLevel >= D3D_FEATURE_LEVEL_11_0)
				{
					if (!dx.dxgiAdapter)
					{
						foundAdapter = true;
						dx.dxgiAdapter = adapter;
						dx.adapterIndex = adapterIndex;
					}
					output = nullptr;
					outputIndex = 0;
					if (ComCall<HRESULT>(adapter, ADAPTER_EnumOutputs, 0u, &output) != DXGI_ERROR_NOT_FOUND)
					{
						do
						{
							if (!dx.dxgiOutput)
								dx.dxgiOutput = output;
							ComCall<HRESULT>(output, OUTPUT_GetDesc, &outputDesc);
							if (outputDesc.Monitor == monitor)
							{
								if (dx.dxgiOutput != output)
									ComCall<unsigned int>(dx.dxgiOutput, UNK_Release);
								if (dx.dxgiAdapter != adapter)
									ComCall<unsigned int>(dx.dxgiAdapter, UNK_Release);
								dx.dxgiAdapter = adapter;
								dx.dxgiOutput = output;
								dx.adapterIndex = adapterIndex;
								return;
							}
							if (dx.dxgiOutput != output)
								ComCall<unsigned int>(output, UNK_Release);
							++outputIndex;
						} while (ComCall<HRESULT>(adapter, ADAPTER_EnumOutputs, outputIndex, &output) !=
						         DXGI_ERROR_NOT_FOUND);
					}
					if (dx.dxgiAdapter != adapter)
						ComCall<unsigned int>(adapter, UNK_Release);
				}
				else
				{
					ComCall<unsigned int>(adapter, UNK_Release);
				}
			}
			++adapterIndex;
		} while (ComCall<HRESULT>(dx.dxgiFactory, FACTORY_EnumAdapters, adapterIndex, &adapter) !=
		         DXGI_ERROR_NOT_FOUND);
		if (foundAdapter)
			return;
	}
	Sys_DirectXFatalError();
}

// Store 14062F340 (lineage: Black Ops' R_CompareDisplayModes, r_init.cpp:1439): qsort order of the display modes,
// by size, then refresh rate (compared as fractions)
int R_CompareDisplayModes(const void *e0, const void *e1)
{
	const DXGI_MODE_DESC *mode0 = (const DXGI_MODE_DESC *)e0;
	const DXGI_MODE_DESC *mode1 = (const DXGI_MODE_DESC *)e1;
	int delta;
	unsigned int rate0;
	unsigned int rate1;

	delta = (int)(mode0->Width - mode1->Width);
	if (delta)
		return delta;
	delta = (int)(mode0->Height - mode1->Height);
	if (delta)
		return delta;
	rate0 = mode0->RefreshRate.Numerator * mode1->RefreshRate.Denominator;
	rate1 = mode1->RefreshRate.Numerator * mode0->RefreshRate.Denominator;
	if (rate0 > rate1)
		return 1;
	return rate0 < rate1 ? -1 : 0;
}

// Store 14062F380 (lineage: Black Ops' R_CompareRefreshRates, r_init.cpp:1477)
int R_CompareRefreshRates(const void *e0, const void *e1)
{
	return *(const int *)e0 - *(const int *)e1;
}

// Store 14062FC90 (lineage: Black Ops' R_EnumDisplayModes, r_init.cpp:1501, with R_GetMonitorDimensions,
// R_AddValidResolution and R_AddValidRefreshRate inlined). Takes the output's desktop size as the native size, lists
// its R8G8B8A8 display modes, and registers r_mode and r_displayRefresh with their names ("<w>x<h>", "<n> Hz").
void R_EnumDisplayModes()
{
	DXGI_OUTPUT_DESC outputDesc;
	bool nativeIsValid;
	unsigned int modeCount;
	unsigned int modeIndex;
	int resolutionCount;
	int refreshRateCount;
	int availableResolutions[257][2];
	int availableRefreshRates[256];
	int refreshRate;
	int rateIndex;
	int resolutionIndex;
	int defaultResolutionIndex;
	int refreshRateIndex;
	int defaultRefreshRateIndex;
	char *modeText;

	nativeIsValid = true;
	if (ComCall<HRESULT>(dx.dxgiOutput, OUTPUT_GetDesc, &outputDesc) == 0)
	{
		dx.adapterNativeWidth = outputDesc.DesktopCoordinates[2] - outputDesc.DesktopCoordinates[0];
		dx.adapterNativeHeight = outputDesc.DesktopCoordinates[3] - outputDesc.DesktopCoordinates[1];
	}
	else
	{
		dx.adapterNativeWidth = GetSystemMetrics(SM_CXSCREEN);
		dx.adapterNativeHeight = GetSystemMetrics(SM_CYSCREEN);
		nativeIsValid = dx.adapterNativeWidth > 0 && dx.adapterNativeHeight > 0;
	}
	dx.adapterNativeIsValid = nativeIsValid;
	if (ComCall<HRESULT>(dx.dxgiOutput, OUTPUT_GetDisplayModeList, DXGI_FORMAT_R8G8B8A8_UNORM, 0u,
	                     &dx.displayModeCount, (DXGI_MODE_DESC *)nullptr) == DXGI_ERROR_NOT_CURRENTLY_AVAILABLE
	    && GetSystemMetrics(SM_REMOTESESSION))
	{
		// a remote desktop session lists no modes: 800x600 at 60 Hz
		dx.displayModeCount = 1;
		dx.displayModes[0].Width = 800;
		dx.displayModes[0].Height = 600;
		dx.displayModes[0].Format = DXGI_FORMAT_R8G8B8A8_UNORM;
		dx.displayModes[0].RefreshRate.Numerator = 60;
		dx.displayModes[0].RefreshRate.Denominator = 1;
		dx.displayModes[0].ScanlineOrdering = DXGI_MODE_SCANLINE_ORDER_PROGRESSIVE;
		dx.displayModes[0].Scaling = DXGI_MODE_SCALING_CENTERED;
		modeCount = 1;
	}
	else
	{
		// the count of the first call is taken as the array's capacity: more than 256 modes overflow displayModes
		ComCall<HRESULT>(dx.dxgiOutput, OUTPUT_GetDisplayModeList, DXGI_FORMAT_R8G8B8A8_UNORM, 0u,
		                 &dx.displayModeCount, dx.displayModes);
		modeCount = dx.displayModeCount;
	}
	qsort(dx.displayModes, modeCount, sizeof(dx.displayModes[0]), R_CompareDisplayModes);
	resolutionCount = 0;
	refreshRateCount = 0;
	for (modeIndex = 0; modeIndex < dx.displayModeCount; ++modeIndex)
	{
		const DXGI_MODE_DESC *mode = &dx.displayModes[modeIndex];
		if ((resolutionCount <= 0 || availableResolutions[resolutionCount - 1][0] != (int)mode->Width
		     || availableResolutions[resolutionCount - 1][1] != (int)mode->Height)
		    && (int)mode->Width >= 640 && (int)mode->Height >= 480)
		{
			availableResolutions[resolutionCount][0] = mode->Width;
			availableResolutions[resolutionCount][1] = mode->Height;
			++resolutionCount;
		}
		// rounded to the nearest Hz; a zero denominator divides by zero
		refreshRate = (int)((mode->RefreshRate.Numerator * 2 + mode->RefreshRate.Denominator)
		                    / (mode->RefreshRate.Denominator * 2));
		for (rateIndex = 0; rateIndex < refreshRateCount; ++rateIndex)
		{
			if (availableRefreshRates[rateIndex] == refreshRate)
				break;
		}
		if (rateIndex == refreshRateCount)
		{
			for (rateIndex = refreshRateCount; rateIndex > 0; --rateIndex)
			{
				if (availableRefreshRates[rateIndex - 1] <= refreshRate)
					break;
				availableRefreshRates[rateIndex] = availableRefreshRates[rateIndex - 1];
			}
			availableRefreshRates[rateIndex] = refreshRate;
			++refreshRateCount;
		}
	}
	modeText = dx.modeText;
	if (!resolutionCount)
	{
		va("No valid resolutions of %i x %i or above found", 640, 480);  // the message is dropped
		Sys_DirectXFatalError();
	}
	memset(dx.resolutionNameTable, 0, sizeof(dx.resolutionNameTable) + sizeof(dx.refreshRateNameTable));
	defaultResolutionIndex = 0;
	for (resolutionIndex = 0; resolutionIndex < resolutionCount; ++resolutionIndex)
	{
		dx.resolutionNameTable[resolutionIndex] = modeText;
		modeText += sprintf(modeText, "%ix%i", availableResolutions[resolutionIndex][0],
		                    availableResolutions[resolutionIndex][1]) + 1;
		if (availableResolutions[defaultResolutionIndex][0] < 800
		    || availableResolutions[defaultResolutionIndex][1] < 600 || resolutionIndex == unk_14A346B40)
			defaultResolutionIndex = resolutionIndex;
		if (nativeIsValid && availableResolutions[resolutionIndex][0] == dx.adapterNativeWidth
		    && availableResolutions[resolutionIndex][1] == dx.adapterNativeHeight)
			defaultResolutionIndex = resolutionIndex;
	}
	dx.resolutionNameTable[resolutionIndex] = nullptr;
	r_mode = Dvar_RegisterEnum("r_mode", dx.resolutionNameTable, defaultResolutionIndex, 0x4003,
	                           "Direct X resolution mode");
	qsort(availableRefreshRates, refreshRateCount, sizeof(availableRefreshRates[0]), R_CompareRefreshRates);
	defaultRefreshRateIndex = 0;
	for (refreshRateIndex = 0; refreshRateIndex < refreshRateCount; ++refreshRateIndex)
	{
		dx.refreshRateNameTable[refreshRateIndex] = modeText;
		modeText += sprintf(modeText, "%i Hz", availableRefreshRates[refreshRateIndex]) + 1;
		if (availableRefreshRates[defaultRefreshRateIndex] < 60)
			defaultRefreshRateIndex = refreshRateIndex;
	}
	dx.refreshRateNameTable[refreshRateIndex] = nullptr;
	r_displayRefresh = Dvar_RegisterEnum("r_displayRefresh", dx.refreshRateNameTable, defaultRefreshRateIndex,
	                                     0x4003, "Refresh rate");
}

// Store 140630670 (lineage: Black Ops' R_SetWndParms, r_init.cpp:2357, with R_StoreWindowSettings' aspect ratio
// choice): the window parameters from the renderer settings. A borderless window takes the monitor's native size
// and position (or becomes windowed when the native size is unknown); the aspect ratio is r_aspectRatio's, or
// "auto" from the size; the scene size comes from r_imageQuality, the spot shadow tile sizes from the scene width.
void R_SetWndParms(GfxWindowParms *wndParms, const GfxWindowInput *input)
{
	GfxDisplayMode displayMode;
	int x;
	int y;
	int displayWidth;
	int displayHeight;
	int width;
	int height;
	int ratio;
	float aspectRatio;
	int sceneWidth;
	int sceneHeight;
	unsigned short shadowTileResSmall;
	unsigned short shadowTileResLarge;
	bool letterbox4x3;
	GfxRefreshRate hz;
	int aaSamples;
	unsigned char omitRTFlags;

	displayMode = input->displayMode;
	x = input->x;
	y = input->y;
	if (displayMode == GFX_DISPLAY_MODE_WINDOWED_NO_BORDER && !dx.adapterNativeIsValid)
	{
		displayMode = GFX_DISPLAY_MODE_WINDOWED;
		sscanf(input->resolutionName, "%ix%i", &displayWidth, &displayHeight);
	}
	else if (displayMode != GFX_DISPLAY_MODE_WINDOWED_NO_BORDER)
	{
		sscanf(input->resolutionName, "%ix%i", &displayWidth, &displayHeight);
	}
	else
	{
		POINT pos;
		MONITORINFO mi;
		HMONITOR monitor;

		displayWidth = dx.adapterNativeWidth;
		displayHeight = dx.adapterNativeHeight;
		pos.x = input->x;
		pos.y = input->y;
		monitor = MonitorFromPoint(pos, MONITOR_DEFAULTTONEAREST);
		mi.cbSize = sizeof(mi);
		mi.rcMonitor.left = 0;
		mi.rcMonitor.top = 0;
		mi.rcMonitor.right = 0;
		mi.rcMonitor.bottom = 0;
		mi.rcWork.left = 0;
		mi.rcWork.top = 0;
		mi.rcWork.right = 0;
		mi.rcWork.bottom = 0;
		mi.dwFlags = 0;
		if (monitor && GetMonitorInfoA(monitor, &mi))
		{
			x = mi.rcMonitor.left;
			y = mi.rcMonitor.top;
		}
		else
		{
			x = 0;
			y = 0;
		}
	}
	switch (input->aspectRatio)
	{
	case GFX_ASPECT_RATIO_AUTO:
		if (displayMode != GFX_DISPLAY_MODE_WINDOWED && dx.adapterNativeIsValid)
		{
			width = dx.adapterNativeWidth;
			height = dx.adapterNativeHeight;
		}
		else
		{
			width = displayWidth;
			height = displayHeight;
		}
		ratio = (int)floor((float)height * 16.0f / (float)width + 0.5f);
		if (ratio == 10)
			aspectRatio = 1.6f;
		else if (ratio < 10)
			aspectRatio = 16.0f / 9.0f;
		else
			aspectRatio = 4.0f / 3.0f;
		break;
	case GFX_ASPECT_RATIO_STANDARD:
		aspectRatio = 4.0f / 3.0f;
		break;
	case GFX_ASPECT_RATIO_WIDE_16_10:
		aspectRatio = 1.6f;
		break;
	default:
		aspectRatio = 16.0f / 9.0f;
		break;
	}
	shadowTileResLarge = 0x400;
	shadowTileResSmall = 0x300;
	if (aspectRatio == 4.0f / 3.0f)
	{
		switch (input->imageQuality)
		{
		case GFX_IMAGE_QUALITY_NATIVE:
			sceneWidth = displayWidth;
			sceneHeight = displayHeight;
			break;
		case GFX_IMAGE_QUALITY_VERYLOW:
			sceneWidth = 640;
			sceneHeight = 480;
			break;
		case GFX_IMAGE_QUALITY_LOW:
			sceneWidth = 800;
			sceneHeight = 600;
			break;
		case GFX_IMAGE_QUALITY_NORMAL:
			sceneWidth = 1024;
			sceneHeight = 768;
			break;
		default:
			sceneWidth = 1280;
			sceneHeight = 960;
			break;
		}
	}
	else
	{
		switch (input->imageQuality)
		{
		case GFX_IMAGE_QUALITY_NATIVE:
			sceneWidth = displayWidth;
			sceneHeight = displayHeight;
			break;
		case GFX_IMAGE_QUALITY_VERYLOW:
			sceneWidth = 736;
			sceneHeight = 460;
			break;
		case GFX_IMAGE_QUALITY_LOW:
			sceneWidth = 896;
			sceneHeight = 544;
			break;
		case GFX_IMAGE_QUALITY_NORMAL:
			sceneWidth = 1152;
			sceneHeight = 720;
			break;
		default:
			sceneWidth = 1408;
			sceneHeight = 880;
			break;
		}
	}
	if (sceneWidth > displayWidth || sceneHeight > displayHeight)
	{
		sceneWidth = displayWidth;
		sceneHeight = displayHeight;
	}
	if (aspectRatio == 4.0f / 3.0f)
	{
		if (sceneWidth >= 1280)
		{
			shadowTileResSmall = 0x400;
			shadowTileResLarge = 0x800;
		}
		else if (sceneWidth >= 1024)
		{
			shadowTileResLarge = 0x600;
		}
		else
		{
			shadowTileResSmall = 0x200;
		}
	}
	else
	{
		if (sceneWidth >= 1408)
		{
			shadowTileResSmall = 0x400;
			shadowTileResLarge = 0x800;
		}
		else if (sceneWidth >= 1152)
		{
			shadowTileResLarge = 0x600;
		}
		else
		{
			shadowTileResSmall = 0x200;
		}
	}
	if (aspectRatio == 4.0f / 3.0f)
		letterbox4x3 = input->letterbox4x3;
	else
		letterbox4x3 = input->forceLetterbox4x3;
	if (letterbox4x3)
		aspectRatio = 16.0f / 9.0f;
	hz.Numerator = 60;
	hz.Denominator = 1;
	aaSamples = sub_140623E30(input->aaMode);
	omitRTFlags = 0;
	if (input->omitUnusedRenderTargets)
	{
		omitRTFlags = input->mbEnable ? 0 : 4;
		if (aaSamples != 1)
			omitRTFlags |= 1;
		omitRTFlags |= 2;
		// the original switches through a jump table over the seven modes without a range check: another value
		// jumps through whatever follows the table
		switch (input->aaMode)
		{
		case GFX_AA_MODE_SMAA:
			omitRTFlags &= ~2;
			break;
		default:
			break;
		}
	}
	wndParms->hz = hz;
	wndParms->x = x;
	wndParms->y = y;
	wndParms->displayMode = displayMode;
	wndParms->displayWidth = displayWidth;
	wndParms->aspectRatioWindow = aspectRatio;
	wndParms->sceneWidth = sceneWidth;
	wndParms->displayHeight = displayHeight;
	wndParms->hwnd = nullptr;
	wndParms->shadowTileResSmall = shadowTileResSmall;
	wndParms->shadowTileResLarge = shadowTileResLarge;
	wndParms->sceneHeight = sceneHeight;
	wndParms->omitRTFlags = omitRTFlags;
	wndParms->letterbox4x3 = letterbox4x3;
	wndParms->aaSamples = aaSamples;
}

// Black Ops' R_SetD3DPresentParameters (r_init.cpp:388), inlined in the Store build (R_CreateDevice, R_ResetDevice):
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

// Store 14062F420 (lineage: Black Ops' R_CreateDevice, r_init.cpp:2000, with R_CreateDeviceInternal): the device
// and immediate context on the chosen adapter, the MSAA sample count, and the swap chain of the window. Returns true
// even when D3D11CreateDevice or CreateSwapChain fail (their results are not checked).
bool R_CreateDevice(const GfxWindowParms *wndParms)
{
	D3D_FEATURE_LEVEL featureLevels[6] = {D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_1, D3D_FEATURE_LEVEL_10_0,
	                                      D3D_FEATURE_LEVEL_9_3, D3D_FEATURE_LEVEL_9_2, D3D_FEATURE_LEVEL_9_1};
	DXGI_ADAPTER_DESC adapterDesc;
	DXGI_ADAPTER_DESC vendorDesc;
	DXGI_SWAP_CHAIN_DESC swapChainDesc;
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
	R_SetD3DPresentParameters(&swapChainDesc, wndParms);
	ComCall<HRESULT>(dx.dxgiFactory, FACTORY_CreateSwapChain, dx.d3d11device, &swapChainDesc,
	                 &dx.windows[0].swapChain);
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

// Store 1406302F0 (PS4 PDB R_FlushSwap, gfx_d3d/r_init.cpp:3699): waits for the GPU (an event query through the
// flush fence), then counts every submitted swap as done
void R_FlushSwap()
{
	R_AcquireGpuFenceLock();
	R_FinishGpuFence();
	R_InsertGpuFence();
	R_FinishGpuFence();
	R_ReleaseGpuFenceLock();
	while (g_gpuSwapFrame != g_gpuSubmitSwapFrame)
		_InterlockedCompareExchange(&g_gpuSwapFrame, g_gpuSwapFrame + 1, g_gpuSwapFrame);
	g_gpuSubmitSwapFrame = g_frontEndSwapFrame;
	g_gpuSwapFrame = g_frontEndSwapFrame;
}

// Store 14062EC80 (name unknown): remembers the swap fence of a submitted frame
void sub_14062EC80(ID3D11Query *fence)
{
	g_gpuSwapFence[g_gpuSubmitSwapFrame & 7] = fence;
	++g_gpuSubmitSwapFrame;
}

// PS4 PDB R_ResetDevice (gfx_d3d/r_init.cpp:7393), inlined into R_RecoverLostDevice in the Store build: releases
// everything that depends on the swap chain, creates a new swap chain for the window on the same device and recreates
// the resources
static void R_ResetDevice()
{
	GfxWindowParms wndParms;
	DXGI_SWAP_CHAIN_DESC swapChainDesc;
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
	R_SetD3DPresentParameters(&swapChainDesc, &wndParms);
	R_ReleaseForShutdownOrReset(unk_14A37CD6C, 1);
	hr = ComCall<HRESULT>(dx.dxgiFactory, FACTORY_CreateSwapChain, dx.d3d11device, &swapChainDesc,
	                      &dx.windows[0].swapChain);
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

// Store 140631A80 (PS4 PDB R_RecoverLostDevice, gfx_d3d/r_init.cpp:7525)
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

// Store 14062F700 (lineage: Black Ops' R_CreateForInitOrReset, r_init.cpp:1265): the resources that depend on the
// device, created at start-up and again (reset != 0) after a lost device. Only the first creation makes the GPU
// fences (one flush fence and a ring of 32 swap fences) and the occlusion query.
bool R_CreateForInitOrReset(int reset)
{
	D3D11_BUFFER_DESC bufferDesc;
	ID3D11Buffer *buffer;
	D3D11_QUERY_DESC queryDesc;
	ID3D11Query *query;
	unsigned int fenceIndex;

	dx.constantBufferTables[0][0] = dx.defaultConstantBuffers[0];
	dx.constantBufferTables[1][0] = dx.defaultConstantBuffers[1];
	dx.constantBufferTables[2][0] = dx.defaultConstantBuffers[2];
	R_BuildSubDomainRangeConstantBuffers();
	sub_1401B6130();
	bufferDesc.ByteWidth = 0x2000;
	bufferDesc.Usage = D3D11_USAGE_DYNAMIC;
	bufferDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
	bufferDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	bufferDesc.MiscFlags = 0;
	bufferDesc.StructureByteStride = 0;
	R_CreateBufferInternal(&bufferDesc, nullptr, &buffer);
	dx.smodelWorldMatrixConstantBuffer = buffer;
	bufferDesc.ByteWidth = 0x800;
	bufferDesc.Usage = D3D11_USAGE_DYNAMIC;
	bufferDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
	bufferDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
	bufferDesc.MiscFlags = 0;
	bufferDesc.StructureByteStride = 0;
	R_CreateBufferInternal(&bufferDesc, nullptr, &buffer);
	dx.smodelLightingOrAmbientConstantBuffer = buffer;
	sub_140640510();
	sub_1406310F0();
	dx.depthStencilStateTables[0] = dx.defaultDepthStencilStates;
	dx.blendStateTables[0] = dx.defaultBlendStates;
	sub_1406508E0();
	sub_14068C300();
	if (!g_allocateMinimalResources)
	{
		R_InitRenderBuffers();
		if (!reset)
		{
			sub_14063EBD0();
			sub_1401B1400();
		}
	}
	R_CreateDynamicBuffers();
	R_SetupPrecompiledConstantBuffer();
	R_InitDefaultDepthImage();
	R_InitDaltonize();
	sub_14068EAE0();
	if (!g_allocateMinimalResources)
		R_CreateParticleCloudBuffer();
	dx.flushGpuFenceIssued = false;
	if (!reset)
	{
		queryDesc.Query = D3D11_QUERY_EVENT;
		queryDesc.MiscFlags = 0;
		if (ComCall<HRESULT>(dx.d3d11device, DEV_CreateQuery, &queryDesc, &dx.flushGpuFence) < 0)
			return false;
		dx.nextFence = 0;
		for (fenceIndex = 0; fenceIndex < 32; ++fenceIndex)
		{
			queryDesc.Query = D3D11_QUERY_EVENT;
			queryDesc.MiscFlags = 0;
			if (ComCall<HRESULT>(dx.d3d11device, DEV_CreateQuery, &queryDesc, &dx.fencePool[fenceIndex]) < 0)
				return false;
		}
	}
	if (!g_allocateMinimalResources && !reset)
	{
		sub_14068BC80();
		sub_14068D600();
		queryDesc.Query = D3D11_QUERY_OCCLUSION;
		queryDesc.MiscFlags = 0;
		if (ComCall<HRESULT>(dx.d3d11device, DEV_CreateQuery, &queryDesc, &query) < 0)
			query = nullptr;
		gfxAssets.pixelCountQuery = query;
		sub_1401AAEF0();
	}
	else
	{
		sub_1401AAEF0();
		if (reset)
			sub_1401AB1C0();
	}
	return true;
}

// Store 14062F930 (lineage: Black Ops' R_CreateGameWindow, r_init.cpp:2272, with R_CreateWindow, R_InitHardware and
// R_StoreWindowSettings inlined): the game window, the device, the renderer's resources, then shows the window.
// The window is created windowed (a borderless popup, or a captioned window); fullscreen is the swap chain's state.
bool R_CreateGameWindow(GfxWindowParms *wndParms)
{
	unsigned int style;
	RECT rc;
	HINSTANCE hinst;
	unsigned int threadIndex;

	style = wndParms->displayMode == GFX_DISPLAY_MODE_WINDOWED_NO_BORDER ? 0x96000000 : 0x00C80000;
	rc.left = 0;
	rc.top = 0;
	rc.right = wndParms->displayWidth;
	rc.bottom = wndParms->displayHeight;
	AdjustWindowRectEx(&rc, style, 0, 0);
	hinst = GetModuleHandleA(nullptr);
	wndParms->hwnd = CreateWindowExA(0, "IW6", "Call of Duty Ghosts Multiplayer", style, wndParms->x, wndParms->y,
	                                 rc.right - rc.left, rc.bottom - rc.top, nullptr, nullptr, hinst, nullptr);
	if (!wndParms->hwnd || !R_CreateDevice(wndParms))
		return false;
	vidConfig.sceneWidth = wndParms->sceneWidth;
	vidConfig.sceneHeight = wndParms->sceneHeight;
	vidConfig.displayWidth = wndParms->displayWidth;
	vidConfig.displayHeight = wndParms->displayHeight;
	vidConfig.omitRTFlags = wndParms->omitRTFlags;
	vidConfig.letterbox4x3 = wndParms->letterbox4x3;
	vidConfig.monitorWidth = wndParms->displayWidth;
	vidConfig.monitorHeight = wndParms->displayHeight;
	vidConfig.displayFrequency[0] = wndParms->hz.Numerator;
	vidConfig.displayFrequency[1] = wndParms->hz.Denominator;
	vidConfig.displayMode = wndParms->displayMode;
	vidConfig.windowAspectRatio = wndParms->aspectRatioWindow;
	vidConfig.displayAspectRatio = (float)wndParms->displayWidth / (float)wndParms->displayHeight;
	vidConfig.sceneAspectRatio = (float)wndParms->sceneWidth / (float)wndParms->sceneHeight;
	vidConfig.shadowTileResSmall = wndParms->shadowTileResSmall;
	vidConfig.shadowTileResLarge = wndParms->shadowTileResLarge;
	Dvar_SetBool(com_wideScreen, wndParms->aspectRatioWindow != 4.0f / 3.0f);
	vidConfig.aspectRatioScenePixel =
		(float)vidConfig.sceneHeight * vidConfig.windowAspectRatio / (float)vidConfig.sceneWidth;
	vidConfig.aspectRatioDisplayPixel =
		(float)vidConfig.displayHeight * vidConfig.windowAspectRatio / (float)vidConfig.displayWidth;
	RB_InitSceneViewport();
	sub_140673FE0();
	if (!R_CreateForInitOrReset(0))
		return false;
	sub_140631540();
	sub_1406038A0();
	sub_14068F530();
	sub_140655D70();
	sub_14062C100();
	sub_14063B250();
	sub_14066A360();
	sub_140634CD0();
	sub_1406294D0();
	sub_1406466E0();
	sub_1401AB1C0();
	dx.windows[dx.windowCount].hwnd = wndParms->hwnd;
	dx.windows[dx.windowCount].width = wndParms->displayWidth;
	dx.windows[dx.windowCount].height = wndParms->displayHeight;
	++dx.windowCount;
	for (threadIndex = 0; threadIndex < 8; ++threadIndex)
	{
		Dvar_ClearModified(r_smp_worker_thread[threadIndex]);
		if (r_smp_worker_thread[threadIndex]->current.enabled)
			sub_14046F6D0(threadIndex + 2);
	}
	ComCall<HRESULT>(dx.windows[0].swapChain, SWAPCHAIN_SetFullscreenState, 0, (IDXGIOutput *)nullptr);
	dx.targetWindowIndex = 0;
	ShowWindow(wndParms->hwnd, SW_SHOW);
	sub_140550190();
	return true;
}

// PS4 PDB R_InitDynamicMesh? (the name of the allocation, "R_InitDynamicMesh"), inlined: a mesh with dynamic index
// and vertex buffers
static void R_InitDynamicMesh(GfxMeshData *mesh, int indexCount, int vertexBytes, int vertSize)
{
	mesh->indices = (unsigned short *)R_AllocDynamicIndexBuffer(&mesh->ib, 2 * indexCount, "R_InitDynamicMesh");
	mesh->totalIndexCount = indexCount;
	mesh->indexCount = 0;
	mesh->vertSize = vertSize;
	R_InitDynamicVertexBufferState(&mesh->vb, vertexBytes, false);
}

// Store 14064C860 (PS4 PDB R_InitRenderBuffers, gfx_d3d/r_rendercmds.cpp:657; the matcher's identification): the
// dynamic meshes of the two back-end data sets, their deferred contexts (65 for the worker threads, one for
// compute), and the full-screen, shadow and flare meshes
void R_InitRenderBuffers()
{
	int dataIndex;
	int contextIndex;
	int viewIndex;
	int i;
	int j;
	int k;

	for (dataIndex = 0; dataIndex < 2; ++dataIndex)
	{
		GfxBackEndDynamicData *data = &unk_14A4FEAE0[dataIndex];
		R_InitDynamicMesh(&data->mesh[0], 0xF00, 0x1E000, 0x30);
		R_InitDynamicMesh(&data->mesh[1], 0xF00, 0x1E000, 0x30);
		R_InitDynamicMesh(&data->mesh[2], 0x30000, 0x600000, 0x30);
		R_InitDynamicMesh(&data->mesh[3], 0x4800, 0x42000, 0x20);
		R_InitDynamicMesh(&data->mesh[4], 0x2400, 0xD8000, 0x90);
		R_AssignNullBuffer(&data->mesh[5].ib);
		data->mesh[5].indices = nullptr;
		data->mesh[5].indexCount = 0;
		data->mesh[5].totalIndexCount = 0;
		data->mesh[5].vertSize = 0x14;
		R_InitDynamicVertexBufferState(&data->mesh[5].vb, 0xB4000, false);
		for (contextIndex = 0; contextIndex < 65; ++contextIndex)
			ComCall<HRESULT>(dx.d3d11device, DEV_CreateDeferredContext, 0u,
			                 &data->workerContexts[contextIndex].context);
	}
	for (dataIndex = 0; dataIndex < 2; ++dataIndex)
	{
		GfxBackEndDynamicData *data = &unk_14A4FEAE0[dataIndex];
		ComCall<HRESULT>(dx.d3d11device, DEV_CreateDeferredContext, 0u, &data->computeContext);
		sub_1401ACD10(&data->computeCmdBuf, sub_14066A480(0x100000, "computeCmds"), 0x100000);
	}
	for (viewIndex = 0; viewIndex < 6; ++viewIndex)
	{
		R_InitDynamicMesh(&gfxMeshGlob.fullSceneViewMesh[viewIndex].meshData, 6, 0x80, 0x20);
		R_SetQuadMesh(&gfxMeshGlob.fullSceneViewMesh[viewIndex], 0.0f, 0.0f, (float)vidConfig.sceneWidth,
		              (float)vidConfig.sceneHeight, 0.0f, 0.0f, 1.0f, 1.0f, 0xFFFFFFFF);
	}
	R_InitDynamicMesh(&gfxMeshGlob.spotShadowViewMeshSmall.meshData, 6, 0x80, 0x20);
	R_SetQuadMesh(&gfxMeshGlob.spotShadowViewMeshSmall, 0.0f, 0.0f, (float)vidConfig.shadowTileResSmall,
	              (float)vidConfig.shadowTileResSmall, 0.0f, 0.0f, 0.5f, 0.5f, 0xFFFFFFFF);
	R_InitDynamicMesh(&gfxMeshGlob.spotShadowViewMeshLarge.meshData, 6, 0x80, 0x20);
	R_SetQuadMesh(&gfxMeshGlob.spotShadowViewMeshLarge, 0.0f, 0.0f, (float)vidConfig.shadowTileResLarge,
	              (float)vidConfig.shadowTileResLarge, 0.0f, 0.0f, 1.0f, 1.0f, 0xFFFFFFFF);
	for (i = 0; i < 6; ++i)
	{
		for (j = 0; j < 4; ++j)
		{
			R_InitDynamicMesh(&gfxMeshGlob.spotShadowBatchedQuadMesh[i][j], 0x1800, 0x20000, 0x20);
			R_InitBatchedQuadMesh(&gfxMeshGlob.spotShadowBatchedQuadMesh[i][j], 0x400);
		}
	}
	for (i = 0; i < 6; ++i)
	{
		for (j = 0; j < 2; ++j)
		{
			for (k = 0; k < 9; ++k)
			{
				R_InitDynamicMesh(&gfxMeshGlob.sunShadowBatchedQuadMesh[i][j][k], 0x6000, 0x80000, 0x20);
				R_InitBatchedQuadMesh(&gfxMeshGlob.sunShadowBatchedQuadMesh[i][j][k], 0x1000);
				R_InitDynamicMesh(&gfxMeshGlob.sunShadowCacheQuadMesh[i][j][k].meshData, 6, 0x80, 0x20);
			}
		}
	}
	for (i = 0; i < 2; ++i)
		R_InitDynamicMesh(&unk_14B076500[i].flareMesh, 0x1200, 0x24000, 0x30);
}

// PS4 PDB R_ShutdownConstantBuffers (gfx_d3d/r_init.cpp:1852), inlined into R_ReleaseForShutdownOrReset
static void R_ShutdownConstantBuffers()
{
	int tableIndex;
	unsigned int bufferIndex;

	for (tableIndex = 0; tableIndex < 3; ++tableIndex)
	{
		for (bufferIndex = 0; bufferIndex < dx.constantBufferCounts[tableIndex][0]; ++bufferIndex)
			R_ReleaseBuffer(dx.defaultConstantBuffers[tableIndex][bufferIndex].buffer);
		memset(dx.defaultConstantBuffers[tableIndex], 0,
		       sizeof(GfxZoneTableEntry) * dx.constantBufferCounts[tableIndex][0]);
		dx.constantBufferTables[tableIndex][0] = nullptr;
		dx.constantBufferCounts[tableIndex][0] = 0;
	}
	R_ShutdownSubDomainRangeConstantBuffers();
	sub_1401B7160();
	sub_1401B0000(dx.smodelWorldMatrixConstantBuffer);
	ComCall<unsigned int>(dx.smodelWorldMatrixConstantBuffer, UNK_Release);
	dx.smodelWorldMatrixConstantBuffer = nullptr;
	sub_1401B0000(dx.smodelLightingOrAmbientConstantBuffer);
	ComCall<unsigned int>(dx.smodelLightingOrAmbientConstantBuffer, UNK_Release);
	dx.smodelLightingOrAmbientConstantBuffer = nullptr;
}

// PS4 PDB R_ShutdownStateTables (gfx_d3d/r_init.cpp:2290), inlined into R_ReleaseForShutdownOrReset
static void R_ShutdownStateTables()
{
	unsigned int depthStencilStateCount;
	unsigned int blendStateCount;
	int stateIndex;

	sub_140640830();
	depthStencilStateCount = dx.depthStencilStateCounts[0];
	blendStateCount = dx.blendStateCounts[0];
	sub_140632700(0);
	memset(dx.defaultDepthStencilStates, 0, sizeof(GfxZoneTableEntry) * depthStencilStateCount);
	memset(dx.defaultDepthStencilStateBits, 0, sizeof(dx.defaultDepthStencilStateBits[0]) * depthStencilStateCount);
	memset(dx.defaultBlendStates, 0, sizeof(GfxZoneTableEntry) * blendStateCount);
	memset(dx.defaultBlendStateBits, 0, sizeof(dx.defaultBlendStateBits[0]) * blendStateCount);
	for (stateIndex = 0; stateIndex < 32; ++stateIndex)
	{
		ComCall<unsigned int>(dx.rasterizerStates[stateIndex], UNK_Release);
		dx.rasterizerStates[stateIndex] = nullptr;
	}
}

// Store 140631DA0 (PS4 PDB R_ReleaseForShutdownOrReset(unsigned frontEndFrameCount, int resetOnly),
// gfx_d3d/r_init.cpp:2572): takes each window out of fullscreen and releases its swap chain and depth-stencil
// texture, then everything created by R_CreateForInitOrReset; a reset keeps the fences and queries
void R_ReleaseForShutdownOrReset(unsigned int frontEndFrameCount, int resetOnly)
{
	int windowIndex;
	int fullscreen;
	int fenceIndex;
	int samplerIndex;

	for (windowIndex = 0; windowIndex < dx.windowCount; ++windowIndex)
	{
		GfxWindowTarget *window = &dx.windows[windowIndex];
		ComCall<HRESULT>(window->swapChain, SWAPCHAIN_GetFullscreenState, &fullscreen, (IDXGIOutput **)nullptr);
		if (fullscreen)
			ComCall<HRESULT>(window->swapChain, SWAPCHAIN_SetFullscreenState, 0, (IDXGIOutput *)nullptr);
		ComCall<unsigned int>(window->depthStencilTex, UNK_Release);
		window->depthStencilTex = nullptr;
		ComCall<unsigned int>(window->swapChain, UNK_Release);
		window->swapChain = nullptr;
	}
	R_ShutdownConstantBuffers();
	R_ShutdownStateTables();
	sub_1401AB230();
	sub_1406513F0();
	if (!resetOnly)
	{
		sub_14063F200();
		sub_1401B1390();
	}
	sub_14062C5C0();
	sub_1401A9990();
	sub_14068F3B0();
	sub_1401B7F00();
	R_DestroyDynamicBuffers();
	R_DestroyParticleCloudBuffer();
	if (!g_allocateMinimalResources)
		sub_14064D450();
	if (dx.flushGpuFence)
	{
		R_LockImmediateContext();
		R_FlushSwap();
		R_UnlockImmediateContext();
		if (!resetOnly)
		{
			ComCall<unsigned int>(dx.flushGpuFence, UNK_Release);
			dx.flushGpuFence = nullptr;
		}
	}
	if (!resetOnly)
	{
		for (fenceIndex = 0; fenceIndex < 32; ++fenceIndex)
		{
			if (dx.fencePool[fenceIndex])
			{
				ComCall<unsigned int>(dx.fencePool[fenceIndex], UNK_Release);
				dx.fencePool[fenceIndex] = nullptr;
			}
		}
	}
	if (!g_allocateMinimalResources && !resetOnly)
	{
		sub_14068DB60();
		sub_14068C170();
	}
	if (gfxAssets.pixelCountQuery && !resetOnly)
	{
		ComCall<unsigned int>(gfxAssets.pixelCountQuery, UNK_Release);
		gfxAssets.pixelCountQuery = nullptr;
	}
	for (samplerIndex = 0; samplerIndex < 256; ++samplerIndex)
	{
		if (dx.samplerStates[samplerIndex])
		{
			ComCall<unsigned int>(dx.samplerStates[samplerIndex], UNK_Release);
			dx.samplerStates[samplerIndex] = nullptr;
		}
	}
	sub_140663EA0();
	sub_140663EB0();
	sub_140663D60();
}

// Store 1406322A0 (PS4 PDB R_Shutdown(int destroyWindow, int isRestart), gfx_d3d/r_init.cpp:1117; empty in the
// server), with R_ShutdownDirect3D inlined: with destroyWindow, unloads the graphics zones, releases everything,
// destroys the windows and releases the context, device, output, adapter and factory
void R_Shutdown(int destroyWindow, int isRestart)
{
	XZoneInfo zoneInfo;
	int i;

	R_SyncRenderThread();
	unk_14A37D581 = false;
	sub_1401AAE90();
	sub_140632660();
	sub_140683F70();
	sub_140634FC0();
	sub_140600CB0(isRestart);
	R_ResetModelLighting();
	sub_14063ECE0();
	if (!isRestart)
		sub_1406652E0();
	unk_14A34B558 = nullptr;
	unk_14A37D5B8[0] = 0;
	unk_14A37D5B8[1] = 0;
	unk_14A37D5B8[2] = 0;
	unk_14A346A94 = 0;
	unk_14A37D5D0[0] = 0;
	unk_14A37D5D0[1] = 0;
	for (i = 0; i < 8; ++i)
		unk_14B89E280[i] = 0;
	R_UnlockSkinnedCache();
	if (destroyWindow)
	{
		sub_140316750();
		zoneInfo.name = nullptr;
		zoneInfo.allocFlags = 0;
		zoneInfo.freeFlags = 0x46;
		sub_14018F210();
		DB_LoadXAssets(&zoneInfo, 1, DB_LOAD_ASYNC_FORCE_FREE);
		sub_140460B90();
		DB_ShutdownXAssets();
		sub_140603D50();
		R_ReleaseForShutdownOrReset(0, 0);
		while (dx.windowCount)
		{
			--dx.windowCount;
			if (IsWindow(dx.windows[dx.windowCount].hwnd))
				DestroyWindow(dx.windows[dx.windowCount].hwnd);
			dx.windows[dx.windowCount].hwnd = nullptr;
		}
		if (dx.immediateContext)
		{
			R_LockImmediateContext();
			ComCall<void>(dx.immediateContext, CTX_ClearState);
			ComCall<void>(dx.immediateContext, CTX_Flush);
			ComCall<unsigned int>(dx.immediateContext, UNK_Release);
			dx.immediateContext = nullptr;
			R_UnlockImmediateContext();
		}
		CloseHandle(dx.immediateContextMutex);
		dx.immediateContextMutex = nullptr;
		if (dx.d3d11device)
		{
			ComCall<unsigned int>(dx.d3d11device, UNK_Release);
			dx.d3d11device = nullptr;
		}
		if (dx.dxgiOutput)
		{
			ComCall<unsigned int>(dx.dxgiOutput, UNK_Release);
			dx.dxgiOutput = nullptr;
		}
		if (dx.dxgiAdapter)
		{
			ComCall<unsigned int>(dx.dxgiAdapter, UNK_Release);
			dx.dxgiAdapter = nullptr;
		}
		if (dx.dxgiFactory)
		{
			ComCall<unsigned int>(dx.dxgiFactory, UNK_Release);
			dx.dxgiFactory = nullptr;
		}
		sub_14064D7E0();
		sub_14062EB40();
	}
	sub_140605130();
	Dvar_SetBool(r_nvidiaGPU, false);
	Dvar_SetInt(r_nvidiaGPUCount, 0);
}

// Store 140675C50 (lineage: Black Ops' RB_SwapBuffers, gfx_d3d/rb_backend.cpp:5189; kept here with the device code
// until rb_backend.cpp exists): presents the frame with r_vsync's sync interval (0-4), then waits for the oldest of
// the 32 swap fences and issues it again for this frame. When the swap chain's fullscreen state doesn't match
// r_displayMode, or the window was (de)activated, the present goes to the window procedure (WM_USER), which switches
// the fullscreen state first.
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
			hr = ComCall<HRESULT>(dx.windows[dx.targetWindowIndex].swapChain, SWAPCHAIN_Present,
			                      (unsigned int)syncInterval, 0u);
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

// Store 1406300F0 (PS4 PDB R_ErrorDescription, gfx_d3d/r_init.cpp:603; the matcher's identification): the system's
// text for an HRESULT, or "(error 0x...)". FormatMessageA's buffer pointer is not initialised before the call.
const char *R_ErrorDescription(HRESULT hr)
{
	IW6_STATIC char buffer[0x400] IW6_AT("R_ErrorDescription", "buffer");
	char *message;

	FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
	               nullptr, hr, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), (char *)&message, 0, nullptr);
	if (message)
	{
		I_strncpyz(buffer, message, sizeof(buffer));
		LocalFree(message);
		return buffer;
	}
	Com_sprintf(buffer, sizeof(buffer), "(error 0x%x)", hr);
	return buffer;
}

// Store 14062F280 (PS4 PDB R_ComErrorCleanup, gfx_d3d/r_init.cpp:7684; the matcher's identification)
void R_ComErrorCleanup(int force)
{
	CG_HudLighting_ComErrorCleanup();
	RB_SetUploadShaderFastMode(0);
	// the int at 0x151464 in the front end's GfxBackEndData (the PS4 PDB's field there is not the Store's)
	if (force || (frontEndDataOut && *(const int *)((const char *)frontEndDataOut + 0x151464)))
	{
		R_AbortRenderCommands();
		R_SyncRenderThread();
		if (dx.d3d11device)
		{
			R_LockImmediateContext();
			R_FlushSwap();
			R_UnlockImmediateContext();
		}
	}
}

// Store 14062EE70 (PS4 PDB R_CheckLostDevice, gfx_d3d/r_init.cpp:7628)
bool R_CheckLostDevice()
{
	int remoteScreenUpdateNesting;

	if (!dx.d3d11device)
		return false;
	if (!dx.deviceLost)
		return true;
	if (Sys_IsMainThread())
	{
		R_WaitFrontendWorkerCmds();
		R_UnlockSkinnedCache();
		remoteScreenUpdateNesting = R_PopRemoteScreenUpdate();
		R_SyncRenderThread();
		dx.deviceLost = true;
		R_RecoverLostDevice();
		R_PushRemoteScreenUpdate(remoteScreenUpdateNesting);
		return false;
	}
	dx.deviceLost = true;
	return false;
}

// Store 140632660 (name unknown): unbinds the vertex streams of the immediate context, under its lock, while the
// device is usable
void sub_140632660()
{
	if (dx.d3d11device && !dx.deviceLost)
	{
		R_LockImmediateContext();
		R_ClearAllStreamSources((GfxCmdBufPrimState *)&gfxCmdBufState);
		R_UnlockImmediateContext();
	}
}

static_assert(__builtin_offsetof(DxGlobals, immediateContextLockCount) == 0x18, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, immediateContextMutex) == 0x3B68, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, adapterIndex) == 0x3B70, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, adapterNativeIsValid) == 0x3B74, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, displayModes) == 0x3B84, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, resolutionNameTable) == 0x5788, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, refreshRateNameTable) == 0x5F90, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, modeText) == 0x6798, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, fencePool) == 0x7B98, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, multiSampleType) == 0x7C9C, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, deviceLost) == 0x7CC8, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, windowCount) == 0x7CD4, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, windows) == 0x7CD8, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, flushGpuFence) == 0x7CF8, "DxGlobals layout (Store)");
static_assert(__builtin_offsetof(DxGlobals, flushGpuFenceIssued) == 0x7D00, "DxGlobals layout (Store)");
static_assert(sizeof(GfxWindowTarget) == 0x20, "GfxWindowTarget");
static_assert(__builtin_offsetof(vidConfig_t, letterbox4x3) == 0x11, "vidConfig_t (Store)");
static_assert(__builtin_offsetof(vidConfig_t, displayFrequency) == 0x18, "vidConfig_t (Store)");
static_assert(sizeof(vidConfig_t) == 0x40, "vidConfig_t (Store)");

// ==== BEGIN images ====
// The adapter's memory sizes (DXGI_ADAPTER_DESC), which the image code budgets textures against. Names unknown.

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"
#include "qcommon/dvar.h"

extern "C" const GUID IID_IDXGIDevice;  // dxguid
extern const dvar_t *r_amdGPU;
extern const dvar_t *r_amdGPUVideoMemoryScale;

// Store 140630CA0 (name unknown): the adapter's shared system memory
unsigned long long sub_140630CA0()
{
	IDXGIDevice *dxgiDevice;
	IDXGIAdapter *adapter;
	DXGI_ADAPTER_DESC desc;

	ComCall<long>(dx.d3d11device, UNK_QueryInterface, &IID_IDXGIDevice, &dxgiDevice);
	ComCall<long>(dxgiDevice, DXGIDEVICE_GetAdapter, &adapter);
	ComCall<long>(adapter, ADAPTER_GetDesc, &desc);
	ComCall<unsigned long>(dxgiDevice, UNK_Release);
	ComCall<unsigned long>(adapter, UNK_Release);
	return desc.SharedSystemMemory;
}

// Store 140630D20 (name unknown): the adapter's dedicated video and system memory, scaled by
// r_amdGPUVideoMemoryScale when r_amdGPU is set
unsigned long long sub_140630D20()
{
	IDXGIDevice *dxgiDevice;
	IDXGIAdapter *adapter;
	DXGI_ADAPTER_DESC desc;

	ComCall<long>(dx.d3d11device, UNK_QueryInterface, &IID_IDXGIDevice, &dxgiDevice);
	ComCall<long>(dxgiDevice, DXGIDEVICE_GetAdapter, &adapter);
	ComCall<long>(adapter, ADAPTER_GetDesc, &desc);
	ComCall<unsigned long>(dxgiDevice, UNK_Release);
	ComCall<unsigned long>(adapter, UNK_Release);
	unsigned long long memory = desc.DedicatedSystemMemory + desc.DedicatedVideoMemory;
	if (r_amdGPU->current.enabled)
		return (unsigned long long)((float)memory * r_amdGPUVideoMemoryScale->current.value);
	return memory;
}

static_assert(sizeof(DXGI_ADAPTER_DESC) == 0x130, "DXGI_ADAPTER_DESC");
static_assert(__builtin_offsetof(DXGI_ADAPTER_DESC, DedicatedVideoMemory) == 0x110, "DXGI_ADAPTER_DESC");
static_assert(__builtin_offsetof(DXGI_ADAPTER_DESC, SharedSystemMemory) == 0x120, "DXGI_ADAPTER_DESC");
// ==== END images ====
