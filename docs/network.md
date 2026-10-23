# Network and platform traffic

This page lists every way the Microsoft Store build (`iw6mp64_MSStore_ship`) can reach the network. It also
shows the few functions all of that traffic goes through. The faithful decomp reproduces all of it. The enhanced
build replaces these paths incrementally in source.

The enhanced build's goal is that it never talks to Activision's, Demonware's, Xbox's or Microsoft's services.
Local play and LAN keep working, and online play goes to our own backend once it exists.

## Ways out

The exe reaches the network only through imported DLLs. It never makes system calls of its own. These are the
DLLs, and the game functions that call them:

| Path | DLL | Used by | All traffic goes through |
|---|---|---|---|
| Game UDP (the game protocol: snapshots, usercmds, out-of-band packets) | WS2_32 | win32/win_net.cpp (reconstructed, tested) | Sys_SendPacket 14054FB70: NA_IP addresses go out through Demonware (dwSendTo 1405A9C80 → bdPlatformSocket), only broadcasts use the game's own socket from NET_OpenIP 14054F300 (sendto). Sys_GetPacket 14054F960 reads that socket (recvfrom) and then Demonware (dwRecvFrom 1405A9740) |
| SOCKS5 proxy for the game socket (only with `net_socksEnabled`) | WS2_32 (TCP) | NET_OpenSocks 14054F5B0 | connect to `net_socksServer:net_socksPort` |
| Game DNS | WS2_32 gethostbyname | Sys_StringToAdr 140535F50 / Sys_StringToSockaddr 140535FE0 (any address string not starting with a digit), NET_GetLocalAddress (inlined in NET_OpenIP; the local host name), NET_OpenSocks | gethostbyname |
| Demonware UDP (peer-to-peer game traffic in DW sessions, STUN, NAT type discovery, UPnP, QoS probes, bandwidth test) | WS2_32 | DemonWare bdSocket/bdNet | bdPlatformSocket::create 14076E930, sendTo 14076EF90, receiveFrom 14076EC90 |
| Demonware TCP (the lobby connection to the LSG) | WS2_32 | bdLobbyConnection | bdPlatformStreamSocket::create 1407E1340, connect 1407E11B0 |
| Demonware DNS | WS2_32 getaddrinfo | bdGetHostByName | bdPlatformSocket::getHostByName 14076EB20 |
| Demonware HTTPS (auth: `https://auth3.prod.demonware.net:443/auth/`, content streaming, uploads) | WINHTTP | bdHTTPWorker(WinHTTP) | WinHttpOpen 1407CF690, WinHttpConnect 1407CD540 |
| Xbox Live services (xsapi over libHttpClient: presence, social, session directory, title storage...) | XCurl.dll | libHttpClient CurlProvider | HC_CALL::PerformAsync 1407B8820; curl_easy_init 1407C1480, curl_multi_add_handle 1407C2A40 |
| Xbox Live real-time activity websocket (`wss://rta.xboxlive.com/connect`) | WINHTTP + Winhttp.dll loaded at run time for the WebSocket functions | libHttpClient WinHttpProvider | HCWebSocketConnectAsync 1407C69E0, WinHttpOpen 1407BF210, WinHttpConnect 1407C57F0 |
| The GDK runtime (sign-in, tokens, licence, invites, connectivity hints, security info for URLs; it talks to Xbox services itself, in process) | xgameruntime.dll, loaded from System32 at run time | 97 GDK functions | LoadLibraryExA 1406AEE34 → QueryApiImpl 1406AEE74 |
| Store pages (`msxbox://game/?productId=`) | WinRT Windows.System.Launcher | DLC/store links | opens the Xbox app; no traffic from the game itself |

Things that look like network access but aren't:

- `getdefaultgateway` (1405D3110, libnatpmp) reads the routing table.
- `GetAdaptersInfo` (iphlpapi, loaded at run time) reads the local adapters.
- `ShellExecuteA` (Sys_DirectXFatalError) opens a local help page.
- bcrypt and CRYPT32 do local cryptography and read the certificate store.

In the exe, nothing else imports WS2_32, WINHTTP or XCurl. The other DLLs it loads (D3D, NVIDIA, AMD, Bink,
DirectSound, XInput) are not network libraries, but their own imports haven't been checked yet.

So the game's own UDP traffic to other players and servers rides on Demonware's socket, not on a socket of its
own. The enhanced build has to send game packets itself when it drops Demonware.

## Servers the game contacts

| Host | Where it is chosen | What it is |
|---|---|---|
| `auth3.prod.demonware.net` (cert, dev variants) | dwSelectAuthAddress 14019AEE0 compares a built-in "RETAIL" with itself, so always prod; the HTTPS auth service picks its environment from XSystemGetXboxLiveSandboxId (140749EF0) | Demonware authentication |
| `lsg.2510.prod.demonware.net` (cert, dev variants) | dwLogOnComplete 14019A9A0, port 443, title 2510 | Demonware lobby (LSG): matchmaking, stats, storage, presence, teams, ... |
| `ghosts-stun.{us,eu,jp,au}.demonware.net`, `stun.{us,eu,jp,au}.demonware.net` | dwNetStart 1405A8C70, bdNetStartParams | STUN / NAT discovery |
| `*.xboxlive.com` (userpresence, social, sessiondirectory, rta) | xsapi | Xbox Live services |
| whatever the GDK runtime and XCurl talk to | inside xgameruntime.dll / XCurl.dll | Xbox sign-in, tokens, licence |

None of these can be configured. The hosts are compiled in, and the game has no dvar for them (the PS4 server
reads `DS_OPT_AUTHADDR`/`DS_OPT_LSGADDR`; the client doesn't).

## The GDK runtime

docs/gdk.md names all 97 GDK calls (13 interfaces) and their callers. The calls that reach Xbox or Microsoft
services are these:

- sign-in (`XUserAddAsync`);
- tokens (`XUserGetTokenAndSignature*`): Demonware's auth and every Xbox Live call depend on these;
- licence and add-ons (`XStoreQueryGameLicense*`, product queries);
- cloud saves (`XGameSave*`);
- achievements (`XGameEventWrite`);
- HTTPS certificate checks (`XNetworkingQuerySecurityInformationForUrl*`);
- the gamer picture and profile card.

XAsync and XTaskQueue carry all of libHttpClient's and xsapi's work but send nothing themselves.

Nothing in the exe quits after a sign-in, licence or connectivity failure. Failures end in a popup, and the
online systems stay off. Online starts only once the licence query has finished and found the game licensed
(1401A1760, 1401A5550). The licence popup's buttons are Lua in the fastfiles and haven't been checked.

If runtime initialisation fails while a kernel debugger is attached,
1406AEC18 calls DebugBreak.

## In each build

**The faithful decomp** (`src/`) reproduces all of this as it is.

**The original exe** is tested with no network at all: a VM or Windows Sandbox without a network adapter. It
then behaves as it does offline: a popup, and the online systems stay off.

**The enhanced build** (`enhanced/`) is replacing the platform layer in source. The target architecture has no
GDK, Demonware, xsapi or XCurl: the game's dw*/Live_* layer will use our own backend client and a configurable
server address. That replacement is not complete. P0005 below disables the reconstructed auth/lobby login
entry points. P0006 blocks lobby-service access and pumping. Xbox/GDK, other service paths,
and the Demonware game transport still need replacements.
The hybrid DLL also resolves unreconstructed functions to the original executable, so this is not yet a
standalone offline game. A future standalone build must check that removed paths and vendor hosts are absent;
that whole-binary guarantee is not claimed by the current entry-point tests.

## Checked

- No `syscall` or `int 0x2e` instruction in the exe, so all traffic goes through the DLLs above.
- Every function that calls a WS2_32, WINHTTP or XCurl import was found by scanning the whole disassembly and
  classified. The ones not in the table only convert addresses or query state: inet_pton, inet_ntop, WSAIoctl
  in bdNetImpl::start, __WSAFDIsSet.
- Run-time lookups (GetProcAddress) fetch only these:
  - the WinHTTP WebSocket functions;
  - GetAdaptersInfo;
  - NVIDIA's nvapi and GameWorks entry points;
  - WinRT activation;
  - a few kernel32 functions;
  - the GDK runtime's own exports.
- The exception is LUI's Lua, which keeps `package.loadlib` and `require`'s C loader (security S21): a script could
  load any DLL.
- The game's own net layer (win_net.cpp, com_net.cpp) is reconstructed and tested, so its list of exits is
  established, not inferred:
  - `bind` of the UDP port (27016 and up to 9 more);
  - `sendto` for broadcasts;
  - `dwSendTo` for every NA_IP address;
  - `gethostbyname` for names;
  - the SOCKS5 handshake when `net_socksEnabled` is set.


## Packet submission contract for a replacement transport

The Store sender `dwSendTo` (1405A9C80, `src/dw/dwnet.cpp`) is below `Sys_SendPacket`:

- `Sys_SendPacket` has already appended the two-byte checksum. `dwSendTo` adds another
  two-byte **little-endian length** prefix before passing those bytes to the router.
- Its input admission limit is 1262 bytes, including the checksum supplied by its caller.
  The router therefore receives at most 1264 bytes. This envelope is distinct from the
  game protocol carried inside it; an independent UDP implementation must explicitly
  decide which transport envelope its peer expects.
- It refreshes the destination's address handle under critical section 0x21. Router
  state 2 permits submission; state 1 returns zero without sending; other states return
  -10. A missing handle or router returns -7; an oversized connected send returns -6.
- Router calls receive temporary intrusive handle references and consume them. The
  sender releases its own retained reference after leaving the outer critical section.
  Dropping the router requires replacing handle ownership and connection state too.
- `dwGetSocketRouter` (1405DA910, PS4 PDB `dw/dwutils.cpp:440`) obtains the `bdNetImpl`
  singleton, returning null on failure or the instance's socket router otherwise.

`tests/differential/test_dwnet.py` compares returns, image-backed reference counts,
address-table writes, lock order, refresh calls and transmitted bytes with the Store
executable. SDK operations are faked: these tests do not initialize Demonware or contact
any network. The original's raw null pointer for an ABI-level aggregate argument is
outside the C++ by-value `netadr_s` calling contract used in these tests.

The PS4-host reference has a different `netadr_s` layout (handle index at +0x10 rather
than the Store build's +0x0C). Store verification does not establish equivalence to that
server build; its differing layout and dependencies need their own reconstruction.

## Receive and handle ownership

`dwRecvFrom` (1405A9740) asks router slot +0x40 whether it is ready. Only the
exact state 1 reaches receive at slot +0x58; otherwise it returns -9. A nonpositive
receive result is returned unchanged, releasing any handle that the router provided.
A positive result without a handle is also returned unchanged.

A positive result with a handle runs the Store build's inlined registration:

1. Search for an equivalent registered handle. Equivalence takes precedence over an
   earlier empty slot, so a received sender keeps its existing index.
2. If none matches, use the first empty slot. When the table is full, unregister the
   entry with the smallest **unsigned** lifetime; ties keep the first entry.
3. Raise the selected entry's lifetime to at least 6600. Registration retains a table
   reference; the receive routine releases its temporary references separately.
4. Remove the first two transport bytes, then derive the sender's IPv4 address and
   port from its real address. The header's contents are not validated here.

`dwUnregisterAddrHandle` (1405A9EA0) gives the router a borrowed reference to the table
entry, pumps the router, then takes critical section 0x21, releases the current table
handle and zeros all 16 bytes of the entry. It rereads the entry after the router calls,
which matters if those calls update the table. `sub_1405A8980` maps router states 1
and 2 to game statuses 0 and 1; other router states become 2. The reserved local index
is immediately status 1 without consulting the router.

The SDK address getters use Win64 hidden return buffers. `include/dw/sdk_abi.h`
expresses that ABI for hybrid calls without claiming complete SDK class layouts.
Receive tests exercise unregister together with receive and compare packet buffers,
address outputs, ownership counts, table selection, lifetime updates and call order.
B0051 records the original's unchecked one-byte transport result for an enhanced fix.

## Stale handles and address recovery

`dwSanityCheckAddressHandle` (1405A9A90) is called by the packet sender and status
queries before reading a table entry. It uses a supplied router, or obtains one when
the argument is null. Invalid indices and empty entries return without changing the
table. It does not acquire a lock itself; callers provide the table lock.

For router state 3, it looks up a replacement using the old handle's endpoint common
address and security ID. Only replacement state 2 is admitted to the table. On
admission it releases the current table reference, retains the replacement for the
table, and clears the entry's four-byte field at +12. Its retained old handle and the lookup's
output reference are released separately. The lookup consumes its temporary common
address reference. Tests cover failed lookups that still provide an output reference,
null candidates, candidates aliasing the old handle, and table changes during a call.

`sub_1405AA0B0` clears the address's IPv4 bytes before checking its type or index. For
a populated nonlocal IP entry it obtains the real address, copies the port and IPv4
bytes, and balances its handle reference. The reserved local index becomes loopback.
An empty in-range IP slot still returns success, with zero IPv4 bytes and the previous
port; an out-of-range index or non-IP type returns failure. These are original
behaviors, not enhanced policies. Sender/refresh tests exercise the implementations
together so a future transport override can preserve the caller-facing contract.

## Serialized common-address conversion

`sub_1405A8300` converts the serialized common address and security ID into a
`netadr_s`. The existing `sub_14054FC70` caller supplies the first 8 bytes of its
input as the security ID and the following 37 bytes as the serialized descriptor.
The SDK performs deserialization; the reconstruction preserves the game-side
control flow and ownership around that boundary.

For a nonnull output, housekeeping runs before the output is zeroed and its handle
index is set to FFFFFFFF. Missing local-common-address or address-map state returns
failure. Deserialization consumes a temporary local-address reference. The decoded
common-address object is reference counted and released separately from any handle
returned by registration.

A loopback descriptor gets the reserved local handle index. Its raw port defaults
to 0C03 and is replaced by the local network address's port when the network
instance exists. For a nonloopback descriptor, successful registration uses the
same equality/free-slot/oldest-entry selection as receive, with lifetime at least
6600. A newly inserted handle requests a router connection. An existing equivalent
handle requests connection only in router state 3. Address extraction uses the
handle after the connection call, including any change to that reference.

B0052 records the original's success return after successful deserialization but
failed or empty registration. The current caller then forwards the invalid handle
index. `test_win_net_common.py` exercises that caller with injected SDK failures,
alongside its existing isolated cases. `dwGetAddressMap` (1405DA000) is reconstructed
separately and checks both the singleton and router before obtaining the map.

The lifetime pass at `sub_1405A8790` holds critical section 0x21 and captures the
unsigned local handle index as its entry count. It decrements a lifetime only
when the entry has a handle and the lifetime is nonzero. Empty entries retain
stale lifetime values, and zero does not wrap to FFFFFFFF. Entry +12 is untouched.

`sub_1405A87E0` clears one nonlocal entry's lifetime under the same lock. It does
not require a nonnull handle or an index below the active count. B0053 records
its unchecked write; current-caller reachability of an invalid index remains
unestablished. `test_dwlifetime.py` compares table writes and lock calls against
the Store binary, including writes above the active count within mapped storage.


## Login reconstruction and offline entry points

`dwLogOnStart` (14019ADA0) first checks platform readiness and the two auth-busy
flags. Its retry scheduler uses a wrapping 32-bit millisecond difference, signed
seconds truncated toward zero, and a delay obtained from the original helper.
At elapsed seconds greater than 120 it resets the attempt count. At exactly 120
it still honors the existing delay. A permitted attempt sets state 1; readiness
and busy failures leave all scheduling state unchanged.

`dwLogOnComplete` (14019A9A0) clears the current state before taking one step:

| Prior state | Original action |
|---|---|
| 1, 2, 8 | Wait for another controller's active logon, otherwise advance to 9 |
| 3 | Pump auth-host DNS; pending stays 3, failure ends login, success joins the controller check |
| 9 | Obtain the cached auth client; start authentication if its status permits |
| 10 | Poll auth status and require result 700 to advance to 11 |
| 11 | Pump lobby-host DNS; construct a port-3074 endpoint, disconnect the old lobby, then connect with auth info |
| 13 | Pump the lobby and inspect connection status plus transport readiness; notify only after assigning state 14 |
| Other states | Fall through with state 0 |

The auth client uses port 443 and title 2510. Its factory (1405DA070) lazily
allocates 0x3580 bytes, caches the constructor result, and returns an existing
client without reconfiguration. Its release helper (1405D9F30) destroys and frees
the captured pointer before clearing the cache, even if the destructor changes
the cache. The busy query (1405D9F10) reads two separate bytes.

Terminal states 0 and 14 release both DNS resolver objects and the auth client.
State 0 also disconnects the lobby. Resolver cleanup (14019AE90) rereads the
second global after destroying the first object. Reset (14019AE70) clears only
the qword before the controller table and its first sixteen bytes; it leaves
resolver pointers untouched. The Store controller scan checks one controller.
All new storage names are descriptive; original unknown names remain `sub_<VA>`.

P0005 replaces `dwLogOnStart`, `dwLogOnComplete`, their status/busy queries,
the auth-client factory, and `DW_Frame` in the enhanced build. Start, step and
frame clear scheduling state and remain offline. Queries never report vendor authentication or pending
vendor login. The factory returns null even when an old cache exists. These
entry points do not call SDK DNS, auth, lobby, clock or platform-readiness code.
They do not masquerade as a successful online login. A replacement account and
dedicated-server client can later own this boundary.

The override is intended for source-linked startup, not hot-swapping an already
connected original process. It does not clean up preexisting SDK objects. The
original selector and cleanup remain available for faithful verification and
separate shutdown paths. `test_backend_offline.py` poisons old object pointers,
rejects modeled platform/backend calls, and checks the offline results.
`test_dwlogon.py` compares the faithful functions with the original, including
login steps with the real reconstructed auth factory and release helpers.

`DW_Frame` (1405D3D40) is the caller that automatically starts or advances login
and pumps a connected lobby. Its inhibit setter (1405D3DC0) stores its low
argument byte without boolean normalization. The original `dwGetLogOnStatus`
name and `DWOnlineStatus` enum are confirmed by PS4 PDB 1402B78D0 and the Store
caller's 32-bit comparisons. The enhanced frame override resets to offline
before any original frame callbacks. Frame integration cases exercise the
faithful driver through the reconstructed status, start, step, and auth helpers.


## Lobby services and disconnection state

`dwGetLobbyService` (1405DA470) lazily constructs the shared SDK lobby in 0x538
bytes of allocated storage. Only initial construction registers an event handler,
using one of four objects at stride 8 for controller indices 0 through 3. Existing
cached objects are returned without registering another handler or changing their
controller association. Allocation/constructor failure returns null. The factory
rereads its global after the handler callback, so a callback can change the result.

`dwGetActiveLobbyService` (1405D9FD0) uses separate storage: it scans the single
Store controller slot at 140DF23D8. It does not read the construction cache at
14A022468. The two pointers must remain distinct in the faithful reconstruction.
The earlier descriptive `logonUnknown` alias is retained for that controller slot.

| Wrapper | Original admission rule |
|---|---|
| `dwGetContentStreaming`, `dwGetDML` | Nonnull lobby; no connection-status check |
| `dwGetCounter`, `dwGetGroup` | Nonnull lobby and SDK connection status exactly 2 |
| `dwIsBdNetReady` | Nonnull SDK net singleton and SDK net status exactly 2 |

`dwLobbyPump` (1405DBF40) clears the activity dword, obtains a lobby, and pumps
that captured object. On status 2 it writes activity 14, calls the anticheat pump
and a game callback, then obtains the lobby again before accessing content.
A nonnull content object is pumped only when the controller gate allows it.
Callbacks can replace the cached lobby or change activity; those effects survive.

The disconnect wrappers preserve separate state. 1405DBFD0 clears only the
selected controller's logon-state dword with no bounds check. 1405DBFF0 clears
the disconnect-state dword and first auth-busy byte, retaining the second byte
and reason. 1405DC010 sets the first byte; 1405DC020 stores its supplied reason
and sets the second byte. Both request cleanup with controller argument 0, and
leave any changes made by that cleanup callback intact.

P0006 overrides the active-lobby accessor, construction factory, four service
getters and lobby pump. Accessors return null without touching either cache or
calling SDK methods. The pump clears only the local activity marker, preserving
the neighboring logon flag, and calls no vendor, anticheat or content callbacks.
These entry points remain unavailable even with poisoned or preexisting cache
pointers. Original net readiness and disconnect bookkeeping are reconstructed
separately; this patch does not replace the game packet transport.

`test_dwservices.py` compares the original wrappers and integration through the
reconstructed factory. `test_services_offline.py` rejects dependency calls from
each enhanced entry point and checks that it cannot return an old vendor object.
The source override is for a reconstruction started offline, not runtime teardown
of SDK objects already owned by an original running process.

## GDK startup, sign-in and token boundary

P0007 adds six enhanced overrides at the reconstructed GDK runtime boundary and
game startup. They prevent these source-linked paths from loading the runtime,
resolving SDK exports or obtaining Xbox interfaces. Reconstructed account-add
and token/signature thunks run through the enhanced lookup guard and return
unavailable without starting an async operation. No completion is fabricated.
Title and feature queries also fail without SDK access, and game startup skips
all GDK subsystem initialization. See docs/gdk.md for faithful behavior and tests.

The reconstructed result and repair entry points now share that guard as well:
account-add results, user ID/state, privilege checks, token result sizes/data and
both account/privilege repair UI pairs return unavailable without modifying
caller buffers. Blocking a request alone is insufficient when an independent
caller can retrieve credentials or initiate repair UI; these calls are tested
separately through the same enhanced interface boundary.

This extends P0005/P0006 offline startup. Unreconstructed original call sites,
HTTP providers, remaining SDK thunks and packet transport still need work; this
is not a claim of whole-game isolation or a working standalone executable.

## Reporting to account services

The original includes account-linked reporting in addition to authentication.
The following routes are established by the Store disassembly and the GDK/HTTP
call graph; this is a static inventory, not a captured list of live traffic.

| Route | Original behavior | Reconstructed enhanced boundary |
|---|---|---|
| Xbox achievement/stat events | Game achievement path 14019F3D0 calls XblEventsWriteInGameEvent 1406D1880; XSAPI reaches XGameEventWrite 1406AF274 | P0008 rejects direct reconstructed XGameEventWrite; event-task pump 14019F390 is inert |
| Presence and social/session services | XSAPI uses libHttpClient/XCurl and the RTA websocket | P0008 stops presence pump 1401A1CA0 and the GDK frame driver; direct SDK/session/HTTP paths remain pending |
| Connected Storage cloud saves | GDK gamesave tasks and completion queue | P0008 drops pending work in reconstructed save pump 1401A1320 without dispatch or provider access; direct save APIs remain pending |
| Vendor login and lobby stats/storage | Demonware auth/lobby clients and service getters | P0005/P0006 block their reconstructed entry points; original callers and remaining service methods remain pending |
| Account sign-in, tokens and repair UI | Xbox runtime interfaces | P0007 guards reconstructed runtime/account entry points; original call sites remain pending |

The main game GDK frame driver 1401A1760 can retry sign-in, advance online
initialization and call the task, save, user, friend, event, store, presence and
session frame functions. P0008 clears its two scheduling latches and invokes
none of these dependencies. Direct pump callers are guarded separately, because
skipping this parent alone does not guard callers outside it.

No successful upload, event receipt or async completion is fabricated. These
changes do not prove that the entire original process sends no traffic: direct
WinHTTP/XCurl providers, XSAPI events above the thunk, session operations and
unreconstructed original call sites still require reconstruction/integration.
A separate generic analytics/crash-upload route has not been established here;
its absence is not claimed. The checks emulate providers and make no real account
or network requests.

### Explicit gameplay telemetry

The original also registers telemetry sampling controls in 1405E92D0. The
following default fractions are read from the original PE's floating-point
constants and paired with their registration calls, not inferred from labels.

| Control | Default fraction | Stored dvar pointer |
|---|---:|---|
| `match_making_telemetry_chance` | 0.05 | 14A05F8D0 |
| `log_mapvote_chance` | 0.01 | 14A05F8D8 |
| `log_teambalance_chance` | 0.01 | 14A05F8E0 |
| `log_host_migration_chance` | 0.10 | 14A05F8E8 |

Matchmaking reporter 140199DA0 compares a random value against the first rate,
but can bypass sampling when 1405F0700(controller, 9) admits a forced event.
It serializes a binary record and calls 140749C00 through the lobby event log.
This path is not yet reconstructed. The map-vote/team-balance settings are
confirmed registrations; their submission callers are not established here.

Host-migration function 1404C6E40 samples the fourth rate, builds text, and calls
1405D6A90 with category 11. That submission helper is now reconstructed. It
obtains the active lobby, checks its admission byte, obtains its event log and
submits text with a length including the terminating NUL. A nonnull returned
reference container determines success. Its separately supplied temporary task
is decremented and virtually destroyed only when the old count was 1; return
success uses the captured pointer even if cleanup changes the container.
`test_dwreporting.py` compares 100 provider/ownership cases with the original.

P0008 also overrides this telemetry-text helper to return 0 without inspecting
the text or invoking lobby/SDK calls. Its test uses invalid payload pointers and
rejects lobby dependencies, so it does not merely rely on P0006's null lobby.
This blocks the source-linked helper, not every original host-migration caller
or the separate binary matchmaking reporter. Turning down sampling controls
alone would not provide full disconnection.

The telemetry-text tests reject removing the terminating NUL from the submitted
length, reading the returned container after cleanup instead of its captured
pointer and omitting the task-reference decrement. Removing its enhanced
override fails the dependency-trap test even with P0006 available. Together
with the GDK reporting checks, 13 source mutations and all six individual P0008
override removals were rejected.
