// enhanced/client_mp/cl_render_time.cpp: the client's clock in microseconds and the fractional render time
// (docs/cgame-frame.md 4.1).
//
// cls_realtimeUs: the original sub_140316290 (src/client_mp/cl_main_mp.cpp, Store 140316290, copied unchanged below)
// advances cls.realtime by Com_Frame's integer msec (limited, smoothed, scaled). The enhanced copy also keeps
// cls_realtimeUs = 1000 * cls.realtime + how far the clock is past com_frameTime at that moment (0..999 µs; 0 when
// com_frameTime is ahead because the com_maxfps wait was added to it). It is strictly increasing, since cls.realtime
// rises by at least 1 ms a frame, and its integer part is always cls.realtime.
//
// The render time T_r = cl.serverTime + fraction + slew. CL_SetCGameTime (140306C40, not changed) moves the client's
// time against cls.realtime by its delta corrections (+-1 ms, -2 after an extrapolated snapshot) and by holding
// cl.serverTime when the new time would go back. Such a correction of up to RENDER_SLEW_LIMIT_MSEC is taken out of
// T_r at once (T_r stays continuous) and put back linearly over the snapshot interval; a larger one (the delta
// halved or reset, a new map) jumps. T_r never goes back. The integer cl.serverTime and every command time stay the
// original's.

#include "client/client.h"
#include "client_mp/client_mp.h"
#include "enhanced/render_time.h"

void R_SyncGpu(int (*WorkCallback)(unsigned long long));  // gfx_d3d/r_init.cpp
void IN_Frame();                                         // win32/win_input.cpp
extern int com_frameTime;
extern int old_com_frameTime;
extern int unk_1442B98E0;
struct DataValidation;
extern DataValidation unk_140CFC520;
void sub_14054B4B0(int msec);
void sub_14017A6C0(DataValidation *validation, int kind);
void sub_140223CE0();
void sub_140191F80();
void sub_14018F6C0();

long long cls_realtimeUs;
RenderTimeState cl_renderTimeState;

// src: Store 140316290, unchanged
static void sub_140316290Faithful(int msec, float frametime)
{
	if (unk_1442B98E0)
		sub_14054B4B0(msec);
	else
		unk_1442B98E0 = 1;
	sub_14017A6C0(&unk_140CFC520, 4);
	sub_140223CE0();
	sub_140191F80();
	if (!cls.gpuSyncedPrevFrame)
	{
		cls.gpuSyncedPrevFrame = true;
		R_SyncGpu(nullptr);
	}
	if (!cls.inputUpdatedPrevFrame)
		IN_Frame();
	cls.realtime += msec;
	frame_msec = com_frameTime - old_com_frameTime;
	cls.frametime_base = frametime;
	cls.gpuSyncedPrevFrame = false;
	cls.inputUpdatedPrevFrame = false;
	cls.frametime = msec;
	if (!frame_msec)
		frame_msec = 1;
	else if (frame_msec > 200)
		frame_msec = 200;
	old_com_frameTime = com_frameTime;
	sub_14018F6C0();
}

// Store 140316290, enhanced: the original, then cls_realtimeUs
void sub_140316290(int msec, float frametime)
{
	sub_140316290Faithful(msec, frametime);
	long long past = Sys_Microseconds() - (long long)com_frameTime * 1000;
	if (past < 0)
		past = 0;
	else if (past > 999)
		past = 999;
	cls_realtimeUs = (long long)cls.realtime * 1000 + past;
}

static double Enh_Floor(double x)
{
	const double t = (double)(long long)x;
	return t > x ? t - 1.0 : t;
}

// new: T_r for this frame (computed once per frame: keyed on cls_realtimeUs and cl.serverTime)
double CL_RenderTime()
{
	RenderTimeState *s = &cl_renderTimeState;
	const clientActive_t *cl = CL_GetLocalClientGlobals(LOCAL_CLIENT_0);
	if (s->valid && s->realtimeUs == cls_realtimeUs && s->serverTime == cl->serverTime)
		return s->renderTime;

	// the fraction of a millisecond the frame is past its integer client time
	long long sub = cls_realtimeUs - (long long)cls.realtime * 1000;
	if (sub < 0 || sub > 999)
		sub = 0;  // cls.realtime was changed without the hook (a reset): no fraction
	const double fraction = (double)sub / 1000.0;

	if (!s->valid)
	{
		s->slew = 0.0;
		s->slewRate = 0.0;
	}
	else
	{
		// the real time since the last frame, and the client time's correction against it
		const double elapsed = (double)(cls_realtimeUs - s->prevRealtimeUs) / 1000.0;
		const int correction = (cl->serverTime - cls.realtime) - (s->prevServerTime - s->prevRealtime);
		if (correction != 0)
		{
			if (correction <= RENDER_SLEW_LIMIT_MSEC && correction >= -RENDER_SLEW_LIMIT_MSEC)
			{
				int interval = cl->snap.serverTime - cl->oldSnapServerTime;
				if (interval <= 0 || interval > 500)
					interval = RENDER_SLEW_DEFAULT_INTERVAL;
				s->slew -= (double)correction;
				s->slewRate = (s->slew < 0.0 ? -s->slew : s->slew) / (double)interval;
			}
			else
			{
				s->slew = 0.0;  // a jump: the client's time is restarted, not smoothed
				s->slewRate = 0.0;
			}
		}
		else if (elapsed > 0.0)
		{
			// put the rest of the slew back, linearly
			const double step = s->slewRate * elapsed;
			if (s->slew > step)
				s->slew -= step;
			else if (s->slew < -step)
				s->slew += step;
			else
				s->slew = 0.0;
		}
	}

	double renderTime = (double)cl->serverTime + fraction + s->slew;
	// never back, unless the client's time jumped back for good (a new map, a reset)
	if (s->valid && renderTime < s->renderTime && s->renderTime - renderTime <= RENDER_SLEW_LIMIT_MSEC)
		renderTime = s->renderTime;

	s->prevServerTime = cl->serverTime;
	s->prevRealtime = cls.realtime;
	s->prevRealtimeUs = cls_realtimeUs;
	s->realtimeUs = cls_realtimeUs;
	s->serverTime = cl->serverTime;
	s->renderTime = renderTime;
	s->valid = 1;
	return renderTime;
}

double CL_RenderTimeOffset()
{
	const double renderTime = CL_RenderTime();
	return renderTime - (double)CL_GetLocalClientGlobals(LOCAL_CLIENT_0)->serverTime;
}
