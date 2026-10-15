# The Microsoft Store build (final target)

Status: package metadata and data files are in R2 (`ghosts/DUMP/`); the executables are still uploading. The
exe-level findings (protection, link date, PDB path, compiler) are to be filled in when they arrive.

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
