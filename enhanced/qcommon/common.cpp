// enhanced/qcommon/common.cpp: com_maxfps up to 1000 (records/patches.tsv, the frame-rate patch).
//
// The original registers com_maxfps with a maximum of 100 (B0024). Com_Frame turns it into a minimum frame time of
// 1000 / com_maxfps whole milliseconds, so a cap gives 1000/k fps (250, 200, 166, ...), and 0 is uncapped (at most
// 1000 fps: Com_Frame never takes less than 1 ms; docs/fps.md section 1). Com_InitDvars is the original otherwise.

#include "client/client.h"
#include "qcommon/cmd.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"
#include "win32/win_local.h"
#include "iw6_static.h"
#define IW6_SOURCE "qcommon/common.cpp"

extern const dvar_t *com_sv_running;

// ==== BEGIN dvars ====
// Com_InitDvars: the common dvars, com_maxfps among them. The Store build's list is the PS4 server's without the
// dedicated server's (sv_config, consoleGame, ds_logfile) and with com_completionResolveCommand, playlistFilename and
// the dcache upload throttle; two other modules' registrations run from it (sub_1403358C0, sub_140223D30).

unsigned int Sys_GetCpuCount();  // qcommon/threads.cpp
void sub_1403358C0();            // registers the map pack and party dvars (name unknown)
void sub_140223D30();            // registers the lui_* dvars (name unknown)
void sub_140464DE0();            // empty (name unknown)

extern const dvar_t *com_dedicated_dhclient;
extern const dvar_t *com_maxfps;
extern const dvar_t *sys_lockThreads;
extern const dvar_t *sys_smp_allowed;
extern const dvar_t *com_fixedtime;
extern const dvar_t *com_maxFrameTime;
extern const dvar_t *sv_paused;
extern const dvar_t *cl_paused;
extern const dvar_t *com_filter_output;
extern const dvar_t *intro;
extern const dvar_t *com_animCheck;
extern const dvar_t *com_hiDef;
extern const dvar_t *com_wideScreen;
extern const dvar_t *com_cinematicEndInWhite;
extern const dvar_t *com_errorResolveCommand;
extern const dvar_t *com_completionResolveCommand;
extern const dvar_t *playlistFilename;
extern const dvar_t *playlistAggrFilename;
extern const dvar_t *playListUpdateCheckMinutes;
extern const dvar_t *dcacheThrottleEnabled;
extern const dvar_t *dcacheThrottleKBytesPerSec;
extern const dvar_t *band_2players;
extern const dvar_t *band_4players;
extern const dvar_t *band_8players;
extern const dvar_t *band_12players;
extern const dvar_t *band_18players;
extern const dvar_t *cpu_speed_8players;
extern const dvar_t *cpu_speed_12players;
extern const dvar_t *cpu_speed_18players;
extern const dvar_t *stringtable_debug;
extern const dvar_t *accessToSubscriberContent;
extern const dvar_t *cl_modifiedDebugPlacement;
IW6_STATIC const char *s_lockThreadNames[] IW6_AT("", "s_lockThreadNames");  // the sys_lockThreads names

// src: Store 140460F80 Com_InitDvars. Enhanced: com_maxfps goes up to 1000 (the original's maximum is 100: B0024).
void Com_InitDvars()
{
	com_dedicated_dhclient = Dvar_RegisterBool("dedicated_dhclient", false, 0, "True if we're a client playing on a DH server");
	com_maxfps = Dvar_RegisterInt("com_maxfps", 85, 0, 1000, 0, "Cap frames per second");
	sys_lockThreads = Dvar_RegisterEnum("sys_lockThreads", s_lockThreadNames, 0, 0,
		"Prevents specified threads from changing CPUs; improves profiling and may fix some bugs, but can hurt performance");
	sys_smp_allowed = Dvar_RegisterBool("sys_smp_allowed", Sys_GetCpuCount() > 1, 0x800, "Allow multi-threading");
	com_fixedtime = Dvar_RegisterInt("fixedtime", 0, 0, 1000, 4, "Use a fixed time rate for each frame");
	com_maxFrameTime = Dvar_RegisterInt("com_maxFrameTime", 100, 50, 5000, 0,
		"Time slows down if a frame takes longer than this many milliseconds");
	sv_paused = Dvar_RegisterInt("sv_paused", 0, 0, 2, 0x2000, "Pause the server");
	cl_paused = Dvar_RegisterInt("cl_paused", 0, 0, 2, 0x2000, "Pause the client");
	com_sv_running = Dvar_RegisterBool("sv_running", false, 0x2000, "Server is running");
	com_filter_output = Dvar_RegisterBool("com_filter_output", false, 0, "Use console filters for filtering output.");
	intro = Dvar_RegisterBool("intro", true, 1, "Intro movie should play");
	com_animCheck = Dvar_RegisterBool("com_animCheck", false, 0, "Check anim tree");
	com_hiDef = Dvar_RegisterBool("hiDef", true, 0x2000, "True if the game video is running in high-def.");
	com_wideScreen = Dvar_RegisterBool("wideScreen", true, 0x2000, "True if the game video is running in 16x9 aspect, false if 4x3.");
	com_cinematicEndInWhite = Dvar_RegisterBool("com_cinematicEndInWhite", false, 0x40,
		"Set by script. True if cinematic ends with a white screen.");
	com_errorResolveCommand = Dvar_RegisterString("com_errorResolveCommand", "", 0x2000,
		"Command to run when they close the error box");
	com_completionResolveCommand = Dvar_RegisterString("com_completionResolveCommand", "", 0x2000,
		"Command to run when the message box successfully closes");
	playlistFilename = Dvar_RegisterString("playlistFilename", "playlists.info", 0, "Playlist filename");
	playlistAggrFilename = Dvar_RegisterString("playlistAggrFilename", "playlists_tu14.aggr", 0, "Aggregated playlist filename");
	playListUpdateCheckMinutes = Dvar_RegisterInt("playListUpdateCheckMinutes", 5, 5, 0x7FFFFFFF, 0,
		"Minutes to wait between checking for updated playlist.");
	dcacheThrottleEnabled = Dvar_RegisterBool("dcacheThrottleEnabled", true, 0, "Enable or disable dcache upload throttling.");
	dcacheThrottleKBytesPerSec = Dvar_RegisterInt("dcacheThrottleKBytesPerSec", 32, 0, 0x7FFFFFFF, 0,
		"Dcache upload throttle limit in K Bytes per second.");
	band_2players = Dvar_RegisterInt("band_2players", 64000, 0, 0x7FFFFFFF, 0, "2 player bandwidth req'd");
	band_4players = Dvar_RegisterInt("band_4players", 128000, 0, 0x7FFFFFFF, 0, "4 player bandwidth req'd");
	band_8players = Dvar_RegisterInt("band_8players", 256000, 0, 0x7FFFFFFF, 0, "8 player bandwidth req'd");
	band_12players = Dvar_RegisterInt("band_12players", 576000, 0, 0x7FFFFFFF, 0, "12 player bandwidth req'd");
	band_18players = Dvar_RegisterInt("band_18players", 725000, 0, 0x7FFFFFFF, 0, "18 player bandwidth req'd");
	cpu_speed_8players = Dvar_RegisterFloat("cpu_speed_8players", 5.7f, 0.0f, 1000.0f, 0, "8 player sys_configureGHz req'd");
	cpu_speed_12players = Dvar_RegisterFloat("cpu_speed_12players", 6.0f, 0.0f, 1000.0f, 0, "12 player sys_configureGHz req'd");
	cpu_speed_18players = Dvar_RegisterFloat("cpu_speed_18players", 9.0f, 0.0f, 1000.0f, 0, "18 player sys_configureGHz req'd");
	stringtable_debug = Dvar_RegisterInt("stringtable_debug", 0, 0, 2, 0, "spam debug info for stringtable lookups");
	sub_1403358C0();
	sub_140223D30();
	sub_140464DE0();
	accessToSubscriberContent = Dvar_RegisterBool("accessToSubscriberContent", true, 0, "Whether to display the subscriber maps.");
	cl_modifiedDebugPlacement = Dvar_RegisterBool("cl_modifiedDebugPlacement", false, 0,
		"Modify the location of debug output (outside of safe area)");
}
