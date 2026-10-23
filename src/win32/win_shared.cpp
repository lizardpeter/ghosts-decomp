// win32/win_shared.cpp (Store build): the millisecond clock and the vector snapping Pmove uses.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Both functions
// are the PS4 server's (PDB, win32/win_shared.cpp:51 and the Sys_SnapVector after it); the Store build's statics
// are laid out as sys_timeBasesInitialized, sys_counterBase, sys_timeBase (149D6237C..149D62388).
//
// Both matter for the frame rate (docs/fps.md): every time in the frame loop and in the usercmds is a whole
// millisecond from Sys_Milliseconds, and PmoveSingle rounds the player's velocity to whole units per second with
// Sys_SnapVector at the end of every move, which is what makes jumps and acceleration depend on the length of the
// commands.

#include <windows.h>

extern "C" float floorf(float x);
extern "C" unsigned long long __rdtsc();

// C names in the PS4 server's MAP
extern "C" int sys_timeBasesInitialized;
extern "C" unsigned long long sys_counterBase;
extern "C" int sys_timeBase;

// Store 14054FE20 (PS4 PDB Sys_Milliseconds, win32/win_shared.cpp:51): timeGetTime since the first call. The first
// call also takes the rdtsc base (sys_counterBase) the raw timer is measured from.
int Sys_Milliseconds()
{
	if (!sys_timeBasesInitialized)
	{
		sys_timeBase = timeGetTime();
		sys_counterBase = __rdtsc();
		sys_timeBasesInitialized = 1;
	}
	return timeGetTime() - sys_timeBase;
}

// Store 14054FE80 (PS4 PDB Sys_SnapVector, win32/win_shared.cpp): each component to the nearest integer, halves up
// (floorf(x + 0.5f)).
void Sys_SnapVector(float *v)
{
	v[0] = floorf(v[0] + 0.5f);
	v[1] = floorf(v[1] + 0.5f);
	v[2] = floorf(v[2] + 0.5f);
}
