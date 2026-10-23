// The few Win32 declarations the reconstruction uses (user32).
//
// Build environment, not game source. The original includes the Windows SDK; these are the same declarations,
// trimmed. In the hybrid build each function resolves to the original's import address table entry.
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#ifndef NULL
#define NULL 0
#endif

typedef int BOOL;
typedef unsigned int UINT;
typedef long LONG;
typedef unsigned long long WPARAM;
typedef long long LPARAM;
typedef struct HWND__ *HWND;
typedef struct HINSTANCE__ *HINSTANCE;
typedef struct HHOOK__ *HHOOK;

typedef struct tagPOINT
{
	LONG x;
	LONG y;
} POINT;

typedef struct tagRECT
{
	LONG left;
	LONG top;
	LONG right;
	LONG bottom;
} RECT;

#define WM_LBUTTONDOWN 0x0201
#define MK_LBUTTON 0x0001

typedef unsigned long DWORD;
typedef unsigned short USHORT;
typedef unsigned long ULONG;
typedef long long LRESULT;
typedef void *HANDLE;
typedef struct HRAWINPUT__ *HRAWINPUT;
typedef LRESULT (*WNDPROC)(HWND, UINT, WPARAM, LPARAM);
typedef DWORD (*LPTHREAD_START_ROUTINE)(void *);

typedef struct tagMSG
{
	HWND hwnd;
	UINT message;
	WPARAM wParam;
	LPARAM lParam;
	DWORD time;
	POINT pt;
} MSG;

typedef struct tagWNDCLASSA
{
	UINT style;
	WNDPROC lpfnWndProc;
	int cbClsExtra;
	int cbWndExtra;
	HINSTANCE hInstance;
	void *hIcon;
	void *hCursor;
	void *hbrBackground;
	const char *lpszMenuName;
	const char *lpszClassName;
} WNDCLASSA;

// Raw input (winuser.h)
typedef struct tagRAWINPUTDEVICE
{
	USHORT usUsagePage;
	USHORT usUsage;
	DWORD dwFlags;
	HWND hwndTarget;
} RAWINPUTDEVICE;

typedef struct tagRAWINPUTHEADER
{
	DWORD dwType;
	DWORD dwSize;
	HANDLE hDevice;
	WPARAM wParam;
} RAWINPUTHEADER;

typedef struct tagRAWMOUSE
{
	USHORT usFlags;
	union
	{
		ULONG ulButtons;
		struct
		{
			USHORT usButtonFlags;
			USHORT usButtonData;
		};
	};
	ULONG ulRawButtons;
	LONG lLastX;
	LONG lLastY;
	ULONG ulExtraInformation;
} RAWMOUSE;

typedef struct tagRAWINPUT
{
	RAWINPUTHEADER header;
	union
	{
		RAWMOUSE mouse;
		unsigned char other[24];  // RAWKEYBOARD, RAWHID: not used
	} data;
} RAWINPUT;

#define WM_INPUT 0x00FF
#define RIM_TYPEMOUSE 0
#define RID_INPUT 0x10000003
#define RIDEV_INPUTSINK 0x00000100
#define MOUSE_MOVE_ABSOLUTE 0x01
#define HID_USAGE_PAGE_GENERIC 0x01
#define HID_USAGE_GENERIC_MOUSE 0x02
#define HWND_MESSAGE ((HWND)(long long)-3)
#define INFINITE 0xFFFFFFFF
#define WAIT_OBJECT_0 0

BOOL RegisterRawInputDevices(const RAWINPUTDEVICE *pRawInputDevices, UINT uiNumDevices, UINT cbSize);
UINT GetRawInputData(HRAWINPUT hRawInput, UINT uiCommand, void *pData, UINT *pcbSize, UINT cbSizeHeader);

HWND GetForegroundWindow(void);
BOOL GetCursorPos(POINT *lpPoint);

DWORD timeGetTime(void);  // winmm (timeapi.h)

BOOL SetCursorPos(int X, int Y);
BOOL ClipCursor(const RECT *lpRect);
int ShowCursor(BOOL bShow);
BOOL GetWindowRect(HWND hWnd, RECT *lpRect);
BOOL GetClientRect(HWND hWnd, RECT *lpRect);
BOOL ScreenToClient(HWND hWnd, POINT *lpPoint);
BOOL ClientToScreen(HWND hWnd, POINT *lpPoint);
BOOL PostMessageA(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);

#define PM_NOREMOVE 0x0000
#define PM_REMOVE 0x0001
BOOL PeekMessageA(MSG *lpMsg, HWND hWnd, UINT wMsgFilterMin, UINT wMsgFilterMax, UINT wRemoveMsg);
BOOL GetMessageA(MSG *lpMsg, HWND hWnd, UINT wMsgFilterMin, UINT wMsgFilterMax);
BOOL TranslateMessage(const MSG *lpMsg);
LRESULT DispatchMessageA(const MSG *lpMsg);
void PostQuitMessage(int nExitCode);

#ifdef __cplusplus
}
#endif
