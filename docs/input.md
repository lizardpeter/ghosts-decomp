# Input: keys, gamepad, mouse

Where the input code lives, what is reconstructed, and how the mouse reaches the view angles.

## Files

| file | what | reconstructed from |
|---|---|---|
| `client/cl_keys.cpp` | key names, bindings (`bind`, `unbind`, `bind_swap`), key catchers; `CL_KeyEvent`, `CL_CharEvent` | PS4 server (its binding half), Store build (the key events) |
| `client/cl_gamepad.cpp` | axis bindings (`bindaxis`), gamepad button events, menu scroll repeat | PS4 server |
| `client_mp/cl_input.cpp` | kbutton handlers; the mouse: `CL_MouseEvent`, `CL_GetMouseMovement`, sensitivity, `CL_MouseMove` | PS4 server (buttons), Store build (mouse) |
| `win32/win_input.cpp` | reading the mouse from Windows, cursor show/clip/recentre, `IN_Frame` | Store build |
| `win32/win_main.cpp` | the event queue (`Sys_QueEvent`, `Sys_GetEvent`), the message pumps | Store build, PS4 server names |
| `qcommon/common.cpp` | `Com_EventLoop` | Store build, PS4 server and Black Ops |

The servers keep only what a dedicated server needs, so the mouse code exists only in the client builds. Its
function names, the file name and the order of the functions come from three places, recorded per function in
`records/names.tsv`:

- **Black Ops' server PDB** (black-ops-1-decomp, `CoDMPServer`): Treyarch's server kept the client code, and its
  `win32/win_input.cpp` and `client_mp/cl_input_mp.cpp` are the same code a generation earlier, with names,
  prototypes and line numbers. IW6's functions follow them closely.
- **The PS4 server PDB** confirms the file: it has `IN_Shutdown` (`win32/win_input.cpp:637`) and the file statics
  `s_wmv`, `window_center_x`, `window_center_y`, `in_appactive`, the same names as Black Ops.
- **iw6-mod's `symbols.hpp`** names `IN_MouseMove`, `IN_RecenterMouse`, `CL_MouseEvent` and `s_wmv` in the Steam
  build, whose code is the same as the Store build's.

A function whose name is unknown is called `sub_<Store address>`.

## The Store build's layout differs from the server PDB

The Store build (and the 2018 Steam build) is a later revision than the 2014 servers:

- `clSnapshot_s` is 0x100 bytes larger (in `playerState_s`), so every `clientActive_t` field after `snap` is 0x100
  further on: `mouseDx` at 0x3534, `cgameFOVSensitivityScale` at 0x3568, `clViewangles` at 0x3610.
- `clientActive_t` has three floats after `clViewangles` that the server doesn't: the view change `CL_MouseMove`
  made this frame (`mouseViewDelta`, name unknown).
- `clientStatic_t` is the same up to `vidConfig` (0x180).

`include/client_mp/client_mp.h` spells out the Store layout and checks the offsets with `static_assert`.

## The mouse path

Once per client frame:

1. `IN_Frame` (win32/win_input.cpp) activates the mouse if the window has focus, then `IN_MouseMove`:
   `GetCursorPos`, in fullscreen clamp to the window (`IN_ClampMouseMove`, which also `ClipCursor`s), subtract the
   last position, scale the position to render pixels, call `CL_MouseEvent(x, y, dx, dy)`, and if it returns 1,
   put the cursor back in the window centre (`IN_RecenterMouse`).
2. `CL_MouseEvent` gives the position to a menu if one has the mouse; otherwise it adds `dx`, `dy` to
   `cl->mouseDx/Dy[mouseIndex]`. Windowed while loading, the movement is dropped.
3. `CL_CreateCmd` calls `CL_MouseMove`, which takes the movement out (`sub_14030D4A0`: `CL_GetMouseMovement` plus
   scaling) and turns it into degrees:

   ```
   speed   = sqrt(dx*dx + dy*dy) / frame_msec          counts per millisecond
   scale   = (speed * cl_mouseAccel + sensitivity) * cl->cgameFOVSensitivityScale
   yaw    -= dx * scale * m_yaw                        m_yaw = m_pitch = 0.022 by default
   pitch  += dy * scale * m_pitch
   ```

   capped per frame by the cgame's maximum yaw/pitch speed when it sets one, then aim assist
   (`AimAssist_UpdateMouseInput`) gets the angles and returns the final ones.

`cgameFOVSensitivityScale` is tan(fov/2)/tan(32.5°), measured against the default FOV 65 and applied to hip fire
too (docs/view.md, B0023). So with `cl_mouseAccel 0` at `cg_fov 65`, one count turns the view by
`sensitivity * 0.022` degrees. MW2019-style "1.5 at 3200 DPI, about 29 cm per 360" is 0.0099 degrees per count:
Ghosts `sensitivity 0.45` at `cg_fov 65`, 0.456 at 64.37 (MW2019's FOV 80), and 0.342 at 80.

Known problems, for the enhanced build: the movement is the system cursor's, after Windows' pointer speed and
acceleration (B0010); in fullscreen one frame can't move further than the cursor can before hitting the window edge
(B0011); and it is sampled once per frame. Raw input (`WM_INPUT` counts accumulated between frames) replaces
`IN_MouseMove`'s cursor arithmetic without touching the rest of the path. The community clients do this by
hooking `IN_MouseMove`'s call site (iw6-mod `raw_mouse.cpp`, GPL; not used here).

## Where cl_input.cpp stands

Reconstructed and matching the Store build:

- the mouse path above, and the key-button plumbing: `IN_KeyDown`, `IN_KeyUp`, `CL_KeyState`, `CL_UpdateCmdButton`,
  `CL_KeyActiveOrPressed`, `CL_ClearKeys`, `CL_SetStance`, `IN_IsTalkKeyHeld`, `CL_IsGamepadEnabled`, the tap
  handlers `CL_UseReload`/`CL_SpecNext`/`CL_SpecPrev`/`CL_ToggleSpec`;
- building a command: `CL_CreateCmd` (with Black Ops' `CL_AdjustAngles` inlined), `CL_CmdButtons`, `CL_KeyMove`
  (stance hold and stance bits inlined), `CL_GamepadMove`, the remote-control input path (`sub_14030DF50`) and
  `CG_HandleLocationSelectionInput`;
- sending: `CL_CreateNewCommands`, `CL_CreateCmdsDuringConnection`, `CL_Input`, `CL_SendCmd` (with
  `CL_ReadyToSendPacket` inlined) and `CL_WritePacket`.

Still to do: `CL_ExecBinding` (14030BC00, the 4 KB jump table from bindings to button handlers; an empty stub in the
server build), `CL_FinishMove` (14030CDF0), and the small getters 14030EE20 and 1404633E0 (the frame time
`CL_CreateCmd` passes to `CL_MouseMove` and `CL_GamepadMove`).

Shared code doesn't always match the Store build either: the Store build computes `vectoyaw` (and probably the other
`atan2` users in com_math.cpp) in double where the server uses float `atan2f`. Those need Store-specific versions;
their Store tests fail, unclaimed, until then.

## Testing

The Store build's functions are tested against the Store exe (`tests/differential/run.py --build
iw6mp64_MSStore_ship`). `tests/differential/win32.py` models the Win32 calls (foreground window, cursor, window and
client rectangles, the cursor display count) and logs them, so the reconstruction has to make the same calls with
the same arguments. Functions the Store build inlines everywhere (`IN_MouseMove`, `IN_ClampMouseMove`,
`IN_ActivateMouse` inside `IN_Frame`, `IN_DeactivateMouse`, `IN_IsForegroundWindow`) are verified through their
callers.

## The key path

How a key press, a mouse button or a typed character gets from Windows to the game in the Store build, and what each
step does immediately. From the Store build's disassembly; names and evidence in `records/names.tsv`. **(R)** marks
functions reconstructed and passing their differential tests (tests/differential/test_win_main.py,
test_common.py, test_cl_keys_events.py); everything else was read, not run.

### The event queue (win32/win_main.cpp)

- `eventQue` (149D5F260) is a ring of 256 `sysEvent_t`, 0x20 bytes each: `evPortIndex` (+0, never written in the
  Store build, so 0), `evTime` (+4), `evType` (+8), `evValue` (+0xC), `evValue2` (+0x10), `evPtrLength` (+0x14),
  `evPtr` (+0x18). `eventHead` (149D61260) is the next slot to fill, `eventTail` (149D61264) the next to take; slot =
  counter & 0xFF. The layout and names are the PS4 server's.
- Types: `SE_NONE` 0, `SE_KEY` 1 (value = key number, value2 = down), `SE_CHAR` 2 (value = the character),
  `SE_CONSOLE` 3 (evPtr = a line of text). There are no packet events: packets are read by `Com_EventLoop` directly.
- Everything runs under `CRITSECT_SYS_EVENT_QUEUE` (0x11). A pump holds it while it dispatches, so the window
  procedure's `Sys_QueEvent` enters it recursively.
- **`Sys_QueEvent` (R, 14054E400)** `(time, type, value, value2, ptrLength, ptr)`: time 0 means `Sys_Milliseconds()`.
  A full queue (head - tail >= 256) silently drops the oldest event and frees its `evPtr`.
- **`Sys_GetEvent` (R, 14054DB80)**: returns the event at the tail if there is one, *without pumping*. Only when the
  queue is empty does it pump: `PeekMessageA(&msg, NULL, 0, 0, PM_NOREMOVE)` / `GetMessageA(&msg, NULL, 0, 0)`
  (`Com_Quit_f` on WM_QUIT) / `g_wv.sysMsgTime = msg.time` / `TranslateMessage` / `DispatchMessageA`, for every
  message of the thread, unfiltered. Then a line from the dedicated console window (`Sys_ConsoleInput`, 1405506B0)
  becomes an `SE_CONSOLE` event (`Com_AllocEvent` = malloc; the copy uses destsize = length, so the line's last
  character is dropped, as in the PS4 server). Then it returns the next event, or `SE_NONE` stamped with the time.
- **`Sys_LoadingKeepAlive` (R, 14054E280)**: the same pump loop under the same critical section, then
  `R_CheckLostDevice`. It runs from every main-thread wait (`R_ProcessWorkerCmdsWithTimeout`, so also from
  `R_SyncGpu`'s back-end wait and com_maxfps sleep, `Sys_FrontEndSleep`, loading) and from 11 other places, one of them
  `RB_SwapBuffers` on the render thread (a thread's pump only sees its own windows' messages; that the game window belongs to the main thread is *unverified*).
  docs/frame.md says it "only queues": that is true of keys, characters and buttons, but the window procedure does
  everything else it does at once, including the WM_USER present and `Key_ClearStates` (below).
- **`Sys_ShutdownEvents` (R, 14054E860)** frees every queued event's text (from `Sys_Quit`).

### Com_EventLoop (R, 140460130; qcommon/common.cpp)

Called at 1404605F5 (top of `Com_Frame`'s body, before the com_maxfps budget), at 140460948 (after `SV_Frame` and
sub_140316290, before `CL_Frame` and `SCR_UpdateScreen`), and once from 140463320 after `Com_Init` / an error.

1. Drains the queue in order, one `Sys_GetEvent` at a time:
   - `SE_KEY` → `CL_KeyEvent(0, key, down, evTime)`;
   - `SE_CHAR` → `CL_CharEvent(0, ch)`;
   - `SE_CONSOLE` → `Cbuf_AddText(0, text)`, `free(text)`, `Cbuf_AddText(0, "\n")` (deferred to `Cbuf_Execute`);
   - other types → `Com_Error(ERR_FATAL, "Com_EventLoop: bad event type %i")`.
2. On `SE_NONE` (Black Ops' `Com_ClientPacketEvent`, inlined): a 0x20000-byte `LargeLocal` buffer and `MSG_Init`,
   then every packet goes to `CL_PacketEvent(0, from, &msg, Sys_Milliseconds())` (140315F70), in this order:
   loopback (`NET_GetLoopPacket(NS_CLIENT1)`, 14046A0F0), deferred (`NET_GetDeferredClientPacket`, 14046A020, a
   16-entry queue other threads fill), and the network (`NET_GetClientPacket` = `Sys_GetPacket`) unless
   `sv_running`.

So within one `Com_EventLoop`, all queued input is applied before any packet of that call.

### The window procedure's input (MainWndProc, 140552660; win32/win_wndproc.cpp)

Not reconstructed (one 1862-byte function that also owns the fullscreen switch). Every message first calls
`SetThreadExecutionState(ES_DISPLAY_REQUIRED)`. Input:

| message | does |
|---|---|
| WM_KEYDOWN (0x100), WM_SYSKEYDOWN (0x104) | `MapKey(lParam, wParam)` (140552F00); if nonzero, `SE_KEY key, 1`; returns 0 (no DefWindowProc, so no Alt menu). WM_SYSKEYDOWN with VK_RETURN (Alt+Enter) returns 0 at once: there is no Alt+Enter toggle here. |
| WM_KEYUP (0x101), WM_SYSKEYUP (0x105) | `MapKey`; `SE_KEY key, 0`; returns 0 |
| WM_CHAR (0x102) | `SE_CHAR wParam`, then DefWindowProc. (TranslateMessage posts it after the WM_KEYDOWN.) |
| WM_MOUSEMOVE, WM_L/R/M/XBUTTONDOWN/UP (0x200-0x20C, not the double clicks) | `IN_MouseEvent(mstate)` from the MK_ flags (L 1, R 2, M 4, X1 8, X2 0x10): an `SE_KEY` K_MOUSE1+n for each button that changed since the last message; then DefWindowProc |
| WM_MOUSEWHEEL (0x20A), the registered MSWHEEL_ROLLMSG | `SE_KEY K_MWHEELUP` (delta > 0) or `K_MWHEELDOWN`, down and up back to back |

All events carry `g_wv.sysMsgTime`, the time of the last message the pump took (not of the message itself when
the window procedure is called directly by `SendMessage`). Repeats are not filtered here: Windows' auto-repeat
WM_KEYDOWNs become more `SE_KEY` down events, which `CL_KeyEvent` counts in `repeats`.

`MapKey` (140552F00): scan code 0x29 (the key left of 1) is always `~`. Otherwise `wParam` 1..0x91 is looked up in
a table [vk][extended] at 140BC79C0; numeric-keypad digits and the decimal key map to 0 (left to WM_CHAR) while a
menu or the console has the keys and the key is not extended. Unmapped keys fall back to
`MapVirtualKeyA(vk, MAPVK_VK_TO_CHAR)`, with characters above 0x7F translated to K_ASCII_* by a table at 140BC7AF0.

Everything else it does (what any pump can trigger):

- WM_CREATE: stores `g_wv.hWnd`, registers `r_autopriority` and MSWHEEL_ROLLMSG. WM_DESTROY clears `g_wv.hWnd`.
- WM_MOVE: fullscreen (`r_displayMode` 0) → `IN_ActivateMouse(0)`; windowed → `vid_xpos`/`vid_ypos`, `IN_Activate(1)`
  if active, and the monitor dvar (140632B70).
- WM_ACTIVATE (6) and WM_ACTIVATEAPP (0x1C): only `g_wv.activationStateChanged = 1`. The render thread's
  `RB_SwapBuffers` sees it and posts WM_USER.
- **WM_USER (0x400), posted by `RB_SwapBuffers`:** under the device mutex (14A381188) `GetFullscreenState`; with
  focus, `SetFullscreenState(TRUE)` if fullscreen was lost and `ShowWindow(SW_RESTORE)`; without, `SetFullscreenState
  (FALSE)` and `ShowWindow(SW_MINIMIZE)` (both only in fullscreen mode); **`Present(lParam, 0)` on the main thread**;
  then `g_wv.isMinimized`, `g_wv.hasFocus`, `activeApp`, **`Key_ClearStates(0)`** (every key that is down is released
  through `CL_GamepadButtonEvent` → `CL_KeyEvent(key, 0)` → the bindings' "-" handlers, immediately), `IN_Activate`,
  14054D000, and the low-level keyboard hook is removed.
- WM_SETFOCUS / WM_KILLFOCUS: process priority with `r_autopriority`. WM_CLOSE: starts the quit (14054E790).
  WM_DISPLAYCHANGE: re-places a window that fills the monitor, `IN_RecenterMouse`. WM_SYSCOMMAND SC_SCREENSAVE and
  WM_POWERBROADCAST queries are refused.
- No raw input (WM_INPUT is not handled; the enhanced build's raw input has its own thread and window).

### CL_KeyEvent (R, 14030F710) and CL_CharEvent (R, 14030F4B0; client/cl_keys.cpp)

`CL_KeyEvent(lc, key, down, time)`; `time` is not used. In order:

1. Alt down and K_F4 down → `PostQuitMessage(0)` (the WM_QUIT reaches the next pump → `Com_Quit_f`). Nothing else.
2. Key state: `keys[key].down = down`; a press increments `repeats` (and `anyKeyDown` on the first), a release
   zeroes `repeats` and decrements `anyKeyDown` (not below 0). An auto-repeat (repeats > 1) goes on only when the
   console or the chat line has the keys, or a menu has them and the key is an arrow or Page Up/Down; never for `` ` ``,
   `~`, Escape.
3. Location selection (keyCatchers & 8) and a press: Escape → `locSelInputState = CANCEL`, a key bound to +attack or
   +attack_akimbo_accessible → `CONFIRM`; the key goes no further. Otherwise `locSelInputState = NONE`.
4. Escape pressed: chat line (0x20) → `Message_Key`; no menu (0x10, 0x40) → by connection state: cinematic/logo →
   `CL_StopLogoOrCinematic`; connecting..primed → nothing; **CA_ACTIVE → `UI_SetActiveMenu(UIMENU_INGAME)`** (or
   MAIN); disconnected/loading → `UI_SetActiveMenu(sub_140527D90())`. With a menu: the LUI key event and
   `UI_KeyEvent(Escape)`. Escape goes no further.
5. **LUI sees every other key, in every state, unless the console has the keys** (`cls.uiStarted` and
   sub_140222E90, which is always true): `sub_140222ED0(lc, controller, key, down, keyCatchers)`. It runs Lua at
   once (events with "immediate" set on the LUI state at 143AF5CF0): key rebinding capture in the controls menu
   (`Key_SetBinding`), a "keybind" event with the key's command when a Lua handler listens for it,
   "mousedown"/"mouseup" for K_MOUSE1/2, and button events while an LUI menu has the keys (0x40). While 0x40 is set a
   press goes no further, except keys bound to +talk/-talk.
6. A release: if the binding is odd and below 0x55 (the "+" of a pair), `CL_ExecBinding(binding + 1, key,
   previous down)`, whoever has the keys; then `UI_KeyEvent(key, 0)` if a menu has them. Done.
7. A press: console (1) → dropped (nothing handles the console's keys in the Store build: no console toggle
   here); menu (0x10) → `UI_KeyEvent` unless the active menu is the scoreboard, or `cl_bypassMouseInput` lets
   K_MOUSE1-3 and keys the menu doesn't list (sub_140503AD0) through to the bindings; chat line (0x20) →
   `Message_Key`; else the binding: none, or disconnected → nothing; **with the gamepad enabled in the profile,
   keyboard bindings are ignored** except +/-talk and chatmodepublic/team; else `CL_ExecBinding(binding, key, 0)`.

`CL_CharEvent(lc, ch)`: ignores `` ` `` and `~` and the console; chat line → `Field_CharEvent` on
`playerKeys.chatField`; menu → `UI_KeyEvent(ch | K_CHAR_FLAG, 1)`; LUI menu (0x40) → sub_140221EC0. **In game,
with no catcher, it does nothing.**

Message_Key (140311190): edits the chat field; Enter sends `say`/`say_team` with `CL_AddReliableCommand`
(immediately into the reliable-command ring), then clears catcher 0x20.

### CL_ExecBinding (14030BC00; client_mp/cl_input.cpp)

`CL_ExecBinding(lc, binding, key, prevDown)`. A binding is an index into the Store build's `g_bindCommands`
(1409919F0 + 10 pointers; 101 entries, 0 = unbound). 1..0x54 are 42 "+"/"-" pairs, 0x55..0x64 single commands.

- Except for +talk/-talk (0x51/0x52), nothing happens unless the byte at 143E96822 and the pointer at
  `cgArray + 0x3390` (143C27310) are set (in game).
- Then, for every binding but 0: **sub_140311D60 `"n <binding>"` as a reliable command** (`CL_AddReliableCommand`
  inlined) while CA_ACTIVE, 143E96824 != 2, and (the int dvar at 146A7D6F8 is 0 or prevDown): how the server's
  `notifyOnPlayerCommand` learns about binds. Immediate, into the ring `CL_WritePacket` sends.
- Then a 0x60-case jump table. Every kbutton handler is `IN_KeyDown`/`IN_KeyUp(&playersKb[lc][kb], key,
  com_frameTime)`: **the button's down time is `com_frameTime`, not the event time.**

| bindings | command | effect |
|---|---|---|
| 1-4, 9-0xC, 0x23-0x24, 0x27-0x28, 0x2B-0x34, 0x37-0x48, 0x4D-0x4E, 0x51-0x52 | +/-attack, melee, breath_sprint, usereload, changezoom, attack_akimbo_accessible, sprint_zoom, forward, back, moveleft/right, left, right, lookup/down, strafe, holdbreath, activate, reload, prone, sprint, talk | kbutton state only (+melee and +melee_zoom/+melee_breath also tap KB_SPECTATE through `CL_ToggleSpec` when the profile's gamepad is off) |
| 0xD-0xE, 0x25-0x26, 0x4B-0x4C, 0x5F, 0x60 | +/-speed_throw, ads_akimbo_accessible, toggleads_throw, toggleads, leaveads | kbuttons and `clients[0].usingAds` (client state) |
| 0x1D-0x22, 0x35-0x36, 0x53-0x54, 0x5C-0x5E | +/-stance, gostand, melee_zoom, movedown, togglecrouch, toggleprone, goprone, gocrouch | kbuttons and the client's stance-hold globals (143E99F68..78), reading `CG_GetPredictedPlayerState` (no cgame writes) |
| 0x49-0x4A, 0x5B | +/-mlook, centerview | KB_MLOOK.active; -mlook without `cl_freelook` and centerview write the client's pitch delta through DataValidation (143E9A030) |
| 0x4F-0x50, 0x61-0x64 | +/-scores, vote yes/no, togglescores, skip | only the `"n <binding>"` command |
| **5, 7** | +frag, +smoke (presses) | kbutton and **1402F7F20: cgame offhand state** (`cgArray`) |
| **0xF-0x1C** | +/-actionslot 1-7 | **cgame calls 1402F2C50/1402F2E50**: weapon/killstreak selection in `cgArray`, LUI notifications |
| **0x56, 0x5A** | weapnext, weapprev | **cgame weapon cycling (1402F5B00)** |
| **0x55, 0x57** | togglemenu, pause | **LUI "toggle_pause" event: opens the pause menu at once** (14021C430) |
| **0x58, 0x59** | chatmodepublic/team | `Cbuf_AddText("chatmode...")` (deferred), or without chat privilege an **LUI popup** at once |

So the handlers that do more than set kbutton or client input state, and when they run: the cgame calls (frag,
smoke, action slots, weapnext/prev), the LUI calls (togglemenu, pause, the chat-privilege popup, and the LUI key event
of every key in step 5), the reliable commands (every binding in game, and the chat line), `PostQuitMessage`
(Alt+F4), the menus (Escape, `UI_KeyEvent`). Only the console text and chatmode are deferred to `Cbuf_Execute`.

### Dispatching keys after the frame wait (enhanced build; the answer for docs/frame.md section 5)

Today a key applied by the second `Com_EventLoop` waits through `SV_Frame`, the com_maxfps sleep and the back-end
wait in `R_SyncGpu`, and the frame-latency wait (P0004), while the mouse is read right after them. The rule below
moves the safe events to right after the wait without reordering anything. Implemented as described
(enhanced/client/cl_late_input.cpp, records/patches.tsv P0009), with one extra stop: Escape stops the drain released too
(its press always stays queued, so its release follows it). *Unverified* on hardware.

**Where.** In the enhanced `R_SyncGpu`, at its end (after the original's own waits and the com_maxfps sleep, so
after everything that blocks). That covers `CL_SyncGpu` in `CG_DrawActiveFrame` (in game), sub_140316290's call and
`CL_CreateCmdsDuringConnection`'s, with one hook; the state test below makes it a no-op outside the game. It is not
re-entered: no key handler calls `R_SyncGpu`, but guard it with a flag anyway.

**How to pump.** Call `Sys_LoadingKeepAlive()` once. `R_SyncGpu`'s wait loops already call it (through
`R_ProcessWorkerCmdsWithTimeout`), unfiltered, at this point of the frame, so one more call adds no new message
handling mid-frame: everything the window procedure can do (WM_USER present, `Key_ClearStates`) already happens
here in the original. A filtered `PeekMessage` (WM_KEYFIRST..WM_KEYLAST, then the mouse range) is worse: two ranges
reorder keys against buttons, PM_QS_INPUT leaves the WM_CHARs `TranslateMessage` posts behind the next key, and a
filter lets input overtake a posted WM_USER, which an unfiltered pump retrieves first. Sent messages are dispatched by
any `PeekMessage` either way. The pump only queues input, so the dispatch is a drain of `eventQue`.

**Which events.** Under `CRITSECT_SYS_EVENT_QUEUE`, look at the event at `eventTail` without taking it; take it
(eventTail + 1), leave the critical section and dispatch it as `Com_EventLoop` does (`CL_KeyEvent(0, value,
value2, time)` / `CL_CharEvent(0, value)`) only if all of these hold when it is its turn, re-tested before every
event (a handler may have changed the state):

- `clientUIActives[0].keyCatchers == 0` and `connectionState == CA_ACTIVE` and `!Com_ErrorEntering()`, and the
  cgame is up (`cgArray + 0x3390` set), i.e. in game with no console, menu, LUI menu, chat line or location
  selection;
- it is `SE_CHAR` (a no-op in that state, taken only to keep order), or `SE_KEY` with:
  - not Escape, not K_F4 while Alt is down;
  - a press: `keys[key].binding` is a safe binding (below); a release: the binding is not odd below 0x55, or
    binding + 1 is safe. Auto-repeats (repeats already > 0) are safe: they stop in step 2;
  - safe bindings: 0, and every binding except 5, 7 (presses of +frag/+smoke; their releases 6, 8 are safe),
    0xF-0x1C (action slots), 0x55-0x5A (togglemenu, weapnext, pause, chatmode, weapprev). The gamepad case needs no
    rule: `CL_KeyEvent` drops those bindings itself.

**The stop rule.** At the first event that fails the test, stop: leave it and everything after it in the queue
(and anything that arrives later) for the next `Com_EventLoop`, which handles them in order as today. Never skip an
event to reach a later one. Console text (`SE_CONSOLE`) and any other type stop the drain too.

**What stays in Com_EventLoop.** Packets (all three sources; `CL_PacketEvent` processes snapshots and server
commands, not something to run inside the cgame frame), console text, every event while any key catcher is set or
outside CA_ACTIVE, Escape and Alt+F4, the unsafe bindings above, and everything queued behind one of these.

**What the rule accepts that still acts at once, and why that is acceptable:**

- the reliable `"n <binding>"` command and kbutton/usingAds/stance state: client-side input state, consumed by
  `CL_CreateCmd` and `CL_WritePacket` later in the same frame, which is what we want;
- the LUI key event (step 5) runs for every key and can run Lua "keybind"/"mousedown" handlers. The original runs it
  from the second `Com_EventLoop`, also outside LUI's own update; whether an in-game Lua handler touches cgame
  state is *unverified*. If one does, extend the rule: stop at keys whose binding has a "keybind" listener;
- `Key_ClearStates` from a WM_USER pumped here, as the original's wait loops already do.

The rule avoids the unsafe handlers by construction: cgame calls (offhands, action slots, weapon cycling) and
anything that opens a menu or a popup (Escape, togglemenu, pause, chatmode) stop the drain, so they run at the start
of the next frame exactly as now, in their original order relative to everything else.

Two side effects to know: kbutton down times are `com_frameTime`, which by then is this frame's, as for keys from
the second `Com_EventLoop` (no change in what `CL_KeyState` reports); and `"n <binding>"` commands are sent in this
frame's packet instead of the next one's.

## The enhanced build

The enhanced build (docs/variants.md) aims with raw input only, in MW2019 units (records/patches.tsv P0001, P0002).

- **Raw input:**
  - A thread of its own owns a message-only window registered for the mouse with RIDEV_INPUTSINK. It adds every
    relative report, in device counts, to 64-bit counters.
  - Each frame, IN_MouseMove gives CL_MouseEvent exactly the counts since the last frame.
  - Windows' pointer speed and acceleration don't apply, and there's no fullscreen clamp.
  - Absolute reports (tablets, remote desktop) are ignored.
  - Movement made while the game is in the background is dropped, and so is the frame focus comes back on.
  - The cursor is still read, but only to place the menus' cursor and keep the cursor in the window.
- **Sensitivity:**
  - One count turns the view by `m_sens` × 0.0066 degrees. `m_sens` defaults to 1.5 and is saved: about 28.9 cm
    per 360° at 3200 DPI.
  - The field of view doesn't change it, for hip fire or ADS. There is no `cl_mouseAccel`, `m_filter`, `m_yaw` or
    `m_pitch`.
  - `m_invertPitch` inverts vertical look.
- **Precision:**
  - The view angles are kept in double precision between frames, so the same movement split over more frames ends
    at the same angle.
  - They are re-read whenever something else moves the view (spawning, the cgame's pitch limits, aim assist).
  - The game's own turn-speed limits (vehicles, turrets) still apply.

