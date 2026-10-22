// Build-facing ABI declarations for SDK methods whose implementation is not reconstructed.
// Large member-function return objects use the Win64 hidden output pointer after `this`.
// These declarations express that lowered ABI explicitly; they are not full SDK class layouts.
#pragma once
bool DwAddrHandleEqual(const void *left, const void *right)
    __asm__("??8bdAddrHandle@@QEBA_NAEBV0@@Z");
void *DwGetRealAddr(const void *handle, void *result)
    __asm__("?getRealAddr@bdAddrHandle@@QEBA?BVbdAddr@@XZ");
void *DwGetInAddr(const void *address, void *result)
    __asm__("?getInAddr@bdInetAddr@@QEBA?AVbdSockAddr@@XZ");
unsigned short DwGetPort(const void *address)
    __asm__("?getPort@bdAddr@@QEBAGXZ");
void DwDestroyInetAddr(void *address)
    __asm__("??1bdInetAddr@@QEAA@XZ");

// 14073ED40: identity accessor called between getRealAddr and getInAddr.
// The matcher also associates unrelated folded identity functions with this address;
// no original name has been established for this caller's accessor.
void *sub_14073ED40(void *address);
