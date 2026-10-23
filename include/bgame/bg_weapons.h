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

struct WeaponDef
{
	unsigned char unknown0[0x640];
	float fGunMaxPitch;  // 0x640: degrees the viewmodel's recoil may reach
	float fGunMaxYaw;
	unsigned char unknown648[0xA56 - 0x648];
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
	unsigned char unknown0[0xB8];
	const AttViewKick *viewKick;
	unsigned char unknownC0[0x10C - 0xC0];
	float viewCenterScale;  // 0: no change
};

struct WeaponCompleteDef
{
	unsigned char unknown0[0xB4];
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

// playerState_s: only the fields reconstructed code uses are spelled out, at the Store build's offsets, with the PS4
// server PDB's names. Up to 0x620 the Store build's playerState_s has the PS4 server's layout (it grows later, in the
// HUD data; docs/input.md); the perks are where the code of both builds reads them.
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
	unsigned char unknown34[0x5C - 0x34];
	int gravity;
	int speed;
	float delta_angles[3];
	int groundEntityNum;
	float vLadderVec[3];
	int jumpTime;
	float jumpOriginZ;
	unsigned char unknown88[0x150 - 0x88];
	int pe_timeADSCameUp;  // pe.timeADSCameUp
	unsigned char unknown154[0x190 - 0x154];
	int viewHeightTarget;
	float viewHeightCurrent;
	int viewHeightLerpTime;
	int viewHeightLerpTarget;
	int viewHeightLerpDown;
	unsigned char unknown1A4[0x240 - 0x1A4];
	int sprintState_sprintButtonUpRequired;  // sprintState.sprintButtonUpRequired
	unsigned char unknown244[0x41C - 0x244];
	Weapon weapCommon_weapon;
	int weapCommon_weapFlags;         // PWF_ALT_MODE
	float weapCommon_fWeaponPosFrac;  // 0 hip .. 1 fully aimed down the sight (Pmove's ADS transition)
	float weapCommon_aimSpreadScale;  // weapCommon.aimSpreadScale
	unsigned char unknown42C[0xE14 - 0x42C];
	unsigned int perks[2];  // the code of both builds reads them here (the PS4 PDB's type dump says 0xD5C)
};
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
