#!/usr/bin/env python3
"""Build exactly one custom Store multiplayer game: all enhanced patches + direct local play.

The faithful reconstruction and isolated network-disabled offline diagnostic are
separate developer targets, not alternative enhanced game releases. The authentic
pinned Store executable must be provided locally; this tool never downloads it.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = "iw6mp64_MSStore_ship"
sys.path.insert(0, str(ROOT / "tools"))
from offline.package import package  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path,
                        default=ROOT / ".work/originals" / (BUILD + ".exe"))
    parser.add_argument("--output", type=Path,
                        default=ROOT / ".work/enhanced-package")
    parser.add_argument("--skip-compile", action="store_true",
                        help="use an already-built enhanced DLL (e.g. CI)")
    args = parser.parse_args()
    original = args.original.resolve()
    if not original.is_file() or original.name != BUILD + ".exe":
        parser.error("supply the authentic pinned iw6mp64_MSStore_ship.exe via --original")
    if args.output.exists():
        parser.error("output directory already exists; refusing to overwrite " + str(args.output))

    dll = ROOT / "build" / BUILD / "enhanced" / "recon.dll"
    if not args.skip_compile:
        env = dict(os.environ, IW6_ORIGINALS=str(original.parent))
        subprocess.run([sys.executable, str(ROOT / "tools/build_recon.py"),
                        "--build", BUILD, "--enhanced"],
                       cwd=ROOT, env=env, check=True)
    if not dll.is_file():
        parser.error("canonical enhanced DLL is missing: " + str(dll))

    # The packaging step verifies the original SHA, DLL profile, all 59
    # pinned entry redirects, final IAT and replacement DLL exports.
    manifest = package(original, dll, args.output, mode="direct")
    if manifest["exe_name"] != "iw6mp64_enhanced.exe" or manifest["mode"] != "direct":
        raise RuntimeError("enhanced package returned an unexpected profile")
    print("Enhanced executable:", args.output / manifest["exe_name"])
    print("Includes: normal enhancements + local identity + direct UDP + vendor guards")
    print("Native map/game join and whole-process vendor isolation: NOT VERIFIED")


if __name__ == "__main__":
    main()
