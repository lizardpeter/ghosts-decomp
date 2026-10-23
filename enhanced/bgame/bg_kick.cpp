// enhanced/bgame/bg_kick.cpp: the view kick on a fixed 5 ms grid (records/patches.tsv, the view-kick patch).
//
// The original BG_KickAngles (src/bgame/bg_weapons_util.cpp) integrates in steps of at most 5 ms of the msec it is
// given. The cgame calls it once a frame with cg.frametime, so up to 200 fps the steps are 5 ms, but above that they
// are the frame's own 1-4 ms, and the kick changes with the frame rate (B0063: at 1000 fps it peaks about 7% lower).
// The kicked angles go into the usercmd, so the server sees the difference.
//
// Enhanced, for the cgame's own kick (cg_s, kickAVel/kickAngles): the real state advances only in whole 5 ms steps,
// with the rest of the frame time carried to the next frame, so it is exactly the original's at 200 fps whatever the
// frame rate. What the cgame sees (and draws, and sends) is that state advanced by the carried time with the original
// step, recomputed every frame from the grid state, so the view still moves every frame and the partial step never
// accumulates. When something else changed the cgame's arrays since the last call (a shot adds velocity, a spawn
// clears it), the grid starts again from that state at that moment: the kick after a shot is then the same function
// of the time since the shot at any frame rate, the original's at 200 fps. Every other caller (the server's bots, with
// 50 ms) gets the original.

#include "bgame/bg_weapons.h"
#include "cgame_mp/cg_local_mp.h"
#include "qcommon/dvar.h"

#define CG_KICK_AVEL 0xB5268    // cg_s: kickAVel[3] (Store 143CD91E8)
#define CG_KICK_ANGLES 0xB5274  // cg_s: kickAngles[3] (Store 143CD91F4)
#define KICK_STEP_MSEC 5

// callees of the original (as declared in src/bgame/bg_weapons_util.cpp)
Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
bool BG_UsingAlternate(const playerState_s *ps);
const ADSOverlay *BG_GetOverlay(Weapon weapon, bool isAlternate);
float BG_AdsViewKickCenterSpeed(Weapon weapon, bool isAlternate);
float BG_HipViewKickCenterSpeed(Weapon weapon, bool isAlternate);
extern const dvar_t *perk_fastSnipeScale;

struct KickGrid
{
	float gridVel[3];   // the kick at the last whole 5 ms step
	float gridAng[3];
	float shownVel[3];  // what was written to the cgame's arrays last time
	float shownAng[3];
	int carry;          // milliseconds since the last whole step (0-4)
	int valid;
};
static KickGrid s_kick;

// src: Store 1402905D0 BG_KickAngles, unchanged (steps of at most 5 ms)
static void BG_KickAnglesOriginal(const playerState_s *ps, int msec, float kickAVel[3], float kickAngles[3])
{
	const Weapon weapon = BG_GetViewmodelWeapon(ps);
	for (; msec > 0; msec -= 5)
	{
		const int step = msec > 5 ? 5 : msec;
		const float dt = (float)step * 0.001f;
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

// Whether the arrays still hold what this function wrote last time (bit for bit: NaN or -0 written by someone else
// counts as a change)
static bool KickUnchanged(const KickGrid *k, const float vel[3], const float ang[3])
{
	const unsigned int *v = (const unsigned int *)vel, *a = (const unsigned int *)ang;
	const unsigned int *sv = (const unsigned int *)k->shownVel, *sa = (const unsigned int *)k->shownAng;
	for (int i = 0; i < 3; ++i)
	{
		if (v[i] != sv[i] || a[i] != sa[i])
			return false;
	}
	return true;
}

// src: Store 1402905D0 BG_KickAngles. Enhanced: the cgame's kick on a fixed 5 ms grid (above).
void BG_KickAngles(const playerState_s *ps, int msec, float kickAVel[3], float kickAngles[3])
{
	char *const cg = (char *)&cgArray[0];
	if (kickAVel != (float *)(cg + CG_KICK_AVEL) || kickAngles != (float *)(cg + CG_KICK_ANGLES))
	{
		BG_KickAnglesOriginal(ps, msec, kickAVel, kickAngles);
		return;
	}

	KickGrid *k = &s_kick;
	if (!k->valid || !KickUnchanged(k, kickAVel, kickAngles))
	{
		// first use, or something else changed the kick (a shot, a spawn): the grid starts again here
		for (int i = 0; i < 3; ++i)
		{
			k->gridVel[i] = kickAVel[i];
			k->gridAng[i] = kickAngles[i];
		}
		k->carry = 0;
		k->valid = 1;
	}

	if (msec > 0)
	{
		const int total = k->carry + msec;
		k->carry = total % KICK_STEP_MSEC;
		BG_KickAnglesOriginal(ps, total - k->carry, k->gridVel, k->gridAng);
	}

	for (int i = 0; i < 3; ++i)
	{
		kickAVel[i] = k->gridVel[i];
		kickAngles[i] = k->gridAng[i];
	}
	if (k->carry)
		BG_KickAnglesOriginal(ps, k->carry, kickAVel, kickAngles);
	for (int i = 0; i < 3; ++i)
	{
		k->shownVel[i] = kickAVel[i];
		k->shownAng[i] = kickAngles[i];
	}
}
