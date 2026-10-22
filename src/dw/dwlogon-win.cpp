// Store authentication/lobby logon flow. Unknown names retain their observed VAs.
#include "dw/dwlogon.h"
#include "dw/dwlogon_state.h"
#include "qcommon/qcommon.h"

bool sub_1401A1A10(int controller);
bool sub_1405D9F10();
int sub_1405F3D10(unsigned int attempt, int maximum);
extern "C" int _wcsicmp(const wchar_t *, const wchar_t *);

// Store 14019A930: 0 offline/suppressed, 1 pending, 2 state 14.
int sub_14019A930(int controller)
{
    if (!dwLogonSuppressed && dwLogonEntries[controller].state)
        return dwLogonEntries[controller].state == 14 ? 2 : 1;
    return 0;
}

// Store supports one controller here. Exclude that controller from the busy test.
bool sub_14019A960(int controller)
{
    const unsigned int state = dwLogonEntries[0].state;
    return controller != 0 && state - 4 <= 9 && state != 8;
}

void dwLogOnStart(int controller)
{
    if (!sub_1401A1A10(controller) || sub_1405D9F10())
        return;
    const unsigned int now = (unsigned int)Sys_Milliseconds();
    DwLogonEntry *entry = &dwLogonEntries[controller];
    const int elapsed = (int)(now - entry->lastAttempt) / 1000;
    unsigned int attempts = 0;
    if (entry->attempts)
    {
        if (elapsed <= 120)
        {
            int delay = entry->retryDelay;
            if (!delay)
            {
                delay = sub_1405F3D10(entry->attempts, 60);
                entry->retryDelay = delay;
            }
            if (elapsed < delay)
            {
                dwLogonSuppressed = 0;
                return;
            }
            attempts = entry->attempts;
        }
    }
    entry->retryDelay = 0;
    entry->attempts = attempts + 1;
    entry->lastAttempt = now;
    entry->state = 1;
    dwLogonSuppressed = 0;
}

// Store 14019AE70: clears exactly 24 bytes beginning eight bytes before entries.
void sub_14019AE70()
{
    dwLogonUnknown = 0;
    dwLogonEntries[0].state = 0;
    dwLogonEntries[0].retryDelay = 0;
    dwLogonEntries[0].attempts = 0;
    dwLogonEntries[0].lastAttempt = 0;
}

void sub_14019AE90()
{
    if (dwAuthResolver)
    {
        ((void (*)(void *, unsigned int))(*(void ***)dwAuthResolver)[0])(dwAuthResolver, 1);
        dwAuthResolver = nullptr;
    }
    if (dwLobbyResolver)
    {
        ((void (*)(void *, unsigned int))(*(void ***)dwLobbyResolver)[0])(dwLobbyResolver, 1);
        dwLobbyResolver = nullptr;
    }
}

const char *dwSelectAuthAddress()
{
    if (!_wcsicmp(L"RETAIL", L"RETAIL"))
        return "auth3.prod.demonware.net";
    if (_wcsicmp(L"RETAIL", L"CERT"))
    {
        if (!_wcsicmp(L"RETAIL", L"ACNA.30"))
            return "auth3.dev.demonware.net";
        _wcsicmp(L"RETAIL", L"INFN.99");
    }
    return "auth3.cert.demonware.net";
}

#include "dw/logon_sdk_abi.h"

// Store 14019A9A0: one state-machine step, followed by terminal cleanup.
void dwLogOnComplete(int controller)
{
    DwLogonEntry *entry = &dwLogonEntries[controller];
    const unsigned int previous = entry->state;
    unsigned char address[144];
    DwLogonInetConstruct(address);
    entry->state = 0;
    switch (previous)
    {
    case 3:
    {
        const int result = sub_1405DA210(dwSelectAuthAddress(), &dwAuthResolver, address);
        if (!result)
        {
            entry->state = 3;
            break;
        }
        if (result == 2)
            break;
        DwLogonInetSet(dwAuthAddress, address);
        // fall through to the same-controller exclusion check
    }
    case 1:
    case 2:
    case 8:
        entry->state = (sub_14019A960(controller) ^ 1) + 8;
        break;
    case 9:
    {
        void *auth = sub_1405DA070(dwSelectAuthAddress(), 443, 2510);
        if (auth && !sub_14074ADA0(auth))
            entry->state = sub_140749D20(auth, controller) ? 10 : 0;
        break;
    }
    case 10:
    {
        void *auth = sub_1405DA070(dwSelectAuthAddress(), 443, 2510);
        if (!auth || sub_14074ADA0(auth))
            entry->state = 10;
        else
            entry->state = sub_14074AD90(auth) == 700 ? 11 : 0;
        break;
    }
    case 11:
    {
        void *auth = sub_1405DA070(dwSelectAuthAddress(), 443, 2510);
        if (sub_14074ADA0(auth))
        {
            entry->state = 11;
            break;
        }
        if (sub_14074AD90(auth) != 700)
            break;
        const char *host;
        if (!_wcsicmp(L"RETAIL", L"RETAIL"))
            host = "lsg.2510.prod.demonware.net";
        else
        {
            if (_wcsicmp(L"RETAIL", L"CERT"))
            {
                if (!_wcsicmp(L"RETAIL", L"ACNA.30"))
                    host = "lsg.2505.dev.demonware.net";
                else
                {
                    _wcsicmp(L"RETAIL", L"INFN.99");
                    host = "lsg.2505.cert.demonware.net";
                }
            }
            else
                host = "lsg.2505.cert.demonware.net";
        }
        const int result = sub_1405DA210(host, &dwLobbyResolver, address);
        if (!result)
        {
            entry->state = 11;
            break;
        }
        if (result == 2)
            break;
        DwLogonInetSet(dwLobbyAddress, address);
        void *lobby = DwLogonLobby(controller);
        unsigned char endpoint[144];
        DwLogonAddrConstruct(endpoint, dwLobbyAddress, 3074);
        if (lobby)
        {
            DwLogonDisconnect(lobby);
            const void *authInfo = sub_14074AD80(auth);
            unsigned char copy[144];
            void *argument = DwLogonAddrCopy(copy, endpoint);
            if (DwLogonConnect(lobby, argument, authInfo, true))
                entry->state = 13;
        }
        DwLogonInetDestroy(endpoint);
        break;
    }
    case 13:
    {
        void *lobby = DwLogonLobby(controller);
        if (lobby)
        {
            DwLogonPump(controller);
            const int status = DwLogonLobbyStatus(lobby);
            if (status == 2)
            {
                if (DwLogonNetReady())
                {
                    entry->state = 14;
                    sub_1405F4820(controller);
                }
            }
            else if (status == 1)
                entry->state = 13;
        }
        break;
    }
    }
    if (entry->state == 0 || entry->state == 14)
    {
        sub_14019AE90();
        sub_1405D9F30();
    }
    if (!entry->state)
    {
        void *lobby = DwLogonLobby(controller);
        if (lobby)
            DwLogonDisconnect(lobby);
    }
    DwLogonInetDestroy(address);
}
