// qcommon/cmd.h: console command arguments and registration (types from the PS4 server PDB, iw6_ds_ps4).
#pragma once

#include "client/client.h"  // LocalClientNum_t

struct CmdArgs
{
	int nesting;
	LocalClientNum_t localClientNum[8];
	int controllerIndex[8];
	int argc[8];
	const char **argv[8];
};

struct cmd_function_s
{
	cmd_function_s *next;
	const char *name;
	void (*function)();
};

extern CmdArgs cmd_args;

void Cmd_AddCommandInternal(const char *cmdName, void (*function)(), cmd_function_s *allocedCmd);
void Cbuf_AddText(LocalClientNum_t localClientNum, const char *text);

// Inlines from this header (qcommon/cmd.h:220 for Cmd_Argv, which the linker also kept out of line).
inline int Cmd_Argc()
{
	return cmd_args.argc[cmd_args.nesting];
}

inline const char *Cmd_Argv(int argIndex)
{
	if (argIndex >= Cmd_Argc())
		return "";
	return cmd_args.argv[cmd_args.nesting][argIndex];
}

// Registers a command with storage for its list node: one static cmd_function_s per call site. In the
// reconstruction the static is the original's (IW6_STATIC), declared at the call site.
#define Cmd_AddCommand(name, function, var) Cmd_AddCommandInternal(name, function, &var)
