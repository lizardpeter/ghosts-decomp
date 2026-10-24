#!/usr/bin/env python3
"""Extract exact Store function pseudocode from generated Ghidra chunks.

Read only: analysis/ is never edited. Used to reconstruct local profile,
UI-readiness and client connection gates function by function.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "analysis/iw6mp64_MSStore_ship/pseudocode/_unattributed"
HEADER = re.compile(r"^// ([0-9A-F]{9})  (.*)$")
DEFAULT = (
    "1401A7EA0",  # GDK signed-in check
    "1401A5740",  # Store query completion state
    "1401A61A0",  # Store license status
    "1401A7E80",  # per-controller eligibility prerequisite
    "140245440",  # LUI CheckGameLicense callback
    "14054B4B0",  # Live_Frame / game online pump
    "14054B1B0",  # multiplayer readiness
    "14054B290",  # multiplayer readiness
    "140311570",  # client join identity / stats
    "1403129D0",  # connectionless response
)


def extract(addresses):
    missing = set(addresses)
    results = {}
    for chunk in sorted(CHUNKS.glob("*.c")):
        current = None
        lines = []
        with chunk.open(encoding="utf-8", errors="replace") as source:
            for lineno, line in enumerate(source, 1):
                match = HEADER.match(line)
                if match:
                    if current is not None:
                        results[current]["pseudocode"] = "".join(lines)
                    current = match.group(1) if match.group(1) in missing else None
                    lines = []
                    if current is not None:
                        results[current] = {
                            "header": match.group(2).rstrip(),
                            "source": str(chunk.relative_to(ROOT)),
                            "line": lineno,
                        }
                        missing.remove(current)
                if current is not None:
                    lines.append(line)
            if current is not None:
                results[current]["pseudocode"] = "".join(lines)
        if not missing:
            break
    return results, sorted(missing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", nargs="*", help="9-digit Store VA (without 0x)")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preview-lines", type=int, default=60)
    args = parser.parse_args()
    addresses = tuple(x.upper().removeprefix("0X") for x in args.address) or DEFAULT
    if any(not re.fullmatch(r"140[0-9A-F]{6}", x) for x in addresses):
        parser.error("Addresses must be 9 uppercase/lowercase hex digits with Store image base")
    result, missing = extract(set(addresses))
    report = {"target": "iw6mp64_MSStore_ship", "functions": result, "missing": missing}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for va in addresses:
        if va not in result:
            print(f"{va}: NOT FOUND")
            continue
        r = result[va]
        source_lines = r["pseudocode"].splitlines()
        print(f"\n=== {va} | {r['header']} | {r['source']}:{r['line']} | {len(source_lines)} lines ===")
        print("\n".join(source_lines[:max(0, args.preview_lines)]))
        if len(source_lines) > args.preview_lines:
            print(f"[{len(source_lines)-args.preview_lines} further lines in JSON report]")
    if missing:
        raise SystemExit("Could not find targets: " + ", ".join(missing))


if __name__ == "__main__":
    main()
