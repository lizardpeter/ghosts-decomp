// dw/dwutils.cpp: PS4 PDB line 440; Store 1405DA910-1405DA92E.
// The Store disassembly calls the bdNetImpl singleton accessor, returns null when
// it fails, and otherwise tail-calls bdNetImpl::getSocketRouter.
#include "dw/dwnet.h"

class bdNetImpl
{
public:
    bdSocketRouter *getSocketRouter();
};
template <typename T> class bdSingleton
{
public:
    static T *getInstance();
};

bdSocketRouter *dwGetSocketRouter()
{
    bdNetImpl *net = bdSingleton<bdNetImpl>::getInstance();
    return net ? net->getSocketRouter() : nullptr;
}

#include "dw/sdk_abi.h"

// Store 1405DA000: obtain the router's address map, with both null gates.
bdAddressMap *dwGetAddressMap()
{
    bdNetImpl *net = bdSingleton<bdNetImpl>::getInstance();
    if (!net)
        return nullptr;
    bdSocketRouter *router = net->getSocketRouter();
    return router ? (bdAddressMap *)DwGetAddressMap(router) : nullptr;
}

#include <iw6_static.h>
#include "dw/logon_sdk_abi.h"
#define IW6_SOURCE "dw/dwutils.cpp"
IW6_STATIC unsigned char authBusy[2] IW6_AT("", "authBusy");
IW6_STATIC void *authClient IW6_AT("", "authClient");

// Store 1405D9F10: either in-flight auth flag blocks another login start.
bool sub_1405D9F10()
{
    return authBusy[0] || authBusy[1];
}

// Store 1405D9F30: destruction and deallocation both use the captured pointer.
void sub_1405D9F30()
{
    void *auth = authClient;
    if (auth)
    {
        sub_14074ACF0(auth);
        DwLogonDeallocate(auth);
        authClient = nullptr;
    }
}

// Store 1405DA070: lazy auth-client construction, distinct from starting login.
void *sub_1405DA070(const char *host, unsigned short port, unsigned int title)
{
    void *auth = authClient;
    if (!auth)
    {
        void *storage = DwLogonAllocate(0x3580);
        auth = storage ? sub_14074ABA0(storage, title, host, port) : nullptr;
        authClient = auth;
    }
    return auth;
}

#include "dw/dwservices.h"
#include "dw/services_state.h"
#include "dw/services_sdk_abi.h"
#include "dw/dwlogon_state.h"

// Store 1405D9FD0: scan the single Store controller slot for an active lobby.
bdLobbyService *dwGetActiveLobbyService()
{
    return (bdLobbyService *)dwLogonUnknown;
}

// Store 1405DA470: only first construction registers a handler, for controllers 0..3.
// The original rereads the cache after the handler callback.
bdLobbyService *dwGetLobbyService(int controller)
{
    if (!dwLobbyServiceCache)
    {
        void *storage = DwLogonAllocate(0x538);
        dwLobbyServiceCache = storage ? (bdLobbyService *)DwServicesLobbyConstruct(storage) : nullptr;
        if (dwLobbyServiceCache && controller >= 0 && controller <= 3)
            DwServicesRegisterHandler(dwLobbyServiceCache, dwLobbyEventHandlers[controller]);
    }
    return dwLobbyServiceCache;
}

// Store 1405DAA30: readiness is specifically SDK state 2.
bool dwIsBdNetReady()
{
    void *net = DwNetInstance();
    return net && sub_1407679F0(net) == 2;
}

// Store 1405DA130/190: these getters do not require a connected lobby.
bdContentStreaming *dwGetContentStreaming(int controller)
{
    bdLobbyService *lobby = dwGetLobbyService(controller);
    return lobby ? (bdContentStreaming *)DwServicesContent(lobby) : nullptr;
}

bdDML *dwGetDML(int controller)
{
    bdLobbyService *lobby = dwGetLobbyService(controller);
    return lobby ? (bdDML *)DwServicesDML(lobby) : nullptr;
}

// Store 1405DA150/1D0: these getters admit only SDK connection state 2.
bdCounter *dwGetCounter(int controller)
{
    bdLobbyService *lobby = dwGetLobbyService(controller);
    return lobby && DwLogonLobbyStatus(lobby) == 2 ? (bdCounter *)DwServicesCounter(lobby) : nullptr;
}

bdGroup *dwGetGroup(int controller)
{
    bdLobbyService *lobby = dwGetLobbyService(controller);
    return lobby && DwLogonLobbyStatus(lobby) == 2 ? (bdGroup *)DwServicesGroup(lobby) : nullptr;
}

// Store 1405DBF40: process a captured lobby, then reacquire it before content work.
void dwLobbyPump(int controller)
{
    dwLobbyActivity = 0;
    bdLobbyService *lobby = dwGetLobbyService(controller);
    if (lobby)
    {
        DwServicesLobbyPump(lobby);
        if (DwLogonLobbyStatus(lobby) == 2)
        {
            dwLobbyActivity = 14;
            LiveAntiCheat_Pump(controller);
            sub_1405D6E60(controller);
            lobby = dwGetLobbyService(controller);
            if (lobby)
            {
                void *content = DwServicesContent(lobby);
                if (content && sub_14045CFF0(controller))
                    DwServicesContentPump(content);
            }
        }
    }
}

// Store 1405DBFD0: unchecked controller index, as in the original.
void sub_1405DBFD0(int controller)
{
    dwLogonEntries[controller].state = 0;
}

// Store 1405DBFF0: clear the first flag only; the second flag/reason are retained.
void sub_1405DBFF0()
{
    dwDisconnectState = 0;
    authBusy[0] = 0;
}

void sub_1405DC010()
{
    authBusy[0] = 1;
    Live_DemonwareDisconnectCleanup(0);
}

void sub_1405DC020(unsigned int reason)
{
    dwDisconnectReason = reason;
    authBusy[1] = 1;
    Live_DemonwareDisconnectCleanup(0);
}

#include "dw/reporting.h"
// Lowered SDK forwarding contracts, not complete SDK class definitions.
unsigned char sub_140748BB0(void *lobby);
void *sub_1407463D0(void *lobby);
void **sub_140749A50(void *log, void **task, const char *text, unsigned int size,
                   unsigned int category, void *optional);

int sub_1405D6A90(const char *text, unsigned int category)
{
    void *lobby = dwGetActiveLobbyService();
    if (!lobby || !sub_140748BB0(lobby))
        return 0;
    void *log = sub_1407463D0(lobby);
    unsigned long long length = 0;
    while (text[length])
        ++length;
    void *temporary;
    void **returned = sub_140749A50(log, &temporary, text,
                                  (unsigned int)(length + 1), category, nullptr);
    void *captured = *returned;
    if (temporary)
    {
        int old = __atomic_fetch_add((int *)((char *)temporary + 8), -1, __ATOMIC_SEQ_CST);
        if (old == 1 && temporary)
            ((void (*)(void *, unsigned int))(*(void ***)temporary)[0])(temporary, (unsigned int)old);
    }
    return captured ? 1 : 0;
}
