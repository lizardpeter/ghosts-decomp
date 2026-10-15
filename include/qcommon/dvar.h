// qcommon/dvar.h: console variables (types from the PS4 server PDB, iw6_ds_ps4).
#pragma once

union DvarValue
{
	bool enabled;
	int integer;
	unsigned int unsignedInt;
	float value;
	float vector[4];
	const char *string;
	unsigned char color[4];
};

union DvarLimits
{
	unsigned char opaque[16];  // enumeration / integer / value / vector limits; not needed yet
};

struct dvar_t
{
	const char *name;
	unsigned int flags;
	unsigned char type;
	bool modified;
	DvarValue current;
	DvarValue latched;
	DvarValue reset;
	DvarLimits domain;
	bool (*domainFunc)(dvar_t *, DvarValue);
	dvar_t *hashNext;
};

#define DVAR_ARCHIVE 0x1

// Flags of dvars changed since the config was last written; thread-local in IW6 (.tls in the original).
extern __declspec(thread) int dvar_modifiedFlags;

int Dvar_GetInt(const char *dvarName);
