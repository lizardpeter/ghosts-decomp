# What the community clients patch

XLabs **iw6x-client** (2020, the user's fork lizardpeter/iw6x-client at a4d8d0a) and its maintained continuation
AlterWare **iw6-mod** (git.alterware.dev/alterware/iw6-mod at b54b3f5, Sep 2026) run the Steam exes and patch them
at runtime. Together they have about 600 patch sites (iw6-mod ~430, iw6x ~160, mostly the same ones). This page
sorts them by what each one means for the reconstruction. Both projects are GPL-3.0. Only facts are recorded
here (addresses, which function, what changes, why); no code is taken.

Addresses are **Steam MP** (`iw6mp64_ship`) unless marked SP. They are in the Steam build, not in our reference
server build. They get carried to the server build's names, and to the Store build, by matching
(docs/retail-builds.md). Function names are the clients' own; treat them as claims until a match confirms them.

## 1. Security fixes: the reconstruction should include these

| Steam MP address | Function (per iw6-mod) | Bug | Fix in iw6-mod | Vector |
|---|---|---|---|---|
| call at 140287C5C → 1405834B0 | `PlayerCards_SetCachedPlayerData` | indices not bounds-checked ("vulnerability") | reject unless `0 <= index1 < 18` and `0 <= index2 < 42` | server/peer → client |
| call at 14047A29A → 140472500 | `SV_ExecuteClientMessage` | negative `reliableSequence - reliableAcknowledge` makes the server hang | clamp `reliableAcknowledge` and drop the message | client → server |
| 1404D8A00 (detour) | `UI_ReplaceDirective` | unchecked source length into a fixed buffer | null/size checks, reject sources > 0x100 (MAX_HUDELEM_TEXT_LEN) | server-sent HUD text → client |
| call at 140399B0F | HudElem set-enum-string `sprintf` | `sprintf` into a 0x800 buffer | bounded `vsnprintf` + terminator | script/server data |
| calls at 140470A88, 140470F68 | `SV_AddBot`, `SV_AddTestClient` name `sprintf` | `sprintf` into a 0x400 buffer | bounded `vsnprintf` | server-side names |
| call at 14041D17E | `NET_DeferPacketToClient` `memmove` | packet copy without a length clamp ("buffer overflow") | clamp to 1262 bytes | any network peer |
| 1402C6AA4 | OOB `print` handler (connectionless packet) | any internet host can print text into the client ("for security reasons") | ignore the built-in handler; only accept `print` from the connected server | any internet host |
| 140815D4E | a routine registered with `atexit` | crash at exit | skip (short jump) | local |
| 1403A1A03 | last-seen-players update | null `g_entities` pointer crash when a server kicks for "invalid password" | null check | server → client |
| `cmd_lui_notify_server` | LUI notify from client to server | a non-host client can send notify 9 (`end_game`) and end the match | reject `end_game` from non-hosts | client → server |
| 1404F0D1A (inside the dvar set path; function not named by iw6-mod) | dvar flag enforcement | write-protected, read-only, cheat and replicated dvars can be set from external sources | enforce the flags for non-internal sources | console/server |
| call at 140287AED | `CG_SetClientDvarFromServer` | a server can override the client's saved (archive) dvars | refuse to change `DVAR_SAVED` dvars from the server | server → client |
| 14017E040..1401747D0 (HKS library openers) | Havok Script (LUI) VM | Lua `io`, `os`, `package`, `debug`, `serialize`, `loadfile`/`dofile`/`load`, `string.dump`, `os.execute` are reachable from UI scripts | don't open these libraries; stub the unsafe functions | malicious mod/fastfile/UI script → arbitrary code |

Asset pools (iw6-mod `asset_restrict`): the XANIMPARTS and ATTACHMENT pools are doubled. These are capacity
limits, not a security fix, but overflowing a fixed pool from loaded content is a crash vector.

## 2. Protections the clients remove: the reconstruction needs replacements

These checks depend on Activision's online services (Demonware, Steam auth), which the community servers don't
have. The clients turn them off. The reconstruction should replace them with working equivalents, not drop them:

- **Secure connection and identity:** "don't establish secure connection" (1402ECF1D, 1402ED02A, 1402ED34D,
  1402C4A1F); "disable xuid verification" (140154AA9/140154AC3, 140474584/1404745DB); "handle xuid without secure
  connection" (14041DFB0); Steam ID bit check (140585410, iw6-mod `auth`); "ignore unregistered connection"
  (140471AAC/140471AF0); "ignore dw handle" in `SV_PacketEvent`, `SV_FindClientByAddress`, `SV_DirectConnect`.
- **Integrity:** "don't send/read checksum" in the `dw_sendto` path (140501A63, 1405019CB); "ignore impure client"
  (140472671); "ignore configstring mismatch" (1402CCCC7); "Patch checksum check" (dedicated, 1404714D4).
- **Signed content:** "Allow loading of unsigned fastfiles" (`DB_LoadXFile`, 1402FBF23). Fastfiles are complex
  binary formats parsed with pointer fix-ups; the signature check is what keeps untrusted ones out.
- **Profanity filter** stubbed (1402F61B0), name changes in game blocked (140470300).

## 3. Arxan and DRM: not part of the game's source

iw6-mod `arxan.cpp`: spoofs anti-debug (NtQueryInformationProcess, NtClose, PEB BeingDebugged, debug registers),
NOPs five integrity-check sites inside the stub sections (14AE2B384, 14A31E98E, 14A920E10, 14A1A2425,
14AE07CEA), and re-routes `dwNetPump` (140558C20), `dwLobbyPump` (140591850) and `dwGetLogonStatus`
(140589480), whose Steam-build bodies are Arxan-wrapped. Also "Bypass Arxan function" (1404758C0, re-routed to
`SV_GameSendServerCommand`). These mark functions where the Steam build's code is not Treyarch/Infinity Ward's,
so they need care when matching. They should matter less if the Store build is Arxan-free.

## 4. Running the client exe as a dedicated server (iw6-mod/iw6x `dedicated.cpp`)

About 40 patches turn the client into a headless server: skip config load/save, disable self-registration,
renderer, sound, image and sound pak loading, `CL_CheckForResend`, host migration (14047BE70), UI gametype
loading. Useful as a map of client-only subsystems. Our reference *is* a dedicated server build, so we have the
real thing to compare against.

## 5. Online services replaced

Demonware is emulated (iw6-mod `demonware.cpp`, `game/demonware/`); `dw_sendto` (140501A00) is redirected to a raw
socket; connectionless (OOB) commands are intercepted at 1402C64CB (inside the client's OOB command dispatch) for the
clients' own protocol (server list, rcon, party). Steam is proxied (`steam_proxy`). For a full reconstruction,
the backend is the same problem as on the user's other projects: emulate it with our own server.

## 6. Quality-of-life and feature changes (optional)

FPS unlock in menus (1402CF58B), `cg_fov` range (call 14027273C), `sv_network_fps` range, `cl_maxpackets` to 125,
ultrawide/aspect ratio fixes (`ultrawide.cpp`), chat font above 1080p, aim-assist dvar, colored names, DLC
unlocks (`Content_DoWeHaveDLCPackByName`, `Entitlements_IsIDUnlocked`), non-fatal missing BSP in MP, gameplay dvars
(gravity, speed, bounces), script loading/extension hooks (`Scr_RegisterFunction`, `VM_Execute`), mods
(`fs_game`, `mod.ff`).

## Names

iw6-mod `symbols.hpp` names 252 functions/variables (250 with an MP address, 190 with SP), iw6x-client 62; there
are ~880 distinct hard-coded addresses in iw6-mod overall. These seed `named` identifications for the Steam
builds. They become evidence for the Store build only through matching, recorded with method `iw6-mod
symbols.hpp` and checked against our own analysis.

## Still to check

- Known exploits from public reports (separate survey in progress): what else has been exploited in Ghosts or
  shared IW code that neither client patches.
- Whether each fix's bug exists in the server reference and in the Store build at the matched function.
