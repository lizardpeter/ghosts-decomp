"""Store receive: router result handling, inline handle registration and payload extraction.

The network-facing SDK methods are modeled. Unregister executes the real original or
reconstructed implementation, exercising both reconstructed routines together.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9
from syms import static, va
from test_dwnet import (M, FAKES, PUMP_STUB, UNREGISTER_STUB, _setup, _log, _u64,
                         _i32, _format_address, _pump, _unregister)

STORE = 'iw6mp64_MSStore_ship'
STATUS_STUB = '?sub_14054EFB0@@YAHPEBUnetadr_s@@@Z'
RECV_STUB = '?sub_14054EFA0@@YAXPEBUnetadr_s@@PEAI@Z'


def _ready(mu):
    _log('ready', mu.reg_read(UC_X86_REG_RCX))
    return M['ready']


def _recv(mu):
    out, buffer, size = mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9)
    _log('receive', mu.reg_read(UC_X86_REG_RCX), size)
    M['m']._emulated_write(out, struct.pack('<Q', M['received']))
    M['m']._emulated_write(buffer, M['payload'][:size])
    return M['recv_result']


def _equal(mu):
    left, right = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    _log('equal', left, right)
    return right == M['equal_to']


def _real_addr(mu):
    handle, out = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    _log('real_address', handle, _i32(mu, handle + 8))
    M['m']._emulated_write(out, M['real_address'])
    return out


def _identity(mu):
    p = mu.reg_read(UC_X86_REG_RCX)
    _log('inet_address', bytes(mu.mem_read(p, 136)))
    return p


def _in_addr(mu):
    src, dst = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    data = bytes(mu.mem_read(src, 132))
    _log('in_address', data)
    M['m']._emulated_write(dst, data)
    return dst


def _get_port(mu):
    p = mu.reg_read(UC_X86_REG_RCX)
    port = struct.unpack('<H', bytes(mu.mem_read(p+132, 2)))[0]
    _log('port', port)
    return port


def _destroy_address(mu):
    p = mu.reg_read(UC_X86_REG_RCX)
    _log('destroy_address', bytes(mu.mem_read(p, 136)))
    M['m']._emulated_write(p, struct.pack('<I', 0xDEADBEEF))


RECV_FAKES = {**FAKES,
    STATUS_STUB: _ready, RECV_STUB: _recv,
    '??8bdAddrHandle@@QEBA_NAEBV0@@Z': _equal,
    '?getRealAddr@bdAddrHandle@@QEBA?BVbdAddr@@XZ': _real_addr,
    '?sub_14073ED40@@YAPEAXPEAX@Z': _identity,
    '?getInAddr@bdInetAddr@@QEBA?AVbdSockAddr@@XZ': _in_addr,
    '?getPort@bdAddr@@QEBAGXZ': _get_port,
    '??1bdInetAddr@@QEAA@XZ': _destroy_address,
    '?dwAddrIndexToAddrString@@YA_NHQEAD_K@Z': _format_address,
    PUMP_STUB: _pump, UNREGISTER_STUB: _unregister,
}


def _receive_setup(pattern, ready, result, has_received, router, seed):
    r = random.Random(seed)
    payload = r.randbytes(max(2, result))
    ip = r.randbytes(4)
    real_address = ip + r.randbytes(128) + struct.pack('<HH', r.randrange(65536), 0xABCD)
    counts = [r.choice((1, 2, 50)) for _ in range(8)]
    # The first two transport bytes are intentionally arbitrary: the original
    # discards them rather than checking that they describe the received length.
    def setup(w):
        _setup(4, router=router)(w)
        table = static('dw/dwnet.cpp', 'addressHandles')
        handle_vtable = _u64(w.m.mu, table + 0x1000)
        received = table + 0x2000
        w.write(received, struct.pack('<QiI', handle_vtable, 1, 0xBEEF))
        handles = [table + 0x2100 + 0x20*i for i in range(8)]
        for h, count in zip(handles, counts):
            w.write(h, struct.pack('<QiI', handle_vtable, count, 0xFACE))
        patterns = {
            'equal0': ([1, 1, 1, 1], 0, [0, 7000, 6600, 0xFFFFFFFF]),
            'equal3': ([1, 1, 1, 1], 3, [7000, 0, 6601, 6600]),
            'empty0': ([0, 1, 1, 1], None, [9000, 100, 5000, 0]),
            'empty2': ([1, 1, 0, 0], None, [7000, 0, 0, 0]),
            'late_equal': ([0, 0, 1, 1], 3, [100, 200, 8000, 12000]),
            'full_tie': ([1, 1, 1, 1], None, [100, 100, 100, 100]),
            'full_oldest2': ([1, 1, 1, 1], None, [0xFFFFFFFF, 20000, 0, 10]),
            'zero_bound': ([0, 0, 0, 0], None, [100, 100, 100, 100]),
        }
        present, equal_index, lifetimes = patterns[pattern]
        for i in range(8):
            w.write(table + i*16, struct.pack('<QII', handles[i] if i < 4 and present[i] else 0,
                                             lifetimes[i % 4], 0x12345678))
        if pattern == 'zero_bound':
            w.u32(static('dw/dwnet.cpp', 'localHandleIndex'), 0)
        M.update(ready=ready, recv_result=result, payload=payload,
                 received=received if has_received else 0,
                 equal_to=handles[equal_index] if equal_index is not None else 0,
                 real_address=real_address)
        if M['router']:
            vtable = _u64(w.m.mu, M['router'])
            w.u64(vtable+8*8, va(STATUS_STUB))
            w.u64(vtable+11*8, va(RECV_STUB))
    return setup


inputs = []
for pattern in ('equal0', 'equal3', 'empty0', 'empty2', 'late_equal', 'full_tie', 'full_oldest2', 'zero_bound'):
    for result in (-9, -2, 0, 2, 3, 20, 1264):
        for has_received in (False, True):
            inputs.append({'args': [bytes([0xA5])*16, bytes([0xCC])*1280, 1280],
                           'setup': _receive_setup(pattern, 1, result, has_received, True, len(inputs)+120)})
for ready in (-1, 0, 1, 2, 3):
    for router in (False, True):
        inputs.append({'args': [bytes([0xA5])*16, bytes([0xCC])*1280, 1280],
                       'setup': _receive_setup('equal0', ready, -9, False, router, len(inputs)+120)})

for size, result in ((0, 0), (1, 0), (2, 2), (3, 3), (64, 64), (1024, 1024)):
    for has_received in (False, True):
        inputs.append({'args': [bytes([0x5A])*16, bytes([0xCC])*max(1, size), size],
                       'setup': _receive_setup('empty2', 1, result, has_received, True, len(inputs)+120)})

CASES = [{'symbol': '?dwRecvFrom@@YAHQEAUnetadr_s@@QEAXI@Z', 'build': STORE,
          'ret': 'int', 'fakes': RECV_FAKES, 'inputs': inputs}]
