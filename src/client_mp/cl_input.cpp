// client_mp/cl_input.cpp
//
// Two sources. The button handlers the PS4 dedicated server keeps (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis) are
// reconstructed from it and tagged with its addresses and lines. The mouse code is client-only and comes from the
// Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses; its names and order follow Black Ops'
// client_mp/cl_input_mp.cpp (black-ops-1-decomp, from its server PDB), and its line numbers are unknown.
// CL_IsGamepadEnabled and CL_ExecBinding are stubs in the server build (folded with `return true` and an empty
// function) and come from the Store build later.
//
// The mouse path, once a frame: IN_MouseMove (win32/win_input.cpp) passes the cursor movement to CL_MouseEvent,
// which adds it to cl->mouseDx/Dy; CL_CreateCmd calls CL_MouseMove, which takes it back out scaled by
// sensitivity, cl_mouseAccel and the cgame's FOV scale (sub_14030D4A0), turns it into degrees with m_yaw and
// m_pitch (0.022 by default) and adds that to the view angles, then lets aim assist adjust them.

#include <math.h>
#include <windows.h>

#include <iw6_static.h>

#include "client/client.h"
#include "client_mp/client_mp.h"
#include "qcommon/dvar.h"

#define IW6_SOURCE "client_mp/cl_input.cpp"

// Button state of every local client (file static).
IW6_STATIC kbutton_t playersKb[1][NUM_BUTTONS] IW6_AT("", "playersKb");

// Mouse dvars (registered in client_mp/cl_main_mp.cpp)
extern const dvar_t *cl_sensitivity;       // "sensitivity"
extern const dvar_t *cl_mouseAccel;
extern const dvar_t *cl_freelook;
extern const dvar_t *cl_bypassMouseInput;
extern const dvar_t *m_pitch;
extern const dvar_t *m_yaw;
extern const dvar_t *m_forward;
extern const dvar_t *m_side;
extern const dvar_t *m_filter;
extern const dvar_t *r_displayMode;        // gfx_d3d: 0 = fullscreen

void IN_ShowSystemCursor(int show);        // win32/win_input.cpp
struct playerState_s;
const playerState_s *CG_GetPredictedPlayerState(LocalClientNum_t localClientNum);
int BG_MeleeChargeShouldLockView(const playerState_s *ps, unsigned char meleeChargeDist);
bool sub_140222E90();                       // always true in the Store build (name unknown)
void sub_140223950(LocalClientNum_t localClientNum, int x, int y);  // cgame: the cursor while keyCatchers 0x40 (name unknown)
void sub_14030B720(int clip);               // client_mp: confines the cursor to the client area (name unknown)
void sub_14027B800(const AimOutput *output, usercmd_s *cmd);       // stores aim assist's melee target in the command (name unknown)

static_assert(__builtin_offsetof(clientActive_t, mouseDx) == 0x3534, "clientActive_t layout (Store build)");
static_assert(__builtin_offsetof(clientActive_t, cgameFOVSensitivityScale) == 0x3568, "clientActive_t layout");
static_assert(__builtin_offsetof(clientActive_t, clViewangles) == 0x3610, "clientActive_t layout");
static_assert(__builtin_offsetof(clientActive_t, mouseViewDelta) == 0x361C, "clientActive_t layout");
static_assert(__builtin_offsetof(usercmd_s, meleeChargeDist) == 0x22, "usercmd_s layout");
static_assert(sizeof(AimInput) == 0x34, "AimInput layout");
static_assert(__builtin_offsetof(clientStatic_t, vidConfig) == 0x180, "clientStatic_t layout");
static_assert(__builtin_offsetof(GamerSettingState, gpadEnabled) == 0x2BC, "GamerSettingState layout");

// Quake 3's IN_KeyDown / IN_KeyUp with the key and time passed in rather than read from the command line
// (inlined into every handler below).
static inline void IN_KeyDown(kbutton_t *b, int k, unsigned int downtime)
{
	if (k == b->down[0] || k == b->down[1])
		return;  // repeating key

	if (!b->down[0])
		b->down[0] = k;
	else if (!b->down[1])
		b->down[1] = k;
	else
		return;  // three keys down

	if (b->active)
		return;  // still down
	b->downtime = downtime;
	b->active = true;
	b->wasPressed = true;
}

static inline void IN_KeyUp(kbutton_t *b, int k, unsigned int uptime)
{
	if (b->down[0] == k)
		b->down[0] = 0;
	else if (b->down[1] == k)
		b->down[1] = 0;
	else
		return;  // key up without corresponding down

	if (b->down[0] || b->down[1])
		return;  // some other key is still holding it down

	b->active = false;
	// save timed portion of this frame
	if (uptime)
		b->msec += uptime - b->downtime;
	else
		b->msec += frame_msec / 2;
}

// A tap: press and release in the same frame.
static inline void IN_KeyTap(kbutton_t *b, int k)
{
	IN_KeyDown(b, k, 0);
	IN_KeyUp(b, k, 0);
}

// 1400ACCF0  client_mp/cl_input.cpp:469
void CL_UseReload(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_USE_RELOAD], key);
}

// 1400ACBF0  client_mp/cl_input.cpp:482
void CL_SpecPrev(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_SPECPREV], key);
}

// 1400ACB70  client_mp/cl_input.cpp:489
void CL_SpecNext(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_SPECNEXT], key);
}

// 1400ACC70  client_mp/cl_input.cpp:496
void CL_ToggleSpec(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_SPECTATE], key);
}

// Q3's ClampChar (inlined)
static inline char ClampChar(int i)
{
	if (i < -127)
		return -127;
	if (i > 127)
		return 127;
	return (char)i;
}

// 14030DB00
int CL_MouseEvent(int x, int y, int dx, int dy)
{
	clientUIActive_t *uiGlobals = CL_GetLocalClientUIGlobals(LOCAL_CLIENT_0);

	if ((uiGlobals->keyCatchers & KEYCATCH_UI) && UI_GetActiveMenu(LOCAL_CLIENT_0) != UIMENU_SCOREBOARD
	    && !cl_bypassMouseInput->current.enabled)
	{
		// a menu has the mouse: it gets the cursor position
		UI_MouseEvent(LOCAL_CLIENT_0, x, y);
	}
	else if (sub_140222E90() && (uiGlobals->keyCatchers & KEYCATCH_UNKNOWN_40))
	{
		IN_ShowSystemCursor(1);
		if (r_displayMode->current.integer)
			ClipCursor(NULL);
		sub_140223950(LOCAL_CLIENT_0, x, y);
		return 0;
	}
	else if (r_displayMode->current.integer && uiGlobals->connectionState > CA_DISCONNECTED
	         && uiGlobals->connectionState < CA_ACTIVE)
	{
		// windowed while loading: the movement is dropped
		IN_ShowSystemCursor(0);
	}
	else
	{
		// the game has the mouse: accumulate the movement until CL_MouseMove takes it
		IN_ShowSystemCursor(0);
		sub_14030B720(1);
		clientActive_t *cl = CL_GetLocalClientGlobals(LOCAL_CLIENT_0);
		cl->mouseDx[cl->mouseIndex] += dx;
		cl->mouseDy[cl->mouseIndex] += dy;
		return 1;
	}

	if (r_displayMode->current.integer)
		ClipCursor(NULL);
	return 0;
}

// 14030E450
void CL_ShowSystemCursor(int show)
{
	IN_ShowSystemCursor(show);
}

// 14030D3C0
void CL_GetMouseMovement(clientActive_t *cl, float *mx, float *my)
{
	if (m_filter->current.enabled)
	{
		// the average of this frame and the last
		*mx = (float)(cl->mouseDx[0] + cl->mouseDx[1]) * 0.5f;
		*my = (float)(cl->mouseDy[0] + cl->mouseDy[1]) * 0.5f;
	}
	else
	{
		*mx = (float)cl->mouseDx[cl->mouseIndex];
		*my = (float)cl->mouseDy[cl->mouseIndex];
	}
	cl->mouseIndex ^= 1;
	cl->mouseDx[cl->mouseIndex] = 0;
	cl->mouseDy[cl->mouseIndex] = 0;

	if (GamerProfile_GetProfileSettings(CL_GetFirstActiveControllerIndex())->gpadEnabled)
	{
		*mx = 0.0f;
		*my = 0.0f;
	}
}

// 14030D4A0: CL_GetMouseMovement scaled by the mouse sensitivity (name unknown; Black Ops does this inside
// CL_MouseMove). In counts times sensitivity: CL_MouseMove turns it into degrees with m_yaw and m_pitch.
void sub_14030D4A0(clientActive_t *cl, float *mx, float *my)
{
	float x;
	float y;
	if (m_filter->current.enabled)
	{
		x = (float)(cl->mouseDx[0] + cl->mouseDx[1]) * 0.5f;
		y = (float)(cl->mouseDy[0] + cl->mouseDy[1]) * 0.5f;
	}
	else
	{
		x = (float)cl->mouseDx[cl->mouseIndex];
		y = (float)cl->mouseDy[cl->mouseIndex];
	}
	cl->mouseIndex ^= 1;
	cl->mouseDx[cl->mouseIndex] = 0;
	cl->mouseDy[cl->mouseIndex] = 0;

	if (GamerProfile_GetProfileSettings(CL_GetFirstActiveControllerIndex())->gpadEnabled)
	{
		x = 0.0f;
		y = 0.0f;
	}

	// sensitivity, plus cl_mouseAccel times the speed in counts per millisecond, times the cgame's scale (zoom)
	const float speed = sqrtf(x * x + y * y) / (float)frame_msec;
	const float accelSensitivity = (speed * cl_mouseAccel->current.value + cl_sensitivity->current.value)
	                             * cl->cgameFOVSensitivityScale;
	*mx = accelSensitivity * x;
	*my = accelSensitivity * y;
}

// 14030DC20
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

	if (!BG_MeleeChargeShouldLockView(CG_GetPredictedPlayerState(localClientNum), 0) && (mx != 0.0f || my != 0.0f))
	{
		kbutton_t *kb = playersKb[localClientNum];

		if (kb[KB_STRAFE].active)
		{
			cmd->rightmove = ClampChar(cmd->rightmove + (int)floor(mx * m_side->current.value + 0.5f));
		}
		else
		{
			float delta = mx * m_yaw->current.value;
			if (cl->cgameMaxYawSpeed > 0.0f)
			{
				const float cap = (float)frame_msec * cl->cgameMaxYawSpeed * 0.001f;
				const float capped = cap < delta ? cap : delta;
				delta = -cap > capped ? -cap : capped;
			}
			cl->clViewangles[1] = cl->clViewangles[1] - delta;
			cl->mouseViewDelta[1] = -delta;
		}

		if ((kb[KB_MLOOK].active || cl_freelook->current.enabled) && !kb[KB_STRAFE].active)
		{
			float delta = my * m_pitch->current.value;
			if (cl->cgameMaxPitchSpeed > 0.0f)
			{
				const float cap = (float)frame_msec * cl->cgameMaxPitchSpeed * 0.001f;
				const float capped = cap < delta ? cap : delta;
				delta = -cap > capped ? -cap : capped;
			}
			cl->clViewangles[0] = cl->clViewangles[0] + delta;
			cl->mouseViewDelta[0] = delta;
		}
		else
		{
			cmd->forwardmove = ClampChar(cmd->forwardmove - (int)floor(my * m_forward->current.value + 0.5f));
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
