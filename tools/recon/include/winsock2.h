// The Winsock declarations the reconstruction uses (ws2_32, x64 layouts).
//
// Build environment, not game source. The original includes the Windows SDK's winsock2.h; these are the same
// declarations, trimmed. The Store build imports ws2_32 by ordinal; tools/build_recon.py links each function to
// its import address table slot by name (pefile resolves the ordinals).
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#ifndef NULL
#define NULL 0
#endif

typedef unsigned long long SOCKET;
typedef unsigned short u_short;
typedef unsigned long u_long;
typedef unsigned short WORD;

#define INVALID_SOCKET (SOCKET)(~0)
#define SOCKET_ERROR (-1)

#define AF_INET 2
#define SOCK_STREAM 1
#define SOCK_DGRAM 2
#define IPPROTO_TCP 6
#define IPPROTO_UDP 17
#define SOL_SOCKET 0xFFFF
#define SO_BROADCAST 0x0020
#define FIONBIO ((long)0x8004667EUL)
#define INADDR_ANY 0UL

#define WSAEWOULDBLOCK 10035
#define WSAECONNREFUSED 10061

#define MAKEWORD(a, b) ((WORD)(((unsigned char)(a)) | ((WORD)((unsigned char)(b))) << 8))

struct in_addr
{
	union
	{
		struct
		{
			unsigned char s_b1, s_b2, s_b3, s_b4;
		} S_un_b;
		struct
		{
			unsigned short s_w1, s_w2;
		} S_un_w;
		u_long S_addr;
	} S_un;
};
#define s_addr S_un.S_addr

struct sockaddr
{
	u_short sa_family;
	char sa_data[14];
};

struct sockaddr_in
{
	short sin_family;
	u_short sin_port;
	struct in_addr sin_addr;
	char sin_zero[8];
};

struct hostent
{
	char *h_name;
	char **h_aliases;
	short h_addrtype;
	short h_length;
	char **h_addr_list;
};

// The x64 layout (lpVendorInfo before the strings), 0x198 bytes.
typedef struct WSAData
{
	WORD wVersion;
	WORD wHighVersion;
	unsigned short iMaxSockets;
	unsigned short iMaxUdpDg;
	char *lpVendorInfo;
	char szDescription[257];
	char szSystemStatus[129];
} WSADATA;

#ifdef IW6_PRIVATE_WINSOCK
#define IW6_WSA __declspec(dllimport)
#else
#define IW6_WSA
#endif

IW6_WSA int WSAStartup(WORD wVersionRequested, WSADATA *lpWSAData);
IW6_WSA int WSAGetLastError(void);
IW6_WSA SOCKET socket(int af, int type, int protocol);
IW6_WSA int closesocket(SOCKET s);
IW6_WSA int ioctlsocket(SOCKET s, long cmd, u_long *argp);
IW6_WSA int setsockopt(SOCKET s, int level, int optname, const char *optval, int optlen);
IW6_WSA int bind(SOCKET s, const struct sockaddr *name, int namelen);
IW6_WSA int connect(SOCKET s, const struct sockaddr *name, int namelen);
IW6_WSA int send(SOCKET s, const char *buf, int len, int flags);
IW6_WSA int recv(SOCKET s, char *buf, int len, int flags);
IW6_WSA int sendto(SOCKET s, const char *buf, int len, int flags, const struct sockaddr *to, int tolen);
IW6_WSA int recvfrom(SOCKET s, char *buf, int len, int flags, struct sockaddr *from, int *fromlen);
IW6_WSA u_short htons(u_short hostshort);
IW6_WSA u_long ntohl(u_long netlong);
IW6_WSA unsigned long inet_addr(const char *cp);
IW6_WSA struct hostent *gethostbyname(const char *name);
IW6_WSA int gethostname(char *name, int namelen);

#ifdef __cplusplus
}
#endif
