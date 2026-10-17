// gfx_d3d/r_rendercmds.cpp (Store build): handing a frame's render commands from the front end to the back end.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names and line
// numbers come from the PS4 server PDB (iw6_ds_ps4), which keeps this half of the file; sub_<VA> where the server has
// no counterpart. The Store build adds a device critical section (sub_1406791E0 leaves it, sub_140676A10 enters it)
// to every change of ownership.
//
// Two GfxBackEndData buffers alternate (R_ToggleSmpFrame, 14064D880): the front end fills frontEndDataOut while the
// render thread draws the other one. A frame is issued in steps (docs/frame.md):
// - R_IssueRenderCommandsBegin(drawType) once the scene's draw lists are being built: registers a frame that will be
//   presented (R_RegisterRenderFrame) and, with the render thread in use, hands the buffer over at once
//   (Sys_WakeRenderer), so the back end starts while the front end is still adding to it;
// - R_IssueRenderCommandsShadow, ..Opaque, ..Emissive as each part of the scene is ready;
// - sub_14064D030 at the end of the frame (after the 2D): marks it finished, hands it over if that didn't happen yet,
//   and without the render thread runs the back end (and the present) on the main thread.
// The main thread owns the device while it runs the back end itself or recovers a lost device; R_SyncRenderThread
// takes it from the render thread and R_ReleaseThreadOwnership gives it back.

#include <iw6_static.h>

#include <string.h>

#include "gfx_d3d/r_buffers.h"
#include "gfx_d3d/r_dx.h"
#include "gfx_d3d/r_rendercmds.h"
#include "qcommon/dvar.h"
#include "qcommon/threads.h"

#define IW6_SOURCE "gfx_d3d/r_rendercmds.cpp"

IW6_STATIC int g_databaseReady2 IW6_AT("", "g_databaseReady2");
IW6_STATIC unsigned int s_smpFrame IW6_AT("", "s_smpFrame");        // which of s_backEndData the front end fills
IW6_STATIC unsigned int g_frameIndex IW6_AT("", "g_frameIndex");    // flipped by R_EndFrame
IW6_STATIC void *s_cmdList IW6_AT("", "s_cmdList");                 // the front end's command list
IW6_STATIC unsigned char s_backEndData[2 * 0x645080] IW6_AT("", "s_backEndData");  // GfxBackEndData[2]

extern const dvar_t *r_smp_backend;           // gfx_d3d/r_dvars.cpp
extern const dvar_t *sys_smp_allowed;         // qcommon/common.cpp
extern const dvar_t *r_SkinnedCacheSize;      // gfx_d3d/r_dvars.cpp
extern const dvar_t *r_SkinnedCacheThreshold; // gfx_d3d/r_dvars.cpp
extern volatile unsigned int g_mainThreadBlocked;  // win32: counted while the main thread waits for the loading screen
extern int unk_14A37D504;  // the skinned cache is past r_SkinnedCacheThreshold (SCR_UpdateScreen warns; name unknown)

bool R_CheckLostDevice();
void R_RegisterRenderFrame();
void R_UnlockSkinnedCache();
void sub_14066C920();                         // restarts the worker threads whose r_smp_worker_thread changed
void sub_1406700E0(GfxBackEndData *data);     // the back end: the frame's start (rb_backend)
void sub_140670A10();                         // the back end: executes the command lists
void sub_140670450();                         // the back end: the frame's end
void sub_140673B60(unsigned int drawType);    // the back end: presents when drawType has 2

// R_ToggleSmpFrame
extern const dvar_t *r_asyncCompute;          // gfx_d3d/r_dvars.cpp
extern const dvar_t *r_useComputeSkinning;    // gfx_d3d/r_dvars.cpp
extern const dvar_t *r_subdiv;                // gfx_d3d/r_dvars.cpp
extern int unk_14A37D4E0[4];                  // copied into each new frame (name unknown)
extern int unk_14A2C76D0;                     // cleared each frame (name unknown)
extern unsigned char unk_14B038300[];         // per g_frameIndex, 0x1F0E0 bytes each (name unknown)
extern unsigned char unk_14B0764C0[];         // the command lists, per g_frameIndex, 0x20 bytes each (name unknown)
// the flare surface lists (GfxFlareSurfList unk_14B076500[2], 0x4858 bytes each; gfx_d3d/r_init.cpp), as bytes here
extern unsigned char unk_14B076500[] __asm__("?unk_14B076500@@3PAUGfxFlareSurfList@@A");
void sub_14063F270();
void sub_1401B28E0();
void sub_1401B3720();
void sub_1401B14D0();
void sub_14063D540();
void sub_14063D210(void *list);               // resets one of the frame's lists
void sub_1401AC1B0(void *pending);

// Store 14064D840 (PS4 PDB R_SyncRenderThread, gfx_d3d/r_rendercmds.cpp:984): the main thread takes the device from
// the render thread (waiting until it has paused)
void R_SyncRenderThread()
{
	if (!Sys_IsRenderThread() && r_glob.startedRenderThread && !r_glob.mainThreadHasOwnership)
	{
		Sys_FrontEndSleep();
		r_glob.mainThreadHasOwnership = true;
		sub_140676A10();
	}
}

// Store 14064D420 (PS4 PDB R_ReleaseThreadOwnership, gfx_d3d/r_rendercmds.cpp:1127): gives the device back to the
// render thread
void R_ReleaseThreadOwnership()
{
	if (r_glob.startedRenderThread && r_glob.mainThreadHasOwnership)
	{
		sub_1406791E0();
		Sys_ReleaseThreadOwnership();
		r_glob.mainThreadHasOwnership = false;
	}
}

// Store 14064D880 (Black Ops' R_ToggleSmpFrame, gfx_d3d/r_rendercmds.cpp:1433): starts filling the other of the two
// GfxBackEndData buffers. Gives the device back, waits (running worker commands) until the render thread has at most
// one frame left, flips s_smpFrame and the skinned cache and reactive motion pools, points frontEndDataOut at
// s_backEndData[s_smpFrame] and resets its lists and the issue state. Called once a frame: in CG_DrawActiveFrame
// between CL_SyncGpu and CL_Input, or in SCR_UpdateFrame before R_IssueRenderCommandsBegin.
#define FRONT(offset, type) (*(type *)((char *)frontEndDataOut + (offset)))
void R_ToggleSmpFrame()
{
	if (Sys_IsMainThread())
		R_ReleaseThreadOwnership();
	R_ProcessWorkerCmdsWithTimeout(sub_14046F5C0, 1);

	const int skinnedCacheFrame = gfxBuf.skinnedCacheVbPoolFrame;
	s_smpFrame = (s_smpFrame - 1) & 1;
	gfxBuf.skinnedCacheVbPoolFrame = (skinnedCacheFrame + 1) % 3;
	gfxBuf.reactiveMotionCbPoolFrame = (gfxBuf.reactiveMotionCbPoolFrame + 1) % 2;
	const unsigned int frameIndex = g_frameIndex;
	frontEndDataOut = (GfxBackEndData *)(s_backEndData + 0x645080ull * s_smpFrame);
	FRONT(0x150CEC, int) = unk_14A37D4E0[0];
	FRONT(0x150CE8, int) = 0;
	FRONT(0x150CF0, int) = unk_14A37D4E0[1];
	FRONT(0x150CFC, int) = unk_14A37D4E0[2];
	FRONT(0x150D00, int) = unk_14A37D4E0[3];
	FRONT(0x150D08, void *) = unk_14B038300 + 0x1F0E0ull * frameIndex;
	FRONT(0x150CE0, void *) = unk_14B0764C0 + 0x20ull * frameIndex;
	if (!unk_14A37D4E0[0])
		sub_14063F270();
	FRONT(0x150C38, GfxVertexBufferState *) = &gfxBuf.skinnedCacheVbPool[skinnedCacheFrame];
	FRONT(0x150C40, GfxVertexBufferState *) = &gfxBuf.skinnedCacheVbPool[gfxBuf.skinnedCacheVbPoolFrame];
	FRONT(0x150C80, GfxReactiveMotionBufferState *) = &gfxBuf.reactiveMotionCbPool[gfxBuf.reactiveMotionCbPoolFrame];
	FRONT(0x150C88, int) = 0;
	sub_1401B28E0();
	sub_1401B3720();
	sub_1401B14D0();
	FRONT(0x150AC0, int) = 0;
	++gfxBuf.skinnedCacheFrameCount;
	unk_14A2C76D0 = 0;
	const bool asyncCompute = r_asyncCompute->current.enabled;
	FRONT(0x150C68, bool) = asyncCompute;
	FRONT(0x150C69, bool) = r_useComputeSkinning->current.enabled || (r_subdiv->current.enabled && asyncCompute);
	sub_14063D540();
	FRONT(0x150C40, GfxVertexBufferState *)->used = 0;
	s_cmdList = FRONT(0x150CE0, void *);
	FRONT(0x150AEC, int) = 0;
	FRONT(0x150AF0, int) = 0;
	FRONT(0x150AF4, int) = 0;
	FRONT(0x150BF8, int) = 0;
	FRONT(0x150BFC, int) = 0;
	FRONT(0x150C04, int) = 1;
	FRONT(0x150C20, int) = 0;
	FRONT(0x150C00, int) = 0;
	FRONT(0x150C08, int) = 0;
	FRONT(0x150C14, int) = 0;
	sub_14063D210((char *)frontEndDataOut + 0x1508E0);
	FRONT(0x150C0C, int) = 0;
	FRONT(0x150C18, int) = 0;
	sub_14063D210((char *)frontEndDataOut + 0x150930);
	FRONT(0x150C10, int) = 0;
	FRONT(0x150C1C, int) = 0;
	sub_14063D210((char *)frontEndDataOut + 0x150980);
	FRONT(0x150C24, int) = 0;
	sub_14063D210((char *)frontEndDataOut + 0x1509D0);
	FRONT(0x150C28, int) = 0;
	sub_14063D210((char *)frontEndDataOut + 0x150A20);
	FRONT(0x150C2C, int) = 0;
	sub_14063D210((char *)frontEndDataOut + 0x150A70);
	FRONT(0x150C30, bool) = false;
	FRONT(0x150C8C, int) = 0;
	FRONT(0x150D10, void *) = nullptr;
	if (FRONT(0x150C50, void *))
	{
		sub_1401AC1B0((char *)frontEndDataOut + 0x150C50);
		FRONT(0x150C48, void *) = (char *)frontEndDataOut + 0x150C50;
	}
	else
	{
		FRONT(0x150C48, void *) = nullptr;
	}
	memset((char *)frontEndDataOut + 0x150D28, 0, 0x104);
	FRONT(0x150CF4, int) = 0;
	FRONT(0x150D04, int) = 0;
	R_IssueState(frontEndDataOut)->unknown8 = 0;
	R_IssueState(frontEndDataOut)->shadowReady = 0;
	R_IssueState(frontEndDataOut)->opaqueReady = 0;
	R_IssueState(frontEndDataOut)->emissiveReady = 0;
	R_IssueState(frontEndDataOut)->finishReady = 0;
	R_IssueState(frontEndDataOut)->abortReady = 0;
	FRONT(0x1F26A0, void *) = unk_14B076500 + 0x4858ull * g_frameIndex;
}
#undef FRONT

// Store 14064CF70 (PS4 PDB R_IssueRenderCommandsBegin, gfx_d3d/r_rendercmds.cpp:1233)
void R_IssueRenderCommandsBegin(unsigned int type)
{
	int renderFromBackEnd = 0;
	if (r_smp_backend->current.enabled && sys_smp_allowed->current.enabled)
		renderFromBackEnd = !r_glob.isRenderingRemoteUpdate;
	R_IssueState(frontEndDataOut)->renderFromBackEnd = renderFromBackEnd;
	R_IssueState(frontEndDataOut)->drawType = type;
	if (dx.deviceLost)
		return;
	if (type & 2)
		R_RegisterRenderFrame();
	if (R_IssueState(frontEndDataOut)->renderFromBackEnd)
	{
		g_databaseReady2 = Sys_IsDatabaseReady2();
		if (g_databaseReady2)
		{
			R_ProcessWorkerCmdsWithTimeout(Sys_IsRendererReady, 1);
			Sys_WakeRenderer(frontEndDataOut);
		}
	}
}

// Store 14064D200 (PS4 PDB R_IssueRenderCommandsShadow, gfx_d3d/r_rendercmds.cpp:1271)
void R_IssueRenderCommandsShadow()
{
	R_IssueState(frontEndDataOut)->shadowReady = 1;
}

// Store 14064D1E0 (PS4 PDB R_IssueRenderCommandsOpaque, gfx_d3d/r_rendercmds.cpp:1280)
void R_IssueRenderCommandsOpaque()
{
	R_IssueState(frontEndDataOut)->opaqueReady = 1;
}

// Store 14064D010 (PS4 PDB R_IssueRenderCommandsEmissive, gfx_d3d/r_rendercmds.cpp:1289)
void R_IssueRenderCommandsEmissive()
{
	R_IssueState(frontEndDataOut)->emissiveReady = 1;
}

// Store 14064D030 (name unknown; not in the server, which has no back end): the end of a frame. Marks it finished
// (finishReady), hands it to the render thread if R_IssueRenderCommandsBegin couldn't (the database wasn't ready),
// notes whether the skinned cache passed r_SkinnedCacheThreshold, and closes frontEndDataOut. With the render thread
// the main thread gives the device back; without it, the main thread takes the device and runs the back end itself,
// presenting the frame.
void sub_14064D030()
{
	const int renderFromBackEnd = R_IssueState(frontEndDataOut)->renderFromBackEnd;
	R_IssueState(frontEndDataOut)->finishReady = 1;
	if (renderFromBackEnd && !g_databaseReady2)
	{
		R_ProcessWorkerCmdsWithTimeout(Sys_IsRendererReady, 1);
		Sys_WakeRenderer(frontEndDataOut);
	}
	if (Sys_IsMainThread())
		sub_14066C920();
	const float threshold = (float)r_SkinnedCacheSize->current.integer * r_SkinnedCacheThreshold->current.value;
	const unsigned int used = **(unsigned int **)((char *)frontEndDataOut + 0x150C40);
	unk_14A37D504 = used >= ((unsigned long long)(unsigned int)(long long)threshold << 5);
	R_UnlockSkinnedCache();
	GfxBackEndData *data = frontEndDataOut;
	frontEndDataOut = nullptr;
	if (renderFromBackEnd)
	{
		R_ReleaseThreadOwnership();
		return;
	}
	if (dx.deviceLost)
		return;
	if (Sys_IsMainThread())
		R_SyncRenderThread();
	if (Sys_IsMainThread())
	{
		r_glob.unknown08 = 1;
		--r_glob.unknown04;
	}
	if (R_CheckLostDevice())
	{
		sub_1406700E0(data);
		sub_140670A10();
		sub_140670450();
		sub_140673B60(R_IssueState(data)->drawType);
	}
	if (Sys_IsMainThread())
	{
		r_glob.unknown08 = 0;
		++r_glob.unknown04;
	}
}

// Store 14064D320 (PS4 PDB R_PreAbortRenderCommands, gfx_d3d/r_rendercmds.cpp:1417)
void R_PreAbortRenderCommands()
{
	if (frontEndDataOut)
		R_IssueState(frontEndDataOut)->abortReady = 1;
}

// Store 14064CF60 (PS4 PDB R_IsInRemoteScreenUpdate, gfx_d3d/r_rendercmds.cpp:4114)
int R_IsInRemoteScreenUpdate()
{
	return r_glob.remoteScreenUpdateNesting != 0;
}

// Store 14064D340 (PS4 PDB R_PushRemoteScreenUpdate, gfx_d3d/r_rendercmds.cpp:4081): the render thread draws the
// loading screen (SCR_UpdateScreen) while the main thread loads
void R_PushRemoteScreenUpdate(int remoteScreenUpdateNesting)
{
	for (; remoteScreenUpdateNesting; --remoteScreenUpdateNesting)
	{
		if (!Sys_IsMainThread() || !r_glob.startedRenderThread)
			continue;
		if (r_glob.remoteScreenUpdateNesting)
		{
			++r_glob.remoteScreenUpdateNesting;
			continue;
		}
		++r_glob.remoteScreenUpdateNesting;
		R_ReleaseThreadOwnership();
		Sys_NotifyRenderer();
	}
}

// Store 14064D220 (PS4 PDB R_PopRemoteScreenUpdate, gfx_d3d/r_rendercmds.cpp:4095): ends the render thread's loading
// screen, waiting until it has drawn the last one, and returns the nesting to restore later
int R_PopRemoteScreenUpdate()
{
	const int remoteScreenUpdateNesting = r_glob.remoteScreenUpdateNesting;
	while (r_glob.remoteScreenUpdateNesting)
	{
		if (!Sys_IsMainThread() || !r_glob.startedRenderThread)
			continue;
		if (r_glob.remoteScreenUpdateNesting != 1)
		{
			--r_glob.remoteScreenUpdateNesting;
			continue;
		}
		while (!r_glob.screenUpdateNotify)
		{
			Sys_CheckQuitRequest();
			Sys_Sleep(1);
		}
		r_glob.screenUpdateNotify = 0;
		--r_glob.remoteScreenUpdateNesting;
		while (!r_glob.screenUpdateNotify)
		{
			++g_mainThreadBlocked;
			Sys_LoadingKeepAlive();
			Sys_CheckQuitRequest();
			Sys_Sleep(1);
			--g_mainThreadBlocked;
		}
		r_glob.screenUpdateNotify = 0;
	}
	return remoteScreenUpdateNesting;
}
