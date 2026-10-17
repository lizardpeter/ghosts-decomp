// qcommon/threads.h: the threads and the events between the main thread (the front end) and the render thread (the
// back end). Names and prototypes from the PS4 server PDB (iw6_ds_ps4, qcommon/threads.cpp), else from Black Ops'
// threads.cpp (lineage), else sub_<Store VA>.
#pragma once

bool Sys_IsMainThread();
bool Sys_IsRenderThread();

// The front end hands a frame to the render thread and takes the device back from it
void Sys_FrontEndSleep();
int Sys_IsRendererReady();
void Sys_WakeRenderer(void *data);
void Sys_NotifyRenderer();
void Sys_ReleaseThreadOwnership();
int Sys_IsDatabaseReady2();
int sub_14046F5C0();  // fewer than two frames handed to the render thread and not yet completed (name unknown)

// The render thread's side
void *Sys_RendererSleep();
void Sys_RenderCompleted();
int sub_14046F320();  // the main thread holds the render thread's ownership (name unknown)
int sub_14046F570();  // the main thread has released it (name unknown)
void sub_14046FB80(); // the render thread pauses for the main thread (name unknown)
void sub_14046FB70(); // the render thread runs again (name unknown)
void sub_14046FFD0(); // the render thread waits until the main thread releases it (name unknown)

void Sys_Sleep(int msec);
void Sys_LoadingKeepAlive();   // win32/win_main.cpp: pumps the window messages while the main thread waits
void Sys_CheckQuitRequest();   // win32/win_main.cpp
