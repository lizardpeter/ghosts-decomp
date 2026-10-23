// Faithful Store matchmaking telemetry. Original names and source path unknown.
#include <iw6_static.h>
#include <string.h>
#include "dw/matchmaking_telemetry.h"
#include "dw/dwservices.h"
#define IW6_SOURCE "dw/matchmaking_telemetry.cpp"
IW6_STATIC MatchmakingTelemetryRecord record IW6_AT("", "record");
IW6_STATIC unsigned long long activeRing[50] IW6_AT("", "activeRing");
IW6_STATIC unsigned long long snapshotRing[50] IW6_AT("", "snapshotRing");
IW6_STATIC unsigned int activeIndex IW6_AT("", "activeIndex");
IW6_STATIC unsigned int snapshotCount IW6_AT("", "snapshotCount");
IW6_STATIC unsigned int currentSlot IW6_AT("", "currentSlot");
IW6_STATIC unsigned int sampleCount IW6_AT("", "sampleCount");
IW6_STATIC unsigned int seenMatches IW6_AT("", "seenMatches");
IW6_STATIC void *recordModeDvar IW6_AT("", "recordModeDvar");
IW6_STATIC void *samplingDvar IW6_AT("", "samplingDvar");
IW6_STATIC void *resetDvar IW6_AT("", "resetDvar");

// Lowered call-site ABI; SDK objects and serialized data remain opaque.
void sub_140536260(void *dst, int value, unsigned long long size);
int sub_14044FCC0();
void sub_140194780(int *count, unsigned short *pairs, unsigned int mask);
unsigned short sub_140194410();
unsigned short sub_140194910();
float sub_140530980(float minimum, float maximum);
unsigned char sub_1405F0700(int controller, int category);
unsigned char sub_140748BB0(void *lobby);
void *sub_1407463D0(void *lobby);
int sub_14044E130(const void *record, unsigned int size, void *buffer, unsigned int capacity);
void sub_140749C00(void *log, void **task, const void *data, unsigned int size,
                   unsigned int category, void *optional);
int Sys_Milliseconds();

void sub_140199300(MatchmakingTelemetryRecord *value)
{
    unsigned char *p = value->bytes;
    sub_140536260(p, 0, 0x9C8);
    sub_140536260(p + 0x1B8, 255, 0x7D0);
    for (unsigned int i = 0; i < 250; ++i)
        *(unsigned short *)(p + 0x1BE + 8*i) = 0;
    *(unsigned short *)p = 3;
    *(unsigned int *)(p + 0x1B4) = 0;
    *(unsigned int *)(p + 0x80) = 0xFFFFFFFF;
    p[2] = *((unsigned char *)recordModeDvar + 0x10);
    *(unsigned int *)(p + 0xB8) = 0;
    *(int *)(p + 0xB0) = sub_14044FCC0();
    currentSlot = 250;
    sampleCount = 0;
    activeIndex = 0;
    snapshotCount = 0;
    seenMatches = 0;
    memset(activeRing, 0, sizeof(activeRing));
    memset(snapshotRing, 0, sizeof(snapshotRing));
    p[0x9AC] = 255;
    unsigned short pairs[10];
    int count = 5;
    sub_140194780(&count, pairs, 0x3FFF);
    for (int i = 0; i < count; ++i)
    {
        const unsigned short first = pairs[2*i];
        const unsigned short second = pairs[2*i + 1];
        p[0x9AD + i] = first > 255 ? 255 : (unsigned char)first;
        p[0x9B2 + i] = (second & 0x7FFF) > 255 ? 255 : (unsigned char)second;
    }
    *(unsigned short *)(p + 0x9C0) = sub_140194410();
    *(unsigned short *)(p + 0x9C2) = sub_140194910();
}

void sub_140199DA0(int controller, MatchmakingTelemetryRecord *value)
{
    if (!value->bytes[1] || value->bytes[0] != 3)
        return;
    const float random = sub_140530980(0.0f, 1.0f);
    if (*(float *)((char *)samplingDvar + 0x10) > random || sub_1405F0700(controller, 9))
    {
        void *lobby = dwGetLobbyService(controller);
        if (lobby && sub_140748BB0(lobby))
        {
            void *log = sub_1407463D0(lobby);
            unsigned char buffer[0xC00];
            const int size = sub_14044E130(value, 0x9C8, buffer, sizeof(buffer));
            if (size > 0)
            {
                void *task;
                sub_140749C00(log, &task, buffer, (unsigned int)size, 5, nullptr);
                if (task)
                {
                    ((void (*)(void *))(*(void ***)task)[1])(task);
                    if (task)
                    {
                        const int old = __atomic_fetch_add((int *)((char *)task + 8), -1, __ATOMIC_SEQ_CST);
                        if (old == 1 && task)
                            ((void (*)(void *, unsigned int))(*(void ***)task)[0])(task, 1);
                    }
                }
            }
        }
    }
    sub_140199300(value);
}

void sub_140199ED0(const unsigned long long *value)
{
    const unsigned int index = activeIndex;
    activeRing[index] = *value;
    const unsigned int next = index + 1;
    activeIndex = next < 50 ? next : 0;
}

void sub_140199CC0()
{
    memcpy(snapshotRing, activeRing, sizeof(activeRing));
    snapshotCount = activeIndex;
    memset(activeRing, 0, sizeof(activeRing));
    activeIndex = 0;
}

void sub_140199480(const unsigned long long *value)
{
    for (int i = 0; i < 50; ++i)
    {
        if (snapshotRing[i] == *value)
        {
            ++seenMatches;
            return;
        }
    }
}

void sub_140199D70()
{
    if (*(int *)((char *)resetDvar + 0x10) == 1)
    {
        sub_140199300(&record);
        *(int *)(record.bytes + 0x90) = Sys_Milliseconds();
    }
}
