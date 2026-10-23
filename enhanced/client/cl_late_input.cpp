// enhanced/client/cl_late_input.cpp: keys and mouse buttons applied after the frame wait (records/patches.tsv P0009).
//
// The original applies key and mouse-button events in Com_EventLoop at the top of Com_Frame, before SV_Frame, the
// com_maxfps sleep, R_SyncGpu's back-end wait and (enhanced, P0004) the frame-latency wait, while the mouse is read
// right after them. The enhanced R_SyncGpu calls CL_DispatchLateInput at its end: it pumps the window messages once
// more and hands the events that arrived since to CL_KeyEvent/CL_CharEvent exactly as Com_EventLoop would, so a key
// pressed during the waits reaches this frame's command like the mouse does.
//
// Only events that are safe in the middle of a client frame are taken (docs/input.md, "Dispatching keys after the
// frame wait"): in game with no key catcher, keys whose binding only changes input state. The first event that isn't
// stops the drain, and it and everything after it stay queued for the next Com_EventLoop, in order: nothing is ever
// skipped or reordered.

#include "cgame_mp/cg_local_mp.h"
#include "client/client.h"
#include "qcommon/qcommon.h"
#include "win32/win_local.h"

#define CRITSECT_SYS_EVENT_QUEUE ((CriticalSection)0x11)
#define BIND_LAST_HELD 0x54  // bindings up to here come in +/- pairs (odd +, even -); src/client/cl_keys.cpp

extern sysEvent_t eventQue[MAX_QUED_EVENTS];  // win32/win_main.cpp
extern int eventHead;
extern int eventTail;
void CL_KeyEvent(LocalClientNum_t localClientNum, int key, int down, unsigned int time);  // client/cl_keys.cpp
void CL_CharEvent(LocalClientNum_t localClientNum, int key);
void Sys_LoadingKeepAlive();  // win32/win_main.cpp

static bool s_dispatchingLateInput;

// A binding whose handler only changes client input state (kbuttons, stance, ADS, the reliable "n <binding>" command).
// Not: the +frag/+smoke presses (5, 7: cgame offhand state), the action slots (0xF-0x1C: cgame weapon and killstreak
// selection), togglemenu, weapnext, pause, chatmode, weapprev (0x55-0x5A: LUI menus and popups, cgame weapon cycling).
static bool CL_IsLateSafeBinding(int binding)
{
	if (binding == 5 || binding == 7)
		return false;
	if (binding >= 0xF && binding <= 0x1C)
		return false;
	if (binding >= 0x55 && binding <= 0x5A)
		return false;
	return true;
}

// In game, with nothing else holding the keys: no console, menu, LUI menu, chat line or location selection
static bool CL_CanDispatchLateInput()
{
	const clientUIActive_t *ui = &clientUIActives[0];
	if (ui->keyCatchers != 0 || ui->connectionState != CA_ACTIVE)
		return false;
	if (Com_ErrorEntering())
		return false;
	return *(void *const *)((const char *)&cgArray[0] + 0x3390) != nullptr;  // the cgame is up (CL_ExecBinding's test)
}

// Whether CL_KeyEvent/CL_CharEvent can run this event now (in game, no key catcher)
static bool CL_IsLateSafeEvent(const sysEvent_t *ev)
{
	if (ev->evType == SE_CHAR)
		return true;  // nothing takes characters in game; taken only to keep the order
	if (ev->evType != SE_KEY)
		return false;  // console text: the command buffer, at the next Com_EventLoop
	const int key = ev->evValue;
	if (key < 0 || key >= 256)
		return false;
	if (key == K_ESCAPE)
		return false;  // a press opens the in-game menu at once; a release follows its press, which stays queued
	const PlayerKeyState *keyState = &playerKeys[0];
	if (key == K_F4 && keyState->keys[K_ALT].down)
		return false;  // Alt+F4 quits
	const KeyState *keys = &keyState->keys[key];
	if (ev->evValue2)
	{
		if (keys->repeats > 0)
			return true;  // an auto-repeat: CL_KeyEvent stops after counting it
		return CL_IsLateSafeBinding(keys->binding);
	}
	// a release runs the "-" half of a held binding
	if (keys->binding <= BIND_LAST_HELD && (keys->binding & 1))
		return CL_IsLateSafeBinding(keys->binding + 1);
	return true;
}

// Called at the end of the enhanced R_SyncGpu (enhanced/gfx_d3d/r_init.cpp), after every wait of the frame. The pump
// is the one R_SyncGpu's own waits already run (Sys_LoadingKeepAlive, unfiltered), so it adds no new message handling
// at this point of the frame; it only queues input. The state is tested again before each event, since a handler may
// change it.
void CL_DispatchLateInput()
{
	if (s_dispatchingLateInput || !CL_CanDispatchLateInput())
		return;
	s_dispatchingLateInput = true;
	Sys_LoadingKeepAlive();
	while (CL_CanDispatchLateInput())
	{
		Sys_EnterCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
		if (eventHead <= eventTail || !CL_IsLateSafeEvent(&eventQue[eventTail & MASK_QUED_EVENTS]))
		{
			Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
			break;
		}
		const sysEvent_t ev = eventQue[eventTail++ & MASK_QUED_EVENTS];
		Sys_LeaveCriticalSection(CRITSECT_SYS_EVENT_QUEUE);
		if (ev.evType == SE_KEY)
			CL_KeyEvent(LOCAL_CLIENT_0, ev.evValue, ev.evValue2, ev.evTime);
		else
			CL_CharEvent(LOCAL_CLIENT_0, ev.evValue);
	}
	s_dispatchingLateInput = false;
}
