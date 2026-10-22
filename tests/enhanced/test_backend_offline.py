"""P0005: login entry points cannot call SDK auth, DNS, lobby or platform gates."""
import test_dwlogon as logon
from syms import static

OVERRIDES = {logon.START, logon.STEP, logon.STATUS, logon.BUSY, logon.AUTH_GET, logon.FRAME}


def _forbid(mu):
    raise AssertionError('offline login reached a backend/platform boundary')


def _fakes():
    boundaries = set(logon.FAKES) | set(logon.STEP_FAKES) | set(logon.AUTH_FAKES) | set(logon.FRAME_FAKES)
    return {name: _forbid for name in boundaries - OVERRIDES}


def _value(writes, address, width=4, default=0):
    old = default.to_bytes(width, 'little')
    return int.from_bytes(b''.join(writes.get(address+i, old[i:i+1]) for i in range(width)), 'little')


def _poisoned(state):
    def apply(w):
        logon.step_setup(state=state)(w)
        entry = static(logon.SOURCE, 'logonEntries')
        for offset in (4, 8, 12):
            w.u32(entry+offset, 0x11223344)
        # Unusable objects would fault if an entry point tried SDK cleanup or polling.
        w.u64(static(logon.SOURCE, 'authResolver'), 1)
        w.u64(static(logon.SOURCE, 'lobbyResolver'), 1)
        w.u64(static(logon.UTILS, 'authClient'), 1)
        w.write(static(logon.SOURCE, 'logonSuppressed'), b'\xFF')
    return apply


def test_backend_start_and_step_stay_offline(env):
    entry = static(logon.SOURCE, 'logonEntries')
    for symbol in (logon.START, logon.STEP, logon.FRAME):
        for state in logon.states:
            result, _, writes, observed = env.call(symbol, [0], ret='void',
                                              setup=_poisoned(state), fakes=_fakes())
            assert result is None, result
            assert not observed, observed
            for offset in (0, 4, 8, 12):
                old = state if offset == 0 else 0x11223344
                assert _value(writes, entry+offset, default=old) == 0, (symbol, state, offset)
            assert _value(writes, static(logon.SOURCE, 'logonSuppressed'), 1, default=255) == 0
            # No resolver or cached SDK-object writes: this is not a hot-swap cleanup API.
            for name, source in (('authResolver', logon.SOURCE), ('lobbyResolver', logon.SOURCE),
                                 ('authClient', logon.UTILS)):
                p = static(source, name)
                assert not any(p+i in writes for i in range(8)), name


def _visible_status(state):
    def apply(w):
        _poisoned(state)(w)
        w.write(static(logon.SOURCE, 'logonSuppressed'), b'\0')
    return apply


def test_backend_status_never_reports_vendor_login(env):
    for symbol in (logon.STATUS, logon.BUSY):
        for state in logon.states:
            for controller in (0, 1):
                result, _, writes, observed = env.call(symbol, [controller], ret='char',
                                                       setup=_visible_status(state), fakes=_fakes())
                assert result == 0 and not writes and not observed, (symbol, state, result)


def test_backend_auth_factory_never_allocates_or_returns_vendor_client(env):
    for state in logon.states:
        for host, port, title in ((b'auth.invalid\0', 443, 2510), (0, 0, 0),
                                  (1, 65535, 0xFFFFFFFF)):
            result, _, writes, observed = env.call(logon.AUTH_GET, [host, port, title], ret='int64',
                                                   setup=_poisoned(state), fakes=_fakes())
            assert result == 0 and not writes and not observed, (state, result)
