// gfx_d3d/rb_shade.cpp (Store build)
//
// The back end's tessellation buffer (`tess`): 2D and other immediate geometry is collected as vertices and indices
// for one material technique, then drawn in one go by RB_EndTessSurface. Names and order from the Xbox One server
// PDB (iw6_ds_xb3: gfx_d3d/rb_shade.cpp), tagged with Store addresses. RB_ClearPixelShader and the other unbinds from
// this file are in gfx_d3d/r_state.cpp (sub_14068D190 to sub_14068D270).
//
// Everything here uses the back end's own state (gfxCmdBufState, gfxCmdBufSourceState) on the immediate context.

#include "gfx_d3d/r_buffers.h"
#include "gfx_d3d/r_state.h"

int R_SetIndexData(GfxCmdBufPrimState *primState, const unsigned short *indices, int triCount);
int R_SetVertexData(GfxCmdBufState *state, const void *data, int vertexCount, int vertexSize);
void R_SetupPass(GfxCmdBufContext context, unsigned int passIndex);
void R_UpdateVertexDecl(GfxCmdBufState *state);
void sub_14065D5A0(GfxCmdBufContext context);  // one of R_SetupPass{Vertex,Pixel,CriticalPixel}ShaderArgs
void R_SetupPassPerObjectArgs(GfxCmdBufContext context);
void R_SetupPassPerPrimArgs(GfxCmdBufContext context);
void R_DrawIndexedPrimitive(GfxCmdBufPrimState *primState, const GfxDrawPrimArgs *args);
void R_GetViewport(const GfxCmdBufSourceState *source, GfxViewport *viewport);
void R_UpdateViewport(GfxCmdBufSourceState *source, const GfxViewport *viewport);
void R_SetViewportAndScissorSeparate(GfxCmdBufState *state, const GfxViewport *viewport, const GfxViewport *scissor);

extern GfxCmdBufSourceState gfxCmdBufSourceState;
extern GfxCmdBufState gfxCmdBufState;
extern const GfxCmdBufContext gfxCmdBufContext;  // {&gfxCmdBufSourceState, &gfxCmdBufState}

#define TESS_VERTEX_SIZE 0x20  // GfxVertex

// Store 14068D420 (xb3 PDB gfx_d3d/rb_shade.cpp:321): uploads the tess vertices to the dynamic vertex buffer (from
// its start again when they don't fit) and draws them with every pass of the current technique
void R_DrawTessTechnique(GfxCmdBufContext context, const GfxDrawPrimArgs *args)
{
	GfxVertexBufferState *vb = gfxBuf.dynamicVertexBuffer;
	GfxCmdBufState *state = context.state;
	const MaterialTechnique *technique = state->technique;
	if (vb->total < (int)(vb->used + tess.vertexCount * TESS_VERTEX_SIZE))
		vb->used = 0;
	int offset = R_SetVertexData(state, &tess, tess.vertexCount, TESS_VERTEX_SIZE);
	ID3D11Buffer *buffer = vb->buffer;
	for (unsigned int passIndex = 0; passIndex < technique->passCount; passIndex++)
	{
		R_SetupPass(context, passIndex);
		R_UpdateVertexDecl(state);
		sub_14065D5A0(context);
		R_SetStreams(&state->prim, buffer, (unsigned int)offset, TESS_VERTEX_SIZE);
		R_SetupPassPerObjectArgs(context);
		R_SetupPassPerPrimArgs(context);
		R_DrawIndexedPrimitive(&state->prim, args);
	}
}

// Store 14068D2A0 (name unknown; the xb3 server's RB_EndTessSurface with a scissor rectangle): sets the viewport
// first when it is dirty (with `scissor`, or the viewport itself), then draws what is in tess and empties it
void sub_14068D2A0(const GfxViewport *scissor)
{
	if (gfxCmdBufSourceState.flags & GFX_SOURCE_VIEWPORT_IS_DIRTY)
	{
		GfxViewport viewport;
		R_GetViewport(&gfxCmdBufSourceState, &viewport);
		R_SetViewportAndScissorSeparate(&gfxCmdBufState, &viewport, scissor ? scissor : &viewport);
		R_UpdateViewport(&gfxCmdBufSourceState, &viewport);
	}
	unsigned int primCount = tess.indexCount / 3;
	GfxDrawPrimArgs args;
	args.baseIndex = R_SetIndexData(&gfxCmdBufState.prim, tess.indices, (int)primCount);
	args.primCount = (int)primCount;
	args.vertIndexBase = 0;
	R_DrawTessTechnique(gfxCmdBufContext, &args);
	tess.indexCount = 0;
	tess.vertexCount = 0;
}

// Store 14068D350 (xb3 PDB gfx_d3d/rb_shade.cpp:665)
void RB_EndTessSurface()
{
	sub_14068D2A0(nullptr);
}

// Store 14068D370 (xb3 PDB gfx_d3d/rb_shade.cpp): starts collecting for a material technique, drawing what was
// collected for another one first. `primStatsTarget` is not used by the Store build.
void RB_SetTessTechnique(const Material *material, MaterialTechniqueType techType, GfxPrimStatsTarget primStatsTarget)
{
	if (gfxCmdBufState.material != material || gfxCmdBufState.techType != techType)
	{
		if (tess.vertexCount)
			sub_14068D2A0(nullptr);
		gfxCmdBufState.material = material;
		tess.firstVertex = 0;
		tess.lastVertex = 0;
		gfxCmdBufState.prim.vertDeclType = 0;  // VERTDECL_GENERIC
		gfxCmdBufState.techType = techType;
		gfxCmdBufState.technique = material->techniqueSet->techniques[techType];
	}
}

// Store 14068D3E0 (xb3 PDB gfx_d3d/rb_shade.cpp:681): tess is full: draws it and starts again with the same
// technique
void RB_TessOverflow()
{
	sub_14068D2A0(nullptr);
	tess.firstVertex = 0;
	tess.lastVertex = 0;
	gfxCmdBufState.prim.vertDeclType = 0;  // VERTDECL_GENERIC
	gfxCmdBufState.technique = gfxCmdBufState.material->techniqueSet->techniques[gfxCmdBufState.techType];
}
