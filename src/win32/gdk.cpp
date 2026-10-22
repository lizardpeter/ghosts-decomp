// Store game-side GDK startup. Original source path and function name unknown.
#include <iw6_static.h>
#include "gdk/runtime.h"
#define IW6_SOURCE "win32/gdk.cpp"
IW6_STATIC char titleString[16] IW6_AT("", "titleString");
IW6_STATIC const char scidString[] IW6_AT("", "scidString");
IW6_STATIC const char *scidPointer IW6_AT("", "scidPointer");
IW6_STATIC unsigned char sdkConfig[] IW6_AT("", "sdkConfig");
IW6_STATIC unsigned char tasks[] IW6_AT("", "tasks");
extern "C" int MessageBoxW(void *window, const wchar_t *text, const wchar_t *caption, unsigned int type);
extern "C" char *_itoa(int value, char *buffer, int radix);
void sub_1406D6240(void *config);
void DwGdkConstructTasks(void *tasks, const char *name)
    __asm__("?TaskManager_ConstructTaskSet@@YAXPEAUOverlappedTaskSet@@PEBD@Z");
void sub_1401A12D0();
void sub_1401A85F0();
void sub_14019F3A0(unsigned int title);
void sub_1401A5770();
void sub_1401A1C70();
void sub_1401A2510();

bool sub_1401A1930()
{
    const int runtime = XGameRuntimeInitialize();
    if (runtime < 0)
    {
        if ((unsigned int)runtime + 0x76DBFEFFU < 2)
            MessageBoxW(nullptr, L"Game Runtime is not installed on this system or needs updating.",
                        L"CallofDutyGhost", 0x10);
        return false;
    }
    unsigned int title;
    if (XGameGetXboxTitleId(&title) < 0)
    {
        MessageBoxW(nullptr, L"Title ID not found in MicrosoftGameConfig.mgc file.", L"CallofDutyGhost", 0x10);
        return false;
    }
    _itoa((int)title, titleString, 10);
    scidPointer = scidString;
    sub_1406D6240(sdkConfig);
    DwGdkConstructTasks(tasks, "GDK tasks.");
    sub_1401A12D0();
    sub_1401A85F0();
    sub_14019F3A0(title);
    sub_1401A5770();
    sub_1401A1C70();
    sub_1401A2510();
    return true;
}
