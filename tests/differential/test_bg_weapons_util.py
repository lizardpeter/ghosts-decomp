"""Differential cases for bgame/bg_weapons_util.cpp: BG_KickAngles (both builds) and the two view-kick center
speeds (the PS4 server; the Store build inlines them into BG_KickAngles, so they are tested there through it).

BG_KickAngles: random msec (0, negative, 1 to 6 ms, frame times, the bots' 50, large), random kick velocities and
angles (zero, near the 10 degree cap, opposite signs, NaN), a random playerState (weapon, alternate flag, ADS
fraction around 0.5, the fast-snipe perk bit) and weapon tables in scratch memory: the viewmodel weapon's and its
alternate's WeaponCompleteDef (altWeapon, center speeds) and WeaponDef (oldWeapon, or no WeaponDef), attachments
with view-center scales and view-kick overrides, an overlay with or without a reticle and perk_fastSnipeScale. The
weapon helpers are faked and their arguments compared."""
import random
import struct

from unicorn.x86_const import UC_X86_REG_R8

from syms import va

PS4 = "iw6_ds_ps4"
COMPLETE = 0x510000  # scratch WeaponCompleteDefs, 0x1000 apart
WEAPDEF = 0x520000   # scratch WeaponDefs, 0x1000 apart
OVERLAY = 0x530000
ATTACH = 0x531000    # four WeaponAttachments, 0x200 apart
VIEWKICK = 0x532000  # four AttViewKicks, 0x40 apart
F_NAMES = {
    "weapon": "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z",
    "alt": "?BG_UsingAlternate@@YA_NPEBUplayerState_s@@@Z",
    "overlay": "?BG_GetOverlay@@YAPEBUADSOverlay@@TWeapon@@_N@Z",
    "attachments": "?BG_GetWeaponAttachments@@YAXTWeapon@@_NQEAPEBUWeaponAttachment@@@Z",
}
OBSERVE = {F_NAMES["weapon"]: "q", F_NAMES["alt"]: "q", F_NAMES["overlay"]: "ib", F_NAMES["attachments"]: "ib"}


def _f(r, scale=1.0):
    return r.choice([0.0, 0.0, -0.0, 1.0, -1.0, 9.99, -9.99, 10.0, 10.5, -12.0, float("nan"),
                     r.uniform(-1, 1) * scale, r.uniform(-10, 10) * scale, r.uniform(-300, 300) * scale])


def _speed(r):
    return r.choice([0.0, 2400.0, 1800.0, 600.0, 50.0, -100.0, float("nan"), r.uniform(0, 4000)])


def _tables(r, index, alt_index):
    """Weapon table entries for the viewmodel weapon and its alternate, written by the setup."""
    defs = []
    for slot, idx in enumerate((index, alt_index)):
        complete = bytearray(0x100)
        struct.pack_into("<ff", complete, 0xB4, _speed(r), _speed(r))
        alt = r.choice([0, 0, alt_index, alt_index | 0x4500, 0x300])
        struct.pack_into("<I", complete, 0xC8, alt)
        weapdef = bytearray(0xB00)
        weapdef[0xA88] = r.choice([0, 0, 1])
        defs.append((idx, slot, bytes(complete), bytes(weapdef), r.random() < 0.15))
    return defs


def _write_tables(w, defs):
    for idx, slot, complete, weapdef, no_def in defs:
        w.m.mu.mem_write(COMPLETE + slot * 0x1000, complete)
        w.m.mu.mem_write(WEAPDEF + slot * 0x1000, weapdef)
        w.u64(va("bg_weaponCompleteDefs") + 8 * idx, COMPLETE + slot * 0x1000)
        w.u64(va("bg_weaponDefs") + 8 * idx, 0 if no_def else WEAPDEF + slot * 0x1000)


def _attachments(r):
    present = [r.random() < 0.5 for _ in range(4)]
    scales = [r.choice([0.0, 0.0, 1.0, 0.5, 2.0, -1.0, float("nan"), r.uniform(0, 3)]) for _ in range(4)]
    kicks = [r.random() < 0.3 for _ in range(4)]
    speeds = [(_speed(r), _speed(r)) for _ in range(4)]

    def write(mu):
        out = mu.reg_read(UC_X86_REG_R8)
        for i in range(4):
            att = ATTACH + 0x200 * i
            kick = VIEWKICK + 0x40 * i
            mu.mem_write(kick + 0x14, struct.pack("<f", speeds[i][0]))
            mu.mem_write(kick + 0x2C, struct.pack("<f", speeds[i][1]))
            mu.mem_write(att + 0xB8, struct.pack("<Q", kick if kicks[i] else 0))
            mu.mem_write(att + 0x10C, struct.pack("<f", scales[i]))
            mu.mem_write(out + 8 * i, struct.pack("<Q", att if present[i] else 0))
    return write


def _kick(r):
    index = r.choice([0, 0x11, 0x2A, 0xFE])
    alt_index = r.choice([0x12, 0x33])
    weapon = index | (r.getrandbits(24) << 8 if r.random() < 0.5 else 0)
    ps = bytearray(0x1000)
    struct.pack_into("<IIf", ps, 0x41C, r.getrandbits(32), r.choice([0, 0x4000, r.getrandbits(32)]),
                     r.choice([0.0, 0.0, 1.0, 0.5, 0.50001, 0.4999, 0.25, float("nan"), r.random()]))
    struct.pack_into("<I", ps, 0xE18, r.choice([0, 0x200, r.getrandbits(32)]))
    msec = r.choice([0, -5, 1, 2, 3, 4, 5, 6, 7, 9, 10, 16, 17, 33, 50, 100, r.randint(-100, 300)])
    vel = struct.pack("<3f", *(_f(r, 100) for _ in range(3)))
    ang = struct.pack("<3f", *(_f(r) for _ in range(3)))
    defs = _tables(r, index, alt_index)
    reticle = r.choice([0, 0, 1, 2])
    perk = r.choice([1.0, 0.5, 2.0, 0.0])
    using_alt = r.choice([0, 1])

    def setup(w):
        _write_tables(w, defs)
        w.m.mu.mem_write(OVERLAY + 0x20, struct.pack("<I", reticle))
        d = w.alloc(bytes(0x60))
        w.write(d + 0x10, struct.pack("<f", perk))
        w.u64(va("perk_fastSnipeScale"), d)

    fakes = {
        F_NAMES["weapon"]: lambda mu: weapon,
        F_NAMES["alt"]: lambda mu: 0xA5C300 | using_alt,  # only the low byte is the bool
        F_NAMES["overlay"]: lambda mu: OVERLAY,
        F_NAMES["attachments"]: _attachments(r),
    }
    return {"args": [bytes(ps), msec, vel, ang], "setup": setup, "fakes": fakes}


def _center_speed(r):
    index = r.choice([0, 0x11, 0x2A])
    alt_index = r.choice([0x12, 0x33])
    defs = _tables(r, index, alt_index)
    weapon = index | (r.getrandbits(24) << 8 if r.random() < 0.5 else 0)
    return {"args": [weapon, r.choice([0, 1])], "setup": lambda w: _write_tables(w, defs),
            "fakes": {F_NAMES["attachments"]: _attachments(r)}}


CASES = [
    {"symbol": "?BG_KickAngles@@YAXPEBUplayerState_s@@HQEAM1@Z", "ret": "void", "observe": OBSERVE,
     "inputs": [_kick(r) for r in [random.Random(1318)] for _ in range(1500)]},
    {"symbol": "?BG_HipViewKickCenterSpeed@@YAMTWeapon@@_N@Z", "build": PS4, "ret": "float",
     "observe": {F_NAMES["attachments"]: "ib"},
     "inputs": [_center_speed(r) for r in [random.Random(5609)] for _ in range(600)]},
    {"symbol": "?BG_AdsViewKickCenterSpeed@@YAMTWeapon@@_N@Z", "build": PS4, "ret": "float",
     "observe": {F_NAMES["attachments"]: "ib"},
     "inputs": [_center_speed(r) for r in [random.Random(5641)] for _ in range(600)]},
]
