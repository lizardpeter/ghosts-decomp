# Roadmap: enhanced build and beyond

Wanted features, all in the enhanced build (docs/variants.md) unless marked otherwise. Each becomes one or more
`records/patches.tsv` entries when implemented. "Needs" lists what has to be decompiled and verified first:
changes go on verified faithful code.

| # | Feature | Kind | Needs | Notes |
|---|---|---|---|---|
| 1 | Uncapped FPS, fully decoupled from game logic and physics | modernize | client frame loop, pmove, cgame prediction, client snapshot code | see below |
| 2 | Raw input without high-DPI / high-polling issues | modernize | win32 input, `CL_MouseMove`-equivalent, usercmd building | see below |
| 3 | v-sync fully off, one frame in flight | modernize | renderer backend / present path | D3D11: flip model with `DXGI_PRESENT_ALLOW_TEARING`, max frame latency 1. Vulkan: `IMMEDIATE`, one frame in flight |
| 4 | Late latch | modernize | view setup (refdef), renderer submission | sample input and rebuild the view matrices as late as possible, just before the frame's draw calls are submitted; GPU-side late latch later (Vulkan) |
| 5 | NVIDIA Reflex, AMD Anti-Lag 2, Intel XeLL | modernize | frame loop markers, present path | Reflex markers (sim start/end, render submit, present) around the decomped loop; on Vulkan via `VK_NV_low_latency2` |
| 6 | DLSS, FSR, XeSS (upscaling; frame generation optional) | modernize | renderer: depth, motion vectors, camera jitter, HUD after upscale | Ghosts has no TAA-style motion vectors: per-object velocity has to be added (previous-frame transforms) and the projection jittered; UI composited after upscaling. Frame generation adds latency; pair it with Reflex. Streamline covers DLSS/XeSS/FSR behind one API |
| 7 | HDR output | modernize | renderer post-processing/tonemap, swapchain, UI compositing | HDR10 (PQ) or scRGB swapchain; replace the SDR tonemap/gamma at the end with an HDR tonemap; paper-white and peak brightness settings; UI drawn at paper-white |
| 8 | FOV and FOV scale like MW2019 | feature | cg_fov registration, view setup, weapon view model FOV | see below |
| 9 | MW2019 sensitivity options | feature | input → view angles, ADS zoom sensitivity | see below |
| 10 | Windows low-latency setup | modernize | platform layer (win32) | MMCSS "Games" for the main/render threads, high-resolution waitable timers instead of `Sleep`, no busy-wait on the wrong core, WASAPI low-latency audio, GameInput/raw HID for pads |
| 11 | JPEG XL screenshots | feature | screenshot command | libjxl; lossless by default; with HDR on, keep the HDR image (JXL stores PQ/HLG) instead of a tonemapped copy |
| 12 | Discord integration | feature | platform/online layer | rich presence (map, mode, score, lobby) and join-from-Discord through the Discord Social SDK; iw6-mod has a reference integration (GPL, ideas only) |
| 13 | Vulkan 1.4 + current Rust | port (separate repo) | full decomp of the subsystems being ported | long-term; uses this repo as a submodule, subsystem by subsystem, C++ as the test oracle (docs/variants.md) |

## 1. Frame rate fully decoupled

IW-engine movement depends on frame rate: pmove runs with the frame's whole-millisecond duration, so jump height
and some movement change at particular FPS values (the old 125/250/333 behaviour). Simply uncapping FPS keeps that.
Approach:
- Run simulation (pmove, prediction, physics) at a fixed rate in fixed-size steps, independent of rendering.
- Render at any rate and interpolate the view and entities between the last two simulation states.
- Keep mouse look out of the fixed step: apply the view angle change per rendered frame (see late latch), so aiming
  stays as responsive as the frame rate.
- Multiplayer: the server is authoritative over usercmds; the client must produce usercmds the server simulates
  identically. Verify against the faithful build that movement no longer depends on frame rate and that prediction
  errors don't increase.

## 2. Raw input

- Raw Input with `RIDEV_NOLEGACY`, read with `GetRawInputBuffer` on the input path rather than one `WM_INPUT` per
  message, so 4000/8000 Hz mice don't flood the message queue.
- Integer counts accumulated losslessly; convert to angles once per frame in double precision. Keep the sub-count
  remainder; never clamp or round deltas. No OS acceleration, no in-game filtering or smoothing unless asked for.
- Ignore Windows pointer speed and "enhance pointer precision" entirely (raw counts).

## 8. FOV like MW2019

MW2019's FOV slider is the **horizontal FOV at 16:9**; Ghosts' `cg_fov` is the horizontal FOV at 4:3
(Hor+ on wider screens: the vertical FOV is kept and the image widens), confirmed in the Store build's
CG_CalcFov (docs/view.md). Ghosts also scales hip-fire mouse sensitivity with cg_fov (B0023). The enhanced build
switches the setting to MW2019 units (horizontal at 16:9) and converts internally; the menu can also show the
actual horizontal FOV for the current aspect ratio. Conversion: vertical = 2·atan(tan(h/2)·9/16), then cg_fov = 2·atan(tan(v/2)·4/3).

| MW2019 FOV | vertical | Ghosts cg_fov |
|---:|---:|---:|
| 80 | 50.53 | 64.37 |
| 90 | 58.72 | 73.74 |
| 100 | 67.67 | 83.58 |
| 105 | 72.49 | 88.69 |
| 110 | 77.55 | 93.93 |
| 120 | 88.51 | 104.82 |

Ghosts' default 65 is 80.69 at 16:9, almost exactly MW2019's default 80. Plan: an FOV setting in MW2019's units
(60–120), a separate weapon (view model) FOV like MW2019's Narrow/Default/Wide, an "ADS FOV: affected/independent"
choice, and correct Hor+ scaling on ultrawide.

## 9. Sensitivity like MW2019

MW2019 turns 0.0066° per mouse count per unit of sensitivity. Ghosts uses `m_yaw` 0.022° per count per unit (the
id/IW default; to confirm in the client, which the server build lacks). At 3200 DPI:

| MW2019 sens | degrees per count | counts per 360 | cm per 360 | same in Ghosts units |
|---:|---:|---:|---:|---:|
| 1.0 | 0.0066 | 54,545 | 43.30 | 0.300 |
| **1.5** (default for us) | 0.0099 | 36,364 | **28.86** | 0.450 |
| 2.0 | 0.0132 | 27,273 | 21.65 | 0.600 |

cm/360 = 360 / (sens × 0.0066) / DPI × 2.54. The setting should be stored in MW2019 units, with the cm/360 at the
user's DPI shown next to it (DPI entered once in settings).

MW2019's aim-down-sights options to reproduce: ADS sensitivity multiplier, separate multipliers for low and high
zoom, "Monitor Distance Coefficient" (default 1.33) and "Affected FOV". With a monitor distance coefficient c, the
ADS sensitivity ratio is atan(c·tan(adsFOV/2)) / atan(c·tan(hipFOV/2)), so a coefficient matches the mouse
movement for the same on-screen distance at that fraction of the screen. Which FOV (horizontal or vertical) MW2019
feeds into this and how "Affected FOV" changes it still needs checking against MW2019 itself before it is final.

## Candidates (suggested, not yet agreed)

- **Security hardening:** fuzz the network, snapshot/gamestate and fastfile parsers against the reconstructed code
  natively; AddressSanitizer test builds; server-side validation of everything a client sends (usercmds, menu
  responses, LUI notifies). The known fixes are in docs/security.md.
- **Performance:** pipeline/shader precompilation against stutter; job-system scaling to all cores; audit
  animation, particle, sway and physics-prop behaviour at uncapped FPS; built-in frame-time and latency overlay.
- **Visuals:** native internal resolution by default (upscaling opt-in); HUD scaling and safe area for 4K and
  ultrawide; toggles for motion blur, film grain, depth of field and chromatic effects; optional sharpening; higher
  shadow, draw-distance and LOD limits.
- **Input:** MW2019 controller options (deadzone shapes, response curves, per-zoom sensitivity); DualSense gyro and
  native prompts; full rebinding with profiles.
- **Online:** our own backend replacing Demonware (accounts, stats and progression, matchmaking, server browser,
  private servers with rcon); Linux dedicated server; higher tick/snapshot rates, interpolation setting, net graph.
- **Platform and quality:** launch without the Xbox app (no GDK dependency); crash minidumps symbolised against our
  build; faster fastfile loading; native modding (scripts, asset overrides); colour-blind filters and subtitle
  options; HRTF/spatial audio and loudness normalisation; native Linux once on Vulkan + SDL; Extinction and Squads
  offline with bots.
