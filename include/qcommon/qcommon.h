// qcommon/qcommon.h and universal/q_shared.h: engine services used across the code (prototypes from the PS4
// server MAP, iw6_ds_ps4).
#pragma once

enum CriticalSection
{
	CRITSECT_CONSOLE = 0x0,
	CRITSECT_KEY_BINDINGS = 0xC,
	// the remaining values are in the PDB (analysis/iw6_ds_ps4/pdb/types.h)
};

void Sys_EnterCriticalSection(CriticalSection critSect);
void Sys_LeaveCriticalSection(CriticalSection critSect);
int Sys_Milliseconds();
bool Com_ErrorEntering();

int SEH_GetCurrentLanguage();
#define LANGUAGE_FRENCH 1

int I_stricmp(const char *s0, const char *s1);
void I_strncpyz(char *dest, const char *src, int destsize);
char *I_strupr(char *s);
