#!/usr/bin/env python3
"""Compile the reconstruction into one x64 Windows DLL, hybrid-linked against the original exe.

    python3 tools/build_recon.py            # -> build/recon.dll, build/recon.symbols.tsv, build/hybrid.tsv

- Every file under src/ is compiled with clang targeting x86_64-pc-windows-msvc, so the Win64 calling convention
  and MSVC x64 C++ name mangling apply. tools/recon/include holds build-environment headers.
- Every defined function is exported under its decorated name, so tests find it by the ORIGINAL
  decorated name from the MAP: a wrong prototype simply isn't found.
- Hybrid link: any symbol the reconstruction uses but does not define yet is resolved to the original
  binary's address from the MAP (and original statics, declared with IW6_STATIC, from the PDB). Functions become a `jmp [rip+0]; .quad <va>` thunk into the original code,
  data becomes an absolute symbol at the original address. So a function can be reconstructed and tested
  before anything it calls is. build/hybrid.tsv lists every such dependency.

This is the `compiles` gate. It is not byte matching: that needs the original VC11 (VS2012) x64 compiler.

Ported from black-ops-1-decomp (x86) and not exercised yet: there is no reconstruction and no MAP-bearing
reference build in the repo so far.
"""
import csv
import subprocess
import tomllib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
# The build the hybrid link resolves against: the first reference build with a MAP (target.toml).
TARGET_BUILD = next((b["id"] for b in tomllib.loads((ROOT / "target.toml").read_text())["build"]
                     if b.get("kind") == "reference" and "map" in b), None)
TRIPLE = "--target=x86_64-pc-windows-msvc"
CFLAGS = [TRIPLE, "-O0", "-ffp-contract=off", "-fno-exceptions",
          "-fms-extensions", "-fno-stack-protector", "-ffreestanding", "-fno-builtin", "-Wall", "-Werror",
          "-Wno-unused-function", "-Wno-unused-variable", f"-I{ROOT / 'include'}",
          f"-isystem{ROOT / 'tools' / 'recon' / 'include'}"]
csv.field_size_limit(1 << 30)


def run(*cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def nm(obj, *flags):
    out = subprocess.run(["llvm-nm", *flags, str(obj)], check=True, capture_output=True, text=True).stdout
    return [line.split() for line in out.splitlines() if line.strip()]


def original_symbols():
    with open(ROOT / "analysis" / TARGET_BUILD / "map" / "publics.tsv", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    syms = {}
    for r in rows:
        syms.setdefault(r["name"], (int(r["va"], 16), "f" in r["flags"]))
    return syms


def original_statics():
    """'iw6s@<source>@<scope>@<name>' -> va, for IW6_STATIC declarations (tools/recon/include/iw6_static.h)."""
    with open(ROOT / "analysis" / TARGET_BUILD / "pdb" / "statics.tsv", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    return {f"iw6s@{r['source']}@{r['scope']}@{r['name']}": int(r["va"], 16) for r in rows}


def main():
    if TARGET_BUILD is None:
        sys.exit("no reference build with a MAP in target.toml yet")
    BUILD.mkdir(exist_ok=True)
    objs, sources = [], []
    for src in sorted((ROOT / "src").rglob("*.cpp")):
        rel = src.relative_to(ROOT / "src")
        obj = BUILD / "obj" / rel.with_suffix(".obj")
        obj.parent.mkdir(parents=True, exist_ok=True)
        run("clang++", "-std=c++17", *CFLAGS, "-c", src, "-o", obj)
        objs.append(obj)
        sources.append(obj)
    if not objs:
        sys.exit("no sources")

    # build environment: the MSVC float marker
    (BUILD / "fltused.c").write_text("int _fltused = 0;\n")
    run("clang", *CFLAGS, "-c", BUILD / "fltused.c", "-o", BUILD / "fltused.obj")
    env_objs = [BUILD / "fltused.obj"]

    defined, exports, rows = set(), [], []
    for obj in sources:
        for parts in nm(obj, "--defined-only", "--extern-only"):
            if len(parts) == 3:
                defined.add(parts[2])
                if parts[1] in ("T", "t"):
                    exports.append(parts[2])
                    rows.append(f"{parts[2]}\t{obj.relative_to(BUILD / 'obj').with_suffix('.cpp')}")
    for obj in env_objs:
        defined |= {p[2] for p in nm(obj, "--defined-only", "--extern-only") if len(p) == 3}
    undefined = sorted({p[-1] for o in objs + env_objs for p in nm(o, "--undefined-only")} - defined)

    orig = original_symbols()
    statics = original_statics()
    # Only functions that exist in the original are exported (and tested). Anything else defined in src/
    # is an inline helper from a header; flag it so new names do not slip in unnoticed.
    stray = [e for e in exports if e not in orig and e not in ("_fltused",)]
    exports = [e for e in exports if e in orig]
    rows = [r for r in rows if r.split("\t")[0] in orig]
    # A stray symbol whose plain name matches an original function is a prototype mismatch (wrong parameter
    # or return type, constness, calling convention): the function would silently drop out of testing.
    def base_name(sym):
        return sym[1:].split("@", 1)[0] if sym.startswith("?") else sym
    orig_names = {}
    for o in orig:
        orig_names.setdefault(base_name(o), []).append(o)
    mismatched = [f"{e}  (original: {', '.join(orig_names[base_name(e)])})" for e in stray if base_name(e) in orig_names]
    if mismatched:
        sys.exit("prototype differs from the original's decorated name:\n  " + "\n  ".join(mismatched))
    if stray:
        print("note: defined in src/ but not in the original MAP (not exported):", ", ".join(stray))
    missing = [u for u in undefined if u not in orig and u not in statics]
    if missing:
        sys.exit("reconstruction uses symbols the original binary does not have:\n  " + "\n  ".join(missing))
    asm = ["\t.text"]
    hybrid = ["symbol\tkind\tva"]
    for u in undefined:
        va, is_func = orig[u] if u in orig else (statics[u], False)
        q = '"' + u + '"'
        if is_func:
            asm += [f"\t.globl {q}", f"{q}:", "\tjmpq *0(%rip)", f"\t.quad {va:#x}"]
        else:
            asm += [f"\t.globl {q}", f"\t.set {q}, {va:#x}"]
        hybrid.append(f"{u}\t{'function' if is_func else 'data'}\t{va:09X}")
    (BUILD / "hybrid.s").write_text("\n".join(asm) + "\n")
    run("clang", TRIPLE, "-c", BUILD / "hybrid.s", "-o", BUILD / "hybrid.obj")
    (BUILD / "hybrid.tsv").write_text("\n".join(hybrid) + "\n")

    dll = BUILD / "recon.dll"
    run("lld-link", "/dll", "/noentry", "/nodefaultlib", "/base:0x180000000", "/fixed", f"/out:{dll}",
        *[f"/export:{e}" for e in exports],  # x64: no leading underscore on C names
        *objs, *env_objs, BUILD / "hybrid.obj")
    (BUILD / "recon.symbols.tsv").write_text("symbol\tsource\n" + "\n".join(rows) + "\n")
    print(f"{dll}: {len(exports)} functions from {len(sources)} files; "
          f"{len(undefined)} symbols resolved to the original binary")


if __name__ == "__main__":
    main()
