// qcommon/common.cpp (Store build): the event loop.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. The PS4 server's
// Com_EventLoop (PDB, qcommon/common.cpp:4367) keeps only the console half; the client half follows Black Ops'
// Com_EventLoop and Com_ClientPacketEvent (server PDB, common.cpp:3128 and 2937, lineage), which the Store build
// inlines into one function.
//
// Com_EventLoop runs twice per Com_Frame (1404605F5 at the top, 140460948 after SV_Frame) and once after Com_Init
// (140463320). It drains the event queue first, in order: keys and mouse buttons go straight to CL_KeyEvent, characters
// to CL_CharEvent, console lines to the command buffer. Only then does it read packets: loopback, deferred, and from
// the network unless a listen server runs (which reads them itself). docs/input.md, "The key path".

#include "client/client.h"
#include "qcommon/cmd.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"
#include "win32/win_local.h"

#include "iw6_static.h"
#define IW6_SOURCE "qcommon/common.cpp"

extern "C" void free(void *ptr);

extern const dvar_t *com_sv_running;

// client
void CL_KeyEvent(LocalClientNum_t localClientNum, int key, int down, unsigned int time);  // client/cl_keys.cpp
void CL_CharEvent(LocalClientNum_t localClientNum, int key);                              // client/cl_keys.cpp
bool CL_PacketEvent(LocalClientNum_t localClientNum, netadr_s from, msg_t *msg, int time);  // client_mp/cl_main_mp.cpp

// Black Ops' Com_ClientPacketEvent (qcommon/common.cpp:2937), with its Com_PacketEventLoop and
// Com_DispatchClientPacketEvent; all inlined into Com_EventLoop in the Store build
static void Com_ClientPacketEvent()
{
	LargeLocal msgBuf_large_local(0x20000);
	unsigned char *msgBuf = (unsigned char *)msgBuf_large_local.GetBuf();
	msg_t netmsg;
	netadr_s adr;

	MSG_Init(&netmsg, msgBuf, 0x20000);
	while (NET_GetLoopPacket(NS_CLIENT1, &adr, &netmsg))
		CL_PacketEvent(LOCAL_CLIENT_0, adr, &netmsg, Sys_Milliseconds());
	while (NET_GetDeferredClientPacket(&adr, &netmsg))
		CL_PacketEvent(LOCAL_CLIENT_0, adr, &netmsg, Sys_Milliseconds());
	if (!com_sv_running->current.enabled)
	{
		while (NET_GetClientPacket(&adr, &netmsg))
			CL_PacketEvent(LOCAL_CLIENT_0, adr, &netmsg, Sys_Milliseconds());
	}
}

// Store 140460130 (PS4 PDB Com_EventLoop, qcommon/common.cpp:4367; client half from Black Ops)
void Com_EventLoop()
{
	while (true)
	{
		const sysEvent_t ev = Sys_GetEvent();
		switch (ev.evType)
		{
		case SE_NONE:
			Com_ClientPacketEvent();
			return;
		case SE_KEY:
			CL_KeyEvent(LOCAL_CLIENT_0, ev.evValue, ev.evValue2, ev.evTime);
			break;
		case SE_CHAR:
			CL_CharEvent(LOCAL_CLIENT_0, ev.evValue);
			break;
		case SE_CONSOLE:
			Cbuf_AddText(LOCAL_CLIENT_0, (const char *)ev.evPtr);
			free(ev.evPtr);  // Com_FreeEvent, inlined (the PS4 server's is Z_FreeInternal)
			Cbuf_AddText(LOCAL_CLIENT_0, "\n");
			break;
		default:
			Com_Error(ERR_FATAL, "\x1f" "Com_EventLoop: bad event type %i", ev.evType);
			break;
		}
	}
}

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

// Store 140460F80 (PS4 PDB Com_InitDvars, qcommon/common.cpp:5328). com_maxfps: default 85, 0..100, so the cap is
// 10 ms a frame at most, or none at all with 0 (Com_Frame then still takes at least 1 ms a frame; docs/fps.md).
void Com_InitDvars()
{
	com_dedicated_dhclient = Dvar_RegisterBool("dedicated_dhclient", false, 0, "True if we're a client playing on a DH server");
	com_maxfps = Dvar_RegisterInt("com_maxfps", 85, 0, 100, 0, "Cap frames per second");
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
// ==== END dvars ====
