// Win64 ABI calls observed in the Store login path. SDK layouts remain opaque.
#pragma once
void *DwLogonInetConstruct(void *out) __asm__("??0bdInetAddr@@QEAA@XZ");
void DwLogonInetDestroy(void *address) __asm__("??1bdInetAddr@@QEAA@XZ");
void DwLogonInetSet(void *address, const void *other) __asm__("?set@bdInetAddr@@QEAAXAEBV1@@Z");
// Store has the hostname as its first argument, unlike the reference match's prototype.
int sub_1405DA210(const char *host, void **resolver, void *address);
void *sub_1405DA070(const char *host, unsigned short port, unsigned int title);
int sub_14074ADA0(void *auth);
bool sub_140749D20(void *auth, int controller);
int sub_14074AD90(void *auth);
const void *sub_14074AD80(void *auth);
void sub_1405D9F30();
void *DwLogonLobby(int controller) __asm__("?dwGetLobbyService@@YAPEAVbdLobbyService@@H@Z");
void *DwLogonAddrConstruct(void *out, const void *address, unsigned short port)
    __asm__("??0bdAddr@@QEAA@AEBVbdInetAddr@@G@Z");
void *DwLogonAddrCopy(void *out, const void *other) __asm__("??0bdAddr@@QEAA@AEBV0@@Z");
void DwLogonDisconnect(void *lobby) __asm__("?disconnect@bdLobbyService@@QEAAXXZ");
bool DwLogonConnect(void *lobby, void *address, const void *authInfo, bool enable)
    __asm__("?connect@bdLobbyService@@QEAA_NVbdAddr@@PEBVbdAuthInfo@@_N@Z");
void DwLogonPump(int controller) __asm__("?dwLobbyPump@@YAXH@Z");
int DwLogonLobbyStatus(void *lobby) __asm__("?getStatus@bdLobbyService@@QEAA?AW4Status@bdLobbyConnection@@XZ");
bool DwLogonNetReady() __asm__("?dwIsBdNetReady@@YA_NXZ");
void sub_1405F4820(int controller);
void *sub_14074ABA0(void *storage, unsigned int title, const char *host, unsigned short port);
void sub_14074ACF0(void *auth);
void *DwLogonAllocate(unsigned long long size) __asm__("?allocate@bdMemory@@SAPEAX_K@Z");
void DwLogonDeallocate(void *storage) __asm__("?deallocate@bdMemory@@SAXPEAX@Z");
