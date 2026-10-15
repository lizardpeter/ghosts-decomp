// cgame_mp/cg_local_mp.h: the multiplayer cgame's per-local-client globals (cg_s), in the Store build's layout.
//
// The PS4 server PDB has cg_s (0xD8700 bytes), but the Store build's is a later and much larger revision: only
// predictedPlayerState keeps its offsets (locationSelectionInfo at +0x23C); frametime is 0x70 earlier, and the
// compass and location-selection fields are 0x37DA8 further on. Only the fields the reconstructed code reads are
// spelled out, at their verified Store offsets (static_asserts in the .cpp files that use them).
#pragma once

#include "client/client.h"

// One spawn point the client checks for being in view (name unknown): 0x14 bytes. The cgame fills the array; the
// client sends its sight states in usercmd_s::sightedSpawnsMask and partialSightedSpawnsMask.
struct SpawnSightPoint
{
	int sightState;  // 1 partially in sight, 2 in sight
	float origin[3];
	bool unknown10;
};

// Spawn point sight tracking (name unknown); the cgame clears all 0x600 bytes at once.
struct SpawnSightGlob
{
	unsigned short traceEntIndex;  // copied to usercmd_s::spawnTraceEntIndex
	int unknown4;
	unsigned short pointCount;
	SpawnSightPoint *nextPoint;
	SpawnSightPoint points[32];    // the count is not checked against this here; 32 bits in the usercmd masks
	unsigned char unknown298[0x600 - 0x298];
};

struct cg_s
{
	// predictedPlayerState (playerState_s): only these fields
	int ps_commandTime;
	int ps_pm_type;
	int ps_pm_time;
	int ps_pm_flags;
	unsigned char unknown10[0x23C - 0x10];
	int ps_locationSelectionInfo;  // 0 when not selecting a location; bit 7: the selection has a direction
	unsigned char unknown240[0x7188C - 0x240];
	int frametime;
	unsigned char unknown71890[0xB52F0 - 0x71890];
	float compassMapWorldSize[2];
	unsigned char unknownB52F8[0xB5368 - 0xB52F8];
	float selectedLocation[2];
	float selectedLocationAngle;
	float selectedDirectionPoint[2];  // Store build only: where the direction cursor is (name unknown)
	unsigned char unknownB537C[0x10F05C - 0xB537C];
	unsigned int sightedClientsMask;  // copied to usercmd_s::sightedClientsMask (name unknown)
	unsigned char unknown10F060[0x10F880 - 0x10F060];
	SpawnSightGlob spawnSight;        // name unknown
	// the rest is not needed yet
};

extern cg_s cgArray[1];  // cgame_mp/cg_main_mp.cpp

// Inline from cgame_mp/cg_local_mp.h: one local client in this build.
inline cg_s *CG_GetLocalClientGlobals(LocalClientNum_t localClientNum)
{
	return &cgArray[0];
}
