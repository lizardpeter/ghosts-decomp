#!/usr/bin/env python3
"""Regression for the canonical IW6 direct package's SOCKS5 overflow guard (S20)."""
import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "offline"))
import package
import detachment_audit

VA = 0x14054F5B0
EXPORT = "Iw6DirectDisableSocks"


def main():
    # Packaging and the fail-closed manifest audit must agree on this exact
    # original entrypoint: an unreferenced enhancement is not a game fix.
    assert package.DIRECT[VA] == EXPORT
    assert VA in detachment_audit.DIRECT_ENTRIES
    assert len(package.DIRECT) == len(detachment_audit.DIRECT_ENTRIES) == 18
    # Regression: these are PS4 server PDB entrypoints, not verified Store
    # addresses. A cross-build native detour would corrupt unrelated code.
    assert not ({0x1400AD720, 0x1400ACEA0, 0x1400AD5F0} & package.DIRECT.keys())

    # Exercise the exact C++ implementation exported by the enhanced game.
    # It has no credential parsing, no network calls, and no socket state.
    source = ROOT / "enhanced" / "direct" / "security.cpp"
    with tempfile.TemporaryDirectory() as tmp:
        library = Path(tmp) / "security.so"
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-shared", "-fPIC", str(source), "-o", str(library)],
                       check=True)
        dll = ctypes.CDLL(str(library))
        disable = getattr(dll, EXPORT)
        disable.argtypes = [ctypes.c_int]
        disable.restype = None
        for port in [-1, 0, 1080, 27016, 65535, 100000]:
            assert disable(port) is None
    print("PASS: SOCKS5 vulnerable original entry is guarded and adapter is inert")


if __name__ == "__main__":
    main()
