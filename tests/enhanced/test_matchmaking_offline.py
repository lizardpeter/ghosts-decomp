"""P0010: discard matchmaking telemetry without collecting or submitting it."""
import struct
import test_matchmaking_telemetry as binary
from syms import static

OVERRIDES = {binary.RESET,binary.REPORT,binary.APPEND,binary.SNAPSHOT,binary.MATCH,binary.TRIGGER}
REGIONS = {'record':0x9C8,'activeRing':400,'snapshotRing':400,'activeIndex':4,
           'snapshotCount':4,'currentSlot':4,'sampleCount':4,'seenMatches':4}


def forbid(mu):
    raise AssertionError('offline matchmaking telemetry reached a collector or vendor dependency')


def fakes(target):
    return {name:forbid for name in set(binary.REPORT_FAKES)|OVERRIDES|{binary.CLOCK}
            if name != target}


def setup(w):
    binary.setup(index=0xFFFFFFFF,reset_value=1)(w)
    for name in ('recordModeDvar','samplingDvar','resetDvar'):
        w.u64(static(binary.SRC,name),1)
    addresses = set()
    for name,size in REGIONS.items():
        base = static(binary.SRC,name)
        addresses.update(range(base&~7,(base+size+7)&~7))
    binary.M['initial'] = {a:bytes(w.m.mu.mem_read(a,1)) for a in addresses}


def expected(clear_record):
    before = binary.M['initial']
    after = dict(before)
    def put(name,data):
        base = static(binary.SRC,name)
        after.update({base+i:data[i:i+1] for i in range(len(data))})
    for name in ('activeRing','snapshotRing'):
        put(name,bytes(400))
    for name in ('activeIndex','snapshotCount','sampleCount','seenMatches'):
        put(name,bytes(4))
    put('currentSlot',struct.pack('<I',250))
    if clear_record:
        put('record',b'\x03'+bytes(0x9C7))
    return before,after


def check(writes,clear_record=False):
    before,after = expected(clear_record)
    assert set(writes) <= set(before), writes
    for address,value in after.items():
        assert writes.get(address,before[address]) == value, hex(address)


def test_matchmaking_report_and_reset_discard_without_sampling_or_recollecting(env):
    for symbol in (binary.REPORT,binary.RESET):
        for kind,pending in ((3,1),(3,0),(0,255),(255,255)):
            payload = bytes([kind,pending])+b'\xE7'*0x9C6
            args = [-1,payload] if symbol == binary.REPORT else [payload]
            value,buffers,writes,calls = env.call(symbol,args,setup=setup,fakes=fakes(symbol))
            assert value is None and not calls
            assert buffers == [b'\x03'+bytes(0x9C7)]
            check(writes)
        args = [0,0] if symbol == binary.REPORT else [0]
        value,buffers,writes,calls = env.call(symbol,args,setup=setup,fakes=fakes(symbol))
        assert value is None and not buffers and not calls
        check(writes)


def test_matchmaking_trigger_and_snapshot_do_not_read_dvars_or_collect(env):
    for symbol in (binary.TRIGGER,binary.SNAPSHOT):
        value,buffers,writes,calls = env.call(symbol,[],setup=setup,fakes=fakes(symbol))
        assert value is None and not buffers and not calls
        check(writes,clear_record=symbol==binary.TRIGGER)


def test_matchmaking_collectors_ignore_identifiers_and_invalid_ring_index(env):
    for symbol in (binary.APPEND,binary.MATCH):
        for pointer in (0,1,0xFFFFFFFFFFFFFFFF):
            value,buffers,writes,calls = env.call(symbol,[pointer],setup=setup,fakes=fakes(symbol))
            assert value is None and not buffers and not writes and not calls
