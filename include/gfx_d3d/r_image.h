// gfx_d3d/r_image.h: images (textures and their views) and render targets, Microsoft Store build layout.
//
// The Direct3D 11 structures are declared by hand (the reconstruction is built without the Windows SDK): only the
// fields the image code uses, at the sizes and offsets of the public d3d11.h / dxgi.h declarations, which the
// static_asserts in src/gfx_d3d/r_image.cpp check against the Store build's stack layouts.
//
// GfxImage and GfxRenderTarget differ from the servers' PDBs (iw6_ds_xb3, iw6_ds_ps4): the Store build's GfxImage
// is 0x68 bytes (the servers' 0x38) and keeps the texture's format, a mip level count and per-picmip level
// sizes for streaming; its GfxRenderTarget has two image-and-surface pairs (the second for multisampling).
#pragma once

#include "client/client.h"
#include "gfx_d3d/r_dx.h"

// ---- Direct3D 11 / DXGI (public API) ---------------------------------------------------------------------

#define D3D11_RESOURCE_MISC_GENERATE_MIPS 0x1
#define D3D11_STANDARD_MULTISAMPLE_PATTERN 0xffffffff

// D3D11_SRV_DIMENSION, D3D11_RTV_DIMENSION, D3D11_DSV_DIMENSION, D3D11_UAV_DIMENSION values
#define D3D11_SRV_DIMENSION_BUFFER 1
#define D3D11_SRV_DIMENSION_TEXTURE1D 2
#define D3D11_SRV_DIMENSION_TEXTURE2D 4
#define D3D11_SRV_DIMENSION_TEXTURE2DMS 6
#define D3D11_SRV_DIMENSION_TEXTURE3D 8
#define D3D11_SRV_DIMENSION_BUFFEREX 11
#define D3D11_RTV_DIMENSION_TEXTURE2D 4
#define D3D11_RTV_DIMENSION_TEXTURE2DMS 6
#define D3D11_DSV_DIMENSION_TEXTURE2D 3
#define D3D11_DSV_DIMENSION_TEXTURE2DMS 5
#define D3D11_UAV_DIMENSION_BUFFER 1
#define D3D11_BUFFER_UAV_FLAG_RAW 0x1
#define D3D11_BUFFEREX_SRV_FLAG_RAW 0x1

struct ID3D11Resource;
struct ID3D11Buffer;
struct ID3D11Texture1D;
struct ID3D11Texture2D;
struct ID3D11Texture3D;
struct ID3D11ShaderResourceView;
struct ID3D11RenderTargetView;
struct ID3D11DepthStencilView;
struct ID3D11UnorderedAccessView;
struct IDXGISwapChain;
struct IDXGIDevice;

struct D3D11_TEXTURE1D_DESC
{
	unsigned int Width;
	unsigned int MipLevels;
	unsigned int ArraySize;
	DXGI_FORMAT Format;
	D3D11_USAGE Usage;
	unsigned int BindFlags;
	unsigned int CPUAccessFlags;
	unsigned int MiscFlags;
};

struct D3D11_TEXTURE2D_DESC
{
	unsigned int Width;
	unsigned int Height;
	unsigned int MipLevels;
	unsigned int ArraySize;
	DXGI_FORMAT Format;
	DXGI_SAMPLE_DESC SampleDesc;
	D3D11_USAGE Usage;
	unsigned int BindFlags;
	unsigned int CPUAccessFlags;
	unsigned int MiscFlags;
};

struct D3D11_TEXTURE3D_DESC
{
	unsigned int Width;
	unsigned int Height;
	unsigned int Depth;
	unsigned int MipLevels;
	DXGI_FORMAT Format;
	D3D11_USAGE Usage;
	unsigned int BindFlags;
	unsigned int CPUAccessFlags;
	unsigned int MiscFlags;
};

// Texture1D/2D/3D/Cube views: {MostDetailedMip, MipLevels}; Texture2DArray adds {FirstArraySlice, ArraySize};
// Buffer: {FirstElement, NumElements}; BufferEx: {FirstElement, NumElements, Flags}.
struct D3D11_SHADER_RESOURCE_VIEW_DESC
{
	DXGI_FORMAT Format;
	unsigned int ViewDimension;
	union
	{
		struct
		{
			unsigned int MostDetailedMip;
			unsigned int MipLevels;
		} Texture;
		struct
		{
			unsigned int FirstElement;
			unsigned int NumElements;
			unsigned int Flags;
		} BufferEx;
		unsigned int raw[4];
	};
};

struct D3D11_RENDER_TARGET_VIEW_DESC
{
	DXGI_FORMAT Format;
	unsigned int ViewDimension;
	union
	{
		unsigned int MipSlice;  // Texture2D
		unsigned int raw[3];
	};
};

struct D3D11_DEPTH_STENCIL_VIEW_DESC
{
	DXGI_FORMAT Format;
	unsigned int ViewDimension;
	unsigned int Flags;
	union
	{
		unsigned int MipSlice;  // Texture2D
		unsigned int raw[3];
	};
};

struct D3D11_UNORDERED_ACCESS_VIEW_DESC
{
	DXGI_FORMAT Format;
	unsigned int ViewDimension;
	struct
	{
		unsigned int FirstElement;
		unsigned int NumElements;
		unsigned int Flags;
	} Buffer;
};

// ---- the game's images ----------------------------------------------------------------------------------

struct GfxImageLoadDef;

// GfxImage::mapType (MapType)
enum
{
	MAPTYPE_1D = 2,
	MAPTYPE_2D = 3,
	MAPTYPE_3D = 4,
	MAPTYPE_CUBE = 5,
	MAPTYPE_ARRAY = 6,  // Store build: 2D texture array (numElements slices)
};

// GfxImage::category: IMG_CATEGORY_WATER is the only one the Store image code tests
#define IMG_CATEGORY_WATER 5
#define IMG_CATEGORY_RENDERTARGET 6

// Image flags (the `imageFlags` argument of Image_Setup and the creation functions). Only the bits the
// Store build's image code tests are named.
#define IMG_FLAG_NOMIPMAPS 0x2
#define IMG_FLAG_CPU_READ 0x800
#define IMG_FLAG_CPU_WRITE 0x1000
#define IMG_FLAG_MAPTYPE_MASK 0x38000  // 0: 2D, 0x8000 cube, 0x10000 3D, 0x20000 array, anything else 1D
#define IMG_FLAG_MAPTYPE_CUBE 0x8000
#define IMG_FLAG_MAPTYPE_3D 0x10000
#define IMG_FLAG_MAPTYPE_ARRAY 0x20000
#define IMG_FLAG_GENERATE_MIPS 0x800000    // render target bind + D3D11_RESOURCE_MISC_GENERATE_MIPS
#define IMG_FLAG_DYNAMIC 0x1000000
#define IMG_FLAG_RENDERTARGET 0x2000000
#define IMG_FLAG_MULTISAMPLE 0x4000000
#define IMG_FLAG_TRACKED 0x10000000        // copied into GfxImage::flags bit 3
#define IMG_FLAG_STAGING 0x20000000
#define IMG_FLAG_DEPTH 0x40000000          // depth-stencil bind; the shader view reads the depth as a colour
#define IMG_FLAG_TYPELESS 0x80000000       // the texture is created typeless

union GfxTextureUnion
{
	ID3D11Texture1D *linemap;
	ID3D11Texture2D *map;
	ID3D11Texture3D *volmap;
	ID3D11Texture2D *cubemap;
	ID3D11Resource *resource;
	GfxImageLoadDef *loadDef;
};

struct GfxTexture
{
	GfxTextureUnion basemap;
	ID3D11ShaderResourceView *shaderView;
	ID3D11ShaderResourceView *shaderViewAlternate;
};

struct Picmip
{
	unsigned char platform[2];
};

struct CardMemory
{
	int platform[2];
};

// Store build only: the size of the image at each picmip level, for streaming (Image_SetupStreamLevel copies
// one into the image; Load_Texture and the streaming upload read the mip count from it).
struct GfxImageStreamLevel
{
	unsigned short width;
	unsigned short height;
	unsigned int cardMemoryAndLevelCount;  // card memory in the low 26 bits, mip level count in the top 6
};

struct GfxImage
{
	GfxTexture texture;
	DXGI_FORMAT format;
	unsigned char mapType;
	unsigned char semantic;
	unsigned char category;
	unsigned char flags;
	Picmip picmip;
	unsigned char track;
	CardMemory cardMemory;
	unsigned short width;
	unsigned short height;
	unsigned short depth;
	unsigned short numElements;
	unsigned char levelCount;
	unsigned char unknown35[11];
	GfxImageStreamLevel streamLevels[4];
	const char *name;
};

// ---- render targets ---------------------------------------------------------------------------------------

enum RenderTargetUsage
{
	RENDERTARGET_USAGE_DEPTH = 0,
	RENDERTARGET_USAGE_RENDER = 1,
	RENDERTARGET_USAGE_RENDER_SHARE_SCENE = 2,
	RENDERTARGET_USAGE_TEXTURE = 3,
	RENDERTARGET_USAGE_TYPELESS = 4,
	RENDERTARGET_USAGE_RENDER_TYPELESS = 5,
	RENDERTARGET_USAGE_TEXTURE_WITH_MIPS = 6,
};

enum FullscreenType
{
	FULLSCREEN_DISPLAY = 0,
	FULLSCREEN_MIXED = 1,
	FULLSCREEN_SCENE = 2,
};

// The servers have one state (GFX_MSAA_STATE_OFF, GFX_MSAA_STATE_COUNT = 1); the Store build has a second one,
// the multisampled surface of a render target.
enum GfxMSAAState
{
	GFX_MSAA_STATE_OFF = 0,
	GFX_MSAA_STATE_ON = 1,
	GFX_MSAA_STATE_COUNT = 2,
};

// GfxRenderTargetId: the Store build's ids (s_renderTargetNames; one more than the servers' from
// R_RENDERTARGET_LETTERBOX_FRAME_BUFFER on); only the ones reconstructed code uses
enum GfxRenderTargetId
{
	R_RENDERTARGET_FRAME_BUFFER = 1,
	R_RENDERTARGET_LETTERBOX_FRAME_BUFFER = 2,
	R_RENDERTARGET_SCENE = 3,
	R_RENDERTARGET_RESOLVED_SCENE = 6,
	R_RENDERTARGET_PIP_SCENE = 13,
	R_RENDERTARGET_PIP_SCENE_FLOAT_Z = 14,
	R_RENDERTARGET_PIP_SCENE_PINGPONG = 15,
	R_RENDERTARGET_PIP_FINAL_SCENE = 16,
	R_RENDERTARGET_PIP_SCENE_NODEPTH = 17,
	R_RENDERTARGET_PIP_SCENE_PINGPONG_NODEPTH = 18,
	R_RENDERTARGET_PIP_FINAL_SCENE_NODEPTH = 19,
	R_RENDERTARGET_SCENE_NODEPTH = 72,
};

struct GfxRenderTargetSurface
{
	ID3D11RenderTargetView *color;
	ID3D11DepthStencilView *depthStencil;
	ID3D11RenderTargetView *colorGamma;
};

struct GfxImageAndSurface
{
	GfxImage *image;
	GfxRenderTargetSurface surface;
};

struct GfxRenderTarget
{
	GfxImageAndSurface imageAndSurfaces[2];  // [GfxMSAAState]: the resolved and the multisampled surface
	unsigned int width;
	unsigned int height;
	DXGI_FORMAT format;
};

extern vidConfig_t vidConfig;  // gfx_d3d/r_init.cpp

// ---- functions --------------------------------------------------------------------------------------------

GfxImage *Image_AllocProg(int imageProgType, unsigned char category, unsigned char semantic);
void Image_SetTextureDescMSAASettings(D3D11_TEXTURE2D_DESC *texDesc, unsigned int imageFlags);
DXGI_FORMAT R_MakeSRGBFormat(DXGI_FORMAT format);
void Image_Setup(GfxImage *image, int width, int height, int depth, int numElements, int imageFlags,
                 DXGI_FORMAT imageFormat, const char *name, const D3D11_SUBRESOURCE_DATA *initData);
void Image_SetupAndLoad(GfxImage *image, int width, int height, int depth, int imageFlags, DXGI_FORMAT imageFormat,
                        const char *name);
void Image_SetupRenderTarget(GfxImage *image, unsigned short width, unsigned short height, int imageFlags,
                             DXGI_FORMAT imageFormat, const char *name);
void Image_SetupRenderTargetDepth(GfxImage *image, unsigned short width, unsigned short height, int imageFlags,
                                  DXGI_FORMAT imageFormat, const char *name);
void Image_SetupRenderTargetTypeless(GfxImage *image, unsigned short width, unsigned short height, int imageFlags,
                                     DXGI_FORMAT imageFormat, const char *name);
void Image_SetupRenderTargetWithMips(GfxImage *image, unsigned short width, unsigned short height,
                                     DXGI_FORMAT imageFormat, const char *name);
ID3D11RenderTargetView *Image_GetColorRenderTarget(unsigned int imageProgType, GfxImage *image, int imageFlags,
                                                   DXGI_FORMAT format);
ID3D11DepthStencilView *Image_GetDepthStencilRenderTarget(unsigned int imageProgType, GfxImage *image);
unsigned int Image_GetCardMemoryAmountForMipLevel(DXGI_FORMAT format, unsigned int mipWidth, unsigned int mipHeight,
                                                  unsigned int mipDepth);
void Image_Create2DTexture_PC(GfxImage *image, unsigned short width, unsigned short height, int mipmapCount,
                              int imageFlags, DXGI_FORMAT imageFormat, const D3D11_SUBRESOURCE_DATA *initData);
void Image_Create3DTexture_PC(GfxImage *image, unsigned short width, unsigned short height, unsigned short depth,
                              int mipmapCount, int imageFlags, DXGI_FORMAT imageFormat,
                              const D3D11_SUBRESOURCE_DATA *initData);
void Image_CreateCubeTexture_PC(GfxImage *image, unsigned short edgeLen, int mipmapCount, int imageFlags,
                                DXGI_FORMAT imageFormat, const D3D11_SUBRESOURCE_DATA *initData);
unsigned int Image_CountMipmaps(unsigned int imageFlags, unsigned int width, unsigned int height, unsigned int depth);
unsigned int Image_CubemapFace(unsigned int faceIndex);

// names unknown (Store build)
void sub_14062AC10(GfxImage *image, unsigned short width, int mipmapCount, int imageFlags, DXGI_FORMAT imageFormat,
                   const D3D11_SUBRESOURCE_DATA *initData);
void sub_14062AF40(GfxImage *image, unsigned short width, unsigned short height, unsigned short numElements,
                   int mipmapCount, int imageFlags, DXGI_FORMAT imageFormat, const D3D11_SUBRESOURCE_DATA *initData);
DXGI_FORMAT sub_14062C460(DXGI_FORMAT format);
void sub_14062E820(int imageFlags, D3D11_USAGE *usage, unsigned int *bindFlags, unsigned int *cpuAccessFlags);
DXGI_FORMAT sub_14062E8A0(DXGI_FORMAT format);
void sub_14062DA40(GfxImage *image, unsigned int picmip);
void sub_1401B0040(GfxImage *image);  // adds the texture's card memory to a running total (not reconstructed)
void sub_14062E8D0(GfxImage *image, int imageFlags, DXGI_FORMAT imageFormat, int width, int height, int depth,
                   int numElements);  // the image's card memory (not reconstructed)
DXGI_FORMAT sub_14064F310();  // R_GetDepthStencilFormat or R_GetShadowMapFormat (folded in the servers)
DXGI_FORMAT sub_14064F350();  // the other one
