# ghosts-decomp

Decompilation of **Call of Duty: Ghosts (IW6)**, PC x64. The final target is the Microsoft Store build
(multiplayer first): no Arxan, rebuilt with VS2019 in 2024.

| Build | Linked | Role |
|---|---|---|
| `iw6mp64_MSStore_ship` / `iw6sp64_MSStore_ship` (Store, 4.0.9.0) | 2024-11-18 | **target**, GDK platform layer |
| `iw6_ds_ps4` (+ Xbox One, PS3, 360 hosts) | 2014 | reference: Windows dedicated servers with full PDB and MAP |
| `iw6mp64_ship` (Steam MP, 3.15) | 2018-04-25 | related: Arxan-protected, original Activision signature; community address maps exist for it |
| `iw6sp64_ship` (Steam SP) | 2015-02-10 | related: Arxan-protected, modified after release |

Compilers: Store build VS2019 (x64, LTCG); servers and Steam exes VS2012 (x64).

- How the repo is organised and the rules for changing it: [AGENTS.md](AGENTS.md)
- Progress: [STATUS.md](STATUS.md)
- What is being reversed and where the originals live: [target.toml](target.toml)
- The builds and their provenance: [docs/retail-builds.md](docs/retail-builds.md)
- How Store functions get their original names, and how accurate that is: [docs/matching.md](docs/matching.md)
- Planned enhancements and the maths behind them: [docs/roadmap.md](docs/roadmap.md)
- The Store build (final target) and how it is run for testing: [docs/store-build.md](docs/store-build.md)
- Decrypting the Arxan-protected Steam exes: [docs/arxan.md](docs/arxan.md)
- Input (keys, gamepad, mouse) and how the mouse reaches the view angles: [docs/input.md](docs/input.md)
- Field of view, its effect on mouse sensitivity, and the aspect ratio: [docs/view.md](docs/view.md)
- Every way the game reaches the network, and where to cut it: [docs/network.md](docs/network.md); the GDK (Xbox) runtime calls: [docs/gdk.md](docs/gdk.md)
- The renderer's Direct3D 11 boundary, and what a Vulkan backend must provide: [docs/renderer.md](docs/renderer.md)

## Pipeline

1. `tools/unpack/arxan.py` emulates each protected exe's entry stub and writes the decrypted image
   (sha256 pinned in `target.toml`).
2. `.github/workflows/ghidra.yml` imports each build into Ghidra (with its PDB when it has one), exports
   functions, call graph, symbols, strings and types, decompiles every function, and commits the results to
   `analysis/<build>/`.
3. `tools/pdb/extract.py` turns a reference build's PDB and/or MAP into `analysis/<build>/pdb/` and `map/`.
4. `tools/status.py` combines `analysis/` with the authored `records/` into `STATUS.md` and the graph.

The game files themselves are never committed.
