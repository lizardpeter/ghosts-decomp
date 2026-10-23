#!/usr/bin/env python3
"""Observe a bounded Windows startup with the native debug API; never patch memory.

Requires an enabled outbound-block firewall rule for this exact executable.
Records loader modules, debug strings, exceptions and the actual process exit.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def firewall(exe, rule):
    env = dict(os.environ, IW6_SMOKE_RULE=rule)
    script = '''$ErrorActionPreference='Stop'
$r = Get-NetFirewallRule -Name $env:IW6_SMOKE_RULE -PolicyStore ActiveStore
$a = $r | Get-NetFirewallApplicationFilter
[pscustomobject]@{enabled=[string]$r.Enabled; action=[string]$r.Action;
 direction=[string]$r.Direction; profile=[string]$r.Profile; program=$a.Program} | ConvertTo-Json -Compress
'''
    r = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', script], env=env, text=True))
    if any(r.get(k) != v for k, v in [('enabled','True'), ('action','Block'), ('direction','Outbound'), ('profile','Any')]):
        raise ValueError('Active outbound-block rule is required')
    if os.path.normcase(os.path.abspath(os.path.expandvars(r['program']))) != os.path.normcase(str(exe)):
        raise ValueError('Firewall rule does not cover this executable')
    return r


def observe(exe, cwd, arguments, seconds):
    if C.sizeof(C.c_void_p) != 8:
        raise RuntimeError('Use 64-bit Python')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    PTR = C.c_void_p
    SIZE = C.c_size_t
    class Startup(C.Structure):
        _fields_ = [('cb',W.DWORD), ('reserved',W.LPWSTR), ('desktop',W.LPWSTR), ('title',W.LPWSTR),
                    ('x',W.DWORD), ('y',W.DWORD), ('xs',W.DWORD), ('ys',W.DWORD),
                    ('xc',W.DWORD), ('yc',W.DWORD), ('fill',W.DWORD), ('flags',W.DWORD),
                    ('show',W.WORD), ('reserved2size',W.WORD), ('reserved2',PTR),
                    ('stdin',W.HANDLE), ('stdout',W.HANDLE), ('stderr',W.HANDLE)]
    class Process(C.Structure):
        _fields_ = [('process',W.HANDLE), ('thread',W.HANDLE), ('pid',W.DWORD), ('tid',W.DWORD)]
    class ExceptionRecord(C.Structure):
        _fields_ = [('code',W.DWORD), ('flags',W.DWORD), ('record',PTR), ('address',PTR),
                    ('count',W.DWORD), ('information',SIZE*15)]
    class ExceptionInfo(C.Structure):
        _fields_ = [('record',ExceptionRecord), ('first',W.DWORD)]
    class CreateInfo(C.Structure):
        _fields_ = [('file',W.HANDLE), ('process',W.HANDLE), ('thread',W.HANDLE), ('base',PTR),
                    ('debug_offset',W.DWORD), ('debug_size',W.DWORD), ('tls',PTR),
                    ('entry',PTR), ('image_name',PTR), ('unicode',W.WORD)]
    class DllInfo(C.Structure):
        _fields_ = [('file',W.HANDLE), ('base',PTR), ('debug_offset',W.DWORD),
                    ('debug_size',W.DWORD), ('image_name',PTR), ('unicode',W.WORD)]
    class DebugString(C.Structure):
        _fields_ = [('text',PTR), ('unicode',W.WORD), ('length',W.WORD)]
    class Info(C.Union):
        _fields_ = [('exception',ExceptionInfo), ('create',CreateInfo), ('dll',DllInfo),
                    ('string',DebugString), ('exit_code',W.DWORD), ('raw',C.c_byte*160)]
    class Event(C.Structure):
        _fields_ = [('code',W.DWORD), ('pid',W.DWORD), ('tid',W.DWORD), ('info',Info)]
    assert C.sizeof(Startup)==104 and C.sizeof(Event)==176 and Event.info.offset==16
    kernel.CreateProcessW.argtypes = [W.LPCWSTR,W.LPWSTR,PTR,PTR,W.BOOL,W.DWORD,PTR,W.LPCWSTR,C.POINTER(Startup),C.POINTER(Process)]
    kernel.CreateProcessW.restype = W.BOOL
    kernel.WaitForDebugEvent.argtypes = [C.POINTER(Event),W.DWORD]
    kernel.WaitForDebugEvent.restype = W.BOOL
    kernel.ContinueDebugEvent.argtypes = [W.DWORD,W.DWORD,W.DWORD]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.TerminateProcess.argtypes = [W.HANDLE,W.UINT]
    kernel.ReadProcessMemory.argtypes = [W.HANDLE,PTR,PTR,SIZE,C.POINTER(SIZE)]
    kernel.GetFinalPathNameByHandleW.argtypes = [W.HANDLE,W.LPWSTR,W.DWORD,W.DWORD]
    startup, process = Startup(), Process()
    startup.cb = C.sizeof(startup)
    command = C.create_unicode_buffer(subprocess.list2cmdline([str(exe),*arguments]))
    if not kernel.CreateProcessW(str(exe),command,None,None,False,2,None,str(cwd),C.byref(startup),C.byref(process)):
        raise C.WinError(C.get_last_error())
    result = {'pid':process.pid, 'events':[], 'timed_out':False, 'exit_code':None,
              'game_join_verified':False, 'whole_process_egress_verified':False}
    deadline = time.monotonic()+seconds
    terminated = False
    try:
        while True:
            if time.monotonic() >= deadline:
                if terminated:
                    break
                result['timed_out'] = True
                kernel.TerminateProcess(process.process,0xE0010002)
                terminated = True
                deadline = time.monotonic()+5
            event = Event()
            if not kernel.WaitForDebugEvent(C.byref(event),100):
                error = C.get_last_error()
                if error == 121:  # ERROR_SEM_TIMEOUT
                    continue
                raise C.WinError(error)
            status = 0x10002  # DBG_CONTINUE
            item = {'event':event.code}
            if event.code in (3,6):
                data = event.info.create if event.code==3 else event.info.dll
                item['base'] = hex(data.base or 0)
                if event.code==3:
                    item['entry'] = hex(data.entry or 0)
                if data.file:
                    name = C.create_unicode_buffer(32768)
                    if kernel.GetFinalPathNameByHandleW(data.file,name,len(name),0):
                        item['path'] = name.value
                    kernel.CloseHandle(data.file)
            elif event.code==1:
                data = event.info.exception
                item.update(code=hex(data.record.code),address=hex(data.record.address or 0),first_chance=bool(data.first))
                if data.record.code != 0x80000003:
                    status = 0x80010001  # let the application's own handlers run
            elif event.code==8:
                data = event.info.string
                n = min(data.length*(2 if data.unicode else 1),16384)
                buffer = C.create_string_buffer(n)
                read = SIZE()
                if n and kernel.ReadProcessMemory(process.process,data.text,buffer,n,C.byref(read)):
                    item['text'] = buffer.raw[:read.value].decode('utf-16-le' if data.unicode else 'utf-8',errors='replace').rstrip('\0')
            elif event.code==5:
                result['exit_code'] = hex(event.info.exit_code)
            if event.code in (1,3,5,6,8):
                result['events'].append(item)
            if not kernel.ContinueDebugEvent(event.pid,event.tid,status):
                raise C.WinError(C.get_last_error())
            if event.code==5:
                break
    finally:
        if result['exit_code'] is None:
            kernel.TerminateProcess(process.process,0xE0010002)
        kernel.CloseHandle(process.thread)
        kernel.CloseHandle(process.process)
    return result


def audit_imports(exe, requirements):
    """Map providers without DllMain and check required exports; do not call them."""
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.LoadLibraryExW.argtypes=[W.LPCWSTR,W.HANDLE,W.DWORD]
    kernel.LoadLibraryExW.restype=W.HANDLE
    kernel.GetProcAddress.argtypes=[W.HANDLE,C.c_void_p]
    kernel.GetProcAddress.restype=C.c_void_p
    kernel.FreeLibrary.argtypes=[W.HANDLE]
    result=[]
    for provider in json.loads(requirements.read_text()):
        local=exe.parent/provider['dll']
        name=str(local) if local.exists() else provider['dll']
        module=kernel.LoadLibraryExW(name,None,1)  # DONT_RESOLVE_DLL_REFERENCES
        item={'dll':provider['dll'],'mapped':bool(module)}
        if not module:
            item['error']=C.get_last_error()
        else:
            try:
                missing=[]
                for symbol in provider['symbols']:
                    value=C.c_char_p(symbol.encode()) if isinstance(symbol,str) else C.c_void_p(symbol)
                    if not kernel.GetProcAddress(module,C.cast(value,C.c_void_p)):
                        missing.append(symbol)
                item['missing_exports']=missing
            finally:
                kernel.FreeLibrary(module)
        result.append(item)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--cwd',type=Path,required=True)
    parser.add_argument('--firewall-rule',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=30)
    parser.add_argument('--imports',type=Path)
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if sys.platform!='win32' or not 1<=args.seconds<=300:
        parser.error('64-bit Windows and seconds 1..300 are required')
    exe=args.exe.resolve(strict=True)
    rule=firewall(exe,args.firewall_rule)
    arguments=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    result=observe(exe,args.cwd.resolve(strict=True),arguments,args.seconds)
    result['firewall']=rule
    if args.imports:
        result['import_audit']=audit_imports(exe,args.imports)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
