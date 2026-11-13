# Materials, technique sets and shaders

What the Microsoft Store build (iw6mp64_MSStore_ship) loads for the asset types MATERIAL (5), VERTEXSHADER (7),
HULLSHADER (8), DOMAINSHADER (9), PIXELSHADER (10), VERTEXDECL (11) and TECHNIQUE_SET (12), how the zone stream
lays them out, and what the renderer does with them. The fastfile container, decompression, blocks and pointer
encoding are in docs/fastfiles.md; this page uses its terms.

| | |
|---|---|
| Structures | include/gfx_d3d/r_material.h (static_asserts on every size and on the offsets the code reads) |
| Loaders | src/gfx_d3d/r_material_load_db.cpp (27 functions), src/gfx_d3d/r_material.cpp (constant buffers), src/gfx_d3d/r_shader.cpp (shader and input layout creation) |
| Tests | tests/differential/test_r_material_load.py (every loader against the Store exe, stream functions faked), tests/fastfile/test_material.py (decoder) |
| Decoder | tools/fastfile/material.py (loaders + readers + JSON), tools/fastfile/dxbc.py (DXBC container and disassembler), tools/fastfile/material_tables.py (name tables), tools/fastfile/material_synth.py (synthetic streams) |

## Sources and what is verified

- **Names and types** are the server PDBs' (iw6_ds_xb3/ps4: `gfx_d3d/r_material_load_db.h`, `tr_types`, the `var*`
  globals in the PS4 MAP). The servers strip what a dedicated server doesn't draw: their `Load_Material` reads only
  the info and the constant buffers, `Load_MaterialTechniqueSet` only the name, and the shader creators are empty.
  The client structures are larger. **Every layout below is the Store build's**, taken from its loaders, which read
  each pointer and count at a fixed offset.
- Functions the servers inline away are named after Black Ops' PDB, which has them: `Load_MaterialTechnique`,
  `Load_MaterialPassArray`, `Load_MaterialTextureDefInfo`, `Load_GfxStateBits`, `Load_water_t`, `Load_PicmipWater`.
- **Verified by test**: all 27 loaders and `Load_InitMaterialConstantBuffer` match the Store exe in the
  differential harness (records/functions.tsv), and each test was mutation-checked. The synthetic streams the tests
  use were checked to be consumed exactly by the original loaders (tests/fastfile/test_material.py), so the stream
  layout described here is the game's.
- **Checked on real zones (not in the repo)**: the decoder, plugged into the pipeline's zone walker, read a
  `techsets_*.ff` zone (841 technique sets, 8275 shaders) and a `*_load.ff` zone (65 materials) to the exact end of
  their streams; every shader parsed as DXBC and disassembled without an unknown opcode. The real-zone check against
  the game's own loader is still to come (below).
- **Not verified**: field meanings the loaders don't touch (marked "server name" below) and the runtime notes taken
  from the servers' renderer code (marked "servers").

## Stream rules used here

- `atStreamStart`: an object is either read from the stream by its own loader (`Load_X(true)`) or was already read
  as part of its parent's bytes (`Load_X(false)`): then only its pointers are fixed up.
- A pointer holds 0 (NULL), `0xFDFDFDFFFFFFFFFF` ("inline": the data follows in the stream; called -1 below),
  `0xFDFDFDFFFFFFFFFE` ("inline + insert", asset pointers only: as -1, and `DB_InsertPointer` reserves an alias slot
  that receives the registered pointer; -2 below), or a packed offset into data loaded earlier
  (`DB_ConvertOffsetToPointer`; `DB_ConvertOffsetToAlias` for asset pointers, which reads the pointer stored there).
- Inline data is allocated at the stream position after aligning it (`+a-1 & ~(a-1)`); alignment changes memory
  addresses only, never the file bytes. Some members (marked "non-NULL = inline") have no offset form: any non-zero
  value means the data follows.
- Asset pointers (`Load_<Type>Ptr`) switch to the temp block (`DB_PushStreamPos(0)`), align the asset to 4, load it
  with `Load_<Type>(true)` and register it with `Load_<Type>Asset` (DB_AddXAsset, which may replace the pointer with an
  already loaded asset of the same name). Each asset's own data goes to the virtual block (`DB_PushStreamPos(3)`).
- An XString field: NULL, -1 (the NUL-terminated string follows, unaligned) or an offset.

## Material (0x3A8; servers 0x2D0)

`Load_Material` (Store 140352F90). Reached through `Load_MaterialHandle` (140353700) / `Load_MaterialHandleArray`
(1403537F0) from other assets, or as an XAsset.

| Offset | Type | Name | Load | Meaning |
|---|---|---|---|---|
| 0x000 | MaterialInfo | info | `Load_MaterialInfo` (140353AD0): name XString | see below |
| 0x028 | u8[412] | stateBitsEntry | - | per technique slot: index of its first pass's GfxStateBits in stateBitsTable (pass i uses entry + i) |
| 0x1C4 | u8 | textureCount | - | entries of textureTable |
| 0x1C5 | u8 | constantCount | - | entries of constantTable |
| 0x1C6 | u8 | stateBitsCount | - | entries of stateBitsTable |
| 0x1C7 | u8 | stateFlags | - | bit 0: in the depth prepass draw with `rgp.depthPrepassMaterial` instead (1406148D0) |
| 0x1C8 | u8 | cameraRegion | - | GfxCameraRegionType; 8 = none (the scene code skips it) |
| 0x1C9 | u8 | materialType | - | switched on by the draw code (14060000 block, server name) |
| 0x1CA | u8 | layerCount | - | PC only: entries of subMaterials (0: the material itself; 14063CAD0) |
| 0x1CB | u8 | assetFlags | - | bit 0: constant buffers dynamic (Load_InitMaterialConstantBuffer); bit 1: tested by the scene code |
| 0x1D0 | MaterialTechniqueSet* | techniqueSet | `Load_MaterialTechniqueSetPtr` (asset pointer) | |
| 0x1D8 | MaterialTextureDef* | textureTable | -1: align 4, textureCount x 0x10, then each def's `Load_MaterialTextureDefInfo`; or offset | |
| 0x1E0 | MaterialConstantDef* | constantTable | -1: align 16, constantCount x 0x20; or offset | |
| 0x1E8 | GfxStateBits* | stateBitsTable | -1: align 4, stateBitsCount x 0x1C, then `Load_GfxStateBits` each; or offset | |
| 0x1F0 | u8[412] | constantBufferIndex | - | per technique slot: index into constantBufferTable |
| 0x390 | MaterialConstantBufferDef* | constantBufferTable | -1: align 4, `Load_MaterialConstantBufferDefArray(true, constantBufferCount)`; or offset | |
| 0x398 | u8 | constantBufferCount | read, then `Load_InitMaterialConstantBuffer(&count, material)` | |
| 0x3A0 | const char** | subMaterials | non-NULL = inline: align 8, `Load_XStringArray(true, layerCount)` | PC only: one material name per layer (hashed by 14036CD20 when the material is sorted) |

Stream order: header (0x3A8, when at the stream start), info name, technique set, textures (all defs, then each
def's image/water), constants, state bits, constant buffers (all defs, then each def's data), layer names.

**MaterialInfo (0x28)**: name (XString), gameFlags (+8), sortKey (+9), textureAtlasRowCount (+0xA),
textureAtlasColumnCount (+0xB), textureAtlasFrameBlend (+0xC), textureAtlasAsArray (+0xD), renderFlags (+0xE),
drawSurf (+0x10, 16 bytes: the servers' GfxDrawSurfFields bit fields; the Store build's sort code, 14063CAD0, fills
bits 46-47 (prepass) and the material sorted index (bits 30-42) at load), surfaceTypeBits (+0x20), hashIndex (+0x24).
Only the name is loaded; the rest are server names at server offsets, consistent with the Store code that reads +8,
+0x10 and the drawSurf bits.

**MaterialTextureDef (0x10)**: nameHash (+0, u32: the hash of the sampler name the technique set's
`MTL_ARG_MATERIAL_TEXTURE/SAMPLER` arguments carry), nameStart/nameEnd (+4/+5: first and last character of that
name), samplerState (+6), semantic (+7, MaterialTextureSemantic), u (+8). `Load_MaterialTextureDefInfo`
(140354220): semantic 0xB (`TS_WATER_MAP`) makes u a water_t (-1: align 4, `Load_water_t(true)`, then
`Load_PicmipWater(&u)` downsamples it by the picmip setting; or offset); every other semantic makes u a GfxImage
pointer loaded by `Load_GfxImagePtr` (the image asset loader, not documented here).

- samplerState, by the servers' `SAMPLER_*` bits: filter (bits 0-2: disabled, nearest, linear, aniso2x, aniso4x,
  cmp, aniso16x), mip (bits 3-4: disabled, nearest, linear, bespoke), clamp U/V/W (bits 5-7, else wrap). The D3D11
  sampler bound is `dx.samplerStates[samplerState]`, which gfx_d3d/r_state.cpp's sub_14065FE60 builds for all 256
  values (the filter combinations come from the texture filter dvars).

**water_t (0x58)** (`Load_water_t`, 1403624D0): three float arrays at +8, +0x10, +0x18 (names from Black Ops: H0X,
H0Y, wTerm), each non-NULL = inline, align 4, `M * N` floats (M at +0x20, N at +0x24, int product); two images at
+0x48 and +0x50 (`Load_GfxImagePtr`). The bytes at 0 and 0x28-0x47 are not read by the loader (Black Ops has the
water's simulation parameters there).

**MaterialConstantDef (0x20)**: nameHash (+0), name (+4, 12 chars, not NUL-terminated when full), literal (+0x10,
float[4]). Read whole; matched by name hash against the technique set's `MTL_ARG_MATERIAL_CONST` arguments.

**MaterialConstantBufferDef (0x80)** (`Load_MaterialConstantBufferDefArray`, 1403532A0): sizes at +0 (vs, hs, ds, ps
data bytes) and +0x10 (vs, hs, ds, ps offset counts); data pointers at +0x20..+0x38, non-NULL = inline, align 16,
size bytes; offset arrays at +0x40..+0x58, non-NULL = inline, align 2, count x u16; four ID3D11Buffer pointers at
+0x60..+0x78, filled at load. The data is the material's constants already laid out as each stage's constant
buffer; `Load_InitMaterialConstantBuffer` (14063AF00) creates one buffer per stage with data (`R_CreateBufferInternal`:
ByteWidth = size, CONSTANT_BUFFER, initial data = the loaded bytes; IMMUTABLE, or DYNAMIC with CPU write when
assetFlags bit 0 is set). The offset arrays (server names) presumably locate the material constants inside that data
for updates; not used by the loader.

**GfxStateBits (0x1C)** (`Load_GfxStateBits`, 14034FCE0): loadBits[3] (+0), zone (+0xC: overwritten with the
loading zone's index, 140372140), depthStencilState[11] (+0xD: one per GfxDepthStencilMode), blendState (+0x18),
rasterizerState (+0x19). See "State bits" below.

## Technique set (0xCF0; servers 0x9B8)

`Load_MaterialTechniqueSet` (140353FF0), `Load_MaterialTechniqueSetPtr` (140354130).

| Offset | Type | Name | Load |
|---|---|---|---|
| 0x00 | const char* | name | XString |
| 0x08 | u16 | flags | server name |
| 0x0A | u8 | worldVertFormat | server name |
| 0x0B | u8 | preDisplacementOnlyCount | server name |
| 0x10 | MaterialTechnique*[412] | techniques | each -1: align 4, `Load_MaterialTechnique`; or offset (techniques shared between sets point at the first copy) |

**Technique slots (MaterialTechniqueType, 412)**: four groups of the servers' 103 names (include/gfx_d3d/r_material.h,
tools/fastfile/material_tables.py): 0x00 standard (`TECHNIQUE_DEPTH_PREPASS` .. `TECHNIQUE_DEBUG_BUMPMAP`), 0x67
instanced, 0xCE subdivision patches (PC only), 0x135 no displacement. The servers have three groups with the
no-displacement group at 0xCE. Evidence for the PC numbering: the Store build's R_SetupDrawGroup (1406148D0) adds
0x67 for instanced static models (surface types 3 and 5), 0xCE for surface types 7, 13 and 14, and 0x135 when the
draw surface asks for the no-displacement variant and the set has it (it tests `techniques[t + 0x135]`, offset
0x9B8 + 8t); the velocity pass picks 0x64/0x65 (`VELOCITY_RIGID/SKINNED`) or 0x132/0x133. The real technique sets
name the 0xCE group's techniques `subdiv_patch_*` and give them hull and domain shaders: they draw Catmull-Clark
subdivision surfaces (r_subdiv). The `SUBDIV_PATCH_` names are ours. Within a group the order is the servers':
depth prepass, shadow map depth, unlit, emissive (4), lit (lit, one light x7, two lights x30, dynamic branching x4,
then the same 41 with DFOG), light (4), fake light (2), sun preview, case texture, wireframe (2), thermal, velocity
(2), debug bumpmap.

**MaterialTechnique (0x10 + passCount x 0x48)** (`Load_MaterialTechnique`, 140353F50): name (+0, XString, loaded
after the passes), flags (+8; the Store build's 1406147F0 tests bit 0 (skipped unless a debug flag is set), 0x10
(needs a spot light) and 0x20), passCount (+0xA), passArray (+0x10). Always read at the stream start (its size
depends on passCount).

**MaterialPass (0x48)** (`Load_MaterialPassArray`, 140353B50):

| Offset | Type | Name | Load |
|---|---|---|---|
| 0x00 | MaterialVertexShader* | vertexShader | `Load_MaterialVertexShaderPtr` |
| 0x08 | MaterialVertexDeclaration* | vertexDecl | `Load_MaterialVertexDeclarationPtr` (after the vertex shader: the input layouts are built against it) |
| 0x10 | MaterialHullShader* | hullShader | `Load_MaterialHullShaderPtr` |
| 0x18 | MaterialDomainShader* | domainShader | `Load_MaterialDomainShaderPtr` |
| 0x20 | MaterialPixelShader* | pixelShader | `Load_MaterialPixelShaderPtr` |
| 0x28 | u8 | pixelOutputMask | server name |
| 0x29 | u8 | perPrimArgCount | arguments updated per primitive |
| 0x2A | u8 | perObjArgCount | per object |
| 0x2B | u8 | stableArgCount | per material/view (stable) |
| 0x2C | u16 x3 | perPrimArgSize, perObjArgSize, stableArgSize | server names: bytes of each argument group's constant buffer |
| 0x32 | u8 | zone | overwritten with the loading zone's index |
| 0x33 | u8 x3 | perPrimConstantBuffer, perObjConstantBuffer, stableConstantBuffer | server names: constant buffer slots |
| 0x38 | u32 | customBufferFlags | server name (CUSTOM_BUFFER_* bits) |
| 0x3C | u8 | customSamplerFlags | server name |
| 0x3D | u8 | precompiledIndex | static model precompiled pass index (Store string "Invalid or unassigned pre-compiled material index") |
| 0x3E | u8 | stageConfig | server name |
| 0x40 | MaterialShaderArgument* | args | non-NULL = inline: align 4, (perPrim + perObj + stable) x 0x10, in that order; then each `MTL_ARG_LITERAL_CONST` argument's u: -1: align 4, 16 bytes (4 floats); or offset |

**MaterialShaderArgument (0x10)**: type (+0), shader (+1: 0 compute, 1 vertex, 2 hull, 3 domain, 4 pixel), dest
(+2: constant register / texture or sampler slot), u (+8):

| type | name | u |
|---|---|---|
| 0 | MTL_ARG_CODE_CONST | index (u16, `CONST_SRC_*`), firstRow (u8), rowCount (u8) |
| 1 | MTL_ARG_CODE_TEXTURE | codeSampler (u32, `TEXTURE_SRC_*`): shader resource only |
| 2 | MTL_ARG_CODE_SAMPLER | codeSampler: texture and sampler |
| 3 | MTL_ARG_MATERIAL_CONST | nameHash of a MaterialConstantDef |
| 4 | MTL_ARG_LITERAL_CONST | pointer to 4 floats in the technique set |
| 5 | MTL_ARG_MATERIAL_TEXTURE | nameHash of a MaterialTextureDef |
| 6 | MTL_ARG_MATERIAL_SAMPLER | nameHash of a MaterialTextureDef (texture and its sampler) |

**Code constants and textures**: the Store build carries its own name tables, `s_codeConstantName` (140BCB060, 363
entries) and `s_codeTextureName` (140BCBBC0, 65), which give the PC numbering (tools/fastfile/material_tables.py):
the servers' order, with `CONST_SRC_CODE_REACTIVEMOTION_CENTERS` taking 16 consecutive indices (0x110..0x11F) instead
of one, so the float4 constants end at 0x122 and the matrices run 0x123..0x16A; and four more textures
(`TEXTURE_SRC_CODE_APEX0..2_DATA`, `TEXTURE_SRC_CODE_VOXEL_DATA`). The renderer fills them each frame (servers:
`R_SetPassShaderPrimArguments`, `..ObjectArguments`, `..StableArguments` in gfx_d3d/r_shade.cpp); which code fills
each constant is not mapped yet.

## Shaders

| Type | Size | Layout | Loader |
|---|---|---|---|
| MaterialVertexShader | 0x28 | name, vs (+8), loadDef (+0x10, 0x18) | `Load_MaterialVertexShader` (140354490), `..Ptr` (140354550) |
| MaterialPixelShader | 0x28 | name, ps, loadDef (0x18) | 140353DA0, 140353E60 |
| MaterialHullShader | 0x20 | name, hs, loadDef (0x10) | 140353920, 1403539E0 |
| MaterialDomainShader | 0x20 | name, ds, loadDef (0x10) | 140353550, 140353610 |

Load def: program (+0: -1: align 4, programSize bytes, then `Load_CreateMaterial<Stage>Shader`; or offset),
programSize (+8, u32, read as a signed int and sign-extended), loadForRenderer (+0xC, u16), and for vertex and pixel
shaders microCodeCrc (+0x10, server name; not read). The shader is created only when `r_loadForRenderer` is on and
loadForRenderer equals `r_rendererInUse` (gfx_d3d/r_shader.cpp; docs/renderer.md).

**The program is a complete DXBC container**, what ID3D11Device::Create*Shader takes. In the shipped technique sets
every shader is shader model 5.0 with the reflection stripped: the chunks are ISGN, OSGN (and PCSG for hull and
domain shaders) and SHEX only, no RDEF and no STAT. For a DXBC to SPIR-V translator (tools/fastfile/dxbc.py reads all
of it):

- SHEX: version token (program type in bits 16-31, model 5.0), length, then the instructions: opcode token (opcode
  bits 0-10, length bits 24-30, extended bit 31; customdata carries its length in the next token), operand tokens
  (component count, mask/swizzle/select, operand type, index dimension and representation per index, immediate
  values). Declarations give everything reflection would: `dcl_constantbuffer cbN[size]` (N is the slot the
  argument groups fill; the shipped shaders use cb0..cb5), `dcl_sampler sN`, `dcl_resource_* tN` with dimension and
  return type, inputs/outputs with system values and interpolation modes, temps and indexable temps, and the
  tessellation declarations (domain, partitioning, output primitive, control point counts, max tess factor, fork
  phases). Opcodes seen in the shipped set include the usual arithmetic, `sample*`, `deriv_rt?_coarse`,
  `f16tof32/f32tof16`, `bfi/ubfe`, `discard`, `if/else/endif`, `oMask` output: all core SM5, no doubles or UAVs in
  the material shaders.
- ISGN/OSGN/PCSG: semantic name and index, register, mask, component type and system value (D3D_NAME numbering) of
  each input and output; vertex shader inputs match the vertex declaration's semantics (s_streamDestInfo), stage
  outputs match the next stage's inputs, pixel shaders write SV_TARGET and some SV_Coverage.
- Bindings follow from the material: argument `dest` is the register/slot, `shader` the stage. Constant buffer slots
  0..2 hold the per-prim/per-object/stable groups and 3 the material's own buffer (servers' `CONSTANT_BUFFER_*`
  enum: PER_PRIM 0, PER_OBJECT 1, STABLE 2, MATERIAL 3, SUBDOMAIN 4, REACTIVEMOTION 5, REACTIVETURBULENCE 6,
  SMODEL_WORLDMATRIX 7, SMODEL_LIGHTING 8, SMODEL_AMBIENT 9; unverified for the Store build).

## Vertex declarations

**MaterialVertexDeclaration (0x838; servers 0x800)** (`Load_MaterialVertexDeclaration`, 1403542D0, `..Ptr`
1403543A0): name (+0), streamCount (+8), hasOptionalSource (+9), routing (+0x10, 0x828): data[31]
MaterialStreamRouting {source, dest, mask} then decl[249] ID3D11InputLayout pointers. After the routing is read,
`Load_MaterialVertexStreamRouting` (1406650E0) builds an input layout for every vertex declaration type against the
**current pass's vertex shader** (`varMaterialPass->vertexShader`), so a vertex declaration is only ever loaded from
a pass, after its vertex shader.

- source (`STREAM_SRC_*`, 22 named in the servers; the Store build's tables have 23 rows): position, color,
  texcoord 0, normal, tangent, texcoord 1-4, vertex lit 0-2, model lightmap coords, normal transform 0-3, color 2,
  texel density 0-1, displacement weights 0-1. Where each source lives for a vertex declaration type (stream,
  offset, DXGI format) is `s_streamSourceInfo[type]` (140BCCB20); dest (`STREAM_DST_*`: position, normal, color 0-1,
  depth, texcoord 0-25) picks the semantic name and index from `s_streamDestInfo` (1408AA310). See
  gfx_d3d/r_shader.cpp's Material_BuildVertexDecl; a type that lacks a source gets no layout, and drawing with it
  is a fatal error (servers' R_UpdateVertexDecl).
- In Vulkan this becomes the pipeline's vertex input state, chosen per (vertex declaration, vertex type).

## State bits

The loader keeps GfxStateBits as authored; the renderer binds D3D11 state objects from tables (servers' R_SetupPass
and R_SetState, gfx_d3d/r_shade.cpp / r_state.cpp):

- **Which entry**: pass i of technique t uses `stateBitsTable[stateBitsEntry[t] + i]`.
- **Rasterizer**: `dx.rasterizerStates[rasterizerState & 0x1F]`: bits 0-1 cull (0/1 none, 2 back, 3 front), 2-3
  polygon offset (1, 2: multiples of r_polygonOffset*; 3: the sm_polygonOffset* shadow map values), 4 wireframe;
  depth clip and scissor on (gfx_d3d/r_state.cpp sub_1406310F0).
- **Depth-stencil**: `dx.depthStencilStateTables[zone][depthStencilState[mode]]` for the current GfxDepthStencilMode
  (modes 0-2 become 5-7, "force depth write", when loadBits[1] bit 0 is set), with stencil ref = loadBits[0] bits
  8-15. The tables are created per zone from 64-bit state bits by sub_14065BED0: bit 0 depth write, bit 1 depth test
  off, bits 2-3 function (ALWAYS, GREATER, EQUAL, GREATER_EQUAL: reversed depth), bits 6-7 stencil front/back
  enable, bits 8-19 front pass/fail/zfail op and func, 20-31 back, 32-39 read mask, 40-47 write mask.
- **Blend**: `dx.blendStateTables[zone][blendState]`, created per zone from 32-bit blend bits by sub_140630A70 /
  sub_1406321C0: bits 0-3 src, 4-7 dest, 8-10 op (0 = blending off), 12-15/16-19/20-22 the alpha equivalents (op 0:
  alpha uses the colour factors), 24-27 RGBA write mask; factor and op tables in r_state.cpp.
- **loadBits** are the servers' `GFXS0_*` (alpha test, cull, polygon line, gamma write (bit 6, toggles sRGB render
  target views), stencil ref), `GFXS1_*` (depth write/test/func, polygon offset, stencil) and `GFXS_*` blend bits (the
  same layout as the blend tables' bits; bit 28 `GFXS2_DEPTHWRITE_OPAQUE` forces depth write without a prepass).
  The tables the indices point into come with each zone (the servers' XGfxGlobals: depth-stencil and blend state
  bits and constant buffer tables, created by `Load_CreateDepthStencilStateTable`/`Load_CreateBlendStateTable`).
- In Vulkan: rasterizer, depth-stencil and blend become pipeline state; the stencil reference is dynamic state.

## Runtime (servers' code, same shape in the Store build where checked)

- R_SetupDrawGroup (Store 1406148D0) picks the technique slot from the draw list and the surface type (see the
  technique slots), skips techniques whose passes all have loadBits[1] bit 0 clear in some lists, and
  R_SetMaterial's counterpart (1406147F0) records material, technique and slot.
- R_SetupPass binds the pixel, hull and domain shaders, the state bits and the material's constant buffer
  (`constantBufferTable[constantBufferIndex[t]]`); R_UpdateVertexDecl binds `vertexDecl->routing.decl[vertDeclType]`
  and the vertex shader; the argument groups are uploaded by R_SetPassShader*Arguments.

## Decoder and converters

tools/fastfile/material.py follows the loaders step for step on the pipeline's Stream (tools/fastfile/iw6ff.py), so
the memory it builds is laid out like the game's; `ASSET_LOADERS` maps the seven asset types to their loaders for the
pipeline's XAsset dispatch (wrap with `asset_ptr(type, loader)`). Readers turn that memory into dicts; converters:

- `material_json(read_material(s, at))`: info, flags, textures (hash, semantic, decoded sampler state, image name
  through `HOOKS["image_name"]`), constants, state bits decoded (load bits and rasterizer), per-technique state bits
  and constant buffer, constant buffers, and the technique set.
- `techset_json(read_techset(s, at))`: every technique by slot name, its passes, shaders by SHA-1 with their DXBC
  chunks, vertex declaration routing by STREAM_SRC/DST name, arguments resolved (code constants and textures by
  name, literals as floats, material constants/textures by hash).
- `export_shaders(techset, dir)`: each distinct shader as `<stage>_<sha1>.dxbc`, with a `.asm` listing from
  tools/fastfile/dxbc.py.
- Images are another loader's: `HOOKS["image_ptr"]` must be set to the image module's Load_GfxImagePtr before a
  zone with inline images (any material zone) is walked; the default resolves offsets and refuses inline images.

## Real-zone check (needs the pipeline)

When the pipeline reader lands: register `material.ASSET_LOADERS` (and the image loader) with its XAsset dispatch,
walk a zone, and compare each material/techset/shader/vertex declaration header and the memory it points at with
what tests/fastfile/store_emu.py's run of the Store build's own DB_LoadXFile leaves in its arena for the same zone
(pointers compared as offsets into their blocks). `techsets_*.ff` zones exercise technique sets, shaders and vertex
declarations; `*_load.ff` and map zones exercise materials, water and layered materials.

## Findings

- The matcher's `Load_MenuListPtr` pair for Store 14034F380 is wrong: it is `Load_GfxImagePtr` (records/names.tsv).
- Store 1406650E0 (named sub_1406650E0 before) is `Load_MaterialVertexStreamRouting`, the servers' MAP name.
- No memory-safety issues in these loaders beyond the stream's general trust in the zone (counts and sizes come
  from the file: e.g. a negative programSize sign-extends into a huge read; `Load_water_t`'s `M * N` is an int
  product). Zone authentication is the pipeline's concern.
