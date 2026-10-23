// cgame_mp/cg_local_mp.h: the multiplayer cgame's per-local-client globals (cg_s), in the Store build's layout.
//
// The PS4 server PDB has cg_s (0xD8700 bytes), but the Store build's is a later and much larger revision: only
// predictedPlayerState keeps its offsets (locationSelectionInfo at +0x23C); frametime is 0x70 earlier, and the
// compass and location-selection fields are 0x37DA8 further on. Only the fields the reconstructed code reads are
// spelled out, at their verified Store offsets (static_asserts in the .cpp files that use them).
#pragma once

#include "bgame/bg_weapons.h"
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

// The snapshot the client keeps per server frame (snapshot_s): the Store build's is 0x104 bytes larger than the PS4
// server's in front of serverTime (a larger playerState_s). Only serverTime is spelled out.
struct snapshot_s
{
	unsigned char unknown0[0x3C7C];
	int serverTime;
};

struct cg_s
{
	// predictedPlayerState (playerState_s): only these fields
	int ps_commandTime;
	int ps_pm_type;
	int ps_pm_time;
	int ps_pm_flags;
	int ps_otherFlags;
	int ps_linkFlags;
	unsigned char unknown18[0x124 - 0x18];
	int ps_eFlags;
	unsigned char unknown128[0x23C - 0x128];
	int ps_locationSelectionInfo;  // 0 when not selecting a location; bit 7: the selection has a direction
	unsigned char unknown240[0x41C - 0x240];
	Weapon ps_weapon;              // weapCommon.weapon
	int ps_weapFlags;              // weapCommon.weapFlags; bit 14: the alternate (underbarrel) mode
	unsigned char unknown424[0x3388 - 0x424];
	snapshot_s *snap;              // the snapshot cg.time has passed
	snapshot_s *nextSnap;          // the one after it, or NULL; entities are interpolated between the two
	unsigned char unknown3398[0x71888 - 0x3398];
	float frameInterpolation;      // (time - snap->serverTime) / (nextSnap->serverTime - snap->serverTime), at least 0
	int frametime;                 // time - oldTime, in milliseconds (0 when time went back)
	int time;                      // the client's game time in milliseconds: cl.serverTime when the frame began
	int oldTime;
	unsigned char unknown71898[0x718C8 - 0x71898];
	// refdef (refdef_t): only these fields
	int refdef_displayViewport[4];
	float refdef_tanHalfFovX;      // tan(horizontal FOV / 2): what the renderer's projection uses
	float refdef_tanHalfFovY;
	float refdef_vieworg[3];
	unsigned char unknown718EC[0xA9A90 - 0x718EC];
	float refdefViewAngles[3];     // the view angles the frame is drawn with (shake, kick and bob added)
	unsigned char unknownA9A9C[0xB1B18 - 0xA9A9C];
	float zoomSensitivity;         // tan(fov / 2) / tan(65 / 2): the mouse sensitivity scale while zoomed
	unsigned char unknownB1B1C[0xB4EF8 - 0xB1B1C];
	unsigned int hybridScopeState;  // 2 or 3: one of a hybrid scope's two FOVs; 4 or 5: switching (name unknown)
	float hybridScopeFrac;          // how far a switch has gone (name unknown)
	unsigned char unknownB4F00[0xB52F0 - 0xB4F00];
	float compassMapWorldSize[2];
	unsigned char unknownB52F8[0xB5368 - 0xB52F8];
	float selectedLocation[2];
	float selectedLocationAngle;
	float selectedDirectionPoint[2];  // Store build only: where the direction cursor is (name unknown)
	unsigned char unknownB537C[0x10E79F - 0xB537C];
	bool remoteMissileCam;          // the view is a remote missile's camera: missileRemoteFOV (name unknown)
	unsigned char unknown10E7A0[0x10EDC4 - 0x10E7A0];
	float scriptedViewFov;          // the FOV while eFlags 0x3800 or otherFlags 0x200000 (name unknown)
	unsigned char unknown10EDC8[0x10F05C - 0x10EDC8];
	unsigned int sightedClientsMask;  // copied to usercmd_s::sightedClientsMask (name unknown)
	unsigned char unknown10F060[0x10F880 - 0x10F060];
	SpawnSightGlob spawnSight;        // name unknown
	// the rest is not needed yet
};

extern cg_s cgArray[1];  // cgame_mp/cg_main_mp.cpp

// The cgame's per-local-client static globals: the Store build keeps the PS4 server PDB's leading fields.
struct cgs_t
{
	int viewX;
	int viewY;
	int viewWidth;
	int viewHeight;
	float viewAspect;  // the window aspect ratio (cls.vidConfig.windowAspectRatio)
	float viewMult;
	// the rest is not needed yet
};

extern cgs_t cgsArray[1];  // cgame_mp/cg_main_mp.cpp

// Inline from cgame_mp/cg_local_mp.h: one local client in this build.
inline cg_s *CG_GetLocalClientGlobals(LocalClientNum_t localClientNum)
{
	return &cgArray[0];
}

inline cgs_t *CG_GetLocalClientStaticGlobals(LocalClientNum_t localClientNum)
{
	return &cgsArray[0];
}
