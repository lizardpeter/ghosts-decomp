#!/usr/bin/env python3
"""Run the differential tests and check records/functions.tsv against the results.

    python3 tests/differential/run.py [--check-records] [-k substring]

Every function the reconstruction exports is tested. Hand-written CASES in test_*.py are used when a
function has them; otherwise inputs are generated from the original prototype (auto.py).

For each input, the original and the reconstruction are called on identical arguments. Results must
match exactly: return value (floats bit-exact, NaN == NaN), every pointer buffer, and every byte the
call wrote into the original image's globals. Inputs on which the ORIGINAL itself crashes are skipped;
a function with too few usable inputs is reported as untestable, not passed.

Writes build/test-results.tsv. With --check-records, fails if records/ claims `matches` (or better)
for a function without a passing test.
"""
import csv
import importlib.util
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auto import auto_case  # noqa: E402
from harness import ROOT, Image, Machine, original_exe  # noqa: E402

BUILD = "CoDMPServer"
MATCHED = {"matches", "integrated"}
MIN_USABLE = 20
csv.field_size_limit(1 << 30)


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return struct.pack("<d", a) == struct.pack("<d", b)
    return a == b


def export_name(symbol):
    # extern "C" x86 names carry a leading underscore in the MAP but not in the DLL's export table
    return symbol[1:] if symbol.startswith("_") else symbol


def read_tsv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def main():
    only = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else None
    mapsyms = {r["name"]: int(r["va"], 16) for r in read_tsv(ROOT / "analysis" / BUILD / "map" / "publics.tsv")}
    recon = Image(ROOT / "build" / "recon.dll")
    m = Machine(Image(original_exe(BUILD)), recon)
    # A modern CPU: the CRT's startup would have set this, enabling its SSE2 math paths.
    m.poke(mapsyms["___use_sse2_mathfcns"], struct.pack("<I", 1))

    explicit = {}
    for test in sorted(Path(__file__).parent.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(test.stem, test)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for case in mod.CASES:
            explicit[case["symbol"]] = case

    symbols = [r["symbol"] for r in read_tsv(ROOT / "build" / "recon.symbols.tsv")]
    results, failed = [], 0
    for sym in sorted(symbols, key=lambda s: mapsyms.get(s, 0)):
        if only and only not in sym:
            continue
        va = mapsyms[sym]
        case = explicit.get(sym)
        how = "explicit"
        if case is None:
            case, note = auto_case(sym, va)
            how = "auto"
            if case is None:
                results.append([BUILD, f"{va:09X}", sym, 0, f"untestable: {note}"])
                failed += 1
                print(f"UNTESTABLE {va:09X} {sym}: {note}")
                continue
        target = recon.exports.get(export_name(sym))
        if target is None:
            verdict, used = "missing: no export with the original decorated name", 0
        else:
            verdict, used = "pass", 0
            for args in case["inputs"]:
                want = m.call(va, args, case["ret"])
                if isinstance(want[0], str) and want[0].startswith("fault"):
                    continue  # the original itself crashes on this input: not a usable case
                got = m.call(target, args, case["ret"])
                used += 1
                # recon globals live at the original's addresses (hybrid link), so writes compare 1:1
                if not (same(want[0], got[0]) and want[1] == got[1] and want[2] == got[2]):
                    verdict = (f"FAIL args={args!r}\n       original={want[0]!r} bufs_equal={want[1] == got[1]} "
                               f"globals_equal={want[2] == got[2]}\n       recon   ={got[0]!r}")
                    break
            if verdict == "pass" and used < min(MIN_USABLE, len(case["inputs"])):
                verdict = f"untestable: original faults on {len(case['inputs']) - used}/{len(case['inputs'])} inputs"
        failed += verdict != "pass"
        results.append([BUILD, f"{va:09X}", sym, used, verdict])
        tag = "ok  " if verdict == "pass" else ("UNTESTABLE" if verdict.startswith("untestable") else "FAIL")
        print(f"{tag} {va:09X} {sym}  ({used} cases, {how})" + ("" if verdict == "pass" else f"\n     {verdict[:600]}"))

    out = ROOT / "build" / "test-results.tsv"
    out.write_text("build\tva\tsymbol\tcases\tresult\n" +
                   "".join("\t".join(str(x).replace("\n", " ") for x in r) + "\n" for r in results))
    known = 0
    if "--check-records" in sys.argv:
        passed = {(r[0], r[1]) for r in results if r[4] == "pass"}
        records = {(r["build"], r["va"]): r for r in read_tsv(ROOT / "records" / "functions.tsv")}
        for key, r in records.items():
            if r["status"] in MATCHED and key not in passed:
                print(f"FAIL records claim {r['status']} for {key[0]}:{key[1]} without a passing test")
                failed += 1
        # A failure is expected, not fatal, only for a function records/ deliberately keeps below
        # `matches` with a note saying why (e.g. it stores its own code addresses in a global).
        for r in results:
            rec = records.get((r[0], r[1]))
            if r[4] != "pass" and rec and rec["status"] not in MATCHED and rec["note"]:
                print(f"known  {r[1]} {r[2]}: records keep it at {rec['status']}: {rec['note']}")
                failed -= 1
                known += 1
    print(f"{len(results) - failed - known}/{len(results)} passed" + (f", {known} known failure(s)" if known else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
