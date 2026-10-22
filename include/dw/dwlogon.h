#pragma once

// PS4 PDB DWOnlineStatus; Store DW_Frame consumes the same 32-bit result.
enum DWOnlineStatus
{
    DW_LIVE_DISCONNECTED = 0,
    DW_LIVE_CONNECTING = 1,
    DW_LIVE_CONNECTED = 2
};

void dwLogOnStart(int controller);
void dwLogOnComplete(int controller);
const char *dwSelectAuthAddress();
DWOnlineStatus dwGetLogOnStatus(int controller);
bool sub_14019A960(int controller);
void sub_14019AE70();
void sub_14019AE90();
void DW_Frame(int controller);
void sub_1405D3DC0(unsigned char inhibit);
