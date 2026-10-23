// cgame_mp/cg_local_mp.h: the multiplayer cgame's per-local-client globals (cg_s), in the Store build's layout.
//
// The PS4 server PDB has cg_s (0xD8700 bytes), but the Store build's is a later and much larger revision: only
// predictedPlayerState keeps its offsets (locationSelectionInfo at +0x23C); frametime is 0x70 earlier, and the
// compass and location-selection fields are 0x37DA8 further on. Only the fields the reconstructed code reads are
// spelled out, at their verified Store offsets (static_asserts in the .cpp files that use them).
#pragma once

#include "bgame/bg_public.h"
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
// server's in front of serverTime (a larger playerState_s). Only the player state and serverTime are spelled out.
struct snapshot_s
{
	playerState_s ps;
	unsigned char unknown3328[0x3C7C - 0x3328];
	int serverTime;
};

// A client entity (centity_s, 0x238 bytes in the Store build): its pose (cpose_t, Black Ops' layout up to the
// angles), the interpolated part of its previous state and its latest state. Only the fields the prediction reads
// and writes are spelled out.
struct centity_s
{
	unsigned short pose_lightingHandle;
	unsigned char pose_eType;          // the entity type the pose was built for
	unsigned char unknown3[0x18 - 0x3];
	float pose_origin[3];
	float pose_angles[3];
	unsigned char unknown30[0x90 - 0x30];
	LerpEntityState currentState;
	entityState_s nextState;
	unsigned char unknown1C0[0x200 - 0x1C0];
	unsigned int flags;                // bit 0: nextState is valid (nextValid)
	unsigned char unknown204[0x20C - 0x204];
	int predictedPickupTime;           // an item: cg.time + 5000 once a predicted pickup was announced (name unknown)
	unsigned char unknown210[0x238 - 0x210];
};
static_assert(__builtin_offsetof(centity_s, currentState) == 0x90, "centity_s layout (Store build)");
static_assert(__builtin_offsetof(centity_s, nextState) == 0xF8, "centity_s layout (Store build)");
static_assert(__builtin_offsetof(centity_s, flags) == 0x200, "centity_s layout (Store build)");
static_assert(sizeof(centity_s) == 0x238, "centity_s size (Store build)");

// The client's copy of the event state of its predicted player state (cgame/cg_playerstate.cpp, as Black Ops'):
// what CG_TransitionPlayerState compares the new state with to fire the events in between.
struct transPlayerState_t
{
	int otherFlags;
	int damageEvent;
	int eventSequence;
	int events[4];  // eventType of each
	int unpredictableEventSequence;
	int unpredictableEvents[4];
};

struct cg_s
{
	union
	{
		playerState_s predictedPlayerState;
		struct  // the fields older code reads by these names
		{
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
		};
	};
	centity_s *predictedPlayerEntity;  // the player's own entry in cg_entitiesArray, set by CG_PredictPlayerState
	unsigned char unknown3330[0x3350 - 0x3330];
	int predictedErrorTime;            // cg.oldTime when the last prediction error was found
	float predictedError[3];           // decayed over cg_errordecay ms by CG_CalcViewValues
	unsigned char unknown3360[0x3368 - 0x3360];
	int demoType;                      // DemoType: CG_DrawActiveFrame's argument
	unsigned char unknown336C[0x3388 - 0x336C];
	snapshot_s *snap;              // the snapshot cg.time has passed
	snapshot_s *nextSnap;          // the one after it, or NULL; entities are interpolated between the two
	unsigned char unknown3398[0x71888 - 0x3398];
	float frameInterpolation;      // (time - snap->serverTime) / (nextSnap->serverTime - snap->serverTime), at least 0
	int frametime;                 // time - oldTime, in milliseconds (0 when time went back)
	int time;                      // the client's game time in milliseconds: cl.serverTime when the frame began
	int oldTime;
	int predictFromTime;           // nextSnap->serverTime, set before prediction: where a platform move starts (name unknown)
	int lastOnEntityTime;          // cg.time when the player last stood on an entity or a platform (name unknown)
	unsigned int groundSurfaceType;  // the predicting pmove_t's groundSurfaceType (name unknown)
	unsigned char unknown718A4[0x718C8 - 0x718A4];
	// refdef (refdef_t): only these fields
	int refdef_displayViewport[4];
	float refdef_tanHalfFovX;      // tan(horizontal FOV / 2): what the renderer's projection uses
	float refdef_tanHalfFovY;
	float refdef_vieworg[3];
	unsigned char unknown718EC[0xA9A90 - 0x718EC];
	float refdefViewAngles[3];     // the view angles the frame is drawn with (shake, kick and bob added)
	unsigned char unknownA9A9C[0xB1B18 - 0xA9A9C];
	float zoomSensitivity;         // tan(fov / 2) / tan(65 / 2): the mouse sensitivity scale while zoomed
	unsigned char unknownB1B1C[0xB2750 - 0xB1B1C];
	int platformContactEntity;      // a moving platform Pmove reported contact with, kept once set (name unknown)
	float platformAngularVelocity[3];  // the platform's turn rate in degrees per second (name unknown)
	unsigned char unknownB2760[0xB2768 - 0xB2760];
	unsigned int weaponSelect;      // Weapon: the weapon the player selected, for the usercmd
	int weaponSelectAlternate;      // nonzero: its alternate mode (name unknown)
	unsigned char unknownB2770[0xB4EF8 - 0xB2770];
	unsigned int hybridScopeState;  // 2 or 3: one of a hybrid scope's two FOVs; 4 or 5: switching (name unknown)
	float hybridScopeFrac;          // how far a switch has gone (name unknown)
	unsigned char unknownB4F00[0xB4F0C - 0xB4F00];
	unsigned int equippedOffHand;   // Weapon
	unsigned char unknownB4F10[0xB5274 - 0xB4F10];
	float kickAngles[3];            // the view kick from firing (BG_KickAngles)
	float offsetAngles[3];          // the ADS view error offset
	unsigned char unknownB528C[0xB52F0 - 0xB528C];
	float compassMapWorldSize[2];
	unsigned char unknownB52F8[0xB5320 - 0xB52F8];
	float shellshockSensitivity;    // shellshock.sensitivity: scales the mouse while shell-shocked, 0 = none
	unsigned char unknownB5324[0xB5368 - 0xB5324];
	float selectedLocation[2];
	float selectedLocationAngle;
	float selectedDirectionPoint[2];  // Store build only: where the direction cursor is (name unknown)
	unsigned char unknownB537C[0x10E79F - 0xB537C];
	bool remoteMissileCam;          // the view is a remote missile's camera: missileRemoteFOV (name unknown)
	unsigned char unknown10E7A0[0x10E82C - 0x10E7A0];
	int extraButtons;               // usercmd buttons the cgame adds to the next command (name unknown)
	unsigned char unknown10E830[0x10E831 - 0x10E830];
	bool viewTeleported;            // the view jumped this frame (spectating another player, teleport): no step
	                                // smoothing, no keeping of the last predicted angles; cleared at the frame's end
	                                // (name unknown; Quake 3's thisFrameTeleport role)
	bool noPredictionError;         // a teleport in this snapshot: don't measure a prediction error (name unknown)
	unsigned char unknown10E833[0x10E834 - 0x10E833];
	int stepViewStart;              // the command time of the last step up or down the view smooths
	float stepViewChange;           // its height, at most cg_viewZSmoothingMax
	float lastAimSpreadScale;       // predictedPlayerState's aimSpreadScale before this frame's prediction (name unknown)
	unsigned char unknown10E840[0x10E84C - 0x10E840];
	int savedCommandTime;           // CG_SavePlayerState: the predicted state the previous frame ended with
	float savedOrigin[3];
	float savedViewangles[3];
	transPlayerState_t savedTrans;
	unsigned char savedPe[0x2C];    // its playerEvents_t pe, restored after the early prediction
	unsigned char unknown10E8C4[0x10EDC4 - 0x10E8C4];
	float scriptedViewFov;          // the FOV while eFlags 0x3800 or otherFlags 0x200000 (name unknown)
	unsigned char unknown10EDC8[0x10F05C - 0x10EDC8];
	unsigned int sightedClientsMask;  // copied to usercmd_s::sightedClientsMask (name unknown)
	unsigned char unknown10F060[0x10F880 - 0x10F060];
	SpawnSightGlob spawnSight;        // name unknown
	unsigned char unknown10FE80[0x10FF10 - 0x10FE80];
	float predictedWeaponPosFrac;     // predictedPlayerState's fWeaponPosFrac after prediction (name unknown)
	// the rest is not needed yet
};

extern cg_s cgArray[1];  // cgame_mp/cg_main_mp.cpp
extern centity_s cg_entitiesArray[1][2048];  // cgame_mp/cg_main_mp.cpp (an array of pointers in Black Ops)

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

// Inline from cgame_mp/cg_local_mp.h: one local client in this build.
inline centity_s *CG_GetEntity(LocalClientNum_t localClientNum, int entityIndex)
{
	return &cg_entitiesArray[0][entityIndex];
}
