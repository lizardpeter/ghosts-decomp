# Models: XModel, XModelSurfs, XSurface, PhysPreset, PhysCollmap

This page describes the model assets of the Microsoft Store build (`iw6mp64_MSStore_ship`) as its code loads and uses
them. For each one it gives the structures with every field, the order in which the zone stream holds them, and the
vertex, index, skinning and collision data. It is written for three readers: the decomp, a Vulkan renderer, and the
importer of an engine that reads Ghosts zones.

Evidence is given in brackets: a Store address, a test, or "data" for values seen in a real zone. Anything that
is not verified says so.

**Sources:**

| What | Where |
|---|---|
| Loaders, reconstructed and differential-tested against the Store exe | src/xanim/xmodel_load_db.cpp, src/gfx_d3d/r_xsurface_load_db.cpp, src/physics/physpreset_load_db.cpp, src/qcommon/cm_brush_related_load_db.cpp |
| Structures, with static_asserts | include/xanim/xmodel.h, include/gfx_d3d/r_xsurface.h, include/physics/physpreset.h, include/qcommon/cm_brush.h |
| Decoder and glTF converter | tools/fastfile/xmodel.py, tested by tests/fastfile/test_xmodel.py |
| The stream rules the loaders rely on | include/database/db_stream_api.h, and docs/fastfiles.md (the pipeline's page) |

**The real-zone check.** The game's own loader (DB_LoadXFile, run in the emulator) loaded
`mp_head_aa_tr.ff`, a 139 KB character head zone. It holds 1 XModel, `head_dlc_head_aa`, with 98 bones, 6 LODs and
35 surfaces, plus 6 XModelSurfs, 5 materials, 4 technique sets and a rawfile. tools/fastfile/xmodel.py's reader
then read that model from the game's memory. Every value marked "data" below comes from this run. The run is a
scratch-only check: nothing of the zone is in the repository.

## Asset types

| Type | Enum | Header size | Entry point | Linked by |
|---|---|---|---|---|
| physpreset | 0x00 | 0x58 | Load_PhysPresetPtr 1403555F0 | Load_PhysPresetAsset 140373270 |
| phys_collmap | 0x01 | 0x58 | Load_PhysCollmapPtr 140355410 | Load_PhysCollmapAsset 1403731B0 |
| xmodelsurfs | 0x03 | 0x38 | Load_XModelSurfsPtr 14035E860 | Load_XModelSurfsAsset 140374190 |
| xmodel | 0x04 | 0x258 | Load_XModelPtr 14035E530 | Load_XModelAsset 1403740C0, then DB_XModelSurfsFixup 1403712F0 |

The header sizes come from DB_GetXAssetTypeSize's table (docs/fastfiles.md) and match what each loader reads.

The servers' sizes differ:

| Structure | Servers (PS4/xb3 PDBs) | Store build |
|---|---|---|
| XModel | 0x228 | 0x258 |
| XModelLodInfo | 0x38 | 0x40 |
| XSurface | 0xC8 | 0xE8 |

Every PC layout claim below comes from the Store build's code, not from the servers' PDB types.

## The stream rules, as these loaders use them

- **Load_Stream(true, p, n)** copies the next n bytes of the decompressed zone to p (the current position) and
  advances the position. Load_Stream(false, ...) reads nothing: the bytes came in with the enclosing structure.
- **Alignment** happens in memory only. `g_streamPos = (g_streamPos + a - 1) & ~(a - 1)` before an array moves the
  write position, never the file. The zone is the loaders' reads packed back to back, in the order they happen.
- **Pointer fields** hold one of these values in the zone:
  - 0 (null).
  - `0xFDFDFDFFFFFFFFFF` (FOLLOWING, "-1"): the data follows at the aligned position.
  - `0xFDFDFDFFFFFFFFFE` (INSERT, "-2", asset pointers only): the data follows, and DB_InsertPointer also reserves a
    slot that later aliases resolve to.
  - Anything else: a packed offset, which DB_ConvertOffsetToPointer turns into an address
    (DB_ConvertOffsetToAlias for asset pointers).
  - Fields marked **always inline** take any non-zero value as FOLLOWING; there is no offset form.
- **Asset pointers** (the `Load_<T>Ptr` rule, Load_XModelPtr 14035E530):
  1. In the temp block (DB_PushStreamPos(0)), the loader checks whether the value is FOLLOWING or INSERT
     (`v - INSERT < 2`, unsigned).
  2. If it is not, the value is an alias, resolved with DB_ConvertOffsetToAlias.
  3. If it is, the loader aligns to 4, points the field at the header, reserves the insert slot for INSERT,
     calls `Load_<T>(true)`, then `Load_<T>Asset(&ptr)` (which links the asset and may replace the pointer), and
     finally writes the final pointer into the insert slot.
- **Asset contents** are loaded in the virtual block. Each asset header loader brackets its contents with
  DB_PushStreamPos(3) / DB_PopStreamPos.
- **XString fields** follow the same rule. FOLLOWING means Load_XStringCustom: the NUL-terminated string at the
  current position, unaligned.

## XModel (0x258 bytes)

The loader is Load_XModel (14035E020). Below, `nb` is numBones, `nr` numRootBones, `ns` numsurfs.

| Off | Type | Name | Load rule and alignment | Runtime use and evidence |
|---|---|---|---|---|
| 0x000 | const char* | name | XString | data: "head_dlc_head_aa"; XModelBad calls DB_IsXAssetDefault(4, name) (140567CF0) |
| 0x008 | u8 | numBones | | XModelNumBones (14056A340); data: 98 |
| 0x009 | u8 | numRootBones | | bones without a parent, first in every bone array; data: 1 |
| 0x00A | u8 | numsurfs | | total over the LODs, rewritten by DB_XModelSurfsFixup; data: 35 |
| 0x00B | u8 | numReactiveMotionParts | | |
| 0x00C | float | scale | | data: 1.0. The servers have lodRampType (u8) at +0xC and scale at +0x10. The Store build has no room for both, and the data has 1.0 at +0xC |
| 0x010 | u32[8] | noScalePartBits | | by size: fills +0x10..+0x30 exactly; data: zero; no Store reader found |
| 0x030 | scr_string_t* | boneNames | FOLLOWING: align 4, Load_scr_string_tArray(nb) | script string per bone; data: j_spine4, j_neck, j_head, ... |
| 0x038 | u8* | parentList | FOLLOWING: unaligned, nb - nr bytes | parent of bone i (i ≥ nr) is `i - parentList[i - nr]` (data: consistent with baseMat) |
| 0x040 | s16* | quats | FOLLOWING: align 2, (nb - nr) × 4 s16 | local rotation (x, y, z, w) / 32767, parent space (data) |
| 0x048 | float* | trans | FOLLOWING: align 4, (nb - nr) × 3 floats | local translation, parent space (data) |
| 0x050 | u8* | partClassification | FOLLOWING: unaligned, nb bytes | hit location per bone (hitLocation_t, below) |
| 0x058 | DObjAnimMat* | baseMat | FOLLOWING: align 4, nb × 0x20 | model-space bind pose (XModelGetBasePose 14056A250) |
| 0x060 | ReactiveMotionModelPart* | reactiveMotionParts | FOLLOWING: align 16, × 0x10 | {center[3], stiffness} |
| 0x068 | Material** | materialHandles | always inline: align 8, Load_MaterialHandleArray(true, ns) (1403537F0) | one material per surface, indexed by lod.surfIndex + i (XModelGetSkins 14056A2F0) |
| 0x070 | XModelLodInfo[6] | lodInfo | Load_Stream(false); per LOD: Load_XModelSurfsPtr on +8, then Load_XModelSurfsFixup | |
| 0x1F0 | s8 | maxLoadedLod | | first LOD XModelGetLodForDist (14056A270) considers; data: 0 |
| 0x1F1 | s8 | numLods | | XModelGetLodForDist; DB_XModelSurfsFixup loop; data: 6 |
| 0x1F2 | s8 | collLod | | by position; data: -1 |
| 0x1F3 | u8 | flags | | bit 2: a LOD uses g_defaultSurfs (DB_XModelSurfsFixup); data: 0xC0 |
| 0x1F4 | s32 | numCollSurfs | | sizes collSurfs (sign-extended) |
| 0x1F8 | XModelCollSurf_s* | collSurfs | always inline: align 4, numCollSurfs × 0x24 | {Bounds, boneIdx, contents, surfFlags} |
| 0x200 | s32 | contents | | XModelGetContents (14056A260) |
| 0x208 | XBoneInfo* | boneInfo | always inline: align 4, nb × 0x1C | {Bounds bounds, radiusSquared} per bone |
| 0x210 | float | radius | | XModelGetRadius (140567D30); data: 19.65 |
| 0x214 | Bounds | bounds | | XModelGetBounds (140567D10): midPoint[3], halfSize[3] |
| 0x22C | u32 | unknown22C | | data: 0; servers have memUsage then bad after bounds; not placed |
| 0x230 | u16* | unknown230 (Store only) | always inline: align 2, ns × 2 | data: 35 values (4307, 3371, 8085, 32154, ...). LODs 0–2 repeat the same 7 values though their geometry differs, and surfaces with the same material have different values. Meaning unknown; no reader found |
| 0x238 | s32 | memUsage? | | data: 373495 (a plausible byte count); by position |
| 0x240 | PhysPreset* | physPreset | asset pointer (Load_PhysPresetPtr) | |
| 0x248 | PhysCollmap* | physCollmap | asset pointer (Load_PhysCollmapPtr) | |
| 0x250 | float | quantization? | | data: 1.0; by position (servers: quantization) |
| 0x254 | u32 | unknown254 | | data: 0xFFC00000 (a float NaN); padding or a Store-only field |

### XModelLodInfo (0x40 bytes, 6 per model)

| Off | Type | Name | Evidence |
|---|---|---|---|
| 0x00 | float | dist | XModelGetLodForDist picks the first LOD with dist > the distance; data: 300, 500, 1200, 2000, 3000, 1e6 |
| 0x04 | u16 | numsurfs | from modelSurfs->numsurfs (DB_XModelSurfsFixup); XModelGetSurfaces (14056A320) |
| 0x06 | u16 | surfIndex | running total of numsurfs (DB_XModelSurfsFixup); XModelGetSkins: materialHandles[surfIndex] |
| 0x08 | XModelSurfs* | modelSurfs | asset pointer (Load_XModelSurfsPtr) |
| 0x10 | s32[8] | partBits | copied from modelSurfs->partBits (Load_XModelSurfsFixup 140374250) |
| 0x30 | XSurface* | surfs | copied from modelSurfs->surfs; XModelGetSurfaces |
| 0x38 | u8[8] | unknown38 (Store only) | data: zero; not read by the loader |

### Link-time fixups

- **Load_XModelSurfsFixup (140374250)** runs after each LOD's Load_XModelSurfsPtr. If modelSurfs is set, it copies
  modelSurfs->partBits (+0x14, 32 bytes) and modelSurfs->surfs into the LOD.
- **DB_XModelSurfsFixup (1403712F0)** runs from Load_XModelAsset after DB_LinkXAssetEntry1:
  1. Clears flag 2.
  2. For each of the numLods LODs: copies partBits and surfs again; sets numsurfs and surfIndex (the running sum);
     sets flag 2 if `surfs == g_defaultSurfs` (144427260).
  3. Stores the sum in numsurfs (+0xA).

  Unlike the servers' copy, it does not skip a LOD whose modelSurfs is null (finding 1).

### Bones

The bone arrays are indexed by bone. The root bones (index < numRootBones) have no entry in parentList, quats or
trans: their local pose is the identity. A worked example follows the list.

- **Parent:** `parent(i) = i - parentList[i - numRootBones]`. Data: j_neck (1) → j_spine4 (0); j_head (2) → j_neck.
- **Local pose:** quat `quats[4 (i - nr) + k] / 32767` (x, y, z, w) and trans `trans[3 (i - nr) + k]`, both in the
  parent's space.
- **baseMat (DObjAnimMat)** is the model-space pose: `{quat[4], trans[3], transWeight}`, where
  `transWeight = 2 / |quat|²` (data: 2.0).
- **Data check:** composing the parent's baseMat with the local pose reproduces baseMat. Over all 98 bones of the
  data model, the largest error is 3e-5.
- **Bone references in surfaces** are byte offsets into the skinning matrix array: `bone index × 0x40` (0x40 is
  sizeof DObjSkelMat).
  - XRigidVertList.boneOffset 128 → bone 2, j_head (data).
  - The GPU blend table (below) holds the plain indices for the same vertices.
- **partBits** (on surfaces, XModelSurfs and LODs) mark the bones used, most significant bit first: bone b is
  `partBits[b >> 5] & (0x80000000 >> (b & 31))`. Data: a surface skinned to bone 2 has partBits[0] = 0x20000000.
- **Hit locations (partClassification)**: 0 none, 1 helmet, 2 head, 3 neck, 4 torso_upr, 5 torso_lwr,
  6 r_arm_upr, 7 l_arm_upr, 8 r_arm_lwr, 9 l_arm_lwr, 10 r_hand, 11 l_hand, 12 r_leg_upr, 13 l_leg_upr,
  14 r_leg_lwr, 15 l_leg_lwr, 16 r_foot, 17 l_foot, 18 gun, 19 shield, 20 armor, 21 soft (hitLocation_t, xb3 PDB).

**Worked example (data).** j_head (2), parent j_neck (1): its local quat (0, 0, 0.1465, 0.9892) and local trans,
composed with j_neck's base pose (quat (0, 0, -0.1465, 0.9892), trans (8.824, 0, 0)), give quat (0, 0, 0, 1) and
trans (11.806, -0.903, 0), which is j_head's baseMat.

## XModelSurfs (0x38 bytes)

The loader is Load_XModelSurfs (14035E750), the same as in the servers.

| Off | Type | Name | Load rule |
|---|---|---|---|
| 0x00 | const char* | name | XString (data: hash-like names such as "f1434dc6_7fb53070_100") |
| 0x08 | XSurface* | surfs | always inline: align 4, numsurfs × 0xE8, then Load_XSurface(false) on each |
| 0x10 | u16 | numsurfs | |
| 0x14 | s32[8] | partBits | |

**Where it lands (data).** The XModelSurfs header itself is loaded in the temp block. In the data zone, every
XModelSurfs follows the XModel header directly (temp address +0x258) and is linked into the asset pool.

## XSurface (0xE8 bytes)

The loader is Load_XSurface (14035EAF0). Buffers and views it creates are noted "GPU" (section "Renderer upload");
in the zone those fields hold whatever the exporter wrote, and the loader overwrites them.

| Off | Type | Name | Load rule | Notes |
|---|---|---|---|---|
| 0x00 | u16 | flags | | bit 3 (0x8): motion vertices (GfxPackedMotionVertex); data: 0x2 rigid, 0x6 blended (bit 2 = skinned?, unverified) |
| 0x02 | u16 | vertCount | | |
| 0x04 | u16 | triCount | | |
| 0x06 | u8 | rigidVertListCount | | |
| 0x07 | u8 | subdivLevelCount (Store only) | | padding in the servers; sizes sub_14035F430's array |
| 0x08 | s16[8] | blendVertCounts | | [n]: vertices blended from n + 1 bones |
| 0x18 | GfxVertexUnion0 | verts0 | FOLLOWING: align 16, vertCount × 0x20 (Load_GfxPackedVertexUnion 14034FAC0 / Load_GfxPackedMotionVertexUnion 14034FA50 by flag 0x8) | |
| 0x20 | u16* | triIndices | FOLLOWING: align 16, triCount × 3 u16 | triangle list |
| 0x28 | ID3D11Buffer* | vb0 | GPU: Load_VertexBuffer(&vb0, verts0, XSurfaceGetVert0Size × vertCount) | XSurfaceGetVert0Size (14066CD30) returns 0x20 |
| 0x30 | SRV* | vb0View | GPU: Load_VertexBufferView(.., vb0, same size, "vb0View") | |
| 0x38 | ID3D11Buffer* | indexBuffer | GPU: Load_IndexBuffer(&ib, triIndices, triCount × 3) | |
| 0x40 | XRigidVertList* | rigidVertLists | FOLLOWING: align 4, rigidVertListCount × 0x10 (Load_XRigidVertListArray, inlined) | |
| 0x48 | u16* | blendVerts | FOLLOWING: align 2, Σ (2n + 1) × blendVertCounts[n] u16 | XBlendInfo, below |
| 0x50 | u8* | blendVertsTable (Store only) | FOLLOWING: unaligned, vertCount × 0x20 | GPU skinning table, below |
| 0x58 | ID3D11Buffer* | blendVertsBuffer (Store only) | GPU: Load_RawDataBuffer(.., blendVertsTable, vertCount × 32, "blendVerts") | |
| 0x60 | SRV* | blendVertsView (Store only) | GPU: Load_RawDataBufferView(.., "blendVertsView") | |
| 0x68 | float(*)[2] | lmapUnwrap | FOLLOWING: align 4, vertCount × 8 | lightmap UVs; vertex declaration VERTDECL_PACKED_MLMAP's second stream (R32G32_FLOAT) |
| 0x70 | ID3D11Buffer* | vblmap | GPU: Load_VertexBuffer(.., lmapUnwrap, vertCount × 8) | |
| 0x78 | SRV* | vblmapView | GPU: "vblmapView" | |
| 0x80 | XSurfaceSubdivInfo* | subdiv (Store only) | always inline: align 4, sub_14035F3A0(true), then sub_1401B3DC0(&subdiv, surf) | subdivision surfaces, below |
| 0x88 | float* | tensionData | FOLLOWING: align 4, Σ blendVertCounts floats | |
| 0x90 | u16* | tensionAccumTable | FOLLOWING: align 2, vertCount × 16 u16 | |
| 0x98 | ID3D11Buffer* | tensionAccumTableBuffer | GPU: raw buffer "tensionAccumTable", vertCount × 32 bytes | |
| 0xA0 | SRV* | tensionAccumTableView | GPU: "tensionAccumTableView" | |
| 0xA8 | ID3D11Buffer* | tensionDataBuffer | GPU: raw buffer "tensionData", **vertCount** × 4 bytes from tensionData | see finding 2 |
| 0xB0 | SRV* | tensionDataView | GPU: "tensionDataView" | |
| 0xB8 | SRV* | indexBufferView | GPU: Load_IndexBufferView(.., indexBuffer, triCount × 6, "indexBufferView") | |
| 0xC0 | u32 | vertexLightingIndex | not read by the loader | data: 0, 0x51C, 0x55A, 0x5C6 for consecutive surfaces: a running vertex offset (each step is the previous surface's vertCount, apart from an extra 1 after the first) |
| 0xC4 | s32[8] | partBits | not read by the loader | bones the surface uses (MSB-first, above) |

### Vertices (GfxPackedVertex, 0x20 bytes)

The layout is given by the servers' PDB. The formats are what the Store build's input layouts declare for
VERTDECL_PACKED (1) and VERTDECL_PACKED_REACTIVEMOTION (2): s_streamSourceInfo 140BCCB20, entries 1 and 2, stream
stride 0x20. XSurfaceGetModelVertDecl picks `VERTDECL_PACKED + (flags & 8 ? 1 : 0)` (servers' r_xsurface.cpp:131).

| Off | Field | DXGI format (input layout) | Decoding |
|---|---|---|---|
| 0x00 | float xyz[3], binormalSign | R32G32B32A32_FLOAT (POSITION, w = binormalSign) | model space, inches, Z up; binormal = sign × cross(normal, tangent) (data: ±1.0) |
| 0x10 | GfxColor color | R8G8B8A8_UNORM (COLOR) | bytes r, g, b, a (data: 0xFFFFFFFF) |
| 0x14 | PackedTexCoords texCoord | R16G16_FLOAT (TEXCOORD_0) | u = half(low 16 bits), v = half(high 16 bits) |
| 0x18 | PackedUnitVec normal | R10G10B10A2_UNORM (NORMAL) | x = (p & 0x3FF) / 1023 × 2 − 1, y from bits 10–19, z from bits 20–29, a = (p >> 30) / 3 (Vec3UnpackUnitVecWithAlpha, servers' com_pack.cpp:68). Data: unit length within 0.0014; normal a = 1 |
| 0x1C | PackedUnitVec tangent | R10G10B10A2_UNORM (TANGENT) | same packing; data: tangent a = 0, normal·tangent within 0.003 |

The motion variant (flag 0x8, GfxPackedMotionVertex) has the same size and offsets. Its 0x0C holds
binormalSignAndHeight and its 0x10 holds pieceIndex.

The other model declarations add a second or third stream:

- VERTDECL_PACKED_VERTLIT (3): a vertex-lit color R8G8B8A8_UNORM plus two R16G16B16A16_FLOAT values, in stream 2.
- VERTDECL_PACKED_MLMAP (4): the lightmap UVs, R32G32_FLOAT, in stream 2, which is vblmap.

The Store build's stream source numbering has 23 slots; the servers' enum has 22. The slots from index 9 on
appear to be shifted by one (unverified).

### Triangles

triIndices is a triangle list: triCount × 3 u16 indices into the surface's vertices (data: all below vertCount).
The index buffer (DXGI R16) is created from it.

### Skinning

**Vertex order.** A surface's vertices come in two groups:

1. **Rigid vertices** first. Each XRigidVertList (0x10 bytes) covers the next vertCount vertices with one bone:

   | Off | Field |
   |---|---|
   | +0 | boneOffset (bone × 0x40) |
   | +2 | vertCount |
   | +4 | triOffset |
   | +6 | triCount |
   | +8 | collisionTree (FOLLOWING: align 4, Load_XSurfaceCollisionTree; or an offset) |

2. **Blended vertices**, grouped by bone count: blendVertCounts[0] one-bone vertices, then blendVertCounts[1]
   two-bone vertices, and so on.

In the data, each surface is either all rigid or all blended (Σ blendVertCounts = vertCount). The order when a
surface has both is the reading of tools/fastfile/xmodel.py, unverified.

**XBlendInfo (blendVerts).** Per vertex with n + 1 bones there are 2n + 1 u16 values: `bone0, bone1, weight1, ...,
boneN, weightN`. Bones are offsets (× 0x40); weights are /65536; bone0 gets 1 − Σ weights. Data: the two-bone
entry (0, 64, 14848) is bone 0 at 0.773 and bone 1 at 0.227.

**blendVertsTable (Store only, 0x20 bytes per vertex).** This is what the GPU skinning shaders read (raw buffer
"blendVerts"):

| Off | Field |
|---|---|
| +0x00 | u16 boneIndex[8] (plain indices, not offsets) |
| +0x10 | u16 weight[7] (weights of bones 1.., /65536) |
| +0x1E | u16 boneCount |

Data: all 314 blended vertices of a surface agree with blendVerts exactly.

**tensionData and tensionAccumTable** are absent from the data model. Their sizes are Σ blendVertCounts floats and
vertCount × 16 u16. They are probably for "tension" (wrinkle) maps; their use is unverified.

### Collision tree (XSurfaceCollisionTree, 0x38 bytes, per rigid vertex list)

The loader is Load_XSurfaceCollisionTree (14035F2E0).

| Off | Field | Load rule |
|---|---|---|
| 0x00 | trans[3] | |
| 0x0C | scale[3] | |
| 0x18 | nodeCount | |
| 0x20 | nodes | always inline: align 16, nodeCount × 0x10: {u16 mins[3], u16 maxs[3], childBeginIndex, childCount} |
| 0x28 | leafCount | |
| 0x30 | leafs | always inline: align 2, leafCount × u16 triangleBeginIndex |

The AABBs are quantized. The servers' XSurfaceTraceLineTree and XSurfaceVisitTrianglesInAabb_ConvertAabb read them
with trans and scale (by name; the exact dequantization is not verified here).

### Subdivision surfaces (Store only)

No server has these types. The names are this project's: they follow the debug names of the buffers built from
each array, and are marked as such in the headers.

**XSurfaceSubdivInfo (0x38 bytes).** The loader is sub_14035F3A0.

| Off | Field | Load rule |
|---|---|---|
| +0x00 | levels | always inline: align 4, subdivLevelCount × 0xE8 (sub_14035F430) |
| +0x08 | u32 flags | bit 2: patch flags converted |
| +0x0C | 0x14 bytes | unread |
| +0x20 | GfxSubdivCache {u32 size; buffer; UAV} | loaded with the header, then sub_1401B3D60 makes the "subdivCache" buffer (DEFAULT, VERTEX \| SHADER_RESOURCE \| UNORDERED_ACCESS, `size` bytes, no data) and the "subdivCacheView" UAV |

**XSurfaceSubdivLevel (0xE8 bytes).** All its arrays are always inline except rigidVertLists.

The counts at +0x08..+0x4B are u32: faceCount, regularPatchCount, regularPatchOffset, facePointCount,
facePointValence4Count, facePointBufferSize, edgePointCount, edgePointSmoothEnd, edgePointUVBorderEnd,
vertexPointCount, vertexPointValence4Count, vertexPointBufferSize, normalCount, normalBufferSize,
transitionPointCount, vertCount, vertOffset. Only the counts the arrays use are read by the code.

| Off | Array | Alignment and size |
|---|---|---|
| +0x00 | rigidVertLists | FOLLOWING or offset; align 4, rigidVertListCount × 16 |
| +0x50 | faceIndices | align 2, 6 × faceCount u16 |
| +0x58 | regularPatchIndices | align 2, 16 × regularPatchCount u16 |
| +0x60 | regularPatchFlags | align 4, regularPatchCount u32 |
| +0x68 | facePoints | align 4, facePointBufferSize & ~3 bytes |
| +0x70 | edgePoints | align 4, 2 × edgePointCount u32 |
| +0x78 | vertexPoints | align 4, vertexPointBufferSize & ~3 bytes |
| +0x80 | normals | align 4, normalBufferSize & ~3 bytes |
| +0x88 | transitionPoints | align 4, transitionPointCount u32 |
| +0x90 | regularPatchCones | align 4, 8 × regularPatchCount floats |
| +0x98..+0xE0 | buffers and views | made by sub_1401B4100 |

**GPU buffers (sub_1401B4100).** When r_loadForRenderer is on, sub_1401B4100 builds each level's buffers:

1. Once per info (flag bit 2), it rewrites every regularPatchFlags entry as `f & 0x3FF`, plus 0x110000 if bit 8 was
   set and 0x440000 if bit 9 was.
2. It builds:
   - index buffers of regularPatchIndices (count × 32 bytes) and faceIndices (count × 12 bytes);
   - raw SRVs of the index buffer;
   - IMMUTABLE raw buffers with SRVs for the flags, cones, facePoints, edgePoints, vertexPoints, normals and
     transitionPoints.

   Each temporary buffer pointer is released once its view exists (sub_1401AC5B0).

The decoder reports the flags as stored, without this rewrite.

## PhysPreset (0x58 bytes)

The loader is Load_PhysPreset (140355500). The layout is the servers' and is the same in the Store build.

| Off | Fields |
|---|---|
| 0x00 | name: XString |
| 0x08 | type (s32) |
| 0x0C | mass, bounce, friction, bulletForceScale, explosiveForceScale (floats) |
| 0x20 | sndAliasPrefix: XString |
| 0x28 | piecesSpreadFraction, piecesUpwardVelocity, minMomentum, maxMomentum, minVolume, maxVolume, minPitch, maxPitch (floats) |
| 0x48 | volumeType, pitchType (PhysPresetScaling: 0 linear, 1 quadratic) |
| 0x50 | tempDefaultToCylinder, perSurfaceSndAlias (bools) |

## PhysCollmap (0x58 bytes) and brushes

The loader is Load_PhysCollmap (1403552B0), with Load_PhysGeomInfoArray inlined.

**PhysCollmap:**

| Off | Field | Load rule |
|---|---|---|
| 0x00 | name | XString |
| 0x08 | u32 count | |
| 0x10 | geoms | always inline: align 4, count × 0x48 |
| 0x18 | PhysMass | centerOfMass[3], momentsOfInertia[3], productsOfInertia[3] |
| 0x3C | Bounds | |

**PhysGeomInfo (0x48 bytes):**

| Off | Field |
|---|---|
| 0x00 | brushWrapper: always inline (align 4, Load_BrushWrapper 14034AF80) |
| 0x08 | s32 type: PhysicsGeomType: 0 none, 1 box, 2 brushmodel, 3 brush, 4 collmap, 5 cylinder, 6 capsule, 7 glass |
| 0x0C | float orientation[3][3] |
| 0x30 | Bounds |

**BrushWrapper (0x58 bytes):**

| Off | Field | Load rule |
|---|---|---|
| 0x00 | Bounds | |
| 0x18 | cbrush_t (0x30), loaded by Load_cbrushWrapper_t (14035F860) | |
| 0x48 | s32 totalEdgeCount | |
| 0x50 | planes | FOLLOWING: align 4, numsides × cplane_s (0x14: normal[3], dist, u8 type, pad[3]) |

**cbrush_t (0x30 bytes):**

| Off | Field | Load rule |
|---|---|---|
| 0x00 | u16 numsides | |
| 0x02 | u16 glassPieceIndex | |
| 0x08 | sides | always inline: align 4, Load_cbrushside_tArray (14035FA50), numsides × 0x10: {plane (FOLLOWING: align 4, 0x14; or offset), u16 materialNum, u8 firstAdjacentSideOffset, u8 edgeCount} |
| 0x10 | baseAdjacentSide | always inline, unaligned, totalEdgeCount bytes (sign-extended) |
| 0x18 | s16 axialMaterialNum[2][3] | |
| 0x24 | u8 firstAdjacentSideOffsets[2][3] | |
| 0x2A | u8 edgeCount[2][3] | |

## The zone stream order of one XModel

This is what tools/fastfile/xmodel.py implements and tests/fastfile/test_xmodel.py builds by hand. Everything
follows inline, `[aN]` is a memory alignment, and the block is noted where it changes.

```
XModel header 0x258 (temp block, at the XModelPtr's aligned position); push virtual:
  name\0
  [a4] boneNames u32 × nb       parentList u8 × (nb-nr)       [a2] quats s16 × 4(nb-nr)
  [a4] trans f32 × 3(nb-nr)     partClassification u8 × nb    [a4] baseMat 0x20 × nb
  [a16] reactiveMotionParts 0x10 × n
  [a8] materialHandles 8 × ns, then each handle by the material rule (alias, or a Material inline)
  for each of the 6 LODs: modelSurfs by the asset pointer rule (push temp, [a4] XModelSurfs header 0x38;
      push virtual: name\0, [a4] XSurface headers 0xE8 × numsurfs, then per surface:
        [a16] verts 0x20 × vertCount     [a16] triIndices 6 × triCount
        [a4] rigidVertLists 0x10 × n, each: [a4] collision tree 0x38, [a16] nodes 0x10 × n, [a2] leafs 2 × n
        [a2] blendVerts                   blendVertsTable 0x20 × vertCount
        [a4] lmapUnwrap 8 × vertCount
        [a4] subdiv info 0x38, [a4] levels 0xE8 × n, then each level's arrays in field order
        [a4] tensionData                  [a2] tensionAccumTable 0x20 × vertCount
      pop; link; pop)
  [a4] collSurfs 0x24 × numCollSurfs    [a4] boneInfo 0x1C × nb    [a2] unknown230 2 × ns
  physPreset by the asset pointer rule  physCollmap by the asset pointer rule
pop
```

## Renderer upload (D3D11)

All of these are called from Load_XSurface right after the data loads. They are reconstructed in
src/gfx_d3d/r_buffers.cpp and tested there.

| Data | D3D11 resource |
|---|---|
| vertices | Load_VertexBuffer: IMMUTABLE, VERTEX_BUFFER \| SHADER_RESOURCE, ALLOW_RAW_VIEWS, vertCount × 0x20 bytes; a raw R32_TYPELESS SRV "vb0View" (Load_VertexBufferView) |
| indices | Load_IndexBuffer: IMMUTABLE, INDEX_BUFFER \| SHADER_RESOURCE, ALLOW_RAW_VIEWS, 2 × 3 × triCount bytes; raw SRV "indexBufferView" |
| lightmap UVs | a second vertex buffer (vblmap) and SRV |
| blend table, tension data and tension accumulation table | IMMUTABLE SHADER_RESOURCE raw buffers through Load_RawDataBuffer (sub_1401AC310) and raw SRVs. These feed the compute-shader skinning cache: the dynamic vertex buffer's raw view and UAV (docs/renderer.md) |
| subdivision data | sub_1401B3D60 and sub_1401B4100, above (reconstructed in src/gfx_d3d/r_subdiv.cpp, tests/differential/test_r_subdiv.py) |

With r_loadForRenderer off (a server, or the emulator), the vertex and index buffer loaders store NULL. The raw
buffer loaders do not check the dvar.

**For a Vulkan backend:**

- Every model buffer is device-local and immutable, so it can be uploaded once from the zone data.
- The SRVs become storage buffer descriptors: the shaders read vertices and indices as raw buffers.
- The input layout becomes a vertex input state with the formats above.

## Decoder and converters (tools/fastfile/xmodel.py)

**Loaders.** load_xmodel, load_xmodel_surfs, load_xsurface, load_collision_tree, load_subdiv_info, load_physpreset,
load_physcollmap and load_brush_wrapper follow the reconstructed C functions statement for statement. So do the
asset pointer rule (asset_ptr) and the two fixups. They run on any stream with the pipeline's Stream methods.
`register(iw6ff.ASSET_LOADERS)` plugs them into the reference reader's walk.

Inline materials need the material module's handle loader (`material_loader`); without one, the handles must be
aliases.

**Readers.** read_xmodel, read_xmodel_surfs, read_xsurface, read_physpreset and read_physcollmap turn a memory image
(the stream's, or the game's memory) into dataclasses:

- bones with local and base pose;
- LODs with surfaces;
- decoded vertices (position, binormal sign, color, UV, normal, tangent and their alphas);
- triangles;
- per-vertex skin weights;
- rigid lists with their collision trees;
- the raw blend data and table;
- lightmap UVs, tension data and subdivision levels;
- physics presets and collision maps.

**Converter: glTF 2.0.** `to_gltf(model)` and `write_glb` produce the following:

- **Skeleton.** One node per bone holds the local base pose. A skin's inverse bind matrices come from baseMat
  (tested: IBM × bind = I).
- **LODs.** Each LOD is its own mesh on its own node; the node's extras hold the LOD index and switch distance.
- **Surfaces.** Each surface is one primitive with POSITION, NORMAL, TANGENT (w = sign of binormalSign),
  TEXCOORD_0, COLOR_0 (normalized u8), JOINTS_0/WEIGHTS_0 (and _1 when a vertex has more than 4 bones) and u16
  indices.
- **Materials.** These are named references (the game material's name, e.g. ",m/mtl_head_hero_ghost_udt") with no
  textures.
- **Units.** Coordinates stay in game units (inches, Z up) under a root node that rotates Z up to Y up. `scale`
  converts units (0.0254 for meters).

The data model converts to a 743 KB binary: 6 meshes, 105 nodes, 5 materials.

**Tests (tests/fastfile/test_xmodel.py, 19 cases).**

- **Synthetic zone.** A hand-built zone has 3 bones, a rigid surface with a collision tree and a blended surface
  with the GPU table, tension data and one subdivision level. It also has aliased materials, a PhysPreset, and a
  PhysCollmap with one brush. The tests check:
  - that every zone byte is consumed;
  - where every array lands in the virtual block (offsets worked out by hand from the alignment rules);
  - the link order;
  - every decoded value;
  - that the GPU handles are cleared;
  - the glTF structure, IBMs, weights and the GLB container.
- **Real zones.** A real-zone test runs when IW6_FASTFILES is set and the pipeline's iw6ff.py is present. It
  decodes the XModels of the zones in IW6_XMODEL_ZONES and checks the invariants.

**What the real-data check against the game still needs from the pipeline:**

1. iw6ff.py's walk has to reach the model. Models load their materials inline (Load_MaterialHandleArray), so the
   material, technique set and image loaders are needed too, or the zone's earlier asset types.
2. Then run the game's DB_LoadXFile on the same zone in the emulator, with the same block bases, and compare each
   block's bytes with the reader's stream image. That is the pipeline's existing comparison, extended to these
   asset types.

The reader part (read_xmodel from the game's own memory) is already checked on the data model.

## Findings (for records/bugs.tsv; not added here)

1. **DB_XModelSurfsFixup (1403712F0) does not check a LOD's modelSurfs for null.**
   - The servers' copy skips such a LOD; the Store copy dereferences it for each of numLods LODs.
   - A zone whose LOD pointer is null with numLods covering it crashes at link time.
   - Kind: robustness, low (zones are built by the tools; signed zones are verified).
2. **The tension data buffer is sized by vertCount, the data by the blended vertex count.**
   - Load_XSurface creates the "tensionData" raw buffer (and its view) with vertCount × 4 bytes from tensionData,
     but loads only Σ blendVertCounts × 4 bytes.
   - On a surface with rigid vertices as well as blended ones, CreateBuffer's initial data reads past the array:
     into the next stream data, or past the block's end.
   - tensionAccumTable is not affected: its data and its buffer are both vertCount × 32 bytes.
   - Kind: ub/robustness, low (whether such surfaces exist in shipped zones is unknown; the data model has none).
3. **The loaders trust every count.**
   - numBones − numRootBones, numCollSurfs and totalEdgeCount are used signed or wrapped. A negative value becomes
     a huge Load_Stream, which reads the zone into memory far past the block.
   - This is the generated loaders' general contract. The unsigned zone variant (IWffu100) is not
     signature-checked, so a crafted unsigned zone can write past the block (security, for docs/security.md).
4. **sub_140601970 (src/gfx_d3d/r_buffers.cpp) takes a fourth argument.** sub_1401B4100 passes a debug name
   ("regularPatchIndices", "faceIndices") in R9, which the function never reads; the reconstruction declares
   three parameters. src/gfx_d3d/r_subdiv.cpp calls it through a four-parameter pointer to stay faithful. A
   decomp naming question, not a game bug.
5. **The matcher pairs 1403537F0 with Load_FxElemMarkVisualsArray. It is Load_MaterialHandleArray**: Load_XModel
   calls it where the PS4 Load_XModel calls Load_MaterialHandleArray. records/names.tsv now overrides the pair.

## Not established

| Field or behaviour | Status |
|---|---|
| XModel +0x10..+0x2F (noScalePartBits) | by size only; zero in the data |
| XModel +0x1F2 (collLod) | by position |
| XModel +0x22C | unknown; 0 in the data |
| XModel +0x230 | the Store-only u16 per surface; meaning unknown |
| XModel +0x238 (memUsage?) | by position and value |
| XModel +0x250 (quantization?) | by position and value |
| XModel +0x254 | unknown |
| XModelLodInfo +0x38 | unknown |
| XSurface flags other than 0x8 | |
| XSurface +0xC0 | the running-offset reading of vertexLightingIndex is from data only |
| tensionData / tensionAccumTable | use |
| Collision tree | dequantization |
| Subdivision | counts the code doesn't read; all names |
| XSurfaceSubdivInfo +0x0C..+0x1F | |
| Vertex order when a surface has both rigid and blended vertices | |
| Stream source numbering beyond index 8 | |
