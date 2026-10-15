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

// The leading fields of playerState_s, the snapshot header after the scores, and the size of clSnapshot_s in the
// Store build (the fields after the scores are 0x104 further on than in the server PDB).
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
	unsigned char unknown620[0x3474 - 0x620];  // the rest of playerState_s, ScoreboardInfo scores
	int valid;
	int snapFlags;
	int serverTime;
	int messageNum;
	unsigned char tail[0x34B8 - 0x3484];
};

struct PlayerVehicleState
{
	int entity;  // ENTITYNUM_NONE (0x7FF) or 0 when not in a vehicle
	int flags;
	int targetEntity;
	float origin[3];
	float angles[3];
	float velocity[3];
	float angVelocity[3];
	float tilt[2];
	float tiltVelocity[2];
	float gunAngles[2];
	unsigned int splineId;
	unsigned int splineNodeIndex;
	float splineLambda;
	float corridorSpeeds[2];
};

struct outPacket_t
{
	int p_cmdNumber;
	int p_serverTime;
	int p_realtime;
};

#define CMD_BACKUP 128
#define CMD_MASK (CMD_BACKUP - 1)
#define MAX_PACKET_USERCMDS 32

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
	PlayerVehicleState cgamePlayerVehState;
	int cgameBobCycle;
	int cgameMovementDir;
	int cgameExtraButtons;
	int cgamePredictedDataServerTime;
	float clViewangles[3];
	float mouseViewDelta[3];  // Store build only: the view change CL_MouseMove made this frame (name unknown)
	usercmd_s cmds[CMD_BACKUP];
	int cmdNumber;
	unsigned char clientArchive[256][0x8C];  // ClientArchiveData
	int clientArchiveIndex;
	int packetBackupCount;
	int packetBackupMask;
	int parseEntitiesCount;
	int parseClientsCount;
	int parseOmnvarsCount;
	outPacket_t outPackets[16];
	// clSnapshot_s snapshots[] and the rest follow
};

extern clientActive_t clients[1];  // client_mp/cl_main_mp.cpp

// Inline from client_mp/client_mp.h: one local client in this build.
inline clientActive_t *CL_GetLocalClientGlobals(LocalClientNum_t localClientNum)
{
	return &clients[0];
}

enum netadrtype_t
{
	NA_BOT = 0x0,
	NA_BAD = 0x1,
	NA_LOOPBACK = 0x2,
	NA_BROADCAST = 0x3,
	NA_IP = 0x4,
};

// The leading netchan_t fields the client code reads, at their Store offsets.
struct netchan_t
{
	int outgoingSequence;
	int sock;                        // netsrc_t
	int dropped;
	int incomingSequence;
	netadrtype_t remoteAddressType;  // remoteAddress.type
	unsigned char unknown14[0x3C - 0x14];
	int unsentFragments;
	// the rest is opaque
};

// The client's connection to the server in the Store build. Its netadr_s is 0x10 bytes (0x14 in the server PDB), so
// the fields after serverAddress are 4 bytes earlier than in the PDB, up to netchan, which is 8-aligned again.
struct clientConnection_t
{
	int qport;
	int clientNum;
	int lastPacketTime;
	unsigned char serverAddress[0x10];  // netadr_s
	int connectLastSendTime;            // also when CL_WritePacket last sent a packet (Black Ops: lastPacketSentTime)
	int connectPacketCount;
	char serverMessage[256];
	int challenge;
	int checksumFeed;
	int reliableSequence;
	int reliableAcknowledge;
	char reliableCommands[128][1024];
	int serverMessageSequence;
	int serverCommandSequence;
	int lastExecutedServerCommand;
	char serverCommands[128][1024];
	bool isServerRestarting;
	alignas(8) netchan_t netchan;  // netchan_t has pointers after the fields above
	// netchanOutgoingBuffer and the rest follow
};

extern clientConnection_t clientConnections[1];  // client_mp/cl_main_mp.cpp

// Inline from client_mp/client_mp.h: one local client in this build.
inline clientConnection_t *CL_GetLocalClientConnection(LocalClientNum_t localClientNum)
{
	return &clientConnections[0];
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
