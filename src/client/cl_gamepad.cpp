// client/cl_gamepad.cpp
//
// Reconstructed from the PS4 dedicated server (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis, changelist 715098): the
// axis bindings and button events it keeps. Functions appear in original line order; each is tagged with its
// address in that build and its original line.

#include <iw6_static.h>

#include "client/client.h"
#include "qcommon/cmd.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "client/cl_gamepad.cpp"

// File statics
IW6_STATIC const char *physicalAxisNames[GPAD_PHYSAXIS_COUNT] IW6_AT("", "physicalAxisNames");
IW6_STATIC const char *virtualAxisNames[GPAD_VIRTAXIS_COUNT] IW6_AT("", "virtualAxisNames");
IW6_STATIC const char *inputTypeNames[GPAD_MAP_COUNT] IW6_AT("", "inputTypeNames");
IW6_STATIC GpadAxesGlob gaGlobs[1] IW6_AT("", "gaGlobs");
IW6_STATIC int lastGamepadEventTimeGlobal IW6_AT("", "lastGamepadEventTimeGlobal");

// 1400ACB30  client/cl_gamepad.cpp:173
void CL_InitGamepadCommands()
{
	IW6_STATIC cmd_function_s Axis_Bind_f_VAR IW6_AT("CL_InitGamepadCommands", "Axis_Bind_f_VAR");
	IW6_STATIC cmd_function_s Axis_Unbindall_f_VAR IW6_AT("CL_InitGamepadCommands", "Axis_Unbindall_f_VAR");

	Cmd_AddCommand("bindaxis", Axis_Bind_f, Axis_Bind_f_VAR);
	Cmd_AddCommand("unbindallaxis", Axis_Unbindall_f, Axis_Unbindall_f_VAR);
}

// 1400ACAF0  client/cl_gamepad.cpp:180
void CL_InitGamepadAxisBindings()
{
	for (int virtAxis = 0; virtAxis < GPAD_VIRTAXIS_COUNT; virtAxis++)
	{
		gaGlobs[0].virtualAxes[virtAxis].physicalAxis = GPAD_PHYSAXIS_NONE;
		gaGlobs[0].virtualAxes[virtAxis].mapType = GPAD_MAP_SQUARED;
		gaGlobs[0].axesValues[virtAxis] = 0;
	}
}

// Name -> enum lookups (inlined into Axis_Bind_f)
static inline GamepadPhysicalAxis StringToPhysicalAxis(const char *name)
{
	for (int axis = 0; axis < GPAD_PHYSAXIS_COUNT; axis++)
	{
		if (!I_stricmp(name, physicalAxisNames[axis]))
			return (GamepadPhysicalAxis)axis;
	}
	return GPAD_PHYSAXIS_NONE;
}

static inline GamepadVirtualAxis StringToVirtualAxis(const char *name)
{
	for (int axis = 0; axis < GPAD_VIRTAXIS_COUNT; axis++)
	{
		if (!I_stricmp(name, virtualAxisNames[axis]))
			return (GamepadVirtualAxis)axis;
	}
	return GPAD_VIRTAXIS_NONE;
}

static inline GamepadMapping StringToGamePadMapping(const char *name)
{
	for (int mapType = 0; mapType < GPAD_MAP_COUNT; mapType++)
	{
		if (!I_stricmp(name, inputTypeNames[mapType]))
			return (GamepadMapping)mapType;
	}
	return GPAD_MAP_NONE;
}

// 1400AC560  client/cl_gamepad.cpp:279
void Axis_Bind_f()
{
	char axisName[1024];

	const int argc = Cmd_Argc();
	if (argc < 2)
		return;

	I_strncpyz(axisName, Cmd_Argv(1), sizeof(axisName));
	I_strupr(axisName);
	const GamepadPhysicalAxis physAxis = StringToPhysicalAxis(axisName);
	if (physAxis == GPAD_PHYSAXIS_NONE)
		return;

	// Without a virtual axis argument the axis stays GPAD_VIRTAXIS_NONE (-1), and the binding below is written one
	// entry before virtualAxes[0], over axesValues[4..5] (records/bugs.tsv B0008).
	GamepadVirtualAxis virtAxis = GPAD_VIRTAXIS_NONE;
	if (argc >= 3)
	{
		I_strncpyz(axisName, Cmd_Argv(2), sizeof(axisName));
		I_strupr(axisName);
		virtAxis = StringToVirtualAxis(axisName);
		if (virtAxis == GPAD_VIRTAXIS_NONE)
			return;
	}

	GamepadMapping mapType = GPAD_MAP_SQUARED;
	if (argc >= 4)
	{
		I_strncpyz(axisName, Cmd_Argv(3), sizeof(axisName));
		I_strupr(axisName);
		mapType = StringToGamePadMapping(axisName);
		if (mapType == GPAD_MAP_NONE)
			return;
	}

	gaGlobs[0].virtualAxes[virtAxis].physicalAxis = physAxis;
	gaGlobs[0].virtualAxes[virtAxis].mapType = mapType;
	dvar_modifiedFlags |= DVAR_ARCHIVE;
}

// 1400AC770  client/cl_gamepad.cpp:343
void Axis_Unbindall_f()
{
	for (int virtAxis = 0; virtAxis < GPAD_VIRTAXIS_COUNT; virtAxis++)
		gaGlobs[0].virtualAxes[virtAxis].physicalAxis = GPAD_PHYSAXIS_NONE;
}

// 1400AC7B0  client/cl_gamepad.cpp:579
bool CL_CheckForIgnoreDueToRepeat(LocalClientNum_t localClientNum, int key, int repeatCount, int time)
{
	clientUIActive_t *uiGlobals = CL_GetLocalClientUIGlobals(localClientNum);

	if ((uiGlobals->keyCatchers & KEYCATCH_UI) || (uiGlobals->keyCatchers & KEYCATCH_UNKNOWN_40))
	{
		for (int i = 0; i < 8; i++)
		{
			if (key != menuScrollButtonList[i])
				continue;

			// menu scrolling: first repeat after a delay, then faster the longer it is held
			if (repeatCount == 1)
			{
				uiGlobals->nextScrollTime = time + Dvar_GetInt("gpad_menu_scroll_delay_first");
				return false;
			}
			if (time <= uiGlobals->nextScrollTime)
				return true;

			const int delayStart = Dvar_GetInt("gpad_menu_scroll_delay_rest_start");
			const int delayEnd = Dvar_GetInt("gpad_menu_scroll_delay_rest_end");
			int delay = delayStart - Dvar_GetInt("gpad_menu_scroll_delay_rest_accel") * repeatCount;
			if (delay >= delayStart)
				delay = delayStart;
			if (delay <= delayEnd)
				delay = delayEnd;
			uiGlobals->nextScrollTime = time + delay;
			return false;
		}
		if (cl_multi_gamepads_enabled)
			return false;
	}
	return repeatCount > 1;
}

// 1400AC8B0  client/cl_gamepad.cpp:732
void CL_GamepadButtonEvent(LocalClientNum_t localClientNum, int controllerIndex, int key, int down, unsigned int time)
{
	clientUIActive_t *uiGlobals = CL_GetLocalClientUIGlobals(localClientNum);
	PlayerKeyState *keyState = &playerKeys[localClientNum];

	const uiMenuCommand_t activeMenu =
		(uiGlobals->keyCatchers & KEYCATCH_UI) ? UI_GetActiveMenu(localClientNum) : UIMENU_NONE;

	// d-pad debounce outside menus: a press at right angles to the last one is ignored for a while
	if (down && activeMenu == UIMENU_NONE && key >= K_DPAD_UP && key <= K_DPAD_RIGHT)
	{
		const int latest = uiGlobals->dpadLatestKey;
		if (latest
		    && (((latest == K_DPAD_UP || latest == K_DPAD_DOWN) && (key == K_DPAD_LEFT || key == K_DPAD_RIGHT))
		        || ((latest == K_DPAD_LEFT || latest == K_DPAD_RIGHT) && (key == K_DPAD_UP || key == K_DPAD_DOWN)))
		    && Sys_Milliseconds() < uiGlobals->dpadNextTime)
			return;
		uiGlobals->dpadNextTime = Sys_Milliseconds() + gpad_dpadDebounceTime->current.integer;
		uiGlobals->dpadLatestKey = key;
	}

	const connstate_t connectionState = uiGlobals->connectionState;
	KeyState *ks = &keyState->keys[key];
	const int prevDown = ks->down;
	ks->down = down;

	if (time && connectionState < CA_CONNECTING)
		lastGamepadEventTimeGlobal = Sys_Milliseconds();

	if (!down)
	{
		ks->repeats = 0;
		if (--keyState->anyKeyDown < 0)
			keyState->anyKeyDown = 0;
	}
	else
	{
		ks->repeats++;
		if (ks->repeats == 1)
			keyState->anyKeyDown++;
		if (CL_CheckForIgnoreDueToRepeat(localClientNum, key, ks->repeats, time))
			return;
	}

	if ((uiGlobals->keyCatchers & KEYCATCH_LOCATION_SELECTION) && down > 0)
	{
		if (key == K_BUTTON_B || key == K_BUTTON_X)
			keyState->locSelInputState = LOC_SEL_INPUT_CANCEL;
		else if (key == K_BUTTON_A || ks->binding == 1 || ks->binding == 33)  // "+attack", "+attack_akimbo_accessible"
			keyState->locSelInputState = LOC_SEL_INPUT_CONFIRM;
		return;
	}

	keyState->locSelInputState = LOC_SEL_INPUT_NONE;
	if (!down)
	{
		// releasing a key runs the "-" half of a "+" command (odd entries of g_bindCommands up to "-sprint_zoom")
		const int binding = ks->binding;
		if (binding < 39 && (binding & 1))
			CL_ExecBinding(localClientNum, binding + 1, key, prevDown);
		if ((uiGlobals->keyCatchers & KEYCATCH_UI) && cls.uiStarted)
			UI_KeyEvent(localClientNum, key, 0);
		return;
	}

	if ((key == K_BUTTON_A || key == K_BUTTON_START) && (connectionState == CA_CINEMATIC || connectionState == CA_LOGO))
		return;
	if (connectionState == CA_DISCONNECTED)
		return;
	const int binding = ks->binding;
	if (!binding)
		return;
	if (CG_TranslateGamepadButton(localClientNum, key, binding))
		return;
	CL_ExecBinding(localClientNum, binding, key, 0);
}
