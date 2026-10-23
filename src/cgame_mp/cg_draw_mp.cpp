// cgame_mp/cg_draw_mp.cpp (Store build): the end of the cgame frame.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses; the name and the
// file from Black Ops' server PDB (cgame_mp/cg_draw_mp.cpp: CG_DrawActive), whose function is the same code.

#include "cgame_mp/cg_local_mp.h"

void CL_SetFOVSensitivityScale(LocalClientNum_t localClientNum, float scale);       // client_mp/cl_cgame_mp.cpp
void CL_SetUserCmdAimValues(LocalClientNum_t localClientNum, const float *kickAngles);
void CL_SetUserCmdWeapons(LocalClientNum_t localClientNum, unsigned int weapon, unsigned int offHand,
                          int alternate);
void CL_SetExtraButtons(LocalClientNum_t localClientNum, int buttons);
void CL_RenderScene(LocalClientNum_t localClientNum, const void *refdef, int renderScreen);
void sub_1402891D0(unsigned int offHand);  // empty in this build (Black Ops' BG_AssertOffhandIndexOrNone)

static_assert(__builtin_offsetof(cg_s, zoomSensitivity) == 0xB1B18, "cg_s layout (Store build)");
static_assert(__builtin_offsetof(cg_s, weaponSelect) == 0xB2768, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, equippedOffHand) == 0xB4F0C, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, kickAngles) == 0xB5274, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, offsetAngles) == 0xB5280, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, shellshockSensitivity) == 0xB5320, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, extraButtons) == 0x10E82C, "cg_s layout");

// Store 1402AB060 (Black Ops' CG_DrawActive, cg_draw_mp.cpp:1805): the last thing CG_DrawActiveFrame does with the
// frame's view. It hands the client what the next usercmd needs, from this frame's cgame: the mouse sensitivity scale
// (the zoom's, times a shellshock's), the view kick plus the ADS view error offset (added to every usercmd's angles by
// CL_FinishMove, so the kick reaches the view only through the next frame's command and its prediction), the
// selected weapon, offhand and alternate mode, and the extra buttons; then the scene goes to the renderer.
void CG_DrawActive(LocalClientNum_t localClientNum, int renderScreen)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	float fovSensitivityScale = cgameGlob->zoomSensitivity;
	if (cgameGlob->shellshockSensitivity != 0.0f)
		fovSensitivityScale = fovSensitivityScale * cgameGlob->shellshockSensitivity;
	CL_SetFOVSensitivityScale(localClientNum, fovSensitivityScale);
	float angles[3];
	angles[0] = cgameGlob->kickAngles[0] + cgameGlob->offsetAngles[0];
	angles[1] = cgameGlob->offsetAngles[1] + cgameGlob->kickAngles[1];
	angles[2] = cgameGlob->offsetAngles[2] + cgameGlob->kickAngles[2];
	CL_SetUserCmdAimValues(localClientNum, angles);
	sub_1402891D0(cgameGlob->equippedOffHand);
	CL_SetUserCmdWeapons(localClientNum, cgameGlob->weaponSelect, cgameGlob->equippedOffHand,
	                     cgameGlob->weaponSelectAlternate);
	CL_SetExtraButtons(localClientNum, cgameGlob->extraButtons);
	cgameGlob->extraButtons = 0;
	CL_RenderScene(localClientNum, cgameGlob->refdef_displayViewport, renderScreen);
}
