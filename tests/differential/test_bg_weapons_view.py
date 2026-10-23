"""Differential cases for bgame/bg_weapons_view.cpp (both builds): the viewmodel's recoil.

BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle: random angle and speed (inside and outside the settle box
of 0.25 degrees and 1 degree per second, past the angle limit, NaN), step lengths around 5 ms and gun kick values
(typical accelerations, speed limits and decays, zero and negative ones).

BG_CalculateWeaponMovement_Recoil: a weaponState_t whose playerState lives in scratch memory (alternate flag, ADS
fraction), random frame times around the 5 ms step (0, negative, 1 to 100 ms, NaN), recoil angles and speeds, the
weapon tables for the alternate-mode lookup and fGunMaxPitch/Yaw, and fakes for the viewmodel weapon, the gun kick
values (eight outputs, two of them on the stack) and BG_IsAimDownSight, whose arguments are compared."""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP

from syms import va

COMPLETE = 0x510000
WEAPDEF = 0x520000
PS = 0x530000


def _angle(r):
    return r.choice([0.0, -0.0, 0.1, -0.24, 0.25, -0.26, 1.0, -3.0, 5.9, 6.0, 6.1, -6.5, 12.0, float("nan"),
                     r.uniform(-1, 1), r.uniform(-8, 8)])


def _speed(r):
    return r.choice([0.0, 0.5, -0.99, 1.0, -1.0, 30.0, -60.0, 400.0, 2000.0, 2500.0, -2500.0, float("nan"),
                     r.uniform(-5, 5), r.uniform(-3000, 3000)])


def _dt(r):
    return r.choice([0.005, 0.005, 0.001, 0.002, 0.003, 0.004, 0.0049999, 0.0050001, 0.0, -0.001, 0.016,
                     float("nan"), r.uniform(0, 0.006)])


def _kick_values(r):
    return [r.choice([1000.0, 800.0, 0.0, -50.0, r.uniform(0, 3000)]),    # accel
            r.choice([2000.0, 50.0, 0.0, -10.0, r.uniform(0, 3000)]),     # speed max
            r.choice([24.0, 16.0, 0.0, 300.0, r.uniform(0, 60)]),         # speed decay
            r.choice([40.0, 20.0, 0.0, -5.0, r.uniform(0, 100)])]         # static decay


def _single(r):
    return [struct.pack("<f", _angle(r)), struct.pack("<f", _speed(r)), ("f", _dt(r)),
            ("f", r.choice([6.0, 3.0, 0.0, -1.0, 15.0, float("nan")]))] + [("f", v) for v in _kick_values(r)]


GUN_KICK = "?BG_GetGunKickSpeed@@YAXTWeapon@@_NPEAM2222222@Z"
WEAPON = "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z"
ADS = "?BG_IsAimDownSight@@YA_NTWeapon@@_N@Z"


def _recoil(r):
    index = r.choice([0, 0x11, 0x2A])
    alt_index = r.choice([0x12, 0x33])
    weapon = index | (r.getrandbits(24) << 8 if r.random() < 0.5 else 0)
    flags = r.choice([0, 0x4000, r.getrandbits(32)])
    frac = r.choice([0.0, 1.0, 0.5, float("nan"), r.random()])
    null_ps = r.random() < 0.03
    ws = bytearray(0x90)
    struct.pack_into("<Q", ws, 0, 0 if null_ps else PS)
    struct.pack_into("<f", ws, 0xC, r.choice([0.0, -0.001, 0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007,
                                              0.0099, 0.01, 0.016, 0.0167, 0.033, 0.1, float("nan"),
                                              r.uniform(0, 0.05)]))
    struct.pack_into("<6f", ws, 0x3C, *(_angle(r) for _ in range(3)), *(_speed(r) for _ in range(3)))
    hip, ads = _kick_values(r), _kick_values(r)
    aims = r.random() < 0.85
    tables = []
    for slot, idx in enumerate((index, alt_index)):
        complete = bytearray(0x100)
        struct.pack_into("<I", complete, 0xC8, r.choice([0, 0, alt_index, alt_index | 0x4500, 0x300]))
        weapdef = bytearray(0xB00)
        struct.pack_into("<ff", weapdef, 0x640, r.choice([6.0, 3.0, 15.0, 0.0]), r.choice([4.0, 8.0, 0.0]))
        weapdef[0xA88] = r.choice([0, 0, 1])
        tables.append((idx, slot, bytes(complete), bytes(weapdef)))

    def setup(w):
        w.m.mu.mem_write(PS + 0x420, struct.pack("<If", flags, frac))
        for idx, slot, complete, weapdef in tables:
            w.m.mu.mem_write(COMPLETE + slot * 0x1000, complete)
            w.m.mu.mem_write(WEAPDEF + slot * 0x1000, weapdef)
            w.u64(va("bg_weaponCompleteDefs") + 8 * idx, COMPLETE + slot * 0x1000)
            w.u64(va("bg_weaponDefs") + 8 * idx, WEAPDEF + slot * 0x1000)

    def gun_kick(mu):
        rsp = mu.reg_read(UC_X86_REG_RSP)
        outs = [mu.reg_read(UC_X86_REG_R8), mu.reg_read(UC_X86_REG_R9)]
        outs += [struct.unpack("<Q", bytes(mu.mem_read(rsp + 0x28 + 8 * i, 8)))[0] for i in range(6)]
        for p, v in zip(outs, hip + ads):
            mu.mem_write(p, struct.pack("<f", v))

    fakes = {WEAPON: lambda mu: weapon, GUN_KICK: gun_kick, ADS: lambda mu: 0xA5C300 | aims}
    return {"args": [bytes(ws)], "setup": setup, "fakes": fakes}


CASES = [
    {"symbol": "?BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle@@YAHPEAM0MMMMMM@Z", "ret": "int",
     "inputs": [_single(r) for r in [random.Random(766)] for _ in range(3000)]},
    {"symbol": "?BG_CalculateWeaponMovement_Recoil@@YAXPEAUweaponState_t@@@Z", "ret": "void",
     "observe": {WEAPON: "q", GUN_KICK: "ib", ADS: "ib"},
     "inputs": [_recoil(r) for r in [random.Random(831)] for _ in range(2000)]},
]
