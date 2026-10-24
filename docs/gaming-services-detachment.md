# Microsoft Gaming Services detachment (custom Store MP profile)

Target: pinned \`iw6mp64_MSStore_ship\`. The faithful \`src/\` build preserves
original behavior; detachment applies only to the opt-in offline/direct package.

## What is implemented

* \`enhanced/_external/gdk/xgameruntime.cpp\` denies runtime initialization,
  interface queries and event submission. \`enhanced/win32/gdk.cpp\` does not
  initialize GDK task queues, Xbox accounts, licence requests, cloud saves or
  presence callbacks in the experimental custom startup.
* \`tools/offline/package.py\` redirects identified original function entries
  to the corresponding custom exports. It also redirects original WinHTTP,
  XCurl, network-send, DNS, COM activation and process-launch imports, while
  keeping the IAT addresses stable.
* The direct profile implements private, selected-peer UDP and local
  identifiers. These are NOT authenticated Microsoft/Activision accounts.
  Original game content checks are not fabricated or removed.
* \`tools/offline/detachment_audit.py\` independently parses the resulting PE,
  checks required GDK and direct-entry redirects, checks every manifest-listed
  import against the *actual final IAT*, and rejects unredirected Xbox/GDK
  and original socket-egress imports. Package creation fails closed if any of
  those known boundaries regress.
* Native Windows CI now applies the same audit to the package and checks the
  bounded debugger module-load trace for \`xgameruntime.dll\`,
  \`xcurl.dll\` and \`xboxliveapi.dll\`. The result is uploaded to
  \`native-launch-diagnostics/vendor-audit.json\`.

## Direct-only local platform replacements

P0024 replaces the original multiplayer availability queries at `14054B1B0`
and `14054B290` with a local-only provider. The caller sees ready only after
`direct_player` configured a local ID and the engine is in its existing
`onlinegame=false` LAN mode. Xbox-enabled/retail modes still fail; no vendor
account, entitlement or privilege state is made up. The LUI callback
`140245440`, which only queues an XStore licence refresh, also becomes an
inert zero-return callback in direct mode. The original GDK runtime and
its 97 xgameruntime.lib interface thunks stay unavailable.

The original Store `Live_Frame` (14054B4B0) includes other checks on Xbox
signed-in state. P0024 does not fake that global state: doing so would activate
original vendor-dependent branches, and identifying independent local consumers
must remain function-by-function work.

## Precise scope of a pass

A pass demonstrates that the audited entry points are redirected, known
network-related original imports are guarded, and none of the explicitly
forbidden GDK client DLLs was observed loading during **that run**. It does
NOT demonstrate that every process, COM broker, background Windows service,
child process, injected DLL, Lua native loader, IPC call or network route has
been examined. A loaded Winsock library is expected for direct UDP; module
presence by itself is not network activity. The Windows diagnostic additionally
uses an outbound-block firewall rule, which prevents proving the live direct
transport during that diagnostic.

The October 23 Windows smoke run (39975535197) got through prior loader and
asset-root errors and stayed running during the 90-second observation. It did
not list \`xgameruntime.dll\` among observed modules. Its captured desktop was
black and full menus, map startup and multiplayer join are **not verified**.
See \`docs/native-launch.md\`.

## Work still required for a wholly independent playable client

1. **Finish the local platform layer:** trace original UI/controller-profile
   readiness, stats save/read, and client/session ownership from GDK calls to
   game consumers. Implement local persistence and session state without
   pretending a vendor licence, token or Xbox handle exists.
2. **Complete custom game lifecycle:** get normal menus, maps, assets, script
   VMs, client-server admission, gamestate, snapshots and usercmd exchange
   working against a custom endpoint. Direct UDP alone is not a playable game.
3. **Run end-to-end, unblocked direct sessions:** use two isolated Windows
   clients with the complete original content. Capture module loads, process
   trees, DNS, TCP/UDP, Windows network/broker events and outbound traffic
   through start, connect, play, disconnect, map change and shutdown. Enforce
   that only the explicitly selected custom endpoint receives game traffic.
4. **Audit the remaining executables and dynamic code:** inspect original
   inline and unresolved platform paths, XSAPI/libHttpClient helpers, dynamic
   WinRT resolution, plugins/scripts, loaded dependencies and external
   process helpers. Do not treat an emulator call-path test or an IAT rewrite
   as a complete process-level security boundary.

The custom game must **never** connect to retail Xbox, Activision or Demonware
services, manufacture vendor auth or integrity responses, or be described as
ban-safe. Native launch without Gaming Services installed, rendered menus,
map gameplay and end-to-end outbound isolation are not yet established.

## Reproduce checks

After creating the opt-in package:

\`\`\`sh
python3 tools/offline/detachment_audit.py \
  --exe .work/direct-package/iw6mp64_offline.exe \
  --manifest .work/direct-package/manifest.json
\`\`\`

With a native \`tools/direct/native_smoke.py\` report, add
\`--runtime diagnostics/game.json --output diagnostics/vendor-audit.json\`.
Both checks return a nonzero exit code for a known-boundary regression.
