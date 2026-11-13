// P0022: custom launchers select the installation through WorkingDirectory.
// The original helper at 140548F90 instead caches the EXE's parent directory,
// which points to the separate package, not to the supplied game installation.
extern "C" __declspec(dllimport) unsigned int GetCurrentDirectoryA(unsigned int, char *);
extern "C" __declspec(dllimport) void AcquireSRWLockExclusive(void *);
extern "C" __declspec(dllimport) void ReleaseSRWLockExclusive(void *);

namespace
{
unsigned long long pathLock;
char gameDirectory[256];
bool pathReady;
}

extern "C" const char *Iw6LocalGameDirectory()
{
    AcquireSRWLockExclusive(&pathLock);
    if (!pathReady)
    {
        const unsigned int length = GetCurrentDirectoryA(sizeof(gameDirectory), gameDirectory);
        pathReady = length > 0 && length < sizeof(gameDirectory);
        if (!pathReady) gameDirectory[0] = 0;
    }
    const char *result = pathReady ? gameDirectory : nullptr;
    ReleaseSRWLockExclusive(&pathLock);
    return result;
}

// P0035: Win32 read-only FastFile I/O trace for the ENHANCED package.
// These two exact-signature IAT forwards preserve normal filesystem behavior.
// No redirection, substitution, relaxed content checks or synthetic success.
// The CI-only IW6_TRACE_FASTFILE_IO=1 switch emits debugger-visible evidence
// for the authentic ui_mp.ff open and its asynchronous file reads.
extern "C" __declspec(dllimport) void *CreateFileA(
    const char *, unsigned int, unsigned int, void *, unsigned int, unsigned int, void *);
extern "C" __declspec(dllimport) int ReadFileEx(
    void *, void *, unsigned int, void *, void *);
extern "C" __declspec(dllimport) unsigned int GetLastError();
extern "C" __declspec(dllimport) void SetLastError(unsigned int);
extern "C" __declspec(dllimport) unsigned int GetEnvironmentVariableA(
    const char *, char *, unsigned int);
extern "C" __declspec(dllimport) unsigned int GetFinalPathNameByHandleA(
    void *, char *, unsigned int, unsigned int);
extern "C" __declspec(dllimport) void OutputDebugStringA(const char *);

namespace
{
struct TraceText
{
    char value[672] = {};
    unsigned int length = 0;
    void Add(const char *s)
    {
        if (!s) return;
        while (*s && length < sizeof(value) - 1) value[length++] = *s++;
        value[length] = 0;
    }
    void Number(unsigned int x)
    {
        char digits[11];
        unsigned int n = 0;
        do { digits[n++] = (char)('0' + (x % 10)); x /= 10; } while (x && n < sizeof(digits));
        while (n && length < sizeof(value) - 1) value[length++] = digits[--n];
        value[length] = 0;
    }
};
bool TraceFastFile()
{
    char flag[2] = {};
    return GetEnvironmentVariableA("IW6_TRACE_FASTFILE_IO", flag, sizeof(flag)) == 1 &&
           flag[0] == '1';
}
bool IsUiFile(const char *path)
{
    if (!path) return false;
    const char target[] = "ui_mp.ff";
    for (const char *p = path; *p; ++p)
    {
        unsigned int i = 0;
        while (target[i] && p[i] &&
               (p[i] == target[i] ||
                (p[i] >= 'A' && p[i] <= 'Z' && p[i] + ('a' - 'A') == target[i])))
            ++i;
        if (!target[i]) return true;
    }
    return false;
}
void TraceResult(const char *verb, const char *path, unsigned int requested,
                 bool success, unsigned int error)
{
    TraceText s;
    s.Add("IW6IO:"); s.Add(verb);
    s.Add(" file="); s.Add(path ? path : "<unknown>");
    if (requested)
    {
        s.Add(" bytes="); s.Number(requested);
    }
    s.Add(" success="); s.Number(success ? 1u : 0u);
    s.Add(" last_error="); s.Number(error);
    OutputDebugStringA(s.value);
}
}
extern "C" void *Iw6TraceCreateFileA(
    const char *path, unsigned int access, unsigned int share, void *security,
    unsigned int disposition, unsigned int flags, void *templateFile)
{
    void *h = CreateFileA(path, access, share, security, disposition, flags, templateFile);
    const unsigned int error = GetLastError();
    if (TraceFastFile() && (IsUiFile(path) || h == (void *)-1))
        TraceResult("OPEN", path, 0, h != (void *)-1, error);
    SetLastError(error);
    return h;
}
extern "C" int Iw6TraceReadFileEx(
    void *file, void *buffer, unsigned int requested, void *overlapped, void *completion)
{
    const int success = ReadFileEx(file, buffer, requested, overlapped, completion);
    const unsigned int error = GetLastError();
    if (TraceFastFile())
    {
        char path[512] = {};
        const unsigned int count = GetFinalPathNameByHandleA(file, path, sizeof(path), 0);
        // If the read failed, record it even when the handle path is unavailable.
        if ((count && count < sizeof(path) && IsUiFile(path)) || !success)
            TraceResult("READ", count && count < sizeof(path) ? path : nullptr,
                        requested, success != 0, error);
    }
    SetLastError(error);
    return success;
}
