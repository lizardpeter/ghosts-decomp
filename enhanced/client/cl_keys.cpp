// Security hardening for S17/B0009 (enhanced reconstruction only).
// The faithful implementation in src/client/cl_keys.cpp intentionally retains
// the original signed-char conversion and unchecked key-state indexing.
// WARNING: this source-linked replacement does not by itself redirect the
// unlocated native Store EXE call sites; see docs/security.md.
#include <string.h>
#include "client/client.h"
#include "qcommon/dvar.h"
#include "qcommon/qcommon.h"

namespace
{
bool ValidIndex(LocalClientNum_t client, int key)
{
    return client == LOCAL_CLIENT_0 && (unsigned int)key < 256U;
}
int HexDigit(unsigned char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
}

int Key_StringToKeynum(const char *str)
{
    if (!str || !str[0]) return -1;
    // The original returns signed char here. Bytes 0x80..0xFF become
    // negative indices and its bind handlers subsequently write out of bounds.
    // Keep extended keys available by explicit 0xNN names instead.
    if (!str[1])
    {
        const unsigned int byte = (unsigned char)str[0];
        return byte < 0x80 ? (int)byte : -1;
    }
    if (str[0] == '0' && str[1] == 'x' && str[2] && str[3] && !str[4])
    {
        const int hi = HexDigit((unsigned char)str[2]);
        const int lo = HexDigit((unsigned char)str[3]);
        return hi < 0 || lo < 0 ? -1 : hi * 16 + lo;
    }
    for (const keyname_t *kn = keynames; kn->name; ++kn)
        if (!I_stricmp(str, kn->name))
            return (unsigned int)kn->keynum < 256U ? kn->keynum : -1;
    return -1;
}

void Key_SetBinding(LocalClientNum_t client, int key, int binding)
{
    if (!ValidIndex(client, key)) return;
    playerKeys[client].keys[key].binding = binding;
    dvar_modifiedFlags |= DVAR_ARCHIVE;
}

int Key_GetBinding(LocalClientNum_t client, int key)
{
    return ValidIndex(client, key) ? playerKeys[client].keys[key].binding : 0;
}

int Key_IsDown(LocalClientNum_t client, int key)
{
    return ValidIndex(client, key) ? playerKeys[client].keys[key].down : 0;
}
