#pragma once
// Custom-session identity, never a vendor account or proof of authentication.
extern "C" int Iw6DirectPlayerConfigure(const char *hexId, const char *name);
extern "C" unsigned long long Iw6DirectPlayerId(int controller);
extern "C" const char *Iw6DirectPlayerIdText(int controller);
extern "C" const char *Iw6DirectPlayerName(int controller);
