// enhanced/cgame_mp/cg_view_step.cpp: the view drawn at the render time (records/patches.tsv P0017; docs/fps.md 6.3, 7.6).
//
// With fixed 5 ms usercmds (enhanced/client_mp/cl_fixed_cmds.cpp) the predicted state ends at the newest command's time,
// 0 to 4 ms before the render time cl->serverTime, and most frames at high frame rates make no command, so the
// original would draw the same origin and angles for several frames (docs/fps.md 7.5). Here, after the faithful
// prediction, one more Pmove runs on copies of the predicted state and of cg_pmove with the temporary command
// cl_viewCmd (the newest command's input, this frame's angles, serverTime = cl->serverTime). Only its movement fields
// (origin, velocity, view angles, bob cycle, view height, lean) are put into cg.predictedPlayerState, from the end of
// CG_PredictPlayerState to the end of CG_DrawActive: what CG_TransitionPlayerState, the view, the viewmodel and the
// scene read in between. The canonical values are put back at the end of CG_DrawActive, and (a no-op unless still
// swapped) at the start of CG_SavePlayerState, the early prediction and CG_PredictPlayerState. Nothing of the
// temporary step reaches the game: its events stay in the copy's pe, the weapon state, delta_angles and every
// cg_pmove field are not swapped, the prediction error, step smoothing, platform cache and item pickups are computed
// only by the faithful code, and the per-client character info the animation conditions are written to is saved and
// restored around the step.
//
// The faithful functions are copied here unchanged (src/cgame_mp/cg_predict_mp.cpp, cg_draw_mp.cpp) and wrapped.

#include <math.h>

#include <iw6_static.h>

#include "bgame/bg_public.h"
#include "cgame_mp/cg_local_mp.h"
#include "enhanced/view_step.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "cgame_mp/cg_predict_mp.cpp"

enum StanceState
{
	CL_STANCE_STAND = 0x0,
};

IW6_STATIC pmove_t cg_pmove[1] IW6_AT("", "cg_pmove");
IW6_STATIC int cg_itemEntityCount IW6_AT("", "cg_itemEntityCount");
IW6_STATIC int cg_itemLocalClientNum IW6_AT("", "cg_itemLocalClientNum");
IW6_STATIC centity_s *cg_itemEntities[256] IW6_AT("", "cg_itemEntities");

extern const dvar_t *cg_errorDecay;          // cgame_mp/cg_main_mp.cpp
extern const dvar_t *cg_viewZSmoothingMin;
extern const dvar_t *cg_viewZSmoothingMax;
extern const dvar_t *cg_viewZSmoothingTime;
extern int unk_143E96824;                    // client_mp: a client mode, 0..3 (name unknown)

int CL_GetCurrentCmdNumber(LocalClientNum_t localClientNum);                      // client_mp/cl_cgame_mp.cpp
int CL_GetUserCmd(LocalClientNum_t localClientNum, int cmdNumber, usercmd_s *ucmd);
void CL_SetUserCmdOrigin(LocalClientNum_t localClientNum, const playerState_s *ps, const float *selectedLocation,
                         float selectedLocationAngle);
void sub_140306FD0(LocalClientNum_t localClientNum, const PlayerVehicleState *vehicleState);
void CL_SetStance(LocalClientNum_t localClientNum, StanceState stance);          // client_mp/cl_input.cpp
void Pmove(pmove_t *pm);                                                          // bgame/bg_pmove.cpp
void BG_EvaluateTrajectory(const trajectory_t *tr, int atTime, float *const result);  // bgame/bg_misc.cpp
void BG_PlayerStateToEntityState(const playerState_s *ps, entityState_s *s, int snap);
void BG_PlayerToEntity_ProcessEvents(const playerState_s *ps, entityState_s *s, unsigned char handler);
int BG_PlayerTouchesItem(const playerState_s *ps, const entityState_s *item, int atTime);
int BG_CanItemBeGrabbed(const entityState_s *ent, const playerState_s *ps, int touched);
void BG_UpdateAnglesMovingPlatform(playerState_s *ps, const float *const deltaAngles, const float *const platformAngles,
                                   float *const angleChange);                     // bgame/bg_pmove.cpp
void BG_UpdateDirectionMovingPlatform(float *const dir, const float *const platformAngles, const float *const deltaAngles);
void BG_UpdatePointMovingPlatform(float *const point, const float *const platformOrigin, const float *const platformAngles,
                                  const float *const deltaAngles, const float *const deltaOrigin);
// cgame_mp/cg_ents_mp.cpp (Black Ops' CG_AdjustPositionForMover, with the origin change and the predicting state
// added): moves `in` with mover moverNum from fromTime to toTime
void CG_AdjustPositionForMover(LocalClientNum_t localClientNum, const float *in, int moverNum, int fromTime, int toTime,
                               float *out, float *outDeltaOrigin, float *outDeltaAngles, playerState_s *ps, pmove_t *pm);
bool sub_140345260(LocalClientNum_t localClientNum);  // localClientNum == 0 (name unknown)
bool sub_140345280(LocalClientNum_t localClientNum);  // localClientNum < 1 (name unknown)
void sub_140304650(trace_t *results, const float *start, const float *end, const Bounds *bounds, int passEntityNum,
                   int contentMask);                   // a cgame trace with a box (name unknown)
void sub_140178C50(LocalClientNum_t localClientNum);  // adds the predicted origin's change since the saved state to
                                                       // a per-client vector at 140CF8470 (name unknown)
int sub_140267140(Weapon weapon);                      // the weapon's type is 5 (name unknown)
int sub_140267880(const entityState_s *item, const playerState_s *ps);  // the player can take the item's ammo (name unknown)
void sub_1402B8F80(LocalClientNum_t localClientNum, int entityNum, int event, Weapon eventParm, bool predicted);
void sub_1402CC6E0(LocalClientNum_t localClientNum, playerState_s *ps);  // the melee charge target (name unknown)
void sub_140277AB0(const playerState_s *ps, entityState_s *vehicle, int unused1, int unused2);  // the vehicle's state
void sub_1402EF5D0(LocalClientNum_t localClientNum, const playerState_s *ps, cg_s *cgameGlob);  // platform delta
void sub_1405BAAA0(LocalClientNum_t localClientNum);  // remote camera transitions; may move cl->clViewangles
void sub_1402D0AC0(LocalClientNum_t localClientNum);  // omnvar-driven state (name unknown)

void CL_SetFOVSensitivityScale(LocalClientNum_t localClientNum, float scale);       // client_mp/cl_cgame_mp.cpp
void CL_SetUserCmdAimValues(LocalClientNum_t localClientNum, const float *kickAngles);
void CL_SetUserCmdWeapons(LocalClientNum_t localClientNum, unsigned int weapon, unsigned int offHand,
                          int alternate);
void CL_SetExtraButtons(LocalClientNum_t localClientNum, int buttons);
void CL_RenderScene(LocalClientNum_t localClientNum, const void *refdef, int renderScreen);
void sub_1402891D0(unsigned int offHand);  // empty in this build (Black Ops' BG_AssertOffhandIndexOrNone)



int CG_PredictPlayerState_Internal(LocalClientNum_t localClientNum, int moverEarly);  // src
void CG_ExtractTransPlayerState(const playerState_s *ps, transPlayerState_t *transPs);  // src
extern "C" unsigned int _tls_index;

int cg_renderTimeView = 1;

#define CHARACTER_INFO_SIZE 0x5D8  // characterInfo_t, the per-client animation state BG_AnimUpdatePlayerStateConditions writes

// The local client's characterInfo_t: the bgame's per-thread client info array (a pointer at +0x10 of the thread's TLS
// block, as the Store build's BG_AnimUpdatePlayerStateConditions reads it) indexed by clientNum
static unsigned char *CG_CharacterInfo(int clientNum)
{
	unsigned char **tlsArray;
	__asm__ volatile("movq %%gs:0x58, %0" : "=r"(tlsArray));
	unsigned char *block = tlsArray[_tls_index];
	unsigned char *infos = *(unsigned char **)(block + 0x10);
	return infos ? infos + (long long)clientNum * CHARACTER_INFO_SIZE : nullptr;
}

struct CanonicalView
{
	int active;
	float origin[3];
	float velocity[3];
	float viewangles[3];
	int bobCycle;
	float viewHeightCurrent;
	float leanf;
};
static CanonicalView s_canonical;
static playerState_s s_viewPs;
static pmove_t s_viewPm;
static unsigned char s_characterInfo[CHARACTER_INFO_SIZE];

static void CG_CopyViewFields(float *origin, float *velocity, float *viewangles, int *bobCycle, float *viewHeight,
                              float *leanf, const float *fromOrigin, const float *fromVelocity, const float *fromAngles,
                              int fromBob, float fromViewHeight, float fromLean)
{
	for (int i = 0; i < 3; ++i)
	{
		origin[i] = fromOrigin[i];
		velocity[i] = fromVelocity[i];
		viewangles[i] = fromAngles[i];
	}
	*bobCycle = fromBob;
	*viewHeight = fromViewHeight;
	*leanf = fromLean;
}

void CG_RestoreCanonicalView()
{
	if (!s_canonical.active)
		return;
	playerState_s *ps = &CG_GetLocalClientGlobals(LOCAL_CLIENT_0)->predictedPlayerState;
	CG_CopyViewFields(ps->origin, ps->velocity, ps->viewangles, &ps->bobCycle, &ps->viewHeightCurrent, &ps->leanf,
	                  s_canonical.origin, s_canonical.velocity, s_canonical.viewangles, s_canonical.bobCycle,
	                  s_canonical.viewHeightCurrent, s_canonical.leanf);
	s_canonical.active = 0;
}

// The movement states in which PM_UpdateViewAngles only adds delta_angles and holds the pitch to 85 degrees
static bool CG_PlainViewAngles(const playerState_s *ps)
{
	return (ps->pm_type == 0 || ps->pm_type == 2 || ps->pm_type == 3) && !(ps->pm_flags & 0x8000D)
	       && ps->vehicleState.entity == ENTITYNUM_NONE && !(ps->eFlags & 0x2000) && !(ps->linkFlags & 4);
}

static inline float CG_AngleNormalize180(const float angle)
{
	const float scaled = angle * 0.0027777778f;
	return (scaled - (float)floor((double)(scaled + 0.5f))) * 360.0f;
}

// The view's state at cl->serverTime, swapped into cg.predictedPlayerState (docs/fps.md 7.6)
static void CG_ViewAtRenderTime(LocalClientNum_t localClientNum, int predicted)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	if (!cg_renderTimeView || !cl_viewCmdValid || !predicted || localClientNum != LOCAL_CLIENT_0)
		return;
	if (cgameGlob->demoType || (ps->otherFlags & 0x2000) || ps->pm_type == 1 || ps->pm_type == 8 || (ps->linkFlags & 4))
		return;
	const int leftover = cl->serverTime - ps->commandTime;
	if (leftover < 0 || leftover > 4 * CMD_STEP_MSEC)
		return;

	Enh_Copy(&s_viewPs, ps, sizeof(s_viewPs));
	usercmd_s latest;
	CL_GetUserCmd(localClientNum, CL_GetCurrentCmdNumber(localClientNum), &latest);
	if (leftover > 0)
	{
		Enh_Copy(&s_viewPm, &cg_pmove[localClientNum], sizeof(s_viewPm));
		s_viewPm.ps = &s_viewPs;
		Enh_Copy(&s_viewPm.oldcmd, &latest, sizeof(latest));
		Enh_Copy(&s_viewPm.cmd, &cl_viewCmd, sizeof(cl_viewCmd));
		s_viewPm.cmd.serverTime = cl->serverTime;
		s_viewPm.viewChange = 0.0f;
		unsigned char *characterInfo = CG_CharacterInfo(ps->clientNum);
		if (characterInfo)
			Enh_Copy(s_characterInfo, characterInfo, CHARACTER_INFO_SIZE);
		Pmove(&s_viewPm);
		if (characterInfo)
			Enh_Copy(characterInfo, s_characterInfo, CHARACTER_INFO_SIZE);
		// a step taken in the partial move starts its smoothing at the render time instead of popping the view
		if (s_viewPm.viewChange != 0.0f)
			s_viewPs.origin[2] = s_viewPs.origin[2] - s_viewPm.viewChange;
	}
	else if (CG_PlainViewAngles(ps)
	         && (cl_viewCmd.angles[0] != latest.angles[0] || cl_viewCmd.angles[1] != latest.angles[1]
	             || cl_viewCmd.angles[2] != latest.angles[2]))
	{
		// no time to move, but the angles changed since the newest command: PM_UpdateViewAngles' rule
		for (int i = 0; i < 3; ++i)
			s_viewPs.viewangles[i] = CG_AngleNormalize180((float)(cl_viewCmd.angles[i] & 0xFFFF) * (360.0f / 65536.0f)
			                                              + s_viewPs.delta_angles[i]);
		if (s_viewPs.viewangles[0] > 85.0f)
			s_viewPs.viewangles[0] = 85.0f;
		else if (s_viewPs.viewangles[0] < -85.0f)
			s_viewPs.viewangles[0] = -85.0f;
	}

	CG_CopyViewFields(s_canonical.origin, s_canonical.velocity, s_canonical.viewangles, &s_canonical.bobCycle,
	                  &s_canonical.viewHeightCurrent, &s_canonical.leanf, ps->origin, ps->velocity, ps->viewangles,
	                  ps->bobCycle, ps->viewHeightCurrent, ps->leanf);
	s_canonical.active = 1;
	CG_CopyViewFields(ps->origin, ps->velocity, ps->viewangles, &ps->bobCycle, &ps->viewHeightCurrent, &ps->leanf,
	                  s_viewPs.origin, s_viewPs.velocity, s_viewPs.viewangles, s_viewPs.bobCycle,
	                  s_viewPs.viewHeightCurrent, s_viewPs.leanf);
}

// src (faithful copies)
static void CG_SavePlayerStateFaithful(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const playerState_s *ps = &cgameGlob->predictedPlayerState;
	cgameGlob->savedOrigin[0] = ps->origin[0];
	cgameGlob->savedOrigin[1] = ps->origin[1];
	cgameGlob->savedOrigin[2] = ps->origin[2];
	cgameGlob->savedViewangles[0] = ps->viewangles[0];
	cgameGlob->savedViewangles[1] = ps->viewangles[1];
	cgameGlob->savedViewangles[2] = ps->viewangles[2];
	cgameGlob->savedCommandTime = ps->commandTime;
	CG_ExtractTransPlayerState(ps, &cgameGlob->savedTrans);
	Enh_Copy(cgameGlob->savedPe, &ps->pe_eventSequence, sizeof(cgameGlob->savedPe));
}


static void sub_1402D2410Faithful()
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(LOCAL_CLIENT_0);
	if (sub_140345280(LOCAL_CLIENT_0) && cgameGlob->nextSnap && CG_PredictPlayerState_Internal(LOCAL_CLIENT_0, 1))
		Enh_Copy(&cgameGlob->predictedPlayerState.pe_eventSequence, cgameGlob->savedPe, sizeof(cgameGlob->savedPe));
}


static int CG_PredictPlayerStateFaithful(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	cgameGlob->lastAimSpreadScale = ps->weapCommon_aimSpreadScale;
	const int predicted = CG_PredictPlayerState_Internal(localClientNum, 0);
	if (ps->pm_flags & PMF_FROZEN)
		CL_SetStance(localClientNum, CL_STANCE_STAND);
	if (!ps->cursorHint)
	{
		ps->cursorHintString = 0;
		ps->cursorHintEntIndex = ENTITYNUM_NONE;
	}

	// a step up or down in this frame's moves starts (or extends) the view's smoothing of it
	pmove_t *pm = &cg_pmove[localClientNum];
	const float viewChange = pm->viewChange;
	if (viewChange == 0.0f || pm->viewChangeTime == cgameGlob->stepViewStart || cgameGlob->viewTeleported
	    || (ps->pm_type & ~3) || ps->pm_type == 1 || !(fabs(viewChange) >= cg_viewZSmoothingMin->current.value))
	{
		if ((float)(cgameGlob->time - cgameGlob->stepViewStart) > cg_viewZSmoothingTime->current.value * 1000.0f)
			cgameGlob->stepViewChange = 0.0f;
	}
	else
	{
		float stepRemaining = 0.0f;
		const float smoothingMsec = cg_viewZSmoothingTime->current.value * 1000.0f;
		if (smoothingMsec > (float)(cgameGlob->time - cgameGlob->stepViewStart))
		{
			const int sinceStart = pm->viewChangeTime - cgameGlob->stepViewStart;
			const int duration = (int)smoothingMsec;
			if (sinceStart >= 0 && sinceStart < duration)
				stepRemaining = (1.0f - (float)sinceStart / (float)duration) * cgameGlob->stepViewChange;
		}
		stepRemaining = stepRemaining + viewChange;
		const float maxChange = cg_viewZSmoothingMax->current.value;
		cgameGlob->stepViewStart = pm->viewChangeTime;
		if (stepRemaining > 0.0f)
			cgameGlob->stepViewChange = maxChange < stepRemaining ? maxChange : stepRemaining;
		else
			cgameGlob->stepViewChange = -maxChange > stepRemaining ? -maxChange : stepRemaining;
	}

	centity_s *playerEnt = CG_GetEntity(localClientNum, ps->clientNum);
	playerEnt->pose_origin[0] = ps->origin[0];
	playerEnt->pose_origin[1] = ps->origin[1];
	playerEnt->pose_origin[2] = ps->origin[2];
	if (!(ps->pm_flags & PMF_MANTLE))
		BG_EvaluateTrajectory(&playerEnt->nextState.lerp.apos, cgameGlob->time, playerEnt->pose_angles);
	if ((unsigned int)ps->meleeChargeEnt <= ENTITYNUM_WORLD)
		sub_1402CC6E0(localClientNum, ps);

	const int vehicleNum = ps->vehicleState.entity;
	if (vehicleNum != ENTITYNUM_NONE && !(ps->otherFlags & 0x2000))
	{
		centity_s *vehicle = CG_GetEntity(localClientNum, vehicleNum);
		if ((vehicle->flags & 1) && !((unsigned char)(vehicle->pose_eType - 0xC) & 0xFD))
		{
			sub_140277AB0(ps, &vehicle->nextState, 0, 0);
			vehicle->pose_eType = (unsigned char)vehicle->nextState.eType;
			Enh_Copy(&vehicle->currentState, &vehicle->nextState.lerp, sizeof(vehicle->currentState));
		}
	}
	sub_140306FD0(localClientNum, &ps->vehicleState);

	playerEnt->nextState.number = (unsigned short)ps->clientNum;
	BG_PlayerStateToEntityState(ps, &playerEnt->nextState, 0);
	BG_PlayerToEntity_ProcessEvents(ps, &playerEnt->nextState, 0);
	playerEnt->flags |= 1;
	playerEnt->pose_eType = (unsigned char)playerEnt->nextState.eType;
	Enh_Copy(&playerEnt->currentState, &playerEnt->nextState.lerp, sizeof(playerEnt->currentState));
	cgameGlob->predictedPlayerEntity = playerEnt;
	*(float *)&playerEnt->nextState.lerp.u[8] = pm->fTorsoPitch;
	*(float *)&playerEnt->nextState.lerp.u[0xC] = pm->fWaistPitch;
	cgameGlob->groundSurfaceType = pm->groundSurfaceType;
	CL_SetUserCmdOrigin(localClientNum, ps, cgameGlob->selectedLocation, cgameGlob->selectedLocationAngle);
	sub_1402EF5D0(localClientNum, ps, cgameGlob);
	cgameGlob->predictedWeaponPosFrac = ps->weapCommon_fWeaponPosFrac;
	sub_1405BAAA0(localClientNum);
	sub_1402D0AC0(localClientNum);
	return predicted;
}


static void CG_DrawActiveFaithful(LocalClientNum_t localClientNum, int renderScreen)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	float fovSensitivityScale = cgameGlob->zoomSensitivity;
	if (cgameGlob->shellshockSensitivity != 0.0f)
		fovSensitivityScale = fovSensitivityScale * cgameGlob->shellshockSensitivity;
	CL_SetFOVSensitivityScale(localClientNum, fovSensitivityScale);
	float angles[3];
	angles[0] = cgameGlob->kickAngles[0] + cgameGlob->offsetAngles[0];
	angles[1] = cgameGlob->offsetAngles[1] + cgameGlob->kickAngles[1];
	angles[2] = cgameGlob->offsetAngles[2] + cgameGlob->kickAngles[2];
	CL_SetUserCmdAimValues(localClientNum, angles);
	sub_1402891D0(cgameGlob->equippedOffHand);
	CL_SetUserCmdWeapons(localClientNum, cgameGlob->weaponSelect, cgameGlob->equippedOffHand,
	                     cgameGlob->weaponSelectAlternate);
	CL_SetExtraButtons(localClientNum, cgameGlob->extraButtons);
	cgameGlob->extraButtons = 0;
	CL_RenderScene(localClientNum, cgameGlob->refdef_displayViewport, renderScreen);
}

// Store 1402D3170, enhanced: the saved state is the canonical one
void CG_SavePlayerState(LocalClientNum_t localClientNum)
{
	CG_RestoreCanonicalView();
	CG_SavePlayerStateFaithful(localClientNum);
}

// Store 1402D2410, enhanced
void sub_1402D2410()
{
	CG_RestoreCanonicalView();
	sub_1402D2410Faithful();
}

// Store 1402D2480, enhanced: the faithful prediction, then the view at the render time
void CG_PredictPlayerState(LocalClientNum_t localClientNum)
{
	CG_RestoreCanonicalView();
	const int predicted = CG_PredictPlayerStateFaithful(localClientNum);
	CG_ViewAtRenderTime(localClientNum, predicted);
}

// Store 1402AB060, enhanced: the end of the cgame frame puts the canonical state back
void CG_DrawActive(LocalClientNum_t localClientNum, int renderScreen)
{
	CG_DrawActiveFaithful(localClientNum, renderScreen);
	CG_RestoreCanonicalView();
}
