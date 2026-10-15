// client/cl_keys.cpp
//
// Reconstructed from the PS4 dedicated server (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis, changelist 715098), which
// keeps the binding and key-state half of this file; the key-event and console-input half is client-only and
// will come from the Store build. Functions appear in original line order; each is tagged with its address in
// that build and its original line.

#include <ctype.h>
#include <string.h>

#include <iw6_static.h>

#include "client/client.h"
#include "qcommon/cmd.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "client/cl_keys.cpp"

// The bindable commands; a key's binding is an index into this table (0 = unbound). File static.
IW6_STATIC const char *g_bindCommands[45] IW6_AT("", "g_bindCommands");

// 1400AD210  client/cl_keys.cpp:1697
int Key_GetOverstrikeMode(LocalClientNum_t localClientNum)
{
	return playerKeys[localClientNum].overstrikeMode;
}

// 1400AD4B0  client/cl_keys.cpp:1703
void Key_SetOverstrikeMode(LocalClientNum_t localClientNum, int state)
{
	playerKeys[localClientNum].overstrikeMode = state;
}

// 1400AD240  client/cl_keys.cpp:1709
int Key_IsDown(LocalClientNum_t localClientNum, int keynum)
{
	if (keynum == -1)
		return 0;
	return playerKeys[localClientNum].keys[keynum].down;
}

// 1400AD4F0  client/cl_keys.cpp:1731
int Key_StringToKeynum(const char *str)
{
	if (!str || !str[0])
		return -1;
	if (!str[1])
		return str[0];

	// "0x" followed by two hex digits
	if (str[0] == '0' && str[1] == 'x' && strlen(str) == 4)
	{
		int n1 = str[2];
		if (n1 >= '0' && n1 <= '9')
			n1 -= '0';
		else if (n1 >= 'a' && n1 <= 'f')
			n1 = n1 - 'a' + 10;
		else
			n1 = 0;

		int n2 = str[3];
		if (n2 >= '0' && n2 <= '9')
			n2 -= '0';
		else if (n2 >= 'a' && n2 <= 'f')
			n2 = n2 - 'a' + 10;
		else
			n2 = 0;

		return n1 * 16 + n2;
	}

	for (const keyname_t *kn = keynames; kn->name; kn++)
	{
		if (!I_stricmp(str, kn->name))
			return kn->keynum;
	}
	return -1;
}

// 1400AD270  client/cl_keys.cpp:1792
bool Key_IsValidGamePadChar(const char key)
{
	return (key >= K_FIRSTGAMEPADBUTTON_RANGE_1 && key <= K_LASTGAMEPADBUTTON_RANGE_1)
	    || (key >= K_FIRSTGAMEPADBUTTON_RANGE_2 && key <= K_LASTGAMEPADBUTTON_RANGE_2)
	    || (key >= K_FIRSTGAMEPADBUTTON_RANGE_3 && key <= K_LASTGAMEPADBUTTON_RANGE_3);
}

// 1400AD290  client/cl_keys.cpp:1805
const char *Key_KeynumToString(int keynum, int translate, int gamePadOnly)
{
	IW6_STATIC char tinystr[5] IW6_AT("Key_KeynumToString", "tinystr");

	if (keynum == -1)
		return "<KEY NOT FOUND>";
	if (keynum < 0 || keynum > 255)
		return "<OUT OF RANGE>";

	if (translate && SEH_GetCurrentLanguage() == LANGUAGE_FRENCH && keynum >= '0' && keynum <= '9')
		return frenchNumberKeysMap[keynum - '0'];

	const keyname_t *kn;
	if (keynum > ' ' && keynum < 127 && keynum != '"')
	{
		// printable ascii; ';' has a name of its own, used when not translating
		tinystr[0] = (char)toupper(keynum);
		tinystr[1] = 0;
		if (keynum != ';' || translate)
			return tinystr;
		kn = keynames;
	}
	else if (translate)
	{
		if (gamePadOnly == 1 && Key_IsValidGamePadChar((char)keynum))
		{
			tinystr[0] = (char)keynum;
			tinystr[1] = 0;
			return tinystr;
		}
		kn = keynames_localized;
	}
	else
	{
		kn = keynames;
	}

	for (; kn->name; kn++)
	{
		if (keynum == kn->keynum)
			return kn->name;
	}

	// make a hex string
	const int i = keynum >> 4;
	const int j = keynum & 15;
	tinystr[0] = '0';
	tinystr[1] = 'x';
	tinystr[2] = (char)(i > 9 ? i + 'a' - 10 : i + '0');
	tinystr[3] = (char)(j > 9 ? j + 'a' - 10 : j + '0');
	tinystr[4] = 0;
	return tinystr;
}

// 1400AD440  client/cl_keys.cpp:1898
void Key_SetBinding(LocalClientNum_t localClientNum, int keynum, int binding)
{
	if (keynum == -1)
		return;
	playerKeys[localClientNum].keys[keynum].binding = binding;
	dvar_modifiedFlags |= DVAR_ARCHIVE;
}

// 1400AD000  client/cl_keys.cpp:1929
int Key_GetBindingForCmd(const char *command)
{
	for (int i = 0; i < 45; i++)
	{
		if (!I_stricmp(command, g_bindCommands[i]))
			return i;
	}
	return 0;
}

// 1400ACFE0  client/cl_keys.cpp:1955
int Key_GetBinding(LocalClientNum_t localClientNum, int keynum)
{
	return playerKeys[localClientNum].keys[keynum].binding;
}

// 1400AD120  client/cl_keys.cpp:1963
int Key_GetCommandAssignmentInternal(LocalClientNum_t localClientNum, const char *command, int *const twokeys,
                                     int gamePadOnly)
{
	twokeys[0] = -1;
	twokeys[1] = -1;

	const int bindNum = Key_GetBindingForCmd(command);
	if (!bindNum)
		return 0;

	int count = 0;
	for (int keynum = 0; keynum < 256; keynum++)
	{
		if (gamePadOnly == 1 && !Key_IsValidGamePadChar((char)keynum))
			continue;
		if (playerKeys[localClientNum].keys[keynum].binding == bindNum)
		{
			twokeys[count] = keynum;
			count++;
			if (count == 2)
				return 2;
		}
	}
	return count;
}

// 1400AD060  client/cl_keys.cpp:2030
int Key_GetCommandAssignment(LocalClientNum_t localClientNum, const char *command, int *const twokeys)
{
	twokeys[0] = -1;
	twokeys[1] = -1;

	const int bindNum = Key_GetBindingForCmd(command);
	if (!bindNum)
		return 0;

	int count = 0;
	for (int keynum = 0; keynum < 256; keynum++)
	{
		if (playerKeys[localClientNum].keys[keynum].binding == bindNum)
		{
			twokeys[count] = keynum;
			count++;
			if (count == 2)
				return 2;
		}
	}
	return count;
}

// 1400AD720  client/cl_keys.cpp:2055
void Key_Unbind_f()
{
	if (Cmd_Argc() != 2)
		return;

	const int b = Key_StringToKeynum(Cmd_Argv(1));
	if (b == -1)
		return;
	Key_SetBinding(LOCAL_CLIENT_0, b, 0);
}

// 1400AD790  client/cl_keys.cpp:2076
void Key_Unbindall_f()
{
	for (int i = 0; i < 256; i++)
		Key_SetBinding(LOCAL_CLIENT_0, i, 0);
}

// 1400ACEA0  client/cl_keys.cpp:2092
void Key_Bind_f()
{
	const int c = Cmd_Argc();
	if (c < 2)
		return;

	int b = Key_StringToKeynum(Cmd_Argv(1));
	if (b == -1)
		return;
	b = tolower(b);
	if (c == 2)
		return;

	const int bindNum = Key_GetBindingForCmd(Cmd_Argv(2));
	if (bindNum)
		Key_SetBinding(LOCAL_CLIENT_0, b, bindNum);
}

// 1400AD5F0  client/cl_keys.cpp:2163
void Key_SwapBind_f()
{
	int keys[2];
	int bindings[2];

	if (Cmd_Argc() != 3)
		return;

	for (int i = 0; i < 2; i++)
	{
		keys[i] = Key_StringToKeynum(Cmd_Argv(i + 1));
		if (keys[i] == -1)
			return;
		keys[i] = tolower(keys[i]);
		bindings[i] = Key_GetBinding(LOCAL_CLIENT_0, keys[i]);
		if (!bindings[i])
			return;
	}

	Key_SetBinding(LOCAL_CLIENT_0, keys[0], bindings[1]);
	Key_SetBinding(LOCAL_CLIENT_0, keys[1], bindings[0]);
}

// 1400ACE30  client/cl_keys.cpp:2356
void CL_InitKeyCommands()
{
	IW6_STATIC cmd_function_s Key_Bind_f_VAR IW6_AT("CL_InitKeyCommands", "Key_Bind_f_VAR");
	IW6_STATIC cmd_function_s Key_SwapBind_f_VAR IW6_AT("CL_InitKeyCommands", "Key_SwapBind_f_VAR");
	IW6_STATIC cmd_function_s Key_Unbind_f_VAR IW6_AT("CL_InitKeyCommands", "Key_Unbind_f_VAR");
	IW6_STATIC cmd_function_s Key_Unbindall_f_VAR IW6_AT("CL_InitKeyCommands", "Key_Unbindall_f_VAR");

	Cmd_AddCommand("bind", Key_Bind_f, Key_Bind_f_VAR);
	Cmd_AddCommand("bind_swap", Key_SwapBind_f, Key_SwapBind_f_VAR);
	Cmd_AddCommand("unbind", Key_Unbind_f, Key_Unbind_f_VAR);
	Cmd_AddCommand("unbindall", Key_Unbindall_f, Key_Unbindall_f_VAR);
}

// 1400ACF50  client/cl_keys.cpp:3157
void Key_ClearStates(LocalClientNum_t localClientNum)
{
	PlayerKeyState *keyState = &playerKeys[localClientNum];
	keyState->anyKeyDown = 0;
	for (int i = 0; i < 256; i++)
	{
		if (keyState->keys[i].down && !Com_ErrorEntering())
			CL_GamepadButtonEvent(localClientNum, CL_ControllerIndexFromClientNum(localClientNum), i, 0, 0);
		keyState->keys[i].down = 0;
		keyState->keys[i].repeats = 0;
	}
}

// 1400ACD80  client/cl_keys.cpp:3169
int CL_GetKeyBindingInternal(LocalClientNum_t localClientNum, const char *command, char (*const keyNames)[128],
                             int gamePadOnly)
{
	int twokeys[2];

	Sys_EnterCriticalSection(CRITSECT_KEY_BINDINGS);
	keyNames[1][0] = 0;
	const int count = Key_GetCommandAssignmentInternal(localClientNum, command, twokeys, gamePadOnly);
	if (count == 0)
	{
		strcpy(keyNames[0], "KEY_UNBOUND");
	}
	else
	{
		Key_KeynumToStringBuf(twokeys[0], keyNames[0], 128, gamePadOnly);
		if (count == 2)
			Key_KeynumToStringBuf(twokeys[1], keyNames[1], 128, gamePadOnly);
	}
	Sys_LeaveCriticalSection(CRITSECT_KEY_BINDINGS);
	return count;
}

// 1400ACD70  client/cl_keys.cpp:3206
int CL_GetGamePadBinding(LocalClientNum_t localClientNum, const char *command, char (*const keyNames)[128])
{
	return CL_GetKeyBindingInternal(localClientNum, command, keyNames, 1);
}

// 1400AD4D0  client/cl_keys.cpp:3249
void Key_Shutdown()
{
	for (int i = 0; i < 256; i++)
		playerKeys[0].keys[i].binding = 0;
}

// 1400AD230  client/cl_keys.cpp:3271
bool Key_IsCatcherActive(LocalClientNum_t localClientNum, int mask)
{
	return (CL_GetLocalClientUIGlobals(localClientNum)->keyCatchers & mask) != 0;
}

// 1400AD430  client/cl_keys.cpp:3289
void Key_RemoveCatcher(LocalClientNum_t localClientNum, int andMask)
{
	// callers pass the complement of the catcher to remove
	CL_GetLocalClientUIGlobals(localClientNum)->keyCatchers &= andMask;
}

// 1400AD490  client/cl_keys.cpp:3301
void Key_SetCatcher(LocalClientNum_t localClientNum, int catcher)
{
	clientUIActive_t *uiGlobals = CL_GetLocalClientUIGlobals(localClientNum);
	if (uiGlobals->keyCatchers & KEYCATCH_CONSOLE)
		catcher |= KEYCATCH_CONSOLE;  // the console stays up
	uiGlobals->keyCatchers = catcher;
}
