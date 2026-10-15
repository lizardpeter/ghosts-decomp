// win32/win_local.h: the Windows platform layer's shared state (types from the PS4 server PDB, iw6_ds_ps4, which has
// the same layout as the Store build for these).
#pragma once

#include <windows.h>

struct dvar_t;

struct WinVars_t
{
	HINSTANCE reflib_library;
	int reflib_active;
	HWND hWnd;
	HINSTANCE hInstance;
	int activeApp;
	int isMinimized;
	int hasFocus;
	int activationStateChanged;
	int recenterMouse;
	HHOOK lowLevelKeyboardHook;
	unsigned int sysMsgTime;
};

struct WinMouseVars_t
{
	int oldButtonState;
	POINT oldPos;
	bool mouseActive;
	bool mouseInitialized;
};

enum sysEventType_t
{
	SE_NONE = 0x0,
	SE_KEY = 0x1,
	SE_CHAR = 0x2,
	SE_CONSOLE = 0x3,
};

extern WinVars_t g_wv;          // win32/win_main.cpp
extern const dvar_t *in_mouse;  // win32/win_input.cpp

void Sys_QueEvent(int time, sysEventType_t type, int value, int value2, int ptrLength, void *ptr);

// win32/win_input.cpp
void IN_RecenterMouse();
void IN_ActivateMouse(int force);
void IN_DeactivateMouse();
void IN_MouseEvent(int mstate);
void IN_SetCursorPos(int x, int y);
void IN_ShowSystemCursor(int show);
void IN_Shutdown();
void IN_Init();
void IN_Activate(int active);
void IN_Frame();
