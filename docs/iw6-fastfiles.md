# IW6 PC FastFile source validation

The standalone tools under `tools/fastfile/` provide read-only, reproducible
format checks against retail *Call of Duty: Ghosts* PC source data. They are
intended to support Ghosts reverse engineering and the separate universal
Rust-test asset importer. They do **not** materialize meshes, gameplay scripts,
collision, or whole game assets.

## Formats proven from original R2 source

All cases use IW6 FastFile version `0x235`. The 24-byte streamed-image rows
begin after the 28-byte fixed prefix. The original compressed-payload offset is
`44 + 24 * image_count`; it is not a constant 44 bytes for actual levels.

- `IWff0100`: the signed/authenticated case, marked `IWffs100` at the
  payload offset. The 8 KiB authentication envelope is followed by repeating
  8 KiB SHA-256 master blocks and up to 256 corresponding 8 KiB compressed
  data blocks. The first block's digest is verified by the inexpensive header
  survey, while every full block is verified by the full-source audit.
- `IWffu100`: unsigned case with zlib directly at the payload offset.
- `XFile`: its first 72 decompressed bytes declare the total content length,
  external length, and seven memory block sizes. The following 40 bytes hold
  counts/pointers for script strings, XAsset entries and graphical globals.

No original source files or decompressed zone bodies are committed or
published as GitHub Actions artifacts. Only JSON diagnostics are uploaded.

## Original-format survey

Successful public [header and first-block validation run](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39049458463).
Each file was requested using bounded HTTP ranges against the owner's
`https://r2.houseofkublai.com/ghosts/DUMP/` endpoint.

| Source zone | Envelope | Streamed image records | Asset-count header |
| --- | --- | ---: | ---: |
| `mp_alien_town.ff` | SHA-256 | 8,160 | 2,560 |
| `mp_alien_armory.ff` | SHA-256 | 10,160 | 2,732 |
| `mp_alien_beacon.ff` | SHA-256 | 9,344 | 2,883 |
| `mp_strikezone.ff` | SHA-256 | 7,416 | 1,924 |
| `black_ice.ff` | direct zlib | 12,116 | 3,591 |
| `common_mp.ff` | SHA-256 | 1,616 | 8,774 |
| `common_core_mp.ff` | SHA-256 | 6,144 | 3,037 |
| `techsets_mp_alien_town.ff` | SHA-256 | 0 | 842 |
| `mp_alien_town_path.ff` | SHA-256 | 0 | 2 |

The first-block checksum validated for every signed sample. These are the
original XAssetList *counts*, not proof that all referenced asset bodies have
been decoded or individually identified.

## Point of Contact full compressed-source audit

Successful public [full-stream validation run](https://github.com/lizardpeter/ghosts-decomp/actions/runs/39049655218).
All four original Point of Contact files were fetched from R2, their physical
lengths matched the source inventory, and their entire compressed data was
streamed through zlib. Every complete SHA-256-authenticated block matched its
master digest, and every decoded XFile length matched its own declaration.

| Source zone | Source bytes | Decoded bytes | Authenticated 8-KiB blocks | Declared XAsset entries |
| --- | ---: | ---: | ---: | ---: |
| `mp_alien_town.ff` | 186,301,740 | 347,242,545 | 22,628 | 2,560 |
| `techsets_mp_alien_town.ff` | 7,479,340 | 58,840,896 | 908 | 842 |
| `mp_alien_town_load.ff` | 1,957,932 | 14,325,979 | 237 | 67 |
| `mp_alien_town_path.ff` | 385,068 | 1,441,055 | 45 | 2 |

All four reported zero unverified partial terminal block bytes. Combined,
they contain **196,124,080 physical source bytes** and
**421,850,475 decompressed bytes**. This validates *archive extraction* and
*header reading*, not scene completeness or a playable Extinction map.

## Reproduce without Git-hosting source data

The checked-in GitHub workflows perform source retrieval using ephemeral
runner storage:

- `.github/workflows/iw6-fastfile-retail.yml` — cheap bounded-range header
  and first-block survey across multiple source families.
- `.github/workflows/iw6-zone-stream-audit.yml` — fully validate the four
  Point of Contact compressed zones, report only counts/sizes, then delete
  the temporary source files.

The offline tools work on lawfully obtained local source files:

```bash
python3 tools/fastfile/probe_headers.py --test
python3 tools/fastfile/probe_zone.py --test
python3 tools/fastfile/probe_zone.py /path/to/ghosts/DUMP/mp_alien_town_path.ff
```

For downstream engine import, the next step is walking the actual IW6
seven-block loader/asset pointers, resolving GfxWorld, ClipMap, materials,
models, scripted entities and authored spawns, then translating that source
evidence into the game's *generic* engine contracts. Nothing here creates a
Ghosts-specific renderer or game-mode fallback.
