#!/usr/bin/env python3
"""Match functions of a target build (retail, no symbols) to a reference build (with PDB/MAP).

    python3 tools/match/match.py <reference-build> <target-build> [--originals DIR] [--same-compiler]

--same-compiler tightens the size check for two builds compiled the same way (e.g. the two server
builds, which is how the matcher is validated against ground truth: tools/match/validate.py).

Reads analysis/<build>/functions.tsv and ghidra/callgraph.tsv for both builds, and the two original exes
(from DIR, default .work/originals, fetched with tools/fetch_originals.py) to find each function's
references to strings and to global data.

Writes analysis/<target>/match/functions.tsv (generated; never hand-edit):
  target_va  ref_va  ref_name  source  method  confidence  evidence

Methods, in the order they run:
  string     the pair are the only functions in their builds referencing a given string
             (several such strings strengthen the match; conflicting candidates are dropped)
  constant   the same with distinctive numeric immediates (at least two shared, each unique on both sides)
  callee     propagation: a matched pair's unmatched callees pair up when each side has exactly one
             candidate with the same matched-callee signature, or exactly one unmatched callee
  caller     the same, upwards through callers
Propagated pairs must also pass structural checks (shared strings when both reference any, size
ratio, callee count). Every match records its evidence. Nothing is matched on position: the retail build is linked with
whole-program optimization and reordered (docs/retail-builds.md).
"""
import bisect
import collections
import csv
import re
import struct
import sys
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parents[2]
csv.field_size_limit(1 << 30)


def read_tsv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


class Build:
    def __init__(self, build_id, exe):
        self.id = build_id
        a = ROOT / "analysis" / build_id
        rows = read_tsv(a / "functions.tsv")
        self.fn = {}
        for r in rows:
            if r.get("thunk_of"):
                continue
            va = int(r["va"], 16)
            self.fn[va] = {"va": va, "size": int(r["size"] or 0),
                           "name": r.get("pdb_name") or r.get("ghidra_name", ""), "source": r.get("source", "")}
        self.starts = sorted(self.fn)
        self.callees = collections.defaultdict(set)
        self.callers = collections.defaultdict(set)
        for e in read_tsv(a / "ghidra" / "callgraph.tsv"):
            c, d = int(e["caller"], 16), int(e["callee"], 16)
            if c in self.fn and d in self.fn and c != d:
                self.callees[c].add(d)
                self.callers[d].add(c)
        self._scan(exe)

    def owner(self, addr):
        i = bisect.bisect_right(self.starts, addr) - 1
        if i < 0:
            return None
        f = self.fn[self.starts[i]]
        return f["va"] if addr < f["va"] + max(f["size"], 1) else None

    def _scan_constants(self, tva, tdata, base, size):
        """Distinctive immediates per function: not addresses, not small, not powers/masks."""
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        md.detail = True
        self.const_refs = collections.defaultdict(set)
        self.fn_consts = collections.defaultdict(set)
        for va, f in self.fn.items():
            off = va - tva
            if off < 0 or off >= len(tdata) or f["size"] <= 0:
                continue
            for ins in md.disasm(tdata[off:off + f["size"]], va):
                for op in ins.operands:
                    if op.type == capstone.x86.X86_OP_IMM:
                        v = op.imm & 0xFFFFFFFF
                    elif op.type == capstone.x86.X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                        continue
                    else:
                        continue
                    if v < 0x10000 or v > 0xFFFF0000 or base <= v < base + size:
                        continue
                    if v & (v - 1) == 0 or (v + 1) & v == 0:
                        continue  # powers of two and low-bit masks are everywhere
                    self.const_refs[v].add(va)
                    self.fn_consts[va].add(v)

    def _scan(self, exe):
        """Every 4-byte value in .text that is the address of a C string -> (string, owning function)."""
        pe = pefile.PE(str(exe), fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        secs = {s.Name.rstrip(b"\0"): s for s in pe.sections}
        strs = {}
        for name in (b".rdata", b".data"):
            s = secs.get(name)
            if not s:
                continue
            d, va = s.get_data(), base + s.VirtualAddress
            for m in re.finditer(rb"[\x20-\x7e\t\n\r]{5,}\x00", d):
                strs[va + m.start()] = m.group()[:-1]
        text = secs[b".text"]
        tva, tdata = base + text.VirtualAddress, text.get_data()
        self._scan_constants(tva, tdata, base, pe.OPTIONAL_HEADER.SizeOfImage)
        self.str_refs = collections.defaultdict(set)   # string -> {function}
        self.fn_strs = collections.defaultdict(set)    # function -> {string}
        for i in range(len(tdata) - 3):
            v = struct.unpack_from("<I", tdata, i)[0]
            s = strs.get(v)
            if s is None:
                continue
            f = self.owner(tva + i)
            if f is not None:
                self.str_refs[s].add(f)
                self.fn_strs[f].add(s)


def main():
    ref_id, tgt_id = sys.argv[1], sys.argv[2]
    originals = Path(sys.argv[sys.argv.index("--originals") + 1]) if "--originals" in sys.argv \
        else ROOT / ".work" / "originals"
    ref = Build(ref_id, originals / f"{ref_id}.exe")
    tgt = Build(tgt_id, originals / f"{tgt_id}.exe")

    match = {}       # tgt va -> (ref va, method, confidence, evidence)
    matched_ref = {}  # ref va -> tgt va

    size_lo, size_hi = (0.5, 2.0) if "--same-compiler" in sys.argv else (0.15, 6.0)

    def compatible(t, r):
        """Cheap structural checks a propagated pair must pass."""
        ts, rs = tgt.fn_strs.get(t, set()), ref.fn_strs.get(r, set())
        if ts and rs and not (ts & rs):
            return False  # both reference strings, none in common
        if ts and not rs:
            return False  # target has strings the reference function never references
        tz, rz = tgt.fn[t]["size"], ref.fn[r]["size"]
        if tz and rz and not (size_lo <= tz / rz <= size_hi):
            return False
        tc, rc = len(tgt.callees[t]), len(ref.callees[r])
        if max(tc, rc) >= 4 and min(tc, rc) * 4 < max(tc, rc):
            return False
        return True

    def accept(t, r, method, conf, ev):
        if t in match or r in matched_ref:
            return False
        if method != "string" and not compatible(t, r):
            return False
        match[t] = (r, method, conf, ev)
        matched_ref[r] = t
        return True

    # 1. unique strings
    votes = collections.defaultdict(lambda: collections.defaultdict(list))  # tgt -> ref -> [strings]
    for s, rfs in ref.str_refs.items():
        tfs = tgt.str_refs.get(s)
        if len(rfs) == 1 and tfs and len(tfs) == 1:
            votes[next(iter(tfs))][next(iter(rfs))].append(s)
    by_ref = collections.defaultdict(set)
    for t, cands in votes.items():
        for r in cands:
            by_ref[r].add(t)
    for t, cands in votes.items():
        if len(cands) != 1:
            continue  # target function pulled toward several reference functions: inlining, skip
        r, ss = next(iter(cands.items()))
        if len(by_ref[r]) != 1:
            continue  # reference function's strings spread over several target functions
        conf = min(0.99, 0.80 + 0.05 * len(ss))
        accept(t, r, "string", conf, f"{len(ss)} unique string(s): " + repr(ss[0][:60].decode("latin1")))
    n_string = len(match)

    # 1b. unique numeric constants: same rules as strings, but a pair needs two constants (one is too weak)
    cvotes = collections.defaultdict(lambda: collections.defaultdict(list))
    for v, rfs in ref.const_refs.items():
        tfs = tgt.const_refs.get(v)
        if len(rfs) == 1 and tfs and len(tfs) == 1:
            cvotes[next(iter(tfs))][next(iter(rfs))].append(v)
    cby_ref = collections.defaultdict(set)
    for t, cands in cvotes.items():
        for r in cands:
            cby_ref[r].add(t)
    for t, cands in cvotes.items():
        if len(cands) != 1:
            continue
        r, vs = next(iter(cands.items()))
        if len(cby_ref[r]) != 1 or len(vs) < 2:
            continue
        accept(t, r, "constant", min(0.95, 0.75 + 0.05 * len(vs)),
               f"{len(vs)} unique constant(s): " + ", ".join(f"{v:#x}" for v in vs[:4]))

    # 2./3. call-graph propagation until nothing changes
    def signature(build, va, mapping):
        """Matched neighbours of a function, expressed in reference addresses."""
        return (frozenset(mapping(x) for x in build.callees[va] if mapping(x) is not None),
                frozenset(mapping(x) for x in build.callers[va] if mapping(x) is not None))

    rounds = 0
    while True:
        rounds += 1
        added = 0
        for direction in ("callee", "caller"):
            for t, (r, *_rest) in list(match.items()):
                tn = [x for x in (tgt.callees[t] if direction == "callee" else tgt.callers[t]) if x not in match]
                rn = [x for x in (ref.callees[r] if direction == "callee" else ref.callers[r]) if x not in matched_ref]
                if not tn or not rn:
                    continue
                if len(tn) == 1 and len(rn) == 1:
                    if accept(tn[0], rn[0], direction, 0.75, f"only unmatched {direction} of {ref.fn[r]['name']}"):
                        added += 1
                    continue
                # pair by matched-neighbour signature when it is unique on both sides
                tsig = collections.defaultdict(list)
                for x in tn:
                    tsig[signature(tgt, x, lambda v: match[v][0] if v in match else None)].append(x)
                rsig = collections.defaultdict(list)
                for x in rn:
                    rsig[signature(ref, x, lambda v: v if v in matched_ref else None)].append(x)
                for sig, txs in tsig.items():
                    if len(txs) == 1 and len(rsig.get(sig, [])) == 1 and (sig[0] or len(sig[1]) > 1):
                        if accept(txs[0], rsig[sig][0], direction, 0.85,
                                  f"{direction} of {ref.fn[r]['name']} with the same {len(sig[0])} matched callees "
                                  f"and {len(sig[1])} matched callers"):
                            added += 1
        if not added:
            break

    out = ROOT / "analysis" / tgt_id / "match"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "functions.tsv", "w", newline="\n") as f:
        f.write("target_va\tref_build\tref_va\tref_name\tsource\tmethod\tconfidence\tevidence\n")
        for t in sorted(match):
            r, method, conf, ev = match[t]
            rf = ref.fn[r]
            f.write(f"{t:09X}\t{ref_id}\t{r:09X}\t{rf['name']}\t{rf['source']}\t{method}\t{conf:.2f}\t"
                    f"{ev.replace(chr(9), ' ').replace(chr(10), ' ')}\n")
    methods = collections.Counter(m[1] for m in match.values())
    print(f"{tgt_id} <- {ref_id}: {len(match):,} of {len(tgt.fn):,} target functions matched "
          f"({100 * len(match) / len(tgt.fn):.1f}%); by method {dict(methods)}; propagation rounds {rounds}")


if __name__ == "__main__":
    main()
