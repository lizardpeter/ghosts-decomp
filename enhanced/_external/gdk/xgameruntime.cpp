// P0007: source-linked offline startup; never enter the vendor runtime.
#include "gdk/runtime.h"

int sub_1406AEE34()
{
    return (int)0x89240100;
}

int sub_1406AEC18(unsigned long long flags)
{
    return (int)0x89240100;
}

int sub_1406AEE74(const void *family, const void *version, void **api)
{
    if (api)
        *api = nullptr;
    return (int)0x89240100;
}

extern "C" int XGameRuntimeInitialize()
{
    return (int)0x89240100;
}

extern "C" void XGameRuntimeUninitialize()
{
    gdkRuntime.initialized = 0;
    gdkRuntime.implicit = 0;
    gdkRuntime.module = nullptr;
    gdkRuntime.query = nullptr;
    gdkRuntime.initialize = nullptr;
    gdkRuntime.initializeEx = nullptr;
    gdkRuntime.report = nullptr;
    gdkRuntime.uninitialize = nullptr;
}

// P0008: refuse direct achievement/stat event submissions without SDK access.
extern "C" int XGameEventWrite(void *user, const char *scid, const char *session,
    const char *name, const char *dimensions, const char *measurements)
{
    return (int)0x89240100;
}
