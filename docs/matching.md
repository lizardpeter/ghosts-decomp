# Matching the Store build to the reference

`tools/match/match.py <reference> <target>` gives target functions the identity of reference functions, with
method, confidence and evidence per pair, into `analysis/<target>/match/functions.tsv`. Content only, never
position (the Store build is LTCG-optimised and reordered).

## Stages (x64)

1. **string**: a string referenced by exactly one function in each build. x64 code reaches data RIP-relatively,
   so every function is disassembled and `[rip+disp]` operands are resolved (BO1's x86 matcher scanned for
   absolute addresses instead).
2. **constant**: at least two distinctive immediates, each unique to one function on both sides.
3. **named**: a string tied to exactly one function by a registration (a string and a function address loaded for
   the same call, `Cmd_AddCommand("name", Func)`) or by a `{name, ..., function}` data-table entry.
4. **callee / caller**: call-graph propagation from matched pairs, with structural checks (shared strings, size
   ratio, callee count).

## Validation on ground truth: Xbox One server vs PS4 server

The Xbox One server was analysed **blind** (Ghidra without its PDB, `ghidra_pdb = false`) and matched against the
PS4 server, then scored against its own PDB/MAP names (`tools/match/validate.py`; folded functions count as
correct when their name sets intersect).

| method | correct | wrong | precision |
|---|---:|---:|---:|
| string | 1,407 | 3 | 99.8% |
| constant | 70 | 0 | 100% |
| named | 189 | 0 | 100% |
| callee | 5,200 | 1 | 100.0% |
| caller | 5,043 | 4 | 99.9% |
| **all** | **11,909** | **8** | **99.9%** |

Coverage: 11,917 of 18,093 functions (65.9%). (BO1, same method: 97.6% precision, 32.6% coverage.) Both are
VS2012 server builds, so this is the easy case; the Store build is harder.

## Store build (iw6mp64_MSStore_ship) against the PS4 server

**5,467 of 23,249 Store functions matched (23.5%)**: string 801, constant 29, named 120, callee 2,147, caller
2,370. That is about 31% of the server's functions.

There is no ground truth for the Store build, so precision is estimated two ways:

- **Call-graph consistency** (the share of a matched function's matched callees that are callees of its server
  counterpart): 90.8% overall (string 87.2%, named 87.4%, constant 83.7%, callee 91.3%, caller 92.2%). On the
  Xbox One pair the same measure reads 99.9%, equal to the true precision there. On the Store build, inlining under
  LTCG adds and removes call edges, so a lower figure is expected even for correct pairs (BO1 retail: 88 to 91%,
  confirmed correct by manual review).
- **Manual review** of 6 random propagated matches against the server pseudocode (`SV_BotCanTargetSentient`,
  `G_GetPlayerViewOrigin`, `Dvar_RegisterFloat`, `BG_GetPlayerEyePosition`, `BG_GetPlayerDamage`, a DemonWare
  `bdHashMap::next`): all 6 consistent (parameter counts and types, structure, and the matched callees agree).

Why coverage is lower than on the server pair: the Store build is a client (renderer, UI, Lua/LUI and client game
code the server lacks), compiled by VS2019 with LTCG (more inlining, different code shape), and the server
registers few named commands (315 against the client's 1,144).

## Next

- Fuzzy structural matching for the rest (instruction n-grams, constant sets, CFG shape), scored the same way.
- Record inlined server functions as inlined into their Store callers rather than unmatched.
- Bring in the client-side names (Xbox 360 prototype MAP, community address maps via the Steam build).
