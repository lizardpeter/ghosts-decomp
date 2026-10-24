"""Differential cases for the cgame's frame (cgame_mp/cg_view_mp.cpp: CG_DrawActiveFrame and CG_UpdateThirdPerson) and
the small functions it calls that are reconstructed with it (cgame/cg_shellshock.cpp, bgame/bg_misc.cpp,
cgame_mp/cg_ents_mp.cpp, client_mp/cl_main_mp.cpp, client/cl_keys.cpp), against the Store build.

CG_DrawActiveFrame: every callee is faked and logged with its arguments (stack pointers as 'ptr', the vectors and
strings they pass by pointer as their contents), so the order of the ~110 calls and what each gets are compared. The
fakes that return something or write state do it from a per-input script: CG_ProcessSnapshots may enter or leave the
kill cam or drop the next snapshot, CG_AddPacketEntities returns up to six delayed entities and sets the jammer's
distance, CG_TransitionPlayerState counts events 0x3A, the trace returns a fraction (1, below 1, NaN), the turret
functions pick a scratch weapon definition, the weapon-select functions accept or refuse, the card lookups return
fake materials. The inputs vary the frame's time against cg.time (forward, equal, backwards), renderScreen, the next
snapshot (missing, snapFlags 2, 0 to 5 entities), the server's map load, the shell shock (snapshot index or the test
shock), third person and the vehicle view, the radar jam (blocked, level, distance -1, below min, between, above
max, NaN; min == max; the sine curve; strength -4..1), the first-person scene's conditions (EMP, kill cam types,
otherFlags 8/0x400000/0x1000, the weapon test), the remote camera reverb, location selection (catcher on or off,
gamepad), the kick (otherFlags 0x4000), the turret FOV (scope zoom with forward/back keys and its clamps, hip/ADS
blend, the zoom sound), the kill cam entity cache, the periodic effect, the timed flag, the weapon selection repair,
the underbarrel alternate, 18 clients' player cards (valid or not, cached or changed), and the eye/view distances.
"""
import random
import struct

from harness import SCRATCH
from syms import va
from win32_display import CURRENT, arg, farg, log_value

STORE = "iw6mp64_MSStore_ship"
CENT = 0x238
SNAP = SCRATCH + 0x10000       # the next snapshot
SNAP0 = SCRATCH + 0x20000      # the current snapshot
DVARS = SCRATCH + 0x30000
WEAPDEF = SCRATCH + 0x40000    # a turret's WeaponDef
OBJ = SCRATCH + 0x50000        # fake DObj handles
STRINGS = SCRATCH + 0x60000
PARMS = SCRATCH + 0x70000      # fake shellshock parms

# cg_s offsets
CG_CLIENTNUM, CG_LC = 0x3360, 0x3364
CG_SNAP, CG_NEXTSNAP = 0x3388, 0x3390
CG_FRAMETIME, CG_TIME, CG_OLDTIME = 0x7188C, 0x71890, 0x71894
CG_FOLLOW3P, CG_3P = 0x718A8, 0x718AC
CG_REFDEF, CG_TANX, CG_VIEWORG, CG_BASEORG = 0x718C8, 0x718D8, 0x718E0, 0x71914
CG_TIMEDFLAG = 0x71A48
CG_WEAPSEL = 0xB2768
CG_SHOCK, CG_TESTSHOCK = 0xB5310, 0xB5340
CG_KILLCAM, CG_KILLCAMTYPE, CG_KILLCAMENT, CG_LOOKAT = 0xB537C, 0xB5394, 0xB5398, 0xB53B8
CG_CHARINFO, CG_CLIENTINFO = 0xFAEB8, 0x10A428
CG_FIRSTPERSON, CG_MISSILECAM = 0x10E79E, 0x10E79F
CG_JAM, CG_JAMDIST, CG_TURRETFOV, CG_SCENEPTR = 0x10EDBC, 0x10EDC0, 0x10EDC4, 0x10EDF0
CG_REMOTEORG, CG_CARDS, CG_VEHICLEVIEW = 0x10EE58, 0x10EE68, 0x10F058

SYM = {
    "CG_DrawActiveFrame": "?CG_DrawActiveFrame@@YAHW4LocalClientNum_t@@HW4DemoType@@W4CubemapShot@@HHH@Z",
    "CG_UpdateThirdPerson": "?CG_UpdateThirdPerson@@YAXW4LocalClientNum_t@@@Z",
}

# every callee of CG_DrawActiveFrame: (decorated name, short name, argument letters)
CALLEES = [
    ("?sub_140654BA0@@YAXXZ", "sub_140654BA0", ""),
    ("?sub_140654C40@@YAXW4LocalClientNum_t@@@Z", "sub_140654C40", "i"),
    ("?sub_1402BE670@@YAXXZ", "sub_1402BE670", ""),
    ("?sub_1403A0030@@YAXW4LocalClientNum_t@@H@Z", "sub_1403A0030", "ii"),
    ("?sub_1403AEFF0@@YAXW4LocalClientNum_t@@@Z", "sub_1403AEFF0", "i"),
    ("?sub_1403447B0@@YAXXZ", "sub_1403447B0", ""),
    ("?sub_14029EDB0@@YAXW4LocalClientNum_t@@@Z", "sub_14029EDB0", "i"),
    ("?FX_RewindTo@@YAXW4LocalClientNum_t@@HH@Z", "FX_RewindTo", "iii"),
    ("?CL_SetWaitingOnServerToLoadMap@@YAXW4LocalClientNum_t@@_N@Z", "CL_SetWaitingOnServerToLoadMap", "ib"),
    ("?sub_1402D3230@@YAXW4LocalClientNum_t@@@Z", "sub_1402D3230", "i"),
    ("?sub_140316200@@YAXXZ", "sub_140316200", ""),
    ("?sub_14018A640@@YAXW4LocalClientNum_t@@@Z", "sub_14018A640", "i"),
    ("?R_SetLodOrigin@@YAXPEBXM@Z", "R_SetLodOrigin", "pf"),
    ("?CG_CompassIncreaseRadarTime@@YAXW4LocalClientNum_t@@@Z", "CG_CompassIncreaseRadarTime", "i"),
    ("?FX_SetNextUpdateTime@@YAXW4LocalClientNum_t@@H@Z", "FX_SetNextUpdateTime", "ii"),
    ("?CG_StartShellShock@@YAXPEAUcg_s@@PEBUshellshock_parms_t@@HH@Z", "CG_StartShellShock", "ppii"),
    ("?CG_UpdateShellShock@@YAXW4LocalClientNum_t@@PEBUshellshock_parms_t@@HH@Z", "CG_UpdateShellShock", "ipii"),
    ("?CG_UpdateThirdPerson@@YAXW4LocalClientNum_t@@@Z", "CG_UpdateThirdPerson", "i"),
    ("?sub_1402EA200@@YAXW4LocalClientNum_t@@_N@Z", "sub_1402EA200", "ib"),
    ("?sub_1403046D0@@YAXW4LocalClientNum_t@@H@Z", "sub_1403046D0", "ii"),
    ("?CG_ClearHudGrenades@@YAXPEAUcg_s@@@Z", "CG_ClearHudGrenades", "p"),
    ("?CG_DObjUpdateInfo@@YAXPEBUcg_s@@PEAUDObj@@_N@Z", "CG_DObjUpdateInfo", "ppb"),
    ("?CG_ProcessClientNoteTracks@@YAXPEAUcg_s@@H@Z", "CG_ProcessClientNoteTracks", "pi"),
    ("?sub_140178750@@YAXW4LocalClientNum_t@@@Z", "sub_140178750", "i"),
    ("?sub_1402EC410@@YAXW4LocalClientNum_t@@@Z", "sub_1402EC410", "i"),
    ("?sub_140377D80@@YAXXZ", "sub_140377D80", ""),
    ("?sub_1402D4BF0@@YAXW4LocalClientNum_t@@@Z", "sub_1402D4BF0", "i"),
    ("?sub_1402E61B0@@YAXW4LocalClientNum_t@@@Z", "sub_1402E61B0", "i"),
    ("?sub_1402FB790@@YAXXZ", "sub_1402FB790", ""),
    ("?sub_1402F11D0@@YAXW4LocalClientNum_t@@PEAXH@Z", "sub_1402F11D0", "ipi"),
    ("?sub_1401B3710@@YAXH@Z", "sub_1401B3710", "i"),
    ("?sub_1401B2960@@YAXW4LocalClientNum_t@@MMPEBXH@Z", "sub_1401B2960", "iffpi"),
    ("?sub_14065BE30@@YAXXZ", "sub_14065BE30", ""),
    ("?sub_1402D2410@@YAXXZ", "sub_1402D2410", ""),
    ("?CL_SyncGpu@@YAXP6AH_K@Z@Z", "CL_SyncGpu", "q"),
    ("?sub_140376E30@@YAXH@Z", "sub_140376E30", "i"),
    ("?R_ToggleSmpFrame@@YAXXZ", "R_ToggleSmpFrame", ""),
    ("?CL_Input@@YAXW4LocalClientNum_t@@@Z", "CL_Input", "i"),
    ("?sub_1402AA2A0@@YAXW4LocalClientNum_t@@@Z", "sub_1402AA2A0", "i"),
    ("?CG_PredictPlayerState@@YAXW4LocalClientNum_t@@@Z", "CG_PredictPlayerState", "i"),
    ("?sub_1402FC4F0@@YAXW4LocalClientNum_t@@@Z", "sub_1402FC4F0", "i"),
    ("?sub_1402FBC30@@YAXW4LocalClientNum_t@@PEAUXModel@@@Z", "sub_1402FBC30", "iq"),
    ("?sub_140658100@@YAXXZ", "sub_140658100", ""),
    ("?CG_ProcessEntity@@YAXW4LocalClientNum_t@@H@Z", "CG_ProcessEntity", "ii"),
    ("?CG_CheckEntEvents@@YAXW4LocalClientNum_t@@PEAUcentity_s@@H@Z", "CG_CheckEntEvents", "ipi"),
    ("?CG_EntityEvent@@YAXW4LocalClientNum_t@@PEAUcentity_s@@HH_N@Z", "CG_EntityEvent", "ipiib"),
    ("?sub_1402CEB10@@YAXW4LocalClientNum_t@@@Z", "sub_1402CEB10", "i"),
    ("?sub_1403AF520@@YAXW4LocalClientNum_t@@@Z", "sub_1403AF520", "i"),
    ("?sub_140471E70@@YAXW4LocalClientNum_t@@H@Z", "sub_140471E70", "ii"),
    ("?sub_14037E3D0@@YAXW4LocalClientNum_t@@@Z", "sub_14037E3D0", "i"),
    ("?sub_140588090@@YAXHH@Z", "sub_140588090", "ii"),
    ("?sub_14019B2C0@@YAXM@Z", "sub_14019B2C0", "f"),
    ("?sub_14065B690@@YAXW4LocalClientNum_t@@H_N1@Z", "sub_14065B690", "iibb"),
    ("?sub_140657FC0@@YAX_N0PEBX0@Z", "sub_140657FC0", "bbqb"),
    ("?SND_SetEnvironmentEffects@@YAXHPEBDMMH@Z", "SND_SetEnvironmentEffects", "isffi"),
    ("?SND_DeactivateEnvironmentEffects@@YAXHH@Z", "SND_DeactivateEnvironmentEffects", "ii"),
    ("?Key_RemoveCatcher@@YAXW4LocalClientNum_t@@H@Z", "Key_RemoveCatcher", "ii"),
    ("?Key_AddCatcher@@YAXW4LocalClientNum_t@@H@Z", "Key_AddCatcher", "ii"),
    ("?sub_1402EF6B0@@YAXW4LocalClientNum_t@@@Z", "sub_1402EF6B0", "i"),
    ("?CL_SendCmd@@YAXW4LocalClientNum_t@@@Z", "CL_SendCmd", "i"),
    ("?sub_1402C1130@@YAHW4LocalClientNum_t@@PEBX@Z", "sub_1402C1130", "iq"),
    ("?CG_UpdateViewWeaponAnim@@YAXW4LocalClientNum_t@@@Z", "CG_UpdateViewWeaponAnim", "i"),
    ("?CG_CalcViewValues@@YAXW4LocalClientNum_t@@@Z", "CG_CalcViewValues", "i"),
    ("?LerpKillCamView@@YAXW4LocalClientNum_t@@@Z", "LerpKillCamView", "i"),
    ("?sub_1402FC790@@YAXW4LocalClientNum_t@@@Z", "sub_1402FC790", "i"),
    ("?CG_AddViewWeapon@@YAXW4LocalClientNum_t@@@Z", "CG_AddViewWeapon", "i"),
    ("?sub_1402AD490@@YAXW4LocalClientNum_t@@@Z", "sub_1402AD490", "i"),
    ("?sub_140654E80@@YAXXZ", "sub_140654E80", ""),
    ("?FX_SetNextUpdateCamera@@YAXW4LocalClientNum_t@@PEBXPEBMM_N@Z", "FX_SetNextUpdateCamera", "ippfb"),
    ("?sub_1402D4820@@YAXW4LocalClientNum_t@@HPEBM@Z", "sub_1402D4820", "iip"),
    ("?sub_140275D90@@YAXW4LocalClientNum_t@@@Z", "sub_140275D90", "i"),
    ("?sub_140655200@@YAXXZ", "sub_140655200", ""),
    ("?sub_1402C5740@@YAXW4LocalClientNum_t@@@Z", "sub_1402C5740", "i"),
    ("?sub_1402BE7B0@@YAXW4LocalClientNum_t@@@Z", "sub_1402BE7B0", "i"),
    ("?sub_1403AF710@@YAXW4LocalClientNum_t@@@Z", "sub_1403AF710", "i"),
    ("?sub_1403AF230@@YAXW4LocalClientNum_t@@@Z", "sub_1403AF230", "i"),
    ("?AimAssist_UpdateScreenTargets@@YAXW4LocalClientNum_t@@PEBM11MM@Z", "AimAssist_UpdateScreenTargets", "ippp"),
    ("?CG_UpdateSceneDepthOfField@@YAXW4LocalClientNum_t@@@Z", "CG_UpdateSceneDepthOfField", "i"),
    ("?sub_14037AE50@@YAXPEBX@Z", "sub_14037AE50", "q"),
    ("?sub_1405E8170@@YAXW4LocalClientNum_t@@@Z", "sub_1405E8170", "i"),
    ("?CG_DrawActive@@YAXW4LocalClientNum_t@@H@Z", "CG_DrawActive", "ii"),
    ("?sub_140179B50@@YAXW4LocalClientNum_t@@@Z", "sub_140179B50", "i"),
    ("?sub_1406A6C80@@YAXXZ", "sub_1406A6C80", ""),
    ("__dyn_tls_on_demand_init", "__dyn_tls_on_demand_init", ""),
]


def _m():
    return CURRENT.get("m")


def _log(*entry):
    m = _m()
    if m is not None:
        m.observed.append(entry)


def _rd(mu, a, n):
    return bytes(mu.mem_read(a, n))


def _ri(mu, a):
    return struct.unpack("<i", _rd(mu, a, 4))[0]


def _wi(mu, a, v):
    mu.mem_write(a, struct.pack("<I", v & 0xFFFFFFFF))


def _ret(mu, v):
    from unicorn.x86_const import UC_X86_REG_RAX
    mu.reg_write(UC_X86_REG_RAX, v & 0xFFFFFFFFFFFFFFFF)


def _logged(name, sig, result=None):
    def run(mu):
        _log("call", name, *(log_value(mu, c, i) for i, c in enumerate(sig)))
        return result(mu) if callable(result) else result
    return run


def _fbits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _f(r, *common):
    return r.choice([*common, float("nan"), r.uniform(-500, 500), r.uniform(-1, 1)])


def _dvar(w, slot, raw4):
    a = DVARS + 0x40 * slot
    w.m.mu.mem_write(a + 0x10, raw4)
    return a


class Script:
    """Per-input fake behaviour; reset at every setup so both runs see the same sequence."""

    def __init__(self, r):
        self.r = r
        self.snapshots = r.choice(["none", "none", "none", "killcam", "drop", "unkill"])
        self.loading = r.random() < 0.05
        self.scrcam = r.choice([0, 0, 0, 1])
        self.dobjs = [r.choice([0, OBJ + 0x100 * i]) for i in range(8)]
        self.delayed = [r.choice([3, 5, 0x40, 0x7FE]) for _ in range(r.choice([0, 0, 1, 2, 6]))]
        self.jam_distance = r.choice([None, None, -1.0, 100.0, 500.0, 900.0, 1e6, 0.0, -5.0, float("nan")])
        self.events = r.choice([0, 0, 1, 3])
        self.emp = r.choice([0, 0, 0, 1])
        self.weapon_ok = r.choice([0, 1, 1])
        self.catcher = r.choice([0, 1])
        self.gamepad = r.choice([0, 1])
        self.turret = r.choice([0, 0, 1, 0x102])
        self.scope = r.choice([0, 1])
        self.forward = r.choice([0, 127, -127, 50, -128, -1])
        self.fraction = r.choice([1.0, 0.5, 0.0, 0.25, float("nan"), 2.0])
        self.numweapons = r.choice([0, 1, 10, 255, 256])
        self.select = [r.choice([0, 0, 1]) for _ in range(16)]
        self.underbarrel = r.choice([0, 1])
        self.df740, self.df750 = r.choice([0, 1]), r.choice([0, 1])
        self.zfar = r.choice([0.0, 4000.0, float("nan")])
        self.c5700 = r.choice([0, 1])
        self.cf440 = r.choice([0, 1])
        self.reset()

    def reset(self):
        self.select_calls = 0


def _fakes(script):
    f = {sym: _logged(name, sig) for sym, name, sig in CALLEES}

    def memset(mu):
        d, v, n = arg(mu, 0), arg(mu, 1) & 0xFF, arg(mu, 2)
        _log("call", "sub_140536260", log_value(mu, "p", 0), v, n)
        mu.mem_write(d, bytes([v]) * n)
    f["?sub_140536260@@YAXPEAXH_K@Z"] = memset

    def predicted(mu):
        _log("call", "CG_GetPredictedPlayerState", arg(mu, 0) & 0xFFFFFFFF)
        return va("cgArray")
    f["?CG_GetPredictedPlayerState@@YAPEBUplayerState_s@@W4LocalClientNum_t@@@Z"] = predicted

    def snapshots(mu):
        _log("call", "CG_ProcessSnapshots", arg(mu, 0) & 0xFFFFFFFF)
        cg = va("cgArray")
        if script.snapshots == "killcam":
            _wi(mu, cg + CG_KILLCAM, 1)
        elif script.snapshots == "unkill":
            _wi(mu, cg + CG_KILLCAM, 0)
        elif script.snapshots == "drop":
            mu.mem_write(cg + CG_NEXTSNAP, bytes(8))
    f["?CG_ProcessSnapshots@@YAXW4LocalClientNum_t@@@Z"] = snapshots
    f["?CL_IsServerLoadingMap@@YA_NXZ"] = _logged("CL_IsServerLoadingMap", "", lambda mu: int(script.loading))
    f["?sub_140187D70@@YAHW4LocalClientNum_t@@@Z"] = _logged("sub_140187D70", "i", lambda mu: script.scrcam)

    def shock_parms(mu):
        i = arg(mu, 0) & 0xFFFFFFFF
        _log("call", "BG_GetShellshockParms", i)
        return PARMS + 0x10 * (i & 0xFF)
    f["?BG_GetShellshockParms@@YAPEAUshellshock_parms_t@@H@Z"] = shock_parms

    def dobj(mu):
        h, lc = arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF
        _log("call", "Com_GetClientDObj", h, lc)
        return script.dobjs[h % len(script.dobjs)]
    f["?Com_GetClientDObj@@YAPEAUDObj@@HW4LocalClientNum_t@@@Z"] = dobj

    def packet_entities(mu):
        lc, out = arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1)
        _log("call", "CG_AddPacketEntities", lc, log_value(mu, "p", 1))
        for i, n in enumerate(script.delayed):
            mu.mem_write(out + 4 * i, struct.pack("<i", n))
        if script.jam_distance is not None:
            mu.mem_write(va("cgArray") + CG_JAMDIST, struct.pack("<f", script.jam_distance))
        return len(script.delayed)
    f["?CG_AddPacketEntities@@YAHW4LocalClientNum_t@@PEAH@Z"] = packet_entities

    def model_name(mu):
        _log("call", "sub_14018DB60", *(log_value(mu, c, i) for i, c in enumerate("iqqii")))
        return STRINGS
    f["?sub_14018DB60@@YAPEBDW4LocalClientNum_t@@PEBUclientInfo_t@@PEBUcharacterInfo_t@@HH@Z"] = model_name
    f["?R_RegisterModel@@YAPEAUXModel@@PEBD@Z"] = _logged("R_RegisterModel", "s", 0x77770000)
    f["?sub_14017F630@@YA_NW4LocalClientNum_t@@@Z"] = _logged("sub_14017F630", "i", lambda mu: script.scrcam)

    def transition(mu):
        _log("call", "CG_TransitionPlayerState", *(log_value(mu, c, i) for i, c in enumerate("ipp")))
        a = va("unk_143C23F68")
        _wi(mu, a, _ri(mu, a) + script.events)
    f["?CG_TransitionPlayerState@@YAXW4LocalClientNum_t@@PEAUplayerState_s@@PEBUtransPlayerState_t@@@Z"] = transition
    f["?sub_1402CF440@@YAHW4LocalClientNum_t@@@Z"] = _logged("sub_1402CF440", "i", lambda mu: script.cf440)
    f["?sub_1402DF740@@YA_NW4LocalClientNum_t@@@Z"] = _logged("sub_1402DF740", "i", lambda mu: script.df740)
    f["?sub_1402DF750@@YA_NW4LocalClientNum_t@@@Z"] = _logged("sub_1402DF750", "i", lambda mu: script.df750)
    f["?BG_IsEMPJammed@@YAHPEBUplayerState_s@@@Z"] = _logged("BG_IsEMPJammed", "p", lambda mu: script.emp)
    f["?sub_1402EF4D0@@YA_NW4LocalClientNum_t@@PEBUcg_s@@@Z"] = _logged("sub_1402EF4D0", "ip",
                                                                      lambda mu: script.weapon_ok)
    f["?Key_IsCatcherActive@@YA_NW4LocalClientNum_t@@H@Z"] = _logged("Key_IsCatcherActive", "ii",
                                                                   lambda mu: script.catcher)
    f["?CL_IsGamepadEnabled@@YA_NW4LocalClientNum_t@@@Z"] = _logged("CL_IsGamepadEnabled", "i",
                                                                  lambda mu: script.gamepad)

    def kick(mu):
        ps, msec, vel, ang = arg(mu, 0), arg(mu, 1) & 0xFFFFFFFF, arg(mu, 2), arg(mu, 3)
        _log("call", "BG_KickAngles", ps, msec, vel, ang)
        mu.mem_write(ang, struct.pack("<f", float(msec)))
    f["?BG_KickAngles@@YAXPEBUplayerState_s@@HQEAM1@Z"] = kick
    f["?sub_1402F8530@@YAIPEBUcg_s@@W4LocalClientNum_t@@@Z"] = _logged("sub_1402F8530", "pi", lambda mu: script.turret)
    f["?sub_1402F86E0@@YA_NW4LocalClientNum_t@@@Z"] = _logged("sub_1402F86E0", "i", lambda mu: script.scope)
    f["?CL_GetCurrentCmdNumber@@YAHW4LocalClientNum_t@@@Z"] = _logged("CL_GetCurrentCmdNumber", "i", 1234)

    def usercmd(mu):
        _log("call", "CL_GetUserCmd", arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF, log_value(mu, "p", 2))
        cmd = bytearray(0x3C)
        cmd[0x1C] = script.forward & 0xFF
        cmd[0x1D] = 0x55
        mu.mem_write(arg(mu, 2), bytes(cmd))
        return 1
    f["?CL_GetUserCmd@@YAHW4LocalClientNum_t@@HPEAUusercmd_s@@@Z"] = usercmd
    f["?sub_14060DC10@@YAMXZ"] = _zfar(script)
    f["?sub_14039AC00@@YAPEBUFxEffectDef@@PEBD@Z"] = _logged("sub_14039AC00", "s", 0x66660000)

    def oriented(mu):
        lc, d, t, org, axis = (arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1), arg(mu, 2) & 0xFFFFFFFF, arg(mu, 3), arg(mu, 4))
        _log("call", "FX_PlayOrientedEffect", lc, d, t, org, _rd(mu, axis, 36))
    f["?FX_PlayOrientedEffect@@YAXW4LocalClientNum_t@@PEBUFxEffectDef@@HQEBMQEAY02$$CBM@Z"] = oriented

    def trace(mu):
        res, start, end, bounds = arg(mu, 0), arg(mu, 1), arg(mu, 2), arg(mu, 3)
        _log("call", "trace", log_value(mu, "p", 0), start, _rd(mu, end, 12), _rd(mu, bounds, 24),
             arg(mu, 4) & 0xFFFFFFFF, arg(mu, 5) & 0xFFFFFFFF)
        mu.mem_write(res, struct.pack("<f", script.fraction) + bytes(0x28))
    f["?sub_140304650@@YAXPEAUtrace_t@@PEBM1PEBUBounds@@HH@Z"] = trace
    f["?sub_1402C5700@@YA_NW4LocalClientNum_t@@@Z"] = _logged("sub_1402C5700", "i", lambda mu: script.c5700)
    f["?BG_GetNumWeapons@@YAIXZ"] = _logged("BG_GetNumWeapons", "", lambda mu: script.numweapons)

    def select(mu):
        _log("call", "sub_1402F8FC0", arg(mu, 0) & 0xFFFFFFFF, arg(mu, 1) & 0xFFFFFFFF, arg(mu, 2) & 0xFF)
        v = script.select[script.select_calls % len(script.select)]
        script.select_calls += 1
        return v
    f["?sub_1402F8FC0@@YA_NW4LocalClientNum_t@@TWeapon@@_N@Z"] = select
    f["?BG_OffhandIsUnderbarrelWeapon@@YAHPEBUplayerState_s@@I@Z"] = _logged("BG_OffhandIsUnderbarrelWeapon", "pi",
                                                                           lambda mu: script.underbarrel)
    f["?sub_1405D3080@@YAPEBXH@Z"] = _logged("sub_1405D3080", "i", lambda mu: 0x55000000 + (arg(mu, 0) & 0xFFFF))
    f["?sub_1405D2FD0@@YAPEBXH@Z"] = _logged("sub_1405D2FD0", "i", lambda mu: 0x56000000 + (arg(mu, 0) & 0xFFFF))
    return f


def _zfar(script):
    def run(mu):
        from unicorn.x86_const import UC_X86_REG_XMM0
        _log("call", "sub_14060DC10")
        mu.reg_write(UC_X86_REG_XMM0, _fbits(script.zfar))
        return None
    return run


def _frame_input(r):
    script = Script(r)
    now = r.choice([1000, 50000, 0x7FFFFF00, r.randint(0, 1 << 30)])
    server_time = (now + r.choice([0, 1, 7, 16, 50, -1, -100, 0x7FFFFFFF])) & 0xFFFFFFFF
    render = r.choice([1, 1, 1, 1, 1, 0, 2])
    draw_render = r.choice([0, 1, 2, r.getrandbits(31)])
    demo, cube, size = r.choice([0, 0, 1, 2]), r.choice([0, 0, 3]), r.getrandbits(16)
    has_next = r.random() < 0.95
    snap_flags = r.choice([0, 0, 0, 0, 2, 1, 0x100])
    entities = [r.choice([0, 1, 2, 7, 0x40, 0x7FE]) for _ in range(r.choice([0, 1, 2, 5]))]
    shock_index = r.choice([0, 0, 1, 7])
    pm_type = r.choice([0, 0, 1, 2, 5, 7, 8])
    other = 0
    for bit in (2, 8, 0x20, 0x1000, 0x2000, 0x4000, 0x400000, 0x8000000, 0x200000):
        if r.random() < 0.3:
            other |= bit
    if r.random() < 0.6:
        other |= 0x4000
    link = r.choice([0, 0, 4])
    vehicle = r.choice([0x7FF, 0x7FF, 0x51])
    viewlocked = r.choice([0x7FF, 0x7FF, 0x52])
    client = r.choice([0, 3, 17])
    viewmodel = r.choice([0, 0, 1, 5, -1])
    radar_blocked = r.choice([0, 0, 1])
    radar_strength = r.choice([-4, -3, -2, -1, 0, 1])
    jam = r.choice([0.0, 0.0, 0.5, 1.0, 0.95, -0.1, 1.2, float("nan")])
    jam_min = r.choice([200.0, 200.0, 800.0, float("nan")])
    jam_max = r.choice([800.0, 800.0, 200.0, 1000.0])
    sincurve = r.choice([0, 1])
    loc_info = r.choice([0, 0, 1, 0x80])
    weapons = [r.choice([0, 0, 1, 2, 0x103, 0x200]) for _ in range(15)]
    equipped = bytes(r.choice([0, 1]) for _ in range(15 * 16))  # PlayerEquippedWeaponState: bools
    weap_flags = r.choice([0, 0x80000, 0x4000, r.getrandbits(32)])
    pos_frac = r.choice([0.0, 1.0, 0.5, float("nan")])
    killcam = r.choice([0, 0, 0, 1])
    killcam_type = r.choice([0, 1, 2, 3, 7])
    killcam_ent, lookat_ent = r.choice([0x7FF, 0x60]), r.choice([0x7FF, 0x61])
    lookat_flags = r.choice([0, 1])
    weapsel = r.choice([1, 9, 0x100, 0xFF, 0x1234])
    weapsel_alt = r.choice([0, 0, 1])
    infos = [r.choice([0, 1]) for _ in range(18)]
    card_ids = [(r.getrandbits(16), r.getrandbits(16)) for _ in range(18)]
    cache = []
    for i in range(18):
        same = r.random() < 0.5
        ids = card_ids[i] if same else (r.getrandbits(16), r.getrandbits(16))
        mats = (r.choice([0, 0x51000000 + i]), r.choice([0, 0x52000000 + i]))
        cache.append(struct.pack("<HHIQQ", ids[0], ids[1], 0, *mats))
    turret_overlay = r.choice([2, 2, 0])
    zoom_rate, zoom_min, zoom_max = r.choice([10.0, -20.0]), r.choice([5.0, 30.0]), r.choice([60.0, 20.0])
    turret_fov = (r.choice([65.0, 40.0]), r.choice([20.0, float("nan")]))
    zoom_sound = r.choice([0, 0x12340000])
    turret_old = r.choice([30.0, 5.0, 60.0, float("nan")])
    effect_period = r.choice([0, 0, 500, -1])
    effect_last = (now - r.choice([0, 499, 500, 501, 5000])) & 0xFFFFFFFF
    timed = (r.choice([0, 1]), r.choice([0, 100, -1]), (now - r.choice([0, 100, 101])) & 0xFFFFFFFF)
    origin = [_f(r, 0.0, 100.0) for _ in range(3)]
    vieworg = [o + r.choice([0.0, 10.0, 1500.0, 3000.0, -2100.0]) if o == o else 0.0 for o in origin]
    view_height = r.choice([60.0, 0.0, float("nan")])
    remote_valid = r.choice([0, 1])
    first_person = r.choice([0, 1])
    missile_cam = r.choice([0, 0, 1])
    vehicle_view = r.choice([0, 1])
    follow3p = r.choice([0, 1])
    flag_177fc = r.choice([0, 1])
    room = r.choice([0, 1, 3])
    junk_cg = bytes(r.getrandbits(8) for _ in range(0x40))
    pm_flags, mantle_flags = r.getrandbits(32), r.getrandbits(32)
    scene_ptr = r.choice([0, 0x44440000])

    def setup(w):
        CURRENT["m"] = w.m
        script.reset()
        mu = w.m.mu
        cg, ents = va("cgArray"), va("cg_entitiesArray")
        ps = bytearray(0x620)
        struct.pack_into("<IiiIIi", ps, 0, 0, pm_type, 0, pm_flags, other, link)
        struct.pack_into("<3f", ps, 0x1C, *origin)
        struct.pack_into("<i", ps, 0xBC, vehicle)
        struct.pack_into("<ii", ps, 0x17C, client, viewmodel)
        struct.pack_into("<f", ps, 0x194, view_height)
        struct.pack_into("<i", ps, 0x1E8, viewlocked)
        struct.pack_into("<i", ps, 0x228, radar_blocked)
        struct.pack_into("<i", ps, 0x230, radar_strength)
        struct.pack_into("<i", ps, 0x23C, loc_info)
        struct.pack_into("<I", ps, 0x270, mantle_flags)
        struct.pack_into("<15I", ps, 0x2E4, *weapons)
        ps[0x320:0x320 + 15 * 16] = equipped
        struct.pack_into("<If", ps, 0x420, weap_flags, pos_frac)
        w.write(cg, bytes(ps))
        w.write(cg + CG_CLIENTNUM, struct.pack("<ii", client, 0))
        w.u64(cg + CG_SNAP, SNAP0)
        w.u64(cg + CG_NEXTSNAP, SNAP if has_next else 0)
        snap0 = bytearray(0x3C90)
        struct.pack_into("<iii", snap0, 0xE9C, shock_index, (now - 100) & 0xFFFFFFFF, 3000)
        mu.mem_write(SNAP0, bytes(snap0))
        snap = bytearray(0x3C88 + 0x108 * 6)
        struct.pack_into("<IIi", snap, 0, 0, pm_type, 0)
        struct.pack_into("<I", snap, 0x10, other)
        struct.pack_into("<i", snap, 0x14, link)
        struct.pack_into("<i", snap, 0x3C74, snap_flags)
        struct.pack_into("<i", snap, 0x3C80, len(entities))
        for i, n in enumerate(entities):
            struct.pack_into("<i", snap, 0x3C88 + 0x108 * i, n)
        mu.mem_write(SNAP, bytes(snap))
        w.u32(cg + CG_TIME, now)
        w.u32(cg + CG_OLDTIME, (now - 9) & 0xFFFFFFFF)
        w.u32(cg + CG_FOLLOW3P, follow3p)
        w.write(cg + CG_TANX, struct.pack("<2f", 0.6, 0.45))
        w.write(cg + CG_VIEWORG, struct.pack("<3f", *vieworg))
        w.write(cg + CG_BASEORG, struct.pack("<3f", *(v + 1.0 for v in vieworg)))
        w.write(cg + CG_TIMEDFLAG, struct.pack("<IiiB", timed[2], 0, timed[1], timed[0]))
        w.write(cg + CG_WEAPSEL, struct.pack("<Ii", weapsel, weapsel_alt))
        w.write(cg + CG_TESTSHOCK, struct.pack("<ii", (now - 50) & 0xFFFFFFFF, 500))
        w.write(cg + CG_KILLCAM, struct.pack("<i", killcam))
        w.write(cg + CG_KILLCAMTYPE, struct.pack("<ii", killcam_type, killcam_ent))
        w.write(cg + CG_LOOKAT, struct.pack("<i", lookat_ent))
        for i in range(18):
            w.write(cg + CG_CHARINFO + 0x5D8 * i + 4, struct.pack("<i", infos[i]))
            w.write(cg + CG_CLIENTINFO + 0x70 * i + 0x34, struct.pack("<HHH", card_ids[i][0], 0, card_ids[i][1]))
            w.write(cg + CG_CARDS + 0x18 * i, cache[i])
        w.write(cg + CG_FIRSTPERSON, bytes([first_person, missile_cam]))
        w.write(cg + CG_JAM, struct.pack("<3f", jam, 123.0, turret_old))
        w.u64(cg + CG_SCENEPTR, scene_ptr)
        w.write(cg + CG_REMOTEORG, struct.pack("<3fB", 1.5, 2.5, 3.5, remote_valid))
        w.write(cg + CG_VEHICLEVIEW, bytes([vehicle_view]))
        w.write(cg + 0x10E831, bytes([1]))
        w.write(cg + 0xA9760, junk_cg)
        for n, flags in ((0x60, 1), (0x61, lookat_flags)):
            e = ents + CENT * n
            w.write(e + 0x18, struct.pack("<6f", 10.0 + n, 20.0, 30.0, 1.0, 2.0, 3.0))
            w.write(e + 0x200, struct.pack("<I", flags))
        w.u64(va("radarjamDistMin"), _dvar(w, 0, struct.pack("<f", jam_min)))
        w.u64(va("radarjamDistMax"), _dvar(w, 1, struct.pack("<f", jam_max)))
        w.u64(va("radarjamSinCurve"), _dvar(w, 2, bytes([sincurve])))
        w.u64(va("RemoteCameraSounds_RoomType"), _dvar(w, 3, struct.pack("<i", room)))
        w.u64(va("RemoteCameraSounds_DryLevel"), _dvar(w, 4, struct.pack("<f", 0.25)))
        w.u64(va("RemoteCameraSounds_WetLevel"), _dvar(w, 5, struct.pack("<f", 0.75)))
        weapdef = bytearray(0x970)
        struct.pack_into("<Q", weapdef, 0x138, zoom_sound)
        struct.pack_into("<i", weapdef, 0x5E8, turret_overlay)
        struct.pack_into("<5f", weapdef, 0x950, *turret_fov, zoom_rate, zoom_min, zoom_max)
        mu.mem_write(WEAPDEF, bytes(weapdef))
        w.u64(va("bg_weaponDefs") + 8, WEAPDEF)
        w.u64(va("bg_weaponDefs") + 16, WEAPDEF)
        effect = va("unk_143E8E3F0")
        w.write(effect, b"fx/misc/blink\0")
        w.write(effect + 0x40, struct.pack("<3fIi", 4.0, 5.0, 6.0, effect_last, effect_period))
        w.u32(va("unk_143C177FC"), flag_177fc)
        w.u64(va("unk_143C17818"), 0x33330000)
        mu.mem_write(STRINGS, b"viewhands_test\0")

    return {"args": [0, server_time, demo, cube, size, render, draw_render], "setup": setup,
            "fakes": _fakes(script)}


def _third_person_input(r):
    pm_type = r.choice([0, 0, 6, 7, 8, -1])
    other = r.choice([0, 0x2000, 0x2002, 0x8002000, 0x8000000, r.getrandbits(32)])
    link = r.choice([0, 4, 5])
    killcam, killcam_type = r.choice([0, 0, 1]), r.choice([0, 1, 3])
    scrcam = r.choice([0, 0, 1])
    follow = r.choice([0, 1, 7])
    has_next = r.random() < 0.97

    def setup(w):
        CURRENT["m"] = w.m
        cg = va("cgArray")
        snap = bytearray(0x20)
        struct.pack_into("<IiiIIi", snap, 0, 0, pm_type, 0, 0, other, link)
        w.m.mu.mem_write(SNAP, bytes(snap))
        w.u64(cg + CG_NEXTSNAP, SNAP if has_next else 0)
        w.u32(cg + CG_KILLCAM, killcam)
        w.u32(cg + CG_KILLCAMTYPE, killcam_type)
        w.u32(cg + CG_FOLLOW3P, follow)
        w.u32(cg + CG_3P, 0x5A5A)
    return {"args": [0], "setup": setup,
            "fakes": {"?sub_140187D70@@YAHW4LocalClientNum_t@@@Z": _logged("sub_140187D70", "i", scrcam)}}


def _cg_buffer(r, size, frametime=None):
    """A cg_s passed by pointer: random bytes where the function reads and writes, zero elsewhere."""
    buf = bytearray(size)
    buf[CG_SHOCK:CG_SHOCK + 0x10] = bytes(r.getrandbits(8) for _ in range(0x10))
    if frametime is not None:
        struct.pack_into("<I", buf, CG_FRAMETIME, frametime & 0xFFFFFFFF)
    return bytes(buf)


def _dobj_input(r):
    frametime = r.choice([0, 1, 16, 17, -5, 0x7FFFFFFF, -0x80000000, r.getrandbits(32)])
    return {"args": [_cg_buffer(r, 0x71890, frametime), r.choice([0, 0x123456, r.getrandbits(48)]),
                     r.choice([0, 1, 0x100, 0xFF])],
            "setup": _bind_machine,
            "fakes": {"?DObjUpdateClientInfo@@YAXPEAUDObj@@M_N@Z": _logged("DObjUpdateClientInfo", "qfb")}}


def _bind_machine(w):
    CURRENT["m"] = w.m


def _flag_input(r, args):
    # bools hold 0 or 1 (the original moves the raw byte, clang normalises: other values are not valid bools)
    old = bytes([r.choice([0, 1]) for _ in range(2)])
    catchers = r.getrandbits(32)

    def setup(w):
        w.write(va("unk_14416A0F8"), old)
        w.u32(va("clientUIActives") + 4, catchers)
    return {"args": args, "setup": setup}


r = random.Random(4816)
CASES = [
    {"symbol": SYM["CG_DrawActiveFrame"], "build": STORE, "ret": "int",
     "inputs": [_frame_input(r) for _ in range(1500)]},
    {"symbol": SYM["CG_UpdateThirdPerson"], "build": STORE, "ret": "void",
     "inputs": [_third_person_input(r) for _ in range(400)]},
    {"symbol": "?CG_StartShellShock@@YAXPEAUcg_s@@PEBUshellshock_parms_t@@HH@Z", "build": STORE, "ret": "void",
     "inputs": [[_cg_buffer(r, 0xB5330), r.getrandbits(48), r.getrandbits(32), r.getrandbits(32)] for _ in range(30)]},
    {"symbol": "?BG_GetShellshockParms@@YAPEAUshellshock_parms_t@@H@Z", "ret": "int64",
     "inputs": [[r.choice([0, 1, 5, 30, -1, r.getrandbits(31)])] for _ in range(60)]},
    {"symbol": "?CL_IsServerLoadingMap@@YA_NXZ", "build": STORE, "ret": "char",
     "inputs": [_flag_input(r, []) for _ in range(30)]},
    {"symbol": "?CL_SetWaitingOnServerToLoadMap@@YAXW4LocalClientNum_t@@_N@Z", "build": STORE, "ret": "void",
     "inputs": [_flag_input(r, [0, r.choice([0, 1])]) for _ in range(40)]},
    {"symbol": "?CG_DObjUpdateInfo@@YAXPEBUcg_s@@PEAUDObj@@_N@Z", "build": STORE, "ret": "void",
     "inputs": [_dobj_input(r) for _ in range(60)]},
    {"symbol": "?Key_AddCatcher@@YAXW4LocalClientNum_t@@H@Z", "build": STORE, "ret": "void",
     "inputs": [_flag_input(r, [0, r.choice([8, 0x10, 0, -1, r.getrandbits(31)])]) for _ in range(40)]},
]
