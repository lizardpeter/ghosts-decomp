"""P0008: reconstructed reporting paths never drive vendor work."""
import test_gdk as gdk
import test_gdk_reporting as reporting
from syms import static

OVERRIDES = {reporting.FRAME,reporting.EVENTS,reporting.SAVES,reporting.PRESENCE,'XGameEventWrite'}


def forbid(mu):
    raise AssertionError('offline reporting entry reached an original task, account or SDK dependency')


def fakes(target):
    boundaries = (set(reporting.FAKES) | set(gdk.THUNK_FAKES) | OVERRIDES |
                  {gdk.ENSURE,gdk.LOAD,gdk.QUERY,'XThreadAssertNotTimeSensitive'})
    return {name:forbid for name in boundaries if name != target}


def setup(mode):
    def apply(w):
        reporting.setup(signed=(255,),attempted=mode,ready=mode,pending=mode,
                        provider=0xFFFFFFFFFFFFFFFF)(w)
        w.write(static(gdk.GAME,'signInAttempted')-4,b'PAD!'+bytes([mode,mode])+b'NG')
        w.write(static(gdk.GAME,'savePending')-4,b'SAVE'+bytes([mode])+b'PAD')
        w.u64(static(gdk.GAME,'presenceQueue'),0xFFFFFFFFFFFFFFFF)
        w.u64(static(gdk.GAME,'saveQueue'),1)
        for name in ('AcquireSRWLockExclusive','ReleaseSRWLockExclusive','LoadLibraryExA',
                     'GetProcAddress','FreeLibrary','DebugBreak'):
            w.m.on_import('KERNEL32.dll!'+name,forbid)
    return apply


def check_write(writes, base, old, expected):
    assert set(writes) <= set(range(base,base+len(old))), writes
    actual = b''.join(writes.get(base+i,old[i:i+1]) for i in range(len(old)))
    assert actual == expected, (actual,expected)


def test_reporting_frame_never_retries_signin_or_pumps_vendor_subsystems(env):
    base = static(gdk.GAME,'signInAttempted')-4
    for mode in (0,1,255):
        for frame in (0,-1,0x7FFFFFFF,-0x80000000):
            value,_,writes,observed = env.call(reporting.FRAME,[frame],setup=setup(mode),
                                              fakes=fakes(reporting.FRAME))
            assert value is None and not observed
            check_write(writes,base,b'PAD!'+bytes([mode,mode])+b'NG',b'PAD!\0\0NG')


def test_reporting_event_and_presence_pumps_do_no_work(env):
    for symbol in (reporting.EVENTS,reporting.PRESENCE):
        for mode in (0,1,255):
            value,_,writes,observed = env.call(symbol,[],setup=setup(mode),fakes=fakes(symbol))
            assert value is None and not writes and not observed


def test_reporting_save_pump_discards_pending_work_without_callbacks(env):
    base = static(gdk.GAME,'savePending')-4
    for mode in (0,1,255):
        value,_,writes,observed = env.call(reporting.SAVES,[],setup=setup(mode),
                                          fakes=fakes(reporting.SAVES))
        assert value is None and not observed
        check_write(writes,base,b'SAVE'+bytes([mode])+b'PAD',b'SAVE\0PAD')


def test_reporting_event_submission_refused_without_reading_payload_or_sdk(env):
    for pointer in (0,1,0xFFFFFFFFFFFFFFFF):
        value,buffers,writes,observed = env.call('XGameEventWrite',[pointer]*6,ret='int',
            setup=setup(255),fakes=fakes('XGameEventWrite'))
        assert value == -0x76DBFF00 and not buffers and not writes and not observed
