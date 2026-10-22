// dw/dwnet.cpp: Store-build packet submission and address-handle bookkeeping.
// Reconstructed from iw6mp64_MSStore_ship disassembly; unknown names remain sub_<VA>.
// Partial layouts below describe only observed fields, not complete Demonware SDK types.
#include <string.h>
#include <iw6_static.h>
#include "qcommon/qcommon.h"

#define IW6_SOURCE "dw/dwnet.cpp"

struct DwHandleEntry
{
    void *handle;
    unsigned int lifetime;
    unsigned int unknown;
};
static_assert(sizeof(DwHandleEntry) == 16, "Store address table stride");
IW6_STATIC int localHandleIndex IW6_AT("", "localHandleIndex");
IW6_STATIC DwHandleEntry addressHandles[] IW6_AT("", "addressHandles");

// Router accessor and address refresh: original names/types are not identified yet.
void *sub_1405DA910();
void sub_1405A9A90(int index, void *router);
extern "C" long _InterlockedIncrement(long volatile *addend);
extern "C" long _InterlockedExchangeAdd(long volatile *addend, long value);

// Reconstruction helpers for the observed virtual calls and intrusive reference count at +8.
namespace
{
inline void Retain(void *handle)
{
    _InterlockedIncrement((long volatile *)((unsigned char *)handle + 8));
}
inline void Release(void *handle)
{
    if (_InterlockedExchangeAdd((long volatile *)((unsigned char *)handle + 8), -1) == 1)
        ((void (*)(void *, unsigned int))(*(void ***)handle)[0])(handle, 1);
}
inline int RouterState(void *router, void **handle)
{
    return ((int (*)(void *, void **))(*(void ***)router)[9])(router, handle);
}
inline int RouterSend(void *router, void **handle, const void *data, unsigned int length)
{
    return ((int (*)(void *, void **, const void *, unsigned int))(*(void ***)router)[10])
        (router, handle, data, length);
}
}

// Store 1405A8AD0: the address-table index reserved for this machine.
unsigned int sub_1405A8AD0()
{
    return localHandleIndex;
}

// Store 1405A9C80. Sys_SendPacket supplies its checksum-framed bytes here.
// Router methods consume the temporary handle references passed to them by value.
int dwSendTo(unsigned int length, const void *data, netadr_s to)
{
    Sys_EnterCriticalSection((CriticalSection)0x21);
    void *handle = NULL;
    void *router;
    const netadr_s *adr = &to;
    // The original also accepts a null ABI-level pointer for this by-value 16-byte struct.
    // Ordinary C++ callers always supply a struct; no additional source-level null branch is needed.
    const int index = (int)adr->addrHandleIndex;
    Sys_EnterCriticalSection((CriticalSection)0x21);
    if (index >= 0 && index < localHandleIndex)
    {
        sub_1405A9A90(index, NULL);
        handle = addressHandles[index].handle;
        if (handle)
            Retain(handle);
    }
    Sys_LeaveCriticalSection((CriticalSection)0x21);
    router = sub_1405DA910();
    int result = -7;
    if (handle && router)
    {
        void *stateHandle = handle;
        Retain(handle);
        const int state = RouterState(router, &stateHandle);
        if (state == 2)
        {
            if (length <= 1262)
            {
                unsigned char packet[1264];
                *(unsigned short *)packet = (unsigned short)length;
                memcpy(packet + 2, data, length);
                void *sendHandle = handle;
                Retain(handle);
                result = RouterSend(router, &sendHandle, packet, length + 2);
            }
            else
                result = -6;
        }
        else
            result = state == 1 ? 0 : -10;
    }
    Sys_LeaveCriticalSection((CriticalSection)0x21);
    if (handle)
        Release(handle);
    return result;
}

// Store 1405A9E50: refresh a nonlocal handle's lifetime. No bounds check in the original.
void sub_1405A9E50(const netadr_s *adr)
{
    if ((int)adr->addrHandleIndex != localHandleIndex)
    {
        Sys_EnterCriticalSection((CriticalSection)0x21);
        addressHandles[adr->addrHandleIndex].lifetime = 7200;
        Sys_LeaveCriticalSection((CriticalSection)0x21);
    }
}
