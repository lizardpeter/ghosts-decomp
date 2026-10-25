#!/usr/bin/env python3
"""Map native debug-observer stack addresses to original Store functions.

Read-only: the source of truth remains generated analysis/ and pinned
functions.tsv. Useful for deciding whether a black native screen is a
loading wait, frame/renderer work, or a platform gate without guessing.
"""
import argparse
import bisect
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = "iw6mp64_MSStore_ship"
ANALYSIS = ROOT / "analysis" / BUILD
STORED = (
    "14036E62B", "14053DD79", "14053D51E",
    "14063159F", "140674BB0", "14046F0D3", "14046FED5",
)


def extract_function(va, limit):
    path = ANALYSIS / "pseudocode" / "_unattributed" / (
        f"{(va >> 4) & ~0xFFFF:08X}.c")
    if not path.is_file():
        return {"source": str(path.relative_to(ROOT)), "error": "chunk missing"}
    needle = f"// {va:09X}  "
    lines = []
    first = None
    with path.open(encoding="utf-8", errors="replace") as source:
        for number, line in enumerate(source, 1):
            if first is None:
                if line.startswith(needle):
                    first = number
                    lines.append(line.rstrip())
            else:
                if line.startswith("// 140") and not line.startswith(needle):
                    break
                if len(lines) < limit:
                    lines.append(line.rstrip())
    return {"source": str(path.relative_to(ROOT)), "line": first,
            "excerpt": "\n".join(lines), "found": first is not None}


def map_stacks(addresses, limit):
    rows = []
    with (ANALYSIS / "functions.tsv").open(newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            try:
                start, size = int(row["va"], 16), int(row["size"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append((start, size, row))
    rows.sort(key=lambda x: x[0])
    starts = [x[0] for x in rows]
    output = {}
    for address in addresses:
        va = int(address, 16)
        index = bisect.bisect_right(starts, va) - 1
        if index < 0:
            output[address] = {"error": "no preceding function"}
            continue
        start, size, row = rows[index]
        if not start <= va < start + size:
            output[address] = {"error": "not inside a nonzero known function",
                               "nearest_start": f"{start:09X}"}
            continue
        output[address] = {
            "function_va": f"{start:09X}",
            "offset": va-start,
            "size": size,
            "source_metadata": row,
            "pseudocode": extract_function(start, limit),
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", nargs="*", help="9-digit Store addresses")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--excerpt-lines", type=int, default=45)
    args = parser.parse_args()
    addresses = args.address or STORED
    for address in addresses:
        try:
            value = int(address.removeprefix("0x"), 16)
        except ValueError:
            parser.error("Invalid address: " + address)
        if value < 0x140000000 or value >= 0x150000000:
            parser.error("Address outside pinned Store executable: " + address)
    lookup = map_stacks([f"{int(a.removeprefix('0x'),16):09X}" for a in addresses],
                        args.excerpt_lines)
    if args.output:
        args.output.write_text(json.dumps(lookup, indent=2) + "\n")
    for address, entry in lookup.items():
        print(f"\n=== observed {address} ===")
        print(json.dumps({k: v for k, v in entry.items()
                          if k not in ("pseudocode", "source_metadata")}, indent=2))
        if "source_metadata" in entry:
            print("function metadata", json.dumps(entry["source_metadata"]))
        if "pseudocode" in entry:
            print(entry["pseudocode"].get("excerpt", ""))


if __name__ == "__main__":
    main()
