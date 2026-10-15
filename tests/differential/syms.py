"""Addresses of the original's globals for hand-written test setups, from the reference build's MAP and PDB."""
import csv
from functools import lru_cache

from harness import ROOT, reference_build

csv.field_size_limit(1 << 30)


def _rows(*parts):
    with open(ROOT / "analysis" / reference_build() / "/".join(parts), newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


@lru_cache(maxsize=None)
def _publics():
    out = {}
    for r in _rows("map", "publics.tsv"):
        name = r["name"]
        base = name[1:].split("@", 1)[0] if name.startswith("?") else name
        out.setdefault(name, int(r["va"], 16))
        out.setdefault(base, int(r["va"], 16))
    return out


@lru_cache(maxsize=None)
def _statics():
    return {(r["source"], r["scope"], r["name"]): int(r["va"], 16) for r in _rows("pdb", "statics.tsv") if r["va"]}


def va(name: str) -> int:
    """A public symbol by decorated or plain name (`playerKeys`, `?cmd_args@@3UCmdArgs@@A`)."""
    return _publics()[name]


def static(source: str, name: str, scope: str = "") -> int:
    """A static by PDB source path, name and enclosing function ("" for file scope)."""
    return _statics()[(source, scope, name)]
