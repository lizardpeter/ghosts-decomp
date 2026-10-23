"""Account results and repair UI: original COM forwarding, with fake SDK only."""
import struct
import test_gdk as gdk
from syms import static, va

METHOD = gdk.ADD_STUB
# Independent observed slots and ABI widths, not read from authored source.
SPECS = (
    ('1406B15C8', 'XUserAddResult', 8, (), (1,)),
    ('1406B1644', 'XUserCheckPrivilege', 20, (1, 2), (3, 4)),
    ('1406B1B10', 'XUserGetId', 11, (), (1,)),
    ('1406B1C84', 'XUserGetState', 14, (), (1,)),
    ('1406B1DE0', 'XUserGetTokenAndSignatureResult', 25, (), (2, 3, 4)),
    ('1406B1E8C', 'XUserGetTokenAndSignatureResultSize', 24, (), (1,)),
    ('1406B201C', 'XUserResolveIssueWithUiAsync', 29, (), ()),
    ('1406B20A8', 'XUserResolveIssueWithUiResult', 30, (), ()),
    ('1406B2118', 'XUserResolvePrivilegeWithUiAsync', 21, (1, 2), ()),
    ('1406B21B8', 'XUserResolvePrivilegeWithUiResult', 22, (), ()),
)


def arguments(name, wide=False, null=False):
    high = 0x123456789ABCDEF0 if wide else 0
    pointer = high or 1
    output = 0 if null else b'UNCHANGED-OUTPUT!'
    if name == 'XUserCheckPrivilege':
        return [pointer, high | 3, high | 254, output, output]
    if name == 'XUserGetTokenAndSignatureResult':
        return [pointer, high | 16, output, output, output]
    if name == 'XUserResolvePrivilegeWithUiAsync':
        return [pointer, high | 4, high | 254, pointer ^ 0x55]
    if name == 'XUserResolveIssueWithUiAsync':
        return [pointer, 0 if null else b'https://example.invalid/account\0', pointer ^ 0x55]
    if name.endswith('WithUiResult'):
        return [pointer]
    return [pointer, output]


def method(mu):
    spec = gdk.M['user_spec']
    name, narrow, outputs = spec[1], spec[3], spec[4]
    count = len(arguments(name))
    args = [gdk.arg(mu, i+1) for i in range(count)]
    for i in narrow:
        args[i] &= 0xFFFFFFFF
    gdk.log('account_method', name, gdk.arg(mu), *args)
    # Provider side effects also survive a failed method, unlike a failed query.
    for index in outputs:
        p = args[index]
        if not p:
            continue
        if name == 'XUserCheckPrivilege':
            value = b'\x01' if index == 3 else struct.pack('<I', 0xFEDCBA98)
        elif name == 'XUserGetState':
            value = struct.pack('<I', 0x87654321)
        elif name == 'XUserGetTokenAndSignatureResult' and index == 2:
            value = b'TOKEN'
        else:
            value = struct.pack('<Q', 0x123456789ABCDEF0)
        gdk.write(p, value)
    return gdk.M['method_result']


def setup(spec, query=0, result=0, integrated=False, cached=False):
    def apply(w):
        if integrated:
            gdk.integrated_setup((cached, 31 if cached else 0, 31, True, 0, query, int(cached), 0))(w)
        else:
            gdk.thunk_setup(sequence=(query,), method_result=result)(w)
        table = [0]*32
        table[2] = va(gdk.RELEASE_STUB)
        table[spec[2]] = va(METHOD)
        vtable = w.alloc(struct.pack('<32Q', *table))
        guid = bytes(w.m.mu.mem_read(static(gdk.SRC, 'userFamily'), 16))
        p = gdk.M['interfaces'][guid]
        w.write(p, struct.pack('<QI', vtable, 2))
        gdk.M['user_spec'] = spec
        gdk.M['method_result'] = result
    return apply


DIRECT_FAKES = {**gdk.THUNK_FAKES, METHOD: gdk.imp(method)}
INTEGRATED_FAKES = {**gdk.INTEGRATED_FAKES, METHOD: gdk.imp(method)}
CASES = []
for spec in SPECS:
    inputs = []
    for query in (0, 1, 0x80004005, 0x89240100):
        for result in (0, 1, 0x80004005):
            for wide in (False, True):
                for null in (False, True):
                    inputs.append({'args': arguments(spec[1], wide, null),
                                   'setup': setup(spec, query, result), 'fakes': DIRECT_FAKES})
    for cached in (False, True):
        for query in (0, 0x80004005, 0x80040154):
            inputs.append({'args': arguments(spec[1], True),
                           'setup': setup(spec, query, 0x80004005, True, cached),
                           'fakes': INTEGRATED_FAKES})
    CASES.append({'symbol': spec[1], 'build': gdk.STORE, 'ret': 'int', 'inputs': inputs})
