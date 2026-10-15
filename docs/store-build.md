# The Microsoft Store build (final target)

Status: both executables are in R2 (`ghosts/DUMP/`); the rest of the package is still uploading.

## The executables

| | iw6mp64_MSStore_ship.exe | iw6sp64_MSStore_ship.exe |
|---|---|---|
| sha256 | dd63cb5b…0757 | 5e232b0f…abd5 |
| linked | 2024-11-18 18:02:39 | 2024-11-18 18:01:11 |
| PDB | `d:\workspace\outrun\iw6-depot\iw6\game\pc\iw6mp64_MSStore_ship.pdb` {0A83874F-F6E2-4423-A596-766DECB765C4} age 4 | `...\iw6sp64_MSStore_ship.pdb` {6FCA2EAC-8BF1-4658-A6CA-C97D35615CA1} age 6 |
| `.text` | 8.0 MB, entropy 6.10 | entropy 6.01 |

- **No Arxan:** normal `.text` entropy, entry point in `.text`, ordinary relocations (31 KB), none of the Steam
  builds' stub sections. **No Steam:** no `steam_api64.dll` import.
- **Toolchain:** linker 14.29, objects from cl 19.29.30154 (VS2019 16.11), dynamic VC14 CRT (`MSVCP140`,
  `VCRUNTIME140`, UCRT); a POGO debug record, so link-time code generation. Very different code generation from
  the VS2012 reference servers.
- **Platform:** `xgameruntime.dll` loaded at runtime (`XGameRuntimeInitialize`), Xbox sign-in (`XUserAddAsync`),
  Xbox Live services (`XblInitialize`, `XblContext`), `XCurl`/`WinHTTP` for HTTP, `bcrypt`/`CRYPT32`, and the
  process lifetime notification API (`api-ms-win-core-psm-appnotify`). A `.xbld` section marks a GDK build.
- Version resource still says ProductVersion 3.15, OriginalFilename `iw6mp64_ship.exe`.
- `GameLaunchHelper.exe` is not in the upload yet; it isn't needed for analysis.

## From the package (MicrosoftGame.config, appxmanifest.xml)

- Package `38985CA0.CallofDutyGhostsPCMS`, version **4.0.9.0**, Store id 9PJH49B6K7DD, Xbox title id `66cdd1f0`,
  MSA app id 45804377-b595-4810-8454-b58e429f36ea.
- Executables: **`iw6mp64_MSStore_ship.exe`** (multiplayer, the first target) and `iw6sp64_MSStore_ship.exe`.
  Both are launched through the GDK's `GameLaunchHelper.exe`.
- **Toolchain:** the package depends on the **VC14** runtime (`Microsoft.VCLibs.140.00.UWPDesktop`), so the exes
  were rebuilt with MSVC 2015 or later, not VS2012 like the servers and the Steam exes. Expect different code
  generation from the reference: structural matching gets harder, while strings and the call graph still work.
  Confirm with the Rich header once the exe is in.
- **Microsoft GDK title:** `AdvancedUserModel` (multi-user Xbox sign-in through XUser), the `appLicensing`
  capability (Store licence checks), a `MultiplayerProtocol` registration (invites), and GDK runtime DLLs in the
  package (`XCurl.dll` for HTTP, `XGamepad.dll`, `ControllerManager.dll`). DirectX 11 is still the dependency.

## Running it for testing

Goal: get the original Store exe into a lobby or match **offline**, so that decompiled functions can be swapped in
and tested in the running game.

1. Map the platform layer: every GDK call (XGameRuntime initialisation, XUser sign-in, XStore licence, XGameSave,
   Xbox Live services, invites) and the game functions that make them.
2. A loader, kept apart from `src/` and `enhanced/`, starts the exe outside its package and answers those calls
   locally: an offline signed-in user, a valid licence, local saves. Every patch it applies to the original is
   listed with address, reason and evidence.
3. Reach a private match with bots or a local dedicated server, fully offline.
4. Later: online play against our own backend.

Rules:
- The licence and sign-in code is Activision's own source, unlike Arxan. The faithful decomp reproduces it; the
  enhanced build replaces it with a clean platform layer. Only the loader strips it from the original binary, for
  testing.
- A patched client never connects to Activision's or Xbox's live services. Testing is offline or against our
  own servers.
