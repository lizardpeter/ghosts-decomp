// win32/win_input.cpp
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), the final target: the servers have no
// client platform layer. The file name, the function names and their order come from Black Ops'
// win32/win_input.cpp (black-ops-1-decomp, from its server PDB), whose code this file still closely follows;
// the Steam build keeps the same functions out of line in the same object (docs/input.md). Line numbers are
// unknown. Each function is tagged with its Store address; a function the Store build inlines everywhere has
// no address and is tested through its callers.
//
// How the mouse is read: once a frame, IN_MouseMove takes the cursor position (GetCursorPos), subtracts the
// previous one, and puts the cursor back in the middle of the window. The movement is therefore the system
// cursor's, after Windows' pointer speed and acceleration, and in fullscreen the cursor is first clamped to the
// window, so a single frame can't move more than the window's half width (records/bugs.tsv B0010, B0011).

#include <windows.h>

#include <iw6_static.h>

#include "client/client.h"
#include "qcommon/dvar.h"
#include "win32/win_local.h"

#define IW6_SOURCE "win32/win_input.cpp"

// File statics
IW6_STATIC WinMouseVars_t s_wmv IW6_AT("", "s_wmv");
IW6_STATIC int window_center_x IW6_AT("", "window_center_x");
IW6_STATIC int window_center_y IW6_AT("", "window_center_y");
IW6_STATIC int in_appactive IW6_AT("", "in_appactive");

// s_wmv.oldPos.x when there is no previous position (mouse just activated, or the window lost focus): the next
// movement is taken as zero.
#define MOUSE_POS_RESET -100000

// Elsewhere in the client
extern const dvar_t *r_displayMode;     // gfx_d3d/r_init.cpp: 0 = fullscreen, then windowed modes
int CL_MouseEvent(int x, int y, int dx, int dy);  // client_mp/cl_input.cpp
void CL_ShowSystemCursor(int show);             // client_mp/cl_input.cpp
void sub_14030B6E0(int clip);                    // client_mp: confines the cursor to the window (name unknown)
void IN_GamepadsMove();                         // win32/win_input.cpp, not reconstructed yet
bool Dvar_GetBool(const char *dvarName);
void Dvar_ClearModified(const dvar_t *dvar);
const dvar_t *Dvar_RegisterBool(const char *dvarName, bool value, unsigned int flags, const char *description);
void IN_StartupGamepads();                      // win32/win_input.cpp, not reconstructed yet
void sub_140549740(void (*callback)(int));       // gamepad/: sets a callback (name unknown)
void sub_140549770(void (*callback)(int));       // gamepad/: sets a callback (name unknown)
void sub_14054A330();                            // win32/win_input.cpp: updates the gamepads (name unknown)
void sub_1403172E0(int);                         // client: the two callbacks (names unknown)
void sub_140317340(int);
void sub_14054A2E0();                            // win32/win_input.cpp: empty in the Store build (name unknown)

// 14054ADF0
void IN_RecenterMouse()
{
	RECT window_rect;

	GetWindowRect(g_wv.hWnd, &window_rect);
	window_center_x = (window_rect.right + window_rect.left) / 2;
	window_center_y = (window_rect.top + window_rect.bottom) / 2;
	SetCursorPos(window_center_x, window_center_y);
}

// (inlined everywhere in the Store build)
void IN_DeactivateWin32Mouse()
{
	ClipCursor(NULL);
	IN_ShowSystemCursor(1);
}

// (inlined everywhere in the Store build)
int IN_IsForegroundWindow()
{
	const HWND foreground = GetForegroundWindow();
	return foreground && foreground == g_wv.hWnd;
}

// 14054A710
void IN_ActivateMouse(int force)
{
	if (!s_wmv.mouseInitialized)
		return;

	if (!in_mouse->current.enabled)
	{
		s_wmv.mouseActive = false;
		return;
	}
	if (!force && s_wmv.mouseActive)
		return;

	if (!IN_IsForegroundWindow())
	{
		s_wmv.mouseActive = false;
		return;
	}
	s_wmv.mouseActive = true;
	s_wmv.oldPos.x = MOUSE_POS_RESET;

	const connstate_t connectionState = CL_GetLocalClientUIGlobals(LOCAL_CLIENT_0)->connectionState;
	if (connectionState > CA_DISCONNECTED && connectionState < CA_ACTIVE)
	{
		CL_ShowSystemCursor(0);
		sub_14030B6E0(0);
	}
}

// (inlined everywhere in the Store build)
void IN_DeactivateMouse()
{
	if (!s_wmv.mouseInitialized || !s_wmv.mouseActive)
		return;
	s_wmv.mouseActive = false;
	IN_DeactivateWin32Mouse();
}

// 14054AD50
void IN_MouseEvent(int mstate)
{
	if (s_wmv.mouseInitialized && mstate != s_wmv.oldButtonState)
	{
		const int changed = mstate ^ s_wmv.oldButtonState;
		for (int button = 0; button < 5; button++)
		{
			if (changed & (1 << button))
				Sys_QueEvent(g_wv.sysMsgTime, SE_KEY, K_MOUSE1 + button, (mstate & (1 << button)) != 0, 0, NULL);
		}
		s_wmv.oldButtonState = mstate;
	}
}

// (inlined everywhere in the Store build)
void IN_ClampMouseMove(POINT *curPos)
{
	RECT rc;

	GetWindowRect(g_wv.hWnd, &rc);
	ClipCursor(&rc);
	bool isClamped = false;
	if (curPos->x < rc.left)
	{
		curPos->x = rc.left;
		isClamped = true;
	}
	else if (curPos->x >= rc.right)
	{
		curPos->x = rc.right - 1;
		isClamped = true;
	}
	if (curPos->y < rc.top)
	{
		curPos->y = rc.top;
		isClamped = true;
	}
	else if (curPos->y >= rc.bottom)
	{
		curPos->y = rc.bottom - 1;
		isClamped = true;
	}
	if (isClamped)
		SetCursorPos(curPos->x, curPos->y);
}

// (inlined everywhere in the Store build)
void IN_MouseMove()
{
	if (!IN_IsForegroundWindow())
	{
		s_wmv.oldPos.x = MOUSE_POS_RESET;
		return;
	}

	POINT curPos;
	GetCursorPos(&curPos);
	if (r_displayMode->current.integer == 0)  // fullscreen
		IN_ClampMouseMove(&curPos);

	const bool resetPos = s_wmv.oldPos.x == MOUSE_POS_RESET;
	int dx;
	int dy;
	if (resetPos)
	{
		dx = 0;
		dy = 0;
	}
	else
	{
		dx = curPos.x - s_wmv.oldPos.x;
		dy = curPos.y - s_wmv.oldPos.y;
	}
	s_wmv.oldPos = curPos;

	// the position in the client area, in render pixels
	ScreenToClient(g_wv.hWnd, &curPos);
	curPos.x = curPos.x * (int)cls.vidConfig.displayWidth / (int)cls.vidConfig.monitorWidth;
	curPos.y = curPos.y * (int)cls.vidConfig.displayHeight / (int)cls.vidConfig.monitorHeight;

	g_wv.recenterMouse = CL_MouseEvent(curPos.x, curPos.y, dx, dy);
	if (g_wv.recenterMouse && (dx || dy || resetPos))
	{
		IN_RecenterMouse();
		s_wmv.oldPos.x = window_center_x;
		s_wmv.oldPos.y = window_center_y;
	}
}

// 14054AE40
void IN_SetCursorPos(int x, int y)
{
	POINT curPos;

	curPos.x = x;
	curPos.y = y;
	ClientToScreen(g_wv.hWnd, &curPos);
	SetCursorPos(curPos.x, curPos.y);
	s_wmv.oldPos = curPos;
}

// 14054AE80
void IN_ShowSystemCursor(int show)
{
	// ShowCursor keeps a display count: call it until the count is exactly 0 (shown) or -1 (hidden)
	const int desiredShow = show ? 0 : -1;
	for (int actualShow = ShowCursor(show); actualShow != desiredShow; actualShow = ShowCursor(actualShow < desiredShow))
		;
}

// (inlined everywhere in the Store build)
void IN_StartupMouse()
{
	s_wmv.mouseInitialized = in_mouse->current.enabled;
}

// (inlined everywhere in the Store build)
void IN_Startup()
{
	IN_StartupMouse();
	IN_StartupGamepads();
	sub_140549740(sub_1403172E0);
	sub_140549770(sub_140317340);
	sub_14054A330();
	Dvar_ClearModified(in_mouse);
}

// 14054AEC0
void IN_Shutdown()
{
	sub_14054A2E0();
	IN_DeactivateMouse();
}

// 14054ACD0
void IN_Init()
{
	in_mouse = Dvar_RegisterBool("in_mouse", true, 3, "Initialize the mouse drivers");
	IN_Startup();
}

// 14054A650
void IN_Activate(int active)
{
	in_appactive = active;
	if (!active)
		IN_DeactivateMouse();
	else
		IN_ActivateMouse(1);
}

// 14054A790
void IN_Frame()
{
	if (Dvar_GetBool("ClickToContinue"))
		PostMessageA(g_wv.hWnd, WM_LBUTTONDOWN, MK_LBUTTON, 0);

	if (!s_wmv.mouseInitialized)
		return;
	if (!in_appactive)
	{
		IN_DeactivateMouse();
		return;
	}

	IN_ActivateMouse(0);
	IN_MouseMove();
	if (IN_IsForegroundWindow())
		IN_GamepadsMove();
}
