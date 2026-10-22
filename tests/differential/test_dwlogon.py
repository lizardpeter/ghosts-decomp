"""Store backend-login boundary. All SDK, clock and resolver calls are modeled."""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX
from syms import static, va

STORE = 'iw6mp64_MSStore_ship'
SOURCE = 'dw/dwlogon-win.cpp'
STATUS = '?sub_14019A930@@YAEH@Z'
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
    {'symbol': STATUS, 'build': STORE, 'ret': 'char', 'inputs': status_inputs},
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
