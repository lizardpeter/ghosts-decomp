# Network and platform traffic

This page lists every way the Microsoft Store build (`iw6mp64_MSStore_ship`) can reach the network. It also
shows the few functions all of that traffic goes through. The faithful decomp reproduces all of it. The enhanced
build replaces it in source.

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

**The enhanced build** (`enhanced/`) replaces the platform layer in source. It has no GDK, no Demonware, no xsapi
and no XCurl. The game's dw*/Live_* layer (dw/, online/, sessions/; the PS4 PDB names them) calls our own
backend client, with its own accounts and login, and that client talks to our server, whose address is a setting.
A test on the built binary checks that none of the hosts above and none of the removed paths are left in it. Game
UDP stays as it is, with the fixes in records/bugs.tsv.

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
