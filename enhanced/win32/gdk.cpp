// P0007: do not initialize Xbox configuration, tasks or services at startup.
#include "gdk/runtime.h"

bool sub_1401A1930()
{
    return false;
}

// P0008: do not drive vendor sign-in, reporting, presence or save tasks.
#include "gdk/reporting_state.h"
void sub_1401A1760(int frame)
{
    gdkSignInAttempted = 0;
    gdkOnlineReady = 0;
}

void sub_14019F390()
{
}

void sub_1401A1CA0()
{
}

void sub_1401A1320()
{
    gdkSavePending = 0;
}
