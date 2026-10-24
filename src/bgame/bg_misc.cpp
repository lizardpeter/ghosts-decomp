// bgame/bg_misc.cpp
//
// Reconstructed from the PS4 server (iw6_ds_ps4, names and lines from its PDB) and checked against the Microsoft
// Store build (iw6mp64_MSStore_ship), which has the same code.

#include "bgame/bg_public.h"

#define IW6_SOURCE "bgame/bg_misc.cpp"

extern shellshock_parms_t bg_shellshockParms[];

// 140076150  bgame/bg_misc.cpp:3326 (Store 140266F40)
shellshock_parms_t *BG_GetShellshockParms(int index)
{
	return &bg_shellshockParms[index];
}
