# Verification

How a function earns `compiles` and `matches` in `records/functions.tsv`. The method is BO1's
(black-ops-1-decomp `docs/verification.md`); this page records what changes for an x64 MSVC 2012 game.

## compiles

`tools/build_recon.py` builds everything under `src/` with clang `--target=x86_64-pc-windows-msvc`
(Win64 calling convention, MSVC x64 C++ mangling) into `build/recon.dll`, exporting every function under
its decorated name. Tests look functions up by the original decorated name, so a wrong prototype shows
up as a missing export.

That only works where an original decorated name is known, i.e. from a reference build's MAP or PDB.
For functions known only from the stripped retail exe there is no decorated name; they are tested by
address (the match records give the address and the prototype).

## Hybrid link (x64)

Anything the reconstruction uses but does not define resolves to the original binary: functions become
`jmp qword ptr [rip+0]` followed by the 8-byte original address (x64 has no `push imm64`), data becomes an
absolute symbol. The DLL is linked at 0x180000000, clear of the exe at 0x140000000.

## matches (differential)

Same contract as BO1: the original and the reconstruction run in one Unicorn address space on identical
inputs; return value, every pointer buffer and every global write must match exactly; inputs on which the
original faults are skipped; too few usable inputs means untestable, never passed.

The harness (`tests/differential/harness.py`) is ported to x64. What changed from BO1:

- `UC_MODE_64`, a GS-based TEB (`gs:[0x30]` self pointer, `gs:[0x60]` PEB) for code that reads it.
- Win64 calling convention: the first four arguments in rcx, rdx, r8, r9, or xmm0 to xmm3 for floating
  point (by position, not by count of each kind); 32 bytes of shadow space above the return address;
  rsp 16-byte aligned before the call; return in rax or xmm0.
- No x87 state to set up: x64 MSVC does all floating point in SSE. The CPU starts with MXCSR 0x1F80.
  The x87-specific workarounds from BO1 (unrounded ST0 returns, `X87_MATH`) don't apply.
- An Arxan-protected build runs from its **unpacked** image (tools/unpack); the harness checks `unpacked_sha256`.
- VC11's x64 CRT math (`sin`, `pow`, ...) is called as ordinary functions in the original; the hybrid link
  routes the reconstruction's calls to the same original routines.

### State, the OS, and calls the test can't see

Most game functions read and write global state and call into the rest of the engine. The harness supports that
without giving up the bit-exact contract:

- **Setup.** An input can carry a `setup(writer)` that writes state into the original's globals (key bindings,
  key catchers, `cmd_args` with an argv in scratch memory, dvar pointers to scratch `dvar_t`s) before each of the
  two calls. Setup writes are undone afterwards like the call's own writes, so inputs never leak into each other.
- **Thread-local storage.** `gs:[0x58]` leads to a copy of the original's TLS template. Reconstructed code reaches
  the same block: `tools/build_recon.py` links the original's `_tls_index` and lays out the DLL's own `.tls` so
  each original TLS variable (`dvar_modifiedFlags`) has its original offset. TLS writes are compared too.
- **Imports.** Every import address table slot of the original points at a stub returning 0 (deterministic
  `timeGetTime`, `EnterCriticalSection` and so on). `Machine.on_import` gives a stub behaviour when a test needs
  one.
- **rdtsc** returns a counter that restarts with every call (`Sys_Milliseconds` seeds `sys_counterBase` from it).
- **Observed calls.** A case can list original functions whose calls are recorded with their arguments and
  compared. That covers callees whose effect is invisible in this build (`CL_ExecBinding` is empty in the
  server); a reconstructed callee is watched at both copies.
- **Fakes.** A case can replace an original function with Python for both runs (`Dvar_GetInt` for dvars that
  were never registered, `Com_ErrorEntering`), so the paths behind them are exercised.
- **Addresses that differ by construction** are normalised before comparing: a pointer the reconstruction stores
  to one of its own functions counts as the original function's address, a pointer into either image's
  `.rdata` counts as the string it points at, and a returned `const char *` is compared as a string (`ret:
  "cstr"`).

Each new case is mutation-checked: a deliberate change in the reconstruction (a constant, a comparison, a
dropped call) must make it fail. A function whose tests survive a mutation gets better inputs, not a pass.

### Testing against the Store build

The final target has no symbols. `tools/symbols.py` gives it a symbol table from `records/names.tsv` (hand
identifications with method, evidence and confidence) and the matcher's pairs; `tools/build_recon.py --build
iw6mp64_MSStore_ship` links the reconstruction against it (unidentified symbols link to a trap, imports go through
the exe's import table, an import outranks a matcher pair), and `tests/differential/run.py --build
iw6mp64_MSStore_ship` tests every function that has a Store address. Only functions records/ claims for the Store
build must pass; a failure elsewhere is reported but doesn't fail the run (shared code that differs in the Store
build, or that needs inputs and identifications nobody has written yet). The CRT is imported there, so the import
stubs implement floor, ceil and sqrt exactly.

Other harness rules that came up with the Store build: every call starts with all registers zeroed; global writes
are compared as net changes (whole qwords, so stored pointers can be normalised); a fake or an observation on a
function applies to its reconstructed copy too; struct padding is left out of compared structs.

## Open: differential suite red against the PS4 server

`tests/differential/run.py --check-records` against `iw6_ds_ps4` fails: of 509 functions tested, 228 pass and
121 are known failures annotated in `records/functions.tsv`, which leaves **160 with neither a pass nor a note**.
CI's check job has been red since the reconstruction stopped compiling (a duplicated D3D11 context enum, fixed in
234184c); this is the next step it fails. None looks like a decompilation error, but each needs one of:

- an explicit test case in `tests/differential/` that sets up the state the function needs, so it can reach `matches`; or
- a `records/functions.tsv` note keeping it below `matches` and saying why (the known-failure mechanism).

### Original faults on every auto-generated input (153)

- 129 are fastfile loaders (`Load_*`, from the asset-decoding work). They read the current zone's stream state,
  so with no zone loaded the original itself faults. They need a test fixture that sets up a `DB_LoadXFile`
  stream (block pointers, stream position) before each call.
- 24 are renderer state and draw functions (`gfx_d3d/r_state.cpp`, `r_shade.cpp`, `rb_shade.cpp`). They probably
  fault for the same reason as the annotated renderer failures: the server's Direct3D back end is stubbed. That
  needs confirming per function. If so, they get the same kind of note, and are tested against the Store build.

Grouped by source file:

- `bgame/bg_tracer_load_db.cpp` (2): `Load_TracerDef 1400BB130`, `Load_TracerDefPtr 1400BB1D0`
- `bgame/bg_weapons_load_db.cpp` (13): `Load_ADSOverlay 1400AFD10`, `Load_AttProjectile 1400B0A60`, `Load_AttRumbles 1400B0BE0`, `Load_VehicleDef 1400BB520`, `Load_VehicleDefPtr 1400BBD00`, `Load_VehiclePhysDef 1400BBDD0`, `Load_WeaponAttachment 1400BC4F0`, `Load_WeaponAttachmentPtr 1400BCD00`, `Load_WeaponAttachmentPtrArray 1400BCDD0`, `Load_WeaponCompleteDef 1400BCEF0`, `Load_WeaponCompleteDefPtr 1400BD580`, `Load_WeaponDef 1400BD650`, `Load_XAnimPartsPtrArray 1400BFDB0`
- `database/db_misc_load_db.cpp` (28): `Load_AddonMapEnts 1400AFD90`, `Load_AddonMapEntsPtr 1400AFF50`, `Load_ComputeShader 1400B1B40`, `Load_ComputeShaderPtr 1400B1C00`, `Load_EquipSoundSetMoveTypesArray 1400B2150`, `Load_EquipmentChanceRattleTypesArray 1400B22A0`, `Load_EquipmentSoundSetArray 1400B2410`, `Load_EquipmentSoundTable 1400B24C0`, `Load_EquipmentSoundTablePtr 1400B27A0`, `Load_GfxComputeShaderLoadDef 1400B4980`, `Load_LeaderboardDef 1400B58D0`, `Load_LeaderboardDefPtr 1400B59A0`, `Load_LuaFile 1400B5F00`, `Load_LuaFilePtr 1400B5FD0`, `Load_ReverbPreset 1400B87C0`, `Load_ReverbPresetPtr 1400B8850`, `Load_SndDriverGlobals 1400B9AF0`, `Load_SndDriverGlobalsPtr 1400B9BC0`, `Load_StructuredDataDefArray 1400BA790`, `Load_StructuredDataDefSet 1400BA920`, `Load_StructuredDataDefSetPtr 1400BA9F0`, `Load_VectorField 1400BB350`, `Load_VectorFieldPtr 1400BB450`, `Load_VehicleTrack 1400BBED0`, `Load_VehicleTrackPtr 1400BBFC0`, `Load_VehicleTrackSegment 1400BC140`, `Load_VehicleTrackSegmentArray 1400BC290`, `Load_VehicleTrackSegment_ptrArray 1400BC430`
- `effectscore/fx_load_db.cpp` (13): `Load_FxEffectDef 1400B2DD0`, `Load_FxEffectDefHandle 1400B2EB0`, `Load_FxElemDefArray 1400B3120`, `Load_FxElemDefVisuals 1400B33F0`, `Load_FxElemExtendedDefPtr 1400B34C0`, `Load_FxElemVisuals 1400B36F0`, `Load_FxElemVisualsArray 1400B37A0`, `Load_FxFlareDef 1400B3930`, `Load_FxParticleSimAnimation 1400B42F0`, `Load_FxParticleSimAnimationPtr 1400B4480`, `Load_FxTrailDef 1400B4550`, `Load_GfxLightDef 1400B4CE0`, `Load_GfxLightDefPtr 1400B4DD0`
- `effectscore/fx_world_load_db.cpp` (11): `Load_FxEffectDefHandleArray 1400B2F80`, `Load_FxGlassSystem 1400B3C20`, `Load_FxImpactTable 1400B40D0`, `Load_FxImpactTablePtr 1400B4220`, `Load_FxWorld 1400B4610`, `Load_FxWorldPtr 1400B46B0`, `Load_G_GlassData 1400B4780`, `Load_GlassWorld 1400B5450`, `Load_GlassWorldPtr 1400B5520`, `Load_SurfaceFxTable 1400BAD20`, `Load_SurfaceFxTablePtr 1400BAE50`
- `gfx_d3d/r_font_load_db.cpp` (2): `Load_Font 1400B2BD0`, `Load_FontHandle 1400B2D00`
- `gfx_d3d/r_postfx_load_db.cpp` (6): `Load_Colorization 1400B1530`, `Load_ColorizationPtr 1400B15C0`, `Load_ColorizationSet 1400B1690`, `Load_ColorizationSetPtr 1400B17B0`, `Load_ToneMapping 1400BAFD0`, `Load_ToneMappingPtr 1400BB060`
- `gfx_d3d/r_shade.cpp` (6): `R_SetHullAndDomainShaders 1402F9A70`, `R_SetIndexData 1402F9B00`, `R_SetPixelShader 1402FA910`, `R_SetVertexData 1402FAB70`, `R_SetVertexShader 1402FAC10`, `R_UpdateVertexDecl 1402FB090`
- `gfx_d3d/r_state.cpp` (15): `R_ChangeDepthRange 1402FC080`, `R_ClearAllStreamSources 1402FC320`, `R_ClearScreenInternal 1402FC490`, `R_DrawCall 1402FCB50`, `R_DrawIndexedPrimitive 1402FCCB0`, `R_DrawInstancedIndexedPrimitive 1402FCD00`, `R_FlushTextureState 1402FCF10`, `R_HW_DisableScissor2D 1402FD9A0`, `R_HW_SetScissor 1402FDA80`, `R_SetCompleteState 1402FDB40`, `R_SetMeshStream 1402FDDC0`, `R_SetPrimType 1402FDF20`, `R_SetViewportAndScissorSeparate 1402FE4E0`, `R_ShutdownCmdBufState 1402FE5E0`, `R_UnbindImage 1402FE730`
- `gfx_d3d/r_state_utils.cpp` (1): `R_InitCmdBufState 1402FED50`
- `gfx_d3d/rb_shade.cpp` (3): `RB_EndTessSurface 14030EB00`, `RB_SetTessTechnique 14030EBB0`, `RB_TessOverflow 14030EC20`
- `qcommon/cm_load_db.cpp` (6): `Load_ClientTriggers 1400B0D70`, `Load_ClipInfo 1400B1030`, `Load_MapEnts 1400B60A0`, `Load_MapTriggers 1400B63A0`, `Load_cbrush_t 1400C1E90`, `Load_cbrushside_t 1400C1F60`
- `ui/ui_menu_load_db.cpp` (27): `Load_ConditionalScriptPtr 1400B1CD0`, `Load_ExpressionString 1400B2940`, `Load_ExpressionSupportingData 1400B29C0`, `Load_ExpressionSupportingDataPtr 1400B2AC0`, `Load_ItemKeyHandler 1400B56D0`, `Load_MenuEventHandlerSet 1400B7600`, `Load_MenuEventHandlerSetPtr 1400B7670`, `Load_MenuList 1400B76D0`, `Load_MenuListPtr 1400B77A0`, `Load_SetLocalVarData 1400B98A0`, `Load_SetLocalVarDataPtr 1400B9930`, `Load_Statement 1400BA1C0`, `Load_StatementPtr 1400BA240`, `Load_UIFunctionList 1400BB2A0`, `Load_XString 1400C1270`, `Load_XStringArray 1400C12E0`, `Load_editFieldDef_ptr 1400C2CC0`, `Load_itemDefData_t 1400C2DF0`, `Load_itemDef_t 1400C2FA0`, `Load_listBoxDef_t 1400C3640`, `Load_menuData_t 1400C36F0`, `Load_menuDef_ptr 1400C3AB0`, `Load_menuDef_t 1400C3CA0`, `Load_multiDef_ptr 1400C3D90`, `Load_newsTickerDef_ptr 1400C3F40`, `Load_textScrollDef_ptr 1400C4950`, `Load_windowDef_t 1400C49B0`
- `universal/com_stringtable_load_db.cpp` (4): `Load_LocalizeEntry 1400B5BE0`, `Load_LocalizeEntryPtr 1400B5CD0`, `Load_StringTable 1400BA510`, `Load_StringTablePtr 1400BA6C0`
- `xanim/xanim_load_db.cpp` (16): `Load_AnimationAimSet 1400B00B0`, `Load_AnimationClass 1400B02C0`, `Load_AnimationClassPtr 1400B0600`, `Load_AnimationStateArray 1400B0780`, `Load_AnimationStateMachine 1400B0950`, `Load_XAnimDeltaPart 1400BF2C0`, `Load_XAnimDeltaPartQuatDataFrames 1400BF4E0`, `Load_XAnimDeltaPartQuatDataFrames2 1400BF440`, `Load_XAnimDynamicFrames 1400BF580`, `Load_XAnimDynamicIndicesDeltaQuat 1400BF6C0`, `Load_XAnimDynamicIndicesDeltaQuat2 1400BF640`, `Load_XAnimDynamicIndicesTrans 1400BF740`, `Load_XAnimIndices 1400BF7C0`, `Load_XAnimPartTrans 1400BF8D0`, `Load_XAnimParts 1400BF970`, `Load_XAnimPartsPtr 1400BFCE0`

### No inputs can be generated (7)

These take a struct by value (`GfxCmdBufContext`) or a state pointer the auto-case generator can't build;
they need explicit cases:

- `R_SetupPass` 1402FAC50 (gfx_d3d/r_shade.cpp)
- `R_SetupPassPerObjectArgs` 1402FAD90 (gfx_d3d/r_shade.cpp)
- `R_SetupPassPerPrimArgs` 1402FAE90 (gfx_d3d/r_shade.cpp)
- `R_SetRenderTarget` 1402FE010 (gfx_d3d/r_state.cpp)
- `R_SetRenderTargetSuite` 1402FE110 (gfx_d3d/r_state.cpp)
- `R_SetState` 1402FE290 (gfx_d3d/r_state.cpp)
- `R_DrawTessTechnique` 14030EC60 (gfx_d3d/rb_shade.cpp)

To regenerate this list: `python3 tests/differential/run.py --check-records`, then every `FAIL`/`UNTESTABLE` line
without a matching `known` line.

## Byte matching

Would need the VC11 (VS2012 Update 4) x64 compiler on a Windows runner. The retail builds are optimized
(and probably LTCG, to be measured as on BO1), so byte matching is not the goal for them; behavioural
equivalence is.

## First run (PS4 server reference)

- Sanity: original functions called directly give the expected results (`AngleNormalize360(-90) = 270`,
  `Vec3Normalize([3,4,0])` returns 5 and writes `[0.6, 0.8, 0]`, `vectoyaw([0,1,0]) = 90`, `I_stricmp`).
- `AngleNormalize360` and `AngleDelta` (universal/com_math.cpp) reconstructed and passing on ~290 generated inputs
  each (NaN, infinities, signed zeros), with `floorf` resolved to the original CRT through the hybrid link.
- Mutation checks: a changed constant fails on a concrete input; a wrong return type no longer drops the
  function silently, the build stops with "prototype differs from the original's decorated name".
