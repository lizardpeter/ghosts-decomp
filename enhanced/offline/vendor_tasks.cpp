// P0018: the custom offline/direct process does not participate in the vendor
// integrity service. No memory samples, fabricated responses or provider calls.
// Win64 callers may pass additional arguments; these boundaries never read them.
extern "C" void Iw6VendorTasksDisabled() {}
extern "C" int Iw6VendorChallengeUnavailable() { return 0; }
// Also cover future source-linked callers, not only original EXE entries.
void LiveAntiCheat_Init() {}
