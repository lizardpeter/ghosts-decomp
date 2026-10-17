// gfx_d3d/r_rendertarget.cpp (Store build)
//
// Render targets: their images, render-target, depth-stencil and shader views, from the Microsoft Store build.
// Names and prototypes from the servers' PDBs (gfx_d3d/r_rendertarget.cpp, iw6_ds_xb3/iw6_ds_ps4), whose render
// target code is compiled but mostly runs against stubbed images; R_ShareRenderTarget from Black Ops' PDB.
//
// The Store build's GfxRenderTarget has a second image-and-surface pair, the multisampled one (GFX_MSAA_STATE_ON),
// and its render target ids are one higher than the servers' from R_RENDERTARGET_LETTERBOX_FRAME_BUFFER on.

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"

#define IW6_SOURCE "gfx_d3d/r_rendertarget.cpp"
#include <iw6_static.h>

struct DxGlobalSceneImageSet
{
	GfxImage *rawFloatZImage;
	GfxImage *rawStencilImage;
	GfxImage *rawPipFloatZImage;
};

// the image prog and name of a render target's multisampled surface
struct MultisampledRenderTargetDef
{
	unsigned short renderTargetId;
	unsigned short imageProgType;
	const char *name;
};

extern GfxRenderTarget gfxRenderTargets[];
extern bool g_allocateMinimalResources;
IW6_STATIC const char *s_renderTargetNames[] IW6_AT("", "s_renderTargetNames");
extern const MultisampledRenderTargetDef unk_1408A9070[12];  // name unknown
extern "C" const GUID IID_ID3D11Texture2D;  // dxguid

// DxGlobals fields of the Store build (names from the Xbox One server's DxGlobals where the use matches)
extern unsigned int unk_14A3852BC;                       // the multisample count
extern IDXGISwapChain *unk_14A385300;                    // the window's swap chain
extern ID3D11Resource *unk_14A385308;                    // the scene's depth-stencil texture
extern ID3D11DepthStencilView *unk_14A3852C8;            // singleSampleDepthStencilSurface
extern ID3D11ShaderResourceView *unk_14A3852D0;          // singleSampleDepthShaderView
extern ID3D11DepthStencilView *unk_14A3852D8;            // the multisampled depth-stencil surface
extern ID3D11ShaderResourceView *unk_14A3852E0;          // its shader view
extern DxGlobalSceneImageSet unk_14A385350[GFX_MSAA_STATE_COUNT];  // sceneImageSets

void R_InitRenderTargetImage(int imageProgType, unsigned short width, unsigned short height,
                             unsigned long long imageFlagsArg, DXGI_FORMAT format, RenderTargetUsage usage,
                             GfxRenderTarget *renderTarget);
void R_InitFullscreenRenderTargetImage(int imageProgType, FullscreenType screenType, int picmip,
                                       unsigned long long imageFlagsArg, DXGI_FORMAT format, RenderTargetUsage usage,
                                       GfxRenderTarget *renderTarget);
void R_ShareRenderTarget(GfxRenderTargetId idFrom, GfxRenderTargetId idTo);

// gfx_d3d/r_rendertarget.cpp:688, inlined in the Store build
static DXGI_FORMAT R_MakeNonTypelessFormat(DXGI_FORMAT format)
{
	switch (format)
	{
	case DXGI_FORMAT_R32G32_TYPELESS:
		return DXGI_FORMAT_R32G32_FLOAT;
	case DXGI_FORMAT_R8G8B8A8_TYPELESS:
		return DXGI_FORMAT_R8G8B8A8_UNORM;
	case DXGI_FORMAT_R32_TYPELESS:
		return DXGI_FORMAT_R32_FLOAT;
	case DXGI_FORMAT_R16_TYPELESS:
		return DXGI_FORMAT_R16_UNORM;
	case DXGI_FORMAT_BC1_TYPELESS:
		return DXGI_FORMAT_BC1_UNORM;
	case DXGI_FORMAT_BC2_TYPELESS:
		return DXGI_FORMAT_BC2_UNORM;
	case DXGI_FORMAT_BC3_TYPELESS:
		return DXGI_FORMAT_BC3_UNORM;
	default:
		return format;
	}
}

// Store 14064E3A0 (gfx_d3d/r_rendertarget.cpp:1716): a scene-sized D32S8 depth-stencil texture, its depth-stencil
// view (returned) and a shader view of its depth
ID3D11DepthStencilView *R_CreateDepthStencilSurface(unsigned int imageFlags, ID3D11ShaderResourceView **outShaderView)
{
	D3D11_TEXTURE2D_DESC texDesc;
	D3D11_DEPTH_STENCIL_VIEW_DESC viewDesc;
	D3D11_SHADER_RESOURCE_VIEW_DESC shaderViewDesc;
	ID3D11Texture2D *texture;
	ID3D11DepthStencilView *depthStencilView;

	texDesc.Width = vidConfig.sceneWidth;
	texDesc.Height = vidConfig.sceneHeight;
	texDesc.SampleDesc.Count = 0;
	texDesc.SampleDesc.Quality = 0;
	texDesc.MipLevels = 1;
	texDesc.ArraySize = 1;
	texDesc.Format = DXGI_FORMAT_R32G8X24_TYPELESS;
	texDesc.Usage = D3D11_USAGE_DEFAULT;
	texDesc.BindFlags = D3D11_BIND_DEPTH_STENCIL | D3D11_BIND_SHADER_RESOURCE;
	texDesc.CPUAccessFlags = 0;
	texDesc.MiscFlags = 0;
	Image_SetTextureDescMSAASettings(&texDesc, imageFlags);
	ComCall<long>(dx.d3d11device, DEV_CreateTexture2D, &texDesc, (const D3D11_SUBRESOURCE_DATA *)nullptr, &texture);
	viewDesc.Format = DXGI_FORMAT_D32_FLOAT_S8X24_UINT;
	viewDesc.ViewDimension = (imageFlags & IMG_FLAG_MULTISAMPLE) ? D3D11_DSV_DIMENSION_TEXTURE2DMS
	                                                             : D3D11_DSV_DIMENSION_TEXTURE2D;
	viewDesc.Flags = 0;
	viewDesc.raw[0] = 0;
	viewDesc.raw[1] = 0;
	viewDesc.raw[2] = 0;
	ComCall<long>(dx.d3d11device, DEV_CreateDepthStencilView, texture, &viewDesc, &depthStencilView);
	shaderViewDesc.Format = DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS;
	shaderViewDesc.raw[0] = 0;
	shaderViewDesc.raw[1] = 0;
	shaderViewDesc.raw[2] = 0;
	shaderViewDesc.raw[3] = 0;
	if (imageFlags & IMG_FLAG_MULTISAMPLE)
	{
		shaderViewDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2DMS;
	}
	else
	{
		shaderViewDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
		shaderViewDesc.Texture.MipLevels = 1;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, texture, &shaderViewDesc, outShaderView);
	ComCall<unsigned long>(texture, UNK_Release);
	return depthStencilView;
}

// Store 14064F360 (gfx_d3d/r_rendertarget.cpp:1168): an image whose shader view reads the depth of a render
// target's depth-stencil surface
GfxImage *R_InitDepthOrStencilViewImage(int imageProgType, GfxRenderTarget *renderTarget, DXGI_FORMAT format,
                                        GfxMSAAState msaaState)
{
	D3D11_SHADER_RESOURCE_VIEW_DESC resourceDesc;
	ID3D11Resource *resource;

	GfxImage *image = Image_AllocProg(imageProgType, IMG_CATEGORY_RENDERTARGET, 0);
	ComCall<void>(renderTarget->imageAndSurfaces[msaaState].surface.depthStencil, VIEW_GetResource, &resource);
	resourceDesc.Format = format;
	resourceDesc.raw[0] = 0;
	resourceDesc.raw[1] = 0;
	resourceDesc.raw[2] = 0;
	resourceDesc.raw[3] = 0;
	if (msaaState == GFX_MSAA_STATE_ON)
	{
		resourceDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2DMS;
	}
	else
	{
		resourceDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
		resourceDesc.Texture.MipLevels = 1;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, resource, &resourceDesc, &image->texture.shaderView);
	ComCall<unsigned long>(resource, UNK_Release);
	image->width = renderTarget->width;
	image->height = renderTarget->height;
	image->depth = 1;
	return image;
}

// Store 14064F420 (gfx_d3d/r_rendertarget.cpp:3260, with R_InitFrameBufferRenderTarget_PC and
// R_InitSceneBufferRenderTarget_PC inlined): the back buffer's views, the scene render target and the resolved
// scene; returns the back buffer's format
DXGI_FORMAT R_InitFrameBufferRenderTarget()
{
	ID3D11Texture2D *backBuffer;
	ID3D11RenderTargetView *backBufferView;
	ID3D11RenderTargetView *framebufferGammaView;
	ID3D11Resource *resource;
	D3D11_RENDER_TARGET_VIEW_DESC backBufferViewDesc;
	D3D11_RENDER_TARGET_VIEW_DESC srgbFramebufferViewDesc;
	D3D11_RENDER_TARGET_VIEW_DESC desc;

	ComCall<long>(unk_14A385300, SWAPCHAIN_GetBuffer, 0u, &IID_ID3D11Texture2D, &backBuffer);
	ComCall<long>(dx.d3d11device, DEV_CreateRenderTargetView, backBuffer,
	              (const D3D11_RENDER_TARGET_VIEW_DESC *)nullptr, &backBufferView);
	ComCall<void>(backBufferView, RTV_GetDesc, &backBufferViewDesc);
	GfxRenderTarget *letterbox = &gfxRenderTargets[R_RENDERTARGET_LETTERBOX_FRAME_BUFFER];
	letterbox->imageAndSurfaces[0].image = nullptr;
	letterbox->imageAndSurfaces[0].surface.color = nullptr;
	letterbox->imageAndSurfaces[0].surface.depthStencil = nullptr;
	letterbox->imageAndSurfaces[0].surface.colorGamma = nullptr;
	letterbox->imageAndSurfaces[1].image = nullptr;
	letterbox->imageAndSurfaces[1].surface.color = nullptr;
	letterbox->imageAndSurfaces[1].surface.depthStencil = nullptr;
	letterbox->imageAndSurfaces[1].surface.colorGamma = nullptr;
	letterbox->width = 0;
	letterbox->height = 0;
	*(unsigned long long *)&letterbox->format = 0;
	if (vidConfig.letterbox4x3)
	{
		letterbox->imageAndSurfaces[0].surface.color = backBufferView;
		letterbox->height = vidConfig.displayHeight;
		letterbox->imageAndSurfaces[0].image = nullptr;
		letterbox->imageAndSurfaces[0].surface.depthStencil = nullptr;
		letterbox->imageAndSurfaces[0].surface.colorGamma = nullptr;
		letterbox->width = vidConfig.displayWidth;
		letterbox->format = backBufferViewDesc.Format;
		R_InitRenderTargetImage(0x11, vidConfig.displayWidth, vidConfig.displayHeight, 0, backBufferViewDesc.Format,
		                        RENDERTARGET_USAGE_TYPELESS, &gfxRenderTargets[R_RENDERTARGET_FRAME_BUFFER]);
	}
	else
	{
		srgbFramebufferViewDesc = backBufferViewDesc;
		srgbFramebufferViewDesc.Format = R_MakeSRGBFormat(backBufferViewDesc.Format);
		ComCall<long>(dx.d3d11device, DEV_CreateRenderTargetView, backBuffer, &srgbFramebufferViewDesc,
		              &framebufferGammaView);
		GfxRenderTarget *frameBuffer = &gfxRenderTargets[R_RENDERTARGET_FRAME_BUFFER];
		frameBuffer->imageAndSurfaces[0].surface.color = backBufferView;
		frameBuffer->imageAndSurfaces[0].surface.colorGamma = framebufferGammaView;
		frameBuffer->width = vidConfig.displayWidth;
		frameBuffer->height = vidConfig.displayHeight;
		frameBuffer->imageAndSurfaces[0].surface.depthStencil = nullptr;
		frameBuffer->format = R_MakeNonTypelessFormat(srgbFramebufferViewDesc.Format);
	}
	ComCall<unsigned long>(backBuffer, UNK_Release);
	R_InitFullscreenRenderTargetImage(0x10, FULLSCREEN_SCENE, 0, unk_14A3852BC ? IMG_FLAG_MULTISAMPLE : 0,
	                                  DXGI_FORMAT_R16G16B16A16_FLOAT, RENDERTARGET_USAGE_RENDER,
	                                  &gfxRenderTargets[R_RENDERTARGET_SCENE]);
	ComCall<void>(gfxRenderTargets[R_RENDERTARGET_SCENE].imageAndSurfaces[0].surface.depthStencil, VIEW_GetResource,
	              &resource);
	unk_14A385308 = resource;
	R_ShareRenderTarget(R_RENDERTARGET_SCENE, R_RENDERTARGET_SCENE_NODEPTH);
	ComCall<void>(gfxRenderTargets[R_RENDERTARGET_FRAME_BUFFER].imageAndSurfaces[0].surface.color, RTV_GetDesc, &desc);
	if (!g_allocateMinimalResources)
	{
		R_InitRenderTargetImage(0xd, (int)vidConfig.sceneWidth <= 1 ? 1 : vidConfig.sceneWidth,
		                        (int)vidConfig.sceneHeight <= 1 ? 1 : vidConfig.sceneHeight, 0,
		                        DXGI_FORMAT_R11G11B10_FLOAT, RENDERTARGET_USAGE_TYPELESS,
		                        &gfxRenderTargets[R_RENDERTARGET_RESOLVED_SCENE]);
	}
	return desc.Format;
}

// Store 14064F720 (gfx_d3d/r_rendertarget.cpp:2450): a render target the size of the display or the scene at a
// picmip, and for rendered-to targets the shared single-sample and multisampled depth-stencil surfaces
void R_InitFullscreenRenderTargetImage(int imageProgType, FullscreenType screenType, int picmip,
                                       unsigned long long imageFlagsArg, DXGI_FORMAT format, RenderTargetUsage usage,
                                       GfxRenderTarget *renderTarget)
{
	int width = screenType == FULLSCREEN_DISPLAY ? vidConfig.displayWidth : vidConfig.sceneWidth;
	width >>= picmip;
	int height = screenType == FULLSCREEN_SCENE ? vidConfig.sceneHeight : vidConfig.displayHeight;
	height >>= picmip;
	R_InitRenderTargetImage(imageProgType, width <= 1 ? 1 : width, height <= 1 ? 1 : height, imageFlagsArg, format,
	                        usage, renderTarget);
	if (usage == RENDERTARGET_USAGE_RENDER || usage == RENDERTARGET_USAGE_RENDER_TYPELESS)
	{
		if ((imageFlagsArg & 0x104000000ull) != 0x104000000ull)
		{
			if (unk_14A3852C8)
			{
				ComCall<unsigned long>(unk_14A3852C8, UNK_AddRef);
			}
			else
			{
				unk_14A3852C8 = R_CreateDepthStencilSurface((unsigned int)imageFlagsArg & ~IMG_FLAG_MULTISAMPLE,
				                                            &unk_14A3852D0);
			}
			renderTarget->imageAndSurfaces[GFX_MSAA_STATE_OFF].surface.depthStencil = unk_14A3852C8;
		}
		if (imageFlagsArg & IMG_FLAG_MULTISAMPLE)
		{
			if (unk_14A3852D8)
				ComCall<unsigned long>(unk_14A3852D8, UNK_AddRef);
			else
				unk_14A3852D8 = R_CreateDepthStencilSurface((unsigned int)imageFlagsArg, &unk_14A3852E0);
			renderTarget->imageAndSurfaces[GFX_MSAA_STATE_ON].surface.depthStencil = unk_14A3852D8;
		}
	}
}

// Store 140650140 (gfx_d3d/r_rendertarget.cpp:2160): a render target image and its view(s) by usage
void R_InitImageAndSurface(GfxImageAndSurface *outImageAndSurface, int imageProgType, unsigned short width,
                           unsigned short height, int imageFlags, DXGI_FORMAT format, RenderTargetUsage usage,
                           const char *imageName)
{
	GfxImage *image = Image_AllocProg(imageProgType, IMG_CATEGORY_RENDERTARGET, 0);
	outImageAndSurface->image = image;
	if (usage == RENDERTARGET_USAGE_TYPELESS || usage == RENDERTARGET_USAGE_RENDER_TYPELESS)
		Image_SetupRenderTargetTypeless(image, width, height, imageFlags, format, imageName);
	else if (usage == RENDERTARGET_USAGE_DEPTH)
		Image_SetupRenderTargetDepth(image, width, height, imageFlags, format, imageName);
	else if (usage == RENDERTARGET_USAGE_TEXTURE_WITH_MIPS)
		Image_SetupRenderTargetWithMips(image, width, height, format, imageName);
	else
		Image_SetupRenderTarget(image, width, height, imageFlags, format, imageName);
	if (usage == RENDERTARGET_USAGE_DEPTH)
	{
		outImageAndSurface->surface.depthStencil =
			Image_GetDepthStencilRenderTarget(imageProgType, outImageAndSurface->image);
	}
	else if (usage == RENDERTARGET_USAGE_TYPELESS || usage == RENDERTARGET_USAGE_RENDER_TYPELESS)
	{
		image = outImageAndSurface->image;
		outImageAndSurface->surface.color = Image_GetColorRenderTarget(imageProgType, image, imageFlags, format);
		outImageAndSurface->surface.colorGamma =
			Image_GetColorRenderTarget(imageProgType, image, imageFlags, R_MakeSRGBFormat(format));
	}
	else
	{
		outImageAndSurface->surface.color =
			Image_GetColorRenderTarget(imageProgType, outImageAndSurface->image, imageFlags, format);
	}
}

// Store 1406502B0 (gfx_d3d/r_rendertarget.cpp:3626, with R_PIPGeneralInitRenderTargets inlined): the
// picture-in-picture scene, its depth-stencil surfaces and float-z images, and the 512x512 PIP targets
void R_InitPIPRenderTargets(unsigned short width, unsigned short height)
{
	D3D11_TEXTURE2D_DESC desc;
	D3D11_DEPTH_STENCIL_VIEW_DESC viewDesc;
	ID3D11Texture2D *texture;

	GfxRenderTarget *pipScene = &gfxRenderTargets[R_RENDERTARGET_PIP_SCENE];
	R_InitRenderTargetImage(8, width, height, unk_14A3852BC ? IMG_FLAG_MULTISAMPLE : 0, DXGI_FORMAT_R16G16B16A16_FLOAT,
	                        RENDERTARGET_USAGE_RENDER, pipScene);
	int msaaStateCount = unk_14A3852BC ? GFX_MSAA_STATE_COUNT : 1;
	for (int msaaState = 0; msaaState != msaaStateCount; msaaState++)
	{
		desc.Width = pipScene->width;
		desc.Height = pipScene->height;
		desc.MipLevels = 1;
		desc.ArraySize = 1;
		desc.Format = DXGI_FORMAT_R32G8X24_TYPELESS;
		desc.SampleDesc.Count = 0;
		desc.SampleDesc.Quality = 0;
		desc.Usage = D3D11_USAGE_DEFAULT;
		desc.BindFlags = D3D11_BIND_DEPTH_STENCIL | D3D11_BIND_SHADER_RESOURCE;
		desc.CPUAccessFlags = 0;
		desc.MiscFlags = 0;
		Image_SetTextureDescMSAASettings(&desc, msaaState == GFX_MSAA_STATE_ON ? IMG_FLAG_MULTISAMPLE : 0);
		ComCall<long>(dx.d3d11device, DEV_CreateTexture2D, &desc, (const D3D11_SUBRESOURCE_DATA *)nullptr, &texture);
		viewDesc.Format = DXGI_FORMAT_D32_FLOAT_S8X24_UINT;
		viewDesc.ViewDimension =
			msaaState == GFX_MSAA_STATE_ON ? D3D11_DSV_DIMENSION_TEXTURE2DMS : D3D11_DSV_DIMENSION_TEXTURE2D;
		viewDesc.Flags = 0;
		viewDesc.raw[0] = 0;
		viewDesc.raw[1] = 0;
		viewDesc.raw[2] = 0;
		ComCall<long>(dx.d3d11device, DEV_CreateDepthStencilView, texture, &viewDesc,
		              &pipScene->imageAndSurfaces[msaaState].surface.depthStencil);
		ComCall<unsigned long>(texture, UNK_Release);
	}
	R_InitRenderTargetImage(9, width, height, 0, DXGI_FORMAT_R32_FLOAT, RENDERTARGET_USAGE_TEXTURE,
	                        &gfxRenderTargets[R_RENDERTARGET_PIP_SCENE_FLOAT_Z]);
	msaaStateCount = unk_14A3852BC ? GFX_MSAA_STATE_COUNT : 1;
	for (int msaaState = 0; msaaState != msaaStateCount; msaaState++)
	{
		unk_14A385350[msaaState].rawPipFloatZImage =
			R_InitDepthOrStencilViewImage(msaaState != GFX_MSAA_STATE_ON ? 0x15 : 0x19d, pipScene,
			                              DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS, (GfxMSAAState)msaaState);
	}
	R_ShareRenderTarget(R_RENDERTARGET_PIP_SCENE, R_RENDERTARGET_PIP_SCENE_NODEPTH);
	R_InitRenderTargetImage(10, 0x200, 0x200, unk_14A3852BC ? IMG_FLAG_MULTISAMPLE : 0,
	                        DXGI_FORMAT_R16G16B16A16_FLOAT, RENDERTARGET_USAGE_RENDER,
	                        &gfxRenderTargets[R_RENDERTARGET_PIP_SCENE_PINGPONG]);
	R_InitRenderTargetImage(11, 0x200, 0x200, unk_14A3852BC ? IMG_FLAG_MULTISAMPLE : 0, DXGI_FORMAT_R8G8B8A8_UNORM,
	                        RENDERTARGET_USAGE_RENDER, &gfxRenderTargets[R_RENDERTARGET_PIP_FINAL_SCENE]);
	for (int msaaState = 0; msaaState < GFX_MSAA_STATE_COUNT; msaaState++)
	{
		ID3D11DepthStencilView *depthStencil = pipScene->imageAndSurfaces[msaaState].surface.depthStencil;
		gfxRenderTargets[R_RENDERTARGET_PIP_SCENE_PINGPONG].imageAndSurfaces[msaaState].surface.depthStencil =
			depthStencil;
		if (depthStencil)
			ComCall<unsigned long>(depthStencil, UNK_AddRef);
	}
	for (int msaaState = 0; msaaState < GFX_MSAA_STATE_COUNT; msaaState++)
	{
		ID3D11DepthStencilView *depthStencil = pipScene->imageAndSurfaces[msaaState].surface.depthStencil;
		gfxRenderTargets[R_RENDERTARGET_PIP_FINAL_SCENE].imageAndSurfaces[msaaState].surface.depthStencil =
			depthStencil;
		if (depthStencil)
			ComCall<unsigned long>(depthStencil, UNK_AddRef);
	}
	R_ShareRenderTarget(R_RENDERTARGET_PIP_SCENE_PINGPONG, R_RENDERTARGET_PIP_SCENE_PINGPONG_NODEPTH);
	R_ShareRenderTarget(R_RENDERTARGET_PIP_FINAL_SCENE, R_RENDERTARGET_PIP_FINAL_SCENE_NODEPTH);
}

// Store 1406505B0 (gfx_d3d/r_rendertarget.cpp:2236): a render target's image and surface, and for a multisampled
// target first its multisampled image and surface (unless the flags ask for that one alone)
void R_InitRenderTargetImage(int imageProgType, unsigned short width, unsigned short height,
                             unsigned long long imageFlagsArg, DXGI_FORMAT format, RenderTargetUsage usage,
                             GfxRenderTarget *renderTarget)
{
	int renderTargetId = (int)(renderTarget - gfxRenderTargets);
	const char *name = s_renderTargetNames[renderTargetId];
	int imageFlags = (int)imageFlagsArg;
	if (imageFlags & IMG_FLAG_MULTISAMPLE)
	{
		const MultisampledRenderTargetDef *def;
		for (def = unk_1408A9070; def != &unk_1408A9070[12]; def++)
		{
			if (def->renderTargetId == renderTargetId)
				break;
		}
		if (def == &unk_1408A9070[12])
			def = nullptr;
		R_InitImageAndSurface(&renderTarget->imageAndSurfaces[GFX_MSAA_STATE_ON], def->imageProgType, width, height,
		                      imageFlags, format, usage, def->name);
		imageFlags &= ~IMG_FLAG_MULTISAMPLE;
	}
	if ((imageFlagsArg & 0x104000000ull) != 0x104000000ull)
		R_InitImageAndSurface(&renderTarget->imageAndSurfaces[GFX_MSAA_STATE_OFF], imageProgType, width, height,
		                      imageFlags, format, usage, name);
	renderTarget->width = width;
	renderTarget->height = height;
	renderTarget->format = format;
}

// Store 140650700 (gfx_d3d/r_rendertarget.cpp:2307): a render target on one mip level of an image
void R_InitRenderTargetImageMipmap(int imageProgType, GfxRenderTarget *renderTarget, GfxImage *baseImage,
                                   DXGI_FORMAT format, int mipLevel)
{
	ID3D11Resource *resource;
	D3D11_SHADER_RESOURCE_VIEW_DESC viewDesc;
	D3D11_RENDER_TARGET_VIEW_DESC desc;

	unsigned int width = baseImage->width >> mipLevel;
	unsigned int height = baseImage->height >> mipLevel;
	GfxImage *image = Image_AllocProg(imageProgType, IMG_CATEGORY_RENDERTARGET, 0);
	renderTarget->imageAndSurfaces[0].image = image;
	renderTarget->width = width;
	renderTarget->height = height;
	renderTarget->format = format;
	ComCall<void>(baseImage->texture.shaderView, VIEW_GetResource, &resource);
	desc.Format = format;
	desc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
	desc.MipSlice = mipLevel;
	desc.raw[1] = 0;
	desc.raw[2] = 0;
	ComCall<long>(dx.d3d11device, DEV_CreateRenderTargetView, resource, &desc,
	              &renderTarget->imageAndSurfaces[0].surface.color);
	viewDesc.Format = format;
	viewDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
	viewDesc.Texture.MostDetailedMip = mipLevel;
	viewDesc.Texture.MipLevels = 1;
	ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, resource, &viewDesc, &image->texture.shaderView);
	ComCall<unsigned long>(resource, UNK_Release);
}

// Store 140650810 (gfx_d3d/r_rendertarget.cpp:4808): a depth render target for the cached shadows
void R_InitRenderTargetImage_CachedShadows(int imageProgType, unsigned short width, unsigned short height,
                                           int imageFlags, DXGI_FORMAT format, GfxRenderTarget *renderTarget)
{
	D3D11_DEPTH_STENCIL_VIEW_DESC desc;
	ID3D11DepthStencilView *depthStencil;

	GfxImage *image = Image_AllocProg(imageProgType, IMG_CATEGORY_RENDERTARGET, 0);
	renderTarget->imageAndSurfaces[0].image = image;
	Image_SetupRenderTargetDepth(image, width, height, imageFlags, format, image->name);
	desc.Format = format;
	desc.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
	desc.Flags = 0;
	desc.MipSlice = 0;
	ComCall<long>(dx.d3d11device, DEV_CreateDepthStencilView,
	              renderTarget->imageAndSurfaces[0].image->texture.basemap.resource, &desc, &depthStencil);
	renderTarget->width = width;
	renderTarget->format = format;
	renderTarget->imageAndSurfaces[0].surface.depthStencil = depthStencil;
	renderTarget->height = height;
}

// Store 140651310 (Black Ops' R_ShareRenderTarget, gfx_d3d/r_rendertarget.cpp:1116): another id for the same
// images and colour views (referenced again); the copy has no depth-stencil surface
void R_ShareRenderTarget(GfxRenderTargetId idFrom, GfxRenderTargetId idTo)
{
	gfxRenderTargets[idTo] = gfxRenderTargets[idFrom];
	for (int msaaState = 0; msaaState < GFX_MSAA_STATE_COUNT; msaaState++)
	{
		if (gfxRenderTargets[idTo].imageAndSurfaces[msaaState].surface.color)
			ComCall<unsigned long>(gfxRenderTargets[idTo].imageAndSurfaces[msaaState].surface.color, UNK_AddRef);
		if (gfxRenderTargets[idTo].imageAndSurfaces[msaaState].surface.colorGamma)
			ComCall<unsigned long>(gfxRenderTargets[idTo].imageAndSurfaces[msaaState].surface.colorGamma, UNK_AddRef);
	}
	for (int msaaState = 0; msaaState < GFX_MSAA_STATE_COUNT; msaaState++)
		gfxRenderTargets[idTo].imageAndSurfaces[msaaState].surface.depthStencil = nullptr;
}

static_assert(sizeof(GfxRenderTarget) == 0x50, "GfxRenderTarget (Store)");
static_assert(__builtin_offsetof(GfxRenderTarget, width) == 0x40, "GfxRenderTarget (Store)");
static_assert(__builtin_offsetof(GfxRenderTarget, format) == 0x48, "GfxRenderTarget (Store)");
static_assert(sizeof(GfxImageAndSurface) == 0x20, "GfxImageAndSurface");
static_assert(sizeof(MultisampledRenderTargetDef) == 0x10, "MultisampledRenderTargetDef");
static_assert(sizeof(DxGlobalSceneImageSet) == 0x18, "DxGlobalSceneImageSet");
static_assert(__builtin_offsetof(vidConfig_t, letterbox4x3) == 0x11, "vidConfig_t (Store)");
