// cgame/cg_weapons.cpp (Store build): the viewmodel.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. The name and file
// are Black Ops' (PDB, cg_weapons.cpp:4815, CG_AddViewWeapon); the body is the Store build's: it keeps the viewmodel's
// models loaded, builds a weaponState_t from cg_s with the frame's time (frametime = cg.frametime * 0.001), runs
// BG_CalculateWeaponMovement (140296F10: sway, recoil, bob, the movement angles), places the viewmodel (1402F51A0),
// keeps the weaponState_t's integrated fields in cg_s, and adds the viewmodel to the scene (1402F30A0).

#include "bgame/bg_public.h"
#include "bgame/bg_weapons.h"
#include "cgame_mp/cg_local_mp.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "cgame/cg_weapons.cpp"

struct XModel;

// A model placement (the renderer's GfxScaledPlacement): BG_CalculateWeaponMovement writes the viewmodel's origin
// offset into it, 1402F51A0 its orientation, origin and scale
struct GfxScaledPlacement
{
	float quat[4];
	float origin[3];
	float scale;
};
static_assert(sizeof(GfxScaledPlacement) == 0x20, "GfxScaledPlacement size");

static_assert(__builtin_offsetof(cg_s, viewmodelAdsState) == 0x3330, "cg_s layout (Store build)");
static_assert(__builtin_offsetof(cg_s, weapLastIdleFactor) == 0x3334, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapBaseOrigin) == 0x3338, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapBaseAngles) == 0x3344, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, cubemapShot) == 0x336C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, unknown71944) == 0x71944, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapSwayViewAngles) == 0xA9AD8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapSwayAngles) == 0xA9AE4, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapSwayOrigin) == 0xA9AF0, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapRecoilAngles) == 0xA9AFC, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weapRecoilSpeed) == 0xA9B08, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, damageTime) == 0xB5240, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, v_dmg_pitch) == 0xB525C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, xyspeed) == 0xB5264, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, gunAngles) == 0xB528C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, gunAdsOffset) == 0xB5294, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, hipViewValue) == 0x10E8C4, "cg_s layout");
static_assert(__builtin_offsetof(playerState_s, hipViewValue) == 0x634, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weaponTimeBase) == 0x13CC, "playerState_s layout");
static_assert(__builtin_offsetof(WeaponDef, gunXModel) == 0x8, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponDef, unknownModels38) == 0x38, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponDef, viewModelExtra) == 0x358, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponCompleteDef, scopes) == 0x20, "WeaponCompleteDef layout");
static_assert(__builtin_offsetof(WeaponAttachment, viewModels) == 0x28, "WeaponAttachment layout");
static_assert(__builtin_offsetof(shellshock_parms_t, view_fadeTime) == 0x14, "shellshock_parms_t layout");

extern const dvar_t *cg_drawGun;

Weapon BG_GetViewmodelWeapon(const playerState_s *ps);                     // bgame/bg_weapons_setup.cpp
const char *sub_14018DB60(LocalClientNum_t localClientNum, const clientInfo_t *ci, const characterInfo_t *info,
                          int which, int viewmodelIndex);    // the player's viewmodel (arms) model name
XModel *R_RegisterModel(const char *name);
void sub_14037AEA0(XModel *model);                     // keeps the arms model loaded this frame (name unknown)
void sub_14037AEF0(const XModel *model);               // keeps a weapon model loaded this frame (name unknown)
bool sub_14028F230(Weapon weapon, bool isAlternate);   // the weapon has a model of its own to keep (name unknown)
void sub_1402C59B0();                                  // ... and keeps it (name unknown)
const XModel *sub_1402F7640(Weapon weapon, const WeaponAttachment *scope);  // the scope's extra model (name unknown)
bool BG_IsThirdPersonMode(const playerState_s *ps);
bool sub_1402AF8A0(const playerState_s *ps, int unused);  // name unknown: with sub_14028F050 false, the gun is hidden
bool sub_14028F050(const playerState_s *ps);
bool BG_IsAimDownSight(Weapon weapon, bool isAlternate);
void sub_14027B740(const playerState_s *ps, float frametime, float *out);  // at the hip, every frame (name unknown)
int sub_140300960(LocalClientNum_t localClientNum, const playerState_s *ps, int unused);  // with pm_flags 1: no bob
int sub_140294C30(const playerState_s *ps, int perk, int unused);       // name unknown; 0x71 here
void BG_CalculateWeaponMovement(weaponState_t *ws, float *const origin, float *const angles, int bob);
void sub_1402F51A0(cg_s *cgameGlob, GfxScaledPlacement *placement, float *angles);  // places the viewmodel
void sub_1402F30A0(LocalClientNum_t localClientNum, const GfxScaledPlacement *placement, const playerState_s *ps,
                   centity_s *cent, int drawGun);      // adds the viewmodel to the scene (name unknown)

// Store 1402F38B0 (Black Ops' CG_AddViewWeapon, cg_weapons.cpp:4815): from CG_DrawActiveFrame once a frame
void CG_AddViewWeapon(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	const Weapon weapon = BG_GetViewmodelWeapon(ps);

	// the models kept loaded: the arms, the weapon's variation, its two extra models and its attachments'
	if (ps->viewmodelIndex > 0)
	{
		const int clientNum = ps->clientNum;
		sub_14037AEA0(R_RegisterModel(sub_14018DB60(localClientNum, &cgameGlob->bgs.clientinfo[clientNum],
		                                             &cgameGlob->bgs.characterinfo[clientNum], 2, ps->viewmodelIndex)));
	}
	const unsigned int weaponIndex = (unsigned char)weapon.data;
	if (weaponIndex)
	{
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

	cgameGlob->unknown71944[0] = 0;
	cgameGlob->unknown71944[1] = 0;
	if ((unsigned int)(ps->pm_type - 5) <= 1 || cgameGlob->renderingThirdPerson || BG_IsThirdPersonMode(ps))
		return;
	int drawGun = 1;
	if (cgameGlob->cubemapShot || !cg_drawGun->current.enabled || (sub_1402AF8A0(ps, 0) && !sub_14028F050(ps)))
		drawGun = 0;
	if (ps->eFlags & 0x203800)
		return;
	if (!weaponIndex)
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

	// the viewmodel's state, from cg_s, with the frame's time
	weaponState_t ws;
	ws.ps = ps;
	ws.xyspeed = cgameGlob->xyspeed;
	ws.frametime = (float)cgameGlob->frametime * 0.001f;
	ws.fLastIdleFactor = cgameGlob->weapLastIdleFactor;
	ws.time = cgameGlob->time - ps->weaponTimeBase;
	ws.damageTime = cgameGlob->damageTime ? cgameGlob->damageTime - ps->weaponTimeBase : 0;
	ws.v_dmg_pitch = cgameGlob->v_dmg_pitch;
	ws.v_dmg_roll = cgameGlob->v_dmg_roll;
	for (int i = 0; i < 3; ++i)
	{
		ws.baseAngles[i] = cgameGlob->weapBaseAngles[i];
		ws.baseOrigin[i] = cgameGlob->weapBaseOrigin[i];
		ws.recoilAngles[i] = cgameGlob->weapRecoilAngles[i];
		ws.recoilSpeed[i] = cgameGlob->weapRecoilSpeed[i];
		ws.swayAngles[i] = cgameGlob->weapSwayAngles[i];
		ws.swayOrigin[i] = cgameGlob->weapSwayOrigin[i];
		ws.swayViewAngles[i] = cgameGlob->weapSwayViewAngles[i];
	}
	ws.shellShockStart = cgameGlob->shellshock_startTime;
	ws.shellShockDuration = cgameGlob->shellshock_duration;
	ws.shellShockFadeTime = cgameGlob->shellshock_parms ? cgameGlob->shellshock_parms->view_fadeTime : 3000;
	if (frac == 0.0f)
	{
		sub_14027B740(ps, ws.frametime, &cgameGlob->hipViewValue);
		ps->hipViewValue = cgameGlob->hipViewValue;
	}

	int noBob;
	if (ps->pm_flags & 1)
		noBob = sub_140300960(localClientNum, ps, 0);
	else if (!(ps->otherFlags & 0x2000) && sub_140294C30(ps, 0x71, 0) && 0.25f > ps->weapCommon_fWeaponPosFrac)
		noBob = 1;
	else
		noBob = 0;

	GfxScaledPlacement placement;
	float angles[3];
	BG_CalculateWeaponMovement(&ws, placement.origin, angles, noBob == 0);
	sub_1402F51A0(cgameGlob, &placement, angles);

	// what the next frame starts from
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

// --- Store 1402FB790: the timed repeats ---------------------------------------------------------------------------

// A repeating event (name unknown): 64 at 143E8EF80. The first 0x20 bytes are the event 1402F6560 is called with
// (weapon at +0x10, its alternate flag at +0x19); every `interval` ms of its own clock it is queued, at most until
// the weapon's count (14028EEA0, 1..4) is reached when `counted` is clear; 300 ms after its start it ends.
struct TimedRepeat
{
	unsigned char event[0x20];
	unsigned int elapsed;    // ms since it started
	unsigned int sinceLast;  // ms since it was last queued
	unsigned int interval;
	unsigned int count;      // times queued
	int active;
	int now;                 // queue it on the next call whatever the interval
	int counted;             // nonzero: no count limit
	unsigned char unknown3C[4];
};
static_assert(sizeof(TimedRepeat) == 0x40, "TimedRepeat size");

// The queue (name unknown): 64 at 143E8E580, handed to 1402F6560 one call after they are queued
struct TimedRepeatEvent
{
	int frame;               // unk_143E8FFD8 when queued; 0 for a free slot
	unsigned char unknown4[4];
	unsigned char event[0x20];
};
static_assert(sizeof(TimedRepeatEvent) == 0x28, "TimedRepeatEvent size");

extern TimedRepeat unk_143E8EF80[64];
extern TimedRepeatEvent unk_143E8E580[64];
extern int unk_143E8FFD8;  // the calls so far (name unknown)
extern int unk_143E8FF84;  // Sys_Milliseconds at the last call (name unknown)
extern const dvar_t *cl_paused;

extern "C" void Com_Memcpy(void *dest, const void *src, const unsigned int count);  // universal/com_shared.cpp
int Sys_Milliseconds();
float sub_140460E10();                                 // the game's timescale (name unknown)
unsigned int sub_14028EEA0(int weapon, bool isAlternate);  // the weapon's repeat count, 1..4 (name unknown)
void sub_1402F6560(int a, unsigned long long b, int weapon, int d, bool e, bool isAlternate, bool g, bool h, int i);

// Store 1402FB790 (name unknown): from CG_DrawActiveFrame once a frame. Advances every active repeat by the wall
// clock's milliseconds since the last call times the timescale (truncated per call), queues the ones that are due,
// then hands over the ones the previous call queued.
void sub_1402FB790()
{
	const int now = Sys_Milliseconds();
	const float scale = sub_140460E10();
	++unk_143E8FFD8;
	const int msec = (int)(scale * (float)(now - unk_143E8FF84));
	unk_143E8FF84 = now;
	if (msec < 0 || cl_paused->current.integer != 0)
		return;
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
