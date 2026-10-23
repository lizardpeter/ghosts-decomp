// Faithful Store startup at 1405F0A80; the PS4 PDB confirms source/name.
// Vendor service behavior is retained here; custom profile removals are enhanced/.
#include "qcommon/cmd.h"

void LiveAntiCheat_ResetAllChallenges();
void LiveAntiCheat_BanCheck_f();
void sub_1405F0450(int controller); // original name unknown; caller establishes int ABI
extern cmd_function_s unk_14A084848; // original command-node name unknown

void LiveAntiCheat_Init()
{
    LiveAntiCheat_ResetAllChallenges();
    sub_1405F0450(0);
    Cmd_AddCommandInternal("banCheck", LiveAntiCheat_BanCheck_f, &unk_14A084848);
}
