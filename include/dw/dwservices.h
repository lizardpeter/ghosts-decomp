#pragma once
class bdLobbyService;
class bdContentStreaming;
class bdCounter;
class bdDML;
class bdGroup;
bdLobbyService *dwGetActiveLobbyService();
bdLobbyService *dwGetLobbyService(int controller);
void dwLobbyPump(int controller);
bool dwIsBdNetReady();
bdContentStreaming *dwGetContentStreaming(int controller);
bdCounter *dwGetCounter(int controller);
bdDML *dwGetDML(int controller);
bdGroup *dwGetGroup(int controller);
void sub_1405DBFD0(int controller);
void sub_1405DBFF0();
void sub_1405DC010();
void sub_1405DC020(unsigned int reason);
