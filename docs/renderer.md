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

Not mapped yet: the per-frame path, which binds state, uploads constants and issues draws and dispatches (rb_backend,
the state cache, the draw wrappers). It is the next step, and the biggest.

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

## Queries

- **Occlusion:** 32 × 4 OCCLUSION queries, plus one more. The per-frame update brackets a 16×16 sprite with
  Begin/End and reads the sample count.
- **Fences:** EVENT queries, as above.
- **Vulkan mapping:** occlusion queries become VkQueryPool OCCLUSION.

## Bugs found here

B0032–B0045 in records/bugs.tsv. The ones that matter most:

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

Next is the frame-latency waitable object: wait for it once per presented frame, then read input. That needs the
frame loop mapped (Com_Frame, the front end and back end hand-off), which is also where any remaining
render-thread latency is.

