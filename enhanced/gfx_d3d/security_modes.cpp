// S23/B0036: bounded GPU mode enumeration, for the enhanced build ONLY.
// Cloned from the verified source reconstruction at src/gfx_d3d/r_init.cpp.
// The original trusted DXGI's mode count as the capacity of dx.displayModes[256],
// followed by unchecked name formatting into dx.modeText[5120].
// The source-level override and C wrapper are deliberately provided together:
// the packaged native EXE entry at 14062FC90 must jump to the wrapper too.
#include <windows.h>
#include <iw6_static.h>
#include "client/client.h"
#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_init.h"
#include "qcommon/dvar.h"

#define DXGI_ERROR_NOT_CURRENTLY_AVAILABLE ((HRESULT)0x887A0022)
#define DXGI_MODE_SCANLINE_ORDER_PROGRESSIVE 1
#define DXGI_MODE_SCALING_CENTERED 1
#define SM_CXSCREEN 0
#define SM_CYSCREEN 1
#define SM_REMOTESESSION 0x1000
extern "C" int GetSystemMetrics(int);
extern "C" void qsort(void *, unsigned long long, unsigned long long, int (*)(const void *, const void *));
extern "C" int sprintf(char *, const char *, ...);
extern "C" void *memset(void *, int, unsigned long long);
extern "C" const char *va(const char *, ...);
void Sys_DirectXFatalError();
int R_CompareDisplayModes(const void *, const void *);
int R_CompareRefreshRates(const void *, const void *);
extern const dvar_t *r_mode;
extern const dvar_t *r_displayRefresh;
extern int unk_14A346B40;
namespace {
constexpr unsigned int kModeCapacity = 256;
constexpr unsigned int kModeStagingCapacity = 4096;
// Device initialization executes on the main thread. Never address a driver
// buffer past its capacity, even if the count it reports is malicious.
DXGI_MODE_DESC stagedModes[kModeStagingCapacity];
}

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
		const unsigned int reported = dx.displayModeCount;
		const unsigned int capacity = reported <= kModeStagingCapacity ? reported : 0;
		DXGI_MODE_DESC *destination = reported > kModeCapacity ? stagedModes : dx.displayModes;
		unsigned int returned = capacity;
		const HRESULT result = capacity ?
			ComCall<HRESULT>(dx.dxgiOutput, OUTPUT_GetDisplayModeList, DXGI_FORMAT_R8G8B8A8_UNORM, 0u,
			                 &returned, destination) : (HRESULT)0x887A0003;
		if (result == 0 && returned > 0 && returned <= capacity)
		{
			// Keep higher-resolution modes when an output lists more than the
			// original 256-entry DxGlobals allocation. Never hand the driver
			// the address of that allocation with an oversize capacity.
			if (destination != dx.displayModes)
			{
				qsort(destination, returned, sizeof(destination[0]), R_CompareDisplayModes);
				const unsigned int first = returned > kModeCapacity ? returned - kModeCapacity : 0;
				const unsigned int retained = returned - first;
				for (unsigned int i = 0; i < retained; ++i) dx.displayModes[i] = destination[first + i];
				dx.displayModeCount = retained;
			}
			else dx.displayModeCount = returned;
		}
		else
		{
			// Some drivers fail rather than return partial entries, or report
			// a nonsensical count. Use a safe desktop fallback, not a partially
			// written array or the driver's unchecked count.
			dx.displayModeCount = 1;
			DXGI_MODE_DESC &fallback = dx.displayModes[0];
			fallback = {};
			fallback.Width = nativeIsValid && dx.adapterNativeWidth >= 640 ? dx.adapterNativeWidth : 800;
			fallback.Height = nativeIsValid && dx.adapterNativeHeight >= 480 ? dx.adapterNativeHeight : 600;
			fallback.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
			fallback.RefreshRate.Numerator = 60;
			fallback.RefreshRate.Denominator = 1;
		}
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
		// Reject impossible driver refresh fractions. Use 64-bit arithmetic
		// to avoid overflow before rounding, and never divide by zero.
		const unsigned long long den = mode->RefreshRate.Denominator;
		if (!den) continue;
		const unsigned long long num = mode->RefreshRate.Numerator;
		const unsigned long long rounded = (num * 2ULL + den) / (den * 2ULL);
		if (rounded == 0 || rounded > 0x7FFFFFFFULL) continue;
		refreshRate = (int)rounded;
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
		// Worst case decimal width + 'x' + height + NUL stays under 32.
		// Reserve space for at least one refresh-rate name.
		if (modeText + 64 > dx.modeText + sizeof(dx.modeText)) break;
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
	resolutionCount = resolutionIndex;
	dx.resolutionNameTable[resolutionIndex] = nullptr;
	r_mode = Dvar_RegisterEnum("r_mode", dx.resolutionNameTable, defaultResolutionIndex, 0x4003,
	                           "Direct X resolution mode");
	qsort(availableRefreshRates, refreshRateCount, sizeof(availableRefreshRates[0]), R_CompareRefreshRates);
	defaultRefreshRateIndex = 0;
	for (refreshRateIndex = 0; refreshRateIndex < refreshRateCount; ++refreshRateIndex)
	{
		// A 32-bit decimal refresh and ' Hz' fit in 32 bytes.
		if (modeText + 32 > dx.modeText + sizeof(dx.modeText)) break;
		dx.refreshRateNameTable[refreshRateIndex] = modeText;
		modeText += sprintf(modeText, "%i Hz", availableRefreshRates[refreshRateIndex]) + 1;
		if (availableRefreshRates[defaultRefreshRateIndex] < 60)
			defaultRefreshRateIndex = refreshRateIndex;
	}
	dx.refreshRateNameTable[refreshRateIndex] = nullptr;
	r_displayRefresh = Dvar_RegisterEnum("r_displayRefresh", dx.refreshRateNameTable, defaultRefreshRateIndex,
	                                     0x4003, "Refresh rate");
}

// Native Store EXE redirect, preserving the zero-argument Win64 ABI.
extern "C" void Iw6SecureEnumDisplayModes() { R_EnumDisplayModes(); }
