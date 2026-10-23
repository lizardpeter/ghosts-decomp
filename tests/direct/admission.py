#!/usr/bin/env python3
"""Probe original local-network admission, stopping at game VM/response boundaries.

This verifies the admission branch only; game/map initialization and response
serialization are modeled and must not be reported as a completed multiplayer join.
"""
import struct
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/offline'),str(ROOT/'tests/differential')]
import package
from harness import Image,Machine,original_exe,SCRATCH
from unicorn.x86_const import UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9


def main():
    with tempfile.TemporaryDirectory() as temp:
        output=Path(temp)/'package'
        package.package(original_exe(package.BUILD),ROOT/'build'/package.BUILD/'direct/recon.dll',output,'direct')
        exe,dll=Image(output/'iw6mp64_offline.exe'),Image(output/'recon.dll')
        m=Machine(exe,dll)
        for slot,name in exe.iat.items():
            if name.startswith('recon.dll!'):m.mu.mem_write(slot,struct.pack('<Q',dll.exports[name.split('!',1)[1]]))
        fields={b'protocol':b'179',b'checksum':b'123',b'challenge':b'456',b'statver':b'1 2',b'qport':b'12345',b'xuid':b'123456789abcdef0'}
        info_area=SCRATCH+0x20000
        def info(mu):
            key=m.read_cstr(mu.reg_read(UC_X86_REG_RDX))
            m._emulated_write(info_area,fields.get(key,b'0')+b'\0')
            return info_area
        def copy(mu):
            dst,src,n=(mu.reg_read(r) for r in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8))
            data=m.read_cstr(src)[:n-1]+b'\0'
            m._emulated_write(dst,data)
            return dst
        def sscanf(mu):
            text=m.read_cstr(mu.reg_read(UC_X86_REG_RCX))
            fmt=m.read_cstr(mu.reg_read(UC_X86_REG_RDX))
            if fmt==b'%i %u':
                values=[int(x) for x in text.split()]
            else:
                assert fmt==b'%8x%8x',fmt
                values=[int(text[:8],16),int(text[8:],16) if text[8:] else 0]
            for register,value in zip((UC_X86_REG_R8,UC_X86_REG_R9),values):
                m._emulated_write(mu.reg_read(register),struct.pack('<I',value))
            return len(values)
        m.on_import('api-ms-win-crt-convert-l1-1-0.dll!atoi',lambda mu:mu.reg_write(UC_X86_REG_RAX,int(m.read_cstr(mu.reg_read(UC_X86_REG_RCX)))))
        outcomes=[]
        def error(mu):outcomes.append(('error',m.read_cstr(mu.reg_read(UC_X86_REG_R8))));return 1
        def response(mu):outcomes.append(('response',mu.reg_read(UC_X86_REG_RCX)));return 0
        def forbidden(mu):raise AssertionError('admission entered a vendor/runtime dependency')
        fakes={
            0x1405462B0:info,0x140545B60:copy,0x1401951B0:sscanf,
            0x14053A7C0:lambda mu:179,0x14044F940:lambda mu:1,0x14044F910:lambda mu:2,
            0x1404C6380:lambda mu:0,0x14046B420:lambda mu:0,
            0x140323090:lambda mu:0x14999B4C0,0x140329B10:lambda mu:-1,
            0x1404D8440:lambda mu:-1,0x1404D8CD0:lambda mu:0,
            0x140264CD0:lambda mu:0,0x140480000:lambda mu:17,
            0x1403D5430:lambda mu:0, # ClientConnect: game VM boundary, not executed
            0x1404BB600:lambda mu:None,0x1404BF410:lambda mu:None,0x1404D27A0:lambda mu:None,
            0x1403EC980:lambda mu:SCRATCH+0x30000,0x1405CF250:lambda mu:0,
            0x14017A790:lambda mu:None,0x1404BE720:response,0x14046A390:error,
            0x1406AEE34:forbidden,0x1406AEE74:forbidden,0x1405DA470:forbidden,
        }
        address=struct.pack('<I4sH2xI',4,b'\x7f\0\0\1',0x8869,0xFFFFFFFF)
        def setup(online,valid_challenge=True):
            def apply(w):
                argv=w.alloc(struct.pack('<QQQ',w.cstr(b'connect'),w.cstr(b'123456789abcdef0'),w.cstr(b'\\protocol\\179')))
                w.u32(0x1469CEDA0,0);w.u32(0x1469CEDE4,3);w.u64(0x1469CEE08,argv)
                w.u32(0x149996FE8,123);w.u32(0x148928A8C,2)
                for pointer,value in [(0x1442B98C8,online),(0x149997130,0),(0x146A7D6C0,1)]:
                    block=w.alloc(bytes(0x10)+struct.pack('<I',value)+bytes(0x40));w.u64(pointer,block)
                w.write(0x149793C2C,address)
                w.u32(0x149793C3C,456 if valid_challenge else 457)
                w.write(0x149793C48,b'123456789abcdef0\0')
            return apply
        for online,valid in [(False,True),(True,True),(False,False)]:
            outcomes.clear()
            value,_,writes,_=m.call(0x1404BC1D0,[address],ret='void',setup=setup(online,valid),fakes=fakes)
            assert value is None,(value,outcomes,m.imports_called)
            if not valid:assert outcomes==[('error',b'error\nEXE_BAD_CHALLENGE')],outcomes
            elif online:assert outcomes==[('error',b'error\nEXE_ERR_UNREGISTERED_CONNECTION')],outcomes
            else:
                slot=0x148928A90+0x83568
                assert outcomes==[('response',slot)],outcomes
                state=b''.join(writes.get(slot+i,b'\0') for i in range(4))
                assert struct.unpack('<i',state)[0]==3,state
            assert not any(n.startswith(('winhttp.dll!','xcurl.dll!')) for n in m.imports_called)
        print('PASS: original LAN admission reaches response boundary with empty party; online admission refuses unregistered client; invalid challenge refused')

if __name__=='__main__':main()
