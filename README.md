# ghosts-decomp

Decompilation of **Call of Duty: Ghosts (IW6)**, PC x64. The final target is the Microsoft Store build
(multiplayer first), reportedly without Arxan; it is being uploaded.

| Build | Linked | Role |
|---|---|---|
| Microsoft Store MP/SP | (pending) | **target** |
| `iw6mp64_ship` (Steam MP, 3.15) | 2018-04-25 | related: Arxan-protected, original Activision signature; community address maps exist for it |
| `iw6sp64_ship` (Steam SP) | 2015-02-10 | related: Arxan-protected, modified after release |

Compiler: MSVC 2012 (VC11) x64. Reference builds with symbols are being added (docs/prior-art.md).

- How the repo is organised and the rules for changing it: [AGENTS.md](AGENTS.md)
- Progress: [STATUS.md](STATUS.md)
- What is being reversed and where the originals live: [target.toml](target.toml)
- The builds and their provenance: [docs/retail-builds.md](docs/retail-builds.md)
- Decrypting the Arxan-protected exes: [docs/arxan.md](docs/arxan.md)

## Pipeline

1. `tools/unpack/arxan.py` emulates each protected exe's entry stub and writes the decrypted image
   (sha256 pinned in `target.toml`).
2. `.github/workflows/ghidra.yml` imports each build into Ghidra (with its PDB when it has one), exports
   functions, call graph, symbols, strings and types, decompiles every function, and commits the results to
   `analysis/<build>/`.
3. `tools/pdb/extract.py` turns a reference build's PDB and/or MAP into `analysis/<build>/pdb/` and `map/`.
4. `tools/status.py` combines `analysis/` with the authored `records/` into `STATUS.md` and the graph.

The game files themselves are never committed.
