// gfx_d3d/r_dxgi.h: the few Direct3D 11 / DXGI types the renderer's device code passes to the API.
//
// Build environment, not game source: the original includes d3d11.h and dxgi.h; the reconstruction is built
// without the Windows SDK, so these are declared by hand, only the members the code reads or writes, at the
// public headers' offsets (static_asserts below; each one checked against the Store build's use of it).
#pragma once

struct ID3D11Device;
struct ID3D11DeviceContext;
struct ID3D11Query;
struct ID3D11Texture2D;
struct IDXGIFactory;
struct IDXGIAdapter;
struct IDXGIOutput;
struct IDXGISwapChain;

struct GUID
{
	unsigned int Data1;
	unsigned short Data2;
	unsigned short Data3;
	unsigned char Data4[8];
};

typedef long HRESULT;

#define DXGI_ERROR_NOT_FOUND ((HRESULT)0x887A0002)
#define DXGI_ERROR_DEVICE_REMOVED ((HRESULT)0x887A0005)

enum DXGI_FORMAT : int
{
	DXGI_FORMAT_R8G8B8A8_UNORM = 28,
};

enum D3D_FEATURE_LEVEL : int
{
	D3D_FEATURE_LEVEL_9_1 = 0x9100,
	D3D_FEATURE_LEVEL_9_2 = 0x9200,
	D3D_FEATURE_LEVEL_9_3 = 0x9300,
	D3D_FEATURE_LEVEL_10_0 = 0xA000,
	D3D_FEATURE_LEVEL_10_1 = 0xA100,
	D3D_FEATURE_LEVEL_11_0 = 0xB000,
};

enum D3D_DRIVER_TYPE : int
{
	D3D_DRIVER_TYPE_UNKNOWN = 0,
};

#define D3D11_CREATE_DEVICE_PREVENT_ALTERING_LAYER_SETTINGS_FROM_REGISTRY 0x80
#define D3D11_SDK_VERSION 7
#define DXGI_USAGE_RENDER_TARGET_OUTPUT 0x20
#define DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH 2
#define DXGI_MWA_NO_WINDOW_CHANGES 1

struct DXGI_RATIONAL
{
	unsigned int Numerator;
	unsigned int Denominator;
};

struct DXGI_MODE_DESC
{
	unsigned int Width;
	unsigned int Height;
	DXGI_RATIONAL RefreshRate;
	DXGI_FORMAT Format;
	int ScanlineOrdering;
	int Scaling;
};

struct DXGI_SAMPLE_DESC
{
	unsigned int Count;
	unsigned int Quality;
};

struct DXGI_SWAP_CHAIN_DESC
{
	DXGI_MODE_DESC BufferDesc;
	DXGI_SAMPLE_DESC SampleDesc;
	unsigned int BufferUsage;
	unsigned int BufferCount;
	struct HWND__ *OutputWindow;
	int Windowed;
	int SwapEffect;  // DXGI_SWAP_EFFECT_DISCARD = 0
	unsigned int Flags;
};

struct DXGI_OUTPUT_DESC
{
	unsigned short DeviceName[32];
	int DesktopCoordinates[4];
	int AttachedToDesktop;
	int Rotation;
	struct HMONITOR__ *Monitor;
};

struct DXGI_ADAPTER_DESC
{
	unsigned short Description[128];
	unsigned int VendorId;
	unsigned int DeviceId;
	unsigned int SubSysId;
	unsigned int Revision;
	unsigned long long DedicatedVideoMemory;
	unsigned long long DedicatedSystemMemory;
	unsigned long long SharedSystemMemory;
	unsigned int AdapterLuid[2];
};

static_assert(sizeof(DXGI_MODE_DESC) == 0x1C, "DXGI_MODE_DESC");
static_assert(sizeof(DXGI_SWAP_CHAIN_DESC) == 0x48, "DXGI_SWAP_CHAIN_DESC");
static_assert(__builtin_offsetof(DXGI_SWAP_CHAIN_DESC, OutputWindow) == 0x30, "DXGI_SWAP_CHAIN_DESC");
static_assert(__builtin_offsetof(DXGI_SWAP_CHAIN_DESC, Flags) == 0x40, "DXGI_SWAP_CHAIN_DESC");
static_assert(__builtin_offsetof(DXGI_OUTPUT_DESC, Monitor) == 0x58, "DXGI_OUTPUT_DESC");
static_assert(sizeof(DXGI_OUTPUT_DESC) == 0x60, "DXGI_OUTPUT_DESC");
static_assert(__builtin_offsetof(DXGI_ADAPTER_DESC, VendorId) == 0x100, "DXGI_ADAPTER_DESC");
static_assert(sizeof(DXGI_ADAPTER_DESC) == 0x130, "DXGI_ADAPTER_DESC");

extern "C" {
// dxgi.dll / d3d11.dll entry points (imports of the Store build)
HRESULT CreateDXGIFactory(const GUID &riid, void **ppFactory);
HRESULT D3D11CreateDevice(IDXGIAdapter *pAdapter, D3D_DRIVER_TYPE DriverType, void *Software, unsigned int Flags,
                          const D3D_FEATURE_LEVEL *pFeatureLevels, unsigned int FeatureLevels,
                          unsigned int SDKVersion, ID3D11Device **ppDevice, D3D_FEATURE_LEVEL *pFeatureLevel,
                          ID3D11DeviceContext **ppImmediateContext);
// dxguid.lib constants, linked into the exe
extern const GUID IID_IDXGIFactory;
extern const GUID IID_ID3D11Texture2D;
}
