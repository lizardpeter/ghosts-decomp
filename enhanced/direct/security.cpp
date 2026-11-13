// Enhanced direct profile: the legacy SOCKS5 client is never necessary.
// The original NET_OpenSocks uses a fixed 64-byte stack buffer for
// user-supplied credentials (B0025/S20). It is not safe to call.
// Only the canonical enhanced/direct executable redirects the original
// Store entry (14054F5B0) here. The faithful reconstruction is untouched.
extern "C" void Iw6DirectDisableSocks(int) {}
