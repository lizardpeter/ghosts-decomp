// Lowered Win64 ABI for SDK calls in the Store lobby wrappers.
#pragma once
void *DwServicesLobbyConstruct(void *storage) __asm__("??0bdLobbyService@@QEAA@XZ");
void DwServicesRegisterHandler(void *lobby, void *handler)
    __asm__("?registerEventHandler@bdLobbyService@@QEAAXPEAVbdLobbyEventHandler@@@Z");
void DwServicesLobbyPump(void *lobby) __asm__("?pump@bdLobbyService@@QEAAXXZ");
void *DwServicesContent(void *lobby) __asm__("?getContentStreaming@bdLobbyService@@QEAAPEAVbdContentStreaming@@XZ");
void *DwServicesCounter(void *lobby) __asm__("?getCounter@bdLobbyService@@QEAAPEAVbdCounter@@XZ");
void *DwServicesDML(void *lobby) __asm__("?getDML@bdLobbyService@@QEAAPEAVbdDML@@XZ");
void *DwServicesGroup(void *lobby) __asm__("?getGroup@bdLobbyService@@QEAAPEAVbdGroup@@XZ");
void DwServicesContentPump(void *content) __asm__("?pump@bdContentStreamingBase@@QEAAXXZ");
int sub_1407679F0(void *net);
void LiveAntiCheat_Pump(int controller);
void sub_1405D6E60(int controller);
bool sub_14045CFF0(int controller);
void Live_DemonwareDisconnectCleanup(int controller);
