// bgame/bg_weapons_util.cpp
//
// Shared game code (client and server), from the PS4 dedicated server (iw6_ds_ps4, PDB names and lines) and the
// Microsoft Store build (iw6mp64_MSStore_ship), which has the same code with the two center-speed helpers inlined
// into BG_KickAngles.

#include "bgame/bg_weapons.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "bgame/bg_weapons_util.cpp"

static_assert(__builtin_offsetof(playerState_s, weapCommon_weapon) == 0x41C, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weapCommon_fWeaponPosFrac) == 0x424, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, perks) == 0xE14, "playerState_s layout");
static_assert(__builtin_offsetof(WeaponCompleteDef, fHipViewKickCenterSpeed) == 0xB8, "WeaponCompleteDef layout");
static_assert(__builtin_offsetof(WeaponCompleteDef, altWeapon) == 0xC8, "WeaponCompleteDef layout");
static_assert(__builtin_offsetof(WeaponDef, oldWeapon) == 0xA88, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponAttachment, viewKick) == 0xB8, "WeaponAttachment layout");
static_assert(__builtin_offsetof(WeaponAttachment, viewCenterScale) == 0x10C, "WeaponAttachment layout");
static_assert(__builtin_offsetof(AttViewKick, adsViewKickCenterSpeed) == 0x2C, "AttViewKick layout");

extern const dvar_t *perk_fastSnipeScale;  // bgame/bg_perks.cpp

Weapon BG_GetViewmodelWeapon(const playerState_s *ps);                    // bgame/bg_weapons_setup.cpp
bool BG_UsingAlternate(const playerState_s *ps);                          // bgame/bg_weapons_util.h (inline)
const ADSOverlay *BG_GetOverlay(Weapon weapon, bool isAlternate);
void BG_GetWeaponAttachments(Weapon weapon, bool isAlternate, const WeaponAttachment *attachments[]);

// The weapon whose definition holds the alternate mode's values (an inline of bg_weapons_util.h in both builds).
static inline unsigned int BG_DefWeaponIndex(Weapon weapon, bool isAlternate)
{
	const unsigned int index = weapon.data & 0xFF;
	if (isAlternate
		&& (!index || bg_weaponCompleteDefs[index]->altWeapon || !bg_weaponDefs[index] || bg_weaponDefs[index]->oldWeapon)
		&& (unsigned char)bg_weaponCompleteDefs[index]->altWeapon)
	{
		return (unsigned char)bg_weaponCompleteDefs[index]->altWeapon;
	}
	return index;
}

// The attachments' view-center scales multiplied (the first attachment's replaces 1, the others multiply; 0 means
// none), and the first attachment that overrides the view kick, if any.
static inline float BG_ViewCenterScale(Weapon weapon, bool isAlternate, const AttViewKick **viewKick)
{
	const WeaponAttachment *attachments[4];
	BG_GetWeaponAttachments(weapon, isAlternate, attachments);
	float scale = 1.0f;
	if (attachments[0] && attachments[0]->viewCenterScale != 0.0f)
		scale = attachments[0]->viewCenterScale;
	for (int i = 1; i < 4; ++i)
	{
		if (attachments[i] && attachments[i]->viewCenterScale != 0.0f)
			scale *= attachments[i]->viewCenterScale;
	}
	*viewKick = nullptr;
	for (int i = 0; i < 4; ++i)
	{
		if (attachments[i] && attachments[i]->viewKick)
		{
			*viewKick = attachments[i]->viewKick;
			break;
		}
	}
	return scale;
}

// PS4 1400971C0 (bgame/bg_weapons_util.cpp:5641); inlined in the Store build's BG_KickAngles. Degrees per second
// squared pulling the view kick back to center while aiming down the sight.
float BG_AdsViewKickCenterSpeed(Weapon weapon, bool isAlternate)
{
	const float speed = bg_weaponCompleteDefs[BG_DefWeaponIndex(weapon, isAlternate)]->fAdsViewKickCenterSpeed;
	const AttViewKick *viewKick;
	const float scale = BG_ViewCenterScale(weapon, isAlternate, &viewKick);
	if (viewKick)
		return scale * viewKick->adsViewKickCenterSpeed;
	return scale * speed;
}

// PS4 14009C620 (bgame/bg_weapons_util.cpp:5609); inlined in the Store build's BG_KickAngles. The same from the hip.
float BG_HipViewKickCenterSpeed(Weapon weapon, bool isAlternate)
{
	const float speed = bg_weaponCompleteDefs[BG_DefWeaponIndex(weapon, isAlternate)]->fHipViewKickCenterSpeed;
	const AttViewKick *viewKick;
	const float scale = BG_ViewCenterScale(weapon, isAlternate, &viewKick);
	if (viewKick)
		return scale * viewKick->hipViewKickCenterSpeed;
	return scale * speed;
}

// PS4 14009D240 (bgame/bg_weapons_util.cpp:1318), Store 1402905D0. Advances the view kick by msec milliseconds:
// kickAngles (degrees, added to the view and to the usercmd's angles) moves by kickAVel (degrees per second), and a
// center speed pulls kickAVel back toward zero while the angle is off center. The step is at most 5 ms: msec is cut
// into 5 ms pieces and a remainder (semi-implicit Euler). Movement back toward the center counts only 6%; crossing
// zero, or reaching it exactly, stops the kick; it is capped at 10 degrees.
//
// The client calls it once a frame with cg.frametime (CG_DrawActiveFrame, Store 1402E817B), the server's bots with
// 50 (Store 14049F9C1). So the client integrates with 5 ms steps up to 200 fps, but at higher frame rates with the
// frame's own 1 to 4 ms: the kick changes with the frame rate (docs/fps-frame.md).
void BG_KickAngles(const playerState_s *ps, int msec, float kickAVel[3], float kickAngles[3])
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
