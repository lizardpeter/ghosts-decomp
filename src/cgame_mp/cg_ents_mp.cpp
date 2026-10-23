// cgame_mp/cg_ents_mp.cpp
//
// Client-only, from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names follow
// Black Ops' cgame_mp/cg_ents_mp.cpp (black-ops-1-decomp, from its server PDB); line numbers are Black Ops'.

#include "cgame_mp/cg_local_mp.h"

#define IW6_SOURCE "cgame_mp/cg_ents_mp.cpp"

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
