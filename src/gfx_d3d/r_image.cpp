// gfx_d3d/r_image.cpp (Store build)
//
// Creating the Direct3D 11 textures and views of images, from the Microsoft Store build (iw6mp64_MSStore_ship).
// Names come from the servers' PDBs (iw6_ds_xb3/iw6_ds_ps4 gfx_d3d/r_image.cpp, whose back end is stubbed) or,
// for the texture creation functions, from Black Ops' r_image.cpp (Image_Create2DTexture_PC and friends, the D3D9
// ancestors); the rest are unknown.

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "gfx_d3d/r_image.cpp"
#include <iw6_static.h>

IW6_STATIC GfxImage g_imageProgs[] IW6_AT("", "g_imageProgs");
IW6_STATIC const char *g_imageProgNames[] IW6_AT("", "g_imageProgNames");
IW6_STATIC GfxImage *g_defaultDepthImage IW6_AT("", "g_defaultDepthImage");

extern const dvar_t *r_loadForRenderer;       // gfx_d3d/r_dvars.cpp
extern const dvar_t *r_picmip_water;          // gfx_d3d/r_dvars.cpp
extern unsigned int unk_14A3852BC;            // the multisample count (in DxGlobals, Store layout)

#define IMAGE_PROG_DEFAULT_DEPTH 0x51

// Store 14062AB40 (gfx_d3d/r_image.cpp:658)
GfxImage *Image_AllocProg(int imageProgType, unsigned char category, unsigned char semantic)
{
	GfxImage *image = &g_imageProgs[imageProgType];
	image->name = g_imageProgNames[imageProgType];
	image->category = category;
	image->semantic = semantic;
	return image;
}

// Store 14062AB70 (name unknown): copies `count` subresources of the source image's texture into `dest`, the
// streaming update's new texture
void sub_14062AB70(GfxTexture *dest, unsigned int destSubresource, GfxImage *source, unsigned int sourceSubresource,
                   int count)
{
	for (int i = 0; i < count; i++)
		ComCall<void>(dx.immediateContext, CTX_CopySubresourceRegion, dest->basemap.resource, destSubresource + i, 0u,
		              0u, 0u, source->texture.basemap.resource, sourceSubresource + i, (const void *)nullptr);
}

// Store 14062AC10 (name unknown): the 1D texture
void sub_14062AC10(GfxImage *image, unsigned short width, int mipmapCount, int imageFlags, DXGI_FORMAT imageFormat,
                   const D3D11_SUBRESOURCE_DATA *initData)
{
	D3D11_TEXTURE1D_DESC desc;

	image->width = width;
	image->height = 1;
	image->depth = 1;
	image->mapType = MAPTYPE_1D;
	desc.Width = width;
	desc.MipLevels = mipmapCount;
	desc.ArraySize = 1;
	desc.Format = imageFormat;
	desc.Usage = D3D11_USAGE_DEFAULT;
	desc.BindFlags = 0;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = 0;
	sub_14062E820(imageFlags, &desc.Usage, &desc.BindFlags, &desc.CPUAccessFlags);
	ComCall<long>(dx.d3d11device, DEV_CreateTexture1D, &desc, initData, &image->texture.basemap.linemap);
	if (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE)
		ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, image->texture.basemap.resource,
		              (const D3D11_SHADER_RESOURCE_VIEW_DESC *)nullptr, &image->texture.shaderView);
	else
		image->texture.shaderView = nullptr;
	sub_1401B0040(image);
}

// Store 14062ACD0 (Black Ops' Image_Create2DTexture_PC, gfx_d3d/r_image.cpp:642, plus the initial data)
void Image_Create2DTexture_PC(GfxImage *image, unsigned short width, unsigned short height, int mipmapCount,
                              int imageFlags, DXGI_FORMAT imageFormat, const D3D11_SUBRESOURCE_DATA *initData)
{
	D3D11_TEXTURE2D_DESC desc;
	D3D11_SHADER_RESOURCE_VIEW_DESC viewDesc;

	desc.Width = width;
	desc.Height = height;
	image->width = width;
	image->height = height;
	image->depth = 1;
	image->mapType = MAPTYPE_2D;
	desc.MipLevels = mipmapCount;
	desc.ArraySize = 1;
	desc.Usage = D3D11_USAGE_DEFAULT;
	desc.BindFlags = 0;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = 0;
	if (imageFlags & IMG_FLAG_TYPELESS)
		desc.Format = sub_14062C460(imageFormat);
	else
		desc.Format = imageFormat;
	desc.MiscFlags |= (imageFlags >> 23) & D3D11_RESOURCE_MISC_GENERATE_MIPS;
	Image_SetTextureDescMSAASettings(&desc, imageFlags);
	sub_14062E820(imageFlags, &desc.Usage, &desc.BindFlags, &desc.CPUAccessFlags);
	ComCall<long>(dx.d3d11device, DEV_CreateTexture2D, &desc, initData, &image->texture.basemap.map);
	if (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE)
	{
		// a depth texture is read as a colour
		if (imageFlags & IMG_FLAG_DEPTH)
		{
			if (imageFormat == DXGI_FORMAT_D32_FLOAT_S8X24_UINT)
				viewDesc.Format = DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS;
			else if (imageFormat == DXGI_FORMAT_D32_FLOAT)
				viewDesc.Format = DXGI_FORMAT_R32_FLOAT;
			else if (imageFormat == DXGI_FORMAT_D16_UNORM)
				viewDesc.Format = DXGI_FORMAT_R16_UNORM;
			else
				viewDesc.Format = imageFormat;
		}
		else
		{
			viewDesc.Format = imageFormat;
		}
		if (imageFlags & IMG_FLAG_MULTISAMPLE)
		{
			viewDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2DMS;
		}
		else
		{
			viewDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
			viewDesc.Texture.MostDetailedMip = 0;
			viewDesc.Texture.MipLevels = 0xffffffff;
		}
		ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, image->texture.basemap.resource, &viewDesc,
		              &image->texture.shaderView);
	}
	else
	{
		image->texture.shaderView = nullptr;
	}
	sub_1401B0040(image);
}

// Store 14062AE30 (Black Ops' Image_Create3DTexture_PC, gfx_d3d/r_image.cpp:696, plus the initial data)
void Image_Create3DTexture_PC(GfxImage *image, unsigned short width, unsigned short height, unsigned short depth,
                              int mipmapCount, int imageFlags, DXGI_FORMAT imageFormat,
                              const D3D11_SUBRESOURCE_DATA *initData)
{
	D3D11_TEXTURE3D_DESC desc;
	D3D11_SHADER_RESOURCE_VIEW_DESC viewDesc;

	desc.Width = width;
	desc.Height = height;
	desc.Depth = depth;
	desc.MipLevels = mipmapCount;
	image->width = width;
	image->height = height;
	image->depth = depth;
	image->mapType = MAPTYPE_3D;
	desc.Usage = D3D11_USAGE_DEFAULT;
	desc.BindFlags = 0;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = 0;
	if (imageFlags & IMG_FLAG_TYPELESS)
		desc.Format = sub_14062C460(imageFormat);
	else
		desc.Format = imageFormat;
	sub_14062E820(imageFlags, &desc.Usage, &desc.BindFlags, &desc.CPUAccessFlags);
	ComCall<long>(dx.d3d11device, DEV_CreateTexture3D, &desc, initData, &image->texture.basemap.volmap);
	if (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE)
	{
		viewDesc.Format = imageFormat;
		viewDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE3D;
		viewDesc.Texture.MostDetailedMip = 0;
		viewDesc.Texture.MipLevels = 0xffffffff;
		ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, image->texture.basemap.resource, &viewDesc,
		              &image->texture.shaderView);
	}
	else
	{
		image->texture.shaderView = nullptr;
	}
	sub_1401B0040(image);
}

// Store 14062AF40 (name unknown): the 2D texture array (one slice per element)
void sub_14062AF40(GfxImage *image, unsigned short width, unsigned short height, unsigned short numElements,
                   int mipmapCount, int imageFlags, DXGI_FORMAT imageFormat, const D3D11_SUBRESOURCE_DATA *initData)
{
	D3D11_TEXTURE2D_DESC desc;

	image->width = width;
	desc.Usage = D3D11_USAGE_DEFAULT;
	desc.BindFlags = 0;
	desc.CPUAccessFlags = 0;
	desc.MiscFlags = 0;
	desc.Width = width;
	desc.Height = height;
	desc.MipLevels = mipmapCount;
	desc.ArraySize = numElements;
	desc.Format = imageFormat;
	image->height = height;
	desc.SampleDesc.Count = 1;
	desc.SampleDesc.Quality = 0;
	image->depth = 1;
	image->mapType = MAPTYPE_ARRAY;
	sub_14062E820(imageFlags, &desc.Usage, &desc.BindFlags, &desc.CPUAccessFlags);
	ComCall<long>(dx.d3d11device, DEV_CreateTexture2D, &desc, initData, &image->texture.basemap.map);
	if (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE)
		ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, image->texture.basemap.resource,
		              (const D3D11_SHADER_RESOURCE_VIEW_DESC *)nullptr, &image->texture.shaderView);
	else
		image->texture.shaderView = nullptr;
	sub_1401B0040(image);
}

// Store 14062B020 (Black Ops' Image_CreateCubeTexture_PC, gfx_d3d/r_image.cpp:738, plus flags and initial data).
// Every cube texture is made sRGB.
void Image_CreateCubeTexture_PC(GfxImage *image, unsigned short edgeLen, int mipmapCount, int imageFlags,
                                DXGI_FORMAT imageFormat, const D3D11_SUBRESOURCE_DATA *initData)
{
	D3D11_TEXTURE2D_DESC desc;

	image->width = edgeLen;
	image->height = edgeLen;
	image->depth = 1;
	image->mapType = MAPTYPE_CUBE;
	desc.Usage = D3D11_USAGE_DEFAULT;
	desc.BindFlags = 0;
	desc.CPUAccessFlags = 0;
	desc.Width = edgeLen;
	desc.Height = edgeLen;
	desc.MipLevels = mipmapCount;
	desc.ArraySize = 6;
	desc.Format = sub_14062E8A0(imageFormat);
	desc.SampleDesc.Count = 1;
	desc.SampleDesc.Quality = 0;
	desc.MiscFlags = 4;  // D3D11_RESOURCE_MISC_TEXTURECUBE
	sub_14062E820(imageFlags, &desc.Usage, &desc.BindFlags, &desc.CPUAccessFlags);
	ComCall<long>(dx.d3d11device, DEV_CreateTexture2D, &desc, initData, &image->texture.basemap.cubemap);
	if (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE)
		ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, image->texture.basemap.resource,
		              (const D3D11_SHADER_RESOURCE_VIEW_DESC *)nullptr, &image->texture.shaderView);
	else
		image->texture.shaderView = nullptr;
	sub_1401B0040(image);
}

// Store 14062B110 (name unknown): creates a texture like the image's at stream level `picmip` (the image itself is
// left alone; its texture and views are returned in `outTexture`)
void sub_14062B110(GfxImage *image, unsigned int picmip, GfxTexture *outTexture)
{
	GfxImage streamed = *image;

	streamed.texture.basemap.map = nullptr;
	sub_14062DA40(&streamed, picmip);
	if (streamed.mapType == MAPTYPE_2D)
		Image_Create2DTexture_PC(&streamed, streamed.width, streamed.height, streamed.levelCount, 0, streamed.format,
		                         nullptr);
	else if (streamed.mapType == MAPTYPE_3D)
		Image_Create3DTexture_PC(&streamed, streamed.width, streamed.height, streamed.depth, streamed.levelCount, 0,
		                         streamed.format, nullptr);
	else if (streamed.mapType == MAPTYPE_ARRAY)
		sub_14062AF40(&streamed, streamed.width, streamed.height, streamed.numElements, streamed.levelCount, 0,
		              streamed.format, nullptr);
	else
		Image_CreateCubeTexture_PC(&streamed, streamed.width, streamed.levelCount, 0, streamed.format, nullptr);
	*outTexture = streamed.texture;
}

// Store 14062B310 (gfx_d3d/r_image.cpp:2731)
ID3D11RenderTargetView *Image_GetColorRenderTarget(unsigned int imageProgType, GfxImage *image, int imageFlags,
                                                   DXGI_FORMAT format)
{
	D3D11_RENDER_TARGET_VIEW_DESC viewDesc;
	ID3D11RenderTargetView *surface;

	viewDesc.Format = format;
	if (imageFlags & IMG_FLAG_MULTISAMPLE)
	{
		viewDesc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2DMS;
	}
	else
	{
		viewDesc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
		viewDesc.MipSlice = 0;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateRenderTargetView, image->texture.basemap.resource, &viewDesc, &surface);
	return surface;
}

// Store 14062B360 (gfx_d3d/r_image.cpp:2709)
ID3D11DepthStencilView *Image_GetDepthStencilRenderTarget(unsigned int imageProgType, GfxImage *image)
{
	D3D11_DEPTH_STENCIL_VIEW_DESC depthStencilViewDesc;
	ID3D11DepthStencilView *surface;

	if (imageProgType < 2)
		depthStencilViewDesc.Format = sub_14064F350();
	else
		depthStencilViewDesc.Format = sub_14064F310();
	depthStencilViewDesc.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
	depthStencilViewDesc.Flags = 0;
	depthStencilViewDesc.MipSlice = 0;
	ComCall<long>(dx.d3d11device, DEV_CreateDepthStencilView, image->texture.basemap.resource, &depthStencilViewDesc,
	              &surface);
	return surface;
}

// Store 14062B580 (name unknown): uploads stream level `picmip` of the image from `data` into `texture`, made by
// sub_14062B110: every face and mip level when picmip is not 0 or the level has one mip, else only as many mips as
// the full image has
void sub_14062B580(GfxTexture *texture, GfxImage *image, unsigned int picmip, const unsigned char *data)
{
	D3D11_SUBRESOURCE_DATA initData[4096];
	int faceCount;
	unsigned int levelCount;
	int uploadCount;
	DXGI_FORMAT format;

	if (image->mapType == MAPTYPE_CUBE)
		faceCount = 6;
	else if (image->mapType == MAPTYPE_ARRAY)
		faceCount = image->numElements;
	else
		faceCount = 1;
	GfxImageStreamLevel *level = &image->streamLevels[picmip];
	levelCount = image->streamLevels[picmip].cardMemoryAndLevelCount >> 26;
	format = image->format;
	if (picmip == 0 && levelCount > 1)
		uploadCount = Image_CountMipmaps(0, level->width, level->height, image->depth);
	else
		uploadCount = 1;
	for (int faceIndex = 0; faceIndex < faceCount; faceIndex++)
	{
		int face;
		if (faceCount == 1)
			face = 0;
		else if (image->mapType == MAPTYPE_ARRAY)
			face = faceIndex;
		else
			face = Image_CubemapFace(faceIndex);
		D3D11_SUBRESOURCE_DATA *sub = &initData[face * levelCount];
		for (int mipLevel = 0; mipLevel < (int)levelCount; mipLevel++)
		{
			unsigned int width = level->width >> mipLevel;
			if (width <= 1)
				width = 1;
			unsigned int height = level->height >> mipLevel;
			if (height <= 1)
				height = 1;
			unsigned int depth = image->depth >> mipLevel;
			sub->pSysMem = data;
			sub->SysMemPitch = Image_GetCardMemoryAmountForMipLevel(format, width, 1, 1);
			sub->SysMemSlicePitch = Image_GetCardMemoryAmountForMipLevel(format, width, height, 1);
			if (depth <= 1)
				depth = 1;
			data += Image_GetCardMemoryAmountForMipLevel(format, width, height, depth);
			sub++;
		}
	}
	for (int faceIndex = 0; faceIndex < faceCount; faceIndex++)
	{
		int face;
		if (faceCount == 1)
			face = 0;
		else if (image->mapType == MAPTYPE_ARRAY)
			face = faceIndex;
		else
			face = Image_CubemapFace(faceIndex);
		for (int mipLevel = 0; mipLevel < uploadCount; mipLevel++)
		{
			const D3D11_SUBRESOURCE_DATA *sub = &initData[face * levelCount + mipLevel];
			ComCall<void>(dx.immediateContext, CTX_UpdateSubresource, texture->basemap.resource,
			              face * levelCount + mipLevel, (const void *)nullptr, sub->pSysMem, sub->SysMemPitch,
			              sub->SysMemSlicePitch);
		}
	}
}

// Store 14062B960 (gfx_d3d/r_image.cpp:954)
void Image_SetTextureDescMSAASettings(D3D11_TEXTURE2D_DESC *texDesc, unsigned int imageFlags)
{
	if (imageFlags & IMG_FLAG_MULTISAMPLE)
	{
		texDesc->SampleDesc.Count = unk_14A3852BC;
		texDesc->SampleDesc.Quality = D3D11_STANDARD_MULTISAMPLE_PATTERN;
	}
	else
	{
		texDesc->SampleDesc.Count = 1;
		texDesc->SampleDesc.Quality = 0;
	}
}

// Store 14062B980 (gfx_d3d/r_image.cpp:1405)
void Image_SetupRenderTarget(GfxImage *image, unsigned short width, unsigned short height, int imageFlags,
                             DXGI_FORMAT imageFormat, const char *name)
{
	Image_SetupAndLoad(image, width, height, 1, imageFlags | IMG_FLAG_RENDERTARGET | IMG_FLAG_NOMIPMAPS | 1,
	                   imageFormat, name);
}

// Store 14062B9C0 (gfx_d3d/r_image.cpp:1388)
void Image_SetupRenderTargetDepth(GfxImage *image, unsigned short width, unsigned short height, int imageFlags,
                                  DXGI_FORMAT imageFormat, const char *name)
{
	Image_SetupAndLoad(image, width, height, 1,
	                   imageFlags | IMG_FLAG_TYPELESS | IMG_FLAG_DEPTH | IMG_FLAG_RENDERTARGET | IMG_FLAG_NOMIPMAPS | 1,
	                   imageFormat, name);
}

// Store 14062BA00 (gfx_d3d/r_image.cpp:1372)
void Image_SetupRenderTargetTypeless(GfxImage *image, unsigned short width, unsigned short height, int imageFlags,
                                     DXGI_FORMAT imageFormat, const char *name)
{
	Image_SetupAndLoad(image, width, height, 1,
	                   imageFlags | IMG_FLAG_TYPELESS | IMG_FLAG_RENDERTARGET | IMG_FLAG_NOMIPMAPS | 1, imageFormat,
	                   name);
}

// Store 14062BA40 (gfx_d3d/r_image.cpp:1421)
void Image_SetupRenderTargetWithMips(GfxImage *image, unsigned short width, unsigned short height,
                                     DXGI_FORMAT imageFormat, const char *name)
{
	Image_SetupAndLoad(image, width, height, 1, IMG_FLAG_RENDERTARGET | 1, imageFormat, name);
}

// Store 14062BA80 (gfx_d3d/r_image.cpp, Black Ops' Load_Texture:930). In the Store build the load def is the
// texture data itself: every face's mip levels one after the other.
void Load_Texture(GfxImageLoadDef **remoteLoadDef, GfxImage *image)
{
	D3D11_SUBRESOURCE_DATA initData[4096];

	image->texture.basemap.map = nullptr;
	if (!r_loadForRenderer->current.enabled)
		return;
	DXGI_FORMAT imageFormat = image->format;
	if (image->category == IMG_CATEGORY_WATER)
	{
		int picmip = r_picmip_water->current.integer;
		image->cardMemory.platform[0] = 0;
		image->cardMemory.platform[1] = 0;
		unsigned int width = image->width >> picmip;
		unsigned int height = image->height >> picmip;
		Image_Create2DTexture_PC(image, width < 4 ? 4 : width, height < 4 ? 4 : height, image->levelCount,
		                         (image->flags & 0x20) ? IMG_FLAG_STAGING | IMG_FLAG_CPU_WRITE : IMG_FLAG_GENERATE_MIPS,
		                         imageFormat, nullptr);
		return;
	}
	int faceCount;
	if (image->mapType == MAPTYPE_CUBE)
		faceCount = 6;
	else if (image->mapType == MAPTYPE_ARRAY)
		faceCount = image->numElements;
	else
		faceCount = 1;
	int levelCount = image->levelCount;
	const unsigned char *data = (const unsigned char *)*remoteLoadDef;
	for (int faceIndex = 0; faceIndex < faceCount; faceIndex++)
	{
		int face;
		if (faceCount == 1)
			face = 0;
		else if (image->mapType == MAPTYPE_ARRAY)
			face = faceIndex;
		else
			face = Image_CubemapFace(faceIndex);
		D3D11_SUBRESOURCE_DATA *sub = &initData[face * levelCount];
		for (int mipLevel = 0; mipLevel < levelCount; mipLevel++)
		{
			unsigned int width = image->width >> mipLevel;
			if (width <= 1)
				width = 1;
			unsigned int height = image->height >> mipLevel;
			if (height <= 1)
				height = 1;
			unsigned int depth = image->depth >> mipLevel;
			sub->pSysMem = data;
			sub->SysMemPitch = Image_GetCardMemoryAmountForMipLevel(imageFormat, width, 1, 1);
			sub->SysMemSlicePitch = Image_GetCardMemoryAmountForMipLevel(imageFormat, width, height, 1);
			if (depth <= 1)
				depth = 1;
			data += Image_GetCardMemoryAmountForMipLevel(imageFormat, width, height, depth);
			sub++;
		}
	}
	if (image->mapType == MAPTYPE_2D)
		Image_Create2DTexture_PC(image, image->width, image->height, image->levelCount, 0, imageFormat, initData);
	else if (image->mapType == MAPTYPE_3D)
		Image_Create3DTexture_PC(image, image->width, image->height, image->depth, image->levelCount, 0, imageFormat,
		                         initData);
	else if (image->mapType == MAPTYPE_ARRAY)
		sub_14062AF40(image, image->width, image->height, image->numElements, image->levelCount, 0, imageFormat,
		              initData);
	else
		Image_CreateCubeTexture_PC(image, image->width, image->levelCount, 0, imageFormat, initData);
}

// Store 14062C040 (gfx_d3d/r_image.cpp:2828)
void R_InitDefaultDepthImage()
{
	D3D11_SUBRESOURCE_DATA data;
	unsigned int defaults[16];

	for (int i = 0; i < 16; i++)
		defaults[i] = 0;
	GfxImage *image = Image_AllocProg(IMAGE_PROG_DEFAULT_DEPTH, 4, 1);
	data.pSysMem = defaults;
	data.SysMemPitch = 16;
	data.SysMemSlicePitch = 0;
	Image_Setup(image, 4, 4, 1, 1, IMG_FLAG_TYPELESS | IMG_FLAG_DEPTH | IMG_FLAG_NOMIPMAPS | 1, sub_14064F350(),
	            "default_depth", &data);
	g_defaultDepthImage = image;
}

// Store 14062C3D0 (gfx_d3d/r_image.cpp:715)
DXGI_FORMAT R_MakeSRGBFormat(DXGI_FORMAT format)
{
	switch (format)
	{
	case DXGI_FORMAT_R8G8B8A8_TYPELESS:
	case DXGI_FORMAT_R8G8B8A8_UNORM:
	case DXGI_FORMAT_R8G8B8A8_UINT:
	case DXGI_FORMAT_R8G8B8A8_SNORM:
	case DXGI_FORMAT_R8G8B8A8_SINT:
		return DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
	case DXGI_FORMAT_BC1_TYPELESS:
	case DXGI_FORMAT_BC1_UNORM:
		return DXGI_FORMAT_BC1_UNORM_SRGB;
	case DXGI_FORMAT_BC2_TYPELESS:
	case DXGI_FORMAT_BC2_UNORM:
		return DXGI_FORMAT_BC2_UNORM_SRGB;
	case DXGI_FORMAT_BC3_TYPELESS:
	case DXGI_FORMAT_BC3_UNORM:
		return DXGI_FORMAT_BC3_UNORM_SRGB;
	default:
		return format;
	}
}

// Store 14062C460 (name unknown): the typeless format of a format's family
DXGI_FORMAT sub_14062C460(DXGI_FORMAT format)
{
	switch (format)
	{
	case DXGI_FORMAT_R32G32_FLOAT:
		return DXGI_FORMAT_R32G32_TYPELESS;
	case DXGI_FORMAT_D32_FLOAT_S8X24_UINT:
	case DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS:
		return DXGI_FORMAT_R32G8X24_TYPELESS;
	case DXGI_FORMAT_R8G8B8A8_UNORM:
	case DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:
	case DXGI_FORMAT_R8G8B8A8_UINT:
	case DXGI_FORMAT_R8G8B8A8_SNORM:
	case DXGI_FORMAT_R8G8B8A8_SINT:
		return DXGI_FORMAT_R8G8B8A8_TYPELESS;
	case DXGI_FORMAT_D32_FLOAT:
	case DXGI_FORMAT_R32_FLOAT:
		return DXGI_FORMAT_R32_TYPELESS;
	case DXGI_FORMAT_R16_FLOAT:
	case DXGI_FORMAT_D16_UNORM:
		return DXGI_FORMAT_R16_TYPELESS;
	case DXGI_FORMAT_BC1_UNORM:
	case DXGI_FORMAT_BC1_UNORM_SRGB:
		return DXGI_FORMAT_BC1_TYPELESS;
	case DXGI_FORMAT_BC2_UNORM:
	case DXGI_FORMAT_BC2_UNORM_SRGB:
		return DXGI_FORMAT_BC2_TYPELESS;
	case DXGI_FORMAT_BC3_UNORM:
	case DXGI_FORMAT_BC3_UNORM_SRGB:
		return DXGI_FORMAT_BC3_TYPELESS;
	default:
		return format;
	}
}

// Store 14062DA40 (name unknown): makes stream level `picmip` the image's current size
void sub_14062DA40(GfxImage *image, unsigned int picmip)
{
	image->levelCount = image->streamLevels[picmip].cardMemoryAndLevelCount >> 26;
	image->width = image->streamLevels[picmip].width;
	image->height = image->streamLevels[picmip].height;
	image->cardMemory.platform[0] = image->streamLevels[picmip].cardMemoryAndLevelCount & 0x3ffffff;
}

static_assert(sizeof(GfxImage) == 0x68, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, format) == 0x18, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, mapType) == 0x1c, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, semantic) == 0x1d, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, category) == 0x1e, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, flags) == 0x1f, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, cardMemory) == 0x24, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, width) == 0x2c, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, numElements) == 0x32, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, levelCount) == 0x34, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, streamLevels) == 0x40, "GfxImage (Store)");
static_assert(__builtin_offsetof(GfxImage, name) == 0x60, "GfxImage (Store)");
static_assert(sizeof(D3D11_TEXTURE1D_DESC) == 0x20, "D3D11_TEXTURE1D_DESC");
static_assert(sizeof(D3D11_TEXTURE2D_DESC) == 0x2c, "D3D11_TEXTURE2D_DESC");
static_assert(__builtin_offsetof(D3D11_TEXTURE2D_DESC, Usage) == 0x1c, "D3D11_TEXTURE2D_DESC");
static_assert(sizeof(D3D11_TEXTURE3D_DESC) == 0x24, "D3D11_TEXTURE3D_DESC");
static_assert(sizeof(D3D11_SHADER_RESOURCE_VIEW_DESC) == 0x18, "D3D11_SHADER_RESOURCE_VIEW_DESC");
static_assert(sizeof(D3D11_RENDER_TARGET_VIEW_DESC) == 0x14, "D3D11_RENDER_TARGET_VIEW_DESC");
static_assert(sizeof(D3D11_DEPTH_STENCIL_VIEW_DESC) == 0x18, "D3D11_DEPTH_STENCIL_VIEW_DESC");
static_assert(sizeof(D3D11_SUBRESOURCE_DATA) == 0x10, "D3D11_SUBRESOURCE_DATA");
