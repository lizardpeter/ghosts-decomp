"""Store dwnet boundary: modeled router, no network or vendor service is contacted.

The router consumes the by-value bdReference arguments. Observe the lock nesting,
refresh requests, intrusive counts, packet contents and router results independently
for the original and reconstruction. Unknown SDK types remain opaque in source.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9

from syms import static

STORE = 'iw6mp64_MSStore_ship'
SEND = '?dwSendTo@@YAHIPEBXUnetadr_s@@@Z'
GETTER = '?sub_1405A8AD0@@YAIXZ'
TOUCH = '?sub_1405A9E50@@YAXPEBUnetadr_s@@@Z'
# Mapped game-function addresses are used as fake virtual slots, never executed.
STATE_STUB = '?sub_14054F8D0@@YAHXZ'
SEND_STUB = '?sub_14054F950@@YAHXZ'
DESTROY_STUB = '?sub_1405AA0B0@@YA_NPEAUnetadr_s@@@Z'
PUMP_STUB = '?sub_14054F8E0@@YA_NPEBUXNADDR@@PEBUnetadr_s@@@Z'
UNREGISTER_STUB = '?sub_14054F2E0@@YA_NPEBI@Z'
M = {}


def _u64(mu, p):
    return struct.unpack('<Q', bytes(mu.mem_read(p, 8)))[0]


def _i32(mu, p):
    return struct.unpack('<i', bytes(mu.mem_read(p, 4)))[0]


def _log(*items):
    M['m'].observed.append(items)


def _lock(mu):
    _log('enter', mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF)


def _unlock(mu):
    _log('leave', mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF)


def _router(mu):
    _log('router')
    return M['router']


def _refresh(mu):
    _log('refresh', mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_RDX))
    if M['replace']:
        M['m']._emulated_write(M['entry'], struct.pack('<Q', M['replacement']))


def _consume(mu, operation):
    router, reference = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    handle = _u64(mu, reference)
    count = _i32(mu, handle + 8)
    _log(operation, router, handle, count)
    M['m']._emulated_write(handle + 8, struct.pack('<I', (count - 1) & 0xFFFFFFFF))
    return handle


def _state(mu):
    _consume(mu, 'state')
    return M['state']


def _send(mu):
    _consume(mu, 'send')
    data, n = mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9) & 0xFFFFFFFF
    _log('packet', n, bytes(mu.mem_read(data, n)))
    return M['result']


def _destroy(mu):
    handle, flags = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF
    _log('destroy', handle, flags, _i32(mu, handle + 8))


FAKES = {
    '?Sys_EnterCriticalSection@@YAXW4CriticalSection@@@Z': _lock,
    '?Sys_LeaveCriticalSection@@YAXW4CriticalSection@@@Z': _unlock,
    '?dwGetSocketRouter@@YAPEAVbdSocketRouter@@XZ': _router,
    '?dwSanityCheckAddressHandle@@YAXHPEAVbdSocketRouter@@@Z': _refresh,
    STATE_STUB: _state,
    SEND_STUB: _send,
    DESTROY_STUB: _destroy,
}


def _setup(local, index=0, count=1, present=True, router=True, state=2, result=123,
           replace=False, lifetimes=None):
    def setup(w):
        from syms import va
        M.clear()
        M.update(m=w.m, state=state, result=result, replace=replace)
        handle_vtable = w.alloc(struct.pack('<Q', va(DESTROY_STUB)))
        # Image-backed fake objects make final reference-count writes part of the
        # harness's compared global state, including paths with no destructor.
        handle = static('dw/dwnet.cpp', 'addressHandles') + 0x1000
        replacement = handle + 0x20
        w.write(handle, struct.pack('<QiI', handle_vtable, count, 0))
        w.write(replacement, struct.pack('<QiI', handle_vtable, count, 0))
        vtable = [0] * 12
        vtable[4] = va(PUMP_STUB)
        vtable[7] = va(UNREGISTER_STUB)
        vtable[9], vtable[10] = va(STATE_STUB), va(SEND_STUB)
        router_vtable = w.alloc(struct.pack('<12Q', *vtable))
        M['router'] = w.alloc(struct.pack('<Q', router_vtable)) if router else 0
        M['entry'] = static('dw/dwnet.cpp', 'addressHandles') + index * 16
        M['replacement'] = replacement
        w.u32(static('dw/dwnet.cpp', 'localHandleIndex'), local)
        for i in range(8):
            value = (lifetimes or [11, 22, 33, 44, 55, 66, 77, 88])[i]
            w.write(static('dw/dwnet.cpp', 'addressHandles') + 16*i,
                    struct.pack('<QII', handle if present else 0, value, 0xAABBCCDD))
    return setup


def _send_inputs():
    out = []
    r = random.Random(0xD06)
    # Explicit Cartesian boundaries: lengths include the exact 1262-byte admission limit.
    for index in (-1, 0, 3, 4, 0x7FFFFFFF):
        for state in (0, 1, 2, 3, 4, -1):
            for length in (0, 1, 2, 1261, 1262, 1263, 0xFFFFFFFF):
                data = r.randbytes(min(length, 1263)) or b'\0'
                adr = struct.pack('<I4sHHi', 4, b'\x0A\x00\x00\x01', 27016, 0, index)
                out.append({'args': [length, data, adr], 'setup': _setup(4, index, state=state)})
    for count in (0, 1, 2, 100):
        for present, router, replace in ((True, False, False), (False, True, False),
                                         (True, True, False), (True, True, True)):
            for result in (-10, -7, -6, -2, 0, 1, 1264):
                out.append({'args': [3, b'abc', struct.pack('<4I', 4, 0, 0, 2)],
                            'setup': _setup(4, 2, count, present, router, 2, result, replace)})
    return out


_r = random.Random(0x8AD0)
CASES = [
    {'symbol': SEND, 'build': STORE, 'ret': 'int', 'fakes': FAKES, 'inputs': _send_inputs()},
    {'symbol': GETTER, 'build': STORE, 'ret': 'int',
     'inputs': [{'args': [], 'setup': _setup(v)} for v in
                [0, 1, 4, -1, 0x7FFFFFFF, -0x80000000] + [_r.getrandbits(32) for _ in range(40)]]},
    {'symbol': TOUCH, 'build': STORE, 'ret': 'void', 'fakes': FAKES,
     'inputs': [{'args': [struct.pack('<4I', 4, 0, 0, index)],
                 'setup': _setup(local, index, lifetimes=[_r.getrandbits(32) for _ in range(8)])}
                for local in (0, 1, 3, 7) for index in range(8)]},
]


# Exercise dwGetSocketRouter independently: neither fake initializes the SDK.
def _instance(mu):
    _log('instance')
    return M['instance']


def _get_router(mu):
    _log('getSocketRouter', mu.reg_read(UC_X86_REG_RCX))
    return M['router']


def _accessor_setup(instance, router):
    def setup(w):
        M.clear()
        M.update(m=w.m, instance=instance, router=router)
    return setup


CASES.append({
    'symbol': '?dwGetSocketRouter@@YAPEAVbdSocketRouter@@XZ', 'build': STORE, 'ret': 'int64',
    'fakes': {'?getInstance@?$bdSingleton@VbdNetImpl@@@@SAPEAVbdNetImpl@@XZ': _instance,
              '?getSocketRouter@bdNetImpl@@QEAAPEAVbdSocketRouter@@XZ': _get_router},
    'inputs': [{'args': [], 'setup': _accessor_setup(instance, router)}
               for instance in (0, 1, 0x12345678, 0x123456789ABCDEF0, 0xFFFFFFFFFFFFFFFF)
               for router in (0, 1, 0x100001234, 0x123456789ABCDEF0, 0xFFFFFFFFFFFFFFFF)],
})


# Connection status observes all router states and verifies the local fast path.
CASES.append({
    'symbol': '?sub_1405A8980@@YAHPEBUnetadr_s@@@Z', 'build': STORE, 'ret': 'int', 'fakes': FAKES,
    'inputs': [{'args': [struct.pack('<I4sHHi', 4, b'\x7F\0\0\1', 27016, 0, index)],
                'setup': _setup(4, index, count, present, router, state, replace=replace)}
               for index in (-1, 0, 3, 4, 5, 0x7FFFFFFF)
               for state in (0, 1, 2, 3, 4, -1)
               for count, present, router, replace in
               ((0, True, True, False), (1, True, True, False), (2, True, True, True),
                (1, False, True, False), (1, True, False, False))],
})


def _format_address(mu):
    _log('format', mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_R8))
    return 0


def _unregister(mu):
    entry = mu.reg_read(UC_X86_REG_RDX)
    _log('unregister', mu.reg_read(UC_X86_REG_RCX), entry, _u64(mu, entry))
    # The original reads the table again after the router has run.
    if M['replace']:
        M['m']._emulated_write(entry, struct.pack('<Q', M['replacement']))


def _pump(mu):
    _log('pump', mu.reg_read(UC_X86_REG_RCX))


CASES.append({
    'symbol': '?dwUnregisterAddrHandle@@YAXI@Z', 'build': STORE, 'ret': 'void',
    'fakes': {**FAKES, '?dwAddrIndexToAddrString@@YA_NHQEAD_K@Z': _format_address,
              UNREGISTER_STUB: _unregister, PUMP_STUB: _pump},
    'inputs': [{'args': [index], 'setup': _setup(4, index, count, present, router, replace=replace)}
               for index in range(8) for count in (0, 1, 2, 100)
               for present, router, replace in ((False, False, False), (False, True, False),
                                                (True, False, False), (True, True, False),
                                                (True, True, True))],
})
