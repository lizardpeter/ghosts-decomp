# Images (GfxImage) and the image paks

What a texture is in the Store build (`iw6mp64_MSStore_ship`), how a zone carries it, where its pixels live, and
how to get every texture out at full resolution. Everything here is from the Store build's code (VAs given) or
measured on real files (named); what isn't is marked *unverified*. The container and the stream rules are
docs/fastfiles.md; the D3D11 side (texture creation and upload) is docs/renderer.md and src/gfx_d3d/r_image.cpp.

Reference reader: `tools/fastfile/image.py` (with `bcn.py` for previews). Tests: `tests/fastfile/test_image.py`
(synthetic, plus invariants on real zones when `IW6_FASTFILES` is set) and `tests/differential/test_image_load.py`
(the loaders against the exe).

```
python3 tools/fastfile/image.py <zone.ff> [--paks <folder with imagefileN.pak>] [--out <dir>] [--png] [--json]
```

lists a zone's images and writes each one whose data is available as a DDS (DX10 header, any DXGI format, full
mip chain, cube faces in D3D order), and with `--png` the top mip as PNG for BC1-BC5 and RGBA8.

## 1. Two kinds of image

| | in the zone | streamed |
|---|---|---|
| `GfxImage::streaming` (+0x35) | 0 | non-zero |
| pixels | in the zone, right after the header (`loadDef`, +0x38) | in `imagefile<N>.pak`, four stream levels |
| `width`, `height`, `levelCount` | the real size | 1, 1, 1 (a placeholder until a level is streamed in) |
| `streamLevels[4]` (+0x40) | 0 | the size of each level, smallest first |
| `cardMemory.platform[0]` / `[1]` | the pixel bytes / the same | 0 / the full image's bytes |
| measured on | mp_alien_town_load.ff: 63 images (load screen, playlist icons; RGBA8, BC2, BC3), all with flags 0x2 | common_bots_mp.ff: the dog's textures (BC1 colour, BC5 normal, BC3 specular), 72 rows |

Character, weapon and map textures are streamed; small UI images are in the zone. A zone can also refer to images
loaded by another zone (an alias, docs/fastfiles.md 7): the `_tr` character zones measured have none of their own.

## 2. GfxImage (0x68 bytes; the servers' is 0x38)

| Off | Type | Name | Meaning |
|---|---|---|---|
| 0x00 | GfxTexture (0x18) | texture | the D3D11 resource and its two shader views; null in the zone, created by Load_Texture |
| 0x18 | DXGI_FORMAT (u32) | format | the texture format (the Store build keeps it here; the servers have no format) |
| 0x1C | u8 | mapType | 2 1D, 3 2D, 4 3D, 5 cube, 6 2D array |
| 0x1D | u8 | semantic | TextureSemantic: 0 2D, 1 function, 2 colour, 3 detail, 5 normal, 8 specular, 10 oceanflow displacement, 11 water, 12 ocean displacement, 13 displacement, 14 parallax |
| 0x1E | u8 | category | 0 unknown, 1 auto-generated, 2 lightmap, 3 load from file (every image measured), 4 raw, 5 water, 6 render target, 7 temp |
| 0x1F | u8 | flags | 0x02: no picmip (keep every stream level); 0x10: copied into a per-image bit set by Load_ImageStream (meaning *unverified*); 0x20: the water texture is a staging texture (Load_Texture) |
| 0x20 | Picmip (2 × u8) | picmip | set after loading (section 5): stream levels left off the top |
| 0x22 | u8 | track | |
| 0x24 | i32 × 2 | cardMemory | [0]: bytes of the pixels the texture has now; [1]: bytes of the full image |
| 0x2C | u16 | width | |
| 0x2E | u16 | height | |
| 0x30 | u16 | depth | 3D textures |
| 0x32 | u16 | numElements | array slices |
| 0x34 | u8 | levelCount | mip levels |
| 0x35 | u8 | streaming | the image is streamed (Load_ImageStream 140374E70 tests it) |
| 0x36 | u8 × 2 | | *unverified* |
| 0x38 | GfxImageLoadDef * | loadDef | in the zone: the pixels of an image that isn't streamed (Load_GfxTextureLoad) |
| 0x40 | GfxImageStreamLevel × 4 | streamLevels | per level: u16 width, u16 height, u32 (card memory in the low 26 bits, mip count in the top 6); the servers' GfxImageStreamData {width, height, pixelSize} |
| 0x60 | const char * | name | |

Offsets verified by the reconstructed code (static_asserts in src/gfx_d3d/r_image.cpp, the loaders below) and the
values measured on the zones above.

## 3. In the zone (Load_GfxImagePtr)

As the loaders read it (src/gfx_d3d/r_image_load_db.cpp, all three matching the exe):

1. **Load_GfxImagePtr** (14034F380), the asset pointer rule: in the temp block, null stays; an offset is an alias
   (DB_ConvertOffsetToAlias); -1/-2 mean the image follows: align to 4, load it, link it with
   **Load_GfxImageAsset** (140372150, which takes the database lock and calls DB_LinkXAssetEntry1 14036D830 for type
   0x0D), and with -2 fill the reserved alias slot.
2. **Load_GfxImage** (14034F120): the 0x68-byte header; then in the virtual block the name (an XString: -1 inline
   at the current position, else an offset); then Load_GfxTextureLoad; then 1403723B0 (section 5).
3. **Load_GfxTextureLoad** (14034F1D0): `loadDef` in the temp block. Null for a streamed image. -1/-2: the pixels
   follow at the current position (no alignment): **1 byte** for the water image (semantic 11, whose texture is
   generated), otherwise **cardMemory.platform[0] bytes**. **Load_Texture** (14062BA80) creates the texture from
   them at once, because the temp block is reused by the next asset.

The pixels are every face (6 for a cube, numElements for an array, else 1), each with its whole mip chain, largest
first. A mip level is `max(1, size >> mip)` in each dimension and `Image_GetCardMemoryAmountForMipLevel` bytes:
`ceil(w / b) * ceil(h / b) * depth * bytes per block`, with 4 × 4 blocks for BC formats. Cube faces are in D3D
order (Image_CubemapFace 14062E0F0 is the identity).

## 4. Streamed images

### The rows

A fastfile's header has the streamed-image rows (docs/fastfiles.md 11): 24 bytes each, {u16 localized, u16 file
index N, u32 pad, u64 offset, u64 end}. **Load_ImageStream** (140374E70, src/database/db_registry.cpp, matching the
exe), the image type's hook run on every newly linked image with its index in the image pool (0x18A0 = 6304
images), does this for an image with `streaming` set:

- it takes the next **four** rows (sub_1403492E0), one per stream level **in order, smallest level first**, and
  stores {offset, end, file} per level in a 0x60-byte entry per pool image (145FB8200). A row with end 0 is a level
  the image doesn't have (an image smaller than the largest level size has fewer levels; measured: the dog's eye
  textures have 3).
- the file is the fastfile itself for N = 0 (sub_1403497F0), else `imagefile<N>.pak`, or
  `<language>_imagefile<N>.pak` when `localized` is set, opened on first use (sub_140548160, which also opens
  `soundfile<N>.pak` for sounds; a failed open is DB_DirtyDiscError). Up to 0x60 paks (14604CFE0, 0x70 each).
- it keeps the image's flag 0x10 in a bit set (14604C200) and the length of the diagonal of level 0
  (`sqrt(w² + h²)`, 145F94D80), which the streaming code uses to prioritise (*unverified* beyond that).

Images not streamed take no rows. The rows of a zone are consumed exactly by its streamed images, in the order the
images are linked (an image inside a material is linked when the material is loaded).

### A level's data

Each row's range `[offset, end)` is **one zlib stream** (measured on imagefile4.pak and imagefile10.pak: every range
read for common_bots_mp.ff inflates completely). Inflated:

- **level 0**: every face's **complete mip chain** at streamLevels[0]'s size (its `levelCount` mips);
- **level k > 0**: every face's **top mip only**, at streamLevels[k]'s size.

So level k's data is `card(k) - card(k-1)` bytes, which is exactly how much the game reads for it
(140375AD0: `streamLevels[k].card - streamLevels[k-1].card`, through DB_ReadXFile 140349B80 with the fastfile
reader's inflate, after DB_InflateInit), and the smaller mips of a level come from the texture of the level below
(14062DCD0 copies them; sub_14062B580 uploads all mips for level 0 and one for the others). Each level's
`levelCount` is one more than the level below's, and its size twice.

Measured on common_bots_mp.ff, `dog_a_head_a_col` (BC1): levels 128² (10936 bytes, 8 mips), 256², 512², 1024²;
the rows inflate to 10936, 32768, 131072 and 524288 bytes, and 524288 + 131072 + 32768 + 10936 = 699064 =
cardMemory[1] = the full 1024² chain of 11 mips.

**The full image** is the highest level present, assembled as: for each face, the top mip of level K, of K-1, ...,
of level 1, then level 0's chain. `image.assemble_streamed` does this; the result has the layout of an in-zone
image (section 3) and is written to DDS.

The game loads levels one at a time, from small to large, as the streamer decides (requests in a ring at
146052650, `image index + level × 0x18A0`; 140375AD0 and its callees, not reconstructed). The order doesn't change
the data.

### The paks

`imagefile<N>.pak` starts with its own header (docs/fastfiles.md 11): magic `IWff0100`/`IWffu100`, an encrypted
count, a hash, an RSA signature, and an encrypted index of 16-byte entries read by sub_140375350 at the end of each
zone load (measured: 1977 entries in imagefile1.pak, increasing u64 offsets). The image data is read only through
the rows; what the index is used for is *unverified*. A zone's rows can point into many paks (common_bots_mp.ff:
imagefile4, 7 and 10).

## 5. After loading: picmip

`1403723B0` runs **sub_14062E430**(image, &image->picmip) on every image Load_GfxImage loads (all matching the
exe): with flags 0x2 the picmip is 0, 0 (no level left off). Otherwise **Image_GetPicmip** (14062B3C0) gives the
setting for the image's kind: colour, detail, water, ocean, parallax maps use 14A2E2968; normal and displacement
maps 14A2E296C; specular maps 14A2E2970 (Black Ops' imageGlobals.picmip / picmipBump / picmipSpec), clamped to
0-3, second byte 2; other kinds 0, 0. That value is then limited to the number of stream levels - 1
(sub_14062D6A0 counts them), and levels are left off the top only while the top level remaining is larger than
`1024 >> picmip` in both dimensions. With picmip 0 every level is used.

## 6. Reconstructed and tested

| VA | Function | File | Test |
|---|---|---|---|
| 14034F380 | Load_GfxImagePtr | src/gfx_d3d/r_image_load_db.cpp | test_image_load.py, 200 cases |
| 14034F120 | Load_GfxImage | src/gfx_d3d/r_image_load_db.cpp | 200 cases |
| 14034F1D0 | Load_GfxTextureLoad | src/gfx_d3d/r_image_load_db.cpp | 200 cases |
| 140374E70 | Load_ImageStream (Store body) | src/database/db_registry.cpp | 200 cases |
| 1403723B0 | (name unknown) | src/database/db_registry.cpp | 40 cases |
| 14062B3C0 | Image_GetPicmip | src/gfx_d3d/r_image.cpp | 200 cases |
| 14062D6A0 | (name unknown): stream level count | src/gfx_d3d/r_image.cpp | 200 cases |
| 14062E430 | (name unknown): picmip from stream levels | src/gfx_d3d/r_image_load_common.cpp | 200 cases |

Mutation checks (one change each, rebuilt and rerun): the water size, the dropped post-load call, the pointer
alignment, a stream level's end, the bit set update, the pak's language flag, the picmip clamp, a semantic case,
the 1024 limit and a comparison; all ten caught. Already reconstructed elsewhere: Load_Texture (14062BA80),
sub_14062B580 (stream level upload), sub_14062DA40 (make a level current), sub_14062B110 (a texture for a level).

## 7. Checked against real data

- **Decoder vs Pillow**: the DDS files written for `img_load_map` (BC3, in zone), `icon_pl_war_games` (RGBA8) and
  `dog_a_head_a_col` (BC1, streamed, assembled from four levels at 1024²) open in Pillow, and Pillow's decode equals
  `bcn.py`'s byte for byte. The images look right (a map overview, a playlist icon, the dog's head texture).
- **Invariants** (tests/fastfile/test_image.py, RealZones): every in-zone image's pixels are cardMemory[0] bytes
  and its mip chain's size; every streamed image's stream levels have card memory equal to their mip chain, each
  level twice the size and one more mip than the one below; the rows are consumed in fours and, in a zone walked
  to the end, all of them.

## 8. Not established

- The fastfile-internal stream data (rows with file index 0): patch_common_alien_mp.ff and code_nvidia.ff have
  them, and the pipeline's reader doesn't open those files yet (an authentication block check fails, docs/
  fastfiles.md); how the data sits in the file is *unverified*.
- The pak index's purpose, flags 0x10, bytes 0x36-0x37, `track`, and the streamer's scheduling (140375620,
  140375AD0, 140376140, 1403776D0, 140379390: priority by screen size via the diagonal, memory budget).
- Localized paks (`<language>_imagefile<N>.pak`): the naming is from the code; none measured.
- 3D and array textures from real zones (the layout rule is the code's; no such image measured yet).
