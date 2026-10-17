// enhanced/client_mp/cl_input.cpp: mouse aim in MW2019 units, independent of the field of view
// (records/bugs.tsv B0010, B0023).
//
// Replaces the mouse half of src/client_mp/cl_input.cpp. One device count turns the view by
// m_sens * 0.0066 degrees, the same as MW2019's sensitivity at any FOV, hip fire and aiming down sights alike: no
// cgame FOV scale (the original's tan(fov/2)/tan(32.5)), no cl_mouseAccel, no m_filter averaging, no m_yaw or
// m_pitch. The view angles are kept in double precision, so splitting the same movement over more frames gives
// the same angle.

#include <math.h>

#include <iw6_static.h>

#include "client/client.h"
#include "client_mp/client_mp.h"
#include "enhanced/raw_input.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "client_mp/cl_input.cpp"

IW6_STATIC kbutton_t playersKb[1][NUM_BUTTONS] IW6_AT("", "playersKb");

extern const dvar_t *cl_freelook;
extern const dvar_t *m_forward;
extern const dvar_t *m_side;

const dvar_t *m_sens;         // MW2019 units
const dvar_t *m_invertPitch;

struct playerState_s;
const playerState_s *CG_GetPredictedPlayerState(LocalClientNum_t localClientNum);
int BG_MeleeChargeShouldLockView(const playerState_s *ps, unsigned char meleeChargeDist);
void sub_14027B800(const AimOutput *output, usercmd_s *cmd);
const dvar_t *Dvar_RegisterFloat(const char *dvarName, float value, float min, float max, unsigned int flags,
                                 const char *description);
const dvar_t *Dvar_RegisterBool(const char *dvarName, bool value, unsigned int flags, const char *description);

static inline char ClampChar(int i)
{
	return i < -127 ? -127 : i > 127 ? 127 : (char)i;
}

void CL_RegisterMouseDvars()
{
	m_sens = Dvar_RegisterFloat("m_sens", 1.5f, 0.01f, 100.0f, 1,
	                            "Mouse sensitivity in MW2019 units: 0.0066 degrees per count each, at any field of view");
	m_invertPitch = Dvar_RegisterBool("m_invertPitch", false, 1, "Invert the mouse's vertical look");
}

// Store 14030D3C0: the movement since the last command, in counts
void CL_GetMouseMovement(clientActive_t *cl, float *mx, float *my)
{
	*mx = (float)cl->mouseDx[cl->mouseIndex];
	*my = (float)cl->mouseDy[cl->mouseIndex];
	cl->mouseIndex ^= 1;
	cl->mouseDx[cl->mouseIndex] = 0;
	cl->mouseDy[cl->mouseIndex] = 0;

	if (GamerProfile_GetProfileSettings(CL_GetFirstActiveControllerIndex())->gpadEnabled)
	{
		*mx = 0.0f;
		*my = 0.0f;
	}
}

// Store 14030D4A0: the original scales the movement here by sensitivity, acceleration and the FOV; the enhanced
// build returns plain counts and CL_MouseMove applies m_sens
void sub_14030D4A0(clientActive_t *cl, float *mx, float *my)
{
	CL_GetMouseMovement(cl, mx, my);
}

// The view angles as CL_MouseMove last left them, in double precision. Anything else that changes
// cl->clViewangles (spawning, the cgame's pitch limits, aim assist) is picked up the next time.
static double s_viewangles[2];
static float s_viewanglesWritten[2];

static double CL_ViewAngle(clientActive_t *cl, int axis)
{
	if (cl->clViewangles[axis] != s_viewanglesWritten[axis])
		s_viewangles[axis] = cl->clViewangles[axis];
	return s_viewangles[axis];
}

static void CL_SetViewAngle(clientActive_t *cl, int axis, double angle)
{
	s_viewangles[axis] = angle;
	s_viewanglesWritten[axis] = (float)angle;
	cl->clViewangles[axis] = s_viewanglesWritten[axis];
}

// Store 14030DC20
void CL_MouseMove(LocalClientNum_t localClientNum, usercmd_s *cmd, float frametime_base)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	float mx;
	float my;

	if (!frame_msec)
		return;

	sub_14030D4A0(cl, &mx, &my);
	cl->mouseViewDelta[0] = 0.0f;
	cl->mouseViewDelta[1] = 0.0f;
	cl->mouseViewDelta[2] = 0.0f;
	if (cl->snap.ps_pm_flags & PMF_NO_MOUSE_LOOK)
		return;

	const double degreesPerCount = (double)m_sens->current.value * MOUSE_DEGREES_PER_COUNT;
	if (!BG_MeleeChargeShouldLockView(CG_GetPredictedPlayerState(localClientNum), 0) && (mx != 0.0f || my != 0.0f))
	{
		kbutton_t *kb = playersKb[localClientNum];

		if (kb[KB_STRAFE].active)
		{
			cmd->rightmove = ClampChar(cmd->rightmove + (int)floor(mx * m_sens->current.value * m_side->current.value + 0.5f));
		}
		else
		{
			double delta = mx * degreesPerCount;
			if (cl->cgameMaxYawSpeed > 0.0f)  // a limit the game sets (vehicles, turrets), not an input filter
			{
				const double cap = (double)frame_msec * cl->cgameMaxYawSpeed * 0.001;
				delta = delta > cap ? cap : delta < -cap ? -cap : delta;
			}
			CL_SetViewAngle(cl, 1, CL_ViewAngle(cl, 1) - delta);
			cl->mouseViewDelta[1] = (float)-delta;
		}

		if ((kb[KB_MLOOK].active || cl_freelook->current.enabled) && !kb[KB_STRAFE].active)
		{
			double delta = my * degreesPerCount;
			if (m_invertPitch->current.enabled)
				delta = -delta;
			if (cl->cgameMaxPitchSpeed > 0.0f)
			{
				const double cap = (double)frame_msec * cl->cgameMaxPitchSpeed * 0.001;
				delta = delta > cap ? cap : delta < -cap ? -cap : delta;
			}
			CL_SetViewAngle(cl, 0, CL_ViewAngle(cl, 0) + delta);
			cl->mouseViewDelta[0] = (float)delta;
		}
		else
		{
			cmd->forwardmove = ClampChar(cmd->forwardmove - (int)floor(my * m_sens->current.value * m_forward->current.value + 0.5f));
		}
	}

	AimInput aimInput;
	aimInput.deltaTime = frametime_base;
	aimInput.deltaTimeScaled = (float)cls.frametime * 0.001f;
	aimInput.pitch = cl->clViewangles[0];
	aimInput.pitchAxis = 0.0f;
	aimInput.pitchMax = 0.0f;
	aimInput.yaw = cl->clViewangles[1];
	aimInput.yawAxis = 0.0f;
	aimInput.yawMax = 0.0f;
	aimInput.forwardAxis = 0.0f;
	aimInput.rightAxis = 0.0f;
	aimInput.buttons = cmd->buttons;
	aimInput.localClientNum = LOCAL_CLIENT_0;
	aimInput.meleeChargeEnt = cmd->meleeChargeEnt;
	aimInput.meleeChargeDist = cmd->meleeChargeDist;

	AimOutput aimOutput;
	AimAssist_UpdateMouseInput(&aimInput, &aimOutput);
	cl->clViewangles[0] = aimOutput.pitch;
	cl->clViewangles[1] = aimOutput.yaw;
	sub_14027B800(&aimOutput, cmd);
}
