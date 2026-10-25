// cgame_mp/cg_draw_mp.cpp (Store build): the end of the cgame frame.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses; the name and the
// file from Black Ops' server PDB (cgame_mp/cg_draw_mp.cpp: CG_DrawActive), whose function is the same code.

#include "cgame_mp/cg_local_mp.h"
#include "client/client.h"

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

int CL_ControllerIndexFromClientNum(LocalClientNum_t localClientNum);  // client/splitscreen.cpp
bool sub_14031FED0(int controllerIndex);                              // name unknown: the ramp's input is enabled
Weapon BG_GetViewmodelWeapon(const playerState_s *ps);
void BG_GetADSTransTimes(const playerState_s *ps, Weapon weapon, bool isAlternate, float *inTime, float *outTime);

static_assert(__builtin_offsetof(cg_s, rampDown) == 0x10F823, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, rampUp) == 0x10F824, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, ramp) == 0x10F828, "cg_s layout");

// Store 1402AA2A0 (name unknown): from CG_DrawActiveFrame once a frame, after CL_Input. cg.ramp moves toward +1 while
// rampUp (and toward -1 while rampDown) by cls.frametime / 300 a frame, when 14031FED0 allows it and pm_flags 1 is
// clear; otherwise it goes back to 0 at that rate, or with pm_flags 0x10 at the weapon's ADS-in rate (frametime /
// (1 / adsInTime)). The rate is per millisecond of the client's frame (cls.frametime, not cg.frametime).
void sub_1402AA2A0(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	const float frametime = (float)cls.frametime;
	float step = frametime / 300.0f;
	const bool enabled = sub_14031FED0(CL_ControllerIndexFromClientNum(localClientNum));
	const int pmFlags = cgameGlob->predictedPlayerState.pm_flags;
	if (enabled && !(pmFlags & 1))
	{
		if (cgameGlob->rampUp && !(pmFlags & 0x10))
		{
			const float v = step + cgameGlob->ramp;
			cgameGlob->ramp = 1.0f < v ? 1.0f : v;
			return;
		}
		if (cgameGlob->rampDown)
		{
			if (!(pmFlags & 0x10))
			{
				const float v = cgameGlob->ramp - step;
				cgameGlob->ramp = -1.0f > v ? -1.0f : v;
				return;
			}
			goto adsRate;
		}
	}
	if (pmFlags & 0x10)
	{
	adsRate:
		const playerState_s *ps = &cgameGlob->predictedPlayerState;
		float inTime, outTime;
		BG_GetADSTransTimes(ps, BG_GetViewmodelWeapon(ps), (ps->weapCommon_weapFlags >> 14) & 1, &inTime, &outTime);
		step = frametime / (1.0f / inTime);
	}
	const float ramp = cgameGlob->ramp;
	if (ramp > 0.0f)
	{
		const float v = ramp - step;
		cgameGlob->ramp = 0.0f > v ? 0.0f : v;
	}
	else if (0.0f > ramp)
	{
		const float v = ramp + step;
		cgameGlob->ramp = 0.0f < v ? 0.0f : v;
	}
}
