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
import re
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


def observe(exe, cwd, arguments, seconds, pending_zones=False, screenshot=None, loader_flags=False):
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
    kernel.OpenThread.argtypes = [W.DWORD,W.BOOL,W.DWORD]
    kernel.OpenThread.restype = W.HANDLE
    kernel.GetThreadContext.argtypes = [W.HANDLE,PTR]
    def registers(tid):
        thread=kernel.OpenThread(8,False,tid)
        if not thread:
            return {}
        try:
            buffer=C.create_string_buffer(1248)
            address=(C.addressof(buffer)+15)&~15
            C.c_uint32.from_address(address+48).value=0x100003
            if not kernel.GetThreadContext(thread,address):
                return {}
            values={name:hex(C.c_uint64.from_address(address+offset).value) for name,offset in
                    [('rax',120),('rcx',128),('rdx',136),('rbx',144),('rsp',152),('rbp',160),
                     ('rsi',168),('rdi',176),('r8',184),('r9',192),('rip',248)]}
            stack=C.create_string_buffer(512)
            read=SIZE()
            if kernel.ReadProcessMemory(process.process,int(values['rsp'],16),stack,len(stack),C.byref(read)):
                values['stack_qwords']=[hex(int.from_bytes(stack.raw[i:i+8],'little')) for i in range(0,read.value,8)]
            return values
        finally:
            kernel.CloseHandle(thread)
    def windows():
        user=C.WinDLL('user32',use_last_error=True)
        callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        user.EnumWindows.argtypes=[callback,W.LPARAM]
        user.EnumChildWindows.argtypes=[W.HWND,callback,W.LPARAM]
        user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        user.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
        titles=[]
        def text(hwnd,_):
            value=C.create_unicode_buffer(4096)
            user.GetWindowTextW(hwnd,value,len(value))
            if value.value:
                titles.append(value.value)
            return True
        def top(hwnd,_):
            pid=W.DWORD()
            user.GetWindowThreadProcessId(hwnd,C.byref(pid))
            if pid.value==process.pid:
                text(hwnd,0)
                user.EnumChildWindows(hwnd,callback(text),0)
            return True
        user.EnumWindows(callback(top),0)
        return titles
    def thread_snapshot():
        class ThreadEntry(C.Structure):
            _fields_=[('size',W.DWORD),('usage',W.DWORD),('tid',W.DWORD),('pid',W.DWORD),
                      ('base_priority',W.LONG),('delta_priority',W.LONG),('flags',W.DWORD)]
        kernel.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD]
        kernel.CreateToolhelp32Snapshot.restype=W.HANDLE
        kernel.Thread32First.argtypes=[W.HANDLE,C.POINTER(ThreadEntry)]
        kernel.Thread32Next.argtypes=[W.HANDLE,C.POINTER(ThreadEntry)]
        kernel.SuspendThread.argtypes=[W.HANDLE]
        kernel.SuspendThread.restype=W.DWORD
        kernel.ResumeThread.argtypes=[W.HANDLE]
        handle=kernel.CreateToolhelp32Snapshot(4,0)
        if handle==C.c_void_p(-1).value:
            return []
        threads=[]
        try:
            entry=ThreadEntry();entry.size=C.sizeof(entry)
            more=kernel.Thread32First(handle,C.byref(entry))
            while more:
                if entry.pid==process.pid:
                    # Include THREAD_QUERY_INFORMATION to attribute the CPU
                    # load to the sampled stack, instead of only seeing total
                    # user CPU time. Fall back to the original rights if denied.
                    thread=kernel.OpenThread(0x4A,False,entry.tid)
                    queried=bool(thread)
                    if not thread:
                        thread=kernel.OpenThread(0xA,False,entry.tid)
                    if thread:
                        suspended=False
                        try:
                            suspended=kernel.SuspendThread(thread)!=0xFFFFFFFF
                            if suspended:
                                snapshot={'tid':entry.tid,'registers':registers(entry.tid)}
                                if queried:
                                    times=[W.FILETIME() for _ in range(4)]
                                    kernel.GetThreadTimes.argtypes=[W.HANDLE,*([C.POINTER(W.FILETIME)]*4)]
                                    if kernel.GetThreadTimes(thread,*(C.byref(t) for t in times)):
                                        snapshot['cpu_seconds']={
                                            name:round(((value.dwHighDateTime<<32)|value.dwLowDateTime)/1e7,3)
                                            for name,value in zip(('kernel','user'),times[2:])}
                                threads.append(snapshot)
                        finally:
                            if suspended: kernel.ResumeThread(thread)
                            kernel.CloseHandle(thread)
                more=kernel.Thread32Next(handle,C.byref(entry))
        finally:
            kernel.CloseHandle(handle)
        return threads
    def startup_flags():
        # Read-only, pinned original Store image addresses. A flag sample is
        # a snapshot, not a claim that the worker thread has run or completed.
        addresses = {
            'asset_handshake': 0x145CAEDF8,
            'asset_request': 0x145CAEDFC,
            'thread_queue_a': 0x149BED150,
            'thread_queue_b': 0x149BED154,
        }
        values = {}
        for name, address in addresses.items():
            value = W.DWORD()
            read = SIZE()
            if (kernel.ReadProcessMemory(process.process,address,C.byref(value),4,C.byref(read))
                    and read.value == 4):
                values[name] = value.value
        return values

    startup, process = Startup(), Process()
    startup.cb = C.sizeof(startup)
    command = C.create_unicode_buffer(subprocess.list2cmdline([str(exe),*arguments]))
    if not kernel.CreateProcessW(str(exe),command,None,None,False,2,None,str(cwd),C.byref(startup),C.byref(process)):
        raise C.WinError(C.get_last_error())
    result = {'pid':process.pid, 'events':[], 'timed_out':False, 'exit_code':None,
              'game_join_verified':False, 'whole_process_egress_verified':False}
    start_time = time.monotonic()
    deadline = start_time+seconds
    next_loader_sample = start_time+5
    if loader_flags:
        result['loader_state'] = []
    terminated = False
    try:
        while True:
            now = time.monotonic()
            if loader_flags and not terminated and now >= next_loader_sample:
                sample = startup_flags()
                if sample:
                    result['loader_state'].append({'elapsed_seconds':round(now-start_time,2),
                                                   'values':sample})
                next_loader_sample = now+5
            if now >= deadline:
                if terminated:
                    break
                result['timed_out'] = True
                result['window_text'] = windows()
                if loader_flags:
                    result['loader_state'].append({'elapsed_seconds':round(now-start_time,2),
                                                   'values':startup_flags(), 'timeout_sample':True})
                result['threads']=thread_snapshot()
                times=[W.FILETIME() for _ in range(4)]
                kernel.GetProcessTimes.argtypes=[W.HANDLE,*([C.POINTER(W.FILETIME)]*4)]
                if kernel.GetProcessTimes(process.process,*(C.byref(t) for t in times)):
                    result['cpu_seconds']={name:round(((value.dwHighDateTime<<32)|value.dwLowDateTime)/1e7,3)
                                           for name,value in zip(('kernel','user'),times[2:])}
                if screenshot:
                    env=dict(os.environ,IW6_SMOKE_SCREENSHOT=str(screenshot.resolve()))
                    capture='''$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing,System.Windows.Forms
$screen=[System.Windows.Forms.SystemInformation]::VirtualScreen
$image=New-Object System.Drawing.Bitmap($screen.Width,$screen.Height)
$graphics=[System.Drawing.Graphics]::FromImage($image)
try {
  $graphics.CopyFromScreen($screen.Left,$screen.Top,0,0,$image.Size)
  $image.Save($env:IW6_SMOKE_SCREENSHOT,[System.Drawing.Imaging.ImageFormat]::Png)
} finally { $graphics.Dispose(); $image.Dispose() }
'''
                    try:
                        subprocess.run(['powershell','-NoProfile','-Command',capture],env=env,
                                       capture_output=True,check=True,timeout=10)
                        result['screenshot']=screenshot.name
                    except (subprocess.SubprocessError,OSError) as error:
                        result['screenshot_error']=str(error)
                if pending_zones:
                    # Store DB thread iterates 0x48-byte requests at 145F05860
                    # (140370280). A queue snapshot is not a failed-file trace.
                    queue=C.create_string_buffer(40*0x48)
                    read=SIZE()
                    names=[]
                    if kernel.ReadProcessMemory(process.process,0x145F05860,queue,len(queue),C.byref(read)):
                        for offset in range(0,read.value,0x48):
                            name=queue.raw[offset:offset+0x40].split(b'\0',1)[0]
                            if re.fullmatch(rb'[A-Za-z0-9_./-]{1,63}',name):
                                names.append(name.decode('ascii'))
                    result['pending_zone_names']=names
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
                if data.record.code not in (0x80000003,0x40010006,0x4001000A):
                    item['registers']=registers(event.tid)
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
    parser.add_argument('--pending-zones',action='store_true',help='read the pinned Store DB request queue at timeout')
    parser.add_argument('--loader-flags',action='store_true',help='sample pinned Store asset/thread handshake flags read-only')
    parser.add_argument('--screenshot',type=Path,help='capture the disposable Windows test desktop at timeout')
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if sys.platform!='win32' or not 1<=args.seconds<=300:
        parser.error('64-bit Windows and seconds 1..300 are required')
    exe=args.exe.resolve(strict=True)
    rule=firewall(exe,args.firewall_rule)
    arguments=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    result=observe(exe,args.cwd.resolve(strict=True),arguments,args.seconds,args.pending_zones,args.screenshot,args.loader_flags)
    result['firewall']=rule
    if args.imports:
        result['import_audit']=audit_imports(exe,args.imports)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
