"""Store backend-login boundary. All SDK, clock and resolver calls are modeled."""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX
from syms import static, va

STORE = 'iw6mp64_MSStore_ship'
SOURCE = 'dw/dwlogon-win.cpp'
STATUS = '?sub_14019A930@@YAHH@Z'
BUSY = '?sub_14019A960@@YA_NH@Z'
START = '?dwLogOnStart@@YAXH@Z'
RESET = '?sub_14019AE70@@YAXXZ'
CLEANUP = '?sub_14019AE90@@YAXXZ'
SELECT = '?dwSelectAuthAddress@@YAPEBDXZ'
DTOR = '?Sys_GetLocalIP@@YA?AUin_addr@@H@Z'
M = {}


def _u32(mu, p):
    return struct.unpack('<I', bytes(mu.mem_read(p, 4)))[0]


def _u64(mu, p):
    return struct.unpack('<Q', bytes(mu.mem_read(p, 8)))[0]


def _log(*args):
    M['m'].observed.append(args)


def _write(p, data):
    M['m']._emulated_write(p, data)


def _wide(mu, p):
    out = bytearray()
    for i in range(100):
        c = bytes(mu.mem_read(p+2*i, 2))
        if c == b'\0\0':
            return out.decode('utf-16le')
        out.extend(c)
    raise AssertionError('unterminated wide string')


def _wcsicmp(mu):
    a, b = (_wide(mu, mu.reg_read(r)) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX))
    _log('wcsicmp', a, b)
    seq = M['compares']
    result = seq.pop(0) if seq else (a.lower() > b.lower()) - (a.lower() < b.lower())
    mu.reg_write(UC_X86_REG_RAX, result & 0xFFFFFFFF)


def _ready(mu):
    _log('ready', mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF)
    return M['ready']


def _busy(mu):
    _log('auth_busy')
    return M['busy']


def _clock(mu):
    _log('clock')
    return M['now']


def _retry(mu):
    _log('retry', mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF,
         mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF)
    return M['retry']


def _destroy(mu):
    obj, flags = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF
    _log('destroy_resolver', obj, flags)
    # The second global must be reread after the first destructor.
    if M['mutate_resolver'] and obj == M['first']:
        _write(static(SOURCE, 'lobbyResolver'), struct.pack('<Q', M['third']))


FAKES = {
    '?sub_1401A1A10@@YA_NH@Z': _ready,
    '?sub_1405D9F10@@YA_NXZ': _busy,
    '?Sys_Milliseconds@@YAHXZ': _clock,
    '?sub_1405F3D10@@YAHIH@Z': _retry,
    DTOR: _destroy,
}


def setup(state=0, suppressed=0, attempts=0, delay=0, last=0, now=0,
          ready=True, busy=False, retry=7, resolvers=0, mutate_resolver=False,
          compares=(), seed=0):
    def apply(w):
        rng = random.Random(seed)
        base = static(SOURCE, 'logonEntries')
        w.write(base-16, rng.randbytes(400))
        w.write(base, struct.pack('<IiII', state & 0xFFFFFFFF, delay, attempts & 0xFFFFFFFF,
                                  last & 0xFFFFFFFF))
        w.write(static(SOURCE, 'logonSuppressed'), bytes([suppressed]))
        objects = base+0x300
        vt = w.alloc(struct.pack('<Q', va(DTOR)))
        for i in range(3):
            w.u64(objects+16*i, vt)
        w.u64(static(SOURCE, 'authResolver'), objects if resolvers & 1 else 0)
        w.u64(static(SOURCE, 'lobbyResolver'), objects+16 if resolvers & 2 else 0)
        M.clear()
        M.update(m=w.m, ready=ready, busy=busy, now=now, retry=retry,
                 mutate_resolver=mutate_resolver, first=objects, third=objects+32,
                 compares=list(compares))
        w.m.on_import('api-ms-win-crt-string-l1-1-0.dll!_wcsicmp', _wcsicmp)
    return apply


rng = random.Random(0x19ADA0)
states = list(range(17)) + [0xFFFFFFFF, 0x80000000, 0x7FFFFFFF]
status_inputs = [{'args': [0], 'setup': setup(state=s, suppressed=g)}
                 for s in states for g in (0, 1, 255)]
busy_inputs = [{'args': [controller], 'setup': setup(state=s)}
               for controller in (-1, 0, 1, 7) for s in states]
start_inputs = []
for attempts in (0, 1, 4, 0xFFFFFFFF):
    for delay in (0, 1, 60, -1):
        for delta in (-2147483648, -1001, -1, 0, 999, 1000, 59999, 60000,
                      120000, 120999, 121000, 2147483647):
            now = rng.getrandbits(32)
            start_inputs.append({'args': [0], 'setup': setup(
                state=13, suppressed=1, attempts=attempts, delay=delay,
                last=(now-delta) & 0xFFFFFFFF, now=now, retry=7)})
for ready, busy in ((False, False), (False, True), (True, True)):
    for state in states:
        start_inputs.append({'args': [0], 'setup': setup(state=state, suppressed=255,
                             attempts=3, delay=0, ready=ready, busy=busy)})
for retry in (-1, 0, 1, 60, 121):
    for delta in (0, 1000, 60000, 120000):
        start_inputs.append({'args': [0], 'setup': setup(attempts=2, now=delta, retry=retry)})

CASES = [
    {'symbol': STATUS, 'build': STORE, 'ret': 'int', 'inputs': status_inputs},
    {'symbol': BUSY, 'build': STORE, 'ret': 'char', 'inputs': busy_inputs},
    {'symbol': START, 'build': STORE, 'ret': 'void', 'fakes': FAKES, 'inputs': start_inputs},
    {'symbol': RESET, 'build': STORE, 'ret': 'void', 'inputs': [
        {'args': [], 'setup': setup(state=s, suppressed=255, attempts=0xFFFFFFFF, delay=-1,
                                   last=0xAABBCCDD, resolvers=3, seed=s)} for s in states]},
    {'symbol': CLEANUP, 'build': STORE, 'ret': 'void', 'fakes': FAKES, 'inputs': [
        {'args': [], 'setup': setup(resolvers=r, mutate_resolver=m, seed=r)}
        for r in range(4) for m in (False, True)]},
    {'symbol': SELECT, 'build': STORE, 'ret': 'cstr', 'inputs': [
        {'args': [], 'setup': setup(compares=c)}
        for c in ((), (0,), (1, 0), (1, 1, 0), (1, 1, 1, 0), (-1, -1, -1, -1))]},
]

# Full game-side login step: the selector and resolver cleanup run reconstructed;
# SDK DNS/auth/lobby operations are fakes and never open a network connection.
from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9

STEP = '?dwLogOnComplete@@YAXH@Z'
AUTH_GET = '?sub_1405DA070@@YAPEAXPEBDGI@Z'
AUTH_FREE = '?sub_1405D9F30@@YAXXZ'
AUTH_BUSY = '?sub_1405D9F10@@YA_NXZ'
LOOKUP = '?sub_1405DA210@@YAHPEBDPEAPEAXPEAX@Z'
ALLOC = '?allocate@bdMemory@@SAPEAX_K@Z'
FREE = '?deallocate@bdMemory@@SAXPEAX@Z'
AUTH_CTOR = '?sub_14074ABA0@@YAPEAXPEAXIPEBDG@Z'
AUTH_DTOR = '?sub_14074ACF0@@YAXPEAX@Z'
INET_CTOR = '??0bdInetAddr@@QEAA@XZ'
INET_DTOR = '??1bdInetAddr@@QEAA@XZ'
INET_SET = '?set@bdInetAddr@@QEAAXAEBV1@@Z'
ADDR_CTOR = '??0bdAddr@@QEAA@AEBVbdInetAddr@@G@Z'
ADDR_COPY = '??0bdAddr@@QEAA@AEBV0@@Z'
LOBBY = '?dwGetLobbyService@@YAPEAVbdLobbyService@@H@Z'
DISCONNECT = '?disconnect@bdLobbyService@@QEAAXXZ'
CONNECT = '?connect@bdLobbyService@@QEAA_NVbdAddr@@PEBVbdAuthInfo@@_N@Z'


def _arg(mu, reg=UC_X86_REG_RCX):
    return mu.reg_read(reg)


def _inet_construct(mu):
    p = _arg(mu)
    M['buffers'][p] = 'inet'
    _log('inet_construct')
    _write(p, bytes([0xC1])*144)
    return p


def _inet_destroy(mu):
    p = _arg(mu)
    _log('inet_destroy', M['buffers'][p], bytes(mu.mem_read(p, 144)))


def _inet_set(mu):
    p, q = _arg(mu), _arg(mu, UC_X86_REG_RDX)
    data = bytes(mu.mem_read(q, 144))
    _log('inet_set', p, data)
    _write(p, data)


def _lookup(mu):
    host, ref, out = _arg(mu), _arg(mu, UC_X86_REG_RDX), _arg(mu, UC_X86_REG_R8)
    _log('lookup', M['m'].read_cstr(host), ref, _u64(mu, ref))
    _write(out, bytes([0xD1])*144)
    return M['lookup']


def _get_auth(mu):
    _log('get_auth', M['m'].read_cstr(_arg(mu)), _arg(mu, UC_X86_REG_RDX) & 0xFFFF,
         _arg(mu, UC_X86_REG_R8) & 0xFFFFFFFF)
    return M['auth']


def _auth_status(mu):
    _log('auth_status', _arg(mu))
    return M['auth_status']


def _auth_login(mu):
    _log('auth_login', _arg(mu), _arg(mu, UC_X86_REG_RDX) & 0xFFFFFFFF)
    return M['login']


def _auth_result(mu):
    _log('auth_result', _arg(mu))
    return M['auth_result']


def _auth_info(mu):
    _log('auth_info', _arg(mu))
    return M['info']


def _auth_cleanup(mu):
    _log('auth_cleanup')


def _get_lobby(mu):
    _log('get_lobby', _arg(mu) & 0xFFFFFFFF)
    return M['lobby']


def _addr_construct(mu):
    p, address, port = _arg(mu), _arg(mu, UC_X86_REG_RDX), _arg(mu, UC_X86_REG_R8) & 0xFFFF
    M['buffers'][p] = 'endpoint'
    _log('addr_construct', address, port)
    _write(p, struct.pack('<H', port)+bytes(mu.mem_read(address, 142)))
    return p


def _addr_copy(mu):
    p, q = _arg(mu), _arg(mu, UC_X86_REG_RDX)
    M['buffers'][p] = 'copy'
    _log('addr_copy', bytes(mu.mem_read(q, 144)))
    _write(p, bytes(mu.mem_read(q, 144)))
    return p


def _disconnect(mu):
    _log('disconnect', _arg(mu))


def _connect(mu):
    _log('connect', _arg(mu), bytes(mu.mem_read(_arg(mu, UC_X86_REG_RDX), 144)),
         _arg(mu, UC_X86_REG_R8), _arg(mu, UC_X86_REG_R9) & 0xFF)
    return M['connect']


def _pump(mu):
    _log('lobby_pump', _arg(mu) & 0xFFFFFFFF)


def _lobby_status(mu):
    _log('lobby_status', _arg(mu))
    return M['lobby_status']


def _net_ready(mu):
    _log('net_ready')
    return M['net_ready']


def _notify(mu):
    _log('notify', _arg(mu) & 0xFFFFFFFF, _u32(mu, static(SOURCE, 'logonEntries')))
    if M['notify_reset']:
        _write(static(SOURCE, 'logonEntries'), struct.pack('<I', 0))


STEP_FAKES = dict(FAKES)
STEP_FAKES.update({
    INET_CTOR: _inet_construct, INET_DTOR: _inet_destroy, INET_SET: _inet_set,
    LOOKUP: _lookup, AUTH_GET: _get_auth, AUTH_FREE: _auth_cleanup,
    '?sub_14074ADA0@@YAHPEAX@Z': _auth_status,
    '?sub_140749D20@@YA_NPEAXH@Z': _auth_login,
    '?sub_14074AD90@@YAHPEAX@Z': _auth_result,
    '?sub_14074AD80@@YAPEBXPEAX@Z': _auth_info,
    LOBBY: _get_lobby, ADDR_CTOR: _addr_construct, ADDR_COPY: _addr_copy,
    DISCONNECT: _disconnect, CONNECT: _connect,
    '?dwLobbyPump@@YAXH@Z': _pump,
    '?getStatus@bdLobbyService@@QEAA?AW4Status@bdLobbyConnection@@XZ': _lobby_status,
    '?dwIsBdNetReady@@YA_NXZ': _net_ready,
    '?sub_1405F4820@@YAXH@Z': _notify,
})


def step_setup(state=0, lookup=1, auth=True, auth_status=0, auth_result=700, login=True,
               lobby=True, connect=True, lobby_status=2, net_ready=True, resolvers=3,
               compares=(), notify_reset=False):
    def apply(w):
        setup(state=state, resolvers=resolvers, compares=compares, seed=state)(w)
        base = static(SOURCE, 'logonEntries')
        M.update(buffers={}, lookup=lookup, auth=base+0x500 if auth else 0,
                 auth_status=auth_status, auth_result=auth_result, login=login,
                 lobby=base+0x600 if lobby else 0, info=base+0x700, connect=connect,
                 lobby_status=lobby_status, net_ready=net_ready, notify_reset=notify_reset)
    return apply


step_inputs = []
for state in states:
    for resolvers in range(4):
        step_inputs.append({'args': [0], 'setup': step_setup(state=state, resolvers=resolvers)})
for result in (-1, 0, 1, 2, 3):
    for resolvers in range(4):
        step_inputs.append({'args': [0], 'setup': step_setup(state=3, lookup=result, resolvers=resolvers)})
for state in (9, 10):
    for auth in (False, True):
        for status in (0, 1, -1):
            for result in (0, 700, 701, -1):
                for login in (False, True):
                    step_inputs.append({'args': [0], 'setup': step_setup(
                        state=state, auth=auth, auth_status=status, auth_result=result, login=login)})
for status in (0, 1, -1):
    for result in (0, 700, 701):
        for lookup in (-1, 0, 1, 2, 3):
            for lobby, connect in ((False, False), (True, False), (True, True)):
                step_inputs.append({'args': [0], 'setup': step_setup(
                    state=11, auth_status=status, auth_result=result, lookup=lookup,
                    lobby=lobby, connect=connect)})
for status in (-1, 0, 1, 2, 3):
    for lobby in (False, True):
        for ready in (False, True):
            for reset in (False, True):
                step_inputs.append({'args': [0], 'setup': step_setup(
                    state=13, lobby=lobby, lobby_status=status, net_ready=ready, notify_reset=reset)})
# Separate environment comparisons for auth and lobby selectors.
for comparisons in ((0, 1, 0), (0, 1, 1, 0), (0, 1, 1, 1, 0)):
    step_inputs.append({'args': [0], 'setup': step_setup(state=11, compares=comparisons)})
CASES.append({'symbol': STEP, 'build': STORE, 'ret': 'void', 'fakes': STEP_FAKES, 'inputs': step_inputs})


# Auth-object ownership, tested independently of the login state machine.
UTILS = 'dw/dwutils.cpp'


def _allocate(mu):
    _log('allocate', _arg(mu))
    return M['allocation']


def _construct_auth(mu):
    _log('construct_auth', _arg(mu), _arg(mu, UC_X86_REG_RDX) & 0xFFFFFFFF,
         M['m'].read_cstr(_arg(mu, UC_X86_REG_R8)), _arg(mu, UC_X86_REG_R9) & 0xFFFF)
    return M['constructed']


def _destruct_auth(mu):
    _log('destruct_auth', _arg(mu))
    if M['mutate_cache']:
        _write(static(UTILS, 'authClient'), struct.pack('<Q', M['constructed']))


def _free(mu):
    _log('free', _arg(mu))


def auth_setup(cached=False, allocation=True, constructed=True, mutate_cache=False, flags=(0, 0)):
    def apply(w):
        setup()(w)
        base = static(SOURCE, 'logonEntries')
        w.u64(static(UTILS, 'authClient'), base+0x500 if cached else 0)
        w.write(static(UTILS, 'authBusy'), bytes(flags))
        M.update(allocation=base+0x600 if allocation else 0,
                 constructed=base+0x700 if constructed else 0, mutate_cache=mutate_cache)
    return apply


AUTH_FAKES = {ALLOC: _allocate, AUTH_CTOR: _construct_auth, AUTH_DTOR: _destruct_auth, FREE: _free}
auth_inputs = []
for cached in (False, True):
    for allocated in (False, True):
        for constructed in (False, True):
            for port in (0, 443, 3074, 65535):
                for title in (0, 2510, 0xFFFFFFFF):
                    auth_inputs.append({'args': [b'auth.invalid\0', port, title], 'setup': auth_setup(
                        cached=cached, allocation=allocated, constructed=constructed)})
CASES.extend([
    {'symbol': AUTH_GET, 'build': STORE, 'ret': 'int64', 'fakes': AUTH_FAKES, 'inputs': auth_inputs},
    {'symbol': AUTH_FREE, 'build': STORE, 'ret': 'void', 'fakes': AUTH_FAKES, 'inputs': [
        {'args': [], 'setup': auth_setup(cached=c, mutate_cache=m)}
        for c in (False, True) for m in (False, True)]},
    {'symbol': AUTH_BUSY, 'build': STORE, 'ret': 'char', 'inputs': [
        {'args': [], 'setup': auth_setup(flags=(a, b))}
        for a in (0, 1, 2, 255) for b in (0, 1, 2, 255)]},
])

# Run login with the reconstructed auth cache/lifetime helpers as well.
INTEGRATED_FAKES = {k: v for k, v in STEP_FAKES.items() if k not in (AUTH_GET, AUTH_FREE)}
INTEGRATED_FAKES.update(AUTH_FAKES)


def integrated_setup(state, cached, allocated, constructed, lookup):
    def apply(w):
        step_setup(state=state, lookup=lookup)(w)
        base = static(SOURCE, 'logonEntries')
        w.u64(static(UTILS, 'authClient'), M['auth'] if cached else 0)
        M.update(allocation=base+0x800 if allocated else 0,
                 constructed=M['auth'] if constructed else 0, mutate_cache=True)
    return apply


for state in (0, 3, 9, 10, 11, 13):
    for cached in (False, True):
        for allocated, constructed in ((False, False), (True, False), (True, True)):
            for lookup in (0, 1, 2):
                step_inputs.append({'args': [0], 'setup': integrated_setup(
                    state, cached, allocated, constructed, lookup), 'fakes': INTEGRATED_FAKES})
# Per-input overrides cannot remove a case-level fake: use full maps for both groups.
for inp in step_inputs[:-108]:
    inp['fakes'] = STEP_FAKES
for case in CASES:
    if case['symbol'] == STEP:
        case['fakes'] = {}

FRAME = '?DW_Frame@@YAXH@Z'
INHIBIT = '?sub_1405D3DC0@@YAXE@Z'
FRAME_SOURCE = 'dw/dwframe.cpp'


def _frame_gate(mu):
    _log('frame_gate')
    return M['frame_gate']


def _frame_status(mu):
    _log('frame_status', _arg(mu) & 0xFFFFFFFF)
    return M['frame_status']


def _frame_start(mu):
    _log('frame_start', _arg(mu) & 0xFFFFFFFF)


def _frame_step(mu):
    _log('frame_step', _arg(mu) & 0xFFFFFFFF)


def _frame_connected(mu):
    _log('frame_connected', _arg(mu) & 0xFFFFFFFF)


FRAME_FAKES = {'?sub_1405F47D0@@YAHXZ': _frame_gate, STATUS: _frame_status,
               START: _frame_start, STEP: _frame_step, '?dwLobbyPump@@YAXH@Z': _pump,
               '?sub_1405F4630@@YAXH@Z': _frame_connected}


def frame_setup(gate, status, inhibit):
    def apply(w):
        setup()(w)
        w.write(static(FRAME_SOURCE, 'inhibitLogon'), bytes([inhibit]))
        M.update(frame_gate=gate, frame_status=status)
    return apply


CASES.extend([
    {'symbol': FRAME, 'build': STORE, 'ret': 'void', 'fakes': FRAME_FAKES, 'inputs': [
        {'args': [controller], 'setup': frame_setup(gate, status, inhibit)}
        for controller in (-1, 0, 1, 7) for gate in (0, 1, -1)
        for status in (0, 1, 2, 3, 256, -1) for inhibit in (0, 1, 255)]},
    {'symbol': INHIBIT, 'build': STORE, 'ret': 'void', 'inputs': [
        {'args': [value], 'setup': frame_setup(0, 0, old)}
        for old in (0, 1, 255) for value in (0, 1, 2, 255, 256, 0xFFFFFFFF)]},
])

# Frame -> status/start/step -> auth-cache helpers, with only SDK boundaries faked.
FRAME_INTEGRATED_FAKES = dict(INTEGRATED_FAKES)
FRAME_INTEGRATED_FAKES.update({'?sub_1405F47D0@@YAHXZ': _frame_gate,
                               '?sub_1405F4630@@YAXH@Z': _frame_connected})


def integrated_frame_setup(state, inhibit, cached):
    def apply(w):
        integrated_setup(state, cached, True, True, 1)(w)
        w.write(static(FRAME_SOURCE, 'inhibitLogon'), bytes([inhibit]))
        M.update(frame_gate=0)
    return apply


for case in CASES:
    if case['symbol'] == FRAME:
        for inp in case['inputs']:
            inp['fakes'] = FRAME_FAKES
        case['fakes'] = {}
        case['inputs'].extend([
            {'args': [0], 'setup': integrated_frame_setup(state, inhibit, cached),
             'fakes': FRAME_INTEGRATED_FAKES}
            for state in (0, 1, 2, 3, 8, 9, 10, 11, 13, 14)
            for inhibit in (0, 1) for cached in (False, True)])
