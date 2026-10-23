// P0011: startup-only failure boundaries for the experimental offline package.
// These are Win64 machine-ABI adapters; extra original arguments are ignored.
extern "C" __declspec(dllimport) void SetLastError(unsigned int error);
extern "C" __declspec(dllimport) void WSASetLastError(int error);
extern "C" __declspec(dllimport) void *GetProcAddress(void *, const char *);
extern "C" __declspec(dllimport) void *LoadLibraryA(const char *);
extern "C" __declspec(dllimport) void *LoadLibraryW(const wchar_t *);
extern "C" __declspec(dllimport) void *LoadLibraryExA(const char *, void *, unsigned int);
extern "C" __declspec(dllimport) void *LoadLibraryExW(const wchar_t *, void *, unsigned int);
extern "C" __declspec(dllimport) unsigned int GetModuleFileNameW(void *, wchar_t *, unsigned int);

namespace
{
unsigned int Lower(unsigned int c) { return c >= 'A' && c <= 'Z' ? c + 32 : c; }
template<class C> bool Same(const C *a, const char *b)
{
    while (*a && *b && Lower(*a) == Lower(*b)) { ++a; ++b; }
    return !*a && !*b;
}
template<class C> bool Blocked(const C *path)
{
    if (!path) return false;
    const C *base = path;
    for (const C *p = path; *p; ++p) if (*p == '/' || *p == '\\') base = p + 1;
    const char *names[] = {"xgameruntime", "xcurl", "winhttp", "wininet", "urlmon", "ws2_32"};
    for (const char *name : names)
    {
        const C *p = base; const char *q = name;
        while (*p && *q && Lower(*p) == Lower(*q)) { ++p; ++q; }
        if (!*q && (!*p || Same(p, ".dll"))) return true;
    }
    return false;
}
void Denied() { SetLastError(5); }
}

extern "C" int Iw6OfflineBootstrap() { return 1; }
extern "C" unsigned long long Iw6DenyNull() { Denied(); return 0; }
extern "C" unsigned long long Iw6DenyMinusOne() { Denied(); return ~0ULL; }
extern "C" int Iw6DenyStatus() { Denied(); return 5; }
extern "C" int Iw6DenyCurl() { Denied(); return 2; } // CURLE_FAILED_INIT
extern "C" int Iw6DenyCurlMulti() { Denied(); return 4; } // CURLM_INTERNAL_ERROR
extern "C" const char *Iw6OfflineErrorText() { return "Network disabled by offline build"; }
extern "C" unsigned long long Iw6DenySocket() { WSASetLastError(10013); return ~0ULL; }
extern "C" void *Iw6DenyDns() { WSASetLastError(10013); return nullptr; }
extern "C" int Iw6DenyAddrInfo(const char *, const char *, const void *, void **result)
{
    if (result) *result = nullptr;
    WSASetLastError(10013);
    return 10013;
}
extern "C" int Iw6DenyCom(const void *, void *, unsigned int, const void *, void **result)
{
    if (result) *result = nullptr;
    Denied(); return (int)0x80070005;
}
extern "C" int Iw6DenyEventRegister(const void *, void *, void *, unsigned long long *handle)
{
    if (handle) *handle = 0;
    Denied(); return 5;
}
extern "C" void *Iw6OfflineLoadLibraryA(const char *path)
{
    if (Blocked(path)) { Denied(); return nullptr; }
    return LoadLibraryA(path);
}
extern "C" void *Iw6OfflineLoadLibraryW(const wchar_t *path)
{
    if (Blocked(path)) { Denied(); return nullptr; }
    return LoadLibraryW(path);
}
extern "C" void *Iw6OfflineLoadLibraryExA(const char *path, void *file, unsigned int flags)
{
    if (Blocked(path)) { Denied(); return nullptr; }
    return LoadLibraryExA(path, file, flags);
}
extern "C" void *Iw6OfflineLoadLibraryExW(const wchar_t *path, void *file, unsigned int flags)
{
    if (Blocked(path)) { Denied(); return nullptr; }
    return LoadLibraryExW(path, file, flags);
}
extern "C" void *Iw6OfflineGetProcAddress(void *module, const char *name)
{
    wchar_t path[512];
    const unsigned int count = GetModuleFileNameW(module, path, 512);
    if (!count || count >= 512 || Blocked(path) ||
        ((unsigned long long)name > 0xFFFF &&
         (Same(name, "RoGetActivationFactory") || Same(name, "RoActivateInstance"))))
    { Denied(); return nullptr; }
    return GetProcAddress(module, name);
}
