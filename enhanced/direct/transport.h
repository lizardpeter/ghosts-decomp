#pragma once
#include "qcommon/qcommon.h"

// Startup-only direct transport. These APIs never resolve DNS or vendor handles.
extern "C" int Iw6DirectWireVersion();
extern "C" int Iw6DirectOpen(const char *bindEndpoint, int server);
extern "C" void Iw6DirectClose();
extern "C" int Iw6DirectSelectPeer(const char *endpoint);
extern "C" int Iw6DirectPeer(netadr_s *address);
extern "C" unsigned short Iw6DirectPort();
extern "C" int Iw6DirectParse(const char *text, netadr_s *address, int allowZeroPort);
extern "C" int Iw6DirectSend(int length, const void *data, const netadr_s *to);
extern "C" int Iw6DirectReceive(netadr_s *from, msg_t *message);
extern "C" int Iw6DirectSameAddress(const netadr_s *a, const netadr_s *b, int comparePort);

// Shared-key mode: exactly 32 hexadecimal characters (128 random bits); returns 0 and clears the key on failure.
extern "C" int Iw6DirectSetKey(const char *hex);
