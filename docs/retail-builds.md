# Builds

The goal is the final retail build: the **Microsoft Store** release (product 9PJH49B6K7DD, Dec 2024),
reportedly without Arxan, multiplayer first. Its files are still being uploaded to R2 (`ghosts/DUMP/`); this
page is updated when they are in. Everything else is reference or supporting material.

## Reference builds: Windows dedicated servers with PDB and MAP

Ghosts' console matches were hosted on Windows x64 servers ("dh_server", dedicated host). There is one build
per console platform, each with its full private PDB and linker MAP. They are PC x64 binaries, unencrypted,
built by the same compiler family as the retail client. They are the source of names, prototypes, types,
source files and line numbers, as CoDMPServer was for BO1.

| Build | PDB name | Linked | Changelist | ProductVersion | sha256 (exe) |
|---|---|---|---|---|---|
| **iw6_ds_ps4** (primary) | iw6mp64_dh_server_orbis.pdb (age 108) | 2014-10-25 | 715098 | 3.15 | 46d92b7e…6d72 |
| iw6_ds_xb3 | iw6mp64_dh_server_durango.pdb (age 42) | 2014-02-22 | 665584 | 3.8 | 3d4781fd…0573 |
| iw6_ds_ps3 | iw6mp64_dh_server_ps3 | 2014-10-27 | 715098 | | e7e8b2bb…6636 |
| iw6_ds_xenon | iw6mp64_dh_server_xenon | 2014-10-27 | 715098 | | 1e6d1e31…3a |

R2 holds each file twice (`iw6_ds.*` and `iw6_ds_<platform>.*`, byte-identical by etag); target.toml uses
`iw6_ds.*`.

Why PS4 is primary: newest changelist (shared with PS3/360, whose hosts ran the same code) and the same
ProductVersion, 3.15, as the final Steam client. The Xbox One host is eight months older; as a second fully
symbolised build it is the ground-truth pair for validating the matcher (match it blind against PS4, score
against its own PDB), as CoDMPServer_s was for BO1.

### What the PS4 server PDB holds (tools/pdb/extract.py)

- 17,504 procedures (S_GPROC32/S_LPROC32), 1,090 of them without a type; 2,437 modules; 97,429 MAP publics;
  ~68k type records; line tables for 14,924 function starts.
- Source root `c:\trees\iw6\code_source\src\` (top-level folders: game, bgame, gfx_d3d, server_mp, qcommon,
  universal, game_mp, database, physics, win32, ui, effectscore, script, vehicle, xanim, ...). Beside it:
  `demonware\`, `libs\`, `speex-1.1.9\`, `common\`, plus Havok Script, NVIDIA and the VC11 CRT.
- VS2012 x64 PDBs carry no per-module primary source file. The extractor derives it from the module's own
  functions' line tables (the source with the object's stem, else the most common one).
- **Identical code folding** (/OPT:ICF) is on: tiny functions with identical bodies share one address, so a
  function's line-table entry can belong to a different function (e.g. `SV_GetMigrationDefaultFlags` carries
  `gfx_d3d/r_dvars.cpp`). The module is the reliable source attribution.
- `pdb/locals.tsv` is empty for now: x64 locals are RSP-relative after the prologue and need the frame size
  from the unwind data to become Ghidra stack offsets. Ghidra's own PDB analyzer applies them meanwhile.

### Compared with BO1's servers

These are **ship builds** (config `ServerDH_ORBIS_Ship`): optimized, unlike BO1's effectively unoptimized
server builds. So byte-matching the reference is not realistic either; behavioural equivalence is the bar
throughout. The reference and the retail client should still be much closer in code generation than on BO1.

## Related builds (no symbols): Steam exes from Plutonium's set

| Build | Linked | Notes | sha256 |
|---|---|---|---|
| iw6mp64_ship | 2018-04-25 | final Steam MP, ProductVersion 3.15; valid Activision Authenticode signature (digest recomputed and matched), so unmodified | 5a6a109b…1518 |
| iw6sp64_ship | 2015-02-10 | Steam SP, older tree `c:\trees\iw6`; unsigned, checksum zeroed, no `.reloc`: modified after release | 0134cbdc…50f5dd |

Both are Arxan-protected: `.text` is encrypted on disk (every 64 KB block at entropy 7.66 to 8.00) and the
entry stub decrypts it at startup. `tools/unpack/arxan.py` reproduces that (docs/arxan.md). They are the builds
iw6x-client and iw6-mod target (DWORD at 0x140001337: MP 0xDB0A33E7, SP 0xA6D147E7), so those projects' named
addresses apply to them directly (docs/prior-art.md).

Compiler (Rich headers): VS2012 linker 11.0; the MP client's objects mostly cl 17.00.61030 (Update 4), the
servers' and SP client's 17.00.60315 (Update 2).
