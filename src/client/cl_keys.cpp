// client/cl_keys.cpp
//
// Reconstructed from the PS4 dedicated server (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis, changelist 715098), which
// keeps the binding and key-state half of this file; the key-event half is client-only and comes from the
// Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses: CL_KeyEvent and CL_CharEvent, named and
// placed after Black Ops' (server PDB, client/cl_keys.cpp:2219 and 2759; IW6 line numbers unknown). Functions appear in
// original line order; each is tagged with its address in that build and its original line.

#include <ctype.h>
#include <string.h>
#include <windows.h>

#include <iw6_static.h>

#include "client/client.h"
#include "qcommon/cmd.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "client/cl_keys.cpp"

struct ScreenPlacement;

// Elsewhere in the client (Store build; docs/input.md, "The key path")
extern const dvar_t *cl_bypassMouseInput;      // client_mp/cl_main_mp.cpp
extern bool unk_14416A0F9[1];                  // per local client: Escape in game opens the main menu, not the in-game one (name unknown)
void Message_Key(LocalClientNum_t localClientNum, int key);              // client/cl_keys.cpp, Store 140311190
bool Field_CharEvent(LocalClientNum_t localClientNum, const ScreenPlacement *scrPlace, field_t *edit, int ch);  // 14030FD40
const ScreenPlacement *sub_140344A20(LocalClientNum_t localClientNum);  // the placement the chat line is drawn with
void CL_StopLogoOrCinematic(LocalClientNum_t localClientNum);           // client_mp/cl_main_mp.cpp, Store 140316A40
int UI_SetActiveMenu(LocalClientNum_t localClientNum, int menu);         // ui_mp/ui_main_mp.cpp
int sub_140527D90(LocalClientNum_t localClientNum);                     // the menu Escape opens while disconnected
bool sub_140222E90();                                                   // LUI: always true in the Store build
void sub_140222ED0(LocalClientNum_t localClientNum, int controllerIndex, int key, int down, int keyCatchers);  // LUI key event
void sub_140221EC0(LocalClientNum_t localClientNum, int ch);            // LUI character event
int sub_140503AD0(LocalClientNum_t localClientNum, int key);            // the menu wants this key despite cl_bypassMouseInput
bool CL_IsGamepadEnabled(LocalClientNum_t localClientNum);              // client_mp/cl_input.cpp

// g_bindCommands indices CL_KeyEvent tests (the Store build's table, 1409919F0 + 10 entries: 101 commands)
#define BIND_ATTACK 0x1                     // +attack
#define BIND_ATTACK_AKIMBO_ACCESSIBLE 0x27  // +attack_akimbo_accessible
#define BIND_TALK 0x51                      // +talk; 0x52 -talk
#define BIND_LAST_HELD 0x54                 // bindings up to here come in +/- pairs (odd +, even -)
#define BIND_CHATMODEPUBLIC 0x58
#define BIND_CHATMODETEAM 0x59

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

// Store 14030F710 (Black Ops' CL_KeyEvent, client/cl_keys.cpp:2219: lineage). A key or mouse button went down or up
// (Com_EventLoop's SE_KEY, or CL_GamepadButtonEvent for keys that aren't gamepad buttons). Updates the key state,
// then gives the key to the first taker: location selection, Escape, LUI (which sees every key unless the console
// has them), the console, a menu, the chat line, and last the key's binding (CL_ExecBinding). `time` isn't used:
// the button handlers take com_frameTime.
void CL_KeyEvent(LocalClientNum_t localClientNum, int key, int down, unsigned int time)
{
	PlayerKeyState *keyState = &playerKeys[localClientNum];
	if (keyState->keys[K_ALT].down && key == K_F4 && down)
	{
		PostQuitMessage(0);
		return;
	}

	clientUIActive_t *uiGlobals = CL_GetLocalClientUIGlobals(localClientNum);
	KeyState *keys = &keyState->keys[key];
	const int prevDown = keys->down;
	keys->down = down;
	if (down)
	{
		keys->repeats++;
		if (keys->repeats == 1)
			keyState->anyKeyDown++;
		if (keys->repeats > 1)
		{
			// auto-repeat reaches only the console, the chat line, and a menu's arrow and page keys
			if (!(uiGlobals->keyCatchers & (KEYCATCH_CONSOLE | KEYCATCH_MESSAGE)))
			{
				if (!(uiGlobals->keyCatchers & KEYCATCH_UI))
					return;
				switch (key)
				{
				case K_UPARROW:
				case K_DOWNARROW:
				case K_LEFTARROW:
				case K_RIGHTARROW:
				case K_PGDN:
				case K_PGUP:
					break;
				default:
					return;
				}
			}
			if (key == '`' || key == '~' || key == K_ESCAPE)
				return;
		}
	}
	else
	{
		keys->repeats = 0;
		keyState->anyKeyDown--;
		if (keyState->anyKeyDown < 0)
			keyState->anyKeyDown = 0;
	}

	// selecting a location (airstrike map): Escape cancels, a fire key confirms, everything else is eaten
	if ((uiGlobals->keyCatchers & KEYCATCH_LOCATION_SELECTION) && down > 0)
	{
		if (key == K_ESCAPE)
			keyState->locSelInputState = LOC_SEL_INPUT_CANCEL;
		else if (keys->binding == BIND_ATTACK || keys->binding == BIND_ATTACK_AKIMBO_ACCESSIBLE)
			keyState->locSelInputState = LOC_SEL_INPUT_CONFIRM;
		return;
	}

	const connstate_t clcState = uiGlobals->connectionState;
	keyState->locSelInputState = LOC_SEL_INPUT_NONE;

	if (key == K_ESCAPE && down)
	{
		if (uiGlobals->keyCatchers & KEYCATCH_MESSAGE)
		{
			Message_Key(localClientNum, K_ESCAPE);
			return;
		}
		if (!(uiGlobals->keyCatchers & (KEYCATCH_UI | KEYCATCH_UNKNOWN_40)))
		{
			switch (clcState)
			{
			case CA_CINEMATIC:
			case CA_LOGO:
				CL_StopLogoOrCinematic(localClientNum);
				return;
			case CA_CONNECTING:
			case CA_CHALLENGING:
			case CA_CONNECTED:
			case CA_SENDINGSTATS:
			case CA_SYNCHRONIZING_DATA:
			case CA_PRIMED:
				return;
			case CA_ACTIVE:
				UI_SetActiveMenu(localClientNum, unk_14416A0F9[localClientNum] ? UIMENU_MAIN : UIMENU_INGAME);
				return;
			default:
				if (cls.uiStarted)
					UI_SetActiveMenu(localClientNum, sub_140527D90(localClientNum));
				return;
			}
		}
		if (cls.uiStarted && sub_140222E90())
		{
			const int keyCatchers = uiGlobals->keyCatchers;
			const int controllerIndex = CL_ControllerIndexFromClientNum(localClientNum);
			sub_140222ED0(localClientNum, controllerIndex, K_ESCAPE, down, keyCatchers);
		}
		UI_KeyEvent(localClientNum, K_ESCAPE, down);
		return;
	}

	// LUI sees the key first; while it has the keys (KEYCATCH_UNKNOWN_40) a press goes no further, except +talk
	int luiHasKey = 0;
	if (cls.uiStarted && sub_140222E90())
	{
		const int keyCatchers = uiGlobals->keyCatchers;
		if (!(keyCatchers & KEYCATCH_CONSOLE))
		{
			luiHasKey = (keyCatchers >> 6) & 1;
			const int controllerIndex = CL_ControllerIndexFromClientNum(localClientNum);
			sub_140222ED0(localClientNum, controllerIndex, key, down, keyCatchers);
			if (keys->binding == BIND_TALK || keys->binding == BIND_TALK + 1)
				luiHasKey = 0;
		}
	}

	if (!down)
	{
		// a release runs the "-" half of a held binding, whoever has the keys
		const int binding = keys->binding;
		if (binding <= BIND_LAST_HELD && (binding & 1))
			CL_ExecBinding(localClientNum, binding + 1, key, prevDown);
		if ((uiGlobals->keyCatchers & KEYCATCH_UI) && cls.uiStarted)
			UI_KeyEvent(localClientNum, key, 0);
		return;
	}

	if (luiHasKey)
		return;
	if (uiGlobals->keyCatchers & KEYCATCH_CONSOLE)
		return;  // nothing handles the console's keys here in the Store build

	if (uiGlobals->keyCatchers & KEYCATCH_UI)
	{
		if (UI_GetActiveMenu(localClientNum) != UIMENU_SCOREBOARD)
		{
			// cl_bypassMouseInput: the first three mouse buttons, and keys the menu doesn't want, reach the bindings
			bool toMenu = true;
			if (cl_bypassMouseInput && cl_bypassMouseInput->current.enabled)
			{
				if ((unsigned int)(key - K_MOUSE1) <= K_MOUSE3 - K_MOUSE1)
					toMenu = false;
				else if (!cls.uiStarted)
					return;
				else if (!sub_140503AD0(localClientNum, key))
					toMenu = false;
			}
			if (toMenu)
			{
				if (cls.uiStarted)
					UI_KeyEvent(localClientNum, key, down);
				return;
			}
		}
	}

	if (uiGlobals->keyCatchers & KEYCATCH_MESSAGE)
	{
		Message_Key(localClientNum, key);
		return;
	}

	const int binding = keys->binding;
	if ((unsigned int)(binding - BIND_TALK) > 1)
	{
		if (clcState == CA_DISCONNECTED)
			return;
		if (!binding)
			return;
		// with the gamepad on, keyboard bindings other than the chat keys are ignored
		const bool gamepad = CL_IsGamepadEnabled(localClientNum);
		if (gamepad && binding != BIND_CHATMODETEAM && binding != BIND_CHATMODEPUBLIC)
			return;
	}
	else if (!binding)
	{
		return;
	}
	CL_ExecBinding(localClientNum, binding, key, 0);
}

// Store 14030F4B0 (Black Ops' CL_CharEvent, client/cl_keys.cpp:2759: lineage). A character (WM_CHAR, Com_EventLoop's
// SE_CHAR) for the chat line, a menu or LUI; without one of their catchers it is dropped.
void CL_CharEvent(LocalClientNum_t localClientNum, int key)
{
	if (key == '`' || key == '~')
		return;
	const int keyCatchers = CL_GetLocalClientUIGlobals(localClientNum)->keyCatchers;
	if (keyCatchers & KEYCATCH_CONSOLE)
		return;
	if (keyCatchers & KEYCATCH_MESSAGE)
	{
		Field_CharEvent(localClientNum, sub_140344A20(localClientNum), &playerKeys[localClientNum].chatField, key);
		return;
	}
	if (keyCatchers & KEYCATCH_UI)
	{
		UI_KeyEvent(localClientNum, key | K_CHAR_FLAG, 1);
		return;
	}
	if (keyCatchers & KEYCATCH_UNKNOWN_40)
		sub_140221EC0(localClientNum, key);
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
