// Faithful Store runtime-library glue. Internal original names are unknown.
#include <iw6_static.h>
#include "gdk/runtime.h"
#define IW6_SOURCE "_external/gdk/xgameruntime.cpp"
IW6_STATIC const unsigned char coreIID[16] IW6_AT("", "coreIID");
IW6_STATIC const unsigned char featureIID[16] IW6_AT("", "featureIID");
IW6_STATIC const unsigned char gameFamily[16] IW6_AT("", "gameFamily");
IW6_STATIC const unsigned char gameVersion[16] IW6_AT("", "gameVersion");
IW6_STATIC const unsigned char userFamily[16] IW6_AT("", "userFamily");
IW6_STATIC const unsigned char userVersion[16] IW6_AT("", "userVersion");
extern "C" void AcquireSRWLockExclusive(void *lock);
extern "C" void ReleaseSRWLockExclusive(void *lock);
extern "C" void *LoadLibraryExA(const char *name, void *file, unsigned long flags);
extern "C" void *GetProcAddress(void *module, const char *name);
extern "C" int FreeLibrary(void *module);
extern "C" void DebugBreak();

int sub_1406AEE34()
{
    if (gdkRuntime.module)
        return 0;
    gdkRuntime.module = LoadLibraryExA("xgameruntime.dll", nullptr, 0x800);
    return gdkRuntime.module ? 0 : (int)0x89240101;
}

int sub_1406AEC18(unsigned long long flags)
{
    int result = 0;
    AcquireSRWLockExclusive(&gdkRuntime.lock);
    if (gdkRuntime.module || (result = sub_1406AEE34()) >= 0)
    {
        if (!gdkRuntime.query)
            gdkRuntime.query = (GdkQuery)GetProcAddress(gdkRuntime.module, "QueryApiImpl");
        if (!gdkRuntime.initialize)
            gdkRuntime.initialize = (GdkInit)GetProcAddress(gdkRuntime.module, "InitializeApiImpl");
        if (!gdkRuntime.initializeEx)
            gdkRuntime.initializeEx = (GdkInitEx)GetProcAddress(gdkRuntime.module, "InitializeApiImplEx");
        if (!gdkRuntime.report)
            gdkRuntime.report = (GdkReport)GetProcAddress(gdkRuntime.module, "XErrorReport");
        if (!gdkRuntime.uninitialize)
            gdkRuntime.uninitialize = (GdkUninit)GetProcAddress(gdkRuntime.module, "UninitializeApiImpl");
        if (!gdkRuntime.query || (!gdkRuntime.initialize && !gdkRuntime.initializeEx) ||
            !gdkRuntime.report || !gdkRuntime.uninitialize)
            result = (int)0x89240101;
        else if (!gdkRuntime.initializeEx && (flags & 1))
        {
            result = (int)0x89240100;
            gdkRuntime.report(result, "XGameRuntimeInitialize must be called before making this call.");
        }
        else if (!gdkRuntime.initialized || (gdkRuntime.implicit && !(flags & 1)))
        {
            result = gdkRuntime.initializeEx ?
                gdkRuntime.initializeEx(0x633600002711ULL, 0x633600000C6DULL, flags | 2) :
                gdkRuntime.initialize(0x6336, 0x2711);
            if (result >= 0)
            {
                gdkRuntime.initialized = 1;
                gdkRuntime.implicit = (unsigned char)(flags & 1);
            }
        }
    }
    if (result < 0 && ((*(volatile unsigned char *)0x7FFE02D4 & 3) == 3))
        DebugBreak();
    ReleaseSRWLockExclusive(&gdkRuntime.lock);
    return result;
}

int sub_1406AEE74(const void *family, const void *version, void **api)
{
    int result;
    if (!gdkRuntime.initialized)
    {
        result = sub_1406AEC18(1);
        if (result < 0)
            return result;
    }
    result = gdkRuntime.query(family, version, api);
    if (result == (int)0x80040154)
    {
        result = (int)0x89240107;
        if (gdkRuntime.report)
            gdkRuntime.report(result, "XGameRuntime is missing required dependencies, run GamingRepair.exe to resolve.");
    }
    return result;
}

extern "C" int XGameRuntimeInitialize()
{
    return sub_1406AEC18(0);
}

extern "C" void XGameRuntimeUninitialize()
{
    AcquireSRWLockExclusive(&gdkRuntime.lock);
    if (gdkRuntime.initialized && !gdkRuntime.implicit && gdkRuntime.uninitialize)
        gdkRuntime.uninitialize();
    gdkRuntime.query = nullptr;
    gdkRuntime.initialize = nullptr;
    gdkRuntime.initializeEx = nullptr;
    gdkRuntime.report = nullptr;
    gdkRuntime.uninitialize = nullptr;
    gdkRuntime.initialized = 0;
    gdkRuntime.implicit = 0;
    if (gdkRuntime.module)
    {
        FreeLibrary(gdkRuntime.module);
        gdkRuntime.module = nullptr;
    }
    ReleaseSRWLockExclusive(&gdkRuntime.lock);
}

namespace
{
void ReleaseApi(void *api)
{
    ((void (*)(void *))(*(void ***)api)[2])(api);
}
}

extern "C" void XThreadAssertNotTimeSensitive()
{
    void *api;
    if (sub_1406AEE74(coreIID, coreIID, &api) >= 0)
    {
        ((void (*)(void *))(*(void ***)api)[29])(api);
        ReleaseApi(api);
    }
}

extern "C" int XGameGetXboxTitleId(unsigned int *title)
{
    XThreadAssertNotTimeSensitive();
    void *api;
    int result = sub_1406AEE74(gameFamily, gameVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, unsigned int *))(*(void ***)api)[3])(api, title);
        ReleaseApi(api);
    }
    return result;
}

extern "C" bool XGameRuntimeIsFeatureAvailable(unsigned int feature)
{
    bool result = false;
    void *api;
    if (sub_1406AEE74(featureIID, featureIID, &api) >= 0)
    {
        result = ((bool (*)(void *, unsigned int))(*(void ***)api)[3])(api, feature);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserAddAsync(unsigned int options, void *async)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, unsigned int, void *))(*(void ***)api)[7])(api, options, async);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserGetTokenAndSignatureAsync(void *user, unsigned int options,
    const char *method, const char *url, unsigned long long headerCount, const void *headers,
    unsigned long long bodySize, const void *body, void *async)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned int, const char *, const char *,
            unsigned long long, const void *, unsigned long long, const void *, void *))
            (*(void ***)api)[23])(api, user, options, method, url, headerCount, headers, bodySize, body, async);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserAddResult(void *async, void **user)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, void **))(*(void ***)api)[8])(api, async, user);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserCheckPrivilege(void *user, unsigned int options, unsigned int privilege, bool *allowed, unsigned int *reason)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned int, unsigned int, bool *, unsigned int *))(*(void ***)api)[20])(api, user, options, privilege, allowed, reason);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserGetId(void *user, unsigned long long *id)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned long long *))(*(void ***)api)[11])(api, user, id);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserGetState(void *user, unsigned int *state)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned int *))(*(void ***)api)[14])(api, user, state);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserGetTokenAndSignatureResult(void *async, unsigned long long size, void *buffer, void **tokenResult, unsigned long long *used)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned long long, void *, void **, unsigned long long *))(*(void ***)api)[25])(api, async, size, buffer, tokenResult, used);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserGetTokenAndSignatureResultSize(void *async, unsigned long long *size)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned long long *))(*(void ***)api)[24])(api, async, size);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserResolveIssueWithUiAsync(void *user, const char *url, void *async)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, const char *, void *))(*(void ***)api)[29])(api, user, url, async);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserResolveIssueWithUiResult(void *async)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *))(*(void ***)api)[30])(api, async);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserResolvePrivilegeWithUiAsync(void *user, unsigned int options, unsigned int privilege, void *async)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, unsigned int, unsigned int, void *))(*(void ***)api)[21])(api, user, options, privilege, async);
        ReleaseApi(api);
    }
    return result;
}

extern "C" int XUserResolvePrivilegeWithUiResult(void *async)
{
    void *api;
    int result = sub_1406AEE74(userFamily, userVersion, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *))(*(void ***)api)[22])(api, async);
        ReleaseApi(api);
    }
    return result;
}

IW6_STATIC const unsigned char eventIID[16] IW6_AT("", "eventIID");
extern "C" int XGameEventWrite(void *user, const char *scid, const char *session,
    const char *name, const char *dimensions, const char *measurements)
{
    XThreadAssertNotTimeSensitive();
    void *api;
    int result = sub_1406AEE74(eventIID, eventIID, &api);
    if (result >= 0)
    {
        result = ((int (*)(void *, void *, const char *, const char *, const char *,
            const char *, const char *))(*(void ***)api)[3])(
                api, user, scid, session, name, dimensions, measurements);
        ReleaseApi(api);
    }
    return result;
}
