"""Store serialized common-address conversion: initialization, ownership and registration."""
import struct

from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9
from syms import static, va
from test_dwnet import M, DESTROY_STUB, _u64, _i32, _log
from test_dwrecv import RECV_FAKES, _receive_setup
from test_dwaddress import _count_write

STORE = 'iw6mp64_MSStore_ship'
CONVERT = '?sub_1405A8300@@YA_NPEAUnetadr_s@@PEBE1@Z'
CONNECT_STUB = '?sub_14054EF80@@YA_NPEBIGPEAUnetadr_s@@@Z'


def _housekeeping(mu):
    _log('housekeeping')


def _local_common(mu):
    out = mu.reg_read(UC_X86_REG_RCX)
    p = M['local_common'] if M['local_present'] else 0
    _log('local_common', p)
    if p:
        _count_write(p, 1)
    M['m']._emulated_write(out, struct.pack('<Q', p))
    return out


def _global_map(mu):
    _log('global_map')
    return M['global_map']


def _allocate(mu):
    _log('allocate', mu.reg_read(UC_X86_REG_RCX))
    return M['decoded_common'] if M['allocated'] else 0


def _construct(mu):
    p = mu.reg_read(UC_X86_REG_RCX)
    _log('construct_common', p)
    return p if M['constructed'] else 0


def _deserialize(mu):
    address, ref, data = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX), mu.reg_read(UC_X86_REG_R8)
    local = _u64(mu, ref)
    _log('deserialize', address, local, _i32(mu, local+8), bytes(mu.mem_read(data, 37)))
    _count_write(local, -1)  # consumes the by-value local-common-address reference
    return M['deserialized']


def _loopback(mu):
    _log('is_loopback', mu.reg_read(UC_X86_REG_RCX))
    return M['loopback']


def _get_handle(mu):
    amap, ref, security, out = (mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX),
                               mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9))
    common = _u64(mu, ref)
    _log('get_handle', amap, common, bytes(mu.mem_read(security, 8)), _i32(mu, common+8) if common else None)
    if common:
        _count_write(common, -1)
    p = M['registered_handle'] if M['handle_present'] else 0
    if p:
        _count_write(p, 1)
    M['m']._emulated_write(out, struct.pack('<Q', p))
    return M['registered']


def _connect(mu):
    router, ref = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    p = _u64(mu, ref)
    _log('connect', router, p, _i32(mu, p+8) if p else None)
    if M['connect_replace']:
        if p:
            _count_write(p, -1)
        new = M['connect_replacement']
        _count_write(new, 1)
        M['m']._emulated_write(ref, struct.pack('<Q', new))


def _net_instance(mu):
    _log('net_instance')
    return M['net_instance']


def _local_address(mu):
    _log('local_address', mu.reg_read(UC_X86_REG_RCX))
    return M['local_address']


COMMON_FAKES = {**RECV_FAKES,
    '?sub_1405A8070@@YAXXZ': _housekeeping,
    '?dwGetLocalCommonAddr@@YA?AV?$bdReference@VbdCommonAddr@@@@XZ': _local_common,
    '?dwGetAddressMap@@YAPEAVbdAddressMap@@XZ': _global_map,
    '?allocate@bdMemory@@SAPEAX_K@Z': _allocate,
    '??0bdCommonAddr@@QEAA@XZ': _construct,
    '?deserialize@bdCommonAddr@@QEAA_NV?$bdReference@VbdCommonAddr@@@@QEBE@Z': _deserialize,
    '?isLoopback@bdCommonAddr@@QEBA_NXZ': _loopback,
    '?getAddrHandle@bdAddressMap@@QEAA_NV?$bdReference@VbdCommonAddr@@@@AEBVbdSecurityID@@AEAV?$bdReference@VbdAddrHandle@@@@@Z': _get_handle,
    CONNECT_STUB: _connect,
    '?getInstance@?$bdSingleton@VbdNetImpl@@@@SAPEAVbdNetImpl@@XZ': _net_instance,
    '?sub_1407679D0@@YAPEAXPEAX@Z': _local_address,
}


def common_setup(pattern='empty2', state=2, router=True, registered=True, handle=True,
                 local=True, amap=True, allocated=True, constructed=True, deserialized=True,
                 loopback=False, net=True, connect_replace=False, seed=1):
    def setup(w):
        _receive_setup(pattern, 1, 0, True, router, seed)(w)
        table = static('dw/dwnet.cpp', 'addressHandles')
        local_common, decoded_common = table+0x3000, table+0x3100
        vtable = _u64(w.m.mu, table+0x1000)
        w.write(local_common, struct.pack('<QiI', vtable, 1, 0))
        w.write(decoded_common, struct.pack('<QiI', vtable, 0, 0))
        w.u32(M['received']+8, 0)  # getAddrHandle creates its output reference
        replacement = table+0x3200
        w.write(replacement, struct.pack('<QiI', vtable, 0, 0))
        local_addr = table+0x3400
        w.write(local_addr, struct.pack('<HHI', 2, (seed*31) & 0xFFFF, 0x7F000001))
        M.update(local_common=local_common, decoded_common=decoded_common, local_present=local,
                 global_map=table+0x3500 if amap else 0, allocated=allocated, constructed=constructed,
                 deserialized=deserialized, loopback=loopback, registered=registered,
                 registered_handle=M['received'], handle_present=handle,
                 state=state, net_instance=table+0x3600 if net else 0, local_address=local_addr,
                 connect_replace=connect_replace, connect_replacement=replacement)
        if M['router']:
            w.u64(_u64(w.m.mu, M['router'])+6*8, va(CONNECT_STUB))
    return setup


SERIALIZED = bytes(range(37))
SECURITY_ID = b'key-tst!'
inputs = []
for pattern in ('equal0', 'equal3', 'empty0', 'empty2', 'late_equal', 'full_tie', 'full_oldest2', 'zero_bound'):
    for state in (0, 1, 2, 3, 4, -1):
        for router in (False, True):
            for registered in (False, True):
                for handle in (False, True):
                    inputs.append({'args': [bytes([0xA5])*16, SERIALIZED, SECURITY_ID],
                                   'setup': common_setup(pattern, state, router, registered, handle,
                                                         seed=len(inputs)+1)})
for local in (False, True):
    for amap in (False, True):
        for allocated, constructed in ((False, False), (True, False), (True, True)):
            for deserialized in (False, True):
                for loopback in (False, True):
                    for net in (False, True):
                        inputs.append({'args': [bytes([0x5A])*16, SERIALIZED, SECURITY_ID],
                                       'setup': common_setup(local=local, amap=amap, allocated=allocated,
                                           constructed=constructed, deserialized=deserialized,
                                           loopback=loopback, net=net, seed=len(inputs)+1)})
for pattern in ('empty2', 'equal0'):
    inputs.append({'args': [bytes(16), SERIALIZED, SECURITY_ID],
                   'setup': common_setup(pattern, 3, connect_replace=True, seed=len(inputs)+1)})
inputs.append({'args': [0, SERIALIZED, SECURITY_ID], 'setup': common_setup()})

CASES = [{'symbol': CONVERT, 'build': STORE, 'ret': 'char', 'fakes': COMMON_FAKES, 'inputs': inputs}]


def _map_instance(mu):
    _log('map_instance')
    return M['instance']


def _map_router(mu):
    _log('map_router', mu.reg_read(UC_X86_REG_RCX))
    return M['router']


def _member_map(mu):
    _log('member_map', mu.reg_read(UC_X86_REG_RCX))
    return M['global_map']


def _map_setup(instance, router, amap):
    def setup(w):
        M.clear()
        M.update(m=w.m, instance=instance, router=router, global_map=amap)
    return setup


CASES.append({
    'symbol': '?dwGetAddressMap@@YAPEAVbdAddressMap@@XZ', 'build': STORE, 'ret': 'int64',
    'fakes': {'?getInstance@?$bdSingleton@VbdNetImpl@@@@SAPEAVbdNetImpl@@XZ': _map_instance,
              '?getSocketRouter@bdNetImpl@@QEAAPEAVbdSocketRouter@@XZ': _map_router,
              '?getAddressMap@bdSocketRouter@@QEAAPEAVbdAddressMap@@XZ': _member_map},
    'inputs': [{'args': [], 'setup': _map_setup(instance, router, amap)}
               for instance in (0, 1, 0xFFFFFFFF, 0x100001234, 0xFFFFFFFFFFFFFFFF)
               for router in (0, 1, 0xFFFFFFFF, 0x100001234, 0xFFFFFFFFFFFFFFFF)
               for amap in (0, 1, 0xFFFFFFFF, 0x100001234, 0xFFFFFFFFFFFFFFFF)],
})
