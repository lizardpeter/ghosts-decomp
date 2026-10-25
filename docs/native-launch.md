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

That complete startup subset still produced the same error in run
[39972909100](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39972909100).
Inspection then exposed the launcher's path mismatch: 1405488C0 builds its
CreateFileA paths using 140548F90, which caches the EXE parent through
GetModuleFileNameA. This ignores the fs_basepath used by the earlier filesystem
check. Our separate package directory therefore points the database at the
wrong root even though the selected working directory contains the originals.

P0022 replaces that helper only in custom offline/direct packages. It caches
the startup working directory under an SRW lock, retains the original 256-byte
path bound, and returns null on API failure/oversize so callers retain their
existing relative-path fallback. LaunchDirect.ps1 already sets WorkingDirectory
to GameDirectory. Tests enter the patched original helper with a spaced path,
API failure and an oversized result; they assert the actual returned root and
lock/API/unlock order. Original content checks remain in place.

Run [39974085602](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39974085602)
with P0022 cleared the fatal content error. The game stayed open for the full
45-second observation without a fatal dialog or a second-chance exception.
This establishes progress through startup, not a rendered menu or gameplay.
The next diagnostic allows 90 seconds and captures the disposable test desktop
before stopping the process, so an open window is not mistaken for a completed
menu load. Pending zone names are a read-only queue snapshot and may include
already processed requests; they are not a file-open failure trace.

Run [39974678078](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39974678078)
kept the process open for 90 seconds, without a fatal dialog. Its 1024x768 desktop
capture was entirely black. That is not evidence of a rendered menu and cannot
alone distinguish a game stall from an unavailable test-session display. The
observer now briefly suspends and resumes each game thread to collect read-only
register/stack snapshots at timeout, and records CPU time. The workflow preserves
runtime log files and display-adapter metadata for the next diagnosis.

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

P0025 adds precise, non-sensitive `OutputDebugStringA` milestones to the **direct
profile only**: `IW6D:DIRECT_COMMANDS_REGISTERED`,
`IW6D:LOCAL_PROFILE_CONFIGURED`, `IW6D:DIRECT_JOIN_CHALLENGE_READY`
and `IW6D:DIRECT_MAP_START_REQUESTED`. The Windows workflow records which
events the actual game process emitted in
`native-launch-diagnostics/direct-milestones.json`. Missing events do not
make the structural smoke test fail: they pinpoint the first unexecuted game
boundary, rather than falsely claiming a menu or map was reached. In
particular, `DIRECT_MAP_START_REQUESTED` is emitted **before** invoking
the original map-start function and is not evidence that a map loaded.
No player names, IDs, tokens or endpoints appear in the markers.

Native [40131610432](https://github.com/lizardpeter/ghosts-decomp/actions/runs/40131610432)
was the first debug run with P0025 milestones. It recorded
`IW6D:DIRECT_COMMANDS_REGISTERED` but **not** `LOCAL_PROFILE_CONFIGURED`,
the join request or a map-start request. The 90-second capture remained black.
This proves custom command registration executed, not that the startup
`+direct_player` line had been consumed by the engine's command buffer.

P0029 now parses a single exact `+direct_player` ID/name pair from the Windows
process command line during NET_Init. Parsing is bounded, quote aware, and
delegates all identity validation to the existing local profile provider; it
does not fake GDK objects, open sockets, change dvars, or launch maps. In
[native 40201268224](https://github.com/lizardpeter/ghosts-decomp/actions/runs/40201268224),
both `DIRECT_COMMANDS_REGISTERED` and **`LOCAL_PROFILE_PREPARED`** were
observed from the actual game. Its normal deferred command still had not
executed. New native jobs additionally require these two milestones to pass.

The read-only stack snapshot from that prior run was mapped back to generated
Store pseudocode by
`tools/analysis/inspect_native_stacks.py`: the initialisation call chain
includes `140631540` calling `14036DF30`; the latter enters
`while (DAT_145CAEDF8 != 0)` with event pumping and `Sleep(1)`. Other
snapshots include `14053DA90`/ `14053D490` waiting on a separate
synchronisation flag and thread worker code. These are **observations of
waiting**, not proof of the flag's producer or the reason it remains set.
`tools/analysis/inspect_loader_flag.py` finds writes/reads of the flag in
generated Store code before any proposed change to the loader.

The complete game installation is not yet staged in the diagnostic. Later asset,
graphics, profile/statistics and connection failures must be addressed from
their own observed evidence. Native map loading, a completed join and full
process/child/IPC traffic isolation remain unverified.

The reference-server LiveAntiCheat_Init limitation is explicitly recorded below
matches. That server clears its feature-ban records inline; the faithful Store
wrapper calls a separate controller-reset helper and has a different command
node. The Store differential test passes. A reference-build failure is expected
and is not evidence that those two builds share one initializer implementation.
