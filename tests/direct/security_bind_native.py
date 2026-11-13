#!/usr/bin/env python3
"""S17/B0009: verify native Store bind handlers are matched, not PS4-offset guesses.

The matcher evidence is not a substitute for eventual native execution, but
packaging must refuse an unmapped/mismapped security-critical handler.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "offline"))
import package
import detachment_audit

MATCH = ROOT / "analysis" / "iw6mp64_MSStore_ship" / "match" / "functions.tsv"
ENTRIES = {
    0x1403106D0: ("Key_Bind_f", "Iw6SecureBind", 0x1400ACEA0),
    0x140310D20: ("Key_SwapBind_f", "Iw6SecureSwapBind", 0x1400AD5F0),
    0x140310EB0: ("Key_Unbind_f", "Iw6SecureUnbind", 0x1400AD720),
}
REFERENCE_ONLY = {item[2] for item in ENTRIES.values()}


def main():
    with MATCH.open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    for native, (name, export, reference) in ENTRIES.items():
        evidence = [r for r in rows
                    if int(r["target_va"], 16) == native
                    and int(r["ref_va"], 16) == reference
                    and r["ref_build"] == "iw6_ds_ps4"
                    and r["ref_name"] == name
                    and r["source"] == "client/cl_keys.cpp"]
        assert len(evidence) == 1, ("missing or changed Store match", name)
        assert float(evidence[0]["confidence"]) >= (0.75 if name == "Key_Bind_f" else 0.89)
        assert package.DIRECT[native] == export
        assert native in detachment_audit.DIRECT_ENTRIES
    assert not (REFERENCE_ONLY & package.DIRECT.keys()), "PS4 VAs used as Store hooks"
    assert set(package.DIRECT) == detachment_audit.DIRECT_ENTRIES
    print("PASS: three native Store key-binding guards match PS4 symbols with reviewed evidence")


if __name__ == "__main__":
    main()
