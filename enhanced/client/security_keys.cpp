// Ghosts enhanced S17/B0009: reject invalid key numbers in the actual
// original console/config bind handlers. Never link these adapters into
// faithful src/. The package redirects the original Store entrypoints here.
#include <ctype.h>
#include "client/client.h"
#include "qcommon/cmd.h"

int Key_StringToKeynum(const char *);
int Key_GetBindingForCmd(const char *);
int Key_GetBinding(LocalClientNum_t, int);
void Key_SetBinding(LocalClientNum_t, int, int);

namespace
{
bool SafeKey(const char *text, int &key)
{
    key = Key_StringToKeynum(text);
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
    const int binding = Key_GetBindingForCmd(Cmd_Argv(2));
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
