// Store 1405D3D40, PS4 PDB dw/dwframe.cpp: the per-frame backend login driver.
#include <iw6_static.h>
#include "dw/dwlogon.h"
#include "dw/logon_sdk_abi.h"
#define IW6_SOURCE "dw/dwframe.cpp"
IW6_STATIC unsigned char inhibitLogon IW6_AT("", "inhibitLogon");
int sub_1405F47D0();
void sub_1405F4630(int controller);

void DW_Frame(int controller)
{
    if (sub_1405F47D0())
        return;
    const int status = dwGetLogOnStatus(controller);
    if (status == 0)
    {
        if (!inhibitLogon)
            dwLogOnStart(controller);
    }
    else if (status == 1)
        dwLogOnComplete(controller);
    else if (status == 2)
    {
        DwLogonPump(controller);
        sub_1405F4630(controller);
    }
    dwGetLogOnStatus(controller);
}

// Store 1405D3DC0: update the automatic-logon inhibit byte verbatim.
void sub_1405D3DC0(unsigned char inhibit)
{
    inhibitLogon = inhibit;
}
