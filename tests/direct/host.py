#!/usr/bin/env python3
"""Run original map-start code to the spawn boundary; model assets, not a game launch."""
import struct
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/offline'),str(ROOT/'tests/differential')]
import package
from harness import Image,Machine,original_exe,SCRATCH
from winsock import Winsock,sockaddr_in
from unicorn.x86_const import UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_RSP


def main():
    with tempfile.TemporaryDirectory() as temp:
        output=Path(temp)/'package'
        package.package(original_exe(package.BUILD),ROOT/'build'/package.BUILD/'direct/recon.dll',output,'direct')
        exe,dll=Image(output/'iw6mp64_offline.exe'),Image(output/'recon.dll')
        m=Machine(exe,dll)
        for slot,name in exe.iat.items():
            if name.startswith('recon.dll!'):m.mu.mem_write(slot,struct.pack('<Q',dll.exports[name.split('!',1)[1]]))
        Winsock().install(m)
        def getsockname(mu):
            m._emulated_write(mu.reg_read(UC_X86_REG_RDX),sockaddr_in(b'\0'*4,27016))
            m._emulated_write(mu.reg_read(UC_X86_REG_R8),struct.pack('<I',16))
            mu.reg_write(UC_X86_REG_RAX,0)
        m.on_import('ws2_32.dll!getsockname',getsockname)
        m.on_import('ws2_32.dll!WSACleanup',lambda mu:mu.reg_write(UC_X86_REG_RAX,0))
        result=m.call(dll.exports['Iw6DirectPlayerConfigure'],[b'123456789abcdef0\0',b'LocalPlayer\0'])
        assert result[0]==1
        for address,value in result[2].items():m.mu.mem_write(address,value)
        events=[]
        def boolean(mu):
            assert mu.reg_read(UC_X86_REG_RDX)==0
            m._emulated_write(mu.reg_read(UC_X86_REG_RCX)+0x10,b'\0')
        def setting(mu):events.append(('setting',m.read_cstr(mu.reg_read(UC_X86_REG_RCX)),m.read_cstr(mu.reg_read(UC_X86_REG_RDX))))
        def compare(mu):
            a,b=(m.read_cstr(mu.reg_read(r)).lower() for r in (UC_X86_REG_RCX,UC_X86_REG_RDX))
            return (a>b)-(a<b)
        def prefix(mu):
            a,b=(m.read_cstr(mu.reg_read(r)).lower() for r in (UC_X86_REG_RCX,UC_X86_REG_RDX));n=mu.reg_read(UC_X86_REG_R8)
            return (a[:n]>b[:n])-(a[:n]<b[:n])
        def lower(mu):
            address=mu.reg_read(UC_X86_REG_RCX)
            m._emulated_write(address,m.read_cstr(address).lower()+b'\0')
            return address
        def asset(mu):events.append(('asset',m.read_cstr(mu.reg_read(UC_X86_REG_RCX))));return 1
        def prepare(mu):events.append(('prepare',m.read_cstr(mu.reg_read(UC_X86_REG_RCX))))
        def spawn(mu):
            fifth=struct.unpack('<Q',m.mu.mem_read(mu.reg_read(UC_X86_REG_RSP)+0x28,8))[0]&255
            events.append(('spawn',m.read_cstr(mu.reg_read(UC_X86_REG_RCX)),mu.reg_read(UC_X86_REG_RDX)&255,
                           mu.reg_read(UC_X86_REG_R8)&255,mu.reg_read(UC_X86_REG_R9)&255,fifth))
        def missing_path(mu):m._emulated_write(mu.reg_read(UC_X86_REG_R9),b'missing.ff\0')
        def reject_content(mu):events.append(('content_rejected',));return 0
        fakes={0x14053E7E0:boolean,0x14053F550:setting,0x140545B90:prefix,0x1405458B0:compare,
               0x140545A60:lower,0x14036C020:asset,0x140536180:lambda mu:0,
               0x140536200:lambda mu:0,0x14053ACD0:lambda mu:1,
               0x14052C360:prepare,0x1404C2640:spawn,0x14036B2B0:missing_path,
               0x140545510:lambda mu:0,0x1401A5150:reject_content}
        def setup(w):
            w.write(0x143E96821,b'\1');w.u32(0x143E96890,0)
            online=w.alloc(bytes(0x10)+b'\1'+bytes(0x50));w.u64(0x1442B98C8,online)
            running=w.alloc(bytes(0x60));w.u64(0x146A7D6C0,running)
        events.clear()
        result=m.call(dll.exports['Iw6DirectHost'],[b'0.0.0.0:27016\0',b'MP_PRISON\0',b'war\0'],setup=setup,fakes=fakes)
        assert result[0]==3,(result[0],events)
        assert events==[('setting',b'g_gametype',b'war'),('setting',b'ui_gametype',b'war'),
                        ('asset',b'mp_prison'),('prepare',b'mp_prison'),('spawn',b'mp_prison',1,0,0,0)],events
        events.clear()
        absent={**fakes,0x14036C020:lambda mu:0}
        result=m.call(dll.exports['Iw6DirectHost'],[b'0.0.0.0:27016\0',b'mp_prison\0',b'war\0'],setup=setup,fakes=absent)
        assert result[0]==3 and ('content_rejected',) in events and not any(e[0]=='spawn' for e in events),(result[0],events)
        assert not any(n.startswith(('winhttp.dll!','xcurl.dll!')) for n in m.imports_called)
    print('PASS: direct_host executes original map normalization/preparation to SV_SpawnServer; missing-content rejection retained; native loading unverified')

if __name__=='__main__':main()
