# The renderer's Direct3D 11 boundary

This page describes what the Microsoft Store build's renderer asks of Direct3D 11 and DXGI: every call, what it
passes, and the game structures around it. A Vulkan backend for the enhanced build has to provide all of this. Each
section names the reconstructed source, all of it tested against the Store build in the differential harness, where
a fake device logs every COM call with its arguments (tests/differential/com.py).

Reconstructed so far (Store build, all `matches`):

| Area | Source | Functions |
|---|---|---|
| Device, swap chain, present, shutdown | src/gfx_d3d/r_init.cpp | 23 |
| Buffers (vertex, index, constant, dynamic, Map/Unmap) | src/gfx_d3d/r_buffers.cpp | 29 |
| Textures, views, render targets | src/gfx_d3d/r_image.cpp, r_image_load_common.cpp, r_rendertarget.cpp, r_compute.cpp | 42 |
| State objects, shaders, input layouts | src/gfx_d3d/r_state.cpp, r_shader.cpp | 26 |
| Queries and GPU fences | src/gfx_d3d/rb_query.cpp | 6 |
| Per-frame state cache, draws, render targets (see below) | src/gfx_d3d/r_state.cpp, r_setstate_d3d.cpp, r_state_utils.cpp | 35 |
| Material passes: shaders, input layouts, constant buffers and uploads, dynamic vertices and indices | src/gfx_d3d/r_shade.cpp | 13 |
| The 2D/immediate tessellation buffer and its draw | src/gfx_d3d/rb_shade.cpp | 5 |

The per-frame path binds state, uploads constants and issues draws and dispatches. Its state cache is mapped (below);
the rest (rb_backend's draw loop, worker command lists, the scene passes) is not yet.

## The device

- `dx` (DxGlobals, 0x14A37D620, gfx_d3d/r_dx.h) holds the device, the immediate context, the DXGI factory, adapter
  and output, the state tables, the display modes and the fences. It is the Xbox One server PDB's layout, with 8
  more bytes after +0x58 and 0x18 more after the fence pool.
- **Creation:**
  - R_ChooseAdapter (14062EEF0) creates the factory and enumerates adapters to find the monitor.
  - R_CreateDevice (14062F420) calls `D3D11CreateDevice` on that adapter with feature levels 11_0 down to 9_1.
    Neither result is checked.
  - The swap chain has two R8G8B8A8_UNORM buffers, DISCARD swap effect, windowed, with ALLOW_MODE_SWITCH.
  - `MakeWindowAssociation(NO_WINDOW_CHANGES)` is called, but before the window exists the first time (B0039).
- **Lost device:** R_RecoverLostDevice (140631A80) recreates the swap chain and every resource. **ResizeBuffers and
  ResizeTarget are never called**: a mode change recreates everything.
- **Present:** RB_SwapBuffers (140675C50) calls `Present(r_vsync clamped to 0..4, 0)`, then inserts a swap fence.
  Fullscreen switches go through the window procedure's `SetFullscreenState`.
- **Threading:**
  - 2 × 65 deferred contexts are created for worker threads, plus 2 compute contexts.
  - Command lists are built with FinishCommandList and replayed with ExecuteCommandList.
  - The immediate context is guarded by a mutex with a lock count and owner thread (inline
    R_LockImmediateContext; about 60 call sites).
  - In Vulkan: secondary command buffers recorded per worker and executed from the primary, with the lock
    becoming queue submission order.
- **Fences:**
  - 32 EVENT queries are used as a fence pool, plus a flush fence.
  - Waiting is a `GetData(NULL, 0, 0)` spin loop, some with `Sleep(0)`.
  - Becomes VkFence and timeline semaphores.
- **Middleware:** NVIDIA APEX, MultiRes, PSM and HairWorks are loaded at start-up (1401AAB70, 1401AAD20) and bind
  to the D3D11 device. A Vulkan backend drops them.

## Buffers

Every buffer goes through `ID3D11Device::CreateBuffer`:

| Buffer | Usage | Bind | CPU | Misc |
|---|---|---|---|---|
| Static vertex, index (Load_VertexBuffer, Load_IndexBuffer, from fastfiles) | IMMUTABLE | VB or IB, plus SRV | none | ALLOW_RAW_VIEWS |
| Dynamic vertex, 1 MB pool | DYNAMIC | VB | WRITE | none |
| Dynamic index, 2 MB pool | DYNAMIC | IB | WRITE | none |
| Constant buffers (size rounded up to 16; 0x2000 and 0x800 for static models) | DYNAMIC | CB | WRITE | none |
| Compute buffers | DEFAULT | VB + SRV + UAV | none | DRAWINDIRECT_ARGS + ALLOW_RAW_VIEWS |

- Map uses subresource 0 with WRITE_DISCARD (pools, particle clouds) or the caller's map type.
- In Vulkan, a discard map becomes a per-frame ring of host-visible memory, because D3D11's "renaming" has to be
  done by hand.
- Raw views are R32_TYPELESS BUFFEREX.

## Textures, views and render targets

- **GfxImage** (0x68 bytes in the Store build, 0x38 in the servers) carries:
  - the texture and two shader views;
  - format, map type, flags;
  - size, mip count;
  - four per-picmip stream levels, used for texture streaming (CopySubresourceRegion, UpdateSubresource).
- **Creation:** CreateTexture1D, 2D, 3D, with cubes and 2D arrays as 2D textures.
  - Usage is DEFAULT, DYNAMIC or STAGING.
  - Bind flags are SRV, plus RT, DS or UAV for render targets.
  - Misc flags are GENERATE_MIPS and TEXTURECUBE.
  - Textures are often created typeless, and the views pick the typed or sRGB format.
- **Depth:** R32G8X24_TYPELESS textures with D32_FLOAT_S8X24_UINT depth-stencil views and R32_FLOAT_X8X24 shader
  views.
- **Reversed depth:** the depth test table is ALWAYS, GREATER, EQUAL, GREATER_EQUAL, so the game uses reversed depth.
- **Render targets** (GfxRenderTarget, 0x50 bytes): a resolved image and surfaces, plus a multisampled pair.
  - The back buffer's view is made sRGB.
  - The scene target is R11G11B10_FLOAT.
  - MSAA uses D3D11_STANDARD_MULTISAMPLE_PATTERN, with counts from CheckMultisampleQualityLevels.
- **Vulkan mapping:**
  - Typeless formats with typed views become VkImage with MUTABLE_FORMAT, plus image views.
  - Cubes and arrays become layered images.
  - Render targets need explicit layout transitions that D3D11 does implicitly.

## Pipeline state

- **Fixed state objects, created up front from bit tables:**
  - **Blend:** per target factors and ops from tables. Independent blend only when targets differ.
  - **Depth-stencil:** 64 state bits. Depth and stencil functions come from tables.
  - **Rasterizer:** 32 states. Solid or wireframe; cull none, back or front. Depth bias from the
    r_polygonOffset/sm_polygonOffset dvars. Depth clip and scissor on.
  - **Samplers:** 256 states built from bits: filter (anisotropic 0x55), address modes, comparison GREATER,
    MaxLOD FLT_MAX, mip bias from `dx.mipBias`.
- **Shaders:**
  - Vertex, hull, domain, pixel and compute shaders are created from DXBC bytecode in the fastfiles' shader
    assets, with no class linkage. They are only created when `r_loadForRenderer` is on.
  - Vulkan needs SPIR-V. The shaders have to be translated (DXBC to SPIR-V) at load time and cached.
- **Input layouts:**
  - Built for all 249 vertex declarations from the stream routing tables (s_streamDestInfo semantics, per-vertex
    data), against each vertex shader's bytecode.
  - In Vulkan these become vertex input state in the pipeline.
- **Pipelines:** Vulkan needs whole pipeline objects where D3D11 combines state at draw time. The fixed tables help:
  a pipeline key is (shaders, blend index, depth index, rasterizer index, input layout, render target formats),
  built and cached on first use.

## The per-frame path: the state cache

Every draw goes through one `GfxCmdBufState` (gfx_d3d/r_state.h): the renderer's copy of what is bound to one
context. The back end's own state is the global `gfxCmdBufState` on the immediate context; R_DrawCall builds one on
the stack for each callback, on whichever context the caller passes (a worker's deferred context or the immediate
one). Every setter compares with the cache and calls Direct3D only on a change. Its partner `GfxCmdBufSourceState`
holds what the shaders read: the code constants, matrices and the frame's inputs.

Reconstructed (Store build, all `matches`):

| Area | Source | Functions |
|---|---|---|
| Gamma writes, default device state | src/gfx_d3d/r_setstate_d3d.cpp | 2 |
| State bits, textures, samplers, streams, draws, viewport, scissor, render targets, clears, R_DrawCall | src/gfx_d3d/r_state.cpp (`per-frame`) | 34 |
| Material passes, constant uploads, dynamic vertices | src/gfx_d3d/r_shade.cpp | 13 |
| Tessellation buffer (2D and immediate geometry) | src/gfx_d3d/rb_shade.cpp | 5 |
| Setting up a state for a context | src/gfx_d3d/r_state_utils.cpp | 1 |

Tests: tests/differential/test_r_state_cmdbuf.py, test_r_shade.py and test_rb_shade.py, with the context model in
tests/differential/d3dctx.py.

- **State bits** (R_SetState): a pass's three 32-bit `loadBits` select prebuilt state objects.
  - Bits 3-5 of word 0 and 4-5 of word 1 choose the rasterizer state (`dx.rasterizerStates`, 32).
  - Word 1 and bits 8-15 of word 0 choose the depth-stencil state, per depth-stencil mode, from the zone's table;
    bits 8-15 are also the stencil reference.
  - Word 2 chooses the blend state from the zone's table, with the cache's blend factor and sample mask.
  - Bit 6 of word 0 is gamma writes. D3D11 has no such render state: R_HW_SetGammaWriteEnable rebinds the target
    through its sRGB view. Float formats (R16G16B16A16_FLOAT, R11G11B10_FLOAT, R16_FLOAT) have none, so it is
    ignored for them, and with a suite (two targets) bound it is always off.
  - The depth hack modes force depth writes by moving to the next three entries of the per-mode table.
- **Samplers and textures**: R_Set{Vertex,Domain,Pixel}{Texture,Sampler} only write the cache and widen a dirty
  range [first, last] per stage. R_FlushTextureState binds each dirty range in one call (slots in between that did
  not change are sent again). The xb3 server only resets the texture ranges; the Store build binds them. Hull shaders
  get no samplers or textures from here. R_UnbindImage unbinds an image from every stage right away, before it
  becomes a render target.
- **Streams and draws**: three vertex streams, bound together as the range of streams that changed. Index counts
  come from the topology: lines ×2, triangles and 3-point patches ×3, 16-point patches ×16, anything else 0.
  DrawIndexed and DrawIndexedInstanced are the only draw calls here; the index format is always R16_UINT.
- **Viewport and scissor**: every rasterizer state has scissoring on, so "no scissor" is an 8192 × 8192 rectangle.
  The viewport's depth range is the cache's: scene 0..0.984375, view model 0.984375..1, force near 1..1, force far
  0..0, full 0..1. With reversed depth (MinDepth is the far end) the gun is drawn in front of the world by giving it
  the top 1.6% of the depth range.
- **Render targets**: R_SetRenderTarget binds one target (its multisampled surfaces when the source state is
  multisampled and the target has them); R_SetRenderTargetSuite binds a suite's two targets (three suites in the
  Store build, two in the servers) with the depth view of the last one that has one. Both unbind the target images
  from the texture slots first and mark the viewport dirty.
- **Material passes** (r_shade.cpp): R_SetupPass picks the technique's pass, sets the pixel, hull and domain
  shaders, the state bits (depth writes forced in the depth hack modes, and for prepass-tagged passes when there is
  no prepass) and the material's own constant buffers (slot 3 of each stage). R_UpdateVertexDecl binds the input
  layout for the prim state's vertex type and the vertex shader. Constants come in three frequencies, each in its own
  constant buffer slot: per primitive (0), per object (1) and stable (2), bound to VS and PS, and to HS and DS for
  tessellated passes. Their values are built on the CPU in shadow arrays (R_SetPassShader*Arguments, not yet
  reconstructed); when the buffer or any value changed, the buffer is mapped with WRITE_DISCARD and the shadow
  copied in. The Store build adds a hull shader resource (slot 1) for tessellated passes with custom flag 0x2000.
- **Dynamic indices** (R_SetIndexData): a ring buffer of 16-bit indices, mapped NO_OVERWRITE while it fills and
  DISCARD when it starts over, always on the immediate context (its only caller draws with the back end's own
  state, so that is correct).
- **The tessellation buffer** (rb_shade.cpp, `tess`): 2D and other immediate geometry (menus, HUD, text, debug
  lines) is collected on the CPU as 0x20-byte vertices (position, colour, texture coordinate, packed normal) and
  16-bit indices, up to 5450 vertices and 0x100000 indices, for one material technique at a time.
  RB_SetTessTechnique switches technique (drawing what was collected first); RB_TessOverflow draws a full buffer and
  goes on. RB_EndTessSurface sets the viewport if it is dirty (R_GetViewport, then R_UpdateViewport refreshes the
  render-target-size and clip-to-texture constants), appends the indices to the dynamic index ring and the vertices
  to the dynamic vertex ring (R_SetVertexData, NO_OVERWRITE while filling, DISCARD at the start) and draws every pass
  of the technique with DrawIndexed. The Store build adds a variant with its own scissor rectangle. The render
  command table (RB_RenderCommandTable, 1408AC040) dispatches the front end's 2D commands (stretch pics, quads,
  text, lines, clears, viewport and scissor) to the functions that fill this buffer.
- **Clears** (R_ClearScreenInternal): the bound views come back from OMGetRenderTargets (and are released after).
- **R_DrawCall**: a fresh state for the output's context (the immediate context is locked meanwhile), the callback,
  then everything the callback left bound is unbound. The constant caches start as all ones, so the first upload
  always happens.
- **R_InitCmdBufState**: clears the cache and puts the context in a matching state: default states, triangle lists,
  no shaders, every sampler `dx.samplerStates[1]`, static-model constant buffers in vertex slots 6 and 7. The cached
  pixel shader, input layout and streams start at values no real one has, so their first set always reaches the
  context. It caches a full-screen scissor and an empty viewport without setting them (B0085).

**In Vulkan:**

- The cache maps onto a pipeline key plus dynamic state. Rasterizer, depth-stencil and blend indices, the shaders,
  the input layout (from the vertex declaration) and the render target formats select a pipeline; stencil
  reference, blend constants, viewport and scissor are dynamic state set per command buffer. Because the indices
  come from fixed tables, pipelines can be built ahead for the combinations materials use.
- The tess buffer maps directly onto a per-frame host-visible vertex and index ring; a flush becomes one indexed
  draw per pass with the ring offsets. The rings must be per frame in flight, which D3D11's DISCARD did implicitly.
- Constant uploads by WRITE_DISCARD become writes into a per-frame ring of host-visible memory with a dynamic
  uniform-buffer offset per draw; the three frequencies map naturally onto three dynamic offsets.
- The texture and sampler dirty ranges become descriptor writes: one descriptor set per stage, updated for the dirty
  range and bound before the draw (or push descriptors).
- Gamma writes become a choice between two image views of the target, so the framebuffer (or dynamic rendering
  attachment) changes; the float-format exception carries over.
- Each R_DrawCall maps to a secondary command buffer (or a section of one) with its own state; the unbind-everything
  at the end has no cost in Vulkan and can go.
- B0085 matters there: viewport and scissor must be set explicitly in every command buffer.

## The per-frame path: what remains

Done so far: the state cache, material pass setup with its constant uploads, and the tess flush (55 functions,
all `matches`). About 350–400 functions remain before nothing in the renderer calls D3D11 directly. In order:

1. **The 2D command handlers and the rest of tess.** The render command table at 1408AC040 has 25 handlers that
   line up one-for-one with the Xbox server's command enum, which names them. Together with the remaining tess
   primitives (quads, rotated pics, text) they complete the main-menu path, the first Vulkan milestone.
2. **Shader argument setup.** R_SetPass{Prim,Object,Stable}ShaderArguments and the code-matrix derivation: pure CPU,
   but every pass needs them. The Store has three folded copies of one Xbox function (kept as `sub_`).
3. **The rest of rb_backend (14066E000–140690000).** About 280 functions: text drawing, the draw-surface iterators
   and the scene passes.
4. **The other direct D3D11 callers.** About 78 functions: post-effects and resolves, compute dispatch, skinning
   and static model buffer uploads, the scene draw loops in 140613xxx–140622xxx, the occlusion sprite.
5. **Worker command lists.** FinishCommandList/ExecuteCommandList, in the 1401CC–1402xx area; in Vulkan these
   become secondary command buffers recorded on the workers.

After that, separately: the DXBC to SPIR-V converter for the game's shaders, and the Vulkan backend itself.

## Queries

- **Occlusion:** 32 × 4 OCCLUSION queries, plus one more. The per-frame update brackets a 16×16 sprite with
  Begin/End and reads the sample count.
- **Fences:** EVENT queries, as above.
- **Vulkan mapping:** occlusion queries become VkQueryPool OCCLUSION.

## Bugs found here

B0032–B0045 and B0085 in records/bugs.tsv. The ones that matter most:

- Load_Texture's 4096-entry stack array has no bounds check (security).
- R_EnumDisplayModes overflows `displayModes[256]` on systems with more modes.
- Display modes with a zero refresh-rate denominator divide by zero.
- Creation results are never checked, so a failed create crashes later.
- GPU waits spin with no timeout.

## Enhanced build: presentation (P0003)

The enhanced build replaces the original's blit-model swap chain (`DXGI_SWAP_EFFECT_DISCARD`) with a flip-model
one (enhanced/gfx_d3d/r_init.cpp):

- **Flip model:** `FLIP_DISCARD` with two buffers, from a DXGI 1.1 factory. Windows can then pass the game's
  buffers straight to the display (independent flip) in fullscreen and in a borderless window covering the monitor.
- **Tearing:** allowed when the system supports it, so `r_vsync 0` can run uncapped or with VRR in a window too.
- **Queue:** at most one frame (`SetMaximumFrameLatency(1)`).
- **Render targets:** flip model unbinds the back buffer at every present, so the render targets that were bound are
  bound again right after it. That keeps the renderer's state cache, which skips rebinding a target it believes is
  bound, correct.
- **Fallback:** a system that can't create a flip-model swap chain gets the original one.

The methods and GUIDs it adds (IDXGIFactory5::CheckFeatureSupport, IDXGIDevice1::SetMaximumFrameLatency) aren't
used by the original exe, so they can't be checked against it the way the reconstruction's slots are. Each call
falls back to the original behaviour when it fails. The tests check the calls and their arguments in the emulator;
whether Windows actually uses independent flip has to be confirmed on a real machine, for example with PresentMon.

The frame-latency waitable object (P0004) is in docs/frame.md, section 5: R_SyncGpu waits on it once per present
before the frame's input is read.
