// client_mp/cl_input.cpp
//
// Reconstructed from the PS4 dedicated server (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis, changelist 715098): the
// few button handlers it keeps. CL_IsGamepadEnabled and CL_ExecBinding are stubs in that build (folded with
// `return true` and an empty function), so they, and the mouse and usercmd code, come from the Store build.
// Functions appear in original line order; each is tagged with its address in that build and its original line.

#include <iw6_static.h>

#include "client/client.h"

#define IW6_SOURCE "client_mp/cl_input.cpp"

// Button state of every local client (file static).
IW6_STATIC kbutton_t playersKb[1][NUM_BUTTONS] IW6_AT("", "playersKb");

// Quake 3's IN_KeyDown / IN_KeyUp with the key and time passed in rather than read from the command line
// (inlined into every handler below).
static inline void IN_KeyDown(kbutton_t *b, int k, unsigned int downtime)
{
	if (k == b->down[0] || k == b->down[1])
		return;  // repeating key

	if (!b->down[0])
		b->down[0] = k;
	else if (!b->down[1])
		b->down[1] = k;
	else
		return;  // three keys down

	if (b->active)
		return;  // still down
	b->downtime = downtime;
	b->active = true;
	b->wasPressed = true;
}

static inline void IN_KeyUp(kbutton_t *b, int k, unsigned int uptime)
{
	if (b->down[0] == k)
		b->down[0] = 0;
	else if (b->down[1] == k)
		b->down[1] = 0;
	else
		return;  // key up without corresponding down

	if (b->down[0] || b->down[1])
		return;  // some other key is still holding it down

	b->active = false;
	// save timed portion of this frame
	if (uptime)
		b->msec += uptime - b->downtime;
	else
		b->msec += frame_msec / 2;
}

// A tap: press and release in the same frame.
static inline void IN_KeyTap(kbutton_t *b, int k)
{
	IN_KeyDown(b, k, 0);
	IN_KeyUp(b, k, 0);
}

// 1400ACCF0  client_mp/cl_input.cpp:469
void CL_UseReload(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_USE_RELOAD], key);
}

// 1400ACBF0  client_mp/cl_input.cpp:482
void CL_SpecPrev(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_SPECPREV], key);
}

// 1400ACB70  client_mp/cl_input.cpp:489
void CL_SpecNext(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_SPECNEXT], key);
}

// 1400ACC70  client_mp/cl_input.cpp:496
void CL_ToggleSpec(LocalClientNum_t localClientNum, int key)
{
	IN_KeyTap(&playersKb[localClientNum][KB_SPECTATE], key);
}
