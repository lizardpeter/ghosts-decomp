// P0006: keep the vendor lobby/service boundary unavailable in the enhanced build.
#include "dw/dwservices.h"
#include "dw/services_state.h"

bdLobbyService *dwGetActiveLobbyService()
{
    return nullptr;
}

bdLobbyService *dwGetLobbyService(int controller)
{
    return nullptr;
}

bdContentStreaming *dwGetContentStreaming(int controller)
{
    return nullptr;
}

bdCounter *dwGetCounter(int controller)
{
    return nullptr;
}

bdDML *dwGetDML(int controller)
{
    return nullptr;
}

bdGroup *dwGetGroup(int controller)
{
    return nullptr;
}

void dwLobbyPump(int controller)
{
    dwLobbyActivity = 0;
}
