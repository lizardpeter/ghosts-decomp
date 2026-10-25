# Frame rate: frame timing, usercmds, movement and prediction (Store build)

How the Microsoft Store build (`iw6mp64_MSStore_ship`) turns the clock into frame times and usercmds, how the
movement code uses them on the client and on the server, and what the enhanced build should change so that movement
no longer depends on the frame rate. The view, animation and interpolation side is a separate document.

Sources and conventions:

- The Store build's disassembly; names from the PS4 server PDB (`iw6_ds_ps4`), Black Ops' server PDB and the matcher,
  each recorded in `records/names.tsv`. **(R)** marks functions reconstructed and passing their differential tests
  (`records/functions.tsv`). *Unverified* marks what was read but not exercised.
- "Measured" numbers come from running the Store build's own `Pmove` (140273A90) in the emulator (section 3.4).

## Summary

- **Nothing in the movement code uses a fixed time step.** Every usercmd is simulated as one `PmoveSingle` step of
  its own length (split only above 66 ms), on the client and identically on the server.
- **`PmoveSingle` rounds the velocity to whole units per second at the end of every step** (`Sys_SnapVector`). With
  gravity 800 a step of n ms changes the vertical speed by 0.8·n, which is rounded every step, so the jump's
  effective gravity depends on n. This is CoD4's 125/250/333 fps effect, and Ghosts has it unchanged: the jump peak is
  31.3 units at 500-1000 fps, 38.2 at the default 85 fps cap, 41.3 at 125 fps and 46.4 at 333 fps. The server
  simulates the client's own command lengths, so this is authoritative, not a prediction artefact.
- **The frame time is whole milliseconds** (`timeGetTime`), at least 1 ms (so at most 1000 fps; a faster frame is
  slept up to 1 ms), at least `1000 / com_maxfps` ms (so `com_maxfps` 85 gives 11 ms frames, 90.9 fps), and smoothed
  over three frames.
- **One usercmd per drawn frame**, timestamped with the client's integer server time. At high frame rates this also
  causes: commands with the same time (the server drops them), more than the 32 commands a packet can carry above
  ~960 fps at 30 packets a second, and a prediction window of only 128 commands (128 ms at 1000 fps).
- **Recommendation:** generate usercmds on a fixed 5 ms grid (200 Hz), decoupled from rendering, and predict the
  view to the render time with a temporary partial step that is never sent. 5 ms (and 10 ms) is the step at which
  gravity changes the speed by a whole number per step (4 units/s), so the jump reaches the designed 39 units
  (39.06 measured). The server needs no change.

## 1. Frame timing (Com_Frame)

### Where the frame's msec comes from

`Com_Frame` (140460380) calls its body (140460400, the PS4 server's `Com_Frame_Try_Block_Function`). The body
inlines the frame-time computation, the PS4 server's `Com_TimeScaleMsec` and `Com_UpdateSlowMotion`, and a three-frame
smoothing the server doesn't have. The steps, in order (`docs/frame.md` gives the rest of the frame):

1. **Minimum frame length.** `maxfps = com_maxfps` (146A7D160). If the timescale `com_timescaleValue` (1409990C0) is
   below 0.1, `maxfps = min(maxfps, max(1, (int)(timescale · 320)))` (or that value if `maxfps` is 0).
   `minMsec = 1000 / maxfps` (integer division; 1 if that is 0), or **1 when `maxfps` is 0**.
2. `com_lastFrameIndex` (146A7D794) is incremented; `idx = old value % 3`.
3. `Com_EventLoop` (R), then `now = Sys_Milliseconds()` (R, 14054FE20: `timeGetTime() - sys_timeBase`, 1 ms
   resolution after `timeBeginPeriod(1)`; the enhanced build takes the same milliseconds from QueryPerformanceCounter,
   docs/cgame-frame.md 4.9).
4. `msec = max(0, now - com_frameTime)`. `g_maxFpsWaitTime = minMsec - msec`; if that is at least 1, `now +=
   g_maxFpsWaitTime` and `msec = minMsec`, else `g_maxFpsWaitTime = 0`. `com_frameTime = now`. The wait itself is
   slept later, in `R_SyncGpu` (docs/frame.md section 3).
5. Clamp: `msec = min(msec, sv_running ? com_maxFrameTime : 5000)` (`com_maxFrameTime` 100, 50..5000). The frame's
   length in seconds is `msec · 0.001`.
6. **Three-frame smoothing**, when `msec <= 40`: three accumulators (146A7D788 int[3], 146A7D798 float[3]) each get
   `msec` (and the seconds) added; accumulator `idx` then holds the last three frames' sum `S`
   (`S = max(minMsec, S)`). The frame's msec becomes `(S + idx) / 3` (at least 1), which spreads the remainder over
   three frames so the total is kept; the seconds become `max(sum, minMsec · 0.001) / 3`; accumulator `idx` restarts
   from `(a0 + a1 + a2 - 2S) / 3`, the other two frames' carried share. Above 40 ms all three get 40 added, `idx`'s is
   reset, and the frame's own msec is used unsmoothed.
7. Slow motion (`g_slowmoCommon`, 146A7D708) moves `com_codeTimeScale` (146A7D7A4); the timescale is snapped to
   exactly 1.0 when equal.
8. `fixedtime` (146A7D150): if set, `msec = fixedtime` and the timescale becomes `fixedtime / msec`. Else with a
   timescale other than 1, `g_acculMsec` (146A7E7B4) carries the fraction: `msec = (int)(msec · timescale +
   g_acculMsec)`. `msec = max(msec, 1)`.
9. That `msec` goes to `SV_Frame`, `sub_140316290` (R; it adds it to `cls.realtime` and `cls.frametime`, sets
   `cls.frametime_base` to the smoothed seconds, and sets `frame_msec = com_frameTime - old_com_frameTime`, the
   unsmoothed length, 0 → 1, at most 200) and 140377180.

This model was checked against the original: the Store build's body run in the emulator with every callee faked,
on 400 random states (frame clock, `com_maxfps` including 0 and negative, timescale 0.05..2, `fixedtime`,
`sv_running`, `com_maxFrameTime`, the accumulators and the frame index), gives exactly the model's msec to both
`SV_Frame` and `sub_140316290` and bit-identical frame seconds. The body itself is not reconstructed: it is 1.9 KB
with ~45 callees and touches thread-local storage three times (the dvar modified flags); the Store build's TLS is now
linkable (`tools/build_recon.py`, `_tls_index`, `dvar_modifiedFlags`, `__tls_guard` in names.tsv), so it is the next
candidate.

Registration (R, `Com_InitDvars`, 140460F80): `com_maxfps` int 85, 0..100; `com_maxFrameTime` 100, 50..5000;
`fixedtime` 0, 0..1000.

### What the numbers mean for the frame rate

- **Available rates with a cap:** `1000 / com_maxfps` is truncated, so the cap gives whole-millisecond frames:
  `com_maxfps` 85 → 11 ms (90.9 fps), 100 → 10 ms (100 fps). Values above 100 are refused by the dvar (B0024).
- **Uncapped:** `com_maxfps 0` is allowed and gives `minMsec = 1`: the game runs at up to 1000 fps already. A frame
  that took less than 1 ms is counted as 1 ms and slept up to it (`g_maxFpsWaitTime = 1`), and `com_frameTime` runs
  ahead of the clock by the overshoot; the next frame's measured msec absorbs it.
- **msec 0 cannot reach the game from Com_Frame**: at 2000 fps every frame would still be counted and slept as
  1 ms. The 1 ms minimum is the hard cap at 1000 fps. (msec 0 does appear in usercmds; see 2.2.)
- **Uncapped at a rate that doesn't divide 1000** the frame msec alternates: at 144 Hz 7, 7, 7, 6, ...; the
  smoothing keeps the total and only rearranges the sequence.
- **Once per frame regardless of msec:** both `Com_EventLoop`s, `Cbuf_Execute` twice, `SV_Frame` (which runs the
  server only when 50 ms have accumulated), `CL_Frame`, the cgame frame (one usercmd, one prediction, one send
  check), `SCR_UpdateScreen`, sound. Nothing in this path loops over fixed time steps.

## 2. Usercmds

### 2.1 Creation

- One command per drawn frame: `CG_DrawActiveFrame` → `CL_Input` (R) → `CL_CreateNewCommands` (R, 14030BB00) →
  `CL_CreateCmd` (R, 14030EB60) → `CL_FinishMove` (R, 14030CDF0). The Store build has no timing in
  `CL_CreateNewCommands`: `frame_msec` is set by `sub_140316290` (R). While connecting,
  `CL_CreateCmdsDuringConnection` (R) does the same once a frame.
- `CL_FinishMove` sets **`cmd.serverTime = cl->serverTime`** unchanged (Black Ops clamped it to the snapshot time +
  5000; the Store build doesn't), the angles `(clViewangles + cgameKickAngles) · 65536/360` rounded to shorts, the
  cgame's weapon/offhand, the alternate-mode and gamepad bits, and ORs in `cgameExtraButtons`.
- **`cl->serverTime`** comes from `CL_SetCGameTime` (140306C40, *name by lineage, not recorded*): `max(previous,
  cls.realtime + serverTimeDelta)`; the delta is nudged by ±1 ms per new snapshot (−2 after an extrapolated one),
  halved toward the target past 100 ms and reset past 500 ms. Between snapshots the command time therefore advances
  by the frame msec of section 1; when the delta drops it can advance by 0.
- **The command's length is `cmd.serverTime - ps.commandTime`**: the server and the prediction both derive it, so the
  length of every command is exactly the client's frame msec (± the delta nudges).

### 2.2 Commands the server drops

- `SV_UserMove` (PS4 PDB) runs a command only if its `serverTime` is greater than the last command's; `ClientThink_real`
  clamps `serverTime` to `level.time` and returns for a command of less than 1 ms. **Two frames with the same
  `cl->serverTime` make two commands with the same time and the server drops the second**, with its angles and
  buttons. It happens when the delta is nudged down by 1 (or 2) ms at a frame msec of 1 (or 2): at 500-1000 fps,
  around every snapshot that adjusts the delta (*rate unverified*). A press that lasted one such command is lost.

### 2.3 Buffer and packets

- `cl->cmds` is a ring of `CMD_BACKUP` 128 (`CMD_MASK` 127). It is overwritten silently; nothing waits for the send.
- `CL_SendCmd` (R, 14030E370) sends at most one packet a frame, when `cls.realtime - lastPacket.p_realtime >=
  1000 / cl_maxpackets` (integer). **The packet interval is that rounded up to whole frames**: with the default 30
  (33 ms) it is 48 ms at 62.5 fps (20.8 packets/s), 40 ms at 125 fps (25/s), 36 ms at 250 (27.8/s), 33 ms at 333 fps
  and above (30.3/s). `cl_maxpackets` is 30 (15..100) and the rate code sets 15 below rate 5000
  (`cl_packetdup` 1, or 2 below 4000).
- `CL_WritePacket` (R, 14030E710) sends every command since the packet `cl_packetdup + 1` packets back, **at most 32**
  (`MAX_PACKET_USERCMDS`), the newest. New commands per packet are `fps / packets per second`: above 32 · 30 = 960 fps
  commands are lost on every packet, and above 480 fps the duplicates that cover a lost packet no longer fit. The
  server then sees a gap and simulates it as one longer command with the next command's input.

### 2.4 Frame-rate dependent parts of building a command

| Where | What | Effect |
|---|---|---|
| `CL_KeyState` (R, 14030DAA0) | movement keys as the fraction of `frame_msec` they were down; down/up times are `com_frameTime`, not the event time | the ramp is quantized to frames; with one command per frame the total is right |
| `CL_MouseMove` (R, 14030DC20) | `cl_mouseAccel` uses counts per `frame_msec`; `m_filter` averages two frames | fps-dependent only with acceleration (default 0) or the filter on; the enhanced build has neither (P0002) |
| `CL_MouseMove` | the cgame's max yaw/pitch speed caps scale with `frame_msec` | time-correct |
| `CL_AdjustAngles` (in `CL_CreateCmd`) | arrow-key turning × `cls.frametime · 0.001` | time-correct |
| `CL_GamepadMove` (R, 14030CF10) | stick turning × `frametime_base` (the smoothed seconds) | time-correct for the turn rate (*the acceleration ramp unverified*) |
| `CL_CreateCmd` | pitch limited to 90° per command | per command; irrelevant in practice |

## 3. Movement physics

### 3.1 Pmove (R, 140273A90)

`Pmove` runs `PmoveSingle` (140273CF0) from `ps->commandTime` to `cmd.serverTime`: nothing if the command is older,
the last 1000 ms at most, in steps of **at most 66 ms**. There is no `pmove_fixed`/`pmove_msec`: a command of n ms
(n ≤ 66) is one step of n ms. After the loop it sets the torso and waist pitch (the PS4 server's `PM_SetPitchValues`,
inlined).

### 3.2 PmoveSingle and the snapping

- `pml.msec = cmd.serverTime - commandTime`, clamped to 1..200; `pml.frametime = msec · 0.001`.
- Gravity is integrated with the trapezoid rule inside `PM_SlideMove` (PS4 PDB): the end velocity `v - g·dt`, the
  average for the move, then the end velocity. For constant gravity that alone is exact at any step.
- **At the end of a normal move `PmoveSingle` calls `Sys_SnapVector(ps->velocity)`** (R, 14054FE80:
  `floorf(x + 0.5f)` per component). With gravity 800 the vertical speed loses 0.8·n per n-ms step and is then
  rounded to a whole number: 1 ms → 1 (effective gravity 1000), 2 ms → 2 (1000), 3 ms → 2 (667), 4 ms → 3 (750),
  5 ms → 4 (800), 7 ms → 6 (857), 8 ms → 6 (750), 10 ms → 8 (800), 16 ms → 13 (812). Acceleration and friction
  are rounded the same way.
- Before the snap, if the player moved less than half as fast as its velocity says (blocked), the velocity is
  replaced by the actual displacement / frametime.

### 3.3 Jump (R, bgame/bg_jump.cpp)

- `Jump_Check` (1402609B0): a new press of the jump button (0x400 not in `oldcmd`), at least 500 ms after the last
  jump, standing, not frozen or mantling, not on a player or agent. The inlined `Jump_Start` sets `velocity[2] =
  sqrt(gravity · 2 · height)` with `height = Jump_GetJumpHeight` (the "alt_jump_height" omnvar, else **39**):
  249.8 units/s. A jump during the landing slowdown divides the squared speed by `Jump_ReduceFriction` (1..2.5).
- **`Jump_ClampVelocity` caps the height at `jumpOriginZ + 39` only when `PM_StepSlideMove` steps up during a jump**
  (and `Jump_GetStepHeight` limits that step to what is left to the peak). A free jump is not capped, so its peak is
  whatever the snapped integration gives. Ledges reached by stepping up are limited to 39; ledges reached by the
  free arc are not.

### 3.4 Measured: one jump at different command lengths

The Store build's own `Pmove` run in the emulator (scratchpad harness, not in the repo): a flat floor at z = 0 from
a faked trace handler (box against a plane, Quake 3's 0.125 surface epsilon), the player standing (gravity 800,
speed 190, bounds 30×30×70), weapon, footstep, animation, sprint, ADS and mantle code faked out
(`BG_GetMoveSpeedScale` = 1.0). Run forward for 1 s, then press jump; peak above take-off, time to landing, distance.

| Command length | Peak | Air time | Distance |
|---|---:|---:|---:|
| 16 ms (62.5 fps) | 38.48 | 624 ms | 118.6 |
| 11 ms (`com_maxfps 85`, 90.9 fps; the default) | 38.22 | 616 ms | 117.0 |
| 10 ms (100 fps; the highest cap) | 39.06 | 630 ms | 119.7 |
| 8 ms (125 fps) | 41.27 | 664 ms | 126.2 |
| 7 ms (142.9 fps) | 36.51 | 588 ms | 111.7 |
| 6 ms (166.7 fps) | 37.53 | 600 ms | 114.0 |
| 5 ms (200 fps) | 39.06 | 625 ms | 118.8 |
| 4 ms (250 fps) | 41.63 | 668 ms | 126.9 |
| 3 ms (333 fps) | 46.43 | 747 ms | 141.9 |
| 2 ms (500 fps) | 31.30 | 500 ms | 95.0 |
| 1 ms (1000 fps) | 31.27 | 500 ms | 95.0 |
| uncapped 60 Hz (16/17 ms, smoothed) | 38.13 | 617 ms | 117.2 |
| uncapped 144 Hz (7/6 ms) | 36.54 | 584 ms | 111.0 |
| uncapped 165 Hz (6 ms) | 37.47 | 600 ms | 114.0 |
| uncapped 240 Hz (4/5 ms) | 41.11 | 658 ms | 125.0 |
| uncapped 360 Hz (3/2 ms) | 43.15 | 692 ms | 131.5 |

(The continuous ideal is 39.0.) Ground movement, from rest with forward held: speed after 96 ms is 113-124 units/s
at 4-16 ms commands but 97 at 1-3 ms, which reach full speed (190) about 30 ms later; the stop from 190 takes 18 units
at 1 ms, 23-26 units at 3-16 ms and 27 at 2 ms. **Splitting the same time into more, shorter commands gives a
different result**: lower and shorter jumps above 400 fps, a higher one at 333 fps, slower acceleration below 4 ms.

## 4. Server and prediction

### 4.1 The server (PS4 server PDB; the Store build's listen server has the same functions, *unverified* in detail)

- The server frame is fixed at 50 ms (`SV_RunFrame`: `svs.time += 50`); snapshots go out from it.
- `SV_UserMove`: each packet's commands (1..32) in order. A command newer than the last one runs at once through
  `SV_ClientThink` → `ClientThink` → `ClientThink_real` → **`Pmove` on that one command**, while the client's think
  time this server frame (`cumulThinkTime`, reset every frame by `SV_BuildSnapshots`) is below `sv_cumulThinkTime`
  (100 ms, "Max client think per server 50 msec frame"). Otherwise it is queued in an 8-command ring that
  `SV_ProcessClientThinks` drains under the same budget; past 8 the oldest are dropped. A command older than or equal
  to the last one is ignored.
- `SV_ClientThink` ignores commands more than 20 s ahead of `svs.time`; `ClientThink_real` clamps `serverTime` to
  `level.time` and ignores commands under 1 ms.
- So **the server's physics is the client's command lengths**: the jump table above is what the server simulates. The
  budget is in milliseconds, so the command rate itself is not limited; nothing else checks it.

### 4.2 Client prediction (1402D2900, the Black Ops `CG_PredictPlayerState_Internal` lineage, *name unrecorded*)

- From the latest snapshot's player state it replays, with `Pmove`, every stored command from `cmdNumber - 127` to
  `cmdNumber` whose time is after the snapshot's `commandTime`, every frame. A prediction error (the snapshot's result
  against the earlier prediction, beyond 0.1 units) is decayed over `cg_errorDecay`-style time (DAT_143C12DD0).
- The client's and the server's splits are the same commands, so they agree; errors come from what the commands
  don't carry (other players, server-side events) and from dropped commands (2.2, 2.3).
- **Cost:** replays per frame ≈ (round trip + snapshot interval + 16 ms) / frame time: about 10 at 100 fps with 100 ms
  ping, about 150 at 1000 fps. Per second that is O(fps² · latency) `PmoveSingle` calls.
- **CMD_BACKUP limit:** only 128 commands can be replayed. At 1000 fps that is 128 ms: with a round trip near 100 ms
  the oldest needed command is already overwritten and the replay starts later than the snapshot, so the gap is
  simulated as one long step (*the visible effect unverified in game*). At 500 fps the window is 256 ms.

## 5. Frame-rate dependencies found

| # | VA | Where | Effect | Severity |
|---|---|---|---|---|
| 1 | 14054FE80, from 140273CF0 | `Sys_SnapVector` on the velocity at the end of every `PmoveSingle` | jump height 31-46 units and distance 95-142 by fps (3.4); acceleration and stopping too | **felt** (server-authoritative) |
| 2 | 140273A90 | `Pmove`: one step per command, no fixed step | makes #1 depend on the frame rate | **felt** (root cause) |
| 3 | 14030CDF0 + 140306C40 | one command per frame at `cl->serverTime`, which can repeat | the server drops commands with a repeated time, with their input (≥500 fps) | felt (rare) |
| 4 | 14030E710 | at most 32 commands a packet | above ~960 fps commands lost every packet; above ~480 fps no redundancy against packet loss | felt |
| 5 | 1402D2900 | prediction replays at most 128 commands, all of them every frame | at 1000 fps a 128 ms window (prediction from a stale start with ordinary ping); CPU cost O(fps² · latency) | visible / performance |
| 6 | 14030E370 | packet interval rounded up to whole frames | 20.8 packets/s at 62.5 fps vs 30.3 at 333+: up to ~15 ms more input delay to the server | felt (minor) |
| 7 | 140460400 | `minMsec = 1000 / com_maxfps` truncated; cap 100 (B0024); 1 ms minimum | only whole-ms frame rates; nothing above 1000 fps | visible (limit) |
| 8 | 140460400 | three-frame msec smoothing | command lengths rearranged, total kept | none |
| 9 | 14054FE20 | 1 ms clock | non-dividing refresh rates give mixed command lengths (144 Hz: 7/6 ms → 36.5-unit jumps) | felt (via #1) |
| 10 | 14030DAA0 | key fractions of `frame_msec`, times at `com_frameTime` | movement ramp quantized to frames | none / barely |
| 11 | 14030DC20 | mouse acceleration per `frame_msec`, `m_filter` over two frames | aim depends on fps when they are used | felt if enabled (default off) |
| 12 | 140260D30 | `Jump_ClampVelocity` only on step-ups | the 39-unit design height does not bound free jumps | felt (via #1) |
| 13 | 140316290 | `frame_msec` clamp turns only 0 into 1, not negative | none in practice (the clock doesn't go back) | none |

Findings worth a `records/bugs.tsv` entry (not added here): #1/#2 (logic, high: gameplay-visible, fps-dependent
jumps), #3 (logic, medium), #4 (limit, medium), #5 (limit/performance, medium), #6 (latency, low).

## 6. Recommendation for the enhanced build: fixed-length usercmds

The server can't be changed, and it simulates exactly the commands it gets. Movement stops depending on the frame
rate only if **the client sends commands of a fixed length, independent of the render rate**.

### 6.1 Which length

**5 ms (200 Hz).** The evidence:

- With gravity 800, 5 ms and 10 ms are the lengths at which gravity changes the speed by a whole number per step
  (4 and 8 units/s), so the snapping adds no bias to the vertical motion: the measured peak is 39.06 units at both,
  the designed jump height (39) and what the original game gives at its highest cap (`com_maxfps 100`, 10 ms). 8 ms
  (125 Hz) would reproduce CoD4's 125 fps jump (41.3, +6 %), not Ghosts' design. (Other gravities, set by script,
  are exact at multiples of other lengths; 5 ms is exact for every multiple of 200.)
- 5 ms halves the input quantization of 10 ms, still fits the network: 6-7 new commands per 33 ms packet, 13-14
  with the default duplication (limit 32; with `cl_maxpackets 15` 26-27, still under 32).
- Prediction: 128 commands cover 640 ms, more than any playable round trip. Replays per frame ≈ 30 at 100 ms ping,
  independent of the frame rate (the cost per rendered frame no longer grows with fps).
- Server: 200 `PmoveSingle` a second per player instead of 85-125, the same total simulated time; within
  `sv_cumulThinkTime` (time-based) and the 8-command queue.
- 10 ms is the conservative alternative: identical physics to `com_maxfps 100` players, half the server cost, but
  5 ms more average input delay and server-side aim sampling at 100 Hz.

### 6.2 Generating the commands

In the enhanced `CL_CreateNewCommands` (14030BB00), keep `lastCmdTime` (the last command's `serverTime`):

```
target = cl->serverTime                               // as CL_SetCGameTime computed it this frame
if (target - lastCmdTime > 500 || target < lastCmdTime - 500)
    lastCmdTime = target - CMD_MSEC                   // (re)anchor after a time reset or a long stall
n = 0
while (lastCmdTime + CMD_MSEC <= target && n < 20)    // at most 100 ms of commands in one frame
{
    lastCmdTime += CMD_MSEC
    build and store a command with serverTime = lastCmdTime
    ++n
}
```

- Command times are strictly increasing and every command is exactly 5 ms, so none is dropped by the server
  (fixes #3) and every Pmove step is 5 ms on the client and the server (fixes #1, #2, #9 for the player's own
  movement). The leftover, `target - lastCmdTime` (0..4 ms), carries over to the next frame; the ±1 ms delta nudges
  only move where the grid falls relative to the render time.
- **Mouse and view angles every frame, commands when due.** Move `CL_MouseMove`'s update of `clViewangles` (and the
  keyboard/gamepad turning) out of the per-command path so it runs once per rendered frame, with the frame's real
  length (as now). A command takes the view angles of the frame that creates it; at 500 fps that is the freshest
  frame, at 60 fps several commands of one frame carry the same angles (optionally interpolated between the previous
  and current frame's angles, which gives the server a smoother aim at low frame rates).
- **Keys per command time, not per frame.** `CL_KeyState` measures against `com_frameTime`/`frame_msec`: a second call
  in the same frame returns 0. Compute the key movement once per command-creating frame over the time its commands
  cover (`frame_msec` := the time since the previous command-creating frame) and give that `forwardmove`/`rightmove`
  to all of the frame's commands. Buttons pressed and released between two commands stay latched until the next
  command reads them (`CL_KeyActiveOrPressed`), as now.
- `CL_FinishMove` takes `serverTime` from the loop instead of `cl->serverTime`. `cgameExtraButtons` go into the first
  command of the frame (it clears them).
- `CL_SendCmd`/`CL_WritePacket` are unchanged; with 200 Hz commands the 32-command limit is never reached (fixes #4)
  and duplicates always fit. Optionally raise the default `cl_maxpackets` to 60-100 for less input delay (#6).
- `com_maxfps`: allow up to 1000 (B0024). Keep the 1 ms minimum frame; going beyond 1000 fps needs a sub-millisecond
  frame clock, which nothing in this path requires once commands are fixed.

### 6.3 Keeping the view smooth: predict to the render time

`CG_PredictPlayerState` replays the stored (fixed) commands as now; its result is the state at `lastCmdTime`, up to
5 ms behind the render time `cl->serverTime`. For the view only:

1. Copy the predicted player state and run one more `Pmove` with a temporary command of `serverTime = target`
   (length = the leftover, 0..4 ms; skip at 0), built from the current frame's input and `clViewangles`.
2. Use that copy for the refdef (origin, view height, bob) and the view angles; never store it, send it, or let its
   events (footsteps, weapon fire) reach the cgame's event processing. The next frame recomputes from the real
   commands, so the partial step's own rounding never accumulates.
3. The view angles come straight from `clViewangles` (+ delta angles), every frame (with P0002's double precision).

The alternative, interpolating between the last two commands' states, needs no extra Pmove but adds up to 5 ms of
display latency to movement. The render time itself is whole milliseconds (`cl->serverTime`): above 1000 fps
frames repeat the same time; making it fractional belongs to the view/interpolation half.

### 6.4 Verifying it in the emulator

1. **Command generator:** drive the enhanced `CL_CreateNewCommands` with frame times for 60, 144, 165, 240, 360, 500
   and 1000 fps (including 7/6-ms and sub-command frames, delta nudges of ±1/−2 and a 600 ms reset): every command is
   5 ms after the previous one, times strictly increase, the total equals the elapsed server time minus a leftover
   below 5 ms, never more than 20 per frame.
2. **Movement invariance:** feed the generated commands to the original Store `Pmove` (the harness of 3.4): the jump
   peak (39.06), air time, distance and the ground acceleration/stop curves must be identical at every frame rate,
   and identical to the 5 ms row of 3.4. Compare also against 10 ms.
3. **Same commands on both sides:** encode the commands with the original `CL_WritePacket` and decode them with the
   original `MSG_ReadDeltaUsercmdKey` path, run the original `ClientThink_real`/`Pmove` sequence on them; the result
   must equal the client's prediction bit for bit, and no command may be skipped (`msec >= 1`, `serverTime <=
   level.time`).
4. **Keys:** a key held for 100 ms at each frame rate gives the same sum of `forwardmove · length` over the commands.
5. **View:** at 500 and 1000 fps the rendered origin from 6.3 advances every frame with the time, stays within one
   partial step's rounding of the canonical prediction, and the view angles equal `clViewangles` of the same frame.
6. On hardware, *unverified* until then: server-side behaviour on official-protocol servers (no rate limits beyond the
   above were found), and the CPU cost of 30 replays per frame at 1000 fps.

### 6.5 Implemented (enhanced/client_mp/cl_fixed_cmds.cpp)

The enhanced `CL_CreateNewCommands` (overrides Store 14030BB00) does 6.2:

- **The grid.** While `lastCmdTime + 5 <= cl.serverTime`, a command at `lastCmdTime += 5`, at most 20 a frame; the
  rest carries. The grid is (re)anchored at `cl.serverTime - 5` on the first frame and whenever `cl.serverTime` is
  more than 500 ms ahead of or behind it. *Deviation:* a smaller step back (the `CL_SetCGameTime` nudges of -1 and -2)
  does not re-anchor, it waits, so command times always increase; re-anchoring on every step back would repeat or
  lower command times, which the server drops (2.2).
- **Every frame**, commands or not: the keyboard turn (Black Ops' `CL_AdjustAngles`, inlined in the original and
  copied unchanged), `CL_MouseMove` (P0002's), `CL_GamepadMove` when a pad is active, and the 90° pitch limit, each
  with the frame's own `frame_msec`/frametime.
- **Only in a frame that makes commands:** `CL_CmdButtons` (so a tap latched since the last command is sent),
  `CL_KeyMove` with `frame_msec` set to the time since the previous command-making frame, `sub_1402A9900`, the spawn
  sight masks, remote control (`sub_14030DF50`) and location selection, and `CL_FinishMove`. All of the frame's
  commands carry the same input; `cgameExtraButtons` only the first (`CL_FinishMove` clears them).
- The default-command mode (`unk_143E96824` not 0 or 3) is the original's: one `MSG_SetDefaultUserCmd` command a
  frame; the grid restarts afterwards.
- Every frame it also builds the temporary view command `cl_viewCmd` (7.9), never stored or sent.

Since docs/cgame-frame.md 4.10 (the tick loop), the function is split: `CL_PrepareFrameInput` (everything above
that runs every frame, plus the buttons and moves into the frame's unfinished command when commands are due),
`CL_EmitTickCommand` (one command: `CL_FinishMove`, `serverTime = lastCmdTime += 5`) and `CL_BuildViewCmd` (the view
command with the aim angles the caller passes). The enhanced `CG_DrawActiveFrame` calls the first once a frame,
the second once in each of its 5 ms ticks (with that tick's kick handed over first: the kick at the previous tick,
not the previous frame's), and the third in the presentation with the kick stepped forward to the render time. The
enhanced `CL_CreateNewCommands` is the three in a row, for its other callers (`CL_CreateCmdsDuringConnection`).

Known simplifications, on frames that make no command: the mouse's movement in strafe mode or without mouse look
(which the original turns into that frame's `rightmove`/`forwardmove`) and aim assist's melee target are dropped; a
sprint tap the gamepad path sees is kept for the next command-making frame; `CG_HandleSpecialStateInput` runs on the
discarded command (from `CL_GamepadMove`).

**Key fractions.** `CL_KeyState` measures against `com_frameTime`, the commands cover grid time, which trails it by
the 0-4 ms leftover. A press or release therefore lands in the right command only to within one command: with forward
held for 100 ms, the sum of `forwardmove · 5` is 12,700 (= 127 · 100) at 60, 165, 240, 360 and 500 fps, 12,695 at
1000 fps and 12,065 (one command short) at 144 Hz. Making it exact would need key times against the grid instead of
the frame (an override of `CL_KeyState`); not done.

Tests (tests/enhanced/test_fixed_cmds.py, frame_sim.py drives whole frames in the emulator): 6.4 items 1, 2 and 4.
The generator at 60, 144, 165, 240, 360, 500 and 1000 fps (fractional frame periods on the integer clock), with
nudges of +1, -1, -2 ms and a 600 ms reset: every command 5 ms after the previous one, never more than 20 a frame,
the leftover after every frame below 5 ms; frames without a command still turn the view. Movement invariance: the
commands of 60, 144, 240 and 1000 fps fed to the Store build's own `Pmove` (noclip and ufo) give bit-identical states
at every command time. The full move (normal `pm_type`, which needs the world's traces) is not run: *unverified*, as
the 5 ms row of 3.4. Also: a 300 ms stall (20 a frame, then catching up), an attack tap between two command-making
frames is sent, the extra buttons only in the frame's first command, a key pressed 2 ms into a span gets 3/5 of
it, a step back of 300 ms waits and one of 2 s re-anchors, the arrow keys turn the view on every frame (the same
-14° over 100 ms at 60, 240 and 1000 fps), and the view command's angles and time. Mutation checks: 13 mutations of
the generator (step, cap, both re-anchor conditions, the key span, buttons, mouse and keyboard turning every frame,
the view command's angles and time, the extra buttons, the grid comparison, the span bookkeeping) all fail.

## 7. Prediction and the rendered view

Where the rendered view's angles and origin come from in the Store build, what the prediction does exactly, and what
the enhanced build must change to draw every frame at its own time when usercmds are fixed 5 ms steps (6.3). From the
disassembly; **(R)** marks the functions reconstructed for this section and passing their differential tests
(tests/differential/test_cg_predict.py, test_cg_draw.py), *measured* marks numbers from running the Store build's
own code in the emulator (scratchpad harness, not in the repo), *unverified* what was only read.

### 7.1 Summary

- **The predicted state is not rebuilt from the snapshot every frame.** `CG_SetNextSnap` (1402DBD40) copies each
  new snapshot's player state into `cg.predictedPlayerState` (20 times a second); between snapshots every frame
  continues from where the previous frame's prediction ended and runs only the commands that are new. Only while the
  player stands on an entity or a moving platform, or did within the last second, is the state copied from the
  snapshot every frame (1402D3230). Section 4.2 and row 5 of section 5 describe a full replay every frame; that holds
  only on platforms. The cost is one full replay per snapshot plus the new commands per frame:
  about 20 · (round trip + 25 ms) · fps + fps `PmoveSingle` calls a second, not O(fps² · latency) (3,500 a second at
  1000 fps and 100 ms instead of ~150,000). On a platform it is a full replay every frame.
- **The rendered angles are `cg.predictedPlayerState.viewangles`, and only `Pmove` writes them.** The mouse moves
  `cl.clViewangles` once per frame; `CL_FinishMove` adds the cgame's kick and ADS offset and rounds them to 16 bits
  into the command; `PmoveSingle` (inside `PM_UpdateViewAngles`) sets `viewangles = AngleNormalize180(short · 360 /
  65536 + delta_angles)` with the pitch held to ±85° by moving `delta_angles` (*measured*); `CG_CalcViewValues`
  copies them to the refdef and adds the view effects. Nothing on the first-person path reads `clViewangles`.
- **No new command, no new angles.** When the newest command's time is not after the predicted state's
  `commandTime`, the prediction runs no `Pmove` and puts back the angles the last frame ended with
  (`savedViewangles`). In the original that is a frame whose `cl.serverTime` repeated (2.2): the view does not turn
  that frame although the mouse moved. With 5 ms commands it would be four frames in five at 1000 fps.
- **The rendered origin is the predicted origin at the newest command's time**, which in the original is the
  frame's own `cl.serverTime` (= `cg.time`), plus the step smoothing and the decaying prediction error
  (`CG_CalcViewValues`), the view height and bob (`CG_OffsetFirstPersonView`).
- **The kick reaches the view one frame late**, through the next frame's command: the cgame's `kickAngles` are read
  only by `CG_DrawActive` (R), which hands them to the client for the next usercmd.
- **For the enhanced build:** run one extra `Pmove` on copies of the predicted state and of `cg_pmove`, with a
  temporary command from this frame's input and angles at `serverTime = cl.serverTime`; swap only the movement
  fields of the copy (origin, velocity, view angles, bob, view height, lean) into `cg.predictedPlayerState` at the
  end of `CG_PredictPlayerState` (R) and put the canonical values back in `CG_DrawActive` (R), with an idempotent
  restore in every reconstructed reader. Details and the list of things that must not leak in 7.6.

### 7.2 The client frame, in order

What touches the predicted state and the view in one `Com_Frame` (Store VAs; docs/frame.md and docs/fps-frame.md
give the rest):

| Step | Where | What |
|---|---|---|
| 1 | 14031B231 (in 14031B1F0, before the cgame frame) | `CG_SavePlayerState` (R, 1402D3170): the predicted state the last frame ended with: `commandTime`, origin, view angles, the trans state (`CG_ExtractTransPlayerState`, R) and, new in this build, `pe` (the predictable events) |
| 2 | `CG_DrawActiveFrame` (1402E7860) | `cg.oldTime = cg.time; cg.time = cl.serverTime` |
| 3 | `CG_ProcessSnapshots` (1402DB4C0) → `CG_SetNextSnap` (1402DBD40) | for each new snapshot: `memcpy(&cg.predictedPlayerState, &snap->ps, 0x3328)`; `CG_BuildItemList` (R) when the item list belongs to another client |
| 4 | 1402D3230 (1402E7A41) | `cg.predictFromTime = nextSnap->serverTime`; for `pm_type` 1 or 8 or `linkFlags & 4` `CG_InterpolatePlayerState(lc, 0)`, for a demo or `otherFlags & 0x2000` `CG_InterpolatePlayerState(lc, 1)` (the state is blended between the snapshots, nothing is predicted); otherwise, if the snapshot's ground entity is an entity (1..0x7FD) or the predicted state rides a platform, `cg.lastOnEntityTime = cg.time`, and while `cg.time - lastOnEntityTime < 1000` the snapshot's state is copied in again |
| 5 | `sub_1402D2410` (R, 1402E7DEE) | the early prediction, local client 0 only: `CG_PredictPlayerState_Internal(0, 1)`, then `pe` is put back from the saved copy |
| 6 | `CL_SyncGpu` → `R_SyncGpu` (1402E7DF5) | the frame wait |
| 7 | `CL_Input` (R, 1402E7E0C) | `IN_Frame`, `CL_CreateNewCommands`: the mouse into `clViewangles`, one command at `cl.serverTime` with `ANGLE2SHORT(clViewangles + cgameKickAngles)` |
| 8 | `CG_PredictPlayerState` (R, 1402E7E1C) | `CG_PredictPlayerState_Internal(lc, 0)` and what follows from the state (7.4) |
| 9 | `CG_TransitionPlayerState` (1402D0750, 1402E7EA7) | fires the predictable events between the saved `eventSequence` and the new one (1402B64C0), the unpredictable ones, the damage feedback |
| 10 | 1402E817B | `BG_KickAngles` (R) on `cg.frametime`: the new kick |
| 11 | 1402E819E | `CL_SendCmd` (R) |
| 12 | `CG_CalcViewValues` (1402EDDD0, 1402E836D) | the refdef from the predicted state (7.5) |
| 13 | `CG_AddViewWeapon` (1402F38B0, 1402E83B5) | the viewmodel from the predicted state |
| 14 | `CG_DrawActive` (R, 1402AB060, 1402E8929) | FOV sensitivity, `kickAngles + offsetAngles` and the weapons for the next command, `CL_RenderScene` |

So in the original the command created in step 7 has `serverTime = cl.serverTime = cg.time`, the prediction of
step 8 ends at that time, and the frame is drawn at it: command time, predicted time and render time are the same
integer millisecond.

### 7.3 CG_PredictPlayerState_Internal (R, 1402D2900)

`int CG_PredictPlayerState_Internal(LocalClientNum_t lc, int moverEarly)`, Black Ops' function of the same name with
moving platforms added. Called with `moverEarly` 1 by `sub_1402D2410` (before the frame's command) and 0 by
`CG_PredictPlayerState` (after it).

1. `current = CL_GetCurrentCmdNumber()` (R, 140305E50). Returns 0 at once for a demo (`cg.demoType`) or
   `otherFlags & 0x2000` (step 4 interpolates those).
2. **The platform.** `moverNum = ps.movingPlatformEntity` if it is 0x3A..0x7FD. Otherwise the cached
   `cg.platformContactEntity` (cg+0xB2750), or, when that is `ENTITYNUM_NONE`, the entity a box trace of the
   player's bounds in place hits with `allsolid` (140304650, mask 0x810011). If that entity has eType 6 or 14 and a
   number other than 0x7FF, it becomes `ps.movingPlatformEntity`, `otherFlags |= 0x1000000` unless mantling, and
   the move starts at `cg.snap->serverTime` instead of `cg.predictFromTime`.
3. `cg_pmove.ps = &cg.predictedPlayerState`. Only when `unk_143E96824 == 0` and `moverEarly == (lc == 0)` (so the
   early call for client 0, the late call for the others): `CG_AdjustPositionForMover` (1402B1F60) moves the origin
   with the platform from that start time to `cg.time`, and for a real platform `BG_UpdateAnglesMovingPlatform`
   turns the view (`delta_angles[1]`), the platform's angular velocity (`cg.platformAngularVelocity`, degrees per
   second, from the angle change over `cg.time - start`; not written when that is 0), the velocity and, mantling, the
   mantle start point are turned with it, and `sub_140178C50` passes the origin change on.
4. **Pmove set-up:** `handler = 0`, `tracemask` 0x2814011 below `pm_type` 7, else 0x810011, 0x800011 for
   `pm_type` 5; `viewChange = 0`, `contactEntity = ENTITYNUM_NONE`, `viewChangeTime = cg.stepViewStart`. Bounds,
   `oldcmd` and the rest of `cg_pmove` carry over from the last call.
5. `CL_GetUserCmd` (R, 1403065F0) of `current - 127` (it always succeeds) and of `current` (the newest,
   `latestCmd`).
6. **The replay**, if `ps.commandTime < latestCmd.serverTime`: for `cmdNum` from `current - 127` to `current`, the
   command into `cg_pmove.cmd`; it is used if `commandTime <= serverTime <= latestCmd.serverTime` and the command
   before it is still in the ring (so `current - 127` itself never is: 127 commands at most). A command at exactly
   `commandTime` is a zero-length `Pmove` (no `PmoveSingle`: nothing moves, the angles stay; only the torso and
   waist pitch are recomputed). For each:
   - **The prediction error**, when `ps.commandTime == cg.savedCommandTime` (the replay has reached the time the last
     frame ended at): the origin moved with the platform from `cg.time` back to `cg.oldTime`, against the saved
     origin. Unless the snapshot was a teleport (`cg.noPredictionError`, cg+0x10E832), if the difference is longer
     than 0.1 and the player is not on a platform: `predictedError = predictedError · max(0, (cg_errordecay - (time -
     predictedErrorTime)) / cg_errordecay) + (saved - new)` (zero first when `cg_errordecay` is 0) and
     `predictedErrorTime = cg.oldTime`. In the incremental case the comparison is with the state itself and the
     difference is 0; it can only be non-zero on the frame after a reset.
   - `Pmove(&cg_pmove)` (R).
   - **Item pickups** (Black Ops' `CG_TouchItemPrediction`, inlined), for `pm_type` 0 or 1: every item in
     `cg_itemEntities` whose announcement is not pending (`predictedPickupTime` 0 or before `cg.time`), that
     `BG_PlayerTouchesItem` and `BG_CanItemBeGrabbed` accept and that is a weapon type 5 (sub_140267140) or an
     equipped weapon whose ammo the player can take (sub_140267880): `predictedPickupTime = cg.time + 5000` and
     event 10 for it (sub_1402B8F80, predicted). This is the only event the prediction raises itself.
7. **No new command** (`ps.commandTime >= latestCmd.serverTime`): unless `cg.viewTeleported`, `ps.viewangles =
   cg.savedViewangles`.
8. If `cg.platformContactEntity` is still `ENTITYNUM_NONE`, it takes `cg_pmove.contactEntity`. Nothing else in the
   build ever resets it (*unverified*: only a reset of the whole `cg_s` would).
9. Returns 1.

**What it writes:** `cg.predictedPlayerState` (all of it, through `Pmove`; the view angles on the no-command path;
`movingPlatformEntity`, `otherFlags`, origin, velocity, mantle point and `delta_angles` through the platform),
`cg.predictedError`, `cg.predictedErrorTime`, `cg.platformAngularVelocity`, `cg.platformContactEntity`, `cg_pmove`
(`ps`, `cmd`, `oldcmd`, `tracemask`, `handler`, `viewChange`, `viewChangeTime`, `contactEntity` and what `Pmove`
writes: `fTorsoPitch`, `fWaistPitch`, `groundSurfaceType`, ...), the items' `predictedPickupTime`. Events: the
predictable events `Pmove` adds to `ps.pe` (footsteps, jumps, landings, weapon fire, through
`BG_AddPredictableEventToPlayerstate`) are not fired here but by step 9, which compares with the trans state saved
at step 1.

**The early call and `pe`.** After a reset (step 3 or 4) the early call replays every unacknowledged command, and
`Pmove` adds their events to `pe` again. `sub_1402D2410` then copies the saved `pe` back, so step 9 fires only the
events of the commands the late call adds (the frame's new command). Events of the server's newer snapshot state in
`pe` are overwritten by this too (*unverified* whether that loses any).

### 7.4 CG_PredictPlayerState (R, 1402D2480)

In order: `cg.lastAimSpreadScale = ps.aimSpreadScale`; `CG_PredictPlayerState_Internal(lc, 0)` (its result is not
used); `CL_SetStance(lc, STAND)` when `pm_flags & 0x400`; no cursor hint clears the hint string (0) and entity
(0x7FF); **the step smoothing** (moved here from Black Ops' internal function): when `cg_pmove.viewChange` is
non-zero, its time differs from `cg.stepViewStart`, the view didn't jump, `pm_type` is 0, 2 or 3 and
`|viewChange| >= cg_viewZSmoothingMin`, the remaining part of the previous step (`(1 - (viewChangeTime -
stepViewStart) / (cg_viewZSmoothingTime · 1000)) · stepViewChange`, only inside that time) plus the new change,
clamped to ±`cg_viewZSmoothingMax`, becomes `cg.stepViewChange` from `cg.stepViewStart = viewChangeTime` (a command
time); otherwise `stepViewChange` is zeroed once `cg.time - stepViewStart` passes the smoothing time. Then the
player's own entity: pose origin = predicted origin, pose angles from its `apos` trajectory at `cg.time` (not while
mantling), `sub_1402CC6E0` for a melee charge target; the vehicle entity's state from `ps.vehicleState`
(sub_140277AB0) when it is valid and of eType 12 or 14; `sub_140306FD0` (R) hands the vehicle state to the client;
`BG_PlayerStateToEntityState` and `BG_PlayerToEntity_ProcessEvents` into the player entity's `nextState`, copied to
`currentState`, then the torso and waist pitch from `cg_pmove`; `cg.predictedPlayerEntity`; `cg.groundSurfaceType`;
`CL_SetUserCmdOrigin` (R, 140306F60: origin, velocity, bob cycle, movement direction and `cl.serverTime` for the next
usercmd); sub_1402EF5D0 (the platform's motion since the saved origin); `cg.predictedWeaponPosFrac`; 1405BAAA0
(remote camera transitions, which may set `clViewangles`); 1402D0AC0.

### 7.5 Where the rendered view comes from

**Angles.** `CG_CalcViewValues` (1402EDDD0) starts the frame's `refdefViewAngles` (cg+0xA9A90) from
`cg.predictedPlayerState.viewangles` and changes them, in first person: the linked-entity adjustment (1402E75C0,
only with `eFlags & 0x200000`), the roll relative to the link angles for `pm_type` 1 or 8 or `linkFlags & 4`
(140264DB0), `CG_OffsetFirstPersonView` (1402E9930: `BG_CalculateViewMovement_Angles`, the bob, the damage kick, the
lean roll), a pitch offset `atan(x · refdef.tanHalfFovY)` in degrees outside `pm_type` 5 and 6 (x a dvar or
140266F80), and the camera shake (`CG_ShakeCamera`, R).
The angles in the predicted state come only from `PmoveSingle`, i.e. from a command:

1. `CL_MouseMove` (R) adds the frame's mouse movement to `cl.clViewangles` (once a frame, docs/input.md).
2. `CL_FinishMove` (R): `cmd.angles[i] = (unsigned short)floor((clViewangles[i] + cgameKickAngles[i]) · 182.04445 +
   0.5)`: 16 bits, a step of 0.0055°. `cgameKickAngles` are the cgame's `kickAngles + offsetAngles` as
   `CG_DrawActive` (R) set them at the end of the previous frame.
3. `PmoveSingle` → `PM_UpdateViewAngles` (PS4 PDB names; the Store build's measured): `viewangles[i] =
   AngleNormalize180(cmd.angles[i] · 360/65536 + delta_angles[i])`; for normal and noclip movement the pitch is held
   to ±85° by changing `delta_angles[0]` (*measured*: 86° gives 85 with `delta_angles[0] = -1.001`); prone, ladder,
   mantle, turret, vehicle and remote control clamp differently (PS4 PDB, *unverified* in the Store build). A
   zero-length `Pmove` leaves the angles as they are (*measured*).
4. On the no-new-command path the angles are `savedViewangles` (7.3 step 7).

`delta_angles` enter only in step 3 (the server and the platform code move them). `clViewangles` are read directly
only off the first-person path: the free third-person spectator camera (1402E9C10 with `otherFlags & 0x2000`) and
the remote-camera transitions (1405B6B40, 1405BAAA0). **So when no new command is predicted, the original does not
show the new `clViewangles`.** The view kick is never added to the view directly: it rides on the next command, so
the view shows it one frame late and quantized.

**Origin.** `refdef.vieworg = ps.origin`, then (`CG_CalcViewValues`): the step smoothing `z -= (1 - min(1, (cg.time
- stepViewStart) / (int)(cg_viewZSmoothingTime · 1000))) · stepViewChange` for `pm_type` 0, 2 and 3 when the view
didn't jump and `cg.time >= stepViewStart`; the prediction error `+= f · predictedError` with `f = (cg_errordecay - (cg.time -
predictedErrorTime)) / cg_errordecay` while 0 < f < 1 (else `predictedErrorTime = 0`), not on a platform and not for
`pm_type` 1 or 8; then `CG_OffsetFirstPersonView`: `+ viewHeightCurrent`, the bob (from `bobCycle` and the
velocity), the landing dip, at least 8 above the origin. All in integer milliseconds of `cg.time`; the origin itself
is the state at the newest command time.

### 7.6 What a view at the render time needs

With fixed 5 ms commands (6.2) the newest command time `lastCmdTime` trails the render time `cl.serverTime` by
`L = 0..4` ms, and most frames create no command.

**(a) The current frame's angles without a new command.** Today they would stay at `savedViewangles` (7.5). They
have to come from a `Pmove` with a command that carries this frame's angles, so that the same clamps apply as to the
next real command (the ±85° pitch, prone, ladder, mantle, turret and vehicle limits all live in
`PM_UpdateViewAngles`).

**(b) The origin at the render time.** One `Pmove` of `L` ms on a copy.

Both come from one extra step. The functions to override, all reconstructed now:

1. **`CL_CreateNewCommands` (R, 14030BB00)**, besides the 5 ms grid of 6.2: every frame, build the command a command
   at `cl.serverTime` would be (the frame's keys, buttons, weapon and `CL_FinishMove`'s angles from this frame's
   `clViewangles + cgameKickAngles`) into an enhanced static `s_viewCmd`, without storing or sending it, and note
   whether the frame stored a real command.
2. **`CG_PredictPlayerState` (R, 1402D2480)**: first restore (point 4), then the faithful body. Then, when the
   prediction ran (`_Internal` returned 1, `pm_type` neither 1 nor 8, no `linkFlags & 4`, not a demo):
   - `viewPs = cg.predictedPlayerState` (0x3328 bytes), `viewPm = cg_pmove[lc]` (0x178), `viewPm.ps = &viewPs`,
     `viewPm.oldcmd = ` the newest real command, `viewPm.cmd = s_viewCmd` with `serverTime = cl.serverTime`;
   - if `L > 0`: save the local client's character info (the 0x5D8 bytes `BG_AnimUpdatePlayerStateConditions`
     writes through the bgame thread-local, at `+0x10 + clientNum · 0x5D8`), `Pmove(&viewPm)`, restore it;
   - if `L == 0` and the frame stored no command (only when `cl.serverTime` repeated), compute
     `viewPs.viewangles[i] = AngleNormalize180(s_viewCmd.angles[i] · 360/65536 + viewPs.delta_angles[i])`, the pitch
     clamped to ±85° (the normal-movement rule; keep the old angles in the special movement states);
   - if `viewPm.viewChange != 0` (the partial step went up or down a step), `viewPs.origin[2] -= viewPm.viewChange`,
     so the view starts the smoothing the canonical step will start a frame later instead of jumping;
   - save the canonical values of the swapped fields in an enhanced static and set a flag, then write the copy's
     `origin`, `velocity`, `viewangles`, `bobCycle`, `viewHeightCurrent` and `leanf` (0x2A8) into
     `cg.predictedPlayerState`. Nothing else: not `commandTime`, `delta_angles`, `pm_flags`, `pe`, the weapon state,
     `groundEntityNum` or the platform fields.
3. **`CG_DrawActive` (R, 1402AB060)**: the faithful body, then restore. The swap is live exactly from the end of the
   prediction to the end of the cgame frame: `CG_TransitionPlayerState` (reads only `pe`, `damageEvent`,
   `otherFlags`: not swapped), `BG_KickAngles` (weapon fields), `CL_SendCmd`, `CG_CalcViewValues`, `CG_AddViewWeapon`
   (the gun follows the view, as it should) and the scene.
4. **The restore** (idempotent, a no-op without the flag) also at the start of `CG_SavePlayerState` (R),
   `sub_1402D2410` (R) and `CG_PredictPlayerState_Internal` (R), in case `CG_DrawActiveFrame` returned before
   `CG_DrawActive`. `CG_SetNextSnap`'s and 1402D3230's copies come after step 1 of 7.2, so they always see the
   restored state.

**What must not leak, and how the above keeps it out:**

| Effect of the temporary step | Kept out by |
|---|---|
| its events (footsteps, jump, landing, weapon fire) | they are added to `viewPs.pe`, which is never swapped in; `CG_TransitionPlayerState` and `BG_PlayerToEntity_ProcessEvents` see the canonical `pe` |
| weapon state (firing, reload, ADS fraction) | not swapped |
| the prediction error and its decay | `_Internal` is not run for it; `CG_SavePlayerState` saves the restored origin |
| the step smoothing state | `cg.stepViewStart`/`stepViewChange` are written only by `CG_PredictPlayerState` from the canonical `cg_pmove`; the temporary `viewChange` only lowers the view |
| `cg_pmove`'s carried fields (`oldcmd`, `viewChange`, `contactEntity`, `fTorsoPitch`, `groundSurfaceType`, `remoteTurretFireTime`, `lastUpdateCMDServerTime`) | the step uses a copy |
| `cg.platformContactEntity`, the platform's angular velocity | set only in `_Internal` |
| item pickup events | the item loop is in `_Internal` |
| the player entity, `CL_SetUserCmdOrigin`, the vehicle state, the stance | done by the faithful body before the swap, from the canonical state |
| the character info's animation conditions (global, per client) | saved and restored around the step |
| `delta_angles` (the pitch clamp moves them) | not swapped |
| global memory written by `Pmove` itself | *measured* for noclip and ufo steps of 1 to 66 ms on private buffers: one thread-local word (TLS +0xD0, 0 → 1, *probably a one-time initialisation guard*); normal movement *unverified* |

**Verifying it in the emulator** (the harness of tests/differential with the enhanced DLL):

1. Drive `CL_CreateNewCommands` and `CG_PredictPlayerState` frame by frame at 1, 2, 2.5 (alternating 2 and 3) and
   4.17 ms frames with a real noclip `Pmove` (the two animation-condition calls faked, as in test_cg_predict.py):
   the swapped origin must advance every frame by the frame's own time (at constant speed, `speed · Δt` within one
   ms of rounding), the view angles must equal `AngleNormalize180(round16(clViewangles + kick) + delta_angles)` of
   the same frame, and the canonical state must be bit-identical to a run without the extra step.
2. Run `CG_DrawActive` and check that `cg.predictedPlayerState` is byte-identical to the canonical state after it;
   call `CG_SavePlayerState` without `CG_DrawActive` in between and check the same.
3. Give `viewPs` a step that fires a weapon event (a `Pmove` fake that adds an event to `pe`): `pe` and
   `cg.predictedPlayerState.pe_eventSequence` must be unchanged after the frame.
4. The faithful functions are unchanged when the extra step is off: the differential tests of 7.8 run on the
   enhanced DLL with the feature disabled.
5. On hardware, *unverified* until then: the viewmodel and the local player's shadow at the swapped position, normal
   movement's global writes, and the cost (one `PmoveSingle` per frame).

### 7.7 Frame-rate dependencies found

| # | VA | Where | Effect | Severity |
|---|---|---|---|---|
| 14 | 1402D2900 | no command newer than the predicted state: the view angles stay at the last frame's | the view does not turn on frames whose `cl.serverTime` repeated (≥ 500 fps, about once per corrected snapshot); with fixed-length commands it would be most frames | visible (rare in the original) |
| 15 | 1402AB060, 14030CDF0 | the kick reaches the view only through the next command | kick one frame late and quantized to 16 bits: 16 ms at 60 fps, 1 ms at 1000 fps | cosmetic |
| 16 | 1402D3230 | on an entity or a platform (and for 1 s after) the predicted state is reset to the snapshot every frame | full replay every frame there: O(fps · window) per frame, the row-5 cost, but only on platforms | performance |
| 17 | 1402D2900 | 127-command window (the oldest of the 128 is never predicted, it has no predecessor) | at 1000 fps a round trip past ~100 ms makes the replay start late with a long first step (row 5) | visible (row 5) |
| 18 | 1402D2900 | the platform's angular velocity from the integer `cg.time - start`, written only when that is non-zero | with a repeated `cg.time` the previous value stays | none / barely |
| 19 | 1402D2480, 1402EDDD0 | step smoothing and error decay | by command times and `cg.time` in ms: frame-rate independent | none |
| 20 | 1402D2900 | `cg.platformContactEntity` is set once and never reset | a platform once touched is checked every frame afterwards (not frame-rate dependent) | none (*unverified* effect) |
| 21 | 1402EDDD0 | the error decay drops the whole error when `f >= 1`, i.e. when `cg.time == predictedErrorTime` (= the `cg.oldTime` of the frame that found it) | a prediction error found in a frame whose `cg.time` did not advance (repeated `cl.serverTime`, ≥ 500 fps) is applied as a snap instead of decaying over `cg_errordecay` | visible (rare) |

Row 5 of section 5 (the cost) is corrected by 7.1: the full replay happens once per snapshot, not every frame,
except on platforms (row 16).

### 7.8 Tests

`CG_PredictPlayerState_Internal`: of 2,560 inputs about 2,490 are usable (the others fault in the original itself:
local client 1, whose `cg_pmove` overlaps `cg_itemEntities`, and some real-`Pmove` states), among them 28 that run
the original `Pmove` for real (noclip and ufo, up to eight commands). Covered: the demo and `otherFlags 0x2000`
exits, all three platform sources, both arguments for clients 0 and 1, the replay with repeated, older-than-the-ring
and newer command times, about 150 prediction-error updates (decay 0, 100, negative, NaN), about 130 item pickup
events, the no-command path and the contact cache. 53 mutations of 14 functions (comparisons, constants, dropped
statements and conditions, swapped operands and arguments) all fail their tests, except two equivalent ones:
`sinceStart > 0` for `>= 0` in the step smoothing (`sinceStart` 0 means `viewChangeTime == stepViewStart`, which
skips the branch) and the operand order of one kick-angle addition in `CG_DrawActive` (it only differs for two NaNs
with different payloads, which the emulator does not distinguish, *unverified*). Three first attempts survived and
got better inputs: the 0.1 error threshold (offsets of 0.1 and 0.15), the `pm_type < 7` tracemask (`pm_type` 6) and
`stepRemaining > 0` (a step that exactly cancels the rest of the previous one).

### 7.9 Implemented (enhanced/cgame_mp/cg_view_step.cpp)

7.6 as designed, with these details:

- **The temporary command** (`cl_viewCmd`, built by the enhanced `CL_CreateNewCommands` every frame): the newest
  stored command's buttons and moves, `serverTime = cl.serverTime`, angles `(unsigned short)floor((clViewangles +
  cgameKickAngles) · 182.04445 + 0.5)` as `CL_FinishMove` rounds them. *Deviation from 7.6 point 1:* not a fresh
  command from this frame's keys (building one would consume the key and button state on frames that make no
  command); the newest command's input is what the keys did up to the last command-making frame, at most one frame
  old.
- **`CG_PredictPlayerState`** (overrides 1402D2480): restore, the faithful body (copied unchanged), then the step,
  for local client 0 when the prediction ran, the switch `cg_renderTimeView` is on, no demo, no `otherFlags 0x2000`,
  `pm_type` not 1 or 8, no `linkFlags & 4`, and the leftover `L = cl.serverTime - commandTime` is 0..20 ms:
  - `L > 0`: copies of the 0x3328-byte state and of `cg_pmove`, `cmd = cl_viewCmd`, `oldcmd` = the newest command,
    `viewChange = 0`; the local client's character info (0x5D8 bytes at the pointer in the thread's TLS block + 0x10,
    indexed by `clientNum`) saved, `Pmove`, restored; a step (`viewChange`) is subtracted from the copy's height.
  - `L == 0` and the view command's angles differ from the newest command's (only when `cl.serverTime` repeated):
    `viewangles = AngleNormalize180(short · 360/65536 + delta_angles)`, pitch held to ±85°, in the plain movement
    states (`pm_type` 0, 2, 3, not prone, mantling, on a ladder, remote controlling, on a turret or in a vehicle);
    otherwise the angles stay.
  - The canonical `origin`, `velocity`, `viewangles`, `bobCycle`, `viewHeightCurrent` and `leanf` are kept and the
    copy's written in.
- **`CG_DrawActive`** (1402AB060): the faithful body, then the restore. **`CG_SavePlayerState`** (1402D3170) and
  **`sub_1402D2410`**: the restore, then the faithful body. `CG_PredictPlayerState_Internal` is not overridden: both
  of its callers restore first.
- `cg_renderTimeView` is a plain global of the enhanced DLL (1 = on), not a dvar yet: the tests switch it off for
  the reference runs.
- All copies are explicit loops (`Enh_Copy`): no `memcpy`/`memset` calls in the new objects (checked in the
  objects' disassembly).

Tests (tests/enhanced/test_view_step.py): whole frames (`CG_SavePlayerState`, `CL_CreateNewCommands`,
`CG_PredictPlayerState`, `CG_DrawActive`) with the faithful prediction running the Store build's own `Pmove` (noclip,
forward held, the view turning every frame) at 1 ms, 2.5 ms (2/3) and 4.17 ms (4, 4, 4, 4, 4, 5) frames:

1. the drawn origin advances every frame by the frame's own time at the drawn velocity (within 3%), where the
   reference run (the step off, as the original draws) stands still on frames without a command;
2. the drawn angles equal `AngleNormalize180(round16(clViewangles + cgameKickAngles) · 360/65536 + delta_angles)` of
   the same frame, also on a frame whose `cl.serverTime` repeated (no command, no time to move);
3. after `CG_DrawActive` the whole predicted state is bit-identical to the reference run's, every frame, and so is
   what `CG_SavePlayerState` saves; `CG_SavePlayerState` without `CG_DrawActive` restores too;
4. with a `Pmove` fake that adds a predictable event only for the temporary command, `pe` and the saved `pe` stay the
   reference's;
5. the character info the animation conditions write is the reference's although the partial steps ran them;
6. a step up of 8 units in the partial move does not raise the drawn height.

Mutation checks: 10 mutations of the view step (each restore, the character info restore, the step compensation,
swapping the whole state, the zero-leftover angles, the command, its time, the switch, the copy's `ps`) all fail.

Not done: the viewmodel, sound and the local player's shadow at the swapped position on hardware, and the normal
(trace-using) movement's own global writes, *unverified* (7.6).

Since docs/cgame-frame.md 4.10 (the tick loop), the step is the presentation's own-view step (`CG_PresentOwnView`,
called by the enhanced `CG_DrawActiveFrame` after its ticks): the ticks predict the canonical state with the faithful
`CG_PredictPlayerState`, `CG_TransitionPlayerState` and the events run in the ticks on the canonical state, the view
command's angles carry the kick stepped forward to the render time, and the one restore point is the end of
`CG_DrawActiveFrame` (`CG_DrawActive` is no longer overridden; `CG_SavePlayerState`, the early prediction, every tick
and `CG_PresentOwnView` restore first as safety nets). The tests above now run through the tick loop
(frame_sim.TickGame).

Since docs/cgame-frame.md 4.9 (stage 1), the step's time is the own view's presentation time, not
`cl.serverTime`. The partial Pmove runs to `floor(T_r)`, where T_r is the fractional, slewed render time, and the
copy's origin moves on by `velocity · (T_r − floor(T_r))`. Only in `PM_STEP_FORWARD`: any other mode of
`cg_presentMode[PC_OWN_VIEW]` draws the canonical prediction.

## Reconstructed for this document

| Function | VA | File | Test |
|---|---|---|---|
| `CL_FinishMove` | 14030CDF0 | client_mp/cl_input.cpp | test_cl_input_finishmove.py |
| `Sys_Milliseconds`, `Sys_SnapVector` | 14054FE20, 14054FE80 (PS4 140245C70, 140245CD0) | win32/win_shared.cpp | test_win_shared.py |
| `Jump_*` (10 functions) | 140260900..140261190 (PS4 too) | bgame/bg_jump.cpp | test_bg_jump.py |
| `Pmove` | 140273A90 (PS4 140082BE0) | bgame/bg_pmove.cpp | test_bg_pmove.py |
| `Com_InitDvars` | 140460F80 | qcommon/common.cpp | test_common_dvars.py |
| `CG_PredictPlayerState_Internal`, `CG_PredictPlayerState`, `sub_1402D2410` | 1402D2900, 1402D2480, 1402D2410 | cgame_mp/cg_predict_mp.cpp | test_cg_predict.py |
| `CG_SavePlayerState`, `CG_ClearSavedPlayerState`, `CG_BuildItemList`, `CG_ClearItemList`, `CG_ItemListLocalClientNum` | 1402D3170, 1402D2380, 1402D2300, 1402D2370, 1402D2400 | cgame_mp/cg_predict_mp.cpp | test_cg_predict.py |
| `CG_ClearTransPlayerState`, `CG_ExtractTransPlayerState` | 1402CFF20, 1402CFF40 | cgame_mp/cg_predict_mp.cpp (Black Ops: cgame/cg_playerstate.cpp) | test_cg_predict.py |
| `CL_GetCurrentCmdNumber`, `CL_GetUserCmd`, `CL_SetUserCmdOrigin`, `sub_140306FD0` | 140305E50, 1403065F0, 140306F60, 140306FD0 | client_mp/cl_cgame_mp.cpp | test_cg_predict.py |
| `CG_DrawActive` | 1402AB060 | cgame_mp/cg_draw_mp.cpp | test_cg_draw.py |
| `CL_SetFOVSensitivityScale`, `CL_SetUserCmdAimValues`, `CL_SetUserCmdWeapons`, `CL_SetExtraButtons` | 140306E80, 140306F30, 140307110, 140306E70 | client_mp/cl_cgame_mp.cpp | test_cg_draw.py |
