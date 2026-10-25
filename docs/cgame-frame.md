# The cgame frame, sorted into simulation and presentation (Store build)

What `CG_DrawActiveFrame` (Store 1402E7860) does, item by item and in order, which of it is input, network,
simulation, presentation, drawing or bookkeeping, which clocks the frame reads, and how the enhanced build should
restructure it into a fixed 5 ms simulation tick plus one presentation pass per rendered frame on a high-resolution
clock. This is phase 1: the map, the faithful reconstruction and the design. Nothing in `enhanced/` changes yet.

Sources and conventions:

- The Store build's disassembly; names from Black Ops' server PDB (black-ops-1-decomp, `CoDMPServer`, which kept the
  cgame), the PS4 server PDB (`iw6_ds_ps4`) and the matcher, every one recorded in `records/names.tsv` with its
  evidence. A callee without a known name is `sub_<Store address>`; names.tsv says what is known of it.
- **(R)** marks functions reconstructed in `src/` and passing their differential tests against the Store build.
- *Unverified* marks what was read from the code but not run, or a role guessed from a callee's shape.
- docs/fps.md (usercmds, Pmove, prediction, P0016, P0017) and docs/fps-frame.md (the per-frame effects, P0014,
  P0015) are the background; this page does not repeat their numbers.

## Summary

- **The frame is one pass with everything interleaved.** Around 110 calls and inline blocks run in one order every
  rendered frame: the scene is cleared, the clock advanced, snapshots processed, ~15 simulation steps integrate
  `cg.frametime` or `cls.frametime`, the GPU wait and the mouse come in the middle, the usercmd is built and sent,
  the predicted state is advanced, and only then is the view computed, the viewmodel built and the scene submitted.
  The presentation reads simulation state, and three simulation steps read presentation results of the *previous*
  frame (the environment volumes use last frame's view origin, the kick that goes into the usercmd is last frame's,
  aim assist uses last frame's screen targets).
- **Simulation steps that integrate the frame time** (each its own state, each called once per frame): the view
  kick (`BG_KickAngles`, B0063), the viewmodel recoil, sway, base position and hold-breath filter
  (`CG_AddViewWeapon`, B0064), the radar sweep, the radar jamming filter (1/15 per frame, B0066), the turret scope
  zoom, the environment volume blend, a ±1 ramp on `cls.frametime / 300`, the kill cam blend, XAnim of every
  entity, of the player's own body and of the viewmodel (with their notetracks), the reactive-motion wind phase, 64
  hinged physics objects (semi-implicit Euler, *frame-rate dependent*), the physics world (fixed steps inside), the
  DiffTrack cameras inside `CG_CalcViewValues`, the HUD timers on `Sys_Milliseconds`, the predicted player state
  (per usercmd) and its events.
- **Presentation** reads that state and computes what is drawn: the refdef and view angles, the viewmodel's pose,
  other entities interpolated between snapshots by `cg.frameInterpolation`, effects at `cg.time`, the HUD, the sound
  listener. Much of it is closed-form in `cg.time` (shakes, fades, step smoothing, error decay, shell shock) and so
  already correct at any render time; some of it carries state that should be simulation (the DiffTrack cameras).
- **Every clock under the frame is whole milliseconds** and comes from `timeGetTime` (section 3). The fractional
  render time the design needs exists nowhere.
- **Design (section 4):** read input once per frame right after the frame wait (as now), then run 0..20 simulation
  ticks of exactly 5 ms on the usercmd grid (each tick: build the usercmd for that time, predict to it, step every
  integrator by 5 ms, fire events), then one presentation pass at the fractional render time that steps the own
  view and viewmodel forward from the latest tick on copies (no latency) and interpolates other entities between
  snapshots, with the mode chosen per category behind one table. P0014 and P0015 become the tick's plain 5 ms calls
  to the unchanged original functions plus a step-forward copy; P0016's grid becomes the tick clock; P0017's partial
  Pmove becomes the own-view category's step-forward.
- **Reconstructed:** `CG_DrawActiveFrame` (R) with `CG_UpdateThirdPerson` (R) and six small callees (R), tested
  against the Store exe with every callee a logged fake (1,500 inputs) and mutation-checked (section 6).
- **New findings** (section 5), not in records/bugs.tsv: P0017 saves and restores the wrong 0x5D8 bytes for the
  character info; a turret scope's zoom sound is started every frame while zooming; 64 hinged objects integrate
  with frame-length Euler steps; the HUD timers run on the wall clock with a one-frame delay in frames;
  `CG_AddPacketEntities` keeps a per-call parity bit; the volume blend reads the previous frame's view.

## 1. Where the frame runs

`SCR_UpdateScreen` → `SCR_UpdateFrame` (14031B1F0: `CG_SavePlayerState` (R) at 14031B231, then) →
`CL_CGameRendering` (14031B150) → **`CG_DrawActiveFrame(localClientNum, cl.serverTime, 0, 0, 0, renderScreen,
drawRenderScreen)`**, where `renderScreen` is 140509710's result == 0 (no full-screen UI) and `drawRenderScreen`
`CL_CGameRendering`'s second argument, passed through to `CG_DrawActive`. When the frame returns 0 (nothing drawn),
`CL_CGameRendering` calls 14030BAD0 and `CL_SendCmd` itself: commands are still made and sent. When it returns 1:
14050EF20(lc, `cls.realtime`) (the UI clock), 14050B110, 14064C1A0.

Signature: `int CG_DrawActiveFrame(LocalClientNum_t, int serverTime, DemoType, CubemapShot, int cubemapSize, int
renderScreen, int drawRenderScreen)` (Black Ops' has no seventh argument and stores `renderScreen` in
`cg.renderScreen`, as this one does at cg+0x3378).

## 2. The frame, in order

Classes: **IN** input (what goes into the next usercmd or the input path), **NET** snapshots and packets, **SIM**
simulation (integrates or filters over time, or fires events), **PRE** presentation (computes what is drawn from
state; category in brackets: own view, viewmodel, other entities, effects, HUD, sound), **DRAW** scene and
renderer submission and pacing, **BK** bookkeeping. "Time" is what clock the item reads. For SIM: the state it
carries between frames and whether running it once per 5 ms tick instead of once per frame is safe. VAs are call
sites in 1402E7860 unless noted.

### 2.1 Start of frame, the clock

| # | VA | Item | Class | Time | Notes |
|---|---|---|---|---|---|
| 1 | 1402E788C | sub_140654BA0: the renderer's scene lists and counts cleared | DRAW | | Black Ops' `R_ClearScene` place |
| 2 | 1402E7894 | sub_140654C40(lc): the scene's per-client state reset, three dvars copied | DRAW | | |
| 3 | 1402E7899 | sub_1402BE670: empties the tag-effect entity list (count 143C0D3E4) | BK | | filled during the frame, read by #81 |
| 4 | 1402E78A3 | sub_1403A0030(lc, serverTime): effects whose time is past serverTime + 1 brought back | PRE (effects) | serverTime | *unverified* role (FX system 1403ACB80) |
| 5 | 1402E78AB | sub_1403AEFF0(lc): three effects-side resets | PRE (effects) | | |
| 6 | 1402E78B0 | sub_1403447B0: 1442D4060 = 1 | BK | | *unverified* |
| 7 | 1402E78B8 | sub_14029EDB0(lc): the collision world's local client | BK | | |
| 8 | 1402E78C4 | unk_143C23F60 = &cg.refdef; `sub_140536260` (memset) of cg+0xA9760, 0x100 bytes | BK | | |
| 9 | 1402E78DF | **the clock**: `oldTime = time`; `cubemapSize`, `renderScreen`, `demoType`, `cubemapShot` stored; `time = bgs.time = serverTime`; `frametime = time - oldTime`, and if negative `frametime = 0, oldTime = time`; `bgs.frametime = max(0, ...)`; `radarJamDistance = -1` | BK | cl.serverTime | the only place cg.time advances (but see #12) |
| 10 | 1402E7920 | `CG_GetPredictedPlayerState(lc)`, kept for #91 | BK | | |
| 11 | 1402E7973 | TLS guard (`__dyn_tls_on_demand_init`), then the thread-local `bgs = &cg.bgs` | BK | | bgame code reads the animation state through it |

### 2.2 Snapshots and the decision to draw

| # | VA | Item | Class | Time | Notes |
|---|---|---|---|---|---|
| 12 | 1402E79B2 | `CG_ProcessSnapshots`: transitions to every snapshot `cg.time` has passed (`CG_SetNextSnap` copies the snapshot's player state into the predicted one, entity events, server commands), `CG_SetFrameInterpolation` (R); on the first snapshot `CG_SetInitialSnapshot` (1402DBBF0) **resets cg.time, oldTime and bgs.time to the snapshot's time** after #9 computed frametime | NET | cg.time | edge-triggered on time; no integration. Fires events. |
| 13 | 1402E79CF | `FX_RewindTo(lc, cg.time, frametime)` when time went back and the kill cam state didn't change in #12 | PRE (effects) | cg.time | |
| 14 | 1402E79D4 | **return 0** (bgs cleared) if `!renderScreen`, no next snapshot, `nextSnap->snapFlags & 2`, or `CL_IsServerLoadingMap()` (R) | BK | | no input, no command, no drawing from the cgame this frame |
| 15 | 1402E7A32 | `CL_SetWaitingOnServerToLoadMap(lc, false)` (R) | BK | | |
| 16 | 1402E7A3A | `g_cgameClientNum = lc` | BK | | |
| 17 | 1402E7A41 | sub_1402D3230: the predicted state's preparation (docs/fps.md 7.2 step 4): `predictFromTime`, and for pm_type 1/8, linkFlags 4, a demo or a followed player `CG_InterpolatePlayerState` (the whole state **interpolated between snapshots at cg.time**), else the snapshot's state copied while on an entity | NET / PRE (own view, when interpolating) | cg.time, frameInterpolation | |
| 18 | 1402E7A46 | sub_140316200: a client double buffer flipped (counter 1441CC5D4) | BK | frame counter | |
| 19 | 1402E7A4B | refdef: `vieworg = cg+0x71914`, `refdef.time = cg.time`, `refdef.frametime = cg.frametime` | PRE (own view) | cg.time | |
| 20 | 1402E7A96 | scripted camera: `sub_140187D70` then `sub_14018A640` (a blend by `(cg.time - start) / duration`) | PRE (own view) | cg.time | closed form |
| 21 | 1402E7AB7 | `R_SetLodOrigin(&refdef, 1.0)`: also **the renderer's scene time** (14B26B108 ms, 14B26B10C s) = refdef.time | DRAW | refdef.time | the renderer's clock (#57) |
| 22 | 1402E7ABF | `CG_CompassIncreaseRadarTime`: the radar sweep `+= frametime / 3500`, radar sounds | SIM (HUD) | cg.frametime, cg.time | state: the sweep in cg. Linear, so tick-safe; its sounds are edge-triggered |
| 23 | 1402E7ACD | `FX_SetNextUpdateTime(lc, cg.time)` | PRE (effects) | cg.time | effects spawn and evaluate by time: frame-rate independent at ms resolution (docs/fps-frame.md 3) |
| 24 | 1402E7B00 | the shell shock: `BG_GetShellshockParms` (R) of the snapshot's index (or the test shock), `CG_StartShellShock` (R), `CG_UpdateShellShock` (blur, sensitivity, sounds, by `cg.time - start`) | PRE (HUD, sound, own view) | cg.time | closed form; its end sounds are edge-triggered |
| 25 | 1402E7B3A | `CG_UpdateThirdPerson` (R): `renderingThirdPerson` from the next snapshot | PRE (own view) | | a decision, no state over time |
| 26 | 1402E7B59 | third-person vehicle view on (sub_1402EA200) or off (sub_1403046D0) | PRE (own view) | | edge |
| 27 | 1402E7B85 | `CG_ClearHudGrenades` | BK | | |

### 2.3 Animation, entities, HUD state

| # | VA | Item | Class | Time | Notes |
|---|---|---|---|---|---|
| 28 | 1402E7BAC | for every entity of the next snapshot with a DObj: `CG_DObjUpdateInfo` (R; `DObjUpdateClientInfo(obj, cg.frametime · 0.001, notify)`) and `CG_ProcessClientNoteTracks` | SIM (other entities) | cg.frametime | state: each DObj's XAnim tree (animation times, blend weights). Time-linear, but the times are float sums of the steps; notetracks fire sounds, effects and the gun hand on crossing. Tick-safe (each notetrack still fires once); cost per tick |
| 29 | 1402E7BEF | sub_140178750: aim assist's per-frame vectors cleared | IN | | |
| 30 | 1402E7BF7 | sub_1402EC410: the weapon overlay/scope state (EMP, kill cam, hybrid sight) | PRE (HUD) | | no clock found |
| 31 | 1402E7BFC | sub_140377D80: 14604C980 = 0 | BK | | |
| 32 | 1402E7C09 | `CG_AddPacketEntities(lc, delayed[])`: every entity's position (interpolated by `cg.frameInterpolation`, trajectories at `cg.time`), scene adds, entity events, looping sounds, the nearest jammer's distance; returns the delayed entities. **Flips a parity bit (143D3C6B8) on every call** | PRE (other entities) + events | cg.time, frameInterpolation | must stay once per presentation (the parity) |
| 33 | 1402E7C0E | inline: **the radar jamming level** moves 1/15 of the way to a target from the jammer distance (radarjamDistMin/Max, radarjamSinCurve) per frame, floored by ps.radarStrength (−3: 1, −2: 0.5, −1: 0.3, else 0), snapped within 0.1 | SIM (HUD) | frames | state cg.radarJamLevel (cg+0x10EDBC). **Not** tick-safe as is: the rate is per call (B0066) |
| 34 | 1402E7D69 | sub_1402D4BF0: a per-client sound state (143E60D60) | PRE (sound) | cg.time | *unverified* |
| 35 | 1402E7D71 | sub_1402E61B0: the environment volume containing **last frame's view origin** (cg+0x10E840) and a blend `frac += cg.frametime / (time · 1000)` between two volumes (1402E5F90) | SIM (effects) | cg.frametime | state 143E743C0..CC. Linear: tick-safe, but it reads a presentation result one frame late |
| 36 | 1402E7D76 | sub_1402FB790: 64 HUD timers advanced by `Sys_Milliseconds()` deltas × a timescale (140460E10); expiry at 300 ms; queued events stamped with a frame counter (143E8FFD8) and handled on the next call | SIM (HUD) | **Sys_Milliseconds**, frame counter | its own wall clock; the hand-off is one frame late, whatever the frame length |
| 37 | 1402E7D8C | sub_1402F11D0(lc, cg+0x10AD28, cg.time) | PRE | cg.time | *unverified* |

### 2.4 Before the GPU wait (local client 0)

| # | VA | Item | Class | Time | Notes |
|---|---|---|---|---|---|
| 38 | 1402E7DAB | sub_1401B3710(cg.time) | BK | cg.time | |
| 39 | 1402E7DE4 | sub_1401B2960(lc, cg.time / 1000, (time − oldTime) / 1000, &refdef, cg.clientNum): reactive motion (foliage): the wind phase `= fmodf(frametime · r_reactiveMotionWindFrequencyScale + phase, 43200)`, actor impulses faded by time | SIM (effects) | cg.time, frame seconds | state 1433E6C78 and the impulse list. Linear; float sums differ with the step |
| 40 | 1402E7DE9 | sub_14065BE30: a sound update marked due (R_SyncGpu runs it) | BK (sound) | | |
| 41 | 1402E7DEE | sub_1402D2410 (R): the early prediction | SIM (prediction) | usercmd times | docs/fps.md 7.3 |
| 42 | 1402E7DF5 | `CL_SyncGpu(NULL)` (R) → `R_SyncGpu`: the com_maxfps sleep, the back-end wait, P0004's frame-latency wait, P0009's late keys | DRAW (pacing), IN (keys) | Sys_Milliseconds | |
| 43 | 1402E7DFF | sub_140376E30(1): a streaming request flushed | BK | | |

### 2.5 Input, prediction, events

| # | VA | Item | Class | Time | Notes |
|---|---|---|---|---|---|
| 44 | 1402E7E04 | `R_ToggleSmpFrame` (R): the front-end buffer flip | DRAW | | may wait for the render thread |
| 45 | 1402E7E0C | `CL_Input` (R): `IN_Frame` (the mouse) and `CL_CreateNewCommands` (R; P0016's grid in the enhanced build) | IN | frame_msec, cls.frametime(_base), com_frameTime, cl.serverTime | the usercmd gets last frame's `cgameKickAngles` |
| 46 | 1402E7E14 | sub_1402AA2A0: 143D337A8 moved toward ±1 by `cls.frametime / 300` per frame (or a weapon rate) | SIM | **cls.frametime** | linear with clamps: tick-safe. *unverified* what it drives |
| 47 | 1402E7E1C | `CG_PredictPlayerState` (R) | SIM (prediction) | usercmd times, cg.time | Pmove per command; the player entity, `CL_SetUserCmdOrigin` |
| 48 | 1402E7E24 | sub_1402FC4F0: the equipped weapons' viewmodel models | PRE (viewmodel) | | |
| 49 | 1402E7E66 | the arms model: sub_14018DB60 → `R_RegisterModel` → sub_1402FBC30, when `ps.viewmodelIndex > 0` | PRE (viewmodel) | | |
| 50 | 1402E7E81 | sub_14017F630 → sub_140658100 (a renderer flag) | DRAW | | |
| 51 | 1402E7EA7 | `unk_143C23F68 = 0`, then `CG_TransitionPlayerState` (the predicted events between the saved and the new state, unpredictable events, damage feedback) | SIM (events) | | events fire once per sequence number: tick-safe |
| 52 | 1402E7EC7 | the delayed entities: `CG_ProcessEntity`, and `CG_CheckEntEvents` when unk_143C177FC | PRE (other entities) + events | cg.time | |
| 53 | 1402E7F42 | `CG_EntityEvent(…, 0x3A, …)` on the view-locked (or vehicle) entity, as many times as #51 counted | SIM (events) | | |
| 54 | 1402E7F60 | sub_1402CF440 → sub_1402CEB10: the player's own DObj in third person: `CG_DObjUpdateInfo` (frametime), notetracks, processing | SIM (own body anim) + PRE | cg.frametime | as #28 |
| 55 | 1402E7F68 | sub_1403AF520: effects worker command 0xB | PRE (effects) | | |
| 56 | 1402E7F76 | sub_140471E70(lc, cg.frametime): a per-client entity list (DObj part bits); **the frame time argument is not used** | PRE | | *unverified* |
| 57 | 1402E7F8A | local client 0: sub_14037E3D0 (client dynamic entities placed from the physics' interpolated states), sub_140588090(0, cg.time) (the physics world stepped to cg.time on a worker), sub_14019B2C0(frametime / 1000) | PRE (effects); SIM (physics) | cg.time; frame seconds | sub_14019B2C0: 64 hinged objects (140DF253C) with gravity, torque and damping, **semi-implicit Euler with the frame's length**: frame-rate dependent, not tick-safe without fixing the step. The physics world (`Phys_RunToTime`-style fixed steps and interpolation, docs/fps-frame.md 3) is already a fixed step, *unverified* in the Store build |
| 58 | 1402E7FD0 | sub_14065B690(lc, 0, sub_1402DF750, sub_1402DF740): a renderer per-client state blended by the scene time (#21) | PRE (effects) | scene time | closed form |
| 59 | 1402E7FDC | **whether the first-person scene is drawn** (cg+0x10E79E): not EMP-jammed, no kill cam of type 1/3/7, and with otherFlags 8 not in a kill cam with otherFlags 0x400000, else sub_1402EF4D0 (the weapon state); then sub_140657FC0 to the renderer | PRE (viewmodel) | | |
| 60 | 1402E805F | `SND_SetEnvironmentEffects(4, room, dry, wet, 0)` while otherFlags 0x20 (a remote camera), else `SND_DeactivateEnvironmentEffects(4, 0)`, every frame | PRE (sound) | | |
| 61 | 1402E80C3 | location selection: key catcher 8 added or removed (`Key_AddCatcher` (R), `Key_RemoveCatcher` (R)), the cursor reset to the centre | IN / HUD | | |
| 62 | 1402E817B | **the view kick**: `BG_KickAngles(&ps, cg.frametime, kickAVel, kickAngles)` (R; P0014) while otherFlags 0x4000, else both zeroed | SIM (own view; reaches the usercmd) | cg.frametime | state cg+0xB5268/0xB5274. Original steps ≤ 5 ms: a 5 ms tick is exactly its 200 fps behaviour |
| 63 | 1402E8196 | sub_1402EF6B0: the spawn sight checks (masks for the next usercmd) | IN | | |
| 64 | 1402E819E | `CL_SendCmd` (R) | NET | cls.realtime | |

### 2.6 The view, the viewmodel, the scene

| # | VA | Item | Class | Time | Notes |
|---|---|---|---|---|---|
| 65 | 1402E81A3 | inline: **a turret's FOV** (cg.scriptedViewFov): with a scope (`overlayInterface` 2) it zooms by `frametime / 1000 · forwardmove / −127 · turretScopeZoomRate`, clamped to min/max, and starts the zoom sound every frame it changes; else `(1 − adsFrac) · turretFov + adsFrac · turretFovADS` | SIM (own view) | cg.frametime, the newest usercmd | linear with clamps: tick-safe; the sound per call is not (section 5) |
| 66 | 1402E82C1 | `CG_UpdateViewWeaponAnim`: the viewmodel's XAnim (`DObjUpdateClientInfo` with cg.frametime), its notetracks | SIM (viewmodel) | cg.frametime | state: the viewmodel DObj's tree |
| 67 | 1402E82C6 | inline (Black Ops' `UpdateKillCamEntityCache`): the kill cam's entity pose and look-at point (+50 up) | PRE (own view) | | |
| 68 | 1402E836D | `CG_CalcViewValues`: the refdef from the predicted state (step smoothing and error decay closed-form in cg.time, `CG_OffsetFirstPersonView`, `CG_ShakeCamera` (R), the FOV), and for remote, killstreak and third-person cameras `DiffTrack`/`DiffTrackAngle` filters (1405B7B30, 1405B88F0, 1402EC620) | PRE (own view) with SIM inside | cg.time, cg.frametime | the DiffTrack cameras carry state per frame (Euler, docs/fps-frame.md 2) |
| 69 | 1402E8375 | `LerpKillCamView`: `frametime / (end − oldTime)` of the remaining way | SIM / PRE (own view) | cg.frametime, cg.oldTime | an exact linear blend |
| 70 | 1402E837A | `cg.lastVieworg = refdef.vieworg` | BK | | read by #35 next frame |
| 71 | 1402E83AD | sub_1402FC790: DObj traces and an effect for each listed entity | PRE (effects) | cg.time | |
| 72 | 1402E83B5 | `CG_AddViewWeapon`: builds `weaponState_t` (frametime = cg.frametime · 0.001) and runs `BG_CalculateWeaponMovement` (recoil (P0015), sway and base DiffTrack, bob from bobCycle), the hold-breath sound filter (1402F30A0), the viewmodel's scene entry | PRE (viewmodel) with SIM inside | cg.frametime, cg.time | state saved back into cg_s |
| 73 | 1402E83BD | sub_1402AD490: the scope lens state | PRE (viewmodel) | | |
| 74 | 1402E83D6 | sub_140654E80 when a missile camera or #59: the renderer's first-person block cleared | DRAW | | |
| 75 | 1402E83FE | `FX_SetNextUpdateCamera(lc, &refdef, &tanHalfFov, zfar (sub_14060DC10), #59)` | PRE (effects) | | |
| 76 | 1402E8413 | sub_1402D4820(lc, ps.clientNum, refdef.vieworg): the listener's origin | PRE (sound) | | |
| 77 | 1402E841B | sub_140275D90: the slide sound loop started or stopped | PRE (sound) | | edge |
| 78 | 1402E8420 | inline: a per-client periodic effect (unk_143E8E3F0) played when `cg.time > last + period` | PRE (effects) | cg.time | after a long frame it plays once, not several times |
| 79 | 1402E84F0 | inline (Black Ops' `GetCeilingHeight`): a 1024-unit box trace up from the player | PRE (effects input) | | |
| 80 | 1402E8542 | sub_140655200; sub_1402C5700 → sub_1402C5740 | DRAW / HUD | | *unverified* |
| 81 | 1402E855E | sub_1402BE7B0: effects at the listed entities' tags | PRE (effects) | | |
| 82 | 1402E8566 | sub_1403AF710, sub_1403AF230: the remaining effects worker commands | PRE (effects) | | |
| 83 | 1402E85A7 | `AimAssist_UpdateScreenTargets(lc, …, tanHalfFovX, tanHalfFovY)` | IN | | computed from this frame's view, used by the next frame's mouse |
| 84 | 1402E85AF | `CG_UpdateSceneDepthOfField` | PRE (own view) | | |
| 85 | 1402E85B4 | inline: a flag that clears itself after `duration` ms of cg.time (cg+0x71A48..54) | BK | cg.time | closed form |
| 86 | 1402E85EE | inline (Black Ops' `CG_ValidateWeaponSelect`): a selection past the weapon table replaced by the first equipped weapon sub_1402F8FC0 accepts; the underbarrel alternate cleared without weapFlags 0x80000 | IN | | |
| 87 | 1402E86BD | inline: the player-card materials of 18 clients (patches.csv, backgrounds.csv) looked up when changed, all kept loaded (sub_14037AE50); sub_1405E8170 (empty); one more material kept | PRE (HUD) | | |
| 88 | 1402E87E3 | inline: the view origin and, when more than 2048 away, the eye handed to 14604CE20/14604CEF8; the remote view origin to 14604CD48 | BK | | *unverified* consumer (streaming?) |
| 89 | 1402E8929 | `CG_DrawActive` (R): FOV sensitivity, `kickAngles + offsetAngles`, the weapons and the extra buttons for the next usercmd, then `CL_RenderScene` | DRAW + IN | | the kick reaches the usercmd from here, one frame late |
| 90 | 1402E8931 | sub_140179B50: aim assist's target traces | IN | | |
| 91 | 1402E8936 | `bgs = 0`; sub_1406A6C80 (the sounds queued this frame start); `viewTeleported = 0`; `lastMantleFlags`, `lastWeapFlags` from #10's pointer; return 1 | BK, PRE (sound) | | |

### 2.7 The shape, by class

- **IN**: #29, #42 (late keys), #45, #61, #63, #83, #86, #89 (hand-off), #90.
- **NET**: #12, #17 (reset), #64.
- **SIM (time-integrating)**: #22, #28, #33, #35, #36, #39, #46, #54, #57 (hinges, physics), #62, #65, #66, #68 (DiffTrack cameras), #69, #72 (recoil, sway, base, hold breath); prediction #41, #47; events #51, #53.
- **PRE**: own view #17 (interpolated mode), #19, #20, #24, #25, #26, #67, #68, #84; viewmodel #48, #49, #59, #72, #73; other entities #32, #52; effects #4, #5, #13, #23, #57, #58, #71, #75, #78, #79, #81, #82; HUD #24, #30, #87; sound #24, #34, #60, #76, #77, #91.
- **DRAW**: #1, #2, #21, #42, #44, #50, #74, #80, #89.

## 3. The clocks

| Clock | Where it is set | From | Readers in the cgame frame |
|---|---|---|---|
| `Sys_Milliseconds` (R, 14054FE20) | every call | `timeGetTime() − sys_timeBase`, 1 ms after `timeBeginPeriod(1)` | Com_Frame (`com_frameTime`); `R_SyncGpu`'s waits; **sub_1402FB790's HUD timers (#36)**; event timestamps (`Sys_QueEvent`); `CL_PacketEvent`; asset lookups (14036C290); the renderer's fps estimate and warning throttles (14066A7C0, 14066A8E0); a random seed in the weapon effects (1402F9820) |
| `com_frameTime` (146A7D6AC) | Com_Frame's body (140460400) | Sys_Milliseconds + the com_maxfps wait | key down times (`CL_KeyState`), P0016's span |
| `frame_msec` (1442B98C0) | sub_140316290 (R) | `com_frameTime − old`, 1..200 | `CL_MouseMove`, `CL_KeyState` (#45) |
| `cls.frametime`, `cls.frametime_base`, `cls.realtime` (cls+0x118/0x11C/0x120) | sub_140316290 (R) | Com_Frame's smoothed, scaled msec | #46 (`cls.frametime / 300`), `CL_AdjustAngles`, `CL_GamepadMove`; `CL_SendCmd` (#64); `CL_SetCGameTime`; the UI clock (14050EF20, after the frame) |
| `cl.serverTime` (143E99EF0) | `CL_SetCGameTime` (140306C40) | `max(prev, cls.realtime + delta)`, delta nudged per snapshot | the usercmd stamp; `CG_DrawActiveFrame`'s argument (#9) |
| `cg.time`, `cg.oldTime`, `cg.frametime` (cg+0x71890/94/8C) | #9; `CG_SetInitialSnapshot` (#12) | cl.serverTime | nearly everything in section 2 |
| `bgs.time`, `bgs.frametime` (cg+0xFAE58, 0xFAE64) | #9 (and #12) | cg.time | the bgame animation code (through the thread-local `bgs`) |
| `refdef.time`, `refdef.frametime` (cg+0x7192C/30) | #19 | cg | `CG_CalcViewValues`; `R_SetLodOrigin` |
| the renderer's scene time (14B26B108 ms, 14B26B10C s) | `R_SetLodOrigin` (#21) | refdef.time | #58 and the renderer (texture animation, shader time *unverified*) |
| `cg.frameInterpolation` (cg+0x71888) | `CG_SetFrameInterpolation` (R) in #12 | cg.time and the snapshots | other entities (#32), #17 |
| effects time | `FX_SetNextUpdateTime(cg.time)` (#23), sub_1403A0030 (#4) | cg.time | the effects workers |
| physics time | sub_140588090(0, cg.time) (#57) | cg.time | the physics worker |
| XAnim dtime | `DObjUpdateClientInfo` (#28, #54, #66) | cg.frametime · 0.001 | animations, notetracks |
| weaponState_t::frametime | `CG_AddViewWeapon` (#72) | cg.frametime · 0.001 | recoil, sway, base, hold breath |
| frame counters | `com_frameNumber` (Com_Frame), `rg.frontEndFrameCount` (14A37CD6C, `R_BeginFrame`), `com_lastFrameIndex`, 1441CC5D4 (#18), 143E8FFD8 (#36), the parity bit 143D3C6B8 (#32) | | throttles, double buffers, the HUD timers' hand-off, entity marking |
| the UI clock | 14050EF20(lc, cls.realtime) after a drawn frame | cls.realtime | LUI and HUD fades (*unverified* inside LUI) |

So two roots, both `timeGetTime`: Com_Frame's integer msec (→ `cls.*`, `cl.serverTime`, `cg.*`, everything derived) and
direct `Sys_Milliseconds` reads (#36 and pacing). The high-resolution clock goes under both (4.1).

## 4. Design: a 5 ms tick loop and a presentation pass

Goals from the brief: simulation in fixed 5 ms ticks that never see the frame time; presentation once per rendered
frame that reads the simulation without changing it, the own view stepped forward to the exact render time, other
entities interpolated as now, one switch per category; a high-resolution clock under both.

### 4.1 The clock

- **One counter.** `Sys_Microseconds()` (int64 µs from `QueryPerformanceCounter`). `Sys_Milliseconds` becomes
  `(int)(µs / 1000)` (floor; both count from the first read): the same integer meaning, now consistent with the
  fraction. Every original millisecond value keeps being computed exactly as today from it.
- **Com_Frame** keeps its integer msec rules (limiter, smoothing, timescale), so `cls.realtime`, `frame_msec` and the
  protocol are unchanged; it also keeps `cls.realtimeUs` (int64) advanced by the frame's real length in µs (the
  smoothing and the timescale applied to the fraction too, so `cls.realtimeUs / 1000` tracks `cls.realtime`).
- **The render time** `T_r` (double, ms) = `cl.serverTime + (cls.realtimeUs mod 1000) / 1000`, with
  `CL_SetCGameTime`'s ±1/−2 ms delta corrections slewed over the next snapshot interval for `T_r` only (the integer
  `cl.serverTime` keeps the original rule, so command times are the original's).
- **The tick time** is P0016's grid: tick k at `t_k = lastCmdTime + 5`, an integer ms, created while `t_k <= cl.serverTime`
  (at most 20 per frame, re-anchored past 500 ms, never backwards). `T_r − t_latest` is 0..5 ms (fractional).
- During a tick the cgame sees `cg.time = t_k`, `cg.oldTime = t_{k−1}`, `cg.frametime = 5` (and `bgs` alike). During
  the presentation it sees `cg.time = floor(T_r)` plus a new `cg.timeFrac` (0..1), and `cg.frametime` is the number of
  ms the presentation clock advanced (only the PRE items that read it, listed in 4.3, which are changed to use the
  fraction or to read tick state).

### 4.2 The enhanced CG_DrawActiveFrame

```
CG_DrawActiveFrame(lc, serverTime, ...):
  [frame start]  #1-#8, #11                          once
  [network]      cg.time = serverTime (the frame's integer render ms); #9's oldTime/frametime for the network only
                 #12 CG_ProcessSnapshots, #13, #14 (return 0), #15, #16
  [pacing+input] #40, #41-early prediction -> folded into the ticks (below), #42 CL_SyncGpu (wait, late keys),
                 #43, #44, IN_Frame + mouse/keys/gamepad into clViewangles (P0016's "every frame" half of #45)
  [ticks]        for each due tick t_k (0..20):
                   cg.oldTime, cg.time, cg.frametime = t_{k-1}, t_k, 5   (bgs too)
                   build the usercmd for t_k (P0016's "commands" half of #45), with cgameKickAngles = the kick at
                     t_{k-1} (canonical, from the previous tick) and the frame's input
                   #17 for t_k, #47 CG_PredictPlayerState up to the usercmd of t_k (canonical; no P0017 swap here)
                   #51 CG_TransitionPlayerState, #53 events                        (events of exactly this command)
                   #62 BG_KickAngles(ps, 5, ...)        original function, 5 ms (P0014 folded)
                   #72's movement half: BG_CalculateWeaponMovement on cg's weaponState with frametime 0.005
                                                        (recoil P0015 folded, sway, base, bob angles, hold breath)
                   #66 viewmodel XAnim dtime 0.005, #28 entity XAnim dtime 0.005 + notetracks, #54 own body XAnim
                   #22 radar sweep, #33 radar jam (per-tick constant, 4.6), #35 volume blend (reads the tick's
                     eye, not last frame's view), #39 reactive motion, #46 ramp (5 instead of cls.frametime),
                     #57 hinges (step 0.005), #65 turret zoom (zoom sound edge-triggered, 4.6), #68's DiffTrack
                     camera filters (split out of CG_CalcViewValues), #69 kill cam blend
                   save the tick snapshot (4.4)
                 #64 CL_SendCmd (once, after the ticks: every command of the frame in one packet as now)
  [present]      cg.time = floor(T_r), cg.timeFrac = frac(T_r)
                 for each category, by its mode (4.3): own view, viewmodel, other entities, effects, HUD, sound
                 #19-#21, #23-#26, #30, #32, #34, #36 (HUD timers on the µs clock), #37, #48-#50, #52, #55-#58,
                 #59-#61, #63, #67, #68 (view only), #70-#91
                 CG_DrawActive: kick for the hand-off = the canonical tick kick (not the stepped one)
  [end]          restore every presentation copy (P0017's restore generalised), bgs = 0, return 1
```

Notes on the order:

- **Input stays where it is**: the mouse is read right after the frame wait (lowest latency), keys too (P0009).
  Each tick's command takes this frame's angles and buttons; P0016's per-frame/per-command split is unchanged.
- **Commands move into the tick loop.** Today (and with P0016) a frame's commands all carry the kick of the previous
  frame's end. In the tick loop command k carries the canonical kick at t_{k−1}: the aim the server sees no longer
  depends on the frame rate at all (B0063 fully), and the kick is at most one tick (5 ms) late instead of one frame.
- **Prediction per tick** (incremental, as the original already is between snapshots: docs/fps.md 7.1): every tick
  sim reads the predicted state *at its own time*, which test (a) needs. The cost is the same Pmoves as now, split.
- **CG_ProcessSnapshots stays once per frame**, at the frame's integer render ms: it is edge-triggered, not an
  integrator, and other entities interpolate from it at the render time. A snapshot that arrives between two
  ticks resets the predicted state (`CG_SetNextSnap`) before the frame's ticks run, as today before the prediction.
- **Frames without a due tick** (above 200 fps, 4 frames in 5 at 1000 fps) run no simulation at all; only the
  presentation, stepped from the same latest tick.

### 4.3 Presentation categories and the one switch

```
enum PresentCategory { PC_OWN_VIEW, PC_VIEWMODEL, PC_OTHER_ENTITIES, PC_EFFECTS, PC_HUD, PC_SOUND, PC_COUNT };
enum PresentMode     { PM_STEP_FORWARD, PM_INTERPOLATE, PM_EXTRAPOLATE };
PresentMode cg_presentMode[PC_COUNT] = { STEP_FORWARD, STEP_FORWARD, INTERPOLATE, INTERPOLATE, STEP_FORWARD, STEP_FORWARD };
double CG_PresentTime(PresentCategory c);   // the time that category is drawn at, from its mode
```

| Category | Items | STEP_FORWARD (default for own view, viewmodel, HUD, sound) | INTERPOLATE (default for other entities, effects) | EXTRAPOLATE (later) |
|---|---|---|---|---|
| own view | #17 (interpolated mode), #19, #20, #24-#26, #67, #68, #84 | the latest tick's predicted state + a partial `Pmove` of `floor(T_r) − t_k` ms on copies (P0017), plus `velocity · timeFrac` for the sub-ms rest; kick, camera filters advanced by the rest on copies; angles from this frame's `clViewangles`; closed-form terms (step smoothing, error decay, shakes, shell shock) evaluated at `T_r` | the last two ticks' states blended at `T_r − 5` (adds 5 ms; for comparison only) | as step-forward |
| viewmodel | #48, #49, #59, #66 (pose), #72 (pose), #73 | the tick's weaponState + one partial step of the rest on a copy (P0015's "shown"), the viewmodel's XAnim time advanced by the rest on a saved tree and restored | blend of the last two ticks | |
| other entities | #32, #52, #28 (pose) | n/a: they have no tick state of ours | today's: snapshots blended by `cg.frameInterpolation` computed at `T_r` (fractional, docs/fps-frame.md 4.1), animation at the latest tick | extrapolate the newest snapshot to `T_r + interpolation delay` (zero-interpolation) |
| effects | #4, #5, #13, #23, #57, #58, #71, #75, #78, #79, #81, #82 | effects evaluated at `T_r` (they are closed-form in time) | at `T_r` as well (FX is time-based either way) | |
| HUD | #24, #30, #36, #87, the 2D after the frame | closed-form HUD terms at `T_r`, simulated ones (radar sweep, jam) from the latest tick + rest | from the latest tick | |
| sound | #34, #60, #76, #77, #91 | the listener at the stepped view (#76 after the own view) | | |

The switch is the `cg_presentMode` table (a dvar per category later). Every presentation consumer reads its mode
through `CG_PresentTime(category)` or one `CG_PresentMode(category)` check, nothing else; changing an entry changes
only the consumers of that category (test d).

### 4.4 The tick state saved for stepping forward

At the end of each tick the canonical values the presentation steps from (all copied, never written back by the
presentation; restored at the end of the frame by the generalised P0017 restore):

- the predicted `playerState_s` (0x3328) and `cg_pmove` (0x178), the newest real usercmd, the tick's time;
- `kickAVel`, `kickAngles`;
- the viewmodel's `weaponState_t` fields kept in cg_s (recoil angles/speed, sway, base, bob angles, last idle
  factor) and the viewmodel XAnim tree's times (its goal weights and times; size *unverified*);
- the DiffTrack camera states of #68 (remote, killstreak, third-person cameras), the kill cam blend (#69);
- the step smoothing (`stepViewStart`, `stepViewChange`) and the error (`predictedError`, `predictedErrorTime`):
  closed-form in time, so the presentation only evaluates them at `T_r`;
- the HUD integrators (radar sweep, jam level, turret FOV) for their step-forward;
- the bgame character info of the local client (0x5D8 bytes at `bgs + 0x459F0 + clientNum · 0x5D8`, see 5.1).

### 4.5 How P0014-P0017 fold in

- **P0014 (kick grid)**: the tick calls the original `BG_KickAngles` with 5; the carry and the change detection go
  away (a shot changes the state inside a tick's event processing, which is on the grid). The "shown" kick becomes
  the own-view step-forward: the original function with the fractional rest on a copy (a float-msec variant of the
  original step: one `min(5, rest)` step is all it ever is).
- **P0015 (recoil grid)**: the same with `BG_CalculateWeaponMovement_Recoil` at `frametime 0.005` per tick; the grid
  keyed on `weaponState_t::time` is not needed (one call per tick), the "shown" step is the viewmodel step-forward.
  It requires splitting `CG_AddViewWeapon` (#72) into its movement half (tick) and its pose/scene half (present).
- **P0016 (5 ms usercmds)**: its grid is the tick clock; its command-building half runs inside the tick loop (one
  command per tick, with that tick's kick), its every-frame half (angles from the mouse, keys, gamepad) stays before
  the ticks. `cl_viewCmd` stays: the presentation's partial Pmove command.
- **P0017 (view at the render time)**: its partial Pmove and swap become the own-view step-forward; the swap/restore
  pair generalises to every presentation copy (one restore point at the end of the frame and at the start of the next
  tick). Fix its character-info save first (5.1).

### 4.6 Items that need more than moving into the tick

- **#33 radar jam**: a per-call constant. Per tick: `jam += (target − jam) · (1 − (14/15)^(5/16.667))` keeps today's
  60 fps look (docs/fps-frame.md 4.5), or keep 1/15 per tick if 15 ticks (75 ms) is wanted.
- **#57 hinges** (sub_14019B2C0): needs `dt = 0.005` per tick; the integrator itself is unchanged.
- **#65 turret zoom sound**: start it on the edge (zooming started), not every call.
- **#36 HUD timers**: on the µs clock instead of `Sys_Milliseconds`; the frame-counter hand-off can stay (it is
  in presentation).
- **#35 volume blend**: read the tick's eye position instead of last frame's view origin.
- **#32 CG_AddPacketEntities**: once per presentation only (its parity bit and event dispatch).
- **#46**: `cls.frametime` → 5 in the tick (it is a cgame integrator reading the client's clock).
- **#68 CG_CalcViewValues**: split the DiffTrack camera filters (state) from the view computation; the filters tick,
  the view steps forward.

### 4.7 HUD, LUI and sound

- The HUD (`CG_Draw2D` in 14031B3D0) and LUI read cg state and `cls.realtime` after the frame: they get the
  presentation's values (closed-form fades at `T_r`, simulated HUD values from the latest tick plus the rest). LUI's
  own clock stays `cls.realtime` (integer); a fractional `cls.realtimeUs` can be offered later.
- Sound: the listener (#76) at the stepped view; doppler (docs/fps-frame.md 4.6) measured over the real elapsed µs;
  event sounds fire from the ticks (events are tick-side), loops and environment effects from the presentation.

### 4.8 Tests that will prove it

All in the emulator with the enhanced DLL, driving whole frames as tests/enhanced/frame_sim.py does, with a fixed
input script (the same mouse path, keys and fire presses as a function of time) and fixed snapshots:

- **(a) simulation identical at every frame pattern.** Run 1 s of game time at 60, 144, 165, 240, 360, 500 and 1000
  fps (fractional periods, the original smoothing and delta nudges on). After every tick compare the canonical
  state (predicted state, cg_pmove, kick, weaponState fields, radar sweep/jam, turret FOV, volume blend, DiffTrack
  cameras, the usercmds and their times) with a reference run at exactly 5 ms frames: **bit-identical at every tick
  time**, and every event (pe sequence, notetracks, CG_EntityEvent) fired once at the same tick. Fails when any
  integrator reads `cg.frametime` of a frame.
- **(b) own view at the render time, no added latency.** At 500, 1000 and 4.17 ms frames: the drawn origin equals a
  `Pmove` of the canonical state to `floor(T_r)` plus `velocity · timeFrac`; the drawn angles equal this frame's
  `clViewangles` (+ delta, clamps); the drawn kick equals the canonical kick advanced by `T_r − t_k`; and the frame
  wait → input → draw path has no tick boundary in it (a mouse movement read this frame is in this frame's view).
  Compare against the original at 1000 fps on frames that make a command: identical view.
- **(c) interpolated categories smooth at uneven periods.** Frames of 2.5 ms (2/3), 4.17 ms (4,4,4,4,4,5) and 6.94 ms
  (144 Hz): other entities' `frameInterpolation` advances by exactly `Δ T_r / snapshot interval` each frame (the
  faithful one alternates), and positions by `speed · Δ T_r` within float rounding.
- **(d) one switch, one category.** For each category, flip its mode and record every presentation output (refdef,
  viewmodel pose, entity poses, effect camera, HUD values, listener): only that category's outputs change, and the
  canonical tick state is bit-identical to (a)'s reference. Then flip them all back: identical to the first run.
- Mutation checks as for P0014-P0017: reading `cg.frametime` instead of 5 in any ticked integrator, skipping a
  restore, using the stepped kick for the usercmd, a category reading another's mode — each must fail a test.

### 4.9 Stage 1 as implemented (the clock, the render time, the mode table)

Stage 1 of the design: 4.1's clock and render time, 4.3's table, wired into other entities and the own view. The
tick loop (4.2) and the per-item fixes (4.6) are stages 2 and 3.

- **The clock** (enhanced/win32/win_clock.cpp): `Sys_Microseconds()` counts `QueryPerformanceCounter` from its first
  read (`sys_qpcBase`, `sys_qpcFrequency`), split as `t / f · 10⁶ + t % f · 10⁶ / f` so it can't overflow;
  `Sys_Milliseconds()` (overrides 14054FE20) is its floor in ms. The QPC base has its own flag (`sys_qpcInitialized`):
  14054FD70 also initialises the original bases (`sys_timeBase`, `sys_counterBase`, `sys_timeBasesInitialized`) from
  timeGetTime, and the enhanced first read only sets those when nothing has. Nothing else in the Store build calls
  timeGetTime (14054FD70 and the original Sys_Milliseconds are its only callers), so every game millisecond now comes
  from QPC.
- **cls_realtimeUs** (enhanced/client_mp/cl_render_time.cpp): the enhanced `sub_140316290` (overrides 140316290; the
  faithful body copied unchanged) then sets `cls_realtimeUs = 1000 · cls.realtime + clamp(Sys_Microseconds() −
  1000 · com_frameTime, 0, 999)`. Com_Frame's body (limiter, smoothing, timescale) is untouched, so `cls.realtime`,
  `cls.frametime`, `frame_msec` and everything sent are the original's.
- **T_r** (`CL_RenderTime()`, same file): `cl.serverTime + fraction + slew`, computed once per frame (cached on
  `cls_realtimeUs` and `cl.serverTime`). `CL_SetCGameTime` (140306C40) is not overridden: the frame's correction is
  observed as the change of `cl.serverTime − cls.realtime` since the last frame. It is either a delta nudge (±1, −2)
  or `cl.serverTime` held by its `max`. A correction of up to 10 ms is taken out of T_r and put back linearly over
  the snapshot interval (`cl.snap.serverTime − cl.oldSnapServerTime`, 50 ms when out of 1..500). A larger one (the
  delta halved or reset) jumps. A backward step of up to 10 ms is held, so T_r never goes back short of a reset.
- **The table** (enhanced/cgame_mp/cg_present.cpp, enhanced/include/enhanced/render_time.h): `PresentCategory`,
  `PresentMode`, `cg_presentMode[]` with 4.3's defaults (own view, viewmodel, HUD, sound `PM_STEP_FORWARD`; other
  entities, effects `PM_INTERPOLATE`), `CG_PresentMode`, `CG_PresentTime` (cg.time + `CL_RenderTimeOffset()`; plus
  `cg_presentExtrapolateMsec` in `PM_EXTRAPOLATE`; the own view in `PM_INTERPOLATE` at cg.time).
- **Other entities**: the enhanced `CG_SetFrameInterpolation` (overrides 1402B5B70) blends at
  `CG_PresentTime(PC_OTHER_ENTITIES)`, fractional; it forms the integer difference first, so with no fraction it is
  the original bit for bit. `PM_EXTRAPOLATE` is the same blend past 1 at the render time plus the lead: switching
  other entities to zero interpolation later only means choosing the lead.
- **The own view** (enhanced/cgame_mp/cg_view_step.cpp, P0017): when `CG_PresentMode(PC_OWN_VIEW)` is
  `PM_STEP_FORWARD`, the partial Pmove runs to `floor(CG_PresentTime(PC_OWN_VIEW))` instead of `cl.serverTime`, and
  the copy's origin moves on by `velocity · rest` for the rest of the millisecond. In any other mode the canonical
  prediction is drawn.
- **Left for stages 2 and 3, still at cg.time**: the viewmodel (CG_AddViewWeapon's weaponState time and XAnim), the
  effects (`FX_SetNextUpdateTime(cg.time)`, an integer, inside the frame), the HUD (the 2D after the frame, the radar
  sweep and fades), sound (the listener follows the drawn view already; doppler and the update times don't), the
  renderer's scene time (`R_SetLodOrigin`, refdef.time), the closed-form view terms in `CG_CalcViewValues` (shakes,
  step smoothing, error decay at cg.time), trajectories evaluated at cg.time in `CG_AddPacketEntities`. Each needs an
  override of a function not yet reconstructed, or the tick loop.

Deviations from 4.1:

1. The fraction is measured when the client's clock advances (in `sub_140316290`, after the server frame), not at
   Com_Frame's own clock read, and it is clamped to 0..999 µs. With the com_maxfps wait added to `com_frameTime` the
   fraction is 0, which is right: the frame is meant for the end of the wait.
2. The fraction is real time, not scaled by the timescale (exact at timescale 1).
3. Only corrections up to 10 ms are slewed (4.1 said "the ±1/−2 ms corrections"; the held `cl.serverTime` is the
   same kind and is slewed too).
4. The own view's `PM_INTERPOLATE` is the canonical prediction (no tick states to blend before stage 2), and
   `PM_EXTRAPOLATE` for it draws the canonical prediction as well.
5. With the slew, a frame whose `cl.serverTime` repeated now steps the view forward by the slewed time. So P0017's
   zero-leftover angle path is reached only when T_r is exactly the newest command's time.

Tests (tests/enhanced/test_render_time.py, 13 tests):
- **The clock.** Sys_Milliseconds and Sys_Microseconds are the floors of the QPC counts for four frequencies. Fed
  timeGetTime values that read the same milliseconds (near the 32-bit wrap), the original Sys_Milliseconds returns the
  same values. The QPC clock still takes its base after 14054FD70's init.
- **The client clock.** The enhanced `sub_140316290` writes exactly the original's globals on 150 inputs, and
  `cls_realtimeUs` follows its rule.
- **T_r.** It is `cl.serverTime` + the fraction at 2.5, 4.17, 6.94, 1 and 16.67 ms frames, monotonic and in
  [cl.serverTime, +1). After a +1, −1, −2 or +2 correction it is continuous and back on `cl.serverTime` + fraction
  within one interval. A held `cl.serverTime` is caught up; a 300 ms correction jumps. A slew put back faster than
  real time holds T_r.
- **(c) Other entities.** At 2.5, 4.17 and 6.94 ms frames `frameInterpolation` advances by ΔT_r / 50 (within 2·10⁻⁶),
  and the original `CG_InterpolateEntityPosition`'s position by 190 · ΔT_r / 1000. With no fraction the blend equals
  the original's on 300 inputs (snapshots up to 2³¹ apart).
- **(b) The own view.** The drawn origin is the fraction-0 run's plus velocity · rest (0.25, 0.6, 0.999 ms), with the
  same frame's angles and an identical canonical state. `PM_INTERPOLATE` draws the canonical state.
- **(d) One switch, one category.** Other entities' `PM_EXTRAPOLATE` with a 7 ms lead moves the blend by exactly
  7/50 and leaves the own view's drawn states identical. The own view's `PM_INTERPOLATE` changes the drawn view and
  not the blend. `CG_PresentTime`/`CG_PresentMode` are checked for every category and mode, an out-of-range mode
  included.

Mutation checks: 26 mutations of the new code (the µs split, the ms floor, the QPC base and its flag, the fraction's
clamp and base, frame_msec's clamp, the slew's sign, rate, decay, limit and reset, the monotonic hold, the fraction's
scale, the accessor's offset, lead, own-view case and mode clamp, the blend's offset, divisor and clamp, the mode check
and the rest of the own view) all fail. Two first attempts survived and got tests: the monotonic hold (a slew put back
in 1 ms) and the own view's `PM_INTERPOLATE` time (the accessor tested directly).

## 5. Findings

New, for the enhanced build (not in records/bugs.tsv; listed here and in the report):

1. **P0017 saves the wrong character info.** `CG_CharacterInfo` (enhanced/cgame_mp/cg_view_step.cpp) takes
   `*(TLS block + 0x10) + clientNum · 0x5D8`, but TLS+0x10 is the `bgs` pointer (PS4 PDB: `?bgs@@3PEAUbgs_t@@EA` at
   TLS offset 0x10) and the character info is `bgs->characterinfo[clientNum]` at `bgs + 0x459F0 + clientNum · 0x5D8`:
   `BG_AnimUpdatePlayerStateConditions` (140258460) writes `bgs + clientNum · 0x5D8 + 0x45EF8`. So the partial Pmove's
   animation-condition writes are **not** undone, and 0x5D8 bytes of `animScriptData` are copied back and forth
   instead (harmless). Its test (tests/enhanced/test_view_step.py, frame_sim.py) points TLS+0x10 straight at a
   scratch character info and fakes the conditions there, so it can't see this. (logic, medium; read from the
   disassembly, not run)
2. **A turret scope's zoom sound starts every frame while zooming** (#65: `sub_1402C1130` whenever the FOV changed):
   at 1000 fps a thousand starts a second (frame-rate dependent; *unverified* whether the alias loops or stacks).
3. **64 hinged objects integrate with the frame's length** (sub_14019B2C0, #57): semi-implicit Euler with gravity,
   torque and damping on `cg.frametime`: their swing changes with the frame rate (*unverified* which objects).
4. **HUD timers on the wall clock** (sub_1402FB790, #36): `Sys_Milliseconds` × a timescale (140460E10), not cg.time
   (*unverified* whether that matters during kill cams or demos), and their events are handed over one frame later
   in frames.
5. **The environment volume blend reads the previous frame's view origin** (sub_1402E61B0, #35): transitions start
   one frame late (16 ms at 60 fps, 1 ms at 1000 fps).
6. **`CG_AddPacketEntities` flips a parity bit per call** (143D3C6B8, #32): it must run exactly once per drawn frame.
7. **`CG_SetInitialSnapshot` resets cg.time after the frame computed `frametime`** (#12): on the first snapshot the
   frame's frametime (and bgs.frametime) belong to the old time. Harmless today (*unverified*); a tick loop must take
   its times after the network step.
8. **sub_140471E70 is passed `cg.frametime` and ignores it** (#56): nothing to fix.
9. Restated from docs/fps.md and docs/fps-frame.md for completeness of the frame: the kick reaches the usercmd one
   frame late (#89), the jam filter per frame (B0066), recoil and kick per frame (B0063, B0064).

## 6. Reconstructed and tested

| Function | Store | Source | Test |
|---|---|---|---|
| `CG_DrawActiveFrame` (with the inlined `UpdateKillCamEntityCache`, `GetCeilingHeight`, `CG_ValidateWeaponSelect`) | 1402E7860 | src/cgame_mp/cg_view_mp.cpp | test_cg_view.py: 1,500 inputs, every callee a logged fake (about 110 calls compared in order with their arguments), global and TLS writes compared |
| `CG_UpdateThirdPerson` | 1402EF9E0 | src/cgame_mp/cg_view_mp.cpp | test_cg_view.py (400) |
| `CG_StartShellShock` | 1402DAC10 | src/cgame/cg_shellshock.cpp | test_cg_view.py |
| `BG_GetShellshockParms` | 140266F40 (PS4 140076150) | src/bgame/bg_misc.cpp | test_cg_view.py, both builds |
| `CL_IsServerLoadingMap`, `CL_SetWaitingOnServerToLoadMap` | 140314FE0, 1403165A0 | src/client_mp/cl_main_mp.cpp | test_cg_view.py (bools 0/1: the original moves the raw byte) |
| `CG_DObjUpdateInfo` | 1402B3140 | src/cgame_mp/cg_ents_mp.cpp | test_cg_view.py |
| `Key_AddCatcher` | 1403106C0 | src/client/cl_keys.cpp | test_cg_view.py |

Mutation checks: 48 mutations (38 of `CG_DrawActiveFrame`: comparisons, constants, dropped statements, swapped
arguments and call order, the early return's TLS clear; 4 of `CG_UpdateThirdPerson`; 1 to 2 of each small function).
All fail their tests except two equivalent ones: `frametime <= 0` for `< 0` (at 0 both leave `frametime` 0 and
`oldTime == time`) and `distMin >= distance` for `>` in the jam distance clamp (at equality both store the same
value). Two first attempts survived and got better inputs: the 2048-unit eye distance (view offsets between 1000
and 2048 added) and `CG_DObjUpdateInfo`'s scale (its fake didn't log without a setup binding the machine).

Layout added to the headers: cg_s fields from 0x3360 to 0x10F058 (the clock arguments, the refdef's time and base
origin, the kill cam, the shell shock, the turret FOV, the radar jam, the bgs with `characterinfo` and `clientinfo`,
the card cache), snapshot_s's `snapFlags`, `numEntities`, `entities`; playerState_s's `viewlocked_entNum`, the radar
fields and `PlayerEquippedWeaponState`'s PS4 names; WeaponDef's turret FOV and zoom fields. Each is checked by a
static_assert in the file that uses it.

## 7. Not done

- The big callees were followed only far enough to place them (section 2); those marked *unverified* were read, not
  run. `CG_ProcessSnapshots`, `CG_CalcViewValues`, `CG_AddViewWeapon`, `CG_AddPacketEntities` and the effects
  workers are not reconstructed; splitting #68 and #72 into tick and presentation halves needs them reconstructed
  first.
- The six small unnamed callees (sub_1402D4820, sub_140178750, sub_1402DF740, sub_1402DF750, sub_140657FC0,
  sub_1401B3710) are fully read (names.tsv) but not reconstructed: none of them reads a clock.
- The viewmodel XAnim save/restore for step-forward (4.4) is untested: its size and cost are *unverified*.
