// Ghosts enhanced S17/B0009: reject invalid key numbers in the actual
// original console/config bind handlers. Never link these adapters into
// faithful src/. The package redirects the original Store entrypoints here.
#include <ctype.h>
#include "client/client.h"
#include "qcommon/cmd.h"

// The enhanced translation unit also compiles source-linked PS4 helpers.
// Do NOT call those functions here: their key binding-name table can resolve
// to the reconstruction's deliberately unmapped 0x200000000 sentinel. The
// pinned Store binary carries the real name tables, so call its verified
// original read-only conversion/lookup helpers by their Store addresses.
// Matcher: analysis/iw6mp64_MSStore_ship/match/functions.tsv.
// This keeps the original game's binding semantics and avoids a native
// 0xC0000005 before the first menu frame.
static int StoreKey_StringToKeynum(const char *s)
{
    return reinterpret_cast<int (*)(const char *)>(0x140310C10ULL)(s);
}
static int StoreKey_GetBindingForCmd(const char *s)
{
    return reinterpret_cast<int (*)(const char *)>(0x140310810ULL)(s);
}
int Key_GetBinding(LocalClientNum_t, int);
void Key_SetBinding(LocalClientNum_t, int, int);

namespace
{
bool SafeKey(const char *text, int &key)
{
    key = StoreKey_StringToKeynum(text);
    // A single byte >=0x80 can sign-extend to -128..-1 in the original.
    // -1 is already a rejection sentinel, but -2..-128 become an OOB index.
    // Validate before tolower, Key_GetBinding or Key_SetBinding.
    return (unsigned int)key < 256;
}
}

// Replacements retain the Store functions' zero-argument Win64 ABI.
extern "C" void Iw6SecureUnbind()
{
    if (Cmd_Argc() != 2) return;
    int key;
    if (!SafeKey(Cmd_Argv(1), key)) return;
    Key_SetBinding(LOCAL_CLIENT_0, key, 0);
}

extern "C" void Iw6SecureBind()
{
    const int count = Cmd_Argc();
    if (count < 2) return;
    int key;
    if (!SafeKey(Cmd_Argv(1), key)) return;
    key = tolower(key);
    if (count == 2) return;
    const int binding = StoreKey_GetBindingForCmd(Cmd_Argv(2));
    if (binding) Key_SetBinding(LOCAL_CLIENT_0, key, binding);
}

extern "C" void Iw6SecureSwapBind()
{
    if (Cmd_Argc() != 3) return;
    int keys[2], bindings[2];
    for (int i = 0; i < 2; ++i)
    {
        if (!SafeKey(Cmd_Argv(i + 1), keys[i])) return;
        keys[i] = tolower(keys[i]);
        bindings[i] = Key_GetBinding(LOCAL_CLIENT_0, keys[i]);
        if (!bindings[i]) return;
    }
    Key_SetBinding(LOCAL_CLIENT_0, keys[0], bindings[1]);
    Key_SetBinding(LOCAL_CLIENT_0, keys[1], bindings[0]);
}
