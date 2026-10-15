# Verification

How a function earns `compiles` and `matches` in `records/functions.tsv`. The method is BO1's
(black-ops-1-decomp `docs/verification.md`); this page records what changes for an x64 MSVC 2012 game.

## compiles

`tools/build_recon.py` builds everything under `src/` with clang `--target=x86_64-pc-windows-msvc`
(Win64 calling convention, MSVC x64 C++ mangling) into `build/recon.dll`, exporting every function under
its decorated name. Tests look functions up by the original decorated name, so a wrong prototype shows
up as a missing export.

That only works where an original decorated name is known, i.e. from a reference build's MAP or PDB.
For functions known only from the stripped retail exe there is no decorated name; they are tested by
address (the match records give the address and the prototype).

## Hybrid link (x64)

Anything the reconstruction uses but does not define resolves to the original binary: functions become
`jmp qword ptr [rip+0]` followed by the 8-byte original address (x64 has no `push imm64`), data becomes an
absolute symbol. The DLL is linked at 0x180000000, clear of the exe at 0x140000000.

## matches (differential)

Same contract as BO1: the original and the reconstruction run in one Unicorn address space on identical
inputs; return value, every pointer buffer and every global write must match exactly; inputs on which the
original faults are skipped; too few usable inputs means untestable, never passed.

The harness (`tests/differential/harness.py`) is ported to x64. What changed from BO1:

- `UC_MODE_64`, a GS-based TEB (`gs:[0x30]` self pointer, `gs:[0x60]` PEB) for code that reads it.
- Win64 calling convention: the first four arguments in rcx, rdx, r8, r9, or xmm0 to xmm3 for floating
  point (by position, not by count of each kind); 32 bytes of shadow space above the return address;
  rsp 16-byte aligned before the call; return in rax or xmm0.
- No x87 state to set up: x64 MSVC does all floating point in SSE. The CPU starts with MXCSR 0x1F80.
  The x87-specific workarounds from BO1 (unrounded ST0 returns, `X87_MATH`) don't apply.
- An Arxan-protected build runs from its **unpacked** image (tools/unpack); the harness checks `unpacked_sha256`.
- VC11's x64 CRT math (`sin`, `pow`, ...) is called as ordinary functions in the original; the hybrid link
  routes the reconstruction's calls to the same original routines.

## Byte matching

Would need the VC11 (VS2012 Update 4) x64 compiler on a Windows runner. The retail builds are optimized
(and probably LTCG, to be measured as on BO1), so byte matching is not the goal for them; behavioural
equivalence is.

## First run (PS4 server reference)

- Sanity: original functions called directly give the expected results (`AngleNormalize360(-90) = 270`,
  `Vec3Normalize([3,4,0])` returns 5 and writes `[0.6, 0.8, 0]`, `vectoyaw([0,1,0]) = 90`, `I_stricmp`).
- `AngleNormalize360` and `AngleDelta` (universal/com_math.cpp) reconstructed and passing on ~290 generated inputs
  each (NaN, infinities, signed zeros), with `floorf` resolved to the original CRT through the hybrid link.
- Mutation checks: a changed constant fails on a concrete input; a wrong return type no longer drops the
  function silently, the build stops with "prototype differs from the original's decorated name".
