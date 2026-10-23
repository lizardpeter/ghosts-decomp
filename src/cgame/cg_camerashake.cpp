// cgame/cg_camerashake.cpp
//
// Client-only, from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. Names, prototypes
// and the CameraShake layout come from the PS4 server PDB (which keeps CG_UpdateCameraShake, CG_AddToShakeSlot and
// CG_StartShakeCamera); CG_ShakeCamera is Black Ops' (cgame/cg_camerashake.cpp:139), absent from the server.
//
// Earthquakes and explosions start a shake (CG_StartShakeCamera): a scale, a length in ms, a source and a radius.
// Up to four are kept per local client. Every frame CG_ShakeCamera rates each live shake from cg.time and the view
// origin and adds the strongest one to the view angles as three sine waves of cg.time. Everything is a function of
// cg.time (whole milliseconds), not of the number of frames: the shake does not change with the frame rate.

#include <math.h>

#include <iw6_static.h>

#include "cgame_mp/cg_local_mp.h"

#define IW6_SOURCE "cgame/cg_camerashake.cpp"

struct CameraShake
{
	int time;          // cg.time when it started
	float scale;
	float length;      // ms
	float radius;      // 0 or less: everywhere at full strength
	float src[3];
	float size;        // set by CG_UpdateCameraShake
	float rumbleScale;
};

struct CameraShakeSet
{
	CameraShake shakes[4];
	float phase;  // re-randomised every frame without a shake
};

static_assert(sizeof(CameraShake) == 0x24, "CameraShake layout");
static_assert(sizeof(CameraShakeSet) == 0x94, "CameraShakeSet layout");
static_assert(__builtin_offsetof(cg_s, refdef_vieworg) == 0x718E0, "cg_s layout");
static_assert(__builtin_offsetof(cg_s, refdefViewAngles) == 0xA9A90, "cg_s layout");

IW6_STATIC CameraShakeSet s_cameraShakeSet[1] IW6_AT("", "s_cameraShakeSet");

float crandom();  // universal/com_math.cpp: a random float in [-1, 1)

// Store 14029BBB0 (PS4 server: cgame/cg_camerashake.cpp:75). Fades the shake linearly over its length and with the
// distance from its source; returns 0 once it is over (or before it starts), else 1 with size and rumbleScale set.
int CG_UpdateCameraShake(LocalClientNum_t localClientNum, const cg_s *cgameGlob, CameraShake *shake)
{
	const int dt = cgameGlob->time - shake->time;
	if (dt < 0)
		return 0;
	const float elapsed = (float)dt;
	if (elapsed >= shake->length)
		return 0;
	float distFrac;
	if (shake->radius <= 0.0f)
	{
		distFrac = 1.0f;
	}
	else
	{
		const float dx = cgameGlob->refdef_vieworg[0] - shake->src[0];
		const float dy = cgameGlob->refdef_vieworg[1] - shake->src[1];
		const float dz = cgameGlob->refdef_vieworg[2] - shake->src[2];
		distFrac = 1.0f - sqrtf(dy * dy + dx * dx + dz * dz) / shake->radius;
	}
	const float scale = (1.0f - elapsed / shake->length) * shake->scale;
	if (scale <= 0.0f)
		return 0;
	shake->rumbleScale = scale;
	if (distFrac >= 0.0f)
		shake->size = distFrac * scale;
	else
		shake->size = distFrac / scale;
	return 1;
}

// Store 14029B7B0 (Black Ops: cgame/cg_camerashake.cpp:139). The strongest live shake (by its pitch amplitude)
// shakes pitch, yaw and roll by 18, 16 and 10 degrees times min(size, 1) * rumbleScale, at 4/3, 5/2 and 2 Hz
// (8, 15 and 12 pi radians per 600 ms of cg.time), all with the same random phase.
void CG_ShakeCamera(LocalClientNum_t localClientNum)
{
	cg_s *cgameGlob = CG_GetLocalClientGlobals(localClientNum);
	CameraShakeSet *set = &s_cameraShakeSet[localClientNum];
	const float t = (float)cgameGlob->time / 600.0f;
	float pitch = 0.0f, yaw = 0.0f, roll = 0.0f;
	float pitchFreq = 0.0f, yawFreq = 0.0f, rollFreq = 0.0f;
	for (int i = 0; i < 4; ++i)
	{
		CameraShake *shake = &set->shakes[i];
		if (!CG_UpdateCameraShake(localClientNum, cgameGlob, shake))
			continue;
		const float size = 1.0f < shake->size ? 1.0f : shake->size;
		const float strength = size * shake->rumbleScale;
		if (strength * 18.0f > pitch)
		{
			pitch = strength * 18.0f;
			yaw = strength * 16.0f;
			roll = strength * 10.0f;
			pitchFreq = 8.0f;
			yawFreq = 15.0f;
			rollFreq = 12.0f;
		}
	}
	if (pitch > 0.0f || yaw > 0.0f || roll > 0.0f)
	{
		const float phase = set->phase;
		cgameGlob->refdefViewAngles[0] += (float)sin((double)(pitchFreq * 3.14159274f * t + phase)) * pitch;
		cgameGlob->refdefViewAngles[1] += (float)sin((double)(yawFreq * 3.14159274f * t + phase)) * yaw;
		cgameGlob->refdefViewAngles[2] += (float)sin((double)(rollFreq * 3.14159274f * t + phase)) * roll;
	}
	else
	{
		set->phase = crandom() * 3.14159274f;
	}
}
