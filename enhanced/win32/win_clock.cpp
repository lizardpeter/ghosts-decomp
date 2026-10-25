// enhanced/win32/win_clock.cpp: the high-resolution clock under the millisecond clock (docs/cgame-frame.md 4.1).
//
// The original Sys_Milliseconds (src/win32/win_shared.cpp, Store 14054FE20) is timeGetTime() since its first call:
// whole milliseconds with nothing below. Here the same function counts on QueryPerformanceCounter: Sys_Microseconds
// is the microseconds since the first read, and Sys_Milliseconds is its floor in milliseconds, so every original
// reader (Com_Frame's frame time, the limiter, event times, the waits) gets the same integer meaning, and the
// fraction the render time needs comes from the same counter. The first call still takes the rdtsc base the raw
// timer is measured from (sys_counterBase) and sets sys_timeBase, as the original's does, unless 14054FD70 (the
// other initialisation of the same bases, from timeGetTime) already did; the QPC base has a flag of its own.

#include <windows.h>

#include "enhanced/render_time.h"

extern "C" unsigned long long __rdtsc();
extern "C" int sys_timeBasesInitialized;
extern "C" unsigned long long sys_counterBase;
extern "C" int sys_timeBase;

long long sys_qpcBase;       // the counter at the first read (not static: tests set it)
long long sys_qpcFrequency;  // counts per second
int sys_qpcInitialized;       // its own flag: 14054FD70 also sets sys_timeBasesInitialized, from timeGetTime

static void Sys_InitClock()
{
	LARGE_INTEGER frequency, counter;
	frequency.QuadPart = 0;
	counter.QuadPart = 0;
	QueryPerformanceFrequency(&frequency);
	QueryPerformanceCounter(&counter);
	sys_qpcFrequency = frequency.QuadPart > 0 ? frequency.QuadPart : 1;
	sys_qpcBase = counter.QuadPart;
	if (!sys_timeBasesInitialized)
	{
		sys_timeBase = timeGetTime();
		sys_counterBase = __rdtsc();
		sys_timeBasesInitialized = 1;
	}
	sys_qpcInitialized = 1;
}

// new: microseconds since the first clock read (never negative)
long long Sys_Microseconds()
{
	if (!sys_qpcInitialized)
		Sys_InitClock();
	LARGE_INTEGER counter;
	counter.QuadPart = 0;
	QueryPerformanceCounter(&counter);
	long long ticks = counter.QuadPart - sys_qpcBase;
	if (ticks < 0)
		ticks = 0;
	// split so ticks * 1000000 can't overflow
	return ticks / sys_qpcFrequency * 1000000 + ticks % sys_qpcFrequency * 1000000 / sys_qpcFrequency;
}

// Store 14054FE20 (src/win32/win_shared.cpp), enhanced: whole milliseconds of Sys_Microseconds
int Sys_Milliseconds()
{
	return (int)(Sys_Microseconds() / 1000);
}
