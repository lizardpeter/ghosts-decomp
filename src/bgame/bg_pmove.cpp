// bgame/bg_pmove.cpp (Store build): the player movement entry point.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses; names follow the
// PS4 server's PDB (bgame/bg_pmove.cpp), whose Pmove is the same code apart from PM_SetPitchValues, which the Store
// build inlines.
//
// Pmove is the only place the length of a usercmd enters the movement code (docs/fps.md). It runs PmoveSingle on
// the time from ps->commandTime to cmd.serverTime, in steps of at most 66 ms, and never more than the last second.
// It does not split the time into fixed steps: a command of n ms is one PmoveSingle of n ms (msec 1..200, frametime
// msec / 1000), so the client's frame rate decides the step the client and the server both simulate.

#include "bgame/bg_public.h"

extern "C" double floor(double x);

#define MAX_PMOVE_MSEC 66

// PS4 PDB PM_SetPitchValues (bgame/bg_pmove.cpp:7059), inlined into Pmove in the Store build: the torso and waist
// pitch, wrapped to [-180, 180) and scaled by how far a prone (11) or 22 view height lerp has got
static inline void PM_SetPitchValues(const playerState_s *ps, pmove_t *pm)
{
	const int target = ps->viewHeightTarget;
	if (target != 22 && (target == 40 || target == BG_GetStandingViewHeight() || target != 11))
	{
		pm->fTorsoPitch = 0.0f;
		pm->fWaistPitch = 0.0f;
		return;
	}

	float frac;
	if (ps->viewHeightLerpTime)
	{
		int duration;
		if (ps->viewHeightLerpTarget == 11)
			duration = 400;
		else if (ps->viewHeightLerpTarget == 40)
			duration = ps->viewHeightLerpDown ? 200 : 400;
		else
			duration = 200;
		const float t = (float)(ps->commandTime - ps->viewHeightLerpTime) / (float)duration;
		frac = 0.0f;
		if (!(0.0f > t))
			frac = 1.0f < t ? 1.0f : t;
		if (!ps->viewHeightLerpDown)
			frac = 1.0f - frac;
	}
	else
	{
		frac = 1.0f;
	}

	float a = pm->fTorsoPitch * 0.0027777778f;
	pm->fTorsoPitch = (a - (float)floor((double)(a + 0.5f))) * 360.0f * frac;
	a = pm->fWaistPitch * 0.0027777778f;
	pm->fWaistPitch = (a - (float)floor((double)(a + 0.5f))) * 360.0f * frac;
}

// Store 140273A90 (PS4 PDB Pmove, bgame/bg_pmove.cpp:7111)
void Pmove(pmove_t *pm)
{
	playerState_s *ps = pm->ps;
	if ((ps->pm_flags & 0x80000) || (pm->cmd.buttons & 0x100000))
	{
		pm->cmd.buttons &= 0x100300;
		pm->cmd.forwardmove = 0;
		pm->cmd.rightmove = 0;
	}
	if (ps->linkFlags & 4)
	{
		pm->cmd.buttons &= 0xFFFFFBF9;
		pm->cmd.forwardmove = 0;
		pm->cmd.rightmove = 0;
	}

	const int finalTime = pm->cmd.serverTime;
	if (finalTime < ps->commandTime)
		return;  // should not happen
	if (finalTime > ps->commandTime + 1000)
		ps->commandTime = finalTime - 1000;
	pm->numtouch = 0;

	// chop the move up if it is too long, to prevent framerate dependent behavior
	while (ps->commandTime != finalTime)
	{
		int msec = finalTime - ps->commandTime;
		if (msec > MAX_PMOVE_MSEC)
			msec = MAX_PMOVE_MSEC;
		pm->cmd.serverTime = ps->commandTime + msec;
		PmoveSingle(pm);
		if (ps->weapCommon_fWeaponPosFrac == 1.0f)
		{
			if (!ps->pe_timeADSCameUp)
				ps->pe_timeADSCameUp = ps->commandTime;
		}
		else
		{
			ps->pe_timeADSCameUp = 0;
		}
		pm->oldcmd = pm->cmd;
	}
	PM_SetPitchValues(ps, pm);
}
