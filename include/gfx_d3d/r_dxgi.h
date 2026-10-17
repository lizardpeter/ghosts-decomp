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
	DXGI_FORMAT_UNKNOWN = 0,
	DXGI_FORMAT_R32G32B32A32_FLOAT = 2,
	DXGI_FORMAT_R16G16B16A16_FLOAT = 10,
	DXGI_FORMAT_R16G16B16A16_UNORM = 11,
	DXGI_FORMAT_R32G32_TYPELESS = 15,
	DXGI_FORMAT_R32G32_FLOAT = 16,
	DXGI_FORMAT_R32G8X24_TYPELESS = 19,
	DXGI_FORMAT_D32_FLOAT_S8X24_UINT = 20,
	DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS = 21,
	DXGI_FORMAT_R11G11B10_FLOAT = 26,
	DXGI_FORMAT_R8G8B8A8_TYPELESS = 27,
	DXGI_FORMAT_R8G8B8A8_UNORM = 28,
	DXGI_FORMAT_R8G8B8A8_UNORM_SRGB = 29,
	DXGI_FORMAT_R8G8B8A8_UINT = 30,
	DXGI_FORMAT_R8G8B8A8_SNORM = 31,
	DXGI_FORMAT_R8G8B8A8_SINT = 32,
	DXGI_FORMAT_R16G16_FLOAT = 34,
	DXGI_FORMAT_R32_TYPELESS = 39,
	DXGI_FORMAT_D32_FLOAT = 40,
	DXGI_FORMAT_R32_FLOAT = 41,
	DXGI_FORMAT_D24_UNORM_S8_UINT = 45,
	DXGI_FORMAT_R8G8_UNORM = 49,
	DXGI_FORMAT_R16_TYPELESS = 53,
	DXGI_FORMAT_R16_FLOAT = 54,
	DXGI_FORMAT_D16_UNORM = 55,
	DXGI_FORMAT_R16_UNORM = 56,
	DXGI_FORMAT_R8_UNORM = 61,
	DXGI_FORMAT_A8_UNORM = 65,
	DXGI_FORMAT_BC1_TYPELESS = 70,
	DXGI_FORMAT_BC1_UNORM = 71,
	DXGI_FORMAT_BC1_UNORM_SRGB = 72,
	DXGI_FORMAT_BC2_TYPELESS = 73,
	DXGI_FORMAT_BC2_UNORM = 74,
	DXGI_FORMAT_BC2_UNORM_SRGB = 75,
	DXGI_FORMAT_BC3_TYPELESS = 76,
	DXGI_FORMAT_BC3_UNORM = 77,
	DXGI_FORMAT_BC3_UNORM_SRGB = 78,
	DXGI_FORMAT_BC4_UNORM = 80,
	DXGI_FORMAT_BC5_UNORM = 83,
	DXGI_FORMAT_BC5_SNORM = 84,
	DXGI_FORMAT_BC6H_UF16 = 95,
	DXGI_FORMAT_BC6H_SF16 = 96,
	DXGI_FORMAT_BC7_UNORM = 98,
	DXGI_FORMAT_BC7_UNORM_SRGB = 99,
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

// Resource descriptions shared by the buffer, image and state code
enum D3D11_USAGE
{
	D3D11_USAGE_DEFAULT = 0,
	D3D11_USAGE_IMMUTABLE = 1,
	D3D11_USAGE_DYNAMIC = 2,
	D3D11_USAGE_STAGING = 3,
};

enum D3D11_BIND_FLAG
{
	D3D11_BIND_VERTEX_BUFFER = 0x1,
	D3D11_BIND_INDEX_BUFFER = 0x2,
	D3D11_BIND_CONSTANT_BUFFER = 0x4,
	D3D11_BIND_SHADER_RESOURCE = 0x8,
	D3D11_BIND_RENDER_TARGET = 0x20,
	D3D11_BIND_DEPTH_STENCIL = 0x40,
	D3D11_BIND_UNORDERED_ACCESS = 0x80,
};

enum D3D11_CPU_ACCESS_FLAG
{
	D3D11_CPU_ACCESS_WRITE = 0x10000,
	D3D11_CPU_ACCESS_READ = 0x20000,
};

struct D3D11_SUBRESOURCE_DATA
{
	const void *pSysMem;
	unsigned int SysMemPitch;
	unsigned int SysMemSlicePitch;
};

struct D3D11_BUFFER_DESC
{
	unsigned int ByteWidth;
	D3D11_USAGE Usage;
	unsigned int BindFlags;
	unsigned int CPUAccessFlags;
	unsigned int MiscFlags;
	unsigned int StructureByteStride;
};
