"""Store handle refresh and concrete-address recovery, with modeled SDK boundaries."""
import struct

from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9
from harness import SCRATCH
from syms import static, va
from test_dwnet import M, FAKES, STATE_STUB, _setup, _log, _u64, _i32, _destroy
from test_dwrecv import RECV_FAKES, _receive_setup

STORE = 'iw6mp64_MSStore_ship'
RECOVER = '?sub_1405AA0B0@@YA_NPEAUnetadr_s@@@Z'
REFRESH = '?dwSanityCheckAddressHandle@@YAXHPEAVbdSocketRouter@@@Z'


def _recover_setup(local, index, present, count, seed):
    def setup(w):
        _receive_setup('equal0', 1, 0, False, True, seed)(w)
        table = static('dw/dwnet.cpp', 'addressHandles')
        w.u32(static('dw/dwnet.cpp', 'localHandleIndex'), local)
        if 0 <= index < 8:
            w.u64(table + 16*index, table+0x1000 if present else 0)
            w.u32(table+0x1008, count)
    return setup


recover_inputs = []
for local in (0, 1, 4, 8):
    for index in (-1, 0, 3, 4, 7, 8, 9, 0x7FFFFFFF):
        for kind in (0, 1, 4, 0x7FFFFFFF):
            for present, count in ((False, 1), (True, 0), (True, 1), (True, 2)):
                recover_inputs.append({
                    'args': [struct.pack('<I4sHHi', kind, b'\xA5\x5A\xEF\xCD', 0x4321, 0xBEEF, index)],
                    'setup': _recover_setup(local, index, present, count, len(recover_inputs)+10),
                })


def _count_write(p, delta):
    mu = M['m'].mu
    n = _i32(mu, p+8)
    M['m']._emulated_write(p+8, struct.pack('<I', (n+delta) & 0xFFFFFFFF))
    return n


def _refresh_state(mu):
    p = _u64(mu, mu.reg_read(UC_X86_REG_RDX))
    count = _count_write(p, -1) if p else None
    _log('refresh_state', mu.reg_read(UC_X86_REG_RCX), p, count)
    result = M['states'][min(M['state_calls'], 1)]
    M['state_calls'] += 1
    # Exercise the reread before replacing/releasing the current table handle.
    if M['mutate_entry'] and M['state_calls'] == 2:
        M['m']._emulated_write(M['entry'], struct.pack('<Q', M['third']))
    return result


def _address_map(mu):
    p = mu.reg_read(UC_X86_REG_RCX)
    _log('address_map', p)
    return p+0x40


def _security_id(mu):
    p = mu.reg_read(UC_X86_REG_RCX)
    _log('security_id', p)
    return p+8


def _common_addr(mu):
    endpoint, out = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
    p = _u64(mu, endpoint)
    _log('common_addr', endpoint, p)
    M['m']._emulated_write(out, struct.pack('<Q', p))
    if p:
        _count_write(p, 1)
    return out


def _find_handle(mu):
    amap, commonref, security, out = (mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX),
                                     mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9))
    common = _u64(mu, commonref)
    _log('find_handle', amap, common, bytes(mu.mem_read(security, 8)))
    if common:
        _count_write(common, -1)  # consumes the by-value common-address reference
    replacement = M['candidate']
    if replacement:
        _count_write(replacement, 1)  # output owns a new reference, even when it aliases the old handle
    M['m']._emulated_write(out, struct.pack('<Q', replacement))
    return M['found']


REFRESH_FAKES = {k: v for k, v in FAKES.items() if k != REFRESH}
REFRESH_FAKES.update({
    STATE_STUB: _refresh_state,
    '?getAddressMap@bdSocketRouter@@QEAAPEAVbdAddressMap@@XZ': _address_map,
    '?sub_140741840@@YAPEAXPEAX@Z': _security_id,
    '?getCommonAddr@bdEndpoint@@QEBA?AV?$bdReference@VbdCommonAddr@@@@XZ': _common_addr,
    '?findAddrHandle@bdAddressMap@@QEBA_NV?$bdReference@VbdCommonAddr@@@@AEBVbdSecurityID@@AEAV?$bdReference@VbdAddrHandle@@@@@Z': _find_handle,
})


def _refresh_setup(index=0, first=3, second=2, found=True, candidate='new',
                   present=True, router=True, supplied=False, count=1,
                   null_common=False, mutate_entry=False):
    def setup(w):
        _setup(4, index, count, present, router)(w)
        old = static('dw/dwnet.cpp', 'addressHandles')+0x1000
        new = old+0x20
        third = old+0x40
        common = old+0x100
        vtable = _u64(w.m.mu, old)
        w.write(common, struct.pack('<QiI', vtable, 1, 0))
        w.write(old+16, struct.pack('<Q8s', 0 if null_common else common, b'KEY-test'))
        w.write(third, struct.pack('<QiI', vtable, 1, 0))
        w.u32(new+8, 0)  # the find output creates its first reference
        M.update(original=old, states=(first, second), state_calls=0, found=found,
                 candidate={'new': new, 'old': old, 'null': 0}[candidate],
                 third=third, mutate_entry=mutate_entry)
        if supplied:
            # _setup's deterministic scratch allocations: the router is last,
            # after the 16-byte handle vtable and 96-byte router vtable.
            assert M['router'] == SCRATCH+112
    return setup


refresh_inputs = []
for index in (-1, 0, 3, 4, 0x7FFFFFFF):
    for first in (0, 1, 2, 3, 4, -1):
        for present, router in ((True, True), (False, True), (True, False)):
            refresh_inputs.append({'args': [index, 0],
                                   'setup': _refresh_setup(index=index, first=first,
                                                           present=present, router=router)})
for second in (0, 1, 2, 3, 4, -1):
    for found in (False, True):
        for candidate in ('new', 'old', 'null'):
            for count in (0, 1, 2):
                refresh_inputs.append({'args': [0, 0], 'setup': _refresh_setup(
                    second=second, found=found, candidate=candidate, count=count)})
for null_common in (False, True):
    for mutate in (False, True):
        refresh_inputs.append({'args': [0, SCRATCH+112], 'setup': _refresh_setup(
            supplied=True, null_common=null_common, mutate_entry=mutate)})

CASES = [
    {'symbol': RECOVER, 'build': STORE, 'ret': 'char', 'fakes': RECV_FAKES, 'inputs': recover_inputs},
    {'symbol': REFRESH, 'build': STORE, 'ret': 'void', 'fakes': REFRESH_FAKES, 'inputs': refresh_inputs},
]
