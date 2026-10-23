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
   resolution after `timeBeginPeriod(1)`).
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

## Reconstructed for this document

| Function | VA | File | Test |
|---|---|---|---|
| `CL_FinishMove` | 14030CDF0 | client_mp/cl_input.cpp | test_cl_input_finishmove.py |
| `Sys_Milliseconds`, `Sys_SnapVector` | 14054FE20, 14054FE80 (PS4 140245C70, 140245CD0) | win32/win_shared.cpp | test_win_shared.py |
| `Jump_*` (10 functions) | 140260900..140261190 (PS4 too) | bgame/bg_jump.cpp | test_bg_jump.py |
| `Pmove` | 140273A90 (PS4 140082BE0) | bgame/bg_pmove.cpp | test_bg_pmove.py |
| `Com_InitDvars` | 140460F80 | qcommon/common.cpp | test_common_dvars.py |
