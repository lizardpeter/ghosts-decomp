// P0012: direct IPv4 UDP transport. Never calls the original network IAT or DW.
#include "transport.h"
#ifdef _WIN32
#define IW6_PRIVATE_WINSOCK
#include <winsock2.h>
extern "C" __declspec(dllimport) int getsockname(SOCKET, sockaddr *, int *);
extern "C" __declspec(dllimport) int WSACleanup();
extern "C" __declspec(dllimport) void AcquireSRWLockExclusive(void *);
extern "C" __declspec(dllimport) void ReleaseSRWLockExclusive(void *);
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <unistd.h>
#include <pthread.h>
using SOCKET = int;
#define INVALID_SOCKET (-1)
#define SOCKET_ERROR (-1)
#define closesocket close
#endif

namespace
{
constexpr int MaxPayload = 1262;
constexpr unsigned int MaxPeers = 64;
SOCKET udp = INVALID_SOCKET;
bool initialized;
bool hosting;
unsigned short boundPort;
netadr_s selected;
netadr_s peers[MaxPeers];
unsigned int peerCount;
#ifdef _WIN32
unsigned long long lockStorage;
struct Lock
{
    Lock() { AcquireSRWLockExclusive(&lockStorage); }
    ~Lock() { ReleaseSRWLockExclusive(&lockStorage); }
};
#else
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
struct Lock
{
    Lock() { pthread_mutex_lock(&mutex); }
    ~Lock() { pthread_mutex_unlock(&mutex); }
};
#endif
unsigned short Swap(unsigned short port) { return (unsigned short)((port >> 8) | (port << 8)); }
bool Unicast(const unsigned char *ip) { return ip[0] > 0 && ip[0] < 224; }
bool Same(const netadr_s &a, const netadr_s &b, bool port)
{
    if (a.type != b.type) return false;
    if (a.type == NA_LOOPBACK || a.type == NA_BOT) return !port || a.port == b.port;
    if (a.type != NA_IP) return false;
    for (int i = 0; i < 4; ++i) if (a.ip[i] != b.ip[i]) return false;
    return !port || a.port == b.port;
}
unsigned short Checksum(const unsigned char *data, int length)
{
    unsigned int sum = 0;
    while (length > 1) { sum += (data[0] << 8) | data[1]; data += 2; length -= 2; }
    if (length) sum += *data;
    while (sum >> 16) sum = (sum & 0xFFFF) + (sum >> 16);
    return (unsigned short)~sum;
}
sockaddr_in Sockaddr(const netadr_s &a)
{
    sockaddr_in result = {};
    result.sin_family = AF_INET;
    result.sin_port = a.port;
    unsigned char *ip = (unsigned char *)&result.sin_addr;
    for (int i = 0; i < 4; ++i) ip[i] = a.ip[i];
    return result;
}
void Close()
{
    if (udp != INVALID_SOCKET) closesocket(udp);
    udp = INVALID_SOCKET;
#ifdef _WIN32
    if (initialized) WSACleanup();
#endif
    initialized = false;
    hosting = false;
    boundPort = 0;
    selected = {};
    peerCount = 0;
}
bool Permitted(const netadr_s &a)
{
    if (!Unicast(a.ip) || a.type != NA_IP || !a.port) return false;
    if (!hosting) return Same(selected, a, true);
    // A listener may reply only to peers from which a checksum-valid packet arrived.
    for (unsigned int i = 0; i < peerCount; ++i) if (Same(peers[i], a, true)) return true;
    return false;
}
}

extern "C" int Iw6DirectParse(const char *text, netadr_s *address, int allowZeroPort)
{
    if (!address) return 0;
    *address = {};
    if (!text) return 0;
    netadr_s result = {};
    for (int i = 0; i < 4; ++i)
    {
        unsigned int value = 0, digits = 0;
        while (*text >= '0' && *text <= '9')
        {
            value = value * 10 + (unsigned int)(*text++ - '0');
            if (++digits > 3 || value > 255) return 0;
        }
        if (!digits) return 0;
        result.ip[i] = (unsigned char)value;
        if (*text++ != (i == 3 ? ':' : '.')) return 0;
    }
    unsigned int port = 0, digits = 0;
    while (*text >= '0' && *text <= '9')
    {
        port = port * 10 + (unsigned int)(*text++ - '0');
        if (++digits > 5 || port > 65535) return 0;
    }
    const bool wildcard = allowZeroPort && !(result.ip[0] | result.ip[1] | result.ip[2] | result.ip[3]);
    if (*text || !digits || (!port && !allowZeroPort) || (!Unicast(result.ip) && !wildcard)) return 0;
    result.type = NA_IP;
    result.port = Swap((unsigned short)port);
    result.addrHandleIndex = 0xFFFFFFFF;
    *address = result;
    return 1;
}
extern "C" int Iw6DirectOpen(const char *bindEndpoint, int server)
{
    Lock guard;
    // A failed reconfiguration must not leave a prior peer/socket live.
    Close();
    netadr_s address;
    if (!Iw6DirectParse(bindEndpoint, &address, 1)) return 0;
#ifdef _WIN32
    WSADATA data;
    if (WSAStartup(0x202, &data)) return 0;
#endif
    initialized = true;
    udp = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (udp == INVALID_SOCKET) { Close(); return 0; }
#ifdef _WIN32
    u_long nonblocking = 1;
    if (ioctlsocket(udp, FIONBIO, &nonblocking) == SOCKET_ERROR) { Close(); return 0; }
#else
    if (fcntl(udp, F_SETFL, O_NONBLOCK) == -1) { Close(); return 0; }
#endif
    sockaddr_in local = Sockaddr(address);
    if (bind(udp, (sockaddr *)&local, sizeof(local)) == SOCKET_ERROR) { Close(); return 0; }
#ifdef _WIN32
    int size = sizeof(local);
#else
    socklen_t size = sizeof(local);
#endif
    if (getsockname(udp, (sockaddr *)&local, &size) == SOCKET_ERROR) { Close(); return 0; }
    boundPort = Swap(local.sin_port);
    hosting = server != 0;
    return 1;
}
extern "C" void Iw6DirectClose() { Lock guard; Close(); }
extern "C" unsigned short Iw6DirectPort() { Lock guard; return boundPort; }
extern "C" int Iw6DirectSelectPeer(const char *endpoint)
{
    netadr_s address;
    const bool valid = Iw6DirectParse(endpoint, &address, 0) != 0;
    Lock guard;
    selected = {}; // Failed selection revokes the old destination.
    if (!valid || udp == INVALID_SOCKET || hosting) return 0;
    selected = address;
    return 1;
}
extern "C" int Iw6DirectPeer(netadr_s *address)
{
    Lock guard;
    if (!address) return 0;
    *address = selected;
    return udp != INVALID_SOCKET && selected.type == NA_IP && !hosting;
}
extern "C" int Iw6DirectSameAddress(const netadr_s *a, const netadr_s *b, int comparePort)
{
    return a && b && Same(*a, *b, comparePort != 0);
}
extern "C" int Iw6DirectSend(int length, const void *data, const netadr_s *to)
{
    if (!to || length < 0 || length > MaxPayload || (length && !data)) return 0;
    Lock guard;
    if (udp == INVALID_SOCKET || !Permitted(*to)) return 0;
    unsigned char packet[MaxPayload + 2];
    for (int i = 0; i < length; ++i) packet[i] = ((const unsigned char *)data)[i];
    const unsigned short checksum = Checksum(packet, length);
    packet[length] = (unsigned char)(checksum >> 8);
    packet[length + 1] = (unsigned char)checksum;
    sockaddr_in destination = Sockaddr(*to);
    return sendto(udp, (const char *)packet, length + 2, 0,
                  (const sockaddr *)&destination, sizeof(destination)) == length + 2;
}
extern "C" int Iw6DirectReceive(netadr_s *from, msg_t *message)
{
    if (!from || !message) return 0;
    message->cursize = 0;
    message->readcount = 0;
    if (!message->data || message->maxsize < 1) return 0;
    Lock guard;
    if (udp == INVALID_SOCKET) return 0;
    // Bounded drain: malformed traffic cannot keep one game frame spinning forever.
    for (int count = 0; count < 64; ++count)
    {
        unsigned char packet[MaxPayload + 3];
        sockaddr_in source = {};
#ifdef _WIN32
        int size = sizeof(source);
#else
        socklen_t size = sizeof(source);
#endif
        const int received = (int)recvfrom(udp, (char *)packet, sizeof(packet), 0,
                                          (sockaddr *)&source, &size);
        if (received == SOCKET_ERROR) return 0;
        if (size != sizeof(source) || source.sin_family != AF_INET || received < 2 || received > MaxPayload + 2) continue;
        const int length = received - 2;
        if (length > message->maxsize || Checksum(packet, length) != ((packet[length] << 8) | packet[length + 1])) continue;
        netadr_s address = {};
        address.type = NA_IP;
        address.port = source.sin_port;
        address.addrHandleIndex = 0xFFFFFFFF;
        for (int i = 0; i < 4; ++i) address.ip[i] = ((const unsigned char *)&source.sin_addr)[i];
        if (!Unicast(address.ip) || !address.port) continue;
        if (hosting)
        {
            unsigned int index = 0;
            for (; index < peerCount; ++index) if (Same(peers[index], address, true)) break;
            if (index == peerCount)
            {
                if (peerCount == MaxPeers) continue;
                peers[peerCount++] = address;
            }
        }
        else if (!Same(address, selected, true)) continue;
        *from = address;
        for (int i = 0; i < length; ++i) message->data[i] = packet[i];
        message->cursize = length;
        return 1;
    }
    return 0;
}
