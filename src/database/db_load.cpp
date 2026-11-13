// database/db_load.cpp (Store build)
//
// The generated top of the zone loader: the script string list, XGlobals, the XAsset array and the dispatch of each
// asset to its Load_<Type>Ptr. Names: the PS4/Xbox One server PDBs (db_load.obj; the line records place the code in
// the generated headers db_assetlist_load_db.h and db_primtypes_load_db.h). The Store build's Load_XAssetHeader
// tests the types in the PS4 order with the same variables; ui_map, aitype, mptype, character and xmodelalias
// have no case (nothing is loaded for them). docs/fastfiles.md describes the stream rules these follow.

#include "database/db_local.h"

struct AddonMapEnts;
struct AnimationClass;
struct Colorization;
struct ColorizationSet;
struct ComWorld;
struct ComputeShader;
struct DopplerPreset;
struct EquipmentSoundTable;
struct Font_s;
struct FxEffectDef;
struct FxImpactTable;
struct FxParticleSimAnimation;
struct FxWorld;
struct GfxImage;
struct GfxLightDef;
struct GfxWorld;
struct GlassWorld;
struct LeaderboardDef;
struct LoadedSound;
struct LocalizeEntry;
struct LuaFile;
struct MapEnts;
struct Material;
struct MaterialDomainShader;
struct MaterialHullShader;
struct MaterialPixelShader;
struct MaterialTechniqueSet;
struct MaterialVertexDeclaration;
struct MaterialVertexShader;
struct MenuList;
struct NetConstStrings;
struct PathData;
struct PhysCollmap;
struct PhysPreset;
struct RawFile;
struct ReverbPreset;
struct ScriptFile;
struct ScriptableDef;
struct SndCurve;
struct SndDriverGlobals;
struct StringTable;
struct StructuredDataDefSet;
struct SurfaceFxTable;
struct ToneMapping;
struct TracerDef;
struct VectorField;
struct VehicleDef;
struct VehicleTrack;
struct WeaponAttachment;
struct WeaponCompleteDef;
struct XAnimParts;
struct XModel;
struct XModelSurfs;
struct clipMap_t;
struct menuDef_t;
struct snd_alias_list_t;

extern PhysPreset **varPhysPresetPtr;
extern PhysCollmap **varPhysCollmapPtr;
extern XAnimParts **varXAnimPartsPtr;
extern XModelSurfs **varXModelSurfsPtr;
extern XModel **varXModelPtr;
extern Material **varMaterialHandle;
extern ComputeShader **varComputeShaderPtr;
extern MaterialPixelShader **varMaterialPixelShaderPtr;
extern MaterialVertexShader **varMaterialVertexShaderPtr;
extern MaterialHullShader **varMaterialHullShaderPtr;
extern MaterialDomainShader **varMaterialDomainShaderPtr;
extern MaterialVertexDeclaration **varMaterialVertexDeclarationPtr;
extern MaterialTechniqueSet **varMaterialTechniqueSetPtr;
extern GfxImage **varGfxImagePtr;
extern snd_alias_list_t **varsnd_alias_list_ptr;
extern SndCurve **varSndCurvePtr;
extern SndCurve **varLpfCurvePtr;
extern SndCurve **varReverbCurvePtr;
extern LoadedSound **varLoadedSoundPtr;
extern clipMap_t **varclipMap_ptr;
extern ComWorld **varComWorldPtr;
extern GlassWorld **varGlassWorldPtr;
extern PathData **varPathDataPtr;
extern VehicleTrack **varVehicleTrackPtr;
extern MapEnts **varMapEntsPtr;
extern FxWorld **varFxWorldPtr;
extern GfxWorld **varGfxWorldPtr;
extern GfxLightDef **varGfxLightDefPtr;
extern Font_s **varFontHandle;
extern MenuList **varMenuListPtr;
extern menuDef_t **varmenuDef_ptr;
extern AnimationClass **varAnimationClassPtr;
extern LocalizeEntry **varLocalizeEntryPtr;
extern WeaponAttachment **varWeaponAttachmentPtr;
extern WeaponCompleteDef **varWeaponCompleteDefPtr;
extern SndDriverGlobals **varSndDriverGlobalsPtr;
extern const FxEffectDef **varFxEffectDefHandle;
extern FxImpactTable **varFxImpactTablePtr;
extern SurfaceFxTable **varSurfaceFxTablePtr;
extern RawFile **varRawFilePtr;
extern ScriptFile **varScriptFilePtr;
extern StringTable **varStringTablePtr;
extern LeaderboardDef **varLeaderboardDefPtr;
extern StructuredDataDefSet **varStructuredDataDefSetPtr;
extern TracerDef **varTracerDefPtr;
extern VehicleDef **varVehicleDefPtr;
extern AddonMapEnts **varAddonMapEntsPtr;
extern NetConstStrings **varNetConstStringsPtr;
extern ReverbPreset **varReverbPresetPtr;
extern LuaFile **varLuaFilePtr;
extern ScriptableDef **varScriptableDefPtr;
extern Colorization **varColorizationPtr;
extern ColorizationSet **varColorizationSetPtr;
extern ToneMapping **varToneMappingPtr;
extern EquipmentSoundTable **varEquipmentSoundTablePtr;
extern VectorField **varVectorFieldPtr;
extern DopplerPreset **varDopplerPresetPtr;
extern FxParticleSimAnimation **varFxParticleSimAnimationPtr;

void Load_PhysPresetPtr(bool atStreamStart);
void Load_PhysCollmapPtr(bool atStreamStart);
void Load_XAnimPartsPtr(bool atStreamStart);
void Load_XModelSurfsPtr(bool atStreamStart);
void Load_XModelPtr(bool atStreamStart);
void Load_MaterialHandle(bool atStreamStart);
void Load_ComputeShaderPtr(bool atStreamStart);
void Load_MaterialPixelShaderPtr(bool atStreamStart);
void Load_MaterialVertexShaderPtr(bool atStreamStart);
void Load_MaterialHullShaderPtr(bool atStreamStart);
void Load_MaterialDomainShaderPtr(bool atStreamStart);
void Load_MaterialVertexDeclarationPtr(bool atStreamStart);
void Load_MaterialTechniqueSetPtr(bool atStreamStart);
void Load_GfxImagePtr(bool atStreamStart);
void Load_snd_alias_list_ptr(bool atStreamStart);
void Load_SndCurvePtr(bool atStreamStart);
void Load_LpfCurvePtr(bool atStreamStart);
void Load_ReverbCurvePtr(bool atStreamStart);
void Load_LoadedSoundPtr(bool atStreamStart);
void Load_clipMap_ptr(bool atStreamStart);
void Load_ComWorldPtr(bool atStreamStart);
void Load_GlassWorldPtr(bool atStreamStart);
void Load_PathDataPtr(bool atStreamStart);
void Load_VehicleTrackPtr(bool atStreamStart);
void Load_MapEntsPtr(bool atStreamStart);
void Load_FxWorldPtr(bool atStreamStart);
void Load_GfxWorldPtr(bool atStreamStart);
void Load_GfxLightDefPtr(bool atStreamStart);
void Load_FontHandle(bool atStreamStart);
void Load_MenuListPtr(bool atStreamStart);
void Load_menuDef_ptr(bool atStreamStart);
void Load_AnimationClassPtr(bool atStreamStart);
void Load_LocalizeEntryPtr(bool atStreamStart);
void Load_WeaponAttachmentPtr(bool atStreamStart);
void Load_WeaponCompleteDefPtr(bool atStreamStart);
void Load_SndDriverGlobalsPtr(bool atStreamStart);
void Load_FxEffectDefHandle(bool atStreamStart);
void Load_FxImpactTablePtr(bool atStreamStart);
void Load_SurfaceFxTablePtr(bool atStreamStart);
void Load_RawFilePtr(bool atStreamStart);
void Load_ScriptFilePtr(bool atStreamStart);
void Load_StringTablePtr(bool atStreamStart);
void Load_LeaderboardDefPtr(bool atStreamStart);
void Load_StructuredDataDefSetPtr(bool atStreamStart);
void Load_TracerDefPtr(bool atStreamStart);
void Load_VehicleDefPtr(bool atStreamStart);
void Load_AddonMapEntsPtr(bool atStreamStart);
void Load_NetConstStringsPtr(bool atStreamStart);
void Load_ReverbPresetPtr(bool atStreamStart);
void Load_LuaFilePtr(bool atStreamStart);
void Load_ScriptableDefPtr(bool atStreamStart);
void Load_ColorizationPtr(bool atStreamStart);
void Load_ColorizationSetPtr(bool atStreamStart);
void Load_ToneMappingPtr(bool atStreamStart);
void Load_EquipmentSoundTablePtr(bool atStreamStart);
void Load_VectorFieldPtr(bool atStreamStart);
void Load_DopplerPresetPtr(bool atStreamStart);
void Load_FxParticleSimAnimationPtr(bool atStreamStart);

extern XGlobals *varXGlobals;
extern XGfxGlobals *varXGfxGlobals;
extern XAssetHeader *varXAssetHeader;
void Load_XGfxGlobals(bool atStreamStart);
void Load_XAssetHeader(bool atStreamStart);

// Store 140355E20 (PS4 PDB Load_ScriptStringList, db_primtypes_load_db.h:6905, with Load_TempStringArray and
// Load_TempString inlined): the list's strings, in the virtual block, each inline (-1: a temp string, made a script
// string) or an offset.
void Load_ScriptStringList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varScriptStringList, 0x10);
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	if (varScriptStringList->strings)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 7) & ~7ull);
		varScriptStringList->strings = (const char **)g_streamPos;
		varTempString = (const char **)g_streamPos;
		long long count = varScriptStringList->count;
		Load_Stream(true, g_streamPos, count * 8);
		const char **str = varTempString;
		for (; count; --count, ++str)
		{
			varTempString = str;
			Load_Stream(false, str, 8);
			if (!*varTempString)
				continue;
			if ((unsigned long long)*varTempString == DB_PTR_INLINE)
			{
				*varTempString = (const char *)g_streamPos;
				varConstChar = (const char *)g_streamPos;
				Load_TempStringCustom(varTempString);
			}
			else
			{
				DB_ConvertOffsetToPointer((unsigned long long *)varTempString);
			}
		}
	}
	DB_PopStreamPos();
}

// Store 14035DF80 (PS4 PDB Load_XGlobalsPtr, db_assetlist_load_db.h:3294): any non-null pointer means inline.
void Load_XGlobalsPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXGlobalsPtr, 8);
	if (!*varXGlobalsPtr)
		return;
	g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
	*varXGlobalsPtr = (XGlobals *)g_streamPos;
	varXGlobals = (XGlobals *)g_streamPos;
	Load_Stream(true, g_streamPos, 8);
	if (!varXGlobals->gfxGlobals)
		return;
	g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
	varXGlobals->gfxGlobals = (XGfxGlobals *)g_streamPos;
	varXGfxGlobals = (XGfxGlobals *)g_streamPos;
	Load_XGfxGlobals(true);
}

// Store 14034A060 (PS4 PDB AllocLoad_XAsset): the XAsset array's place, 4-aligned.
XAsset *AllocLoad_XAsset()
{
	g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
	return (XAsset *)g_streamPos;
}

// Store 14035D5F0 (PS4 PDB Load_XAsset, db_assetlist_load_db.h:2974)
void Load_XAsset(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXAsset, sizeof(XAsset));
	varXAssetHeader = &varXAsset->header;
	Load_XAssetHeader(false);
}

// Store 14035D630 (PS4 PDB Load_XAssetHeader, db_assetlist_load_db.h:1534)
void Load_XAssetHeader(bool atStreamStart)
{
	switch (varXAsset->type)
	{
	case ASSET_TYPE_PHYSPRESET:
		varPhysPresetPtr = (PhysPreset **)varXAssetHeader;
		Load_PhysPresetPtr(atStreamStart);
		return;
	case ASSET_TYPE_PHYSCOLLMAP:
		varPhysCollmapPtr = (PhysCollmap **)varXAssetHeader;
		Load_PhysCollmapPtr(atStreamStart);
		return;
	case ASSET_TYPE_XANIMPARTS:
		varXAnimPartsPtr = (XAnimParts **)varXAssetHeader;
		Load_XAnimPartsPtr(atStreamStart);
		return;
	case ASSET_TYPE_XMODEL_SURFS:
		varXModelSurfsPtr = (XModelSurfs **)varXAssetHeader;
		Load_XModelSurfsPtr(atStreamStart);
		return;
	case ASSET_TYPE_XMODEL:
		varXModelPtr = (XModel **)varXAssetHeader;
		Load_XModelPtr(atStreamStart);
		return;
	case ASSET_TYPE_MATERIAL:
		varMaterialHandle = (Material **)varXAssetHeader;
		Load_MaterialHandle(atStreamStart);
		return;
	case ASSET_TYPE_COMPUTESHADER:
		varComputeShaderPtr = (ComputeShader **)varXAssetHeader;
		Load_ComputeShaderPtr(atStreamStart);
		return;
	case ASSET_TYPE_PIXELSHADER:
		varMaterialPixelShaderPtr = (MaterialPixelShader **)varXAssetHeader;
		Load_MaterialPixelShaderPtr(atStreamStart);
		return;
	case ASSET_TYPE_VERTEXSHADER:
		varMaterialVertexShaderPtr = (MaterialVertexShader **)varXAssetHeader;
		Load_MaterialVertexShaderPtr(atStreamStart);
		return;
	case ASSET_TYPE_HULLSHADER:
		varMaterialHullShaderPtr = (MaterialHullShader **)varXAssetHeader;
		Load_MaterialHullShaderPtr(atStreamStart);
		return;
	case ASSET_TYPE_DOMAINSHADER:
		varMaterialDomainShaderPtr = (MaterialDomainShader **)varXAssetHeader;
		Load_MaterialDomainShaderPtr(atStreamStart);
		return;
	case ASSET_TYPE_VERTEXDECL:
		varMaterialVertexDeclarationPtr = (MaterialVertexDeclaration **)varXAssetHeader;
		Load_MaterialVertexDeclarationPtr(atStreamStart);
		return;
	case ASSET_TYPE_TECHNIQUE_SET:
		varMaterialTechniqueSetPtr = (MaterialTechniqueSet **)varXAssetHeader;
		Load_MaterialTechniqueSetPtr(atStreamStart);
		return;
	case ASSET_TYPE_IMAGE:
		varGfxImagePtr = (GfxImage **)varXAssetHeader;
		Load_GfxImagePtr(atStreamStart);
		return;
	case ASSET_TYPE_SOUND:
		varsnd_alias_list_ptr = (snd_alias_list_t **)varXAssetHeader;
		Load_snd_alias_list_ptr(atStreamStart);
		return;
	case ASSET_TYPE_SOUND_CURVE:
		varSndCurvePtr = (SndCurve **)varXAssetHeader;
		Load_SndCurvePtr(atStreamStart);
		return;
	case ASSET_TYPE_LPF_CURVE:
		varLpfCurvePtr = (SndCurve **)varXAssetHeader;
		Load_LpfCurvePtr(atStreamStart);
		return;
	case ASSET_TYPE_REVERB_CURVE:
		varReverbCurvePtr = (SndCurve **)varXAssetHeader;
		Load_ReverbCurvePtr(atStreamStart);
		return;
	case ASSET_TYPE_LOADED_SOUND:
		varLoadedSoundPtr = (LoadedSound **)varXAssetHeader;
		Load_LoadedSoundPtr(atStreamStart);
		return;
	case ASSET_TYPE_CLIPMAP:
		varclipMap_ptr = (clipMap_t **)varXAssetHeader;
		Load_clipMap_ptr(atStreamStart);
		return;
	case ASSET_TYPE_COMWORLD:
		varComWorldPtr = (ComWorld **)varXAssetHeader;
		Load_ComWorldPtr(atStreamStart);
		return;
	case ASSET_TYPE_GLASSWORLD:
		varGlassWorldPtr = (GlassWorld **)varXAssetHeader;
		Load_GlassWorldPtr(atStreamStart);
		return;
	case ASSET_TYPE_PATHDATA:
		varPathDataPtr = (PathData **)varXAssetHeader;
		Load_PathDataPtr(atStreamStart);
		return;
	case ASSET_TYPE_VEHICLE_TRACK:
		varVehicleTrackPtr = (VehicleTrack **)varXAssetHeader;
		Load_VehicleTrackPtr(atStreamStart);
		return;
	case ASSET_TYPE_MAP_ENTS:
		varMapEntsPtr = (MapEnts **)varXAssetHeader;
		Load_MapEntsPtr(atStreamStart);
		return;
	case ASSET_TYPE_FXWORLD:
		varFxWorldPtr = (FxWorld **)varXAssetHeader;
		Load_FxWorldPtr(atStreamStart);
		return;
	case ASSET_TYPE_GFXWORLD:
		varGfxWorldPtr = (GfxWorld **)varXAssetHeader;
		Load_GfxWorldPtr(atStreamStart);
		return;
	case ASSET_TYPE_LIGHT_DEF:
		varGfxLightDefPtr = (GfxLightDef **)varXAssetHeader;
		Load_GfxLightDefPtr(atStreamStart);
		return;
	case ASSET_TYPE_FONT:
		varFontHandle = (Font_s **)varXAssetHeader;
		Load_FontHandle(atStreamStart);
		return;
	case ASSET_TYPE_MENULIST:
		varMenuListPtr = (MenuList **)varXAssetHeader;
		Load_MenuListPtr(atStreamStart);
		return;
	case ASSET_TYPE_MENU:
		varmenuDef_ptr = (menuDef_t **)varXAssetHeader;
		Load_menuDef_ptr(atStreamStart);
		return;
	case ASSET_TYPE_ANIMCLASS:
		varAnimationClassPtr = (AnimationClass **)varXAssetHeader;
		Load_AnimationClassPtr(atStreamStart);
		return;
	case ASSET_TYPE_LOCALIZE_ENTRY:
		varLocalizeEntryPtr = (LocalizeEntry **)varXAssetHeader;
		Load_LocalizeEntryPtr(atStreamStart);
		return;
	case ASSET_TYPE_ATTACHMENT:
		varWeaponAttachmentPtr = (WeaponAttachment **)varXAssetHeader;
		Load_WeaponAttachmentPtr(atStreamStart);
		return;
	case ASSET_TYPE_WEAPON:
		varWeaponCompleteDefPtr = (WeaponCompleteDef **)varXAssetHeader;
		Load_WeaponCompleteDefPtr(atStreamStart);
		return;
	case ASSET_TYPE_SNDDRIVER_GLOBALS:
		varSndDriverGlobalsPtr = (SndDriverGlobals **)varXAssetHeader;
		Load_SndDriverGlobalsPtr(atStreamStart);
		return;
	case ASSET_TYPE_FX:
		varFxEffectDefHandle = (const FxEffectDef **)varXAssetHeader;
		Load_FxEffectDefHandle(atStreamStart);
		return;
	case ASSET_TYPE_IMPACT_FX:
		varFxImpactTablePtr = (FxImpactTable **)varXAssetHeader;
		Load_FxImpactTablePtr(atStreamStart);
		return;
	case ASSET_TYPE_SURFACE_FX:
		varSurfaceFxTablePtr = (SurfaceFxTable **)varXAssetHeader;
		Load_SurfaceFxTablePtr(atStreamStart);
		return;
	case ASSET_TYPE_RAWFILE:
		varRawFilePtr = (RawFile **)varXAssetHeader;
		Load_RawFilePtr(atStreamStart);
		return;
	case ASSET_TYPE_SCRIPTFILE:
		varScriptFilePtr = (ScriptFile **)varXAssetHeader;
		Load_ScriptFilePtr(atStreamStart);
		return;
	case ASSET_TYPE_STRINGTABLE:
		varStringTablePtr = (StringTable **)varXAssetHeader;
		Load_StringTablePtr(atStreamStart);
		return;
	case ASSET_TYPE_LEADERBOARD:
		varLeaderboardDefPtr = (LeaderboardDef **)varXAssetHeader;
		Load_LeaderboardDefPtr(atStreamStart);
		return;
	case ASSET_TYPE_STRUCTURED_DATA_DEF:
		varStructuredDataDefSetPtr = (StructuredDataDefSet **)varXAssetHeader;
		Load_StructuredDataDefSetPtr(atStreamStart);
		return;
	case ASSET_TYPE_TRACER:
		varTracerDefPtr = (TracerDef **)varXAssetHeader;
		Load_TracerDefPtr(atStreamStart);
		return;
	case ASSET_TYPE_VEHICLE:
		varVehicleDefPtr = (VehicleDef **)varXAssetHeader;
		Load_VehicleDefPtr(atStreamStart);
		return;
	case ASSET_TYPE_ADDON_MAP_ENTS:
		varAddonMapEntsPtr = (AddonMapEnts **)varXAssetHeader;
		Load_AddonMapEntsPtr(atStreamStart);
		return;
	case ASSET_TYPE_NET_CONST_STRINGS:
		varNetConstStringsPtr = (NetConstStrings **)varXAssetHeader;
		Load_NetConstStringsPtr(atStreamStart);
		return;
	case ASSET_TYPE_REVERB_PRESET:
		varReverbPresetPtr = (ReverbPreset **)varXAssetHeader;
		Load_ReverbPresetPtr(atStreamStart);
		return;
	case ASSET_TYPE_LUA_FILE:
		varLuaFilePtr = (LuaFile **)varXAssetHeader;
		Load_LuaFilePtr(atStreamStart);
		return;
	case ASSET_TYPE_SCRIPTABLE:
		varScriptableDefPtr = (ScriptableDef **)varXAssetHeader;
		Load_ScriptableDefPtr(atStreamStart);
		return;
	case ASSET_TYPE_COLORIZATION:
		varColorizationPtr = (Colorization **)varXAssetHeader;
		Load_ColorizationPtr(atStreamStart);
		return;
	case ASSET_TYPE_COLORIZATIONSET:
		varColorizationSetPtr = (ColorizationSet **)varXAssetHeader;
		Load_ColorizationSetPtr(atStreamStart);
		return;
	case ASSET_TYPE_TONEMAPPING:
		varToneMappingPtr = (ToneMapping **)varXAssetHeader;
		Load_ToneMappingPtr(atStreamStart);
		return;
	case ASSET_TYPE_EQUIPMENT_SND_TABLE:
		varEquipmentSoundTablePtr = (EquipmentSoundTable **)varXAssetHeader;
		Load_EquipmentSoundTablePtr(atStreamStart);
		return;
	case ASSET_TYPE_VECTORFIELD:
		varVectorFieldPtr = (VectorField **)varXAssetHeader;
		Load_VectorFieldPtr(atStreamStart);
		return;
	case ASSET_TYPE_DOPPLER_PRESET:
		varDopplerPresetPtr = (DopplerPreset **)varXAssetHeader;
		Load_DopplerPresetPtr(atStreamStart);
		return;
	case ASSET_TYPE_PARTICLE_SIM_ANIMATION:
		varFxParticleSimAnimationPtr = (FxParticleSimAnimation **)varXAssetHeader;
		Load_FxParticleSimAnimationPtr(atStreamStart);
		return;
	default:
		return;
	}
}
