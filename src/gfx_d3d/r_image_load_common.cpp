// gfx_d3d/r_image_load_common.cpp (Store build)
//
// Setting up images (size, creation by map type) and the size arithmetic, from the Microsoft Store build. Names
// from the servers' PDBs (gfx_d3d/r_image_load_common.cpp) or Black Ops' r_image_load_common.cpp
// (Image_CountMipmaps, Image_CubemapFace).

#include "gfx_d3d/r_image.h"
#include "qcommon/dvar.h"

extern const dvar_t *r_loadForRenderer;  // gfx_d3d/r_dvars.cpp

// Store 14062E0C0 (Black Ops' Image_CountMipmaps, gfx_d3d/r_image_load_common.cpp:1080)
unsigned int Image_CountMipmaps(unsigned int imageFlags, unsigned int width, unsigned int height, unsigned int depth)
{
	if (imageFlags & IMG_FLAG_NOMIPMAPS)
		return 1;
	unsigned int mipCount = 1;
	unsigned int mipRes = 1;
	while (mipRes < width || mipRes < height || mipRes < depth)
	{
		mipRes += mipRes;
		mipCount++;
	}
	return mipCount;
}

// Store 14062E0F0 (Black Ops' Image_CubemapFace, gfx_d3d/r_image_load_common.cpp:1718): a cube face is an array
// slice in Direct3D 11
unsigned int Image_CubemapFace(unsigned int faceIndex)
{
	return faceIndex;
}

// Store 14062E300 (gfx_d3d/r_image_load_common.cpp:441)
unsigned int Image_GetCardMemoryAmountForMipLevel(DXGI_FORMAT format, unsigned int mipWidth, unsigned int mipHeight,
                                                  unsigned int mipDepth)
{
	switch (format)
	{
	case DXGI_FORMAT_R32G32B32A32_FLOAT:
		return mipWidth * mipHeight * mipDepth * 16;
	case DXGI_FORMAT_R16G16B16A16_FLOAT:
	case DXGI_FORMAT_R16G16B16A16_UNORM:
	case DXGI_FORMAT_R32G32_FLOAT:
	case DXGI_FORMAT_R32G8X24_TYPELESS:
	case DXGI_FORMAT_D32_FLOAT_S8X24_UINT:
	case DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS:
		return mipWidth * mipHeight * mipDepth * 8;
	case DXGI_FORMAT_R11G11B10_FLOAT:
	case DXGI_FORMAT_R8G8B8A8_UNORM:
	case DXGI_FORMAT_R16G16_FLOAT:
	case DXGI_FORMAT_D32_FLOAT:
	case DXGI_FORMAT_R32_FLOAT:
	case DXGI_FORMAT_D24_UNORM_S8_UINT:
		return mipWidth * mipHeight * mipDepth * 4;
	case DXGI_FORMAT_R8G8_UNORM:
	case DXGI_FORMAT_R16_FLOAT:
	case DXGI_FORMAT_D16_UNORM:
	case DXGI_FORMAT_R16_UNORM:
		return mipWidth * mipHeight * mipDepth * 2;
	case DXGI_FORMAT_R8_UNORM:
	case DXGI_FORMAT_A8_UNORM:
		return mipWidth * mipHeight * mipDepth;
	case DXGI_FORMAT_BC1_UNORM:
	case DXGI_FORMAT_BC4_UNORM:
		return ((mipWidth + 3) >> 2) * ((mipHeight + 3) >> 2) * mipDepth * 8;
	case DXGI_FORMAT_BC2_UNORM:
	case DXGI_FORMAT_BC3_UNORM:
	case DXGI_FORMAT_BC5_UNORM:
	case DXGI_FORMAT_BC5_SNORM:
	case DXGI_FORMAT_BC6H_UF16:
	case DXGI_FORMAT_BC6H_SF16:
	case DXGI_FORMAT_BC7_UNORM:
	case DXGI_FORMAT_BC7_UNORM_SRGB:
		return ((mipWidth + 3) >> 2) * ((mipHeight + 3) >> 2) * mipDepth * 16;
	default:
		return 0;
	}
}

// Store 14062E4F0 (gfx_d3d/r_image_load_common.cpp, Image_Setup)
void Image_Setup(GfxImage *image, int width, int height, int depth, int numElements, int imageFlags,
                 DXGI_FORMAT imageFormat, const char *name, const D3D11_SUBRESOURCE_DATA *initData)
{
	if (!image->name)
		image->name = name;
	image->numElements = numElements;
	image->width = width;
	image->height = height;
	image->depth = depth;
	int mipmapCount = (imageFlags & IMG_FLAG_NOMIPMAPS) ? 1 : 0;
	if (!r_loadForRenderer->current.enabled)
		return;
	switch (imageFlags & IMG_FLAG_MAPTYPE_MASK)
	{
	case 0:
		Image_Create2DTexture_PC(image, width, height, mipmapCount, imageFlags, imageFormat, initData);
		break;
	case IMG_FLAG_MAPTYPE_CUBE:
		Image_CreateCubeTexture_PC(image, width, mipmapCount, imageFlags, imageFormat, initData);
		break;
	case IMG_FLAG_MAPTYPE_3D:
		Image_Create3DTexture_PC(image, width, height, depth, mipmapCount, imageFlags, imageFormat, initData);
		break;
	case IMG_FLAG_MAPTYPE_ARRAY:
		sub_14062AF40(image, width, height, numElements, mipmapCount, imageFlags, imageFormat, initData);
		break;
	default:
		sub_14062AC10(image, width, mipmapCount, imageFlags, imageFormat, initData);
		break;
	}
	sub_14062E8D0(image, imageFlags, imageFormat, width, height, depth, numElements);
	if (imageFlags & IMG_FLAG_TRACKED)
		image->flags |= 8;
	else
		image->flags &= ~8;
}

// Store 14062E690 (gfx_d3d/r_image_load_common.cpp, Image_SetupAndLoad)
void Image_SetupAndLoad(GfxImage *image, int width, int height, int depth, int imageFlags, DXGI_FORMAT imageFormat,
                        const char *name)
{
	if (!image->name)
		image->name = name;
	image->numElements = 1;
	image->width = width;
	image->height = height;
	image->depth = depth;
	int mipmapCount = (imageFlags & IMG_FLAG_NOMIPMAPS) ? 1 : 0;
	if (!r_loadForRenderer->current.enabled)
		return;
	switch (imageFlags & IMG_FLAG_MAPTYPE_MASK)
	{
	case 0:
		Image_Create2DTexture_PC(image, width, height, mipmapCount, imageFlags, imageFormat, nullptr);
		break;
	case IMG_FLAG_MAPTYPE_CUBE:
		Image_CreateCubeTexture_PC(image, width, mipmapCount, imageFlags, imageFormat, nullptr);
		break;
	case IMG_FLAG_MAPTYPE_3D:
		Image_Create3DTexture_PC(image, width, height, depth, mipmapCount, imageFlags, imageFormat, nullptr);
		break;
	case IMG_FLAG_MAPTYPE_ARRAY:
		sub_14062AF40(image, width, height, 1, mipmapCount, imageFlags, imageFormat, nullptr);
		break;
	default:
		sub_14062AC10(image, width, mipmapCount, imageFlags, imageFormat, nullptr);
		break;
	}
	sub_14062E8D0(image, imageFlags, imageFormat, width, height, depth, 1);
	if (imageFlags & IMG_FLAG_TRACKED)
		image->flags |= 8;
	else
		image->flags &= ~8;
}

// Store 14062E820 (name unknown): the usage, bind flags and CPU access of a texture with these image flags
void sub_14062E820(int imageFlags, D3D11_USAGE *usage, unsigned int *bindFlags, unsigned int *cpuAccessFlags)
{
	*usage = D3D11_USAGE_DEFAULT;
	*cpuAccessFlags = 0;
	*bindFlags = D3D11_BIND_SHADER_RESOURCE;
	if (imageFlags & IMG_FLAG_DYNAMIC)
	{
		*usage = D3D11_USAGE_DYNAMIC;
		*cpuAccessFlags = D3D11_CPU_ACCESS_WRITE;
	}
	if (imageFlags & IMG_FLAG_STAGING)
	{
		*usage = D3D11_USAGE_STAGING;
		*bindFlags = 0;
	}
	if (imageFlags & IMG_FLAG_GENERATE_MIPS)
		*bindFlags |= D3D11_BIND_RENDER_TARGET;
	if (imageFlags & IMG_FLAG_RENDERTARGET)
	{
		if (imageFlags & IMG_FLAG_DEPTH)
		{
			*bindFlags |= D3D11_BIND_DEPTH_STENCIL;
		}
		else
		{
			*bindFlags |= D3D11_BIND_RENDER_TARGET;
			if (!(imageFlags & IMG_FLAG_MULTISAMPLE))
				*bindFlags |= D3D11_BIND_UNORDERED_ACCESS;
		}
	}
	if (imageFlags & IMG_FLAG_CPU_READ)
		*cpuAccessFlags |= D3D11_CPU_ACCESS_READ;
	if (imageFlags & IMG_FLAG_CPU_WRITE)
		*cpuAccessFlags |= D3D11_CPU_ACCESS_WRITE;
}

// Store 14062E8A0 (name unknown): the sRGB format of a UNORM colour format (cube textures)
DXGI_FORMAT sub_14062E8A0(DXGI_FORMAT format)
{
	if (format == DXGI_FORMAT_R8G8B8A8_UNORM)
		return DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
	if (format == DXGI_FORMAT_BC1_UNORM)
		return DXGI_FORMAT_BC1_UNORM_SRGB;
	if (format == DXGI_FORMAT_BC2_UNORM)
		return DXGI_FORMAT_BC2_UNORM_SRGB;
	if (format == DXGI_FORMAT_BC3_UNORM)
		return DXGI_FORMAT_BC3_UNORM_SRGB;
	return format;
}
