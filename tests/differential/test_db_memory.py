"""Differential cases for database/db_memory.cpp: the zone's block allocation (PMem_AllocFromSource_NoDebug is
scripted for both runs: it records its arguments and returns a place in the input's buffer) and the Store build's
callback block allocator.

These cases are the Store build's (its layouts and callees differ from the servers'; records/functions.tsv keeps
the server copies at compiles with the reason).
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX

from harness import HEAP
from syms import va

M = {}


def fake_pmem(mu):
    a = [mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)]
    M["m"].observed.append(("PMem_AllocFromSource_NoDebug", a[0], a[1], a[2] & 0xFFFFFFFF, a[3] & 0xFFFFFFFF))
    M["next"] += 0x100000
    return M["next"]


FAKES = {"?PMem_AllocFromSource_NoDebug@@YAPEAX_K0IW4PMem_Source@@@Z": fake_pmem}


def sizes(r):
    return [r.choice([0, 0, 1, 0xFFF, 0x1000, 0x1001, r.randrange(1 << 20), r.getrandbits(40)]) for _ in range(7)]


def inputs(seed, args, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        a = args(r)
        s = r.getrandbits(32)

        def setup(w, s=s):
            M["m"], M["next"] = w.m, 0x7000000000
            rr = random.Random(s)
            w.u64(va("unk_144427248"), rr.choice([0, 0x5F0000, rr.getrandbits(48)]))
            w.u64(va("unk_144427250"), rr.choice([0, 3, 0x1000, rr.getrandbits(20)]))
        out.append({"args": a, "setup": setup})
    return out


def zone_args(r, with_type):
    buf = struct.pack("<7Q", *sizes(r)) + bytes(8) + r.randbytes(0x70)   # blockSize[7], pad, XZoneMemory
    a = [buf, HEAP + 0x200, HEAP + 0x40]
    return a + [r.choice([0, 1, 2, 3])] if with_type else a


CASES = [
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DB_AllocXZoneMemoryInternal@@YAXQEA_KPEBDPEAUXZoneMemory@@I@Z", "ret": "void", "fakes": FAKES,
     "inputs": inputs(0x6A0, lambda r: zone_args(r, True))},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DB_AllocXZoneMemory@@YAXQEA_KPEBDPEAUXZoneMemory@@@Z", "ret": "void", "fakes": FAKES,
     "inputs": inputs(0x6A1, lambda r: zone_args(r, False))},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?sub_140369230@@YAPEAE_K0@Z", "ret": "int64", "fakes": FAKES,
     "inputs": inputs(0x6A2, lambda r: [r.choice([0, 1, 8, 0x100, r.getrandbits(20)]), r.choice([1, 2, 4, 8, 16, 0x1000, 3])])},
]
