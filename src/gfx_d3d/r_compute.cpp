// gfx_d3d/r_compute.cpp (Store build)
//
// Compute shader buffers, from the Microsoft Store build. The servers' PDBs have R_CreateComputeConstantBuffer and
// R_DestroyComputeBuffer(View) here; the view creation functions below are unnamed (they take a debug name the
// retail build doesn't use).

// ==== BEGIN images ====
#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_image.h"

// Store 1401AC380 (name unknown): a raw (byte address) unordered access view of a buffer, in 32-bit words
void sub_1401AC380(ID3D11Buffer *buffer, const char *name, ID3D11UnorderedAccessView **outView)
{
	D3D11_BUFFER_DESC bufferDesc;
	D3D11_UNORDERED_ACCESS_VIEW_DESC viewDesc;

	ComCall<void>(buffer, BUF_GetDesc, &bufferDesc);
	viewDesc.Buffer.NumElements = bufferDesc.ByteWidth >> 2;
	viewDesc.ViewDimension = D3D11_UAV_DIMENSION_BUFFER;
	viewDesc.Buffer.FirstElement = 0;
	viewDesc.Format = DXGI_FORMAT_R32_TYPELESS;
	viewDesc.Buffer.Flags = D3D11_BUFFER_UAV_FLAG_RAW;
	ComCall<long>(dx.d3d11device, DEV_CreateUnorderedAccessView, buffer, &viewDesc, outView);
}

// Store 1401AC3F0 (name unknown): a raw shader resource view (BUFFEREX) of a buffer, in 32-bit words
void sub_1401AC3F0(ID3D11Buffer *buffer, const char *name, ID3D11ShaderResourceView **outView)
{
	D3D11_BUFFER_DESC bufferDesc;
	D3D11_SHADER_RESOURCE_VIEW_DESC viewDesc;

	ComCall<void>(buffer, BUF_GetDesc, &bufferDesc);
	viewDesc.BufferEx.NumElements = bufferDesc.ByteWidth >> 2;
	viewDesc.ViewDimension = D3D11_SRV_DIMENSION_BUFFEREX;
	viewDesc.BufferEx.FirstElement = 0;
	viewDesc.BufferEx.Flags = D3D11_BUFFEREX_SRV_FLAG_RAW;
	viewDesc.raw[3] = 0;
	viewDesc.Format = DXGI_FORMAT_R32_TYPELESS;
	ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, buffer, &viewDesc, outView);
}

// Store 1401AC4D0 (name unknown): an unordered access view of a buffer of elementSize-byte elements
void sub_1401AC4D0(ID3D11Buffer *buffer, unsigned int elementSize, const char *name,
                   ID3D11UnorderedAccessView **outView)
{
	D3D11_BUFFER_DESC bufferDesc;
	D3D11_UNORDERED_ACCESS_VIEW_DESC viewDesc;

	ComCall<void>(buffer, BUF_GetDesc, &bufferDesc);
	viewDesc.ViewDimension = D3D11_UAV_DIMENSION_BUFFER;
	viewDesc.Buffer.FirstElement = 0;
	viewDesc.Buffer.Flags = 0;
	viewDesc.Format = DXGI_FORMAT_UNKNOWN;
	viewDesc.Buffer.NumElements = bufferDesc.ByteWidth / elementSize;
	ComCall<long>(dx.d3d11device, DEV_CreateUnorderedAccessView, buffer, &viewDesc, outView);
}

// Store 1401AC540 (name unknown): a shader resource view of a buffer of elementSize-byte elements
void sub_1401AC540(ID3D11Buffer *buffer, unsigned int elementSize, const char *name,
                   ID3D11ShaderResourceView **outView)
{
	D3D11_BUFFER_DESC bufferDesc;
	D3D11_SHADER_RESOURCE_VIEW_DESC viewDesc;

	ComCall<void>(buffer, BUF_GetDesc, &bufferDesc);
	viewDesc.ViewDimension = D3D11_SRV_DIMENSION_BUFFER;
	viewDesc.BufferEx.FirstElement = 0;
	viewDesc.BufferEx.Flags = 0;
	viewDesc.raw[3] = 0;
	viewDesc.Format = DXGI_FORMAT_UNKNOWN;
	viewDesc.BufferEx.NumElements = bufferDesc.ByteWidth / elementSize;
	ComCall<long>(dx.d3d11device, DEV_CreateShaderResourceView, buffer, &viewDesc, outView);
}

static_assert(sizeof(D3D11_BUFFER_DESC) == 0x18, "D3D11_BUFFER_DESC");
static_assert(sizeof(D3D11_UNORDERED_ACCESS_VIEW_DESC) == 0x14, "D3D11_UNORDERED_ACCESS_VIEW_DESC");
// ==== END images ====
