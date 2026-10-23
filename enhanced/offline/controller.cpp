// P0021: no legacy XInput provider in the custom process. These Win64 adapters
// report ERROR_DEVICE_NOT_CONNECTED, without reading or writing caller buffers.
// XInput returns its error directly; it does not use Win32 GetLastError.
extern "C" unsigned int Iw6NoControllerState(unsigned int, void *) { return 1167; }
extern "C" unsigned int Iw6NoControllerCapabilities(unsigned int, unsigned int, void *) { return 1167; }
extern "C" unsigned int Iw6NoControllerVibration(unsigned int, const void *) { return 1167; }
