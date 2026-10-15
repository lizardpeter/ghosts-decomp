"""Differential cases for CL_CreateCmd and its two whole-command handlers (client_mp/cl_input.cpp, Store build).

Random client state (all 35 kbuttons, view angles, yaw/pitch caps, pm_type and pm_flags, stance, mouse
accumulators), cgame state (locationSelectionInfo, frametime, map size, selected location, direction and direction
cursor, sighted clients and spawn points), key state (key 201, locSelInputState), the profile (gpadEnabled, invert)
and the dvars involved, set up as scratch dvar_t's.

The engine around them is faked and its arguments compared: the gamepad (CL_GamepadAxisValue returns a random value
per axis, GPad_IsActive), the controller index, the profile, the slow-motion frametime (sub_1404633E0), and
CL_CreateCmd's per-path callees, which also change the command and the view angles so that their order and the
90-degree pitch clamp are visible. CL_KeyState, Key_*, CL_GetMouseMovement, sub_14030D4A0, Vec2Normalize and AngleNormalize360 run for real (all
verified); vectoyaw is faked (see _vectoyaw).
"""
import math
import random
import struct

from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_XMM0

from syms import static, va

STORE = "iw6mp64_MSStore_ship"
KB_SIZE, NUM_BUTTONS = 0x14, 35
SETTINGS = 0x5F0000  # scratch GamerSettingState: invert at +0x44, gpadEnabled at +0x2BC
CL_PM_TYPE, CL_PM_FLAGS = 0x8 + 0x4, 0x8 + 0xC
CL_MOUSEDX, CL_STANCE, CL_FOVSCALE, CL_VIEWANGLES = 0x3534, 0x3548, 0x3568, 0x3610
CG_LOCSEL, CG_FRAMETIME, CG_MAPSIZE, CG_SELECTED = 0x23C, 0x7188C, 0xB52F0, 0xB5368
CG_SIGHTED_CLIENTS, CG_SPAWN_SIGHT = 0x10F05C, 0x10F880
KEYS_DOWN_201, LOCSEL_STATE = 0x124 + 12 * 201, 0xD24


def _f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _fbits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _kbutton(r):
    keys = [r.choice([0, 0, 0, 5, 9, 200, r.randint(0, 255)]) for _ in range(2)]
    downtime = r.choice([0, 0, 100, 5000, r.getrandbits(32)])
    msec = r.choice([0, 0, 3, 16, 33, 100, r.getrandbits(32)])
    return struct.pack("<iiIIBBxx", *keys, downtime, msec, r.random() < 0.4, r.random() < 0.3)


def _angle(r):
    return r.choice([0.0, 90.0, 359.9, -45.0, r.uniform(-400, 400), r.uniform(0, 360)])


def _unit(r):
    return r.choice([0.0, 0.5, 1.0, -0.1, 1.2, r.uniform(-0.3, 1.3), r.uniform(0, 1)])


def _axis(r):
    return r.choice([0.0, 0.0, 1.0, -1.0, 0.1, -0.15, r.uniform(-1.5, 1.5), r.uniform(-1, 1)])


def _state(r):
    """Random state; returns (setup, values the fakes use)."""
    kb = b"".join(_kbutton(r) for _ in range(NUM_BUTTONS))
    pm_type = r.choice([0, 1, 1, 2, 5, 7, -1])
    pm_flags = r.choice([0, 0, 0x800, 0x80000, 0x80800, r.getrandbits(32)])
    stance = (r.random() < 0.5, r.choice([0, 1, 2, 3, 3, 4]))
    mouse = [r.choice([0, 0, 3, -7, 40, r.randint(-500, 500)]) for _ in range(4)] + [r.choice([0, 1])]
    caps = [r.choice([1.0, 0.5]), r.choice([0.0, 0.0, 90.0, 0.1, 400.0]), r.choice([0.0, 0.0, 90.0, 0.1, 400.0])]
    angles = [_angle(r) for _ in range(3)]
    frametime = r.choice([0, 1, 16, 33, 100, r.randint(0, 1000)])
    frametime_base = r.choice([0.0, 0.016, 0.033, r.uniform(0, 1)])
    frame_msec = r.choice([0, 1, 16, 33])
    frame_time = r.choice([0, 100, 5000, r.getrandbits(31)])
    catchers = r.choice([0, 0, 8, 8, 0x18, 0x10, 0x1])
    dvars = {
        "cl_yawspeed": r.choice([140.0, 0.0, 400.0, r.uniform(-50, 500)]),
        "cl_pitchspeed": r.choice([140.0, 0.0, 400.0, r.uniform(-50, 500)]),
        "cl_anglespeedkey": r.choice([1.5, 1.0, 0.0, r.uniform(0, 5)]),
        "cl_dirSelConvergenceTime": r.choice([0.5, 0.1, 1.0, 0.0, r.uniform(0.01, 2)]),
        "cg_mapLocationSelectionCursorSpeed": r.choice([0.6, 1.0, 0.0, r.uniform(0, 3)]),
        "m_yaw": r.choice([0.022, -0.022, 0.0, r.uniform(-1, 1)]),
        "m_pitch": r.choice([0.022, -0.022, 0.0, r.uniform(-1, 1)]),
        "cl_sensitivity": r.choice([5.0, 1.0, r.uniform(0, 20)]),
        "cl_mouseAccel": r.choice([0.0, 0.0, 0.5]),
        "m_filter": r.choice([0, 1]),
    }
    loc_info = r.choice([0, 0x1, 0x80, 0x81, 0x7F, r.getrandbits(32)])
    cg_frametime = r.choice([0, 16, 33, 50, r.randint(-10, 1000)])
    map_size = [r.choice([1000.0, 2000.0, 0.0, r.uniform(100, 5000)]) for _ in range(2)]
    selected = [_unit(r), _unit(r), r.choice([0.0, 90.0, 360.0, 400.0, -5.0, r.uniform(0, 360)]), _unit(r), _unit(r)]
    sighted_clients = r.getrandbits(32)
    trace_ent = r.getrandbits(16)
    count = r.choice([0, 1, 5, 16, 32, r.randint(0, 40)])
    points = [r.choice([0, 1, 2, 3, -1]) for _ in range(40)]
    key201 = r.random() < 0.5
    locsel = r.choice([0, 1, 1, 2, 3])
    gpad = r.random() < 0.4
    invert = r.random() < 0.5

    def setup(w):
        _vectoyaw.machine = w.m
        w.write(static("client_mp/cl_input.cpp", "playersKb"), kb)
        cl = va("clients")
        w.write(cl + CL_PM_TYPE, struct.pack("<i", pm_type))
        w.u32(cl + CL_PM_FLAGS, pm_flags)
        w.write(cl + CL_MOUSEDX, struct.pack("<5i", *mouse))
        w.write(cl + CL_STANCE, struct.pack("<Bxxxi", *stance))
        w.write(cl + CL_FOVSCALE, struct.pack("<3f", *caps))
        w.write(cl + CL_VIEWANGLES, struct.pack("<3f", *angles))
        w.u32(va("cls") + 0x118, frametime)
        w.write(va("cls") + 0x11C, struct.pack("<f", frametime_base))
        w.u32(va("frame_msec"), frame_msec)
        w.u32(va("com_frameTime"), frame_time)
        w.u32(va("clientUIActives") + 0x4, catchers)
        for name, value in dvars.items():
            d = w.alloc(bytes(0x60))
            w.write(d + 0x10, struct.pack("<B" if name == "m_filter" else "<f", value))
            w.u64(va(name), d)
        cg = va("cgArray")
        w.u32(cg + CG_LOCSEL, loc_info)
        w.write(cg + CG_FRAMETIME, struct.pack("<i", cg_frametime))
        w.write(cg + CG_MAPSIZE, struct.pack("<2f", *map_size))
        w.write(cg + CG_SELECTED, struct.pack("<5f", *selected))
        w.u32(cg + CG_SIGHTED_CLIENTS, sighted_clients)
        w.write(cg + CG_SPAWN_SIGHT, struct.pack("<H6xH", trace_ent, count))
        w.write(cg + CG_SPAWN_SIGHT + 0x18, b"".join(struct.pack("<i16x", s) for s in points))
        keys = va("playerKeys")
        w.u32(keys + KEYS_DOWN_201, key201)
        w.u32(keys + LOCSEL_STATE, locsel)
        w.m.mu.mem_write(SETTINGS + 0x44, bytes([invert]))
        w.m.mu.mem_write(SETTINGS + 0x2BC, bytes([gpad]))
    return setup


def _ret_float(value):
    def fake(mu):
        mu.reg_write(UC_X86_REG_XMM0, _fbits(value))
        return None
    return fake


def _axis_fake(values):
    def fake(mu):
        mu.reg_write(UC_X86_REG_XMM0, _fbits(values[mu.reg_read(UC_X86_REG_RDX) & 0xFFFFFFFF]))
        return None
    return fake


def _view_delta(r):
    """A fake that turns the view (clViewangles[0] and [1]) by a random amount, as the movement code does."""
    d = [r.choice([0.0, 30.0, -60.0, 95.0, -120.0, 90.5, -90.5, r.uniform(-200, 200)]), r.uniform(-50, 50)]

    def fake(mu):
        a = va("clients") + CL_VIEWANGLES
        pitch, yaw = struct.unpack("<2f", bytes(mu.mem_read(a, 8)))
        mu.mem_write(a, struct.pack("<2f", _f32(pitch + d[0]), _f32(yaw + d[1])))
        return None
    return fake


def _cmd_or(reg, offset, value):
    """A fake that ORs a dword into the command its `reg` argument points to (records the order of the calls)."""
    def fake(mu):
        p = mu.reg_read(reg) + offset
        old = struct.unpack("<I", bytes(mu.mem_read(p, 4)))[0]
        mu.mem_write(p, struct.pack("<I", old | value))
        return None
    return fake


def _both(*fns):
    def fake(mu):
        for fn in fns:
            fn(mu)
        return None
    return fake


SYM = {
    "settings": "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z",
    "ctrl": "?CL_ControllerIndexFromClientNum@@YAHW4LocalClientNum_t@@@Z",
    "axis": "?CL_GamepadAxisValue@@YAMW4LocalClientNum_t@@W4GamepadVirtualAxis@@@Z",
    "gpad": "?GPad_IsActive@@YA_NH@Z",
    "buttons": "?CL_CmdButtons@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "keymove": "?CL_KeyMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "mousemove": "?CL_MouseMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@M@Z",
    "gpadmove": "?CL_GamepadMove@@YAXW4LocalClientNum_t@@MPEAUusercmd_s@@@Z",
    "finish": "?CL_FinishMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "slowmo": "?sub_1404633E0@@YAMM@Z",
    "cgame": "?sub_1402A9900@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "remote": "?sub_14030DF50@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "locsel": "?CG_HandleLocationSelectionInput@@YA_NW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "removecatcher": "?Key_RemoveCatcher@@YAXW4LocalClientNum_t@@H@Z",
    "keydown": "?Key_IsDown@@YAHW4LocalClientNum_t@@H@Z",
    "catcher": "?Key_IsCatcherActive@@YA_NW4LocalClientNum_t@@H@Z",
    "mouse": "?CL_GetMouseMovement@@YAXPEAUclientActive_t@@PEAM1@Z",
    "mousescaled": "?sub_14030D4A0@@YAXPEAUclientActive_t@@PEAM1@Z",
    "normalize": "?Vec2Normalize@@YAMQEAM@Z",
    "vectoyaw": "?vectoyaw@@YAMQEBM@Z",
    "angle360": "?AngleNormalize360@@YAMM@Z",
}

OBSERVE = {
    SYM["settings"]: "i", SYM["ctrl"]: "", SYM["axis"]: "ii", SYM["gpad"]: "i",
    SYM["buttons"]: "iq", SYM["keymove"]: "iq", SYM["mousemove"]: "iqf", SYM["gpadmove"]: "ifq",
    SYM["finish"]: "iq", SYM["slowmo"]: "f", SYM["cgame"]: "iq", SYM["remote"]: "iq", SYM["locsel"]: "iq",
    SYM["removecatcher"]: "ii", SYM["keydown"]: "ii", SYM["catcher"]: "ii",
    SYM["mouse"]: "q", SYM["mousescaled"]: "q", SYM["normalize"]: "", SYM["vectoyaw"]: "", SYM["angle360"]: "f",
}


def _vectoyaw(mu):
    """vectoyaw, faked: the Store build's computes in double (atan2) where the reconstruction's com_math.cpp follows
    the PS4 server (atan2f), so each side would otherwise reach a different vectoyaw. Records the vector."""
    x, y = struct.unpack("<2f", bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 8)))
    _vectoyaw.machine.observed.append(("vectoyaw", _fbits(x), _fbits(y)))
    yaw = 0.0 if x == 0.0 and y == 0.0 else math.degrees(math.atan2(y, x))
    mu.reg_write(UC_X86_REG_XMM0, _fbits(yaw + 360.0 if yaw < 0.0 else yaw))
    return None


def _engine_fakes(r):
    axes = [_axis(r) for _ in range(6)]
    return {
        SYM["vectoyaw"]: _vectoyaw,
        SYM["settings"]: lambda mu: SETTINGS,
        SYM["ctrl"]: (lambda v: lambda mu: v)(r.choice([0, 0, 1, 3])),
        SYM["axis"]: _axis_fake(axes),
        SYM["gpad"]: (lambda v: lambda mu: v)(r.choice([0, 1])),
    }


def _createcmd_fakes(r):
    fakes = _engine_fakes(r)
    fakes.update({
        SYM["buttons"]: _cmd_or(UC_X86_REG_RDX, 4, r.getrandbits(32)),
        SYM["keymove"]: _cmd_or(UC_X86_REG_RDX, 0x1C, r.getrandbits(16)),
        SYM["mousemove"]: _both(_view_delta(r), _cmd_or(UC_X86_REG_RDX, 0x14, 1)),
        SYM["gpadmove"]: _both(_view_delta(r), _cmd_or(UC_X86_REG_R8, 0x14, 2)),
        SYM["cgame"]: _both(_view_delta(r), _cmd_or(UC_X86_REG_RDX, 0x14, 4)),
        SYM["finish"]: _cmd_or(UC_X86_REG_RDX, 0x18, 0x10000),
        SYM["slowmo"]: _ret_float(r.choice([0.001, 0.016, 0.05, r.uniform(0, 1)])),
        SYM["remote"]: _cmd_or(UC_X86_REG_RDX, 0x14, 8),
    })
    handled = r.choice([0, 1])
    mark = _cmd_or(UC_X86_REG_RDX, 0x14, 16)

    def locsel(mu):
        mark(mu)
        return handled
    fakes[SYM["locsel"]] = locsel
    return fakes


def _cmd(r):
    return bytes(r.getrandbits(8) for _ in range(0x3C))


def _cases(symbol, seed, n, args, fakes, ret="void"):
    r = random.Random(seed)
    inputs = [{"args": args(r), "setup": _state(r), "fakes": fakes(r)} for _ in range(n)]
    return {"symbol": symbol, "build": STORE, "ret": ret, "observe": OBSERVE, "inputs": inputs}


CASES = [
    # usercmd_s returned through the hidden pointer in rcx, the local client in edx
    _cases("?CL_CreateCmd@@YA?AUusercmd_s@@W4LocalClientNum_t@@@Z", 2622, 1500, lambda r: [_cmd(r), 0],
           _createcmd_fakes),
    _cases(SYM["remote"], 0xDF50, 1500, lambda r: [0, _cmd(r)], _engine_fakes),
    _cases(SYM["locsel"], 2461, 2500, lambda r: [0, _cmd(r)], _engine_fakes, ret="char"),
]
