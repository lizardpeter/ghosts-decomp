// bgame/bg_jump.cpp (Store build): jumping.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses; names, order and
// line numbers are the PS4 server's (PDB, bgame/bg_jump.cpp), whose code is the same apart from what the Store build
// inlines: Jump_Start and Jump_PushOffLadder into Jump_Check, and Jump_GetJumpHeight into its three users.
//
// A jump sets velocity[2] = sqrt(2 * gravity * jump height) once (39 units unless the "alt_jump_height" omnvar says
// otherwise), and from then on gravity and Sys_SnapVector in PmoveSingle decide how high it goes. Jump_ClampVelocity
// caps the height at jumpOriginZ + 39 only when PM_StepSlideMove steps up during a jump, not in free flight, so the
// peak of a free jump depends on how long each command is (docs/fps.md).

#include "bgame/bg_public.h"

extern "C" float sqrtf(float x);

extern LocalClientNum_t g_cgameClientNum;  // cgame: the local client the cgame's movement runs for

#define JUMP_LAND_SLOWDOWN_TIME 1800  // pm_time after landing from a jump (0x708)

// Store 140260E60 (PS4 PDB Jump_GetJumpHeight, bgame/bg_jump.cpp:114). Omnvar_GetDef is called for nothing (the
// check that used it is compiled out). handler 0 is the cgame's movement, any other the game's.
float Jump_GetJumpHeight(pmove_t *pm)
{
	if (pm)
	{
		const unsigned int index = Omnvar_GetIndexByName("alt_jump_height");
		if (index != 0xFFFFFFFF)
		{
			Omnvar_GetDef(index);
			const OmnvarData *data = pm->handler ? G_Omnvar_GetData(index, -1, nullptr)
			                                     : sub_140543040(g_cgameClientNum, index);
			if (data && data->value != 0.0f)
				return data->value;
		}
	}
	return 39.0f;
}

// Store 140260E40 (PS4 PDB Jump_ClearState, bgame/bg_jump.cpp:161)
void Jump_ClearState(playerState_s *ps)
{
	ps->pm_flags &= ~PMF_JUMPING;
	ps->jumpOriginZ = 0.0f;
}

// Store 140260EE0 (PS4 PDB Jump_GetStepHeight, bgame/bg_jump.cpp:171): while the player is below the jump's peak
// height, PM_StepSlideMove may step up 18 units, or what is left to the peak.
bool Jump_GetStepHeight(pmove_t *pm, playerState_s *ps, const float *const origin, float *stepSize)
{
	if (!(Jump_GetJumpHeight(pm) + ps->jumpOriginZ > origin[2]))
		return false;
	*stepSize = 18.0f;
	if (origin[2] + *stepSize > Jump_GetJumpHeight(pm) + ps->jumpOriginZ)
		*stepSize = (Jump_GetJumpHeight(pm) + ps->jumpOriginZ) - origin[2];
	return true;
}

// Store 140261090 (PS4 PDB Jump_IsPlayerAboveMax, bgame/bg_jump.cpp:196)
bool Jump_IsPlayerAboveMax(pmove_t *pm, playerState_s *ps)
{
	return ps->origin[2] >= Jump_GetJumpHeight(pm) + ps->jumpOriginZ;
}

// Store 140260900 (PS4 PDB Jump_ActivateSlowdown, bgame/bg_jump.cpp:207)
void Jump_ActivateSlowdown(playerState_s *ps)
{
	if (!ps->pm_time)
	{
		ps->pm_flags |= PMF_JUMPING;
		ps->pm_time = JUMP_LAND_SLOWDOWN_TIME;
	}
}

// Store 140260920 (PS4 PDB Jump_ApplySlowdown, bgame/bg_jump.cpp:220): the landing slowdown
void Jump_ApplySlowdown(playerState_s *ps)
{
	float scale = 1.0f;
	if (ps->pm_time > JUMP_LAND_SLOWDOWN_TIME)
	{
		Jump_ClearState(ps);
		scale = 0.65f;
	}
	else if (!ps->pm_time)
	{
		if (ps->jumpOriginZ + 18.0f > ps->origin[2])
		{
			scale = 0.65f;
			ps->pm_time = JUMP_LAND_SLOWDOWN_TIME;
		}
		else
		{
			scale = 0.5f;
			ps->pm_time = 1200;
		}
	}
	ps->velocity[0] = scale * ps->velocity[0];
	ps->velocity[1] = scale * ps->velocity[1];
	ps->velocity[2] = scale * ps->velocity[2];
}

// Store 140261130 (PS4 PDB Jump_ReduceFriction, bgame/bg_jump.cpp:273): the friction factor during the slowdown,
// 1 + 1.5 * pm_time / 1700, capped at 2.5
float Jump_ReduceFriction(playerState_s *ps)
{
	if (ps->pm_time > JUMP_LAND_SLOWDOWN_TIME)
	{
		Jump_ClearState(ps);
		return 1.0f;
	}
	if (ps->pm_time >= 1700)
		return 2.5f;
	return (float)ps->pm_time * 1.5f * 0.00058823527f + 1.0f;
}

// Store 140260D30 (PS4 PDB Jump_ClampVelocity, bgame/bg_jump.cpp:296): after a step up during a jump, no more upward
// speed than reaches the jump's peak height. The Store build computes 2 * height * gravity as (h + h) * gravity.
void Jump_ClampVelocity(pmove_t *pm, playerState_s *ps, const float *const origin)
{
	if (!(ps->origin[2] - origin[2] > 0.0f))
		return;
	const float heightLeft = (Jump_GetJumpHeight(pm) + ps->jumpOriginZ) - ps->origin[2];
	if (0.1f > heightLeft)
	{
		ps->velocity[2] = 0.0f;
		return;
	}
	const float speed = sqrtf((heightLeft + heightLeft) * (float)ps->gravity);
	if (ps->velocity[2] > speed)
		ps->velocity[2] = speed;
}

// PS4 PDB Jump_Start (bgame/bg_jump.cpp:344), inlined into Jump_Check in the Store build: a second jump during the
// landing slowdown starts slower (its speed squared divided by the friction factor)
static inline void Jump_Start(pmove_t *pm, pml_t *pml, float height)
{
	playerState_s *ps = pm->ps;
	float speedSquared = (float)ps->gravity * (height * 2.0f);
	if ((ps->pm_flags & PMF_JUMPING) && ps->pm_time <= JUMP_LAND_SLOWDOWN_TIME)
		speedSquared = speedSquared / (ps->pm_time >= 1700 ? 2.5f : (float)ps->pm_time * 1.5f * 0.00058823527f + 1.0f);
	pml->groundPlane = 0;
	pml->almostGroundPlane = 0;
	pml->walking = 0;
	ps->groundEntityNum = ENTITYNUM_NONE;
	ps->jumpTime = pm->cmd.serverTime;
	ps->jumpOriginZ = ps->origin[2];
	ps->velocity[2] = sqrtf(speedSquared);
	ps->pm_flags &= ~(PMF_JUMP_HELD | PMF_TIME_LAND);
	ps->pm_flags |= PMF_JUMPING;
	ps->pm_time = 0;
	ps->sprintState_sprintButtonUpRequired = 0;
	const float spread = ps->weapCommon_aimSpreadScale + 64.0f;
	ps->weapCommon_aimSpreadScale = spread < 255.0f ? spread : 255.0f;
}

// PS4 PDB Jump_PushOffLadder (bgame/bg_jump.cpp:389), inlined into Jump_Check in the Store build, which normalizes the
// flat view direction with Vec3Normalize
static inline void Jump_PushOffLadder(playerState_s *ps, pml_t *pml)
{
	ps->velocity[2] = ps->velocity[2] * 0.75f;
	float dir[3];
	dir[0] = pml->forward[0];
	dir[1] = pml->forward[1];
	dir[2] = 0.0f;
	Vec3Normalize(dir);
	if (ps->vLadderVec[1] * pml->forward[1] + ps->vLadderVec[0] * pml->forward[0] + ps->vLadderVec[2] * pml->forward[2] < 0.0f)
	{
		// reflect off the ladder
		const float dot = (ps->vLadderVec[1] * dir[1] + ps->vLadderVec[0] * dir[0] + ps->vLadderVec[2] * dir[2]) * -2.0f;
		dir[0] = ps->vLadderVec[0] * dot + dir[0];
		dir[1] = ps->vLadderVec[1] * dot + dir[1];
		dir[2] = ps->vLadderVec[2] * dot + dir[2];
		Vec3Normalize(dir);
	}
	ps->pm_flags &= ~PMF_LADDER;
	ps->velocity[0] = dir[0] * 128.0f;
	ps->velocity[1] = dir[1] * 128.0f;
}

// Store 1402609B0 (PS4 PDB Jump_Check, bgame/bg_jump.cpp:445): starts a jump on a new press of the jump button
// (cmd.buttons 0x400), at least 500 ms after the last one, standing, not off a player or an agent (eType 12, 14)
bool Jump_Check(pmove_t *pm, pml_t *pml)
{
	playerState_s *ps = pm->ps;
	const int flags = ps->pm_flags;
	if ((flags & PMF_NO_JUMP) || pm->cmd.serverTime - ps->jumpTime < 500 || (flags & PMF_FROZEN) || (flags & PMF_MANTLE)
	    || ps->pm_type >= 7 || PM_GetEffectiveStance(ps) != PM_EFF_STANCE_DEFAULT || !(pm->cmd.buttons & 0x400))
		return false;
	if (pm->oldcmd.buttons & 0x400)
	{
		pm->cmd.buttons &= ~0x400u;
		return false;
	}
	if (pml->groundTrace.hitId != ENTITYNUM_NONE
	    && ((BG_GetEntityState(pm->handler, pml->groundTrace.hitId)->eType - 12) & ~2) == 0)
		return false;

	Jump_Start(pm, pml, Jump_GetJumpHeight(pm));
	const unsigned int surfaceType = PM_GroundSurfaceType(pml);
	if (surfaceType)
		BG_AddPredictableEventToPlayerstate(0x7F, BG_PackFootstepEventParm(ps, surfaceType), ps);
	if (ps->pm_flags & PMF_LADDER)
		Jump_PushOffLadder(ps, pml);
	BG_AnimUpdatePlayerStateConditions(pm);
	BG_AnimScriptEvent(ps, pm->cmd.forwardmove < 0 ? ANIM_ET_JUMPBK : ANIM_ET_JUMP, 0, 1, &pml->holdrand);
	return true;
}

// Store 140261190 (PS4 PDB Jump_RegisterDvars): empty
void Jump_RegisterDvars()
{
}
