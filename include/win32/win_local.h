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

// An event in the system event queue (PS4 server PDB layout, which the Store build has too: evPortIndex is never
// written there, so it stays 0)
struct sysEvent_t
{
	int evPortIndex;
	int evTime;
	sysEventType_t evType;
	int evValue;
	int evValue2;
	int evPtrLength;  // the size of evPtr's allocation (SE_CONSOLE: the text and its terminator)
	void *evPtr;      // Com_AllocEvent'ed; freed by whoever takes the event
};
static_assert(sizeof(sysEvent_t) == 0x20, "sysEvent_t layout");

#define MAX_QUED_EVENTS 256
#define MASK_QUED_EVENTS (MAX_QUED_EVENTS - 1)

extern WinVars_t g_wv;          // win32/win_main.cpp
extern const dvar_t *in_mouse;  // win32/win_input.cpp

// win32/win_main.cpp
void Sys_QueEvent(int time, sysEventType_t type, int value, int value2, int ptrLength, void *ptr);
void Sys_ShutdownEvents();
void Sys_LoadingKeepAlive();
sysEvent_t Sys_GetEvent();

char *Sys_ConsoleInput();         // win32/win_syscon.cpp
void *Com_AllocEvent(int size);   // qcommon/common.cpp
void Com_Quit_f();                // qcommon/common.cpp

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
