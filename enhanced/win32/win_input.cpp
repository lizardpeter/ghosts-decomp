// enhanced/win32/win_input.cpp: the mouse aims with raw input only (records/bugs.tsv B0010, B0011).
//
// Replaces two functions of src/win32/win_input.cpp; everything else there is used as it is. IN_MouseMove takes
// the raw movement (enhanced/win32/win_rawinput.cpp) instead of the cursor's. The cursor position is still read,
// but only for the menus' cursor and to keep the cursor in the window; it never moves the view.

#include <windows.h>

#include <iw6_static.h>

#include "client/client.h"
#include "enhanced/raw_input.h"
#include "qcommon/dvar.h"
#include "win32/win_local.h"

#define IW6_SOURCE "win32/win_input.cpp"

IW6_STATIC WinMouseVars_t s_wmv IW6_AT("", "s_wmv");
IW6_STATIC int window_center_x IW6_AT("", "window_center_x");
IW6_STATIC int window_center_y IW6_AT("", "window_center_y");

#define MOUSE_POS_RESET -100000

extern const dvar_t *r_displayMode;
int CL_MouseEvent(int x, int y, int dx, int dy);
int IN_IsForegroundWindow();
void IN_ClampMouseMove(POINT *curPos);
void IN_Startup();
const dvar_t *Dvar_RegisterBool(const char *dvarName, bool value, unsigned int flags, const char *description);
void CL_RegisterMouseDvars();  // enhanced/client_mp/cl_input.cpp

// Store 14054ACD0, plus the raw input thread and the mouse dvars
void IN_Init()
{
	in_mouse = Dvar_RegisterBool("in_mouse", true, 3, "Initialize the mouse drivers");
	CL_RegisterMouseDvars();
	IN_StartRawInput();
	IN_Startup();
}

void IN_MouseMove()
{
	// always taken, so movement made while the game is in the background never arrives later
	int dx;
	int dy;
	IN_TakeRawMouse(&dx, &dy);

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
	if (resetPos)
	{
		// the frame focus comes back: the movement that brought the game to the front isn't aim
		dx = 0;
		dy = 0;
	}
	s_wmv.oldPos = curPos;

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
