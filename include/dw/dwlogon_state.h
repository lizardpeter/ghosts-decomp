// Observed Store storage and lowered SDK boundary, not complete SDK class layouts.
#pragma once
struct DwLogonEntry
{
    unsigned int state;
    int retryDelay;
    unsigned int attempts;
    unsigned int lastAttempt;
    unsigned char unknown[8];
};
static_assert(sizeof(DwLogonEntry) == 24, "Store logon entry stride");
extern DwLogonEntry dwLogonEntries[] __asm__("iw6s@dw/dwlogon-win.cpp@@logonEntries");
extern unsigned char dwLogonSuppressed __asm__("iw6s@dw/dwlogon-win.cpp@@logonSuppressed");
extern unsigned long long dwLogonUnknown __asm__("iw6s@dw/dwlogon-win.cpp@@logonUnknown");
extern void *dwAuthResolver __asm__("iw6s@dw/dwlogon-win.cpp@@authResolver");
extern void *dwLobbyResolver __asm__("iw6s@dw/dwlogon-win.cpp@@lobbyResolver");
extern unsigned char dwAuthAddress[144] __asm__("iw6s@dw/dwlogon-win.cpp@@authAddress");
extern unsigned char dwLobbyAddress[144] __asm__("iw6s@dw/dwlogon-win.cpp@@lobbyAddress");
