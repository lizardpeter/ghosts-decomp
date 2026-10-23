#!/usr/bin/env python3
"""No custom-process vendor initialization, scanning, blob creation or submission."""
import struct
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/offline'),str(ROOT/'tests/differential')]
import package
from harness import Image,Machine,original_exe
from unicorn import UC_HOOK_CODE


def main():
    for mode in ('offline','direct'):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'package'
            manifest=package.package(original_exe(package.BUILD),ROOT/'build'/package.BUILD/mode/'recon.dll',output,mode)
            exe,dll=Image(output/'iw6mp64_offline.exe'),Image(output/'recon.dll')
            m=Machine(exe,dll)
            for slot,name in exe.iat.items():
                if name.startswith('recon.dll!'):m.mu.mem_write(slot,struct.pack('<Q',dll.exports[name.split('!',1)[1]]))
            # A guarded call must never execute any other original instruction.
            def forbid(mu,address,size,context):
                if address not in package.VENDOR_TASKS:raise AssertionError(f'original dependency reached {address:09X}')
            hook=m.mu.hook_add(UC_HOOK_CODE,forbid,begin=exe.base,end=exe.base+exe.size-1)
            for va,export in package.VENDOR_TASKS.items():
                for pointer in (0,1,0xFFFFFFFFFFFFFFFF):
                    ret='int' if export=='Iw6VendorChallengeUnavailable' else 'void'
                    result,buffers,writes,observed=m.call(va,[pointer]*6,ret=ret)
                    assert result==(0 if ret=='int' else None),(mode,va,result)
                    assert not buffers and not writes and not observed,(mode,va,writes,observed)
                    assert not m.imports_called,m.imports_called
            m.mu.hook_del(hook)
            assert all(any(g['va']==f'{va:09X}' and g['symbol']==export for g in manifest['guards'])
                       for va,export in package.VENDOR_TASKS.items())
    print('PASS: 10 vendor service entry removals in offline/direct; invalid payload pointers never read; no original work, writes or imports')

if __name__=='__main__':main()
