// P0012: Store-only bridge. Absolute state locations are pinned by the package
// input hash; see docs/direct-connect.md for the disassembly evidence and limits.
#include "transport.h"
#include "qcommon/cmd.h"

namespace
{
template<class T> T &State(unsigned long long address) { return *(T *)address; }
cmd_function_s connectCommand;
cmd_function_s listenCommand;
cmd_function_s stopCommand;
bool commandsRegistered;
int lastResult;
}

extern "C" int Iw6DirectProfile() { return 1; }
extern "C" int Iw6DirectResult() { return lastResult; }

// Only called on the engine command thread, after normal local-client init.
// Result: 1 started, -1 bad endpoint, -2 inactive client, -3 disconnect first,
// -4 socket failure. This does not claim account authentication or map loading.
extern "C" int Iw6DirectBeginJoin(const char *endpoint)
{
    netadr_s peer;
    if (!Iw6DirectParse(endpoint, &peer, 0)) return lastResult = -1;
    if (!State<unsigned char>(0x143E96821)) return lastResult = -2;
    if (State<int>(0x143E96890) >= 3) return lastResult = -3;
    if (!Iw6DirectOpen("0.0.0.0:0", 0) || !Iw6DirectSelectPeer(endpoint))
    { Iw6DirectClose(); return lastResult = -4; }

    // The normal join initializer at 140311F70 uses these fields before entering
    // CL_CheckForResend (140311310). Do not manufacture a logged-in SDK object.
    State<netadr_s>(0x14416A10C) = peer;
    State<int>(0x14416A100) = State<int>(0x146B456A0); // qport used by netchan too
    State<int>(0x14416A11C) = -99999; // force the first challenge request
    State<int>(0x14416A120) = 0;      // retry count
    State<int>(0x14416A224) = 0;      // old challenge
    State<int>(0x143E96824) = 0;      // ordinary join, not a migration/demo
    State<unsigned int>(0x143E9688C) &= 1;
    State<int>(0x143E96A24) = 0;
    char *name = (char *)0x1441CB718;
    unsigned int i = 0;
    for (; endpoint[i] && i < 255; ++i) name[i] = endpoint[i];
    name[i] = 0;
    State<int>(0x143E96890) = 3;      // CA_CONNECTING, published last
    return lastResult = 1;
}

namespace
{
void Connect()
{
    if (Cmd_Argc() != 2) { lastResult = -1; return; }
    Iw6DirectBeginJoin(Cmd_Argv(1));
}
void Listen()
{
    if (Cmd_Argc() != 2) { lastResult = -1; return; }
    if (State<int>(0x143E96890) >= 3) { lastResult = -3; return; }
    lastResult = Iw6DirectOpen(Cmd_Argv(1), 1) ? 2 : -4;
}
void Stop()
{
    Iw6DirectClose();
    lastResult = 0;
    // Local client teardown still belongs to the engine's disconnect command.
}
}

extern "C" void Iw6DirectInit()
{
    // NET_Init runs before normal CL initialization; register commands here but
    // defer opening sockets and touching client state until a command executes.
    if (commandsRegistered) return;
    Cmd_AddCommandInternal("connect", Connect, &connectCommand);
    Cmd_AddCommandInternal("direct_listen", Listen, &listenCommand);
    Cmd_AddCommandInternal("direct_stop", Stop, &stopCommand);
    commandsRegistered = true;
}
extern "C" bool Iw6DirectSendPacket(int length, const void *data, netadr_s to)
{
    return Iw6DirectSend(length, data, &to) != 0;
}
extern "C" int Iw6DirectGetPacket(netadr_s *from, msg_t *message)
{
    return Iw6DirectReceive(from, message);
}
extern "C" int Iw6DirectCompare(const netadr_s *a, const netadr_s *b)
{
    // Use endpoints, never DW handle equality. In particular two invalid handle
    // indices must not make unrelated IPs or ports compare equal.
    return Iw6DirectSameAddress(a, b, 1);
}
extern "C" int Iw6DirectHandleState(unsigned int)
{
    netadr_s peer;
    return Iw6DirectPeer(&peer) ? 1 : 0;
}
extern "C" int Iw6DirectAddressState(const netadr_s *address)
{
    netadr_s peer;
    return Iw6DirectPeer(&peer) && Iw6DirectSameAddress(&peer, address, 1) ? 1 : 0;
}
extern "C" void Iw6DirectIgnoreHandle()
{
    // Startup-only replacement: no DW handles are created by this transport.
    // Never index DW's table with a direct address's FFFFFFFF sentinel.
}

// Source-linked callers must use the same boundary as patched EXE callers.
void NET_Init() { Iw6DirectInit(); }
bool Sys_SendPacket(int length, const void *data, netadr_s to)
{
    return Iw6DirectSendPacket(length, data, to);
}
int Sys_GetPacket(netadr_s *from, msg_t *message)
{
    return Iw6DirectGetPacket(from, message);
}
int sub_1405A8980(const netadr_s *address) { return Iw6DirectAddressState(address); }
void sub_1405A9E50(const netadr_s *) {}
void sub_1405A87E0(const netadr_s *) {}
