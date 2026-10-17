// enhanced/win32/win_rawinput.cpp: raw mouse input (records/bugs.tsv B0010, B0011).
//
// The original aims with the system cursor's movement (GetCursorPos), after Windows' pointer speed and
// acceleration, sampled once a frame. Here a thread of its own owns a message-only window registered for the
// mouse's raw input (RIDEV_INPUTSINK, so input arrives whichever window is in front) and adds every relative
// report, in device counts, to two 64-bit counters. IN_MouseMove takes what has accumulated since the last
// frame. Nothing is lost between frames, nothing is rounded, and there is no other mouse mode.

#include "enhanced/raw_input.h"

// Win32 functions the original also imports (declared here, not in the shared windows.h shim, where some of
// the reconstruction declares them with its own spellings)
extern "C" {
unsigned short RegisterClassA(const WNDCLASSA *lpWndClass);
HWND CreateWindowExA(DWORD dwExStyle, const char *lpClassName, const char *lpWindowName, DWORD dwStyle, int X,
                     int Y, int nWidth, int nHeight, HWND hWndParent, void *hMenu, HINSTANCE hInstance,
                     void *lpParam);
LRESULT DefWindowProcA(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
BOOL GetMessageA(MSG *lpMsg, HWND hWnd, UINT wMsgFilterMin, UINT wMsgFilterMax);
LRESULT DispatchMessageA(const MSG *lpMsg);
HINSTANCE GetModuleHandleA(const char *lpModuleName);
HANDLE CreateThread(void *lpThreadAttributes, unsigned long long dwStackSize, LPTHREAD_START_ROUTINE lpStartAddress,
                    void *lpParameter, DWORD dwCreationFlags, DWORD *lpThreadId);
HANDLE CreateEventA(void *lpEventAttributes, BOOL bManualReset, BOOL bInitialState, const char *lpName);
BOOL SetEvent(HANDLE hEvent);
DWORD WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds);
BOOL CloseHandle(HANDLE hObject);
}

static long long s_rawDx;
static long long s_rawDy;
static bool s_rawInputActive;
static HANDLE s_rawInputReady;

void IN_RawInputAdd(const RAWMOUSE *mouse)
{
	if (mouse->usFlags & MOUSE_MOVE_ABSOLUTE)
		return;
	__atomic_fetch_add(&s_rawDx, (long long)mouse->lLastX, __ATOMIC_RELAXED);
	__atomic_fetch_add(&s_rawDy, (long long)mouse->lLastY, __ATOMIC_RELAXED);
}

void IN_TakeRawMouse(int *dx, int *dy)
{
	long long x = __atomic_exchange_n(&s_rawDx, 0, __ATOMIC_RELAXED);
	long long y = __atomic_exchange_n(&s_rawDy, 0, __ATOMIC_RELAXED);
	// a frame can't plausibly hold 2^31 counts; clamp rather than wrap
	*dx = x > 0x7FFFFFFF ? 0x7FFFFFFF : x < -0x7FFFFFFF ? -0x7FFFFFFF : (int)x;
	*dy = y > 0x7FFFFFFF ? 0x7FFFFFFF : y < -0x7FFFFFFF ? -0x7FFFFFFF : (int)y;
}

// WM_INPUT on the raw input thread's window
LRESULT IN_RawInputWndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
	if (msg == WM_INPUT)
	{
		RAWINPUT raw;
		UINT size = sizeof(raw);
		if (GetRawInputData((HRAWINPUT)lParam, RID_INPUT, &raw, &size, sizeof(RAWINPUTHEADER)) != (UINT)-1
		    && raw.header.dwType == RIM_TYPEMOUSE)
			IN_RawInputAdd(&raw.data.mouse);
	}
	return DefWindowProcA(hWnd, msg, wParam, lParam);  // also frees the WM_INPUT data
}

static DWORD IN_RawInputThread(void *)
{
	WNDCLASSA wc = {};
	wc.lpfnWndProc = IN_RawInputWndProc;
	wc.hInstance = GetModuleHandleA(nullptr);
	wc.lpszClassName = "IW6RawInput";
	RegisterClassA(&wc);
	HWND hWnd = CreateWindowExA(0, wc.lpszClassName, "", 0, 0, 0, 0, 0, HWND_MESSAGE, nullptr, wc.hInstance, nullptr);

	RAWINPUTDEVICE device;
	device.usUsagePage = HID_USAGE_PAGE_GENERIC;
	device.usUsage = HID_USAGE_GENERIC_MOUSE;
	device.dwFlags = RIDEV_INPUTSINK;
	device.hwndTarget = hWnd;
	s_rawInputActive = hWnd && RegisterRawInputDevices(&device, 1, sizeof(device));
	SetEvent(s_rawInputReady);
	if (!s_rawInputActive)
		return 1;

	MSG msg;
	while (GetMessageA(&msg, nullptr, 0, 0) > 0)
		DispatchMessageA(&msg);
	return 0;
}

bool IN_StartRawInput()
{
	if (s_rawInputActive)
		return true;
	s_rawInputReady = CreateEventA(nullptr, 1, 0, nullptr);
	HANDLE thread = CreateThread(nullptr, 0, IN_RawInputThread, nullptr, 0, nullptr);
	if (!thread)
		return false;
	WaitForSingleObject(s_rawInputReady, INFINITE);
	CloseHandle(thread);
	CloseHandle(s_rawInputReady);
	return s_rawInputActive;
}
