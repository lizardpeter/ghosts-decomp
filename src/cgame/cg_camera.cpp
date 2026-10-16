// cgame/cg_camera.cpp
//
// Client-only, from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names follow
// Black Ops' cgame/cg_camera.cpp (black-ops-1-decomp, from its server PDB); line numbers are unknown.
//
// The view's field of view, once a frame: CG_GetViewFov (Store 1402E8D20) picks the FOV (cg_fov, blended toward
// the weapon's ADS FOV, times cg_fovScale, clamped to [cg_fovMin, 170]) and CG_CalcFov turns it into the refdef's
// tangents. cg_fov is the horizontal FOV of a 4:3 view: tan(fovY / 2) = 0.75 * tan(cg_fov / 2) whatever the
// window's shape, and the horizontal FOV widens with the aspect ratio (Hor+).

#include <math.h>

#include "cgame_mp/cg_local_mp.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "cgame/cg_camera.cpp"

// cgame_mp/cg_main_mp.cpp
extern const dvar_t *cg_fov;
extern const dvar_t *cg_fovScale;
extern const dvar_t *cg_fovMin;
extern const dvar_t *missileRemoteFOV;

// Set by sub_14017F070 and others; name unknown.
extern int unk_143D33E80;   // nonzero: no ADS zoom-in
extern bool unk_143D33E84;  // the zoom is held fully in

struct playerState_s;
void sub_140532D80(float fovX, float aspect, float *tanHalfFovX, float *tanHalfFovY);  // universal/com_math.cpp
Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
float BG_ADSZoomFov(const playerState_s *ps, Weapon weapon, bool isAlternate);
bool BG_CanHybridToggle(const playerState_s *ps, Weapon weapon, bool isAlternate);
bool BG_IsThirdPersonMode(const playerState_s *ps);
float CG_GetWeaponZoom(const cg_s *cgameGlob, Weapon weapon);
float sub_140288830(const playerState_s *ps, Weapon weapon, bool isAlternate, bool second);  // a hybrid scope's FOVs (name unknown)
bool sub_140294880(const playerState_s *ps);              // bgame: ADS zoom is held back (name unknown)
bool sub_14028FDA0(Weapon weapon, bool isAlternate);       // bgame: the weapon zooms when aiming (name unknown)
float sub_1402869E0(const playerState_s *ps, Weapon weapon);  // bgame: a variable-zoom scope's FOV, or 0 (name unknown)
bool sub_1405B7A60(LocalClientNum_t localClientNum);       // a remote camera with its own FOV (name unknown)
float sub_1405B6C50(LocalClientNum_t localClientNum);      // that camera's FOV (name unknown)
bool sub_1405B7890(LocalClientNum_t localClientNum);       // (name unknown)
float sub_1405B7B10(const cg_s *cgameGlob, float fov);     // fov plus a per-entity offset (name unknown)
int sub_140187D70(LocalClientNum_t localClientNum);        // (name unknown)
float sub_140187060(LocalClientNum_t localClientNum, float fov);  // (name unknown)

static_assert(__builtin_offsetof(cg_s, frametime) == 0x7188C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdef_tanHalfFovX) == 0x718D8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdef_tanHalfFovY) == 0x718DC, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, zoomSensitivity) == 0xB1B18, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, ps_otherFlags) == 0x10, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, ps_linkFlags) == 0x14, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, ps_eFlags) == 0x124, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, ps_weapon) == 0x41C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, ps_weapFlags) == 0x420, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, hybridScopeState) == 0xB4EF8, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, remoteMissileCam) == 0x10E79F, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, scriptedViewFov) == 0x10EDC4, "cg_s layout");
static_assert(__builtin_offsetof(cgs_t, viewAspect) == 0x10, "cgs_t layout");
static_assert(__builtin_offsetof(cgs_t, viewMult) == 0x14, "cgs_t layout");

// Store 1402E9060 (name unknown): a distance scale for the current zoom, about 1 at cg_fov 65 and smaller when
// zoomed in; the caller (Store 1405B97F0) multiplies a distance by it before comparing it with a dvar's limit.
float sub_1402E9060()
{
	return cgArray[0].refdef_tanHalfFovY * 2.118673f / cg_fovScale->current.value;
}

// Store 1402E8D20 (Black Ops: cgame/cg_camera.cpp:912)
float CG_GetViewFov(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const playerState_s *ps = (const playerState_s *)cgameGlob;  // predictedPlayerState comes first
	const Weapon weapon = BG_GetViewmodelWeapon(ps);
	const bool isAlternate = (cgameGlob->ps_weapFlags >> 14) & 1;
	float fov;
	if (cgameGlob->ps_pm_type == 6)
	{
		fov = 90.0f;
	}
	else if ((cgameGlob->ps_linkFlags & 4) && (unsigned char)weapon.data)
	{
		fov = BG_ADSZoomFov(ps, weapon, isAlternate);
	}
	else if (cgameGlob->remoteMissileCam)
	{
		fov = missileRemoteFOV->current.value;
	}
	else if (sub_1405B7A60(localClientNum))
	{
		fov = sub_1405B6C50(localClientNum);
	}
	else if (cgameGlob->ps_eFlags & 0x3800)
	{
		fov = cgameGlob->scriptedViewFov;
	}
	else if (cgameGlob->ps_otherFlags & 0x200000)
	{
		fov = cgameGlob->scriptedViewFov;
	}
	else if (BG_CanHybridToggle(ps, weapon, isAlternate) && !sub_140294880(ps) && cgameGlob->hybridScopeState > 1)
	{
		const float first = sub_140288830(ps, weapon, isAlternate, false);
		const float second = sub_140288830(ps, weapon, isAlternate, true);
		switch (cgameGlob->hybridScopeState)
		{
		case 2:
			fov = first;
			break;
		case 3:
			fov = second;
			break;
		case 4:
			fov = (1.0f - cgameGlob->hybridScopeFrac) * first + cgameGlob->hybridScopeFrac * second;
			break;
		case 5:
			fov = (1.0f - cgameGlob->hybridScopeFrac) * second + cgameGlob->hybridScopeFrac * first;
			break;
		default:
			fov = cg_fov->current.value;
			break;
		}
	}
	else
	{
		fov = cg_fov->current.value;
		if (!unk_143D33E80 && sub_14028FDA0(weapon, isAlternate))
		{
			float zoomFov = sub_1402869E0(ps, weapon);
			if (zoomFov == 0.0f)
				zoomFov = BG_ADSZoomFov(ps, weapon, isAlternate);
			const float adsFov = fov < zoomFov ? fov : zoomFov;
			float zoom = CG_GetWeaponZoom(cgameGlob, weapon);
			if (unk_143D33E84)
				zoom = 1.0f;
			else if (sub_140294880(ps))
				zoom = 0.0f;
			fov = (1.0f - zoom) * fov + zoom * adsFov;
		}
	}
	fov *= cg_fovScale->current.value;
	if (BG_IsThirdPersonMode(ps))
		fov *= 0.89999998f;
	if (sub_1405B7890(localClientNum))
		fov = sub_1405B7B10(cgameGlob, fov);
	if (sub_140187D70(localClientNum))
		fov = sub_140187060(localClientNum, fov);
	const float fovMin = cg_fovMin->current.value;
	fov = fovMin > fov ? fovMin : fov;
	return fov < 170.0f ? fov : 170.0f;
}

// Store 1402EB4D0. Black Ops' version also fetches the FOV itself when given 0 and applies the camera tween; the
// Store build's callers do that first.
void CG_CalcFov(LocalClientNum_t localClientNum, float fov_x)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	cgs_t *cgs = CG_GetLocalClientStaticGlobals(localClientNum);
	sub_140532D80(fov_x, cgs->viewAspect * cgs->viewMult, &cgameGlob->refdef_tanHalfFovX,
	              &cgameGlob->refdef_tanHalfFovY);
	// 0.63707024 = tan(65 / 2): sensitivity is relative to the default FOV
	cgameGlob->zoomSensitivity = (float)tan((double)(fov_x * 0.017453292f * 0.5f)) / 0.63707024f;
}
