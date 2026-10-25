// enhanced/cgame_mp/cg_present.cpp: the presentation's time and mode per category (docs/cgame-frame.md 4.3, stage 1).
//
// Every presentation consumer asks CG_PresentTime(category) for the time it draws at and CG_PresentMode(category)
// for how; changing an entry of cg_presentMode changes that category and nothing else. Wired so far: other entities
// (CG_SetFrameInterpolation below: the snapshot blend at the fractional render time) and the own view
// (enhanced/cgame_mp/cg_view_step.cpp: the partial step to floor(T_r) and the velocity for the rest). The viewmodel,
// effects, HUD and sound still draw at cg.time (stages 2 and 3).

#include "cgame_mp/cg_local_mp.h"
#include "enhanced/render_time.h"

int cg_presentMode[PC_COUNT] = {
	PM_STEP_FORWARD,   // own view: nothing the player aims with is interpolated
	PM_STEP_FORWARD,   // viewmodel
	PM_INTERPOLATE,    // other entities: between snapshots, as the original
	PM_INTERPOLATE,    // effects
	PM_STEP_FORWARD,   // HUD
	PM_STEP_FORWARD,   // sound
};
double cg_presentExtrapolateMsec = 0.0;

PresentMode CG_PresentMode(PresentCategory category)
{
	if ((unsigned int)category >= PC_COUNT)
		return PM_STEP_FORWARD;
	const int mode = cg_presentMode[category];
	return mode == PM_INTERPOLATE || mode == PM_EXTRAPOLATE ? (PresentMode)mode : PM_STEP_FORWARD;
}

double CG_PresentTime(PresentCategory category)
{
	const cg_s *cgameGlob = CG_GetLocalClientGlobals(LOCAL_CLIENT_0);
	const PresentMode mode = CG_PresentMode(category);
	if (category == PC_OWN_VIEW && mode == PM_INTERPOLATE)
		return (double)cgameGlob->time;
	double time = (double)cgameGlob->time + CL_RenderTimeOffset();
	if (mode == PM_EXTRAPOLATE)
		time += cg_presentExtrapolateMsec;
	return time;
}

// Store 1402B5B70 (src/cgame_mp/cg_ents_mp.cpp), enhanced: the blend between the snapshots at the time other
// entities are drawn at, fractional. With no fraction (the time is cg.time) it is the original bit for bit: the
// integer difference is formed first, as the original does, and only then the fraction added.
void CG_SetFrameInterpolation(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const int snapTime = cgameGlob->snap->serverTime;
	const int delta = cgameGlob->nextSnap->serverTime - snapTime;
	if (!delta)
	{
		cgameGlob->frameInterpolation = 0.0f;
		return;
	}
	const double offset = CG_PresentTime(PC_OTHER_ENTITIES) - (double)cgameGlob->time;
	const int sinceSnap = cgameGlob->time - snapTime;
	cgameGlob->frameInterpolation = (float)((double)sinceSnap + offset) / (float)delta;
	if (cgameGlob->frameInterpolation < 0.0f)
		cgameGlob->frameInterpolation = 0.0f;
}
