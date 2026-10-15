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
#include <string.h>
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

void sub_140311D60(LocalClientNum_t localClientNum, int value, int force);  // queues a reliable client command (name unknown)

enum StanceState
{
	CL_STANCE_STAND = 0x0,
	CL_STANCE_CROUCH = 0x1,
	CL_STANCE_PRONE = 0x2,
};

extern int com_frameTime;  // qcommon/common.cpp

// Store 14030D650  client_mp/cl_input.cpp:109 (a `return true` stub in the server build)
bool CL_IsGamepadEnabled(LocalClientNum_t localClientNum)
{
	return GamerProfile_GetProfileSettings(CL_GetFirstActiveControllerIndex())->gpadEnabled;
}

// Store 14030EE50: Quake 3's IN_KeyDown with the key and time passed in rather than read from the command line
void IN_KeyDown(kbutton_t *b, int k, unsigned int downtime)
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

// Store 14030EE80
void IN_KeyUp(kbutton_t *b, int k, unsigned int uptime)
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

// Store 14030DAA0: the fraction of the frame the key was down
float CL_KeyState(kbutton_t *key)
{
	int msec = key->msec;
	key->msec = 0;

	if (key->active)
	{
		// still down
		if (!key->downtime)
			msec = com_frameTime;
		else
			msec += com_frameTime - key->downtime;
		key->downtime = com_frameTime;
	}

	if (msec <= 0)
		return 0.0f;
	if (msec >= frame_msec)
		return 1.0f;
	return (float)msec / frame_msec;
}

// Store 14030E410
void CL_SetStance(LocalClientNum_t localClientNum, StanceState stance)
{
	if (playersKb[localClientNum][KB_PRONE].active || playersKb[localClientNum][KB_DOWN].active)
		return;
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	cl->stance = stance;
	cl->stanceHeld = false;
}

// Store 14030E660  client_mp/cl_input.cpp:469 (the server build has no reliable command: 1400ACCF0)
void CL_UseReload(LocalClientNum_t localClientNum, int key)
{
	sub_140311D60(localClientNum, 11, 0);
	IN_KeyDown(&playersKb[localClientNum][KB_USE_RELOAD], key, 0);
	IN_KeyUp(&playersKb[localClientNum][KB_USE_RELOAD], key, 0);
}

// 1400ACBF0  client_mp/cl_input.cpp:482  (Store 14030E500)
void CL_SpecPrev(LocalClientNum_t localClientNum, int key)
{
	IN_KeyDown(&playersKb[localClientNum][KB_SPECPREV], key, 0);
	IN_KeyUp(&playersKb[localClientNum][KB_SPECPREV], key, 0);
}

// 1400ACB70  client_mp/cl_input.cpp:489  (Store 14030E470)
void CL_SpecNext(LocalClientNum_t localClientNum, int key)
{
	IN_KeyDown(&playersKb[localClientNum][KB_SPECNEXT], key, 0);
	IN_KeyUp(&playersKb[localClientNum][KB_SPECNEXT], key, 0);
}

// 1400ACC70  client_mp/cl_input.cpp:496  (Store 14030E590)
void CL_ToggleSpec(LocalClientNum_t localClientNum, int key)
{
	IN_KeyDown(&playersKb[localClientNum][KB_SPECTATE], key, 0);
	IN_KeyUp(&playersKb[localClientNum][KB_SPECTATE], key, 0);
}

// Store 14030EE10
bool IN_IsTalkKeyHeld()
{
	return playersKb[0][KB_TALK].active;
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

// Store 14030D670
bool CL_KeyActiveOrPressed(LocalClientNum_t localClientNum, int keyIndex)
{
	return playersKb[localClientNum][keyIndex].active || playersKb[localClientNum][keyIndex].wasPressed;
}

// Store 14030E620: sets the command button for a key that is down or was pressed this frame
void CL_UpdateCmdButton(LocalClientNum_t localClientNum, unsigned int *cmdButtons, int keyIndex, unsigned int buttonFlag)
{
	if (playersKb[localClientNum][keyIndex].active || playersKb[localClientNum][keyIndex].wasPressed)
		*cmdButtons |= buttonFlag;
	playersKb[localClientNum][keyIndex].wasPressed = false;
}

// Store 14030B6B0
void CL_ClearKeys(LocalClientNum_t localClientNum)
{
	memset(playersKb[localClientNum], 0, sizeof(playersKb[localClientNum]));
}

// ==== BEGIN cmdbuttons ====

static_assert(__builtin_offsetof(clientActive_t, snap) == 0x8, "clientActive_t layout");
static_assert(__builtin_offsetof(clSnapshot_s, ps_weapState) == 0x2AC, "playerState_s layout (Store build)");
static_assert(__builtin_offsetof(clSnapshot_s, ps_weapon) == 0x41C, "playerState_s layout");
static_assert(__builtin_offsetof(clSnapshot_s, ps_weapFlags) == 0x420, "playerState_s layout");
static_assert(__builtin_offsetof(clSnapshot_s, ps_lastWeaponHand) == 0x43C, "playerState_s layout");
static_assert(__builtin_offsetof(clSnapshot_s, ps_ammoInClip) == 0x530, "playerState_s layout");
static_assert(sizeof(clSnapshot_s) == 0x34B8, "clSnapshot_s size (Store build)");
static_assert(__builtin_offsetof(clientActive_t, stanceHeld) == 0x3548, "clientActive_t layout");
static_assert(__builtin_offsetof(clientActive_t, wasSprinting) == 0x3558, "clientActive_t layout");


// bgame/bg_weapons_util.h (inlined)
static inline int BG_GetAmmoInClip(const clSnapshot_s *ps, Weapon weapon, bool isAlternate, PlayerHandIndex hand)
{
	const unsigned long long clipIndex = BG_ClipForWeapon(weapon, isAlternate);
	for (int i = 0; i < MAX_AMMO_SLOTS; i++)
	{
		if (ps->ps_ammoInClip[i].clipIndex == clipIndex)
			return ps->ps_ammoInClip[i].ammoCount[hand];
	}
	return 0;
}

// Store 14030D6B0  client_mp/cl_input.cpp (Black Ops' CL_KeyMove, cl_input_mp.cpp:1589), with CL_StanceButtonUpdate
// and CL_AddCurrentStanceToCmd inlined
void CL_KeyMove(LocalClientNum_t localClientNum, usercmd_s *cmd)
{
	kbutton_t *kb = playersKb[localClientNum];
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);

	if (kb[KB_PRONE].active || kb[KB_DOWN].active)
	{
		cl->stance = CL_STANCE_STAND;
		if (kb[KB_PRONE].active)
		{
			cmd->buttons |= 0x100;
			cmd->buttons &= ~0x200u;
		}
		else
		{
			cmd->buttons |= 0x200;
			cmd->buttons &= ~0x100u;
		}
		cmd->buttons |= 0x1000;
	}
	else
	{
		// CL_StanceButtonUpdate: the stance key held long enough goes prone (or stands), or slides when sprinting
		if (cl->stanceHeld)
		{
			const int holdTime = cl->wasSprinting ? 200 : 300;
			if ((int)((unsigned int)com_frameTime - (unsigned int)cl->stanceTime) >= holdTime)
			{
				if (cl->wasSprinting || cl->stance == 3)
				{
					// stanceHeld stays set
					cl->wasSprinting = false;
					cl->stance = 3;  // CL_STANCE_SLIDE
				}
				else
				{
					cl->stanceHeld = false;
					cl->stance = cl->stancePosition == CL_STANCE_PRONE ? CL_STANCE_STAND : CL_STANCE_PRONE;
				}
			}
		}

		// CL_AddCurrentStanceToCmd
		switch (cl->stance)
		{
		case CL_STANCE_CROUCH:
			cmd->buttons |= 0x200;
			cmd->buttons &= ~0x100u;
			cmd->buttons &= ~0x1000u;
			break;
		case CL_STANCE_PRONE:
			cmd->buttons |= 0x100;
			cmd->buttons &= ~0x200u;
			cmd->buttons &= ~0x1000u;
			break;
		case 3:  // CL_STANCE_SLIDE
			cmd->buttons &= ~0x20000000u;
			if (cl->stanceHeld)
				cmd->buttons |= 0x20000000;
			cmd->buttons &= ~0x100u;
			cmd->buttons |= 0x200;
			cmd->buttons &= ~0x1000u;
			break;
		default:
			cmd->buttons &= ~0x100u;
			cmd->buttons &= ~0x200u;
			cmd->buttons &= ~0x1000u;
			break;
		}
	}

	if (kb[KB_SPEED].active != cl->usingAds)
		cmd->buttons |= 0x800;
	else
		cmd->buttons &= ~0x800u;
	if (cl->usingAds && !kb[KB_SPEED].active)
		cmd->buttons |= 0x10000000;
	else
		cmd->buttons &= ~0x10000000u;

	if (kb[KB_ADS_ACCESSIBLE].active || kb[KB_ADS_ACCESSIBLE].wasPressed)
	{
		const clSnapshot_s *ps = &cl->snap;
		if (ps->ps_lastWeaponHand == WEAPON_HAND_LEFT)
		{
			if (ps->ps_weapState[WEAPON_HAND_LEFT].weaponState == WEAPON_FIRING)
				cmd->buttons |= 0x80000;
			else if (ps->ps_weapState[WEAPON_HAND_RIGHT].weaponState == WEAPON_FIRING)
				cmd->buttons |= 0x1;
			else if (kb[KB_ADS_ACCESSIBLE].wasPressed)
			{
				if (!BG_GetAmmoInClip(ps, ps->ps_weapon, (ps->ps_weapFlags & PWF_ALT_MODE) != 0, WEAPON_HAND_LEFT))
					cmd->buttons |= 0x1;
				else if (BG_ShotLimitReached((const playerState_s *)ps, ps->ps_weapon, WEAPON_HAND_LEFT))
					cmd->buttons |= 0x1;
				else
					cmd->buttons |= 0x80000;
			}
		}
		kb[KB_ADS_ACCESSIBLE].wasPressed = false;
	}

	int side = (int)(CL_KeyState(&kb[KB_MOVERIGHT]) * 127.0f);
	side += (int)(CL_KeyState(&kb[KB_MOVELEFT]) * -127.0f);
	int forward = (int)(CL_KeyState(&kb[KB_FORWARD]) * 127.0f);
	forward += (int)(CL_KeyState(&kb[KB_BACK]) * -127.0f);

	if (!kb[KB_BACK].active)
	{
		if (kb[KB_SPRINT].active || kb[KB_SPRINT].wasPressed)
		{
			cmd->buttons |= 0x2;
			kb[KB_SPRINT].wasPressed = false;
		}
		else
		{
			cmd->buttons &= ~0x2u;
		}
	}

	if (kb[KB_STRAFE].active && !(cmd->buttons & 0x2))
	{
		side += (int)(CL_KeyState(&kb[KB_RIGHT]) * 127.0f);
		side += (int)(CL_KeyState(&kb[KB_LEFT]) * -127.0f);
	}

	if (cmd->buttons & 0x1)
	{
		if (BG_WeaponDef(cl->snap.ps_weapon, (cl->snap.ps_weapFlags & PWF_ALT_MODE) != 0)->meleeOnly)
			cmd->buttons |= 0x4;
	}

	cmd->forwardmove = ClampChar(forward);
	cmd->rightmove = ClampChar(side);

	if (!CL_IsGamepadEnabled(localClientNum))
		CG_HandleSpecialStateInput(localClientNum, &cmd->buttons);
}

// Store 14030B7D0  client_mp/cl_input.cpp (Black Ops' CL_CmdButtons, cl_input_mp.cpp:2337)
void CL_CmdButtons(LocalClientNum_t localClientNum, usercmd_s *cmd)
{
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_ATTACK, 0x1);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_BREATH, 0x2000);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_ZOOM, 0x4000000);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_FRAG, 0x4000);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_OFFHANDSECONDARY, 0x8000);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_MELEE, 0x4);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_ACTIVATE, 0x8);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_RELOAD, 0x10);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_USE_RELOAD, 0x20);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_PRONE, 0x100);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_CROUCH, 0x200);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_UP, 0x400);
	CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_THROW, 0x80000);

	// Key_IsCatcherActive(localClientNum, -1)
	if (CL_GetLocalClientUIGlobals(localClientNum)->keyCatchers && !cl_bypassMouseInput->current.enabled
	    && UI_GetActiveMenu(localClientNum) != UIMENU_SCOREBOARD)
		cmd->buttons |= 0x800000;

	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	if (cl->snap.ps_weapFlags & 0x1)
		cmd->buttons |= 0x10;

	if (CL_GetLocalClientUIGlobals(localClientNum)->connectionState > CA_CONNECTED
	    && (cl->snap.ps_pm_type == 2 || cl->snap.ps_pm_type == 3 || cl->snap.ps_pm_type == 5))  // PM_NOCLIP, PM_UFO, PM_SPECTATOR
		CL_UpdateCmdButton(localClientNum, &cmd->buttons, KB_ANYUP, 0x400);

	if (CL_KeyActiveOrPressed(localClientNum, KB_ADS_ACCESSIBLE))
		cmd->buttons |= 0x800;
	if (CL_KeyActiveOrPressed(localClientNum, KB_ATTACK_ACCESSIBLE))
		cmd->buttons |= 0x1;
	if (cl->snap.ps_lastWeaponHand == WEAPON_HAND_LEFT && CL_KeyActiveOrPressed(localClientNum, KB_ATTACK_ACCESSIBLE))
		cmd->buttons |= 0x80000;
	playersKb[localClientNum][KB_ATTACK_ACCESSIBLE].wasPressed = false;
}

// ==== END cmdbuttons ====

// ==== BEGIN gamepadmove ====

enum GamePadButton
{
	GPAD_B = 0x10002000,
	GPAD_L_TRIG = 0x20000000,
	GPAD_R_TRIG = 0x20000001,
};

static_assert(__builtin_offsetof(clSnapshot_s, ps_eFlags) == 0x124, "playerState_s layout (Store build)");
static_assert(__builtin_offsetof(usercmd_s, airburstMarkDistance) == 0x1E, "usercmd_s layout");
static_assert(__builtin_offsetof(GamerSettingState, invertedPitch) == 0x44, "GamerSettingState layout");

float CL_GamepadAxisValue(LocalClientNum_t localClientNum, GamepadVirtualAxis virtualAxis);  // client/cl_gamepad.cpp
float GPad_GetButton(int portIndex, GamePadButton button);               // win32/win_gamepad.cpp
bool CG_ShouldUpdateViewAngles(LocalClientNum_t localClientNum);         // cgame_mp/cg_gamepad.cpp
void AimAssist_UpdateGamePadInput(const AimInput *input, AimOutput *output);  // aim_assist/aim_assist.cpp
float sub_140263E10(const playerState_s *ps, float yawAxis);  // bgame: scales the yaw stick down near the prone yaw limit (name unknown)
int sub_1402F7090(LocalClientNum_t localClientNum, const playerState_s *ps, unsigned int buttons, int *distance);  // cgame: airburst mark distance (name unknown)

// Store 14030D390: the sign of the pitch stick, +1 with the profile's inverted pitch (name unknown)
float sub_14030D390(LocalClientNum_t localClientNum)
{
	return GamerProfile_GetProfileSettings(CL_GetFirstActiveControllerIndex())->invertedPitch ? 1.0f : -1.0f;
}

// Store 14030CF10  (Black Ops: client_mp/cl_input_mp.cpp:1804)
void CL_GamepadMove(LocalClientNum_t localClientNum, float frametime_base, usercmd_s *cmd)
{
	if (!CL_IsGamepadEnabled(localClientNum))
		return;
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	if (cl->snap.ps_pm_flags & PMF_NO_MOUSE_LOOK)
		return;

	const int controllerIndex = CL_GetFirstActiveControllerIndex();
	float pitch = CL_GamepadAxisValue(localClientNum, GPAD_VIRTAXIS_PITCH);
	pitch *= sub_14030D390(localClientNum);
	const float yaw = -CL_GamepadAxisValue(localClientNum, GPAD_VIRTAXIS_YAW);
	const float forward = CL_GamepadAxisValue(localClientNum, GPAD_VIRTAXIS_FORWARD);
	const float side = CL_GamepadAxisValue(localClientNum, GPAD_VIRTAXIS_SIDE);
	const float attack = CL_GamepadAxisValue(localClientNum, GPAD_VIRTAXIS_ATTACK);

	// scale so that the stick's square maps onto the full move range
	float moveScale = 127.0f;
	if (fabs(side) > 0.0f || fabs(forward) > 0.0f)
	{
		float length;
		if (fabs(side) > fabs(forward))
			length = forward / side;
		else
			length = side / forward;
		moveScale = sqrtf(length * length + 1.0f) * 127.0f;
	}
	int rightMove = (int)(moveScale * side);
	int forwardMove = (int)(moveScale * forward);
	// a centred stick keeps the keyboard's move, clamped again (-128 becomes -127)
	if (!rightMove)
		rightMove = cmd->rightmove;
	cmd->rightmove = ClampChar(rightMove);
	if (!forwardMove)
		forwardMove = cmd->forwardmove;
	cmd->forwardmove = ClampChar(forwardMove);

	kbutton_t *kb = playersKb[localClientNum];
	if (kb[KB_SPEED].active == !cl->usingAds)
		cmd->buttons |= 0x800;
	if (!kb[KB_BACK].active)
	{
		if (kb[KB_SPRINT].active || kb[KB_SPRINT].wasPressed)
		{
			cmd->buttons |= 0x2;
			kb[KB_SPRINT].wasPressed = false;
		}
		else
		{
			cmd->buttons &= ~0x2u;
		}
	}

	if (attack >= 0.8f)
		cmd->buttons |= 0x1;
	if (cmd->buttons & 0x1)
	{
		if (BG_WeaponDef(cl->snap.ps_weapon, (cl->snap.ps_weapFlags >> 14) & 1)->meleeOnly)
			cmd->buttons |= 0x4;
	}

	if (cl->snap.ps_eFlags & 0x200000)
	{
		if (GPad_GetButton(controllerIndex, GPAD_R_TRIG) != 0.0f)
			cmd->buttons |= 0x1000000;
		if (GPad_GetButton(controllerIndex, GPAD_L_TRIG) != 0.0f)
			cmd->buttons |= 0x2000000;
		if (GPad_GetButton(controllerIndex, GPAD_B) != 0.0f)
			cmd->buttons |= 0x2000000;
	}

	CG_HandleSpecialStateInput(localClientNum, &cmd->buttons);
	if (CG_ShouldUpdateViewAngles(localClientNum))
	{
		AimInput aimInput;
		aimInput.deltaTime = frametime_base;
		aimInput.deltaTimeScaled = (float)cls.frametime * 0.001f;
		aimInput.pitch = cl->clViewangles[0];
		aimInput.pitchAxis = pitch;
		aimInput.pitchMax = cl->cgameMaxPitchSpeed;
		aimInput.yaw = cl->clViewangles[1];
		aimInput.yawAxis = sub_140263E10(CG_GetPredictedPlayerState(localClientNum), yaw);
		aimInput.yawMax = cl->cgameMaxYawSpeed;
		aimInput.forwardAxis = forward;
		aimInput.rightAxis = side;
		aimInput.buttons = cmd->buttons;
		aimInput.localClientNum = localClientNum;
		aimInput.meleeChargeEnt = cmd->meleeChargeEnt;
		aimInput.meleeChargeDist = cmd->meleeChargeDist;

		AimOutput aimOutput;
		AimAssist_UpdateGamePadInput(&aimInput, &aimOutput);
		cl->clViewangles[0] = aimOutput.pitch;
		cl->clViewangles[1] = aimOutput.yaw;
		sub_14027B800(&aimOutput, cmd);
	}

	int airburstDistance;
	if (sub_1402F7090(localClientNum, (const playerState_s *)&cl->snap, cmd->buttons, &airburstDistance))
	{
		cmd->buttons |= 0x8000000;
		cmd->airburstMarkDistance = (unsigned short)airburstDistance;
	}
}

// ==== END gamepadmove ====
