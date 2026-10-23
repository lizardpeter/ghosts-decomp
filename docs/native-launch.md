# Custom process startup diagnostics

The custom build has now been attempted as an actual Windows process, beyond the
emulator tests. This is still a startup investigation, not a playable build.

The first native diagnostic run is
[39969395538](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39969395538).
The Windows debug observer first ran a separate fixture: it captured the fixture's
debug string and its expected exit code 17. It then launched the packaged Store MP
EXE, with authentic Bink, AMD AGS and the initial pre-gfx FastFiles present.

The game image mapped at 140000000 and recon.dll mapped at 180000000. The loader
loaded Bink and AMD AGS but exited with C0000135 (missing DLL) before the initial
debugger breakpoint. Neither engine startup nor the map loader was reached. The
diagnostic workflow therefore succeeding means observation succeeded; it does
not mean the game launched successfully. The import-audit follow-up maps each
required provider without running DllMain and checks its exported symbols.

The follow-up run
[39969941352](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39969941352)
isolated XINPUT1_3.dll: loading that provider returned error 126, while every
other required provider and export mapped successfully. P0021 removes the three
legacy controller imports, which the pinned EXE requests by ordinals 2, 3 and 4
(GetState, SetState and GetCapabilities). The custom adapters report device not
connected (1167), without touching buffers or invoking another provider. The
offline/direct packages currently use keyboard/mouse; this change does not
create a replacement controller backend. The faithful source is unchanged.
Tests enter the original IAT slots with null and invalid pointers and verify
both the exact adapter selection and the absence of state writes/import calls.

With P0021 applied, run
[39970959738](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39970959738)
passed the initial loader breakpoint and mapped all required imports. The
45-second observation then found a Fatal Error dialog: initialization could not
load fileSysCheck.cfg. This was a missing diagnostic input, not a reason to
disable the engine's filesystem check. The authentic original is
`ghosts/DUMP/main/fileSysCheck.cfg` (77 bytes, SHA-256
`d753023fba1af8e6952c7d7204a1737d26bce038d689570798a46565fa6d3fbd`).
The workflow now stages that file under main/ and uses smaller source checkouts
to shorten subsequent startup iterations.

Run [39971930736](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39971930736)
cleared that filesystem error and reached `MENU_CONTENT_NOT_AVAILABLE`. The
Store failure site at 1403705E0 belongs to the FastFile-open path at 140370440:
it raises a fatal error when opening a required zone fails. This does not by
itself identify a missing map, a licence failure or a server requirement.

`records/native-startup-sources.tsv` now inventories 48 original core/UI and
English FastFiles (701,934,318 bytes). `tools/direct/fetch_startup.py` stages this
subset into the real game directory, preserving paths, checking exact sizes
and plain MD5 ETags pinned from the source inventory, and reporting newly
computed SHA-256 values. Existing valid originals are reused. No placeholder
FastFiles or content-availability bypass is supplied. Maps, streamed PAKs and
the remainder of the installation are outside this startup subset.

The observer requires a matching, active outbound-block Windows Firewall rule
for the exact executable path. The workflow also checks that the firewall
service and profiles are enabled. It removes its temporary rule after stopping
the process. Reports retain the rule evidence, DLL load events, debug strings,
first/second-chance exception addresses, exit code and timeout state. It uses the
Windows debug API without changing process memory or replacing functions at
runtime. The game package itself still uses the reviewed startup replacements.
No successful integrity response or ban-immunity claim follows from this test.

The Linux-host attempt used Wine 9.0. After correcting Wine's relocated
wineserver path in the extracted local runtime, it failed immediately with
`wineserver: socket: Operation not permitted`. This host denies AF_UNIX socket
creation before the diagnostic's additional network policy is installed. Wine
therefore cannot start its runtime service here; no game code was reached. The
host also denies ptrace, so strace could not trace the loader.

`tools/offline/wine_smoke.py` verifies the custom package hashes, launches with a
bounded timeout, and installs an inherited libseccomp policy allowing only Unix
sockets and denying io_uring setup. Its `--self-test` verifies IPv4/IPv6/netlink
socket denial and inheritance across exec. This deliberately prevents custom
UDP too. Host IPC brokers are outside that policy's isolation claim. Use the
Windows workflow when a host does not support Wine's required Unix sockets.

The complete game installation is not yet staged in the diagnostic. Later asset,
graphics, profile/statistics and connection failures must be addressed from
their own observed evidence. Native map loading, a completed join and full
process/child/IPC traffic isolation remain unverified.

The reference-server LiveAntiCheat_Init limitation is explicitly recorded below
matches. That server clears its feature-ban records inline; the faithful Store
wrapper calls a separate controller-reset helper and has a different command
node. The Store differential test passes. A reference-build failure is expected
and is not evidence that those two builds share one initializer implementation.
