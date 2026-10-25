// enhanced/include/enhanced/tick.h: the cgame's 5 ms tick loop and its presentation pass (docs/cgame-frame.md 4.2,
// 4.10). Shared by enhanced/cgame_mp/cg_tick.cpp (the loop, in the enhanced CG_DrawActiveFrame),
// enhanced/client_mp/cl_fixed_cmds.cpp (the commands), enhanced/cgame_mp/cg_view_step.cpp (prediction, the own view)
// and enhanced/bgame/bg_kick.cpp (the kick's step-forward).
#pragma once

#include "enhanced/view_step.h"

struct playerState_s;

// 1: CG_DrawActiveFrame runs the tick loop; 0: the original frame (one prediction, the kick with cg.frametime), as
// it also does while the client makes no grid commands. Tests switch it off for the faithful comparison.
extern int cg_tickLoop;

// --- client (enhanced/client_mp/cl_fixed_cmds.cpp) -------------------------------------------------------------
// The frame's input into the unfinished command; the number of due ticks (0..20), or -1: no grid commands this frame
int CL_PrepareFrameInput(LocalClientNum_t localClientNum);
// One command at the next tick time (the newest command's time + 5); returns that time
int CL_EmitTickCommand(LocalClientNum_t localClientNum);
// The newest grid command's time: the latest tick's
int CL_LastTickTime();
// How many ticks CL_PrepareFrameInput will find due this frame, and the time before the first (no state changed)
int CL_TicksDue(LocalClientNum_t localClientNum, int *prevTime);
// cl_viewCmd from the newest command, this frame's view angles plus aimAngles, at cl->serverTime
void CL_BuildViewCmd(LocalClientNum_t localClientNum, const float *aimAngles);

// --- cgame (enhanced/cgame_mp/cg_view_step.cpp) -----------------------------------------------------------------
int CG_PredictTick(LocalClientNum_t localClientNum);    // the faithful CG_PredictPlayerState; 1: the state is predicted
void CG_EarlyPredictTick();                             // the faithful sub_1402D2410 (the platform's move)
void CG_SaveTickState(LocalClientNum_t localClientNum); // the faithful CG_SavePlayerState: the tick's end
// The own view's step-forward (P0017's partial Pmove with cl_viewCmd), swapped into cg.predictedPlayerState
void CG_PresentOwnView(LocalClientNum_t localClientNum);
// Puts back every presentation copy (the own view's fields, the turret scope's FOV); a no-op when nothing is swapped in
void CG_RestorePresentation();

// --- cgame (enhanced/cgame_mp/cg_draw_mp.cpp) ---------------------------------------------------------------------
void CG_RampTick(LocalClientNum_t localClientNum, int frametime);  // sub_1402AA2A0's step with this many ms

// --- cgame (enhanced/cgame/cg_weapons.cpp) ----------------------------------------------------------------------
extern int cg_tickLoopFrame;                             // 1 while CG_DrawActiveFrame runs the tick loop
void CG_ViewWeaponTick(LocalClientNum_t localClientNum); // the viewmodel's movement half, once per tick

// --- bgame (enhanced/bgame/bg_kick.cpp) ---------------------------------------------------------------------------
// The original BG_KickAngles' step with a float msec (for a whole msec bit for bit BG_KickAngles)
void BG_KickAnglesStep(const playerState_s *ps, float msec, float kickAVel[3], float kickAngles[3]);
