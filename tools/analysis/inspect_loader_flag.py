#!/usr/bin/env python3
"""Trace reads/writes of the Store renderer/asset startup wait flag.

Read generated Store pseudocode without modifying analysis/. The native
debugger found a stack return site inside 14036DF30, which contains
this handshake. Native run 40201962452 sampled zero throughout 90 seconds;
that wait is NOT verified as the cause of the black startup screen.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSEUDO = ROOT / "analysis/iw6mp64_MSStore_ship/pseudocode/_unattributed"
ADDRESS = "145caedf8"
OUT = ROOT / "native-loader-flag.json"


def run():
    records = []
    for path in sorted(PSEUDO.glob("*.c")):
        source = path.read_text(encoding="utf-8", errors="replace").splitlines()
        owner = None
        for i, line in enumerate(source):
            if line.startswith("// 140") and len(line) > 14 and line[12:13] == " ":
                owner = line[3:12]
            if ADDRESS in line.lower():
                lo = max(0, i - 8)
                hi = min(len(source), i + 9)
                records.append({
                    "function": owner,
                    "source": str(path.relative_to(ROOT)),
                    "line": i+1,
                    "context": "\n".join(f"{k+1}: {source[k]}" for k in range(lo, hi)),
                })
    OUT.write_text(json.dumps({"flag": ADDRESS, "references": records}, indent=2) + "\n")
    print("Renderer/asset wait flag: %s, %d pseudocode references" % (ADDRESS, len(records)))
    for record in records:
        print("\n=== %s %s:%s ===" % (record["function"], record["source"], record["line"]))
        print(record["context"])
    if not records:
        raise SystemExit("No references to observed wait flag; inspect disassembly")


if __name__ == "__main__":
    run()
