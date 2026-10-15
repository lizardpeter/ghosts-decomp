# Prior art and symbol sources

What exists for IW6 outside this repo, and what it is worth to us. Surveyed 2026-10 (see git history);
re-check before relying on availability.

## No decomp exists

No Hex-Rays-style reimplementation (like KisakBlack for BO1 or KisakCOD for CoD4) exists for IW6, nor for
IW5, S1, H1 or IW7. The community work on Ghosts is runtime clients that hook the retail exe.

## Hook clients

| Project | License | Targets | Contents |
|---|---|---|---|
| AlterWare **iw6-mod** (git.alterware.dev/alterware/iw6-mod) | GPL-3.0 | Steam `iw6mp64_ship.exe` / `iw6sp64_ship.exe`; identifies them by the DWORD at 0x140001337 (`0xDB0A33E7`, `0xA6D147E7`) | `symbols.hpp`: 258 named functions/variables with MP and SP addresses; ~990 hard-coded addresses in total; `structs.hpp`: ~218 struct/enum definitions, few size checks. Hooks and helpers, not decompiled game code. |
| XLabs **iw6x-client** (taken down; archive.org snapshot, forks incl. lizardpeter/iw6x-client) | GPL-3.0 (to confirm from the source) | Same Steam builds | Predecessor of iw6-mod; same kind of data. |

**Our targets are exactly these builds:** `iw6mp64_ship` has 0xDB0A33E7 and `iw6sp64_ship` has 0xA6D147E7 at
0x140001337. iw6-mod's addresses therefore apply to our analysis without any matching step.

How we use it: names and addresses are facts, and enter `records/` as identifications with method
`iw6-mod symbols.hpp` and that evidence, to be checked against our own analysis (strings, call graph).
Its *code* is not imported: that would make this repo GPL-3.0, which is the user's decision.

Arxan: these clients patch at runtime and let the stub decrypt `.text` first; they do not publish a
decrypted exe. We decrypt by emulation instead (`docs/arxan.md`).

## Symbol builds

- **Xbox 360 prototypes with linker MAPs.** The May 9 2013 (build 507466) and May 21 2013 (build 515054)
  prototypes on archive.org contain `1-iw6sp.exe` with **`1-iw6sp.map`**. The May 9 MAP has 35,899 named
  functions with MSVC-decorated names (argument types included) across 1,534 objects: names, prototypes and
  the source-file layout of the singleplayer engine, six months before release. PowerPC, so it can be used
  only by content-based matching (strings, constants, call graph), never by code comparison.
  Hidden Palace says the full archives also carry PDBs; unverified (the full download is 9.3 GB).
- Later 360 prototypes (Jul 19, Aug 29 2013, Sep 23 MP beta): symbol status unknown.
- No PC PDB or MAP is known publicly. (The user mentioned a PC server build with EXE and MAP; R2 key
  pending.) Ghosts has no separate dedicated-server exe; servers ran `iw6mp64_ship.exe`.

## Microsoft Store build

"Call of Duty: Ghosts (Windows)" (Store product 9PJH49B6K7DD) was released on 2024-12-16 with other older
CoD titles on the Xbox app. Whether it is Arxan-free and which code it carries is not public; the user is
uploading a copy (reportedly without Arxan). To check when it arrives: PE timestamp, PDB path/GUID, Rich
header (compiler), and how much code it shares with the 2018 Steam build.

## Engine relatives

Ghosts descends from IW5 (MW3), which descends from IW4/IW3. KisakCOD (CoD4) and KisakBlack (BO1), both
GPL-3.0, are structural models and name sources for shared engine code, not code to import.
