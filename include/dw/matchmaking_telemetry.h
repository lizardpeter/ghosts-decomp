// Observed Store layouts; names/source placement are descriptive, originals unknown.
#pragma once
struct MatchmakingTelemetryRecord { unsigned char bytes[0x9C8]; };
static_assert(sizeof(MatchmakingTelemetryRecord) == 0x9C8, "Store telemetry record size");
void sub_140199300(MatchmakingTelemetryRecord *record);
void sub_140199DA0(int controller, MatchmakingTelemetryRecord *record);
void sub_140199ED0(const unsigned long long *value);
void sub_140199CC0();
void sub_140199480(const unsigned long long *value);
void sub_140199D70();
extern MatchmakingTelemetryRecord matchmakingTelemetry __asm__("iw6s@dw/matchmaking_telemetry.cpp@@record");
extern unsigned long long telemetryActiveRing[50] __asm__("iw6s@dw/matchmaking_telemetry.cpp@@activeRing");
extern unsigned long long telemetrySnapshotRing[50] __asm__("iw6s@dw/matchmaking_telemetry.cpp@@snapshotRing");
extern unsigned int telemetryActiveIndex __asm__("iw6s@dw/matchmaking_telemetry.cpp@@activeIndex");
extern unsigned int telemetrySnapshotCount __asm__("iw6s@dw/matchmaking_telemetry.cpp@@snapshotCount");
extern unsigned int telemetryCurrentSlot __asm__("iw6s@dw/matchmaking_telemetry.cpp@@currentSlot");
extern unsigned int telemetrySampleCount __asm__("iw6s@dw/matchmaking_telemetry.cpp@@sampleCount");
extern unsigned int telemetrySeenMatches __asm__("iw6s@dw/matchmaking_telemetry.cpp@@seenMatches");
