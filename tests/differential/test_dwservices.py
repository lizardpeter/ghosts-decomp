"""Store service lifecycle and pump; SDK calls are modeled, never live network."""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX
from syms import static
from test_dwlogon import (M, STORE, SOURCE as LOGON, UTILS, _arg, _u32, _u64,
                         _log, _write, setup as logon_setup, ALLOC, LOBBY)

ACTIVE = '?dwGetActiveLobbyService@@YAPEAVbdLobbyService@@XZ'
PUMP = '?dwLobbyPump@@YAXH@Z'
READY = '?dwIsBdNetReady@@YA_NXZ'
CONTENT = '?dwGetContentStreaming@@YAPEAVbdContentStreaming@@H@Z'
COUNTER = '?dwGetCounter@@YAPEAVbdCounter@@H@Z'
DML = '?dwGetDML@@YAPEAVbdDML@@H@Z'
GROUP = '?dwGetGroup@@YAPEAVbdGroup@@H@Z'
RESET_STATE = '?sub_1405DBFD0@@YAXH@Z'
CLEAR = '?sub_1405DBFF0@@YAXXZ'
REQUEST = '?sub_1405DC010@@YAXXZ'
REASON = '?sub_1405DC020@@YAXI@Z'
CTOR = '??0bdLobbyService@@QEAA@XZ'
REGISTER = '?registerEventHandler@bdLobbyService@@QEAAXPEAVbdLobbyEventHandler@@@Z'
SDK_PUMP = '?pump@bdLobbyService@@QEAAXXZ'
STATUS = '?getStatus@bdLobbyService@@QEAA?AW4Status@bdLobbyConnection@@XZ'
SDK_CONTENT = '?getContentStreaming@bdLobbyService@@QEAAPEAVbdContentStreaming@@XZ'
SDK_COUNTER = '?getCounter@bdLobbyService@@QEAAPEAVbdCounter@@XZ'
SDK_DML = '?getDML@bdLobbyService@@QEAAPEAVbdDML@@XZ'
SDK_GROUP = '?getGroup@bdLobbyService@@QEAAPEAVbdGroup@@XZ'
CONTENT_PUMP = '?pump@bdContentStreamingBase@@QEAAXXZ'
ANTI = '?LiveAntiCheat_Pump@@YAXH@Z'
GAME = '?sub_1405D6E60@@YAXH@Z'
CONTENT_GATE = '?sub_14045CFF0@@YA_NH@Z'
CLEANUP = '?Live_DemonwareDisconnectCleanup@@YAXH@Z'
INSTANCE = '?getInstance@?$bdSingleton@VbdNetImpl@@@@SAPEAVbdNetImpl@@XZ'
NET_STATUS = '?sub_1407679F0@@YAHPEAX@Z'


def _allocate(mu):
    _log('lobby_allocate', _arg(mu))
    return M['allocation']


def _construct(mu):
    _log('lobby_construct', _arg(mu))
    return M['constructed']


def _register(mu):
    _log('register_handler', _arg(mu), _arg(mu, UC_X86_REG_RDX))
    if M['handler_mutation'] != 'none':
        p = M['second'] if M['handler_mutation'] == 'replace' else 0
        _write(static(UTILS, 'lobbyService'), struct.pack('<Q', p))


def _lobby(mu):
    index = M['lobby_calls']
    M['lobby_calls'] += 1
    _log('lobby', _arg(mu) & 0xFFFFFFFF)
    return M['first'] if not index else M['second']


def _status(mu):
    _log('lobby_status', _arg(mu))
    return M['status']


def _service(mu, name):
    _log(name, _arg(mu))
    return M['service']


def _sdk_pump(mu):
    _log('sdk_pump', _arg(mu), _u32(mu, static(UTILS, 'lobbyActivity')))
    if M['pump_mutation']:
        _write(static(UTILS, 'lobbyService'), struct.pack('<Q', M['second']))


def _anti(mu):
    _log('anticheat', _arg(mu) & 0xFFFFFFFF, _u32(mu, static(UTILS, 'lobbyActivity')))
    if M['pump_mutation']:
        _write(static(UTILS, 'lobbyActivity'), struct.pack('<I', 7))


def _game(mu):
    _log('game_callback', _arg(mu) & 0xFFFFFFFF)


def _content_gate(mu):
    _log('content_gate', _arg(mu) & 0xFFFFFFFF)
    return M['content_gate']


def _content_pump(mu):
    _log('content_pump', _arg(mu))


def _cleanup(mu):
    _log('disconnect_cleanup', _arg(mu) & 0xFFFFFFFF,
         bytes(mu.mem_read(static(UTILS, 'authBusy'), 2)),
         _u32(mu, static(UTILS, 'disconnectReason')))
    # Callback sees the updated flags/reason and may modify them itself.
    if M['cleanup_mutation']:
        _write(static(UTILS, 'authBusy'), b'\xA1\xB2')
        _write(static(UTILS, 'disconnectReason'), struct.pack('<I', 0x12345678))


def _instance(mu):
    _log('net_instance')
    return M['net']


def _net_status(mu):
    _log('net_status', _arg(mu))
    return M['net_status']


FACTORY_FAKES = {ALLOC: _allocate, CTOR: _construct, REGISTER: _register}
SERVICE_FAKES = {LOBBY: _lobby, STATUS: _status,
                 SDK_CONTENT: lambda mu: _service(mu, 'get_content'),
                 SDK_COUNTER: lambda mu: _service(mu, 'get_counter'),
                 SDK_DML: lambda mu: _service(mu, 'get_dml'),
                 SDK_GROUP: lambda mu: _service(mu, 'get_group')}
PUMP_FAKES = dict(SERVICE_FAKES)
PUMP_FAKES.update({SDK_PUMP: _sdk_pump, ANTI: _anti, GAME: _game,
                   CONTENT_GATE: _content_gate, CONTENT_PUMP: _content_pump})
READY_FAKES = {INSTANCE: _instance, NET_STATUS: _net_status}
CLEANUP_FAKES = {CLEANUP: _cleanup}


def setup(cached=False, allocation=True, constructed=True, active=0, first=True,
          second=True, service=True, status=2, content_gate=True, handler_mutation='none',
          pump_mutation=False, cleanup_mutation=False, flags=(0, 0), reason=0,
          net=True, net_status=2, state=0, seed=0):
    def apply(w):
        logon_setup(state=state, seed=seed)(w)
        base = static(LOGON, 'logonEntries')+0x1000
        w.u64(static(UTILS, 'lobbyService'), base if cached else 0)
        w.u64(static(LOGON, 'logonUnknown'), active)
        w.write(static(UTILS, 'authBusy'), bytes(flags))
        w.u32(static(UTILS, 'disconnectReason'), reason)
        w.u32(static(UTILS, 'disconnectState'), 0xAABBCCDD)
        w.u32(static(UTILS, 'lobbyActivity'), 0x11223344)
        M.update(allocation=base+0x100 if allocation else 0,
                 constructed=base+0x200 if constructed else 0,
                 first=base if first else 0, second=base+0x300 if second else 0,
                 service=base+0x400 if service else 0, status=status, content_gate=content_gate,
                 handler_mutation=handler_mutation, pump_mutation=pump_mutation,
                 cleanup_mutation=cleanup_mutation, lobby_calls=0,
                 net=base+0x500 if net else 0, net_status=net_status)
    return apply


controllers = (-1, 0, 1, 2, 3, 4, 0x7FFFFFFF, -0x80000000)
factory_inputs = []
for controller in controllers:
    for cached in (False, True):
        for allocated, constructed in ((False, False), (True, False), (True, True)):
            for mutation in ('none', 'replace', 'clear'):
                factory_inputs.append({'args': [controller], 'setup': setup(
                    cached=cached, allocation=allocated, constructed=constructed, handler_mutation=mutation)})

service_inputs = []
for controller in controllers:
    for first in (False, True):
        for status in (-1, 0, 1, 2, 3, 256):
            for service in (False, True):
                service_inputs.append({'args': [controller], 'setup': setup(
                    first=first, status=status, service=service)})

pump_inputs = []
for controller in controllers:
    for first, second in ((False, False), (True, False), (True, True)):
        for status in (-1, 0, 1, 2, 3):
            for service, gate in ((False, False), (True, False), (True, True)):
                for mutation in (False, True):
                    pump_inputs.append({'args': [controller], 'setup': setup(
                        first=first, second=second, status=status, service=service,
                        content_gate=gate, pump_mutation=mutation)})

rng = random.Random(0xDBFD0)
CASES = [
    {'symbol': ACTIVE, 'build': STORE, 'ret': 'int64', 'inputs': [
        {'args': [], 'setup': setup(cached=cached, active=active)} for cached in (False, True)
        for active in (0, 1, 0x123456789ABCDEF0, 0xFFFFFFFFFFFFFFFF)]},
    {'symbol': LOBBY, 'build': STORE, 'ret': 'int64', 'fakes': FACTORY_FAKES, 'inputs': factory_inputs},
    {'symbol': READY, 'build': STORE, 'ret': 'char', 'fakes': READY_FAKES, 'inputs': [
        {'args': [], 'setup': setup(net=net, net_status=status)}
        for net in (False, True) for status in (-1, 0, 1, 2, 3, 256)]},
    {'symbol': PUMP, 'build': STORE, 'ret': 'void', 'fakes': PUMP_FAKES, 'inputs': pump_inputs},
    {'symbol': RESET_STATE, 'build': STORE, 'ret': 'void', 'inputs': [
        {'args': [controller], 'setup': setup(state=state, seed=state)}
        for controller in range(4) for state in (0, 1, 14, 0xFFFFFFFF)]},
    {'symbol': CLEAR, 'build': STORE, 'ret': 'void', 'inputs': [
        {'args': [], 'setup': setup(flags=(a, b), reason=0xFFFFFFFF)}
        for a in (0, 1, 255) for b in (0, 1, 255)]},
    {'symbol': REQUEST, 'build': STORE, 'ret': 'void', 'fakes': CLEANUP_FAKES, 'inputs': [
        {'args': [], 'setup': setup(flags=(a, b), cleanup_mutation=mutation)}
        for a in (0, 1, 255) for b in (0, 1, 255) for mutation in (False, True)]},
    {'symbol': REASON, 'build': STORE, 'ret': 'void', 'fakes': CLEANUP_FAKES, 'inputs': [
        {'args': [reason], 'setup': setup(flags=(a, b), cleanup_mutation=mutation)}
        for reason in (0, 1, 255, 0xFFFFFFFF, rng.getrandbits(32))
        for a in (0, 1, 255) for b in (0, 1, 255) for mutation in (False, True)]},
]
for symbol in (CONTENT, COUNTER, DML, GROUP):
    CASES.append({'symbol': symbol, 'build': STORE, 'ret': 'int64',
                  'fakes': SERVICE_FAKES, 'inputs': service_inputs})

# Service getters and pump with the reconstructed factory, including callback cache replacement.
INTEGRATED_FAKES = {k: v for k, v in PUMP_FAKES.items() if k != LOBBY}
INTEGRATED_FAKES.update(FACTORY_FAKES)
for case in CASES:
    if case['symbol'] in (CONTENT, COUNTER, DML, GROUP, PUMP):
        baseline = case['fakes']
        for inp in case['inputs']:
            inp['fakes'] = baseline
        case['fakes'] = {}
        case['inputs'].extend([
            {'args': [controller], 'setup': setup(
                cached=cached, allocation=allocated, constructed=constructed,
                handler_mutation=mutation, status=status, content_gate=True),
             'fakes': INTEGRATED_FAKES}
            for controller in (0, 3, 4) for cached in (False, True)
            for allocated, constructed in ((False, False), (True, False), (True, True))
            for mutation in ('none', 'replace', 'clear') for status in (1, 2)])
