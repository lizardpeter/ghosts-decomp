"""Frame-by-frame driving of the enhanced client and cgame frame in the emulator, for the fixed-command and
render-time-view tests (test_fixed_cmds.py, test_view_step.py). Not a test module itself.

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
CHARINFO = SCRATCH + 0xB0000      # the bgame's character info array (0x5D8 per client)

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
    w.write(TLS_BLOCK + 0x10, struct.pack("<Q", CHARINFO))
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
        cl = va("clients")
        self.world.call(S["create"], [0], scratch_setup, generator_fakes(self.mouse))
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


class Game:
    """A whole client frame: CG_SavePlayerState (the frame's start), CL_CreateNewCommands, CG_PredictPlayerState,
    CG_DrawActive, with the faithful prediction running the Store build's Pmove (noclip by default)."""

    def __init__(self, env, enabled=True, pm_type=2, kick=(0.25, -0.5, 0.0), pmove=None, anim=noop):
        self.env = env
        self.world = World(env)
        self.client = Client(env, self.world)
        self.fakes = dict(generator_fakes(self.client.mouse))
        self.fakes.update(cgame_fakes(anim))
        if pmove:
            self.fakes[S["pmove"]] = pmove
        w, cg = self.world, va("cgArray")
        w.poke(env.data("cg_renderTimeView"), struct.pack("<i", 1 if enabled else 0))
        start = self.client.realtime + 1
        ps = bytearray(0x620)
        struct.pack_into("<iiii", ps, 0, start - 5, pm_type, 0, 0)
        struct.pack_into("<i", ps, 0x44, 0x7FF)
        struct.pack_into("<ii", ps, 0x5C, 800, 190)
        struct.pack_into("<i", ps, 0x70, 0x7FF)
        struct.pack_into("<i", ps, 0xBC, 0x7FF)
        struct.pack_into("<if", ps, 0x190, 60, 60.0)
        w.poke(cg, bytes(ps))
        w.poke(cg + 0xE08, struct.pack("<i", 0x7FF))
        w.poke(cg + CG_SNAP, struct.pack("<QQ", SNAP, SNAP))
        w.poke(cg + CG_PLATFORM_CONTACT, struct.pack("<i", 0x7FF))
        w.poke(cg + CG_KICK, struct.pack("<3f", *kick))
        w.poke(va("clients") + CL_KICK, struct.pack("<3f", *kick))
        w.poke(static(PREDICT, "cg_pmove") + 0x108, struct.pack("<6f", 0, 0, 35, 15, 15, 35))
        w.poke(cg + CG_SAVED, struct.pack("<i", start - 5))
        self.views, self.after_draw, self.times = [], [], []

    def call(self, name, args):
        return self.world.call(S[name], args, scratch_setup, self.fakes)

    def frame(self, msec, delta_change=0, draw=True):
        c, cg = self.client, va("cgArray")
        old = struct.unpack("<i", self.world.read(cg + CG_TIME, 4))[0]
        c.clock(msec, delta_change)
        self.world.poke(cg + CG_OLDTIME, struct.pack("<i", old))
        self.world.poke(cg + CG_TIME, struct.pack("<i", c.server_time))
        self.call("save", [0])
        c.create()
        self.call("predict", [0])
        self.views.append(self.world.read(cg, 0x620))
        if draw:
            self.call("draw", [0, 0])
            self.after_draw.append(self.world.read(cg, PS_SIZE))
        self.times.append(c.server_time)
