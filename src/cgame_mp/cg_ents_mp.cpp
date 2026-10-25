// cgame_mp/cg_ents_mp.cpp
//
// Client-only, from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names follow
// Black Ops' cgame_mp/cg_ents_mp.cpp (black-ops-1-decomp, from its server PDB); line numbers are Black Ops'.

#include "cgame_mp/cg_local_mp.h"

#define IW6_SOURCE "cgame_mp/cg_ents_mp.cpp"

struct DObj;
void DObjUpdateClientInfo(DObj *obj, float dtime, bool notify);  // xanim (Black Ops' name; Store 140558FB0)

static_assert(__builtin_offsetof(cg_s, snap) == 0x3388, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, nextSnap) == 0x3390, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, frameInterpolation) == 0x71888, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, time) == 0x71890, "cg_s layout");
static_assert(__builtin_offsetof(snapshot_s, serverTime) == 0x3C7C, "snapshot_s layout");

// Store 1402B5B70 (Black Ops: cgame_mp/cg_ents_mp.cpp:1038). How far cg.time is from the current snapshot towards
// the next one, for interpolating entities between them (CG_InterpolateEntityPosition, Store 1402B3980). Called
// every frame from CG_ProcessSnapshots (Store 1402DB4C0) and again from CG_SetNextSnap when a new snapshot arrives.
// Both times are whole milliseconds, so the fraction moves in steps of 1 / (snapshot interval in ms): 1/50 at the
// default 20 snapshots a second. Past the next snapshot it goes above 1 (no clamp); before the current one, 0.
void CG_SetFrameInterpolation(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const int snapTime = cgameGlob->snap->serverTime;
	const int delta = cgameGlob->nextSnap->serverTime - snapTime;
	if (!delta)
	{
		cgameGlob->frameInterpolation = 0.0f;
		return;
	}
	cgameGlob->frameInterpolation = (float)(cgameGlob->time - snapTime) / (float)delta;
	if (cgameGlob->frameInterpolation < 0.0f)
		cgameGlob->frameInterpolation = 0.0f;
}

// Store 1402B3140 (Black Ops' CG_DObjUpdateInfo, cgame_mp/cg_ents_mp.cpp): advances an entity's animation by the
// frame's time, cg.frametime in seconds; with notify, its notetracks are collected for the caller
void CG_DObjUpdateInfo(const cg_s *cgameGlob, DObj *obj, bool notify)
{
	DObjUpdateClientInfo(obj, (float)cgameGlob->frametime * 0.001f, notify);
}

DObj *Com_GetClientDObj(int handle, LocalClientNum_t localClientNum);
void CG_ProcessClientNoteTracks(cg_s *cgameGlob, int clientNum);
void sub_1402CDF70(LocalClientNum_t localClientNum, centity_s *cent);  // the player's own model posed (name unknown)
void sub_1402B4F90(LocalClientNum_t localClientNum, centity_s *cent);  // ... and added to the scene (name unknown)

// Store 1402CEB10 (name unknown): the player's own model in third person, from CG_DrawActiveFrame when 1402CF440 says
// so: its XAnim advanced by the frame (CG_DObjUpdateInfo with notetracks, then CG_ProcessClientNoteTracks), then
// posed and added to the scene for cg.predictedPlayerEntity
void sub_1402CEB10(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	DObj *obj = Com_GetClientDObj(cgameGlob->predictedPlayerState.clientNum, localClientNum);
	if (obj)
	{
		CG_DObjUpdateInfo(cgameGlob, obj, true);
		CG_ProcessClientNoteTracks(cgameGlob, cgameGlob->predictedPlayerState.clientNum);
	}
	sub_1402CDF70(localClientNum, cgameGlob->predictedPlayerEntity);
	sub_1402B4F90(localClientNum, cgameGlob->predictedPlayerEntity);
}
