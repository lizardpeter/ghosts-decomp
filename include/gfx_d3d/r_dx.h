// gfx_d3d/r_dx.h: the renderer's Direct3D globals (DxGlobals), Store-build layout.
//
// The Xbox One server PDB (iw6_ds_xb3) has DxGlobals (0x7d38 bytes); the Store build's starts the same way
// (verified: D3D11CreateDevice stores the device at +0x08 and the feature level at +0x38, CreateDXGIFactory the
// factory at +0x20). Only the fields reconstructed code uses are spelled out.
#pragma once

struct ID3D11Device;
struct ID3D11DeviceContext;
struct IDXGIFactory;
struct IDXGIAdapter;
struct IDXGIOutput;

struct DxGlobals
{
	void *hinst;
	ID3D11Device *d3d11device;
	ID3D11DeviceContext *immediateContext;
	int immediateContextLockCount;
	unsigned int immediateContextThreadId;
	IDXGIFactory *dxgiFactory;
	IDXGIAdapter *dxgiAdapter;
	IDXGIOutput *dxgiOutput;
	int d3d11FeatureLevel;
	// the rest is not needed yet
};

extern DxGlobals dx;  // gfx_d3d/r_init.cpp
