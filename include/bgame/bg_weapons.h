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
	unsigned char unknown0[0xA56];
	bool meleeOnly;  // 0xA56, as in the PS4 PDB
};

struct playerState_s;

const WeaponDef *BG_WeaponDef(const Weapon weapon, bool isAlternate);              // bgame/bg_weapons_util.h:384
unsigned long long BG_ClipForWeapon(const Weapon weapon, bool isAlternate);       // bgame/bg_weapons_ammo.cpp:45
int BG_ShotLimitReached(const playerState_s *ps, Weapon weapon, PlayerHandIndex hand);  // bgame/bg_weapons.cpp:3101
