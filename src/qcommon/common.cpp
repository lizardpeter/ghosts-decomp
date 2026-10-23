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
