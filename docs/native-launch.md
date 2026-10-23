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
