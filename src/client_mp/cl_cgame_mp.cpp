// client_mp/cl_cgame_mp.cpp (Store build): the client side of the cgame interface the prediction uses.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses; names and file
// from Black Ops' server PDB (client_mp/cl_cgame_mp.cpp), whose functions are the same code a generation earlier.
// The cgame reads the client's usercmd ring through CL_GetCurrentCmdNumber and CL_GetUserCmd, and hands the
// predicted origin and vehicle state back for the next command (CL_SetUserCmdOrigin, sub_140306FD0).

#include "client_mp/client_mp.h"
#include "qcommon/qcommon.h"

static_assert(__builtin_offsetof(clientActive_t, cgameOrigin) == 0x3580, "clientActive_t layout (Store build)");
static_assert(__builtin_offsetof(clientActive_t, cgamePlayerVehState) == 0x3598, "clientActive_t layout");
static_assert(__builtin_offsetof(clientActive_t, cgameBobCycle) == 0x3600, "clientActive_t layout");
static_assert(__builtin_offsetof(clientActive_t, cgamePredictedDataServerTime) == 0x360C, "clientActive_t layout");

// Store 140305E50 (Black Ops' CL_GetCurrentCmdNumber, cl_cgame_mp.cpp:195): the newest command's number
int CL_GetCurrentCmdNumber(LocalClientNum_t localClientNum)
{
	return CL_GetLocalClientGlobals(localClientNum)->cmdNumber;
}

// Store 1403065F0 (Black Ops' CL_GetUserCmd, cl_cgame_mp.cpp:138): a copy of command cmdNumber, or 0 when it has
// already been overwritten in the ring of CMD_BACKUP. A number past the newest is an ERR_DROP; if Com_Error returns,
// the command is read anyway.
int CL_GetUserCmd(LocalClientNum_t localClientNum, int cmdNumber, usercmd_s *ucmd)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	if (cmdNumber > cl->cmdNumber)
		Com_Error(ERR_DROP, "\x1F" "CL_GetUserCmd: %i >= %i", cmdNumber, cl->cmdNumber);
	if (cmdNumber <= cl->cmdNumber - CMD_BACKUP)
		return 0;
	*ucmd = cl->cmds[cmdNumber & CMD_MASK];
	return 1;
}

// Store 140306F60 (Black Ops' CL_SetUserCmdOrigin, cl_cgame_mp.cpp:357, which took the fields one by one): the
// predicted origin, velocity, bob cycle and movement direction for the next usercmd, stamped with cl->serverTime.
// The Store build's callers also pass cg's selected location and its angle, which this function does not read.
void CL_SetUserCmdOrigin(LocalClientNum_t localClientNum, const playerState_s *ps, const float *selectedLocation,
                         float selectedLocationAngle)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	cl->cgamePredictedDataServerTime = cl->serverTime;
	cl->cgameOrigin[0] = ps->origin[0];
	cl->cgameOrigin[1] = ps->origin[1];
	cl->cgameOrigin[2] = ps->origin[2];
	cl->cgameVelocity[0] = ps->velocity[0];
	cl->cgameVelocity[1] = ps->velocity[1];
	cl->cgameVelocity[2] = ps->velocity[2];
	cl->cgameBobCycle = ps->bobCycle;
	cl->cgameMovementDir = ps->movementDir;
}

// Store 140306FD0 (name unknown; Black Ops' CL_SetUserCmdVehicle took the vehicle's position and velocities): the
// predicted player's vehicle state for the next usercmd
void sub_140306FD0(LocalClientNum_t localClientNum, const PlayerVehicleState *vehicleState)
{
	CL_GetLocalClientGlobals(localClientNum)->cgamePlayerVehState = *vehicleState;
}

void sub_1402891D0(unsigned int offHand);  // empty in this build (Black Ops' BG_AssertOffhandIndexOrNone)

// Store 140306E80 (Black Ops' CL_SetFOVSensitivityScale, cl_cgame_mp.cpp:384): the scale CL_MouseMove applies
void CL_SetFOVSensitivityScale(LocalClientNum_t localClientNum, float scale)
{
	CL_GetLocalClientGlobals(localClientNum)->cgameFOVSensitivityScale = scale;
}

// Store 140306F30 (Black Ops' CL_SetUserCmdAimValues): the angles CL_FinishMove adds to every command's view angles
void CL_SetUserCmdAimValues(LocalClientNum_t localClientNum, const float *kickAngles)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	cl->cgameKickAngles[0] = kickAngles[0];
	cl->cgameKickAngles[1] = kickAngles[1];
	cl->cgameKickAngles[2] = kickAngles[2];
}

// Store 140307110 (Black Ops' CL_SetUserCmdWeapons, cl_cgame_mp.cpp:321)
void CL_SetUserCmdWeapons(LocalClientNum_t localClientNum, unsigned int weapon, unsigned int offHand, int alternate)
{
	clientActive_t *cl = CL_GetLocalClientGlobals(localClientNum);
	sub_1402891D0(offHand);
	cl->cgameUserCmdWeapon = weapon;
	cl->cgameUserCmdOffHand = offHand;
	cl->cgameUserCmdAlternate = alternate != 0;
}

// Store 140306E70 (Black Ops' CL_SetExtraButtons, cl_cgame_mp.cpp:393, which took a bit array): OR-ed into the next
// command's buttons by CL_FinishMove, which clears them
void CL_SetExtraButtons(LocalClientNum_t localClientNum, int buttons)
{
	CL_GetLocalClientGlobals(localClientNum)->cgameExtraButtons |= buttons;
}
