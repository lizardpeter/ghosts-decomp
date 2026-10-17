// enhanced/include/enhanced/dxgi_flip.h: the DXGI 1.1-1.5 pieces the enhanced build's presentation uses, declared by
// hand like gfx_d3d/r_dxgi.h (the build has no Windows SDK). The original exe uses none of these, so unlike
// gfx_d3d/com_call.h's slots they can't be checked against a call in the Store build: they are the public
// interfaces' positions and values, and every use falls back to the original behaviour when a call fails.
#pragma once

#include "gfx_d3d/r_dxgi.h"

struct ID3D11RenderTargetView;
struct ID3D11DepthStencilView;

extern "C" HRESULT CreateDXGIFactory1(const GUID &riid, void **ppFactory);  // dxgi.dll

// {7632e1f5-ee65-4dca-87fd-84cd75f8838d}
static const GUID IID_IDXGIFactory5_Enhanced = {0x7632E1F5, 0xEE65, 0x4DCA, {0x87, 0xFD, 0x84, 0xCD, 0x75, 0xF8, 0x83, 0x8D}};
// {77db970f-6276-48ba-ba28-070143b4392c}
static const GUID IID_IDXGIDevice1_Enhanced = {0x77DB970F, 0x6276, 0x48BA, {0xBA, 0x28, 0x07, 0x01, 0x43, 0xB4, 0x39, 0x2C}};

enum EnhancedDxgiSlot : unsigned int
{
	FACTORY5_CheckFeatureSupport = 28,   // IDXGIFactory5
	DXGIDEVICE1_SetMaximumFrameLatency = 12,  // IDXGIDevice1
	CTX_OMSetRenderTargets = 33,         // ID3D11DeviceContext (checked: Store 140663172 `call [rax+0x108]`)
	CTX_OMGetRenderTargets = 89,         // ID3D11DeviceContext (checked: Store 14067066C `call [rax+0x2c8]`)
};

#define DXGI_SWAP_EFFECT_FLIP_DISCARD 4
#define DXGI_SWAP_CHAIN_FLAG_ALLOW_TEARING 0x800
#define DXGI_PRESENT_ALLOW_TEARING 0x200
#define DXGI_FEATURE_PRESENT_ALLOW_TEARING 0
