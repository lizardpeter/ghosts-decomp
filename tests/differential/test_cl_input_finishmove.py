"""Differential cases for CL_FinishMove (client_mp/cl_input.cpp, Store build): the last step of every usercmd.

Random client state: cl->serverTime (near the int limits too), the cgame's weapon, offhand and alternate flag, the
view angles and kick angles (fractions of a short step, negative, past 360, huge, NaN and infinity), the extra
buttons, and the profile's gamepad flag. The command passed in has random contents, so the buttons that are kept,
set and cleared are visible. CL_ControllerIndexFromClientNum and GamerProfile_GetProfileSettings are faked and
observed, and the empty sub_1402891D0 is observed for its argument.
"""
import random
import struct

STORE = "iw6mp64_MSStore_ship"
SETTINGS = 0x5F0000  # scratch GamerSettingState: gpadEnabled at +0x2BC
CL_SERVERTIME, CL_USERCMD_WEAPON, CL_KICK, CL_EXTRA, CL_VIEWANGLES = 0x34D0, 0x355C, 0x3574, 0x3608, 0x3610

SYM = {
    "settings": "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z",
    "ctrl": "?CL_ControllerIndexFromClientNum@@YAHW4LocalClientNum_t@@@Z",
    "offhand": "?sub_1402891D0@@YAXI@Z",
}
OBSERVE = {SYM["settings"]: "i", SYM["ctrl"]: "i", SYM["offhand"]: "i"}


def _angle(r):
    return r.choice([0.0, -0.0, 0.002, 0.00274, -0.00275, 90.0, 180.0, 359.997, 360.0, -45.0, 720.5, 1e7, -3e9,
                     float("inf"), float("-inf"), float("nan"), r.uniform(-400, 400), r.uniform(-1, 1),
                     r.uniform(0, 360)])


def _kick(r):
    return r.choice([0.0, 0.0, 0.0, 1.5, -2.25, 0.001, r.uniform(-10, 10)])


def _input(r):
    server_time = r.choice([0, 1, 1000, 0x7FFFFFFF, -1, -0x80000000, r.getrandbits(32)])
    weapon = r.choice([0, 1, 0x1234, r.getrandbits(32)])
    offhand = r.choice([0, 3, r.getrandbits(32)])
    alternate = r.choice([0, 0, 1, -1, r.getrandbits(32)])
    angles = [_angle(r) for _ in range(3)]
    kick = [_kick(r) for _ in range(3)]
    extra = r.choice([0, 0, 0x400000, 0x40000000, 1, r.getrandbits(32)])
    gpad = r.choice([0, 0, 1, 0xFF])
    ctrl = r.choice([0, 0, 1, 3])
    cmd = bytes(r.getrandbits(8) for _ in range(0x3C))

    def setup(w):
        from syms import va
        cl = va("clients")
        w.write(cl + CL_SERVERTIME, struct.pack("<I", server_time & 0xFFFFFFFF))
        w.write(cl + CL_USERCMD_WEAPON, struct.pack("<IIi", weapon, offhand, alternate - (1 << 32) if alternate >= 1 << 31 else alternate))
        w.write(cl + CL_KICK, struct.pack("<3f", *kick))
        w.write(cl + CL_EXTRA, struct.pack("<I", extra))
        w.write(cl + CL_VIEWANGLES, struct.pack("<3f", *angles))
        w.m.mu.mem_write(SETTINGS + 0x2BC, bytes([gpad]))

    fakes = {SYM["settings"]: lambda mu: SETTINGS, SYM["ctrl"]: (lambda v: lambda mu: v)(ctrl),
             SYM["offhand"]: lambda mu: None}
    return {"args": [r.choice([0, 0, 0, 1]), cmd], "setup": setup, "fakes": fakes}


r = random.Random(2435)
CASES = [
    {"symbol": "?CL_FinishMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z", "build": STORE, "ret": "void",
     "observe": OBSERVE, "inputs": [_input(r) for _ in range(1500)]},
]
