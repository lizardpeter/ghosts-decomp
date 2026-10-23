// qcommon/qcommon.h and universal/q_shared.h: engine services used across the code (prototypes from the PS4
// server MAP, iw6_ds_ps4).
#pragma once

enum CriticalSection
{
	CRITSECT_CONSOLE = 0x0,
	CRITSECT_KEY_BINDINGS = 0xC,
	// the remaining values are in the PDB (analysis/iw6_ds_ps4/pdb/types.h)
};

void Sys_EnterCriticalSection(CriticalSection critSect);
void Sys_LeaveCriticalSection(CriticalSection critSect);
int Sys_Milliseconds();
bool Com_ErrorEntering();
bool Com_ErrorEntered();

enum errorParm_t
{
	ERR_FATAL = 0x0,
	ERR_DROP = 0x1,
	ERR_SERVERDISCONNECT = 0x2,
	ERR_DISCONNECT = 0x3,
	ERR_SCRIPT = 0x4,
	ERR_SCRIPT_DROP = 0x5,
	ERR_LOCALIZATION = 0x6,
	ERR_MAPLOADERRORSUMMARY = 0x7,
};

void Com_Error(errorParm_t code, const char *fmt, ...);
int Com_HashKey(const char *string, int maxlen);  // universal/com_shared.cpp

// qcommon/msg.cpp
struct msg_t
{
	int overflowed;
	int readOnly;
	unsigned char *data;
	unsigned char *splitData;
	int maxsize;
	int cursize;
	int splitSize;
	int readcount;
	int bit;
	int lastEntityRef;
	int targetLocalNetID;  // netsrc_t
	int useZlib;
};

// qcommon/qcommon.h: network addresses
enum netadrtype_t
{
	NA_BOT = 0x0,
	NA_BAD = 0x1,
	NA_LOOPBACK = 0x2,
	NA_BROADCAST = 0x3,
	NA_IP = 0x4,
};

// The Store build's netadr_s is 0x10 bytes: the server PDB's localNetID (0xC) is gone, so addrHandleIndex (the
// DemonWare address handle of an NA_IP address) moved from 0x10 to 0xC (Sys_SendPacket copies 16 bytes,
// sub_14054EFA0 reads 0xC).
struct netadr_s
{
	netadrtype_t type;
	unsigned char ip[4];
	unsigned short port;
	unsigned int addrHandleIndex;
};
static_assert(sizeof(netadr_s) == 0x10, "netadr_s layout (Store build)");
static_assert(__builtin_offsetof(netadr_s, port) == 0x8, "netadr_s layout");
static_assert(__builtin_offsetof(netadr_s, addrHandleIndex) == 0xC, "netadr_s layout");

struct playerState_s;
struct usercmd_s;

void MSG_Init(msg_t *buf, unsigned char *data, int length);
void MSG_WriteBits(msg_t *msg, int value, int bits);
void MSG_WriteBit0(msg_t *msg);
void MSG_WriteBit1(msg_t *msg);
void MSG_WriteByte(msg_t *msg, int c);
void MSG_WriteLong(msg_t *msg, int c);
void MSG_WriteString(msg_t *sb, const char *s);
int MSG_WriteBitsCompress(bool trainHuffman, const unsigned char *from, unsigned char *to, int size);
void MSG_SetDefaultUserCmd(const playerState_s *ps, usercmd_s *cmd);
void MSG_WriteDeltaUsercmdKey(msg_t *msg, int key, const usercmd_s *from, const usercmd_s *to);  // qcommon/msg_mp.cpp

enum netsrc_t
{
	NS_CLIENT1 = 0x0,
	NS_MAXCLIENTS = 0x1,
	NS_SERVER = 0x2,
	NS_PACKET = 0x3,
	NS_INVALID_NETSRC = 0x4,
};

// qcommon/net_chan_mp.cpp
int NET_GetLoopPacket(netsrc_t sock, netadr_s *net_from, msg_t *net_message);
bool NET_GetDeferredClientPacket(netadr_s *net_from, msg_t *net_message);
int NET_GetClientPacket(netadr_s *net_from, msg_t *net_message);

// universal/com_memory.cpp: a large buffer borrowed from the stack-like LargeLocal region for one scope
class LargeLocal
{
public:
	LargeLocal(unsigned long long sizeParam);
	~LargeLocal();
	void *GetBuf();

private:
	unsigned long long startPos;
	unsigned long long size;
};

int SEH_GetCurrentLanguage();
#define LANGUAGE_FRENCH 1

int I_stricmp(const char *s0, const char *s1);
void I_strncpyz(char *dest, const char *src, int destsize);
char *I_strupr(char *s);
