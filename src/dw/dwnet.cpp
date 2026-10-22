// dw/dwnet.cpp: Store-build packet submission and address-handle bookkeeping.
// Reconstructed from iw6mp64_MSStore_ship disassembly; unknown names remain sub_<VA>.
// Partial layouts below describe only observed fields, not complete Demonware SDK types.
#include <string.h>
#include <iw6_static.h>
#include "qcommon/qcommon.h"
#include "dw/dwnet.h"
#include "dw/sdk_abi.h"

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
    void *handle = nullptr;
    void *router;
    const netadr_s *adr = &to;
    // The original checks its ABI-level aggregate pointer for null; ordinary C++ callers
    // always supply the by-value struct. Null aggregate pointers are outside this source contract.
    const int index = (int)adr->addrHandleIndex;
    Sys_EnterCriticalSection((CriticalSection)0x21);
    if (index >= 0 && index < localHandleIndex)
    {
        dwSanityCheckAddressHandle(index, nullptr);
        handle = addressHandles[index].handle;
        if (handle)
            Retain(handle);
    }
    Sys_LeaveCriticalSection((CriticalSection)0x21);
    router = dwGetSocketRouter();
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

// Store 1405A8980: maps the router's connection state to the game's task status.
// Original name unknown. A local address is complete without consulting the router.
int sub_1405A8980(const netadr_s *adr)
{
    const int index = (int)adr->addrHandleIndex;
    Sys_EnterCriticalSection((CriticalSection)0x21);
    if (index == localHandleIndex)
    {
        Sys_LeaveCriticalSection((CriticalSection)0x21);
        return 1;
    }
    void *router = dwGetSocketRouter();
    void *handle = nullptr;
    Sys_EnterCriticalSection((CriticalSection)0x21);
    if (index >= 0 && index < localHandleIndex)
    {
        dwSanityCheckAddressHandle(index, nullptr);
        handle = addressHandles[index].handle;
        if (handle)
            Retain(handle);
    }
    Sys_LeaveCriticalSection((CriticalSection)0x21);
    int result = 2;
    if (router && handle)
    {
        void *stateHandle = handle;
        Retain(handle);
        const int state = RouterState(router, &stateHandle);
        if (state == 1)
            result = 0;
        else if (state == 2)
            result = 1;
    }
    Sys_LeaveCriticalSection((CriticalSection)0x21);
    if (handle)
        Release(handle);
    return result;
}

bool dwAddrIndexToAddrString(int index, char *const buffer, unsigned long long size);

// Store 1405A9EA0 (PS4 PDB dw/dwnet.cpp: dwUnregisterAddrHandle).
// Router slot +0x38 borrows the table entry; unlike send/state it does not consume
// a temporary reference. It runs before the game takes the table's lock.
void dwUnregisterAddrHandle(unsigned int index)
{
    char address[32];
    dwAddrIndexToAddrString((int)index, address, sizeof(address));
    void *router = dwGetSocketRouter();
    DwHandleEntry *entry = &addressHandles[index];
    if (router && entry->handle)
    {
        ((void (*)(void *, void **))(*(void ***)router)[7])(router, &entry->handle);
        ((void (*)(void *))(*(void ***)router)[4])(router);
    }
    Sys_EnterCriticalSection((CriticalSection)0x21);
    if (entry->handle)
        Release(entry->handle);
    entry->handle = nullptr;
    entry->lifetime = 0;
    entry->unknown = 0;
    Sys_LeaveCriticalSection((CriticalSection)0x21);
}


void dwUnregisterAddrHandle(unsigned int index);
struct in_addr;
void NET_InAddrToIpAddr(const in_addr *in, unsigned char *const out);

// Store 1405A9740. Registration is inlined here in this build: find an equal
// handle, otherwise the first empty entry, otherwise evict the oldest lifetime.
// The original strips two bytes without validating that a positive result is >=2.
int dwRecvFrom(netadr_s *const from, void *const buffer, unsigned int bufferSize)
{
    Sys_EnterCriticalSection((CriticalSection)0x21);
    int result = -9;
    void *router = dwGetSocketRouter();
    if (router && ((int (*)(void *))(*(void ***)router)[8])(router) == 1)
    {
        void *received = nullptr;
        result = ((int (*)(void *, void **, void *, unsigned int))(*(void ***)router)[11])
            (router, &received, buffer, bufferSize);
        if (result > 0)
        {
            if (!received)
            {
                Sys_LeaveCriticalSection((CriticalSection)0x21);
                return result;
            }
            Retain(received);
            Sys_EnterCriticalSection((CriticalSection)0x21);
            unsigned int index = 0;
            unsigned int firstFree = ~0u;
            unsigned int oldest = ~0u;
            bool foundFree = false;
            for (;; ++index)
            {
                if (index >= (unsigned int)localHandleIndex)
                {
                    index = firstFree;
                    if (!foundFree)
                    {
                        index = (int)oldest < 0 ? 0 : oldest;
                        dwUnregisterAddrHandle(index);
                    }
                    DwHandleEntry &entry = addressHandles[(int)index];
                    if (entry.handle)
                        Release(entry.handle);
                    entry.handle = received;
                    Retain(received);
                    break;
                }
                void *other = addressHandles[index].handle;
                bool equal = false;
                if (!other)
                {
                    if (!foundFree)
                    {
                        foundFree = true;
                        firstFree = index;
                    }
                }
                else
                {
                    equal = DwAddrHandleEqual(received, other);
                    if ((int)oldest < 0 || addressHandles[index].lifetime < addressHandles[(int)oldest].lifetime)
                        oldest = index;
                }
                if (equal)
                    break;
            }
            if (addressHandles[(int)index].lifetime < 6600)
                addressHandles[(int)index].lifetime = 6600;
            Sys_LeaveCriticalSection((CriticalSection)0x21);
            Release(received);
            result -= 2;
            memmove(buffer, (unsigned char *)buffer + 2, (unsigned long long)(long long)result);

            alignas(8) unsigned char realAddress[136];
            alignas(8) unsigned char internetAddress[144];
            void *real = DwGetRealAddr(received, realAddress);
            void *inet = sub_14073ED40(real);
            void *sockaddr = DwGetInAddr(inet, internetAddress);
            unsigned int ip4 = *(const unsigned int *)sockaddr;
            DwDestroyInetAddr(realAddress);
            NET_InAddrToIpAddr((const in_addr *)&ip4, from->ip);

            alignas(8) unsigned char portAddress[136];
            real = DwGetRealAddr(received, portAddress);
            from->port = DwGetPort(real);
            DwDestroyInetAddr(portAddress);
            from->addrHandleIndex = index;
            from->type = NA_IP;
        }
        if (received)
            Release(received);
    }
    Sys_LeaveCriticalSection((CriticalSection)0x21);
    return result;
}

// Store 1405AA0B0: recover a concrete IP/port from the address-handle index.
// The original clears the IP even on failure and succeeds for an empty valid slot.
void NET_InAddrSetLoopback(in_addr *address);
bool sub_1405AA0B0(netadr_s *adr)
{
    *(unsigned int *)adr->ip = 0;
    if (adr->type != NA_IP)
        return false;
    const unsigned int index = adr->addrHandleIndex;
    if (index < (unsigned int)localHandleIndex)
    {
        void *handle = addressHandles[index].handle;
        if (handle)
        {
            Retain(handle);
            alignas(8) unsigned char realAddress[144];
            alignas(8) unsigned char internetAddress[144];
            DwGetRealAddr(handle, realAddress);
            adr->port = DwGetPort(realAddress);
            void *inet = sub_14073ED40(realAddress);
            void *sockaddr = DwGetInAddr(inet, internetAddress);
            *(unsigned int *)adr->ip = *(const unsigned int *)sockaddr;
            DwDestroyInetAddr(realAddress);
            Release(handle);
        }
    }
    else if (index == (unsigned int)localHandleIndex)
        NET_InAddrSetLoopback((in_addr *)adr->ip);
    else
        return false;
    return true;
}

// Store 1405A9A90, PS4 PDB dw/dwnet.cpp:681. No lock is acquired here:
// callers protect the table, including the nested calls in send/status helpers.
void dwSanityCheckAddressHandle(int index, bdSocketRouter *socketRouter)
{
    void *router = socketRouter ? socketRouter : dwGetSocketRouter();
    if (!router || index < 0 || index >= localHandleIndex)
        return;
    DwHandleEntry &entry = addressHandles[index];
    void *original = entry.handle;
    if (!original)
        return;
    Retain(original);
    void *stateHandle = original;
    Retain(original);
    if (RouterState(router, &stateHandle) == 3)
    {
        void *replacement = nullptr;
        void *map = DwGetAddressMap(router);
        void *endpoint = (unsigned char *)original + 16;
        void *securityID = sub_140741840(endpoint);
        void *commonRef[2];
        void *common = DwGetEndpointCommonAddr(endpoint, commonRef);
        // findAddrHandle consumes the temporary common-address reference.
        if (DwFindAddrHandle(map, common, securityID, &replacement))
        {
            stateHandle = replacement;
            if (replacement)
                Retain(replacement);
            if (RouterState(router, &stateHandle) == 2)
            {
                if (entry.handle)
                    Release(entry.handle);
                entry.handle = replacement;
                if (replacement)
                    Retain(replacement);
                entry.unknown = 0;
            }
        }
        if (replacement)
            Release(replacement);
    }
    Release(original);
}
