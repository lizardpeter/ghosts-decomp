// cgame_mp/cg_predict_mp.cpp (Store build): prediction of the local player.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names and the
// file from Black Ops' server PDB (cgame_mp/cg_predict_mp.cpp: CG_PredictPlayerState, CG_PredictPlayerState_Internal,
// CG_SavePlayerState, CG_ClearSavedPlayerState) and cgame/cg_playerstate.cpp (the transPlayerState_t helpers); the
// Store build's functions follow them, with moving platforms added and the work split differently (docs/fps.md 7).
//
// How the predicted player state evolves:
// - CG_SetNextSnap (1402DBD40) copies each new snapshot's player state into cg.predictedPlayerState. Between
//   snapshots the state is NOT reset: every frame continues from where the previous frame's prediction ended. Only
//   while the player stands on an entity or a platform, or did in the last second, does the frame's preparation
//   (1402D3230) copy the snapshot's state again every frame.
// - CG_PredictPlayerState_Internal runs Pmove on every stored command whose serverTime is not older than
//   predictedPlayerState.commandTime (a command at exactly that time is a zero-length Pmove) up to the newest
//   command. After a reset that replays everything the server has not acknowledged; otherwise it is the frame's new
//   command(s).
// - It runs twice a frame for local client 0: once before the GPU sync and the frame's new usercmd (sub_1402D2410,
//   which also moves the player with a platform and then puts back the predictable events the replay made), and
//   once after it (CG_PredictPlayerState).

#include "cgame_mp/cg_local_mp.h"
#include "bgame/bg_public.h"
#include "qcommon/dvar.h"
#include <iw6_static.h>
#include <math.h>
#include <string.h>

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

static_assert(__builtin_offsetof(cg_s, predictedPlayerEntity) == 0x3328, "cg_s layout (Store build)");
static_assert(__builtin_offsetof(cg_s, predictedErrorTime) == 0x3350, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, demoType) == 0x3368, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, nextSnap) == 0x3390, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, predictFromTime) == 0x71898, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, groundSurfaceType) == 0x718A0, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, platformContactEntity) == 0xB2750, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, selectedLocation) == 0xB5368, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, viewTeleported) == 0x10E831, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, stepViewStart) == 0x10E834, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, lastAimSpreadScale) == 0x10E83C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, savedCommandTime) == 0x10E84C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, savedTrans) == 0x10E868, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, savedPe) == 0x10E898, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, predictedWeaponPosFrac) == 0x10FF10, "cg_s layout");
static_assert(__builtin_offsetof(pmove_t, bounds) == 0x108, "pmove_t layout");
static_assert(__builtin_offsetof(pmove_t, contactEntity) == 0x124, "pmove_t layout");
static_assert(__builtin_offsetof(pmove_t, viewChangeTime) == 0x158, "pmove_t layout");
static_assert(__builtin_offsetof(pmove_t, remoteTurretFireTime) == 0x168, "pmove_t layout");
static_assert(__builtin_offsetof(trace_t, hitId) == 0x1C, "trace_t layout");
static_assert(__builtin_offsetof(trace_t, allsolid) == 0x26, "trace_t layout");
static_assert(__builtin_offsetof(playerState_s, mantleState_startPosition) == 0x278, "playerState_s layout");

// universal/com_math.h's inline AngleNormalize180, with the floor made in double as in the original
static inline float AngleNormalize180(const float angle)
{
	const float scaled = angle * 0.0027777778f;
	return (scaled - (float)floor((double)(scaled + 0.5f))) * 360.0f;
}

// A mover the player can ride: eType 6 or 14 (ET_SCRIPTMOVER and the platform type)
static inline bool CG_IsMovingPlatformType(const centity_s *cent)
{
	return ((cent->nextState.eType - 6) & ~8) == 0;
}

// An entity number in the range the Store build accepts for a moving platform
static inline bool CG_IsMovingPlatformEntity(int entityNum)
{
	return (unsigned int)(entityNum - 0x3A) <= 0x7C3;
}

// bgame's inline lookup of an equipped weapon (inlined in the Store build)
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

// Store 1402CFF20 (Black Ops' CG_ClearTransPlayerState, cgame/cg_playerstate.cpp:298)
void CG_ClearTransPlayerState(transPlayerState_t *transPs)
{
	transPs->otherFlags = 0;
	transPs->damageEvent = 0;
	transPs->eventSequence = 0;
	for (int i = 0; i < 4; ++i)
		transPs->events[i] = 0;
	transPs->unpredictableEventSequence = 0;
	for (int i = 0; i < 4; ++i)
		transPs->unpredictableEvents[i] = 0;
}

// Store 1402CFF40 (Black Ops' CG_ExtractTransPlayerState, cgame/cg_playerstate.cpp:309): what
// CG_TransitionPlayerState compares the next predicted state with
void CG_ExtractTransPlayerState(const playerState_s *ps, transPlayerState_t *transPs)
{
	transPs->otherFlags = ps->otherFlags;
	transPs->damageEvent = ps->damageEvent;
	transPs->eventSequence = ps->pe_eventSequence;
	transPs->unpredictableEventSequence = ps->unpredictableEventSequence;
	for (int i = 0; i < 4; ++i)
	{
		transPs->events[i] = ps->pe_events[i].eventType;
		transPs->unpredictableEvents[i] = ps->unpredictableEvents[i].eventType;
	}
}

// Store 1402D2300 (Black Ops' CG_BuildItemList, cg_predict_mp.cpp:71): the snapshot's items (eType 3) that carry a
// weapon, for the pickup prediction
void CG_BuildItemList(LocalClientNum_t localClientNum, const snapshot_s *nextSnap)
{
	const int numEntities = *(const int *)((const unsigned char *)nextSnap + 0x3C80);
	const unsigned char *entities = (const unsigned char *)nextSnap + 0x3C88;  // entityState_s[], 0x108 bytes each
	cg_itemEntityCount = 0;
	cg_itemLocalClientNum = localClientNum;
	int count = 0;
	for (int i = 0; i < numEntities; ++i)
	{
		centity_s *cent = CG_GetEntity(localClientNum, *(const int *)(entities + 0x108 * i));
		if (cent->nextState.eType == 3 && (unsigned char)cent->nextState.weapon.data)
			cg_itemEntities[count++] = cent;
	}
	cg_itemEntityCount = count;
}

// Store 1402D2370 (Black Ops' CG_ClearItemList, cg_predict_mp.cpp:62)
void CG_ClearItemList()
{
	cg_itemEntityCount = 0;
}

// Store 1402D2400 (Black Ops' CG_ItemListLocalClientNum, cg_predict_mp.cpp:53)
int CG_ItemListLocalClientNum()
{
	return cg_itemLocalClientNum;
}

// Store 1402D2380 (Black Ops' CG_ClearSavedPlayerState, cg_predict_mp.cpp:614)
void CG_ClearSavedPlayerState(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	for (int i = 0; i < 3; ++i)
		cgameGlob->savedOrigin[i] = 0.0f;
	cgameGlob->savedCommandTime = 0;
	for (int i = 0; i < 3; ++i)
		cgameGlob->savedViewangles[i] = 0.0f;
	CG_ClearTransPlayerState(&cgameGlob->savedTrans);
	cg_pmove[localClientNum].remoteTurretFireTime = 0;
	cg_pmove[localClientNum].lastUpdateCMDServerTime = 0;
}

// Store 1402D3170 (Black Ops' CG_SavePlayerState, cg_predict_mp.cpp:628): the predicted state the frame ended with,
// saved at the start of the next client frame (from 14031B1F0) before anything moves it: the prediction error is
// measured against its origin, the angles are kept from it when no command is new, CG_TransitionPlayerState fires
// the events after its trans state, and the early prediction puts its pe back. The Store build also saves pe.
void CG_SavePlayerState(LocalClientNum_t localClientNum)
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
	memcpy(cgameGlob->savedPe, &ps->pe_eventSequence, sizeof(cgameGlob->savedPe));
}

// Store 1402D2900 (Black Ops' CG_PredictPlayerState_Internal, cg_predict_mp.cpp:670). Returns 0 without doing anything
// for a demo or when otherFlags 0x2000 is set (the state is interpolated instead, by 1402D3230), else 1.
//
// moverEarly: 1 for the call before the frame's usercmd (sub_1402D2410), 0 for CG_PredictPlayerState's. For local
// client 0 the moving platform is applied only in the early call; for the others only in the late one.
int CG_PredictPlayerState_Internal(LocalClientNum_t localClientNum, int moverEarly)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	const int current = CL_GetCurrentCmdNumber(localClientNum);
	if (cgameGlob->demoType || (ps->otherFlags & 0x2000))
		return 0;

	// the platform the player rides: the predicted state's, else the one Pmove reported contact with before, else
	// whatever the player's box is stuck in
	int fromTime = cgameGlob->predictFromTime;
	int moverNum = ps->movingPlatformEntity;
	if (!CG_IsMovingPlatformEntity(moverNum))
	{
		moverNum = ENTITYNUM_NONE;
		int candidate = cgameGlob->platformContactEntity;
		bool found = false;
		if (candidate != ENTITYNUM_NONE)
		{
			found = CG_IsMovingPlatformType(CG_GetEntity(localClientNum, candidate));
		}
		else
		{
			trace_t trace;
			sub_140304650(&trace, ps->origin, ps->origin, (const Bounds *)cg_pmove[localClientNum].bounds, 0, 0x810011);
			if (trace.allsolid)
			{
				candidate = trace.hitId;
				found = CG_IsMovingPlatformType(CG_GetEntity(localClientNum, candidate));
			}
		}
		if (found)
		{
			const int number = CG_GetEntity(localClientNum, candidate)->nextState.number;
			if (number != ENTITYNUM_NONE)
			{
				moverNum = number;
				ps->movingPlatformEntity = number;
				if (!(ps->pm_flags & PMF_MANTLE))
					ps->otherFlags |= 0x1000000;
				fromTime = cgameGlob->snap->serverTime;
			}
		}
	}

	pmove_t *pm = &cg_pmove[localClientNum];
	pm->ps = ps;
	bool moverNow;
	if (sub_140345260(localClientNum) && moverEarly)
		moverNow = true;
	else
		moverNow = !sub_140345260(localClientNum) && !moverEarly;

	float deltaOrigin[3];
	float deltaAngles[3];
	if (!unk_143E96824 && moverNow)
	{
		CG_AdjustPositionForMover(localClientNum, ps->origin, moverNum, fromTime, cgameGlob->time, ps->origin,
		                          deltaOrigin, deltaAngles, ps, pm);
		if (CG_IsMovingPlatformEntity(moverNum))
		{
			centity_s *mover = CG_GetEntity(localClientNum, moverNum);
			float angleChange[3];
			BG_UpdateAnglesMovingPlatform(ps, deltaAngles, mover->pose_angles, angleChange);
			const int elapsed = cgameGlob->time - fromTime;
			if (elapsed)
			{
				angleChange[0] = AngleNormalize180(angleChange[0]);
				angleChange[1] = AngleNormalize180(angleChange[1]);
				const float scale = 1000.0f / (float)elapsed;
				cgameGlob->platformAngularVelocity[0] = scale * angleChange[0];
				cgameGlob->platformAngularVelocity[1] = scale * angleChange[1];
				cgameGlob->platformAngularVelocity[2] = angleChange[2] * scale;
			}
			BG_UpdateDirectionMovingPlatform(ps->velocity, mover->pose_angles, deltaAngles);
			if (ps->pm_flags & PMF_MANTLE)
				BG_UpdatePointMovingPlatform(ps->mantleState_startPosition, mover->pose_origin, mover->pose_angles,
				                             deltaAngles, deltaOrigin);
			sub_140178C50(localClientNum);
		}
	}

	pm->handler = 0;
	pm->tracemask = pm->ps->pm_type < 7 ? 0x2814011 : 0x810011;
	if (ps->pm_type == 5)
		pm->tracemask = 0x800011;
	pm->viewChange = 0.0f;
	pm->contactEntity = ENTITYNUM_NONE;
	pm->viewChangeTime = cgameGlob->stepViewStart;

	usercmd_s oldestCmd;
	if (!CL_GetUserCmd(localClientNum, current - (CMD_BACKUP - 1), &oldestCmd))
		return 1;  // never: the oldest command in the ring is always there

	usercmd_s latestCmd;
	CL_GetUserCmd(localClientNum, current, &latestCmd);
	if (ps->commandTime < latestCmd.serverTime)
	{
		for (int cmdNum = current - (CMD_BACKUP - 1); cmdNum <= current; ++cmdNum)
		{
			CL_GetUserCmd(localClientNum, cmdNum, &pm->cmd);
			if (pm->cmd.serverTime < ps->commandTime || pm->cmd.serverTime > latestCmd.serverTime)
				continue;
			if (!CL_GetUserCmd(localClientNum, cmdNum - 1, &pm->oldcmd))
				continue;  // the oldest command in the ring has no predecessor: it is never predicted

			// the prediction error: where the previous frame's prediction had the player at this time, against where
			// the replay from the snapshot puts it (both moved with the platform from oldTime)
			if (ps->commandTime == cgameGlob->savedCommandTime)
			{
				float adjusted[3];
				CG_AdjustPositionForMover(localClientNum, ps->origin, moverNum, cgameGlob->time, cgameGlob->oldTime,
				                          adjusted, deltaOrigin, deltaAngles, ps, pm);
				float delta[3];
				delta[0] = cgameGlob->savedOrigin[0] - adjusted[0];
				delta[1] = cgameGlob->savedOrigin[1] - adjusted[1];
				delta[2] = cgameGlob->savedOrigin[2] - adjusted[2];
				if (!cgameGlob->noPredictionError)
				{
					const float len = sqrtf(delta[1] * delta[1] + delta[0] * delta[0] + delta[2] * delta[2]);
					if (len > 0.1f && !CG_IsMovingPlatformEntity(ps->movingPlatformEntity))
					{
						const float decay = cg_errorDecay->current.value;
						if (decay == 0.0f)
						{
							cgameGlob->predictedError[0] = 0.0f;
							cgameGlob->predictedError[1] = 0.0f;
							cgameGlob->predictedError[2] = 0.0f;
						}
						else
						{
							float f = (decay - (float)(cgameGlob->time - cgameGlob->predictedErrorTime)) / decay;
							f = 0.0f > f ? 0.0f : f;
							cgameGlob->predictedError[0] = cgameGlob->predictedError[0] * f;
							cgameGlob->predictedError[1] = cgameGlob->predictedError[1] * f;
							cgameGlob->predictedError[2] = cgameGlob->predictedError[2] * f;
						}
						cgameGlob->predictedError[0] = cgameGlob->predictedError[0] + delta[0];
						cgameGlob->predictedError[1] = cgameGlob->predictedError[1] + delta[1];
						cgameGlob->predictedErrorTime = cgameGlob->oldTime;
						cgameGlob->predictedError[2] = cgameGlob->predictedError[2] + delta[2];
					}
				}
			}

			Pmove(pm);

			// Black Ops' CG_TouchItemPrediction, inlined: announce the pickup of an item the predicted player touches
			if ((unsigned int)ps->pm_type <= 1)
			{
				for (int i = 0; i < cg_itemEntityCount; ++i)
				{
					centity_s *cent = cg_itemEntities[i];
					if (cent->predictedPickupTime && cent->predictedPickupTime >= cgameGlob->time)
						continue;
					if (!BG_PlayerTouchesItem(ps, &cent->nextState, cgameGlob->time))
						continue;
					if (!BG_CanItemBeGrabbed(&cent->nextState, ps, 1))
						continue;
					if (!sub_140267140(cent->nextState.weapon))
					{
						if (!BG_PlayerHasEquippedWeapon(ps, cent->nextState.weapon))
							continue;
						if (!sub_140267880(&cent->nextState, ps))
							continue;
					}
					cent->predictedPickupTime = cgameGlob->time + 5000;
					sub_1402B8F80(localClientNum, cent->nextState.number, 10, cent->nextState.weapon, true);
				}
			}
		}
	}
	else if (!cgameGlob->viewTeleported)
	{
		// no command is newer than the state: keep the angles the last frame's prediction ended with
		ps->viewangles[0] = cgameGlob->savedViewangles[0];
		ps->viewangles[2] = cgameGlob->savedViewangles[2];
		ps->viewangles[1] = cgameGlob->savedViewangles[1];
	}

	if (cgameGlob->platformContactEntity == ENTITYNUM_NONE)
		cgameGlob->platformContactEntity = pm->contactEntity;
	return 1;
}

// Store 1402D2410 (name unknown): the prediction before the frame's GPU sync and usercmd, for local client 0 once a
// snapshot is there. It brings the state up to the commands made so far and moves it with its platform; then it puts
// the predictable events (pe) back to what the last frame ended with, so the replay after a new snapshot doesn't
// announce the events of commands that were predicted before.
void sub_1402D2410()
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(LOCAL_CLIENT_0);
	if (sub_140345280(LOCAL_CLIENT_0) && cgameGlob->nextSnap && CG_PredictPlayerState_Internal(LOCAL_CLIENT_0, 1))
		memcpy(&cgameGlob->predictedPlayerState.pe_eventSequence, cgameGlob->savedPe, sizeof(cgameGlob->savedPe));
}

// Store 1402D2480 (Black Ops' CG_PredictPlayerState, cg_predict_mp.cpp:1012): the prediction after the frame's
// usercmd, then what follows from the predicted state: the stance, the step smoothing, the player's own entity,
// the vehicle, and the values the client puts in the next usercmd. Black Ops sent the usercmd from here; the Store
// build's CG_DrawActiveFrame calls CL_SendCmd itself.
void CG_PredictPlayerState(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	playerState_s *ps = &cgameGlob->predictedPlayerState;
	cgameGlob->lastAimSpreadScale = ps->weapCommon_aimSpreadScale;
	CG_PredictPlayerState_Internal(localClientNum, 0);
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
			memcpy(&vehicle->currentState, &vehicle->nextState.lerp, sizeof(vehicle->currentState));
		}
	}
	sub_140306FD0(localClientNum, &ps->vehicleState);

	playerEnt->nextState.number = (unsigned short)ps->clientNum;
	BG_PlayerStateToEntityState(ps, &playerEnt->nextState, 0);
	BG_PlayerToEntity_ProcessEvents(ps, &playerEnt->nextState, 0);
	playerEnt->flags |= 1;
	playerEnt->pose_eType = (unsigned char)playerEnt->nextState.eType;
	memcpy(&playerEnt->currentState, &playerEnt->nextState.lerp, sizeof(playerEnt->currentState));
	cgameGlob->predictedPlayerEntity = playerEnt;
	*(float *)&playerEnt->nextState.lerp.u[8] = pm->fTorsoPitch;
	*(float *)&playerEnt->nextState.lerp.u[0xC] = pm->fWaistPitch;
	cgameGlob->groundSurfaceType = pm->groundSurfaceType;
	CL_SetUserCmdOrigin(localClientNum, ps, cgameGlob->selectedLocation, cgameGlob->selectedLocationAngle);
	sub_1402EF5D0(localClientNum, ps, cgameGlob);
	cgameGlob->predictedWeaponPosFrac = ps->weapCommon_fWeaponPosFrac;
	sub_1405BAAA0(localClientNum);
	sub_1402D0AC0(localClientNum);
}
