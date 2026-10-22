"""P0007: no runtime DLL, Xbox interface, account or token work on these paths."""
import struct
import test_gdk as gdk
from syms import static

UNAVAILABLE = -0x76DBFF00  # HRESULT 0x89240100
OVERRIDES = {gdk.LOAD, gdk.ENSURE, gdk.QUERY, gdk.GAME_INIT,
             'XGameRuntimeInitialize', 'XGameRuntimeUninitialize'}


def _forbid(mu):
    raise AssertionError('offline GDK path reached a runtime/SDK dependency')


def _fakes(target, inherited=False):
    boundaries = (set(gdk.RUNTIME_FAKES) | set(gdk.THUNK_FAKES) |
                  set(gdk.STARTUP_FAKES) | OVERRIDES)
    if inherited:
        boundaries -= {gdk.QUERY, 'XThreadAssertNotTimeSensitive'}
    return {name: _forbid for name in boundaries if name != target}


def _state(mode):
    if mode == 0:
        return struct.pack('<QBB6sQ5Q', 0x123456789ABCDEF0, 0, 0, b'PADDED', 0, *([0]*5))
    return struct.pack('<QBB6sQ5Q', 0x123456789ABCDEF0, 255, 255, b'PADDED',
                       1, *([0xFFFFFFFFFFFFFFFF]*5))


def _setup(mode):
    def apply(w):
        w.write(static(gdk.SRC, 'runtime'), _state(mode))
        for name in ('AcquireSRWLockExclusive', 'ReleaseSRWLockExclusive', 'LoadLibraryExA',
                     'GetProcAddress', 'FreeLibrary', 'DebugBreak'):
            w.m.on_import('KERNEL32.dll!'+name, _forbid)
        w.m.on_import('USER32.dll!MessageBoxW', _forbid)
        w.m.on_import('api-ms-win-crt-convert-l1-1-0.dll!_itoa', _forbid)
    return apply


def test_gdk_runtime_entry_guards_ignore_cached_vendor_state(env):
    for mode in (0, 1):
        for symbol, args in ((gdk.LOAD, []), (gdk.ENSURE, [0]), (gdk.ENSURE, [1]),
                             (gdk.ENSURE, [0xFFFFFFFFFFFFFFFF]), ('XGameRuntimeInitialize', [])):
            value, _, writes, observed = env.call(symbol, args, ret='int', setup=_setup(mode),
                                                  fakes=_fakes(symbol))
            assert value == UNAVAILABLE and not writes and not observed, (symbol, value, writes)


def test_gdk_query_clears_output_and_never_reads_interface_ids(env):
    for mode in (0, 1):
        for output in (0, b'OLD-API!'):
            value, buffers, writes, observed = env.call(
                gdk.QUERY, [1, 0xFFFFFFFFFFFFFFFF, output], ret='int',
                setup=_setup(mode), fakes=_fakes(gdk.QUERY))
            assert value == UNAVAILABLE and not writes and not observed
            if output:
                assert buffers[0] == bytes(8), buffers


def test_gdk_uninitialize_clears_only_runtime_fields_without_sdk_cleanup(env):
    base = static(gdk.SRC, 'runtime')
    for mode in (0, 1):
        value, _, writes, observed = env.call(
            'XGameRuntimeUninitialize', [], setup=_setup(mode),
            fakes=_fakes('XGameRuntimeUninitialize'))
        assert value is None and not observed
        expected = bytearray(_state(mode))
        expected[8:10] = bytes(2)
        expected[16:64] = bytes(48)
        original = _state(mode)
        for offset, byte in enumerate(expected):
            assert writes.get(base+offset, original[offset:offset+1]) == bytes([byte]), offset
        assert set(writes) <= set(range(base+8, base+64))


def test_gdk_game_startup_skips_all_vendor_subsystems(env):
    for mode in (0, 1):
        value, _, writes, observed = env.call(gdk.GAME_INIT, [], ret='char',
            setup=_setup(mode), fakes=_fakes(gdk.GAME_INIT))
        assert value == 0 and not writes and not observed


def test_gdk_reconstructed_thunks_stop_at_actual_offline_query(env):
    calls = [('XThreadAssertNotTimeSensitive', [], 'void', None),
             ('XGameGetXboxTitleId', [b'TOLD'], 'int', UNAVAILABLE),
             ('XGameRuntimeIsFeatureAvailable', [0xFFFFFFFF], 'char', 0),
             ('XUserAddAsync', [0xFFFFFFFF, 1], 'int', UNAVAILABLE),
             ('XUserGetTokenAndSignatureAsync', [1, 0xFFFFFFFF, 1, 1,
                 0xFFFFFFFFFFFFFFFF, 1, 0xFFFFFFFFFFFFFFFF, 1, 1], 'int', UNAVAILABLE)]
    for mode in (0, 1):
        for symbol, args, ret, expected in calls:
            value, buffers, writes, observed = env.call(symbol, args, ret=ret,
                setup=_setup(mode), fakes=_fakes(symbol, inherited=True))
            assert value == expected and not writes and not observed, (symbol, value)
            if symbol == 'XGameGetXboxTitleId':
                assert buffers[0] == b'TOLD'
