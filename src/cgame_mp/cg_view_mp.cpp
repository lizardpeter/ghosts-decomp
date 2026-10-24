// cgame_mp/cg_view_mp.cpp (Store build): the cgame's frame.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. The function and
// file names are Black Ops' (server PDB, cgame_mp/cg_view_mp.cpp: CG_DrawActiveFrame, and the statics it inlines:
// UpdateKillCamEntityCache, GetCeilingHeight, CG_ValidateWeaponSelect). The Store build's frame has the same
// skeleton as Black Ops' but a different order and many more steps (docs/cgame-frame.md lists every one of them with
// its classification).
//
// Most callees are not reconstructed and have no known name: they are declared here as sub_<Store address> with
// the prototype their call sites show, and records/names.tsv records what is known of each.

#include "cgame_mp/cg_local_mp.h"
#include "bgame/bg_public.h"
#include "client_mp/client_mp.h"
#include "qcommon/dvar.h"
#include <iw6_static.h>
#include <math.h>

#define IW6_SOURCE "cgame_mp/cg_view_mp.cpp"

struct DObj;
struct XModel;
struct FxEffectDef;

// thread-local storage the original reaches through the CRT's on-demand TLS initialisation (VS2019)
extern "C" __declspec(thread) unsigned char __tls_guard;  // _external/crt/tlsdyn.cpp: TLS offset 0xD0
extern "C" void __dyn_tls_on_demand_init();

extern LocalClientNum_t g_cgameClientNum;    // the local client the bgame's traces run for
extern void *unk_143C23F60;                  // points at cg.refdef while the frame runs (name unknown)
extern int unk_143C23F68;                    // events 0x3A to fire on the player this frame; CG_TransitionPlayerState
                                             // counts them (name unknown)
extern int unk_143C177FC;                    // nonzero: delayed entities also run CG_CheckEntEvents (name unknown)
extern const void *unk_143C17818;            // a material kept loaded every frame (name unknown)
extern const char *unk_14098F720[];          // the reverb room-type names RemoteCameraSounds_RoomType indexes
extern const Bounds unk_140827238;           // the player's standing bounds: midpoint (0, 0, 35), half size (15, 15, 35)
extern const dvar_t *RemoteCameraSounds_RoomType;
extern const dvar_t *RemoteCameraSounds_DryLevel;
extern const dvar_t *RemoteCameraSounds_WetLevel;
extern const dvar_t *radarjamDistMin;
extern const dvar_t *radarjamDistMax;
extern const dvar_t *radarjamSinCurve;
extern WeaponDef *bg_weaponDefs[];

// A per-local-client effect played every `period` ms at a fixed place (name unknown): 0x54 bytes at 143E8E3F0
struct PeriodicEffect
{
	char name[0x40];       // the effect's name, as FX lookups take it
	float origin[3];
	int lastTime;          // cg.time of the last play
	int period;            // 0 or less: off
};
static_assert(sizeof(PeriodicEffect) == 0x54, "PeriodicEffect size (Store build)");
extern PeriodicEffect unk_143E8E3F0[1];

// the view position the cgame hands to another system every frame (14604Cxxx; names unknown)
extern int unk_14604C9A4;            // set to 1 whenever cg.drawFirstPersonScene is
extern bool unk_14604CD10[1];        // the remote view origin below is valid
extern bool unk_14604CD22[1];        // the view origin below is valid
extern bool unk_14604CD34[1];        // the eye position below is valid (only set when it is more than 2048 from the view)
extern float unk_14604CD48[1][3];    // cg.remoteViewOrigin
extern float unk_14604CE20[1][3];    // cg.refdef_vieworg
extern float unk_14604CEF8[1][3];    // the player's eye: origin + viewHeightCurrent

static_assert(__builtin_offsetof(cg_s, clientNum) == 0x3360, "cg_s layout (Store build)");
static_assert(__builtin_offsetof(cg_s, renderScreen) == 0x3378, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, renderingThirdPerson) == 0x718AC, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, lastMantleFlags) == 0x718B8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, heightToCeiling) == 0x718C0, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdef_displayViewport) == 0x718C8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdef_baseVieworg) == 0x71914, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdef_time) == 0x7192C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, timedFlagStart) == 0x71A48, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, timedFlagActive) == 0x71A54, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, clearedEachFrame) == 0xA9760, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdefViewAngles) == 0xA9A90, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, aimAssistView) == 0xA9AA8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, weaponSelect) == 0xB2768, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, lastWeapFlags) == 0xB4EEC, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, kickAVel) == 0xB5268, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, kickAngles) == 0xB5274, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, shellshock_parms) == 0xB5310, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, shellshockSensitivity) == 0xB5320, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, testShock_time) == 0xB5340, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, selectedLocation) == 0xB5368, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, inKillCam) == 0xB537C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, killCamType) == 0xB5394, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, killCamEntityAngles) == 0xB53A8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, killCamLookAtOrigin) == 0xB53BC, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, bgs) == 0xB54C8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, bgs.time) == 0xFAE58, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, bgs.frametime) == 0xFAE64, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, bgs.clientinfo) == 0x10A428, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, unknown10AD28) == 0x10AD28, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, drawFirstPersonScene) == 0x10E79E, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, lastVieworg) == 0x10E840, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, savedTrans) == 0x10E868, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, hudGrenadeCount) == 0x10ED48, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, radarJamLevel) == 0x10EDBC, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, scriptedViewFov) == 0x10EDC4, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, sceneUnknown) == 0x10EDF0, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, remoteViewOrigin) == 0x10EE58, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, cardCache) == 0x10EE68, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, vehicleViewActive) == 0x10F058, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, sightedClientsMask) == 0x10F05C, "cg_s layout");
static_assert(__builtin_offsetof(snapshot_s, snapFlags) == 0x3C74, "snapshot_s layout");
static_assert(__builtin_offsetof(snapshot_s, numEntities) == 0x3C80, "snapshot_s layout");
static_assert(__builtin_offsetof(snapshot_s, entities) == 0x3C88, "snapshot_s layout");
static_assert(__builtin_offsetof(WeaponDef, turretZoomSound) == 0x138, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponDef, overlayInterface) == 0x5E8, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponDef, turretFov) == 0x950, "WeaponDef layout");
static_assert(__builtin_offsetof(WeaponDef, turretScopeZoomMax) == 0x960, "WeaponDef layout");

// --- callees, in the order the frame calls them -----------------------------------------------------------------
void sub_140654BA0();                                        // the renderer's scene lists cleared (R_ClearScene role)
void sub_140654C40(LocalClientNum_t localClientNum);         // the scene's per-client state reset
void sub_1402BE670();                                        // empties the tag-effect list 1402BE7B0 walks
void sub_1403A0030(LocalClientNum_t localClientNum, int serverTime);  // effects: up to serverTime + 1
void sub_1403AEFF0(LocalClientNum_t localClientNum);         // effects: three resets
void sub_1403447B0();                                        // sets the flag at 1442D4060
void sub_14029EDB0(LocalClientNum_t localClientNum);         // the client the cgame's collision world is for
void sub_140536260(void *dest, int value, unsigned long long size);  // memset (Com_Memset)
const playerState_s *CG_GetPredictedPlayerState(LocalClientNum_t localClientNum);
void CG_ProcessSnapshots(LocalClientNum_t localClientNum);
void FX_RewindTo(LocalClientNum_t localClientNum, int time, int frametime);
bool CL_IsServerLoadingMap();
void CL_SetWaitingOnServerToLoadMap(LocalClientNum_t localClientNum, bool waiting);
void sub_1402D3230(LocalClientNum_t localClientNum);         // the predicted state's preparation (docs/fps.md 7.2)
void sub_140316200();                                        // the client's double-buffered per-frame block flips
int sub_140187D70(LocalClientNum_t localClientNum);          // a scripted camera is active (CG_ScrCamActive role)
void sub_14018A640(LocalClientNum_t localClientNum);         // the scripted camera's view (CG_ScrCamCalcView role)
void R_SetLodOrigin(const void *refdef, float scale);
void CG_CompassIncreaseRadarTime(LocalClientNum_t localClientNum);
void FX_SetNextUpdateTime(LocalClientNum_t localClientNum, int time);
shellshock_parms_t *BG_GetShellshockParms(int index);
void CG_StartShellShock(cg_s *cgameGlob, const shellshock_parms_t *parms, int start, int duration);
void CG_UpdateShellShock(LocalClientNum_t localClientNum, const shellshock_parms_t *parms, int start, int duration);
void sub_1402EA200(LocalClientNum_t localClientNum, bool active);  // the third-person vehicle view on or off
void sub_1403046D0(LocalClientNum_t localClientNum, int clientNum);  // ... its "off" for a client (thunk to 14029EFC0)
void CG_ClearHudGrenades(cg_s *cgameGlob);
DObj *Com_GetClientDObj(int handle, LocalClientNum_t localClientNum);
void CG_DObjUpdateInfo(const cg_s *cgameGlob, DObj *obj, bool notify);
void CG_ProcessClientNoteTracks(cg_s *cgameGlob, int clientNum);
void sub_140178750(LocalClientNum_t localClientNum);         // aim assist's per-frame vectors cleared
void sub_1402EC410(LocalClientNum_t localClientNum);         // the weapon's scope/overlay state
void sub_140377D80();                                        // clears 14604C980
int CG_AddPacketEntities(LocalClientNum_t localClientNum, int *delayedEntities);
void sub_1402D4BF0(LocalClientNum_t localClientNum);         // the sound listener's per-frame state (name unknown)
void sub_1402E61B0(LocalClientNum_t localClientNum);         // the environment volume at the last view origin
void sub_1402FB790();                                        // HUD timers on Sys_Milliseconds
void sub_1402F11D0(LocalClientNum_t localClientNum, void *state, int time);
bool sub_140345260(LocalClientNum_t localClientNum);         // localClientNum == 0
void sub_1401B3710(int time);
void sub_1401B2960(LocalClientNum_t localClientNum, float time, float frametime, const void *refdef, int clientNum);
void sub_14065BE30();                                        // marks a sound update due in R_SyncGpu
void sub_1402D2410();                                        // the early prediction (cg_predict_mp.cpp)
void CL_SyncGpu(int (*WorkCallback)(unsigned long long));
void sub_140376E30(int arg);
void R_ToggleSmpFrame();
void CL_Input(LocalClientNum_t localClientNum);
void sub_1402AA2A0(LocalClientNum_t localClientNum);         // a +-1 ramp moved by cls.frametime / 300
void CG_PredictPlayerState(LocalClientNum_t localClientNum);
void sub_1402FC4F0(LocalClientNum_t localClientNum);         // the equipped weapons' viewmodels
const char *sub_14018DB60(LocalClientNum_t localClientNum, const clientInfo_t *ci, const characterInfo_t *info,
                          int which, int viewmodelIndex);    // the player's viewmodel (arms) model name
XModel *R_RegisterModel(const char *name);
void sub_1402FBC30(LocalClientNum_t localClientNum, XModel *model);
bool sub_14017F630(LocalClientNum_t localClientNum);         // unk_143D33E84
void sub_140658100();
void CG_TransitionPlayerState(LocalClientNum_t localClientNum, playerState_s *ps, const transPlayerState_t *transPs);
void CG_ProcessEntity(LocalClientNum_t localClientNum, int entityNum);
void CG_CheckEntEvents(LocalClientNum_t localClientNum, centity_s *cent, int unused);
void CG_EntityEvent(LocalClientNum_t localClientNum, centity_s *cent, int event, int eventParm, bool predicted);
int sub_1402CF440(LocalClientNum_t localClientNum);          // the player's own model is updated (third person)
void sub_1402CEB10(LocalClientNum_t localClientNum);         // ... and updates it
void sub_1403AF520(LocalClientNum_t localClientNum);         // effects: worker command 0xB
void sub_140471E70(LocalClientNum_t localClientNum, int frametime);
void sub_14037E3D0(LocalClientNum_t localClientNum);         // dynamic entities from the physics (DynEntCl)
void sub_140588090(int world, int time);                     // physics: worker command 0 at the time
void sub_14019B2C0(float frametime);
bool sub_1402DF740(LocalClientNum_t localClientNum);
bool sub_1402DF750(LocalClientNum_t localClientNum);
void sub_14065B690(LocalClientNum_t localClientNum, int unused, bool a, bool b);
int BG_IsEMPJammed(const playerState_s *ps);
bool sub_1402EF4D0(LocalClientNum_t localClientNum, const cg_s *cgameGlob);
void sub_140657FC0(bool drawFirstPerson, bool a, const void *b, bool c);
void SND_SetEnvironmentEffects(int priority, const char *roomType, float dryLevel, float wetLevel, int fadeTime);
void SND_DeactivateEnvironmentEffects(int priority, int fadeTime);
bool Key_IsCatcherActive(LocalClientNum_t localClientNum, int mask);
void Key_RemoveCatcher(LocalClientNum_t localClientNum, int andMask);
void Key_AddCatcher(LocalClientNum_t localClientNum, int orMask);
bool CL_IsGamepadEnabled(LocalClientNum_t localClientNum);
void BG_KickAngles(const playerState_s *ps, int msec, float *const kickAVel, float *const kickAngles);
void sub_1402EF6B0(LocalClientNum_t localClientNum);         // the spawn sight checks for the next usercmd
void CL_SendCmd(LocalClientNum_t localClientNum);
unsigned int sub_1402F8530(const cg_s *cgameGlob, LocalClientNum_t localClientNum);  // the turret's weapon index
bool sub_1402F86E0(LocalClientNum_t localClientNum);         // ... and it can be used now
int CL_GetCurrentCmdNumber(LocalClientNum_t localClientNum);
int CL_GetUserCmd(LocalClientNum_t localClientNum, int cmdNumber, usercmd_s *ucmd);
int sub_1402C1130(LocalClientNum_t localClientNum, const void *soundAlias);  // plays a sound on the player
void CG_UpdateViewWeaponAnim(LocalClientNum_t localClientNum);
void CG_CalcViewValues(LocalClientNum_t localClientNum);
void LerpKillCamView(LocalClientNum_t localClientNum);
void sub_1402FC790(LocalClientNum_t localClientNum);         // DObj traces for a list of entities, with effects
void CG_AddViewWeapon(LocalClientNum_t localClientNum);
void sub_1402AD490(LocalClientNum_t localClientNum);         // the weapon's scope (sniper glint) state
void sub_140654E80();                                        // the renderer's first-person block cleared
float sub_14060DC10();                                       // the far plane (r_zfar or the map's)
void FX_SetNextUpdateCamera(LocalClientNum_t localClientNum, const void *refdef, const float *tanHalfFov,
                            float zfar, bool drawFirstPerson);
void sub_1402D4820(LocalClientNum_t localClientNum, int clientNum, const float *origin);  // the listener's origin
void sub_140275D90(LocalClientNum_t localClientNum);         // the slide sound loop
const FxEffectDef *sub_14039AC00(const char *name);          // an effect by name
void FX_PlayOrientedEffect(LocalClientNum_t localClientNum, const FxEffectDef *def, int startTime,
                           const float *const origin, const float (*const axis)[3]);
void sub_140304650(trace_t *results, const float *start, const float *end, const Bounds *bounds, int passEntityNum,
                   int contentMask);                         // a cgame box trace
void sub_140655200();
bool sub_1402C5700(LocalClientNum_t localClientNum);
void sub_1402C5740(LocalClientNum_t localClientNum);
void sub_1402BE7B0(LocalClientNum_t localClientNum);         // effects at entities' tags
void sub_1403AF710(LocalClientNum_t localClientNum);         // effects: worker commands
void sub_1403AF230(LocalClientNum_t localClientNum);         // effects: worker command 0
void AimAssist_UpdateScreenTargets(LocalClientNum_t localClientNum, const float *a, const float *b, const float *c,
                                   float tanHalfFovX, float tanHalfFovY);
void CG_UpdateSceneDepthOfField(LocalClientNum_t localClientNum);
unsigned int BG_GetNumWeapons();
bool sub_1402F8FC0(LocalClientNum_t localClientNum, Weapon weapon, bool isAlternate);  // selects a weapon if it can
int BG_OffhandIsUnderbarrelWeapon(const playerState_s *ps, unsigned int offhand);
const void *sub_1405D3080(int patchIndex);                   // the patch's material (mp/cac/patches.csv)
const void *sub_1405D2FD0(int backgroundIndex);              // the background's material (mp/cac/backgrounds.csv)
void sub_14037AE50(const void *material);                    // keeps a material loaded this frame
void sub_1405E8170(LocalClientNum_t localClientNum);         // empty in this build
void CG_DrawActive(LocalClientNum_t localClientNum, int renderScreen);
void sub_140179B50(LocalClientNum_t localClientNum);         // aim assist's targets, traced
void sub_1406A6C80();                                        // the sounds queued this frame start

// Store 1402EF9E0 (Black Ops' CG_UpdateThirdPerson, cgame_mp/cg_view_mp.cpp): third person for a vehicle or
// turret view (pm_type 7 and up), otherFlags 2, linkFlags 4, a kill cam of a type other than 0 and a scripted
// camera; while
// following another player (otherFlags 0x2000, no kill cam) followThirdPerson, or always with otherFlags 0x8000000
void CG_UpdateThirdPerson(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const playerState_s *ps = &cgameGlob->nextSnap->ps;
	if (ps->pm_type >= 7 || (ps->otherFlags & 2) || (ps->linkFlags & 4)
	    || (cgameGlob->inKillCam && cgameGlob->killCamType) || sub_140187D70(localClientNum))
	{
		cgameGlob->renderingThirdPerson = 1;
		return;
	}
	const int otherFlags = cgameGlob->nextSnap->ps.otherFlags;
	if ((otherFlags & 0x2000) && !cgameGlob->inKillCam)
		cgameGlob->renderingThirdPerson = (otherFlags & 0x8000000) ? 1 : cgameGlob->followThirdPerson;
	else
		cgameGlob->renderingThirdPerson = 0;
}

// Black Ops' UpdateKillCamEntityCache (cgame_mp/cg_view_mp.cpp), inlined: the kill cam's entities' poses
static inline void UpdateKillCamEntityCache(cg_s *cgameGlob, LocalClientNum_t localClientNum)
{
	if (!cgameGlob->inKillCam)
		return;
	if (cgameGlob->killCamEntity != ENTITYNUM_NONE)
	{
		const centity_s *cent = CG_GetEntity(localClientNum, cgameGlob->killCamEntity);
		cgameGlob->killCamEntityOrigin[0] = cent->pose_origin[0];
		cgameGlob->killCamEntityOrigin[1] = cent->pose_origin[1];
		cgameGlob->killCamEntityOrigin[2] = cent->pose_origin[2];
		cgameGlob->killCamEntityAngles[0] = cent->pose_angles[0];
		cgameGlob->killCamEntityAngles[1] = cent->pose_angles[1];
		cgameGlob->killCamEntityAngles[2] = cent->pose_angles[2];
	}
	if (cgameGlob->killCamLookAtEntity != ENTITYNUM_NONE)
	{
		const centity_s *cent = CG_GetEntity(localClientNum, cgameGlob->killCamLookAtEntity);
		if (cent->flags & 1)
		{
			cgameGlob->killCamLookAtOrigin[0] = cent->pose_origin[0];
			cgameGlob->killCamLookAtOrigin[1] = cent->pose_origin[1];
			cgameGlob->killCamLookAtOrigin[2] = cent->pose_origin[2] + 50.0f;
		}
	}
}

// Black Ops' GetCeilingHeight (cgame_mp/cg_view_mp.cpp), inlined: the room above the player, for the effects
static inline void GetCeilingHeight(cg_s *cgameGlob)
{
	const playerState_s *ps = &cgameGlob->predictedPlayerState;
	float end[3];
	end[0] = ps->origin[0];
	end[1] = ps->origin[1];
	end[2] = ps->origin[2] + 1024.0f;
	trace_t trace;
	sub_140304650(&trace, ps->origin, end, &unk_140827238, ENTITYNUM_NONE, 1);
	if (trace.fraction >= 1.0f)
		cgameGlob->heightToCeiling = 3.4028235e38f;
	else
		cgameGlob->heightToCeiling = ((end[2] - ps->origin[2]) * trace.fraction + ps->origin[2]) - ps->origin[2];
}

// bgame's inline lookups of an equipped weapon (inlined in the Store build)
static inline bool BG_PlayerHasEquippedWeapon(const playerState_s *ps, const Weapon weapon)
{
	if (!(unsigned char)weapon.data)
		return false;
	for (int i = 0; i < 15; ++i)
	{
		if (ps->weaponsEquipped[i].data == weapon.data)
			return true;  // the original also tests i >= 0 and &weapEquippedData[i] != NULL, both always true
	}
	return false;
}

static inline const PlayerEquippedWeaponState *BG_GetEquippedWeaponState(const playerState_s *ps, const Weapon weapon)
{
	for (int i = 0; i < 15; ++i)
	{
		if (ps->weaponsEquipped[i].data == weapon.data)
			return &ps->weapEquippedData[i];
	}
	return nullptr;
}

// Black Ops' CG_ValidateWeaponSelect (cgame_mp/cg_view_mp.cpp), inlined: a selection past the weapon table is
// replaced by the first equipped weapon that can be selected
static inline void CG_ValidateWeaponSelect(cg_s *cgameGlob, LocalClientNum_t localClientNum)
{
	if ((unsigned char)cgameGlob->weaponSelect < BG_GetNumWeapons())
		return;
	cgameGlob->weaponSelect = 0;
	cgameGlob->weaponSelectAlternate = 0;
	const playerState_s *ps = &cgameGlob->predictedPlayerState;
	for (int i = 0; i < 15; ++i)
	{
		const Weapon weapon = ps->weaponsEquipped[i];
		if (!(unsigned char)weapon.data || !BG_PlayerHasEquippedWeapon(ps, weapon))
			continue;
		const PlayerEquippedWeaponState *state = BG_GetEquippedWeaponState(ps, weapon);
		const bool isAlternate = state ? state->inAltMode : false;
		if (sub_1402F8FC0(localClientNum, weapon, isAlternate))
			return;
	}
}

// Store 1402E7860 (Black Ops' CG_DrawActiveFrame, cg_view_mp.cpp:4816): the cgame's frame, from CL_CGameRendering
// (14031B150) with cl.serverTime. Returns 0 without drawing when the screen isn't rendered, there is no next
// snapshot or the server changes the map, else 1.
int CG_DrawActiveFrame(LocalClientNum_t localClientNum, int serverTime, DemoType demoType, CubemapShot cubemapShot, int cubemapSize,
                       int renderScreen, int drawRenderScreen)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	sub_140654BA0();
	sub_140654C40(localClientNum);
	sub_1402BE670();
	sub_1403A0030(localClientNum, serverTime);
	sub_1403AEFF0(localClientNum);
	sub_1403447B0();
	sub_14029EDB0(localClientNum);
	unk_143C23F60 = cgameGlob->refdef_displayViewport;
	sub_140536260(cgameGlob->clearedEachFrame, 0, sizeof(cgameGlob->clearedEachFrame));

	// the frame's time
	cgameGlob->oldTime = cgameGlob->time;
	cgameGlob->cubemapSize = cubemapSize;
	cgameGlob->renderScreen = renderScreen;
	cgameGlob->time = serverTime;
	cgameGlob->bgs.time = serverTime;
	cgameGlob->demoType = demoType;
	cgameGlob->cubemapShot = cubemapShot;
	const playerState_s *lastPs = CG_GetPredictedPlayerState(localClientNum);
	const int frametime = cgameGlob->time - cgameGlob->oldTime;
	cgameGlob->frametime = frametime;
	if (frametime < 0)
	{
		cgameGlob->frametime = 0;
		cgameGlob->oldTime = cgameGlob->time;
	}
	cgameGlob->bgs.frametime = frametime >= 0 ? frametime : 0;
	cgameGlob->radarJamDistance = -1.0f;

	if (!__tls_guard)
		__dyn_tls_on_demand_init();
	const int inKillCam = cgameGlob->inKillCam;
	bgs = &cgameGlob->bgs;
	CG_ProcessSnapshots(localClientNum);
	if (frametime < 0 && cgameGlob->inKillCam == inKillCam)
		FX_RewindTo(localClientNum, cgameGlob->time, frametime);

	if (!cgameGlob->renderScreen || !cgameGlob->nextSnap || (cgameGlob->nextSnap->snapFlags & 2)
	    || CL_IsServerLoadingMap())
	{
		if (!__tls_guard)
			__dyn_tls_on_demand_init();
		bgs = nullptr;
		return 0;
	}

	CL_SetWaitingOnServerToLoadMap(localClientNum, false);
	g_cgameClientNum = localClientNum;
	sub_1402D3230(localClientNum);
	sub_140316200();
	cgameGlob->refdef_vieworg[0] = cgameGlob->refdef_baseVieworg[0];
	cgameGlob->refdef_time = cgameGlob->time;
	cgameGlob->refdef_vieworg[2] = cgameGlob->refdef_baseVieworg[2];
	cgameGlob->refdef_vieworg[1] = cgameGlob->refdef_baseVieworg[1];
	cgameGlob->refdef_frametime = cgameGlob->frametime;
	if (sub_140187D70(localClientNum))
		sub_14018A640(localClientNum);
	R_SetLodOrigin(cgameGlob->refdef_displayViewport, 1.0f);
	CG_CompassIncreaseRadarTime(localClientNum);
	FX_SetNextUpdateTime(localClientNum, cgameGlob->time);

	// the shell shock: the snapshot's, or the test shock
	const snapshot_s *snap = cgameGlob->snap;
	const int shockIndex = *(const int *)((const unsigned char *)snap + 0xE9C);  // ps.shellshockIndex
	int shockStart, shockDuration;
	if (!shockIndex)
	{
		shockStart = cgameGlob->testShock_time;
		shockDuration = cgameGlob->testShock_duration;
	}
	else
	{
		shockStart = *(const int *)((const unsigned char *)snap + 0xEA0);       // ps.shellshockTime
		shockDuration = *(const int *)((const unsigned char *)snap + 0xEA4);    // ps.shellshockDuration
	}
	CG_StartShellShock(cgameGlob, BG_GetShellshockParms(shockIndex), shockStart, shockDuration);
	CG_UpdateShellShock(localClientNum, cgameGlob->shellshock_parms, cgameGlob->shellshock_startTime,
	                    cgameGlob->shellshock_duration);

	CG_UpdateThirdPerson(localClientNum);
	if (cgameGlob->renderingThirdPerson && cgameGlob->predictedPlayerState.vehicleState.entity != ENTITYNUM_NONE)
	{
		sub_1402EA200(localClientNum, true);
	}
	else if (cgameGlob->vehicleViewActive)
	{
		sub_1403046D0(localClientNum, cgameGlob->predictedPlayerState.clientNum);
		cgameGlob->vehicleViewActive = false;
	}
	CG_ClearHudGrenades(cgameGlob);

	// the animation of every entity in the next snapshot, and its notetracks
	unsigned int count = (unsigned int)cgameGlob->nextSnap->numEntities;
	for (unsigned long long i = 0; count; ++i, --count)
	{
		const int entityNum = *(const int *)cgameGlob->nextSnap->entities[i];
		DObj *obj = Com_GetClientDObj(entityNum, localClientNum);
		if (obj)
		{
			CG_DObjUpdateInfo(cgameGlob, obj, true);
			CG_ProcessClientNoteTracks(cgameGlob, entityNum);
		}
	}
	sub_140178750(localClientNum);
	sub_1402EC410(localClientNum);
	sub_140377D80();
	int delayedEntities[16];
	const long long delayedCount = CG_AddPacketEntities(localClientNum, delayedEntities);

	// the radar jamming level: 1/15 of the way to its target per frame
	float jam = cgameGlob->radarJamLevel;
	float jamFloor = 0.5f;
	const float jamDistance = cgameGlob->radarJamDistance;
	if (cgameGlob->predictedPlayerState.radarBlocked || jam > 0.0f
	    || (!(0.0f >= jamDistance) && !(jamDistance > radarjamDistMax->current.value)))
	{
		const float distMax = radarjamDistMax->current.value;
		const float distMin = radarjamDistMin->current.value;
		const float range = distMax - distMin;
		if (range != 0.0f)
		{
			float distance;
			if (cgameGlob->radarJamDistance == -1.0f)
			{
				cgameGlob->radarJamDistance = distMax;
				distance = distMax;
			}
			else
			{
				distance = cgameGlob->radarJamDistance;
				if (distMin > distance)
				{
					cgameGlob->radarJamDistance = distMin;
					distance = distMin;
				}
			}
			float target = 1.0f - (distance - distMin) / range;
			if (radarjamSinCurve->current.enabled)
				target = sinf(target * 3.1415927f * 0.5f);
			const int strength = cgameGlob->predictedPlayerState.radarStrength;
			if (strength <= -3)
				jamFloor = 1.0f;
			else if (strength > -2)
				jamFloor = strength > -1 ? 0.0f : 0.3f;
			target = target > jamFloor ? target : jamFloor;
			const float toGo = target - jam;
			if (0.01f > toGo * toGo)
				jam = target;
			if (target != jam)
				jam = toGo / 15.0f + jam;
			float level = jam - 1.0f >= 0.0f ? 1.0f : jam;
			if (0.0f - jam >= 0.0f)
				level = 0.0f;
			cgameGlob->radarJamLevel = level;
		}
	}

	sub_1402D4BF0(localClientNum);
	sub_1402E61B0(localClientNum);
	sub_1402FB790();
	sub_1402F11D0(localClientNum, cgameGlob->unknown10AD28, cgameGlob->time);
	if (sub_140345260(localClientNum))
	{
		sub_1401B3710(cgameGlob->time);
		sub_1401B2960(localClientNum, (float)cgameGlob->time * 0.001f,
		              (float)(cgameGlob->time - cgameGlob->oldTime) * 0.001f, cgameGlob->refdef_displayViewport,
		              cgameGlob->clientNum);
		sub_14065BE30();
		sub_1402D2410();
		CL_SyncGpu(nullptr);
		sub_140376E30(1);
	}
	R_ToggleSmpFrame();
	CL_Input(localClientNum);
	sub_1402AA2A0(localClientNum);
	CG_PredictPlayerState(localClientNum);
	sub_1402FC4F0(localClientNum);
	if (cgameGlob->predictedPlayerState.viewmodelIndex > 0)
	{
		const int clientNum = cgameGlob->predictedPlayerState.clientNum;
		const char *name = sub_14018DB60(localClientNum, &cgameGlob->bgs.clientinfo[clientNum],
		                                 &cgameGlob->bgs.characterinfo[clientNum], 2,
		                                 cgameGlob->predictedPlayerState.viewmodelIndex);
		sub_1402FBC30(localClientNum, R_RegisterModel(name));
	}
	if (sub_14017F630(localClientNum))
		sub_140658100();

	// the events of the new predicted state
	unk_143C23F68 = 0;
	CG_TransitionPlayerState(localClientNum, &cgameGlob->predictedPlayerState, &cgameGlob->savedTrans);
	for (long long i = 0; i < delayedCount; ++i)
	{
		CG_ProcessEntity(localClientNum, delayedEntities[i]);
		if (unk_143C177FC)
			CG_CheckEntEvents(localClientNum, CG_GetEntity(localClientNum, delayedEntities[i]), 0);
	}
	if (unk_143C23F68 > 0)
	{
		int entityNum = cgameGlob->predictedPlayerState.viewlocked_entNum;
		if (entityNum != ENTITYNUM_NONE || (entityNum = cgameGlob->predictedPlayerState.vehicleState.entity) != ENTITYNUM_NONE)
		{
			centity_s *cent = CG_GetEntity(localClientNum, entityNum);
			if (cent)
			{
				for (int i = 0; i < unk_143C23F68; ++i)
					CG_EntityEvent(localClientNum, cent, 0x3A, 0, false);
			}
		}
	}
	if (sub_1402CF440(localClientNum))
		sub_1402CEB10(localClientNum);
	sub_1403AF520(localClientNum);
	sub_140471E70(localClientNum, cgameGlob->frametime);
	if (sub_140345260(localClientNum))
	{
		sub_14037E3D0(localClientNum);
		sub_140588090(0, cgameGlob->time);
		sub_14019B2C0((float)cgameGlob->frametime * 0.001f);
	}
	const bool b = sub_1402DF740(localClientNum);
	const bool a = sub_1402DF750(localClientNum);
	sub_14065B690(localClientNum, 0, a, b);

	// whether the first-person scene (the viewmodel) is drawn
	bool drawFirstPerson;
	if (!BG_IsEMPJammed(&cgameGlob->predictedPlayerState)
	    && (!cgameGlob->inKillCam
	        || (cgameGlob->killCamType != 1 && cgameGlob->killCamType != 3 && cgameGlob->killCamType != 7))
	    && ((cgameGlob->predictedPlayerState.otherFlags & 8)
	            ? (!cgameGlob->inKillCam || !(cgameGlob->predictedPlayerState.otherFlags & 0x400000))
	            : sub_1402EF4D0(localClientNum, cgameGlob)))
	{
		cgameGlob->drawFirstPersonScene = true;
		drawFirstPerson = true;
		unk_14604C9A4 = 1;
	}
	else
	{
		drawFirstPerson = false;
		cgameGlob->drawFirstPersonScene = false;
	}
	sub_140657FC0(drawFirstPerson, !(cgameGlob->predictedPlayerState.otherFlags & 8), cgameGlob->sceneUnknown,
	              !(cgameGlob->predictedPlayerState.otherFlags & 0x1000));

	// a remote camera's reverb
	if (cgameGlob->predictedPlayerState.otherFlags & 0x20)
		SND_SetEnvironmentEffects(4, unk_14098F720[RemoteCameraSounds_RoomType->current.integer],
		                          RemoteCameraSounds_DryLevel->current.value, RemoteCameraSounds_WetLevel->current.value, 0);
	else
		SND_DeactivateEnvironmentEffects(4, 0);

	// location selection: the key catcher follows the player state; a new selection starts at the map's centre
	bool resetSelection = true;
	if (!cgameGlob->predictedPlayerState.locationSelectionInfo || (cgameGlob->predictedPlayerState.otherFlags & 0x2000)
	    || cgameGlob->predictedPlayerState.pm_type == 5)
	{
		if (Key_IsCatcherActive(localClientNum, KEYCATCH_LOCATION_SELECTION))
			Key_RemoveCatcher(localClientNum, ~KEYCATCH_LOCATION_SELECTION);
	}
	else if (Key_IsCatcherActive(localClientNum, KEYCATCH_LOCATION_SELECTION))
	{
		resetSelection = false;
	}
	else
	{
		Key_AddCatcher(localClientNum, KEYCATCH_LOCATION_SELECTION);
	}
	if (resetSelection)
	{
		cgameGlob->selectedLocation[0] = 0.5f;
		cgameGlob->selectedLocation[1] = 0.5f;
		cgameGlob->selectedLocationAngle = 0.0f;
		if (!CL_IsGamepadEnabled(localClientNum))
		{
			cgameGlob->selectedDirectionPoint[1] = 0.5f;
			cgameGlob->selectedDirectionPoint[0] = 0.5f;
		}
	}

	// the view kick, while the server says the player plays (otherFlags 0x4000)
	if (cgameGlob->predictedPlayerState.otherFlags & 0x4000)
	{
		BG_KickAngles(&cgameGlob->predictedPlayerState, cgameGlob->frametime, cgameGlob->kickAVel, cgameGlob->kickAngles);
	}
	else
	{
		cgameGlob->kickAVel[0] = 0.0f;
		cgameGlob->kickAVel[1] = 0.0f;
		cgameGlob->kickAVel[2] = 0.0f;
		cgameGlob->kickAngles[0] = 0.0f;
		cgameGlob->kickAngles[1] = 0.0f;
		cgameGlob->kickAngles[2] = 0.0f;
	}
	sub_1402EF6B0(localClientNum);
	CL_SendCmd(localClientNum);

	// a turret's FOV: its scope zooms with the forward/back keys, else hip to ADS
	const unsigned int turret = sub_1402F8530(cgameGlob, cgameGlob->localClientNum);
	if ((unsigned char)turret)
	{
		const WeaponDef *weapDef = bg_weaponDefs[(unsigned char)turret];
		float fov;
		if (sub_1402F86E0(cgameGlob->localClientNum) && weapDef->overlayInterface == 2)
		{
			usercmd_s cmd;
			CL_GetUserCmd(cgameGlob->localClientNum, CL_GetCurrentCmdNumber(cgameGlob->localClientNum), &cmd);
			const float oldFov = cgameGlob->scriptedViewFov;
			const float zoomed = (float)cgameGlob->frametime / 1000.0f * ((float)cmd.forwardmove / -127.0f)
			                     * weapDef->turretScopeZoomRate + oldFov;
			fov = weapDef->turretScopeZoomMin;
			if (!(fov > zoomed))
				fov = weapDef->turretScopeZoomMax < zoomed ? weapDef->turretScopeZoomMax : zoomed;
			if (__builtin_fabsf(fov - oldFov) > 0.0f && weapDef->turretZoomSound)
				sub_1402C1130(cgameGlob->localClientNum, weapDef->turretZoomSound);
		}
		else
		{
			const float frac = cgameGlob->predictedPlayerState.weapCommon_fWeaponPosFrac;
			fov = (1.0f - frac) * weapDef->turretFov + frac * weapDef->turretFovADS;
		}
		cgameGlob->scriptedViewFov = fov;
	}

	// the view
	CG_UpdateViewWeaponAnim(localClientNum);
	UpdateKillCamEntityCache(cgameGlob, localClientNum);
	CG_CalcViewValues(localClientNum);
	LerpKillCamView(localClientNum);
	cgameGlob->lastVieworg[0] = cgameGlob->refdef_vieworg[0];
	cgameGlob->lastVieworg[2] = cgameGlob->refdef_vieworg[2];
	cgameGlob->lastVieworg[1] = cgameGlob->refdef_vieworg[1];
	sub_1402FC790(localClientNum);
	CG_AddViewWeapon(localClientNum);
	sub_1402AD490(localClientNum);
	if (cgameGlob->remoteMissileCam || cgameGlob->drawFirstPersonScene)
		sub_140654E80();
	const bool drawFirstPersonFx = cgameGlob->drawFirstPersonScene;
	FX_SetNextUpdateCamera(localClientNum, cgameGlob->refdef_displayViewport, &cgameGlob->refdef_tanHalfFovX,
	                       sub_14060DC10(), drawFirstPersonFx);
	sub_1402D4820(localClientNum, cgameGlob->predictedPlayerState.clientNum, cgameGlob->refdef_vieworg);
	sub_140275D90(localClientNum);

	PeriodicEffect *effect = &unk_143E8E3F0[localClientNum];
	if (effect->period >= 1 && cgameGlob->time > effect->period + effect->lastTime)
	{
		const FxEffectDef *def = sub_14039AC00(effect->name);
		const int time = cgameGlob->time;
		float axis[3][3];
		axis[2][2] = 0.0f;
		axis[0][0] = 0.0f;
		axis[0][1] = 0.0f;
		axis[0][2] = 1.0f;
		axis[1][0] = 1.0f;
		axis[1][1] = 0.0f;
		axis[1][2] = 0.0f;
		axis[2][0] = 0.0f;
		axis[2][1] = 1.0f;
		FX_PlayOrientedEffect(localClientNum, def, time, effect->origin, axis);
		effect->lastTime = time;
	}

	GetCeilingHeight(cgameGlob);
	sub_140655200();
	if (sub_1402C5700(localClientNum))
		sub_1402C5740(localClientNum);
	sub_1402BE7B0(localClientNum);
	sub_1403AF710(localClientNum);
	sub_1403AF230(localClientNum);
	AimAssist_UpdateScreenTargets(localClientNum, cgameGlob->aimAssistView[0], cgameGlob->aimAssistView[1],
	                              cgameGlob->aimAssistView[2], cgameGlob->refdef_tanHalfFovX,
	                              cgameGlob->refdef_tanHalfFovY);
	CG_UpdateSceneDepthOfField(localClientNum);
	if (cgameGlob->snap && cgameGlob->timedFlagActive && cgameGlob->timedFlagDuration > 0)
	{
		cgameGlob->timedFlagLastTime = cgameGlob->time;
		if (cgameGlob->time - cgameGlob->timedFlagStart > cgameGlob->timedFlagDuration)
			*(unsigned short *)&cgameGlob->timedFlagActive = 0;
	}

	CG_ValidateWeaponSelect(cgameGlob, localClientNum);
	if (cgameGlob->weaponSelectAlternate
	    && BG_OffhandIsUnderbarrelWeapon(&cgameGlob->predictedPlayerState, 0xC000))
	{
		cgameGlob->weaponSelectAlternate =
		    (cgameGlob->predictedPlayerState.weapCommon_weapFlags & 0x80000) ? cgameGlob->weaponSelectAlternate : 0;
	}

	// the player cards' materials of every client, looked up again when a client's card changed
	for (int i = 0; i < 18; ++i)
	{
		if (!cgameGlob->bgs.characterinfo[i].infoValid)
			continue;
		unsigned short ids[2];
		ids[0] = cgameGlob->bgs.clientinfo[i].patchIndex;
		ids[1] = cgameGlob->bgs.clientinfo[i].backgroundIndex;
		ClientCardCache *cache = &cgameGlob->cardCache[i];
		for (unsigned int j = 0; j < 2; ++j)
		{
			const void *material = cache->materials[j];
			const unsigned short id = ids[j];
			if (!material || cache->ids[j] != id)
			{
				if (j == 0)
					material = sub_1405D3080(id);
				else if (j == 1)
					material = sub_1405D2FD0(id);
				else
					material = nullptr;
				cache->materials[j] = material;
				cache->ids[j] = id;
			}
			sub_14037AE50(material);
		}
	}
	sub_1405E8170(localClientNum);
	sub_14037AE50(unk_143C17818);

	// the view and the eye for 14604Cxxx
	const playerState_s *ps = &cgameGlob->predictedPlayerState;
	const float eyeZ = ps->viewHeightCurrent + ps->origin[2];
	const float dx = ps->origin[0] - cgameGlob->refdef_vieworg[0];
	unk_14604CE20[localClientNum][0] = cgameGlob->refdef_vieworg[0];
	unk_14604CE20[localClientNum][1] = cgameGlob->refdef_vieworg[1];
	const float dy = ps->origin[1] - cgameGlob->refdef_vieworg[1];
	unk_14604CE20[localClientNum][2] = cgameGlob->refdef_vieworg[2];
	unk_14604CD22[localClientNum] = true;
	const float dz = eyeZ - cgameGlob->refdef_vieworg[2];
	if (dy * dy + dx * dx + dz * dz > 4194304.0f)
	{
		unk_14604CEF8[localClientNum][0] = ps->origin[0];
		unk_14604CEF8[localClientNum][1] = ps->origin[1];
		unk_14604CEF8[localClientNum][2] = eyeZ;
		unk_14604CD34[localClientNum] = true;
	}
	bool remoteValid;
	if ((unsigned int)ps->pm_type <= 1 && !(ps->otherFlags & 0x2000))
	{
		cgameGlob->remoteViewOriginValid = false;
		remoteValid = false;
	}
	else
	{
		remoteValid = cgameGlob->remoteViewOriginValid;
		if (remoteValid)
		{
			unk_14604CD48[localClientNum][0] = cgameGlob->remoteViewOrigin[0];
			unk_14604CD48[localClientNum][2] = cgameGlob->remoteViewOrigin[2];
			unk_14604CD48[localClientNum][1] = cgameGlob->remoteViewOrigin[1];
		}
	}
	unk_14604CD10[localClientNum] = remoteValid;

	CG_DrawActive(localClientNum, drawRenderScreen);
	sub_140179B50(localClientNum);
	if (!__tls_guard)
		__dyn_tls_on_demand_init();
	bgs = nullptr;
	sub_1406A6C80();
	cgameGlob->viewTeleported = false;
	cgameGlob->lastMantleFlags = *(const int *)((const unsigned char *)lastPs + 0x270);  // mantleState.flags
	cgameGlob->lastWeapFlags = lastPs->weapCommon_weapFlags;
	return 1;
}
