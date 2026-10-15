#!/usr/bin/env python3
"""Score a match against ground truth when the target build has its own symbols.

    python3 tools/match/match.py CoDMPServer CoDMPServer_s --same-compiler
    python3 tools/match/validate.py CoDMPServer CoDMPServer_s

Both server builds have MAP/PDB names, so matching one to the other "blind" measures the matcher's
precision per method. A pair counts as correct when the decorated (or PDB) names agree.
"""
import collections
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
csv.field_size_limit(1 << 30)


def rd(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


ref_id, tgt_id = sys.argv[1], sys.argv[2]
name = lambda r: r["map_name"] or r["pdb_name"]
truth = {r["va"]: name(r) for r in rd(ROOT / "analysis" / tgt_id / "functions.tsv")}
refn = {r["va"]: name(r) for r in rd(ROOT / "analysis" / ref_id / "functions.tsv")}
res = collections.defaultdict(lambda: [0, 0, 0])
for m in rd(ROOT / "analysis" / tgt_id / "match" / "functions.tsv"):
    t, r = truth.get(m["target_va"], ""), refn.get(m["ref_va"], "")
    res[m["method"]][2 if not (t and r) else (0 if t == r else 1)] += 1
tot = [sum(v[i] for v in res.values()) for i in range(3)]
for k, (ok, bad, unk) in sorted(res.items()) + [("all", tot)]:
    print(f"{k:8} correct {ok:6}  wrong {bad:5}  unverifiable {unk:4}  precision {100 * ok / max(ok + bad, 1):5.1f}%")
