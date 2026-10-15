"""Differential cases for the gamepad half of client_mp/cl_input.cpp (and CL_GamepadAxisValue in client/cl_gamepad.cpp)
against the Store build.

CL_GamepadMove: random client state (usingAds, pm_flags, eFlags, weapon and weapFlags, view angles, yaw/pitch speed
caps, cls.frametime), random KB_SPEED/KB_BACK/KB_SPRINT buttons, the profile's gpadEnabled and invertedPitch, and a
random usercmd. The engine around it is faked and its arguments compared: the stick axes (CL_GamepadAxisValue
returns made-up floats per axis, including 0, +-1, out of range and NaN), BG_WeaponDef (meleeOnly), GPad_GetButton,
CG_HandleSpecialStateInput (adds button bits), CG_ShouldUpdateViewAngles, the prone yaw scaling, aim assist (whole
AimInput checked, a made-up AimOutput returned), the airburst distance.

CL_GamepadAxisValue: random gaGlobs (axis values, virtual axis bindings and mappings) and virtual axis.
"""
import math
import random
import struct

from unicorn.x86_const import (UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_XMM0,
                               UC_X86_REG_XMM1)

from syms import static, va

STORE = "iw6mp64_MSStore_ship"
SETTINGS = 0x5E0000   # scratch GamerSettingState (invertedPitch +0x44, gpadEnabled +0x2BC)
WEAPONDEF = 0x5F0000  # scratch WeaponDef (meleeOnly +0xA56)
KB_SIZE, KB_BACK, KB_SPEED, KB_SPRINT = 0x14, 3, 9, 29
CL_FOVSCALE, CL_VIEWANGLES = 0x3568, 0x3610
PS = 0x8  # clients[0].snap.ps


def _xmm0(mu, x):
    mu.reg_write(UC_X86_REG_XMM0, struct.unpack("<I", struct.pack("<f", x))[0])


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def _axis_value(r):
    return r.choice([0.0, 0.0, 1.0, -1.0, 0.5, -0.25, 1e-6, -1e-6, 0.8, 0.79999995, 2.5, -3.0, float("nan"),
                     r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1)])


def _state(r):
    using_ads = r.random() < 0.5
    pm_flags = r.choice([0, 0, 0, 0, 0x800, 0x801, 0x4])
    eflags = r.choice([0, 0, 0x200000, 0x200000, 0xFFFFFFFF, 0x1FFFFF])
    weapon = r.getrandbits(32)
    weap_flags = r.choice([0, 0x4000, r.getrandbits(32)])
    angles = [r.uniform(-400, 400) for _ in range(3)]
    view_delta = [r.uniform(-5, 5) for _ in range(3)]
    caps = [r.choice([0.0, 90.0, 0.5, -1.0]) for _ in range(2)]
    frametime = r.choice([0, 7, 16, 33, r.randint(-100, 100000)])
    kb = {i: (r.random() < 0.5, r.random() < 0.5) for i in (KB_BACK, KB_SPEED, KB_SPRINT)}
    gpad = r.random() < 0.9
    inverted = r.random() < 0.5
    melee_only = r.random() < 0.3

    def setup(w):
        cl = va("clients")
        w.write(cl, bytes([using_ads]))
        w.u32(cl + PS + 0xC, pm_flags)
        w.u32(cl + PS + 0x124, eflags)
        w.write(cl + PS + 0x41C, struct.pack("<II", weapon, weap_flags))
        w.write(cl + CL_FOVSCALE + 4, struct.pack("<2f", *caps))
        w.write(cl + CL_VIEWANGLES, struct.pack("<6f", *angles, *view_delta))
        w.u32(va("cls") + 0x118, frametime)
        kbs = static("client_mp/cl_input.cpp", "playersKb")
        for i, (active, pressed) in kb.items():
            w.write(kbs + i * KB_SIZE + 0x10, bytes([active, pressed]))
        w.m.mu.mem_write(SETTINGS + 0x44, bytes([inverted]))
        w.m.mu.mem_write(SETTINGS + 0x2BC, bytes([gpad]))
        w.m.mu.mem_write(WEAPONDEF + 0xA56, bytes([melee_only]))
    return setup


def _record(*item):
    _record.machine.observed.append(item)


def _fakes(r):
    axes = [_axis_value(r) for _ in range(6)]
    buttons = {0x20000001: _axis_value(r), 0x20000000: _axis_value(r), 0x10002000: _axis_value(r)}
    controller = r.choice([0, 0, 1, 3])
    extra_buttons = r.choice([0, 0, 0x1, 0x2, 0x800, r.getrandbits(32)])
    should_update = r.random() < 0.7
    yaw_scale = r.choice([1.0, 0.0, 0.5, -2.0])
    airburst = r.random() < 0.4
    distance = r.getrandbits(32)

    def axis(mu):
        _xmm0(mu, axes[mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF])

    def button(mu):
        _xmm0(mu, buttons.get(mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF, 0.0))

    def special_state(mu):
        p = mu.reg_read(UC_X86_REG_RDX)
        v = struct.unpack("<I", bytes(mu.mem_read(p, 4)))[0]
        mu.mem_write(p, struct.pack("<I", v | extra_buttons))

    def prone_yaw(mu):
        _xmm0(mu, _f32(mu.reg_read(UC_X86_REG_XMM1)) * yaw_scale)

    def aim_assist(mu):
        inp = bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 0x33))  # 0x33 is padding
        _record("AimInput", inp)
        pitch, yaw = struct.unpack_from("<f", inp, 8)[0], struct.unpack_from("<f", inp, 0x14)[0]
        axes_sum = sum(struct.unpack_from("<f", inp, o)[0] for o in (0xC, 0x18))
        mu.mem_write(mu.reg_read(UC_X86_REG_RDX), struct.pack("<ffHB", pitch + 1.0, yaw - 2.0 + axes_sum,
                                                              *struct.unpack_from("<HB", inp, 0x30)) + b"\0")

    def melee_to_cmd(mu):
        out = bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 0xB))  # 0xB is padding
        _record("AimOutput", out, mu.reg_read(UC_X86_REG_RDX))

    def airburst_distance(mu):
        if airburst:
            mu.mem_write(mu.reg_read(UC_X86_REG_R9), struct.pack("<I", distance))
        return int(airburst)

    return {
        "?CL_GetFirstActiveControllerIndex@@YAHXZ": lambda mu: controller,
        "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": lambda mu: SETTINGS,
        "?CL_GamepadAxisValue@@YAMW4LocalClientNum_t@@W4GamepadVirtualAxis@@@Z": axis,
        "?BG_WeaponDef@@YAPEBUWeaponDef@@TWeapon@@_N@Z": lambda mu: WEAPONDEF,
        "?GPad_GetButton@@YAMHW4GamePadButton@@@Z": button,
        "?CG_HandleSpecialStateInput@@YAXW4LocalClientNum_t@@PEAI@Z": special_state,
        "?CG_ShouldUpdateViewAngles@@YA_NW4LocalClientNum_t@@@Z": lambda mu: int(should_update),
        "?sub_140263E10@@YAMPEBUplayerState_s@@M@Z": prone_yaw,
        "?AimAssist_UpdateGamePadInput@@YAXPEBUAimInput@@PEAUAimOutput@@@Z": aim_assist,
        "?sub_14027B800@@YAXPEBUAimOutput@@PEAUusercmd_s@@@Z": melee_to_cmd,
        "?sub_1402F7090@@YAHW4LocalClientNum_t@@PEBUplayerState_s@@IPEAH@Z": airburst_distance,
    }


OBSERVE = {
    "?CL_GetFirstActiveControllerIndex@@YAHXZ": "",
    "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": "i",
    "?CL_GamepadAxisValue@@YAMW4LocalClientNum_t@@W4GamepadVirtualAxis@@@Z": "ii",
    "?BG_WeaponDef@@YAPEBUWeaponDef@@TWeapon@@_N@Z": "ib",
    "?GPad_GetButton@@YAMHW4GamePadButton@@@Z": "ii",
    "?CG_HandleSpecialStateInput@@YAXW4LocalClientNum_t@@PEAI@Z": "iq",
    "?CG_ShouldUpdateViewAngles@@YA_NW4LocalClientNum_t@@@Z": "i",
    "?sub_140263E10@@YAMPEBUplayerState_s@@M@Z": "qf",
    "?sub_1402F7090@@YAHW4LocalClientNum_t@@PEBUplayerState_s@@IPEAH@Z": "iqi",
}


def _usercmd(r):
    cmd = bytearray(r.getrandbits(8) for _ in range(0x3C))
    if r.random() < 0.6:
        cmd[0x1C] = r.choice([0, 0, 127, 128, 129, 120, 5])
        cmd[0x1D] = r.choice([0, 0, 127, 128, 129, 136, 250])
    if r.random() < 0.5:
        cmd[4:8] = struct.pack("<I", r.choice([0, 1, 2, 4, 0x800, 0x2000]))
    return bytes(cmd)


def _gamepad_move(r):
    state, fakes = _state(r), _fakes(r)

    def setup(w):
        _record.machine = w.m
        state(w)
    args = [0, ("f", r.choice([0.0, 0.016, 0.033, r.uniform(0, 1)])), _usercmd(r)]
    return {"args": args, "setup": setup, "fakes": fakes}


def _axis_input(r):
    values = [r.choice([0, 0, 1, -1, 32767, -32768, 65535, -65535, 16000, r.randint(-32768, 32767),
                        r.randint(-2 ** 31, 2 ** 31 - 1)]) for _ in range(6)]
    mapping = [(r.choice([-1, -1, 0, 1, 2, 3, 4, 5]), r.choice([0, 1, 1, -1, 2])) for _ in range(6)]

    def setup(w):
        w.write(static("client/cl_gamepad.cpp", "gaGlobs"),
                struct.pack("<6i", *values) + b"".join(struct.pack("<ii", *m) for m in mapping))
    return {"args": [0, r.randint(0, 5)], "setup": setup}


def _pitch_sign(r):
    inverted, controller = r.random() < 0.5, r.choice([0, 1, 3])

    def setup(w):
        w.m.mu.mem_write(SETTINGS + 0x44, bytes([inverted]))
    return {"args": [0], "setup": setup,
            "fakes": {"?CL_GetFirstActiveControllerIndex@@YAHXZ": lambda mu: controller,
                      "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": lambda mu: SETTINGS}}


def inputs(seed, make, n):
    r = random.Random(seed)
    return [make(r) for _ in range(n)]


CASES = [
    {"symbol": "?CL_GamepadMove@@YAXW4LocalClientNum_t@@MPEAUusercmd_s@@@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE, "inputs": inputs(1804, _gamepad_move, 2500)},
    {"symbol": "?sub_14030D390@@YAMW4LocalClientNum_t@@@Z", "build": STORE, "ret": "float", "observe": OBSERVE,
     "inputs": inputs(1390, _pitch_sign, 100)},
    {"symbol": "?CL_GamepadAxisValue@@YAMW4LocalClientNum_t@@W4GamepadVirtualAxis@@@Z", "build": STORE,
     "ret": "float", "inputs": inputs(706, _axis_input, 1500)},
]
