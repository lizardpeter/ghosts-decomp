"""Vendor telemetry text sender: forwarding and temporary task ownership."""
import struct
import test_gdk as gdk
from syms import static

STORE = gdk.STORE
SEND = '?sub_1405D6A90@@YAHPEBDI@Z'
ACTIVE = '?dwGetActiveLobbyService@@YAPEAVbdLobbyService@@XZ'
CONNECTED = '?sub_140748BB0@@YAEPEAX@Z'
LOG = '?sub_1407463D0@@YAPEAXPEAX@Z'
RECORD = '?sub_140749A50@@YAPEAPEAXPEAXPEAPEAXPEBDII0@Z'
DESTROY = gdk.RELEASE_STUB
TM = {}


def log(*args):
    TM['m'].observed.append(args)


def write(p, data):
    TM['m']._emulated_write(p,data)


def active(mu):
    log('active_lobby')
    return TM['lobby']


def connected(mu):
    log('connected',gdk.arg(mu))
    return TM['connected']


def event_log(mu):
    log('event_log',gdk.arg(mu))
    return TM['event_log']


def record(mu):
    log('submit_text',gdk.arg(mu),TM['m'].read_cstr(gdk.arg(mu,2)),
        gdk.arg(mu,3)&0xFFFFFFFF,gdk.arg(mu,4)&0xFFFFFFFF,gdk.arg(mu,5))
    write(gdk.arg(mu,1),struct.pack('<Q',TM['temporary']))
    return TM['box']


def destroy(mu):
    task = gdk.arg(mu)
    count = struct.unpack('<I',bytes(mu.mem_read(task+8,4)))[0]
    log('destroy_task',task,gdk.arg(mu,1)&0xFFFFFFFF,count)
    if TM['mutate']:
        write(TM['box'],bytes(8))


FAKES = {ACTIVE:active,CONNECTED:connected,LOG:event_log,RECORD:record,DESTROY:destroy}


def setup(lobby=True,connected=255,event_log=True,temporary=True,captured=True,refs=1,mutate=False):
    def apply(w):
        base = static('dw/dwutils.cpp','lobbyService')+0x4000
        task,box = base+0x100,base+0x200
        vtable = w.alloc(struct.pack('<Q',gdk.va(DESTROY)))
        w.write(task,struct.pack('<QI4s',vtable,refs,b'KEEP'))
        w.u64(box,task if captured else 0)
        TM.clear()
        TM.update(m=w.m,lobby=base if lobby else 0,connected=connected,
                  event_log=base+0x80 if event_log else 0,temporary=task if temporary else 0,
                  box=box,mutate=mutate)
    return apply


inputs = []
for temporary in (False,True):
    for captured in (False,True):
        for refs in (0,1,2,0xFFFFFFFF):
            for mutate in (False,True):
                for text in (b'\0',b'host-migration telemetry\0',b'line one\nline two\0'):
                    inputs.append({'args':[text,0xFFFFFFFF if mutate else 11],
                        'setup':setup(temporary=temporary,captured=captured,refs=refs,mutate=mutate)})
for lobby,connected in ((False,0),(False,255),(True,0)):
    inputs.append({'args':[1,9], 'setup':setup(lobby=lobby,connected=connected)})
inputs.append({'args':[b'null event-log forwards\0',0], 'setup':setup(event_log=False)})
CASES = [{'symbol':SEND,'build':STORE,'ret':'int','fakes':FAKES,'inputs':inputs}]
