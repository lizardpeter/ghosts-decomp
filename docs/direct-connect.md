# Direct connect without vendor services

P0012/P0019 add an experimental direct profile for the pinned Store multiplayer build. It builds a DLL and a patched
EXE copy, registers `connect IPv4:port`, and routes the original challenge request through independent UDP.
**Entering a map and completing a multiplayer join are not yet verified or complete.** This is not a standalone
source build: unreconstructed engine code still runs from the pinned original EXE. Neither function records nor
this package claim native integration or whole-process isolation.

## Build and package

Use the same LLVM toolchain, Python, pefile and Unicorn dependencies as the other reconstruction builds:

```sh
IW6_ORIGINALS=.work/originals python3 tools/build_recon.py --build iw6mp64_MSStore_ship --direct
python3 tests/direct/transport.py
python3 tests/direct/profile.py
IW6_ORIGINALS=.work/originals python3 tests/direct/game.py
IW6_ORIGINALS=.work/originals python3 tests/direct/admission.py
IW6_ORIGINALS=.work/originals python3 tests/direct/host.py
IW6_ORIGINALS=.work/originals python3 tests/offline/vendor_tasks.py
python3 tools/offline/package.py --mode direct \
  --original .work/originals/iw6mp64_MSStore_ship.exe \
  --output .work/direct-package
```

The output directory must not already exist. It contains the patched EXE, `recon.dll`, hashes/change manifest,
and `LaunchDirect.ps1`. Offline and direct DLLs cannot be interchanged by the packager. Faithful sources and the
ordinary enhanced/offline profiles do not include `enhanced/direct/`. The executable filename remains
`iw6mp64_offline.exe` for compatibility with the package format; the manifest selects the actual mode.

The Windows launch experiment, with the original complete game installation available, is:

```powershell
.\LaunchDirect.ps1 -GameDirectory 'D:\Games\Ghosts' -Connect '192.168.1.20:27016' -PlayerName 'LocalPlayer'
# Listen-server map-start experiment, not a verified headless dedicated server:
.\LaunchDirect.ps1 -GameDirectory 'D:\Games\Ghosts' -HostEndpoint '0.0.0.0:27016' -Map 'mp_prison' -GameType 'war'
```

The launcher verifies package hashes, prepares a persistent local profile, then queues `direct_player` and
`connect` or `direct_host` after engine startup. Use `-Profile one` / `-Profile two` for independent local
profiles and data folders on one Windows account. Numeric IPv4 and a nonzero explicit
port are required. In a functioning game console, first configure `direct_player <16-digit-hex-ID> "Player Name"`, then
use `connect IP:port` or `direct_host bind-IP:port map gametype`. IDs must be nonzero; names are 1–31
ASCII letters, digits, spaces, underscores or hyphens, without leading/trailing spaces. Profile changes
are refused while connected or hosting. Windows launcher preparation is tested with process launch intercepted.
Actual Windows startup attempts use the native debug observer and authentic startup assets; see
[native-launch.md](native-launch.md). Successful graphics/menu startup and a completed join remain unverified.

## What is connected

The direct profile retains all 31 P0011 vendor guards, the ten P0018 vendor integrity/reporting guards,
the P0022 local asset-root replacement and all 58 original import redirects. Its total is 59 entry
replacements, including 14 direct identity/transport entries and three P0024 local-platform entries. See [vendor-disconnection.md](vendor-disconnection.md). Original WinHTTP,
XCurl, GDK runtime loading, DNS, socket creation/sends and the selected account/reporting/process/broker paths
remain unavailable. The replacement transport has private Winsock imports in the DLL; they do not go through
the original IAT. Only this explicit opt-in profile opens game sockets. It is not run inside the network-disabled
Sandbox, since that configuration also prevents reaching a custom server.

Local IDs are custom-session identifiers, not vendor accounts or proof of authentication. No GDK handles
are created and GDK initialization still reports unavailable. The launcher uses local cryptographic randomness
for a first profile ID and retains it in `LOCALAPPDATA/GhostsDirect/<profile>/player.json`; this file is
separate from game stats and progression. Cloud-save and full stats/profile lifecycle replacements remain
incomplete. A server must not treat this self-asserted ID as an authorization credential.

The Windows transport uses a nonblocking IPv4 datagram socket and a separate lock; the same transport source
uses POSIX sockets in native Linux tests. No hostname resolution, TCP, SOCKS, NAT traversal or broadcast
fallback is used. A client sends only to the endpoint selected by `connect` and drops incoming packets from
other endpoints. A listener replies only to peers whose valid packet it has received. There are 64 listener
peer slots, retained until close/reopen; listener peer/session lifecycle is still experimental.

P0020 places an eight-byte custom header before the game payload: ASCII `IW6D`, version byte 1,
reserved flags byte 0 and a big-endian 16-bit payload length. The receive path requires this header,
exact length, supported version/flags and valid checksum before exposing data to the game. Both peers
need this custom transport; retail-format replies are rejected. This is a protocol compatibility
boundary, not server authentication or an IP blocklist. An explicitly entered destination still receives
a UDP datagram; complete vendor-traffic isolation is not established by a packet marker.

The inner payload retains the original checksum convention: big-endian 16-bit words, an unshifted odd final byte, carry
folding and one's complement, followed by two checksum bytes. The replacement checks lengths before reads or
copies, limits payloads to 1262 bytes, ignores malformed packets and bounds each receive drain to 64 datagrams.
Failed peer selection clears the old client destination; failed socket reconfiguration closes the old socket.

`direct_listen IPv4:port` opens a transport listener, including explicit `0.0.0.0` binding. It **does not start a
map or create a playable dedicated server**. `direct_stop` closes the transport; game teardown still belongs to
the engine's `disconnect` command. A second `connect` while a join/game is active is refused until disconnect.

## Store integration evidence

The package adds these entry replacements to P0011. Names below describe replacement behavior, not recovered
original names where the original is unknown.

| Original entry | Direct replacement |
|---|---|
| 14054F200 NET_Init | Register commands once, defer socket creation until a command |
| 14054F960 Sys_GetPacket | Receive and validate independent game UDP |
| 14054FB70 Sys_SendPacket | Send independent game UDP |
| 140469E70 / 140469EC0 / 140469F20 | Compare actual IP and port, never a DW handle sentinel |
| 1405A8830 | Report transport task readiness only after client peer selection |
| 1405A8980 | Report readiness only for the selected endpoint |
| 1405A9E50 / 1405A87E0 | Ignore DW lifetime-table updates; no DW handles exist |
| 1401A7DB0 | Engine player-name view reads the local profile |
| 1401A7E10 / 14054C360 | Engine ID getter reads the local profile |
| 14054C0F0 | Engine ID-string view reads the local profile |

Source-linked packet/handle callers use the same direct replacements. Address comparisons deliberately require
matching ports too, including the entry tentatively named NET_CompareBaseAdr by the matcher. NAT rebinding,
peer migration and sharing a client identity across endpoints are not supported by this profile.

`connect` was removed at shutdown (140316854) but is not registered by the retail command initialization at
140314120. P0012 registers it through the existing Cmd_AddCommandInternal ABI at 1404448D0. Command arguments
now bind to 1469CECF0: `nesting` at +0, argc array at +44 hex, argv array at +68 hex, matching CmdArgs layout.
This also removes a prior unresolved-data-to-zero binding from the DLL link.

Before a direct join or listener opens, the bridge requires the initialized boolean `onlinegame` dvar and
sets it to false through Dvar_SetBool (14053E7E0). This selects the engine's existing local-network admission
and stats behavior; it does not grant a vendor session or report successful vendor authentication. Missing or
unexpected dvar state is refused. Other UI/platform gates still need a local provider.

The normal join initializer at 140311F70 writes the server address at 14416A10C, qport at 14416A100, retry time
at 14416A11C and count at 14416A120 before setting connection state 3 at 143E96890. The direct command performs
this limited transition only after the engine's normal local-client initialization flag at 143E96821 is set,
and only when the old connection state is below 3. It does not manufacture SDK account objects or set vendor
login status. The original retry function at 140311310 then emits `getchallenge`; its DW readiness lookup is
replaced by the selected transport's readiness. Full local profile setup and other join initialization work
remain to be reconstructed.

## Local multiplayer readiness (P0024)

The two Store multiplayer eligibility queries at **14054B1B0** and
**14054B290** normally report reason 0xC when Xbox sign-in or Store
licensing has not completed. The generated Store pseudocode shows that they
otherwise continue through privilege checks and vendor state. In the custom
**direct** profile only, both original entries now redirect to
`Iw6DirectLocalPlayReady`. That replacement:

- Requires controller 0, an explicitly configured nonzero custom player ID,
  a valid boolean `onlinegame` dvar, and `onlinegame == false`.
- Returns reason 0xC and false for missing/invalid profile, other controllers,
  missing/online dvar state or null output pointers.
- Returns reason 0 and true **only for custom local-session eligibility**. It
  never requests Xbox sign-in or returns a forged vendor licence/token.

The original LUI `CheckGameLicense` callback at **140245440** only attempts an
`XStoreQueryGameLicenseAsync` refresh and returns zero. P0024 makes this callback
inert in **direct mode only**, preserving the zero return without manufacturing
a valid Microsoft licence or starting an unavailable GDK Store task. The
faithful and ordinary enhanced/offline profiles retain the original behavior.

These gates do not establish native menu availability, map loading, access to
retail servers, or authenticated network identity. Other original LUI licence
and profile paths remain to be disentangled, and no vendor capability/permission
check is bypassed for retail or Xbox-network mode.

## Remaining path to a playable game

- **Local identity and session ownership:** 140311570 still fills xuid/xnaddr, stats versions and related fields.
  P0019 now supplies local name/ID views and tests the original challenge using that ID. Complete local
  stats data and a custom session contract still need reconstruction. Vendor login must stay unavailable, while
  gameplay/UI readiness uses the replacement provider.
- **Server admission and hosting:** SV_DirectConnect at 1404BC1D0 checks protocol, checksum, challenge and stats
  versions, then uses registered party/session membership. Its final rejection is
  EXE_ERR_UNREGISTERED_CONNECTION. The original local-network admission branch when `onlinegame`
  is false reaches the response boundary in the admission probe with no party membership; direct mode now
  selects that branch. The probe models game VM callbacks and response serialization, so it does not establish
  that an actual player enters the map. Merely
  opening the listener does not populate a party or spawn a server.
- **Map startup:** `direct_host` opens the game listener, sets local-network mode and g_gametype/ui_gametype,
  then calls the original SV_StartMap at 1404BADC0 with the Store four-argument ABI. Tests run its real map
  normalization and preparation to the SV_SpawnServer boundary at 1404C2640. Asset checks and their rejection
  path remain intact. World/asset loading, VM initialization, automatic local-player connection and map changes
  still need native tests. Result 3 means a request was made, not that a playable server exists. This is a
  listen-server startup experiment; renderer-free dedicated-server lifecycle remains separate work.
- **Response, stats and gameplay:** the client connectionless handler at 1403129D0 handles challengeResponse,
  connectResponse, syncDataResponse and statResponse. In particular connectResponse still uses the data helper
  at 14018D6B0. Successful admission, gamestate, snapshot/usercmd exchange, disconnect/reconnect and map changes
  must be exercised end to end.
- **Native validation:** launch on Windows with full assets, enter a map with at least two independent clients,
  and capture outbound traffic while loading, playing, disconnecting and switching maps. Loaded libraries and
  IPC are not fully audited. The code guards are not a complete whole-process vendor-blocking guarantee.

These remaining dependencies are tracked in B0069. No function is promoted to `integrated` by emulator tests.

## Verification

`tests/direct/transport.py` compiles the actual transport source natively and sends real localhost datagrams
between separate client/server instances and an independent Python socket. It checks framing, endpoint
restrictions, invalid lengths, truncated packets, parser edge cases, failure cleanup and shutdown.

`tests/direct/game.py` models Windows loading/import resolution for a newly packaged pinned EXE and DLL. It
calls the original NET_Init entry, captures the actual registered console handlers, executes `connect`, then
runs the **original** 140311310 challenge retry through the new packet entry to the private socket import.
Only local formatting and scratch allocation are modeled for this challenge sequence; it uses the original
local/guest naming branch. It also verifies that vendor imports remain redirected, different endpoints do not
alias through FFFFFFFF handles, lifetime updates do not touch the DW table, and GDK initialization still fails.
This is machine-code path verification, not a native Windows game test or a completed join.

`tests/direct/admission.py` runs the original SV_DirectConnect with synthetic initialized server state,
valid protocol/checksum/challenge/stats fields and no party members. Local parsing, empty-party queries,
game VM callbacks and response serialization are modeled. It checks that local-network mode assigns a free
client slot and reaches the response boundary, that online mode refuses an unregistered client, and that a bad
challenge is rejected before admission. This narrows the remaining work; it does not replace native validation.

`tests/direct/host.py` runs the original map-start routine with modeled asset availability and local string
helpers, stopping at SV_SpawnServer. It checks normalization and the missing-content rejection path. The
Windows CI launcher test executes profile/argument preparation with Start-Process intercepted; it does not
launch the EXE. Neither test substitutes for a native game with full assets.

`tests/direct/transport.py` also rejects checksum-valid retail-format packets, unsupported envelope
versions/flags and length mismatches. The package records IW6D/version 1 and refuses a direct DLL
without the wire-version export. Earlier experimental unwrapped packets are no longer compatible.
