// VC11 (VS2012) x64 CRT math, as the original binary links it.
//
// Build environment, not game source. Declarations only: in the hybrid build each one resolves to the
// original binary's CRT routine (by its MAP name, e.g. floorf at the address in analysis/<build>/map), so the
// reconstruction runs the very same math library as the original. Add functions here as reconstructed code
// needs them.
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

float floorf(float);
double floor(double);

#ifdef __cplusplus
}
#endif
