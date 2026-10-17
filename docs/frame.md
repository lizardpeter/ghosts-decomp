# The frame loop (Store build)

How one frame runs in the Microsoft Store build (`iw6mp64_MSStore_ship`). It covers three things:

- what the main thread does and in what order;
- how a frame is handed to the render thread and presented;
- how far ahead each stage may run, which decides the latency from a mouse movement to the screen.

The last section says where the enhanced build should wait on a frame-latency waitable swap chain.

Sources:

- Everything comes from the Store build's disassembly, with names from the PS4 server PDB (`iw6_ds_ps4`) and Black Ops' server PDB (lineage). Each name's evidence is in `records/names.tsv`.
- The functions marked **(R)** are reconstructed and pass their differential tests (`records/functions.tsv`).
- Statements marked *unverified* were read from the code but not exercised.

## The threads

| Thread | Runs | Identified by |
|---|---|---|
| Main | `Com_Frame` (140460380) in a loop: input, client, server, cgame, the renderer's front end | `threadId[0]` (146B623B0), `Sys_IsMainThread` (R) |
| Render | `RB_RenderThread` (140674A80): the back end, `Present` | `threadId[1]`, `Sys_IsRenderThread` (R) |
| Workers | `r_smp_worker_thread0..7`: worker commands (draw-surface generation, skinning, ...) | |

The main thread can also run worker commands itself. That happens whenever it waits in `R_ProcessWorkerCmdsWithTimeout` (14066C730). On the main thread that function also pumps window messages (`Sys_LoadingKeepAlive`, 14054E280) between waits.

## 1. The main thread's frame

### Com_Frame and its body

`Com_Frame` (140460380) does three things:

1. It sets a `setjmp` for `Com_Error`, then calls `DB_Update` (1403710E0) and the body (140460400), then `++com_frameNumber`.
2. After an error it runs `Com_ErrorCleanup` and related cleanup, including `R_ComErrorCleanup` and `R_PushRemoteScreenUpdate`.
3. Finally it calls 140463320 (see `IN_Frame` below).

The body, in order (VAs are the call sites):

1. Writes `config_mp.cfg` and `keys_mp.cfg` if they changed (`Com_WriteConfiguration`, inlined).
2. `Sys_UpdateHotkeyBlock` (1405531C0, 140460564) and `SetAnimCheck(com_animCheck)` (140479840).
3. **The frame budget.** It reads `com_maxfps` (146A7D160), which is registered with default 85, min 0, max 100.
   - A timescale below 0.1 lowers the budget.
   - `minMsec = 1000 / maxfps`, or 1 when `com_maxfps` is 0.
4. `Win_UpdateThreadLock` (140470640). Then `com_lastFrameIndex = n % 3`.
5. **`Com_EventLoop` (140460130, called at 1404605F5).** It drains `Sys_GetEvent` (14054DB80), which runs the window message pump (`PeekMessage`/`DispatchMessage`):
   - key and button events go to `CL_KeyEvent` (14030F710), then `CL_ExecBinding`, then the button handlers (`IN_KeyDown`/`IN_KeyUp`). Key state changes here, directly.
   - console text goes to `Cbuf_AddText`.
   - loopback and network packets go to `CL_PacketEvent` (140315F70).
6. **The com_maxfps limiter is computed here but not slept:**
   - `now = Sys_Milliseconds()` (1404605FA). `msec = max(0, now - com_frameTime)`.
   - `g_maxFpsWaitTime` (14A346A80) is set to `minMsec - msec`, or 0 when that is below 1. When it is set, `now += g_maxFpsWaitTime` and `msec = minMsec`.
   - `msec` is clamped to `com_maxFrameTime` while `sv_running`, otherwise to 5000. Then `com_frameTime = now`.
   - **The sleep itself happens later, in `R_SyncGpu`.**
7. Smooths `msec` over the last three frames, applies the timescale and `fixedtime`, and computes the frame time in seconds.
8. `Cbuf_Execute` (1404444C0), then the dvar and profile updates (140321B90).
9. `SV_Frame` (1404C4470), the listen server. Then 140193A70, 140194450 (online), and 1406570B0 (it stores `com_frameTime`).
10. **sub_140316290 (R)** (14046093C), with `msec` and the frame time:
    - `R_SyncGpu(NULL)` unless `cls.gpuSyncedPrevFrame`, and `IN_Frame()` unless `cls.inputUpdatedPrevFrame`. In game, the previous frame's cgame has already done both, so it skips them.
    - It then advances `cls.realtime`, `cls.frametime`, `cls.frametime_base` and `frame_msec`. `frame_msec` is `com_frameTime - old_com_frameTime`, clamped to 1..200.
    - It clears both flags.
11. 140377180(msec), then `Com_EventLoop` again (140460948), then `Cbuf_Execute`.
12. Demo and recorded-command playback (146A7D650...).
13. **`CL_Frame` (140313D80, 140460AA1)** handles connection state:
    - `CL_CreateCmdsDuringConnection` (R, 14030BA90): `CL_SyncGpu(NULL)` and a command while connected but not active.
    - `CL_SendCmd` (R) for connection states 5..9.
14. UI menu activation when disconnected, then sound (140316AD0).
15. **`SCR_UpdateScreen` (14031B6A0, 140460B3D)**, the frame drawn. See below.
16. 14031B600 (gamepad and rumble), then 1405F3970.

### SCR_UpdateScreen: the client frame that is drawn

`SCR_UpdateScreen` (14031B6A0) returns without drawing in these cases:

- it is already running (`updateScreenCalled`, 1442BE14C);
- the screen isn't initialized (1442BE148);
- `com_errorEntered`;
- before the client is active (connection state below `CA_ACTIVE`), it draws only every 16 ms (states up to 7) or 33 ms (loading, primed).

Otherwise it calls:

1. `R_BeginFrame` (14064C480). It increments `rg.frontEndFrameCount` (14A37CD6C).
2. `SCR_UpdateFrame` (14031B1F0). It sets `g_gpuFrameWait` to 1, or 0 for a cinematic (sub_1406321B0, R), then calls `CL_CGameRendering` (14031B150).
   - In game, that calls **`CG_DrawActiveFrame` (1402E7860)**. Its order:
     1. Snapshot processing and prediction state (1402D3230...).
     2. For local client 0: 1402D2410, then **`CL_SyncGpu(NULL)` (1402E7DF5)**, which sets `cls.gpuSyncedPrevFrame` and calls `R_SyncGpu`. Then 140376E30(1).
     3. **`R_ToggleSmpFrame` (14064D880, 1402E7E04).**
     4. **`CL_Input` (14030D610, 1402E7E0C).** For local client 0 it sets `cls.inputUpdatedPrevFrame` and calls `IN_Frame` (the mouse), then `CL_CreateNewCommands` (14030BB00). That calls `CL_CreateCmd`, which applies the mouse to `clViewangles` and builds the usercmd.
     5. 1402AA2A0, then 1402D2480. The latter runs the player prediction with the new command (*unverified*: its name and that it is the prediction).
     6. View and scene set-up (1402FC4F0, ...). The refdef and view angles for rendering are computed after the usercmd, from the predicted state.
     7. **`CL_SendCmd` (1402E819E)**: the command goes to the server in the same frame.
     8. The scene is submitted to worker commands. Worker command 0x17 (140655210) issues it to the back end:
        - `R_IssueRenderCommandsBegin(drawType)`, then `R_IssueRenderCommandsShadow`;
        - later `..Opaque` and `..Emissive`, all (R).
   - Without a cgame frame (menus, loading), `SCR_UpdateFrame` ends with `R_ToggleSmpFrame` and `R_IssueRenderCommandsBegin(3)`.
3. The 2D: 14031B3D0 (UI, HUD, console).
4. `R_EndFrame` (14064C610). It adds the end command.
5. **sub_14064D030 (R)**, the frame's end:
   - It sets `finishReady` and wakes the render thread if `R_IssueRenderCommandsBegin` could not (`g_databaseReady2` was 0).
   - It notes whether the skinned cache is over `r_SkinnedCacheThreshold`, then clears `frontEndDataOut`.
   - With the render thread in use, it gives the device back (`R_ReleaseThreadOwnership`, R).
   - Without the render thread, the main thread takes the device and runs the back end and the present itself (140673B60 → `RB_SwapBuffers`).

### Where IN_Frame runs (question 3)

| Call site | Function | When |
|---|---|---|
| 14030D631 | `CL_Input` (R) | In game, once per drawn frame, from `CG_DrawActiveFrame`, right after `R_SyncGpu` and `R_ToggleSmpFrame`, right before `CL_CreateNewCommands`. Only for local client 0, which sets `cls.inputUpdatedPrevFrame`. |
| 1403162F5 | sub_140316290 (R) | Once per `Com_Frame`, early (after `SV_Frame`, before `CL_Frame` and `SCR_UpdateScreen`), unless the previous frame's `CL_Input` read the mouse. This covers menus, loading, connecting, and frames where the cgame didn't draw. |
| 140463383 | 140463320 | After `Com_Init` and after recovering from a `Com_Error` (not per frame). It starts the client's hunk users, opens the main menu, calls `IN_Frame`, then flushes with `Com_EventLoop`. |

So `IN_Frame` runs exactly once per `Com_Frame`: either in the cgame frame, or else in the next frame's sub_140316290. The exception is a frame that switches into the cgame: sub_140316290 calls it, and then `CL_Input` calls it again. `R_SyncGpu` follows the same pattern through `cls.gpuSyncedPrevFrame`.

## 2. The render thread and the hand-off

### Buffers and ownership

- **Two `GfxBackEndData` buffers** (`s_backEndData`, 14A3AE200, 0x645080 bytes each) alternate.
- `R_ToggleSmpFrame` (R, 14064D880; Black Ops' name) does the following:
  1. It gives the device back (`R_ReleaseThreadOwnership`, inlined).
  2. It waits, running worker commands, until `sub_14046F5C0` (R) holds: `g_renderWaitCount <= 1`, so the render thread has at most one frame left to finish.
  3. It flips `s_smpFrame` (14A3AE18C) and points `frontEndDataOut` (14A3AE180) at the other buffer. It also advances
     `gfxBuf`'s skinned cache (3 buffers) and reactive motion (2) pools, sets `s_cmdList`, and clears the new frame's
     lists and issue state.
- **Ownership of the device** is shared through the events in `qcommon/threads.cpp` (R; PS4 PDB names, the statics at 146B625D0..146B625F8):
  - The main thread takes the device with `R_SyncRenderThread` (R, 14064D840). That calls `Sys_FrontEndSleep` (R): wait for `rendererRunningEvent`, reset `noThreadOwnershipEvent`, wake the render thread, then wait for `renderPausedEvent` while pumping messages.
  - The main thread gives the device back with `R_ReleaseThreadOwnership` (R, 14064D420): `Sys_ReleaseThreadOwnership` (R) sets `noThreadOwnershipEvent`.
  - The Store build adds a device critical section (0x2B, one past the server's `CRITSECT_COUNT`). sub_1406791E0 leaves it and sub_140676A10 enters it.
  - The main thread owns the device only to recover a lost device, to run the back end itself, and during loading.

### Issuing a frame

`R_IssueRenderCommandsBegin(drawType)` (R, 14064CF70; PS4 PDB) works as follows:

1. It sets `renderFromBackEnd = r_smp_backend && sys_smp_allowed && !r_glob.isRenderingRemoteUpdate`.
2. Unless the device is lost, it calls `R_RegisterRenderFrame` (R) for `drawType & 2`. That marks a frame that will be presented.
3. With the render thread in use and the database ready, it waits until the render thread has taken the previous buffer (`Sys_IsRendererReady` (R): `smpData == NULL`).
4. It then hands the buffer over: `Sys_WakeRenderer` (R) increments `g_renderWaitCount`, stores `smpData` and sets both backend events.

The back end starts on the scene while the front end is still generating it. The ready flags (`shadowReady`, `opaqueReady`, `emissiveReady`, `finishReady`, at `GfxBackEndData + 0x151454..0x151460`) tell it how far the scene is.

### The render thread

`RB_RenderThread` (140674A80) loops:

1. It waits for `backendEvent[1]`, either running worker commands (`r_smp_backend` and `sys_smp_allowed`) or with 10 ms waits.
2. If the main thread owns the device (sub_14046F320, R), it draws the frame it holds, then pauses:
   - it sets the pause state (sub_14046FB80, R);
   - waits for `noThreadOwnershipEvent` (sub_14046FFD0 or worker commands);
   - then runs again (sub_14046FB70, R).
3. While `r_glob.remoteScreenUpdateNesting` is set (loading), it calls `SCR_UpdateScreen` itself in a loop. **It presents loading screens without the main thread.**
4. `smpData = Sys_RendererSleep()` (R). If it got a frame, it calls 140674970.

140674970 runs one frame on the render thread:

1. `R_CheckLostDevice`.
2. The back end: the scene set-up for `drawType & 1` (`++backEndFrameCount`), then 140670A10 (executes the command lists), then 140670450.
3. **`Sys_RenderCompleted` (R): `g_renderWaitCount - 1`, `backendEvent[0]`.**
4. Worker commands.
5. If `finishReady` was set and `drawType & 2`:
   - sub_140632160 (R): `s_beginSmpFrameTime = now`;
   - **`RB_SwapBuffers` (140675C50, R): `Present(r_vsync clamped to 0..4, 0)`**;
   - sub_140632190 (R): `s_renderCompleteTime = now`.

`RB_SwapBuffers` is called by the render thread in normal play. It is called by the main thread only with `r_smp_backend 0`, `sys_smp_allowed 0`, or a remote update (140673B60 from sub_14064D030).

There are two more cases inside `RB_SwapBuffers`:

- When the swap chain's fullscreen state doesn't match `r_displayMode`, it posts `WM_USER` to the window instead. The window procedure then presents on the main thread, during its next message pump.
- `unk_14A37D568` replaces `Present` with 1406967E0.

### The swap counters and fences

- `g_frontEndSwapFrame` (14A3853A4) counts frames registered for presenting (`R_RegisterRenderFrame`, R).
- `g_gpuSubmitSwapFrame` counts frames presented (sub_14062EC80, after `Present`).
- `g_gpuSwapFrame` (14A346A84) is meant to count frames the GPU finished.
- **The shipped build never reads `g_gpuSwapFence[8]`.** Every check (sub_140632BC0, R, and the copies inlined in `R_RegisterRenderFrame`, sub_1406301A0, sub_140630210 and `R_SyncGpu`) moves `g_gpuSwapFrame` straight up to `g_gpuSubmitSwapFrame`. The fence query was compiled out; the PS4 server's loops are the same. So "finished on the GPU" means "`Present` returned".
- The one GPU wait left is in `RB_SwapBuffers`: before reusing an EVENT query from the 32-entry `dx.fencePool`, it spins until that query has signalled. The pool is shared with other users (14062CE00, sub_14067D210), so this bounds nothing in practice.
- **The GPU's queue is bounded only by DXGI:**
  - the original: maximum frame latency 3, the default;
  - the enhanced build: `SetMaximumFrameLatency(1)` (P0003).

### How far each stage may run ahead

| Who waits | Where | Condition | Result |
|---|---|---|---|
| Front end, start of a frame | `R_SyncGpu` (sub_140630210) | `g_renderWaitCount <= 1` and `g_frontEndSwapFrame - g_gpuSwapFrame <= g_gpuFrameWait` (1) | Before frame N+1's input, frame N-1 has returned from `Present`. Frame N may still be in the back end. |
| Front end, buffer flip | `R_ToggleSmpFrame` | `g_renderWaitCount <= 1` | The buffer about to be reused is free. |
| Front end, hand-off | `R_IssueRenderCommandsBegin` / sub_14064D030 | `smpData == NULL` | The render thread has taken the previous frame. |
| Front end, registering | `R_RegisterRenderFrame` (R) | sleeps while `g_frontEndSwapFrame - g_gpuSwapFrame >= 3` | A backstop. The conditions above keep it from triggering. |
| Back end | `Present` | DXGI's queue | Blocks when the maximum frame latency is reached. |

The front end can therefore be **one frame ahead of the back end**. The back end, through `Present`, can be up to **DXGI's maximum frame latency ahead of the GPU**: 3 in the original, 1 with P0003.

## 3. R_SyncGpu: the com_maxfps sleep and the back-end wait

`R_SyncGpu(WorkCallback)` (R, 1406327D0; Black Ops' name, r_init.cpp:3559) runs on the main thread once per client frame. It is the only place the com_maxfps budget is slept. Its steps:

1. **Lost device.** `R_CheckLostDevice` is inlined. A lost device is recovered and the function returns.
2. **Setup.** It records `start`, resets the catch-up times, and runs a pending sound update (140316AD0) if the back end is behind.
3. **The work callback.** If there is one, it gets 1 ms slices (an rdtsc deadline, `1 / msecPerRawTimerTick`) until the back end has caught up. In the Store build every caller passes `NULL`.
4. **Wait for the back end.** It runs worker commands until sub_140630210 holds, timing how long it waited while behind.
5. **The sleep length.** `wait = g_maxFpsWaitTime - (now - start - time spent behind)`, at least 0, and `g_maxFpsWaitTime` is cleared.
   - While a registered frame hasn't been presented, the wait is at least `min(12 ms, start - last present began) - (now - last present returned)`. This is a pacing term that keeps the front end in step with the presents.
6. **The sleep.** `g_waitRendererTime = now + wait`. It runs the sound update if one is due, then runs worker commands until that time (sub_1406302D0, R), pumping window messages.

The waiting is a loop of worker commands with 1 ms waits on `backendEvent[0]`. It is not a timer sleep, so it doesn't oversleep by a scheduler tick.

## 4. Latency: from a mouse movement to the screen (question 4)

In game, CPU-bound, with the render thread. Frame N on the main thread runs these stages in order:

1. `Com_EventLoop`: key and button state.
2. `SV_Frame`, `CL_Frame`, `CG_DrawActiveFrame` up to the sync.
3. **`R_SyncGpu`**: wait until frame N-2 has returned from `Present` and the render thread has at most frame N-1 left to finish, then sleep out com_maxfps.
4. **`IN_Frame` → `CL_CreateCmd`**: the mouse is read and the view angles and usercmd are made.
5. Prediction, view, scene generation. The back end of frame N starts as soon as `R_IssueRenderCommandsBegin` hands it over.
6. The 2D, `R_EndFrame`, sub_14064D030.

The render thread then finishes frame N's back end and calls `Present`. That returns once frame N is queued. The GPU renders it after the frames ahead of it, and the display shows it at the next refresh (vsync) or at once (tearing).

Whole frames of latency between reading the mouse and the frame that shows it:

1. **The front end's own frame:** from `IN_Frame` to the end of the frame. This is unavoidable, but short, because the mouse is read after the wait and late in the frame.
2. **The render thread: up to one more frame.** Frame N's back end overlaps the main thread's frame N+1. Frame N's `Present` comes as late as the end of the back end's work. The back end starts during frame N's scene generation, so this is usually less than a frame.
3. **DXGI's queue: up to 3 frames when GPU-bound** (the default maximum frame latency). The engine's own GPU check is compiled out (section 2), so nothing in the game prevents this. P0003's `SetMaximumFrameLatency(1)` cuts it to one.
4. **Scan-out:** waiting for the next refresh with vsync, half a refresh on average. Nothing is lost with tearing or VRR.
5. **Keys and buttons are older than the mouse.** They are read in `Com_EventLoop` at the start of `Com_Frame`, before `R_SyncGpu` sleeps. A key press therefore waits up to the com_maxfps sleep, plus the back-end wait, plus the rest of the frame longer than a mouse movement made at the same time. Messages that arrive during the waits are pumped (`Sys_LoadingKeepAlive`) but only queued; they are processed in the next frame's `Com_EventLoop`.

A GPU-bound frame in the original therefore runs input → front end → back end → up to 3 queued frames → scan-out, which is about 4 to 5 frames. With P0003 it is about 2 to 3 frames, *unverified* on hardware. CPU-bound with a free GPU queue, it is about 1 to 2 frames.

## 5. Where to wait on the frame-latency waitable object (question 5)

### Where

**In `R_SyncGpu` (1406327D0), on the main thread, right after the lost-device check and before `start = Sys_Milliseconds()`.**

- It is the one place that runs once per client frame on the thread that starts the frame's work. It runs before anything that frame reads input for:
  - in game: `CG_DrawActiveFrame` → `CL_SyncGpu` → `R_SyncGpu`, then `R_ToggleSmpFrame`, then `CL_Input` → `IN_Frame`, `CL_CreateNewCommands`;
  - in menus and loading: sub_140316290 → `R_SyncGpu(NULL)`, then `IN_Frame`;
  - while connecting: `CL_CreateCmdsDuringConnection` → `CL_SyncGpu`, then `CL_CreateNewCommands`.
- Being first in `R_SyncGpu`, the time spent in the wait counts against the com_maxfps budget (`now - start`). The existing back-end wait becomes a no-op in the steady state: once frame N-1 is on screen, it has been presented, so `g_renderWaitCount <= 1`. The same holds for the wait in `R_ToggleSmpFrame`.

### Pairing waits with presents

`R_SyncGpu` doesn't run exactly once per present. It can run twice in a frame that switches into the cgame, and it runs in frames that don't present: the throttled `SCR_UpdateScreen` before `CA_ACTIVE`, an error, or a lost device. Some presents also happen without it:

- loading screens drawn by the render thread (`remoteScreenUpdateNesting`);
- the window-procedure present after a fullscreen switch.

So pair by counting, not by call:

- Wait once for each frame registered for presenting since the last wait. In the steady state that is one wait, for frame N, at the start of frame N+1:

  ```
  while (s_waitedSwapFrame != g_frontEndSwapFrame - s_droppedSwapFrames)
  {
      WaitForSingleObjectEx(waitable, timeout, TRUE);
      ++s_waitedSwapFrame;
  }
  ```

- `g_frontEndSwapFrame` is incremented by `R_RegisterRenderFrame`, once per frame that will be presented, on whichever thread issues it. That includes the render thread's loading screens.
- Count a registered frame that is then not presented in `s_droppedSwapFrames`:
  - 140674970 skipped the swap because `finishReady` was 0 or `R_CheckLostDevice` failed;
  - `RB_SwapBuffers` took the `unk_14A37D568` path.
- With the default semaphore count of 1 and `SetMaximumFrameLatency(1)`, the wait for frame N returns once frame N-1 has started to be displayed. Frame N is then still in the back end or the GPU. Frame N+1's input is read with exactly one frame in flight, and the front-end/back-end overlap is kept.
  - Waiting instead for frame N's own retirement would serialize the main thread behind the render thread and the GPU. That is lowest latency, but it loses the overlap.
- Reset the counters, and use the new swap chain's waitable object, whenever the swap chain is recreated (`R_RecoverLostDevice`) or flushed (`R_FlushSwap`).
- After a long loading screen, many registered frames may be pending. They have all been displayed, so the waits return at once. Capping the loop at the latency plus one is simpler.
- The waitable object needs:
  - `DXGI_SWAP_CHAIN_FLAG_FRAME_LATENCY_WAITABLE_OBJECT` at creation;
  - `IDXGISwapChain2::SetMaximumFrameLatency` (`IDXGIDevice1::SetMaximumFrameLatency`, which P0003 uses, doesn't apply to such a swap chain);
  - one wait before the first frame.

### Frames with no present, and the timeout

- **Before `CA_ACTIVE`** (`SCR_UpdateScreen` throttled to 16 or 33 ms), errors, and `scr_initialized == 0`: no frame is registered, so with the counting above no wait happens.
- **Lost device:** `R_SyncGpu` returns before the wait, and `R_IssueRenderCommandsBegin` registers nothing.
- **Loading:** the render thread presents, the main thread is loading and doesn't call `R_SyncGpu`. The registered frames are paired afterwards.
- **Minimized or occluded:** the game has no minimized check (no `IsIconic`; *unverified* beyond searching for it). It keeps rendering and presenting. Whether a flip-model swap chain's waitable object is still signalled at a steady rate while minimized is *unverified*, so the timeout matters most here. A timeout of about two refresh periods, at least about 50 ms, keeps a missed signal from stalling the game.

### Input

- **The mouse can stay where it is.** `IN_Frame` already runs right after `R_SyncGpu` in every state:
  - in game, only `R_ToggleSmpFrame` lies between them, and its wait is satisfied once the waitable object has signalled;
  - with the enhanced build's raw input (P0001), `IN_MouseMove` takes all counts up to that moment.
  - One exception: while connecting, sub_140316290 reads the mouse before `CL_CreateCmdsDuringConnection`'s `R_SyncGpu`. It doesn't matter there.
- **Keys and mouse buttons should move.** They are applied in `Com_EventLoop` at the start of `Com_Frame`, before the wait. To make them as fresh as the mouse, the enhanced build should do this in `CG_DrawActiveFrame` after `CL_SyncGpu` and before `CL_Input` (and likewise in sub_140316290 after its `R_SyncGpu`):
  1. pump the window messages again;
  2. dispatch only the key and character events from `Sys_GetEvent` (`CL_KeyEvent` → `CL_ExecBinding` → the button handlers set the button state directly);
  3. leave packets and console text for the next `Com_EventLoop`.

  *Unverified:* that no key binding has an effect that is unsafe in the middle of the cgame frame. Bindings that run console commands only queue them (`Cbuf_AddText`), which is safe. Menu keys (`UI_KeyEvent`) are the case to check.
- **The alternative, rejected:** waiting at the top of `Com_Frame` before its first `Com_EventLoop` would make keys fresh without moving anything. But then the com_maxfps sleep and the back-end wait in `R_SyncGpu` would come after the input, adding up to a frame of latency whenever com_maxfps limits, and the listen server's frame would run in between.

### As implemented (P0004)

`enhanced/gfx_d3d/r_init.cpp` follows the placement above, with these choices:

- **Pairing by counted presents, not registered frames.** The render thread counts each successful `Present` on the
  waitable swap chain, and `R_SyncGpu` waits once for each present counted since its last wait. A frame that was
  registered but not presented then needs no bookkeeping: no override of 140674970 and no `s_droppedSwapFrames`.
  Loading screens are counted too, and their waits return at once.
  - With latency 1, the wait for present p returns once present p-1 is on screen.
  - In the steady state the back end has presented frame N by the start of frame N+1, so this is the same wait as
    above. If the back end is still on frame N, the wait is for frame N-2, and the original's own back-end wait in
    `R_SyncGpu` (`g_gpuFrameWait`) still holds the front end one frame ahead.
- **Signals no count pairs with.** Two cases:
  - a present made by the window procedure after a fullscreen switch (`RB_SwapBuffers` posts `WM_USER`);
  - a wait that timed out, whose signal may still come.

  Either would let one more frame queue up for good. The next frame therefore takes every pending signal (zero-timeout
  waits) instead of counting. That frame may wait up to one refresh longer, once.
- **Timeout:** two refresh periods from `vidConfig.displayFrequency`, at least 50 ms and at most 1 s. The wait is
  alertable, and a wait ended by an APC is repeated.
- **Reset:** a lost device's new swap chain gets its own object (the old handle is closed) and the counts start
  again. `R_FlushSwap` needs nothing, because presents are counted, not swap frames.
- **Start time:** the wait comes after `R_SyncGpu`'s first clock read, so time spent waiting counts against
  com_maxfps' frame time.
- **The rest of `R_SyncGpu` is the original,** compared call for call with the Store build on the differential
  test's inputs (tests/enhanced/test_frame_wait.py).
- **Fallbacks:** without `IDXGISwapChain2` there is no object and no wait. If the system refuses the flag, a flip-model
  swap chain is made without it, then the original swap chain.
- **Keys are not moved yet** (the re-pump described above). The mouse is read right after the wait.
- **Unverified on hardware:** that the waitable object behaves as documented on this game's swap chain (signal rate
  when minimized or occluded, a `DXGI_STATUS_OCCLUDED` present). Check with PresentMon: one frame queued, and the
  latency between the mouse and the photon.

## Findings for the enhanced build

These are not recorded in `records/bugs.tsv`.

- **The swap fences are written but never read** (`g_gpuSwapFence`, sub_14062EC80). The engine's "GPU frames behind" logic measures returns from `Present`, so it never limits the GPU queue. Only DXGI does, and it defaults to 3 frames. (performance; P0003 and the waitable object fix it)
- **Keys and buttons are read before the com_maxfps sleep and the back-end wait**, so they are up to a frame older than the mouse in the same frame. (latency)
- **`com_maxfps` is registered with a maximum of 100** (default 85). (limit, *unverified* in game)
- **`R_SyncGpu`'s pacing term is capped at 12 ms** (min(12, ...)). That is about one 83 Hz frame, an assumption about the refresh rate. (low)
- **`R_PopRemoteScreenUpdate` spins forever** if it is called off the main thread, or with the render thread not started, while the nesting is non-zero. Its loop doesn't change the nesting then. The PS4 server's version is the same. The current callers run on the main thread. (robustness, low)
- **`sub_140630210` only updates the catch-up end time while `s_gpuStartCatchUpTime > 0`, not `>= 0`.** A catch-up that starts at time 0 is never measured. (negligible)
