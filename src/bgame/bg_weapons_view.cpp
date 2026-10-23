// bgame/bg_weapons_view.cpp
//
// The viewmodel's movement (weapon position, sway, recoil, bob), shared game code: names, prototypes and line
// numbers from the PS4 dedicated server (iw6_ds_ps4); the Microsoft Store build (iw6mp64_MSStore_ship) has the same
// code. The cgame runs BG_CalculateWeaponMovement (Store 140296F10) once a frame with weaponState_t::frametime =
// cg.frametime * 0.001 (Store 1402F38B0).

#include "bgame/bg_weapons.h"

#define IW6_SOURCE "bgame/bg_weapons_view.cpp"

static_assert(__builtin_offsetof(weaponState_t, frametime) == 0xC, "weaponState_t layout");
static_assert(__builtin_offsetof(weaponState_t, recoilAngles) == 0x3C, "weaponState_t layout");
static_assert(__builtin_offsetof(weaponState_t, recoilSpeed) == 0x48, "weaponState_t layout");
static_assert(sizeof(weaponState_t) == 0x90, "weaponState_t layout");
static_assert(__builtin_offsetof(WeaponDef, fGunMaxPitch) == 0x640, "WeaponDef layout");

Weapon BG_GetViewmodelWeapon(const playerState_s *ps);  // bgame/bg_weapons_setup.cpp
bool BG_IsAimDownSight(Weapon weapon, bool isAlternate);  // bgame/bg_weapons_util.cpp
void BG_GetGunKickSpeed(Weapon weapon, bool isAlternate, float *hipAccel, float *hipSpeedMax, float *hipSpeedDecay,
	float *hipStaticDecay, float *adsAccel, float *adsSpeedMax, float *adsSpeedDecay, float *adsStaticDecay);

static inline float I_fabs(float x)
{
	return __builtin_fabsf(x);
}

// PS4 1400A35F0 (bgame/bg_weapons_view.cpp:766), Store 140297FF0. One step of dt seconds for one recoil angle:
// position first (clamped to maxAngle, which also stops a speed pushing past it), then the spring toward center
// (accel, degrees per second squared), then the speed's decay (proportional, then static) and its clamp. Returns 1
// (and zeroes both) once the angle and the speed are small.
int BG_CalculateWeaponMovement_Recoil_Internal_SingleAngle(float *angle, float *speed, float dt, float maxAngle,
	float accel, float speedMax, float speedDecay, float staticDecay)
{
	if (I_fabs(*angle) < 0.25f && I_fabs(*speed) < 1.0f)
	{
		*angle = 0.0f;
		*speed = 0.0f;
		return 1;
	}
	*angle = dt * *speed + *angle;
	if (*angle > maxAngle)
	{
		*angle = maxAngle;
		if (*speed > 0.0f)
			*speed = 0.0f;
	}
	else if (-maxAngle > *angle)
	{
		*angle = -maxAngle;
		if (0.0f > *speed)
			*speed = 0.0f;
	}
	if (*angle > 0.0f)
		*speed = *speed - dt * accel;
	else if (0.0f > *angle)
		*speed = dt * accel + *speed;
	float s = *speed;
	s = s - s * speedDecay * dt;
	const float staticStep = dt * staticDecay;
	if (s > 0.0f)
	{
		s = s - staticStep;
		*speed = s;
		if (0.0f > s)
		{
			s = 0.0f;
			*speed = 0.0f;
		}
	}
	else
	{
		s = staticStep + s;
		*speed = s;
		if (s > 0.0f)
		{
			s = 0.0f;
			*speed = 0.0f;
		}
	}
	if (s > speedMax)
		*speed = speedMax;
	else if (-speedMax > s)
		*speed = -speedMax;
	return 0;
}

// PS4 1400A3310 (bgame/bg_weapons_view.cpp:831), Store 140297CF0. The viewmodel's recoil (recoilAngles, pushed by
// recoilSpeed when firing), for weapons that aim down the sight: the gun kick values are blended between hip and
// ADS by the ADS fraction, and the frame's time is integrated in steps of at most 5 ms (the remainder last) until
// both angles have settled. Like BG_KickAngles, the steps are the frame's own 1 to 4 ms above 200 fps.
void BG_CalculateWeaponMovement_Recoil(weaponState_t *ws)
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
