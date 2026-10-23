#!/usr/bin/env python3
"""Experimental Store MP startup package; never modifies the supplied original.

Imports keep their original IAT slots. New ILTs/descriptors split each original
provider into contiguous runs, so call sites and pointers need no rewriting.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import struct
import sys
import tomllib
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import symbols

BUILD = 'iw6mp64_MSStore_ship'
MAGIC = b'IW6OFFLINE1\0\0\x01\0\0\0'
PATCHES = {'P0005', 'P0006', 'P0007', 'P0008', 'P0010'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def align(n, a):
    return (n + a - 1) // a * a


def adapter(dll, name):
    dll = dll.lower()
    if dll == 'winhttp.dll':
        return 'Iw6DenyMinusOne' if name == 'WinHttpSetStatusCallback' else 'Iw6DenyNull'
    if dll == 'xcurl.dll':
        if name == 'curl_easy_strerror': return 'Iw6OfflineErrorText'
        if name in {'curl_global_init', 'curl_easy_setopt', 'curl_easy_getinfo'}: return 'Iw6DenyCurl'
        if name in {'curl_multi_add_handle', 'curl_multi_remove_handle', 'curl_multi_perform', 'curl_multi_poll'}: return 'Iw6DenyCurlMulti'
        return 'Iw6DenyNull'
    if dll == 'ws2_32.dll':
        if name in {'socket', 'WSASocketA', 'connect', 'send', 'sendto', 'WSASendTo', 'WSAIoctl'}: return 'Iw6DenySocket'
        if name == 'gethostbyname': return 'Iw6DenyDns'
        if name == 'getaddrinfo': return 'Iw6DenyAddrInfo'
    if dll == 'kernel32.dll':
        if name in {'LoadLibraryA', 'LoadLibraryW', 'LoadLibraryExA', 'LoadLibraryExW', 'GetProcAddress'}: return 'Iw6Offline' + name
        if name == 'CreateProcessA': return 'Iw6DenyNull'
    if dll == 'ole32.dll' and name == 'CoCreateInstance': return 'Iw6DenyCom'
    if dll == 'shell32.dll' and name == 'ShellExecuteA': return 'Iw6DenyStatus'
    if dll == 'advapi32.dll':
        if name == 'EventRegister': return 'Iw6DenyEventRegister'
        if name in {'EventWriteTransfer', 'EventSetInformation'}: return 'Iw6DenyStatus'
    if dll.startswith('api-ms-win-crt-'):
        if name == 'system': return 'Iw6DenyMinusOne'
        if name == '_popen': return 'Iw6DenyNull'
    return None


def guards():
    """Only the explicitly reviewed vendor patches; never redirect all exports."""
    rows = list(csv.DictReader((ROOT / 'records/patches.tsv').open(), delimiter='\t'))
    addresses = set()
    for row in rows:
        if row['id'] in PATCHES:
            addresses.update(int(s, 16) for s in re.findall(r'\b140[0-9A-F]{6}\b', '\t'.join(row.values())))
    if len(addresses) != 31:
        raise ValueError('vendor guard profile changed; review the 31 entries')
    table = symbols.table(BUILD)
    return [(va, name) for va in sorted(addresses)
            for name, (addr, kind) in table.items() if addr == va and kind == 'function']


def transform(original, dll_bytes):
    cfg = tomllib.loads((ROOT / 'target.toml').read_text())
    expected = next(b['exe']['sha256'] for b in cfg['build'] if b['id'] == BUILD)
    if sha(original) != expected:
        raise ValueError('original does not match the pinned Store MP SHA-256')
    pe = pefile.PE(data=original)
    dll = pefile.PE(data=dll_bytes)
    if pe.OPTIONAL_HEADER.ImageBase != 0x140000000 or dll.OPTIONAL_HEADER.ImageBase != 0x180000000:
        raise ValueError('fixed image bases required')
    if dll.OPTIONAL_HEADER.AddressOfEntryPoint == 0 or dll.OPTIONAL_HEADER.DllCharacteristics & 0x40:
        raise ValueError('build the DLL using --offline (fixed base and bootstrap required)')
    exports = {e.name.decode(): dll.OPTIONAL_HEADER.ImageBase + e.address for e in dll.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
    if not {'Iw6OfflineBootstrap', 'Iw6OfflineDllMain', 'Iw6DenySocket'} <= exports.keys():
        raise ValueError('offline exports missing')
    if exports['Iw6OfflineDllMain'] != dll.OPTIONAL_HEADER.ImageBase + dll.OPTIONAL_HEADER.AddressOfEntryPoint:
        raise ValueError('DLL entry must be the offline attach guard')
    if any(d.VirtualAddress for d in [pe.OPTIONAL_HEADER.DATA_DIRECTORY[13]]):
        raise ValueError('unreviewed delay imports')
    data = bytearray(original)
    rva = align(max(s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData) for s in pe.sections), pe.OPTIONAL_HEADER.SectionAlignment)
    raw = align(len(data), pe.OPTIONAL_HEADER.FileAlignment)
    section_header = pe.sections[-1].get_file_offset() + 40
    if section_header + 40 > min(s.PointerToRawData for s in pe.sections if s.SizeOfRawData):
        raise ValueError('no section header space')
    payload = bytearray(MAGIC)
    def add(blob, alignment=1):
        payload.extend(b'\0' * (align(len(payload), alignment) - len(payload)))
        result = rva + len(payload)
        payload.extend(blob)
        return result
    def text(s): return add(s.encode('ascii') + b'\0')
    runs, redirected = [], []
    for desc in pe.DIRECTORY_ENTRY_IMPORT:
        provider = desc.dll.decode('ascii')
        current = None
        for imp in desc.imports:
            name = imp.name.decode('ascii') if imp.name else None
            replacement = adapter(provider, name)
            dest = 'recon.dll' if replacement else provider
            if current is None or current[0] != dest:
                current = [dest, imp.address - pe.OPTIONAL_HEADER.ImageBase, []]
                runs.append(current)
            if replacement:
                if replacement not in exports: raise ValueError('missing adapter ' + replacement)
                redirected.append({'provider': provider, 'name': name, 'iat_rva': imp.address - pe.OPTIONAL_HEADER.ImageBase, 'export': replacement})
            target = replacement or name
            thunk = add(b'\0\0' + target.encode('ascii') + b'\0', 2) if target else (1 << 63) | imp.ordinal
            current[2].append(thunk)
    # Explicit bootstrap import ensures recon.dll is loaded even if no guarded call runs.
    bootstrap_iat = add(b'\0' * 16, 8)
    runs.append(['recon.dll', bootstrap_iat, [add(b'\0\0Iw6OfflineBootstrap\0', 2)]])
    descriptors = bytearray()
    for provider, iat, thunks in runs:
        ilt = add(struct.pack('<' + 'Q' * (len(thunks) + 1), *thunks, 0), 8)
        descriptors.extend(struct.pack('<IIIII', ilt, 0, 0, text(provider), iat))
    imports_rva = add(descriptors + b'\0' * 20, 4)
    changes = []
    functions = {int(row['va'],16): int(row['size']) for row in csv.DictReader((ROOT / 'analysis' / BUILD / 'functions.tsv').open(), delimiter='\t')}
    targets = [(va, name) for va, name in guards() if name in exports]
    if len(targets) != 31 or len({va for va, _ in targets}) != 31:
        raise ValueError('missing or ambiguous guard symbols')
    for va, symbol in targets:
        if symbol not in exports or functions[va] < 5: raise ValueError('invalid guard ' + symbol)
        offset = pe.get_offset_from_rva(va - pe.OPTIONAL_HEADER.ImageBase)
        patch = b'\xe9' + struct.pack('<i', exports[symbol] - va - 5)
        changes.append({'va': f'{va:09X}', 'symbol': symbol, 'export_va': f'{exports[symbol]:09X}', 'before': data[offset:offset+5].hex(), 'after': patch.hex()})
        data[offset:offset+5] = patch
    raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
    data.extend(b'\0' * (raw - len(data)))
    data.extend(payload + b'\0' * (raw_size - len(payload)))
    struct.pack_into('<8sIIIIIIHHI', data, section_header, b'.iw6off\0', len(payload), rva, raw_size, raw, 0, 0, 0, 0, 0xC0000040)
    def put(field, value, fmt='<I'):
        struct.pack_into(fmt, data, field, value)
    put(pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'), len(pe.sections)+1, '<H')
    put(pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'), align(rva + len(payload), pe.OPTIONAL_HEADER.SectionAlignment))
    put(pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfInitializedData'), pe.OPTIONAL_HEADER.SizeOfInitializedData + raw_size)
    put(pe.OPTIONAL_HEADER.get_field_absolute_offset('DllCharacteristics'), pe.OPTIONAL_HEADER.DllCharacteristics & ~0x60, '<H')
    for index in (4, 11): # signature and bound imports no longer describe this copy
        put(pe.OPTIONAL_HEADER.DATA_DIRECTORY[index].get_file_offset(), 0, '<Q')
    struct.pack_into('<II', data, pe.OPTIONAL_HEADER.DATA_DIRECTORY[1].get_file_offset(), imports_rva, len(descriptors)+20)
    put(pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'), 0)
    put(pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'), pefile.PE(data=bytes(data)).generate_checksum())
    manifest = {'format': 1, 'build': BUILD, 'original_sha256': expected,
                'exe_sha256': sha(data), 'dll_sha256': sha(dll_bytes),
                'guards': changes, 'imports': redirected,
                'native_launch_verified': False, 'whole_process_egress_verified': False}
    return bytes(data), manifest


def package(original, dll, output):
    dll_bytes = dll.read_bytes()
    patched, manifest = transform(original.read_bytes(), dll_bytes)
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / 'iw6mp64_offline.exe').write_bytes(patched)
        (output / 'recon.dll').write_bytes(dll_bytes)
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        for name in ('ConfigureSandbox.ps1', 'LaunchSandbox.ps1'):
            shutil.copyfile(ROOT / 'tools/offline' / name, output / name)
    except BaseException:
        shutil.rmtree(output)
        raise
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--dll', type=Path, default=ROOT / 'build' / BUILD / 'offline/recon.dll')
    parser.add_argument('--output', type=Path, required=True, help='new directory; must not exist')
    args = parser.parse_args()
    result = package(args.original, args.dll, args.output)
    print(f"Packaged {len(result['guards'])} guard jumps and {len(result['imports'])} import redirects; native verification pending")
