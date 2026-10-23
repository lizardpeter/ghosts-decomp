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
