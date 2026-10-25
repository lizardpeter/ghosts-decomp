// enhanced/include/enhanced/render_time.h: the high-resolution clock, the fractional render time and the presentation's
// mode table (docs/cgame-frame.md 4.1 and 4.3, stage 1).
//
// - Sys_Microseconds: microseconds since the first clock read, from QueryPerformanceCounter. Sys_Milliseconds is
//   floor(Sys_Microseconds() / 1000): the original's integer meaning (milliseconds since the first call), now with a
//   fraction underneath (enhanced/win32/win_clock.cpp).
// - cls_realtimeUs: cls.realtime in microseconds: 1000 * cls.realtime plus how far the clock was past com_frameTime
//   when the client's clock advanced (0..999 µs), kept by the enhanced sub_140316290
//   (enhanced/client_mp/cl_render_time.cpp). Every original integer (cls.realtime, frame_msec, the protocol) is the
//   original's.
// - CL_RenderTime: the render time T_r in milliseconds, cl.serverTime + the fraction of cls_realtimeUs, with
//   CL_SetCGameTime's small corrections of the client's time slewed over a snapshot interval instead of jumping.
// - The presentation asks CG_PresentTime(category) for the time it draws a category at, and CG_PresentMode for how;
//   nothing else in the presentation picks a time (enhanced/cgame_mp/cg_present.cpp).
#pragma once

long long Sys_Microseconds();

extern long long cls_realtimeUs;

#define RENDER_SLEW_LIMIT_MSEC 10   // corrections of the client's time up to this are slewed, larger ones jump
#define RENDER_SLEW_DEFAULT_INTERVAL 50  // the slew's length when the snapshot interval is unknown

struct RenderTimeState
{
	long long realtimeUs;   // the cls_realtimeUs the cached value is for
	int serverTime;         // the cl.serverTime it is for
	int prevServerTime;     // the previous frame's
	int prevRealtime;       // the previous frame's cls.realtime
	long long prevRealtimeUs;
	double slew;            // ms still to be applied to T_r (T_r = cl.serverTime + fraction + slew)
	double slewRate;        // ms of slew removed per ms of real time
	double renderTime;      // T_r
	int valid;
};
extern RenderTimeState cl_renderTimeState;

// T_r in ms (cached per frame), and T_r - cl.serverTime (the fraction and the slew)
double CL_RenderTime();
double CL_RenderTimeOffset();

enum PresentCategory
{
	PC_OWN_VIEW = 0,
	PC_VIEWMODEL = 1,
	PC_OTHER_ENTITIES = 2,
	PC_EFFECTS = 3,
	PC_HUD = 4,
	PC_SOUND = 5,
	PC_COUNT = 6,
};

enum PresentMode
{
	PM_STEP_FORWARD = 0,   // from the newest simulated state, stepped forward to the render time on copies
	PM_INTERPOLATE = 1,    // between states that already exist (other entities: the snapshots, at the render time)
	PM_EXTRAPOLATE = 2,    // past the newest state to the render time plus cg_presentExtrapolateMsec
};

// The one switch: the mode of each category. Defaults: the own view, the viewmodel, the HUD and sound step forward
// (nothing the player aims with is interpolated), other entities and effects interpolate.
extern int cg_presentMode[PC_COUNT];
extern double cg_presentExtrapolateMsec;  // how far past the render time PM_EXTRAPOLATE draws (0 for now)

PresentMode CG_PresentMode(PresentCategory category);

// The cgame time (ms, fractional) a category is drawn at:
// - PM_STEP_FORWARD and PM_INTERPOLATE: cg.time + CL_RenderTimeOffset() (the render time, in cg.time's frame);
//   for the own view, PM_INTERPOLATE is cg.time (the newest predicted state, as the original draws it, until the
//   tick loop provides states to blend);
// - PM_EXTRAPOLATE: that plus cg_presentExtrapolateMsec.
double CG_PresentTime(PresentCategory category);
