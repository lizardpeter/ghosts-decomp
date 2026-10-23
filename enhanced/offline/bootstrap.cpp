// This entry point is linked only by --offline. Refuse an unprepared host image.
extern "C" __declspec(dllimport) void *GetModuleHandleW(const wchar_t *);
extern "C" __declspec(dllimport) void *GetCurrentProcess();
extern "C" __declspec(dllimport) int TerminateProcess(void *, unsigned int);
extern "C" int Iw6OfflineDllMain(void *module, unsigned int reason, void *)
{
    if (reason != 1) return 1;
    unsigned char *image = (unsigned char *)GetModuleHandleW(nullptr);
    bool valid = (unsigned long long)image == 0x140000000ULL &&
                 (unsigned long long)module == 0x180000000ULL;
    if (valid)
    {
        valid = *(unsigned short *)image == 0x5A4D;
        const unsigned int nt = *(unsigned int *)(image + 0x3C);
        valid = valid && nt < 0x400 && *(unsigned int *)(image + nt) == 0x4550;
        if (valid)
        {
            const unsigned int count = *(unsigned short *)(image + nt + 6);
            const unsigned int size = *(unsigned short *)(image + nt + 20);
            const unsigned char *section = image + nt + 24 + size;
            valid = false;
            if (count <= 32 && size == 240)
                for (unsigned int i = 0; i < count; ++i, section += 40)
                    if (*(unsigned long long *)section == 0x0066666F3677692EULL) // .iw6off
                    {
                        const unsigned int rva = *(unsigned int *)(section + 12);
                        if (rva >= 0xBC9E000 && rva + 16 <= *(unsigned int *)(image + nt + 24 + 56) && rva < 0xC000000)
                        {
                            const unsigned char *mark = image + rva;
                            valid = *(unsigned long long *)mark == 0x494C46464F365749ULL &&
                                    *(unsigned long long *)(mark + 8) == 0x000001000031454EULL;
                        }
                    }
        }
    }
    if (!valid) { TerminateProcess(GetCurrentProcess(), 0xE0010001); return 0; }
    return 1;
}
