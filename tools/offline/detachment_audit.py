#!/usr/bin/env python3
"""Fail-closed checks for the *known* Microsoft/Xbox egress boundaries.

This is a structural audit of an experimental custom executable, not proof that
the whole process (including Windows brokers, IPC and child processes) is offline.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import pefile

# GDK loader, query/initialization, game startup/frame, and event submission.
# These entries must be redirected in the *packaged executable*, not just in
# source-linked calls in the reconstructed DLL.
GDK_ENTRIES = {
    0x1406AEE34, 0x1406AEC18, 0x1406AEE74,
    0x1406AF4BC, 0x1406AF52C, 0x1401A1930,
    0x1401A1760, 0x1406AF274,
}
DIRECT_ENTRIES = {
    0x140245440,  # original LUI XStore licence-refresh callback
    0x14054B1B0, 0x14054B290,  # local-only readiness gates
    0x14054F200, 0x14054F960, 0x14054FB70,
    0x1401A7DB0, 0x1401A7E10, 0x14054C360, 0x14054C0F0,
}
# An unexpected direct import from one of these SDK/HTTP providers is a build
# error. Windows itself may load other providers for unrelated local features.
FORBIDDEN_IMPORT_DLLS = {
    "xgameruntime.dll", "xcurl.dll", "winhttp.dll", "wininet.dll",
    "urlmon.dll", "xboxliveapi.dll", "xboxservices.dll",
    "gamingservices.dll",
}
# The original executable can retain non-egress Winsock utilities, but not a
# way to create/send/connect through its unguarded original import table.
ORIGINAL_WINSOCK_EGRESS = {
    "socket", "wsasocketa", "wsasocketw", "connect", "wsaconnect",
    "send", "sendto", "wsasend", "wsasendto", "wsaioctl",
    "gethostbyname", "getaddrinfo", "getaddrinfow",
}
# These DLLs have no legitimate role inside the custom game process. Loading a
# module is not itself traffic; use this as a regression signal, not an egress
# or licence/DRM assertion.
UNEXPECTED_RUNTIME_DLLS = {
    "xgameruntime.dll", "xcurl.dll", "xboxliveapi.dll",
    "xboxservices.dll", "gamingservices.dll",
}
# The pinned original may statically import only a subset of LoadLibrary*
# functions. GetProcAddress is required, and its returned loader pointers are
# separately wrapped/tested even when they are not static imports.
REQUIRED_LOADER_WRAPPERS = {"Iw6OfflineGetProcAddress"}


def _name(value):
    return (value.decode("ascii") if isinstance(value, bytes) else str(value)).lower()


def _imports(image):
    """Return IAT RVA -> (provider, name/ordinal) for the resulting PE."""
    pe = pefile.PE(data=image)
    if getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", None):
        raise ValueError("Unreviewed delay-loaded imports")
    entries = {}
    for descriptor in pe.DIRECTORY_ENTRY_IMPORT:
        provider = _name(descriptor.dll)
        for imp in descriptor.imports:
            rva = imp.address - pe.OPTIONAL_HEADER.ImageBase
            if rva in entries:
                raise ValueError("Duplicate IAT RVA in final image")
            name = _name(imp.name) if imp.name else "#" + str(imp.ordinal)
            entries[rva] = (provider, name)
    return entries


def audit_replacement_dll(dll_image, manifest):
    """Check that the *actual* recon.dll owns every promised guard/IAT target.

    A manifest and patched EXE can agree with each other while referencing
    a different or incomplete DLL. Do not trust those two sources alone.
    """
    errors = []
    if hashlib.sha256(dll_image).hexdigest() != manifest.get("dll_sha256"):
        errors.append("Replacement recon.dll hash does not match manifest")
    try:
        dll = pefile.PE(data=dll_image)
        if dll.OPTIONAL_HEADER.ImageBase != 0x180000000:
            errors.append("Replacement recon.dll has unexpected image base")
        if getattr(dll, "DIRECTORY_ENTRY_DELAY_IMPORT", None):
            errors.append("Unreviewed replacement DLL delay imports")
        if not hasattr(dll, "DIRECTORY_ENTRY_EXPORT"):
            return errors + ["Replacement DLL has no export directory"]
        exports = {}
        for symbol in dll.DIRECTORY_ENTRY_EXPORT.symbols:
            if symbol.name:
                name = symbol.name.decode("ascii", errors="replace")
                exports[name] = dll.OPTIONAL_HEADER.ImageBase + symbol.address
        # Import adapters and entry guards must resolve to executable exports
        # at the exact VA encoded in the original patched game executable.
        for item in manifest.get("guards", []):
            try:
                name = item["symbol"]
                target = int(item["export_va"], 16)
                if exports.get(name) != target:
                    errors.append("Wrong replacement DLL target for %s" % name)
            except (KeyError, TypeError, ValueError, AttributeError):
                errors.append("Invalid guard/export record for replacement DLL")
        for item in manifest.get("imports", []):
            try:
                name = item["export"]
                if name not in exports:
                    errors.append("Missing replacement import adapter: " + name)
            except (KeyError, TypeError):
                errors.append("Invalid import/export record for replacement DLL")
        if "Iw6OfflineBootstrap" not in exports or "Iw6OfflineDllMain" not in exports:
            errors.append("Replacement DLL lacks required offline bootstrap")
        if ("Iw6DirectProfile" in exports) != (manifest.get("mode") == "direct"):
            errors.append("Replacement DLL profile does not match manifest")
        # These are DLL dependencies, not just game EXE dependencies.
        for entry in dll.DIRECTORY_ENTRY_IMPORT:
            provider = _name(entry.dll)
            if provider in FORBIDDEN_IMPORT_DLLS:
                errors.append("Replacement DLL imports forbidden provider: " + provider)
    except (pefile.PEFormatError, AttributeError, ValueError) as error:
        errors.append("Cannot inspect replacement DLL: %s" % error)
    return errors


def audit_package(image, manifest, dll_image=None):
    """Return actionable errors; never claim whole-process isolation."""
    errors = []
    mode = manifest.get("mode")
    if mode not in ("offline", "direct"):
        errors.append("Unknown package profile")
    if hashlib.sha256(image).hexdigest() != manifest.get("exe_sha256"):
        errors.append("Packaged EXE does not match manifest hash")
    if manifest.get("build") != "iw6mp64_MSStore_ship":
        errors.append("Package is not the pinned Store multiplayer target")
    guard_list = manifest.get("guards", [])
    try:
        guards = {int(item["va"], 16): item["symbol"] for item in guard_list}
    except (KeyError, TypeError, ValueError):
        errors.append("Malformed guard manifest")
        guards = {}
    if len(guards) != len(guard_list):
        errors.append("Duplicate original function guard")
    # Verify every *actual original entry*, independent of the manifest's
    # after bytes and of the packaging function that constructed the image.
    # This also checks non-GDK vendor and direct-mode entries.
    try:
        patched_pe = pefile.PE(data=image)
        base = patched_pe.OPTIONAL_HEADER.ImageBase
        for item in guard_list:
            try:
                va = int(item["va"], 16)
                destination = int(item["export_va"], 16)
                patch = bytes.fromhex(item["after"])
                rva = va - base
                section = patched_pe.get_section_by_rva(rva)
                if not section or not (section.Characteristics & 0x20000000):
                    errors.append("Guard outside executable section at %09X" % va)
                    continue
                offset = patched_pe.get_offset_from_rva(rva)
                expected = b"\xe9" + struct.pack("<i", destination - va - 5)
                if len(patch) != 5 or patch != expected or image[offset:offset+5] != expected:
                    errors.append("Incorrect or missing original entry jump at %09X" % va)
            except (KeyError, ValueError, TypeError, OverflowError, struct.error):
                errors.append("Invalid guard entry metadata")
    except (pefile.PEFormatError, AttributeError) as error:
        errors.append("Cannot inspect packaged function guards: %s" % error)
    for va in sorted(GDK_ENTRIES - guards.keys()):
        errors.append("Missing GDK guard at %09X" % va)
    if mode == "direct":
        for va in sorted(DIRECT_ENTRIES - guards.keys()):
            errors.append("Missing direct/local-session entry at %09X" % va)

    try:
        imports = _imports(image)
    except (ValueError, pefile.PEFormatError, AttributeError) as error:
        return errors + ["Cannot inspect final PE imports: %s" % error]
    for rva, (provider, name) in sorted(imports.items()):
        if provider in FORBIDDEN_IMPORT_DLLS:
            errors.append("Forbidden provider import %s!%s at IAT %X" % (provider, name, rva))
        if provider == "ws2_32.dll" and name in ORIGINAL_WINSOCK_EGRESS:
            errors.append("Original network egress import %s at IAT %X" % (name, rva))

    redirected = manifest.get("imports", [])
    if not isinstance(redirected, list):
        return errors + ["Malformed import redirection manifest"]
    adapter_names = set()
    for record in redirected:
        try:
            rva, export = record["iat_rva"], record["export"]
            actual = imports.get(rva)
            if actual != ("recon.dll", export.lower()):
                errors.append("Redirect at IAT %X is not wired to recon.dll!%s" % (rva, export))
            adapter_names.add(export)
        except (TypeError, KeyError, AttributeError):
            errors.append("Malformed redirected import")
    for name in sorted(REQUIRED_LOADER_WRAPPERS - adapter_names):
        errors.append("Missing dynamic loader/procedure guard: " + name)
    if not any(_name(item.get("provider", "")) == "xcurl.dll" for item in redirected):
        errors.append("XCurl imports were not redirected")
    if not any(_name(item.get("provider", "")) == "winhttp.dll" for item in redirected):
        errors.append("WinHTTP imports were not redirected")
    if dll_image is None:
        errors.append("Replacement recon.dll was not supplied for verification")
    else:
        errors.extend(audit_replacement_dll(dll_image, manifest))
    # Manifest status flags are deliberately not promoted by this static test.
    return errors


def audit_runtime(report):
    """Review a bounded native debug trace for direct GDK client DLL loads."""
    errors = []
    modules = []
    for item in report.get("events", []):
        # 3=CREATE_PROCESS_DEBUG_EVENT; 6=LOAD_DLL_DEBUG_EVENT.
        if item.get("event") not in (3, 6) or not item.get("path"):
            continue
        module = item["path"].replace("\\", "/").rsplit("/", 1)[-1].lower()
        modules.append(module)
        if module in UNEXPECTED_RUNTIME_DLLS:
            errors.append("Unexpected vendor runtime module: " + module)
    if not modules:
        errors.append("Native trace has no named module loads; cannot assess runtime dependencies")
    return errors, {"observed_modules": len(modules),
                    "unexpected_vendor_modules": sorted(set(modules) & UNEXPECTED_RUNTIME_DLLS),
                    "whole_process_egress_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dll", type=Path, help="replacement recon.dll (defaults to EXE directory)")
    parser.add_argument("--runtime", type=Path, help="optional native_smoke.py JSON trace")
    parser.add_argument("--output", type=Path, help="optional machine-readable audit")
    args = parser.parse_args()
    image = args.exe.read_bytes()
    manifest = json.loads(args.manifest.read_text())
    dll_path = args.dll or args.exe.with_name("recon.dll")
    errors = audit_package(image, manifest, dll_path.read_bytes() if dll_path.exists() else None)
    runtime = None
    if args.runtime:
        more, runtime = audit_runtime(json.loads(args.runtime.read_text()))
        errors.extend(more)
    result = {"passed": not errors, "errors": errors,
              "profile": manifest.get("mode"), "runtime": runtime,
              "whole_process_egress_verified": False}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
