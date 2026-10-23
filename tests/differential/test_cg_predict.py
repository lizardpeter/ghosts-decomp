"""Differential cases for the prediction (cgame_mp/cg_predict_mp.cpp, cgame/cg_playerstate.cpp's transPlayerState_t
helpers) and the client's side of it (client_mp/cl_cgame_mp.cpp), against the Store build.

CG_PredictPlayerState_Internal gets a random client: a usercmd ring of 128 commands (times increasing by 0 to 17 ms,
repeats included, random buttons, angles and moves) and a command number near the int limits; the predicted state's
commandTime at, between, before and after the command times (older than the ring, equal to the newest, newer); the
saved state from the last frame (commandTime equal to a replayed command's or not, origin near or far); the
prediction error, its time and cg_errordecay (0, 100, negative, NaN); demoType, otherFlags 0x2000, pm_type and the
mantle flag; the moving platform (the state's own, the cached contact entity, or the trace's allsolid hit; entity
types 6, 14 and others, numbers that are and aren't platforms, ENTITYNUM_NONE), cg.time against the platform's start
time (equal, so no angular velocity); the client mode unk_143E96824; local client 0 or 1 and both values of the
second argument; up to five items with pickup times before, at and after cg.time and equipped or missing weapons.

The engine is faked and every call is logged with its arguments (stack pointers as 'ptr', the vectors they pass by
value): Pmove (moves commandTime to cmd.serverTime, moves the origin, sets the view angles from the command, and by a
script changes pm_type, the platform entity and pm->contactEntity), CG_AdjustPositionForMover (writes the moved
origin and both deltas), the trace (allsolid and hitId by script), the three BG_Update*MovingPlatform, the origin
handoff, the item checks and the pickup event. CL_GetUserCmd and CL_GetCurrentCmdNumber run for real.

A second set runs the original Pmove for real (noclip and ufo, a few commands each; the weapon tables point at an
empty definition and the two animation-condition calls are faked), so the replay is checked with the real movement
and view-angle code of both builds.

CG_PredictPlayerState: CG_PredictPlayerState_Internal is faked (both copies) and sets the pmove_t's view change, its
time, the torso and waist pitch and the ground surface from a script; the step smoothing dvars (min, max, time:
0, negative, NaN), the step start against cg.time and the view change time, viewTeleported, pm_type, the stance,
cursor hint, melee charge entity, vehicle (flags, eType 12, 14 and others, otherFlags 0x2000) and the player's
entity. Its callees are faked and logged except CL_SetUserCmdOrigin and sub_140306FD0 (reconstructed, run for real).
"""
import math
import random
import struct

from harness import SCRATCH
from syms import static, va
from win32_display import CURRENT, arg, farg, log_value

STORE = "iw6mp64_MSStore_ship"
SRC = "cgame_mp/cg_predict_mp.cpp"
CMD_SIZE, PS_SIZE, PM_SIZE, CENT_SIZE = 0x3C, 0x3328, 0x178, 0x238
CL_SERVERTIME, CL_CMDS, CL_CMDNUMBER = 0x34D0, 0x3628, 0x5428
CG_DEMOTYPE, CG_SNAP, CG_NEXTSNAP = 0x3368, 0x3388, 0x3390
CG_ERRTIME, CG_ERR = 0x3350, 0x3354
CG_TIME, CG_OLDTIME, CG_FROMTIME = 0x71890, 0x71894, 0x71898
CG_CONTACT, CG_PLATFORM_AV = 0xB2750, 0xB2754
CG_SELECTED = 0xB5368
CG_TELEPORTED, CG_NOERROR, CG_STEPSTART, CG_STEPCHANGE = 0x10E831, 0x10E832, 0x10E834, 0x10E838
CG_SAVED = 0x10E84C  # commandTime, origin, viewangles, trans (0x30), pe (0x2C)
SNAP = SCRATCH + 0x40000           # scratch snapshot_s (serverTime at +0x3C7C)
DVARS = SCRATCH + 0x80000          # scratch dvar_t's, 0x40 apart
WEAPDEF = SCRATCH + 0x90000        # an empty weapon definition for the real Pmove
SYM = {
    "pmove": "?Pmove@@YAXPEAUpmove_t@@@Z",
    "adjust": "?CG_AdjustPositionForMover@@YAXW4LocalClientNum_t@@PEBMHHHPEAM22PEAUplayerState_s@@PEAUpmove_t@@@Z",
    "trace": "?sub_140304650@@YAXPEAUtrace_t@@PEBM1PEBUBounds@@HH@Z",
    "angles": "?BG_UpdateAnglesMovingPlatform@@YAXPEAUplayerState_s@@QEBM1QEAM@Z",
    "dir": "?BG_UpdateDirectionMovingPlatform@@YAXQEAMQEBM1@Z",
    "point": "?BG_UpdatePointMovingPlatform@@YAXQEAMQEBM111@Z",
    "origin": "?sub_140178C50@@YAXW4LocalClientNum_t@@@Z",
    "touches": "?BG_PlayerTouchesItem@@YAHPEBUplayerState_s@@PEBUentityState_s@@H@Z",
    "grabbed": "?BG_CanItemBeGrabbed@@YAHPEBUentityState_s@@PEBUplayerState_s@@H@Z",
    "type5": "?sub_140267140@@YAHTWeapon@@@Z",
    "ammo": "?sub_140267880@@YAHPEBUentityState_s@@PEBUplayerState_s@@@Z",
    "event": "?sub_1402B8F80@@YAXW4LocalClientNum_t@@HHTWeapon@@_N@Z",
    "com_error": "?Com_Error@@YAXW4errorParm_t@@PEBDZZ",
    "anim_cond": "?BG_AnimUpdatePlayerStateConditions@@YAXPEAUpmove_t@@@Z",
    "set_cond": "?BG_SetConditionValue@@YAXPEAUcharacterInfo_t@@H_K@Z",
    "internal": "?CG_PredictPlayerState_Internal@@YAHW4LocalClientNum_t@@H@Z",
    "stance": "?CL_SetStance@@YAXW4LocalClientNum_t@@W4StanceState@@@Z",
    "traj": "?BG_EvaluateTrajectory@@YAXPEBUtrajectory_t@@HQEAM@Z",
    "melee": "?sub_1402CC6E0@@YAXW4LocalClientNum_t@@PEAUplayerState_s@@@Z",
    "vehicle": "?sub_140277AB0@@YAXPEBUplayerState_s@@PEAUentityState_s@@HH@Z",
    "ps2es": "?BG_PlayerStateToEntityState@@YAXPEBUplayerState_s@@PEAUentityState_s@@H@Z",
    "events": "?BG_PlayerToEntity_ProcessEvents@@YAXPEBUplayerState_s@@PEAUentityState_s@@E@Z",
    "platform": "?sub_1402EF5D0@@YAXW4LocalClientNum_t@@PEBUplayerState_s@@PEAUcg_s@@@Z",
    "remote": "?sub_1405BAAA0@@YAXW4LocalClientNum_t@@@Z",
    "omnvar": "?sub_1402D0AC0@@YAXW4LocalClientNum_t@@@Z",
}


def _m():
    return CURRENT.get("m")


def _log(*entry):
    m = _m()
    if m is not None:
        m.observed.append(entry)


def _rd(mu, a, n):
    return bytes(mu.mem_read(a, n))


def _vec(mu, a):
    return _rd(mu, a, 12)


def _wf(mu, a, *v):
    mu.mem_write(a, struct.pack(f"<{len(v)}f", *v))


def _rf(mu, a, n=1):
    return struct.unpack(f"<{n}f", _rd(mu, a, 4 * n))


def _ri(mu, a):
    return struct.unpack("<i", _rd(mu, a, 4))[0]


def _wi(mu, a, v):
    mu.mem_write(a, struct.pack("<I", v & 0xFFFFFFFF))


def _ptr(mu, v):
    return "ptr" if 0x100000 <= v < 0x200000 else v


def _f(r, *common):
    return r.choice([*common, float("nan"), r.uniform(-1000, 1000), r.uniform(-1, 1)])


def _dvar(w, slot, value):
    a = DVARS + 0x40 * slot
    w.m.mu.mem_write(a + 0x10, struct.pack("<f", value))
    return a


class Script:
    """Per-input fake behaviour; reset at every setup so both runs see the same sequence."""

    def __init__(self, r):
        self.r = r
        self.pm_type_at = r.choice([None, None, 0, 1, 2])  # the Pmove call that makes pm_type 2 (ends the item checks)
        self.platform_at = r.choice([None, None, None, 0, 1])
        self.platform_value = r.choice([0x7FF, 0x3A, 0x100, 0x39])
        self.contact = r.choice([0x7FF, 0x7FF, 0x123, 0x3A, 5])
        self.allsolid = r.choice([0, 1, 1])
        self.hit = r.choice([0x123, 0x3A, 0x7FF, 0x300])
        self.angle_change = [r.choice([0.0, 10.5, 370.25, -190.0, 179.9, float("nan"), r.uniform(-720, 720)])
                             for _ in range(3)]
        self.delta_angles = r.choice([[0.0, 0.0, 0.0], [0.0, 2.5, 0.0], [1.0, -3.0, 0.5]])
        self.items = [r.choice([0, 1, 1]) for _ in range(20)]
        self.reset()

    def reset(self):
        self.calls = 0
        self.item_calls = 0


def _pmove_fake(script):
    def run(mu):
        pm = arg(mu, 0)
        ps = struct.unpack("<Q", _rd(mu, pm, 8))[0]
        cmd_time = _ri(mu, pm + 8)
        command_time = _ri(mu, ps)
        _log("Pmove", _rd(mu, pm + 8, CMD_SIZE), _rd(mu, pm + 0x44, CMD_SIZE), command_time, _rd(mu, pm + 0x80, 4),
             _rd(mu, pm + 0x124, 4), _rd(mu, pm + 0x158, 8), _rd(mu, pm + 0x174, 1), _rd(mu, ps + 0x1C, 12),
             _rd(mu, ps + 0x44, 4), _rd(mu, ps + 0x4, 4))
        if cmd_time >= command_time:
            msec = cmd_time - command_time
            _wi(mu, ps, cmd_time)
            x, y, z = _rf(mu, ps + 0x1C, 3)
            _wf(mu, ps + 0x1C, x + 0.25 * msec, y - 0.125 * msec, z)
            angles = struct.unpack("<3i", _rd(mu, pm + 0x10, 12))
            _wf(mu, ps + 0x184, *((a & 0xFFFF) * (360.0 / 65536.0) for a in angles))
        if script.calls == script.pm_type_at:
            _wi(mu, ps + 4, 2)
        if script.calls == script.platform_at:
            _wi(mu, ps + 0x44, script.platform_value)
        _wi(mu, pm + 0x124, script.contact if script.calls == 1 else 0x7FF)
        script.calls += 1
        return None
    return run


def _adjust_fake(mu):
    lc, in_, mover, t0, t1 = arg(mu, 0), arg(mu, 1), arg(mu, 2), arg(mu, 3), arg(mu, 4)
    out, d_origin, d_angles, ps, pm = arg(mu, 5), arg(mu, 6), arg(mu, 7), arg(mu, 8), arg(mu, 9)
    vin = _rf(mu, in_, 3)
    _log("CG_AdjustPositionForMover", lc & 0xFFFFFFFF, _ptr(mu, in_), _vec(mu, in_), mover & 0xFFFFFFFF,
         t0 & 0xFFFFFFFF, t1 & 0xFFFFFFFF, _ptr(mu, out), _ptr(mu, d_origin), _ptr(mu, d_angles), ps, pm)
    k = ((t1 - t0) & 0xFFFFFFFF)
    k = k - (1 << 32) if k & 0x80000000 else k
    mv = mover & 0xFFFFFFFF
    dx = 0.0 if mv == 0x7FF else 0.003 * k + 0.5
    _wf(mu, out, vin[0] + dx, vin[1] - dx, vin[2] + (0.25 if mv & 1 else 0.0))
    _wf(mu, d_origin, dx, -dx, 0.25)
    _wf(mu, d_angles, 0.0, (mv & 7) * 1.5 - 3.0, 0.0)
    return None


def _trace_fake(script):
    def run(mu):
        results = arg(mu, 0)
        _log("trace", _ptr(mu, results), _vec(mu, arg(mu, 1)), _vec(mu, arg(mu, 2)), arg(mu, 3), arg(mu, 4) & 0xFFFFFFFF,
             arg(mu, 5) & 0xFFFFFFFF)
        mu.mem_write(results, bytes(0x2C))
        mu.mem_write(results + 0x1C, struct.pack("<H", script.hit))
        mu.mem_write(results + 0x26, bytes([script.allsolid]))
        return None
    return run


def _angles_fake(script):
    def run(mu):
        ps, d, plat, out = arg(mu, 0), arg(mu, 1), arg(mu, 2), arg(mu, 3)
        _log("BG_UpdateAnglesMovingPlatform", ps, _vec(mu, d), plat, _ptr(mu, out))
        _wf(mu, out, *script.angle_change)
        y = _rf(mu, ps + 0x68)[0]
        _wf(mu, ps + 0x68, y + _rf(mu, d + 4)[0])
        return None
    return run


def _dir_fake(mu):
    v, plat, d = arg(mu, 0), arg(mu, 1), arg(mu, 2)
    _log("BG_UpdateDirectionMovingPlatform", v, plat, _vec(mu, d))
    x = _rf(mu, v)[0]
    _wf(mu, v, x + 1.0)
    return None


def _point_fake(mu):
    p, org, ang, d, dorg = arg(mu, 0), arg(mu, 1), arg(mu, 2), arg(mu, 3), arg(mu, 4)
    _log("BG_UpdatePointMovingPlatform", p, org, ang, _vec(mu, d), _vec(mu, dorg))
    z = _rf(mu, p + 8)[0]
    _wf(mu, p + 8, z + 2.0)
    return None


def _item_fake(name, script, sig):
    def run(mu):
        _log(name, *(log_value(mu, c, i) for i, c in enumerate(sig)))
        v = script.items[script.item_calls % len(script.items)]
        script.item_calls += 1
        return v
    return run


def _simple(name, sig, result=None):
    def run(mu):
        _log(name, *(log_value(mu, c, i) for i, c in enumerate(sig)))
        return result
    return run


def _cmds(r, current, start_time):
    """The ring: commands current-127..current with increasing times; returns {cmdNumber: serverTime} too."""
    times, t = {}, start_time
    ring = bytearray(128 * CMD_SIZE)
    for n in range(current - 127, current + 1):
        t = (t + r.choice([0, 1, 1, 2, 5, 5, 7, 16, 17])) & 0xFFFFFFFF
        times[n] = t if t < 1 << 31 else t - (1 << 32)
        cmd = bytearray(r.getrandbits(8) for _ in range(CMD_SIZE))
        struct.pack_into("<I", cmd, 0, t)
        ring[(n & 127) * CMD_SIZE:(n & 127) * CMD_SIZE + CMD_SIZE] = cmd
    return ring, times


def _internal_input(r, real_pmove=False):
    lc = r.choice([0, 0, 0, 0, 0, 1]) if not real_pmove else 0
    early = r.choice([0, 1])
    current = r.choice([127, 128, 200, 5000, 0x7FFFFFF0, r.randint(130, 1 << 24)])
    start = r.choice([1000, 50000, 0x7FFFF000, r.randint(0, 1 << 30)])
    ring, times = _cmds(r, current, start)
    latest = times[current]
    if real_pmove:
        back = r.choice([0, 1, 2, 3, 5, 8])
    else:
        back = r.choice([0, 1, 2, 5, 20, 126, 127, 128, 200, -1])
    if back < 0:
        command_time = latest + r.choice([0, 1, 50])
    elif current - back in times:
        command_time = times[current - back] + r.choice([0, 0, 0, -1, 1])
    else:
        command_time = times[current - 127] - r.choice([1, 100])
    saved_time = r.choice([command_time, command_time,
                           times[max(current - 127, current - r.randint(0, 8))], r.getrandbits(31)])
    origin = [_f(r, 0.0, 100.0) for _ in range(3)]
    saved_origin = [o + r.choice([0.0, 0.0, 0.05, 0.1, 0.15, 0.2, -3.0, 50.0]) if not math.isnan(o) else 1.0 for o in origin]
    now = (command_time + r.choice([0, 5, 50, 100, -10])) & 0xFFFFFFFF
    old = (now - r.choice([0, 1, 5, 16, 50])) & 0xFFFFFFFF
    err_time = (now - r.choice([0, 10, 99, 100, 101, 500])) & 0xFFFFFFFF
    from_time = r.choice([now, now, (now - 50) & 0xFFFFFFFF, (now - 7) & 0xFFFFFFFF])
    decay = r.choice([100.0, 100.0, 0.0, 50.0, -100.0, float("nan"), 1e-30])
    demo = r.choice([0] * 12 + [1])
    other = r.choice([0, 0, 0x2000 if not real_pmove else 0, 0x1000000, r.getrandbits(32) & ~0x2000])
    pm_type = r.choice([2, 3]) if real_pmove else r.choice([0, 0, 1, 2, 5, 6, 7, 8, 4])
    pm_flags = r.choice([0, 0, 4, r.getrandbits(32)]) if not real_pmove else r.choice([0, 0x4000])
    platform = r.choice([0x7FF, 0x7FF, 0x7FF, 0x3A, 0x39, 0x7FD, 0x7FE, 0x123, r.randint(0, 0x7FF)])
    contact = r.choice([0x7FF, 0x7FF, 0x123, 0x3A, 0x200])
    script = Script(r)
    entity_types = {n: r.choice([6, 14, 14, 7, 0, 22]) for n in (0x123, 0x3A, 0x200, 0x300, 0x7FF, script.hit,
                                                                 contact, platform)}
    entity_numbers = {n: r.choice([n, n, n, 0x7FF, 0x3A, 5]) for n in entity_types}
    items = [(0x400 + i, r.choice([0, 0, 5, 0x123, r.getrandbits(32)]),
              r.choice([0, 0, now, (now - 1) & 0xFFFFFFFF, (now + 1) & 0xFFFFFFFF, (now + 4999) & 0xFFFFFFFF]))
             for i in range(r.choice([0, 0, 1, 3, 5]))]
    equipped = [r.choice([0, 5, 0x123, r.getrandbits(32)]) for _ in range(15)]
    mode = r.choice([0, 0, 0, 0, 1, 2])
    delta = [_f(r, 0.0) for _ in range(3)]
    viewangles = [_f(r, 0.0, 90.0) for _ in range(3)]
    saved_angles = [_f(r, 0.0, 45.0) for _ in range(3)]
    flags = (r.choice([0, 1]), r.choice([0, 0, 0, 1]))
    err = [_f(r, 0.0) for _ in range(3)]
    snap_time = r.getrandbits(31)
    garbage_pm = bytes(r.getrandbits(8) for _ in range(PM_SIZE))

    def setup(w):
        CURRENT["m"] = w.m
        script.reset()
        mu = w.m.mu
        cg, cl, ents = va("cgArray"), va("clients"), va("cg_entitiesArray")
        w.write(cl + CL_CMDS, bytes(ring))
        w.u32(cl + CL_CMDNUMBER, current)
        ps = bytearray(0x620)
        struct.pack_into("<IiiII", ps, 0, command_time & 0xFFFFFFFF, pm_type, 0, pm_flags & 0xFFFFFFFF, other)
        struct.pack_into("<3f3f", ps, 0x1C, *origin, *(r2 for r2 in (1.0, -2.0, 3.0)))
        struct.pack_into("<i", ps, 0x44, platform)
        struct.pack_into("<ii3f", ps, 0x5C, 800, 190, *delta)
        struct.pack_into("<i", ps, 0x70, 0x7FF)
        struct.pack_into("<i", ps, 0xBC, 0x7FF)
        struct.pack_into("<3f", ps, 0x184, *viewangles)
        struct.pack_into("<if", ps, 0x190, 60, 60.0)
        struct.pack_into("<3f", ps, 0x278, 1.0, 2.0, 3.0)
        struct.pack_into("<15I", ps, 0x2E4, *equipped)
        w.write(cg, bytes(ps))
        w.u32(cg + CG_DEMOTYPE, demo)
        w.u64(cg + CG_SNAP, SNAP)
        w.u64(cg + CG_NEXTSNAP, SNAP)
        mu.mem_write(SNAP + 0x3C7C, struct.pack("<I", snap_time))
        w.u32(cg + CG_TIME, now)
        w.u32(cg + CG_OLDTIME, old)
        w.u32(cg + CG_FROMTIME, from_time)
        w.u32(cg + CG_ERRTIME, err_time)
        w.write(cg + CG_ERR, struct.pack("<3f", *err))
        w.u32(cg + CG_CONTACT, contact)
        w.write(cg + CG_TELEPORTED, bytes(flags))
        w.u32(cg + CG_STEPSTART, (now - 30) & 0xFFFFFFFF)
        w.write(cg + CG_SAVED, struct.pack("<I3f3f", saved_time & 0xFFFFFFFF, *saved_origin, *saved_angles))
        pm = static(SRC, "cg_pmove") + PM_SIZE * lc
        w.write(pm, garbage_pm)
        w.write(pm + 0x108, struct.pack("<6f", 0, 0, 35, 15, 15, 35))
        for n, t in entity_types.items():
            e = ents + CENT_SIZE * n
            w.write(e + 0xF8, struct.pack("<ii", entity_numbers[n], t))
            w.write(e + 0x18, struct.pack("<6f", 10.0, 20.0, 30.0, 0.0, 90.0, 0.0))
        item_list = static(SRC, "cg_itemEntities")
        for i, (n, weapon, pickup) in enumerate(items):
            e = ents + CENT_SIZE * n
            w.write(e + 0xF8, struct.pack("<ii", n, 3))
            w.write(e + 0x1BC, struct.pack("<I", weapon))
            w.write(e + 0x20C, struct.pack("<I", pickup))
            w.u64(item_list + 8 * i, e)
        w.u32(static(SRC, "cg_itemEntityCount"), len(items))
        w.u64(va("cg_errorDecay"), _dvar(w, 0, decay))
        w.u32(va("unk_143E96824"), mode)
        if real_pmove:
            w.u64(va("bg_weaponDefs"), WEAPDEF)
            w.u64(va("bg_weaponCompleteDefs"), WEAPDEF)

    fakes = {
        SYM["adjust"]: _adjust_fake,
        SYM["trace"]: _trace_fake(script),
        SYM["angles"]: _angles_fake(script),
        SYM["dir"]: _dir_fake,
        SYM["point"]: _point_fake,
        SYM["origin"]: _simple("sub_140178C50", "i"),
        SYM["touches"]: _item_fake("BG_PlayerTouchesItem", script, "ppi"),
        SYM["grabbed"]: _item_fake("BG_CanItemBeGrabbed", script, "ppi"),
        SYM["type5"]: _item_fake("sub_140267140", script, "i"),
        SYM["ammo"]: _item_fake("sub_140267880", script, "pp"),
        SYM["event"]: _simple("sub_1402B8F80", "iiiib"),
        SYM["com_error"]: _simple("Com_Error", "isii"),
    }
    if real_pmove:
        fakes[SYM["anim_cond"]] = _simple("BG_AnimUpdatePlayerStateConditions", "p")
        fakes[SYM["set_cond"]] = _simple("BG_SetConditionValue", "piq")
    else:
        fakes[SYM["pmove"]] = _pmove_fake(script)
    return {"args": [lc, early], "setup": setup, "fakes": fakes}


def _internal_fake(script):
    """CG_PredictPlayerState_Internal for CG_PredictPlayerState's cases: sets what the caller reads afterwards."""
    def run(mu):
        lc, early = arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF
        _log("CG_PredictPlayerState_Internal", lc, early)
        pm = static(SRC, "cg_pmove") + PM_SIZE * lc
        _wf(mu, pm + 0x15C, script["view_change"])
        _wi(mu, pm + 0x158, script["view_change_time"])
        _wf(mu, pm + 0x160, script["torso"], script["waist"])
        _wi(mu, pm + 0x170, script["surface"])
        cg = va("cgArray")
        _wi(mu, cg + 0xC, script["pm_flags"])
        return 1
    return run


def _ps2es_fake(mu):
    ps, es = arg(mu, 0), arg(mu, 1)
    _log("BG_PlayerStateToEntityState", ps, es, arg(mu, 2) & 0xFFFFFFFF, _rd(mu, es, 8))
    mu.mem_write(es + 4, struct.pack("<I", 1))
    mu.mem_write(es + 8, _rd(mu, ps + 0x1C, 0x60))  # some of the state into lerp, so the copy is visible
    return None


def _vehicle_fake(mu):
    ps, es = arg(mu, 0), arg(mu, 1)
    _log("sub_140277AB0", ps, es, arg(mu, 2) & 0xFFFFFFFF, arg(mu, 3) & 0xFFFFFFFF)
    mu.mem_write(es + 4, struct.pack("<I", 13))
    mu.mem_write(es + 8, bytes(range(0x40, 0x40 + 0x68)))
    return None


def _predict_input(r):
    view_change = r.choice([0.0, 0.0, 4.0, -4.0, 0.5, 20.0, -30.0, float("nan"), r.uniform(-40, 40)])
    now = r.choice([1000, 50000, 0x7FFFFF00, r.randint(0, 1 << 30)])
    step_start = (now - r.choice([0, 1, 50, 149, 150, 151, 400, -20, 5000])) & 0xFFFFFFFF
    script = {
        "view_change": view_change,
        "view_change_time": r.choice([step_start, (step_start + r.choice([1, 20, 75, 75, 149, 150, 200])) & 0xFFFFFFFF,
                                      (step_start - 5) & 0xFFFFFFFF, now]),
        "torso": _f(r, 0.0), "waist": _f(r, 0.0),
        "surface": r.getrandbits(32),
        "pm_flags": r.choice([0, 0x400, 4, 0x404, r.getrandbits(32)]),
    }
    zmin = r.choice([1.0, 1.0, 0.0, 5.0, -1.0, float("nan")])
    zmax = r.choice([16.0, 16.0, 0.0, 10.0, -16.0, float("nan")])
    ztime = r.choice([0.15, 0.15, 0.0, 0.1, -0.1, float("nan"), 3e9])
    step_change = _f(r, 0.0, 8.0, -8.0)
    pm_type = r.choice([0, 0, 1, 2, 3, 4, 5, 8])
    teleported = r.choice([0, 0, 0, 1])
    client = r.choice([0, 3, 17])
    hint = r.choice([0, 0, 5])
    melee = r.choice([0x7FF, 0x7FF, 0x7FE, 0x10, -1, 0x800])
    vehicle = r.choice([0x7FF, 0x7FF, 0x50, 0x51])
    vehicle_flags = r.choice([0, 1, 1, 3])
    vehicle_etype = r.choice([12, 14, 13, 0, 0x10C])
    other = r.choice([0, 0, 0x2000, r.getrandbits(32)])
    if r.random() < 0.1:  # the previous step's remainder cancels the new one exactly (stepRemaining == 0)
        script["view_change"], step_change, zmin, ztime = 4.0, -8.0, 1.0, 0.15
        zmax = r.choice([-16.0, 0.0, 16.0])
        step_start = (now - 100) & 0xFFFFFFFF
        script["view_change_time"] = (step_start + 75) & 0xFFFFFFFF
        pm_type, teleported = 0, 0
    ps_bytes = bytes(r.getrandbits(8) for _ in range(0x620))
    ent_bytes = bytes(r.getrandbits(8) for _ in range(CENT_SIZE))
    selected = struct.pack("<3f", *(_f(r, 0.0) for _ in range(3)))

    def setup(w):
        CURRENT["m"] = w.m
        cg, ents = va("cgArray"), va("cg_entitiesArray")
        ps = bytearray(ps_bytes)
        struct.pack_into("<i", ps, 4, pm_type)
        struct.pack_into("<I", ps, 0x10, other)
        struct.pack_into("<i", ps, 0xBC, vehicle)
        struct.pack_into("<i", ps, 0x17C, client)
        struct.pack_into("<i", ps, 0x210, hint)
        w.write(cg, bytes(ps))
        w.write(cg + 0xE08, struct.pack("<i", melee))
        w.u32(cg + CG_TIME, now)
        w.u32(cg + CG_STEPSTART, step_start)
        w.write(cg + CG_STEPCHANGE, struct.pack("<f", step_change))
        w.write(cg + CG_TELEPORTED, bytes([teleported]))
        w.write(cg + CG_SELECTED, selected)
        w.write(ents + CENT_SIZE * client, ent_bytes)
        e = ents + CENT_SIZE * vehicle
        w.write(e, bytes(CENT_SIZE))
        w.write(e + 2, bytes([vehicle_etype & 0xFF]))
        w.write(e + 0x200, struct.pack("<I", vehicle_flags))
        w.write(e + 0x100, bytes(range(0x68)))
        w.u64(va("cg_viewZSmoothingMin"), _dvar(w, 0, zmin))
        w.u64(va("cg_viewZSmoothingMax"), _dvar(w, 1, zmax))
        w.u64(va("cg_viewZSmoothingTime"), _dvar(w, 2, ztime))

    fakes = {
        SYM["internal"]: _internal_fake(script),
        SYM["stance"]: _simple("CL_SetStance", "ii"),
        SYM["traj"]: _simple("BG_EvaluateTrajectory", "pip"),
        SYM["melee"]: _simple("sub_1402CC6E0", "ip"),
        SYM["vehicle"]: _vehicle_fake,
        SYM["ps2es"]: _ps2es_fake,
        SYM["events"]: _simple("BG_PlayerToEntity_ProcessEvents", "ppb"),
        SYM["platform"]: _simple("sub_1402EF5D0", "ipp"),
        SYM["remote"]: _simple("sub_1405BAAA0", "i"),
        SYM["omnvar"]: _simple("sub_1402D0AC0", "i"),
    }
    return {"args": [r.choice([0, 0, 0, 1])], "setup": setup, "fakes": fakes}


def _early_input(r):
    ret = r.choice([0, 1, 1])
    has_next = r.choice([1, 1, 0])
    pe = bytes(r.getrandbits(8) for _ in range(0x2C))
    saved = bytes(r.getrandbits(8) for _ in range(0x2C))

    def internal(mu):
        _log("CG_PredictPlayerState_Internal", arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF)
        mu.mem_write(va("cgArray") + 0x128, bytes(b ^ 0x5A for b in pe))  # the replay changes pe
        return ret

    def setup(w):
        CURRENT["m"] = w.m
        cg = va("cgArray")
        w.u64(cg + CG_NEXTSNAP, SNAP if has_next else 0)
        w.write(cg + 0x128, pe)
        w.write(cg + CG_SAVED + 0x4C, saved)
    return {"args": [], "setup": setup, "fakes": {SYM["internal"]: internal}}


def _getusercmd_input(r):
    current = r.choice([0, 127, 128, 1000, 0x7FFFFFFF, -0x80000000, r.getrandbits(31)])
    n = (current + r.choice([0, -1, -126, -127, -128, -129, 1, 5, -1000, 0x40000000])) & 0xFFFFFFFF
    n = n - (1 << 32) if n >= 1 << 31 else n
    ring = bytes(r.getrandbits(8) for _ in range(128 * CMD_SIZE))

    def setup(w):
        CURRENT["m"] = w.m
        cl = va("clients")
        w.write(cl + CL_CMDS, ring)
        w.u32(cl + CL_CMDNUMBER, current)
    return {"args": [0, n, bytes(CMD_SIZE)], "setup": setup,
            "fakes": {SYM["com_error"]: _simple("Com_Error", "isii")}}


def _cl_state_input(r, args):
    current = r.getrandbits(32)
    server_time = r.getrandbits(32)

    def setup(w):
        cl = va("clients")
        w.u32(cl + CL_CMDNUMBER, current)
        w.u32(cl + CL_SERVERTIME, server_time)
    return {"args": args, "setup": setup}


def _ps_buffer(r):
    return bytes(r.getrandbits(8) for _ in range(0x620))


def _save_input(r):
    ps = _ps_buffer(r)

    def setup(w):
        w.write(va("cgArray"), ps)
    return {"args": [r.choice([0, 1])], "setup": setup}


def _clear_saved_input(r):
    junk = bytes(r.getrandbits(8) for _ in range(0x78))
    pm_junk = bytes(r.getrandbits(8) for _ in range(PM_SIZE))
    lc = r.choice([0, 0, 1])

    def setup(w):
        w.write(va("cgArray") + CG_SAVED, junk)
        w.write(static(SRC, "cg_pmove") + PM_SIZE * lc, pm_junk)
    return {"args": [lc], "setup": setup}


def _build_items_input(r):
    count = r.choice([0, 1, 5, 40, -1, r.randint(0, 64)])
    numbers = [r.choice([r.randint(0, 0x7FF), 0x10, 0x11]) for _ in range(max(count, 0))]
    types = {n: r.choice([3, 3, 2, 0, 0x103]) for n in numbers}
    weapons = {n: r.choice([0, 0x100, 5, r.getrandbits(32)]) for n in numbers}
    lc = r.choice([0, 0, 1])
    old_count = r.getrandbits(8)

    def setup(w):
        mu = w.m.mu
        mu.mem_write(SNAP + 0x3C80, struct.pack("<i", count))
        for i, n in enumerate(numbers):
            mu.mem_write(SNAP + 0x3C88 + 0x108 * i, struct.pack("<i", n))
        ents = va("cg_entitiesArray")
        for n in numbers:
            w.write(ents + CENT_SIZE * n + 0xFC, struct.pack("<i", types[n]))
            w.write(ents + CENT_SIZE * n + 0x1BC, struct.pack("<I", weapons[n]))
        w.u32(static(SRC, "cg_itemEntityCount"), old_count)
    return {"args": [lc, SNAP], "setup": setup}


def _item_state_input(r, args):
    count, lcn = r.getrandbits(32), r.getrandbits(32)

    def setup(w):
        w.u32(static(SRC, "cg_itemEntityCount"), count)
        w.u32(static(SRC, "cg_itemLocalClientNum"), lcn)
    return {"args": args, "setup": setup}


def _trans(r):
    return bytes(r.getrandbits(8) for _ in range(0x30))


r = random.Random(1012)
CASES = [
    {"symbol": SYM["internal"], "build": STORE, "ret": "int",
     "inputs": [_internal_input(r) for _ in range(2500)] + [_internal_input(r, True) for _ in range(60)]},
    {"symbol": "?CG_PredictPlayerState@@YAXW4LocalClientNum_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [_predict_input(r) for _ in range(1500)]},
    {"symbol": "?sub_1402D2410@@YAXXZ", "build": STORE, "ret": "void", "inputs": [_early_input(r) for _ in range(200)]},
    {"symbol": "?CL_GetUserCmd@@YAHW4LocalClientNum_t@@HPEAUusercmd_s@@@Z", "build": STORE, "ret": "int",
     "inputs": [_getusercmd_input(r) for _ in range(600)]},
    {"symbol": "?CL_GetCurrentCmdNumber@@YAHW4LocalClientNum_t@@@Z", "build": STORE, "ret": "int",
     "inputs": [_cl_state_input(r, [0]) for _ in range(50)]},
    {"symbol": "?CL_SetUserCmdOrigin@@YAXW4LocalClientNum_t@@PEBUplayerState_s@@PEBMM@Z", "build": STORE,
     "ret": "void", "inputs": [_cl_state_input(r, [0, _ps_buffer(r), bytes(12), ("f", _f(r, 0.0))]) for _ in range(300)]},
    {"symbol": "?sub_140306FD0@@YAXW4LocalClientNum_t@@PEBUPlayerVehicleState@@@Z", "build": STORE, "ret": "void",
     "inputs": [[0, bytes(r.getrandbits(8) for _ in range(0x68))] for _ in range(100)]},
    {"symbol": "?CG_SavePlayerState@@YAXW4LocalClientNum_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [_save_input(r) for _ in range(300)]},
    {"symbol": "?CG_ClearSavedPlayerState@@YAXW4LocalClientNum_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [_clear_saved_input(r) for _ in range(100)]},
    {"symbol": "?CG_ExtractTransPlayerState@@YAXPEBUplayerState_s@@PEAUtransPlayerState_t@@@Z", "build": STORE,
     "ret": "void", "inputs": [[_ps_buffer(r), _trans(r)] for _ in range(300)]},
    {"symbol": "?CG_ClearTransPlayerState@@YAXPEAUtransPlayerState_t@@@Z", "build": STORE, "ret": "void",
     "inputs": [[_trans(r)] for _ in range(50)]},
    {"symbol": "?CG_BuildItemList@@YAXW4LocalClientNum_t@@PEBUsnapshot_s@@@Z", "build": STORE, "ret": "void",
     "inputs": [_build_items_input(r) for _ in range(300)]},
    {"symbol": "?CG_ClearItemList@@YAXXZ", "build": STORE, "ret": "void",
     "inputs": [_item_state_input(r, []) for _ in range(30)]},
    {"symbol": "?CG_ItemListLocalClientNum@@YAHXZ", "build": STORE, "ret": "int",
     "inputs": [_item_state_input(r, []) for _ in range(30)]},
]
