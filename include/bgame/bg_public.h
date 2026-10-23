// bgame/bg_public.h: the player movement types (playerState_s, pmove_t, pml_t, trace_t), with the PS4 server PDB's
// field names. Only the fields the reconstructed movement code uses are spelled out, at the Store build's offsets;
// up to 0x620 the Store build's playerState_s has the PS4 server's layout (it grows later, in the HUD data;
// docs/input.md), and pmove_t and pml_t are the same size as the server's (0x178, 0xA4).
#pragma once

#include "client_mp/client_mp.h"  // usercmd_s
#include "universal/com_math.h"   // Bounds

#define ENTITYNUM_WORLD 0x7FE
#ifndef ENTITYNUM_NONE
#define ENTITYNUM_NONE 0x7FF
#endif

// pm_flags (names from Quake 3 where the bit is the same, else descriptive)
#define PMF_PRONE 0x1
#define PMF_DUCKED 0x2
#define PMF_MANTLE 0x4
#define PMF_LADDER 0x8
#define PMF_JUMP_HELD 0x80   // with 0x100: cleared by a jump
#define PMF_TIME_LAND 0x100
#define PMF_FROZEN 0x400     // jump refused (name unknown)
#define PMF_JUMPING 0x2000   // a jump is in progress: jumpOriginZ is valid and the jump slowdown applies
#define PMF_NO_JUMP 0x40000  // jump refused (name unknown)

// playerState_s is in bgame/bg_weapons.h (the lowest header that needs it; client_mp.h includes it)

struct trace_t
{
	float fraction;
	float normal[3];
	int surfaceFlags;
	int contents;
	int hitType;  // TraceHitType
	unsigned short hitId;
	unsigned short modelIndex;
	unsigned int partName;
	unsigned short partGroup;
	bool allsolid;
	bool startsolid;
	bool walkable;
	bool getPenetration;
	bool removePitchAndRollRotations;
};

struct Bounds;

struct pmove_t
{
	playerState_s *ps;
	usercmd_s cmd;
	usercmd_s oldcmd;
	int tracemask;
	int numtouch;
	int touchents[32];
	float bounds[6];  // Bounds: midPoint, halfSize
	float speed;
	int contactEntity;
	int proneChange;
	bool mantleStarted;
	float mantleEndPos[3];
	int mantleDuration;
	float meleeEntOrigin[3];
	float meleeEntVelocity[3];
	int viewChangeTime;
	float viewChange;
	float fTorsoPitch;
	float fWaistPitch;
	int remoteTurretFireTime;
	int lastUpdateCMDServerTime;
	unsigned int groundSurfaceType;
	unsigned char handler;
};

struct pml_t
{
	float forward[3];
	float right[3];
	float up[3];
	float frametime;
	int msec;
	int walking;
	int groundPlane;
	int almostGroundPlane;
	trace_t groundTrace;
	float impactSpeed;
	float previous_origin[3];
	float previous_velocity[3];
	float wishdir[3];
	unsigned int holdrand;
	float platformUp[3];
	int flinch;
	int turning;
};

struct trajectory_t
{
	int trType;
	int trTime;
	int trDuration;
	float trBase[3];
	float trDelta[3];
};

// The part of an entity's state the client interpolates (LerpEntityState): only the trajectories are spelled out.
struct LerpEntityState
{
	int eFlags;
	trajectory_t pos;
	trajectory_t apos;
	unsigned char u[0x68 - 0x4C];  // per entity type; for a player, the torso and waist pitch at +8 and +0xC
};

// entityState_s: the Store build's layout up to the weapon (what the cgame's item and player code reads)
struct entityState_s
{
	int number;
	int eType;
	LerpEntityState lerp;
	unsigned char unknown70[0xC4 - 0x70];
	Weapon weapon;  // an item's weapon
};
static_assert(sizeof(trajectory_t) == 0x24, "trajectory_t layout");
static_assert(__builtin_offsetof(entityState_s, lerp.apos) == 0x30, "entityState_s layout (Store build)");
static_assert(__builtin_offsetof(entityState_s, weapon) == 0xC4, "entityState_s layout (Store build)");

struct OmnvarData
{
	unsigned int timeModified;
	float value;  // current.value (a union with the integer and enum values)
};

struct OmnvarDef;

enum EffectiveStance
{
	PM_EFF_STANCE_DEFAULT = 0x0,
	PM_EFF_STANCE_PRONE = 0x1,
	PM_EFF_STANCE_DUCKED = 0x2,
	PM_EFF_STANCE_LASTSTANDCRAWL = 0x3,
	PM_EFF_STANCE_COUNT = 0x4,
};

enum scriptAnimEventTypes_t
{
	ANIM_ET_JUMP = 0x2,    // the PS4 server's values for the two Jump_Check uses
	ANIM_ET_JUMPBK = 0x3,
};

static_assert(sizeof(trace_t) == 0x2C, "trace_t layout");
static_assert(sizeof(pmove_t) == 0x178, "pmove_t layout (Store build, as the PS4 server's)");
static_assert(__builtin_offsetof(pmove_t, oldcmd) == 0x44, "pmove_t layout");
static_assert(__builtin_offsetof(pmove_t, numtouch) == 0x84, "pmove_t layout");
static_assert(__builtin_offsetof(pmove_t, fTorsoPitch) == 0x160, "pmove_t layout");
static_assert(__builtin_offsetof(pmove_t, handler) == 0x174, "pmove_t layout");
static_assert(sizeof(pml_t) == 0xA4, "pml_t layout");
static_assert(__builtin_offsetof(pml_t, groundTrace) == 0x38, "pml_t layout");
static_assert(__builtin_offsetof(pml_t, holdrand) == 0x8C, "pml_t layout");
static_assert(__builtin_offsetof(playerState_s, gravity) == 0x5C, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, jumpOriginZ) == 0x84, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, viewHeightTarget) == 0x190, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weapCommon_aimSpreadScale) == 0x428, "playerState_s layout");

// bgame
void PmoveSingle(pmove_t *pm);                                                  // bgame/bg_pmove.cpp
int BG_GetStandingViewHeight();                                                 // bgame/bg_pmove.cpp
EffectiveStance PM_GetEffectiveStance(const playerState_s *ps);
unsigned int PM_GroundSurfaceType(pml_t *pml);
const entityState_s *BG_GetEntityState(unsigned char handler, int entityIndex);
int BG_PackFootstepEventParm(const playerState_s *ps, int surfaceType);         // bgame/bg_equipment_snd.cpp
void BG_AddPredictableEventToPlayerstate(int newEvent, int eventParm, playerState_s *ps);
void BG_AnimUpdatePlayerStateConditions(pmove_t *pm);                           // bgame/bg_animation_mp.cpp
int BG_AnimScriptEvent(playerState_s *ps, scriptAnimEventTypes_t event, int isContinue, int force, unsigned int *randSeed);
unsigned int Omnvar_GetIndexByName(const char *name);                           // game/g_omnvar.cpp
const OmnvarDef *Omnvar_GetDef(unsigned int index);
OmnvarData *G_Omnvar_GetData(unsigned int index, int clientNum, playerState_s *const ps);
OmnvarData *sub_140543040(LocalClientNum_t localClientNum, unsigned int index);             // the cgame's omnvar data (name unknown)
float Vec3Normalize(float *const v);
void Sys_SnapVector(float *v);                                                  // win32/win_shared.cpp
