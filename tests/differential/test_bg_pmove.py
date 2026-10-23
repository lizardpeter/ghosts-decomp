"""Differential cases for Pmove (bgame/bg_pmove.cpp), against the Store build and the PS4 server.

The playerState_s is a buffer of its own (a trailing argument Pmove doesn't take, so the harness compares it), with
pmove_t.ps pointing at it. Random state: cmd.serverTime against ps->commandTime (behind it, equal, 1..66 ms ahead, a
multiple of 66, up to and past 1000 ms ahead, across the int wrap), the buttons and pm_flags/linkFlags bits that
clear the command, the view height target and lerp state the pitch values depend on (prone 11, 22, standing 32,
crouch 40, lerp targets and directions, lerp times before, at and after the command time), the torso and waist
pitch (past +-180, NaN), and timeADSCameUp.

PmoveSingle is faked: it logs the step's cmd.serverTime and the whole oldcmd it is given, moves ps->commandTime to
cmd.serverTime as the real one does, sets weapCommon.fWeaponPosFrac to 1 or not by a script, and changes the command
(buttons, forwardmove) so that copying it to oldcmd is visible in the next step.
"""
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX

from harness import HEAP, _page
from win32_display import CURRENT

STORE = "iw6mp64_MSStore_ship"
PM_SIZE, PS_SIZE = 0x178, 0x620


class PmoveSingle:
    def __init__(self, r):
        self.frac = [r.choice([1.0, 1.0, 0.0, 0.5]) for _ in range(40)]
        self.i = 0

    def reset(self):
        self.i = 0

    def __call__(self, mu):
        m = CURRENT["m"]
        pm = mu.reg_read(UC_X86_REG_RCX)
        ps = struct.unpack("<Q", bytes(mu.mem_read(pm, 8)))[0]
        server_time = bytes(mu.mem_read(pm + 8, 4))
        m.observed.append(("call", "PmoveSingle", server_time, bytes(mu.mem_read(pm + 0x44, 0x3C)),
                           bytes(mu.mem_read(pm + 0x84, 4))))
        mu.mem_write(ps, server_time)
        mu.mem_write(ps + 0x424, struct.pack("<f", self.frac[self.i % len(self.frac)]))
        buttons = struct.unpack("<I", bytes(mu.mem_read(pm + 0xC, 4)))[0]
        mu.mem_write(pm + 0xC, struct.pack("<I", buttons ^ (1 << (self.i % 32))))
        mu.mem_write(pm + 0x24, bytes([self.i & 0xFF]))
        self.i += 1
        return None


def _input(r):
    ps = bytearray(PS_SIZE)
    command_time = r.choice([0, 1000, 0x7FFFFF00, -5000, r.getrandbits(31)])
    delta = r.choice([-1, -66, 0, 0, 1, 8, 16, 65, 66, 67, 132, 200, 999, 1000, 1001, 1066, 5000, r.randint(0, 1100)])
    final = (command_time + delta) & 0xFFFFFFFF
    flags = r.choice([0, 0, 0x80000, 0x800, r.getrandbits(32)])
    struct.pack_into("<IiiI", ps, 0, command_time & 0xFFFFFFFF, 0, 0, flags)
    struct.pack_into("<i", ps, 0x14, r.choice([0, 0, 4, 5, r.getrandbits(31)]))
    struct.pack_into("<i", ps, 0x150, r.choice([0, 0, 1234, command_time & 0x7FFFFFFF]))
    target = r.choice([11, 11, 22, 32, 40, 60, 0])
    lerp_time = r.choice([0, 0, (command_time + r.choice([-500, -401, -200, -100, 0, 100])) & 0xFFFFFFFF])
    struct.pack_into("<iiIii", ps, 0x190, target, 0, lerp_time, r.choice([11, 40, 22, 0]), r.choice([0, 1]))
    struct.pack_into("<f", ps, 0x424, r.choice([0.0, 1.0]))
    pm = bytearray(r.getrandbits(8) for _ in range(PM_SIZE))
    struct.pack_into("<Q", pm, 0, HEAP + _page(PM_SIZE + 16))
    struct.pack_into("<I", pm, 8, final)
    struct.pack_into("<I", pm, 0xC, r.choice([0, 0x100000, 0x400, r.getrandbits(32)]))
    struct.pack_into("<2f", pm, 0x160, r.choice([0.0, 30.0, -45.5, 180.0, 181.0, -540.25, 1e9, float("nan")]),
                     r.choice([0.0, 12.0, -179.9, 359.0, r.uniform(-1000, 1000)]))
    single = PmoveSingle(r)

    def setup(w):
        CURRENT["m"] = w.m
        single.reset()
    return {"args": [bytes(pm), bytes(ps)], "setup": setup, "fakes": {"?PmoveSingle@@YAXPEAUpmove_t@@@Z": single}}


r = random.Random(7111)
CASES = [{"symbol": "?Pmove@@YAXPEAUpmove_t@@@Z", "ret": "void", "inputs": [_input(r) for _ in range(1500)]}]
