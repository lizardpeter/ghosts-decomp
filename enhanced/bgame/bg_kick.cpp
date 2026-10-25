// enhanced/bgame/bg_kick.cpp: the view kick's step for the presentation (records/patches.tsv P0014, folded into the
// tick loop: docs/cgame-frame.md 4.5, 4.10).
//
// The original BG_KickAngles (src/bgame/bg_weapons_util.cpp) integrates in steps of at most 5 ms of the msec it is
// given; the cgame called it once a frame with cg.frametime, so above 200 fps the steps were the frame's own 1-4 ms and
// the kick changed with the frame rate (B0063). With the tick loop (enhanced/cgame_mp/cg_tick.cpp) the cgame calls the
// unchanged original once per 5 ms tick with 5, so the canonical kick is the original's at 200 fps whatever the frame
// rate, and BG_KickAngles itself is not replaced any more (every caller gets the original).
//
// What is left here is the presentation's step-forward: the canonical kick advanced by the fractional time from the
// latest tick to the own view's presentation time, on a copy (it only goes into the view's temporary command, never
// into cg_s or a real usercmd). It is the original's step with a float msec: one step of min(5, msec) at a time, so
// for a whole msec it is bit for bit BG_KickAngles(ps, msec).

#include "bgame/bg_weapons.h"
#include "qcommon/dvar.h"

// callees of the original (as declared in src/bgame/bg_weapons_util.cpp)
Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
bool BG_UsingAlternate(const playerState_s *ps);
const ADSOverlay *BG_GetOverlay(Weapon weapon, bool isAlternate);
float BG_AdsViewKickCenterSpeed(Weapon weapon, bool isAlternate);
float BG_HipViewKickCenterSpeed(Weapon weapon, bool isAlternate);
extern const dvar_t *perk_fastSnipeScale;

// src: Store 1402905D0 BG_KickAngles, with msec a float (the step's dt is (float)step * 0.001f as in the original)
void BG_KickAnglesStep(const playerState_s *ps, float msec, float kickAVel[3], float kickAngles[3])
{
	const Weapon weapon = BG_GetViewmodelWeapon(ps);
	for (; msec > 0.0f; msec -= 5.0f)
	{
		const float step = msec > 5.0f ? 5.0f : msec;
		const float dt = step * 0.001f;
		for (int i = 0; i < 3; ++i)
		{
			float vel = kickAVel[i];
			if (vel == 0.0f && kickAngles[i] == 0.0f)
				continue;
			if (kickAngles[i] != 0.0f)
			{
				float accel = kickAngles[i] > 0.0f ? -1.0f : 1.0f;
				if (!(weapon.data & 0xFF))
					accel *= 2400.0f;
				else if (ps->weapCommon_fWeaponPosFrac > 0.5f)
					accel *= BG_AdsViewKickCenterSpeed(weapon, BG_UsingAlternate(ps));
				else
					accel *= BG_HipViewKickCenterSpeed(weapon, BG_UsingAlternate(ps));
				const bool isAlternate = ps && (ps->weapCommon_weapFlags & PWF_ALT_MODE);
				if (BG_GetOverlay(ps->weapCommon_weapon, isAlternate)->reticle != WEAPOVERLAYRETICLE_NONE
					&& ps->weapCommon_fWeaponPosFrac > 0.0f && (ps->perks[1] & 0x200))
				{
					accel *= perk_fastSnipeScale->current.value;
				}
				vel = accel * dt + vel;
				kickAVel[i] = vel;
			}
			const float angle = kickAngles[i];
			float change = vel * dt;
			if (angle * change < 0.0f)
				change *= 0.06f;
			const float next = angle + change;
			if (!(angle * next >= 0.0f))
			{
				kickAngles[i] = 0.0f;
			}
			else
			{
				kickAngles[i] = next;
				if (next != 0.0f)
				{
					if (!(__builtin_fabsf(next) > 10.0f))
						continue;
					kickAngles[i] = next > 0.0f ? 10.0f : -10.0f;
				}
			}
			kickAVel[i] = 0.0f;
		}
	}
}
