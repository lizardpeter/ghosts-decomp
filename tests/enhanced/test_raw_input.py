"""Raw mouse input and MW2019-unit aim (enhanced/win32/win_rawinput.cpp, win_input.cpp, client_mp/cl_input.cpp).

What must hold:
- every relative raw report is counted exactly; absolute reports are ignored; taking the counts clears them;
- IN_MouseMove hands the game exactly the raw counts, whatever the cursor does; movement made in the background
  is thrown away, and so is the first frame after focus comes back;
- one count turns the view by m_sens * 0.0066 degrees, whatever the FOV scale, m_yaw, m_pitch, cl_mouseAccel
  or m_filter say; the angle is kept in double precision.
"""
import struct

from syms import va
from win32 import HWND_GAME, Win32

CL_MOUSEDX, CL_FOVSCALE, CL_VIEWANGLES = 0x3534, 0x3568, 0x3610
KB_SIZE, KB_STRAFE, KB_MLOOK = 0x14, 8, 13
SETTINGS = 0x500E00
SEND = "?IN_RawInputAdd@@YAXPEBUtagRAWMOUSE@@@Z"
TAKE = "?IN_TakeRawMouse@@YAXPEAH0@Z"
MOVE = "?IN_MouseMove@@YAXXZ"
AIM = "?CL_MouseMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@M@Z"
EVENT = "?CL_MouseEvent@@YAHHHHH@Z"


def _q(written, addr):
    return struct.unpack("<q", b"".join(written[addr + i] for i in range(8)))[0]


def _d(written, addr):
    return struct.unpack("<d", b"".join(written[addr + i] for i in range(8)))[0]


def _f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _rawmouse(dx, dy, flags=0):
    return struct.pack("<HHIIiiI", flags, 0, 0, 0, dx, dy, 0)


def _counters(env, dx, dy):
    def setup(w):
        w.write(env.data("s_rawDx"), struct.pack("<q", dx))
        w.write(env.data("s_rawDy"), struct.pack("<q", dy))
    return setup


def test_relative_reports_are_counted(env):
    for start, (dx, dy) in (((100, 200), (5, -3)), ((0, 0), (-32768, 32767)), ((1 << 40, -(1 << 40)), (1, -1))):
        _, _, written, _ = env.call(SEND, [_rawmouse(dx, dy)], setup=_counters(env, *start))
        assert _q(written, env.data("s_rawDx")) == start[0] + dx
        assert _q(written, env.data("s_rawDy")) == start[1] + dy


def test_absolute_reports_are_ignored(env):
    _, _, written, _ = env.call(SEND, [_rawmouse(500, 500, flags=1)], setup=_counters(env, 7, 8))
    assert env.data("s_rawDx") not in written and env.data("s_rawDy") not in written


def test_take_returns_and_clears(env):
    _, bufs, written, _ = env.call(TAKE, [bytes(4), bytes(4)], setup=_counters(env, 37, -12))
    assert struct.unpack("<i", bufs[0])[0] == 37 and struct.unpack("<i", bufs[1])[0] == -12
    assert _q(written, env.data("s_rawDx")) == 0 and _q(written, env.data("s_rawDy")) == 0


def test_take_clamps_instead_of_wrapping(env):
    _, bufs, _, _ = env.call(TAKE, [bytes(4), bytes(4)], setup=_counters(env, 1 << 40, -(1 << 40)))
    assert struct.unpack("<i", bufs[0])[0] == 0x7FFFFFFF and struct.unpack("<i", bufs[1])[0] == -0x7FFFFFFF


def _mouse_move(env, raw, foreground=HWND_GAME, old_pos=(400, 300), cursor=(1900, 20)):
    events = []

    def event(mu):
        from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9
        signed = lambda v: v - (1 << 32) if v & 0x80000000 else v  # noqa: E731
        events.append((signed(mu.reg_read(UC_X86_REG_R8) & 0xFFFFFFFF), signed(mu.reg_read(UC_X86_REG_R9) & 0xFFFFFFFF)))
        return 1

    win = Win32(foreground=foreground, cursor=cursor)

    def setup(w):
        _counters(env, *raw)(w)
        w.u64(va("g_wv") + 0x10, HWND_GAME)
        s_wmv = va("iw6s@win32/win_input.cpp@@s_wmv")
        w.write(s_wmv + 4, struct.pack("<ii", *old_pos))
        d = w.alloc(bytes(0x60))  # r_displayMode: windowed
        w.write(d + 0x10, struct.pack("<i", 1))
        w.u64(va("r_displayMode"), d)
        cls = va("cls")
        w.write(cls + 0x180, struct.pack("<4I", 1920, 1080, 1920, 1080))  # scene and display size
        w.write(cls + 0x180 + 0x20, struct.pack("<2I", 1920, 1080))       # monitor size
        Win32(**vars(win)).install(w.m)
    _, _, written, _ = env.call(MOVE, [], setup=setup, fakes={EVENT: event})
    return events, written


def test_mouse_move_passes_raw_counts(env):
    events, written = _mouse_move(env, (37, -12))
    assert events == [(37, -12)], events  # the cursor jumped 1500 px; only the raw counts count
    assert _q(written, env.data("s_rawDx")) == 0


def test_background_movement_is_dropped(env):
    events, written = _mouse_move(env, (500, 500), foreground=0x99)
    assert events == []
    assert _q(written, env.data("s_rawDx")) == 0 and _q(written, env.data("s_rawDy")) == 0


def test_first_frame_after_focus_is_dropped(env):
    events, _ = _mouse_move(env, (25, 25), old_pos=(-100000, 0))
    assert events == [(0, 0)], events


def _aim(env, dx, dy, sens=1.5, invert=False, fov_scale=1.0, angles=(10.0, 37.0), max_speed=(0.0, 0.0),
         shadow=None, frame_msec=16):
    def ret(value):
        return lambda mu: value

    def echo(mu):  # aim assist leaves the angles alone
        from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX
        inp = bytes(mu.mem_read(mu.reg_read(UC_X86_REG_RCX), 0x34))
        pitch, yaw = struct.unpack_from("<f", inp, 8)[0], struct.unpack_from("<f", inp, 0x14)[0]
        mu.mem_write(mu.reg_read(UC_X86_REG_RDX), struct.pack("<ffHB", pitch, yaw, 0, 0) + b"\0")
        return None

    def setup(w):
        cl = va("clients")
        w.write(cl + CL_MOUSEDX, struct.pack("<5i", dx, 0, dy, 0, 0))
        w.write(cl + CL_FOVSCALE, struct.pack("<3f", fov_scale, *max_speed))
        w.write(cl + CL_VIEWANGLES, struct.pack("<3f", *angles, 0.0))
        w.u32(va("frame_msec"), frame_msec)
        for name, value in (("m_sens", ("f", sens)), ("m_invertPitch", ("b", invert))):
            d = w.alloc(bytes(0x60))
            w.write(d + 0x10, struct.pack({"f": "<f", "b": "<B"}[value[0]], value[1]))
            w.u64(env.data(name), d)
        for name, value in (("cl_freelook", 1), ("m_side", 0), ("m_forward", 0), ("m_yaw", 0), ("m_pitch", 0),
                            ("cl_mouseAccel", 0), ("m_filter", 0)):
            d = w.alloc(bytes(0x60))
            w.write(d + 0x10, struct.pack("<f", 7.5) if name in ("m_yaw", "m_pitch", "cl_mouseAccel")
                    else bytes([value]) * 4)
            w.u64(va(name), d)
        if shadow:
            w.write(env.data("s_viewangles"), struct.pack("<2d", *shadow))
            w.write(env.data("s_viewanglesWritten"), struct.pack("<2f", _f32(shadow[0]), _f32(shadow[1])))
    fakes = {
        "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z": ret(SETTINGS),
        "?CG_GetPredictedPlayerState@@YAPEBUplayerState_s@@W4LocalClientNum_t@@@Z": ret(0x500D00),
        "?BG_MeleeChargeShouldLockView@@YAHPEBUplayerState_s@@E@Z": ret(0),
        "?AimAssist_UpdateMouseInput@@YAXPEBUAimInput@@PEAUAimOutput@@@Z": echo,
        "?sub_14027B800@@YAXPEBUAimOutput@@PEAUusercmd_s@@@Z": ret(None),
    }
    _, _, written, _ = env.call(AIM, [0, bytes(0x40), ("f", 0.016)], setup=setup, fakes=fakes)
    a = va("clients") + CL_VIEWANGLES
    pitch = struct.unpack("<f", b"".join(written.get(a + i, b"\0") for i in range(4)))[0] if a in written else angles[0]
    yaw = struct.unpack("<f", b"".join(written[a + 4 + i] for i in range(4)))[0] if a + 4 in written else angles[1]
    return pitch, yaw, written


def test_one_count_is_sens_times_0_0066_degrees(env):
    for sens, dx, dy in ((1.5, 100, -50), (1.0, 1, 1), (0.37, -12345, 678), (4.0, 3, 0)):
        pitch, yaw, _ = _aim(env, dx, dy, sens=sens)
        k = float(_f32(sens)) * 0.0066
        assert yaw == _f32(37.0 - dx * k), (sens, dx, yaw, 37.0 - dx * k)
        assert pitch == _f32(10.0 + dy * k), (sens, dy, pitch)


def test_fov_does_not_change_sensitivity(env):
    results = {_aim(env, 250, -90, fov_scale=s)[:2] for s in (1.0, 0.5, 1.317, 0.2)}
    assert len(results) == 1, results


def test_invert_pitch(env):
    p0, _, _ = _aim(env, 0, 40)
    p1, _, _ = _aim(env, 0, 40, invert=True)
    assert p0 - 10.0 == -(p1 - 10.0) != 0


def test_angle_kept_in_double_precision(env):
    # continuing from an angle a float can't hold exactly: the double copy carries on, not the rounded float
    shadow = (10.123456789012345, 37.98765432101234)
    _, _, written = _aim(env, 1, 1, shadow=shadow, angles=(_f32(shadow[0]), _f32(shadow[1])))
    k = float(_f32(1.5)) * 0.0066
    assert _d(written, env.data("s_viewangles")) == shadow[0] + 1 * k
    assert _d(written, env.data("s_viewangles") + 8) == shadow[1] - 1 * k


def test_external_angle_change_is_picked_up(env):
    # spawning or the cgame moved the view since the last frame: start from the new angle, not the stale copy
    pitch, yaw, _ = _aim(env, 10, 0, shadow=(1.0, 2.0), angles=(50.0, 60.0))
    assert yaw == _f32(60.0 - 10 * float(_f32(1.5)) * 0.0066)


def test_game_speed_limits_still_apply(env):
    # a turret's maximum yaw speed: 16 ms * 10 deg/s = 0.16 degrees at most
    _, yaw, _ = _aim(env, 1000, 0, max_speed=(0.0, 10.0))
    assert abs((37.0 - yaw) - 0.16) < 1e-5, yaw
