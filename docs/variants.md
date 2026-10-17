# Faithful and enhanced builds

The repo produces two builds from one source tree (decomp-project skill, principle 8).

| | **faithful** | **enhanced** |
|---|---|---|
| Purpose | the decomp: reproduces the original exactly, bugs included; the ground truth | the faithful code plus deliberate, documented changes: security fixes, bug fixes, modernization, features |
| Source | `src/`, `include/` | `src/` + `enhanced/` (same layout as `src/`) |
| Tests | strict: `matches` means identical behaviour to the original binary | each change's intended effect, and identical to faithful everywhere else |
| Online use | not safe: it keeps the original's known vulnerabilities (docs/security.md) | intended |

## Rules

1. **`src/` contains only original behaviour.** Never "improve" a faithful function, even for an obvious bug:
   the bug is part of the original. Record it as a finding and fix it in `enhanced/`.
2. **A function defined in `enhanced/` overrides the faithful one in the enhanced build only.** This uses the same
   per-function linking as the hybrid link, so there are no conditionals in `src/`. Faithful fixes reach the
   enhanced build automatically because it shares that code.
3. **`records/patches.tsv` lists every change:** id, functions changed (build + VA), kind (`bugfix`, `security`,
   `modernize` such as frame rate, widescreen, platform ports, or `feature`), description, test reference.
4. **Two build targets; CI builds and tests both.**
5. **Changes go on verified faithful code** wherever possible. Patching unverified code makes it impossible to
   tell a fix from a decompilation error. Security-critical functions are therefore good early decomp targets.
6. **Created with the first enhancement** (raw mouse input, P0001): `enhanced/`, `records/patches.tsv`, the
   enhanced build target and tests/enhanced/.
7. **One repo** unless licensing or contributors differ (e.g. importing GPL code from iw6-mod/iw6x-client, which
   the faithful repo should not take on). A separate enhanced repo would use this one as a submodule, never a
   copy, and needs the user's decision first.

Arxan and DRM are in neither build: they aren't game source.

## Building and testing

    python3 tools/build_recon.py --build iw6mp64_MSStore_ship --enhanced   # -> build/iw6mp64_MSStore_ship/enhanced/
    python3 tests/enhanced/run.py

- The enhanced DLL compiles `src/` and `enhanced/` together. Enhanced objects link first and the linker keeps the
  first definition, so a function in `enhanced/` replaces the faithful one everywhere, calls from `src/`
  included. A function the original inlines (no address of its own) can be replaced too, as long as `src/`
  reconstructs it as a function.
- `enhanced/include/` holds headers only the enhanced build uses. Win32 functions the original exe doesn't import
  are real imports of the enhanced DLL (tools/recon/lib/*.def).
- tests/enhanced/ runs in the same emulator as the differential tests, but checks each change's intended
  behaviour instead of comparing with the original. Every patch names its tests in records/patches.tsv, and its
  tests must fail when the change is undone.
- A link map (recon.map) lets tests reach the enhanced build's own statics.

## Known bugs

Every bug found in the original is listed in `records/bugs.tsv` (security issues too, with the detail in
docs/security.md). That list is the work queue for `bugfix` and `security` changes in the enhanced build.

## Planned enhancements

- `security`: docs/security.md (community fixes, CVE-2018-20817 and related public reports, audit targets).
- Replacements for the online protections the community clients disable (docs/community-patches.md section 2):
  identity and connection security against our own backend instead of Demonware/Steam, and fastfile signature
  checking kept or replaced with our own signing.
- `modernize`/`feature`: candidates in docs/community-patches.md section 6 (FPS, FOV, ultrawide, ...), picked one
  by one, runtime-switchable where it makes sense.
