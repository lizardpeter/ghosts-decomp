// P0005: disable the reconstructed vendor auth/lobby login entry points.
// Source replacement only; other Xbox/GDK and transport paths have separate work ahead.
#include "dw/dwlogon.h"
#include "dw/dwlogon_state.h"

namespace
{
void SetOffline(int controller)
{
    DwLogonEntry *entry = &dwLogonEntries[controller];
    entry->state = 0;
    entry->retryDelay = 0;
    entry->attempts = 0;
    entry->lastAttempt = 0;
    dwLogonSuppressed = 0;
}
}

void dwLogOnStart(int controller)
{
    SetOffline(controller);
}

void dwLogOnComplete(int controller)
{
    SetOffline(controller);
}

DWOnlineStatus dwGetLogOnStatus(int controller)
{
    return DW_LIVE_DISCONNECTED;
}

bool sub_14019A960(int controller)
{
    return false;
}

// Block direct callers too: no cached vendor client is returned or constructed.
void *sub_1405DA070(const char *host, unsigned short port, unsigned int title)
{
    return nullptr;
}

// Block the per-frame driver too, before any vendor state/pump callbacks.
void DW_Frame(int controller)
{
    SetOffline(controller);
}
