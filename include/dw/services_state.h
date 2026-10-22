// Observed Store storage; descriptive names, not complete SDK class layouts.
#pragma once
class bdLobbyService;
extern bdLobbyService *dwLobbyServiceCache __asm__("iw6s@dw/dwutils.cpp@@lobbyService");
extern unsigned char dwLobbyEventHandlers[4][8] __asm__("iw6s@dw/dwutils.cpp@@lobbyEventHandlers");
extern unsigned int dwLobbyActivity __asm__("iw6s@dw/dwutils.cpp@@lobbyActivity");
extern unsigned int dwDisconnectState __asm__("iw6s@dw/dwutils.cpp@@disconnectState");
extern unsigned int dwDisconnectReason __asm__("iw6s@dw/dwutils.cpp@@disconnectReason");
