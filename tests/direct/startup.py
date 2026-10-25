#!/usr/bin/env python3
"""Original package/DLL boundary: early local profile from native command line.

Runs the same Windows import and custom export in Unicorn; no account, UI,
filesystem or vendor-provider calls are modeled.
"""
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/offline'), str(ROOT/'tests/differential')]
import package
from harness import Image, Machine, original_exe, SCRATCH
from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX

CMDLINE = SCRATCH + 0x4000


def main():
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / 'package'
        package.package(original_exe(package.BUILD),
                        ROOT/'build'/package.BUILD/'direct/recon.dll', output, 'direct')
        exe = Image(output/'iw6mp64_offline.exe')
        dll = Image(output/'recon.dll')
        m = Machine(exe, dll)
        for slot, name in exe.iat.items():
            if name.startswith('recon.dll!'):
                m.mu.mem_write(slot, struct.pack('<Q', dll.exports[name.split('!', 1)[1]]))
        milestone = []
        m.on_import('kernel32.dll!GetCommandLineA',
                    lambda mu: mu.reg_write(UC_X86_REG_RAX, CMDLINE))
        m.on_import('kernel32.dll!OutputDebugStringA',
                    lambda mu: milestone.append(m.read_cstr(mu.reg_read(UC_X86_REG_RCX))))

        def run(command, expected):
            if command is None:
                data = b'\0'
            else:
                data = command + b'\0'
            def prepare(w):
                w.write(CMDLINE, data)
            # A DLL global write is rolled back by the differential harness;
            # no positive profile remains between these independent cases.
            value, _, writes, observed = m.call(dll.exports['Iw6DirectLoadStartupProfile'],
                                                 [], setup=prepare)
            assert value == expected and not observed, (command, value, observed)
            assert not any('xcurl' in name or 'xgameruntime' in name
                           for name in m.imports_called), m.imports_called
            return writes

        invalid = (
            b'game.exe +set fs_basepath "C:\\My +direct_player\\Data"',
            b'game.exe +direct_player 123456789abcdef0',
            b'game.exe +direct_player bogus LocalPlayer',
            b'game.exe +direct_player 0000000000000000 LocalPlayer',
            b'game.exe +direct_player 123456789abcdef0 "bad;name"',
            b'game.exe +direct_player 123456789abcdef0 "unterminated',
            b'game.exe +direct_player 123456789abcdef0 Valid +direct_player 1 Other',
            b'game.exe +set fs_homepath "' + b'x' * 8200 + b'"',
        )
        for command in invalid:
            count = len(milestone)
            assert not run(command, 0)
            assert len(milestone) == count, (command, milestone)
            assert m.call(dll.exports['Iw6DirectPlayerId'], [0], ret='int64')[0] == 0

        command = (b'"C:\\Games\\ghosts.exe" +set fs_basepath '
                   b'"C:\\Ghosts +direct_player\\assets" '
                   b'+direct_player 123456789ABCDEF0 "Local Player" '
                   b'+connect 127.0.0.1:27016')
        writes = run(command, 1)
        assert milestone == [b'IW6D:LOCAL_PROFILE_PREPARED'], milestone
        for address, byte in writes.items():
            m.mu.mem_write(address, byte)
        assert m.call(dll.exports['Iw6DirectPlayerId'], [0], ret='int64')[0] == 0x123456789ABCDEF0
        assert m.call(dll.exports['Iw6DirectPlayerName'], [0], ret='cstr')[0] == b'Local Player'
        assert m.call(dll.exports['Iw6DirectPlayerIdText'], [0], ret='cstr')[0] == b'123456789abcdef0'
        assert m.call(dll.exports['Iw6DirectPlayerId'], [1], ret='int64')[0] == 0
    print('PASS: bounded quoted direct launcher profile is initialized before deferred Cbuf commands')


if __name__ == '__main__':
    main()
