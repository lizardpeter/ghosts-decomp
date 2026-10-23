# Vendor service disconnection in the custom process

P0018 removes ten vendor integrity/reporting service entry points from both the offline and direct packages.
The faithful source remains separate. The custom profiles do not initialize this service, accept its challenge
jobs, sample memory for it, build its response blobs, or submit its validation reports. A declined challenge
returns zero; no successful hash, clean scan result or remote attestation is fabricated.

| Store entry | Original role | Custom behavior |
|---|---|---|
| 1405F0A80 | LiveAntiCheat_Init | No initialization or banCheck registration |
| 1405EFD60 | banCheck command/service query | No service query |
| 1405F0AB0 | Queue incoming challenges | No queue mutation or payload reads |
| 1405EFAC0 | Memory-hash request processing | Unavailable, without reading request or memory |
| 1405F0D50 | Challenge processing/dispatch | Unavailable, without reading request |
| 1405F10E0 | Service pump | No callbacks |
| 1405F1AB0 | Match validation-infraction reporting | No match-data collection/submission |
| 1405F2230 | Automatic feature query/update | No callbacks |
| 1405F2280 | Build controller response blobs | No collection, serialization or SDK calls |
| 1405F24F0 | Submit/poll pending response tasks | No SDK calls |

The identified subsystem is online/live_anticheat.cpp in the PS4 reference PDB; the Store match table and
Store disassembly provide the target entry points. Its original hash dispatcher invokes text-section lookup
and hash jobs. Its response-blob path includes controller/hardware/timing data, and pending-send code enters
Demonware anti-cheat service methods. Removing the entire lifecycle avoids retaining a scanner that merely
fails to upload later. These are startup-only changes: attaching the DLL to an already running official
process, unloading live SDK objects, and hot-swapping providers are not supported.

`tests/offline/vendor_tasks.py` enters the patched original EXE addresses for both package profiles. It passes
null and deliberately invalid payload pointers, rejects any execution of another original function, and
asserts no reads requiring those payloads, no state writes, and no OS/provider imports. Existing transport,
account and reporting guards remain in force. Ordinary faithful source is not changed to behave offline.

This work does not establish that every possible integrity check, loaded DLL, crash reporter or IPC path has
been removed. It does not establish ban immunity. Direct UDP is for a custom peer/server, not an official
service. Native Windows launch and traffic capture during startup, gameplay, disconnect and shutdown remain
required before claiming complete vendor isolation. No official online compatibility is claimed.

The startup function LiveAntiCheat_Init at 1405F0A80 is also reconstructed faithfully in
`src/online/live_anticheat.cpp`. Its differential test checks reset/controller-reset/command-registration
order and arguments, including the original command node and callback. A skipped-initializer mutant is
detected. The faithful implementation still performs those calls; packaged custom profiles remove them.
