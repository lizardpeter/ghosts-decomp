"""Binary matchmaking reporter and local collection; all providers are simulated."""
import struct
from unicorn.x86_const import UC_X86_REG_XMM0, UC_X86_REG_XMM1
import test_gdk as gdk
from syms import static, va

SRC = 'dw/matchmaking_telemetry.cpp'
STORE = gdk.STORE
RESET = '?sub_140199300@@YAXPEAUMatchmakingTelemetryRecord@@@Z'
REPORT = '?sub_140199DA0@@YAXHPEAUMatchmakingTelemetryRecord@@@Z'
APPEND = '?sub_140199ED0@@YAXPEB_K@Z'
SNAPSHOT = '?sub_140199CC0@@YAXXZ'
MATCH = '?sub_140199480@@YAXPEB_K@Z'
TRIGGER = '?sub_140199D70@@YAXXZ'
FILL = '?sub_140536260@@YAXPEAXH_K@Z'
MODE = '?sub_14044FCC0@@YAHXZ'
PAIRS = '?sub_140194780@@YAXPEAHPEAGI@Z'
VALUE1 = '?sub_140194410@@YAGXZ'
VALUE2 = '?sub_140194910@@YAGXZ'
RANDOM = '?sub_140530980@@YAMMM@Z'
FORCE = '?sub_1405F0700@@YAEHH@Z'
LOBBY = '?dwGetLobbyService@@YAPEAVbdLobbyService@@H@Z'
CONNECTED = '?sub_140748BB0@@YAEPEAX@Z'
LOG = '?sub_1407463D0@@YAPEAXPEAX@Z'
SERIALIZE = '?sub_14044E130@@YAHPEBXIPEAXI@Z'
SUBMIT = '?sub_140749C00@@YAXPEAXPEAPEAXPEBXII0@Z'
CLOCK = '?Sys_Milliseconds@@YAHXZ'
SLOT1 = gdk.TOKEN_STUB
DESTROY = gdk.RELEASE_STUB
M = {}


def arg(mu,i=0):
    return gdk.arg(mu,i)


def read(p,n):
    return bytes(M['m'].mu.mem_read(p,n))


def write(p,b):
    M['m']._emulated_write(p,b)


def log(*items):
    M['m'].observed.append(items)


def fill(mu):
    p,value,size = arg(mu),arg(mu,1)&255,arg(mu,2)
    log('fill',p,value,size)
    write(p,bytes([value])*size)


def mode(mu):
    log('mode')
    return M['mode']


def pairs(mu):
    count,out,mask = arg(mu),arg(mu,1),arg(mu,2)&0xFFFFFFFF
    log('pairs',struct.unpack('<i',read(count,4))[0],mask)
    write(count,struct.pack('<i',M['pair_count']))
    write(out,struct.pack('<10H',*M['pairs']))


def value1(mu):
    log('value1')
    return M['value1']


def value2(mu):
    log('value2')
    return M['value2']


def random(mu):
    log('random',mu.reg_read(UC_X86_REG_XMM0)&0xFFFFFFFF,
        mu.reg_read(UC_X86_REG_XMM1)&0xFFFFFFFF)
    if M['change_rate']:
        write(M['sampling']+0x10,struct.pack('<I',0x3F800000))
    mu.reg_write(UC_X86_REG_XMM0,M['random_bits'])


def force(mu):
    log('force',arg(mu)&0xFFFFFFFF,arg(mu,1)&0xFFFFFFFF)
    return M['force']


def lobby(mu):
    log('lobby',arg(mu)&0xFFFFFFFF)
    return M['lobby']


def connected(mu):
    log('connected',arg(mu))
    return M['connected']


def event_log(mu):
    log('event_log',arg(mu))
    return M['event_log']


def serialize(mu):
    log('serialize',arg(mu,1)&0xFFFFFFFF,arg(mu,3)&0xFFFFFFFF,read(arg(mu),8))
    if M['size']>0:
        write(arg(mu,2),bytes((i*7)&255 for i in range(M['size'])))
    return M['size']


def submit(mu):
    size = arg(mu,3)&0xFFFFFFFF
    log('submit',arg(mu),read(arg(mu,2),size),size,arg(mu,4)&0xFFFFFFFF,arg(mu,5))
    M['task_output'] = arg(mu,1)
    write(arg(mu,1),struct.pack('<Q',M['task'] if M['has_task'] else 0))


def slot1(mu):
    log('task_method',arg(mu))
    if M['replace_task']:
        write(M['task_output'],struct.pack('<Q',M['replacement'] if M['replace_task']==2 else 0))


def destroy(mu):
    p = arg(mu)
    log('destroy',p,arg(mu,1)&0xFFFFFFFF,struct.unpack('<I',read(p+8,4))[0])


def reset_fake(mu):
    log('reset',arg(mu),read(arg(mu),4))
    write(arg(mu),b'RESETTED')


def clock(mu):
    log('clock')
    return 0x87654321


RESET_FAKES = {FILL:fill,MODE:mode,PAIRS:pairs,VALUE1:value1,VALUE2:value2}
REPORT_FAKES = {**RESET_FAKES,RESET:reset_fake,RANDOM:random,FORCE:force,LOBBY:lobby,
               CONNECTED:connected,LOG:event_log,SERIALIZE:serialize,SUBMIT:submit,
               SLOT1:slot1,DESTROY:destroy}


def setup(rate_bits=0x3D4CCCCD,random_bits=0,force=0,lobby=True,connected=255,
          event_log=True,size=13,has_task=True,refs=1,replace_task=0,pair_count=5,
          pair_values=(0,0,255,255,256,0x8001,0xFFFF,0xFFFF,123,0x8100),
          mode_byte=255,change_rate=False,index=3,seen=0xFFFFFFFF,reset_value=1):
    def apply(w):
        base = static(gdk.SRC,'runtime')+0x5000
        dmode,sampling,reset = base,base+0x40,base+0x80
        w.u64(static(SRC,'recordModeDvar'),dmode)
        w.u64(static(SRC,'samplingDvar'),sampling)
        w.u64(static(SRC,'resetDvar'),reset)
        w.write(dmode+0x10,bytes([mode_byte]))
        w.u32(sampling+0x10,rate_bits)
        w.u32(reset+0x10,reset_value)
        w.write(static(SRC,'record'),b'\xA5'*0x9C8)
        for name,offset in (('activeRing',0),('snapshotRing',100)):
            w.write(static(SRC,name),struct.pack('<50Q',*[i+offset for i in range(50)]))
        for name,value in (('activeIndex',index),('snapshotCount',17),('currentSlot',42),
                           ('sampleCount',123),('seenMatches',seen)):
            w.u32(static(SRC,name),value)
        table = w.alloc(struct.pack('<2Q',va(DESTROY),va(SLOT1)))
        task,replacement = base+0x100,base+0x140
        for p in (task,replacement):
            w.write(p,struct.pack('<QI4s',table,refs,b'KEEP'))
        M.clear()
        M.update(m=w.m,mode=0xFFFFFFFF,pair_count=pair_count,pairs=pair_values,
                 value1=0x12345678,value2=0xFFFFFFFF,random_bits=random_bits,force=force,
                 lobby=base+0x200 if lobby else 0,connected=connected,
                 event_log=base+0x240 if event_log else 0,size=size,task=task,
                 replacement=replacement,has_task=has_task,replace_task=replace_task,
                 sampling=sampling,change_rate=change_rate)
    return apply


def record(kind=3,pending=1):
    return bytes([kind,pending])+b'\xCC'*(0x9C8-2)


reset_inputs = []
for count in (-1,0,1,5):
    for mode_byte in (0,1,255):
        reset_inputs.append({'args':[b'\x55'*0x9C8],
            'setup':setup(pair_count=count,mode_byte=mode_byte)})
reset_inputs.append({'args':[0x140DF0F00],'setup':setup()})
report_inputs = []
for rate,draw in ((0,0),(0x3F800000,0),(0x3D4CCCCD,0x3D4CCCCD),
                  (0x7FC00000,0),(0x3F800000,0x7FC00000)):
    for forced in (0,255):
        for has_lobby,is_connected in ((False,0),(True,0),(True,255)):
            report_inputs.append({'args':[-1,record()], 'setup':setup(
                rate_bits=rate,random_bits=draw,force=forced,lobby=has_lobby,
                connected=is_connected)})
for size in (0,-1,1,0xC00):
    for has_task in (False,True):
        report_inputs.append({'args':[0,record()], 'setup':setup(size=size,has_task=has_task)})
for refs in (0,1,2,0xFFFFFFFF):
    for replacement in (0,1,2):
        report_inputs.append({'args':[3,record()], 'setup':setup(refs=refs,replace_task=replacement)})
for kind,pending in ((0,0),(3,0),(2,1),(255,255),(3,255)):
    report_inputs.append({'args':[0,record(kind,pending)],'setup':setup()})
report_inputs.append({'args':[0,record()], 'setup':setup(event_log=False,change_rate=True,rate_bits=0)})
# Connected path through the real reconstructed reset and its simulated local providers.
for forced in (0,255):
    report_inputs.append({'args':[1,record()], 'setup':setup(force=forced,rate_bits=0),
                          'fakes':{k:v for k,v in REPORT_FAKES.items() if k != RESET}})

CASES = [
 {'symbol':RESET,'build':STORE,'ret':'void','fakes':RESET_FAKES,'inputs':reset_inputs},
 {'symbol':REPORT,'build':STORE,'ret':'void','fakes':REPORT_FAKES,'inputs':report_inputs},
 {'symbol':APPEND,'build':STORE,'ret':'void','inputs':[
     {'args':[struct.pack('<Q',value)],'setup':setup(index=index)}
     for index in (0,1,48,49,50,51) for value in (0,1,0xFFFFFFFFFFFFFFFF)]},
 {'symbol':SNAPSHOT,'build':STORE,'ret':'void','inputs':[
     {'args':[],'setup':setup(index=i)} for i in (0,1,49,50,0xFFFFFFFF)]},
 {'symbol':MATCH,'build':STORE,'ret':'void','inputs':[
     {'args':[struct.pack('<Q',value)],'setup':setup(seen=seen)}
     for value in (0,99,100,125,149,150,0xFFFFFFFFFFFFFFFF) for seen in (0,0xFFFFFFFF)]},
 {'symbol':TRIGGER,'build':STORE,'ret':'void','fakes':{RESET:reset_fake,CLOCK:clock},
  'inputs':[{'args':[],'setup':setup(reset_value=v)} for v in (0,1,2,0xFFFFFFFF)]},
]
CASES[-1]['inputs'].append({'args':[],'setup':setup(),
                          'fakes':{**RESET_FAKES,CLOCK:clock}})

# Per-input maps replace the direct-call fixture for connected reset cases.
# The runner merges case maps, so do not leave RESET faked at case level.
for case in CASES:
    defaults = case.pop('fakes', {})
    for inp in case['inputs']:
        inp.setdefault('fakes', defaults)
