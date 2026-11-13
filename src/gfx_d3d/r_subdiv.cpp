// gfx_d3d/r_subdiv.cpp (Store build; the file name is a guess): GPU buffers of subdivision surfaces.
//
// Store only: no server has subdivision surfaces. Load_XSurface (14035EAF0) calls these after loading an XSurface's
// subdivision data (sub_14035F3A0, sub_14035F430): one scratch buffer per surface for the subdivided vertices, and
// per subdivision level the index buffers and raw compute buffers the tessellation shaders read. Names unknown
// (sub_<VA>); what each buffer is named comes from the debug names passed to the buffer creators. Layouts:
// include/gfx_d3d/r_xsurface.h, docs/assets/models.md.

#include "gfx_d3d/r_xsurface.h"
#include "qcommon/dvar.h"

extern const dvar_t *r_loadForRenderer;

HRESULT R_ReleaseBuffer(ID3D11Buffer *buffer);  // gfx_d3d/r_buffers.cpp
void sub_1401AC0E0(ID3D11ShaderResourceView **view);
void sub_1401AC310(unsigned int bytes, unsigned int bindFlags, D3D11_USAGE usage, const void *data, const char *name,
                   ID3D11Buffer **buffer);
void sub_1401AC380(ID3D11Buffer *buffer, const char *name, ID3D11UnorderedAccessView **view);
void sub_1401AC3F0(ID3D11Buffer *buffer, const char *name, ID3D11ShaderResourceView **view);
// Store 140601970: an immutable index buffer that is also a raw shader resource. Callers here pass a debug name
// as a fourth argument, which the function never reads (src/gfx_d3d/r_buffers.cpp gives it three parameters).
void sub_140601970(ID3D11Buffer **ib, int sizeInBytes, const void *bufferData);
typedef void (*IndexBufferWithName)(ID3D11Buffer **ib, int sizeInBytes, const void *bufferData, const char *name);

// Store 1401AC5B0 (gfx_d3d/r_compute.cpp's neighbourhood; name unknown): release a buffer and clear the pointer
void sub_1401AC5B0(ID3D11Buffer **buffer)
{
	if (*buffer)
		R_ReleaseBuffer(*buffer);
	*buffer = nullptr;
}

// Store 1401B3D60 (name unknown): the subdivision cache, a GPU-written vertex buffer with a UAV
void sub_1401B3D60(GfxSubdivCache *cache)
{
	if (!cache->size)
		return;
	sub_1401AC310(cache->size, D3D11_BIND_VERTEX_BUFFER | D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_UNORDERED_ACCESS,
	              D3D11_USAGE_DEFAULT, nullptr, "subdivCache", &cache->subdivCacheBuffer);
	sub_1401AC380(cache->subdivCacheBuffer, "subdivCacheView", &cache->subdivCacheView);
}

// Store 1401B3DC0 (name unknown): its first argument (&surf->subdiv) is unused
void sub_1401B3DC0(XSurfaceSubdivInfo **subdiv, XSurface *surf)
{
	sub_1401B4100(surf);
}

// Store 1401B4100 (name unknown): per subdivision level, with r_loadForRenderer on, the patch flags are converted
// once (flag 4 of the info) and every array becomes a GPU buffer with a view; temporary buffer pointers are dropped
// once their view holds the resource.
void sub_1401B4100(XSurface *surf)
{
	XSurfaceSubdivInfo *info = surf->subdiv;
	XSurfaceSubdivLevel *level = info->levels;
	for (unsigned int levelIndex = 0; levelIndex < surf->subdivLevelCount; levelIndex++, level++)
	{
		if (!r_loadForRenderer->current.enabled)
			continue;
		if (!(info->flags & 4))
		{
			for (unsigned int i = 0; i < level->regularPatchCount; i++)
			{
				unsigned int flags = level->regularPatchFlags[i];
				unsigned int converted = flags & 0x3FF;
				if (flags & 0x100)
					converted |= 0x110000;
				if (converted & 0x200)
					converted |= 0x440000;
				level->regularPatchFlags[i] = converted;
			}
			info->flags |= 4;
		}
		if (level->regularPatchCount)
		{
			((IndexBufferWithName)sub_140601970)(&level->regularPatchIndexBuffer, level->regularPatchCount << 5,
			                                     level->regularPatchIndices, "regularPatchIndices");
			sub_1401AC3F0(level->regularPatchIndexBuffer, "regularPatchIndexBufferView",
			              &level->regularPatchIndexBufferView);
			ID3D11Buffer *flagsBuffer;
			sub_1401AC310(level->regularPatchCount << 2, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE,
			              level->regularPatchFlags, "regularPatchFlags", &flagsBuffer);
			sub_1401AC3F0(flagsBuffer, "regularPatchFlagsView", &level->regularPatchFlagsView);
			sub_1401AC5B0(&flagsBuffer);
			if (level->regularPatchCones)
			{
				ID3D11Buffer *conesBuffer;
				sub_1401AC310(level->regularPatchCount << 5, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE,
				              level->regularPatchCones, "regularPatchCones", &conesBuffer);
				sub_1401AC3F0(conesBuffer, "regularPatchConesView", &level->regularPatchConesView);
				sub_1401AC5B0(&conesBuffer);
			}
			else
			{
				sub_1401AC0E0(&level->regularPatchConesView);
			}
		}
		if (level->faceCount)
			((IndexBufferWithName)sub_140601970)(&level->faceIndexBuffer, 12 * level->faceCount, level->faceIndices,
			                                     "faceIndices");
		if (level->facePointBufferSize)
		{
			ID3D11Buffer *buffer;
			sub_1401AC310(level->facePointBufferSize, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE,
			              level->facePoints, "facePoints", &buffer);
			sub_1401AC3F0(buffer, "facePointsView", &level->facePointsView);
			sub_1401AC5B0(&buffer);
		}
		if (level->edgePointCount)
		{
			ID3D11Buffer *buffer;
			sub_1401AC310(8 * level->edgePointCount, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE,
			              level->edgePoints, "edgePoints", &buffer);
			sub_1401AC3F0(buffer, "edgePointsView", &level->edgePointsView);
			sub_1401AC5B0(&buffer);
		}
		if (level->vertexPointBufferSize)
		{
			ID3D11Buffer *buffer;
			sub_1401AC310(level->vertexPointBufferSize, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE,
			              level->vertexPoints, "vertexPoints", &buffer);
			sub_1401AC3F0(buffer, "vertexPointsView", &level->vertexPointsView);
			sub_1401AC5B0(&buffer);
		}
		if (level->normalCount)
		{
			ID3D11Buffer *buffer;
			sub_1401AC310(level->normalBufferSize, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE, level->normals,
			              "normals", &buffer);
			sub_1401AC3F0(buffer, "normalsView", &level->normalsView);
			sub_1401AC5B0(&buffer);
		}
		if (level->transitionPointCount)
		{
			ID3D11Buffer *buffer;
			sub_1401AC310(4 * level->transitionPointCount, D3D11_BIND_SHADER_RESOURCE, D3D11_USAGE_IMMUTABLE,
			              level->transitionPoints, "transitionPoints", &buffer);
			sub_1401AC3F0(buffer, "transitionPointsView", &level->transitionPointsView);
			sub_1401AC5B0(&buffer);
		}
	}
}
