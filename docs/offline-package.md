# Experimental offline package

P0011 adds a startup-only integration experiment for the **pinned Store multiplayer executable**.
It is not a verified runnable game or a whole-process egress guarantee. Native Windows launch,
asset loading, graphics, menu progression and outbound traffic capture remain unverified.
The default faithful and enhanced DLL builds retain their existing behavior. `src/` is unchanged.

## Build and test

With the normal LLVM toolchain and pinned originals available:

```sh
IW6_ORIGINALS=.work/originals python3 tools/build_recon.py --build iw6mp64_MSStore_ship --offline
IW6_ORIGINALS=.work/originals python3 tests/offline/run.py
python3 tools/offline/package.py \
  --original .work/originals/iw6mp64_MSStore_ship.exe \
  --output .work/offline-package
```

The output directory must be new. The packager checks the original SHA-256 from `target.toml`,
requires the offline DLL entry point and fixed bases, and never edits the original. Do not commit
packaged executables or originals. `manifest.json` records both output hashes, all original entry
bytes and replacement branches, and every redirected import. It explicitly records that native
launch and whole-process egress have not been verified.

## Integration boundary

The packager redirects the 31 original function entries covered by P0005/P0006/P0007/P0008/P0010
to their enhanced exports. Calls and function pointers that enter those original addresses now
reach the guards. It does not redirect arbitrary engine exports, interior entry points, or every
possible vendor function. No function is promoted to `integrated` based on these emulator tests.

A new `.iw6off` section holds unbound import descriptors, independent import lookup tables and
an explicit bootstrap import. Original IAT slot addresses stay unchanged; descriptors are split
into contiguous runs when a provider changes. The original WinHTTP and XCurl imports become
`recon.dll` failure adapters, so these providers are no longer imported by the EXE. Selected
Winsock socket creation, send, connect, extension lookup and DNS imports fail with WSAEACCES.
Cleanup and address-formatting APIs remain available. Original process launch, shell launch,
CRT command execution, COM activation and ETW reporting imports are also refused.

The original LoadLibrary/GetProcAddress imports use wrappers that reject known networking/GDK
module basenames and dynamic WinRT activation entry points. Dynamic requests for loader/procedure entry points return the same guarded wrappers; dynamic
process and shell launch requests return failure adapters. Other libraries remain available
for rendering and local runtime needs. The adapters' own kernel/error imports go directly to OS
DLLs, avoiding recursion through the original IAT. This is a reviewed set of boundaries, not a
complete audit of all dynamic resolution, syscalls, loaded libraries, helper processes or IPC.
Generic failure adapters ignore unused Win64 arguments; DNS, COM and event registration clear
output pointers. Failed CURL multi operations do not initialize caller counters; callers must
honor the failure return. Invalid non-null output pointers retain the normal API caller contract.

Both images must load at their preferred bases (EXE `140000000`, DLL `180000000`). DLL attach
checks the bases and package section marker and terminates an unprepared host. The packager
removes stale binding/signature directories, retains NX and updates the PE checksum. The marker
is a format check, not a cryptographic integrity boundary. The sandbox launcher verifies output
hashes before startup. PE editing invalidates any original signature and may encounter loader,
CFG, packaging or startup assumptions that emulation cannot establish.

## Contained Windows launch experiment

On a Windows host with Windows Sandbox installed, copy the package to a separate folder and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ConfigureSandbox.ps1 -GameDirectory 'D:\Games\Ghosts'
```

Open the generated `Offline.wsb`. It disables Sandbox networking and maps both package and game
folders read-only. The guest launch script refuses to start if an active adapter is present or an
adapter query fails, verifies package hashes, and uses `C:\GhostsData` for writable game data.
It points `fs_basepath` to the mapped game assets. Missing dependencies, Store startup assumptions,
Sandbox graphics support or asset path requirements can still prevent launch; none has been
validated on Windows here. Direct execution outside the sandbox loses this containment.

Network-disabled containment is deliberately broad: it also prevents connections to a future
custom dedicated server. A future dedicated transport needs its own implementation and a
separately reviewed launch policy. Do not enable unrestricted networking based only on these stubs.

## What is tested

`tests/offline/run.py` creates a package from the pinned original and models loader import
resolution in Unicorn. It checks all 31 original entry jumps, executes original account code
through the new shared guard, calls original transport IAT targets through actual failure code,
checks dynamic library/procedure rejection and allowed rendering lookups, verifies attach
refusal and marker validation, checks PE structure/checksum, and rejects invalid originals and
output-directory reuse. This establishes these machine-code boundaries, not native game startup.

PE structure reference: <https://learn.microsoft.com/en-us/windows/win32/debug/pe-format>.
Sandbox configuration: <https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file>.
