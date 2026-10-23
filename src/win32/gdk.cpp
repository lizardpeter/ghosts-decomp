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

// Lowered call-site contracts; original subsystem names are unknown.
unsigned char sub_140222950() __asm__("?sub_140222950@@YAEXZ");
unsigned char sub_1401A7EA0(int controller) __asm__("?sub_1401A7EA0@@YAEH@Z");
unsigned char sub_1401A7ED0(int controller) __asm__("?sub_1401A7ED0@@YAEH@Z");
void sub_1401A8000(int controller) __asm__("?sub_1401A8000@@YAXH@Z");
int sub_1401A7DF0(int controller) __asm__("?sub_1401A7DF0@@YAHH@Z");
unsigned char sub_1401A7F20() __asm__("?sub_1401A7F20@@YAEXZ");
void sub_1401A5930(int controller, unsigned char force) __asm__("?sub_1401A5930@@YAXHE@Z");
int sub_1401A5740() __asm__("?sub_1401A5740@@YAHXZ");
unsigned char sub_1401A61A0() __asm__("?sub_1401A61A0@@YAEXZ");
unsigned char sub_1404523E0() __asm__("?sub_1404523E0@@YAEXZ");
void sub_1401A53E0(int frame) __asm__("?sub_1401A53E0@@YAXH@Z");
unsigned char sub_14031FF20(int controller) __asm__("?sub_14031FF20@@YAEH@Z");
void sub_140320100(int controller) __asm__("?sub_140320100@@YAXH@Z");
void sub_140320070(int controller) __asm__("?sub_140320070@@YAXH@Z");
void sub_1401A10E0(int controller) __asm__("?sub_1401A10E0@@YAXH@Z");
void sub_1401A1190(int controller) __asm__("?sub_1401A1190@@YAXH@Z");
void sub_140448B70(int controller) __asm__("?sub_140448B70@@YAXH@Z");
void sub_140447100(int controller) __asm__("?sub_140447100@@YAXH@Z");
void sub_140447340(int controller) __asm__("?sub_140447340@@YAXH@Z");
void sub_14044F240(int controller) __asm__("?sub_14044F240@@YAXH@Z");
void sub_140457A80(int controller) __asm__("?sub_140457A80@@YAXH@Z");
void sub_140452810(int controller) __asm__("?sub_140452810@@YAXH@Z");
void sub_140452830(int controller) __asm__("?sub_140452830@@YAXH@Z");
void sub_1405EC320(int controller) __asm__("?sub_1405EC320@@YAXH@Z");
void sub_1405F26B0(int controller) __asm__("?sub_1405F26B0@@YAXH@Z");
void sub_1405D6340(int controller) __asm__("?sub_1405D6340@@YAXH@Z");
void sub_1401A28C0(int controller) __asm__("?sub_1401A28C0@@YAXH@Z");
void sub_1405F3B10(int controller) __asm__("?sub_1405F3B10@@YAXH@Z");
void sub_1405D3DC0(unsigned char value) __asm__("?sub_1405D3DC0@@YAXE@Z");
void sub_140237000(int controller, int value) __asm__("?sub_140237000@@YAXHH@Z");
void sub_1401A8710() __asm__("?sub_1401A8710@@YAXXZ");
void sub_14019F940() __asm__("?sub_14019F940@@YAXXZ");
void sub_1401A2790() __asm__("?sub_1401A2790@@YAXXZ");
void sub_14045F4F0(void *tasks) __asm__("?sub_14045F4F0@@YAXPEAX@Z");
unsigned char sub_1406B1124(void *queue, unsigned int port, unsigned int timeout) __asm__("XTaskQueueDispatch");
IW6_STATIC unsigned char signInAttempted IW6_AT("", "signInAttempted");
IW6_STATIC unsigned char onlineReady IW6_AT("", "onlineReady");
IW6_STATIC unsigned char eventTasks[] IW6_AT("", "eventTasks");
IW6_STATIC void * presenceQueue IW6_AT("", "presenceQueue");
IW6_STATIC unsigned char presenceTasks[] IW6_AT("", "presenceTasks");
IW6_STATIC void * saveProvider IW6_AT("", "saveProvider");
IW6_STATIC unsigned char savePending IW6_AT("", "savePending");
IW6_STATIC void * saveQueue IW6_AT("", "saveQueue");
IW6_STATIC unsigned char saveTasks[] IW6_AT("", "saveTasks");

void sub_14019F390()
{
    sub_14045F4F0(eventTasks);
}

void sub_1401A1CA0()
{
    sub_1406B1124(presenceQueue, 1, 0);
    sub_14045F4F0(presenceTasks);
}

void sub_1401A1320()
{
    if (sub_1401A7EA0(0) && saveProvider && savePending)
    {
        if (sub_14031FF20(0))
            sub_140320100(0);
        sub_140320070(0);
        savePending = 0;
    }
    sub_1406B1124(saveQueue, 1, 0);
    sub_14045F4F0(saveTasks);
}

void sub_1401A1760(int frame)
{
    if (sub_140222950() && !sub_1401A7EA0(0) && !signInAttempted)
    {
        if (!sub_1401A7EA0(0) && !sub_1401A7ED0(0))
        {
            sub_1401A8000(0);
            signInAttempted = 1;
            onlineReady = 0;
        }
        else if (sub_1401A7DF0(0) == 0 && sub_1401A7F20())
            sub_1401A5930(0, 1);
    }
    if (sub_1401A7EA0(0) && signInAttempted)
    {
        if (sub_1401A5740() == 4 && sub_1401A61A0())
            onlineReady = 1;
        if (onlineReady)
        {
            sub_1401A10E0(0);
            sub_1401A1190(0);
            sub_1405D3DC0(0);
            sub_140448B70(0);
            sub_140447100(0);
            sub_140447340(0);
            sub_14044F240(0);
            if (!sub_1404523E0())
                sub_140457A80(0);
            sub_140452810(0);
            sub_140452830(0);
            sub_1405EC320(0);
            sub_1405F26B0(0);
            sub_1405D6340(0);
            sub_140237000(0, 1);
            sub_1401A28C0(0);
            signInAttempted = 0;
        }
        else
            sub_1405F3B10(0);
    }
    sub_14045F4F0(tasks);
    sub_1401A1320();
    sub_1401A8710();
    sub_14019F940();
    sub_14019F390();
    sub_1401A53E0(frame);
    sub_1401A1CA0();
    sub_1401A2790();
}
