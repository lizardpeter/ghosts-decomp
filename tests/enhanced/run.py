#!/usr/bin/env python3
"""Tests of the enhanced build (enhanced/), in the same emulator as the differential tests.

The enhanced build changes behaviour on purpose, so it isn't compared with the original: each test states what
the enhanced function must do and checks it. The Store exe and build/<build>/enhanced/recon.dll are mapped
together as in tests/differential, so enhanced code still runs on the original's data and engine.

    python3 tools/build_recon.py --build iw6mp64_MSStore_ship --enhanced
    python3 tests/enhanced/run.py [-k name]

Each tests/enhanced/test_*.py defines functions test_<name>(env); env.call(symbol, args, ...) runs an export of
the enhanced DLL (or an original function by name) and returns the harness's (value, buffers, globals written,
observed calls).
"""
import importlib.util
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "differential"))
sys.path.insert(0, str(HERE.parents[1] / "tools"))

from harness import ROOT, Image, Machine, original_exe  # noqa: E402
import symbols  # noqa: E402
import syms  # noqa: E402

BUILD = "iw6mp64_MSStore_ship"


class Env:
    def __init__(self):
        self.dll = Image(ROOT / "build" / BUILD / "enhanced" / "recon.dll")
        self.machine = Machine(Image(original_exe(BUILD)), self.dll)
        self.table = {name: va for name, (va, kind) in symbols.table(BUILD).items()}
        syms.BUILD = BUILD

    def data(self, name):
        """A global or static of the enhanced DLL, by its plain name in the link map."""
        if not hasattr(self, "_map"):
            self._map = {}
            for line in (ROOT / "build" / BUILD / "enhanced" / "recon.map").read_text().splitlines():
                parts = line.split()
                if len(parts) >= 4 and ":" in parts[0] and len(parts[2]) == 16:
                    self._map.setdefault(parts[1], int(parts[2], 16))
        if name in self._map:
            return self._map[name]
        return next(va for sym, va in self._map.items() if sym.startswith(f"?{name}@@"))

    def va(self, symbol):
        """An export of the enhanced DLL, else the original's function or global."""
        return self.dll.exports.get(symbol) or self.table[symbol]

    def call(self, symbol, args, ret="void", setup=None, fakes=None, observe=None):
        hooks = {}
        for s, fn in (fakes or {}).items():
            for va in (self.dll.exports.get(s), self.table.get(s)):
                if va:
                    hooks[va] = fn
        obs = {}
        for s, spec in (observe or {}).items():
            for va in (self.dll.exports.get(s), self.table.get(s)):
                if va:
                    obs[va] = spec
        return self.machine.call(self.va(symbol), args, ret, setup, hooks, obs)


def main():
    only = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else None
    env = Env()
    passed = failed = 0
    for path in sorted(HERE.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in sorted(n for n in dir(mod) if n.startswith("test_")):
            if only and only not in name:
                continue
            try:
                getattr(mod, name)(env)
                print(f"ok   {path.stem}.{name}")
                passed += 1
            except Exception:
                print(f"FAIL {path.stem}.{name}")
                traceback.print_exc(limit=3)
                failed += 1
    print(f"{passed}/{passed + failed} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
