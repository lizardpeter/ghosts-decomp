// enhanced/client_mp/cl_fixed_cmds.cpp: usercmds of a fixed 5 ms, independent of the frame rate (records/patches.tsv P0016; docs/fps.md 6.2).
//
// The original CL_CreateNewCommands (src/client_mp/cl_input.cpp, Store 14030BB00) makes one command per rendered
// frame, stamped cl->serverTime, so every command is as long as the frame and the movement physics, which the server
// runs on the same commands, change with the frame rate (B0056/B0057, docs/fps.md 3.4). Here commands are made on a
// grid: while lastCmdTime + 5 <= cl->serverTime, a command at lastCmdTime += 5, at most 20 a frame; the rest of the
// time carries to the next frame. The grid restarts at cl->serverTime when the client's time jumps by more than
// 500 ms either way (a map change, a long stall); a smaller step back just waits, so command times always increase.
//
// What runs when:
// - every rendered frame: the view angles (keyboard turning, the mouse, the gamepad sticks and aim assist, i.e. the
//   original's CL_AdjustAngles, CL_MouseMove and CL_GamepadMove), with the frame's own frame_msec and frametime, and
//   the 90-degree pitch limit; and the temporary view command cl_viewCmd (enhanced/include/enhanced/view_step.h);
// - only in a frame that makes commands: the buttons (CL_CmdButtons: a tap latched since the last command is not
//   lost), the movement keys (CL_KeyMove, with frame_msec set to the time since the previous command-making frame so
//   the keys' fractions cover the span the commands cover; CL_KeyState measures since its last call, which was then),
//   the cgame's command adjustment (sub_1402A9900), remote control and location selection (which take the whole
//   command), and CL_FinishMove. All of the frame's commands carry the same buttons, moves and angles;
//   cgameExtraButtons go only into the first (CL_FinishMove clears them).
// - The mode where the original replaces the user's input by a default command (unk_143E96824 not 0 or 3) is the
//   original's: one default command a frame.
//
// Known simplifications, on frames that make no command: a sprint tap seen by the gamepad path is kept for the next
// command-making frame; the mouse's movement in strafe mode or without mouse look (which the original turns into
// moves of that frame's command) and aim assist's melee target are dropped for that frame.

#include <math.h>

#include <iw6_static.h>

#include "cgame_mp/cg_local_mp.h"
#include "client/client.h"
#include "client_mp/client_mp.h"
#include "enhanced/view_step.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "client_mp/cl_input.cpp"

IW6_STATIC kbutton_t playersKb[1][NUM_BUTTONS] IW6_AT("", "playersKb");

extern int com_frameTime;                  // qcommon/common.cpp
extern int unk_143E96824;                  // client_mp: a client mode, 0..3 (name unknown)
extern const dvar_t *cl_yawspeed;
extern const dvar_t *cl_pitchspeed;
extern const dvar_t *cl_anglespeedkey;

struct DataValidation;
extern DataValidation unk_140CFC520;
void sub_14017AB80(DataValidation *validation, const void *data, int offset, int size, bool force);
void sub_14017AAE0(DataValidation *validation, const void *data, int offset, int size);

void CL_CmdButtons(LocalClientNum_t localClientNum, usercmd_s *cmd);
void CL_KeyMove(LocalClientNum_t localClientNum, usercmd_s *cmd);
void CL_MouseMove(LocalClientNum_t localClientNum, usercmd_s *cmd, float frametime_base);
void CL_GamepadMove(LocalClientNum_t localClientNum, float frametime_base, usercmd_s *cmd);
void CL_FinishMove(LocalClientNum_t localClientNum, usercmd_s *cmd);
float CL_KeyState(kbutton_t *key);
bool GPad_IsActive(int portIndex);
float sub_1404633E0(float frametime_base);
void sub_1402A9900(LocalClientNum_t localClientNum, usercmd_s *cmd);
void sub_14030DF50(LocalClientNum_t localClientNum, usercmd_s *cmd);
bool CG_HandleLocationSelectionInput(LocalClientNum_t localClientNum, usercmd_s *cmd);

#define PMF_REMOTE_CONTROL 0x80000

usercmd_s cl_viewCmd;
int cl_viewCmdValid;

struct FixedCmdGrid
{
	int lastCmdTime;       // the newest command's serverTime
	int lastCmdFrameTime;  // com_frameTime of the last frame that made commands
	int valid;
};
static FixedCmdGrid s_grid;

// src: Black Ops' CL_AdjustAngles, inlined in the Store build's CL_CreateCmd (unchanged)
static void CL_AdjustAnglesFrame(LocalClientNum_t localClientNum)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	kbutton_t *kb = playersKb[localClientNum];

	if (cl->snap.ps_pm_flags & PMF_NO_MOUSE_LOOK)
		return;

	float speed = (float)cls.frametime * 0.001f;
	if (kb[KB_SPEED].active)
		speed *= cl_anglespeedkey->current.value;

	if (!kb[KB_STRAFE].active)
	{
		float yawSpeed = cl_yawspeed->current.value;
		if (cl->cgameMaxYawSpeed > 0.0f)
			yawSpeed = yawSpeed < cl->cgameMaxYawSpeed ? yawSpeed : cl->cgameMaxYawSpeed;
		yawSpeed *= speed;
		cl->clViewangles[1] = cl->clViewangles[1] - CL_KeyState(&kb[KB_RIGHT]) * yawSpeed;
		cl->clViewangles[1] = CL_KeyState(&kb[KB_LEFT]) * yawSpeed + cl->clViewangles[1];
	}

	float pitchSpeed = cl_pitchspeed->current.value;
	if (cl->cgameMaxPitchSpeed > 0.0f)
		pitchSpeed = pitchSpeed < cl->cgameMaxPitchSpeed ? pitchSpeed : cl->cgameMaxPitchSpeed;
	pitchSpeed *= speed;
	cl->clViewangles[0] = cl->clViewangles[0] - CL_KeyState(&kb[KB_LOOKUP]) * pitchSpeed;
	cl->clViewangles[0] = CL_KeyState(&kb[KB_LOOKDOWN]) * pitchSpeed + cl->clViewangles[0];
}

static void CL_ClearCmd(LocalClientNum_t localClientNum, usercmd_s *cmd)
{
	unsigned char *p = (unsigned char *)cmd;
	for (unsigned int i = 0; i < sizeof(*cmd); ++i)
		p[i] = 0;
	cmd->meleeChargeEnt = ENTITYNUM_NONE;
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	cmd->sightedClientsMask = cgameGlob->sightedClientsMask;
	cmd->spawnTraceEntIndex = cgameGlob->spawnSight.traceEntIndex;
}

// src CL_CreateCmd's spawn sight masks (only for a command that is stored)
static void CL_AddSpawnSight(LocalClientNum_t localClientNum, usercmd_s *cmd)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	if (cl->snap.ps_pm_type != 0 && cl->snap.ps_pm_type != 1)  // PM_NORMAL, PM_NORMAL_LINKED
		return;
	for (unsigned short i = 0; i < cgameGlob->spawnSight.pointCount; i++)
	{
		switch (cgameGlob->spawnSight.points[i].sightState)
		{
		case 1:
			cmd->partialSightedSpawnsMask |= 1 << i;
			break;
		case 2:
			cmd->sightedSpawnsMask |= 1 << i;
			break;
		}
	}
}

// How many commands are due at cl->serverTime (0..20), after re-anchoring the grid if the time jumped
static int CL_CommandsDue(clientActive_t *cl)
{
	const int target = cl->serverTime;
	if (!s_grid.valid || target - s_grid.lastCmdTime > CMD_REANCHOR_MSEC || s_grid.lastCmdTime - target > CMD_REANCHOR_MSEC)
	{
		s_grid.lastCmdTime = target - CMD_STEP_MSEC;
		s_grid.lastCmdFrameTime = com_frameTime - (int)frame_msec;
		s_grid.valid = 1;
	}
	int n = 0;
	while (n < CMD_MAX_PER_FRAME && target - (s_grid.lastCmdTime + CMD_STEP_MSEC * n) >= CMD_STEP_MSEC)
		++n;
	return n;
}

// Store 14030BB00 (src/client_mp/cl_input.cpp), enhanced
void CL_CreateNewCommands(LocalClientNum_t localClientNum)
{
	if (CL_GetLocalClientUIGlobals(localClientNum)->connectionState < CA_PRIMED)
		return;

	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	const int mode = unk_143E96824;
	if (mode != 0 && mode != 3)
	{
		++cl->cmdNumber;
		MSG_SetDefaultUserCmd((const playerState_s *)&cl->snap, &cl->cmds[cl->cmdNumber & CMD_MASK]);
		s_grid.valid = 0;
		cl_viewCmdValid = 0;
		return;
	}

	sub_14017AB80(&unk_140CFC520, cl->clViewangles, 0, sizeof(cl->clViewangles), false);
	const int count = CL_CommandsDue(cl);

	// the frame's input, as CL_CreateCmd builds it
	const float oldPitch = cl->clViewangles[0];
	CL_AdjustAnglesFrame(localClientNum);
	usercmd_s cmd;
	CL_ClearCmd(localClientNum, &cmd);
	if (count)
		CL_AddSpawnSight(localClientNum, &cmd);

	kbutton_t *kb = playersKb[localClientNum];
	// remote control and location selection take the whole command, so they run only when commands are made
	bool handled = true;
	if (cl->snap.ps_pm_flags & PMF_REMOTE_CONTROL)
	{
		if (count)
			sub_14030DF50(localClientNum, &cmd);
	}
	else if (Key_IsCatcherActive(localClientNum, KEYCATCH_LOCATION_SELECTION))
	{
		handled = !count || CG_HandleLocationSelectionInput(localClientNum, &cmd);
	}
	else
	{
		handled = false;
	}
	if (!handled)
	{
		if (count)
		{
			// the keys over the span this frame's commands cover
			const unsigned int frameMsec = frame_msec;
			int span = com_frameTime - s_grid.lastCmdFrameTime;
			frame_msec = span > 0 ? (unsigned int)span : 1u;
			CL_CmdButtons(localClientNum, &cmd);
			CL_KeyMove(localClientNum, &cmd);
			frame_msec = frameMsec;
		}
		const float frametime_base = sub_1404633E0(cls.frametime_base);
		CL_MouseMove(localClientNum, &cmd, frametime_base);
		if (GPad_IsActive(CL_ControllerIndexFromClientNum(localClientNum)))
		{
			const bool sprintPressed = kb[KB_SPRINT].wasPressed;
			CL_GamepadMove(localClientNum, frametime_base, &cmd);
			if (!count)
				kb[KB_SPRINT].wasPressed = sprintPressed;
		}
		if (count)
			sub_1402A9900(localClientNum, &cmd);

		// never more than 90 degrees of pitch in one frame
		if (cl->clViewangles[0] - oldPitch > 90.0f)
			cl->clViewangles[0] = oldPitch + 90.0f;
		else if (oldPitch - cl->clViewangles[0] > 90.0f)
			cl->clViewangles[0] = oldPitch - 90.0f;
	}

	if (count)
	{
		s_grid.lastCmdFrameTime = com_frameTime;
		usercmd_s unfinished;
		Enh_Copy(&unfinished, &cmd, sizeof(cmd));
		for (int i = 0; i < count; ++i)
		{
			usercmd_s out;
			Enh_Copy(&out, &unfinished, sizeof(out));
			CL_FinishMove(localClientNum, &out);  // the first takes cgameExtraButtons and clears them
			s_grid.lastCmdTime += CMD_STEP_MSEC;
			out.serverTime = s_grid.lastCmdTime;
			++cl->cmdNumber;
			Enh_Copy(&cl->cmds[cl->cmdNumber & CMD_MASK], &out, sizeof(out));
		}
	}

	// the temporary view command: the newest command's input with this frame's angles, at cl->serverTime
	Enh_Copy(&cl_viewCmd, &cl->cmds[cl->cmdNumber & CMD_MASK], sizeof(cl_viewCmd));
	cl_viewCmd.serverTime = cl->serverTime;
	for (int i = 0; i < 3; i++)
		cl_viewCmd.angles[i] = (unsigned short)(int)floor((double)((cl->clViewangles[i] + cl->cgameKickAngles[i]) * 182.04445f + 0.5f));
	cl_viewCmdValid = 1;

	sub_14017AAE0(&unk_140CFC520, cl->clViewangles, 0, sizeof(cl->clViewangles));
}
