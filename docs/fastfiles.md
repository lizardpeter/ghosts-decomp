# Fastfiles

How the Microsoft Store build (`iw6mp64_MSStore_ship`) reads a fastfile (`.ff`), from the code that does it. Every
rule names the function (Store address) it comes from, or says "measured on <file>"; anything else is marked
*unverified*. Names come from the PS4 and Xbox One server PDBs (`analysis/iw6_ds_ps4`, `iw6_ds_xb3`), whose
database code is the same apart from the differences noted; identifications are in `records/names.tsv`.

The reference reader is `tools/fastfile/iw6ff.py` (standard library only). It is checked against the game itself:
`tests/fastfile/store_emu.py` runs the Store build's own `DB_LoadXFile` in the emulator on the same file, and
`tests/fastfile/test_store.py` requires the reader's script strings, asset types and names, every byte of every
block and the asset pool copies to equal the game's (section 12).

## 1. The file

A fastfile is an uncompressed prefix, then the compressed zone: directly (unsigned) or inside an authenticated block
chain (signed). `DB_LoadXFile` (140349300) reads the prefix with `DB_ReadXFileUncompressed` (140349E20):

| Offset | Size | Field | Rule |
|---|---|---|---|
| 0 | 8 | magic | `IWff0100` (signed) or `IWffu100` (unsigned); anything else is `DB_DirtyDiscError` (1403496B0): "Disc read error" |
| 8 | 4 | version | must be 0x235; otherwise a memory-backed file just returns, a disk file is `Com_Error(ERR_DROP, "...out of date / newer than client executable...")` |
| 12 | 1 | *unused* | read and dropped (1 in every file measured) |
| 13 | 1 | compressor | `DB_SetFileLoadCompressor` (14034A000): 0 zlib, 2 passthrough, else "Unknown compression type" |
| 14 | 2 | *unused* | read and dropped (8, 4 measured) |
| 16 | 8 | *unused* | two dwords read and dropped (0 measured) |
| 24 | 4 | streamed image row count | at most 0x6280, else `DB_DirtyDiscError` |
| 28 | 24 × count | streamed image rows | section 11 |
| 28 + 24n | 8 | load bar size | the first argument of `LoadBar_LoadingFastfile` (140190CE0); equals the file's size on every file measured |
| 36 + 24n | 8 | load bar end | `LoadBar_LoadingFastfile(size, end - size)`; larger than the file for map zones (mp_alien_town.ff: by 38,885,717 bytes, close to but not the sum of its first-level streamed image sizes, 39,355,114; meaning *unverified*) |
| 44 + 24n | | the compressed zone | |

The previous research branch (`iw6-fastfile-retail-probes`) had this layout right (28-byte fixed part, 24-byte rows,
payload at 44 + 24n); its names for the two sizes ("byte_count_a/b") are now the load bar's.

## 2. Unsigned files

`DB_InflateInit(magic != "IWffu100")` (140349820) passes the zone to `DB_AuthLoad_InflateInit` (140349030), which
for an unsigned file sets up zlib (`db_inflateInit_`, "1.1.4", 0x58-byte stream, 0x20000 bytes of `db_zipMemory`)
or passthrough. The compressed zone is one zlib stream starting right after the prefix.

**An unsigned file read from disk is refused:** `DB_InflateInit` only calls the inflater when the file is signed or
memory-backed (`DBFile.handle == NULL`); an unsigned file with a handle is `DB_DirtyDiscError` (the PS4 server has
the same rule). The unsigned zones in the PC dump (patch_*.ff, code_pre_gfx.ff, the single-player maps such as
black_ice.ff; 22 of the first 86 files probed) can therefore only be loaded by this exe from memory; whether the
single-player Store exe differs is *unverified*.

The `.ffd` files of the dump (673, all named `dev_<zone>.ffd`) are unsigned fastfiles of the same format (measured:
dev_black_ice_outro_tr.ffd is one raw file named after its zone); the MP Store exe has no `.ffd` string, so what
loads them is *unverified*.

The compressor is fixed for the process by the first zone: a later zone with the other one is
`Sys_Error("Mixed compression types are not supported")` (14034A000; the emulator test reproduces it).

## 3. Signed files

The compressed zone is a chain of 0x2000-byte blocks, checked by `sub_1403489E0` (the servers'
`DBX_AuthLoad_ProcessHeader`, `_ProcessMasterBlock` and `_ProcessDataBlock` in one function) as
`DB_AuthLoad_Inflate` (140348D30) gathers them. Only whole blocks are processed: bytes after the last whole block
are never read.

1. **Header block** (`DB_AuthHeader`, 0x1FD0 bytes used):

   | Offset | Size | Field |
   |---|---|---|
   | 0x000 | 8 | magic `IWffs100` |
   | 0x008 | 4 | reserved |
   | 0x00C | 32 | SHA-256 of the subheader (0x12C..0x1FD0) |
   | 0x02C | 256 | RSA signature of that hash |
   | 0x12C | 32 | zone name, NUL-padded; byte 0x14B must be 0 |
   | 0x14C | 4 | reserved |
   | 0x150 | 32 × 244 | SHA-256 of each master block |

   It is accepted when the magic matches, the name is terminated, the subheader hashes to 0x00C, the signature
   verifies (`DBX_AuthLoad_ValidateSignature` 140348C10 → `_Try` 140348C60: libtomcrypt `rsa_verify_hash_ex`
   with LTC_PKCS_1_PSS, SHA-256, salt length 8, the 2048-bit key `s_publicKey` at 140992AA0, e = 65537, in a
   48000-byte stack arena), and the name equals the zone being loaded (`I_strncpyz` of `DBFile.name`, 32 bytes
   compared). The header is copied into `g_authLoad` (14430AB80).
2. **Groups**: then a master block (256 SHA-256 hashes; its own hash must equal
   `masterBlockHashes[group - 1]`), followed by up to 256 data blocks, each hashing to its entry. After the 256th
   data block the next block is the next group's master block.
3. **Data blocks** are the zlib stream (one stream across all of them), inflated from `g_authLoad`'s own z_stream.

A failed check makes the inflater return -6, and `DB_ReadXFile` (140349B80) turns any result above 1 into
`Sys_Error("Disc read error '%s'")`. `DB_LoadXFile` hands the header's 256-byte signature back to its caller through
its third argument (`sub_140348960`, zeros for an unsigned zone); what the caller does with it is *unverified*.

The prior branch had the 8 KiB envelope, the master blocks and the SHA-256 checks right, but described the envelope
as "SHA-256 master blocks" only: the header's RSA-PSS signature, the name check and the 244-group limit
(244 × 256 × 8 KiB ≈ 488 MiB of compressed data per file) are new here.

## 4. Reading

`DB_InitLoadXFile` (1403498A0) starts reading at offset 0 in 0x40000-byte stages into two alternating buffers
(`g_fileBuf`, 1443A4980), with `ReadFileEx` and an alertable `SleepEx` (`DB_ReadXFileStage` 140349C30,
`DB_WaitXFileStage` 140349A50, `DB_FileReadCompletion` 140349710), or by `memcpy` from `DBFile.memoryBuffer` when
the handle is NULL. An empty file is "Fastfile for zone '%s' is empty." `DB_ReadXFile` inflates into the
destination, waiting for the next stage whenever output is still wanted. A broken `mp_playlists` download is
deleted before any of these errors. `DB_LoadData` is 0xD0 bytes in the Store build (0xB0 in the servers).

## 5. The zone

The decompressed stream starts with the XFile header (`DB_ReadXFile(&xfile, 0x48)`):

| Offset | Field |
|---|---|
| 0x00 | size: the stream's length after this header (measured: header + size = decompressed length on every file read) |
| 0x08 | externalSize (0 measured; not used by the loader) |
| 0x10 | blockSize[7] |

The game never compares `size` with what it reads; the loaders read what they ask for.

**Blocks** (`XFILE_BLOCK_*`) and their memory (`DB_AllocXZoneMemory` 140369260 → `DB_AllocXZoneMemoryInternal`
1403692F0, `g_block_mem_type` 140992D98, `g_memoryTypeInfo` 140992DB8):

| Block | Name | Memory type | Notes |
|---|---|---|---|
| 0 | temp | 3 | reused: each pop out of it rewinds it (section 6) |
| 1 | physical | 1 | |
| 2 | runtime | 3 | never read from the file: zero-filled |
| 3 | virtual | 0 | most data |
| 4 | large | 0 | |
| 5 | callback | 3 | the Store build adds a bump allocator over it (`sub_140369230`) |
| 6 | script | 2 | script file sources and bytecode |

The types are allocated in the order 1, 0, 3, 2; each type is one `PMem_AllocFromSource_NoDebug` of its blocks'
sizes, each rounded up to 0x1000 (every type's alignment), blocks in index order.

Then `DB_LoadXFile` reads the XAssetList (0x28 bytes) straight into `g_varXAssetList` (144310BF8), not into a
block: script string count (int, +0), strings pointer (+8), asset count (int, +0x10), assets pointer (+0x18),
XGlobals pointer (+0x20). Everything after it is read by the generated loaders through `Load_Stream`.

## 6. The stream

The stream position is per block (`g_streamPosArray` 145F06618, the current one in `g_streamPos` 145F06610,
`g_streamPosIndex` 145F06650), set to each block's start by `DB_InitStreams` (1403746E0).

- `Load_Stream(atStreamStart, ptr, size)` (1403749E0): when atStreamStart and size are non-zero, `size` bytes of
  the stream go to `ptr` (which the generated code has always just set to the current position) and the position
  advances. **In the runtime block nothing is read**: the bytes are zero-filled. A call with atStreamStart false
  reads nothing: it is how a loader visits a field that was already read as part of its parent.
- `DB_PushStreamPos(block)` (1403748D0) saves (current block, position of the new block) on a 64-entry stack
  (`g_streamPosStack` 145F06660) and switches; `DB_PopStreamPos` (140374850) switches back. **Popping out of the
  temp block rewinds it to where the push found it**: temp memory is reused, which is why asset headers (loaded into
  temp by `Load_<Type>Ptr`) must be copied out by `DB_Add` (section 8).
- **Alignment** is in the generated code, before the pointer is set: `(pos + a - 1) & ~(a - 1)` with a = 4 for
  structures and arrays of them (headers, the XAsset array, XGlobals), 8 for pointer arrays (the script string
  table, `Load_XStringPtr`), 2 for u16 arrays (path node lists), none for byte arrays and strings. The alignment
  of each field is the per-type work's to record (the Store disassembly of each `Load_*`).
- `Load_XStringCustom` (140374AC0): an inline string is read one byte at a time up to and including its NUL; the
  position moves by its length + 1 (no alignment, no length limit).

## 7. Pointers in the stream

A pointer field holds, as read from the file:

| Value | Meaning |
|---|---|
| 0 | null |
| 0xFDFDFDFFFFFFFFFF (-1) | the data follows in the stream: the loader aligns, stores the current position in the field and loads it |
| 0xFDFDFDFFFFFFFFFE (-2) | as -1, and first reserves an alias slot (`DB_InsertPointer` 140374750: 8 bytes, 8-aligned, in the virtual block) that receives the asset's final pointer after `DB_Add` |
| anything else | a packed offset to something loaded earlier in this zone: block = bits 32-35, offset = low 32 bits - 1 (`DB_GetPackedOffsetStreamPos` 1401905A0; bits 36-63 are ignored) |

A packed offset becomes either a pointer into that block (`DB_ConvertOffsetToPointer` 1403749A0: structures,
strings) or **the pointer stored at that place** (`DB_ConvertOffsetToAlias` 140374960: an asset reference, where
the offset points at an alias slot). Which one is the generated code's choice per field. Nothing checks an
offset against its block's size.

XString fields use -1 or an offset (`Load_XString`'s rule, inline in every loader). XGlobals: any non-zero pointer
means inline (`Load_XGlobalsPtr` 14035DF80 has no -1 test).

## 8. Assets

The XAsset array: if the list's pointer is non-null, `AllocLoad_XAsset` (14034A060) aligns the virtual block to 4,
the array (16 bytes per asset: type, pad, header pointer) is read in one `Load_Stream`, and `Load_XAsset`
(14035D5F0) is called for each with atStreamStart false. `Load_XAssetHeader` (14035D630) dispatches on the type to
`Load_<Type>Ptr`, all of which follow one rule (e.g. `Load_PathDataPtr` 1403551C0):

1. push the temp block;
2. null: nothing; an offset: `DB_ConvertOffsetToAlias` (an asset loaded earlier in this zone);
3. -1 / -2: align 4, the header goes in temp (`Load_<Type>(true)`, which pushes the virtual block for what the
   header points to), with -2 reserving an alias slot first;
4. `Load_<Type>Asset` (`DB_LinkXAssetEntry1` 14036D830 with the type): the header is copied into the type's pool,
   or an existing asset of that name is kept, and the pointer becomes the pool entry; a -2 slot receives it;
5. pop (the temp block rewinds for the next asset).

An asset's name is at a per-type offset in its header (the name getters at 1409924A0).

## 9. Script strings

`Load_ScriptStringList` (140355E20): in the virtual block, the table (count × 8 bytes, 8-aligned), then for each
entry: null, an offset (`DB_ConvertOffsetToPointer`), or -1: an inline string (`Load_TempStringCustom` 140374A30),
immediately turned into a script string by `SL_GetString(str, 4)`; the table entry becomes the handle (zero
extended). Script string fields in assets hold an index into this table (`Load_ScriptStringCustom` 14037AF90:
`*field = (u32)table[(int)*field]`). Measured on mp_alien_town_path.ff: 225 entries, entry 0 null, 224 strings.

## 10. The type table

From `Load_XAssetHeader` (14035D630, the same order and variables as the PS4 PDB's), the type name table
(`g_assetNames` 1409920A0), `DB_GetXAssetTypeSize` (1403488D0, table 1409928A0) and the name getters (1409924A0).
The Store (PC client) build has no handler and no load case for 0x1C, 0x28-0x2B (so a zone with them loads nothing
for them); 0x3F is the count, 0x40 the asset list.

| Type | Name | Header | Name at | Load_*Ptr | var |
|---|---|---|---|---|---|
| 0x00 | physpreset | 0x58 | 0 | Load_PhysPresetPtr 1403555F0 | 144426758 |
| 0x01 | phys_collmap | 0x58 | 0 | Load_PhysCollmapPtr 140355410 | 144424FB0 |
| 0x02 | xanim | 0x88 | 0 | Load_XAnimPartsPtr 14035D3D0 | 144425998 |
| 0x03 | xmodelsurfs | 0x38 | 0 | Load_XModelSurfsPtr 14035E860 | 1444251B8 |
| 0x04 | xmodel | 0x258 | 0 | Load_XModelPtr 14035E530 | 1444267F8 |
| 0x05 | material | 0x3A8 | 0 | Load_MaterialHandle 140353700 | 144425D20 |
| 0x06 | computeshader | 0x20 | 0 | Load_ComputeShaderPtr 14034BF40 | 144425C30 |
| 0x07 | vertexshader | 0x28 | 0 | Load_MaterialVertexShaderPtr 140354550 | 144425C20 |
| 0x08 | hullshader | 0x20 | 0 | Load_MaterialHullShaderPtr 1403539E0 | 144425C40 |
| 0x09 | domainshader | 0x20 | 0 | Load_MaterialDomainShaderPtr 140353610 | 144425C50 |
| 0x0A | pixelshader | 0x28 | 0 | Load_MaterialPixelShaderPtr 140353E60 | 144425C60 |
| 0x0B | vertexdecl | 0x838 | 0 | Load_MaterialVertexDeclarationPtr 1403543A0 | 144425C78 |
| 0x0C | techset | 0xCF0 | 0 | Load_MaterialTechniqueSetPtr 140354130 | 144425D10 |
| 0x0D | image | 0x68 | 0x60 | Load_GfxImagePtr 14034F380 | 144425868 |
| 0x0E | sound | 0x18 | 0 | Load_snd_alias_list_ptr 140361F10 | 144426678 |
| 0x0F | sndcurve | 0x98 | 8 | Load_SndCurvePtr 140356DD0 | 144426628 |
| 0x10 | lpfcurve | 0x98 | 8 | Load_LpfCurvePtr 140352960 | 144426630 |
| 0x11 | reverbsendcurve | 0x98 | 8 | Load_ReverbCurvePtr 1403559A0 | 144426638 |
| 0x12 | loaded_sound | 0x38 | 0 | Load_LoadedSoundPtr 140352600 | 1444265E8 |
| 0x13 | col_map_mp | 0x280 | 0 | Load_clipMap_ptr 14035FB10 | 144425650 |
| 0x14 | com_map | 0x28 | 0 | Load_ComWorldPtr 14034BD90 | 1444267D0 |
| 0x15 | glass_map | 0x10 | 0 | Load_GlassWorldPtr 1403520B0 | 144425B90 |
| 0x16 | aipaths | 0x88 | 0 | Load_PathDataPtr 1403551C0 | 144425B80 |
| 0x17 | vehicle_track | 0x18 | 0 | Load_VehicleTrackPtr 140359430 | 1444257E8 |
| 0x18 | map_ents | 0x100 | 0 | Load_MapEntsPtr 140352D50 | 144425630 |
| 0x19 | fx_map | 0xB0 | 0 | Load_FxWorldPtr 14034E9B0 | 144426DC0 |
| 0x1A | gfx_map | 0xA30 | 0 | Load_GfxWorldPtr 140351D10 | 144426920 |
| 0x1B | lightdef | 0x30 | 0 | Load_GfxLightDefPtr 14034F560 | 144426D50 |
| 0x1C | ui_map | none | | none | |
| 0x1D | font | 0x28 | 0 | Load_FontHandle 14034CF50 | 1444252D0 |
| 0x1E | menufile | 0x18 | 0 | Load_MenuListPtr 140354980 | 144426EE8 |
| 0x1F | menu | 0xC8 | 8 | Load_menuDef_ptr 140361710 | 144426ED8 |
| 0x20 | animclass | 0x58 | 0 | Load_AnimationClassPtr 14034A880 | 1444254D0 |
| 0x21 | localize | 0x10 | 8 | Load_LocalizeEntryPtr 1403527E0 | 144425A48 |
| 0x22 | attachment | 0x118 | 0 | Load_WeaponAttachmentPtr 14035A240 | 144426350 |
| 0x23 | weapon | 0xA98 | 0 | Load_WeaponCompleteDefPtr 14035ACA0 | 144426BF8 |
| 0x24 | snddriverglobals | 0x18 | 0 | Load_SndDriverGlobalsPtr 140356F90 | 1444264D8 |
| 0x25 | fx | 0x40 | 0 | Load_FxEffectDefHandle 14034D120 | 1444260F8 |
| 0x26 | impactfx | 0x10 | 0 | Load_FxImpactTablePtr 14034E4E0 | 144425AE0 |
| 0x27 | surfacefx | 0x10 | 0 | Load_SurfaceFxTablePtr 1403582C0 | 144425AF8 |
| 0x28-0x2B | aitype, mptype, character, xmodelalias | none | | none | |
| 0x2C | rawfile | 0x18 | 0 | Load_RawFilePtr 140355820 | 144425A68 |
| 0x2D | scriptfile | 0x28 | 0 | Load_ScriptFilePtr 140355D30 | 144425A78 |
| 0x2E | stringtable | 0x18 | 0 | Load_StringTablePtr 140357B00 | 144425B50 |
| 0x2F | leaderboarddef | 0x28 | 0 | Load_LeaderboardDefPtr 140352470 | 144426468 |
| 0x30 | structureddatadef | 0x18 | 0 | Load_StructuredDataDefSetPtr 140357ED0 | 144425F18 |
| 0x31 | tracer | 0x78 | 0 | Load_TracerDefPtr 1403585D0 | 144425F98 |
| 0x32 | vehicle | 0x610 | 0 | Load_VehicleDefPtr 140359150 | 144425460 |
| 0x33 | addon_map_ents | 0x68 | 0 | Load_AddonMapEntsPtr 14034A370 | 144425640 |
| 0x34 | netconststrings | 0x20 | 0 | Load_NetConstStringsPtr 140354B60 | 144426530 |
| 0x35 | reverbpreset | 0x48 | 0 | Load_ReverbPresetPtr 140355B20 | 1444252F8 |
| 0x36 | luafile | 0x18 | 0 | Load_LuaFilePtr 140352B20 | 1444253B8 |
| 0x37 | scriptable | 0x40 | 0 | Load_ScriptableDefPtr 140356330 | 144424B70 |
| 0x38 | colorization | 0x30 | 0x28 | Load_ColorizationPtr 14034B8C0 | 1444253D8 |
| 0x39 | colorizationset | 0x68 | 0 | Load_ColorizationSetPtr 14034BAD0 | 1444253E8 |
| 0x3A | tonemapping | 0x70 | 0x68 | Load_ToneMappingPtr 140358440 | 1444253F8 |
| 0x3B | equipsndtable | 0x58 | 0 | Load_EquipmentSoundTablePtr 14034CB70 | 144425268 |
| 0x3C | vectorfield | 0x50 | 0 | Load_VectorFieldPtr 140358870 | 1444257A0 |
| 0x3D | dopplerpreset | 0x20 | 0 | Load_DopplerPresetPtr 14034C150 | 144426560 |
| 0x3E | particlesimanimation | 0x60 | 0 | Load_FxParticleSimAnimationPtr 14034E760 | 144426090 |

The Store build's GfxImage is 0x68 bytes (0x38 in the servers), with the name at +0x60.

**XGlobals** (`Load_XGlobalsPtr` 14035DF80, `Load_XGfxGlobals` 14035DBB0): an 8-byte XGlobals and, when its
pointer is non-null, a 0x68-byte XGfxGlobals with arrays at +8 (count +0, 8 bytes each), +0x10 (count +4, 4
bytes), +0x38, +0x40, +0x48 (counts +0x28, +0x2C, +0x30, 4 bytes each), all 4-aligned; the pointer arrays at
+0x18, +0x20, +0x50, +0x58, +0x60 are in the runtime block (so they read nothing and come out null), and the
renderer creates GPU buffers for them while loading (14063ACC0, 14063ABD0, 14063AC60; names unknown). Measured on
mp_alien_town_load.ff: 128 bytes of runtime block.

## 11. Streamed images

Each row of the prefix is 24 bytes:

| Offset | Size | Field |
|---|---|---|
| 0 | 2 | localized: the pak is `<language>_imagefile<N>.pak` instead of `imagefile<N>.pak` (140548160) |
| 2 | 2 | N, the pak index (up to 0x60 open paks, 14604CFE0, 0x70 bytes each); 0 = this fastfile itself (`sub_1403497F0` returns the file being loaded) |
| 4 | 4 | padding (0 measured) |
| 8 | 8 | offset of the data in that file |
| 16 | 8 | end of the data |

`DB_LoadXFile` keeps the rows (144310C20, count 1443A4820) and resets a cursor (144310BF4). `sub_1403492E0`
hands them out in order, four per streamed image: `Load_ImageStream`'s Store body (140374E70, reached through a
function pointer at 140993968, with the image's pool index from 14036CC90) takes them for every GfxImage whose byte
+0x35 is set and stores, per picmip level, {offset, end, file} in a 0x60-byte entry per image (145FB8200 +
0x60 × index), opening the pak on first use ("imagefile%d", `FS` open mode 4 or 5 for localized); it also sets a
bit from the image's flags (+0x1F & 0x10) in 14604C200 and stores the length of the image's (width +0x40,
height +0x42) diagonal. Rows with offset and end 0 are unused levels.

Measured on mp_alien_town.ff: 8160 rows (2040 images, every image's first row used, 5438 rows in all), all in
imagefile1-63 (none localized, none in the fastfile); the 9593 bytes of a row's range in imagefile1.pak are one
zlib stream (16384 bytes inflated). What a level holds and how the game reads it: docs/assets/images.md (level 0 is the whole mip chain at the
smallest size, each higher level only its top mip).

**Image pak index** (`sub_140375350`, called at the end of `DB_LoadXFile`): for every pak opened for the zone and
not indexed yet, it reads the pak's own header: magic `IWff0100`/`IWffu100`, a version dword, 16 bytes decrypted
by 140349200 (AES-ECB through libtomcrypt with a key schedule at 140992BB0) giving the entry count, a 32-byte hash
and a 256-byte signature checked by `DBX_AuthLoad_ValidateSignature`, then count × 16 encrypted entries, whose
SHA-256 must verify against the same signature. Measured with the game's own decryption on imagefile1.pak: 1977
entries, each an increasing u64 offset into the pak and 8 more bytes (meaning *unverified*). The decrypted index is
kept per pak (+0x58 count, +0x60 entries); how it is used is *unverified* (docs/assets/images.md 4).

## 12. The reference reader and how it is checked

`tools/fastfile/iw6ff.py ZONE.ff [--exe STORE.exe]` reads the prefix, verifies the container as above (the RSA
signature when given the exe, from which it takes the key), decompresses, and walks the zone with a `Stream` class
that is the game's stream: seven block images laid out as the game lays them out, push/pop with the temp rewind,
alignment, the pointer rules, script strings, the asset pool copies (`Stream.link`). It lists the script strings
and the XAssetList (type, name). Asset bodies are walked by per-type loaders (`ASSET_LOADERS`: physpreset, aipaths,
rawfile, scriptfile so far); at the first asset without one the walk stops (the next asset starts where that one
ends), and the remaining entries are listed by type only.

The check against the game (`tests/fastfile/test_store.py`):

- `store_emu.py` maps the Store exe in Unicorn, hands it the fastfile as a memory-backed `DBFile` and calls
  `DB_LoadXFile`. Everything from the header checks through SHA-256, the RSA-PSS signature (real libtomcrypt),
  zlib, the block allocation, the stream and every loader runs as the game's code; only the allocator, `SL_GetString`,
  `DB_LinkXAssetEntry1` (copies the header into a pool region, as for a new asset), the load bar and two renderer
  callbacks are Python, plus a null D3D device and `r_loadForRenderer` off.
- The reader is given the game's block addresses, and must produce the same script strings (in `SL_GetString`
  order), asset types, linked (type, name), every byte of every block, the pool copies, the streamed image rows and
  the 256 bytes handed back.
- Real zones (`$IW6_FASTFILES`): equal on mp_alien_town_path.ff (signed, 2 assets, 224 strings, 1.4 MB of virtual
  block: byte for byte), patch_common.ff, patch_oilrocks.ff, code_pre_gfx.ff, ui_install.ff, factory_tr_ignore.ff,
  patch_flood.ff (unsigned: script files in the script block, raw files, phys presets), and up to the XAsset array
  on mp_alien_town_load.ff, techsets_mp_alien_town.ff and a 4 MB prefix of mp_alien_town.ff (2560 assets, 1985
  script strings, 8160 streamed image rows).
- Synthetic zones (every CI run with the Store exe): 40 random zones with every pointer kind (inline, null, offsets,
  -2 slots and aliases to them), both compressors, and streamed image rows; mutation checks (a pop that doesn't
  rewind temp, an unaligned insert slot, a raw file sized by len) are caught.

## 13. Findings (for records/bugs.tsv)

Not filed by this work (the brief reserves records/bugs.tsv); each is reproducible with the code above:

- **No bounds checks in the stream** (security, with the signature as the only guard): `Load_Stream` writes past a
  block when the zone asks for more than `blockSize`; packed offsets (`DB_ConvertOffsetTo*`) and their block
  index (0-15 for 7 blocks) are not checked; `DB_PushStreamPos` does not check its 64-entry stack; negative counts
  (the asset count, the script string count) are sign-extended into huge `Load_Stream` sizes or long loops;
  `Load_XStringCustom` has no length limit. A signed zone can only exploit this with Infinity Ward's key; an
  unsigned one only from memory (section 2).
- **More than 244 groups** in a signed file index past `masterBlockHashes[243]` into the rest of `g_authLoad`
  (`sub_1403489E0`): a file over ~488 MiB compressed fails or reads unrelated bytes as hashes (no retail file is
  that large in the PC dump measured; the largest map zones are ~330 MB).
- **`DB_ReadXFileStage` with a memory-backed file** compares the remaining size as a signed int: a
  `memoryBufferSize` whose low 32 bits are negative makes a ~4 GB `memcpy` (140349C30).
- **The prefix's three unused bytes and two unused dwords** are read and ignored; the version check returns quietly
  for memory-backed files.
- `Load_RawFile` (140355760) reads `compressedLen` bytes of buffer regardless of `len` (so an uncompressed raw file
  must store its size in `compressedLen`); behaviour to keep, noted for the importer.

## 14. What the per-asset-type work starts with

- Each type's `Load_<Type>` in the Store disassembly, from its `Load_<Type>Ptr` in the table above: the header
  size, which fields are XStrings, script strings, inline structures (and their alignment) or offsets, which
  pointers use `DB_ConvertOffsetToAlias` (asset references) and which block each part goes to (pushes).
- Add a loader to `tools/fastfile/iw6ff.py` (`ASSET_LOADERS[type] = asset_ptr(type, load_x)`, using `Stream`'s
  `load`, `align`, `push`/`pop`, `xstring_ptr`, `offset_to_pointer`/`offset_to_alias`), then run
  `tests/fastfile/test_store.py` with `$IW6_FASTFILES` on a zone that has the type: a zone whose every asset has a
  loader is compared in full, byte for byte, against the game.
- Order that unlocks real zones: material and techset/shaders (mp_alien_town_load.ff is 65 materials, a techset
  and a raw file; techsets_mp_alien_town.ff is 841 techsets), then image (streamed rows: section 11), xmodel and
  xmodelsurfs, then gfx_map/col_map_mp/com_map for map zones. Loading materials and images for real in the
  emulator needs the renderer's dvars registered (14A2E2550 among others) or the device calls faked; the emulator's
  `assets=False` mode stops before the first asset meanwhile.
