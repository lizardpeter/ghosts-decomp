// enhanced/bgame/bg_recoil.cpp: the viewmodel's recoil on a fixed 5 ms grid of the cgame's time (records/patches.tsv P0015).
//
// The original BG_CalculateWeaponMovement_Recoil (src/bgame/bg_weapons_view.cpp) integrates the frame's time
// (weaponState_t::frametime, cg.frametime * 0.001f) in steps of at most 5 ms, so above 200 fps the steps are the
// frame's own 1-4 ms and the recoil changes with the frame rate (B0064: its peak is 12% lower at 1 ms frames).
//
// Enhanced: the real recoil state advances in whole 5 ms steps of the cgame's time (weaponState_t::time), each one
// exactly the original's step at 200 fps; what the viewmodel shows is that state advanced to the frame's time by one
// more original step of the rest (0-4 ms), recomputed every frame, so it moves every frame and the partial step never
// accumulates. Keyed on the time rather than on summed frame times, so a second call at the same time gives the same
// result. When something else changed the recoil since the last call (a shot pushes recoilSpeed), the grid starts
// again from that state at the last call's time; when the time goes back (a kill cam, a new cgame), at this call's.

#include "bgame/bg_weapons.h"

#define RECOIL_STEP_MSEC 5
#define RECOIL_MAX_STEPS 200  // one second: the recoil has settled long before

// callees of the original (as declared in src/bgame/bg_weapons_view.cpp)
Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
bool BG_IsAimDownSight(Weapon weapon, bool isAlternate);
void BG_GetGunKickSpeed(Weapon weapon, bool isAlternate, float *hipAccel, float *hipSpeedMax, float *hipSpeedDecay,
	float *hipStaticDecay, float *adsAccel, float *adsSpeedMax, float *adsSpeedDecay, float *adsStaticDecay);
int BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle(float *angle, float *speed, float dt, float maxAngle,
	float accel, float speedMax, float speedDecay, float staticDecay);

struct RecoilGrid
{
	float gridAngles[3];  // the recoil at gridTime
	float gridSpeed[3];
	float shownAngles[3];  // what this function left in the weaponState_t last time
	float shownSpeed[3];
	int gridTime;
	int lastTime;
	int valid;
};
static RecoilGrid s_recoil;

// src: Store 140297CF0 BG_CalculateWeaponMovement_Recoil, unchanged
static void BG_CalculateWeaponMovement_RecoilOriginal(weaponState_t *ws)
{
	const playerState_s *ps = ws->ps;
	const bool isAlternate = ps && (ps->weapCommon_weapFlags & PWF_ALT_MODE);
	const Weapon weapon = BG_GetViewmodelWeapon(ps);
	unsigned int defIndex = weapon.data & 0xFF;
	if (isAlternate
		&& (!defIndex || bg_weaponCompleteDefs[defIndex]->altWeapon || !bg_weaponDefs[defIndex]
			|| bg_weaponDefs[defIndex]->oldWeapon)
		&& (unsigned char)bg_weaponCompleteDefs[defIndex]->altWeapon)
	{
		defIndex = (unsigned char)bg_weaponCompleteDefs[defIndex]->altWeapon;
	}
	const WeaponDef *weapDef = bg_weaponDefs[defIndex];
	float hipAccel, hipSpeedMax, hipSpeedDecay, hipStaticDecay, adsAccel, adsSpeedMax, adsSpeedDecay, adsStaticDecay;
	BG_GetGunKickSpeed(weapon, isAlternate, &hipAccel, &hipSpeedMax, &hipSpeedDecay, &hipStaticDecay, &adsAccel,
		&adsSpeedMax, &adsSpeedDecay, &adsStaticDecay);
	if (!BG_IsAimDownSight(weapon, isAlternate))
		return;
	const float frac = ps->weapCommon_fWeaponPosFrac;
	const float accel = (adsAccel - hipAccel) * frac + hipAccel;
	const float speedMax = (adsSpeedMax - hipSpeedMax) * frac + hipSpeedMax;
	const float speedDecay = (adsSpeedDecay - hipSpeedDecay) * frac + hipSpeedDecay;
	const float staticDecay = (adsStaticDecay - hipStaticDecay) * frac + hipStaticDecay;
	float remaining = ws->frametime;
	if (!(remaining > 0.0f))
		return;
	do
	{
		float dt;
		if (remaining > 0.005f)
		{
			dt = 0.005f;
			remaining = remaining + -0.005f;
		}
		else
		{
			dt = remaining;
			remaining = 0.0f;
		}
		const int pitchDone = BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle(&ws->recoilAngles[0],
			&ws->recoilSpeed[0], dt, weapDef->fGunMaxPitch, accel, speedMax, speedDecay, staticDecay);
		const int yawDone = BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle(&ws->recoilAngles[1],
			&ws->recoilSpeed[1], dt, weapDef->fGunMaxYaw, accel, speedMax, speedDecay, staticDecay);
		if (yawDone && pitchDone)
			break;
	} while (remaining > 0.0f);
}

static void RecoilLoad(weaponState_t *ws, const float angles[3], const float speed[3])
{
	for (int i = 0; i < 3; ++i)
	{
		ws->recoilAngles[i] = angles[i];
		ws->recoilSpeed[i] = speed[i];
	}
}

static void RecoilStore(const weaponState_t *ws, float angles[3], float speed[3])
{
	for (int i = 0; i < 3; ++i)
	{
		angles[i] = ws->recoilAngles[i];
		speed[i] = ws->recoilSpeed[i];
	}
}

// The original's step for msec milliseconds, with the frame time the cgame would give it for such a frame
static void RecoilAdvance(weaponState_t *ws, int msec)
{
	const float frametime = ws->frametime;
	ws->frametime = (float)msec * 0.001f;
	BG_CalculateWeaponMovement_RecoilOriginal(ws);
	ws->frametime = frametime;
}

static bool RecoilUnchanged(const RecoilGrid *g, const weaponState_t *ws)
{
	const unsigned int *a = (const unsigned int *)ws->recoilAngles, *s = (const unsigned int *)ws->recoilSpeed;
	const unsigned int *sa = (const unsigned int *)g->shownAngles, *ss = (const unsigned int *)g->shownSpeed;
	for (int i = 0; i < 3; ++i)
	{
		if (a[i] != sa[i] || s[i] != ss[i])
			return false;
	}
	return true;
}

// src: Store 140297CF0 BG_CalculateWeaponMovement_Recoil. Enhanced: on a fixed 5 ms grid (above).
void BG_CalculateWeaponMovement_Recoil(weaponState_t *ws)
{
	RecoilGrid *g = &s_recoil;
	const int now = ws->time;
	int frameMsec = (int)(ws->frametime * 1000.0f + 0.5f);
	if (!(frameMsec > 0))
		frameMsec = 0;  // also NaN

	if (!g->valid || now - g->lastTime < 0)
	{
		RecoilStore(ws, g->gridAngles, g->gridSpeed);
		g->gridTime = now - frameMsec;
		g->valid = 1;
	}
	else if (!RecoilUnchanged(g, ws))
	{
		RecoilStore(ws, g->gridAngles, g->gridSpeed);
		g->gridTime = g->lastTime;
	}

	// whole steps on the grid
	RecoilLoad(ws, g->gridAngles, g->gridSpeed);
	int steps = 0;
	while (now - g->gridTime >= RECOIL_STEP_MSEC)
	{
		if (steps++ == RECOIL_MAX_STEPS)
		{
			g->gridTime = now - (now - g->gridTime) % RECOIL_STEP_MSEC;
			break;
		}
		RecoilAdvance(ws, RECOIL_STEP_MSEC);
		g->gridTime += RECOIL_STEP_MSEC;
	}
	RecoilStore(ws, g->gridAngles, g->gridSpeed);

	// what the viewmodel shows: the grid state advanced to now
	const int rest = now - g->gridTime;
	if (rest > 0)
		RecoilAdvance(ws, rest);
	RecoilStore(ws, g->shownAngles, g->shownSpeed);
	g->lastTime = now;
}
