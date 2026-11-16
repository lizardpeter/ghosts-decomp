# The world's render data (GfxWorld, gfx_map)

What a map's render geometry is in the Store build (`iw6mp64_MSStore_ship`), how its zone carries it, and how to
get it out. From the Store build's loader (VAs given) and verified on real maps: the reference reader
(`tools/fastfile/gfxworld.py`) loads the GfxWorld of **mp_conflict.ff** (Dynasty) and **mp_alien_armory.ff**
(an Extinction map, probably Nightfall: *unverified*; Point of Contact is mp_alien_town) to exactly the state the game's own loader leaves (section 6). The servers have the struct
types (their GfxWorld is 0x9E8 bytes, PC 0xA30) but load almost none of it; names here are theirs where the
layout matches, and the PC-only parts are described. *unverified* marks what isn't established.

```
python3 tools/fastfile/gfxworld.py <map.ff> --out <dir>          (a zone the readers can walk to its GfxWorld)
python3 tests/fastfile/world_check.py <map.ff>                   (the game's loader in the emulator; $IW6_ORIGINALS)
```

The glTF export (`gfxworld.to_gltf`) has the world surfaces (one primitive per material: position, normal, UV,
lightmap UV, vertex colour) and every static model placement as a node with its XModel's LOD 0 as mesh, in game
units (inches, Z up) under a root node that turns them to glTF's Y up (and metres with `--scale`).

## 1. Where it is

Asset type **0x1A** (`gfx_map`, DB_GetXAssetTypeSize 0xA30), name `maps/mp/<map>.d3dbsp`. In the map's own zone,
near the end (mp_conflict.ff: asset 1702 of 1707, after the collision map). Its data is most of the zone:
mp_conflict.ff's GfxWorld is 0x6449000 bytes (100 MB) of the decompressed stream, mp_alien_armory.ff's 0x8A3D200.
The XModels it places are loaded inline (inside the static model list) unless an earlier asset loaded them; so are
its materials and images (the images streamed, docs/assets/images.md).

## 2. GfxWorld (0xA30 bytes)

| Off | Field | Loaded as |
|---|---|---|
| 0x000 | name, baseName | XStrings |
| 0x010 | bspVersion, planeCount (+0x14), nodeCount (+0x18), surfaceCount (+0x1C), skyCount (+0x20) | |
| 0x028 | skies | skyCount × 0x20 GfxSky: skySurfCount, skyStartSurfs (int ×), skyImage (GfxImage) |
| 0x030 | lastSunPrimaryLightIndex, primaryLightCount (+0x34), primaryLightEnvCount, sort keys | |
| 0x050 | dpvsPlanes (0x20) | Load_GfxWorldDpvsPlanes 140350CA0: cellCount, planes (planeCount × 0x14; -1 inline, else an offset to an earlier copy), nodes (u16 ×), sceneEntCellBits (runtime) |
| 0x070 | aabbTreeCounts | cellCount ints |
| 0x078 | aabbTrees | cellCount × 8, 128-aligned; each (Load_GfxCellTree 14034EE10) aabbTreeCounts[cell] × 0x38 GfxAabbTree with smodelIndexes (u16 ×) |
| 0x080 | cells | cellCount × 0x48 GfxCell (Load_GfxCell 14034EC90): bounds, portals (0x50 each, vertices 12 bytes each), reflection probe and reference index bytes |
| 0x088 | draw (0xB0) | Load_GfxWorldDraw 140351830, section 3 |
| 0x138 | lightGrid (0x620) | Load_GfxLightGrid 14034F650: rowDataStart, rawRowData, entries (8), colors (0xA8), stage gains, palette, and the tree (14034F8A0) at +0x5D0 |
| 0x758 | modelCount, models | × 0x3C GfxBrushModel (bounds, radius, startSurfIndex, surfaceCount) |
| 0x768 | bounds | *unverified* (the values measured don't look like bounds) |
| 0x784 | materialMemoryCount, materialMemory | × 0x10 {Material *, int} |
| 0x790 | sun (0x70 sunflare_t) | spriteMaterial (+8), flareMaterial (+0x10) |
| 0x7F0 | outdoorLookupMatrix (+0x800), outdoorImage (+0x840) | GfxImage |
| 0x848 | cellCasterBits, cellHasSunLitSurfsBits, sceneDynModel, sceneDynBrush, primaryLight(DynEnt)ShadowVis ×3, nonSunPrimaryLightForModelDynEnt | runtime block, sized from the counts |
| 0x888 | shadowGeom, shadowGeomOptimized | primaryLightCount × 0x18 (Load_GfxShadowGeometryArray 14034FBD0) |
| 0x898 | lightRegion | primaryLightCount × 0x10, hulls 0x58, axes 0x14 (Load_GfxLightRegion 14034F950) |
| 0x8A0 | dpvs (0x118; 0xE0 on the servers) | Load_GfxWorldDpvsStatic 140350DD0, section 4 |
| 0x9B8 | dpvsDyn (0x50) | Load_GfxWorldDpvsDynamic 140350990: all runtime |
| 0xA08 | mapVtxChecksum, heroOnlyLightCount (+0xA0C), heroOnlyLights (+0xA10, × 0x44) | |
| 0xA18 | fogTypesAllowed | |
| 0xA1C | PC only: Umbra tome size, tome data (+0xA20, 16-aligned), tome pointer (+0xA28) | the visibility data of the Umbra library: magic 0xD600, version 0x12 (1406B8020 checks it and points +0xA28 at it) |

## 3. Geometry (GfxWorldDraw, +0x88)

| Off | Field |
|---|---|
| 0x00 | reflectionProbeCount; reflectionProbes (+0x08, GfxImage * each), reflectionProbeOrigins (+0x10, 0x20 each with probe volumes 0x60), textures (+0x18, runtime) |
| 0x20 | reflectionProbeReferenceCount; origins (+0x28, 12 bytes), references (+0x30, bytes) |
| 0x38 | lightmapCount; lightmaps (+0x40, {primary, secondary} GfxImage), runtime textures (+0x48, +0x50), override images (+0x58, +0x60) |
| 0x68 | trisType, vertexCount (+0x6C) |
| 0x70 | vertices: vertexCount × **GfxWorldVertex** (0x2C), vertex buffer (+0x78) |
| 0x80 | vertexLayerDataSize; layer data (+0x88), its buffer (+0x90) |
| 0x98 | indexCount; indices (+0xA0, u16), index buffer (+0xA8) |

**GfxWorldVertex** (0x2C): xyz (3 float), binormalSign (float), colour (RGBA8), texCoord (2 float), lmapCoord
(2 float), normal and tangent (PackedUnitVec, 10:10:10:2 as in models, docs/assets/models.md).

A **surface** (GfxSurface, 0x28, in dpvs.surfaces): srfTriangles_t {vertexLayerData, firstVertex, maxEdgeLength,
vertexCount (u16), triCount (u16), baseIndex}, the Material (+0x18) and 8 bytes of lighting and flags (+0x20).
Its triangles are `indices[baseIndex .. baseIndex + 3 × triCount]`, each **relative to firstVertex** (checked: on
both maps every surface's indices stay inside the vertex array).

## 4. Static models and surfaces (GfxWorldDpvsStatic, +0x8A0, 0x118 bytes)

| Off | Field |
|---|---|
| 0x00 | smodelCount, staticSurfaceCount, the lit/decal/trans/shadow/emissive begin-end pairs |
| 0x30 | smodelVisDataCount, surfaceVisDataCount |
| 0x38-0xB0 | vis data: twelve runtime arrays (128-aligned) and one in the zone at +0x98 (smodelCount + 1 words; PC only) |
| 0xB8 | sortedSurfIndex (staticSurfaceCount words) |
| 0xC0 | smodelInsts (× 0x24: bounds, lighting origin) |
| 0xC8 | surfaces (surfaceCount × 0x28, above) |
| 0xD0 | surfacesBounds (× 0x24 on PC; 0x1C on the servers) |
| 0xD8 | smodelDrawInsts (× **0xB0** on PC; 0x90 on the servers), below |
| 0xE0-0xF8 | runtime: surfaceMaterials (× 0x10), surfaceCastsSunShadow, sunShadowOptCount (+0xF0), sunSurfVisDataCount (+0xF4), surfaceCastsSunShadowOpt |
| 0x100 | constantBuffersLit, constantBuffersAmbient (runtime: smodelCount pointers) |

**GfxStaticModelDrawInst** (0xB0): placement (origin, axis[3][3] forward/left/up, scale: 0x34 bytes), XModel *
(+0x38), groundLighting (+0x40), vertex lighting info (+0x50, **0x38** on PC: lighting values × 0x14, their buffer and
"lightingValuesView" shader view, numLightingValues at +0x34), then, *unverified* (the servers' order at the PC
sizes): lightmap info (+0x88, lightmapIndex +0x98), lightingHandle, cullDist (+0x9E), flags (+0xA0), staticModelId,
primaryLightEnvIndex, reflectionProbeIndex, firstMtlSkinIndex, sunShadowFlags.

## 5. Measured

| | mp_conflict (Dynasty) | mp_alien_armory (Extinction) |
|---|---|---|
| vertices | 374,756 | 652,316 |
| surfaces | 10,225 (373 materials) | 34,741 |
| static model placements / models | 5,566 / 185 (all in the zone) | 10,112 / 403 (399 in the zone) |
| cells, lightmaps, probes (Dynasty) | 37, 2, 3 | |

Rendered from the glTF export, both are the maps as in the game (layout, buildings, trees, placements).

## 6. How it was checked

`tests/fastfile/world_check.py` runs the Store build's own fastfile loader on the whole zone in the emulator
(tests/fastfile/store_emu.py), stops it where Load_GfxWorldPtr (140351D10) starts, hands the reader the game's
stream state (zone position, block positions, position stack, block memory, asset pool, streamed-image row
cursor), lets both load the GfxWorld, and compares the state when Load_GfxWorldPtr returns: the zone position,
every block's position and every byte written to it, and the asset pool. On both maps all are equal, with two
rules: GPU objects (D3D11 buffers and views) are 0 in the reader where the game created an object (it creates
material constant buffers even with r_loadForRenderer off); and XModel flag bytes are taken from the reader,
because the emulator's stand-in for DB_LinkXAssetEntry1 doesn't write the pool header back as the real one does
(14036D830), so there the game's surfs fixup runs on the other copy.

Doing this needed three emulator changes: a larger allocation heap (a map zone authenticates hundreds of blocks),
a stand-in for references to other zones' assets that aren't loaded (DB_AllocXAssetEntry with the default asset,
14036B340: a zeroed header in its own region), and tolerance for context methods sharing the device stand-in.
The reader also gained Load_NetConstStrings, the image picmip after loading (docs/assets/images.md 5) and the
faithful default-surfs flag in DB_XModelSurfsFixup.

## 7. Reconstructed in C

`src/gfx_d3d/r_gfx_world_load_db.cpp` (structs in `include/gfx_d3d/r_gfx_world.h`, sizes and offsets asserted):
every function below is differential-tested against the Store build (`tests/differential/test_gfxworld_load.py`,
150-200 random inputs each, with the stream functions and every callee as logged fakes, so the zone consumed, every
byte written, every stream variable set and every call made are compared) and mutation-checked (one deliberate
change per function, all caught).

| VA | Function | VA | Function |
|---|---|---|---|
| 140351D10 | Load_GfxWorldPtr | 14034F650 | Load_GfxLightGrid |
| 14034FF30 | Load_GfxWorld | 14034F8A0 | Load_GfxLightGridTree |
| 140350CA0 | Load_GfxWorldDpvsPlanes | 14034FBD0 | Load_GfxShadowGeometryArray |
| 14034EE10 | Load_GfxCellTree | 14034F950 | Load_GfxLightRegion |
| 14034EC90 | Load_GfxCell | 140350DD0 | Load_GfxWorldDpvsStatic |
| 140351830 | Load_GfxWorldDraw | 14034FD70 | Load_GfxStaticModelVertexLightingInfo |
| 140351E00 | Load_GfxWorldVertexData0 | 140361E10 | (name unknown): the constant buffer pointer arrays |
| 140351EB0 | Load_GfxWorldVertexLayerData | 140350990 | Load_GfxWorldDpvsDynamic |
| 1401B7180 | (name unknown): the Umbra tome pointer | 14034BBC0 | Load_ComWorld (com_map, section 8) |
|  |  | 14034BD90 | Load_ComWorldPtr |

The names other than Load_GfxWorldPtr/Load_GfxWorld/Load_GfxWorldAsset follow the generator's Load_<Type>
convention for the struct each loads (the servers don't have these functions); the 53 stream variables they set
are named var<Type> the same way (records/names.tsv).

## 8. Lighting and textures

### Lightmaps

GfxWorldDraw +0x38 is the lightmap count and +0x40 the lightmaps, each {primary, secondary} GfxImage. A world
surface's lightmap is the low byte of its lighting-and-flags word (surface +0x20: lightmapIndex,
reflectionProbeIndex, primaryLightEnvIndex, flags); 0xFF means none. Dynasty has 2 lightmaps:

| | format | size | bound at |
|---|---|---|---|
| primary | BC4 | 2048 × 4096 | t2: sun visibility (0..1) |
| secondary | R16G16B16A16_FLOAT | 1024 × 4096 | t3: two halves, see below |

Evidence: the DXBC of Dynasty's lit world pixel shader (techset `l_sm_r0c0nl0sl0l0_b1hb1c1vl1sl1l1sr0_nfwpf`, zone
techsets_mp_conflict.ff, disassembled with tools/fastfile/dxbc.py). From the vertex's lightmap coordinate (u, v) it
samples the secondary lightmap twice:

- **top** at (u, v / 2): rgb is the ambient term, a is the light direction's x;
- **bottom** at (u, v / 2 + 1/2): rgb is the directional term, a is the direction's y; z = sqrt(1 − x² − y²).

The baked diffuse light for a tangent-space normal N is `top.rgb · N.z + bottom.rgb · saturate(dot(N, dir))`, and
the pixel is `albedo · that + specular`. The LIT_DIR techniques (technique 8) add the sun on top: the sun colour
(constant buffer 1, register 6) times the primary lightmap's visibility. Reference code:
`gfxworld.decode_lightmap` and `gfxworld.lightmap_lighting` (tests/fastfile/test_gfxworld.py).

The values are linear HDR (Dynasty: mean ≈ 0.9, 99th percentile ≈ 8), so a viewer needs tone mapping. Static
models do not use the lightmaps. On Dynasty (5566 placed models) and Point of Contact, mp_alien_town (15260) none has
per-vertex lighting values (GfxStaticModelVertexLightingInfo +0x34 is 0 everywhere) and every model lightmap index
(+0x98) is 0xFFFFFFFF. The game lights them from the light grid at run time: R_SetAllStaticModelLighting
(Store 14063EEF0) calls R_GetLightingAtPoint (140682120) for every draw instance with flags (+0xA0) & 0x240, with
&world->lightGrid, the instance's lighting origin (GfxStaticModelInst, 0x24 bytes, +0x18), its primary light
environment (+0xA4) and its lighting handle (u16 at +0x9C) minus one. The handle is 0 in the zone on every instance:
the game assigns it at run time (R_AllocStaticModelLighting). Foliage also carries a ground lighting colour
(+0x40, 4 floats: HDR RGB and a fourth value; 1381 Dynasty instances, all grass and foliage). So props need the
light grid: R_GetLightingAtPoint -> R_GetLightingAtPointSH (140682240) -> GetLightingAtPoint (14067FF80) ->
R_LightGridLookup_Compressed (140683500) / _NonCompressed (140683BD0) -> R_GetLightGrid (140646380), which decodes a
block of the compressed tree (PC: through a 509-slot block cache, 140644CC0, that the servers do not have).

### Light grid (GfxWorld + 0x138)

What lights the static models (above) and moving objects. GfxLightGrid (0x620 bytes) holds the grid's bounds,
`entries` (8 bytes: colorsIndex, primaryLightEnvIndex, needsTrace), `colors` (GfxLightGridColors: rgb[56][3], 0xA8
bytes), a palette (`paletteEntryAddress`, `paletteBitstream`, with range exponents for 8, 12 and 16 bit encodings),
sky and default colours (56 × RGB floats each) and, at +0x5D0, a compressed tree (GfxLightGridTree, 0x50 bytes):

| tree | |
|---|---|
| +0x00 maxDepth (u8), +0x04 nodeCount, +0x08 leafCount | Dynasty: 8, 3498, 16071; Point of Contact: 9, 8871, 40597 |
| +0x0C coordMinGridSpace, +0x18 coordMaxGridSpace, +0x24 coordHalfSizeGridSpace | int[3] each |
| +0x30 defaultColorIndexBitCount, +0x34 defaultLightIndexBitCount | 16 and 8 (Dynasty) |
| +0x38 p_nodeTable (u32 × nodeCount), +0x40 leafTableSize, +0x48 p_leafTable | |

**Looking up a point** (R_GetLightGrid, Store 140646380). A grid point (u16 x, y, z) inside the bounds belongs to a
block of 4 × 4 points in x and y and 1 in z: block (bx, by, bz) = ((x − min.x) >> 2, (y − min.y) >> 2, z − min.z),
and its cell is `CELL_ORDER[(x & 3) + 4 · (y & 3)]` with CELL_ORDER = 0 1 4 5 2 3 6 7 8 9 12 13 10 11 14 15 (the
raw coordinate, not relative to min). The node table is an octree: each u32 is a child mask (high 8 bits) and an
index (low 24). From node 0, at each depth d = 0..maxDepth the child is bit (maxDepth − d) of bz, by, bx as
(z << 2 | y << 1 | x); a missing child means no data (all zero). Below maxDepth the next node is index + the number
of present children before this one; at maxDepth the index is the byte offset of the block group in the leaf
table.

**A block group** (R_DecodeLightGridBlock, 140644F00) is a bit stream, read least significant bit first:

1. Node header, byte aligned (R_LoadLightGridNodeBitStream): format (8 bits); a 6-bit byte size per present child;
   then for colour and light indices each: a minimum and bit count (format 1 / 8), a default (2 / 0x10) and a
   table of up to 16 values (4 / 0x20).
2. Skip the sizes of the children before this one; the block itself, byte aligned
   (R_LoadLightGridBlockBitStream): format (8 bits, when its size is not 0), per index kind a minimum and bit
   count, a default, and commands (R_LoadLightGridBlockIndexBitStream): 0 = all 16 values; 1 = 2 or 3 listed cells
   get one value; 2 = a cell mask, one value each; 3 = a cell mask, one value. Commands 1 and 3 end with a
   continue bit. Masks are 16 literal bits or a 4-bit code into a 16-entry table of 4-cell groups.
   Format 0x40 and 0x80 add two voxel masks (the low and high voxel bit of each cell).
3. Every cell starts at the default; the commands write their cells; values become indices relative to the
   minimum (0 stays 0, else value − 1 + min), through the node's table when it has one.

The result per point is GfxLightGridRaw: colorIndex, lightIndex (primary light environment) and 2 voxel bits.
`tools/fastfile/lightgrid.py` decodes it, function by function. tests/fastfile/lightgrid_check.py calls the game's
own R_GetLightGrid in the emulator (after the Store's table initialiser, 1406466E0) on every cell of sampled
blocks: 16000 Dynasty and 32000 Point of Contact cells, all equal.

**Colours.** A colorIndex selects a record of the palette: `paletteBitstream + paletteEntryAddress[colorIndex]`
(R_BlendLightGridColorsSH). The record is second-order spherical harmonics, 9 coefficients per colour channel
(R_DecodeLightGridSphericalHarmonics, Store 1406452D0, the coefficient decoders inlined):

- a u16 header with a 5-bit exponent per channel (r: bits 10–14, g: 5–9, b: 0–4), each minus 8; scale = 2^e;
- per channel, by its exponent against the grid's range exponents (+0x64, +0x65; Dynasty 0, 4, 23): up to the
  first, 9 bytes of 8-bit values; up to the second, 14 bytes of 12-bit values (8 bytes of high parts after the
  u16 c0, the low nibbles packed after them); else 18 bytes of u16 values. 12 and 16 bit channels start 2-byte
  aligned, and the record's size is even;
- coefficient 0 is value × scale / 2^bits (0 to scale), the others value × 2·scale / 2^bits − scale.

The light from a unit direction (x, y, z) is `c0 + c1 x + c2 y + c3 z + c4 zx + c5 zy + c6 xy + c7 (3z² − 1) +
c8 (x² − y²)` with the basis constants folded into the coefficients (R_SphericalHarmonicsToColorsLDR, which stores
it for the 56 grid directions as min(255, 127.5·sqrt(L)): 1.0 is mid-range). Dynasty: 65310 palette entries
(2.7 MB); sampled at the static models' lighting origins the light from straight up is bluish (the sky),
mean ≈ (3.3, 3.8, 4.6).

**World to grid** (R_LightGridLookup_Compressed): grid x, y = (floor(v) + 0x20000) >> 5 (32 units), z the same
>> 6 (64 units); the game blends the 8 surrounding points by trilinear weights (corner i = (i >> 2, i >> 1 & 1,
i & 1)) after testing each sample's visibility (R_IsValidLightGridSample, the voxel bits, the primary light
environment). `lightgrid.sample_sh` blends the corners that have colour, without the visibility tests: an
approximation.

Scale against the lightmaps: *unverified*. Rendered with the same factor, grid-lit models on Dynasty come out about
four times brighter than lightmapped surfaces around them (light from above ≈ 3–4.6 against a lightmap mean of
≈ 0.9). Either the grid holds light the lightmaps leave to the sun pass, or the model shaders scale it; the model
shaders' use of the coefficients has not been read yet.

`decode_spherical_harmonics` equals the game's decoder bit for bit on 2000 Dynasty palette entries
(tests/fastfile/lightgrid_check.py); on Point of Contact the tree and palette checks are equal as well (8000 cells,
2000 entries).

### Primary lights (ComWorld, com_map, asset type 0x14)

ComWorld (0x28): name, isInUse, primaryLightCount (+0x0C), primaryLights (+0x10, × 0x78), primaryLightEnvCount
(+0x18), primaryLightEnvs (+0x20, × 0xA: four light indices and a count). ComPrimaryLight: type (1 sun, 2 spot,
3 omni), canUseShadowMap, exponent, colour (+4), dir (+0x10), up (+0x1C), origin (+0x28), radius (+0x34), the cone
cosines (outer, inner, expanded), rotation and translation limits, cookie animation (rotation, scroll, scale,
translation), defName (+0x70, an XString). Light 0 is always empty; Dynasty has the sun (light 1) and 25 spots.
Load_ComWorld (14034BBC0) and Load_ComWorldPtr (14034BD90) are reconstructed in C (section 7);
`gfxworld.read_com_world` reads them.

The static lights are already baked into the lightmaps; the primary lights are what the game lights dynamic
objects and specular with. The sun's dir is taken to point towards the sun (*unverified*).

### Material texture roles

A material's texture table (Material +0x1D8, 16 bytes per entry: name hash, first and last name characters,
sampler state, semantic, image) doesn't say which texture is the colour map; the shader does. In the lit world
shaders the MATERIAL_TEXTURE arguments bind:

| name hash | register | role | image semantic |
|---|---|---|---|
| 0xA0AB1041 | t0 | base colour | 2 (colour map) |
| 0x59D30D0F | t6 | normal map | 5 (normal map) |
| 0x34ECCCB3 | t7 | specular map | 8 (specular map) |

Other shaders (water, for example) reuse the hashes for other images, so `material.texture_roles` takes a hash
only when the image's semantic agrees, and otherwise falls back to the first image of the role's semantic.
Normal maps are BC5 (x, y) or BC3 with x in alpha and y in green; z = sqrt(1 − x² − y²).

### glTF

`to_gltf(..., material_images=, lightmap_images=, lights=)` groups world triangles per (material, lightmap),
names the materials `<material>@lm<N>`, uses the base colour as baseColorTexture, lists the other roles and the
lightmap images in the material extras, and writes the primary lights as KHR_lights_punctual. COLOR_0 is the
stored vertex colour; multiplied into the base colour it gives false colours (red to yellow gradients, magenta), so
on blended surfaces it most likely holds layer weights, not a tint (*unverified*: the vertex shaders' use). Most streamed images of a map live in the image paks (`imagefileN.pak`, docs/assets/images.md); without
those the exporter can only use the images in the zone itself.

## 9. Not done

- The collision map (col_map_mp), map entities (map_ents), lightdef, effects (fx_map), glass
  (glass_map): separate assets.
- The light grid's visibility tests (R_IsValidLightGridSample, the voxel bits, light environments), its
  non-compressed path (entries, colors) and hero-only lights; vertex lighting values (unused on the maps measured).
- The Umbra tome's contents, the surface lighting flags, the vertex layer data and the
  PC-only vis arrays: loaded and placed exactly, their meaning *unverified*.
- Walking a map zone from the start with the readers alone needs every asset type before the GfxWorld (sound,
  fx, xanim, ...); until then the game's loader gets there (world_check.py).
