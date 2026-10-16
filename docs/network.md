# Network and platform traffic

This page lists every way the Microsoft Store build (`iw6mp64_MSStore_ship`) can reach the network. It also
shows the few functions all of that traffic goes through. Those are the places to cut it, and later to point it at
our own server.

The goal is that a patched or rebuilt client never talks to Activision's, Demonware's, Xbox's or Microsoft's
services. Local play and LAN must keep working, and online play goes to our own backend once it exists.

## Ways out

The exe reaches the network only through imported DLLs. It never makes system calls of its own. These are the
DLLs, and the game functions that call them:

| Path | DLL | Used by | All traffic goes through |
|---|---|---|---|
| Game UDP (the game protocol: snapshots, usercmds, out-of-band packets) | WS2_32 | win32/win_net.cpp | NET_OpenIP 14054F300 (the only socket), Sys_SendPacket 14054FB70 (sendto), Sys_GetPacket 14054F960 (recvfrom) |
| SOCKS5 proxy for the game socket (only with `net_socksEnabled`) | WS2_32 (TCP) | NET_OpenSocks 14054F5B0 | connect to `net_socksServer:net_socksPort` |
| Game DNS | WS2_32 gethostbyname | 140535F50 / 140535FE0 (address strings), NET_OpenIP, NET_OpenSocks | gethostbyname |
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
DirectSound, XInput) are not network libraries, but their own imports haven't been checked yet. The guard below
covers them anyway, because it hooks the Winsock and WinHTTP functions themselves, for every module in the
process.

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

An offline loader has to answer at least these:

- `XGameRuntimeInitialize`;
- `XGameGetXboxTitleId` = 0x66CDD1F0 (outside its package the exe has no MicrosoftGame.config);
- working XAsync and XTaskQueue;
- one signed-in user: an ID, a gamertag, state 0, not a guest, every privilege granted;
- `XUserIsStoreUser` true;
- `XblContextCreateHandle` succeeding;
- connectivity registration succeeding;
- a store context;
- a licence with isActive 1 and isTrial 0.

Add-on and DLC queries may fail. If runtime initialisation fails while a kernel debugger is attached,
1406AEC18 calls DebugBreak.

## Cutting it

**The faithful decomp** (`src/`) reproduces all of this as it is. Nothing is cut there.

**The loader**, used for testing the original exe offline (docs/store-build.md), cuts traffic at the DLL
boundary. That is the one place nothing can slip past:

- Ship our own `XCurl.dll` next to the exe. The exe imports it by name from its own folder, and it isn't a
  KnownDLL, so ours loads before any game code runs. Every request it gets fails as "no network", or goes to our
  server. Its DllMain also installs the guard below.
- The guard hooks the functions in WS2_32 and WINHTTP themselves, not only the exe's import table, so every DLL in
  the process is covered. It stays small because only these functions matter:
  - WS2_32: `socket`/`WSASocketA` are allowed (local play needs them), but `connect`, `sendto` and `WSASendTo` are
    checked against an allow-list: loopback, private LAN ranges, and our server.
  - DNS: `gethostbyname` and `getaddrinfo` are answered from a local table. Demonware and Xbox names fail, or
    resolve to our server.
  - WINHTTP: `WinHttpOpen` returns NULL. With no session, every WinHTTP and WebSocket path fails at its first
    step.
  - `LoadLibraryExA("xgameruntime.dll")`: the exe loads it from System32 only (flag 0x800), so the exe's import
    of LoadLibraryExA is patched to catch it. It gets our local implementation of the GDK interfaces the game uses (an offline signed-in user, a
    valid licence, local saves) instead of the real runtime.
- Each of these is listed with its reason and evidence, as docs/store-build.md requires for loader patches.

**The enhanced build** (`enhanced/`) replaces the platform layer in source. It has no GDK, no Demonware, no xsapi
and no XCurl. One backend client talks to our server, whose address is a setting. Game UDP stays as it is, with
the fixes in records/bugs.tsv.

## Where our server plugs in

- **Short term (loader):** the DNS table maps the Demonware hosts to our server, and our server speaks enough of
  the Demonware protocol (auth, then the LSG lobby: the bdLobbyService tasks the game uses). This is how the
  community's private Demonware emulators work. It gives sign-in, matchmaking, stats and storage without
  changing the game's online code.
- **Long term (enhanced):** the game's dw*/Live_* layer (dw/, online/, sessions/, the PS4 PDB names them) calls our
  own protocol instead of bd* tasks.
