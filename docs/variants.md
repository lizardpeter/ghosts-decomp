# Two variants: faithful and patched

The repo produces two builds from one source tree.

| | **faithful** | **patched** |
|---|---|---|
| Purpose | the decomp: behaves exactly like the original, bugs included | a version to play: security fixes, replaced online checks, enhancements |
| Verified against the original | yes, every function (differential tests, records/functions.tsv) | only where it intentionally doesn't differ |
| Build flag | default | `IW6_PATCHED=1` (`tools/build_recon.py --variant patched`, added with the first patch) |
| Online use | not recommended: it has the original's known vulnerabilities | intended |

## Rules

1. **`src/` is faithful.** A function in `src/` reproduces the original's behaviour, including bugs, and earns
   `matches` only by passing the differential test. Never "fix" something in passing; record it as a finding.
2. **Changes live in `patches/`, mirroring `src/`'s layout.** Two kinds:
   - **Replacements:** a whole function rewritten in `patches/<same path>.cpp`. In a patched build the linker uses
     it instead of the `src/` version (`build_recon.py` drops the faithful definition of any symbol a patch file
     defines). This is the default; it keeps `src/` free of conditionals.
   - **Points:** a check that has to sit in the middle of a long function and doesn't justify duplicating it.
     Written in `src/` as `IW6_FIX(id) { ... }`, which compiles to nothing in the faithful build. Use sparingly;
     each one names a fix id.
3. **Every change has a record** in `records/patches.tsv`: `id`, `kind` (security | replacement | enhancement |
   qol), `functions` (original symbols touched), `doc` (where it is explained), `test` (the test that shows the
   original's behaviour and the patched behaviour), `source` (our own finding, or e.g. `iw6-mod security.cpp`, as
   the source of the *idea*; their code is GPL and isn't copied).
4. **Security fixes come with a test that triggers the original bug** in the emulator: the faithful build must
   show the bug (crash, out-of-bounds write, hang), the patched one must not. That keeps the fix list honest.
5. **Enhancements are switchable at runtime where it makes sense** (dvars: FOV range, FPS cap, ultrawide), so the
   patched build can still be run "stock".

## Starting list (patched)

- Security: docs/community-patches.md section 1, plus publicly reported exploits once surveyed.
- Replacements for disabled online protections (section 2): identity and connection security against our own
  backend instead of Demonware/Steam, fastfile signature checking kept or replaced with our own signing.
- Arxan/DRM: absent from both variants. It isn't game source, so the faithful build doesn't reproduce it either.
- QoL/enhancements: section 6, picked one by one.

## While the reconstruction is incomplete

Both variants run hybrid (docs/verification.md): whatever isn't reconstructed yet runs the original code. A patch
can only apply to a function that has been reconstructed, so security-relevant functions are good early targets.
Until then a fix can be applied the community way, as a hook on the original function from the patched DLL,
recorded with kind `security` and marked temporary.
