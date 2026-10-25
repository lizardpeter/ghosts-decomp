// enhanced/cgame/cg_weapons.cpp: the viewmodel split into a tick half and a presentation half (records/patches.tsv
// P0027, P0015 folded; docs/cgame-frame.md 4.2, 4.5, 4.10).
//
// The faithful CG_AddViewWeapon (src/cgame/cg_weapons.cpp, Store 1402F38B0) integrates the viewmodel's weaponState_t
// (sway, recoil, bob, base angles, idle factor: BG_CalculateWeaponMovement) once a frame with frametime =
// cg.frametime * 0.001 and keeps the result in cg_s, then places the viewmodel and adds it to the scene. Split:
// - CG_ViewWeaponTick, in every 5 ms tick (cg.frametime 5): the movement half, the faithful code from the guards to the
//   copy-back: the ADS state, the weaponState_t from cg_s with frametime 0.005 and the tick's own horizontal speed
//   (14026A870 of the canonical state; the original takes cg.xyspeed, which CG_CalcViewValues sets in the
//   presentation from the drawn state), the hip integrator (14027B740), the bob
//   flag, BG_CalculateWeaponMovement (the original, so the recoil is BG_CalculateWeaponMovement_Recoil's own 5 ms
//   step: P0015's grid is gone), and the integrated fields back into cg_s. Its origin and angles are not used.
// - CG_AddViewWeapon, in the presentation: the models kept loaded, the guards and the gun flag as the original, then
//   the weaponState_t from cg_s (the latest tick's) on a copy with frametime = the viewmodel's presentation time minus
//   the latest tick (the step-forward of 4.3), BG_CalculateWeaponMovement on the copy for the origin and angles, the
//   placement (1402F51A0) and the scene (1402F30A0). Nothing is copied back: the canonical state is the tick's.
// Without the tick loop in this frame (CG_DrawActiveFrame's fallback) CG_AddViewWeapon is the faithful one.
//
// The viewmodel's animation (CG_UpdateViewWeaponAnim, XAnim) runs in the ticks with 5 ms and is drawn at the latest
// tick's pose: a step-forward of the pose isn't done (docs/cgame-frame.md 4.10: the XAnim tree's state is the global
// XAnimInfo pool's 0x40-byte nodes, an advance frees nodes and fires notetracks, and the skeleton is built from the
// tree after the frame).

#include "bgame/bg_public.h"
#include "bgame/bg_weapons.h"
#include "cgame_mp/cg_local_mp.h"
#include "enhanced/render_time.h"
#include "enhanced/tick.h"
#include "qcommon/dvar.h"

struct XModel;

struct GfxScaledPlacement
{
	float quat[4];
	float origin[3];
	float scale;
};

extern const dvar_t *cg_drawGun;

Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
const char *sub_14018DB60(LocalClientNum_t localClientNum, const clientInfo_t *ci, const characterInfo_t *info,
                          int which, int viewmodelIndex);
XModel *R_RegisterModel(const char *name);
void sub_14037AEA0(XModel *model);
void sub_14037AEF0(const XModel *model);
bool sub_14028F230(Weapon weapon, bool isAlternate);
void sub_1402C59B0();
const XModel *sub_1402F7640(Weapon weapon, const WeaponAttachment *scope);
bool BG_IsThirdPersonMode(const playerState_s *ps);
bool sub_1402AF8A0(const playerState_s *ps, int unused);
bool sub_14028F050(const playerState_s *ps);
bool BG_IsAimDownSight(Weapon weapon, bool isAlternate);
void sub_14027B740(const playerState_s *ps, float frametime, float *out);
int sub_140300960(LocalClientNum_t localClientNum, const playerState_s *ps, int unused);
int sub_140294C30(const playerState_s *ps, int perk, int unused);
float sub_14026A870(const playerState_s *ps, int time);  // the horizontal speed (0 or the climb speed on a ladder)
void BG_CalculateWeaponMovement(weaponState_t *ws, float *const origin, float *const angles, int bob);
void sub_1402F51A0(cg_s *cgameGlob, GfxScaledPlacement *placement, float *angles);
void sub_1402F30A0(LocalClientNum_t localClientNum, const GfxScaledPlacement *placement, const playerState_s *ps,
                   centity_s *cent, int drawGun);

int cg_tickLoopFrame;  // CG_DrawActiveFrame: 1 while this frame runs the tick loop

// The models kept loaded (src, unchanged)
static void CG_ViewWeaponModels(LocalClientNum_t localClientNum, cg_s *cgameGlob, const Weapon weapon)
{
	const playerState_s *ps = &cgameGlob->predictedPlayerState;
	if (ps->viewmodelIndex > 0)
	{
		const int clientNum = ps->clientNum;
		sub_14037AEA0(R_RegisterModel(sub_14018DB60(localClientNum, &cgameGlob->bgs.clientinfo[clientNum],
		                                             &cgameGlob->bgs.characterinfo[clientNum], 2, ps->viewmodelIndex)));
	}
	const unsigned int weaponIndex = (unsigned char)weapon.data;
	if (!weaponIndex)
		return;
	const WeaponDef *weapDef = bg_weaponDefs[weaponIndex];
	const WeaponCompleteDef *complete = bg_weaponCompleteDefs[weaponIndex];
	unsigned int variation = (weapon.data >> 8) & 0x3F;
	if (!weapDef->gunXModel[variation] && variation && weapDef->unknownModels38[variation - 1])
		variation = 0;
	if (weapDef->gunXModel[variation])
		sub_14037AEF0(weapDef->gunXModel[variation]);
	if (weapDef->viewModelExtra[0])
		sub_14037AEF0(weapDef->viewModelExtra[0]);
	if (weapDef->viewModelExtra[1])
		sub_14037AEF0(weapDef->viewModelExtra[1]);
	if (sub_14028F230(weapon, (ps->weapCommon_weapFlags >> 14) & 1))
		sub_1402C59B0();
	const unsigned int scope = (weapon.data >> 14) & 7;
	if (scope)
	{
		const WeaponAttachment *att = complete->scopes[scope - 1];
		if (att->viewModels[variation])
			sub_14037AEF0(att->viewModels[variation]);
		const XModel *extra = sub_1402F7640(weapon, att);
		if (extra)
			sub_14037AEF0(extra);
	}
	const unsigned int underBarrel = (weapon.data >> 17) & 3;
	if (underBarrel && complete->underBarrels[underBarrel - 1]->viewModels[variation])
		sub_14037AEF0(complete->underBarrels[underBarrel - 1]->viewModels[variation]);
	const unsigned int others = weapon.data >> 19;
	if (others & 0x7F)
	{
		unsigned int bit = 1;
		for (int i = 0; i < 7; ++i, bit += bit)
		{
			if ((others & bit & 0x7F) && complete->others[i]->viewModels[variation])
				sub_14037AEF0(complete->others[i]->viewModels[variation]);
		}
	}
}

// The viewmodel's state from cg_s (src, unchanged) with the given frametime and time
static void CG_ViewWeaponState(cg_s *cgameGlob, weaponState_t *ws, float frametime, int time)
{
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	ws->ps = ps;
	ws->xyspeed = cgameGlob->xyspeed;
	ws->frametime = frametime;
	ws->fLastIdleFactor = cgameGlob->weapLastIdleFactor;
	ws->time = time - ps->weaponTimeBase;
	ws->damageTime = cgameGlob->damageTime ? cgameGlob->damageTime - ps->weaponTimeBase : 0;
	ws->v_dmg_pitch = cgameGlob->v_dmg_pitch;
	ws->v_dmg_roll = cgameGlob->v_dmg_roll;
	for (int i = 0; i < 3; ++i)
	{
		ws->baseAngles[i] = cgameGlob->weapBaseAngles[i];
		ws->baseOrigin[i] = cgameGlob->weapBaseOrigin[i];
		ws->recoilAngles[i] = cgameGlob->weapRecoilAngles[i];
		ws->recoilSpeed[i] = cgameGlob->weapRecoilSpeed[i];
		ws->swayAngles[i] = cgameGlob->weapSwayAngles[i];
		ws->swayOrigin[i] = cgameGlob->weapSwayOrigin[i];
		ws->swayViewAngles[i] = cgameGlob->weapSwayViewAngles[i];
	}
	ws->shellShockStart = cgameGlob->shellshock_startTime;
	ws->shellShockDuration = cgameGlob->shellshock_duration;
	ws->shellShockFadeTime = cgameGlob->shellshock_parms ? cgameGlob->shellshock_parms->view_fadeTime : 3000;
}

// The bob flag (src, unchanged)
static int CG_ViewWeaponNoBob(LocalClientNum_t localClientNum, const playerState_s *ps)
{
	if (ps->pm_flags & 1)
		return sub_140300960(localClientNum, ps, 0);
	if (!(ps->otherFlags & 0x2000) && sub_140294C30(ps, 0x71, 0) && 0.25f > ps->weapCommon_fWeaponPosFrac)
		return 1;
	return 0;
}

// Whether the viewmodel is simulated and drawn at all (src's guards, without the gun flag)
static bool CG_ViewWeaponActive(const cg_s *cgameGlob)
{
	const playerState_s *ps = &cgameGlob->predictedPlayerState;
	if ((unsigned int)(ps->pm_type - 5) <= 1 || cgameGlob->renderingThirdPerson || BG_IsThirdPersonMode(ps))
		return false;
	return !(ps->eFlags & 0x203800);
}

// src's CG_AddViewWeapon from the guards to the copy-back, with the tick's frametime (cg.frametime: 5)
void CG_ViewWeaponTick(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	if (!CG_ViewWeaponActive(cgameGlob) || !(unsigned char)BG_GetViewmodelWeapon(ps).data)
		return;
	const bool aims = BG_IsAimDownSight(BG_GetViewmodelWeapon(ps), (ps->weapCommon_weapFlags >> 14) & 1);
	const float frac = ps->weapCommon_fWeaponPosFrac;
	if (aims)
	{
		if (frac == 1.0f)
			cgameGlob->viewmodelAdsState = 0;
		else if (frac == 0.0f)
			cgameGlob->viewmodelAdsState = 1;
	}
	weaponState_t ws;
	CG_ViewWeaponState(cgameGlob, &ws, (float)cgameGlob->frametime * 0.001f, cgameGlob->time);
	// the tick's own speed (CG_CalcViewValues sets cg.xyspeed in the presentation, from the drawn state)
	ws.xyspeed = sub_14026A870(ps, cgameGlob->time);
	if (frac == 0.0f)
	{
		sub_14027B740(ps, ws.frametime, &cgameGlob->hipViewValue);
		ps->hipViewValue = cgameGlob->hipViewValue;
	}
	const int noBob = CG_ViewWeaponNoBob(localClientNum, ps);
	GfxScaledPlacement placement;
	float angles[3];
	BG_CalculateWeaponMovement(&ws, placement.origin, angles, noBob == 0);
	for (int i = 0; i < 3; ++i)
	{
		cgameGlob->weapRecoilAngles[i] = ws.recoilAngles[i];
		cgameGlob->weapRecoilSpeed[i] = ws.recoilSpeed[i];
		cgameGlob->weapSwayAngles[i] = ws.swayAngles[i];
		cgameGlob->weapSwayOrigin[i] = ws.swayOrigin[i];
		cgameGlob->weapSwayViewAngles[i] = ws.swayViewAngles[i];
		cgameGlob->weapBaseAngles[i] = ws.baseAngles[i];
		cgameGlob->weapBaseOrigin[i] = ws.baseOrigin[i];
	}
	cgameGlob->weapLastIdleFactor = ws.fLastIdleFactor;
}

// src: the faithful CG_AddViewWeapon (the frame without the tick loop)
static void CG_AddViewWeaponFaithful(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	const Weapon weapon = BG_GetViewmodelWeapon(ps);
	CG_ViewWeaponModels(localClientNum, cgameGlob, weapon);
	cgameGlob->unknown71944[0] = 0;
	cgameGlob->unknown71944[1] = 0;
	if ((unsigned int)(ps->pm_type - 5) <= 1 || cgameGlob->renderingThirdPerson || BG_IsThirdPersonMode(ps))
		return;
	int drawGun = 1;
	if (cgameGlob->cubemapShot || !cg_drawGun->current.enabled || (sub_1402AF8A0(ps, 0) && !sub_14028F050(ps)))
		drawGun = 0;
	if (ps->eFlags & 0x203800)
		return;
	if (!(unsigned char)weapon.data)
	{
		cgameGlob->gunAngles[0] = cgameGlob->refdefViewAngles[0];
		cgameGlob->gunAngles[1] = cgameGlob->refdefViewAngles[1];
		cgameGlob->gunAdsOffset[0] = 0.0f;
		cgameGlob->gunAdsOffset[1] = 0.0f;
		cgameGlob->gunAdsOffset[2] = 0.0f;
		return;
	}
	const bool aims = BG_IsAimDownSight(BG_GetViewmodelWeapon(ps), (ps->weapCommon_weapFlags >> 14) & 1);
	const float frac = ps->weapCommon_fWeaponPosFrac;
	if (aims)
	{
		if (frac == 1.0f)
			cgameGlob->viewmodelAdsState = 0;
		else if (frac == 0.0f)
			cgameGlob->viewmodelAdsState = 1;
	}
	weaponState_t ws;
	CG_ViewWeaponState(cgameGlob, &ws, (float)cgameGlob->frametime * 0.001f, cgameGlob->time);
	if (frac == 0.0f)
	{
		sub_14027B740(ps, ws.frametime, &cgameGlob->hipViewValue);
		ps->hipViewValue = cgameGlob->hipViewValue;
	}
	const int noBob = CG_ViewWeaponNoBob(localClientNum, ps);
	GfxScaledPlacement placement;
	float angles[3];
	BG_CalculateWeaponMovement(&ws, placement.origin, angles, noBob == 0);
	sub_1402F51A0(cgameGlob, &placement, angles);
	for (int i = 0; i < 3; ++i)
	{
		cgameGlob->weapRecoilAngles[i] = ws.recoilAngles[i];
		cgameGlob->weapRecoilSpeed[i] = ws.recoilSpeed[i];
		cgameGlob->weapSwayAngles[i] = ws.swayAngles[i];
		cgameGlob->weapSwayOrigin[i] = ws.swayOrigin[i];
		cgameGlob->weapSwayViewAngles[i] = ws.swayViewAngles[i];
		cgameGlob->weapBaseAngles[i] = ws.baseAngles[i];
		cgameGlob->weapBaseOrigin[i] = ws.baseOrigin[i];
	}
	cgameGlob->weapLastIdleFactor = ws.fLastIdleFactor;
	sub_1402F30A0(localClientNum, &placement, ps, cgameGlob->predictedPlayerEntity, drawGun);
}

// Store 1402F38B0, enhanced: in a tick-loop frame, the presentation half (above)
void CG_AddViewWeapon(LocalClientNum_t localClientNum)
{
	if (!cg_tickLoopFrame)
	{
		CG_AddViewWeaponFaithful(localClientNum);
		return;
	}
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	const Weapon weapon = BG_GetViewmodelWeapon(ps);
	CG_ViewWeaponModels(localClientNum, cgameGlob, weapon);
	cgameGlob->unknown71944[0] = 0;
	cgameGlob->unknown71944[1] = 0;
	if ((unsigned int)(ps->pm_type - 5) <= 1 || cgameGlob->renderingThirdPerson || BG_IsThirdPersonMode(ps))
		return;
	int drawGun = 1;
	if (cgameGlob->cubemapShot || !cg_drawGun->current.enabled || (sub_1402AF8A0(ps, 0) && !sub_14028F050(ps)))
		drawGun = 0;
	if (ps->eFlags & 0x203800)
		return;
	if (!(unsigned char)weapon.data)
	{
		cgameGlob->gunAngles[0] = cgameGlob->refdefViewAngles[0];
		cgameGlob->gunAngles[1] = cgameGlob->refdefViewAngles[1];
		cgameGlob->gunAdsOffset[0] = 0.0f;
		cgameGlob->gunAdsOffset[1] = 0.0f;
		cgameGlob->gunAdsOffset[2] = 0.0f;
		return;
	}

	// the latest tick's state stepped forward to the viewmodel's presentation time, on a copy
	double rest = 0.0;
	int time = CL_LastTickTime();
	if (CG_PresentMode(PC_VIEWMODEL) != PM_INTERPOLATE)
	{
		const double presentTime = CG_PresentTime(PC_VIEWMODEL);
		rest = presentTime - (double)time;
		if (rest < 0.0)
			rest = 0.0;
		double floorTime = (double)(long long)presentTime;
		if (floorTime > presentTime)
			floorTime -= 1.0;
		if ((int)floorTime > time)
			time = (int)floorTime;
	}
	weaponState_t ws;
	CG_ViewWeaponState(cgameGlob, &ws, (float)(rest * 0.001), time);
	const int noBob = CG_ViewWeaponNoBob(localClientNum, ps);
	GfxScaledPlacement placement;
	float angles[3];
	BG_CalculateWeaponMovement(&ws, placement.origin, angles, noBob == 0);
	sub_1402F51A0(cgameGlob, &placement, angles);
	sub_1402F30A0(localClientNum, &placement, ps, cgameGlob->predictedPlayerEntity, drawGun);
}

// --- Store 1402FB790: the timed repeats on the microsecond clock (B0079) -----------------------------------------
//
// The original advances its 64 repeating events by (int)(timescale * (the wall clock's whole milliseconds since the
// last call)), truncated per call: at a timescale below 1 and 1 ms frames that is 0 every frame, so they never run
// out at 1000 fps and do at 60 (and at 1 the per-call truncation is exact). Enhanced: the scaled time is measured in
// microseconds (Sys_Microseconds) and the part below a millisecond is carried to the next call, so the repeats see the
// same scaled milliseconds over any span whatever the frame rate; the rest of the function is the original's. With a
// timescale of 1 and a clock on whole milliseconds it is the original bit for bit. The queue is still handed over on
// the call after (the original's one-call hand-off; it runs once a frame, before the ticks).

#include "enhanced/render_time.h"

struct TimedRepeat
{
	unsigned char event[0x20];
	unsigned int elapsed;
	unsigned int sinceLast;
	unsigned int interval;
	unsigned int count;
	int active;
	int now;
	int counted;
	unsigned char unknown3C[4];
};

struct TimedRepeatEvent
{
	int frame;
	unsigned char unknown4[4];
	unsigned char event[0x20];
};

extern TimedRepeat unk_143E8EF80[64];
extern TimedRepeatEvent unk_143E8E580[64];
extern int unk_143E8FFD8;
extern int unk_143E8FF84;
extern const dvar_t *cl_paused;

extern "C" void Com_Memcpy(void *dest, const void *src, const unsigned int count);
int Sys_Milliseconds();
float sub_140460E10();
unsigned int sub_14028EEA0(int weapon, bool isAlternate);
void sub_1402F6560(int a, unsigned long long b, int weapon, int d, bool e, bool isAlternate, bool g, bool h, int i);

struct RepeatClock
{
	long long lastUs;
	double carryUs;  // scaled microseconds not yet given out as whole milliseconds
	int valid;
};
static RepeatClock s_repeatClock;

void sub_1402FB790()
{
	const long long nowUs = Sys_Microseconds();
	const int now = Sys_Milliseconds();
	const float scale = sub_140460E10();
	++unk_143E8FFD8;
	RepeatClock *c = &s_repeatClock;
	if (!c->valid)
	{
		c->lastUs = (long long)unk_143E8FF84 * 1000;
		c->carryUs = 0.0;
		c->valid = 1;
	}
	const double scaled = c->carryUs + (double)scale * (double)(nowUs - c->lastUs);
	c->lastUs = nowUs;
	unk_143E8FF84 = now;
	int msec = -1;
	if (scaled >= 0.0 && scaled < 2147483647000.0)
	{
		msec = (int)(scaled / 1000.0);
		c->carryUs = scaled - (double)msec * 1000.0;
	}
	if (msec < 0 || cl_paused->current.integer != 0)
	{
		c->carryUs = 0.0;  // as the original, time that isn't given out is dropped
		return;
	}
	for (int i = 0; i < 64; ++i)
	{
		TimedRepeat *t = &unk_143E8EF80[i];
		if (!t->active)
			continue;
		t->elapsed += msec;
		if (t->elapsed > 300)
		{
			t->active = 0;
			continue;
		}
		if (!t->counted)
		{
			const unsigned int limit = sub_14028EEA0(*(const int *)&t->event[0x10], t->event[0x19]);
			if (limit - 1 <= 3 && t->count >= limit)
			{
				t->count = 0;
				t->active = 0;
				t->sinceLast = 0;
				continue;
			}
		}
		unsigned int since = t->sinceLast;
		if (!t->now)
		{
			since += msec;
			t->sinceLast = since;
		}
		if (since < t->interval && !t->now)
			continue;
		t->sinceLast = 0;
		for (unsigned int j = 0; j < 64; ++j)
		{
			if (!unk_143E8E580[j].frame)
			{
				unk_143E8E580[j].frame = unk_143E8FFD8;
				Com_Memcpy(unk_143E8E580[j].event, t->event, 0x20);
				break;
			}
		}
		++t->count;
		t->now = 0;
	}
	const int previous = unk_143E8FFD8 - 1;
	for (int j = 0; j < 64; ++j)
	{
		TimedRepeatEvent *q = &unk_143E8E580[j];
		if (!q->frame || q->frame != previous)
			continue;
		const unsigned char *e = q->event;
		sub_1402F6560(*(const int *)e, *(const unsigned long long *)(e + 8), *(const int *)(e + 0x10),
		              *(const int *)(e + 0x14), e[0x18], e[0x19], e[0x1A], e[0x1B], *(const int *)(e + 0x1C));
		q->frame = 0;
	}
}
