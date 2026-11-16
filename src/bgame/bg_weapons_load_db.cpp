// bgame/bg_weapons_load_db.cpp (Store build): the zone loaders of weapons (WeaponCompleteDef, asset type 0x23, with
// its WeaponDef), attachments (WeaponAttachment, 0x22) and vehicles (VehicleDef, 0x32), with the pointer arrays and
// entries they use.
//
// Generated loader functions (database/db_load.cpp includes them; the servers' PDB places them in
// gfx_d3d/r_material_load_db.h). The code is the Store build's, tagged with Store addresses. Where the server gives
// a block its own function (Load_AttSight, Load_AnimOverrideEntryArray, ...) the Store build inlines it, and the
// Store build gives NoteTrackToSoundEntry its own function where the server inlines it into the array.
// tools/fastfile/weapon.py is the same logic in Python, checked against the game on real zones
// (docs/assets/weapons.md); tests/differential/test_weapon_load.py checks this file against the exe.

#include "bgame/bg_weapons_load_db.h"

void Load_MaterialHandle(bool atStreamStart);                         // Store 140353700
void Load_MaterialHandleArray(bool atStreamStart, unsigned long long count);  // Store 1403537F0
void Load_XModelPtr(bool atStreamStart);                              // Store 14035E530
void Load_XModelPtrArray(bool atStreamStart, unsigned long long count);  // Store 14035E620
void Load_XAnimParts(bool atStreamStart);                             // Store 14035D040
void Load_XAnimPartsPtr(bool atStreamStart);                          // Store 14035D3D0
void Load_XAnimPartsAsset(XAnimParts **header);                       // Store 140374000
void Load_FxEffectDefHandle(bool atStreamStart);                      // Store 14034D120
void Load_FxEffectDefHandleArray(bool atStreamStart, unsigned long long count);  // Store 14034D210
void Load_PhysCollmapPtr(bool atStreamStart);                         // Store 140355410
void Load_PhysPresetPtr(bool atStreamStart);                          // Store 1403555F0
void Load_TracerDefPtr(bool atStreamStart);                           // Store 1403585D0
void Load_SndAliasCustom(snd_alias_list_t **var);                     // Store 1405367A0
void Load_ScriptStringCustom(scr_string_t *var);                      // Store 14037AF90
void Load_WeaponAttachmentAsset(WeaponAttachment **attachment);       // Store 140373E80
void Load_WeaponCompleteDefAsset(WeaponCompleteDef **weapon);         // Store 140373F40
void Load_VehicleDefAsset(VehicleDef **vehicle);                      // Store 140373D00

void Load_WeaponDef(bool atStreamStart);
void Load_WeaponAttachment(bool atStreamStart);
void Load_WeaponCompleteDefPtr(bool atStreamStart);

extern Material **varMaterialHandle;                                 // Store 144425D20
extern XModel **varXModelPtr;                                        // Store 1444267F8
extern XAnimParts **varXAnimPartsPtr;                                // Store 144425998
extern XAnimParts *varXAnimParts;                                    // Store 144425990
extern const FxEffectDef **varFxEffectDefHandle;                     // Store 1444260F8
extern PhysCollmap **varPhysCollmapPtr;                              // Store 144424FB0
extern PhysPreset **varPhysPresetPtr;                                // Store 144426758
extern TracerDef **varTracerDefPtr;                                  // Store 144425F98
extern snd_alias_list_t **varsnd_alias_list_name;                    // Store 144426680
extern vec2_t *varvec2_t;                                            // Store 144424C78
extern WeaponCompleteDef **varWeaponCompleteDefPtr;                  // Store 144426BF8
extern WeaponCompleteDef *varWeaponCompleteDef;                      // Store 144426BF0
extern WeaponDef *varWeaponDef;                                      // Store 144426BE8
extern WeaponAttachment **varWeaponAttachmentPtr;                    // Store 144426350
extern WeaponAttachment *varWeaponAttachment;                        // Store 144426348
extern AnimOverrideEntry *varAnimOverrideEntry;                      // Store 144426B70
extern SoundOverrideEntry *varSoundOverrideEntry;                    // Store 144426B78
extern FXOverrideEntry *varFXOverrideEntry;                          // Store 144426B80
extern ReloadStateTimerEntry *varReloadStateTimerEntry;              // Store 144426B88
extern NoteTrackToSoundEntry *varNoteTrackToSoundEntry;              // Store 144426B90
extern ADSOverlay *varADSOverlay;                                    // Store 144426008
extern AttAmmoGeneral *varAttAmmoGeneral;                            // Store 1444262B0
extern AttADSOverlay *varAttADSOverlay;                              // Store 1444262B8
extern AttUI *varAttUI;                                              // Store 1444262C0
extern AttSight *varAttSight;                                        // Store 1444262C8
extern AttReload *varAttReload;                                      // Store 1444262D0
extern AttAddOns *varAttAddOns;                                      // Store 1444262D8
extern AttGeneral *varAttGeneral;                                    // Store 1444262E0
extern AttAimAssist *varAttAimAssist;                                // Store 1444262E8
extern AttAmmunition *varAttAmmunition;                              // Store 1444262F0
extern AttDamage *varAttDamage;                                      // Store 1444262F8
extern AttLocationDamage *varAttLocationDamage;                      // Store 144426300
extern AttIdleSettings *varAttIdleSettings;                          // Store 144426308
extern AttADSSettings *varAttADSSettings;                            // Store 144426310
extern AttScopeDriftSettings *varAttScopeDriftSettings;              // Store 144426318
extern AttHipSpread *varAttHipSpread;                                // Store 144426320
extern AttGunKick *varAttGunKick;                                    // Store 144426328
extern AttViewKick *varAttViewKick;                                  // Store 144426330
extern AttRumbles *varAttRumbles;                                    // Store 144426338
extern AttProjectile *varAttProjectile;                              // Store 144426340
extern VehicleDef **varVehicleDefPtr;                                // Store 144425460
extern VehicleDef *varVehicleDef;                                    // Store 144425458
extern VehiclePhysDef *varVehiclePhysDef;                            // Store 144425450

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// The generated code's repeated statements, written once.

static inline void LoadXString(const char **field)
{
	varXString = field;
	Load_Stream(false, varXString, 8);
	if (*varXString)
	{
		if ((unsigned long long)*varXString == DB_PTR_FOLLOWING)
		{
			*varXString = (const char *)g_streamPos;
			varConstChar = (const char *)g_streamPos;
			Load_XStringCustom(varXString);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)varXString);
		}
	}
}

static inline void LoadSound(snd_alias_list_t **field)
{
	varsnd_alias_list_name = field;
	Load_Stream(false, varsnd_alias_list_name, 8);
	Load_SndAliasCustom(varsnd_alias_list_name);
}

static inline void LoadMaterial(Material **field)
{
	varMaterialHandle = field;
	Load_MaterialHandle(false);
}

static inline void LoadEffect(FxEffectDef **field)
{
	varFxEffectDefHandle = (const FxEffectDef **)field;
	Load_FxEffectDefHandle(false);
}

static inline void LoadModel(XModel **field)
{
	varXModelPtr = field;
	Load_XModelPtr(false);
}

// Load_scr_string_tArray, inlined: `count` script strings at varscr_string_t.
static inline void LoadScriptStrings(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varscr_string_t, 4 * count);
	scr_string_t *str = varscr_string_t;
	for (; count; count--)
	{
		varscr_string_t = str;
		Load_Stream(false, str, 4);
		Load_ScriptStringCustom(varscr_string_t);
		str++;
	}
}

// Load_snd_alias_list_nameArray, inlined: `count` sounds by name at varsnd_alias_list_name.
static inline void LoadSounds(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varsnd_alias_list_name, 8 * count);
	snd_alias_list_t **sound = varsnd_alias_list_name;
	for (; count; count--)
	{
		varsnd_alias_list_name = sound;
		Load_Stream(false, sound, 8);
		Load_SndAliasCustom(varsnd_alias_list_name);
		sound++;
	}
}

// A pointer field to data that follows in the stream (-1: point it at the stream, aligned) or elsewhere in the zone
// (an offset). True when the data follows and is to be loaded.
template <typename T>
static inline bool Follows(T **field, unsigned long long align)
{
	if (!*field)
		return false;
	if ((unsigned long long)*field != DB_PTR_FOLLOWING)
	{
		DB_ConvertOffsetToPointer((unsigned long long *)field);
		return false;
	}
	ALIGN_POS(align);
	*field = (T *)g_streamPos;
	return true;
}

// A pointer field whose data always follows when it is set (the generated code does not test for -1).
template <typename T>
static inline bool FollowsAlways(T **field, unsigned long long align)
{
	if (!*field)
		return false;
	ALIGN_POS(align);
	*field = (T *)g_streamPos;
	return true;
}

// ==== pointer arrays ==============================================================================================

// Store 14035D4C0
void Load_XAnimPartsPtrArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varXAnimPartsPtr, sizeof(XAnimParts *) * count);
	XAnimParts **animPtr = varXAnimPartsPtr;
	for (; count; count--)
	{
		varXAnimPartsPtr = animPtr;
		Load_Stream(false, animPtr, sizeof(XAnimParts *));
		DB_PushStreamPos(XFILE_BLOCK_TEMP);
		XAnimParts **current = varXAnimPartsPtr;
		unsigned long long value = (unsigned long long)*varXAnimPartsPtr;
		if (value)
		{
			if (DB_PTR_IS_INLINE(value))
			{
				ALIGN_POS(4);
				*varXAnimPartsPtr = (XAnimParts *)g_streamPos;
				varXAnimParts = (XAnimParts *)g_streamPos;
				unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
				Load_XAnimParts(true);
				Load_XAnimPartsAsset(current);
				if (inserted)
					*(XAnimParts **)inserted = *current;
			}
			else
			{
				DB_ConvertOffsetToAlias((unsigned long long *)varXAnimPartsPtr);
			}
		}
		DB_PopStreamPos();
		animPtr++;
	}
}

// ==== attachments =================================================================================================

// Store 14034A080: the scope overlay's four materials.
void Load_ADSOverlay(bool atStreamStart)
{
	Load_Stream(atStreamStart, varADSOverlay, sizeof(ADSOverlay));
	LoadMaterial(&varADSOverlay->shader);
	LoadMaterial(&varADSOverlay->shaderLowRes);
	LoadMaterial(&varADSOverlay->shaderEMP);
	LoadMaterial(&varADSOverlay->shaderEMPLowRes);
}

// Store 14034AEA0
void Load_AttRumbles(bool atStreamStart)
{
	Load_Stream(atStreamStart, varAttRumbles, sizeof(AttRumbles));
	LoadXString(&varAttRumbles->fireRumble);
	LoadXString(&varAttRumbles->meleeImpactRumble);
}

// Store 14034AD20
void Load_AttProjectile(bool atStreamStart)
{
	Load_Stream(atStreamStart, varAttProjectile, sizeof(AttProjectile));
	LoadXString(&varAttProjectile->projectileName);
	LoadModel(&varAttProjectile->projectileModel);
	LoadEffect(&varAttProjectile->projExplosionEffect);
	LoadSound(&varAttProjectile->projExplosionSound);
	LoadEffect(&varAttProjectile->projDudEffect);
	LoadSound(&varAttProjectile->projDudSound);
	LoadEffect(&varAttProjectile->projTrailEffect);
	LoadEffect(&varAttProjectile->projIgnitionEffect);
	LoadSound(&varAttProjectile->projIgnitionSound);
}

// An attachment's block of plain values: the data follows when the field is set (aligned 4).
template <typename T>
static inline void LoadAttBlock(T **field, T **var)
{
	if (FollowsAlways(field, 4))
	{
		*var = *field;
		Load_Stream(true, *var, sizeof(T));
	}
}

// Store 140359A30
void Load_WeaponAttachment(bool atStreamStart)
{
	Load_Stream(atStreamStart, varWeaponAttachment, sizeof(WeaponAttachment));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varWeaponAttachment->szInternalName);
	LoadXString(&varWeaponAttachment->szDisplayName);
	if (Follows(&varWeaponAttachment->worldModels, 8))
	{
		varXModelPtr = varWeaponAttachment->worldModels;
		Load_XModelPtrArray(true, 0x40);
	}
	if (Follows(&varWeaponAttachment->viewModels, 8))
	{
		varXModelPtr = varWeaponAttachment->viewModels;
		Load_XModelPtrArray(true, 0x40);
	}
	if (Follows(&varWeaponAttachment->reticleViewModels, 8))
	{
		varXModelPtr = varWeaponAttachment->reticleViewModels;
		Load_XModelPtrArray(true, 0x10);
	}
	if (FollowsAlways(&varWeaponAttachment->ammogeneral, 4))
	{
		varAttAmmoGeneral = varWeaponAttachment->ammogeneral;
		Load_Stream(true, varAttAmmoGeneral, sizeof(AttAmmoGeneral));
		varTracerDefPtr = &varAttAmmoGeneral->tracerType;
		Load_TracerDefPtr(false);
	}
	LoadAttBlock(&varWeaponAttachment->sight, &varAttSight);
	if (FollowsAlways(&varWeaponAttachment->reload, 2))
	{
		varAttReload = varWeaponAttachment->reload;
		Load_Stream(true, varAttReload, sizeof(AttReload));
	}
	if (varWeaponAttachment->addOns)                                   // not aligned
	{
		varWeaponAttachment->addOns = (AttAddOns *)g_streamPos;
		varAttAddOns = (AttAddOns *)g_streamPos;
		Load_Stream(true, varAttAddOns, sizeof(AttAddOns));
	}
	if (FollowsAlways(&varWeaponAttachment->general, 4))
	{
		varAttGeneral = varWeaponAttachment->general;
		Load_Stream(true, varAttGeneral, sizeof(AttGeneral));
		LoadMaterial(&varAttGeneral->reticleCenter);
		LoadMaterial(&varAttGeneral->reticleSide);
	}
	LoadAttBlock(&varWeaponAttachment->aimAssist, &varAttAimAssist);
	LoadAttBlock(&varWeaponAttachment->ammunition, &varAttAmmunition);
	LoadAttBlock(&varWeaponAttachment->damage, &varAttDamage);
	LoadAttBlock(&varWeaponAttachment->locationDamage, &varAttLocationDamage);
	LoadAttBlock(&varWeaponAttachment->idleSettings, &varAttIdleSettings);
	LoadAttBlock(&varWeaponAttachment->adsSettings, &varAttADSSettings);
	LoadAttBlock(&varWeaponAttachment->adsSettingsMain, &varAttADSSettings);
	LoadAttBlock(&varWeaponAttachment->scopeDriftSettings, &varAttScopeDriftSettings);
	LoadAttBlock(&varWeaponAttachment->scopeDriftSettingsMain, &varAttScopeDriftSettings);
	LoadAttBlock(&varWeaponAttachment->hipSpread, &varAttHipSpread);
	LoadAttBlock(&varWeaponAttachment->gunKick, &varAttGunKick);
	LoadAttBlock(&varWeaponAttachment->viewKick, &varAttViewKick);
	if (FollowsAlways(&varWeaponAttachment->adsOverlay, 4))
	{
		varAttADSOverlay = varWeaponAttachment->adsOverlay;
		Load_Stream(true, varAttADSOverlay, sizeof(AttADSOverlay));
		varADSOverlay = &varAttADSOverlay->overlay;
		Load_ADSOverlay(false);
	}
	if (FollowsAlways(&varWeaponAttachment->ui, 4))
	{
		varAttUI = varWeaponAttachment->ui;
		Load_Stream(true, varAttUI, sizeof(AttUI));
		LoadMaterial(&varAttUI->dpadIcon);
		LoadMaterial(&varAttUI->ammoCounterIcon);
	}
	if (FollowsAlways(&varWeaponAttachment->rumbles, 4))
	{
		varAttRumbles = varWeaponAttachment->rumbles;
		Load_AttRumbles(true);
	}
	if (FollowsAlways(&varWeaponAttachment->projectile, 4))
	{
		varAttProjectile = varWeaponAttachment->projectile;
		Load_AttProjectile(true);
	}
	DB_PopStreamPos();
}

// Store 14035A240
void Load_WeaponAttachmentPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varWeaponAttachmentPtr, sizeof(WeaponAttachment *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	WeaponAttachment **ptr = varWeaponAttachmentPtr;
	unsigned long long value = (unsigned long long)*varWeaponAttachmentPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varWeaponAttachmentPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varWeaponAttachmentPtr = (WeaponAttachment *)g_streamPos;
		varWeaponAttachment = (WeaponAttachment *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_WeaponAttachment(true);
		Load_WeaponAttachmentAsset(ptr);
		if (inserted)
			*(WeaponAttachment **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// Store 14035A330
void Load_WeaponAttachmentPtrArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varWeaponAttachmentPtr, sizeof(WeaponAttachment *) * count);
	WeaponAttachment **attachmentPtr = varWeaponAttachmentPtr;
	for (; count; count--)
	{
		varWeaponAttachmentPtr = attachmentPtr;
		Load_Stream(false, attachmentPtr, sizeof(WeaponAttachment *));
		DB_PushStreamPos(XFILE_BLOCK_TEMP);
		WeaponAttachment **current = varWeaponAttachmentPtr;
		unsigned long long value = (unsigned long long)*varWeaponAttachmentPtr;
		if (value)
		{
			if (DB_PTR_IS_INLINE(value))
			{
				ALIGN_POS(4);
				*varWeaponAttachmentPtr = (WeaponAttachment *)g_streamPos;
				varWeaponAttachment = (WeaponAttachment *)g_streamPos;
				unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
				Load_WeaponAttachment(true);
				Load_WeaponAttachmentAsset(current);
				if (inserted)
					*(WeaponAttachment **)inserted = *current;
			}
			else
			{
				DB_ConvertOffsetToAlias((unsigned long long *)varWeaponAttachmentPtr);
			}
		}
		DB_PopStreamPos();
		attachmentPtr++;
	}
}

// ==== weapons =====================================================================================================

// Store 140354C50: one entry of a weapon's notetrack sound overrides (the server inlines it into
// Load_NoteTrackToSoundEntryArray).
void Load_NoteTrackToSoundEntry(bool atStreamStart)
{
	Load_Stream(atStreamStart, varNoteTrackToSoundEntry, sizeof(NoteTrackToSoundEntry));
	if (Follows(&varNoteTrackToSoundEntry->notetrackSoundMapKeys, 4))
	{
		varscr_string_t = varNoteTrackToSoundEntry->notetrackSoundMapKeys;
		LoadScriptStrings(true, 0x18);
	}
	if (Follows(&varNoteTrackToSoundEntry->notetrackSoundMapValues, 4))
	{
		varscr_string_t = varNoteTrackToSoundEntry->notetrackSoundMapValues;
		LoadScriptStrings(true, 0x18);
	}
}

// Store 14035AD90. The complete def being loaded (varWeaponCompleteDef) gives the counts of the original accuracy
// graphs. No block push: the WeaponDef is inside the complete def's.
void Load_WeaponDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varWeaponDef, sizeof(WeaponDef));
	LoadXString(&varWeaponDef->szOverlayName);
	if (Follows(&varWeaponDef->gunXModel, 8))
	{
		varXModelPtr = varWeaponDef->gunXModel;
		Load_XModelPtrArray(true, 0x40);
	}
	LoadModel(&varWeaponDef->handXModel);
	LoadModel(&varWeaponDef->camoWorldModel);
	LoadModel(&varWeaponDef->camoViewModel);
	LoadMaterial(&varWeaponDef->camoWorldModelMaterialOverride);
	LoadMaterial(&varWeaponDef->camoViewModelMaterialOverride);
	if (Follows(&varWeaponDef->camoMaterialTarget, 8))
	{
		varMaterialHandle = varWeaponDef->camoMaterialTarget;
		Load_MaterialHandleArray(true, 0x3F);
	}
	if (Follows(&varWeaponDef->szXAnimsRightHanded, 8))
	{
		varXAnimPartsPtr = varWeaponDef->szXAnimsRightHanded;
		Load_XAnimPartsPtrArray(true, 0x7C);
	}
	if (Follows(&varWeaponDef->szXAnimsLeftHanded, 8))
	{
		varXAnimPartsPtr = varWeaponDef->szXAnimsLeftHanded;
		Load_XAnimPartsPtrArray(true, 0x7C);
	}
	LoadXString(&varWeaponDef->szModeName);
	if (Follows(&varWeaponDef->notetrackSoundMapKeys, 4))
	{
		varscr_string_t = varWeaponDef->notetrackSoundMapKeys;
		LoadScriptStrings(true, 0x18);
	}
	if (Follows(&varWeaponDef->notetrackSoundMapValues, 4))
	{
		varscr_string_t = varWeaponDef->notetrackSoundMapValues;
		LoadScriptStrings(true, 0x18);
	}
	if (Follows(&varWeaponDef->notetrackRumbleMapKeys, 4))
	{
		varscr_string_t = varWeaponDef->notetrackRumbleMapKeys;
		LoadScriptStrings(true, 0x10);
	}
	if (Follows(&varWeaponDef->notetrackRumbleMapValues, 4))
	{
		varscr_string_t = varWeaponDef->notetrackRumbleMapValues;
		LoadScriptStrings(true, 0x10);
	}
	if (Follows(&varWeaponDef->notetrackFXMapKeys, 4))
	{
		varscr_string_t = varWeaponDef->notetrackFXMapKeys;
		LoadScriptStrings(true, 0x10);
	}
	if (Follows(&varWeaponDef->notetrackFXMapValues, 8))
	{
		varFxEffectDefHandle = (const FxEffectDef **)varWeaponDef->notetrackFXMapValues;
		Load_FxEffectDefHandleArray(true, 0x10);
	}
	if (Follows(&varWeaponDef->notetrackFXMapTagValues, 4))
	{
		varscr_string_t = varWeaponDef->notetrackFXMapTagValues;
		LoadScriptStrings(true, 0x10);
	}
	LoadEffect(&varWeaponDef->viewFlashEffect);
	LoadEffect(&varWeaponDef->worldFlashEffect);
	LoadEffect(&varWeaponDef->viewFlashADSEffect);
	LoadSound(&varWeaponDef->pickupSound);
	LoadSound(&varWeaponDef->pickupSoundPlayer);
	LoadSound(&varWeaponDef->ammoPickupSound);
	LoadSound(&varWeaponDef->ammoPickupSoundPlayer);
	LoadSound(&varWeaponDef->projectileSound);
	LoadSound(&varWeaponDef->pullbackSound);
	LoadSound(&varWeaponDef->pullbackSoundPlayer);
	LoadSound(&varWeaponDef->fireSound);
	LoadSound(&varWeaponDef->fireSoundPlayer);
	LoadSound(&varWeaponDef->fireSoundPlayerAkimbo);
	LoadSound(&varWeaponDef->fireLoopSound);
	LoadSound(&varWeaponDef->fireLoopSoundPlayer);
	LoadSound(&varWeaponDef->fireStopSound);
	LoadSound(&varWeaponDef->fireStopSoundPlayer);
	LoadSound(&varWeaponDef->fireLastSound);
	LoadSound(&varWeaponDef->fireLastSoundPlayer);
	LoadSound(&varWeaponDef->emptyFireSound);
	LoadSound(&varWeaponDef->emptyFireSoundPlayer);
	LoadSound(&varWeaponDef->meleeSwipeSound);
	LoadSound(&varWeaponDef->meleeSwipeSoundPlayer);
	LoadSound(&varWeaponDef->meleeHitSound);
	LoadSound(&varWeaponDef->meleeMissSound);
	LoadSound(&varWeaponDef->rechamberSound);
	LoadSound(&varWeaponDef->rechamberSoundPlayer);
	LoadSound(&varWeaponDef->reloadSound);
	LoadSound(&varWeaponDef->reloadSoundPlayer);
	LoadSound(&varWeaponDef->reloadEmptySound);
	LoadSound(&varWeaponDef->reloadEmptySoundPlayer);
	LoadSound(&varWeaponDef->reloadStartSound);
	LoadSound(&varWeaponDef->reloadStartSoundPlayer);
	LoadSound(&varWeaponDef->reloadEndSound);
	LoadSound(&varWeaponDef->reloadEndSoundPlayer);
	LoadSound(&varWeaponDef->detonateSound);
	LoadSound(&varWeaponDef->detonateSoundPlayer);
	LoadSound(&varWeaponDef->nightVisionWearSound);
	LoadSound(&varWeaponDef->nightVisionWearSoundPlayer);
	LoadSound(&varWeaponDef->nightVisionRemoveSound);
	LoadSound(&varWeaponDef->nightVisionRemoveSoundPlayer);
	LoadSound(&varWeaponDef->altSwitchSound);
	LoadSound(&varWeaponDef->altSwitchSoundPlayer);
	LoadSound(&varWeaponDef->raiseSound);
	LoadSound(&varWeaponDef->raiseSoundPlayer);
	LoadSound(&varWeaponDef->firstRaiseSound);
	LoadSound(&varWeaponDef->firstRaiseSoundPlayer);
	LoadSound(&varWeaponDef->putawaySound);
	LoadSound(&varWeaponDef->putawaySoundPlayer);
	LoadSound(&varWeaponDef->scanSound);
	LoadSound(&varWeaponDef->changeVariableZoomSound);
	if (Follows(&varWeaponDef->bounceSound, 8))
	{
		varsnd_alias_list_name = varWeaponDef->bounceSound;
		LoadSounds(true, 0x1F);
	}
	if (Follows(&varWeaponDef->rollingSound, 8))
	{
		varsnd_alias_list_name = varWeaponDef->rollingSound;
		LoadSounds(true, 0x1F);
	}
	LoadEffect(&varWeaponDef->viewShellEjectEffect);
	LoadEffect(&varWeaponDef->worldShellEjectEffect);
	LoadEffect(&varWeaponDef->viewLastShotEjectEffect);
	LoadEffect(&varWeaponDef->worldLastShotEjectEffect);
	LoadEffect(&varWeaponDef->viewMagEjectEffect);
	LoadMaterial(&varWeaponDef->reticleCenter);
	LoadMaterial(&varWeaponDef->reticleSide);
	if (Follows(&varWeaponDef->worldModel, 8))
	{
		varXModelPtr = varWeaponDef->worldModel;
		Load_XModelPtrArray(true, 0x40);
	}
	LoadModel(&varWeaponDef->worldClipModel);
	LoadModel(&varWeaponDef->rocketModel);
	LoadModel(&varWeaponDef->knifeModel);
	LoadModel(&varWeaponDef->worldKnifeModel);
	LoadMaterial(&varWeaponDef->hudIcon);
	LoadMaterial(&varWeaponDef->pickupIcon);
	LoadMaterial(&varWeaponDef->ammoCounterIcon);
	LoadXString(&varWeaponDef->szAmmoName);
	LoadXString(&varWeaponDef->szClipName);
	LoadXString(&varWeaponDef->szSharedAmmoCapName);
	varADSOverlay = &varWeaponDef->overlay;
	Load_ADSOverlay(false);
	varPhysCollmapPtr = &varWeaponDef->physCollmap;
	Load_PhysCollmapPtr(false);
	LoadXString(&varWeaponDef->projectileName);
	LoadModel(&varWeaponDef->projectileModel);
	LoadEffect(&varWeaponDef->projExplosionEffect);
	LoadEffect(&varWeaponDef->projDudEffect);
	LoadSound(&varWeaponDef->projExplosionSound);
	LoadSound(&varWeaponDef->projDudSound);
	if (Follows(&varWeaponDef->parallelBounce, 4))
	{
		varfloat = varWeaponDef->parallelBounce;
		Load_Stream(true, varfloat, 0x7C);
	}
	if (Follows(&varWeaponDef->perpendicularBounce, 4))
	{
		varfloat = varWeaponDef->perpendicularBounce;
		Load_Stream(true, varfloat, 0x7C);
	}
	LoadEffect(&varWeaponDef->projTrailEffect);
	LoadEffect(&varWeaponDef->projBeaconEffect);
	LoadEffect(&varWeaponDef->projIgnitionEffect);
	LoadSound(&varWeaponDef->projIgnitionSound);
	LoadXString(&varWeaponDef->accuracyGraphName[0]);
	if (Follows(&varWeaponDef->originalAccuracyGraphKnots[0], 4))
	{
		varvec2_t = varWeaponDef->originalAccuracyGraphKnots[0];
		Load_Stream(true, varvec2_t, sizeof(vec2_t) * varWeaponCompleteDef->accuracyGraphKnotCount[0]);
	}
	LoadXString(&varWeaponDef->accuracyGraphName[1]);
	if (Follows(&varWeaponDef->originalAccuracyGraphKnots[1], 4))
	{
		varvec2_t = varWeaponDef->originalAccuracyGraphKnots[1];
		Load_Stream(true, varvec2_t, sizeof(vec2_t) * varWeaponCompleteDef->accuracyGraphKnotCount[1]);
	}
	LoadXString(&varWeaponDef->szUseHintString);
	LoadXString(&varWeaponDef->dropHintString);
	LoadXString(&varWeaponDef->szScript);
	if (Follows(&varWeaponDef->locationDamageMultipliers, 4))
	{
		varfloat = varWeaponDef->locationDamageMultipliers;
		Load_Stream(true, varfloat, 0x58);
	}
	LoadXString(&varWeaponDef->fireRumble);
	LoadXString(&varWeaponDef->meleeImpactRumble);
	varTracerDefPtr = &varWeaponDef->tracerType;
	Load_TracerDefPtr(false);
	LoadSound(&varWeaponDef->turretOverheatSound);
	LoadEffect(&varWeaponDef->turretOverheatEffect);
	LoadXString(&varWeaponDef->turretBarrelSpinRumble);
	LoadSound(&varWeaponDef->turretBarrelSpinMaxSnd);
	varsnd_alias_list_name = varWeaponDef->turretBarrelSpinUpSnd;
	LoadSounds(false, 4);
	varsnd_alias_list_name = varWeaponDef->turretBarrelSpinDownSnd;
	LoadSounds(false, 4);
	LoadSound(&varWeaponDef->missileConeSoundAlias);
	LoadSound(&varWeaponDef->missileConeSoundAliasAtBase);
	varscr_string_t = &varWeaponDef->knifeAttachTagOverride;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	varscr_string_t = &varWeaponDef->stowTag;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	LoadModel(&varWeaponDef->stowOffsetModel);
}

// Store 14035A460. The override arrays' element loaders (Load_AnimOverrideEntryArray and the others in the server)
// are inlined.
void Load_WeaponCompleteDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varWeaponCompleteDef, sizeof(WeaponCompleteDef));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varWeaponCompleteDef->szInternalName);
	if (Follows(&varWeaponCompleteDef->weapDef, 4))
	{
		varWeaponDef = varWeaponCompleteDef->weapDef;
		Load_WeaponDef(true);
	}
	LoadXString(&varWeaponCompleteDef->szDisplayName);
	if (Follows(&varWeaponCompleteDef->hideTags, 4))
	{
		varscr_string_t = varWeaponCompleteDef->hideTags;
		LoadScriptStrings(true, 0x20);
	}
	if (Follows(&varWeaponCompleteDef->scopes, 8))
	{
		varWeaponAttachmentPtr = varWeaponCompleteDef->scopes;
		Load_WeaponAttachmentPtrArray(true, 6);
	}
	if (Follows(&varWeaponCompleteDef->underBarrels, 8))
	{
		varWeaponAttachmentPtr = varWeaponCompleteDef->underBarrels;
		Load_WeaponAttachmentPtrArray(true, 3);
	}
	if (Follows(&varWeaponCompleteDef->others, 8))
	{
		varWeaponAttachmentPtr = varWeaponCompleteDef->others;
		Load_WeaponAttachmentPtrArray(true, 8);
	}
	if (Follows(&varWeaponCompleteDef->szXAnims, 8))
	{
		varXAnimPartsPtr = varWeaponCompleteDef->szXAnims;
		Load_XAnimPartsPtrArray(true, 0x7C);
	}
	if (Follows(&varWeaponCompleteDef->animOverrides, 4))
	{
		varAnimOverrideEntry = varWeaponCompleteDef->animOverrides;
		unsigned long long count = varWeaponCompleteDef->numAnimOverrides;
		Load_Stream(true, varAnimOverrideEntry, sizeof(AnimOverrideEntry) * count);
		AnimOverrideEntry *entry = varAnimOverrideEntry;
		for (; count; count--)
		{
			varAnimOverrideEntry = entry;
			Load_Stream(false, entry, sizeof(AnimOverrideEntry));
			varXAnimPartsPtr = &varAnimOverrideEntry->overrideAnim;
			Load_XAnimPartsPtr(false);
			varXAnimPartsPtr = &varAnimOverrideEntry->altmodeAnim;
			Load_XAnimPartsPtr(false);
			entry++;
		}
	}
	if (Follows(&varWeaponCompleteDef->soundOverrides, 4))
	{
		varSoundOverrideEntry = varWeaponCompleteDef->soundOverrides;
		unsigned long long count = varWeaponCompleteDef->numSoundOverrides;
		Load_Stream(true, varSoundOverrideEntry, sizeof(SoundOverrideEntry) * count);
		SoundOverrideEntry *entry = varSoundOverrideEntry;
		for (; count; count--)
		{
			varSoundOverrideEntry = entry;
			Load_Stream(false, entry, sizeof(SoundOverrideEntry));
			LoadSound(&varSoundOverrideEntry->overrideSound);
			LoadSound(&varSoundOverrideEntry->altmodeSound);
			entry++;
		}
	}
	if (Follows(&varWeaponCompleteDef->fxOverrides, 4))
	{
		varFXOverrideEntry = varWeaponCompleteDef->fxOverrides;
		unsigned long long count = varWeaponCompleteDef->numFXOverrides;
		Load_Stream(true, varFXOverrideEntry, sizeof(FXOverrideEntry) * count);
		FXOverrideEntry *entry = varFXOverrideEntry;
		for (; count; count--)
		{
			varFXOverrideEntry = entry;
			Load_Stream(false, entry, sizeof(FXOverrideEntry));
			LoadEffect(&varFXOverrideEntry->overrideFX);
			LoadEffect(&varFXOverrideEntry->altmodeFX);
			entry++;
		}
	}
	if (Follows(&varWeaponCompleteDef->reloadOverrides, 4))
	{
		varReloadStateTimerEntry = varWeaponCompleteDef->reloadOverrides;
		Load_Stream(true, varReloadStateTimerEntry,
		            sizeof(ReloadStateTimerEntry) * (unsigned long long)varWeaponCompleteDef->numReloadStateTimerOverrides);
	}
	if (FollowsAlways(&varWeaponCompleteDef->notetrackOverrides, 4))
	{
		varNoteTrackToSoundEntry = varWeaponCompleteDef->notetrackOverrides;
		unsigned long long count = varWeaponCompleteDef->numNotetrackOverrides;
		Load_Stream(true, varNoteTrackToSoundEntry, sizeof(NoteTrackToSoundEntry) * count);
		NoteTrackToSoundEntry *entry = varNoteTrackToSoundEntry;
		for (; count; count--)
		{
			varNoteTrackToSoundEntry = entry;
			Load_NoteTrackToSoundEntry(false);
			entry++;
		}
	}
	LoadXString(&varWeaponCompleteDef->szAltWeaponName);
	LoadMaterial(&varWeaponCompleteDef->killIcon);
	LoadMaterial(&varWeaponCompleteDef->dpadIcon);
	if (Follows(&varWeaponCompleteDef->accuracyGraphKnots[0], 4))
	{
		varvec2_t = varWeaponCompleteDef->accuracyGraphKnots[0];
		Load_Stream(true, varvec2_t, sizeof(vec2_t) * varWeaponCompleteDef->accuracyGraphKnotCount[0]);
	}
	if (Follows(&varWeaponCompleteDef->accuracyGraphKnots[1], 4))
	{
		varvec2_t = varWeaponCompleteDef->accuracyGraphKnots[1];
		Load_Stream(true, varvec2_t, sizeof(vec2_t) * varWeaponCompleteDef->accuracyGraphKnotCount[1]);
	}
	LoadXString(&varWeaponCompleteDef->szAdsrBaseSetting);
	DB_PopStreamPos();
}

// Store 14035ACA0
void Load_WeaponCompleteDefPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varWeaponCompleteDefPtr, sizeof(WeaponCompleteDef *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	WeaponCompleteDef **ptr = varWeaponCompleteDefPtr;
	unsigned long long value = (unsigned long long)*varWeaponCompleteDefPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varWeaponCompleteDefPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varWeaponCompleteDefPtr = (WeaponCompleteDef *)g_streamPos;
		varWeaponCompleteDef = (WeaponCompleteDef *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_WeaponCompleteDef(true);
		Load_WeaponCompleteDefAsset(ptr);
		if (inserted)
			*(WeaponCompleteDef **)inserted = *ptr;
	}
	DB_PopStreamPos();
}

// ==== vehicles ====================================================================================================

// Store 140359240
void Load_VehiclePhysDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varVehiclePhysDef, sizeof(VehiclePhysDef));
	LoadXString(&varVehiclePhysDef->physPresetName);
	varPhysPresetPtr = &varVehiclePhysDef->physPreset;
	Load_PhysPresetPtr(false);
	LoadXString(&varVehiclePhysDef->accelGraphName);
}

// Store 140358960
void Load_VehicleDef(bool atStreamStart)
{
	Load_Stream(atStreamStart, varVehicleDef, sizeof(VehicleDef));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varVehicleDef->name);
	LoadXString(&varVehicleDef->useHintString);
	varVehiclePhysDef = &varVehicleDef->vehPhysDef;
	Load_VehiclePhysDef(false);
	LoadEffect(&varVehicleDef->vehHelicopterGroundFx);
	LoadEffect(&varVehicleDef->vehHelicopterGroundWaterFx);
	LoadXString(&varVehicleDef->turretWeaponName);
	varWeaponCompleteDefPtr = &varVehicleDef->turretWeapon;
	Load_WeaponCompleteDefPtr(false);
	LoadSound(&varVehicleDef->turretSpinSnd);
	LoadSound(&varVehicleDef->turretStopSnd);
	varscr_string_t = varVehicleDef->trophyTags;
	LoadScriptStrings(false, 4);
	LoadEffect(&varVehicleDef->trophyExplodeFx);
	LoadEffect(&varVehicleDef->trophyFlashFx);
	LoadMaterial(&varVehicleDef->compassFriendlyIcon);
	LoadMaterial(&varVehicleDef->compassEnemyIcon);
	LoadMaterial(&varVehicleDef->compassFriendlyAltIcon);
	LoadMaterial(&varVehicleDef->compassEnemyAltIcon);
	LoadSound(&varVehicleDef->idleLowSnd);
	LoadSound(&varVehicleDef->idleHighSnd);
	LoadSound(&varVehicleDef->engineLowSnd);
	LoadSound(&varVehicleDef->engineHighSnd);
	varscr_string_t = &varVehicleDef->audioOriginTag;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	LoadSound(&varVehicleDef->idleLowSndAlt);
	LoadSound(&varVehicleDef->idleHighSndAlt);
	LoadSound(&varVehicleDef->engineLowSndAlt);
	LoadSound(&varVehicleDef->engineHighSndAlt);
	varscr_string_t = &varVehicleDef->audioOriginTagAlt;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	LoadSound(&varVehicleDef->turretSpinSndAlt);
	LoadSound(&varVehicleDef->turretStopSndAlt);
	LoadSound(&varVehicleDef->engineStartUpSnd);
	LoadSound(&varVehicleDef->engineShutdownSnd);
	LoadSound(&varVehicleDef->engineIdleSnd);
	LoadSound(&varVehicleDef->engineSustainSnd);
	LoadSound(&varVehicleDef->engineRampUpSnd);
	LoadSound(&varVehicleDef->engineRampDownSnd);
	LoadSound(&varVehicleDef->suspensionSoftSnd);
	LoadSound(&varVehicleDef->suspensionHardSnd);
	LoadSound(&varVehicleDef->collisionSnd);
	LoadSound(&varVehicleDef->speedSnd);
	LoadXString(&varVehicleDef->surfaceSndPrefix);
	varsnd_alias_list_name = varVehicleDef->surfaceSnds;
	LoadSounds(false, 0x1F);
	LoadXString(&varVehicleDef->soundTriggerOverrideZone);
	DB_PopStreamPos();
}

// Store 140359150
void Load_VehicleDefPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varVehicleDefPtr, sizeof(VehicleDef *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	VehicleDef **ptr = varVehicleDefPtr;
	unsigned long long value = (unsigned long long)*varVehicleDefPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varVehicleDefPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varVehicleDefPtr = (VehicleDef *)g_streamPos;
		varVehicleDef = (VehicleDef *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_VehicleDef(true);
		Load_VehicleDefAsset(ptr);
		if (inserted)
			*(VehicleDef **)inserted = *ptr;
	}
	DB_PopStreamPos();
}
