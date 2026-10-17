// enhanced/raw_input.h: raw mouse input (enhanced/win32/win_rawinput.cpp).
#pragma once

#include <windows.h>

// Starts the raw input thread. False if the mouse couldn't be registered for raw input; the mouse then doesn't
// aim at all (raw input is the only mode).
bool IN_StartRawInput();

// Adds one raw mouse report to the counters: relative movement only (absolute reports, from tablets and remote
// desktops, are ignored).
void IN_RawInputAdd(const RAWMOUSE *mouse);

// The movement since the last call, in device counts; the counters restart at zero.
void IN_TakeRawMouse(int *dx, int *dy);

// MW2019's mouse scale: degrees per device count per unit of m_sens.
#define MOUSE_DEGREES_PER_COUNT 0.0066
