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

void *DwGetAddressMap(void *router)
    __asm__("?getAddressMap@bdSocketRouter@@QEAAPEAVbdAddressMap@@XZ");
void *DwGetEndpointCommonAddr(const void *endpoint, void *result)
    __asm__("?getCommonAddr@bdEndpoint@@QEBA?AV?$bdReference@VbdCommonAddr@@@@XZ");
bool DwFindAddrHandle(const void *map, void *commonAddrRef, const void *securityID, void *resultRef)
    __asm__("?findAddrHandle@bdAddressMap@@QEBA_NV?$bdReference@VbdCommonAddr@@@@AEBVbdSecurityID@@AEAV?$bdReference@VbdAddrHandle@@@@@Z");
// Store 140741840: returns endpoint+8 in the refresh caller; name not established.
void *sub_140741840(void *endpoint);

void *DwGetLocalCommonAddr(void *result)
    __asm__("?dwGetLocalCommonAddr@@YA?AV?$bdReference@VbdCommonAddr@@@@XZ");
void *DwGlobalAddressMap() __asm__("?dwGetAddressMap@@YAPEAVbdAddressMap@@XZ");
void *DwAllocate(unsigned long long size) __asm__("?allocate@bdMemory@@SAPEAX_K@Z");
void *DwConstructCommonAddr(void *storage) __asm__("??0bdCommonAddr@@QEAA@XZ");
bool DwDeserializeCommonAddr(void *address, void *localReference, const unsigned char *serialized)
    __asm__("?deserialize@bdCommonAddr@@QEAA_NV?$bdReference@VbdCommonAddr@@@@QEBE@Z");
bool DwIsLoopbackCommonAddr(const void *address) __asm__("?isLoopback@bdCommonAddr@@QEBA_NXZ");
bool DwGetAddrHandle(void *map, void *commonReference, const void *securityID, void *resultReference)
    __asm__("?getAddrHandle@bdAddressMap@@QEAA_NV?$bdReference@VbdCommonAddr@@@@AEBVbdSecurityID@@AEAV?$bdReference@VbdAddrHandle@@@@@Z");
void *DwNetInstance() __asm__("?getInstance@?$bdSingleton@VbdNetImpl@@@@SAPEAVbdNetImpl@@XZ");
void *sub_1407679D0(void *net);  // returns net+8; conversion reads its port at +2
