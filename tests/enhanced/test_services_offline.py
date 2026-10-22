"""P0006: direct service entry points do not expose or operate on vendor objects."""
import test_dwservices as services
from syms import static

OVERRIDES = {services.ACTIVE, services.LOBBY, services.PUMP, services.CONTENT,
             services.COUNTER, services.DML, services.GROUP}


def _forbid(mu):
    raise AssertionError('offline service entry point reached a vendor dependency')


def _fakes(target):
    boundaries = (set(services.FACTORY_FAKES) | set(services.SERVICE_FAKES) |
                  set(services.PUMP_FAKES) | set(services.READY_FAKES) |
                  set(services.CLEANUP_FAKES) | OVERRIDES)
    return {name: _forbid for name in boundaries if name != target}


def _poisoned(active, cached):
    def apply(w):
        services.setup(active=active)(w)
        w.u64(static(services.UTILS, 'lobbyService'), cached)
        w.write(static(services.LOGON, 'logonSuppressed'), b'\xFF')
    return apply


def test_services_getters_do_not_expose_old_or_new_vendor_objects(env):
    getters = (services.ACTIVE, services.LOBBY, services.CONTENT,
               services.COUNTER, services.DML, services.GROUP)
    for symbol in getters:
        for active, cached in ((0, 0), (1, 2), (0xFFFFFFFFFFFFFFFF, 1)):
            for controller in (-1, 0, 1, 3, 4, 0x7FFFFFFF, -0x80000000):
                args = [] if symbol == services.ACTIVE else [controller]
                result, _, writes, observed = env.call(
                    symbol, args, ret='int64', setup=_poisoned(active, cached), fakes=_fakes(symbol))
                assert result == 0 and not writes and not observed, (symbol, controller, result)


def test_services_lobby_pump_stays_inactive_without_callbacks(env):
    activity = static(services.UTILS, 'lobbyActivity')
    for active, cached in ((0, 0), (1, 2), (0xFFFFFFFFFFFFFFFF, 1)):
        for controller in (-1, 0, 1, 3, 4, 0x7FFFFFFF, -0x80000000):
            result, _, writes, observed = env.call(
                services.PUMP, [controller], ret='void', setup=_poisoned(active, cached),
                fakes=_fakes(services.PUMP))
            assert result is None and not observed, (controller, result)
            assert all(writes.get(activity+i) == b'\0' for i in range(4))
            assert writes.get(activity+4) == b'\xFF', 'neighboring logon flag must be retained'
            assert set(writes) <= set(range(activity, activity+8)), writes
