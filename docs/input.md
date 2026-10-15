# Input: keys, gamepad, mouse

Where the input code lives, what is reconstructed, and how the mouse reaches the view angles.

## Files

| file | what | reconstructed from |
|---|---|---|
| `client/cl_keys.cpp` | key names, bindings (`bind`, `unbind`, `bind_swap`), key catchers | PS4 server (its binding half) |
| `client/cl_gamepad.cpp` | axis bindings (`bindaxis`), gamepad button events, menu scroll repeat | PS4 server |
| `client_mp/cl_input.cpp` | kbutton handlers; the mouse: `CL_MouseEvent`, `CL_GetMouseMovement`, sensitivity, `CL_MouseMove` | PS4 server (buttons), Store build (mouse) |
| `win32/win_input.cpp` | reading the mouse from Windows, cursor show/clip/recentre, `IN_Frame` | Store build |

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

So with `cl_mouseAccel 0` and no zoom, one count turns the view by `sensitivity * 0.022` degrees. MW2019-style
"1.5 at 3200 DPI, about 29 cm per 360" is 0.0099 degrees per count, which is Ghosts `sensitivity 0.45`.

Known problems, for the enhanced build: the movement is the system cursor's, after Windows' pointer speed and
acceleration (B0010); in fullscreen one frame can't move further than the cursor can before hitting the window edge
(B0011); and it is sampled once per frame. Raw input (`WM_INPUT` counts accumulated between frames) replaces
`IN_MouseMove`'s cursor arithmetic without touching the rest of the path. The community clients do this by
hooking `IN_MouseMove`'s call site (iw6-mod `raw_mouse.cpp`, GPL; not used here).

## Testing

The Store build's functions are tested against the Store exe (`tests/differential/run.py --build
iw6mp64_MSStore_ship`). `tests/differential/win32.py` models the Win32 calls (foreground window, cursor, window and
client rectangles, the cursor display count) and logs them, so the reconstruction has to make the same calls with
the same arguments. Functions the Store build inlines everywhere (`IN_MouseMove`, `IN_ClampMouseMove`,
`IN_ActivateMouse` inside `IN_Frame`, `IN_DeactivateMouse`, `IN_IsForegroundWindow`) are verified through their
callers.
