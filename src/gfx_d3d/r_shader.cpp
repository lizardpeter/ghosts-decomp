// gfx_d3d/r_shader.cpp (Store build)
//
// Shader and input-layout creation from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store
// addresses. The servers' MAP and PDB (iw6_ds_ps4, iw6_ds_xb3) name the shader loaders in gfx_d3d/r_material.cpp
// (Load_CreateMaterialPixelShader and the rest, and the Material_Reload* callbacks), but their bodies are stubs
// there, so the Store build is the source; line numbers are unknown. The vertex declaration code follows Black Ops'
// Material_BuildVertexDecl / Load_BuildVertexDecl (gfx_d3d/r_material.cpp), which D3D11 turned into input layouts
// built against a vertex shader's bytecode.
//
// A shader is created only when r_loadForRenderer is set and the shader was compiled for the renderer in use
// (loadDef.loadForRenderer == r_rendererInUse); otherwise its D3D object stays NULL. Compute shaders skip that
// check. Pixel and vertex shaders are created with the thread raised to at least normal priority.

#include <string.h>

#include <iw6_static.h>

#include "gfx_d3d/com_call.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_state_d3d11.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "gfx_d3d/r_shader.cpp"

// ---- assets (xb3 PDB types; the Store build reads the same offsets) -------------------------------------------

struct GfxShaderLoadDef  // GfxPixelShaderLoadDef, GfxVertexShaderLoadDef, GfxHullShaderLoadDef, ...
{
	unsigned char *program;
	unsigned int programSize;
	unsigned short loadForRenderer;  // not in the compute shader's
};

struct MaterialPixelShader
{
	const char *name;
	ID3D11PixelShader *ps;
	GfxShaderLoadDef loadDef;
};

struct MaterialVertexShader
{
	const char *name;
	ID3D11VertexShader *vs;
	GfxShaderLoadDef loadDef;
};

struct MaterialHullShader
{
	const char *name;
	ID3D11HullShader *hs;
	GfxShaderLoadDef loadDef;
};

struct MaterialDomainShader
{
	const char *name;
	ID3D11DomainShader *ds;
	GfxShaderLoadDef loadDef;
};

struct ComputeShader
{
	const char *name;
	ID3D11ComputeShader *cs;
	GfxShaderLoadDef loadDef;
};

union XAssetHeader
{
	ComputeShader *computeShader;
	MaterialVertexShader *vertexShader;
	MaterialHullShader *hullShader;
	MaterialDomainShader *domainShader;
	MaterialPixelShader *pixelShader;
};

struct MaterialStreamRouting
{
	unsigned char source;
	unsigned char dest;
	unsigned char mask;
};

#define VERTEXDECL_TYPE_COUNT 249  // 242 in the xb3 server

struct MaterialVertexStreamRouting
{
	MaterialStreamRouting data[31];
	ID3D11InputLayout *decl[VERTEXDECL_TYPE_COUNT];
};

// Where a stream source lives in a vertex declaration type's buffers; Stream 0xFF: the type lacks it.
struct stream_source_info_t
{
	unsigned char Stream;
	unsigned char Offset;
	unsigned char unknown[2];
	int Format;  // DXGI_FORMAT
};

struct GfxVertexDeclSources  // one per vertex declaration type, name unknown
{
	unsigned int unknown;
	stream_source_info_t source[23];
};

struct stream_dest_info_t
{
	unsigned char semanticNameIndex;  // into s_vertexSemanticNames
	unsigned char semanticIndex;
};

struct TempPriority
{
	void *threadHandle;
	int oldPriority;
};

static_assert(__builtin_offsetof(MaterialPixelShader, loadDef) == 0x10, "MaterialPixelShader layout");
static_assert(__builtin_offsetof(GfxShaderLoadDef, programSize) == 0x8, "GfxShaderLoadDef layout");
static_assert(__builtin_offsetof(GfxShaderLoadDef, loadForRenderer) == 0xC, "GfxShaderLoadDef layout");
static_assert(__builtin_offsetof(MaterialVertexStreamRouting, decl) == 0x60, "MaterialVertexStreamRouting layout");
static_assert(sizeof(MaterialVertexStreamRouting) == 0x60 + 0x7C8, "MaterialVertexStreamRouting layout");
static_assert(sizeof(GfxVertexDeclSources) == 0xBC, "GfxVertexDeclSources layout");

extern const dvar_t *r_loadForRenderer;
extern const dvar_t *r_rendererInUse;

void Sys_TempPriorityAtLeastNormalBegin(TempPriority *priority);
void Sys_TempPriorityEnd(TempPriority *priority);

// gfx_d3d/r_state_vertex.cpp in the PS4 server's MAP
IW6_STATIC const stream_dest_info_t s_streamDestInfo[] IW6_AT("", "s_streamDestInfo");
IW6_STATIC const char *const s_vertexSemanticNames[] IW6_AT("", "s_vertexSemanticNames");
// Black Ops' s_streamSourceInfo: per vertex declaration type, where each stream source is
IW6_STATIC const GfxVertexDeclSources s_streamSourceInfo[VERTEXDECL_TYPE_COUNT] IW6_AT("", "s_streamSourceInfo");

// ---- shaders --------------------------------------------------------------------------------------------------

// Store 14063AC20 (gfx_d3d/r_material.cpp in the PS4 MAP)
void Load_CreateComputeShader(unsigned char **data, ComputeShader *shader)
{
	if (!*data)
	{
		shader->cs = (ID3D11ComputeShader *)*data;
		return;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateComputeShader, (const void *)*data, (unsigned long long)shader->loadDef.programSize,
	              (void *)nullptr, &shader->cs);
}

// Store 14063AD10 (gfx_d3d/r_material.cpp in the PS4 MAP)
void Load_CreateMaterialDomainShader(unsigned char **data, MaterialDomainShader *shader)
{
	if (*data && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		ComCall<long>(dx.d3d11device, DEV_CreateDomainShader, (const void *)*data,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->ds);
		return;
	}
	shader->ds = nullptr;
}

// Store 14063AD70 (gfx_d3d/r_material.cpp in the PS4 MAP)
void Load_CreateMaterialHullShader(unsigned char **data, MaterialHullShader *shader)
{
	if (*data && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		ComCall<long>(dx.d3d11device, DEV_CreateHullShader, (const void *)*data,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->hs);
		return;
	}
	shader->hs = nullptr;
}

// Store 14063ADD0 (gfx_d3d/r_material.cpp in the PS4 MAP)
void Load_CreateMaterialPixelShader(unsigned char **data, MaterialPixelShader *shader)
{
	if (*data && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		TempPriority priority;
		Sys_TempPriorityAtLeastNormalBegin(&priority);
		ComCall<long>(dx.d3d11device, DEV_CreatePixelShader, (const void *)*data,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->ps);
		Sys_TempPriorityEnd(&priority);
		return;
	}
	shader->ps = nullptr;
}

// Store 14063AE60 (gfx_d3d/r_material.cpp in the PS4 MAP)
void Load_CreateMaterialVertexShader(unsigned char **data, MaterialVertexShader *shader)
{
	if (*data && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		TempPriority priority;
		Sys_TempPriorityAtLeastNormalBegin(&priority);
		ComCall<long>(dx.d3d11device, DEV_CreateVertexShader, (const void *)*data,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->vs);
		Sys_TempPriorityEnd(&priority);
		return;
	}
	shader->vs = nullptr;
}

// Store 14063BA50: the asset reload callbacks (Material_Reload*, gfx_d3d/r_material.cpp in the PS4 MAP) create the
// shader again from its own load definition.
void Material_ReloadComputeShader(XAssetHeader header, void *data)
{
	ComputeShader *shader = header.computeShader;
	if (!shader->loadDef.program)
	{
		shader->cs = (ID3D11ComputeShader *)shader->loadDef.program;
		return;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateComputeShader, (const void *)shader->loadDef.program,
	              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->cs);
}

// Store 14063BAA0
void Material_ReloadDomainShader(XAssetHeader header, void *data)
{
	MaterialDomainShader *shader = header.domainShader;
	if (shader->loadDef.program && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		ComCall<long>(dx.d3d11device, DEV_CreateDomainShader, (const void *)shader->loadDef.program,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->ds);
		return;
	}
	shader->ds = nullptr;
}

// Store 14063BB10
void Material_ReloadHullShader(XAssetHeader header, void *data)
{
	MaterialHullShader *shader = header.hullShader;
	if (shader->loadDef.program && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		ComCall<long>(dx.d3d11device, DEV_CreateHullShader, (const void *)shader->loadDef.program,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->hs);
		return;
	}
	shader->hs = nullptr;
}

// Store 14063BB80
void Material_ReloadPixelShader(XAssetHeader header, void *data)
{
	MaterialPixelShader *shader = header.pixelShader;
	if (shader->loadDef.program && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		TempPriority priority;
		Sys_TempPriorityAtLeastNormalBegin(&priority);
		ComCall<long>(dx.d3d11device, DEV_CreatePixelShader, (const void *)shader->loadDef.program,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->ps);
		Sys_TempPriorityEnd(&priority);
		return;
	}
	shader->ps = nullptr;
}

// Store 14063BC10
void Material_ReloadVertexShader(XAssetHeader header, void *data)
{
	MaterialVertexShader *shader = header.vertexShader;
	if (shader->loadDef.program && r_loadForRenderer->current.enabled &&
	    shader->loadDef.loadForRenderer == r_rendererInUse->current.integer)
	{
		TempPriority priority;
		Sys_TempPriorityAtLeastNormalBegin(&priority);
		ComCall<long>(dx.d3d11device, DEV_CreateVertexShader, (const void *)shader->loadDef.program,
		              (unsigned long long)shader->loadDef.programSize, (void *)nullptr, &shader->vs);
		Sys_TempPriorityEnd(&priority);
		return;
	}
	shader->vs = nullptr;
}

// ---- input layouts --------------------------------------------------------------------------------------------

// Store 140665180 (Black Ops' Material_BuildVertexDecl, gfx_d3d/r_material.cpp): the input layout that feeds a
// vertex shader from one vertex declaration type. Elements are kept sorted by input slot (insertion sort); NULL
// when the type lacks one of the routed sources.
ID3D11InputLayout *Material_BuildVertexDecl(const MaterialStreamRouting *routingData, unsigned int streamCount,
                                            const GfxVertexDeclSources *sourceTable, const MaterialVertexShader *vs)
{
	D3D11_INPUT_ELEMENT_DESC elemTable[257];
	ID3D11InputLayout *decl = nullptr;
	int elemIndex = 0;

	for (; streamCount; streamCount--, routingData++)
	{
		const stream_source_info_t *sourceInfo = &sourceTable->source[routingData->source];
		if (sourceInfo->Stream == 0xFF)
			return nullptr;
		const stream_dest_info_t *destInfo = &s_streamDestInfo[routingData->dest];
		int elemIndexInsert = elemIndex;
		while (elemIndexInsert > 0 && elemTable[elemIndexInsert - 1].InputSlot > sourceInfo->Stream)
		{
			elemTable[elemIndexInsert] = elemTable[elemIndexInsert - 1];
			elemIndexInsert--;
		}
		elemIndex++;
		elemTable[elemIndexInsert].SemanticName = s_vertexSemanticNames[destInfo->semanticNameIndex];
		elemTable[elemIndexInsert].SemanticIndex = destInfo->semanticIndex;
		elemTable[elemIndexInsert].Format = sourceInfo->Format;
		elemTable[elemIndexInsert].InputSlot = sourceInfo->Stream;
		elemTable[elemIndexInsert].AlignedByteOffset = sourceInfo->Offset;
		elemTable[elemIndexInsert].InputSlotClass = 0;
		elemTable[elemIndexInsert].InstanceDataStepRate = 0;
	}
	ComCall<long>(dx.d3d11device, DEV_CreateInputLayout, (const D3D11_INPUT_ELEMENT_DESC *)elemTable,
	              (unsigned int)elemIndex, (const void *)vs->loadDef.program, (unsigned long long)vs->loadDef.programSize,
	              &decl);
	return decl;
}

// Store 1406650E0 (name unknown; Black Ops' Load_BuildVertexDecl loop): the input layouts of every vertex
// declaration type for one routing and vertex shader, or all NULL when nothing is loaded for this renderer.
void sub_1406650E0(MaterialVertexStreamRouting *routing, unsigned int streamCount, const MaterialVertexShader *vs)
{
	if (!r_loadForRenderer->current.enabled || !streamCount)
	{
		memset(routing->decl, 0, sizeof(routing->decl));
		return;
	}
	for (int vertDeclType = 0; vertDeclType < VERTEXDECL_TYPE_COUNT; vertDeclType++)
		routing->decl[vertDeclType] = Material_BuildVertexDecl(routing->data, streamCount,
		                                                        &s_streamSourceInfo[vertDeclType], vs);
}
