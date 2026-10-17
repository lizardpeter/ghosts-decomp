// gfx_d3d/r_init.h: the renderer's device and window set-up (types from the XB3 server PDB, iw6_ds_xb3, with the
// Store build's additions).
#pragma once

#include "client/client.h"
#include "gfx_d3d/r_dx.h"

enum GfxDisplayMode : int
{
	GFX_DISPLAY_MODE_FULLSCREEN = 0,
	GFX_DISPLAY_MODE_WINDOWED_NO_BORDER = 1,
	GFX_DISPLAY_MODE_WINDOWED = 2,
};

enum GfxAspectRatio : int
{
	GFX_ASPECT_RATIO_AUTO = 0,
	GFX_ASPECT_RATIO_STANDARD = 1,
	GFX_ASPECT_RATIO_WIDE_16_10 = 2,
	GFX_ASPECT_RATIO_WIDE_16_9 = 3,
};

enum GfxImageQuality : int
{
	GFX_IMAGE_QUALITY_NATIVE = 0,
	GFX_IMAGE_QUALITY_VERYLOW = 1,
	GFX_IMAGE_QUALITY_LOW = 2,
	GFX_IMAGE_QUALITY_NORMAL = 3,
	GFX_IMAGE_QUALITY_HIGH = 4,
};

enum GfxAAMode : int
{
	GFX_AA_MODE_OFF = 0,
	GFX_AA_MODE_FXAA = 1,
	GFX_AA_MODE_MSAA2X = 2,
	GFX_AA_MODE_MSAA4X = 3,
	GFX_AA_MODE_SMAA = 4,
	GFX_AA_MODE_TXAA2X = 5,
	GFX_AA_MODE_TXAA4X = 6,
};

struct GfxRefreshRate
{
	unsigned int Numerator;
	unsigned int Denominator;
};

// The renderer settings a window is created from (R_InitGraphicsApi fills it from the dvars).
struct GfxWindowInput
{
	GfxDisplayMode displayMode;      // r_displayMode
	GfxAspectRatio aspectRatio;      // r_aspectRatio
	GfxImageQuality imageQuality;    // r_imageQuality
	GfxAAMode aaMode;                // r_aaMode
	int x;                           // vid_xpos
	int y;                           // vid_ypos
	const char *resolutionName;      // r_mode's string, "<w>x<h>"
	const char *refreshRateName;     // r_displayRefresh's string
	int ssaoMode;                    // r_ssao
	bool mbEnable;                   // r_mbEnableA
	bool omitUnusedRenderTargets;    // r_omitUnusedRenderTargets
	bool letterbox4x3;               // Store build: r_letterbox4x3 || r_forceLetterbox4x3
	bool forceLetterbox4x3;          // Store build: r_forceLetterbox4x3
};

struct GfxWindowParms
{
	struct HWND__ *hwnd;
	GfxRefreshRate hz;
	GfxDisplayMode displayMode;
	int x;
	int y;
	float aspectRatioWindow;
	unsigned short shadowTileResSmall;
	unsigned short shadowTileResLarge;
	int sceneWidth;
	int sceneHeight;
	int displayWidth;
	int displayHeight;
	unsigned char omitRTFlags;
	bool letterbox4x3;               // Store build: 16:9 forced (4:3 letterbox)
	int aaSamples;
};

static_assert(sizeof(GfxWindowInput) == 0x30, "GfxWindowInput (Store)");
static_assert(__builtin_offsetof(GfxWindowInput, resolutionName) == 0x18, "GfxWindowInput (Store)");
static_assert(__builtin_offsetof(GfxWindowInput, mbEnable) == 0x2C, "GfxWindowInput (Store)");
static_assert(sizeof(GfxWindowParms) == 0x40, "GfxWindowParms (Store)");
static_assert(__builtin_offsetof(GfxWindowParms, aspectRatioWindow) == 0x1C, "GfxWindowParms (Store)");
static_assert(__builtin_offsetof(GfxWindowParms, displayWidth) == 0x2C, "GfxWindowParms (Store)");
static_assert(__builtin_offsetof(GfxWindowParms, letterbox4x3) == 0x35, "GfxWindowParms (Store)");
static_assert(__builtin_offsetof(GfxWindowParms, aaSamples) == 0x38, "GfxWindowParms (Store)");

extern vidConfig_t vidConfig;  // gfx_d3d/r_init.cpp: the renderer's own copy (14A37D5E0 in the Store build)

bool R_CheckLostDevice();
bool R_RecoverLostDevice();
void R_ReleaseForShutdownOrReset(unsigned int frontEndFrameCount, int reset);
void R_Shutdown(int destroyWindow, int fromReset);
void R_InitRenderBuffers();
