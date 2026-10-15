// universal/com_math.cpp
//
// Reconstructed from the PS4 dedicated server (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis, changelist 715098).
// Functions appear in original line order; each is tagged with its address in that build and its original line.

#include <math.h>

#include "universal/com_math.h"

// 14022C700  universal/com_math.cpp:2608
float AngleNormalize360(const float angle)
{
	const float scaled = angle * (1.0f / 360.0f);
	const float result = (scaled - floorf(scaled)) * 360.0f;
	if (result - 360.0f >= 0.0f)
		return result - 360.0f;
	return result;
}

// 14022C6B0  universal/com_math.cpp:2628
float AngleDelta(const float angle1, const float angle2)
{
	const float scaled = (angle1 - angle2) * (1.0f / 360.0f);
	return (scaled - floorf(scaled + 0.5f)) * 360.0f;
}
