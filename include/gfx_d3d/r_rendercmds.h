// gfx_d3d/r_rendercmds.h: handing a frame's render commands from the front end (main thread) to the back end (the
// render thread). Types from the PS4 server PDB (iw6_ds_ps4) with the Store build's layout.
#pragma once

// GfxGlobals r_glob (PS4 PDB, gfx_d3d/r_init.cpp). The Store build has two more ints after startedRenderThread, so
// everything from isRenderingRemoteUpdate on is 0xC further than in the server; checked against every access.
struct GfxGlobals
{
	bool mainThreadHasOwnership;         // the main thread owns the device; the render thread waits (Sys_FrontEndSleep)
	bool startedRenderThread;
	int unknown04;                       // Store: lowered while the main thread runs the back end itself
	int unknown08;                       // Store: 1 while the main thread runs the back end itself
	bool isRenderingRemoteUpdate;        // the render thread is drawing the loading screen (SCR_UpdateScreen)
	volatile int screenUpdateNotify;
	volatile int remoteScreenUpdateNesting;
	int backEndFrameCount;
	unsigned char unknown1C[0x38 - 0x1C];  // the server's freezeDrawData, freezeDrawLock, skeleton time stamps
};
static_assert(__builtin_offsetof(GfxGlobals, isRenderingRemoteUpdate) == 0xC, "GfxGlobals (Store)");
static_assert(__builtin_offsetof(GfxGlobals, remoteScreenUpdateNesting) == 0x14, "GfxGlobals (Store)");
static_assert(__builtin_offsetof(GfxGlobals, backEndFrameCount) == 0x18, "GfxGlobals (Store)");

extern GfxGlobals r_glob;  // 14A37D580

// The end of GfxBackEndData (0x645080 bytes in the Store build): how far the front end has issued the frame. Names from
// the PS4 server's GfxBackEndData (drawType at 0x1280 there), which has no field at +0x8.
struct GfxBackEndIssueState
{
	unsigned int drawType;               // R_IssueRenderCommandsBegin's argument: 1 the scene, 2 present (swap)
	int renderFromBackEnd;               // r_smp_backend && sys_smp_allowed && !isRenderingRemoteUpdate
	int unknown8;
	volatile int shadowReady;
	volatile int opaqueReady;
	volatile int emissiveReady;
	volatile int finishReady;            // the front end issued the whole frame (the 2D part too)
	volatile int abortReady;
	int endSwapFrame;                    // g_frontEndSwapFrame when the frame was registered for presenting
};
#define GFX_BACKEND_ISSUE_STATE 0x151448
struct GfxBackEndData;
inline GfxBackEndIssueState *R_IssueState(GfxBackEndData *data)
{
	return (GfxBackEndIssueState *)((char *)data + GFX_BACKEND_ISSUE_STATE);
}

extern GfxBackEndData *frontEndDataOut;  // the frame the front end fills (one of s_backEndData[2])

// gfx_d3d/r_rendercmds.cpp
void R_SyncRenderThread();
void R_ReleaseThreadOwnership();
int R_IsInRemoteScreenUpdate();
void R_PushRemoteScreenUpdate(int remoteScreenUpdateNesting);
int R_PopRemoteScreenUpdate();
void R_PreAbortRenderCommands();
void R_IssueRenderCommandsBegin(unsigned int type);
void R_IssueRenderCommandsShadow();
void R_IssueRenderCommandsOpaque();
void R_IssueRenderCommandsEmissive();
void sub_14064D030();

// gfx_d3d/r_workercmds.cpp: runs worker commands until isDone() returns non-zero
void R_ProcessWorkerCmdsWithTimeout(int (*isDone)(), int timeout);

// Store: the device critical section (CRITSECT 0x2B, one more than the server has) the thread that draws holds
void sub_1406791E0();  // leaves it (the main thread gives the device to the render thread)
void sub_140676A10();  // enters it
