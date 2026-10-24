// cgame/cg_shellshock.cpp (Store build): the shell shock's state in cg_s.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names from Black
// Ops' server PDB (cgame/cg_shellshock.cpp); the PS4 server has no cgame.

#include "cgame_mp/cg_local_mp.h"

#define IW6_SOURCE "cgame/cg_shellshock.cpp"

static_assert(__builtin_offsetof(cg_s, shellshock_parms) == 0xB5310, "cg_s layout (Store build)");
static_assert(__builtin_offsetof(cg_s, shellshock_duration) == 0xB531C, "cg_s layout");

// Store 1402DAC10 (Black Ops' CG_StartShellShock): the shock CG_UpdateShellShock plays, set every frame from the
// snapshot (or the test shock) by CG_DrawActiveFrame
void CG_StartShellShock(cg_s *cgameGlob, const shellshock_parms_t *parms, int start, int duration)
{
	cgameGlob->shellshock_parms = parms;
	cgameGlob->shellshock_startTime = start;
	cgameGlob->shellshock_duration = duration;
}
