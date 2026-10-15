"""Differential cases for CL_KeyMove and CL_CmdButtons (client_mp/cl_input.cpp) against the Store build.

Random button state (all 35 kbuttons of local client 0, timed for CL_KeyState), frame_msec, com_frameTime, the stance
state (held, stance, position, time held, sprinting), usingAds, the playerState fields the two read (pm_type, both
hands' weaponState, weapon, weapFlags, lastWeaponHand, the clip ammo table), key catchers, connection state,
cl_bypassMouseInput and the profile's gpadEnabled. The weapon helpers, the UI and the cgame are faked and their
arguments compared.
"""
import random
import struct

from syms import static, va

STORE = "iw6mp64_MSStore_ship"
KB_SIZE, NUM_BUTTONS = 0x14, 35
SETTINGS = 0x500E00  # scratch GamerSettingState (gpadEnabled at +0x2BC)
WEAPDEF = 0x540000   # scratch WeaponDef (meleeOnly at +0xA56)
PS = 0x8             # clients[0].snap.ps
CL_STANCE = 0x3548   # stanceHeld, stance, stancePosition, stanceTime, wasSprinting
CLIPS = [0x1111, 0x2222, 0x3333, 0x0, 0xFFFFFFFF00000001]


def _kbutton(r):
    keys = [r.choice([0, 0, 0, 5, 9, 200, -1, r.randint(0, 255)]) for _ in range(2)]
    downtime = r.choice([0, 0, 100, 5000, r.getrandbits(32)])
    msec = r.choice([0, 0, 3, 16, 33, 100, 40, r.getrandbits(32)])
    return struct.pack("<iiIIBBxx", *keys, downtime, msec, r.random() < 0.45, r.random() < 0.35)


def _state(r):
    kb = bytearray(b"".join(_kbutton(r) for _ in range(NUM_BUTTONS)))
    frame_msec = r.choice([0, 1, 16, 16, 33, 100])
    frame_time = r.choice([0, 100, 5000, 100000, r.getrandbits(31), r.getrandbits(32)])
    held = r.choice([0, 1, 1])
    stance = r.choice([0, 1, 2, 3, 3, 4])
    position = r.choice([0, 1, 2])
    since = r.choice([0, 100, 199, 200, 201, 299, 300, 301, 5000, -50, r.getrandbits(32)])
    sprinting = r.choice([0, 1])
    using_ads = r.choice([0, 1])
    pm_type = r.choice([0, 1, 2, 3, 4, 5, 6, 7])
    weap_states = [r.choice([0, 6, 6, 8]) for _ in range(2)]
    weapon = r.getrandbits(32)
    weap_flags = r.getrandbits(32) & r.choice([0, 0x1, 0x4000, 0x4001, 0xFFFFFFFF])
    last_hand = r.choice([0, 1, 1])
    clips = b"".join(struct.pack("<Qii", r.choice(CLIPS), r.choice([0, 3, -1]), r.choice([0, 0, 5, -1]))
                     for _ in range(15))
    melee_only = r.choice([0, 1])
    catchers = r.choice([0, 0, 0x10, 0x40, 0x1, 0x80000000])
    connstate = r.choice([0, 5, 6, 9, 10, 10])
    bypass = r.choice([0, 0, 1])
    gpad = r.random() < 0.3

    def setup(w):
        w.write(static("client_mp/cl_input.cpp", "playersKb"), bytes(kb))
        w.u32(va("frame_msec"), frame_msec)
        w.u32(va("com_frameTime"), frame_time)
        cl = va("clients")
        w.write(cl, bytes([using_ads]))
        w.write(cl + CL_STANCE, struct.pack("<BxxxiiIB", held, stance, position,
                                            (frame_time - since) & 0xFFFFFFFF, sprinting))
        w.u32(cl + PS + 0x4, pm_type)
        w.u32(cl + PS + 0x2AC + 0x10, weap_states[0])
        w.u32(cl + PS + 0x2C8 + 0x10, weap_states[1])
        w.write(cl + PS + 0x41C, struct.pack("<II", weapon, weap_flags))
        w.u32(cl + PS + 0x43C, last_hand)
        w.write(cl + PS + 0x530, clips)
        ui = va("clientUIActives")
        w.u32(ui + 0x4, catchers)
        w.u32(ui + 0x8, connstate)
        d = w.alloc(bytes(0x60))
        w.write(d + 0x10, bytes([bypass]))
        w.u64(va("cl_bypassMouseInput"), d)
        w.m.mu.mem_write(SETTINGS + 0x2BC, bytes([gpad]))
        w.m.mu.mem_write(WEAPDEF + 0xA56, bytes([melee_only]))
    return setup


def _ret(value):
    return lambda mu: value


OBSERVE = {
    "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": "i",
    "?UI_GetActiveMenu@@YA?AW4uiMenuCommand_t@@W4LocalClientNum_t@@@Z": "i",
    "?BG_WeaponDef@@YAPEBUWeaponDef@@TWeapon@@_N@Z": "ib",
    "?BG_ClipForWeapon@@YA_KTWeapon@@_N@Z": "ib",
    "?BG_ShotLimitReached@@YAHPEBUplayerState_s@@TWeapon@@W4PlayerHandIndex@@@Z": "qii",
    "?CG_HandleSpecialStateInput@@YAXW4LocalClientNum_t@@PEAI@Z": "iq",
}


def _usercmd(r):
    cmd = bytearray(r.getrandbits(8) for _ in range(0x3C))
    if r.random() < 0.4:
        cmd[4:8] = struct.pack("<I", r.choice([0, 0xFFFFFFFF, 1, 0x20000000]))
    return bytes(cmd)


def inputs(seed, n):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        fakes = {
            "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": _ret(SETTINGS),
            "?UI_GetActiveMenu@@YA?AW4uiMenuCommand_t@@W4LocalClientNum_t@@@Z": _ret(r.choice([0, 6, 2])),
            "?BG_WeaponDef@@YAPEBUWeaponDef@@TWeapon@@_N@Z": _ret(WEAPDEF),
            "?BG_ClipForWeapon@@YA_KTWeapon@@_N@Z": _ret(r.choice(CLIPS + [0x4444])),
            "?BG_ShotLimitReached@@YAHPEBUplayerState_s@@TWeapon@@W4PlayerHandIndex@@@Z": _ret(r.choice([0, 1])),
            "?CG_HandleSpecialStateInput@@YAXW4LocalClientNum_t@@PEAI@Z": _ret(None),
        }
        out.append({"args": [0, _usercmd(r)], "setup": _state(r), "fakes": fakes})
    return out


CASES = [
    {"symbol": "?CL_KeyMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE, "inputs": inputs(1589, 3000)},
    {"symbol": "?CL_CmdButtons@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE, "inputs": inputs(2337, 1500)},
]
