// client_mp/client_mp.h: the multiplayer client's per-local-client state, in the Store build's layout.
//
// The 2014 server PDB has these types, but the Store build (like the 2018 Steam build) is a later revision: its
// clSnapshot_s is 0x100 bytes larger (a larger playerState_s), which moves every clientActive_t field after snap by
// 0x100, and it has three floats after clViewangles that the server's layout doesn't (docs/input.md). Only the
// fields the reconstructed code reads are spelled out; the rest is opaque until a function needs it.
#pragma once

#include "client/client.h"
#include "bgame/bg_weapons.h"

struct usercmd_s
{
	int serverTime;
	unsigned int buttons;
	int angles[3];
	unsigned int weapon;   // Weapon
	unsigned int offHand;  // Weapon
	char forwardmove;
	char rightmove;
	unsigned short airburstMarkDistance;
	unsigned short meleeChargeEnt;
	unsigned char meleeChargeDist;
	char selectedLoc[2];
	unsigned char selectedLocAngle;
	char remoteControlAngles[2];
	char remoteControlMove[3];
	unsigned int sightedClientsMask;
	unsigned short spawnTraceEntIndex;
	unsigned int sightedSpawnsMask;
	unsigned int partialSightedSpawnsMask;
};

// The leading fields of playerState_s and the size of clSnapshot_s in the Store build.
struct clSnapshot_s
{
	int ps_commandTime;
	int ps_pm_type;
	int ps_pm_time;
	int ps_pm_flags;
	unsigned char unknown10[0x124 - 0x10];
	int ps_eFlags;
	unsigned char unknown128[0x2AC - 0x128];
	PlayerActiveWeaponState ps_weapState[2];  // per hand
	unsigned char unknown2E4[0x41C - 0x2E4];
	Weapon ps_weapon;                         // weapCommon.weapon
	int ps_weapFlags;                         // weapCommon.weapFlags
	unsigned char unknown424[0x43C - 0x424];
	PlayerHandIndex ps_lastWeaponHand;        // weapCommon.lastWeaponHand
	GlobalAmmo ps_ammoNotInClip[MAX_AMMO_SLOTS];
	ClipAmmo ps_ammoInClip[MAX_AMMO_SLOTS];
	unsigned char rest[0x34B8 - 0x620];
};

#define PMF_NO_MOUSE_LOOK 0x800  // pm_flags bit that stops mouse look (name unknown; Black Ops tests the same bit)

struct clientActive_t
{
	bool usingAds;
	int timeoutcount;
	clSnapshot_s snap;
	int oldSnapServerTime;
	int oldServerTime;
	int extrapolatedSnapshot;
	bool alwaysFalse;
	int serverTime;
	int oldFrameServerTime;
	int serverTimeDelta;
	int newSnapshots;
	int serverId;
	char mapname[64];
	int mapcrc;
	int parseEntitiesIndex;
	int parseClientsIndex;
	int parseOmnvarsIdx;
	int mouseDx[2];
	int mouseDy[2];
	int mouseIndex;
	bool stanceHeld;
	int stance;                  // StanceState
	int stancePosition;          // StanceState
	int stanceTime;
	bool wasSprinting;
	unsigned int cgameUserCmdWeapon;   // Weapon
	unsigned int cgameUserCmdOffHand;  // Weapon
	int cgameUserCmdAlternate;
	float cgameFOVSensitivityScale;
	float cgameMaxPitchSpeed;
	float cgameMaxYawSpeed;
	float cgameKickAngles[3];
	float cgameOrigin[3];
	float cgameVelocity[3];
	unsigned char cgamePlayerVehState[0x68];  // PlayerVehicleState
	int cgameBobCycle;
	int cgameMovementDir;
	int cgameExtraButtons;
	int cgamePredictedDataServerTime;
	float clViewangles[3];
	float mouseViewDelta[3];  // Store build only: the view change CL_MouseMove made this frame (name unknown)
	// usercmd_s cmds[128] and the rest follow
};

extern clientActive_t clients[1];  // client_mp/cl_main_mp.cpp

// Inline from client_mp/client_mp.h: one local client in this build.
inline clientActive_t *CL_GetLocalClientGlobals(LocalClientNum_t localClientNum)
{
	return &clients[0];
}

struct AimInput
{
	float deltaTime;
	float deltaTimeScaled;
	float pitch;
	float pitchAxis;
	float pitchMax;
	float yaw;
	float yawAxis;
	float yawMax;
	float forwardAxis;
	float rightAxis;
	int buttons;
	LocalClientNum_t localClientNum;
	unsigned short meleeChargeEnt;
	unsigned char meleeChargeDist;
};

struct AimOutput
{
	float pitch;
	float yaw;
	unsigned short meleeChargeEnt;
	unsigned char meleeChargeDist;
};

void AimAssist_UpdateMouseInput(const AimInput *input, AimOutput *output);  // aim_assist/aim_assist.cpp
void CG_HandleSpecialStateInput(LocalClientNum_t localClientNum, unsigned int *buttons);  // cgame_mp/cg_gamepad.cpp
