// bgame/bg_weapons.h: the weapon types and helpers the client's input code uses (types and prototypes from the
// PS4 server PDB). Only the fields the reconstructed code reads are spelled out.
#pragma once

union Weapon
{
	unsigned int data;  // weaponIdx:8, weaponVariation:6, weaponScopes:3, weaponUnderBarrels:2, weaponOthers:7, ...
};

enum PlayerHandIndex
{
	WEAPON_HAND_RIGHT = 0x0,
	WEAPON_HAND_LEFT = 0x1,
	NUM_WEAPON_HANDS = 0x2,
	WEAPON_HAND_DEFAULT = 0x0,
};

enum weaponstate_t
{
	WEAPON_READY = 0x0,
	WEAPON_RAISING = 0x1,
	WEAPON_RAISING_ALTSWITCH = 0x2,
	WEAPON_DROPPING = 0x3,
	WEAPON_DROPPING_QUICK = 0x4,
	WEAPON_DROPPING_ALT = 0x5,
	WEAPON_FIRING = 0x6,
	WEAPON_RECHAMBERING = 0x7,
	WEAPON_RELOADING = 0x8,
};

struct PlayerActiveWeaponState
{
	int weapAnim;
	int weaponTime;
	int weaponDelay;
	int weaponRestrictKickTime;
	int weaponState;  // weaponstate_t
	int weapHandFlags;
	unsigned int weaponShotCount;
};

struct GlobalAmmo
{
	unsigned long long ammoType;
	int ammoCount;
};

struct ClipAmmo
{
	unsigned long long clipIndex;
	int ammoCount[2];  // per hand
};

#define MAX_AMMO_SLOTS 15
#define PWF_ALT_MODE 0x4000  // weapFlags bit: the weapon is in its alternate mode (name unknown)

struct XModel;

struct WeaponDef
{
	unsigned char unknown0[0x8];
	XModel **gunXModel;           // 0x8: the viewmodel per variation (Weapon bits 8..13)
	unsigned char unknown10[0x38 - 0x10];
	const void **unknownModels38; // 0x38: the variation falls back to 0 when its gunXModel is missing and this is set
	unsigned char unknown40[0x138 - 0x40];
	const void *turretZoomSound;  // 0x138: played while a turret scope zooms (PS4 PDB: fireStopSoundPlayer; the Store
	                              // build's name unknown)
	unsigned char unknown140[0x358 - 0x140];
	const XModel *viewModelExtra[2];  // 0x358, 0x360: two more models kept loaded with the viewmodel (names unknown)
	unsigned char unknown368[0x5E8 - 0x368];
	int overlayInterface;    // 0x5E8: WeapOverlayInteface_t, 2 a turret scope (PS4 PDB)
	unsigned char unknown5EC[0x640 - 0x5EC];
	float fGunMaxPitch;  // 0x640: degrees the viewmodel's recoil may reach
	float fGunMaxYaw;
	unsigned char unknown648[0x950 - 0x648];
	float turretFov;               // 0x950..0x960 as in the PS4 PDB
	float turretFovADS;
	float turretScopeZoomRate;     // degrees of FOV per second while the forward/back keys zoom the scope
	float turretScopeZoomMin;
	float turretScopeZoomMax;
	unsigned char unknown964[0xA56 - 0x964];
	bool meleeOnly;  // 0xA56, as in the PS4 PDB
	unsigned char unknownA57[0xA88 - 0xA57];
	bool oldWeapon;  // 0xA88
};


// The weapon tables (bgame/bg_weapons_setup.cpp), indexed by Weapon::data & 0xFF. Same layouts in the PS4 server
// and the Store build; only the fields the reconstructed code reads are spelled out.
struct AttViewKick
{
	unsigned char unknown0[0x14];
	float hipViewKickCenterSpeed;
	unsigned char unknown18[0x2C - 0x18];
	float adsViewKickCenterSpeed;
};

struct WeaponAttachment
{
	unsigned char unknown0[0x28];
	XModel **viewModels;  // 0x28: the attachment's viewmodel per variation (name unknown)
	unsigned char unknown30[0xB8 - 0x30];
	const AttViewKick *viewKick;
	unsigned char unknownC0[0x10C - 0xC0];
	float viewCenterScale;  // 0: no change
};

struct WeaponCompleteDef
{
	unsigned char unknown0[0x20];
	WeaponAttachment **scopes;        // 0x20, 0x28, 0x30: by Weapon bits 14..16 (1-based), 17..18 (1-based) and the
	WeaponAttachment **underBarrels;  // seven bits 19..25 (the IW6 asset layout's names; *unverified*)
	WeaponAttachment **others;
	unsigned char unknown38[0xB4 - 0x38];
	float fAdsViewKickCenterSpeed;
	float fHipViewKickCenterSpeed;
	unsigned char unknownBC[0xC8 - 0xBC];
	int altWeapon;  // Weapon::data of the alternate mode; only its low byte is tested
};

enum weapOverlayReticle_t
{
	WEAPOVERLAYRETICLE_NONE = 0x0,
	WEAPOVERLAYRETICLE_CROSSHAIR = 0x1,
	WEAPOVERLAYRETICLE_NUM = 0x2,
};

struct ADSOverlay
{
	unsigned char unknown0[0x20];
	weapOverlayReticle_t reticle;
};

extern WeaponCompleteDef *bg_weaponCompleteDefs[];
extern WeaponDef *bg_weaponDefs[];

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

struct EntityEvent
{
	int eventType;
	int eventParm;
};

struct PlayerEquippedWeaponState  // the PS4 server PDB's layout
{
	bool usedBefore;
	bool dualWielding;
	bool inAltMode;
	bool needsRechamber[2];
	unsigned char unknown5[0x8 - 0x5];
	int zoomLevelIndex;
	bool thermalEnabled;
	bool hybridScope;
	unsigned char unknownE[0x10 - 0xE];
};

// playerState_s: only the fields reconstructed code uses are spelled out, at the Store build's offsets, with the PS4
// server PDB's names. Up to 0x620 the Store build's playerState_s has the PS4 server's layout (it grows later, in the
// HUD data; docs/input.md); the perks and meleeChargeEnt are where the code of both builds reads them. The whole
// struct is 0x3328 bytes in the Store build (the size the cgame copies from a snapshot; 0x3248 in the PS4 server).
struct playerState_s
{
	int commandTime;
	int pm_type;
	int pm_time;
	int pm_flags;
	int otherFlags;
	int linkFlags;
	int bobCycle;
	float origin[3];
	float velocity[3];
	unsigned char unknown34[0x44 - 0x34];
	int movingPlatformEntity;  // the entity the player rides (0x3A..0x7FD), else ENTITYNUM_NONE
	unsigned char unknown48[0x5C - 0x48];
	int gravity;
	int speed;
	float delta_angles[3];
	int groundEntityNum;
	float vLadderVec[3];
	int jumpTime;
	float jumpOriginZ;
	unsigned char unknown88[0xA8 - 0x88];
	int movementDir;
	unsigned char unknownAC[0xBC - 0xAC];
	PlayerVehicleState vehicleState;
	int eFlags;
	int pe_eventSequence;  // pe (playerEvents_t): the predictable events
	EntityEvent pe_events[4];
	int pe_oldEventSequence;
	int pe_timeADSCameUp;  // pe.timeADSCameUp
	int unpredictableEventSequence;
	int unpredictableEventSequenceOld;
	EntityEvent unpredictableEvents[4];
	int clientNum;
	int viewmodelIndex;
	float viewangles[3];
	int viewHeightTarget;
	float viewHeightCurrent;
	int viewHeightLerpTime;
	int viewHeightLerpTarget;
	int viewHeightLerpDown;
	unsigned char unknown1A4[0x1B4 - 0x1A4];
	int damageEvent;
	unsigned char unknown1B8[0x1E8 - 0x1B8];
	int viewlocked_entNum;  // the entity a locked view (a turret, a vehicle) follows, ENTITYNUM_NONE for none
	unsigned char unknown1EC[0x210 - 0x1EC];
	int cursorHint;
	unsigned int cursorHintString;
	int cursorHintEntIndex;
	unsigned char unknown21C[0x228 - 0x21C];
	int radarBlocked;
	int radarMode;
	int radarStrength;  // -3 or less, -2, -1, 0 or more: the radar jamming level's floor (1, 0.5, 0.3, 0)
	unsigned char unknown234[0x23C - 0x234];
	int locationSelectionInfo;
	int sprintState_sprintButtonUpRequired;  // sprintState.sprintButtonUpRequired
	unsigned char unknown244[0x278 - 0x244];
	float mantleState_startPosition[3];  // mantleState.startPosition
	unsigned char unknown284[0x2A8 - 0x284];
	float leanf;
	unsigned char unknown2AC[0x2E4 - 0x2AC];
	Weapon weaponsEquipped[15];
	PlayerEquippedWeaponState weapEquippedData[15];
	unsigned char unknown410[0x41C - 0x410];
	Weapon weapCommon_weapon;
	int weapCommon_weapFlags;         // PWF_ALT_MODE
	float weapCommon_fWeaponPosFrac;  // 0 hip .. 1 fully aimed down the sight (Pmove's ADS transition)
	float weapCommon_aimSpreadScale;  // weapCommon.aimSpreadScale
	unsigned char unknown42C[0x634 - 0x42C];
	float hipViewValue;               // cg.hipViewValue, copied by CG_AddViewWeapon at the hip (name unknown)
	unsigned char unknown638[0xE08 - 0x638];
	int meleeChargeEnt;
	unsigned char unknownE0C[0xE14 - 0xE0C];
	unsigned int perks[2];  // the code of both builds reads them here (the PS4 PDB's type dump says 0xD5C)
	unsigned char unknownE1C[0x13CC - 0xE1C];
	int weaponTimeBase;               // weaponState_t::time and damageTime are cg's times minus this (name unknown)
	unsigned char unknown13D0[0x3328 - 0x13D0];
};
static_assert(__builtin_offsetof(playerState_s, movingPlatformEntity) == 0x44, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, vehicleState) == 0xBC, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, eFlags) == 0x124, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, pe_timeADSCameUp) == 0x150, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, clientNum) == 0x17C, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, viewangles) == 0x184, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, cursorHint) == 0x210, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, viewlocked_entNum) == 0x1E8, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, radarStrength) == 0x230, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, locationSelectionInfo) == 0x23C, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weaponsEquipped) == 0x2E4, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weapEquippedData) == 0x320, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, meleeChargeEnt) == 0xE08, "playerState_s layout");
static_assert(sizeof(playerState_s) == 0x3328, "playerState_s size (Store build)");
static_assert(__builtin_offsetof(playerState_s, gravity) == 0x5C, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, jumpOriginZ) == 0x84, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, viewHeightTarget) == 0x190, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weapCommon_weapon) == 0x41C, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, weapCommon_aimSpreadScale) == 0x428, "playerState_s layout");
static_assert(__builtin_offsetof(playerState_s, perks) == 0xE14, "playerState_s layout");

// The viewmodel's movement state for one frame (bgame/bg_weapons_view.cpp); the cgame builds it from cg_s
// (Store 1402F38B0) and saves it back. Same layout in both builds.
struct weaponState_t
{
	const playerState_s *ps;
	float xyspeed;
	float frametime;        // seconds: cg.frametime * 0.001
	float fLastIdleFactor;
	int time;
	int damageTime;
	float v_dmg_pitch;
	float v_dmg_roll;
	float baseAngles[3];
	float baseOrigin[3];
	float recoilAngles[3];
	float recoilSpeed[3];
	float swayAngles[3];
	float swayOrigin[3];
	float swayViewAngles[3];
	float bobAngles[3];
	int shellShockStart;
	int shellShockDuration;
	int shellShockFadeTime;
};

const WeaponDef *BG_WeaponDef(const Weapon weapon, bool isAlternate);              // bgame/bg_weapons_util.h:384
unsigned long long BG_ClipForWeapon(const Weapon weapon, bool isAlternate);       // bgame/bg_weapons_ammo.cpp:45
int BG_ShotLimitReached(const playerState_s *ps, Weapon weapon, PlayerHandIndex hand);  // bgame/bg_weapons.cpp:3101
