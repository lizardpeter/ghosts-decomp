#!/usr/bin/env python3
"""Packaged original EXE -> registered connect command -> original resend -> private UDP.

Windows loader/socket APIs are modeled. Native game startup remains unverified.
"""
import struct
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/offline'),str(ROOT/'tests/differential')]
import package
from harness import Image,Machine,original_exe,SCRATCH
from winsock import Winsock,sockaddr_in
from unicorn.x86_const import UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9


def main():
    dll_path=ROOT/'build'/package.BUILD/'direct/recon.dll'
    original=original_exe(package.BUILD)
    with tempfile.TemporaryDirectory() as temp:
        directory=Path(temp)/'direct'
        manifest=package.package(original,dll_path,directory,mode='direct')
        assert manifest['mode']=='direct' and not manifest['game_join_verified']
        assert len(manifest['guards'])==31+len(package.VENDOR_TASKS)+len(package.DIRECT) and len(manifest['imports'])==58
        assert (directory/'LaunchDirect.ps1').exists() and not (directory/'ConfigureSandbox.ps1').exists()
        exe,dll=Image(directory/'iw6mp64_offline.exe'),Image(directory/'recon.dll')
        m=Machine(exe,dll)
        for slot,name in exe.iat.items():
            if name.startswith('recon.dll!'):
                m.mu.mem_write(slot,struct.pack('<Q',dll.exports[name.split('!',1)[1]]))
        # Product's private imports are direct OS imports; original egress stays denied.
        assert 'ws2_32.dll!socket' in dll.iat.values()
        for name in ('socket','sendto','WSASocketA','connect','gethostbyname','getaddrinfo'):
            assert 'ws2_32.dll!'+name not in exe.iat.values()
        network=Winsock()
        network.install(m)
        def ret(mu,value):mu.reg_write(UC_X86_REG_RAX,value&0xFFFFFFFFFFFFFFFF)
        def getsockname(mu):
            m._emulated_write(mu.reg_read(UC_X86_REG_RDX),sockaddr_in(b'\0'*4,30001))
            m._emulated_write(mu.reg_read(UC_X86_REG_R8),struct.pack('<i',16))
            ret(mu,0)
        m.on_import('ws2_32.dll!getsockname',getsockname)
        m.on_import('ws2_32.dll!WSACleanup',lambda mu:ret(mu,0))
        def local_network(mu):
            assert mu.reg_read(UC_X86_REG_RDX)==0
            m._emulated_write(mu.reg_read(UC_X86_REG_RCX)+0x10,b'\0')
        settings=[]
        def set_string(mu):
            settings.append((m.read_cstr(mu.reg_read(UC_X86_REG_RCX)),m.read_cstr(mu.reg_read(UC_X86_REG_RDX))))
        commands={}
        def register(mu):
            name=m.read_cstr(mu.reg_read(UC_X86_REG_RCX)).decode()
            assert name not in commands
            commands[name]=mu.reg_read(UC_X86_REG_RDX)
        def call(va,args,ret_type='int',setup=None,fakes=None):
            result=m.call(va,args,ret=ret_type,setup=setup,fakes={0x14053E7E0:local_network,0x14053F550:set_string,**(fakes or {})})
            assert not (isinstance(result[0],str) and result[0].startswith('fault')),result[0]
            # Model process lifetime: the differential harness normally rolls image
            # writes back, while this integration sequence intentionally keeps them.
            for address,value in result[2].items():m.mu.mem_write(address,value)
            return result
        call(0x14054F200,[],ret_type='void',fakes={0x1404448D0:register})
        call(0x14054F200,[],ret_type='void',fakes={0x1404448D0:register})
        assert set(commands)=={'connect','direct_listen','direct_stop','direct_player','direct_host'}
        assert not any(n.startswith('ws2_32.dll!') for n in m.imports_called)
        endpoint=b'127.0.0.1:27016\0'
        # No inactive-client fabrication or mutation on rejected input.
        assert call(dll.exports['Iw6DirectBeginJoin'],[endpoint])[0]==-2
        m.mu.mem_write(0x142E67170,struct.pack('<I',1)) # original local/guest naming branch
        m.mu.mem_write(0x143E96821,b'\1')
        m.mu.mem_write(0x143E96890,struct.pack('<i',0))
        m.mu.mem_write(0x146B456A0,struct.pack('<i',12345))
        assert call(dll.exports['Iw6DirectBeginJoin'],[endpoint])[0]==-5
        online_dvar=0x143E90000
        m.mu.mem_write(online_dvar,bytes(0x60))
        m.mu.mem_write(online_dvar+0x10,b'\1')
        m.mu.mem_write(0x1442B98C8,struct.pack('<Q',online_dvar))
        assert call(dll.exports['Iw6DirectBeginJoin'],[endpoint])[0]==-9
        def player_arguments(w):
            argv=w.alloc(struct.pack('<QQQ',w.cstr(b'direct_player'),w.cstr(b'123456789abcdef0'),w.cstr(b'Local Player')))
            w.u32(0x1469CECF0,0);w.u32(0x1469CED34,3);w.u64(0x1469CED58,argv)
        call(commands['direct_player'],[],ret_type='void',setup=player_arguments)
        assert call(dll.exports['Iw6DirectPlayerId'],[0],ret_type='int64')[0]==0x123456789ABCDEF0
        assert call(0x14054C0F0,[0],ret_type='cstr')[0]==b'123456789abcdef0'
        assert call(0x1401A7DB0,[0],ret_type='cstr')[0]==b'Local Player'
        assert settings==[(b'name',b'Local Player')]
        def arguments(w):
            argv=w.alloc(struct.pack('<QQ',w.cstr(b'connect'),w.cstr(endpoint[:-1])))
            w.u32(0x1469CECF0,0)
            w.u32(0x1469CED34,2)
            w.u64(0x1469CED58,argv)
        call(commands['connect'],[],ret_type='void',setup=arguments)
        assert bytes(m.mu.mem_read(online_dvar+0x10,1))==b'\0'
        assert struct.unpack('<i',m.mu.mem_read(0x143E96890,4))[0]==3
        assert bytes(m.mu.mem_read(0x14416A10C,16))==struct.pack('<I4sH2xI',4,b'\x7f\0\0\1',socket_port(27016),0xFFFFFFFF)
        assert call(dll.exports['Iw6DirectResult'],[])[0]==1
        assert call(dll.exports['Iw6DirectBeginJoin'],[endpoint])[0]==-3
        # Run the actual unmodified original challenge retry routine. Only local
        # formatting and its scratch allocator are modeled, not identity/SDK work.
        def format_player(mu):
            fmt=m.read_cstr(mu.reg_read(UC_X86_REG_R8))
            assert fmt==b'Player%i',fmt
            text=b'Player'+str(mu.reg_read(UC_X86_REG_R9)).encode()+b'\0'
            m._emulated_write(mu.reg_read(UC_X86_REG_RCX),text);ret(mu,len(text)-1)
        def format_challenge(mu):
            assert m.read_cstr(mu.reg_read(UC_X86_REG_RCX))==b'getchallenge 0 "%s"'
            text=b'getchallenge 0 "'+m.read_cstr(mu.reg_read(UC_X86_REG_RDX))+b'"\0'
            m._emulated_write(SCRATCH+0x5000,text);ret(mu,SCRATCH+0x5000)
        def allocate(mu):
            m._emulated_write(mu.reg_read(UC_X86_REG_RCX),struct.pack('<Q',SCRATCH+0x8000))
        def get_memory(mu):ret(mu,struct.unpack('<Q',m.mu.mem_read(mu.reg_read(UC_X86_REG_RCX),8))[0])
        fakes={0x140545600:format_player,0x140546CC0:format_challenge,
               0x140534A60:allocate,0x140534C60:get_memory,0x140534B60:lambda mu:None}
        result=call(0x140311310,[0],ret_type='void',fakes={0x14053E7E0:local_network,0x14053F550:set_string,**(fakes or {})})
        sent=[entry for entry in result[3] if entry[:2]==('import','sendto')]
        assert len(sent)==1,result[3]
        assert sent[0][3][:6]==b'IW6D\x01\0' and sent[0][3][8:-2].startswith(b'\xff'*4+b'getchallenge 0 "Player1"\0'),sent
        assert sent[0][-2]==sockaddr_in(b'\x7f\0\0\1',27016),sent
        assert not any(n.startswith(('winhttp.dll!','xcurl.dll!')) for n in m.imports_called)
        # With the original normal naming branch, the same unmodified resend
        # code reads our local ID through the engine getter, not an SDK account.
        def format_id(mu):
            value=struct.unpack('<Q',m.mu.mem_read(mu.reg_read(UC_X86_REG_RCX),8))[0]
            assert value==0x123456789ABCDEF0,value
            m._emulated_write(mu.reg_read(UC_X86_REG_RDX),f'{value:016x}'.encode()+b'\0')
        def retry(w):
            w.u32(0x142E67170,0)
            w.u32(0x14416A11C,-99999)
        result=call(0x140311310,[0],ret_type='void',setup=retry,fakes={**fakes,0x14046AE00:format_id})
        sent=[entry for entry in result[3] if entry[:2]==('import','sendto')]
        assert len(sent)==1 and sent[0][3][:6]==b'IW6D\x01\0' and sent[0][3][8:-2].startswith(b'\xff'*4+b'getchallenge 0 "123456789abcdef0"\0'),sent
        # The patched original receive ABI returns a checksum-validated packet
        # through msg_t without falling back to Demonware.
        from transport import packet
        network.recvfrom.append((packet(b'reply'),sockaddr_in(b'\x7f\0\0\1',27016)))
        data_address=SCRATCH+0xA0000
        message_address=SCRATCH+0xA1000
        from_address=SCRATCH+0xA2000
        def receive_setup(w):
            message=struct.pack('<iiQQiiiiiiii',0,0,data_address,0,1280,0,0,99,0,0,0,0)
            w.m.mu.mem_write(message_address,message)
        assert call(0x14054F960,[from_address,message_address],setup=receive_setup)[0]==1
        assert bytes(m.mu.mem_read(data_address,5))==b'reply'
        assert struct.unpack('<i',m.mu.mem_read(message_address+0x1C,4))[0]==5
        # Address identity is endpoint identity even when all DW sentinels match.
        a=struct.pack('<I4sH2xI',4,b'\x7f\0\0\1',socket_port(27016),0xFFFFFFFF)
        b=struct.pack('<I4sH2xI',4,b'\x7f\0\0\2',socket_port(27016),0xFFFFFFFF)
        c=struct.pack('<I4sH2xI',4,b'\x7f\0\0\1',socket_port(27017),0xFFFFFFFF)
        for va in (0x140469E70,0x140469EC0,0x140469F20):
            assert call(va,[a,a])[0]==1
            assert call(va,[a,b])[0]==0
            assert call(va,[a,c])[0]==0
        for va in (0x1405A9E50,0x1405A87E0):
            assert not call(va,[1],ret_type='void')[2]
        # A host command reaches the reviewed original Store map-start ABI;
        # the emulator stops at that engine boundary, so this is not map loading.
        call(commands['direct_stop'],[],ret_type='void')
        m.mu.mem_write(0x143E96890,struct.pack('<i',0))
        map_calls=[]
        def start_map(mu):
            map_calls.append((mu.reg_read(UC_X86_REG_RCX),m.read_cstr(mu.reg_read(UC_X86_REG_RDX)),
                              mu.reg_read(UC_X86_REG_R8)&255,mu.reg_read(UC_X86_REG_R9)&255))
        assert call(dll.exports['Iw6DirectHost'],[b'0.0.0.0:27016\0',b'mp_test;quit\0',b'war\0'])[0]==-6
        assert not map_calls
        settings.clear()
        result=call(dll.exports['Iw6DirectHost'],[b'0.0.0.0:27016\0',b'mp_prison\0',b'war\0'],fakes={0x1404BADC0:start_map})
        assert result[0]==3 and map_calls==[(0,b'mp_prison',1,0)]
        assert settings==[(b'g_gametype',b'war'),(b'ui_gametype',b'war')]
        # The original account query remains unavailable, never synthetic success.
        assert call(0x1406AF4BC,[])[0]==-0x76DBFF00
        call(commands['direct_stop'],[],ret_type='void')
        assert call(dll.exports['Iw6DirectPort'],[])[0]==0
        for mode in ('offline','wrong'):
            try:package.transform(original.read_bytes(),dll_path.read_bytes(),mode)
            except ValueError:pass
            else:raise AssertionError('profile mismatch accepted')
    print('PASS: original NET_Init registers connect; real command starts original challenge resend through private UDP; vendor imports remain blocked')


def socket_port(port):return struct.unpack('<H',struct.pack('>H',port))[0]
if __name__=='__main__':main()
