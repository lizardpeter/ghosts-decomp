// P0012: Store-only bridge. Absolute state locations are pinned by the package
// input hash; see docs/direct-connect.md for the disassembly evidence and limits.
#include "transport.h"
#include "profile.h"
#include "qcommon/cmd.h"
#include "qcommon/dvar.h"
void Dvar_SetBool(const dvar_t *, bool);
extern "C" __declspec(dllimport) void OutputDebugStringA(const char *);
extern "C" int Iw6DirectLoadStartupProfile();
extern "C" void Iw6DirectStartupMilestone(const char *text) { OutputDebugStringA(text); }
void Dvar_SetStringByName(const char *, const char *);

namespace
{
template<class T> T &State(unsigned long long address) { return *(T *)address; }
cmd_function_s connectCommand;
cmd_function_s listenCommand;
cmd_function_s stopCommand;
cmd_function_s playerCommand;
cmd_function_s hostCommand;
bool commandsRegistered;
int lastResult;
bool Identifier(const char *text, unsigned int maximum, unsigned int minimum)
{
    if (!text) return false;
    unsigned int count = 0;
    for (; text[count]; ++count)
    {
        const unsigned char c = (unsigned char)text[count];
        if (count >= maximum || !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '_')) return false;
    }
    return count >= minimum;
}
bool ServerRunning()
{
    const dvar_t *running = State<const dvar_t *>(0x146A7D6C0);
    return running && running->type == 0 && running->current.enabled;
}
bool LocalNetworkMode()
{
    const dvar_t *online = State<const dvar_t *>(0x1442B98C8);
    if (!online || online->type != 0) return false;
    // Reuse the engine's local-network admission/stats branch. This is gameplay
    // policy, not a claim of vendor authentication. Do not directly edit a dvar.
    Dvar_SetBool(online, false);
    return true;
}
}

extern "C" int Iw6DirectProfile() { return 1; }
extern "C" int Iw6DirectResult() { return lastResult; }

// The Store LUI CheckGameLicense callback at 140245440 only calls the GDK
// XStore license refresh and returns zero. Direct mode has no XStore context:
// keep the callback ABI and no-op rather than attempting a vendor query or
// reporting a fabricated successful license.
extern "C" int Iw6DirectNoXboxLicenseRefresh() { return 0; }

// P0024: Game-local multiplayer gate for the custom direct profile only.
// The Store entries 14054B1B0 and 14054B290 normally require an XUser, an
// XStore licence and Xbox privileges. Those vendor checks cannot describe a
// self-hosted local session. Never turn this into Xbox/retail eligibility.
// Require the configured local player and the engine's existing LAN branch.
// 0xC is the original not-signed-in/not-licensed reason for refusal.
extern "C" int Iw6DirectLocalPlayReady(int controller, unsigned int *reason)
{
    if (reason) *reason = 0xC;
    if (!reason || controller != 0 || !Iw6DirectPlayerId(0)) return 0;
    const dvar_t *online = State<const dvar_t *>(0x1442B98C8);
    if (!online || online->type != 0 || online->current.enabled) return 0;
    *reason = 0;
    return 1;
}

// Only called on the engine command thread, after normal local-client init.
// Result: 1 started, -1 bad endpoint, -2 inactive client, -3 disconnect first,
// -4 socket failure, -5 onlinegame dvar not initialized. This does not claim account authentication or map loading.
extern "C" int Iw6DirectBeginJoin(const char *endpoint)
{
    netadr_s peer;
    if (!Iw6DirectParse(endpoint, &peer, 0)) return lastResult = -1;
    if (!State<unsigned char>(0x143E96821)) return lastResult = -2;
    if (State<int>(0x143E96890) >= 3) return lastResult = -3;
    // Refuse an unconfigured player *before* changing onlinegame. An invalid
    // join/host request must not put the menu into LAN mode as a side effect.
    if (!Iw6DirectPlayerId(0)) return lastResult = -9;
    if (!LocalNetworkMode()) return lastResult = -5;
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
    OutputDebugStringA("IW6D:DIRECT_JOIN_CHALLENGE_READY");
    return lastResult = 1;
}

// Store SV_StartMap has an extra fourth boolean compared with the reference
// prototype. Call the reviewed original ABI, preserving asset/entitlement checks.
extern "C" int Iw6DirectHost(const char *bind, const char *map, const char *gametype)
{
    netadr_s address;
    if (!Iw6DirectParse(bind, &address, 1) || !Identifier(map, 63, 3) ||
        !Identifier(gametype, 31, 1)) return lastResult = -6;
    if (!State<unsigned char>(0x143E96821)) return lastResult = -2;
    if (State<int>(0x143E96890) >= 3 || ServerRunning()) return lastResult = -3;
    // Refuse an unconfigured player *before* changing onlinegame. An invalid
    // join/host request must not put the menu into LAN mode as a side effect.
    if (!Iw6DirectPlayerId(0)) return lastResult = -9;
    if (!LocalNetworkMode()) return lastResult = -5;
    if (!Iw6DirectOpen(bind, 1)) return lastResult = -4;
    Dvar_SetStringByName("g_gametype", gametype);
    Dvar_SetStringByName("ui_gametype", gametype);
    // Map startup may reject missing/unavailable content or fail before spawn.
    // Result 3 means only that the request was made, not that a game is ready.
    OutputDebugStringA("IW6D:DIRECT_MAP_START_REQUESTED");
    ((void (*)(LocalClientNum_t, const char *, bool, bool))0x1404BADC0)(LOCAL_CLIENT_0, map, true, false);
    return lastResult = 3;
}

namespace
{
void ConfigurePlayer()
{
    if (Cmd_Argc() != 3) { lastResult = -1; return; }
    if (State<int>(0x143E96890) >= 3 || ServerRunning()) { lastResult = -3; return; }
    if (!Iw6DirectPlayerConfigure(Cmd_Argv(1), Cmd_Argv(2))) { lastResult = -9; return; }
    const char *name = Iw6DirectPlayerName(0);
    char *cache = (char *)0x149D59D34;
    unsigned int i = 0;
    for (; name[i] && i < 31; ++i) cache[i] = name[i];
    cache[i] = 0;
    State<unsigned long long>(0x149D59D58) = Iw6DirectPlayerId(0);
    Dvar_SetStringByName("name", name);
    OutputDebugStringA("IW6D:LOCAL_PROFILE_CONFIGURED");
    lastResult = 4;
}
void Host()
{
    if (Cmd_Argc() != 4) { lastResult = -6; return; }
    Iw6DirectHost(Cmd_Argv(1), Cmd_Argv(2), Cmd_Argv(3));
}
void Connect()
{
    if (Cmd_Argc() != 2) { lastResult = -1; return; }
    Iw6DirectBeginJoin(Cmd_Argv(1));
}
void Listen()
{
    if (Cmd_Argc() != 2) { lastResult = -1; return; }
    if (State<int>(0x143E96890) >= 3) { lastResult = -3; return; }
    if (!LocalNetworkMode()) { lastResult = -5; return; }
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
    Cmd_AddCommandInternal("direct_player", ConfigurePlayer, &playerCommand);
    Cmd_AddCommandInternal("direct_host", Host, &hostCommand);
    commandsRegistered = true;
    OutputDebugStringA("IW6D:DIRECT_COMMANDS_REGISTERED");
    // Normal +commands can be held while assets/UI initialise. Read only the
    // launcher profile early; deferred engine commands retain their normal job.
    Iw6DirectLoadStartupProfile();
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
