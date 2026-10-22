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
