// win32/win_net.cpp
//
// The client's UDP socket, reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship). The file and most
// names come from Black Ops' win32/win_net.cpp (black-ops-1-decomp, server PDB) and the PS4 server's
// ds/ds_net.cpp (iw6_ds_ps4, PDB), which has the same NET_GetDvars, NET_Config, NET_IPSocket,
// NET_GetLocalAddress, NET_OpenIP, NET_Init, Sys_GetPacket and Sys_SendPacket; their common ancestor is Quake
// III's win_net.c, whose SOCKS5 client (NET_OpenSocks) the Store build still has. Line numbers are unknown. Each
// function is tagged with its Store address; a function the Store build inlines everywhere has no address and is
// tested through its callers.
//
// Packets: Sys_SendPacket sends broadcasts with sendto on ip_socket and everything addressed to an NA_IP address
// through DemonWare (dwSendTo); Sys_GetPacket reads ip_socket with recvfrom and, when that has nothing, DemonWare
// (dwRecvFrom). Both append or check a 16-bit checksum (universal/com_net.cpp). The Store build's ship
// configuration compiles out every Com_Printf, which leaves some WSAGetLastError calls without a use.

#include <string.h>
#include <winsock2.h>

#include <iw6_static.h>

#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "win32/win_net.cpp"

#define MAX_IPS 16
#define PORT_ANY -1
#define PORT_SERVER 27016

// Globals (in the PS4 server MAP, ds_net.obj)
extern const dvar_t *ip;    // "net_ip"
extern const dvar_t *port;  // "net_port"

// File statics
IW6_STATIC WSADATA winsockdata IW6_AT("", "winsockdata");
IW6_STATIC int winsockInitialized IW6_AT("", "winsockInitialized");
IW6_STATIC int usingSocks IW6_AT("", "usingSocks");
IW6_STATIC int networkingEnabled IW6_AT("", "networkingEnabled");
IW6_STATIC const dvar_t *net_noudp IW6_AT("", "net_noudp");
IW6_STATIC const dvar_t *net_socksEnabled IW6_AT("", "net_socksEnabled");
IW6_STATIC const dvar_t *net_socksServer IW6_AT("", "net_socksServer");
IW6_STATIC const dvar_t *net_socksPort IW6_AT("", "net_socksPort");
IW6_STATIC const dvar_t *net_socksUsername IW6_AT("", "net_socksUsername");
IW6_STATIC const dvar_t *net_socksPassword IW6_AT("", "net_socksPassword");
IW6_STATIC sockaddr socksRelayAddr IW6_AT("", "socksRelayAddr");
IW6_STATIC SOCKET ip_socket IW6_AT("", "ip_socket");
IW6_STATIC SOCKET socks_socket IW6_AT("", "socks_socket");
IW6_STATIC int numIP IW6_AT("", "numIP");
IW6_STATIC unsigned char localIP[MAX_IPS][4] IW6_AT("", "localIP");

// A second socket Sys_GetPacket reads after ip_socket. Nothing in the Store build ever sets it, so it stays 0 and
// is skipped (Quake III's ioquake3 reads ip6_socket there).
extern SOCKET unk_149D62370;

static_assert(__builtin_offsetof(msg_t, data) == 0x8, "msg_t layout (Store build)");
static_assert(__builtin_offsetof(msg_t, maxsize) == 0x18, "msg_t layout");
static_assert(__builtin_offsetof(msg_t, cursize) == 0x1C, "msg_t layout");
static_assert(__builtin_offsetof(msg_t, readcount) == 0x24, "msg_t layout");
static_assert(__builtin_offsetof(dvar_t, modified) == 0xD, "dvar_t layout");
static_assert(__builtin_offsetof(dvar_t, current) == 0x10, "dvar_t layout");
static_assert(sizeof(WSADATA) == 0x198, "WSADATA layout (x64)");
static_assert(sizeof(sockaddr) == 0x10, "sockaddr layout");

// DemonWare (dw/dwnet.cpp)
struct XNADDR
{
	unsigned char addrBuff[37];
};
class bdSecurityID;
bool dwNetadrToCommonAddr(netadr_s addr, unsigned char *commonAddr, unsigned int commonAddrSize,
                          bdSecurityID *const secID);
int dwRecvFrom(netadr_s *const from, void *const buffer, unsigned int bufferSize);
int dwSendTo(unsigned int length, const void *data, netadr_s to);
bool sub_1405AA0B0(netadr_s *adr);                     // fills in an NA_IP address from its address handle
int sub_1405A8980(const netadr_s *adr);                // a connection state of the address (1, 2 or 3)
unsigned int sub_1405A8AD0();                          // the address handle index meaning "this machine"
bool sub_1405A8300(netadr_s *adr, const unsigned char *commonAddr, const unsigned char *secID);

// universal/com_net.cpp
void NetadrToSockadr(netadr_s *a, sockaddr *s);
void SockadrToNetadr(sockaddr *s, netadr_s *a);
unsigned short Sys_Checksum(unsigned char *data, int len);
unsigned short Sys_ChecksumCopy(unsigned char *dest, unsigned char *src, int len);
int Sys_StringToSockaddr(const char *s, sockaddr *sadr);

// Store 14054EF80 (name unknown): an NA_IP address for a DemonWare address handle and port, completed by
// sub_1405AA0B0
bool sub_14054EF80(const unsigned int *addrHandleIndex, unsigned short port, netadr_s *adr)
{
	adr->type = NA_IP;
	adr->port = port;
	adr->addrHandleIndex = *addrHandleIndex;
	*(unsigned int *)adr->ip = 0;
	return sub_1405AA0B0(adr);
}

// Store 14054EFA0 (name unknown)
void sub_14054EFA0(const netadr_s *adr, unsigned int *addrHandleIndex)
{
	*addrHandleIndex = adr->addrHandleIndex;
}

// Store 14054EFB0 (name unknown): 2 when sub_1405A8980 reports state 1, else 1
int sub_14054EFB0(const netadr_s *adr)
{
	return (sub_1405A8980(adr) == 1) + 1;
}

// Store 14054EFD0: registers the network dvars; returns whether any of them was modified
int NET_GetDvars()
{
	int modified = 0;

	if (net_noudp && net_noudp->modified)
		modified = 1;
	net_noudp = Dvar_RegisterBool("net_noudp", false, 3, "Disable UDP");
	if (net_socksEnabled && net_socksEnabled->modified)
		modified = 1;
	net_socksEnabled = Dvar_RegisterBool("net_socksEnabled", false, 3, "Enable network sockets");
	if (net_socksServer && net_socksServer->modified)
		modified = 1;
	net_socksServer = Dvar_RegisterString("net_socksServer", "", 3, "Network socket server");
	if (net_socksPort && net_socksPort->modified)
		modified = 1;
	net_socksPort = Dvar_RegisterInt("net_socksPort", 1080, 0, 0xFFFF, 3, "Network socket port");
	if (net_socksUsername && net_socksUsername->modified)
		modified = 1;
	net_socksUsername = Dvar_RegisterString("net_socksUsername", "", 3, "Network socket username");
	if (net_socksPassword && net_socksPassword->modified)
		modified = 1;
	net_socksPassword = Dvar_RegisterString("net_socksPassword", "", 3, "Network socket password");
	if (ip && ip->modified)
		modified = 1;
	ip = Dvar_RegisterString("net_ip", "localhost", 2, "Network IP Address");
	if (port && port->modified)
		modified = 1;
	port = Dvar_RegisterInt("net_port", PORT_SERVER, 0, 0xFFFF, 2, "Network port");
	return modified;
}

// Store 14054F1D0  (ds/ds_net.cpp:2591 in the server)
int NET_GetXnAddrForNetAddr(const netadr_s *addr, XNADDR *xnaddr, bdSecurityID *secID)
{
	return dwNetadrToCommonAddr(*addr, xnaddr->addrBuff, sizeof(xnaddr->addrBuff), secID);
}

// Store 14054F2E0 (name unknown): whether the handle is the one meaning this machine
bool sub_14054F2E0(const unsigned int *addrHandleIndex)
{
	return *addrHandleIndex == sub_1405A8AD0();
}

// (inlined everywhere in the Store build)
SOCKET NET_IPSocket(const char *net_interface, int port, int protocol)
{
	u_long _true = 1;
	int i = 1;
	sockaddr_in address;

	const SOCKET newsocket = socket(AF_INET, SOCK_DGRAM, protocol);
	if (newsocket == INVALID_SOCKET)
	{
		WSAGetLastError();
		return 0;
	}
	// the socket is leaked when ioctlsocket or setsockopt fails
	if (ioctlsocket(newsocket, FIONBIO, &_true) == SOCKET_ERROR)
		return 0;
	if (setsockopt(newsocket, SOL_SOCKET, SO_BROADCAST, (const char *)&i, sizeof(i)) == SOCKET_ERROR)
		return 0;

	// sin_zero is left uninitialized unless Sys_StringToSockaddr filled the address
	if (!net_interface || !net_interface[0] || !I_stricmp(net_interface, "localhost"))
		address.sin_addr.s_addr = INADDR_ANY;
	else
		Sys_StringToSockaddr(net_interface, (sockaddr *)&address);

	if (port == PORT_ANY)
		address.sin_port = 0;
	else
		address.sin_port = htons((u_short)port);
	address.sin_family = AF_INET;

	if (bind(newsocket, (const sockaddr *)&address, sizeof(address)) == SOCKET_ERROR)
	{
		closesocket(newsocket);
		return 0;
	}
	return newsocket;
}

// (inlined everywhere in the Store build)
void NET_GetLocalAddress()
{
	char hostname[256];

	if (gethostname(hostname, 256) == SOCKET_ERROR)
	{
		WSAGetLastError();
		return;
	}
	const hostent *hostInfo = gethostbyname(hostname);
	if (!hostInfo)
	{
		WSAGetLastError();
		return;
	}
	if (hostInfo->h_addrtype != AF_INET)
		return;

	numIP = 0;
	const unsigned char *p;
	while ((p = (const unsigned char *)hostInfo->h_addr_list[numIP]) != NULL && numIP < MAX_IPS)
	{
		ntohl(*(const u_long *)p);
		localIP[numIP][0] = p[0];
		localIP[numIP][1] = p[1];
		localIP[numIP][2] = p[2];
		localIP[numIP][3] = p[3];
		numIP++;
	}
}

void NET_OpenSocks(int port);

// Store 14054F300, with NET_IPSocket and NET_GetLocalAddress inlined
void NET_OpenIP()
{
	ip = Dvar_RegisterString("net_ip", "localhost", 2, "Network IP Address");
	port = Dvar_RegisterInt("net_port", PORT_SERVER, 0, 0xFFFF, 2, "Network port");

	// net_port is read again after Dvar_SetInt has stored port + i in it
	for (int i = 0; i < 10; i++)
	{
		ip_socket = NET_IPSocket(ip->current.string, port->current.integer + i, IPPROTO_UDP);
		if (ip_socket)
		{
			Dvar_SetInt(port, port->current.integer + i);
			if (net_socksEnabled->current.enabled)
				NET_OpenSocks(port->current.integer + i);
			NET_GetLocalAddress();
			return;
		}
	}
}

// Store 14054F5B0: SOCKS5 (RFC 1928) UDP ASSOCIATE through net_socksServer, with RFC 1929 username/password
// authentication when either is set
void NET_OpenSocks(int port)
{
	sockaddr_in address;
	unsigned char buf[64];
	bool rfc1929;
	int len;

	usingSocks = 0;
	if ((socks_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) == INVALID_SOCKET)
	{
		WSAGetLastError();
		return;
	}

	const hostent *h = gethostbyname(net_socksServer->current.string);
	if (!h)
	{
		WSAGetLastError();
		return;
	}
	if (h->h_addrtype != AF_INET)
		return;
	address.sin_family = AF_INET;
	address.sin_addr.s_addr = *(const u_long *)h->h_addr_list[0];
	address.sin_port = htons((u_short)net_socksPort->current.integer);
	if (connect(socks_socket, (const sockaddr *)&address, sizeof(address)) == SOCKET_ERROR)
	{
		WSAGetLastError();
		return;
	}

	// method selection; with authentication the method list is buf[2] = 2 and an unset buf[3]
	if (*net_socksUsername->current.string || *net_socksPassword->current.string)
		rfc1929 = true;
	else
		rfc1929 = false;
	buf[0] = 5;
	if (rfc1929)
	{
		buf[1] = 2;
		len = 4;
	}
	else
	{
		buf[1] = 1;
		len = 3;
	}
	buf[2] = 0;
	if (rfc1929)
		buf[2] = 2;
	if (send(socks_socket, (const char *)buf, len, 0) == SOCKET_ERROR)
	{
		WSAGetLastError();
		return;
	}

	len = recv(socks_socket, (char *)buf, 64, 0);
	if (len == SOCKET_ERROR)
	{
		WSAGetLastError();
		return;
	}
	if (len != 2 || buf[0] != 5)
		return;
	switch (buf[1])
	{
	case 0:
		break;
	case 2:
		break;
	default:
		return;
	}

	if (buf[1] == 2)
	{
		// the username and password are copied into the 64-byte buf without a length check
		// strlen, which the Store build expands inline (it links no strlen)
		int ulen = 0;
		while (net_socksUsername->current.string[ulen])
			ulen++;
		int plen = 0;
		while (net_socksPassword->current.string[plen])
			plen++;

		buf[0] = 1;
		buf[1] = (unsigned char)ulen;
		if (ulen)
			memcpy(&buf[2], net_socksUsername->current.string, ulen);
		buf[2 + ulen] = (unsigned char)plen;
		if (plen)
			memcpy(&buf[3 + ulen], net_socksPassword->current.string, plen);

		if (send(socks_socket, (const char *)buf, 3 + ulen + plen, 0) == SOCKET_ERROR)
		{
			WSAGetLastError();
			return;
		}
		len = recv(socks_socket, (char *)buf, 64, 0);
		if (len == SOCKET_ERROR)
		{
			WSAGetLastError();
			return;
		}
		if (len != 2 || buf[0] != 1)
			return;
		if (buf[1] != 0)
			return;
	}

	// UDP ASSOCIATE from INADDR_ANY:port; a failed send is not treated as an error (Quake III returns)
	buf[0] = 5;
	buf[1] = 3;
	buf[2] = 0;
	buf[3] = 1;
	*(u_long *)&buf[4] = INADDR_ANY;
	*(u_short *)&buf[8] = htons((u_short)port);
	if (send(socks_socket, (const char *)buf, 10, 0) == SOCKET_ERROR)
		WSAGetLastError();

	// a reply shorter than 10 bytes leaves the rest of the request in buf, which is taken as the relay address
	len = recv(socks_socket, (char *)buf, 64, 0);
	if (len == SOCKET_ERROR)
	{
		WSAGetLastError();
		return;
	}
	if (len < 2 || buf[0] != 5)
		return;
	if (buf[1] != 0)
		return;
	if (buf[3] != 1)
		return;
	((sockaddr_in *)&socksRelayAddr)->sin_family = AF_INET;
	((sockaddr_in *)&socksRelayAddr)->sin_addr.s_addr = *(const u_long *)&buf[4];
	((sockaddr_in *)&socksRelayAddr)->sin_port = *(const u_short *)&buf[8];
	memset(((sockaddr_in *)&socksRelayAddr)->sin_zero, 0, 8);
	usingSocks = 1;
}

// Store 14054F8D0 (name unknown): returns 1
int sub_14054F8D0()
{
	return 1;
}

// Store 14054F8E0 (name unknown): whether xnaddr is the DemonWare common address of adr
bool sub_14054F8E0(const XNADDR *xnaddr, const netadr_s *adr)
{
	XNADDR adrXnaddr;

	if (!dwNetadrToCommonAddr(*adr, adrXnaddr.addrBuff, sizeof(adrXnaddr.addrBuff), NULL))
		return false;
	return memcmp(xnaddr, &adrXnaddr, sizeof(adrXnaddr)) == 0;
}

// Store 14054F940  (ds/ds_net.cpp:905 in the server); i is not checked against numIP
in_addr Sys_GetLocalIP(int i)
{
	return *(const in_addr *)localIP[i];
}

// Store 14054F950 (name unknown): the number of local addresses NET_GetLocalAddress found
int sub_14054F950()
{
	return numIP;
}

// Store 14054F960
int Sys_GetPacket(netadr_s *net_from, msg_t *net_message)
{
	sockaddr from;
	int fromlen;

	for (int i = 0; i < 2; i++)
	{
		const SOCKET sock = i == 0 ? ip_socket : unk_149D62370;
		if (!sock)
			continue;

		fromlen = sizeof(from);
		bool fromDemonWare = false;
		int ret = recvfrom(sock, (char *)net_message->data, net_message->maxsize, 0, &from, &fromlen);
		if (ret == SOCKET_ERROR)
		{
			const int err = WSAGetLastError();
			if (err != WSAEWOULDBLOCK && err != WSAECONNREFUSED)
				continue;
			ret = dwRecvFrom(net_from, net_message->data, net_message->maxsize);
			if (ret == -2 || ret == -9)
				continue;
			fromDemonWare = true;
			if (ret < 0)
				continue;
		}

		if (!fromDemonWare)
		{
			if (sock == ip_socket)
				memset(((sockaddr_in *)&from)->sin_zero, 0, sizeof(((sockaddr_in *)&from)->sin_zero));

			if (usingSocks && sock == ip_socket && !memcmp(&from, &socksRelayAddr, fromlen))
			{
				// a datagram from the SOCKS relay: a 10-byte header with the sender's IPv4 address and port
				if (ret < 10 || net_message->data[0] != 0 || net_message->data[1] != 0 || net_message->data[2] != 0
				    || net_message->data[3] != 1)
					continue;
				net_from->type = NA_IP;
				net_from->ip[0] = net_message->data[4];
				net_from->ip[1] = net_message->data[5];
				net_from->ip[2] = net_message->data[6];
				net_from->ip[3] = net_message->data[7];
				net_from->port = *(const unsigned short *)&net_message->data[8];
				net_message->readcount = 10;
			}
			else
			{
				SockadrToNetadr(&from, net_from);
				net_message->readcount = 0;
			}
		}

		if (ret == net_message->maxsize)
			continue;  // oversize packet

		// the last two bytes are the checksum of the rest; a packet of 0 or 1 bytes reads them from before data
		ret -= 2;
		const unsigned short checksum = Sys_Checksum(net_message->data, ret);
		if (((net_message->data[ret] << 8) | net_message->data[ret + 1]) != checksum)
			return 0;
		net_message->cursize = ret;
		return 1;
	}
	return 0;
}

// Store 14054FB70: length is not checked against the 1280-byte buffer
bool Sys_SendPacket(int length, const void *data, netadr_s to)
{
	unsigned char buf[1280];
	sockaddr addr;

	const unsigned short checksum = Sys_ChecksumCopy(buf, (unsigned char *)data, length);
	buf[length] = (unsigned char)(checksum >> 8);
	buf[length + 1] = (unsigned char)checksum;

	if (to.type == NA_BROADCAST)
	{
		if (!ip_socket)
			return false;
		NetadrToSockadr(&to, &addr);
		return sendto(ip_socket, (const char *)buf, length + 2, 0, &addr, sizeof(addr)) >= 0;
	}
	if (to.type == NA_IP)
		return dwSendTo(length + 2, buf, to) >= 0;

	Com_Error(ERR_FATAL, "NET_SendPacket: bad address type %i", to.type);
	return false;
}

// Store 14054FC70 (name unknown): the DemonWare address handle of a common address and the port to use with it
// (none for this machine or a loopback address, else 27016)
bool sub_14054FC70(const unsigned char *secIDAndCommonAddr, unsigned int *addrHandleIndex, unsigned short *outPort)
{
	netadr_s adr;

	const bool result = sub_1405A8300(&adr, secIDAndCommonAddr + 8, secIDAndCommonAddr);
	*addrHandleIndex = adr.addrHandleIndex;
	*outPort = sub_1405A8AD0() == adr.addrHandleIndex || adr.type == NA_LOOPBACK ? 0 : PORT_SERVER;
	return result;
}

// (inlined everywhere in the Store build)
void NET_Config(int enableNetworking)
{
	int stop;
	int start;

	const int modified = NET_GetDvars();
	if (net_noudp->current.enabled)
		enableNetworking = 0;

	if (enableNetworking == networkingEnabled)
	{
		if (!modified)
			return;
		if (enableNetworking)
		{
			stop = 1;
			start = 1;
		}
		else
		{
			stop = 0;
			start = 0;
		}
	}
	else
	{
		if (enableNetworking)
		{
			stop = 0;
			start = 1;
		}
		else
		{
			stop = 1;
			start = 0;
		}
		networkingEnabled = enableNetworking;
	}

	if (stop)
	{
		if (ip_socket && ip_socket != INVALID_SOCKET)
		{
			closesocket(ip_socket);
			ip_socket = 0;
		}
		if (socks_socket && socks_socket != INVALID_SOCKET)
		{
			closesocket(socks_socket);
			socks_socket = 0;
		}
	}
	if (start)
	{
		if (!net_noudp->current.enabled)
			NET_OpenIP();
	}
}

// Store 14054F200, with NET_Config inlined
void NET_Init()
{
	if (WSAStartup(MAKEWORD(1, 1), &winsockdata))
		return;
	winsockInitialized = 1;
	NET_GetDvars();
	NET_Config(1);
}
