"""Frame-by-frame driving of the enhanced client and cgame frame in the emulator, for the fixed-command, tick-loop,
kick, render-time and own-view tests (test_fixed_cmds.py, test_tick.py, test_kick.py, test_render_time.py,
test_view_step.py): Client (the client's clock and CL_CreateNewCommands) and TickGame (whole frames through the
enhanced CG_DrawActiveFrame). Not a test module itself.

Every env.call rolls its writes back, so a World keeps everything the calls wrote (globals of both images and the TLS
block) and writes it back before the next call: the sequence of calls then behaves like consecutive frames.
"""
import math
import struct

from harness import SCRATCH, TLS_BLOCK
from syms import static, va

CLIENT, PREDICT = "client_mp/cl_input.cpp", "cgame_mp/cg_predict_mp.cpp"
CL_SERVERTIME, CL_KICK, CL_EXTRA, CL_VIEWANGLES, CL_CMDS, CL_CMDNUMBER = 0x34D0, 0x3574, 0x3608, 0x3610, 0x3628, 0x5428
CLS_FRAMETIME, CLS_FRAMETIME_BASE, CLS_REALTIME = 0x118, 0x11C, 0x120
UI_CONNSTATE, CA_ACTIVE = 0x8, 0xA
KB_SIZE, KB_FORWARD, KB_ATTACK = 0x14, 2, 0x11
CMD_SIZE, PS_SIZE, PM_SIZE = 0x3C, 0x3328, 0x178
CG_SNAP, CG_NEXTSNAP, CG_TIME, CG_OLDTIME = 0x3388, 0x3390, 0x71890, 0x71894
SETTINGS = SCRATCH + 0x70000      # GamerSettingState
DVARS = SCRATCH + 0x80000         # dvar_t's, 0x40 apart
WEAPDEF = SCRATCH + 0x90000       # an empty weapon definition for the real Pmove
SNAP = SCRATCH + 0xA0000          # snapshot_s
BGS = SCRATCH + 0xB0000           # the bgame's thread-local state (bgs_t; TLS block +0x10 points at it)
CHARINFO = BGS + 0x459F0          # its characterInfo_t array (0x5D8 per client; Store 140255FC7, 140258535)

S = {
    "create": "?CL_CreateNewCommands@@YAXW4LocalClientNum_t@@@Z",
    "validate": "?sub_14017AB80@@YAXPEAUDataValidation@@PEBXHH_N@Z",
    "record": "?sub_14017AAE0@@YAXPEAUDataValidation@@PEBXHH@Z",
    "mousemove": "?CL_MouseMove@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@M@Z",
    "gpad": "?GPad_IsActive@@YA_NH@Z",
    "ctrl": "?CL_ControllerIndexFromClientNum@@YAHW4LocalClientNum_t@@@Z",
    "settings": "?GamerProfile_GetProfileSettings@@YAPEAUGamerSettingState@@H@Z",
    "offhand": "?sub_1402891D0@@YAXI@Z",
    "slowmo": "?sub_1404633E0@@YAMM@Z",
    "cgame": "?sub_1402A9900@@YAXW4LocalClientNum_t@@PEAUusercmd_s@@@Z",
    "special": "?CG_HandleSpecialStateInput@@YAXW4LocalClientNum_t@@PEAI@Z",
    "keydown": "?IN_KeyDown@@YAXPEAUkbutton_t@@HI@Z",
    "keyup": "?IN_KeyUp@@YAXPEAUkbutton_t@@HI@Z",
    "predict": "?CG_PredictPlayerState@@YAXW4LocalClientNum_t@@@Z",
    "draw": "?CG_DrawActive@@YAXW4LocalClientNum_t@@H@Z",
    "save": "?CG_SavePlayerState@@YAXW4LocalClientNum_t@@@Z",
    "early": "?sub_1402D2410@@YAXXZ",
    "pmove": "?Pmove@@YAXPEAUpmove_t@@@Z",
    "render": "?CL_RenderScene@@YAXW4LocalClientNum_t@@PEBXH@Z",
    "anim_cond": "?BG_AnimUpdatePlayerStateConditions@@YAXPEAUpmove_t@@@Z",
    "set_cond": "?BG_SetConditionValue@@YAXPEAUcharacterInfo_t@@H_K@Z",
    "adjust": "?CG_AdjustPositionForMover@@YAXW4LocalClientNum_t@@PEBMHHHPEAM22PEAUplayerState_s@@PEAUpmove_t@@@Z",
    "trace": "?sub_140304650@@YAXPEAUtrace_t@@PEBM1PEBUBounds@@HH@Z",
    "origin": "?sub_140178C50@@YAXW4LocalClientNum_t@@@Z",
    "stance": "?CL_SetStance@@YAXW4LocalClientNum_t@@W4StanceState@@@Z",
    "traj": "?BG_EvaluateTrajectory@@YAXPEBUtrajectory_t@@HQEAM@Z",
    "melee": "?sub_1402CC6E0@@YAXW4LocalClientNum_t@@PEAUplayerState_s@@@Z",
    "ps2es": "?BG_PlayerStateToEntityState@@YAXPEBUplayerState_s@@PEAUentityState_s@@H@Z",
    "events": "?BG_PlayerToEntity_ProcessEvents@@YAXPEBUplayerState_s@@PEAUentityState_s@@E@Z",
    "platform": "?sub_1402EF5D0@@YAXW4LocalClientNum_t@@PEBUplayerState_s@@PEAUcg_s@@@Z",
    "remote": "?sub_1405BAAA0@@YAXW4LocalClientNum_t@@@Z",
    "omnvar": "?sub_1402D0AC0@@YAXW4LocalClientNum_t@@@Z",
}


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def rd(mu, a, n):
    return bytes(mu.mem_read(a, n))


def noop(mu):
    return None


MACHINE = {}


def wmem(mu, address, data):
    """A write a fake makes for the program: journaled like the emulated code's own, so it is reported and rolled back."""
    MACHINE["m"]._emulated_write(address, bytes(data))


class World:
    """Memory that persists across calls: everything a call wrote is written back before the next one."""

    def __init__(self, env):
        self.env = env
        self.mem = {}
        MACHINE["m"] = env.machine

    def poke(self, address, data):
        for i, b in enumerate(data):
            self.mem[address + i] = bytes([b])

    def read(self, address, size):
        return b"".join(self.mem.get(address + i, b"\0") for i in range(size))

    def apply(self, w):
        run_start, run = None, bytearray()
        for a in sorted(self.mem):
            if run_start is not None and a == run_start + len(run):
                run += self.mem[a]
                continue
            if run_start is not None:
                w.write(run_start, bytes(run))
            run_start, run = a, bytearray(self.mem[a])
        if run_start is not None:
            w.write(run_start, bytes(run))

    def call(self, symbol, args, base_setup, fakes, ret="void"):
        def setup(w):
            base_setup(w)
            self.apply(w)
        value, _, written, observed = self.env.call(symbol, args, ret, setup, fakes)
        if isinstance(value, str) and value.startswith("fault"):
            raise AssertionError(f"{symbol}: {value}")
        self.mem.update(written)
        return value, observed


def dvar(w, slot, value):
    a = DVARS + 0x40 * slot
    w.m.mu.mem_write(a + 0x10, struct.pack("<f", value))
    return a


def scratch_setup(w):
    """What lives outside the images: scratch dvars, the profile, the snapshot, the character info pointer."""
    mu = w.m.mu
    for name, slot, value in (("cl_yawspeed", 0, 140.0), ("cl_pitchspeed", 1, 140.0), ("cl_anglespeedkey", 2, 1.5),
                              ("cg_errorDecay", 3, 100.0), ("cg_viewZSmoothingMin", 4, 1.0),
                              ("cg_viewZSmoothingMax", 5, 16.0), ("cg_viewZSmoothingTime", 6, 0.15)):
        w.u64(va(name), dvar(w, slot, value))
    mu.mem_write(SETTINGS + 0x2BC, b"\0")
    mu.mem_write(SNAP + 0x3C7C, struct.pack("<i", 0))
    w.write(TLS_BLOCK + 0x10, struct.pack("<Q", BGS))
    w.u64(va("bg_weaponDefs"), WEAPDEF)
    w.u64(va("bg_weaponCompleteDefs"), WEAPDEF)


class Mouse:
    """CL_MouseMove, faked: turns the view by a fixed amount per call (the real one needs raw input and m_sens)."""

    def __init__(self, yaw_per_call=0.0137, pitch_per_call=0.0021):
        self.yaw, self.pitch = yaw_per_call, pitch_per_call
        self.calls = 0

    def __call__(self, mu):
        cl = va("clients")
        p, y = struct.unpack("<2f", rd(mu, cl + CL_VIEWANGLES, 8))
        wmem(mu, cl + CL_VIEWANGLES, struct.pack("<2f", p + self.pitch, y + self.yaw))
        self.calls += 1
        return None


def generator_fakes(mouse):
    def zero_float(mu):
        from unicorn.x86_const import UC_X86_REG_XMM0
        mu.reg_write(UC_X86_REG_XMM0, 0)
        return None
    return {S["validate"]: noop, S["record"]: noop, S["mousemove"]: mouse, S["gpad"]: lambda mu: 0,
            S["ctrl"]: lambda mu: 0, S["settings"]: lambda mu: SETTINGS, S["offhand"]: noop, S["slowmo"]: zero_float,
            S["cgame"]: noop, S["special"]: noop}


class Client:
    """The client half of a frame: the clock and CL_CreateNewCommands, with the commands it stored collected."""

    def __init__(self, env, world, start_time=100000, mouse=None):
        self.env, self.world = env, world
        self.realtime = start_time
        self.delta = 0
        self.server_time = start_time
        self.mouse = mouse or Mouse()
        cl, ui = va("clients"), va("clientUIActives")
        world.poke(ui + UI_CONNSTATE, struct.pack("<i", CA_ACTIVE))
        world.poke(va("unk_143E96824"), struct.pack("<i", 0))
        world.poke(cl + CL_CMDNUMBER, struct.pack("<i", 1000))
        world.poke(cl + CL_VIEWANGLES, struct.pack("<3f", 0.0, 0.0, 0.0))
        self.cmd_number = 1000
        self.commands = []    # (frame index, serverTime, raw bytes)
        self.per_frame = []
        self.frame_index = 0

    def clock(self, msec, delta_change=0):
        cl, cls = va("clients"), va("cls")
        self.realtime += msec
        self.delta += delta_change
        self.server_time = max(self.server_time, self.realtime + self.delta)
        w = self.world
        w.poke(cls + CLS_REALTIME, struct.pack("<i", self.realtime))
        w.poke(cls + CLS_FRAMETIME, struct.pack("<i", msec))
        w.poke(cls + CLS_FRAMETIME_BASE, struct.pack("<f", msec * 0.001))
        w.poke(va("com_frameTime"), struct.pack("<i", self.realtime))
        w.poke(va("frame_msec"), struct.pack("<I", msec))
        w.poke(cl + CL_SERVERTIME, struct.pack("<i", self.server_time))

    def create(self):
        self.world.call(S["create"], [0], scratch_setup, generator_fakes(self.mouse))
        return self.collect()

    def collect(self):
        """The commands stored since the last collect."""
        cl = va("clients")
        number = struct.unpack("<i", self.world.read(cl + CL_CMDNUMBER, 4))[0]
        new = []
        for n in range(self.cmd_number + 1, number + 1):
            raw = self.world.read(cl + CL_CMDS + (n & 127) * CMD_SIZE, CMD_SIZE)
            new.append(raw)
            self.commands.append((self.frame_index, struct.unpack_from("<i", raw)[0], raw))
        self.per_frame.append(len(new))
        self.cmd_number = number
        self.frame_index += 1
        return new

    def key(self, button, down):
        """IN_KeyDown / IN_KeyUp at the current com_frameTime, as the key handlers do."""
        kb = static(CLIENT, "playersKb") + KB_SIZE * button
        self.world.call(S["keydown" if down else "keyup"], [kb, 0x41, self.realtime], scratch_setup, {})


def frame_pattern(fps, total_ms, start=0.0):
    """Whole-millisecond frame lengths of a fractional frame period (the client's clock is integer ms)."""
    period = 1000.0 / fps
    out, t, last = [], start, int(math.floor(start))
    while t < start + total_ms:
        t += period
        now = int(math.floor(t + 1e-9))
        out.append(max(1, now - last))
        last += out[-1]
    return out


CG_KICK, CG_SAVED, CG_PLATFORM_CONTACT = 0xB5274, 0x10E84C, 0xB2750


def cgame_fakes(anim=noop):
    def adjust(mu):
        from win32_display import arg
        wmem(mu, arg(mu, 5), rd(mu, arg(mu, 1), 12))
        wmem(mu, arg(mu, 6), bytes(12))
        wmem(mu, arg(mu, 7), bytes(12))
        return None

    def trace(mu):
        from win32_display import arg
        wmem(mu, arg(mu, 0), bytes(0x2C))
        return None
    fakes = {S[n]: noop for n in ("origin", "stance", "traj", "melee", "ps2es", "events", "platform", "remote",
                                  "omnvar", "render", "offhand", "set_cond")}
    fakes.update({S["adjust"]: adjust, S["trace"]: trace, S["anim_cond"]: anim})
    return fakes


# --- whole cgame frames through the enhanced CG_DrawActiveFrame (the tick loop, docs/cgame-frame.md 4.2, 4.10) ------

DAF = "?CG_DrawActiveFrame@@YAHW4LocalClientNum_t@@HW4DemoType@@W4CubemapShot@@HHH@Z"
CG_KICK_AVEL, CG_FRAMETIME, CG_BGS_TIME, CG_BGS_FRAMETIME = 0xB5268, 0x7188C, 0xFAE58, 0xFAE64
CG_RECOIL = 0xA9AFC                         # cg_s: the viewmodel's recoilAngles, recoilSpeed
CG_JAM, CG_TURRET_FOV, CG_RAMP = 0x10EDBC, 0x10EDC4, 0x10F828   # radarJamLevel, scriptedViewFov, ramp
PE_SEQ, PE_EVENTS = 0x128, 0x12C            # playerState_s: pe.eventSequence, pe.events[4] (8 bytes each)
TRANS_SEQ = 8                               # transPlayerState_t: eventSequence
SHOCK_PARMS = SCRATCH + 0xC0000
OVERLAY = SCRATCH + 0xC1000
REAL_IN_TICK_LOOP = {"?CG_DrawActive@@YAXW4LocalClientNum_t@@H@Z", "?sub_1402D2410@@YAXXZ",
                     "?CG_PredictPlayerState@@YAXW4LocalClientNum_t@@@Z"}


def _ret0(mu):
    return 0


class Ticks:
    """What the frame's ticks did, from the fakes: CG_TransitionPlayerState runs once per tick right after the
    tick's prediction, so it records the tick's time, the predicted state, cg_pmove, the kick before the tick's step,
    and the events it would fire (the pe sequence numbers between the saved trans state and the new state)."""

    def __init__(self, ps_size=PS_SIZE, shots=None):
        self.ps_size = ps_size
        self.rows = []       # (frame, cg.time, cg.oldTime, cg.frametime, bgs.time, bgs.frametime, ps, pm, kick,
                             #  the viewmodel's recoil, (jam, turret FOV, ramp) raw) before the tick's integrators
        self.events = []     # (cg.time, sequence, type, parm)
        self.entity_events = []
        self.frame = 0
        self.shots = dict(shots or {})   # tick time -> kick velocity added (a shot fired in that tick's events)
        self.counts = {}     # tick time -> events 0x3A to count
        self.writes = {}     # tick time -> [(cg offset, bytes)] the tick's events write (a weapon change, buttons)

    def transition(self, mu):
        from win32_display import arg
        cg = va("cgArray")
        ps, trans = arg(mu, 1), arg(mu, 2)
        msec, time, old = struct.unpack("<iii", rd(mu, cg + CG_FRAMETIME, 12))
        bgs_time, bgs_msec = struct.unpack("<i", rd(mu, cg + CG_BGS_TIME, 4))[0], struct.unpack("<i", rd(mu, cg + CG_BGS_FRAMETIME, 4))[0]
        state = rd(mu, ps, self.ps_size)
        pm = rd(mu, static(PREDICT, "cg_pmove"), PM_SIZE)
        kick = rd(mu, cg + CG_KICK_AVEL, 24)
        recoil = struct.unpack("<6f", rd(mu, cg + CG_RECOIL, 24))
        extra = (rd(mu, cg + CG_JAM, 4), rd(mu, cg + CG_TURRET_FOV, 4), rd(mu, cg + CG_RAMP, 4))
        self.rows.append((self.frame, time, old, msec, bgs_time, bgs_msec, state, pm, kick, recoil, extra))
        seq, saved = struct.unpack("<i", state[PE_SEQ:PE_SEQ + 4])[0], struct.unpack("<i", rd(mu, trans + TRANS_SEQ, 4))[0]
        for s in range(saved, seq):
            etype, parm = struct.unpack_from("<ii", state, PE_EVENTS + 8 * (s & 3))
            self.events.append((time, s, etype, parm))
        if time in self.shots:
            vel = struct.unpack("<3f", rd(mu, cg + CG_KICK_AVEL, 12))
            wmem(mu, cg + CG_KICK_AVEL, struct.pack("<3f", *(v + d for v, d in zip(vel, self.shots[time]))))
        for off, data in self.writes.get(time, ()):
            wmem(mu, cg + off, data)
        n = self.counts.get(time, 0)
        if n:
            a = va("unk_143C23F68")
            wmem(mu, a, struct.pack("<i", struct.unpack("<i", rd(mu, a, 4))[0] + n))
        return None

    def entity_event(self, mu):
        from win32_display import arg
        cg = va("cgArray")
        self.entity_events.append((struct.unpack("<i", rd(mu, cg + CG_TIME, 4))[0], arg(mu, 1), arg(mu, 2) & 0xFFFFFFFF))
        return None


def frame_fakes(ticks, drawn, sent):
    """Every callee of CG_DrawActiveFrame that isn't part of the tick loop or the presentation's own view, faked: the
    network, effects, scene, sound, HUD and weapon-view functions do nothing; the queries answer "no"."""
    from test_cg_view import CALLEES
    f = {sym: noop for sym, _, _ in CALLEES if sym not in REAL_IN_TICK_LOOP}

    def memset(mu):
        from win32_display import arg
        wmem(mu, arg(mu, 0), bytes([arg(mu, 1) & 0xFF]) * arg(mu, 2))
    f["?sub_140536260@@YAXPEAXH_K@Z"] = memset
    f["?CG_GetPredictedPlayerState@@YAPEBUplayerState_s@@W4LocalClientNum_t@@@Z"] = lambda mu: va("cgArray")
    f["?CG_ProcessSnapshots@@YAXW4LocalClientNum_t@@@Z"] = noop
    f["?BG_GetShellshockParms@@YAPEAUshellshock_parms_t@@H@Z"] = lambda mu: SHOCK_PARMS
    f["?CG_AddPacketEntities@@YAHW4LocalClientNum_t@@PEAH@Z"] = _ret0
    for sym in ("?CL_IsServerLoadingMap@@YA_NXZ", "?sub_140187D70@@YAHW4LocalClientNum_t@@@Z",
                "?Com_GetClientDObj@@YAPEAUDObj@@HW4LocalClientNum_t@@@Z", "?sub_14017F630@@YA_NW4LocalClientNum_t@@@Z",
                "?sub_1402CF440@@YAHW4LocalClientNum_t@@@Z", "?sub_1402DF740@@YA_NW4LocalClientNum_t@@@Z",
                "?sub_1402DF750@@YA_NW4LocalClientNum_t@@@Z", "?BG_IsEMPJammed@@YAHPEBUplayerState_s@@@Z",
                "?sub_1402EF4D0@@YA_NW4LocalClientNum_t@@PEBUcg_s@@@Z", "?CL_IsGamepadEnabled@@YA_NW4LocalClientNum_t@@@Z",
                "?sub_1402F8530@@YAIPEBUcg_s@@W4LocalClientNum_t@@@Z", "?sub_1402C5700@@YA_NW4LocalClientNum_t@@@Z",
                "?BG_OffhandIsUnderbarrelWeapon@@YAHPEBUplayerState_s@@I@Z", "?IN_Frame@@YAXXZ",
                "?BG_GetViewmodelWeapon@@YA?ATWeapon@@PEBUplayerState_s@@@Z", "?BG_UsingAlternate@@YA_NPEBUplayerState_s@@@Z"):
        f[sym] = _ret0
    for sym in ("?BG_IsThirdPersonMode@@YA_NPEBUplayerState_s@@@Z", "?BG_IsAimDownSight@@YA_NTWeapon@@_N@Z",
                "?sub_140300960@@YAHW4LocalClientNum_t@@PEBUplayerState_s@@H@Z",
                "?sub_140294C30@@YAHPEBUplayerState_s@@HH@Z"):
        f[sym] = _ret0
    for sym in ("?sub_14027B740@@YAXPEBUplayerState_s@@MPEAM@Z", "?sub_14026A870@@YAMPEBUplayerState_s@@H@Z",
                "?BG_CalculateWeaponMovement@@YAXPEAUweaponState_t@@QEAM1H@Z"):
        f[sym] = noop                          # the viewmodel's movement half in the ticks: nothing to move
    for sym in ("?sub_14028F230@@YA_NTWeapon@@_N@Z", "?sub_1402AF8A0@@YA_NPEBUplayerState_s@@H@Z",
                "?sub_14028F050@@YA_NPEBUplayerState_s@@@Z",
                "?sub_1402F7640@@YAPEBUXModel@@TWeapon@@PEBUWeaponAttachment@@@Z"):
        f[sym] = _ret0
    for sym in ("?sub_14037AEA0@@YAXPEAUXModel@@@Z", "?sub_14037AEF0@@YAXPEBUXModel@@@Z",
                "?sub_1402F51A0@@YAXPEAUcg_s@@PEAUGfxScaledPlacement@@PEAM@Z",
                "?sub_1402F30A0@@YAXW4LocalClientNum_t@@PEBUGfxScaledPlacement@@PEBUplayerState_s@@PEAUcentity_s@@H@Z"):
        f[sym] = noop                          # the viewmodel's placement and scene (CG_AddViewWeapon's own callees)
    f["?sub_14031FED0@@YA_NH@Z"] = _ret0          # the ramp's input: off
    for sym in ("?sub_1402CDF70@@YAXW4LocalClientNum_t@@PEAUcentity_s@@@Z",
                "?sub_1402B4F90@@YAXW4LocalClientNum_t@@PEAUcentity_s@@@Z"):
        f[sym] = noop                          # the player's own model's pose and scene entry
    f["?BG_GetNumWeapons@@YAIXZ"] = lambda mu: 256
    f["?sub_14060DC10@@YAMXZ"] = noop          # the far plane: whatever xmm0 holds goes to the faked FX camera
    f["?BG_GetOverlay@@YAPEBUADSOverlay@@TWeapon@@_N@Z"] = lambda mu: OVERLAY
    f["?CG_TransitionPlayerState@@YAXW4LocalClientNum_t@@PEAUplayerState_s@@PEBUtransPlayerState_t@@@Z"] = ticks.transition
    f["?CG_EntityEvent@@YAXW4LocalClientNum_t@@PEAUcentity_s@@HH_N@Z"] = ticks.entity_event

    def calc_view(mu):
        drawn.append(rd(mu, va("cgArray"), 0x620))
        return None
    f["?CG_CalcViewValues@@YAXW4LocalClientNum_t@@@Z"] = calc_view

    def send(mu):
        cl = va("clients")
        sent.append(struct.unpack("<i", rd(mu, cl + CL_CMDNUMBER, 4))[0])
        return None
    f["?CL_SendCmd@@YAXW4LocalClientNum_t@@@Z"] = send
    return f


class TickGame:
    """Whole client frames as the client runs them: the clock (cls.realtime, cls_realtimeUs with a fraction,
    cl.serverTime with the delta nudges), CG_SavePlayerState, then the enhanced CG_DrawActiveFrame with the tick loop,
    the faithful prediction running the Store build's Pmove (noclip by default) or a fake, and every callee outside
    the loop and the own view faked (frame_fakes).

    Collected: per frame the drawn state (what CG_CalcViewValues sees), the state after the frame, the frame's new
    commands, the command number at CL_SendCmd; per tick (Ticks) the tick's times, state, cg_pmove, kick and events."""

    def __init__(self, env, pm_type=2, kick=(0.0, 0.0, 0.0), kick_avel=(0.0, 0.0, 0.0), pmove=None, anim=noop,
                 mouse=None, other_flags=0x4000, tick_loop=True, render_time_view=True, shots=None, ps_size=PS_SIZE):
        self.env = env
        self.world = World(env)
        self.client = Client(env, self.world, mouse=mouse)
        self.ticks = Ticks(ps_size, shots)
        self.drawn, self.sent = [], []
        self.fakes = dict(generator_fakes(self.client.mouse))
        self.fakes.update(cgame_fakes(anim))
        self.fakes.update(frame_fakes(self.ticks, self.drawn, self.sent))
        if pmove:
            self.fakes[S["pmove"]] = pmove
        w, cg = self.world, va("cgArray")
        w.poke(env.data("cg_renderTimeView"), struct.pack("<i", 1 if render_time_view else 0))
        w.poke(env.data("cg_tickLoop"), struct.pack("<i", 1 if tick_loop else 0))
        start = self.client.realtime + 1
        ps = bytearray(0x620)
        struct.pack_into("<iiiiI", ps, 0, start - 5, pm_type, 0, 0, other_flags)
        struct.pack_into("<i", ps, 0x44, 0x7FF)
        struct.pack_into("<ii", ps, 0x5C, 800, 190)
        struct.pack_into("<i", ps, 0x70, 0x7FF)
        struct.pack_into("<i", ps, 0xBC, 0x7FF)
        struct.pack_into("<if", ps, 0x190, 60, 60.0)
        struct.pack_into("<i", ps, 0x1E8, 0x7FF)      # viewlocked_entNum: none
        w.poke(cg, bytes(ps))
        w.poke(cg + 0xE08, struct.pack("<i", 0x7FF))
        w.poke(cg + CG_SNAP, struct.pack("<QQ", SNAP, SNAP))
        w.poke(cg + CG_PLATFORM_CONTACT, struct.pack("<i", 0x7FF))
        w.poke(cg + CG_KICK_AVEL, struct.pack("<3f3f", *kick_avel, *kick))
        w.poke(cg + CG_TIME, struct.pack("<i", start - 5))
        w.poke(cg + 0x3378, struct.pack("<i", 1))     # renderScreen
        w.poke(static(PREDICT, "cg_pmove") + 0x108, struct.pack("<6f", 0, 0, 35, 15, 15, 35))
        w.poke(cg + CG_SAVED, struct.pack("<i", start - 5))
        self.after, self.times, self.frame_commands, self.view_angles = [], [], [], []
        self.fraction_us = 0

    def call(self, name, args, ret="void"):
        return self.world.call(S[name] if name in S else name, args, scratch_setup, self.fakes, ret=ret)

    def frame(self, msec, delta_change=0, fraction_us=None, save=True):
        c = self.client
        c.clock(msec, delta_change)
        if fraction_us is not None:
            self.fraction_us = fraction_us
        self.world.poke(self.env.data("cls_realtimeUs"), struct.pack("<q", c.realtime * 1000 + self.fraction_us))
        self.ticks.frame = c.frame_index
        if save:
            self.call("save", [0])
        value, _ = self.call(DAF, [0, c.server_time, 0, 0, 0, 1, 0], ret="int")
        assert value == 1, value
        self.frame_commands.append(c.collect())
        self.after.append(self.world.read(va("cgArray"), PS_SIZE))
        self.view_angles.append(self.world.read(va("clients") + CL_VIEWANGLES, 12))
        self.times.append(c.server_time)
