// bgame/bg_weapons_load_db.h: the full layouts of the weapon assets as the zone loaders see them: WeaponCompleteDef
// (asset type 0x23) with its WeaponDef, WeaponAttachment (0x22) with its Att* blocks, VehicleDef (0x32), and the
// override entries. Transcribed field for field from the PS4 server PDB (analysis/iw6_ds_ps4/pdb/types.h); the Store
// build's loaders use the same offsets and sizes (src/bgame/bg_weapons_load_db.cpp, tests/differential/
// test_weapon_load.py). The PDB renders accuracyGraphKnots as `float *[2][2]` at 16 bytes: it is two vec2_t arrays.
//
// bgame/bg_weapons.h keeps the partial layouts the gameplay code was reconstructed against (unknown fields named by
// offset); the two are not included together.
#pragma once

#include <stddef.h>

#include "database/db_stream_api.h"

enum AttachmentType : int;
enum ImpactType : int;
enum OffhandClass : int;
enum PenetrateType : int;
enum VehCamZOffsetMode : int;
enum VehicleAxleType : int;
enum VehicleTurretFireType : int;
enum VehicleType : int;
enum WeapOverlayInteface_t : int;
enum WeapStickinessType : int;
enum activeReticleType_t : int;
enum ammoCounterClipType_t : int;
enum guidedMissileType_t : int;
enum weapClass_t : int;
enum weapFireType_t : int;
enum weapInventoryType_t : int;
enum weapOverlayReticle_t : int;
enum weapProjExposion_t : int;
enum weapStance_t : int;
enum weapType_t : int;
enum weaponIconRatioType_t : int;

struct ADSOverlay;
struct AnimOverrideEntry;
struct AttADSOverlay;
struct AttADSSettings;
struct AttAddOns;
struct AttAimAssist;
struct AttAmmoGeneral;
struct AttAmmunition;
struct AttDamage;
struct AttGeneral;
struct AttGunKick;
struct AttHipSpread;
struct AttIdleSettings;
struct AttLocationDamage;
struct AttProjectile;
struct AttReload;
struct AttRumbles;
struct AttScopeDriftSettings;
struct AttSight;
struct AttUI;
struct AttViewKick;
struct FXOverrideEntry;
struct FxEffectDef;
struct Material;
struct NoteTrackToSoundEntry;
struct PhysCollmap;
struct PhysPreset;
struct ReloadStateTimerEntry;
struct SoundOverrideEntry;
struct StateTimers;
struct TracerDef;
struct VehicleDef;
struct VehiclePhysDef;
struct WeaponAttachment;
struct WeaponCompleteDef;
struct WeaponDef;
struct XAnimParts;
struct XModel;
struct snd_alias_list_t;
typedef float vec2_t[2];

struct WeaponCompleteDef
{
	const char *szInternalName;                             // +0x000
	WeaponDef *weapDef;                                     // +0x008
	const char *szDisplayName;                              // +0x010
	scr_string_t *hideTags;                                 // +0x018
	WeaponAttachment **scopes;                              // +0x020
	WeaponAttachment **underBarrels;                        // +0x028
	WeaponAttachment **others;                              // +0x030
	XAnimParts **szXAnims;                                  // +0x038
	unsigned int numAnimOverrides;                          // +0x040
	AnimOverrideEntry *animOverrides;                       // +0x048
	unsigned int numSoundOverrides;                         // +0x050
	SoundOverrideEntry *soundOverrides;                     // +0x058
	unsigned int numFXOverrides;                            // +0x060
	FXOverrideEntry *fxOverrides;                           // +0x068
	unsigned int numReloadStateTimerOverrides;              // +0x070
	ReloadStateTimerEntry *reloadOverrides;                 // +0x078
	unsigned int numNotetrackOverrides;                     // +0x080
	NoteTrackToSoundEntry *notetrackOverrides;              // +0x088
	float fAdsZoomFov;                                      // +0x090
	int iAdsTransInTime;                                    // +0x094
	int iAdsTransOutTime;                                   // +0x098
	int iClipSize;                                          // +0x09C
	ImpactType impactType;                                  // +0x0A0
	int iFireTime;                                          // +0x0A4
	int iFireTimeAkimbo;                                    // +0x0A8
	weaponIconRatioType_t dpadIconRatio;                    // +0x0AC
	float penetrateMultiplier;                              // +0x0B0
	float fAdsViewKickCenterSpeed;                          // +0x0B4
	float fHipViewKickCenterSpeed;                          // +0x0B8
	const char *szAltWeaponName;                            // +0x0C0
	int altWeapon;                                          // +0x0C8
	int iAltRaiseTime;                                      // +0x0CC
	int iAltRaiseTimeAkimbo;                                // +0x0D0
	Material *killIcon;                                     // +0x0D8
	Material *dpadIcon;                                     // +0x0E0
	int fireAnimLength;                                     // +0x0E8
	int fireAnimLengthAkimbo;                               // +0x0EC
	int iFirstRaiseTime;                                    // +0x0F0
	int iFirstRaiseTimeAkimbo;                              // +0x0F4
	int ammoDropStockMax;                                   // +0x0F8
	float adsDofStart;                                      // +0x0FC
	float adsDofEnd;                                        // +0x100
	unsigned short accuracyGraphKnotCount[2];               // +0x104
	vec2_t *accuracyGraphKnots[2];                          // +0x108
	bool motionTracker;                                     // +0x118
	bool enhanced;                                          // +0x119
	bool dpadIconShowsAmmo;                                 // +0x11A
	const char *szAdsrBaseSetting;                          // +0x120
};
static_assert(sizeof(WeaponCompleteDef) == 0x128, "WeaponCompleteDef");
static_assert(offsetof(WeaponCompleteDef, szInternalName) == 0x0, "WeaponCompleteDef::szInternalName");
static_assert(offsetof(WeaponCompleteDef, weapDef) == 0x8, "WeaponCompleteDef::weapDef");
static_assert(offsetof(WeaponCompleteDef, szDisplayName) == 0x10, "WeaponCompleteDef::szDisplayName");
static_assert(offsetof(WeaponCompleteDef, hideTags) == 0x18, "WeaponCompleteDef::hideTags");
static_assert(offsetof(WeaponCompleteDef, scopes) == 0x20, "WeaponCompleteDef::scopes");
static_assert(offsetof(WeaponCompleteDef, underBarrels) == 0x28, "WeaponCompleteDef::underBarrels");
static_assert(offsetof(WeaponCompleteDef, others) == 0x30, "WeaponCompleteDef::others");
static_assert(offsetof(WeaponCompleteDef, szXAnims) == 0x38, "WeaponCompleteDef::szXAnims");
static_assert(offsetof(WeaponCompleteDef, animOverrides) == 0x48, "WeaponCompleteDef::animOverrides");
static_assert(offsetof(WeaponCompleteDef, soundOverrides) == 0x58, "WeaponCompleteDef::soundOverrides");
static_assert(offsetof(WeaponCompleteDef, fxOverrides) == 0x68, "WeaponCompleteDef::fxOverrides");
static_assert(offsetof(WeaponCompleteDef, reloadOverrides) == 0x78, "WeaponCompleteDef::reloadOverrides");
static_assert(offsetof(WeaponCompleteDef, notetrackOverrides) == 0x88, "WeaponCompleteDef::notetrackOverrides");
static_assert(offsetof(WeaponCompleteDef, szAltWeaponName) == 0xC0, "WeaponCompleteDef::szAltWeaponName");
static_assert(offsetof(WeaponCompleteDef, killIcon) == 0xD8, "WeaponCompleteDef::killIcon");
static_assert(offsetof(WeaponCompleteDef, dpadIcon) == 0xE0, "WeaponCompleteDef::dpadIcon");
static_assert(offsetof(WeaponCompleteDef, accuracyGraphKnots) == 0x108, "WeaponCompleteDef::accuracyGraphKnots");
static_assert(offsetof(WeaponCompleteDef, szAdsrBaseSetting) == 0x120, "WeaponCompleteDef::szAdsrBaseSetting");

struct StateTimers
{
	int iFireDelay;                                         // +0x000
	int iMeleeDelay;                                        // +0x004
	int meleeChargeDelay;                                   // +0x008
	int iDetonateDelay;                                     // +0x00C
	int iRechamberTime;                                     // +0x010
	int rechamberTimeOneHanded;                             // +0x014
	int iRechamberBoltTime;                                 // +0x018
	int iHoldFireTime;                                      // +0x01C
	int iHoldPrimeTime;                                     // +0x020
	int iDetonateTime;                                      // +0x024
	int iMeleeTime;                                         // +0x028
	int meleeChargeTime;                                    // +0x02C
	int iReloadTime;                                        // +0x030
	int reloadShowRocketTime;                               // +0x034
	int iReloadEmptyTime;                                   // +0x038
	int iReloadAddTime;                                     // +0x03C
	int iReloadEmptyAddTime;                                // +0x040
	int iReloadStartTime;                                   // +0x044
	int iReloadStartAddTime;                                // +0x048
	int iReloadEndTime;                                     // +0x04C
	int iDropTime;                                          // +0x050
	int iRaiseTime;                                         // +0x054
	int iAltDropTime;                                       // +0x058
	int quickDropTime;                                      // +0x05C
	int quickRaiseTime;                                     // +0x060
	int iBreachRaiseTime;                                   // +0x064
	int iEmptyRaiseTime;                                    // +0x068
	int iEmptyDropTime;                                     // +0x06C
	int sprintInTime;                                       // +0x070
	int sprintLoopTime;                                     // +0x074
	int sprintOutTime;                                      // +0x078
	int stunnedTimeBegin;                                   // +0x07C
	int stunnedTimeLoop;                                    // +0x080
	int stunnedTimeEnd;                                     // +0x084
	int nightVisionWearTime;                                // +0x088
	int nightVisionWearTimeFadeOutEnd;                      // +0x08C
	int nightVisionWearTimePowerUp;                         // +0x090
	int nightVisionRemoveTime;                              // +0x094
	int nightVisionRemoveTimePowerDown;                     // +0x098
	int nightVisionRemoveTimeFadeInStart;                   // +0x09C
	int fuseTime;                                           // +0x0A0
	int aiFuseTime;                                         // +0x0A4
	int primeTime;                                          // +0x0A8
	bool bHoldFullPrime;                                    // +0x0AC
	int blastFrontTime;                                     // +0x0B0
	int blastRightTime;                                     // +0x0B4
	int blastBackTime;                                      // +0x0B8
	int blastLeftTime;                                      // +0x0BC
	int slideInTime;                                        // +0x0C0
	int slideLoopTime;                                      // +0x0C4
	int slideOutTime;                                       // +0x0C8
};
static_assert(sizeof(StateTimers) == 0xCC, "StateTimers");

struct ADSOverlay
{
	Material *shader;                                       // +0x000
	Material *shaderLowRes;                                 // +0x008
	Material *shaderEMP;                                    // +0x010
	Material *shaderEMPLowRes;                              // +0x018
	weapOverlayReticle_t reticle;                           // +0x020
	float width;                                            // +0x024
	float height;                                           // +0x028
	float widthSplitscreen;                                 // +0x02C
	float heightSplitscreen;                                // +0x030
};
static_assert(sizeof(ADSOverlay) == 0x38, "ADSOverlay");
static_assert(offsetof(ADSOverlay, shader) == 0x0, "ADSOverlay::shader");
static_assert(offsetof(ADSOverlay, shaderLowRes) == 0x8, "ADSOverlay::shaderLowRes");
static_assert(offsetof(ADSOverlay, shaderEMP) == 0x10, "ADSOverlay::shaderEMP");
static_assert(offsetof(ADSOverlay, shaderEMPLowRes) == 0x18, "ADSOverlay::shaderEMPLowRes");

struct WeaponDef
{
	const char *szOverlayName;                              // +0x000
	XModel **gunXModel;                                     // +0x008
	XModel *handXModel;                                     // +0x010
	XModel *camoWorldModel;                                 // +0x018
	XModel *camoViewModel;                                  // +0x020
	Material *camoWorldModelMaterialOverride;               // +0x028
	Material *camoViewModelMaterialOverride;                // +0x030
	Material **camoMaterialTarget;                          // +0x038
	XAnimParts **szXAnimsRightHanded;                       // +0x040
	XAnimParts **szXAnimsLeftHanded;                        // +0x048
	const char *szModeName;                                 // +0x050
	scr_string_t *notetrackSoundMapKeys;                    // +0x058
	scr_string_t *notetrackSoundMapValues;                  // +0x060
	scr_string_t *notetrackRumbleMapKeys;                   // +0x068
	scr_string_t *notetrackRumbleMapValues;                 // +0x070
	scr_string_t *notetrackFXMapKeys;                       // +0x078
	FxEffectDef **notetrackFXMapValues;                     // +0x080
	scr_string_t *notetrackFXMapTagValues;                  // +0x088
	int playerAnimType;                                     // +0x090
	weapType_t weapType;                                    // +0x094
	weapClass_t weapClass;                                  // +0x098
	PenetrateType penetrateType;                            // +0x09C
	weapInventoryType_t inventoryType;                      // +0x0A0
	weapFireType_t fireType;                                // +0x0A4
	float burstFireCooldown;                                // +0x0A8
	OffhandClass offhandClass;                              // +0x0AC
	weapStance_t stance;                                    // +0x0B0
	unsigned char rattleSoundType;                          // +0x0B4
	FxEffectDef *viewFlashEffect;                           // +0x0B8
	FxEffectDef *worldFlashEffect;                          // +0x0C0
	FxEffectDef *viewFlashADSEffect;                        // +0x0C8
	snd_alias_list_t *pickupSound;                          // +0x0D0
	snd_alias_list_t *pickupSoundPlayer;                    // +0x0D8
	snd_alias_list_t *ammoPickupSound;                      // +0x0E0
	snd_alias_list_t *ammoPickupSoundPlayer;                // +0x0E8
	snd_alias_list_t *projectileSound;                      // +0x0F0
	snd_alias_list_t *pullbackSound;                        // +0x0F8
	snd_alias_list_t *pullbackSoundPlayer;                  // +0x100
	snd_alias_list_t *fireSound;                            // +0x108
	snd_alias_list_t *fireSoundPlayer;                      // +0x110
	snd_alias_list_t *fireSoundPlayerAkimbo;                // +0x118
	snd_alias_list_t *fireLoopSound;                        // +0x120
	snd_alias_list_t *fireLoopSoundPlayer;                  // +0x128
	snd_alias_list_t *fireStopSound;                        // +0x130
	snd_alias_list_t *fireStopSoundPlayer;                  // +0x138
	snd_alias_list_t *fireLastSound;                        // +0x140
	snd_alias_list_t *fireLastSoundPlayer;                  // +0x148
	snd_alias_list_t *emptyFireSound;                       // +0x150
	snd_alias_list_t *emptyFireSoundPlayer;                 // +0x158
	snd_alias_list_t *meleeSwipeSound;                      // +0x160
	snd_alias_list_t *meleeSwipeSoundPlayer;                // +0x168
	snd_alias_list_t *meleeHitSound;                        // +0x170
	snd_alias_list_t *meleeMissSound;                       // +0x178
	snd_alias_list_t *rechamberSound;                       // +0x180
	snd_alias_list_t *rechamberSoundPlayer;                 // +0x188
	snd_alias_list_t *reloadSound;                          // +0x190
	snd_alias_list_t *reloadSoundPlayer;                    // +0x198
	snd_alias_list_t *reloadEmptySound;                     // +0x1A0
	snd_alias_list_t *reloadEmptySoundPlayer;               // +0x1A8
	snd_alias_list_t *reloadStartSound;                     // +0x1B0
	snd_alias_list_t *reloadStartSoundPlayer;               // +0x1B8
	snd_alias_list_t *reloadEndSound;                       // +0x1C0
	snd_alias_list_t *reloadEndSoundPlayer;                 // +0x1C8
	snd_alias_list_t *detonateSound;                        // +0x1D0
	snd_alias_list_t *detonateSoundPlayer;                  // +0x1D8
	snd_alias_list_t *nightVisionWearSound;                 // +0x1E0
	snd_alias_list_t *nightVisionWearSoundPlayer;           // +0x1E8
	snd_alias_list_t *nightVisionRemoveSound;               // +0x1F0
	snd_alias_list_t *nightVisionRemoveSoundPlayer;         // +0x1F8
	snd_alias_list_t *altSwitchSound;                       // +0x200
	snd_alias_list_t *altSwitchSoundPlayer;                 // +0x208
	snd_alias_list_t *raiseSound;                           // +0x210
	snd_alias_list_t *raiseSoundPlayer;                     // +0x218
	snd_alias_list_t *firstRaiseSound;                      // +0x220
	snd_alias_list_t *firstRaiseSoundPlayer;                // +0x228
	snd_alias_list_t *putawaySound;                         // +0x230
	snd_alias_list_t *putawaySoundPlayer;                   // +0x238
	snd_alias_list_t *scanSound;                            // +0x240
	snd_alias_list_t *changeVariableZoomSound;              // +0x248
	snd_alias_list_t **bounceSound;                         // +0x250
	snd_alias_list_t **rollingSound;                        // +0x258
	FxEffectDef *viewShellEjectEffect;                      // +0x260
	FxEffectDef *worldShellEjectEffect;                     // +0x268
	FxEffectDef *viewLastShotEjectEffect;                   // +0x270
	FxEffectDef *worldLastShotEjectEffect;                  // +0x278
	FxEffectDef *viewMagEjectEffect;                        // +0x280
	Material *reticleCenter;                                // +0x288
	Material *reticleSide;                                  // +0x290
	int iReticleCenterSize;                                 // +0x298
	int iReticleSideSize;                                   // +0x29C
	int iReticleMinOfs;                                     // +0x2A0
	activeReticleType_t activeReticleType;                  // +0x2A4
	float vStandMove[3];                                    // +0x2A8
	float vStandRot[3];                                     // +0x2B4
	float strafeMove[3];                                    // +0x2C0
	float strafeRot[3];                                     // +0x2CC
	float vDuckedOfs[3];                                    // +0x2D8
	float vDuckedMove[3];                                   // +0x2E4
	float vDuckedRot[3];                                    // +0x2F0
	float vProneOfs[3];                                     // +0x2FC
	float vProneMove[3];                                    // +0x308
	float vProneRot[3];                                     // +0x314
	float fPosMoveRate;                                     // +0x320
	float fPosProneMoveRate;                                // +0x324
	float fStandMoveMinSpeed;                               // +0x328
	float fDuckedMoveMinSpeed;                              // +0x32C
	float fProneMoveMinSpeed;                               // +0x330
	float fPosRotRate;                                      // +0x334
	float fPosProneRotRate;                                 // +0x338
	float fStandRotMinSpeed;                                // +0x33C
	float fDuckedRotMinSpeed;                               // +0x340
	float fProneRotMinSpeed;                                // +0x344
	XModel **worldModel;                                    // +0x348
	XModel *worldClipModel;                                 // +0x350
	XModel *rocketModel;                                    // +0x358
	XModel *knifeModel;                                     // +0x360
	XModel *worldKnifeModel;                                // +0x368
	Material *hudIcon;                                      // +0x370
	weaponIconRatioType_t hudIconRatio;                     // +0x378
	Material *pickupIcon;                                   // +0x380
	weaponIconRatioType_t pickupIconRatio;                  // +0x388
	Material *ammoCounterIcon;                              // +0x390
	weaponIconRatioType_t ammoCounterIconRatio;             // +0x398
	ammoCounterClipType_t ammoCounterClip;                  // +0x39C
	int iStartAmmo;                                         // +0x3A0
	const char *szAmmoName;                                 // +0x3A8
	int iAmmoIndex;                                         // +0x3B0
	const char *szClipName;                                 // +0x3B8
	int iClipIndex;                                         // +0x3C0
	int iMaxAmmo;                                           // +0x3C4
	int shotCount;                                          // +0x3C8
	const char *szSharedAmmoCapName;                        // +0x3D0
	int iSharedAmmoCapIndex;                                // +0x3D8
	int iSharedAmmoCap;                                     // +0x3DC
	int damage;                                             // +0x3E0
	int playerDamage;                                       // +0x3E4
	int iMeleeDamage;                                       // +0x3E8
	int iDamageType;                                        // +0x3EC
	StateTimers stateTimers;                                // +0x3F0
	StateTimers akimboStateTimers;                          // +0x4BC
	float autoAimRange;                                     // +0x588
	float aimAssistRange;                                   // +0x58C
	float aimAssistRangeAds;                                // +0x590
	float aimPadding;                                       // +0x594
	float enemyCrosshairRange;                              // +0x598
	float moveSpeedScale;                                   // +0x59C
	float adsMoveSpeedScale;                                // +0x5A0
	float sprintDurationScale;                              // +0x5A4
	float fAdsZoomInFrac;                                   // +0x5A8
	float fAdsZoomOutFrac;                                  // +0x5AC
	ADSOverlay overlay;                                     // +0x5B0
	WeapOverlayInteface_t overlayInterface;                 // +0x5E8
	float fAdsBobFactor;                                    // +0x5EC
	float fAdsViewBobMult;                                  // +0x5F0
	float fHipSpreadStandMin;                               // +0x5F4
	float fHipSpreadDuckedMin;                              // +0x5F8
	float fHipSpreadProneMin;                               // +0x5FC
	float hipSpreadStandMax;                                // +0x600
	float hipSpreadDuckedMax;                               // +0x604
	float hipSpreadProneMax;                                // +0x608
	float fHipSpreadDecayRate;                              // +0x60C
	float fHipSpreadFireAdd;                                // +0x610
	float fHipSpreadTurnAdd;                                // +0x614
	float fHipSpreadMoveAdd;                                // +0x618
	float fHipSpreadDuckedDecay;                            // +0x61C
	float fHipSpreadProneDecay;                             // +0x620
	float fHipReticleSidePos;                               // +0x624
	float fAdsIdleAmount;                                   // +0x628
	float fHipIdleAmount;                                   // +0x62C
	float adsIdleSpeed;                                     // +0x630
	float hipIdleSpeed;                                     // +0x634
	float fIdleCrouchFactor;                                // +0x638
	float fIdleProneFactor;                                 // +0x63C
	float fGunMaxPitch;                                     // +0x640
	float fGunMaxYaw;                                       // +0x644
	float adsIdleLerpStartTime;                             // +0x648
	float adsIdleLerpTime;                                  // +0x64C
	float swayMaxAngleSteadyAim;                            // +0x650
	float swayMaxAngle;                                     // +0x654
	float swayLerpSpeed;                                    // +0x658
	float swayPitchScale;                                   // +0x65C
	float swayYawScale;                                     // +0x660
	float swayHorizScale;                                   // +0x664
	float swayVertScale;                                    // +0x668
	float swayShellShockScale;                              // +0x66C
	float adsSwayMaxAngle;                                  // +0x670
	float adsSwayLerpSpeed;                                 // +0x674
	float adsSwayPitchScale;                                // +0x678
	float adsSwayYawScale;                                  // +0x67C
	float adsSwayHorizScale;                                // +0x680
	float adsSwayVertScale;                                 // +0x684
	float adsViewErrorMin;                                  // +0x688
	float adsViewErrorMax;                                  // +0x68C
	float adsFireAnimFrac;                                  // +0x690
	PhysCollmap *physCollmap;                               // +0x698
	float dualWieldViewModelOffset;                         // +0x6A0
	float fScopeDriftDelay;                                 // +0x6A4
	float fScopeDriftLerpInTime;                            // +0x6A8
	float fScopeDriftSteadyTime;                            // +0x6AC
	float fScopeDriftLerpOutTime;                           // +0x6B0
	float fScopeDriftSteadyFactor;                          // +0x6B4
	float fScopeDriftUnsteadyFactor;                        // +0x6B8
	weaponIconRatioType_t killIconRatio;                    // +0x6BC
	int iReloadAmmoAdd;                                     // +0x6C0
	int iReloadStartAdd;                                    // +0x6C4
	int ammoDropStockMin;                                   // +0x6C8
	int ammoDropClipPercentMin;                             // +0x6CC
	int ammoDropClipPercentMax;                             // +0x6D0
	int iExplosionRadius;                                   // +0x6D4
	int iExplosionRadiusMin;                                // +0x6D8
	int iExplosionInnerDamage;                              // +0x6DC
	int iExplosionOuterDamage;                              // +0x6E0
	float damageConeAngle;                                  // +0x6E4
	float bulletExplDmgMult;                                // +0x6E8
	float bulletExplRadiusMult;                             // +0x6EC
	int iProjectileSpeed;                                   // +0x6F0
	int iProjectileSpeedUp;                                 // +0x6F4
	int iProjectileSpeedForward;                            // +0x6F8
	int iProjectileActivateDist;                            // +0x6FC
	float projLifetime;                                     // +0x700
	float timeToAccelerate;                                 // +0x704
	float projectileCurvature;                              // +0x708
	const char *projectileName;                             // +0x710
	XModel *projectileModel;                                // +0x718
	weapProjExposion_t projExplosion;                       // +0x720
	FxEffectDef *projExplosionEffect;                       // +0x728
	FxEffectDef *projDudEffect;                             // +0x730
	snd_alias_list_t *projExplosionSound;                   // +0x738
	snd_alias_list_t *projDudSound;                         // +0x740
	WeapStickinessType stickiness;                          // +0x748
	float lowAmmoWarningThreshold;                          // +0x74C
	float ricochetChance;                                   // +0x750
	bool riotShieldEnableDamage;                            // +0x754
	int riotShieldHealth;                                   // +0x758
	float riotShieldDamageMult;                             // +0x75C
	float *parallelBounce;                                  // +0x760
	float *perpendicularBounce;                             // +0x768
	FxEffectDef *projTrailEffect;                           // +0x770
	FxEffectDef *projBeaconEffect;                          // +0x778
	float vProjectileColor[3];                              // +0x780
	guidedMissileType_t guidedMissileType;                  // +0x78C
	float maxSteeringAccel;                                 // +0x790
	int projIgnitionDelay;                                  // +0x794
	FxEffectDef *projIgnitionEffect;                        // +0x798
	snd_alias_list_t *projIgnitionSound;                    // +0x7A0
	float fAdsAimPitch;                                     // +0x7A8
	float fAdsCrosshairInFrac;                              // +0x7AC
	float fAdsCrosshairOutFrac;                             // +0x7B0
	bool adsShouldShowCrosshair;                            // +0x7B4
	int adsGunKickReducedKickBullets;                       // +0x7B8
	float adsGunKickReducedKickPercent;                     // +0x7BC
	float fAdsGunKickPitchMin;                              // +0x7C0
	float fAdsGunKickPitchMax;                              // +0x7C4
	float fAdsGunKickYawMin;                                // +0x7C8
	float fAdsGunKickYawMax;                                // +0x7CC
	float fAdsGunKickMagMin;                                // +0x7D0
	float fAdsGunKickAccel;                                 // +0x7D4
	float fAdsGunKickSpeedMax;                              // +0x7D8
	float fAdsGunKickSpeedDecay;                            // +0x7DC
	float fAdsGunKickStaticDecay;                           // +0x7E0
	float fAdsViewKickPitchMin;                             // +0x7E4
	float fAdsViewKickPitchMax;                             // +0x7E8
	float fAdsViewKickYawMin;                               // +0x7EC
	float fAdsViewKickYawMax;                               // +0x7F0
	float fAdsViewKickMagMin;                               // +0x7F4
	float fAdsViewScatterMin;                               // +0x7F8
	float fAdsViewScatterMax;                               // +0x7FC
	float fAdsSpread;                                       // +0x800
	int hipGunKickReducedKickBullets;                       // +0x804
	float hipGunKickReducedKickPercent;                     // +0x808
	float fHipGunKickPitchMin;                              // +0x80C
	float fHipGunKickPitchMax;                              // +0x810
	float fHipGunKickYawMin;                                // +0x814
	float fHipGunKickYawMax;                                // +0x818
	float fHipGunKickMagMin;                                // +0x81C
	float fHipGunKickAccel;                                 // +0x820
	float fHipGunKickSpeedMax;                              // +0x824
	float fHipGunKickSpeedDecay;                            // +0x828
	float fHipGunKickStaticDecay;                           // +0x82C
	float fHipViewKickPitchMin;                             // +0x830
	float fHipViewKickPitchMax;                             // +0x834
	float fHipViewKickYawMin;                               // +0x838
	float fHipViewKickYawMax;                               // +0x83C
	float fHipViewKickMagMin;                               // +0x840
	float fHipViewScatterMin;                               // +0x844
	float fHipViewScatterMax;                               // +0x848
	float fightDist;                                        // +0x84C
	float maxDist;                                          // +0x850
	const char *accuracyGraphName[2];                       // +0x858
	vec2_t *originalAccuracyGraphKnots[2];                  // +0x868
	unsigned short originalAccuracyGraphKnotCount[2];       // +0x878
	int iPositionReloadTransTime;                           // +0x87C
	float leftArc;                                          // +0x880
	float rightArc;                                         // +0x884
	float topArc;                                           // +0x888
	float bottomArc;                                        // +0x88C
	float accuracy;                                         // +0x890
	float aiSpread;                                         // +0x894
	float playerSpread;                                     // +0x898
	float minTurnSpeed[2];                                  // +0x89C
	float maxTurnSpeed[2];                                  // +0x8A4
	float pitchConvergenceTime;                             // +0x8AC
	float yawConvergenceTime;                               // +0x8B0
	float suppressTime;                                     // +0x8B4
	float maxRange;                                         // +0x8B8
	float fAnimHorRotateInc;                                // +0x8BC
	float fPlayerPositionDist;                              // +0x8C0
	const char *szUseHintString;                            // +0x8C8
	const char *dropHintString;                             // +0x8D0
	unsigned int iUseHintStringIndex;                       // +0x8D8
	unsigned int dropHintStringIndex;                       // +0x8DC
	float horizViewJitter;                                  // +0x8E0
	float vertViewJitter;                                   // +0x8E4
	float scanSpeed;                                        // +0x8E8
	float scanAccel;                                        // +0x8EC
	int scanPauseTime;                                      // +0x8F0
	const char *szScript;                                   // +0x8F8
	float fOOPosAnimLength[2];                              // +0x900
	int minDamage;                                          // +0x908
	int minPlayerDamage;                                    // +0x90C
	float fMaxDamageRange;                                  // +0x910
	float fMinDamageRange;                                  // +0x914
	float destabilizationRateTime;                          // +0x918
	float destabilizationCurvatureMax;                      // +0x91C
	int destabilizeDistance;                                // +0x920
	float *locationDamageMultipliers;                       // +0x928
	const char *fireRumble;                                 // +0x930
	const char *meleeImpactRumble;                          // +0x938
	TracerDef *tracerType;                                  // +0x940
	bool turretADSEnabled;                                  // +0x948
	float turretADSTime;                                    // +0x94C
	float turretFov;                                        // +0x950
	float turretFovADS;                                     // +0x954
	float turretScopeZoomRate;                              // +0x958
	float turretScopeZoomMin;                               // +0x95C
	float turretScopeZoomMax;                               // +0x960
	float turretOverheatUpRate;                             // +0x964
	float turretOverheatDownRate;                           // +0x968
	float turretOverheatPenalty;                            // +0x96C
	snd_alias_list_t *turretOverheatSound;                  // +0x970
	FxEffectDef *turretOverheatEffect;                      // +0x978
	const char *turretBarrelSpinRumble;                     // +0x980
	float turretBarrelSpinSpeed;                            // +0x988
	float turretBarrelSpinUpTime;                           // +0x98C
	float turretBarrelSpinDownTime;                         // +0x990
	snd_alias_list_t *turretBarrelSpinMaxSnd;               // +0x998
	snd_alias_list_t *turretBarrelSpinUpSnd[4];             // +0x9A0
	snd_alias_list_t *turretBarrelSpinDownSnd[4];           // +0x9C0
	snd_alias_list_t *missileConeSoundAlias;                // +0x9E0
	snd_alias_list_t *missileConeSoundAliasAtBase;          // +0x9E8
	float missileConeSoundRadiusAtTop;                      // +0x9F0
	float missileConeSoundRadiusAtBase;                     // +0x9F4
	float missileConeSoundHeight;                           // +0x9F8
	float missileConeSoundOriginOffset;                     // +0x9FC
	float missileConeSoundVolumescaleAtCore;                // +0xA00
	float missileConeSoundVolumescaleAtEdge;                // +0xA04
	float missileConeSoundVolumescaleCoreSize;              // +0xA08
	float missileConeSoundPitchAtTop;                       // +0xA0C
	float missileConeSoundPitchAtBottom;                    // +0xA10
	float missileConeSoundPitchTopSize;                     // +0xA14
	float missileConeSoundPitchBottomSize;                  // +0xA18
	float missileConeSoundCrossfadeTopSize;                 // +0xA1C
	float missileConeSoundCrossfadeBottomSize;              // +0xA20
	scr_string_t knifeAttachTagOverride;                    // +0xA24
	bool knifeAlwaysAttached;                               // +0xA28
	bool meleeOverrideValues;                               // +0xA29
	float aim_automelee_lerp;                               // +0xA2C
	float aim_automelee_range;                              // +0xA30
	float aim_automelee_region_height;                      // +0xA34
	float aim_automelee_region_width;                       // +0xA38
	float player_meleeHeight;                               // +0xA3C
	float player_meleeRange;                                // +0xA40
	float player_meleeWidth;                                // +0xA44
	bool sharedAmmo;                                        // +0xA48
	bool lockonSupported;                                   // +0xA49
	bool requireLockonToFire;                               // +0xA4A
	bool isAirburstWeapon;                                  // +0xA4B
	bool bigExplosion;                                      // +0xA4C
	bool noAdsWhenMagEmpty;                                 // +0xA4D
	bool avoidDropCleanup;                                  // +0xA4E
	bool inheritsPerks;                                     // +0xA4F
	bool crosshairColorChange;                              // +0xA50
	bool bRifleBullet;                                      // +0xA51
	bool armorPiercing;                                     // +0xA52
	bool bBoltAction;                                       // +0xA53
	bool aimDownSight;                                      // +0xA54
	bool canHoldBreath;                                     // +0xA55
	bool meleeOnly;                                         // +0xA56
	bool canVariableZoom;                                   // +0xA57
	bool bRechamberWhileAds;                                // +0xA58
	bool bBulletExplosiveDamage;                            // +0xA59
	bool bCookOffHold;                                      // +0xA5A
	bool reticleSpin45;                                     // +0xA5B
	bool bClipOnly;                                         // +0xA5C
	bool noAmmoPickup;                                      // +0xA5D
	bool adsFireOnly;                                       // +0xA5E
	bool cancelAutoHolsterWhenEmpty;                        // +0xA5F
	bool disableSwitchToWhenEmpty;                          // +0xA60
	bool suppressAmmoReserveDisplay;                        // +0xA61
	bool laserSightDuringNightvision;                       // +0xA62
	bool markableViewmodel;                                 // +0xA63
	bool noDualWield;                                       // +0xA64
	bool flipKillIcon;                                      // +0xA65
	bool bNoPartialReload;                                  // +0xA66
	bool bSegmentedReload;                                  // +0xA67
	bool bMultipleReload;                                   // +0xA68
	bool blocksProne;                                       // +0xA69
	bool silenced;                                          // +0xA6A
	bool isRollingGrenade;                                  // +0xA6B
	bool projExplosionEffectForceNormalUp;                  // +0xA6C
	bool projExplosionEffectInheritParentDirection;         // +0xA6D
	bool bProjImpactExplode;                                // +0xA6E
	bool bProjTrajectoryEvents;                             // +0xA6F
	bool bProjWhizByEnabled;                                // +0xA70
	bool stickToPlayers;                                    // +0xA71
	bool stickToVehicles;                                   // +0xA72
	bool stickToTurrets;                                    // +0xA73
	bool thrownSideways;                                    // +0xA74
	bool hasDetonator;                                      // +0xA75
	bool disableFiring;                                     // +0xA76
	bool timedDetonation;                                   // +0xA77
	bool rotate;                                            // +0xA78
	bool holdButtonToThrow;                                 // +0xA79
	bool freezeMovementWhenFiring;                          // +0xA7A
	bool thermalScope;                                      // +0xA7B
	bool thermalToggle;                                     // +0xA7C
	bool outlineEnemies;                                    // +0xA7D
	bool altModeSameWeapon;                                 // +0xA7E
	bool turretBarrelSpinEnabled;                           // +0xA7F
	bool missileConeSoundEnabled;                           // +0xA80
	bool missileConeSoundPitchshiftEnabled;                 // +0xA81
	bool missileConeSoundCrossfadeEnabled;                  // +0xA82
	bool offhandHoldIsCancelable;                           // +0xA83
	bool doNotAllowAttachmentsToOverrideSpread;             // +0xA84
	bool useFastReloadAnims;                                // +0xA85
	bool useScopeDrift;                                     // +0xA86
	bool alwaysShatterGlassOnImpact;                        // +0xA87
	bool oldWeapon;                                         // +0xA88
	scr_string_t stowTag;                                   // +0xA8C
	XModel *stowOffsetModel;                                // +0xA90
};
static_assert(sizeof(WeaponDef) == 0xA98, "WeaponDef");
static_assert(offsetof(WeaponDef, szOverlayName) == 0x0, "WeaponDef::szOverlayName");
static_assert(offsetof(WeaponDef, gunXModel) == 0x8, "WeaponDef::gunXModel");
static_assert(offsetof(WeaponDef, handXModel) == 0x10, "WeaponDef::handXModel");
static_assert(offsetof(WeaponDef, camoWorldModel) == 0x18, "WeaponDef::camoWorldModel");
static_assert(offsetof(WeaponDef, camoViewModel) == 0x20, "WeaponDef::camoViewModel");
static_assert(offsetof(WeaponDef, camoWorldModelMaterialOverride) == 0x28, "WeaponDef::camoWorldModelMaterialOverride");
static_assert(offsetof(WeaponDef, camoViewModelMaterialOverride) == 0x30, "WeaponDef::camoViewModelMaterialOverride");
static_assert(offsetof(WeaponDef, camoMaterialTarget) == 0x38, "WeaponDef::camoMaterialTarget");
static_assert(offsetof(WeaponDef, szXAnimsRightHanded) == 0x40, "WeaponDef::szXAnimsRightHanded");
static_assert(offsetof(WeaponDef, szXAnimsLeftHanded) == 0x48, "WeaponDef::szXAnimsLeftHanded");
static_assert(offsetof(WeaponDef, szModeName) == 0x50, "WeaponDef::szModeName");
static_assert(offsetof(WeaponDef, notetrackSoundMapKeys) == 0x58, "WeaponDef::notetrackSoundMapKeys");
static_assert(offsetof(WeaponDef, notetrackSoundMapValues) == 0x60, "WeaponDef::notetrackSoundMapValues");
static_assert(offsetof(WeaponDef, notetrackRumbleMapKeys) == 0x68, "WeaponDef::notetrackRumbleMapKeys");
static_assert(offsetof(WeaponDef, notetrackRumbleMapValues) == 0x70, "WeaponDef::notetrackRumbleMapValues");
static_assert(offsetof(WeaponDef, notetrackFXMapKeys) == 0x78, "WeaponDef::notetrackFXMapKeys");
static_assert(offsetof(WeaponDef, notetrackFXMapValues) == 0x80, "WeaponDef::notetrackFXMapValues");
static_assert(offsetof(WeaponDef, notetrackFXMapTagValues) == 0x88, "WeaponDef::notetrackFXMapTagValues");
static_assert(offsetof(WeaponDef, viewFlashEffect) == 0xB8, "WeaponDef::viewFlashEffect");
static_assert(offsetof(WeaponDef, worldFlashEffect) == 0xC0, "WeaponDef::worldFlashEffect");
static_assert(offsetof(WeaponDef, viewFlashADSEffect) == 0xC8, "WeaponDef::viewFlashADSEffect");
static_assert(offsetof(WeaponDef, pickupSound) == 0xD0, "WeaponDef::pickupSound");
static_assert(offsetof(WeaponDef, pickupSoundPlayer) == 0xD8, "WeaponDef::pickupSoundPlayer");
static_assert(offsetof(WeaponDef, ammoPickupSound) == 0xE0, "WeaponDef::ammoPickupSound");
static_assert(offsetof(WeaponDef, ammoPickupSoundPlayer) == 0xE8, "WeaponDef::ammoPickupSoundPlayer");
static_assert(offsetof(WeaponDef, projectileSound) == 0xF0, "WeaponDef::projectileSound");
static_assert(offsetof(WeaponDef, pullbackSound) == 0xF8, "WeaponDef::pullbackSound");
static_assert(offsetof(WeaponDef, pullbackSoundPlayer) == 0x100, "WeaponDef::pullbackSoundPlayer");
static_assert(offsetof(WeaponDef, fireSound) == 0x108, "WeaponDef::fireSound");
static_assert(offsetof(WeaponDef, fireSoundPlayer) == 0x110, "WeaponDef::fireSoundPlayer");
static_assert(offsetof(WeaponDef, fireSoundPlayerAkimbo) == 0x118, "WeaponDef::fireSoundPlayerAkimbo");
static_assert(offsetof(WeaponDef, fireLoopSound) == 0x120, "WeaponDef::fireLoopSound");
static_assert(offsetof(WeaponDef, fireLoopSoundPlayer) == 0x128, "WeaponDef::fireLoopSoundPlayer");
static_assert(offsetof(WeaponDef, fireStopSound) == 0x130, "WeaponDef::fireStopSound");
static_assert(offsetof(WeaponDef, fireStopSoundPlayer) == 0x138, "WeaponDef::fireStopSoundPlayer");
static_assert(offsetof(WeaponDef, fireLastSound) == 0x140, "WeaponDef::fireLastSound");
static_assert(offsetof(WeaponDef, fireLastSoundPlayer) == 0x148, "WeaponDef::fireLastSoundPlayer");
static_assert(offsetof(WeaponDef, emptyFireSound) == 0x150, "WeaponDef::emptyFireSound");
static_assert(offsetof(WeaponDef, emptyFireSoundPlayer) == 0x158, "WeaponDef::emptyFireSoundPlayer");
static_assert(offsetof(WeaponDef, meleeSwipeSound) == 0x160, "WeaponDef::meleeSwipeSound");
static_assert(offsetof(WeaponDef, meleeSwipeSoundPlayer) == 0x168, "WeaponDef::meleeSwipeSoundPlayer");
static_assert(offsetof(WeaponDef, meleeHitSound) == 0x170, "WeaponDef::meleeHitSound");
static_assert(offsetof(WeaponDef, meleeMissSound) == 0x178, "WeaponDef::meleeMissSound");
static_assert(offsetof(WeaponDef, rechamberSound) == 0x180, "WeaponDef::rechamberSound");
static_assert(offsetof(WeaponDef, rechamberSoundPlayer) == 0x188, "WeaponDef::rechamberSoundPlayer");
static_assert(offsetof(WeaponDef, reloadSound) == 0x190, "WeaponDef::reloadSound");
static_assert(offsetof(WeaponDef, reloadSoundPlayer) == 0x198, "WeaponDef::reloadSoundPlayer");
static_assert(offsetof(WeaponDef, reloadEmptySound) == 0x1A0, "WeaponDef::reloadEmptySound");
static_assert(offsetof(WeaponDef, reloadEmptySoundPlayer) == 0x1A8, "WeaponDef::reloadEmptySoundPlayer");
static_assert(offsetof(WeaponDef, reloadStartSound) == 0x1B0, "WeaponDef::reloadStartSound");
static_assert(offsetof(WeaponDef, reloadStartSoundPlayer) == 0x1B8, "WeaponDef::reloadStartSoundPlayer");
static_assert(offsetof(WeaponDef, reloadEndSound) == 0x1C0, "WeaponDef::reloadEndSound");
static_assert(offsetof(WeaponDef, reloadEndSoundPlayer) == 0x1C8, "WeaponDef::reloadEndSoundPlayer");
static_assert(offsetof(WeaponDef, detonateSound) == 0x1D0, "WeaponDef::detonateSound");
static_assert(offsetof(WeaponDef, detonateSoundPlayer) == 0x1D8, "WeaponDef::detonateSoundPlayer");
static_assert(offsetof(WeaponDef, nightVisionWearSound) == 0x1E0, "WeaponDef::nightVisionWearSound");
static_assert(offsetof(WeaponDef, nightVisionWearSoundPlayer) == 0x1E8, "WeaponDef::nightVisionWearSoundPlayer");
static_assert(offsetof(WeaponDef, nightVisionRemoveSound) == 0x1F0, "WeaponDef::nightVisionRemoveSound");
static_assert(offsetof(WeaponDef, nightVisionRemoveSoundPlayer) == 0x1F8, "WeaponDef::nightVisionRemoveSoundPlayer");
static_assert(offsetof(WeaponDef, altSwitchSound) == 0x200, "WeaponDef::altSwitchSound");
static_assert(offsetof(WeaponDef, altSwitchSoundPlayer) == 0x208, "WeaponDef::altSwitchSoundPlayer");
static_assert(offsetof(WeaponDef, raiseSound) == 0x210, "WeaponDef::raiseSound");
static_assert(offsetof(WeaponDef, raiseSoundPlayer) == 0x218, "WeaponDef::raiseSoundPlayer");
static_assert(offsetof(WeaponDef, firstRaiseSound) == 0x220, "WeaponDef::firstRaiseSound");
static_assert(offsetof(WeaponDef, firstRaiseSoundPlayer) == 0x228, "WeaponDef::firstRaiseSoundPlayer");
static_assert(offsetof(WeaponDef, putawaySound) == 0x230, "WeaponDef::putawaySound");
static_assert(offsetof(WeaponDef, putawaySoundPlayer) == 0x238, "WeaponDef::putawaySoundPlayer");
static_assert(offsetof(WeaponDef, scanSound) == 0x240, "WeaponDef::scanSound");
static_assert(offsetof(WeaponDef, changeVariableZoomSound) == 0x248, "WeaponDef::changeVariableZoomSound");
static_assert(offsetof(WeaponDef, bounceSound) == 0x250, "WeaponDef::bounceSound");
static_assert(offsetof(WeaponDef, rollingSound) == 0x258, "WeaponDef::rollingSound");
static_assert(offsetof(WeaponDef, viewShellEjectEffect) == 0x260, "WeaponDef::viewShellEjectEffect");
static_assert(offsetof(WeaponDef, worldShellEjectEffect) == 0x268, "WeaponDef::worldShellEjectEffect");
static_assert(offsetof(WeaponDef, viewLastShotEjectEffect) == 0x270, "WeaponDef::viewLastShotEjectEffect");
static_assert(offsetof(WeaponDef, worldLastShotEjectEffect) == 0x278, "WeaponDef::worldLastShotEjectEffect");
static_assert(offsetof(WeaponDef, viewMagEjectEffect) == 0x280, "WeaponDef::viewMagEjectEffect");
static_assert(offsetof(WeaponDef, reticleCenter) == 0x288, "WeaponDef::reticleCenter");
static_assert(offsetof(WeaponDef, reticleSide) == 0x290, "WeaponDef::reticleSide");
static_assert(offsetof(WeaponDef, worldModel) == 0x348, "WeaponDef::worldModel");
static_assert(offsetof(WeaponDef, worldClipModel) == 0x350, "WeaponDef::worldClipModel");
static_assert(offsetof(WeaponDef, rocketModel) == 0x358, "WeaponDef::rocketModel");
static_assert(offsetof(WeaponDef, knifeModel) == 0x360, "WeaponDef::knifeModel");
static_assert(offsetof(WeaponDef, worldKnifeModel) == 0x368, "WeaponDef::worldKnifeModel");
static_assert(offsetof(WeaponDef, hudIcon) == 0x370, "WeaponDef::hudIcon");
static_assert(offsetof(WeaponDef, pickupIcon) == 0x380, "WeaponDef::pickupIcon");
static_assert(offsetof(WeaponDef, ammoCounterIcon) == 0x390, "WeaponDef::ammoCounterIcon");
static_assert(offsetof(WeaponDef, szAmmoName) == 0x3A8, "WeaponDef::szAmmoName");
static_assert(offsetof(WeaponDef, szClipName) == 0x3B8, "WeaponDef::szClipName");
static_assert(offsetof(WeaponDef, szSharedAmmoCapName) == 0x3D0, "WeaponDef::szSharedAmmoCapName");
static_assert(offsetof(WeaponDef, physCollmap) == 0x698, "WeaponDef::physCollmap");
static_assert(offsetof(WeaponDef, projectileName) == 0x710, "WeaponDef::projectileName");
static_assert(offsetof(WeaponDef, projectileModel) == 0x718, "WeaponDef::projectileModel");
static_assert(offsetof(WeaponDef, projExplosionEffect) == 0x728, "WeaponDef::projExplosionEffect");
static_assert(offsetof(WeaponDef, projDudEffect) == 0x730, "WeaponDef::projDudEffect");
static_assert(offsetof(WeaponDef, projExplosionSound) == 0x738, "WeaponDef::projExplosionSound");
static_assert(offsetof(WeaponDef, projDudSound) == 0x740, "WeaponDef::projDudSound");
static_assert(offsetof(WeaponDef, parallelBounce) == 0x760, "WeaponDef::parallelBounce");
static_assert(offsetof(WeaponDef, perpendicularBounce) == 0x768, "WeaponDef::perpendicularBounce");
static_assert(offsetof(WeaponDef, projTrailEffect) == 0x770, "WeaponDef::projTrailEffect");
static_assert(offsetof(WeaponDef, projBeaconEffect) == 0x778, "WeaponDef::projBeaconEffect");
static_assert(offsetof(WeaponDef, projIgnitionEffect) == 0x798, "WeaponDef::projIgnitionEffect");
static_assert(offsetof(WeaponDef, projIgnitionSound) == 0x7A0, "WeaponDef::projIgnitionSound");
static_assert(offsetof(WeaponDef, accuracyGraphName) == 0x858, "WeaponDef::accuracyGraphName");
static_assert(offsetof(WeaponDef, originalAccuracyGraphKnots) == 0x868, "WeaponDef::originalAccuracyGraphKnots");
static_assert(offsetof(WeaponDef, szUseHintString) == 0x8C8, "WeaponDef::szUseHintString");
static_assert(offsetof(WeaponDef, dropHintString) == 0x8D0, "WeaponDef::dropHintString");
static_assert(offsetof(WeaponDef, szScript) == 0x8F8, "WeaponDef::szScript");
static_assert(offsetof(WeaponDef, locationDamageMultipliers) == 0x928, "WeaponDef::locationDamageMultipliers");
static_assert(offsetof(WeaponDef, fireRumble) == 0x930, "WeaponDef::fireRumble");
static_assert(offsetof(WeaponDef, meleeImpactRumble) == 0x938, "WeaponDef::meleeImpactRumble");
static_assert(offsetof(WeaponDef, tracerType) == 0x940, "WeaponDef::tracerType");
static_assert(offsetof(WeaponDef, turretOverheatSound) == 0x970, "WeaponDef::turretOverheatSound");
static_assert(offsetof(WeaponDef, turretOverheatEffect) == 0x978, "WeaponDef::turretOverheatEffect");
static_assert(offsetof(WeaponDef, turretBarrelSpinRumble) == 0x980, "WeaponDef::turretBarrelSpinRumble");
static_assert(offsetof(WeaponDef, turretBarrelSpinMaxSnd) == 0x998, "WeaponDef::turretBarrelSpinMaxSnd");
static_assert(offsetof(WeaponDef, turretBarrelSpinUpSnd) == 0x9A0, "WeaponDef::turretBarrelSpinUpSnd");
static_assert(offsetof(WeaponDef, turretBarrelSpinDownSnd) == 0x9C0, "WeaponDef::turretBarrelSpinDownSnd");
static_assert(offsetof(WeaponDef, missileConeSoundAlias) == 0x9E0, "WeaponDef::missileConeSoundAlias");
static_assert(offsetof(WeaponDef, missileConeSoundAliasAtBase) == 0x9E8, "WeaponDef::missileConeSoundAliasAtBase");
static_assert(offsetof(WeaponDef, stowOffsetModel) == 0xA90, "WeaponDef::stowOffsetModel");

struct WeaponAttachment
{
	const char *szInternalName;                             // +0x000
	const char *szDisplayName;                              // +0x008
	AttachmentType type;                                    // +0x010
	weapType_t weaponType;                                  // +0x014
	weapClass_t weapClass;                                  // +0x018
	XModel **worldModels;                                   // +0x020
	XModel **viewModels;                                    // +0x028
	XModel **reticleViewModels;                             // +0x030
	AttAmmoGeneral *ammogeneral;                            // +0x038
	AttSight *sight;                                        // +0x040
	AttReload *reload;                                      // +0x048
	AttAddOns *addOns;                                      // +0x050
	AttGeneral *general;                                    // +0x058
	AttAimAssist *aimAssist;                                // +0x060
	AttAmmunition *ammunition;                              // +0x068
	AttDamage *damage;                                      // +0x070
	AttLocationDamage *locationDamage;                      // +0x078
	AttIdleSettings *idleSettings;                          // +0x080
	AttADSSettings *adsSettings;                            // +0x088
	AttADSSettings *adsSettingsMain;                        // +0x090
	AttScopeDriftSettings *scopeDriftSettings;              // +0x098
	AttScopeDriftSettings *scopeDriftSettingsMain;          // +0x0A0
	AttHipSpread *hipSpread;                                // +0x0A8
	AttGunKick *gunKick;                                    // +0x0B0
	AttViewKick *viewKick;                                  // +0x0B8
	AttADSOverlay *adsOverlay;                              // +0x0C0
	AttUI *ui;                                              // +0x0C8
	AttRumbles *rumbles;                                    // +0x0D0
	AttProjectile *projectile;                              // +0x0D8
	float ammunitionScale;                                  // +0x0E0
	float damageScale;                                      // +0x0E4
	float damageScaleMin;                                   // +0x0E8
	float stateTimersScale;                                 // +0x0EC
	float fireTimersScale;                                  // +0x0F0
	float idleSettingsScale;                                // +0x0F4
	float adsSettingsScale;                                 // +0x0F8
	float adsSettingsScaleMain;                             // +0x0FC
	float hipSpreadScale;                                   // +0x100
	float gunKickScale;                                     // +0x104
	float viewKickScale;                                    // +0x108
	float viewCenterScale;                                  // +0x10C
	int loadIndex;                                          // +0x110
	bool hideIronSightsWithThisAttachment;                  // +0x114
	bool shareAmmoWithAlt;                                  // +0x115
};
static_assert(sizeof(WeaponAttachment) == 0x118, "WeaponAttachment");
static_assert(offsetof(WeaponAttachment, szInternalName) == 0x0, "WeaponAttachment::szInternalName");
static_assert(offsetof(WeaponAttachment, szDisplayName) == 0x8, "WeaponAttachment::szDisplayName");
static_assert(offsetof(WeaponAttachment, worldModels) == 0x20, "WeaponAttachment::worldModels");
static_assert(offsetof(WeaponAttachment, viewModels) == 0x28, "WeaponAttachment::viewModels");
static_assert(offsetof(WeaponAttachment, reticleViewModels) == 0x30, "WeaponAttachment::reticleViewModels");
static_assert(offsetof(WeaponAttachment, ammogeneral) == 0x38, "WeaponAttachment::ammogeneral");
static_assert(offsetof(WeaponAttachment, sight) == 0x40, "WeaponAttachment::sight");
static_assert(offsetof(WeaponAttachment, reload) == 0x48, "WeaponAttachment::reload");
static_assert(offsetof(WeaponAttachment, addOns) == 0x50, "WeaponAttachment::addOns");
static_assert(offsetof(WeaponAttachment, general) == 0x58, "WeaponAttachment::general");
static_assert(offsetof(WeaponAttachment, aimAssist) == 0x60, "WeaponAttachment::aimAssist");
static_assert(offsetof(WeaponAttachment, ammunition) == 0x68, "WeaponAttachment::ammunition");
static_assert(offsetof(WeaponAttachment, damage) == 0x70, "WeaponAttachment::damage");
static_assert(offsetof(WeaponAttachment, locationDamage) == 0x78, "WeaponAttachment::locationDamage");
static_assert(offsetof(WeaponAttachment, idleSettings) == 0x80, "WeaponAttachment::idleSettings");
static_assert(offsetof(WeaponAttachment, adsSettings) == 0x88, "WeaponAttachment::adsSettings");
static_assert(offsetof(WeaponAttachment, adsSettingsMain) == 0x90, "WeaponAttachment::adsSettingsMain");
static_assert(offsetof(WeaponAttachment, scopeDriftSettings) == 0x98, "WeaponAttachment::scopeDriftSettings");
static_assert(offsetof(WeaponAttachment, scopeDriftSettingsMain) == 0xA0, "WeaponAttachment::scopeDriftSettingsMain");
static_assert(offsetof(WeaponAttachment, hipSpread) == 0xA8, "WeaponAttachment::hipSpread");
static_assert(offsetof(WeaponAttachment, gunKick) == 0xB0, "WeaponAttachment::gunKick");
static_assert(offsetof(WeaponAttachment, viewKick) == 0xB8, "WeaponAttachment::viewKick");
static_assert(offsetof(WeaponAttachment, adsOverlay) == 0xC0, "WeaponAttachment::adsOverlay");
static_assert(offsetof(WeaponAttachment, ui) == 0xC8, "WeaponAttachment::ui");
static_assert(offsetof(WeaponAttachment, rumbles) == 0xD0, "WeaponAttachment::rumbles");
static_assert(offsetof(WeaponAttachment, projectile) == 0xD8, "WeaponAttachment::projectile");

struct VehiclePhysDef
{
	int physicsEnabled;                                     // +0x000
	const char *physPresetName;                             // +0x008
	PhysPreset *physPreset;                                 // +0x010
	const char *accelGraphName;                             // +0x018
	VehicleAxleType steeringAxle;                           // +0x020
	VehicleAxleType powerAxle;                              // +0x024
	VehicleAxleType brakingAxle;                            // +0x028
	float topSpeed;                                         // +0x02C
	float reverseSpeed;                                     // +0x030
	float maxVelocity;                                      // +0x034
	float maxPitch;                                         // +0x038
	float maxRoll;                                          // +0x03C
	float suspensionTravelFront;                            // +0x040
	float suspensionTravelRear;                             // +0x044
	float suspensionStrengthFront;                          // +0x048
	float suspensionDampingFront;                           // +0x04C
	float suspensionStrengthRear;                           // +0x050
	float suspensionDampingRear;                            // +0x054
	float frictionBraking;                                  // +0x058
	float frictionCoasting;                                 // +0x05C
	float frictionTopSpeed;                                 // +0x060
	float frictionSide;                                     // +0x064
	float frictionSideRear;                                 // +0x068
	float velocityDependentSlip;                            // +0x06C
	float rollStability;                                    // +0x070
	float rollResistance;                                   // +0x074
	float pitchResistance;                                  // +0x078
	float yawResistance;                                    // +0x07C
	float uprightStrengthPitch;                             // +0x080
	float uprightStrengthRoll;                              // +0x084
	float targetAirPitch;                                   // +0x088
	float airYawTorque;                                     // +0x08C
	float airPitchTorque;                                   // +0x090
	float minimumMomentumForCollision;                      // +0x094
	float collisionLaunchForceScale;                        // +0x098
	float wreckedMassScale;                                 // +0x09C
	float wreckedBodyFriction;                              // +0x0A0
	float minimumJoltForNotify;                             // +0x0A4
	float slipThresholdFront;                               // +0x0A8
	float slipThresholdRear;                                // +0x0AC
	float slipFricScaleFront;                               // +0x0B0
	float slipFricScaleRear;                                // +0x0B4
	float slipFricRateFront;                                // +0x0B8
	float slipFricRateRear;                                 // +0x0BC
	float slipYawTorque;                                    // +0x0C0
};
static_assert(sizeof(VehiclePhysDef) == 0xC8, "VehiclePhysDef");
static_assert(offsetof(VehiclePhysDef, physPresetName) == 0x8, "VehiclePhysDef::physPresetName");
static_assert(offsetof(VehiclePhysDef, physPreset) == 0x10, "VehiclePhysDef::physPreset");
static_assert(offsetof(VehiclePhysDef, accelGraphName) == 0x18, "VehiclePhysDef::accelGraphName");

struct VehicleDef
{
	const char *name;                                       // +0x000
	VehicleType type;                                       // +0x008
	const char *useHintString;                              // +0x010
	int health;                                             // +0x018
	int quadBarrel;                                         // +0x01C
	int hitClientScriptables;                               // +0x020
	float texScrollScale;                                   // +0x024
	float topSpeed;                                         // +0x028
	float accel;                                            // +0x02C
	float rotRate;                                          // +0x030
	float rotAccel;                                         // +0x034
	float maxBodyPitch;                                     // +0x038
	float maxBodyRoll;                                      // +0x03C
	float fakeBodyAccelPitch;                               // +0x040
	float fakeBodyAccelRoll;                                // +0x044
	float fakeBodyVelPitch;                                 // +0x048
	float fakeBodyVelRoll;                                  // +0x04C
	float fakeBodySideVelPitch;                             // +0x050
	float fakeBodyPitchStrength;                            // +0x054
	float fakeBodyRollStrength;                             // +0x058
	float fakeBodyPitchDampening;                           // +0x05C
	float fakeBodyRollDampening;                            // +0x060
	float fakeBodyBoatRockingAmplitude;                     // +0x064
	float fakeBodyBoatRockingPeriod;                        // +0x068
	float fakeBodyBoatRockingRotationPeriod;                // +0x06C
	float fakeBodyBoatRockingFadeoutSpeed;                  // +0x070
	float boatBouncingMinForce;                             // +0x074
	float boatBouncingMaxForce;                             // +0x078
	float boatBouncingRate;                                 // +0x07C
	float boatBouncingFadeinSpeed;                          // +0x080
	float boatBouncingFadeoutSteeringAngle;                 // +0x084
	float collisionDamage;                                  // +0x088
	float collisionSpeed;                                   // +0x08C
	float killcamOffset[3];                                 // +0x090
	int playerProtected;                                    // +0x09C
	int bulletDamage;                                       // +0x0A0
	int armorPiercingDamage;                                // +0x0A4
	int grenadeDamage;                                      // +0x0A8
	int projectileDamage;                                   // +0x0AC
	int projectileSplashDamage;                             // +0x0B0
	int heavyExplosiveDamage;                               // +0x0B4
	VehiclePhysDef vehPhysDef;                              // +0x0B8
	float boostDuration;                                    // +0x180
	float boostRechargeTime;                                // +0x184
	float boostAcceleration;                                // +0x188
	float suspensionTravel;                                 // +0x18C
	float maxSteeringAngle;                                 // +0x190
	float steeringLerp;                                     // +0x194
	float minSteeringScale;                                 // +0x198
	float minSteeringSpeed;                                 // +0x19C
	int disableWheelsTurning;                               // +0x1A0
	int vehHelicopterIsASplinePlane;                        // +0x1A4
	int vehHelicopterLockAltitude;                          // +0x1A8
	int vehHelicopterOffsetFromMesh;                        // +0x1AC
	float vehHelicopterAltitudeOffset;                      // +0x1B0
	float vehHelicopterPitchOffset;                         // +0x1B4
	float vehHelicopterBoundsRadius;                        // +0x1B8
	float vehHelicopterMaxSpeed;                            // +0x1BC
	float vehHelicopterMaxSpeedVertical;                    // +0x1C0
	float vehHelicopterMaxAccel;                            // +0x1C4
	float vehHelicopterMaxAccelVertical;                    // +0x1C8
	float vehHelicopterDecelerationFwd;                     // +0x1CC
	float vehHelicopterDecelerationSide;                    // +0x1D0
	float vehHelicopterDecelerationUp;                      // +0x1D4
	float vehHelicopterMaxYawRate;                          // +0x1D8
	float vehHelicopterMaxYawAccel;                         // +0x1DC
	float vehHelicopterTiltFromVelocity;                    // +0x1E0
	float vehHelicopterTiltFromControllerAxes;              // +0x1E4
	float vehHelicopterTiltFromAcceleration;                // +0x1E8
	float vehHelicopterTiltFromDeceleration;                // +0x1EC
	float vehHelicopterTiltFromFwdAndYaw_VelAtMaxTilt;      // +0x1F0
	float vehHelicopterTiltFromFwdAndYaw;                   // +0x1F4
	float vehHelicopterTiltMomentum;                        // +0x1F8
	float vehHelicopterTiltSpeed;                           // +0x1FC
	float vehHelicopterMaxPitch;                            // +0x200
	float vehHelicopterMaxRoll;                             // +0x204
	float vehHelicopterHoverSpeedThreshold;                 // +0x208
	float vehHelicopterJitterJerkyness;                     // +0x20C
	float vehHelicopterLookaheadTime;                       // +0x210
	int vehHelicopterSoftCollisions;                        // +0x214
	int vehHelicopterUseGroundFX;                           // +0x218
	FxEffectDef *vehHelicopterGroundFx;                     // +0x220
	FxEffectDef *vehHelicopterGroundWaterFx;                // +0x228
	float vehHelicopterGroundFxDefaultRepeatRate;           // +0x230
	float vehHelicopterGroundFxSlowestRepeatRate;           // +0x234
	float vehHelicopterGroundFxFastestRepeatRate;           // +0x238
	float vehHelicopterGroundFxMinGroundDist;               // +0x23C
	float vehHelicopterGroundFxMaxGroundDist;               // +0x240
	float vehSplinePlaneCorridorMaxXVel;                    // +0x244
	float vehSplinePlaneCorridorMaxZVel;                    // +0x248
	float vehSplinePlaneCorridorMaxXAccel;                  // +0x24C
	float vehSplinePlaneCorridorMaxZAccel;                  // +0x250
	float vehSplinePlaneTangentLookAtRate;                  // +0x254
	float vehSplinePlaneMaxPitchSpeed;                      // +0x258
	float vehSplinePlaneMaxYawSpeed;                        // +0x25C
	float vehSplinePlaneMaxRollSpeed;                       // +0x260
	float vehSplinePlanePitchSpeedRate;                     // +0x264
	float vehSplinePlaneYawSpeedRate;                       // +0x268
	float vehSplinePlaneRollSpeedRateUp;                    // +0x26C
	float vehSplinePlaneRollSpeedRateDown;                  // +0x270
	float vehSplinePlaneMaxPitchAccel;                      // +0x274
	float vehSplinePlaneMaxYawAccel;                        // +0x278
	float vehSplinePlaneMaxRollAccel;                       // +0x27C
	float vehSplinePlaneYawToRollFactor;                    // +0x280
	float vehSplinePlaneRollToYawFactor;                    // +0x284
	float vehSplinePlaneRollToYawFactorBlend;               // +0x288
	float vehSplinePlaneMaxPitch;                           // +0x28C
	float vehSplinePlaneMaxRoll;                            // +0x290
	float vehSplinePlaneMaxPitchFromRoll;                   // +0x294
	float vehSplinePlaneMaxRollYawOffset;                   // +0x298
	float vehSplinePlaneRollYawOffsetThreshold;             // +0x29C
	float vehSplinePlaneMaxTiltRoll;                        // +0x2A0
	float vehSplinePlaneMaxTiltPitch;                       // +0x2A4
	float vehSplinePlaneTiltRollRate;                       // +0x2A8
	float vehSplinePlaneTiltPitchRate;                      // +0x2AC
	int camLookEnabled;                                     // +0x2B0
	int camRelativeControl;                                 // +0x2B4
	int camRemoteDrive;                                     // +0x2B8
	float camLerp;                                          // +0x2BC
	float camHeight;                                        // +0x2C0
	float camRadius;                                        // +0x2C4
	float camPitchInfluence;                                // +0x2C8
	float camYawInfluence;                                  // +0x2CC
	float camRollInfluence;                                 // +0x2D0
	float camFovIncrease;                                   // +0x2D4
	float camFovOffset;                                     // +0x2D8
	float camFovSpeed;                                      // +0x2DC
	float camReturnSpeed;                                   // +0x2E0
	float camReturnLerp;                                    // +0x2E4
	float camVehicleAnglePitchRate;                         // +0x2E8
	float camVehicleAngleYawRate;                           // +0x2EC
	float camVehicleAngleRollRate;                          // +0x2F0
	int vehCam_UseGDT;                                      // +0x2F4
	float vehCam_anglesPitch;                               // +0x2F8
	float vehCam_anglesYaw;                                 // +0x2FC
	float vehCam_anglesRoll;                                // +0x300
	float vehCam_offsetX;                                   // +0x304
	float vehCam_offsetY;                                   // +0x308
	float vehCam_offsetZ;                                   // +0x30C
	float vehCam_radius;                                    // +0x310
	float vehCam_speedInfluence;                            // +0x314
	float vehCam_pitchTurnRate;                             // +0x318
	float vehCam_pitchClamp;                                // +0x31C
	float vehCam_yawTurnRate;                               // +0x320
	float vehCam_yawClamp;                                  // +0x324
	VehCamZOffsetMode vehCam_zOffsetMode;                   // +0x328
	float vehCam_anglesPitch3P;                             // +0x32C
	float vehCam_anglesYaw3P;                               // +0x330
	float vehCam_anglesRoll3P;                              // +0x334
	float vehCam_offsetX3P;                                 // +0x338
	float vehCam_offsetY3P;                                 // +0x33C
	float vehCam_offsetZ3P;                                 // +0x340
	float vehCam_radius3P;                                  // +0x344
	float vehCam_speedInfluence3P;                          // +0x348
	float vehCam_pitchTurnRate3P;                           // +0x34C
	float vehCam_pitchClamp3P;                              // +0x350
	float vehCam_yawTurnRate3P;                             // +0x354
	float vehCam_yawClamp3P;                                // +0x358
	VehCamZOffsetMode vehCam_zOffsetMode3P;                 // +0x35C
	const char *turretWeaponName;                           // +0x360
	WeaponCompleteDef *turretWeapon;                        // +0x368
	float turretHorizSpanLeft;                              // +0x370
	float turretHorizSpanRight;                             // +0x374
	float turretVertSpanUp;                                 // +0x378
	float turretVertSpanDown;                               // +0x37C
	float turretHorizResistLeft;                            // +0x380
	float turretHorizResistRight;                           // +0x384
	float turretVertResistUp;                               // +0x388
	float turretVertResistDown;                             // +0x38C
	float turretRotRate;                                    // +0x390
	VehicleTurretFireType turretFireType;                   // +0x394
	snd_alias_list_t *turretSpinSnd;                        // +0x398
	snd_alias_list_t *turretStopSnd;                        // +0x3A0
	int trophyEnabled;                                      // +0x3A8
	float trophyRadius;                                     // +0x3AC
	float trophyInactiveRadius;                             // +0x3B0
	int trophyAmmoCount;                                    // +0x3B4
	float trophyReloadTime;                                 // +0x3B8
	scr_string_t trophyTags[4];                             // +0x3BC
	FxEffectDef *trophyExplodeFx;                           // +0x3D0
	FxEffectDef *trophyFlashFx;                             // +0x3D8
	Material *compassFriendlyIcon;                          // +0x3E0
	Material *compassEnemyIcon;                             // +0x3E8
	Material *compassFriendlyAltIcon;                       // +0x3F0
	Material *compassEnemyAltIcon;                          // +0x3F8
	int compassIconWidth;                                   // +0x400
	int compassIconHeight;                                  // +0x404
	snd_alias_list_t *idleLowSnd;                           // +0x408
	snd_alias_list_t *idleHighSnd;                          // +0x410
	snd_alias_list_t *engineLowSnd;                         // +0x418
	snd_alias_list_t *engineHighSnd;                        // +0x420
	float engineSndSpeed;                                   // +0x428
	scr_string_t audioOriginTag;                            // +0x42C
	snd_alias_list_t *idleLowSndAlt;                        // +0x430
	snd_alias_list_t *idleHighSndAlt;                       // +0x438
	snd_alias_list_t *engineLowSndAlt;                      // +0x440
	snd_alias_list_t *engineHighSndAlt;                     // +0x448
	float engineSndSpeedAlt;                                // +0x450
	scr_string_t audioOriginTagAlt;                         // +0x454
	snd_alias_list_t *turretSpinSndAlt;                     // +0x458
	snd_alias_list_t *turretStopSndAlt;                     // +0x460
	snd_alias_list_t *engineStartUpSnd;                     // +0x468
	int engineStartUpLength;                                // +0x470
	snd_alias_list_t *engineShutdownSnd;                    // +0x478
	snd_alias_list_t *engineIdleSnd;                        // +0x480
	snd_alias_list_t *engineSustainSnd;                     // +0x488
	snd_alias_list_t *engineRampUpSnd;                      // +0x490
	int engineRampUpLength;                                 // +0x498
	snd_alias_list_t *engineRampDownSnd;                    // +0x4A0
	int engineRampDownLength;                               // +0x4A8
	snd_alias_list_t *suspensionSoftSnd;                    // +0x4B0
	float suspensionSoftCompression;                        // +0x4B8
	snd_alias_list_t *suspensionHardSnd;                    // +0x4C0
	float suspensionHardCompression;                        // +0x4C8
	snd_alias_list_t *collisionSnd;                         // +0x4D0
	float collisionBlendSpeed;                              // +0x4D8
	snd_alias_list_t *speedSnd;                             // +0x4E0
	float speedSndBlendSpeed;                               // +0x4E8
	const char *surfaceSndPrefix;                           // +0x4F0
	snd_alias_list_t *surfaceSnds[31];                      // +0x4F8
	float surfaceSndBlendSpeed;                             // +0x5F0
	float slideVolume;                                      // +0x5F4
	float slideBlendSpeed;                                  // +0x5F8
	float inAirPitch;                                       // +0x5FC
	const char *soundTriggerOverrideZone;                   // +0x600
	bool soundTriggerOverrideReverb;                        // +0x608
	bool soundTriggerOverrideMix;                           // +0x609
	bool soundTriggerOverrideFilter;                        // +0x60A
	bool soundTriggerOverrideOcclusion;                     // +0x60B
	bool soundTriggerOverrideAmbient;                       // +0x60C
	bool soundTriggerOverrideAmbientEvents;                 // +0x60D
	bool soundTriggerOverrideADSR;                          // +0x60E
};
static_assert(sizeof(VehicleDef) == 0x610, "VehicleDef");
static_assert(offsetof(VehicleDef, name) == 0x0, "VehicleDef::name");
static_assert(offsetof(VehicleDef, useHintString) == 0x10, "VehicleDef::useHintString");
static_assert(offsetof(VehicleDef, vehHelicopterGroundFx) == 0x220, "VehicleDef::vehHelicopterGroundFx");
static_assert(offsetof(VehicleDef, vehHelicopterGroundWaterFx) == 0x228, "VehicleDef::vehHelicopterGroundWaterFx");
static_assert(offsetof(VehicleDef, turretWeaponName) == 0x360, "VehicleDef::turretWeaponName");
static_assert(offsetof(VehicleDef, turretWeapon) == 0x368, "VehicleDef::turretWeapon");
static_assert(offsetof(VehicleDef, turretSpinSnd) == 0x398, "VehicleDef::turretSpinSnd");
static_assert(offsetof(VehicleDef, turretStopSnd) == 0x3A0, "VehicleDef::turretStopSnd");
static_assert(offsetof(VehicleDef, trophyExplodeFx) == 0x3D0, "VehicleDef::trophyExplodeFx");
static_assert(offsetof(VehicleDef, trophyFlashFx) == 0x3D8, "VehicleDef::trophyFlashFx");
static_assert(offsetof(VehicleDef, compassFriendlyIcon) == 0x3E0, "VehicleDef::compassFriendlyIcon");
static_assert(offsetof(VehicleDef, compassEnemyIcon) == 0x3E8, "VehicleDef::compassEnemyIcon");
static_assert(offsetof(VehicleDef, compassFriendlyAltIcon) == 0x3F0, "VehicleDef::compassFriendlyAltIcon");
static_assert(offsetof(VehicleDef, compassEnemyAltIcon) == 0x3F8, "VehicleDef::compassEnemyAltIcon");
static_assert(offsetof(VehicleDef, idleLowSnd) == 0x408, "VehicleDef::idleLowSnd");
static_assert(offsetof(VehicleDef, idleHighSnd) == 0x410, "VehicleDef::idleHighSnd");
static_assert(offsetof(VehicleDef, engineLowSnd) == 0x418, "VehicleDef::engineLowSnd");
static_assert(offsetof(VehicleDef, engineHighSnd) == 0x420, "VehicleDef::engineHighSnd");
static_assert(offsetof(VehicleDef, idleLowSndAlt) == 0x430, "VehicleDef::idleLowSndAlt");
static_assert(offsetof(VehicleDef, idleHighSndAlt) == 0x438, "VehicleDef::idleHighSndAlt");
static_assert(offsetof(VehicleDef, engineLowSndAlt) == 0x440, "VehicleDef::engineLowSndAlt");
static_assert(offsetof(VehicleDef, engineHighSndAlt) == 0x448, "VehicleDef::engineHighSndAlt");
static_assert(offsetof(VehicleDef, turretSpinSndAlt) == 0x458, "VehicleDef::turretSpinSndAlt");
static_assert(offsetof(VehicleDef, turretStopSndAlt) == 0x460, "VehicleDef::turretStopSndAlt");
static_assert(offsetof(VehicleDef, engineStartUpSnd) == 0x468, "VehicleDef::engineStartUpSnd");
static_assert(offsetof(VehicleDef, engineShutdownSnd) == 0x478, "VehicleDef::engineShutdownSnd");
static_assert(offsetof(VehicleDef, engineIdleSnd) == 0x480, "VehicleDef::engineIdleSnd");
static_assert(offsetof(VehicleDef, engineSustainSnd) == 0x488, "VehicleDef::engineSustainSnd");
static_assert(offsetof(VehicleDef, engineRampUpSnd) == 0x490, "VehicleDef::engineRampUpSnd");
static_assert(offsetof(VehicleDef, engineRampDownSnd) == 0x4A0, "VehicleDef::engineRampDownSnd");
static_assert(offsetof(VehicleDef, suspensionSoftSnd) == 0x4B0, "VehicleDef::suspensionSoftSnd");
static_assert(offsetof(VehicleDef, suspensionHardSnd) == 0x4C0, "VehicleDef::suspensionHardSnd");
static_assert(offsetof(VehicleDef, collisionSnd) == 0x4D0, "VehicleDef::collisionSnd");
static_assert(offsetof(VehicleDef, speedSnd) == 0x4E0, "VehicleDef::speedSnd");
static_assert(offsetof(VehicleDef, surfaceSndPrefix) == 0x4F0, "VehicleDef::surfaceSndPrefix");
static_assert(offsetof(VehicleDef, surfaceSnds) == 0x4F8, "VehicleDef::surfaceSnds");
static_assert(offsetof(VehicleDef, soundTriggerOverrideZone) == 0x600, "VehicleDef::soundTriggerOverrideZone");

struct AnimOverrideEntry
{
	unsigned short attachment1;                             // +0x000
	unsigned short attachment2;                             // +0x002
	XAnimParts *overrideAnim;                               // +0x008
	XAnimParts *altmodeAnim;                                // +0x010
	unsigned int animTreeType;                              // +0x018
	int animTime;                                           // +0x01C
	int altTime;                                            // +0x020
};
static_assert(sizeof(AnimOverrideEntry) == 0x28, "AnimOverrideEntry");
static_assert(offsetof(AnimOverrideEntry, overrideAnim) == 0x8, "AnimOverrideEntry::overrideAnim");
static_assert(offsetof(AnimOverrideEntry, altmodeAnim) == 0x10, "AnimOverrideEntry::altmodeAnim");

struct SoundOverrideEntry
{
	unsigned short attachment1;                             // +0x000
	unsigned short attachment2;                             // +0x002
	snd_alias_list_t *overrideSound;                        // +0x008
	snd_alias_list_t *altmodeSound;                         // +0x010
	unsigned int soundType;                                 // +0x018
};
static_assert(sizeof(SoundOverrideEntry) == 0x20, "SoundOverrideEntry");
static_assert(offsetof(SoundOverrideEntry, overrideSound) == 0x8, "SoundOverrideEntry::overrideSound");
static_assert(offsetof(SoundOverrideEntry, altmodeSound) == 0x10, "SoundOverrideEntry::altmodeSound");

struct FXOverrideEntry
{
	unsigned short attachment1;                             // +0x000
	unsigned short attachment2;                             // +0x002
	FxEffectDef *overrideFX;                                // +0x008
	FxEffectDef *altmodeFX;                                 // +0x010
	unsigned int fxType;                                    // +0x018
};
static_assert(sizeof(FXOverrideEntry) == 0x20, "FXOverrideEntry");
static_assert(offsetof(FXOverrideEntry, overrideFX) == 0x8, "FXOverrideEntry::overrideFX");
static_assert(offsetof(FXOverrideEntry, altmodeFX) == 0x10, "FXOverrideEntry::altmodeFX");

struct ReloadStateTimerEntry
{
	int attachment;                                         // +0x000
	int reloadAddTime;                                      // +0x004
	int reloadEmptyAddTime;                                 // +0x008
	int reloadStartAddTime;                                 // +0x00C
};
static_assert(sizeof(ReloadStateTimerEntry) == 0x10, "ReloadStateTimerEntry");

struct NoteTrackToSoundEntry
{
	int attachment;                                         // +0x000
	scr_string_t *notetrackSoundMapKeys;                    // +0x008
	scr_string_t *notetrackSoundMapValues;                  // +0x010
};
static_assert(sizeof(NoteTrackToSoundEntry) == 0x18, "NoteTrackToSoundEntry");
static_assert(offsetof(NoteTrackToSoundEntry, notetrackSoundMapKeys) == 0x8, "NoteTrackToSoundEntry::notetrackSoundMapKeys");
static_assert(offsetof(NoteTrackToSoundEntry, notetrackSoundMapValues) == 0x10, "NoteTrackToSoundEntry::notetrackSoundMapValues");

struct AttAmmoGeneral
{
	PenetrateType penetrateType;                            // +0x000
	float penetrateMultiplier;                              // +0x004
	ImpactType impactType;                                  // +0x008
	weapFireType_t fireType;                                // +0x00C
	TracerDef *tracerType;                                  // +0x010
	bool rifleBullet;                                       // +0x018
	bool armorPiercing;                                     // +0x019
};
static_assert(sizeof(AttAmmoGeneral) == 0x20, "AttAmmoGeneral");
static_assert(offsetof(AttAmmoGeneral, tracerType) == 0x10, "AttAmmoGeneral::tracerType");

struct AttSight
{
	bool aimDownSight;                                      // +0x000
	bool adsFire;                                           // +0x001
	bool rechamberWhileAds;                                 // +0x002
	bool noAdsWhenMagEmpty;                                 // +0x003
	bool canHoldBreath;                                     // +0x004
	bool canVariableZoom;                                   // +0x005
	bool hideRailWithThisScope;                             // +0x006
	bool useScopeDrift;                                     // +0x007
	bool useDualFOV;                                        // +0x008
};
static_assert(sizeof(AttSight) == 0x9, "AttSight");

struct AttReload
{
	bool noPartialReload;                                   // +0x000
	bool segmentedReload;                                   // +0x001
};
static_assert(sizeof(AttReload) == 0x2, "AttReload");

struct AttAddOns
{
	bool motionTracker;                                     // +0x000
	bool silenced;                                          // +0x001
	bool riotShield;                                        // +0x002
};
static_assert(sizeof(AttAddOns) == 0x3, "AttAddOns");

struct AttGeneral
{
	bool boltAction;                                        // +0x000
	bool inheritsPerks;                                     // +0x001
	bool reticleSpin45;                                     // +0x002
	float enemyCrosshairRange;                              // +0x004
	Material *reticleCenter;                                // +0x008
	Material *reticleSide;                                  // +0x010
	int reticleCenterSize;                                  // +0x018
	int reticleSideSize;                                    // +0x01C
	float moveSpeedScale;                                   // +0x020
	float adsMoveSpeedScale;                                // +0x024
};
static_assert(sizeof(AttGeneral) == 0x28, "AttGeneral");
static_assert(offsetof(AttGeneral, reticleCenter) == 0x8, "AttGeneral::reticleCenter");
static_assert(offsetof(AttGeneral, reticleSide) == 0x10, "AttGeneral::reticleSide");

struct AttAimAssist
{
	float autoAimRange;                                     // +0x000
	float aimAssistRange;                                   // +0x004
	float aimAssistRangeAds;                                // +0x008
};
static_assert(sizeof(AttAimAssist) == 0xC, "AttAimAssist");

struct AttAmmunition
{
	int maxAmmo;                                            // +0x000
	int startAmmo;                                          // +0x004
	int clipSize;                                           // +0x008
	int shotCount;                                          // +0x00C
	int reloadAmmoAdd;                                      // +0x010
	int reloadStartAdd;                                     // +0x014
};
static_assert(sizeof(AttAmmunition) == 0x18, "AttAmmunition");

struct AttDamage
{
	int damage;                                             // +0x000
	int minDamage;                                          // +0x004
	int meleeDamage;                                        // +0x008
	float maxDamageRange;                                   // +0x00C
	float minDamageRange;                                   // +0x010
	int playerDamage;                                       // +0x014
	int minPlayerDamage;                                    // +0x018
};
static_assert(sizeof(AttDamage) == 0x1C, "AttDamage");

struct AttLocationDamage
{
	float locNone;                                          // +0x000
	float locHelmet;                                        // +0x004
	float locHead;                                          // +0x008
	float locNeck;                                          // +0x00C
	float locTorsoUpper;                                    // +0x010
	float locTorsoLower;                                    // +0x014
	float locRightArmUpper;                                 // +0x018
	float locRightArmLower;                                 // +0x01C
	float locRightHand;                                     // +0x020
	float locLeftArmUpper;                                  // +0x024
	float locLeftArmLower;                                  // +0x028
	float locLeftHand;                                      // +0x02C
	float locRightLegUpper;                                 // +0x030
	float locRightLegLower;                                 // +0x034
	float locRightFoot;                                     // +0x038
	float locLeftLegUpper;                                  // +0x03C
	float locLeftLegLower;                                  // +0x040
	float locLeftFoot;                                      // +0x044
	float locGun;                                           // +0x048
};
static_assert(sizeof(AttLocationDamage) == 0x4C, "AttLocationDamage");

struct AttIdleSettings
{
	float hipIdleAmount;                                    // +0x000
	float hipIdleSpeed;                                     // +0x004
	float idleCrouchFactor;                                 // +0x008
	float idleProneFactor;                                  // +0x00C
	float adsIdleLerpStartTime;                             // +0x010
	float adsIdleLerpTime;                                  // +0x014
};
static_assert(sizeof(AttIdleSettings) == 0x18, "AttIdleSettings");

struct AttADSSettings
{
	float adsSpread;                                        // +0x000
	float adsAimPitch;                                      // +0x004
	float adsTransInTime;                                   // +0x008
	float adsTransOutTime;                                  // +0x00C
	int adsReloadTransTime;                                 // +0x010
	float adsCrosshairInFrac;                               // +0x014
	float adsCrosshairOutFrac;                              // +0x018
	float adsZoomFov;                                       // +0x01C
	float adsZoomInFrac;                                    // +0x020
	float adsZoomOutFrac;                                   // +0x024
	float adsFovLerpTime;                                   // +0x028
	float adsBobFactor;                                     // +0x02C
	float adsViewBobMult;                                   // +0x030
	float adsViewErrorMin;                                  // +0x034
	float adsViewErrorMax;                                  // +0x038
	float adsFireAnimFrac;                                  // +0x03C
};
static_assert(sizeof(AttADSSettings) == 0x40, "AttADSSettings");

struct AttScopeDriftSettings
{
	float fScopeDriftDelay;                                 // +0x000
	float fScopeDriftLerpInTime;                            // +0x004
	float fScopeDriftSteadyTime;                            // +0x008
	float fScopeDriftLerpOutTime;                           // +0x00C
	float fScopeDriftSteadyFactor;                          // +0x010
	float fScopeDriftUnsteadyFactor;                        // +0x014
};
static_assert(sizeof(AttScopeDriftSettings) == 0x18, "AttScopeDriftSettings");

struct AttHipSpread
{
	float hipSpreadStandMin;                                // +0x000
	float hipSpreadDuckedMin;                               // +0x004
	float hipSpreadProneMin;                                // +0x008
	float hipSpreadMax;                                     // +0x00C
	float hipSpreadDuckedMax;                               // +0x010
	float hipSpreadProneMax;                                // +0x014
	float hipSpreadFireAdd;                                 // +0x018
	float hipSpreadTurnAdd;                                 // +0x01C
	float hipSpreadMoveAdd;                                 // +0x020
	float hipSpreadDecayRate;                               // +0x024
	float hipSpreadDuckedDecay;                             // +0x028
	float hipSpreadProneDecay;                              // +0x02C
};
static_assert(sizeof(AttHipSpread) == 0x30, "AttHipSpread");

struct AttGunKick
{
	int hipGunKickReducedKickBullets;                       // +0x000
	float hipGunKickReducedKickPercent;                     // +0x004
	float hipGunKickPitchMin;                               // +0x008
	float hipGunKickPitchMax;                               // +0x00C
	float hipGunKickYawMin;                                 // +0x010
	float hipGunKickYawMax;                                 // +0x014
	float hipGunKickMagMin;                                 // +0x018
	float hipGunKickAccel;                                  // +0x01C
	float hipGunKickSpeedMax;                               // +0x020
	float hipGunKickSpeedDecay;                             // +0x024
	float hipGunKickStaticDecay;                            // +0x028
	int adsGunKickReducedKickBullets;                       // +0x02C
	float adsGunKickReducedKickPercent;                     // +0x030
	float adsGunKickPitchMin;                               // +0x034
	float adsGunKickPitchMax;                               // +0x038
	float adsGunKickYawMin;                                 // +0x03C
	float adsGunKickYawMax;                                 // +0x040
	float adsGunKickMagMin;                                 // +0x044
	float adsGunKickAccel;                                  // +0x048
	float adsGunKickSpeedMax;                               // +0x04C
	float adsGunKickSpeedDecay;                             // +0x050
	float adsGunKickStaticDecay;                            // +0x054
};
static_assert(sizeof(AttGunKick) == 0x58, "AttGunKick");

struct AttViewKick
{
	float hipViewKickPitchMin;                              // +0x000
	float hipViewKickPitchMax;                              // +0x004
	float hipViewKickYawMin;                                // +0x008
	float hipViewKickYawMax;                                // +0x00C
	float hipViewKickMagMin;                                // +0x010
	float hipViewKickCenterSpeed;                           // +0x014
	float adsViewKickPitchMin;                              // +0x018
	float adsViewKickPitchMax;                              // +0x01C
	float adsViewKickYawMin;                                // +0x020
	float adsViewKickYawMax;                                // +0x024
	float adsViewKickMagMin;                                // +0x028
	float adsViewKickCenterSpeed;                           // +0x02C
};
static_assert(sizeof(AttViewKick) == 0x30, "AttViewKick");

struct AttADSOverlay
{
	ADSOverlay overlay;                                     // +0x000
	bool hybridToggle;                                      // +0x038
	bool thermalScope;                                      // +0x039
	bool thermalToggle;                                     // +0x03A
	bool outlineEnemies;                                    // +0x03B
};
static_assert(sizeof(AttADSOverlay) == 0x40, "AttADSOverlay");

struct AttUI
{
	Material *dpadIcon;                                     // +0x000
	Material *ammoCounterIcon;                              // +0x008
	weaponIconRatioType_t dpadIconRatio;                    // +0x010
	weaponIconRatioType_t ammoCounterIconRatio;             // +0x014
	ammoCounterClipType_t ammoCounterClip;                  // +0x018
};
static_assert(sizeof(AttUI) == 0x20, "AttUI");
static_assert(offsetof(AttUI, dpadIcon) == 0x0, "AttUI::dpadIcon");
static_assert(offsetof(AttUI, ammoCounterIcon) == 0x8, "AttUI::ammoCounterIcon");

struct AttRumbles
{
	const char *fireRumble;                                 // +0x000
	const char *meleeImpactRumble;                          // +0x008
};
static_assert(sizeof(AttRumbles) == 0x10, "AttRumbles");
static_assert(offsetof(AttRumbles, fireRumble) == 0x0, "AttRumbles::fireRumble");
static_assert(offsetof(AttRumbles, meleeImpactRumble) == 0x8, "AttRumbles::meleeImpactRumble");

struct AttProjectile
{
	int explosionRadius;                                    // +0x000
	int explosionInnerDamage;                               // +0x004
	int explosionOuterDamage;                               // +0x008
	float damageConeAngle;                                  // +0x00C
	int projectileSpeed;                                    // +0x010
	int projectileSpeedUp;                                  // +0x014
	int projectileActivateDist;                             // +0x018
	float projectileLifetime;                               // +0x01C
	const char *projectileName;                             // +0x020
	XModel *projectileModel;                                // +0x028
	weapProjExposion_t projExplosionType;                   // +0x030
	FxEffectDef *projExplosionEffect;                       // +0x038
	bool projExplosionEffectForceNormalUp;                  // +0x040
	snd_alias_list_t *projExplosionSound;                   // +0x048
	FxEffectDef *projDudEffect;                             // +0x050
	snd_alias_list_t *projDudSound;                         // +0x058
	bool projImpactExplode;                                 // +0x060
	float destabilizationRateTime;                          // +0x064
	float destabilizationCurvatureMax;                      // +0x068
	int destabilizeDistance;                                // +0x06C
	FxEffectDef *projTrailEffect;                           // +0x070
	int projIgnitionDelay;                                  // +0x078
	FxEffectDef *projIgnitionEffect;                        // +0x080
	snd_alias_list_t *projIgnitionSound;                    // +0x088
};
static_assert(sizeof(AttProjectile) == 0x90, "AttProjectile");
static_assert(offsetof(AttProjectile, projectileName) == 0x20, "AttProjectile::projectileName");
static_assert(offsetof(AttProjectile, projectileModel) == 0x28, "AttProjectile::projectileModel");
static_assert(offsetof(AttProjectile, projExplosionEffect) == 0x38, "AttProjectile::projExplosionEffect");
static_assert(offsetof(AttProjectile, projExplosionSound) == 0x48, "AttProjectile::projExplosionSound");
static_assert(offsetof(AttProjectile, projDudEffect) == 0x50, "AttProjectile::projDudEffect");
static_assert(offsetof(AttProjectile, projDudSound) == 0x58, "AttProjectile::projDudSound");
static_assert(offsetof(AttProjectile, projTrailEffect) == 0x70, "AttProjectile::projTrailEffect");
static_assert(offsetof(AttProjectile, projIgnitionEffect) == 0x80, "AttProjectile::projIgnitionEffect");
static_assert(offsetof(AttProjectile, projIgnitionSound) == 0x88, "AttProjectile::projIgnitionSound");

