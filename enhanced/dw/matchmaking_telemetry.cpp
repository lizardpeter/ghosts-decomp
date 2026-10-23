// P0010: discard reconstructed matchmaking telemetry without account/SDK calls.
#include <string.h>
#include "dw/matchmaking_telemetry.h"

namespace
{
void DiscardTelemetry(MatchmakingTelemetryRecord *value)
{
    if (value)
    {
        memset(value, 0, sizeof(*value));
        value->bytes[0] = 3;
    }
    memset(telemetryActiveRing, 0, sizeof(telemetryActiveRing));
    memset(telemetrySnapshotRing, 0, sizeof(telemetrySnapshotRing));
    telemetryActiveIndex = 0;
    telemetrySnapshotCount = 0;
    telemetryCurrentSlot = 250;
    telemetrySampleCount = 0;
    telemetrySeenMatches = 0;
}
}

void sub_140199DA0(int controller, MatchmakingTelemetryRecord *value)
{
    DiscardTelemetry(value);
}

void sub_140199300(MatchmakingTelemetryRecord *value)
{
    DiscardTelemetry(value);
}

void sub_140199D70()
{
    DiscardTelemetry(&matchmakingTelemetry);
}

void sub_140199CC0()
{
    DiscardTelemetry(nullptr);
}

void sub_140199ED0(const unsigned long long *value)
{
}

void sub_140199480(const unsigned long long *value)
{
}
