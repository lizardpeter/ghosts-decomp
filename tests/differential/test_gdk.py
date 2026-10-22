"""Store GDK glue: modeled DLL exports/COM interfaces, no real DLL or service."""
import struct
from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP
from syms import static, va

STORE = 'iw6mp64_MSStore_ship'
SRC = '_external/gdk/xgameruntime.cpp'
GAME = 'win32/gdk.cpp'
ENSURE = '?sub_1406AEC18@@YAH_K@Z'
LOAD = '?sub_1406AEE34@@YAHXZ'
QUERY = '?sub_1406AEE74@@YAHPEBX0PEAPEAX@Z'
GAME_INIT = '?sub_1401A1930@@YA_NXZ'
QSTUB = '?Sys_GetLocalIP@@YA?AUin_addr@@H@Z'
ISTUB = '?sub_14054F950@@YAHXZ'
ESTUB = '?sub_14054F8D0@@YAHXZ'
RSTUB = '?sub_14054F8E0@@YA_NPEBUXNADDR@@PEBUnetadr_s@@@Z'
USTUB = '?sub_14054F2E0@@YA_NPEBI@Z'
EXPORTS = ('QueryApiImpl','InitializeApiImpl','InitializeApiImplEx','XErrorReport','UninitializeApiImpl')
STUBS = (QSTUB, ISTUB, ESTUB, RSTUB, USTUB)
M = {}


def arg(mu, i=0):
    if i < 4:
        return mu.reg_read((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)[i])
    return u64(mu, mu.reg_read(UC_X86_REG_RSP)+40+8*(i-4))


def u64(mu, p):
    return struct.unpack('<Q', bytes(mu.mem_read(p, 8)))[0]


def log(*items):
    M['m'].observed.append(items)


def write(p, data):
    M['m']._emulated_write(p, data)


def cstr(p):
    return M['m'].read_cstr(p)


def wide(mu, p):
    data = bytearray()
    for i in range(200):
        b = bytes(mu.mem_read(p+2*i, 2))
        if b == b'\0\0':
            return data.decode('utf-16le')
        data.extend(b)
    raise AssertionError('unterminated UTF16')


def imp(fn):
    def hook(mu):
        value = fn(mu)
        if value is not None:
            mu.reg_write(UC_X86_REG_RAX, value & 0xFFFFFFFFFFFFFFFF)
    return hook


def acquire(mu):
    log('lock', arg(mu))


def release(mu):
    log('unlock', arg(mu))


def load(mu):
    log('load', cstr(arg(mu)), arg(mu, 1), arg(mu, 2))
    return M['load_module']


def proc(mu):
    name = cstr(arg(mu, 1)).decode()
    log('proc', arg(mu), name)
    return M['available'][EXPORTS.index(name)]


def free(mu):
    log('free', arg(mu))
    return 0  # ignored by the original, including failure


def debugger(mu):
    log('debugbreak')


def query_impl(mu):
    log('query', bytes(mu.mem_read(arg(mu), 16)), bytes(mu.mem_read(arg(mu, 1), 16)))
    if M['write_api'] and arg(mu, 2):
        write(arg(mu, 2), struct.pack('<Q', M['api']))
    return M['query_result']


def init_impl(mu):
    log('initialize', arg(mu) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF)
    return M['init_result']


def init_ex_impl(mu):
    log('initialize_ex', arg(mu), arg(mu, 1), arg(mu, 2))
    return M['init_result']


def report(mu):
    log('report', arg(mu) & 0xFFFFFFFF, cstr(arg(mu, 1)))


def uninit_impl(mu):
    base = static(SRC, 'runtime')
    log('uninitialize', bytes(mu.mem_read(base+8, 2)), u64(mu, base+16))
    if M['mutate_uninit']:
        write(base+16, struct.pack('<Q', M['load_module']+0x100))


def ensure_fake(mu):
    log('ensure', arg(mu))
    return M['ensure_result']


RUNTIME_FAKES = {QSTUB: query_impl, ISTUB: init_impl, ESTUB: init_ex_impl,
                 RSTUB: report, USTUB: uninit_impl}


def setup(module=True, initialized=0, implicit=0, cached=31, available=31,
          load_ok=True, init_result=0, query_result=0, ensure_result=0,
          write_api=True, debug=0, mutate_uninit=False):
    def apply(w):
        base = static(SRC, 'runtime')
        module_ptr = base+0x1000
        pointers = [va(s) for s in STUBS]
        w.write(base, struct.pack('<QBB6sQ5Q', 0, initialized, implicit, b'PADDED',
                                  module_ptr if module else 0,
                                  *[p if cached & (1<<i) else 0 for i,p in enumerate(pointers)]))
        if not getattr(w.m, '_gdk_kuser_mapped', False):
            w.m.mu.mem_map(0x7FFE0000, 0x10000)
            w.m._gdk_kuser_mapped = True
        w.write(0x7FFE02D4, bytes([debug]))
        M.clear()
        M.update(m=w.m, load_module=module_ptr if load_ok else 0,
                 available=[p if available & (1<<i) else 0 for i,p in enumerate(pointers)],
                 init_result=init_result, query_result=query_result, ensure_result=ensure_result,
                 write_api=write_api, api=base+0x2000, mutate_uninit=mutate_uninit)
        for name, fn in (('AcquireSRWLockExclusive',acquire),('ReleaseSRWLockExclusive',release),
                         ('LoadLibraryExA',load),('GetProcAddress',proc),('FreeLibrary',free),('DebugBreak',debugger)):
            w.m.on_import('KERNEL32.dll!'+name, imp(fn))
    return apply


ensure_inputs = []
for flags in (0, 1, 2, 3, 0xFFFFFFFF, 0x8000000000000001):
    for initialized, implicit in ((0,0),(1,0),(1,1),(255,255)):
        for cached in (0, 3, 27, 31):
            for available in (0, 1, 23, 27, 29, 30, 31):
                ensure_inputs.append({'args':[flags], 'setup':setup(
                    initialized=initialized,implicit=implicit,cached=cached,available=available)})
for module, load_ok in ((False,False),(False,True),(True,False)):
    for result in (0, 1, 0x80004005, 0x89240100):
        for debug in (0, 1, 2, 3, 255):
            ensure_inputs.append({'args':[0], 'setup':setup(module=module,load_ok=load_ok,
                                 cached=0,init_result=result,debug=debug)})

query_inputs = []
for initialized in (0,1):
    for ensure_result in (0,1,0x80004005):
        for query_result in (0,1,0x80004005,0x80040154,0x89240107):
            for cached in (23,31):
                for output in (False,True):
                    query_inputs.append({'args':[bytes(range(16)),bytes(range(16,32)),b'API-OLD!'],
                      'setup':setup(initialized=initialized,ensure_result=ensure_result,
                                    query_result=query_result,cached=cached,write_api=output)})

CASES = [
 {'symbol':LOAD,'build':STORE,'ret':'int','inputs':[
     {'args':[],'setup':setup(module=module,load_ok=ok)} for module in (False,True) for ok in (False,True)]},
 {'symbol':ENSURE,'build':STORE,'ret':'int','fakes':RUNTIME_FAKES,'inputs':ensure_inputs},
 {'symbol':QUERY,'build':STORE,'ret':'int','fakes':{**RUNTIME_FAKES,ENSURE:ensure_fake},'inputs':query_inputs},
 {'symbol':'XGameRuntimeInitialize','build':STORE,'ret':'int','fakes':{ENSURE:ensure_fake},'inputs':[
     {'args':[],'setup':setup(ensure_result=r)} for r in (0,1,0x80004005,0x89240100,0xFFFFFFFF)]},
 {'symbol':'XGameRuntimeUninitialize','build':STORE,'ret':'void','fakes':RUNTIME_FAKES,'inputs':[
     {'args':[],'setup':setup(module=module,initialized=i,implicit=p,cached=c,mutate_uninit=m)}
     for module in (False,True) for i in (0,1,255) for p in (0,1,255)
     for c in (0,15,31) for m in (False,True)]},
]

# Real thunk forwarding through modeled COM objects, including nine-argument tokens.
RELEASE_STUB = '?NET_InAddrToString@@YAXPEBUin_addr@@QEAD@Z'
TITLE_STUB = '?sub_14054EFB0@@YAHPEBUnetadr_s@@@Z'
FEATURE_STUB = '?sub_14054EFA0@@YAXPEBUnetadr_s@@PEAI@Z'
THREAD_STUB = '?sub_14054EF80@@YA_NPEBIGPEAUnetadr_s@@@Z'
ADD_STUB = '?NET_InAddrSetLoopback@@YAXPEAUin_addr@@@Z'
TOKEN_STUB = '?NET_InAddrToIpAddr@@YAXPEBUin_addr@@QEAE@Z'


def ref(p, delta):
    old = struct.unpack('<I',bytes(M['m'].mu.mem_read(p+8,4)))[0]
    write(p+8,struct.pack('<I',(old+delta)&0xFFFFFFFF))
    return old


def query_fake(mu):
    family, version, out = arg(mu),arg(mu,1),arg(mu,2)
    f = bytes(mu.mem_read(family,16))
    v = bytes(mu.mem_read(version,16))
    log('query_api', f, v)
    index = M['query_calls']
    M['query_calls'] += 1
    result = M['query_sequence'][min(index,len(M['query_sequence'])-1)]
    if result & 0x80000000 == 0:
        p = M['interfaces'][f]
        write(out,struct.pack('<Q',p))
        ref(p,1)
    return result


def release_api(mu):
    p = arg(mu)
    log('release_api',p,ref(p,-1))


def thread_method(mu):
    log('thread_guard',arg(mu))


def title_method(mu):
    log('title',arg(mu))
    write(arg(mu,1),struct.pack('<I',M['title']))
    return M['method_result']


def feature_method(mu):
    log('feature',arg(mu),arg(mu,1)&0xFFFFFFFF)
    return M['feature']


def add_method(mu):
    log('user_add',arg(mu),arg(mu,1)&0xFFFFFFFF,arg(mu,2))
    return M['method_result']


def token_method(mu):
    log('token',arg(mu),arg(mu,1),arg(mu,2)&0xFFFFFFFF,cstr(arg(mu,3)),
        cstr(arg(mu,4)),arg(mu,5),arg(mu,6),arg(mu,7),arg(mu,8),arg(mu,9))
    return M['method_result']


THUNK_FAKES = {QUERY:query_fake,RELEASE_STUB:release_api,TITLE_STUB:title_method,
               FEATURE_STUB:feature_method,THREAD_STUB:thread_method,
               ADD_STUB:add_method,TOKEN_STUB:token_method}


def thunk_setup(sequence=(0,), method_result=0, title=2510, feature=True):
    def apply(w):
        setup()(w)
        pointers = {}
        for i,(name,slot,stub) in enumerate((('coreIID',29,THREAD_STUB),('gameFamily',3,TITLE_STUB),
                         ('featureIID',3,FEATURE_STUB),('userFamily',7,ADD_STUB))):
            table = [0]*30
            table[2] = va(RELEASE_STUB)
            table[slot] = va(stub)
            if name == 'userFamily':
                table[23] = va(TOKEN_STUB)
            vtable = w.alloc(struct.pack('<30Q',*table))
            p = static(SRC,'runtime')+0x2000+0x40*i
            w.write(p,struct.pack('<QI',vtable,2))
            guid = bytes(w.m.mu.mem_read(static(SRC,name),16))
            pointers[guid] = p
        M.update(interfaces=pointers,query_calls=0,query_sequence=sequence,
                 method_result=method_result,title=title,feature=feature)
    return apply


thunk_inputs = []
for q in (0,1,0x80004005,0x89240100):
    for r in (0,1,0x80004005,0xFFFFFFFF):
        for option in (0,1,4,0xFFFFFFFF):
            thunk_inputs.append({'args':[option,0x123456789ABCDEF0],
                                 'setup':thunk_setup(sequence=(q,),method_result=r)})
title_inputs = []
for sequence in ((0,0),(0,0x80004005),(0x80004005,0),(0x80004005,0x80004005),(1,1)):
    for result in (0,1,0x80004005):
        for title in (0,2510,0xFFFFFFFF):
            title_inputs.append({'args':[b'TOLD'], 'setup':thunk_setup(
                sequence=sequence,method_result=result,title=title)})
feature_inputs = [{'args':[feature], 'setup':thunk_setup(sequence=(q,),feature=available)}
                  for feature in (0,10,20,0xFFFFFFFF) for q in (0,1,0x80004005)
                  for available in (False,True)]
token_inputs = []
for q in (0,1,0x80004005,0x89240100):
    for r in (0,1,0x80004005):
        for n in (0,1,0xFFFFFFFF,0x123456789ABCDEF0):
            token_inputs.append({'args':[0x123456789ABCDEF0,0xFFFFFFFF,b'POST\0',
                b'https://example.invalid/token\0',n,0xCAFEBABE,n^0x55,0xDEADBEEF,0xFEDCBA9876543210],
                'setup':thunk_setup(sequence=(q,),method_result=r)})
CASES.extend([
 {'symbol':'XThreadAssertNotTimeSensitive','build':STORE,'ret':'void','fakes':THUNK_FAKES,
  'inputs':[{'args':[],'setup':thunk_setup(sequence=(q,))} for q in (0,1,0x80004005,0x89240100)]},
 {'symbol':'XGameGetXboxTitleId','build':STORE,'ret':'int','fakes':THUNK_FAKES,'inputs':title_inputs},
 {'symbol':'XGameRuntimeIsFeatureAvailable','build':STORE,'ret':'char','fakes':THUNK_FAKES,'inputs':feature_inputs},
 {'symbol':'XUserAddAsync','build':STORE,'ret':'int','fakes':THUNK_FAKES,'inputs':thunk_inputs},
 {'symbol':'XUserGetTokenAndSignatureAsync','build':STORE,'ret':'int','fakes':THUNK_FAKES,'inputs':token_inputs},
])

# Game startup: failure handling, title serialization and initializer ordering.
GAME_CALLBACKS = ('?sub_1401A12D0@@YAXXZ','?sub_1401A85F0@@YAXXZ','?sub_14019F3A0@@YAXI@Z',
                  '?sub_1401A5770@@YAXXZ','?sub_1401A1C70@@YAXXZ','?sub_1401A2510@@YAXXZ')
TASKS = '?TaskManager_ConstructTaskSet@@YAXPEAUOverlappedTaskSet@@PEBD@Z'
CONFIG = '?sub_1406D6240@@YAXPEAX@Z'


def runtime_fake(mu):
    log('runtime_start')
    return M['runtime_result']


def title_fake(mu):
    log('get_title')
    write(arg(mu),struct.pack('<I',M['title']))
    return M['title_result']


def message(mu):
    log('message',arg(mu),wide(mu,arg(mu,1)),wide(mu,arg(mu,2)),arg(mu,3)&0xFFFFFFFF)
    return 1


def itoa(mu):
    value = arg(mu)&0xFFFFFFFF
    if value & 0x80000000:
        value -= 0x100000000
    p = arg(mu,1)
    log('itoa',value,p,arg(mu,2)&0xFFFFFFFF)
    write(p,str(value).encode()+b'\0')
    return p


def config(mu):
    log('config',arg(mu),u64(mu,static(GAME,'scidPointer')))


def tasks(mu):
    log('tasks',arg(mu),cstr(arg(mu,1)))


def callback(name):
    def run(mu):
        log(name, arg(mu)&0xFFFFFFFF) if '19F3A0' in name else log(name)
    return run


STARTUP_FAKES = {'XGameRuntimeInitialize':runtime_fake,'XGameGetXboxTitleId':title_fake,
                  CONFIG:config,TASKS:tasks,**{name:callback(name) for name in GAME_CALLBACKS}}


def startup_setup(runtime_result=0,title_result=0,title=2510):
    def apply(w):
        setup()(w)
        w.write(static(GAME,'titleString'),b'\xA5'*16)
        w.u64(static(GAME,'scidPointer'),0x12345678)
        M.update(runtime_result=runtime_result,title_result=title_result,title=title)
        w.m.on_import('USER32.dll!MessageBoxW',imp(message))
        w.m.on_import('api-ms-win-crt-convert-l1-1-0.dll!_itoa',imp(itoa))
    return apply


CASES.append({'symbol':GAME_INIT,'build':STORE,'ret':'char','fakes':STARTUP_FAKES,'inputs':[
 {'args':[],'setup':startup_setup(runtime_result=runtime,title_result=result,title=title)}
 for runtime in (0,1,0xFFFFFFFF,0x80004005,0x89240100,0x89240101,0x89240102)
 for result in (0,1,0x80004005) for title in (0,2510,0xFFFFFFFF)]})

# End-to-end reconstructed startup/runtime/query/thunks; only OS and SDK providers are modeled.
INTEGRATED_FAKES = dict(RUNTIME_FAKES)
INTEGRATED_FAKES.update({k:v for k,v in THUNK_FAKES.items() if k != QUERY})
INTEGRATED_FAKES.update({k:v for k,v in STARTUP_FAKES.items()
                          if k not in ('XGameRuntimeInitialize','XGameGetXboxTitleId')})
INTEGRATED_FAKES[QSTUB] = query_fake


def integrated_setup(profile):
    def apply(w):
        thunk_setup()(w)
        module,cached,available,load_ok,init_result,query_result,initialized,implicit = profile
        base = static(SRC,'runtime')
        pointers = [va(s) for s in STUBS]
        module_ptr = base+0x1000
        w.write(base,struct.pack('<QBB6sQ5Q',0,initialized,implicit,b'PADDED',
                module_ptr if module else 0,*[p if cached & (1<<i) else 0 for i,p in enumerate(pointers)]))
        w.write(static(GAME,'titleString'),b'\xA5'*16)
        w.u64(static(GAME,'scidPointer'),0x12345678)
        M.update(load_module=module_ptr if load_ok else 0,
                 available=[p if available & (1<<i) else 0 for i,p in enumerate(pointers)],
                 init_result=init_result,query_sequence=(query_result,))
        w.m.on_import('USER32.dll!MessageBoxW',imp(message))
        w.m.on_import('api-ms-win-crt-convert-l1-1-0.dll!_itoa',imp(itoa))
    return apply


profiles = ((False,0,31,False,0,0,0,0), (False,0,31,True,0,0,0,0),
            (True,0,27,True,0,0,0,0), (True,31,31,True,0x80004005,0,0,0),
            (True,31,31,True,0,0x80040154,0,0), (True,31,31,True,1,0,0,0),
            (True,31,31,True,0,0,1,0))
integrated_args = {
 'XGameRuntimeInitialize':[], QUERY:[0x1408B1D40,0x1408B1D40,b'API-OLD!'],
 'XThreadAssertNotTimeSensitive':[], 'XGameGetXboxTitleId':[b'TOLD'],
 'XGameRuntimeIsFeatureAvailable':[10], 'XUserAddAsync':[4,0x123456789ABCDEF0],
 'XUserGetTokenAndSignatureAsync':[0x123456789ABCDEF0,1,b'POST\0',b'https://example.invalid/token\0',
                                 2,0xCAFEBABE,3,0xDEADBEEF,0xFEDCBA9876543210], GAME_INIT:[]}
for case in CASES:
    if case['symbol'] in integrated_args:
        baseline = case.get('fakes',{})
        for inp in case['inputs']:
            inp['fakes'] = baseline
        case['fakes'] = {}
        case['inputs'].extend([{'args':integrated_args[case['symbol']],
                               'setup':integrated_setup(profile),'fakes':INTEGRATED_FAKES}
                              for profile in profiles])
