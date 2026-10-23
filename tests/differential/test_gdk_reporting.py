"""GDK reporting drivers and event submission, with no real SDK or network."""
import csv
import struct
import test_gdk as gdk
from harness import ROOT
from syms import static, va

GAME = gdk.GAME
FRAME = '?sub_1401A1760@@YAXH@Z'
EVENTS = '?sub_14019F390@@YAXXZ'
SAVES = '?sub_1401A1320@@YAXXZ'
PRESENCE = '?sub_1401A1CA0@@YAXXZ'
TABLE = {r['va']: r['symbol'] for r in csv.DictReader(
    (ROOT/'records/names.tsv').open(), delimiter='\t')
    if r['build'] == gdk.STORE and r['kind'] == 'function'}
RM = {}
# Callback arguments at original call sites: i = dword, b = low byte, p = pointer.
CALLS = {
 '140222950':'', '1401A7EA0':'i', '1401A7ED0':'i', '1401A8000':'i',
 '1401A7DF0':'i', '1401A7F20':'', '1401A5930':'ib', '1401A5740':'',
 '1401A61A0':'', '1404523E0':'', '1401A53E0':'i', '14031FF20':'i',
 '140320100':'i', '140320070':'i', '1405D3DC0':'b', '140237000':'ii',
 '1401A8710':'', '14019F940':'', '1401A2790':'', '14045F4F0':'p',
 '1406B1124':'pii', '1401A1320':'', '14019F390':'', '1401A1CA0':''}
for address in ('1401A10E0','1401A1190','140448B70','140447100','140447340',
                '14044F240','140457A80','140452810','140452830','1405EC320',
                '1405F26B0','1405D6340','1401A28C0','1405F3B10'):
    CALLS[address] = 'i'


def fake(address, kinds):
    def run(mu):
        args = tuple(gdk.arg(mu, i) & (0xFF if kind == 'b' else
                     0xFFFFFFFF if kind == 'i' else 0xFFFFFFFFFFFFFFFF)
                     for i, kind in enumerate(kinds))
        RM['machine'].observed.append((address, *args))
        if RM['mutate'] == address:
            for name, value in (('signInAttempted',255),('onlineReady',2),('savePending',255)):
                RM['machine']._emulated_write(static(GAME,name), bytes([value]))
        if address == '1401A7EA0':
            index = RM['signed_calls']
            RM['signed_calls'] += 1
            return RM['signed'][min(index, len(RM['signed'])-1)]
        return RM['returns'].get(address, 0)
    return run


FAKES = {TABLE[a]: fake(a, kinds) for a,kinds in CALLS.items()}


def setup(menu=1, signed=(0,), attempted=0, ready=0, store=0, store_ready=0,
          busy=0, state=0, match=1, special=0, mutate='', pending=1, provider=1, save_ready=1):
    def apply(w):
        RM.clear()
        RM.update(machine=w.m, signed=signed, signed_calls=0, mutate=mutate,
                  returns={'140222950':menu,'1401A7ED0':busy,'1401A7DF0':state,
                    '1401A7F20':match,'1401A5740':store,'1401A61A0':store_ready,
                    '1404523E0':special,'14031FF20':save_ready,'1406B1124':255})
        w.write(static(GAME,'signInAttempted'), bytes([attempted,ready])+b'NEIGHBOR!!')
        w.write(static(GAME,'savePending'), bytes([pending])+b'PADDED!')
        w.u64(static(GAME,'saveProvider'), provider)
        w.u64(static(GAME,'saveQueue'), 0x123456789ABCDEF0)
        w.u64(static(GAME,'presenceQueue'), 0xFEDCBA9876543210)
    return apply


frame_inputs = []
for menu in (0,255):
    for signed in ((0,), (0,0,1), (0,255,1), (1,), (255,)):
        for attempted,ready in ((0,0),(1,0),(1,1),(255,255)):
            for store,store_ready in ((0,0),(4,0),(4,255)):
                for busy in (0,255):
                    frame_inputs.append({'args':[-123], 'setup':setup(menu=menu,signed=signed,
                        attempted=attempted,ready=ready,store=store,store_ready=store_ready,
                        busy=busy,special=busy)})
for state in (0,1,0xFFFFFFFF):
    for match in (0,255):
        frame_inputs.append({'args':[0x7FFFFFFF], 'setup':setup(
            signed=(0,1,0),state=state,match=match)})
for mutation in ('1401A8000','1401A61A0','1401A10E0','1401A28C0','14045F4F0'):
    frame_inputs.append({'args':[0], 'setup':setup(signed=(0,0,1),store=4,
                         store_ready=1,mutate=mutation)})
CASES = [
 {'symbol':FRAME,'build':gdk.STORE,'ret':'void','fakes':FAKES,'inputs':frame_inputs},
 {'symbol':EVENTS,'build':gdk.STORE,'ret':'void','fakes':FAKES,
  'inputs':[{'args':[],'setup':setup()}]},
 {'symbol':PRESENCE,'build':gdk.STORE,'ret':'void','fakes':FAKES,
  'inputs':[{'args':[],'setup':setup(mutate=m)} for m in ('','1406B1124')]},
 {'symbol':SAVES,'build':gdk.STORE,'ret':'void','fakes':FAKES,
  'inputs':[{'args':[],'setup':setup(signed=(signed,),provider=provider,pending=pending,
     save_ready=save_ready,mutate=m)} for signed in (0,1,255) for provider in (0,1)
     for pending in (0,1,255) for save_ready in (0,255) for m in ('','140320070')]},
]
# Frame integration keeps the three reconstructed reporting pumps real.
for profile in ((0,),(1,),(0,0,1),(255,)):
    CASES[0]['inputs'].append({'args':[1], 'setup':setup(signed=profile,store=4,store_ready=1),
        'fakes':{k:v for k,v in FAKES.items() if k not in (EVENTS,PRESENCE,SAVES)}})

EVENT_METHOD = gdk.TOKEN_STUB


def event_method(mu):
    gdk.log('write_event', gdk.arg(mu), gdk.arg(mu,1),
            *[gdk.cstr(gdk.arg(mu,i)) if gdk.arg(mu,i) else None for i in range(2,7)])
    return gdk.M['method_result']


def event_setup(sequence=(0,0), result=0):
    def apply(w):
        gdk.thunk_setup(sequence=sequence,method_result=result)(w)
        table = [0]*4
        table[2],table[3] = va(gdk.RELEASE_STUB),va(EVENT_METHOD)
        vtable = w.alloc(struct.pack('<4Q',*table))
        p = static(gdk.SRC,'runtime')+0x2200
        w.write(p,struct.pack('<QI',vtable,2))
        guid = bytes(w.m.mu.mem_read(static(gdk.SRC,'eventIID'),16))
        gdk.M['interfaces'][guid] = p
    return apply


EVENT_FAKES = {**gdk.THUNK_FAKES, EVENT_METHOD:event_method}
event_inputs = []
for sequence in ((0,0),(0x80004005,0),(0,0x80004005),(1,1),(1,0x80040154)):
    for result in (0,1,0x80004005):
        for null in (False,True):
            event_inputs.append({'args':[0x123456789ABCDEF0,
                *([0]*5 if null else [b'scid\0',b'play-session\0',b'Achievement1Unlocked\0',
                                      b'{"Unlock":true}\0',b'{}\0'])],
                'setup':event_setup(sequence,result)})
CASES.append({'symbol':'XGameEventWrite','build':gdk.STORE,'ret':'int',
              'fakes':EVENT_FAKES,'inputs':event_inputs})

# A direct test must execute its target; the same symbol is a dependency in frame tests.
for case in CASES:
    case['fakes'] = {k:v for k,v in case['fakes'].items() if k != case['symbol']}
