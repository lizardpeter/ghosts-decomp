"""Check tools/fastfile/clipmap.py against the game: the Store build's own loader (store_emu.py) loads a real map
zone; when it reaches Load_clipMap_ptr (14035FB10) the stream state is handed to the Python reader, which loads the
clipMap_t; the game's state when Load_clipMap_ptr returns must then be the same (zone position, every block position,
every byte of block memory and the asset pool). The same comparison as world_check.py.

    python3 tests/fastfile/clipmap_check.py <map.ff>      (needs $IW6_ORIGINALS)

Used by tests/fastfile/test_clipmap.py (with IW6_FASTFILES).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools" / "fastfile"))

import world_check  # noqa: E402

LOAD_CLIPMAP_PTR = 0x14035FB10
VAR_CLIPMAP_PTR = 0x144425650


def compare(ff: bytes, name: str):
    import clipmap
    return world_check.compare(ff, name, LOAD_CLIPMAP_PTR, VAR_CLIPMAP_PTR, clipmap.load_clipmap_ptr)


if __name__ == "__main__":
    path = Path(sys.argv[1])
    diffs, st = compare(path.read_bytes(), path.stem)
    if st:
        before, after, s = st
        print(f"clipMap: zone {before.read_total:#x} -> {after.read_total:#x}, "
              f"virtual {before.pos[3]:#x} -> {after.pos[3]:#x}, runtime {before.pos[2]:#x} -> {after.pos[2]:#x}")
    print("\n".join(diffs) if diffs else "reader == game")
    sys.exit(1 if diffs else 0)
