#!/usr/bin/env python3
"""Loader-model integration tests against a newly packaged pinned executable.

This deliberately enters original EXE code/IAT slots, not enhanced exports.
It models import resolution; it is not a Windows loader or game launch test.
"""
import json
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/offline'), str(ROOT / 'tests/differential')]
import package
from harness import Image, Machine, original_exe
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_RAX


def check():
    original = original_exe(package.BUILD)
    dll_path = ROOT / 'build' / package.BUILD / 'offline/recon.dll'
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / 'package'
        manifest = package.package(original, dll_path, output)
        exe, dll = Image(output / 'iw6mp64_offline.exe'), Image(output / 'recon.dll')
        m = Machine(exe, dll)
        # Resolve actual recon exports into original IAT slots, like the loader.
        for slot, name in exe.iat.items():
            if name.startswith('recon.dll!'):
                m.mu.mem_write(slot, struct.pack('<Q', dll.exports[name.split('!',1)[1]]))
        assert len(manifest['guards']) == 31 and len(manifest['imports']) == 55
        errors = []
        m.on_import('kernel32.dll!SetLastError', lambda mu: errors.append(mu.reg_read(UC_X86_REG_RCX)))
        m.on_import('ws2_32.dll!WSASetLastError', lambda mu: errors.append(mu.reg_read(UC_X86_REG_RCX)))
        # Every vendor entry branches to its exact enhanced export before executing original code.
        for guard in manifest['guards']:
            va, target = int(guard['va'],16), int(guard['export_va'],16)
            visited = []
            def stop(mu, address, size, data):
                visited.append(address)
                if address == target: mu.emu_stop()
            hook = m.mu.hook_add(UC_HOOK_CODE, stop)
            m.mu.emu_start(va, target + 1, count=2)
            m.mu.hook_del(hook)
            assert visited == [va, target], (guard, visited)
        # Original game calls now enter no-work guards, without original dependencies.
        for symbol, args, expected in [
            ('XGameRuntimeInitialize', [], -0x76DBFF00),
            ('XGameEventWrite', [1]*6, -0x76DBFF00),
            ('?sub_1405D6A90@@YAHPEBDI@Z', [1,9], 0),
        ]:
            guard = next(g for g in manifest['guards'] if g['symbol'] == symbol)
            value, _, _, observed = m.call(int(guard['va'],16), args)
            assert value == expected and not observed, (symbol, value)
            assert not m.imports_called, m.imports_called
        # Unmodified original account thunk inherits the patched interface-query guard.
        table = package.symbols.table(package.BUILD)
        names = [name for name in table if 'XUserGetGamertag' in name]
        assert len(names) == 1, names
        va = table[names[0]][0]
        assert va not in {int(g['va'],16) for g in manifest['guards']}
        result = m.call(va, [1,0,0,1,0])[0]
        assert result == -0x76DBFF00, result
        assert not m.imports_called, m.imports_called
        # Calls through original network/process/event IATs execute actual failure code.
        results = {'Iw6DenyNull':0, 'Iw6DenyMinusOne':-1, 'Iw6DenyStatus':5,
                   'Iw6DenyCurl':2, 'Iw6DenyCurlMulti':4, 'Iw6DenySocket':-1,
                   'Iw6DenyDns':0, 'Iw6DenyAddrInfo':10013,
                   'Iw6DenyCom':-0x7FF8FFFB, 'Iw6DenyEventRegister':5}
        tested = 0
        for imp in manifest['imports']:
            export = imp['export']
            if export not in results: continue
            address = struct.unpack('<Q', m.mu.mem_read(exe.base + imp['iat_rva'],8))[0]
            assert address == dll.exports[export]
            # Zero optional output pointers, but poison unused payload arguments.
            args = [0,0,0,0,0]
            if export not in {'Iw6DenyAddrInfo','Iw6DenyCom','Iw6DenyEventRegister'}: args = [1]*6
            errors.clear()
            value = m.call(address, args)[0]
            assert value == results[export], (imp, value)
            assert errors == [10013 if export in {'Iw6DenySocket','Iw6DenyDns','Iw6DenyAddrInfo'} else 5]
            tested += 1
        # Requirements are also asserted by original API identity, independently
        # of the packager's manifest/export selection.
        original_slots = {name:slot for slot,name in Image(original).iat.items()}
        required = {
            'winhttp.dll!WinHttpOpen':0, 'winhttp.dll!WinHttpSendRequest':0,
            'xcurl.dll!curl_easy_init':0, 'xcurl.dll!curl_easy_setopt':2,
            'ws2_32.dll!socket':-1, 'ws2_32.dll!WSASocketA':-1,
            'ws2_32.dll!connect':-1, 'ws2_32.dll!send':-1,
            'ws2_32.dll!sendto':-1, 'ws2_32.dll!WSASendTo':-1,
            'ws2_32.dll!WSAIoctl':-1, 'ws2_32.dll!gethostbyname':0,
            'ws2_32.dll!getaddrinfo':10013, 'kernel32.dll!CreateProcessA':0,
            'ole32.dll!CoCreateInstance':-0x7FF8FFFB,
            'shell32.dll!ShellExecuteA':5, 'advapi32.dll!EventRegister':5,
        }
        for identity, expected in required.items():
            slot = original_slots[identity]
            assert exe.iat[slot].startswith('recon.dll!'), identity
            target = struct.unpack('<Q',m.mu.mem_read(slot,8))[0]
            assert m.call(target,[0]*6)[0] == expected, identity
        # Out parameters are cleared on refused DNS, COM and event registration.
        for export, args, index in [
            ('Iw6DenyAddrInfo',[0,0,0,b'POISON!!'],0),
            ('Iw6DenyCom',[0,0,0,0,b'POISON!!'],0),
            ('Iw6DenyEventRegister',[0,0,0,b'POISON!!'],0),
        ]:
            value, buffers, _, _ = m.call(dll.exports[export], args)
            assert buffers[index] == bytes(8), (export,buffers)
        # Dynamic resolution must not reintroduce blocked libraries or broker activation.
        for fn in ('LoadLibraryA','LoadLibraryW','LoadLibraryExA','LoadLibraryExW'):
            calls = []
            m.on_import('kernel32.dll!'+fn, lambda mu: calls.append(1))
            for path in ('WINHTTP.dll','C:\\Windows\\System32\\XGameRuntime.DLL','xcurl','ws2_32.dll','urlmon.dll','wininet'):
                encoded = path.encode('utf-16le')+b'\0\0' if fn.endswith('W') else path.encode()+b'\0'
                assert m.call(dll.exports['Iw6Offline'+fn],[encoded,0,0])[0] == 0
                assert not calls
            encoded = 'd3d11.dll'.encode('utf-16le')+b'\0\0' if fn.endswith('W') else b'd3d11.dll\0'
            m.call(dll.exports['Iw6Offline'+fn],[encoded,0,0])
            assert calls == [1]
        def module_path(path, count=None):
            def fake(mu):
                mu.mem_write(mu.reg_read(UC_X86_REG_RDX),path.encode('utf-16le')+b'\0\0')
                mu.reg_write(UC_X86_REG_RAX, len(path) if count is None else count)
            m.on_import('kernel32.dll!GetModuleFileNameW',fake)
        calls = []
        m.on_import('kernel32.dll!GetProcAddress', lambda mu: (calls.append(1), mu.reg_write(UC_X86_REG_RAX,123)))
        for path, name in [('C:\\Windows\\WINHTTP.dll', b'WinHttpOpen\0'),
                           ('combase.dll',b'RoGetActivationFactory\0'),
                           ('combase.dll',b'RoActivateInstance\0')]:
            module_path(path)
            assert m.call(dll.exports['Iw6OfflineGetProcAddress'],[1,name])[0] == 0
            assert not calls
        for count in (0,512):
            module_path('d3d11.dll',count)
            assert m.call(dll.exports['Iw6OfflineGetProcAddress'],[1,b'D3D11CreateDevice\0'])[0] == 0
        module_path('d3d11.dll')
        assert m.call(dll.exports['Iw6OfflineGetProcAddress'],[1,b'D3D11CreateDevice\0'])[0] == 123
        assert m.call(dll.exports['Iw6OfflineGetProcAddress'],[1,7])[0] == 123
        assert calls == [1,1]
        for name, export in [('GetProcAddress','Iw6OfflineGetProcAddress'),
                             ('LoadLibraryA','Iw6OfflineLoadLibraryA'),
                             ('LoadLibraryW','Iw6OfflineLoadLibraryW'),
                             ('LoadLibraryExA','Iw6OfflineLoadLibraryExA'),
                             ('LoadLibraryExW','Iw6OfflineLoadLibraryExW'),
                             ('CreateProcessW','Iw6DenyNull'),
                             ('ShellExecuteW','Iw6DenyStatus')]:
            result = m.call(dll.exports['Iw6OfflineGetProcAddress'],[1,name.encode()+b'\0'],ret='int64')[0]
            assert result == dll.exports[export], (name,result)
        assert calls == [1,1]
        # DLL attach succeeds only for the prepared preferred-base host.
        terminated = []
        m.on_import('kernel32.dll!GetModuleHandleW',lambda mu: mu.reg_write(UC_X86_REG_RAX,exe.base))
        m.on_import('kernel32.dll!GetCurrentProcess',lambda mu: mu.reg_write(UC_X86_REG_RAX,0xFFFFFFFFFFFFFFFF))
        m.on_import('kernel32.dll!TerminateProcess',lambda mu: terminated.append(mu.reg_read(UC_X86_REG_RDX)))
        entry = dll.base + dll.pe.OPTIONAL_HEADER.AddressOfEntryPoint
        assert m.call(entry,[dll.base,1,0])[0] == 1 and not terminated
        assert m.call(entry,[dll.base+0x1000,1,0])[0] == 0 and terminated == [0xE0010001]
        marker = exe.base + exe.pe.sections[-1].VirtualAddress
        assert m.call(entry,[dll.base,1,0],setup=lambda w:w.write(marker,b'BROKEN!!'))[0] == 0
        # Refuse wrong inputs and overwrites; originals stay byte-identical.
        before = package.sha(original.read_bytes())
        rebuilt, rebuilt_manifest = package.transform(original.read_bytes(),dll_path.read_bytes())
        assert rebuilt == (output/'iw6mp64_offline.exe').read_bytes()
        assert rebuilt_manifest == manifest
        ordinary = ROOT/'build'/package.BUILD/'enhanced/recon.dll'
        if ordinary.exists():
            try: package.transform(original.read_bytes(),ordinary.read_bytes())
            except ValueError: pass
            else: raise AssertionError('ordinary enhanced DLL accepted as offline')
        for bad in (b'', original.read_bytes()[:-1]):
            try: package.transform(bad,dll_path.read_bytes())
            except ValueError: pass
            else: raise AssertionError('wrong original accepted')
        try: package.package(original,dll_path,output)
        except FileExistsError: pass
        else: raise AssertionError('existing package overwritten')
        assert package.sha(original.read_bytes()) == before
        assert json.loads((output/'manifest.json').read_text()) == manifest
        assert not manifest['native_launch_verified'] and not manifest['whole_process_egress_verified']
        # PE structure: all original slots retained, no XCurl/WinHTTP provider remains.
        original_image = Image(original)
        assert set(original_image.iat) <= set(exe.iat)
        assert all(not n.startswith(('winhttp.dll!','xcurl.dll!')) for n in exe.iat.values())
        assert package.sha((output/'iw6mp64_offline.exe').read_bytes()) == manifest['exe_sha256']
        assert exe.pe.verify_checksum()
        print(f'PASS: 31 original guard entries; original account thunk; {tested} failure imports; dynamic loading, bootstrap, PE and refusal checks')


if __name__ == '__main__':
    check()
