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

// The PS4 server PDB's enums for CG_DrawActiveFrame's arguments
enum DemoType
{
	DEMO_TYPE_NONE = 0x0,
	DEMO_TYPE_CLIENT = 0x1,
	DEMO_TYPE_SERVER = 0x2,
};

enum CubemapShot
{
	CUBEMAPSHOT_NONE = 0x0,
	CUBEMAPSHOT_RIGHT = 0x1,
	CUBEMAPSHOT_LEFT = 0x2,
	CUBEMAPSHOT_BACK = 0x3,
	CUBEMAPSHOT_FRONT = 0x4,
	CUBEMAPSHOT_UP = 0x5,
	CUBEMAPSHOT_DOWN = 0x6,
	CUBEMAPSHOT_COUNT = 0x7,
};

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
	unsigned char unknown3328[0x3C74 - 0x3328];
	int snapFlags;                 // bit 1: the server is changing the map (CG_DrawActiveFrame draws nothing)
	unsigned char unknown3C78[0x3C7C - 0x3C78];
	int serverTime;
	int numEntities;
	unsigned char unknown3C84[0x3C88 - 0x3C84];
	unsigned char entities[1][0x108];  // entityState_s, 0x108 bytes each: the entity number first
};

// The bgame's per-local-client animation state (bgs_t): the PS4 server PDB's layout with 0x40 more bytes before
// time (Store build: time at +0x45990, characterinfo at +0x459F0, clientinfo at +0x54F60). The thread-local `bgs`
// points at it while the cgame runs bgame code.
struct characterInfo_t
{
	unsigned char unknown0[0x4];
	int infoValid;
	unsigned char unknown8[0x5D8 - 0x8];
};

struct clientInfo_t
{
	unsigned char unknown0[0x34];
	unsigned short patchIndex;       // a row of mp/cac/patches.csv: the player card's patch (name unknown)
	unsigned char unknown36[0x38 - 0x36];
	unsigned short backgroundIndex;  // a row of mp/cac/backgrounds.csv: the player card's background (name unknown)
	unsigned char unknown3A[0x70 - 0x3A];
};

struct bgs_t
{
	unsigned char unknown0[0x45990];  // animScriptData, generic_human, animClassTrees and 0x40 more than the PS4's
	int time;
	int deltaTime;
	int latestSnapshotTime;
	int frametime;
	unsigned char unknown459A0[0x459F0 - 0x459A0];
	characterInfo_t characterinfo[42];
	clientInfo_t clientinfo[18];
};
static_assert(__builtin_offsetof(bgs_t, characterinfo) == 0x459F0, "bgs_t layout (Store build)");
static_assert(sizeof(bgs_t) == 0x55740, "bgs_t size (Store build)");

extern __declspec(thread) bgs_t *bgs;  // bgame/bg_animation_mp.cpp (PS4 PDB: TLS offset 0x10, as in the Store build)

// The player-card materials the cgame keeps loaded for one client (name unknown): 0x18 bytes
struct ClientCardCache
{
	unsigned short ids[2];         // the patch and background indices the materials were looked up for
	unsigned char unknown4[0x8 - 0x4];
	const void *materials[2];
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
	int viewmodelAdsState;             // CG_AddViewWeapon: 0 once fully aimed down a sight, 1 back at the hip (name unknown)
	float weapLastIdleFactor;          // the viewmodel's weaponState_t, kept between frames (CG_AddViewWeapon):
	float weapBaseOrigin[3];           // fLastIdleFactor, baseOrigin, baseAngles
	float weapBaseAngles[3];
	int predictedErrorTime;            // cg.oldTime when the last prediction error was found
	float predictedError[3];           // decayed over cg_errordecay ms by CG_CalcViewValues
	int clientNum;                     // the local player's client number (Black Ops' cg.clientNum)
	LocalClientNum_t localClientNum;
	int demoType;                      // DemoType: CG_DrawActiveFrame's argument
	int cubemapShot;                   // CubemapShot: CG_DrawActiveFrame's argument
	int cubemapSize;                   // CG_DrawActiveFrame's argument
	unsigned char unknown3374[0x3378 - 0x3374];
	int renderScreen;                  // CG_DrawActiveFrame's argument: 0 draws nothing (a full-screen menu is up)
	unsigned char unknown337C[0x3388 - 0x337C];
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
	unsigned char unknown718A4[0x718A8 - 0x718A4];
	int followThirdPerson;         // what renderingThirdPerson is while following another player (name unknown)
	int renderingThirdPerson;      // set every frame by CG_UpdateThirdPerson (1402EF9E0)
	unsigned char unknown718B0[0x718B8 - 0x718B0];
	int lastMantleFlags;           // predictedPlayerState.mantleState.flags when the last frame ended (name unknown)
	unsigned char unknown718BC[0x718C0 - 0x718BC];
	float heightToCeiling;         // from the view up to what a 1024-unit box trace hits, FLT_MAX for nothing
	unsigned char unknown718C4[0x718C8 - 0x718C4];
	// refdef (refdef_t): only these fields
	int refdef_displayViewport[4];
	float refdef_tanHalfFovX;      // tan(horizontal FOV / 2): what the renderer's projection uses
	float refdef_tanHalfFovY;
	float refdef_vieworg[3];
	unsigned char unknown718EC[0x71914 - 0x718EC];
	float refdef_baseVieworg[3];   // what refdef_vieworg starts the frame from (name unknown)
	unsigned char unknown71920[0x7192C - 0x71920];
	int refdef_time;               // cg.time: the renderer's scene time (R_SetLodOrigin's caller copies it)
	int refdef_frametime;          // cg.frametime (name unknown)
	unsigned char unknown71934[0x71944 - 0x71934];
	unsigned int unknown71944[2];  // zeroed (one 8-byte store) by every CG_AddViewWeapon (name unknown)
	unsigned char unknown7194C[0x71A48 - 0x7194C];
	int timedFlagStart;            // a flag that clears itself timedFlagDuration ms after timedFlagStart (name unknown)
	int timedFlagLastTime;
	int timedFlagDuration;
	bool timedFlagActive;
	unsigned char unknown71A55[0xA9760 - 0x71A55];
	unsigned char clearedEachFrame[0x100];  // zeroed at the start of every CG_DrawActiveFrame (name unknown)
	unsigned char unknownA9860[0xA9A90 - 0xA9860];
	float refdefViewAngles[3];     // the view angles the frame is drawn with (shake, kick and bob added)
	unsigned char unknownA9A9C[0xA9AA8 - 0xA9A9C];
	float aimAssistView[3][3];     // the three vectors AimAssist_UpdateScreenTargets (140178CC0) gets (names unknown)
	unsigned char unknownA9ACC[0xA9AD8 - 0xA9ACC];
	float weapSwayViewAngles[3];   // the viewmodel's weaponState_t, kept between frames (CG_AddViewWeapon): swayViewAngles,
	float weapSwayAngles[3];       // swayAngles, swayOrigin, recoilAngles, recoilSpeed
	float weapSwayOrigin[3];
	float weapRecoilAngles[3];
	float weapRecoilSpeed[3];
	unsigned char unknownA9B14[0xB1B18 - 0xA9B14];
	float zoomSensitivity;         // tan(fov / 2) / tan(65 / 2): the mouse sensitivity scale while zoomed
	unsigned char unknownB1B1C[0xB2750 - 0xB1B1C];
	int platformContactEntity;      // a moving platform Pmove reported contact with, kept once set (name unknown)
	float platformAngularVelocity[3];  // the platform's turn rate in degrees per second (name unknown)
	unsigned char unknownB2760[0xB2768 - 0xB2760];
	unsigned int weaponSelect;      // Weapon: the weapon the player selected, for the usercmd
	int weaponSelectAlternate;      // nonzero: its alternate mode (name unknown)
	unsigned char unknownB2770[0xB4EEC - 0xB2770];
	int lastWeapFlags;              // predictedPlayerState.weapCommon.weapFlags when the last frame ended (name unknown)
	unsigned char unknownB4EF0[0xB4EF8 - 0xB4EF0];
	unsigned int hybridScopeState;  // 2 or 3: one of a hybrid scope's two FOVs; 4 or 5: switching (name unknown)
	float hybridScopeFrac;          // how far a switch has gone (name unknown)
	unsigned char unknownB4F00[0xB4F0C - 0xB4F00];
	unsigned int equippedOffHand;   // Weapon
	unsigned char unknownB4F10[0xB5240 - 0xB4F10];
	int damageTime;                 // cg.time of the last damage, 0 for none: the viewmodel's damage kick (name unknown)
	unsigned char unknownB5244[0xB525C - 0xB5244];
	float v_dmg_pitch;              // the viewmodel's damage kick (weaponState_t's v_dmg_pitch, v_dmg_roll)
	float v_dmg_roll;
	float xyspeed;                  // the player's horizontal speed, for the viewmodel's bob (CG_CalcViewValues sets it)
	float kickAVel[3];              // the view kick's angular velocity (BG_KickAngles)
	float kickAngles[3];            // the view kick from firing (BG_KickAngles)
	float offsetAngles[3];          // the ADS view error offset
	float gunAngles[2];             // the viewmodel's pitch and yaw as placed (1402F51A0; the view's without a weapon)
	float gunAdsOffset[3];          // the viewmodel's offset from the view, scaled by fWeaponPosFrac (1402F51A0)
	unsigned char unknownB52A0[0xB52F0 - 0xB52A0];
	float compassMapWorldSize[2];
	unsigned char unknownB52F8[0xB5310 - 0xB52F8];
	const shellshock_parms_t *shellshock_parms;  // shellshock (Black Ops' cg.shellshock)
	int shellshock_startTime;
	int shellshock_duration;
	float shellshockSensitivity;    // shellshock.sensitivity: scales the mouse while shell-shocked, 0 = none
	unsigned char unknownB5324[0xB5340 - 0xB5324];
	int testShock_time;             // testShock (Black Ops' cg.testShock): the shock without a snapshot index
	int testShock_duration;
	unsigned char unknownB5348[0xB5368 - 0xB5348];
	float selectedLocation[2];
	float selectedLocationAngle;
	float selectedDirectionPoint[2];  // Store build only: where the direction cursor is (name unknown)
	int inKillCam;                  // the kill cam is playing (name unknown)
	unsigned char unknownB5380[0xB5394 - 0xB5380];
	int killCamType;                // 1, 3 and 7 hide the first-person scene (name unknown)
	int killCamEntity;              // the entity the kill cam follows, ENTITYNUM_NONE for none (name unknown)
	float killCamEntityOrigin[3];   // its pose, copied every frame (Black Ops' UpdateKillCamEntityCache role)
	float killCamEntityAngles[3];
	unsigned char unknownB53B4[0xB53B8 - 0xB53B4];
	int killCamLookAtEntity;        // the entity the kill cam looks at (name unknown)
	float killCamLookAtOrigin[3];   // its pose origin, 50 units up
	unsigned char unknownB53C8[0xB54C8 - 0xB53C8];
	bgs_t bgs;
	unsigned char unknown10AC08[0x10AD28 - 0x10AC08];
	unsigned char unknown10AD28[0x10E79E - 0x10AD28];  // a state 1402F11D0 updates (name unknown)
	bool drawFirstPersonScene;      // set every frame from the EMP, kill cam and weapon state (name unknown, *unverified*)
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
	float lastVieworg[3];           // refdef_vieworg after CG_CalcViewValues (the next frame's volume checks read it)
	int savedCommandTime;           // CG_SavePlayerState: the predicted state the previous frame ended with
	float savedOrigin[3];
	float savedViewangles[3];
	transPlayerState_t savedTrans;
	unsigned char savedPe[0x2C];    // its playerEvents_t pe, restored after the early prediction
	float hipViewValue;             // what 14027B740 computes from the frame's time at the hip (name unknown)
	unsigned char unknown10E8C8[0x10ED48 - 0x10E8C8];
	int hudGrenadeCount;            // cleared every frame (Black Ops' CG_ClearHudGrenades role, name unknown)
	unsigned char unknown10ED4C[0x10EDBC - 0x10ED4C];
	float radarJamLevel;            // 0..1, moved 1/15 of the way to its target every frame (name unknown)
	float radarJamDistance;         // the nearest jammer's distance, -1 for none (set by the entity pass; name unknown)
	float scriptedViewFov;          // the FOV while eFlags 0x3800 or otherFlags 0x200000 (name unknown)
	unsigned char unknown10EDC8[0x10EDF0 - 0x10EDC8];
	const void *sceneUnknown;       // handed to the renderer every frame (140657FC0; name unknown)
	unsigned char unknown10EDF8[0x10EE58 - 0x10EDF8];
	float remoteViewOrigin[3];      // handed to 14604CD48 while remoteViewOriginValid (name unknown)
	bool remoteViewOriginValid;
	unsigned char unknown10EE65[0x10EE68 - 0x10EE65];
	ClientCardCache cardCache[18];
	unsigned char unknown10F018[0x10F058 - 0x10F018];
	bool vehicleViewActive;         // 1402EA200 turned the third-person vehicle view on (name unknown)
	unsigned char unknown10F059[0x10F05C - 0x10F059];
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
