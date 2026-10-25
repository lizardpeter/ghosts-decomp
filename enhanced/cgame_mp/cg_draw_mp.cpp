// enhanced/cgame_mp/cg_draw_mp.cpp: the ramp (sub_1402AA2A0) at 5 ms per tick (records/patches.tsv P0028;
// docs/cgame-frame.md 4.6, 4.11).
//
// The original (src/cgame_mp/cg_draw_mp.cpp, Store 1402AA2A0) moves cg.ramp by the client's frame time
// (cls.frametime / 300, or / (1 / the ADS-in time)) once a frame, from CG_DrawActiveFrame. The step is linear with
// clamps, so with 5 ms per tick it is the same over time at any frame rate. CG_RampTick is the original's body with
// the frame time a parameter: the tick loop calls it with 5 in every tick; sub_1402AA2A0 (the frame without the
// tick loop) with cls.frametime, the original.

#include "cgame_mp/cg_local_mp.h"
#include "client/client.h"
#include "enhanced/tick.h"

int CL_ControllerIndexFromClientNum(LocalClientNum_t localClientNum);
bool sub_14031FED0(int controllerIndex);
Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
void BG_GetADSTransTimes(const playerState_s *ps, Weapon weapon, bool isAlternate, float *inTime, float *outTime);

// src: Store 1402AA2A0's body, with cls.frametime a parameter
void CG_RampTick(LocalClientNum_t localClientNum, int frametimeMsec)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const float frametime = (float)frametimeMsec;
	float step = frametime / 300.0f;
	const bool enabled = sub_14031FED0(CL_ControllerIndexFromClientNum(localClientNum));
	const int pmFlags = cgameGlob->predictedPlayerState.pm_flags;
	if (enabled && !(pmFlags & 1))
	{
		if (cgameGlob->rampUp && !(pmFlags & 0x10))
		{
			const float v = step + cgameGlob->ramp;
			cgameGlob->ramp = 1.0f < v ? 1.0f : v;
			return;
		}
		if (cgameGlob->rampDown)
		{
			if (!(pmFlags & 0x10))
			{
				const float v = cgameGlob->ramp - step;
				cgameGlob->ramp = -1.0f > v ? -1.0f : v;
				return;
			}
			goto adsRate;
		}
	}
	if (pmFlags & 0x10)
	{
	adsRate:
		const playerState_s *ps = &cgameGlob->predictedPlayerState;
		float inTime, outTime;
		BG_GetADSTransTimes(ps, BG_GetViewmodelWeapon(ps), (ps->weapCommon_weapFlags >> 14) & 1, &inTime, &outTime);
		step = frametime / (1.0f / inTime);
	}
	const float ramp = cgameGlob->ramp;
	if (ramp > 0.0f)
	{
		const float v = ramp - step;
		cgameGlob->ramp = 0.0f > v ? 0.0f : v;
	}
	else if (0.0f > ramp)
	{
		const float v = ramp + step;
		cgameGlob->ramp = 0.0f < v ? 0.0f : v;
	}
}

// Store 1402AA2A0, enhanced: the original with the client's frame time
void sub_1402AA2A0(LocalClientNum_t localClientNum)
{
	CG_RampTick(localClientNum, cls.frametime);
}
