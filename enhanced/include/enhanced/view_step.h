// enhanced/include/enhanced/view_step.h: usercmds on a fixed 5 ms grid and the view at the render time
// (docs/fps.md 6.2, 6.3 and 7.6). Shared by enhanced/client_mp/cl_fixed_cmds.cpp and enhanced/cgame_mp/cg_view_step.cpp.
#pragma once

#include "client_mp/client_mp.h"

#define CMD_STEP_MSEC 5          // every usercmd is 5 ms long
#define CMD_MAX_PER_FRAME 20     // at most 100 ms of commands in one frame
#define CMD_REANCHOR_MSEC 500    // a jump of the client's time beyond this restarts the grid

// The command a command at cl->serverTime would be: the newest stored command's buttons and moves with this frame's
// view angles (clViewangles + cgameKickAngles, rounded as CL_FinishMove does) and serverTime = cl->serverTime. Built
// every frame by CL_CreateNewCommands, never stored or sent; CG_PredictPlayerState uses it for the view's partial step.
extern usercmd_s cl_viewCmd;
extern int cl_viewCmdValid;

// 1: the view is drawn at the render time (the partial step of 7.6); 0: the canonical prediction is drawn, as in the
// original. Tests switch it off to get the reference run.
extern int cg_renderTimeView;

// Puts the canonical predicted state back if the view's fields are swapped in; a no-op otherwise.
void CG_RestoreCanonicalView();

// Explicit copies: the build uses -fno-builtin, and memcpy is a CRT import the test harness only stubs. Eight bytes at
// a time, then the rest (the copies are of whole structures that don't overlap).
static inline void Enh_Copy(void *dst, const void *src, unsigned long long size)
{
	unsigned char *d = (unsigned char *)dst;
	const unsigned char *s = (const unsigned char *)src;
	unsigned long long i = 0;
	for (; i + 8 <= size; i += 8)
	{
		unsigned long long q;
		__builtin_memcpy(&q, s + i, 8);
		__builtin_memcpy(d + i, &q, 8);
	}
	for (; i < size; ++i)
		d[i] = s[i];
}
