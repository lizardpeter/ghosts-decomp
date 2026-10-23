// Observed Win64 ABI, with opaque SDK objects and buffers.
#pragma once
using GdkQuery = int (*)(const void *, const void *, void **);
using GdkInit = int (*)(unsigned int, unsigned int);
using GdkInitEx = int (*)(unsigned long long, unsigned long long, unsigned long long);
using GdkReport = void (*)(int, const char *);
using GdkUninit = void (*)();
struct GdkRuntimeState
{
    unsigned long long lock;
    unsigned char initialized;
    unsigned char implicit;
    unsigned char padding[6];
    void *module;
    GdkQuery query;
    GdkInit initialize;
    GdkInitEx initializeEx;
    GdkReport report;
    GdkUninit uninitialize;
};
static_assert(sizeof(GdkRuntimeState) == 64, "Store runtime globals");
static_assert(__builtin_offsetof(GdkRuntimeState, module) == 16, "runtime module offset");
extern GdkRuntimeState gdkRuntime __asm__("iw6s@_external/gdk/xgameruntime.cpp@@runtime");
int sub_1406AEC18(unsigned long long flags);
int sub_1406AEE34();
int sub_1406AEE74(const void *family, const void *version, void **api);
extern "C" int XGameRuntimeInitialize();
extern "C" void XGameRuntimeUninitialize();
extern "C" void XThreadAssertNotTimeSensitive();
extern "C" int XGameGetXboxTitleId(unsigned int *title);
extern "C" bool XGameRuntimeIsFeatureAvailable(unsigned int feature);
extern "C" int XUserAddAsync(unsigned int options, void *async);
// Stack arguments are explicit qwords: this is a lowered forwarding contract.
extern "C" int XUserGetTokenAndSignatureAsync(void *user, unsigned int options,
    const char *method, const char *url, unsigned long long headerCount, const void *headers,
    unsigned long long bodySize, const void *body, void *async);
bool sub_1401A1930();

// Account/result forwarding observed in the Store binary; opaque SDK storage.
extern "C" int XUserAddResult(void *async, void **user);
extern "C" int XUserCheckPrivilege(void *user, unsigned int options, unsigned int privilege, bool *allowed, unsigned int *reason);
extern "C" int XUserGetId(void *user, unsigned long long *id);
extern "C" int XUserGetState(void *user, unsigned int *state);
extern "C" int XUserGetTokenAndSignatureResult(void *async, unsigned long long size, void *buffer, void **tokenResult, unsigned long long *used);
extern "C" int XUserGetTokenAndSignatureResultSize(void *async, unsigned long long *size);
extern "C" int XUserResolveIssueWithUiAsync(void *user, const char *url, void *async);
extern "C" int XUserResolveIssueWithUiResult(void *async);
extern "C" int XUserResolvePrivilegeWithUiAsync(void *user, unsigned int options, unsigned int privilege, void *async);
extern "C" int XUserResolvePrivilegeWithUiResult(void *async);
void sub_1401A1760(int frame);
void sub_14019F390();
void sub_1401A1320();
void sub_1401A1CA0();
extern "C" int XGameEventWrite(void *user, const char *scid, const char *session,
    const char *name, const char *dimensions, const char *measurements);
