# Per-frame logic outside movement (Store build)

What the Microsoft Store build (`iw6mp64_MSStore_ship`) does once per rendered frame besides movement, and which of
it changes with the frame rate. Frame timing, usercmds, Pmove and prediction are the other half (docs/fps.md); this
page takes the client's time base, the view effects, the viewmodel, animation, effects, sound, UI, physics and the
renderer's per-frame work, and ends with what the enhanced build should change to run at any frame rate up to about
1000 fps without the game behaving differently.

Sources and conventions:

- The Store build's disassembly, with names from Black Ops' server PDB (black-ops-1-decomp, `CoDMPServer`, which kept
  the cgame), the PS4 server PDB (`iw6_ds_ps4`: bgame, the camera shake, physics, effects) and the matcher. Every name
  this page uses for a Store address is in `records/names.tsv` with its evidence.
- **(R)** marks functions reconstructed in `src/` that pass their differential tests against the Store build (and the
  PS4 server where it has them).
- Numbers in tables marked *measured* come from running the original Store functions in the test emulator (the
  harness of tests/differential) frame by frame; the method is in section 4.
- *Unverified* marks what was read from the code but not run.

## Summary

- **The client's clocks are whole milliseconds.** `cls.realtime` advances by Com_Frame's integer `msec` (at least 1),
  `cl.serverTime` is `cls.realtime` plus an integer delta that `CL_SetCGameTime` nudges by 1 or 2 ms per snapshot, and
  `cg.time` is `cl.serverTime`. Everything the cgame draws is a function of these integers: entity interpolation
  (`cg.frameInterpolation`, steps of 1/50 at 20 snapshots a second), effects, animation, shakes and fades.
- **The original's frame limiter only produces whole-millisecond frames** (1000/k fps: 333, 250, 200, 166 ...), so
  with `com_maxfps` in charge the steps are even. At frame times that are not whole milliseconds (vsync at 144 or 240
  Hz, VRR, GPU-bound frames) the per-frame step alternates, for example 4, 4, 4, 4, 4, 5 ms at 240 Hz, and everything
  that moves on screen (other players, effects, and the camera's own translation through prediction) moves in uneven
  steps: at 240 Hz every sixth frame moves 20% too far, at 400 fps frames alternate 20% short and 20% long.
- **Two per-frame integrations change their result with the frame rate**, both in shared bgame code driven by
  `cg.frametime`:
  - **`BG_KickAngles` (R, 1402905D0), the view kick from firing.** It integrates in steps of at most 5 ms, so it gives
    one answer at any frame time that is a multiple of 5 ms and others elsewhere. At 1000 fps the kick is about 7%
    smaller and recovers about 5% sooner than at 200 fps or less (*measured*). **The kick is added to the usercmd's
    angles** (`CL_FinishMove`), so this changes what the server sees as the player's aim, not only the picture.
  - **`BG_CalculateWeaponMovement_Recoil` (R, 140297CF0), the viewmodel's recoil.** Same 5 ms rule: at 1000 fps the
    gun's kick is about 12% smaller than at 200 fps, and it settles between 120 and 170 ms depending on the frame
    pattern (*measured*). Visible, not sent to the server.
- **Per-frame constants (frame-rate dependent filters):** the radar jamming level moves 1/15 of the way per frame
  (CG_DrawActiveFrame), and the doppler pitch is smoothed per sound update (`snd_dopplerSmoothing`). Both are
  cosmetic.
- **First-order filters with the frame time** (`DiffTrack`, `DiffTrackAngle`, the viewmodel's base position) are Euler
  steps: their time constant is `-ln(1 - rate·dt)/dt` instead of `1/rate`. That is within 1% of the exact value at
  200 fps and above, so they matter only at low frame rates.
- **Frame-rate independent:** the camera shake (R), the damage kick, step smoothing, prediction error decay, the
  landing dip, the kill cam blend, view bob (driven by Pmove's `bobCycle`), the FOV and zoom blends, the radar sweep,
  the HUD fades, effects, animation, the UI clock and the hybrid scope switch.
- **Recommendation, in order of what a player would notice:** a fractional client time for interpolation and the
  view (section 4.1), the view kick and the viewmodel recoil on a fixed 5 ms grid (4.2, 4.3), then the cosmetic
  filters (4.4 to 4.6). The protocol, `cg.time`'s integer meaning and the server's view of the player stay as they are.

## 1. The time base of the client frame

### Where each time comes from

| Time | Where it is set | How | Precision |
|---|---|---|---|
| `com_frameTime`, `msec` | Com_Frame's body (140460400) | `Sys_Milliseconds()` after the event loop; the com_maxfps wait is added to it (docs/frame.md step 6), clamped, then smoothed over three frames with the remainder carried, scaled by timescale, at least 1 | integer ms |
| `cls.realtime`, `cls.frametime` | sub_140316290 (R) | `cls.realtime += msec`, `cls.frametime = msec`, `cls.frametime_base = msec / 1000` (float) | integer ms |
| `cl.serverTime` (143E99EF0) | CL_SetCGameTime (140306C40, from CL_Frame) | `max(previous, cls.realtime + serverTimeDelta)`; on a new snapshot the delta is reset (more than 500 ms off), averaged toward the target (more than 100 ms off) or moved by 1 ms toward it, or by -2 ms after a frame that ran past the newest snapshot, while timescale is 1. The target keeps the client one snapshot interval plus 16 ms behind the newest snapshot. | integer ms |
| `cg.time`, `cg.oldTime`, `cg.frametime` (cg+0x71890, +0x71894, +0x7188C) | CG_DrawActiveFrame (1402E7860), called by CL_CGameRendering (14031B150) with `cl.serverTime` | `oldTime = time; time = serverTime; frametime = time - oldTime`, or 0 with `oldTime = time` when time went back (CG_ProcessSnapshots also pulls `time` up to the current snapshot) | integer ms |
| `cg.frameInterpolation` (cg+0x71888) | CG_SetFrameInterpolation (R, 1402B5B70), every frame from CG_ProcessSnapshots (1402DB4C0) and again from CG_SetNextSnap (1402DBD40) | `(cg.time - snap.serverTime) / (nextSnap.serverTime - snap.serverTime)`, 0 when negative or when both snapshots have the same time | float, from integer ms |
| `weaponState_t::frametime` | CG_AddViewWeapon (1402F38B0) | `cg.frametime * 0.001` | float, from integer ms |
| the UI's time | 14050EF20 (from 14031B3D0, the 2D) | `cls.realtime`; also an FPS figure, `4000 / (sum of the last four frame deltas)` | integer ms |

The usercmd is stamped with the same `cl.serverTime` (`CL_FinishMove`, docs/input.md), so the cgame's frame and the
command it sends have one clock.

### How often two frames get the same time

- `cls.realtime` never repeats. Com_Frame passes at least 1 ms, and with `com_maxfps 0` its limiter still waits for
  `minMsec = 1`: the original never runs a client frame shorter than 1 ms (1000 fps is its ceiling).
- `cl.serverTime`, and so `cg.time`, can repeat. When a snapshot makes `CL_SetCGameTime` lower the delta by 1 (or 2
  after extrapolating) in a frame where `cls.realtime` rose by only 1, the maximum keeps the old time and
  `cg.frametime` is 0 for that frame. At 2 ms frames such a frame advances by 1 ms instead of 2. This happens at most
  once per snapshot (20 a second), whenever the delta is being corrected; the opposite correction makes a step 1 ms
  longer.
- At frame periods that are not whole milliseconds, the integer differences alternate. Without the three-frame
  smoothing a 240 Hz frame (4.17 ms) advances 4, 4, 4, 4, 4, 5 ms, a 400 fps frame 2, 3, 2, 3 ms, a 144 Hz frame
  7, 7, 7, 7, 7, 6 ms. The smoothing in Com_Frame redistributes the remainders but its output is still integer, so the
  pattern keeps a ±1 ms error per frame (*unverified* in detail: the smoothing is the other half's subject).
- Under the original's own limiter the frame time is `1000 / com_maxfps` rounded down to whole milliseconds and the
  steps are even: 100 → 10 ms, 300 → 3 ms (333 fps), 240 → 4 ms (250 fps), 144 → 6 ms (166 fps).

### What interpolates with it

- **Other entities** (players, vehicles, projectiles in interpolated mode): CG_CalcEntityLerpPositions (1402B21B0)
  sends them to CG_InterpolateEntityPosition (1402B3980), which blends the two snapshots' positions by
  `cg.frameInterpolation`. Entities with a trajectory are evaluated at `cg.time` (140265F00). Both move in whole
  milliseconds: the fraction steps by 1/50 per millisecond at 20 snapshots a second.
- **The player's own view origin** is the predicted player state's origin (prediction runs Pmove up to the newest
  command's `serverTime`, docs/fps.md), plus two time-based corrections in CG_CalcViewValues (1402EDDD0): the step
  smoothing `z = origin.z - (1 - min(1, (cg.time - stepViewStart) / (cg_viewZSmoothingTime · 1000))) · stepViewChange`
  and the prediction error decay `origin += max(0, (cg_errordecay - (cg.time - predictedErrorTime)) / cg_errordecay)
  · predictedError`. Nothing interpolates the view origin between milliseconds.
- **The viewmodel** follows the view; its movement (section 2) takes `cg.frametime * 0.001` and the predicted state.

### Stutter from millisecond quantization

Rotation is not quantized: the mouse is applied to the view angles every frame (docs/input.md). Translation is. When
the frame period is not a whole number of milliseconds, a moving target, an effect, and the camera itself while
strafing advance by uneven amounts per frame, by up to one millisecond of motion more or less than the frame
deserves: about 0.2 units per frame at a running speed of about 190 units a second. At 240 Hz every sixth frame
moves 20% too far (a 40 Hz beat), at 400 fps the frames alternate 20% short and 20% long. It is invisible under the
original's limiter (whole-millisecond frames) and visible as micro-stutter on high-refresh and VRR displays, most
in smooth panning. The 1 ms corrections of `CL_SetCGameTime` add a short or long step up to 20 times a second at any
frame rate.

### Where a fractional time would go

Implemented in the enhanced build for items 1, 2 (as a slewed render time rather than a fractional `cl.serverTime`)
and 4, and for the own view (5, as a step forward instead of an interpolation): docs/cgame-frame.md 4.9.

1. `cls.realtime`: keep the integer (it is the protocol's and the game logic's clock) and add a fractional part from
   the high-resolution counter (`Sys_Milliseconds` is integer; the enhanced build now derives it from QPC).
2. `CL_SetCGameTime`: a fractional `cl.serverTime`, with the delta corrections slewed over a snapshot interval instead
   of 1 ms steps. The integer part still stamps usercmds.
3. `CG_DrawActiveFrame`: `cg.time` stays integer; a new `cg.timeFrac` (0 to 1 ms) beside it.
4. `CG_SetFrameInterpolation`: `(cg.time + cg.timeFrac - snap.serverTime) / delta`. This alone smooths every
   interpolated entity.
5. The view origin: interpolate the predicted origin by `cg.timeFrac` between the last two predicted states (or
   extrapolate by the predicted velocity), at the end of prediction (docs/fps.md owns prediction).
6. Optional, for completeness: the effects system's update time and the trajectory evaluation (`BG_EvaluateTrajectory`
   at `cg.time + timeFrac`), and XAnim's float `dtime`.

## 2. Per-frame effects in the cgame view

CG_DrawActiveFrame (1402E7860) runs, in order: the time update, CG_ProcessSnapshots, the GPU sync and `CL_Input`
(docs/frame.md), prediction (1402D2480), the view (CG_CalcViewValues, 1402EDDD0) and the viewmodel (CG_AddViewWeapon,
1402F38B0), the view kick, and the client state it hands back to the client (1402AB060: the FOV sensitivity scale
and the kick angles for the next usercmd).

| Effect | Function (Store VA) | Input | Formula | Frame rate | Severity |
|---|---|---|---|---|---|
| View kick from firing | BG_KickAngles (R, 1402905D0), from CG_DrawActiveFrame (1402E817B) while `ps.otherFlags & 0x4000` (set by the server for a playing client) | `cg.frametime` (int ms) | per step of `min(5, rest)` ms: `vel += ±centerSpeed · dt` toward center, `angle += vel · dt` (only 6% of it when moving back toward center), stop on crossing zero, cap ±10°; centerSpeed is 2400 without a weapon, else the weapon's hip or ADS center speed (ADS above `fWeaponPosFrac` 0.5) times its attachments' scales, times `perk_fastSnipeScale` with that perk while scoped | **dependent**: identical for frame times that are multiples of 5 ms, different otherwise | **felt; sent to the server** (usercmd angles) |
| Viewmodel recoil | BG_CalculateWeaponMovement_Recoil (R, 140297CF0) and its single-angle step (R, 140297FF0) | `cg.frametime · 0.001` | per step of `min(0.005, rest)` s: angle += speed·dt (clamped to fGunMaxPitch/Yaw), spring `accel` toward center, `speed -= speed·decay·dt`, then a static decay, clamp to `speedMax`; hip and ADS values blended by `fWeaponPosFrac`; settles when angle < 0.25° and speed < 1°/s | **dependent** above 200 fps (and at non-multiples of 5 ms) | visible |
| Weapon sway | BG_CalculateWeaponMovement_Sway (140298100) | `frametime` (s), the view angles' change since the last frame | target = view-angle change / (frametime · 60), clamped to swayMaxAngle (blended to the ADS values); `DiffTrack`/`DiffTrackAngle` toward it at swayLerpSpeed; skipped when frametime is 0 (the change then carries to the next frame) | mean independent; Euler time constant; ±20% noise in the target where the integer frametime does not match the frame (filtered to well under 1%) | cosmetic |
| Viewmodel base position (stance, movement) | BG_CalculateWeaponMovement_Base (1402971C0) | `frametime` | `base += (target - base) · min(1, frametime · fPosMoveRate)` (and `fPosRotRate`) | Euler, near exact at high fps | cosmetic |
| Viewmodel bob | BG_CalculateWeaponMovement_Bob (1402979D0) | `ps.bobCycle` (a byte Pmove advances), xyspeed | sines of `bobCycle / 255 · 2π`, amplitude from xyspeed, scaled down while aiming | independent; phase in steps of 1/256 cycle | none |
| Idle sway, damage kick on the gun | BG_SetWeaponMovementAngles (1402988E0) | cg.time, damage time | sines of time; the kick over 100 ms in and 400 ms out | independent | none |
| View bob, ADS bob | BG_CalculateViewMovement_Angles (140296770), CG_OffsetFirstPersonView (1402E9930) | `ps.bobCycle` | as the viewmodel bob, into the view angles and the view origin | independent | none |
| Damage kick on the view | inlined in 140296770 | `time - damageTime` | rises over 100 ms, falls over 400 ms (GetLeanFraction curve) | independent | none |
| Lean roll | 1402AA1C0 | `ps.leanf` (Pmove) | roll += leanf · 12 | independent | none |
| Landing dip | CG_OffsetFirstPersonView | `cg.time - landTime` | in over 150 ms, out over 300 ms | independent | none |
| Step smoothing | CG_CalcViewValues | `cg.time - stepViewStart` | linear over `cg_viewZSmoothingTime` (set by prediction within `cg_viewZSmoothingMin/Max`) | independent | none |
| Prediction error decay | CG_CalcViewValues | `cg.time - predictedErrorTime` | linear over `cg_errordecay` | independent | none |
| Camera shake (earthquakes, explosions) | CG_ShakeCamera (R, 14029B7B0), CG_UpdateCameraShake (R, 14029BBB0) | `cg.time` | strongest of four shakes: fade `(1 - age/length) · scale`, by distance `1 - dist/radius`; angles += `sin(k·π·cg.time/600 + phase)` · (18, 16, 10)° · min(size, 1) · rumbleScale, k = 8, 15, 12 | independent (the phase is re-randomised every frame without a shake, which does not matter) | none |
| Zoom and ADS FOV | CG_GetViewFov (R, 1402E8D20) | `fWeaponPosFrac` (Pmove), zoom fraction | docs/view.md | independent (follows Pmove) | none |
| Hybrid scope switch | 1402F9120 | the switch animation's XAnim time | fraction = anim time · rate / switch time | independent | none |
| Kill cam blend | 1402EE9A0 | `cg.frametime`, the blend's end time | each frame moves `frametime / (end - oldTime)` of the remaining way: an exact linear blend | independent | none |
| Remote and killstreak cameras, third person | 1405B7B30, 1405B88F0, 1402EC620 | `cg.frametime` | `DiffTrack`/`DiffTrackAngle` | Euler, near exact at high fps | cosmetic |
| Hold-breath sound level | 1402F30A0 | `cg.frametime` | `DiffTrack` | Euler | cosmetic |
| Radar jamming level | inline in CG_DrawActiveFrame (from 1402E7C57) | none | `jam += (target - jam) / 15` per frame (snap when the squared difference is under 0.01), target from the distance to the jammer (`radarjamDistMin/Max`, `radarjamSinCurve`) | **dependent**: 15 frames is 250 ms at 60 fps, 15 ms at 1000 fps | cosmetic (HUD) |
| Radar sweep | 1402C51E0 | `cg.frametime` | `sweep += frametime / 3500` | independent | none |
| HUD timers and fades | 1402C8820, 1402C9FF0 and others | `cg.frametime`, `cg.time` | linear in time | independent | none |

### The view kick in numbers

`BG_KickAngles` with no weapon (center speed 2400 °/s²) after a kick velocity of -120 °/s in pitch, run frame by
frame (*measured*, original Store function):

| Frames | Peak kick | Back to 0 | At 100 ms | At 200 ms |
|---|---:|---:|---:|---:|
| 5 ms steps: 200 fps or any multiple of 5 ms (10, 15, 20 ...) | -3.300° | 270 ms | -3.138° | -1.734° |
| 1 ms (1000 fps) | -3.060° | 257 ms | -2.884° | -1.451° |
| 2 ms (500 fps) | -3.120° | 260 ms | -2.947° | -1.522° |
| 2, 3 ms (400 fps) | -3.084° | 260 ms | -2.909° | -1.479° |
| 3 ms (333 fps) | -3.182° | 264 ms | -2.999° | -1.573° |
| 4 ms (250 fps) | -3.245° | 268 ms | -3.079° | -1.668° |
| 4, 4, 4, 4, 4, 5 ms (240 Hz) | -3.228° | 266 ms | -3.062° | -1.649° |
| 7, 7, 7, 7, 7, 7, 6 ms (144 Hz) | -3.355° | 275 ms | -3.175° | -1.668° |
| 16, 17, 17 ms (60 Hz) | -3.319° | 283 ms | -3.158° | -1.757° |

A kick that reaches the 10° cap (-300 °/s) differs much less (the cap dominates). The kick angles are added to the
view and, through 1402AB060 → `cl.cgameKickAngles` (140306F30) → `CL_FinishMove`, to every usercmd's angles, so a
player at 1000 fps fires from an aim that kicks about 7% less than a player at 100 fps. The bots run the same
function with 50 ms (Store 14049F9C1), i.e. on the 5 ms grid.

### The viewmodel recoil in numbers

The single-angle step run as `BG_CalculateWeaponMovement_Recoil` divides the frame (*measured*, original Store
function; accel 1000, speedMax 2000, decay 24, static decay 40, fGunMaxPitch 6, initial speed 60 °/s):

| Frames | Peak | Settled (snapped to 0) | At 60 ms |
|---|---:|---:|---:|
| 5 or 10 ms | 1.090° | 170 ms | 0.931° |
| 16, 17, 17 ms | 1.063° | 166 ms | 0.827° |
| 7 ms | 1.060° | 124 ms | 0.864° |
| 4 ms | 1.057° | 164 ms | 0.885° |
| 4, 4, 4, 4, 4, 5 ms | 1.060° | 120 ms | 0.865° |
| 3 ms | 1.025° | 165 ms | 0.840° |
| 2 ms | 0.993° | 162 ms | 0.795° |
| 1 ms | 0.962° | 155 ms | 0.750° |

The settle test (|angle| < 0.25° and |speed| < 1 °/s, checked per step) makes the end of the recoil jump by tens of
milliseconds between frame patterns.

### First-order filters

`DiffTrack (tgt, cur, rate, dt)` (140530470, R) returns `cur + (tgt - cur) · rate · dt`, or `tgt` when the error is
below 0.001 or the step would overshoot; `DiffTrackAngle` (R, 1405304D0) does the same on the shorter way around. One
step is the explicit Euler step of `d/dt cur = rate · (tgt - cur)`, so after n frames of dt the remaining error is
`(1 - rate·dt)^n` instead of `exp(-rate · n·dt)`: an effective rate of `-ln(1 - rate·dt) / dt`. For rate 10/s that is
10.05/s at 1000 fps, 10.2/s at 250 fps, 10.9/s at 60 fps and 12.0/s at 30 fps. The viewmodel's base position uses
`min(1, rate · dt)`, the same step. Between 200 and 1000 fps these filters differ by under 1%.

### Viewmodel sway and the integer frame time

The sway's target is the view's angular speed, `Δangles / (frametime · 60)`. The angles change by what the mouse moved
during the real frame, while `frametime` is the integer difference of `cg.time`. Where they disagree (2 or 3 ms for a
2.5 ms frame) the target jumps by ±20 to 25% from frame to frame and is biased up by a few percent (the mean of 2.5/f
for f = 2, 3 is 1.04); the `DiffTrack` at swayLerpSpeed moves only `rate · dt` (about 1.5%) of the way per frame, so
what reaches the screen is a ripple well under 1% (*unverified* in game). With frametime 0 the function returns
before saving the view angles, and the next frame measures both frames' change over its own time: consistent.

## 3. Animation, effects, sound, UI, physics, the renderer

| System | Per-frame entry (Store) | Time input | Frame-rate behaviour |
|---|---|---|---|
| Effects (FX) | 1403AF360 (localClientNum, `cg.time`) from CG_DrawActiveFrame; 1403AF1B0 rewinds when time went back; the update proper runs as worker commands (`FX_Update` passes, PS4 `effectscore/fx_update*.cpp`) | integer ms (`msecBegin`, `msecUpdateEnd`) | Particles are spawned by time (looping intervals in ms) and their positions evaluated from their spawn time and velocity curves (PS4 `FXIW_IntegrateVelocity*`), not stepped per frame; trails spawn by distance, with the last element following the emitter. Frame-rate independent at ms resolution; a 0 ms frame updates nothing. One per-frame random spread: 1405CFBB0 spawns at `cg.time - rand() % frametime / 2`, within the frame. |
| XAnim, viewmodel | 140558FB0 (DObj, `cg.frametime · 0.001`, notify) from 1402FC0D0 | float seconds from integer ms | Animation time and notetracks advance by dtime; blends are rates per second (PS4 `xanim/xanim.cpp`). Independent. |
| XAnim, entities | 1402B4280 (msec to 14025D9F0 and 14017C060) | `cg.frametime` | the same, integer ms (*unverified* in detail) |
| Sound | the client's sound update, 140316AD0 → 1406ADF80 and 1406AD170: from Com_Frame (step 14), from SCR_UpdateFrame's end, and from R_SyncGpu when CG_DrawActiveFrame has marked one due (14065BE30), so once or more per rendered frame (*unverified* how often in normal play) | `cg.frametime` | Doppler (1406AD9E0): each channel's speed is measured from its and the listener's movement since the last update, and the pitch is **smoothed per update**: `p = (k · p + new) / (k + 1)`, k = `snd_dopplerSmoothing`. With updates tied to frames, at 500 fps the smoothing is about eight times shorter than at 60 fps, and the per-frame position steps it smooths are ms-quantized: **audible** as a noisier doppler at high frame rates (cosmetic). Occlusion and fades use ms times (`snd_occlusionDelay`, `snd_occlusionLerpTime`; *unverified*). |
| UI and LUI | 14050EF20 (`cls.realtime`) before the 2D; LUI's frame 140223F30 | integer ms | UI animations and timers run on the UI clock (*unverified* inside LUI). The UI's FPS figure averages four frames. |
| HUD | radar sweep 1402C51E0, timers 1402C8820/1402C9FF0 | `cg.frametime`, `cg.time` | independent; the radar jamming filter is per frame (section 2) |
| Physics (ODE: dynents, ragdolls, vehicles' bodies) | `Phys_RunToTime` (PS4 1402782F0, `physics/phys_ode.cpp:3944`; the Store copy is *unverified*) | integer ms | Steps of `max(remaining / 2, g_phys_msecStep)`, at most two per call, then positions blended between the last two steps by `timeNowLerpFrac`. Below the step size per frame this is a fixed step with interpolation: independent. Above it (low fps) the steps grow. |
| Ragdolls | `ragdoll_fps` (149F616C0, default 20) is registered at 1405A2080 | | no direct reader of the dvar found in the Store build (*unverified* how ragdolls step); they run in the physics world above |
| Motion blur | 1406572B0 (`r_mbEnable`) | the previous frame's view matrices | blur from the camera's change since the last frame, so its length scales with the frame time: at 500 fps an eighth of 60 fps (*unverified* in the shaders). A 360° shutter: arguably correct, but different. |
| Texture animation | 14063B0D0 (`r_atlasAnimFPS`) | a ms time | by time; independent |
| Renderer frame counters | `rg.frontEndFrameCount` (14A37CD6C) | frames | used for "once per frame" bookkeeping and warning throttles (14066A7C0 estimates the fps from it, 14066A8E0 rate-limits a warning by that); no gameplay or visual effect found |
| Texture streaming | none | | the PC build has no image streaming dvars or per-frame budget (searched the strings) |

**CPU cost per frame.** Everything above runs once per rendered frame on the main thread: snapshot processing,
prediction (which replays every unacknowledged usercmd, one per frame: the count grows with frame rate times ping,
docs/fps.md), entity interpolation and XAnim for every visible entity, the FX update, a capsule trace up from the view
for the ceiling height (CG_DrawActiveFrame, 140304650), the sound update and LUI. None of it is throttled by time, so
the cost per second grows linearly with the frame rate; that is expected, but the prediction replay grows with frame
rate twice over.

## 4. Recommendation for "fully uncoupled"

Ranked by what the player would notice. Each change is an override in `enhanced/` on reconstructed faithful code where
it exists; nothing here changes the protocol, the meaning of `cg.time` or what the server computes.

### 4.1 Fractional time for interpolation and the view origin

- **Change:** a fractional client clock beside the integer one (section 1, "Where a fractional time would go"), then
  `CG_SetFrameInterpolation` (R, 1402B5B70) with `cg.time + cg.timeFrac`, and the view origin interpolated by
  `cg.timeFrac` after prediction. `CL_SetCGameTime`'s 1 ms delta steps become a slew over a snapshot interval, applied
  to the fractional clock only (the integer `cl.serverTime` that stamps usercmds keeps the original rule, so the
  server sees the same command times).
- **Effect:** removes the uneven per-frame motion of other players, effects and the camera's translation at 144 to
  1000 Hz and with VRR.
- **Verify:** run the enhanced `CG_SetFrameInterpolation` with the snapshots fixed and `cg.time + timeFrac` stepping by
  2.5 ms (400 fps), 4.1667 ms (240 Hz) and 1 ms; the fraction must advance by exactly `step / interval` each frame
  (the faithful one alternates). The faithful function is unchanged when `timeFrac` is 0, which the differential test
  of the faithful code already covers.

### 4.2 The view kick on a fixed 5 ms grid

- **Change:** an enhanced `BG_KickAngles` (R) that, for the cgame's own arrays (`kickAVel`/`kickAngles` at
  143CD91E8/143CD91F4), carries `msec % 5` to the next call and runs only whole 5 ms steps; for display, optionally
  extrapolate the shown kick by `kickAVel · carried ms`. Other callers (the bots pass 50) are already on the grid and
  stay identical.
- **Effect:** the kick, and the aim the server receives in usercmds, are the same at every frame rate (what 200 fps and
  below give today). Highest priority after 4.1 because it is the one per-frame difference the server sees.
- **Verify in the emulator:** call the enhanced function with the frame patterns of section 2's table and compare
  `kickAngles` and `kickAVel` at every multiple of 5 ms with the faithful function run in 5 ms frames: they must be
  bit-identical. Then check that a 50 ms call (the bots) matches the faithful function exactly.
- **Since the tick loop** (docs/cgame-frame.md 4.10): implemented as P0014's grid first, now folded: the cgame calls
  the unchanged `BG_KickAngles` with 5 in every 5 ms tick, and the view command carries a copy stepped forward to the
  render time; the grid and its carry are gone.

### 4.3 The viewmodel recoil on a fixed 5 ms grid

- **Change:** the same for `BG_CalculateWeaponMovement_Recoil` (R, 140297CF0): carry the remainder of
  `frametime` below 5 ms in the enhanced build (a static beside cg's recoil state; `weaponState_t` is rebuilt every
  frame by CG_AddViewWeapon), and step whole 5 ms only. To remove the up-to-5 ms delay, show
  `recoilAngles + recoilSpeed · carried` without storing it.
- **Effect:** the gun's recoil animation and its settle time stop depending on the frame rate.
- **Verify:** as 4.2, with `BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle` (R) unchanged and the frame
  patterns of the recoil table; identical angles and speeds at multiples of 5 ms.
- **Since the tick loop** (docs/cgame-frame.md 4.10): implemented as P0015's grid first, now folded: `CG_AddViewWeapon`
  (R) is split, its movement half (the whole `BG_CalculateWeaponMovement`: sway, recoil, bob, base) runs in every
  5 ms tick with frametime 0.005, and the presentation steps a copy forward to the render time; the grid is gone.

### 4.4 Exact first-order filters in the viewmodel

- **Change:** in enhanced copies of the sway and base functions (140298100, 1402971C0), replace the Euler step
  `rate · dt` by `1 - exp(-rate · dt)`, and compute the sway's target from the frame's real duration (the fractional
  frame time) instead of the integer `frametime`. Do not change `DiffTrack` itself: the bgame vehicle code and the
  server share it.
- **Effect:** small (under 1% above 200 fps, several percent at 30 to 60 fps); makes the viewmodel identical across
  frame rates.
- **Verify:** feed a step target and compare the filtered value at 50, 100, 200 and 400 ms for 1, 2, 4, 7, 16 and
  33 ms frames: equal to `1 - exp(-rate · t)` within float rounding.

### 4.5 The radar jamming filter

- **Change:** `jam += (target - jam) · (1 - (14/15)^(frametime / 16.667))`, which keeps today's 60 fps behaviour. It
  is inline in CG_DrawActiveFrame, so it needs that function reconstructed (large) or the filter moved out in the
  enhanced build.
- **Effect:** cosmetic (how fast the minimap's jamming fades in and out).
- **Verify:** the jam level after a target step at fixed times, for several frame times.

### 4.6 Doppler smoothing

- **Change:** in 1406AD9E0, make the smoothing weight a time constant: `w = k / (k + 1)` per 16.667 ms, i.e.
  `p = p · w^(msec/16.667) + new · (1 - w^(msec/16.667))`; and measure the speeds over the fractional frame time.
- **Effect:** cosmetic, audible.
- **Verify:** a source passing at constant speed, pitch versus time for several frame times.

### 4.7 Optional

- Motion blur: scale the per-frame camera motion to a fixed shutter (for example 1/60 s) if the 60 fps look is wanted.
- The UI's FPS figure and warning throttles need nothing.

### How to verify in the emulator (all of the above)

The harness of tests/differential runs any original function on chosen memory (`Machine.call` with buffers, setups
and fakes). For a per-frame function, call it repeatedly, feeding the previous call's output buffers back, once with
frame times of 5 ms (or the reference pattern) and once with each pattern under test, then compare the state at the
times the patterns share. The measurements in section 2 were made this way against the original Store build
(`BG_KickAngles` with `BG_GetViewmodelWeapon` faked to "no weapon" and `BG_GetOverlay` pointed at an empty overlay;
the recoil step with typical gun kick values; `DiffTrack` directly). An enhanced function's test does the same with
the enhanced build and requires identical results across patterns; it must fail when the change is undone.

## Reconstructed and tested

| Function | Store | PS4 server | Source | Test |
|---|---|---|---|---|
| CG_SetFrameInterpolation | 1402B5B70 | not in the server | src/cgame_mp/cg_ents_mp.cpp | test_cg_camerashake.py (snapshot pairs equal, reversed, 1 ms to 2^31 apart; time before, between and after) |
| CG_UpdateCameraShake | 14029BBB0 | 1400A4800 (different cg_s layout: kept at `compiles` there) | src/cgame/cg_camerashake.cpp | test_cg_camerashake.py |
| CG_ShakeCamera | 14029B7B0 | not in the server | src/cgame/cg_camerashake.cpp | test_cg_camerashake.py (four shakes, dominant one, phase, crandom path) |
| BG_KickAngles | 1402905D0 | 14009D240 | src/bgame/bg_weapons_util.cpp | test_bg_weapons_util.py (msec 0 to 300, NaN and capped angles, weapon tables, attachments, overlay, perk) |
| BG_HipViewKickCenterSpeed, BG_AdsViewKickCenterSpeed | inlined in BG_KickAngles | 14009C620, 1400971C0 | src/bgame/bg_weapons_util.cpp | test_bg_weapons_util.py |
| BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle | 140297FF0 | 1400A35F0 | src/bgame/bg_weapons_view.cpp | test_bg_weapons_view.py |
| BG_CalculateWeaponMovement_Recoil | 140297CF0 | 1400A3310 | src/bgame/bg_weapons_view.cpp | test_bg_weapons_view.py (frame times around the 5 ms step, NaN, null playerState) |
| DiffTrack, DiffTrackAngle | 140530470, 1405304D0 | 14022DC10, 14022DC80 (already matching) | src/universal/com_math.cpp | generated inputs and test_com_math.py |

Each new case was mutation-checked: 24 mutations (changed comparisons, constants, step sizes, multiplication orders,
dropped clamps and conditions) all make it fail, in both builds where both have the function. Three first attempts
survived because they were equivalent and were replaced: `distFrac > 0` for `>= 0` (0 · scale and 0 / scale are
both +0), `scale *= first` for `scale = first` (scale is 1 there), and `remaining >= 0.005` for `> 0.005` (both
leave 0 to do).

## Findings for the enhanced build

Not recorded in `records/bugs.tsv` (the brief reserves it); listed here and in the report.

- **The view kick depends on the frame time** (BG_KickAngles, 1402905D0): 5 ms Euler steps with the frame's remainder.
  It reaches the usercmd's angles. (logic, gameplay-visible)
- **The viewmodel recoil depends on the frame time** (BG_CalculateWeaponMovement_Recoil, 140297CF0): the same 5 ms
  rule, plus a per-step settle test. (quality)
- **Millisecond clocks without a fractional part**: entity interpolation and the camera's translation step unevenly
  at frame periods that are not whole milliseconds; `CL_SetCGameTime` corrects the clock in 1 ms steps. (quality)
- **Per-frame constant filters**: the radar jamming level (1/15 per frame, CG_DrawActiveFrame) and the doppler pitch
  (`snd_dopplerSmoothing` per update, 1406AD9E0). (quality, low)
- **The matcher pairs CG_AddViewWeapon (1402F38B0) with the server's ClientThink_real**; records/names.tsv now
  overrides it.
