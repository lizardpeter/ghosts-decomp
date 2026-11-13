// gfx_d3d/r_material.cpp (Store build): material load-time creation.
//
// The servers' MAP names Load_InitMaterialConstantBuffer in gfx_d3d/r_material.cpp but folds it into an empty stub;
// the Store build's body is the source. The shader and input layout creators of the same file are in
// gfx_d3d/r_shader.cpp.

#include "gfx_d3d/r_buffers.h"
#include "gfx_d3d/r_material.h"

// Store 14063AF00: creates the material's constant buffers, one per stage that has data, initialised from the
// loaded data. They are immutable unless the material's asset flags have bit 0 set, which makes them dynamic and
// CPU-writable. Results aren't checked (a failed create leaves the buffer NULL).
void Load_InitMaterialConstantBuffer(unsigned char *constantBufferCount, Material *material)
{
	unsigned int dynamic = material->assetFlags & 1;
	unsigned int cpuAccessFlags = dynamic << 16;  // D3D11_CPU_ACCESS_WRITE
	unsigned int usage = dynamic + 1;            // D3D11_USAGE_IMMUTABLE or D3D11_USAGE_DYNAMIC

	for (int bufferIndex = 0; bufferIndex < (int)material->constantBufferCount; bufferIndex++)
	{
		D3D11_BUFFER_DESC desc;
		D3D11_SUBRESOURCE_DATA data;
		MaterialConstantBufferDef *def = &material->constantBufferTable[bufferIndex];

		desc.ByteWidth = 0;
		desc.Usage = (D3D11_USAGE)usage;
		desc.BindFlags = 4;  // D3D11_BIND_CONSTANT_BUFFER
		desc.CPUAccessFlags = cpuAccessFlags;
		desc.MiscFlags = 0;
		desc.StructureByteStride = 0;
		data.pSysMem = nullptr;
		data.SysMemPitch = 0;
		data.SysMemSlicePitch = 0;
		if (def->vsDataSize)
		{
			data.pSysMem = def->vsData;
			desc.ByteWidth = def->vsDataSize;
			R_CreateBufferInternal(&desc, &data, &material->constantBufferTable[bufferIndex].vsConstantBuffer);
		}
		def = &material->constantBufferTable[bufferIndex];
		if (def->hsDataSize)
		{
			data.pSysMem = def->hsData;
			desc.ByteWidth = def->hsDataSize;
			R_CreateBufferInternal(&desc, &data, &material->constantBufferTable[bufferIndex].hsConstantBuffer);
		}
		def = &material->constantBufferTable[bufferIndex];
		if (def->dsDataSize)
		{
			data.pSysMem = def->dsData;
			desc.ByteWidth = def->dsDataSize;
			R_CreateBufferInternal(&desc, &data, &material->constantBufferTable[bufferIndex].dsConstantBuffer);
		}
		def = &material->constantBufferTable[bufferIndex];
		if (def->psDataSize)
		{
			data.pSysMem = def->psData;
			desc.ByteWidth = def->psDataSize;
			R_CreateBufferInternal(&desc, &data, &material->constantBufferTable[bufferIndex].psConstantBuffer);
		}
	}
}
