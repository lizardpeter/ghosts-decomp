# Direct connect without vendor services

P0012 adds an experimental direct profile for the pinned Store multiplayer build. It builds a DLL and a patched
EXE copy, registers `connect IPv4:port`, and routes the original challenge request through independent UDP.
**Entering a map and completing a multiplayer join are not yet verified or complete.** This is not a standalone
source build: unreconstructed engine code still runs from the pinned original EXE. Neither function records nor
this package claim native integration or whole-process isolation.

## Build and package

Use the same LLVM toolchain, Python, pefile and Unicorn dependencies as the other reconstruction builds:

```sh
IW6_ORIGINALS=.work/originals python3 tools/build_recon.py --build iw6mp64_MSStore_ship --direct
python3 tests/direct/transport.py
IW6_ORIGINALS=.work/originals python3 tests/direct/game.py
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
.\LaunchDirect.ps1 -GameDirectory 'D:\Games\Ghosts' -Connect '192.168.1.20:27016'
```

This verifies package hashes and queues `+connect` after engine startup. Numeric IPv4 and a nonzero explicit
port are required. The same command can be entered in a functioning game console. This launch script has not
been executed on Windows here. Asset discovery, native DLL loading, graphics and menu entry remain unverified;
only the pinned executables are present in the development test environment.

## What is connected

The direct profile retains all 31 P0011 vendor guards and all 55 original import redirects. Original WinHTTP,
XCurl, GDK runtime loading, DNS, socket creation/sends and the selected account/reporting/process/broker paths
remain unavailable. The replacement transport has private Winsock imports in the DLL; they do not go through
the original IAT. Only this explicit opt-in profile opens game sockets. It is not run inside the network-disabled
Sandbox, since that configuration also prevents reaching a custom server.

The Windows transport uses a nonblocking IPv4 datagram socket and a separate lock; the same transport source
uses POSIX sockets in native Linux tests. No hostname resolution, TCP, SOCKS, NAT traversal or broadcast
fallback is used. A client sends only to the endpoint selected by `connect` and drops incoming packets from
other endpoints. A listener replies only to peers whose valid packet it has received. There are 64 listener
peer slots, retained until close/reopen; listener peer/session lifecycle is still experimental.

Packets retain the original checksum convention: big-endian 16-bit words, an unshifted odd final byte, carry
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

Source-linked packet/handle callers use the same direct replacements. Address comparisons deliberately require
matching ports too, including the entry tentatively named NET_CompareBaseAdr by the matcher. NAT rebinding,
peer migration and sharing a client identity across endpoints are not supported by this profile.

`connect` was removed at shutdown (140316854) but is not registered by the retail command initialization at
140314120. P0012 registers it through the existing Cmd_AddCommandInternal ABI at 1404448D0. Command arguments
now bind to 1469CECF0: `nesting` at +0, argc array at +44 hex, argv array at +68 hex, matching CmdArgs layout.
This also removes a prior unresolved-data-to-zero binding from the DLL link.

The normal join initializer at 140311F70 writes the server address at 14416A10C, qport at 14416A100, retry time
at 14416A11C and count at 14416A120 before setting connection state 3 at 143E96890. The direct command performs
this limited transition only after the engine's normal local-client initialization flag at 143E96821 is set,
and only when the old connection state is below 3. It does not manufacture SDK account objects or set vendor
login status. The original retry function at 140311310 then emits `getchallenge`; its DW readiness lookup is
replaced by the selected transport's readiness. Full local profile setup and other join initialization work
remain to be reconstructed.

## Remaining path to a playable game

- **Local identity and session ownership:** 140311570 still fills xuid/xnaddr, stats versions and related fields.
  These need a local player/profile and custom session contract. Vendor login must stay unavailable, while
  gameplay/UI readiness uses the replacement provider.
- **Server admission and hosting:** SV_DirectConnect at 1404BC1D0 checks protocol, checksum, challenge and stats
  versions, then uses registered party/session membership. Its final rejection is
  EXE_ERR_UNREGISTERED_CONNECTION. There is also an original local-network admission branch when `onlinegame`
  is false; this needs testing as a potential way to reuse engine admission without vendor membership. Merely
  opening the listener does not populate a party or spawn a server.
- **Map startup:** matched SV_StartMap at 1404BADC0 and SV_SpawnServer at 1404C2640 still need their complete
  startup contracts checked, including assets, map/game settings and client/server lifecycle. No speculative
  hard-coded map-start call has been inserted.
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
