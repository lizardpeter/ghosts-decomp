// enhanced/sound/snd.cpp: the doppler pitch smoothed with a time constant (records/patches.tsv P0028; B0067;
// docs/fps-frame.md 4.6, docs/cgame-frame.md 4.11).
//
// The original (src/sound/snd.cpp, Store 1406AD9E0) smooths each channel's doppler pitch per sound update,
// p = (k p + new) / (k + 1), k = snd_dopplerSmoothing; the updates follow the frames, so at 500 fps it smooths over
// about an eighth of the time it does at 60. Enhanced: the old pitch's weight k / (k + 1) is taken per 16.667 ms and
// raised to msec / 16.667 for an update of msec (the update's own msec, cg.frametime): the same smoothing over time at
// any frame rate, the original's at 60 fps (up to rounding). Without a positive k it is the original. The rest of the
// function is the original's.

#include <math.h>

#include "cgame_mp/cg_local_mp.h"
#include "qcommon/dvar.h"


// The doppler's parameters, as the dvars give them or an override has them (name unknown)
struct SndDopplerParms
{
	unsigned char unknown0[8];
	float speedOfSound;    // snd_dopplerBaseSpeedOfSound
	float velocityScale;   // snd_dopplerPlayerVelocityScale
	float pitchMin;        // snd_dopplerPitchMin
	float pitchMax;        // snd_dopplerPitchMax
	float smoothing;       // snd_dopplerSmoothing: the old pitch's weight per update
};

// The part of a sound channel the doppler reads (0xF8 apart, from 4 bytes into the channel; name unknown)
#pragma pack(push, 4)
struct SndDopplerChannel
{
	int entity;                       // the sound's entity, for its position (1402C0600)
	unsigned char unknown4[0x74 - 4];
	const unsigned char *alias;       // +0xB8: the alias has doppler; +0xC0: its own parameters (or null)
	unsigned char unknown7C[0xF8 - 0x7C];
};
#pragma pack(pop)
static_assert(sizeof(SndDopplerChannel) == 0xF8, "SndDopplerChannel size");

extern int unk_14BAF3368;                      // the update's msec when the doppler was first run, 0 before (name unknown)
extern float unk_14BAF336C[3];                 // the listener's position at the last update (name unknown)
extern float unk_14BAF3378[32][3];             // each channel's source position at the last update (name unknown)
extern float unk_14BAF34F8[32];                // each channel's doppler pitch (name unknown)
extern SndDopplerChannel unk_14BAEC804[32];    // channels 8..39 (name unknown)
extern const SndDopplerParms *unk_14BAF3578;   // an override of the dvars (name unknown)
extern const dvar_t *snd_dopplerEnable;
extern const dvar_t *snd_dopplerAuditionEnable;
extern const dvar_t *snd_dopplerBaseSpeedOfSound;
extern const dvar_t *snd_dopplerPlayerVelocityScale;
extern const dvar_t *snd_dopplerPitchMin;
extern const dvar_t *snd_dopplerPitchMax;
extern const dvar_t *snd_dopplerSmoothing;

bool sub_1404DC1A0(int channel);                                  // the channel is free or paused (name unknown)
void sub_1402C0600(int entity, float *origin, void *unused);      // a sound entity's position (name unknown)

// The smoothing as a time constant: the old pitch's weight per update, smoothing / (smoothing + 1), is the weight per
// 16.667 ms (one update at 60 fps); an update of msec takes it to the power msec / 16.667
static float SND_DopplerWeight(float smoothing, int msec)
{
	if (!(smoothing > 0.0f))
		return -1.0f;  // not a weight: the original's formula
	return (float)exp(log((double)smoothing / ((double)smoothing + 1.0)) * ((double)msec * 0.06));
}

// Store 1406AD9E0, enhanced (B0067)
void sub_1406AD9E0(int msec)
{
	if (msec <= 0)
		return;
	// the listener: the first entity's pose (cg_entitiesArray[0][0], the local player's)
	const float lx = cg_entitiesArray[0][0].pose_origin[0], ly = cg_entitiesArray[0][0].pose_origin[1];
	const float lz = cg_entitiesArray[0][0].pose_origin[2];
	if (unk_14BAF3368 <= 0)
	{
		unk_14BAF336C[0] = lx;
		unk_14BAF3368 = msec;
		unk_14BAF336C[1] = ly;
		unk_14BAF336C[2] = lz;
		return;
	}
	const float listenerDelta[3] = {lx - unk_14BAF336C[0], ly - unk_14BAF336C[1], lz - unk_14BAF336C[2]};
	const float seconds = (float)msec / 1000.0f;
	float speed, scale, pitchMin, pitchMax, smoothing;
	if (unk_14BAF3578 && !snd_dopplerAuditionEnable->current.enabled)
	{
		scale = unk_14BAF3578->velocityScale;
		pitchMin = unk_14BAF3578->pitchMin;
		pitchMax = unk_14BAF3578->pitchMax;
		smoothing = unk_14BAF3578->smoothing;
		speed = unk_14BAF3578->speedOfSound;
	}
	else
	{
		scale = snd_dopplerPlayerVelocityScale->current.value;
		pitchMin = snd_dopplerPitchMin->current.value;
		pitchMax = snd_dopplerPitchMax->current.value;
		smoothing = snd_dopplerSmoothing->current.value;
		speed = snd_dopplerBaseSpeedOfSound->current.value;
	}
	for (int i = 8; i < 40; ++i)
	{
		SndDopplerChannel *ch = &unk_14BAEC804[i - 8];
		float *pitch = &unk_14BAF34F8[i - 8];
		float *last = unk_14BAF3378[i - 8];
		if (!snd_dopplerEnable->current.enabled || sub_1404DC1A0(i) || !ch->alias || !ch->alias[0xB8])
		{
			*pitch = 1.0f;
			continue;
		}
		const SndDopplerParms *own = *(const SndDopplerParms *const *)(ch->alias + 0xC0);
		float cScale, cMin, cMax, cSmoothing, cSpeed;
		if (own && !snd_dopplerAuditionEnable->current.enabled)
		{
			cScale = own->velocityScale;
			cMin = own->pitchMin;
			cMax = own->pitchMax;
			cSmoothing = own->smoothing;
			cSpeed = own->speedOfSound;
		}
		else
		{
			if (!own && !snd_dopplerAuditionEnable->current.enabled && !unk_14BAF3578)
			{
				*pitch = 1.0f;
				continue;
			}
			cScale = scale;
			cMin = pitchMin;
			cMax = pitchMax;
			cSpeed = speed;
			cSmoothing = smoothing;
		}
		const float travel = seconds * cSpeed;
		float origin[3];
		unsigned char unused[0xD0];
		sub_1402C0600(ch->entity, origin, unused);
		const float dx = origin[0] - lx, dy = origin[1] - ly, dz = origin[2] - lz;
		const float sx = origin[0] - last[0], sy = origin[1] - last[1], sz = origin[2] - last[2];
		const float dist = sqrtf(dy * dy + dx * dx + dz * dz);
		if (!(dist > 0.001f))
		{
			*pitch = 1.0f;
			continue;
		}
		const float limit = travel * 4.0f;
		const float source = (sy * dy + sx * dx + sz * dz) / dist;
		const float listener = (listenerDelta[1] * dy + listenerDelta[0] * dx + listenerDelta[2] * dz) / dist * cScale
		                       + travel;
		float heard = listener - limit >= 0.0f ? limit : listener;
		if (0.1f - listener >= 0.0f)
			heard = 0.1f;
		const float emitted = travel + source;
		float sent = emitted - limit >= 0.0f ? limit : emitted;
		if (0.1f - emitted >= 0.0f)
			sent = 0.1f;
		float ratio = heard / sent;
		if (1.0f > ratio)
		{
			const float f = (ratio - 1.0f) * -1.0f / (cMax - 1.0f);
			ratio = f * cMin + (1.0f - f);
		}
		const float hi = ratio - cMax >= 0.0f ? cMax : ratio;
		const float clamped = cMin - ratio >= 0.0f ? cMin : hi;
		const float weight = SND_DopplerWeight(cSmoothing, msec);
		if (weight < 0.0f)
			*pitch = (cSmoothing * *pitch + clamped) / (cSmoothing + 1.0f);
		else
			*pitch = weight * *pitch + (1.0f - weight) * clamped;
		last[2] = origin[2];
		last[0] = origin[0];
		last[1] = origin[1];
	}
	unk_14BAF336C[0] = lx;
	unk_14BAF336C[2] = lz;
	unk_14BAF336C[1] = ly;
}
