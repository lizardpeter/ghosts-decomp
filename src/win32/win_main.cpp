// win32/win_main.cpp (Store build): the system event queue and the window message pump.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names, the layout
// of the queue and of an event come from the PS4 server PDB (iw6_ds_ps4, win32/win_main.cpp:973..1127), whose code is
// the same except where noted; Black Ops' server PDB has the same functions (lineage).
//
// The queue (docs/input.md, "The key path"): a ring of 256 sysEvent_t. The window procedure (MainWndProc, while a pump
// dispatches messages) and IN_MouseEvent add key, character and mouse-button events with Sys_QueEvent; Sys_GetEvent
// takes them out in order, and pumps the window messages only when the queue is empty. Com_EventLoop is the only
// reader. Everything runs under CRITSECT_SYS_EVENT_QUEUE, which is held while a pump dispatches, so the window
// procedure's Sys_QueEvent enters it recursively.

#include <string.h>
#include <windows.h>

#include "client/client.h"
#include "qcommon/qcommon.h"
#include "win32/win_local.h"

extern "C" {
void *malloc(size_t size);
void free(void *ptr);
}

#define CRITSECT_SYS_EVENT_QUEUE ((CriticalSection)0x11)  // PS4 PDB enum CriticalSection

// Globals (PS4 MAP: win_main.obj)
extern sysEvent_t eventQue[MAX_QUED_EVENTS];
extern int eventHead;  // the next slot to fill
extern int eventTail;  // the next slot to take; eventHead - eventTail events are queued

bool R_CheckLostDevice();  // gfx_d3d/r_init.cpp

// Store 14054E400 (PS4 PDB Sys_QueEvent, win32/win_main.cpp:973). A full queue drops its oldest event. A time of 0
// means now.
void Sys_QueEvent(int time, sysEventType_t type, int value, int value2, int ptrLength, void *ptr)
{
	Sys_EnterCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
	sysEvent_t *ev = &eventQue[eventHead & MASK_QUED_EVENTS];
	if (eventHead - eventTail >= MAX_QUED_EVENTS)
	{
		// overflow: the slot is the oldest event's (no message, unlike Quake 3)
		if (ev->evPtr)
			free(ev->evPtr);  // Com_FreeEvent, inlined (the PS4 server's is Z_FreeInternal)
		eventTail++;
	}
	eventHead++;
	if (time == 0)
		time = Sys_Milliseconds();
	ev->evTime = time;
	ev->evType = type;
	ev->evValue = value;
	ev->evValue2 = value2;
	ev->evPtrLength = ptrLength;
	ev->evPtr = ptr;
	Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
}

// Store 14054E860 (PS4 PDB Sys_ShutdownEvents, win32/win_main.cpp:1018): drops every queued event
void Sys_ShutdownEvents()
{
	Sys_EnterCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
	while (eventTail < eventHead)
	{
		sysEvent_t *ev = &eventQue[eventTail & MASK_QUED_EVENTS];
		eventTail++;
		if (ev->evPtr)
			free(ev->evPtr);
	}
	Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
}

// Store 14054E280 (PS4 PDB Sys_LoadingKeepAlive, win32/win_main.cpp:1048): pumps every pending window message while
// the main thread waits (loading, R_SyncGpu's and the other worker-command waits, Sys_FrontEndSleep). The window
// procedure queues the input it gets, so key events wait for the next Com_EventLoop; but whatever else it does (the
// WM_USER present, Key_ClearStates on a focus change) happens here. The Store build also records the message time,
// which the PS4 server doesn't.
void Sys_LoadingKeepAlive()
{
	MSG msg;

	Sys_EnterCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
	while (PeekMessageA(&msg, nullptr, 0, 0, PM_NOREMOVE))
	{
		if (!GetMessageA(&msg, nullptr, 0, 0))
			Com_Quit_f();
		g_wv.sysMsgTime = msg.time;
		TranslateMessage(&msg);
		DispatchMessageA(&msg);
	}
	Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
	R_CheckLostDevice();
}

// Store 14054DB80 (PS4 PDB Sys_GetEvent, win32/win_main.cpp:1096; Black Ops splits it into Win_GetEvent): the next
// queued event, or SE_NONE stamped with the current time. The window messages are pumped only when the queue is
// empty, then a line from the dedicated console window becomes an SE_CONSOLE event.
sysEvent_t Sys_GetEvent()
{
	Sys_EnterCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
	if (eventHead > eventTail)
	{
		const sysEvent_t ev = eventQue[eventTail++ & MASK_QUED_EVENTS];
		Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
		return ev;
	}

	MSG msg;
	while (PeekMessageA(&msg, nullptr, 0, 0, PM_NOREMOVE))
	{
		if (!GetMessageA(&msg, nullptr, 0, 0))
			Com_Quit_f();
		g_wv.sysMsgTime = msg.time;
		TranslateMessage(&msg);
		DispatchMessageA(&msg);
	}

	const char *s = Sys_ConsoleInput();
	if (s)
	{
		int len = 0;  // strlen, inlined
		while (s[len])
			len++;
		char *b = (char *)Com_AllocEvent(len + 1);
		// destsize len, not len + 1: the copy drops the line's last character (the PS4 server's is the same)
		I_strncpyz(b, s, len);
		Sys_QueEvent(0, SE_CONSOLE, 0, 0, len + 1, b);
	}

	if (eventHead > eventTail)
	{
		const sysEvent_t ev = eventQue[eventTail++ & MASK_QUED_EVENTS];
		Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
		return ev;
	}

	sysEvent_t ev;
	memset(&ev, 0, sizeof(ev));
	ev.evTime = Sys_Milliseconds();
	Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
	return ev;
}
