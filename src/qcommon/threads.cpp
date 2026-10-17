// qcommon/threads.cpp (Store build): the main thread, the render thread and the events between them.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names come from
// the PS4 server PDB (iw6_ds_ps4, which keeps the front end's half of this file), else from Black Ops' threads.cpp
// (lineage), else sub_<VA>. The file statics have the PS4 server's layout (renderPausedEvent .. smpData), 0x10 lower.
//
// The hand-off (docs/frame.md): the front end fills a GfxBackEndData and gives it to the render thread with
// Sys_WakeRenderer (smpData, g_renderWaitCount + 1, both backend events). The render thread takes it with
// Sys_RendererSleep and reports it done with Sys_RenderCompleted (g_renderWaitCount - 1, backendEvent[0]) before it
// presents. Ownership of the device goes back and forth with noThreadOwnershipEvent: the main thread takes it with
// Sys_FrontEndSleep (the render thread pauses, renderPausedEvent) and gives it back with Sys_ReleaseThreadOwnership.

#include <windows.h>

#include <iw6_static.h>

#include "qcommon/threads.h"

#define IW6_SOURCE "qcommon/threads.cpp"

extern "C" {
unsigned long WaitForSingleObject(void *handle, unsigned long milliseconds);
unsigned long GetCurrentThreadId(void);
int SetEvent(void *event);
int ResetEvent(void *event);
long _InterlockedIncrement(long volatile *addend);
long _InterlockedDecrement(long volatile *addend);
void *_InterlockedExchangePointer(void *volatile *target, void *value);
}

// File statics (PS4 PDB names)
IW6_STATIC void *renderPausedEvent IW6_AT("", "renderPausedEvent");          // the render thread waits for the main thread
IW6_STATIC void *noThreadOwnershipEvent IW6_AT("", "noThreadOwnershipEvent");  // set: the main thread doesn't own the device
IW6_STATIC void *rendererRunningEvent IW6_AT("", "rendererRunningEvent");    // set: the render thread isn't paused
IW6_STATIC void *backendEvent[2] IW6_AT("", "backendEvent");                 // [0] worker commands / frame done, [1] wake the render thread
IW6_STATIC void *volatile smpData IW6_AT("", "smpData");                     // the GfxBackEndData handed to the render thread
IW6_STATIC volatile long g_renderWaitCount IW6_AT("", "g_renderWaitCount");  // frames handed over and not yet completed
IW6_STATIC volatile int databaseCompletedEvent2 IW6_AT("", "databaseCompletedEvent2");

extern unsigned long threadId[];  // THREAD_CONTEXT_*: [0] the main thread, [1] the render thread

// Store 14046F550 (PS4 PDB Sys_IsMainThread, qcommon/threads.cpp:2959)
bool Sys_IsMainThread()
{
	return GetCurrentThreadId() == threadId[0];
}

// Store 14046F5A0 (PS4 PDB Sys_IsRenderThread, qcommon/threads.cpp:2931)
bool Sys_IsRenderThread()
{
	return GetCurrentThreadId() == threadId[1];
}

// Store 14046F350 (PS4 PDB Sys_FrontEndSleep, qcommon/threads.cpp:2075): the main thread takes the device from the
// render thread. Waits until the render thread runs, takes ownership, wakes the render thread so it sees that, and
// waits until it has paused, pumping the window messages meanwhile.
void Sys_FrontEndSleep()
{
	WaitForSingleObject(rendererRunningEvent, 0xFFFFFFFF);
	ResetEvent(noThreadOwnershipEvent);
	SetEvent(backendEvent[1]);
	while (WaitForSingleObject(renderPausedEvent, 1))
		Sys_LoadingKeepAlive();
}

// Store 14046F5C0 (name unknown; not in the PS4 server): the render thread has fewer than two frames to finish, so the
// front end may start another (R_SyncGpu's and R_ToggleSmpFrame's wait condition)
int sub_14046F5C0()
{
	return g_renderWaitCount <= 1;
}

// Store 14046F5D0 (PS4 PDB Sys_IsRendererReady, qcommon/threads.cpp:2108): the render thread took the last frame
int Sys_IsRendererReady()
{
	return smpData == nullptr;
}

// Store 14046F510 (PS4 PDB Sys_IsDatabaseReady2, qcommon/threads.cpp:2838)
int Sys_IsDatabaseReady2()
{
	return databaseCompletedEvent2;
}

// Store 14046F610 (PS4 PDB Sys_NotifyRenderer, qcommon/threads.cpp:2163)
void Sys_NotifyRenderer()
{
	SetEvent(backendEvent[1]);
}

// Store 14046F620 (PS4 PDB Sys_ReleaseThreadOwnership, qcommon/threads.cpp:3379)
void Sys_ReleaseThreadOwnership()
{
	SetEvent(noThreadOwnershipEvent);
}

// Store 14046F630 (Black Ops' Sys_RenderCompleted, qcommon/threads.cpp:1508): the render thread finished a frame's
// commands (it presents after this)
void Sys_RenderCompleted()
{
	SetEvent(backendEvent[0]);
	_InterlockedDecrement(&g_renderWaitCount);
}

// Store 14046F650 (Black Ops' Sys_RendererSleep, qcommon/threads.cpp:1486): the render thread takes the frame
void *Sys_RendererSleep()
{
	return _InterlockedExchangePointer((void *volatile *)&smpData, nullptr);
}

// Store 14046F320 (name unknown): the main thread owns the device (noThreadOwnershipEvent is not set)
int sub_14046F320()
{
	return WaitForSingleObject(noThreadOwnershipEvent, 0) != 0;
}

// Store 14046F570 (name unknown): the main thread has given the device back
int sub_14046F570()
{
	return WaitForSingleObject(noThreadOwnershipEvent, 0) == 0;
}

// Store 14046FB70 (name unknown): the render thread runs again
void sub_14046FB70()
{
	SetEvent(rendererRunningEvent);
}

// Store 14046FB80 (name unknown): the render thread pauses for the main thread (which waits for this in
// Sys_FrontEndSleep)
void sub_14046FB80()
{
	ResetEvent(rendererRunningEvent);
	SetEvent(renderPausedEvent);
}

// Store 14046FFD0 (name unknown): the render thread waits until the main thread gives the device back
void sub_14046FFD0()
{
	WaitForSingleObject(noThreadOwnershipEvent, 0xFFFFFFFF);
}

// Store 140470200 (PS4 PDB Sys_WakeRenderer, qcommon/threads.cpp:2132): hands a frame to the render thread
void Sys_WakeRenderer(void *data)
{
	_InterlockedIncrement(&g_renderWaitCount);
	smpData = data;
	SetEvent(backendEvent[1]);
	SetEvent(backendEvent[0]);
}
