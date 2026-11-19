// gfx_d3d/r_shade.cpp (Store build)
//
// Setting up a material pass on a context: its shaders, input layout, state bits and constant buffers, and the
// dynamic index buffer for 2D and effects geometry. Names and order from the Xbox One server PDB (iw6_ds_xb3:
// gfx_d3d/r_shade.cpp), whose code for these is complete, tagged with Store addresses.
//
// A pass's constants come in three frequencies (per primitive, per object, stable), each in its own constant buffer
// slot (0, 1, 2) for the vertex and pixel shaders and, when the pass is tessellated, the hull and domain shaders.
// The material's own constants are slot 3. The constant values are built on the CPU in the prim state's shadow
// arrays by R_SetPassShader*Arguments, then uploaded with Map(WRITE_DISCARD) when anything changed.

#include "gfx_d3d/r_buffers.h"
#include "gfx_d3d/r_state.h"
#include "qcommon/qcommon.h"

extern "C" void *memcpy(void *dst, const void *src, unsigned long long n);

bool R_SetPassShaderPrimArguments(GfxCmdBufContext context, const MaterialShaderArgument *__restrict arg,
                                  unsigned int argCount);
bool R_SetPassShaderObjectArguments(GfxCmdBufContext context, const MaterialShaderArgument *__restrict arg,
                                    unsigned int argCount);
bool R_SetPassShaderStableArguments(GfxCmdBufContext context, const MaterialShaderArgument *__restrict arg,
                                    unsigned int argCount);

// D3D11 constant buffer slots
#define CB_PER_PRIM 0
#define CB_PER_OBJECT 1
#define CB_STABLE 2
#define CB_MATERIAL 3

// Store 14065C2D0 (xb3 PDB gfx_d3d/r_shade.cpp:2514)
void R_SetHullAndDomainShaders(GfxCmdBufState *state, const MaterialHullShader *hullShader,
                               const MaterialDomainShader *domainShader)
{
	if (state->hullShader != hullShader || state->domainShader != domainShader)
	{
		state->hullShader = hullShader;
		state->domainShader = domainShader;
		ComCall<void>(state->prim.device, CTX_HSSetShader, hullShader ? hullShader->prog.hs : nullptr,
		              (void *const *)nullptr, 0u);
		ComCall<void>(state->prim.device, CTX_DSSetShader, domainShader ? domainShader->prog.ds : nullptr,
		              (void *const *)nullptr, 0u);
	}
}

// Store 14065C360 (xb3 PDB gfx_d3d/r_shade.cpp:2422): appends triangles' indices to the dynamic index buffer (a ring:
// it starts over from 0, discarding, when they don't fit) and binds it. Returns the first index's position. The
// buffer is always mapped on the immediate context, whichever context the prim state belongs to.
int R_SetIndexData(GfxCmdBufPrimState *primState, const unsigned short *indices, int triCount)
{
	int indexCount = 3 * triCount;
	if (gfxBuf.dynamicIndexBuffer->used + indexCount > gfxBuf.dynamicIndexBuffer->total)
		gfxBuf.dynamicIndexBuffer->used = 0;
	int baseIndex = gfxBuf.dynamicIndexBuffer->used;
	int bytes = 2 * indexCount;
	ID3D11Buffer *buffer = gfxBuf.dynamicIndexBuffer->buffer;
	D3D11_MAP lockFlags = gfxBuf.dynamicIndexBuffer->used != 0 ? D3D11_MAP_WRITE_NO_OVERWRITE : D3D11_MAP_WRITE_DISCARD;
	void *dst = R_LockIndexBuffer(dx.immediateContext, buffer, 2 * gfxBuf.dynamicIndexBuffer->used, bytes, lockFlags);
	memcpy(dst, indices, (long long)bytes);
	R_UnlockIndexBuffer(dx.immediateContext, buffer);
	if (primState->indexBuffer != buffer)
	{
		primState->indexBuffer = buffer;
		ComCall<void>(primState->device, CTX_IASetIndexBuffer, buffer, (unsigned int)DXGI_FORMAT_R16_UINT_VALUE, 0u);
	}
	gfxBuf.dynamicIndexBuffer->used += indexCount;
	return baseIndex;
}

// Store 14065CCE0 (xb3 PDB gfx_d3d/r_shade.cpp:2572)
void R_SetPixelShader(GfxCmdBufState *state, const MaterialPixelShader *pixelShader)
{
	if (state->pixelShader != pixelShader)
	{
		ComCall<void>(state->prim.device, CTX_PSSetShader, pixelShader ? pixelShader->prog.ps : nullptr,
		              (void *const *)nullptr, 0u);
		state->pixelShader = pixelShader;
	}
}

// R_SetPerPrimConstantBuffer, R_SetPerObjectConstantBuffer and R_SetStableConstantBuffer (xb3 PDB
// gfx_d3d/r_shade.cpp:893, 1017, 1140) differ only in the slot, the table and the cached buffers. The pass's buffer
// (none when it has no constants of that frequency) is bound to the vertex and pixel shaders, and to the hull and
// domain shaders when the pass has them. Returns whether a buffer is bound and anything was (re)bound.
static inline bool R_SetPassConstantBuffer(GfxCmdBufState *state, const MaterialPass *pass, unsigned int slot,
                                           unsigned short argSize, unsigned int bufferIndex,
                                           ID3D11Buffer **cachedVSPS, ID3D11Buffer **cachedHSDS)
{
	ID3D11Buffer *buffer;
	if (argSize == 0)
		buffer = nullptr;
	else
		buffer = dx.constantBufferTables[slot][pass->zone][bufferIndex].buffer;
	bool changed = *cachedVSPS != buffer;
	if (changed)
	{
		*cachedVSPS = buffer;
		ComCall<void>(state->prim.device, CTX_VSSetConstantBuffers, slot, 1u, (ID3D11Buffer *const *)&buffer);
		ComCall<void>(state->prim.device, CTX_PSSetConstantBuffers, slot, 1u, (ID3D11Buffer *const *)&buffer);
	}
	if (!pass->hullShader && !pass->domainShader)
	{
		if (!changed)
			return false;
	}
	else if (*cachedHSDS != buffer)
	{
		*cachedHSDS = buffer;
		ComCall<void>(state->prim.device, CTX_HSSetConstantBuffers, slot, 1u, (ID3D11Buffer *const *)&buffer);
		ComCall<void>(state->prim.device, CTX_DSSetConstantBuffers, slot, 1u, (ID3D11Buffer *const *)&buffer);
	}
	return buffer != nullptr;
}

static inline bool R_SetPerPrimConstantBuffer(GfxCmdBufState *state, const MaterialPass *pass)
{
	return R_SetPassConstantBuffer(state, pass, CB_PER_PRIM, pass->perPrimArgSize, pass->perPrimConstantBuffer,
	                               &state->prim.perPrimVSPSConstantBuffer, &state->prim.perPrimHSDSConstantBuffer);
}

static inline bool R_SetPerObjectConstantBuffer(GfxCmdBufState *state, const MaterialPass *pass)
{
	return R_SetPassConstantBuffer(state, pass, CB_PER_OBJECT, pass->perObjArgSize, pass->perObjConstantBuffer,
	                               &state->prim.perObjectVSPSConstantBuffer, &state->prim.perObjectHSDSConstantBuffer);
}

// Store 14065CD30 (xb3 PDB gfx_d3d/r_shade.cpp:1140; the per-prim and per-object ones are inlined in the Store build)
bool R_SetStableConstantBuffer(GfxCmdBufState *state, const MaterialPass *pass)
{
	return R_SetPassConstantBuffer(state, pass, CB_STABLE, pass->stableArgSize, pass->stableConstantBuffer,
	                               &state->prim.stableVSPSConstantBuffer, &state->prim.stableHSDSConstantBuffer);
}

// Store 14065D160 (xb3 PDB gfx_d3d/r_shade.cpp:2499)
void R_SetVertexShader(GfxCmdBufState *state, const MaterialVertexShader *vertexShader)
{
	if (state->vertexShader != vertexShader)
	{
		ComCall<void>(state->prim.device, CTX_VSSetShader, vertexShader->prog.vs, (void *const *)nullptr, 0u);
		state->vertexShader = vertexShader;
	}
}

// xb3 PDB R_SetMaterialConstantBuffer (gfx_d3d/r_shade.cpp:1218), inlined in the Store build: the material's own
// constant buffers for the current technique, slot 3 of each stage
static inline void R_SetMaterialConstantBuffer(GfxCmdBufState *state, const Material *material)
{
	if (!material->constantBufferCount)
		return;
	unsigned char index = material->constantBufferIndex[state->techType];
	if (index == 0xFF)
		return;
	MaterialConstantBufferDef *def = &material->constantBufferTable[index];
	if (state->prim.perMaterialVSConstantBuffer != def->vsConstantBuffer)
	{
		state->prim.perMaterialVSConstantBuffer = def->vsConstantBuffer;
		ComCall<void>(state->prim.device, CTX_VSSetConstantBuffers, (unsigned int)CB_MATERIAL, 1u,
		              (ID3D11Buffer *const *)&def->vsConstantBuffer);
	}
	if (state->prim.perMaterialHSConstantBuffer != def->hsConstantBuffer)
	{
		state->prim.perMaterialHSConstantBuffer = def->hsConstantBuffer;
		ComCall<void>(state->prim.device, CTX_HSSetConstantBuffers, (unsigned int)CB_MATERIAL, 1u,
		              (ID3D11Buffer *const *)&def->hsConstantBuffer);
	}
	if (state->prim.perMaterialDSConstantBuffer != def->dsConstantBuffer)
	{
		state->prim.perMaterialDSConstantBuffer = def->dsConstantBuffer;
		ComCall<void>(state->prim.device, CTX_DSSetConstantBuffers, (unsigned int)CB_MATERIAL, 1u,
		              (ID3D11Buffer *const *)&def->dsConstantBuffer);
	}
	if (state->prim.perMaterialPSConstantBuffer != def->psConstantBuffer)
	{
		state->prim.perMaterialPSConstantBuffer = def->psConstantBuffer;
		ComCall<void>(state->prim.device, CTX_PSSetConstantBuffers, (unsigned int)CB_MATERIAL, 1u,
		              (ID3D11Buffer *const *)&def->psConstantBuffer);
	}
}

// The GfxBackEndData member whose view the Store build binds as hull shader resource 1 for passes with custom
// buffer flag 0x2000 (tessellation; name unknown)
#define BACKEND_TESSELLATION_OBJECT 0x150C40
#define CUSTOM_BUFFER_HULL_RESOURCE 0x2000

// Store 14065D300 (xb3 PDB gfx_d3d/r_shade.cpp:3346): selects pass `passIndex` of the current technique and sets its
// pixel, hull and domain shaders, its state bits (with depth writes forced from the depth hack modes on, and for
// prepass-tagged passes when there is no prepass) and the material's constant buffers. The Store build adds the hull
// shader resource for tessellated passes.
void R_SetupPass(GfxCmdBufContext context, unsigned int passIndex)
{
	GfxCmdBufState *state = context.state;
	const MaterialPass *pass = &state->technique->passArray[passIndex];
	state->pass = pass;
	state->passIndex = passIndex;
	const Material *material = state->material;
	const GfxStateBits *refStateBits =
		&material->stateBitsTable[material->stateBitsEntry[state->techType] + passIndex];
	R_SetPixelShader(state, pass->pixelShader);
	R_SetHullAndDomainShaders(state, pass->hullShader, pass->domainShader);
	unsigned int stateBits[3];
	stateBits[0] = refStateBits->loadBits[0];
	stateBits[1] = refStateBits->loadBits[1];
	stateBits[2] = refStateBits->loadBits[2];
	if ((int)context.source->depthStencilMode >= 4)
		stateBits[1] |= 1;
	else if ((context.source->flags & GFX_SOURCE_NO_PREPASS) && ((stateBits[2] >> 28) & 1))
		stateBits[1] |= 1;
	R_SetState(context, stateBits, refStateBits);
	if (pass->customBufferFlags & CUSTOM_BUFFER_HULL_RESOURCE)
	{
		const char *object = *(const char *const *)((const char *)context.source->input.data + BACKEND_TESSELLATION_OBJECT);
		ID3D11ShaderResourceView *view = *(ID3D11ShaderResourceView *const *)(object + 0x20);
		ComCall<void>(context.state->prim.device, CTX_HSSetShaderResources, 1u, 1u, &view);
	}
	R_SetMaterialConstantBuffer(state, material);
}

// Map(WRITE_DISCARD) the pass's buffer of one frequency and copy its constants from the shadow array
static inline void R_UploadPassConstants(GfxCmdBufState *state, ID3D11Buffer *buffer, const void *shadow,
                                         unsigned short size)
{
	D3D11_MAPPED_SUBRESOURCE mapped;
	ComCall<long>(state->prim.device, CTX_Map, buffer, 0u, D3D11_MAP_WRITE_DISCARD, 0u, &mapped);
	memcpy(mapped.pData, shadow, size);
	ComCall<void>(state->prim.device, CTX_Unmap, buffer, 0u);
}

static inline ID3D11Buffer *R_PassConstantBuffer(const MaterialPass *pass, unsigned int slot, unsigned short size,
                                                 unsigned int bufferIndex)
{
	if (size == 0)
		return nullptr;
	return dx.constantBufferTables[slot][pass->zone][bufferIndex].buffer;
}

// R_SetupPassVertexShaderArgs, R_SetupPassPixelShaderArgs and R_SetupPassCriticalPixelShaderArgs (xb3 PDB
// gfx_d3d/r_shade.cpp; identical code folded into one in xb3) are three identical copies in the Store build, which
// one is which is unknown: the stable constants and textures of the current pass.
static inline void R_SetupPassStableArgs(GfxCmdBufContext context)
{
	GfxCmdBufState *state = context.state;
	const MaterialPass *pass = state->pass;
	if (pass->stableArgCount)
	{
		bool bufferChanged = R_SetStableConstantBuffer(state, pass);
		bool argsChanged = R_SetPassShaderStableArguments(
			context, &pass->args[pass->perObjArgCount + pass->perPrimArgCount], pass->stableArgCount);
		if (argsChanged || bufferChanged)
			R_UploadPassConstants(
				state, R_PassConstantBuffer(pass, CB_STABLE, pass->stableArgSize, pass->stableConstantBuffer),
				state->prim.stableConstantShadow, pass->stableArgSize);
	}
	R_FlushTextureState(state);
}

// Store 14065D5A0 (one of the three; see above)
void sub_14065D5A0(GfxCmdBufContext context)
{
	R_SetupPassStableArgs(context);
}

// Store 14065DA20 (one of the three; see above)
void sub_14065DA20(GfxCmdBufContext context)
{
	R_SetupPassStableArgs(context);
}

// Store 14065DB20 (one of the three; see above)
void sub_14065DB20(GfxCmdBufContext context)
{
	R_SetupPassStableArgs(context);
}

// Store 14065D6A0 (xb3 PDB gfx_d3d/r_shade.cpp:1329)
void R_SetupPassPerObjectArgs(GfxCmdBufContext context)
{
	GfxCmdBufState *state = context.state;
	const MaterialPass *pass = state->pass;
	if (pass->perObjArgCount)
	{
		bool bufferChanged = R_SetPerObjectConstantBuffer(state, pass);
		bool argsChanged =
			R_SetPassShaderObjectArguments(context, &pass->args[pass->perPrimArgCount], pass->perObjArgCount);
		if (argsChanged || bufferChanged)
			R_UploadPassConstants(
				state, R_PassConstantBuffer(pass, CB_PER_OBJECT, pass->perObjArgSize, pass->perObjConstantBuffer),
				state->prim.perObjectConstantShadow, pass->perObjArgSize);
	}
	R_FlushTextureState(state);
}

// Store 14065D870 (xb3 PDB gfx_d3d/r_shade.cpp:1296)
void R_SetupPassPerPrimArgs(GfxCmdBufContext context)
{
	GfxCmdBufState *state = context.state;
	const MaterialPass *pass = state->pass;
	if (pass->perPrimArgCount)
	{
		bool bufferChanged = R_SetPerPrimConstantBuffer(state, pass);
		bool argsChanged = R_SetPassShaderPrimArguments(context, pass->args, pass->perPrimArgCount);
		if (argsChanged || bufferChanged)
			R_UploadPassConstants(
				state, R_PassConstantBuffer(pass, CB_PER_PRIM, pass->perPrimArgSize, pass->perPrimConstantBuffer),
				state->prim.perPrimConstantShadow, pass->perPrimArgSize);
	}
	R_FlushTextureState(state);
}

// Store 14065DC20 (xb3 PDB gfx_d3d/r_shade.cpp:2897): the input layout for the prim state's vertex type and the
// pass's vertex shader. A pass without a vertex declaration (vertices generated in the shader) unbinds the layout;
// one whose declaration has no layout for this vertex type is a fatal error.
void R_UpdateVertexDecl(GfxCmdBufState *state)
{
	const MaterialPass *pass = state->pass;
	if (!pass->vertexDecl)
	{
		if (state->prim.vertexDecl)
		{
			ComCall<void>(state->prim.device, CTX_IASetInputLayout, (ID3D11InputLayout *)nullptr);
			state->prim.vertexDecl = nullptr;
		}
		R_SetVertexShader(state, pass->vertexShader);
		return;
	}
	const MaterialVertexShader *vertexShader = pass->vertexShader;
	ID3D11InputLayout *layout = pass->vertexDecl->routing.decl[state->prim.vertDeclType];
	if (state->prim.vertexDecl != layout)
	{
		ComCall<void>(state->prim.device, CTX_IASetInputLayout, layout);
		state->prim.vertexDecl = layout;
	}
	if (!pass->vertexDecl->routing.decl[state->prim.vertDeclType])
		Com_Error(ERR_FATAL, "Vertex type %i doesn't have the information used by shader %s in material %s\n",
		          state->prim.vertDeclType, vertexShader->name, *(const char *const *)state->material);
	if (state->vertexShader != vertexShader)
	{
		ComCall<void>(state->prim.device, CTX_VSSetShader, vertexShader->prog.vs, (void *const *)nullptr, 0u);
		state->vertexShader = vertexShader;
	}
}
