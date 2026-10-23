// client/client.h: client-side input state (types and prototypes from the PS4 server PDB and MAP, iw6_ds_ps4).
#pragma once

struct dvar_t;

enum LocalClientNum_t
{
	LOCAL_CLIENT_INVALID = -1,
	LOCAL_CLIENT_0 = 0x0,
	LOCAL_CLIENT_LAST = 0x0,
	LOCAL_CLIENT_COUNT = 0x1,
};

enum keyNum_t
{
	K_NONE = 0x0000,
	K_FIRSTGAMEPADBUTTON_RANGE_1 = 0x0001,
	K_BUTTON_A = 0x0001,
	K_BUTTON_B = 0x0002,
	K_BUTTON_X = 0x0003,
	K_BUTTON_Y = 0x0004,
	K_BUTTON_LSHLDR = 0x0005,
	K_BUTTON_RSHLDR = 0x0006,
	K_LASTGAMEPADBUTTON_RANGE_1 = 0x0006,
	K_TAB = 0x0009,
	K_ENTER = 0x000d,
	K_FIRSTGAMEPADBUTTON_RANGE_2 = 0x000e,
	K_BUTTON_START = 0x000e,
	K_BUTTON_BACK = 0x000f,
	K_BUTTON_LSTICK = 0x0010,
	K_BUTTON_RSTICK = 0x0011,
	K_BUTTON_LTRIG = 0x0012,
	K_BUTTON_RTRIG = 0x0013,
	K_DPAD_UP = 0x0014,
	K_FIRSTDPAD = 0x0014,
	K_DPAD_DOWN = 0x0015,
	K_DPAD_LEFT = 0x0016,
	K_DPAD_RIGHT = 0x0017,
	K_BUTTON_LSTICK_ALTIMAGE = 0x0018,
	K_BUTTON_RSTICK_ALTIMAGE = 0x0019,
	K_LASTDPAD = 0x0017,
	K_LASTGAMEPADBUTTON_RANGE_2 = 0x0017,
	K_ESCAPE = 0x001b,
	K_FIRSTGAMEPADBUTTON_RANGE_3 = 0x001c,
	K_APAD_UP = 0x001c,
	K_FIRSTAPAD = 0x001c,
	K_APAD_DOWN = 0x001d,
	K_APAD_LEFT = 0x001e,
	K_APAD_RIGHT = 0x001f,
	K_LASTAPAD = 0x001f,
	K_LASTGAMEPADBUTTON_RANGE_3 = 0x001f,
	K_SPACE = 0x0020,
	K_BACKSPACE = 0x007f,
	K_ASCII_FIRST = 0x0080,
	K_ASCII_181 = 0x0080,
	K_ASCII_191 = 0x0081,
	K_ASCII_223 = 0x0082,
	K_ASCII_224 = 0x0083,
	K_ASCII_225 = 0x0084,
	K_ASCII_228 = 0x0085,
	K_ASCII_229 = 0x0086,
	K_ASCII_230 = 0x0087,
	K_ASCII_231 = 0x0088,
	K_ASCII_232 = 0x0089,
	K_ASCII_233 = 0x008a,
	K_ASCII_236 = 0x008b,
	K_ASCII_241 = 0x008c,
	K_ASCII_242 = 0x008d,
	K_ASCII_243 = 0x008e,
	K_ASCII_246 = 0x008f,
	K_ASCII_248 = 0x0090,
	K_ASCII_249 = 0x0091,
	K_ASCII_250 = 0x0092,
	K_ASCII_252 = 0x0093,
	K_END_ASCII_CHARS = 0x0094,
	K_COMMAND = 0x0096,
	K_CAPSLOCK = 0x0097,
	K_POWER = 0x0098,
	K_PAUSE = 0x0099,
	K_UPARROW = 0x009a,
	K_DOWNARROW = 0x009b,
	K_LEFTARROW = 0x009c,
	K_RIGHTARROW = 0x009d,
	K_ALT = 0x009e,
	K_CTRL = 0x009f,
	K_SHIFT = 0x00a0,
	K_INS = 0x00a1,
	K_DEL = 0x00a2,
	K_PGDN = 0x00a3,
	K_PGUP = 0x00a4,
	K_HOME = 0x00a5,
	K_END = 0x00a6,
	K_F1 = 0x00a7,
	K_F2 = 0x00a8,
	K_F3 = 0x00a9,
	K_F4 = 0x00aa,
	K_F5 = 0x00ab,
	K_F6 = 0x00ac,
	K_F7 = 0x00ad,
	K_F8 = 0x00ae,
	K_F9 = 0x00af,
	K_F10 = 0x00b0,
	K_F11 = 0x00b1,
	K_F12 = 0x00b2,
	K_F13 = 0x00b3,
	K_F14 = 0x00b4,
	K_F15 = 0x00b5,
	K_KP_HOME = 0x00b6,
	K_KP_UPARROW = 0x00b7,
	K_KP_PGUP = 0x00b8,
	K_KP_LEFTARROW = 0x00b9,
	K_KP_5 = 0x00ba,
	K_KP_RIGHTARROW = 0x00bb,
	K_KP_END = 0x00bc,
	K_KP_DOWNARROW = 0x00bd,
	K_KP_PGDN = 0x00be,
	K_KP_ENTER = 0x00bf,
	K_KP_INS = 0x00c0,
	K_KP_DEL = 0x00c1,
	K_KP_SLASH = 0x00c2,
	K_KP_MINUS = 0x00c3,
	K_KP_PLUS = 0x00c4,
	K_KP_NUMLOCK = 0x00c5,
	K_KP_STAR = 0x00c6,
	K_KP_EQUALS = 0x00c7,
	K_MOUSE1 = 0x00c8,
	K_MOUSE2 = 0x00c9,
	K_MOUSE3 = 0x00ca,
	K_MOUSE4 = 0x00cb,
	K_MOUSE5 = 0x00cc,
	K_MWHEELDOWN = 0x00cd,
	K_MWHEELUP = 0x00ce,
	K_AUX1 = 0x00cf,
	K_AUX2 = 0x00d0,
	K_AUX3 = 0x00d1,
	K_AUX4 = 0x00d2,
	K_AUX5 = 0x00d3,
	K_AUX6 = 0x00d4,
	K_AUX7 = 0x00d5,
	K_AUX8 = 0x00d6,
	K_AUX9 = 0x00d7,
	K_AUX10 = 0x00d8,
	K_AUX11 = 0x00d9,
	K_AUX12 = 0x00da,
	K_AUX13 = 0x00db,
	K_AUX14 = 0x00dc,
	K_AUX15 = 0x00dd,
	K_AUX16 = 0x00de,
	K_LAST_KEY = 0x00df,
};

struct KeyState
{
	int down;
	int repeats;
	int binding;
};

struct field_t
{
	int cursor;
	int scroll;
	int drawWidth;
	int widthInPixels;
	float charHeight;
	int fixedSize;
	char buffer[256];
};

enum LocSelInputState
{
	LOC_SEL_INPUT_NONE = 0x0,
	LOC_SEL_INPUT_CONFIRM = 0x1,
	LOC_SEL_INPUT_CANCEL = 0x2,
};

struct PlayerKeyState
{
	field_t chatField;
	int chat_team;
	int overstrikeMode;
	int anyKeyDown;
	KeyState keys[256];
	LocSelInputState locSelInputState;
};

struct keyname_t
{
	const char *name;
	int keynum;
};

enum connstate_t
{
	CA_DISCONNECTED = 0x0,
	CA_CINEMATIC = 0x1,
	CA_LOGO = 0x2,
	CA_CONNECTING = 0x3,
	CA_CHALLENGING = 0x4,
	CA_CONNECTED = 0x5,
	CA_SENDINGSTATS = 0x6,
	CA_SYNCHRONIZING_DATA = 0x7,
	CA_LOADING = 0x8,
	CA_PRIMED = 0x9,
	CA_ACTIVE = 0xA,
};

struct clientUIActive_t
{
	bool active;
	bool isRunning;
	bool cgameInitialized;
	bool cgameInitCalled;
	int keyCatchers;
	connstate_t connectionState;
	int nextScrollTime;
	int dpadNextTime;
	int dpadLatestKey;
	unsigned char itemsUnlocked[320];
	bool itemsUnlockedInited;
	bool itemsUnlockedLastGameDirty;
	unsigned short itemsUnlockedLastGame[16];
	int itemsUnlockedLastGameCount;
	unsigned char *itemsUnlockedBuffer;
	int itemsUnlockedLocalClientNum;
	int itemsUnlockedControllerIndex;
	int itemsUnlockedStatsSource;
};

// keyCatchers bits (values from the code; the names are Quake 3's where it has the same bit)
#define KEYCATCH_CONSOLE 0x1
#define KEYCATCH_LOCATION_SELECTION 0x8
#define KEYCATCH_UI 0x10
#define KEYCATCH_MESSAGE 0x20     // the chat line (Message_Key, Field_CharEvent on playerKeys.chatField)
#define KEYCATCH_UNKNOWN_40 0x40  // also stops menu-scroll repeat (CL_CheckForIgnoreDueToRepeat); name unknown. Store
                                  // build: an LUI menu takes the keys (CL_KeyEvent skips the bindings)

// UI_KeyEvent's key for a character (WM_CHAR) rather than a key (Quake 3's K_CHAR_FLAG)
#define K_CHAR_FLAG 0x400

struct vidConfig_t
{
	unsigned int sceneWidth;
	unsigned int sceneHeight;
	unsigned int displayWidth;
	unsigned int displayHeight;
	unsigned char omitRTFlags;
	bool letterbox4x3;  // Store build only (in the servers' padding): GfxWindowParms::letterbox4x3 (gfx_d3d)
	unsigned short shadowTileResSmall;
	unsigned short shadowTileResLarge;
	unsigned int displayFrequency[2];  // displayFreq_t: numerator, denominator
	unsigned int monitorWidth;
	unsigned int monitorHeight;
	int displayMode;
	float windowAspectRatio;
	float displayAspectRatio;
	float sceneAspectRatio;
	float aspectRatioScenePixel;
	float aspectRatioDisplayPixel;
};

// Only the leading fields of clientStatic_t (0xE9B00 bytes in the PS4 server; the Store build has the same offsets up
// to vidConfig). The rest is in the PDB.
struct clientStatic_t
{
	int quit;
	int hunkUsersStarted;
	char servername[256];
	int rendererStarted;
	int soundStarted;
	int inUpdateSound;
	int uiStarted;
	int frametime;
	float frametime_base;
	int realtime;
	bool gpuSyncedPrevFrame;
	bool inputUpdatedPrevFrame;
	unsigned char logo[0x20];       // clientLogo_t
	float mapCenter[3];
	int lastServerPinged;
	int pingedServerCount;
	int totalServersParsed;
	int pingUpdateSource;
	struct Material *whiteMaterial;
	struct Material *consoleMaterial;
	struct Font_s *consoleFont;
	vidConfig_t vidConfig;
};

// A controller's profile settings (GamerProfile_GetProfileSettings). Only the field the input code reads; 0xF2C
// bytes in the Store build, absent from the server PDB.
struct GamerSettingState
{
	unsigned char unknown0[0x44];
	bool invertedPitch;  // the profile's "invertedPitch" (profile_toggleInvertedPitch flips it)
	unsigned char unknown45[0x2BC - 0x45];
	bool gpadEnabled;  // the profile's "gpadEnabled": mouse movement is ignored while it is set
};

struct kbutton_t
{
	int down[2];
	unsigned int downtime;
	unsigned int msec;
	bool active;
	bool wasPressed;
};

enum kbuttons_t
{
	KB_LEFT = 0x0,
	KB_RIGHT = 0x1,
	KB_FORWARD = 0x2,
	KB_BACK = 0x3,
	KB_LOOKUP = 0x4,
	KB_LOOKDOWN = 0x5,
	KB_MOVELEFT = 0x6,
	KB_MOVERIGHT = 0x7,
	KB_STRAFE = 0x8,
	KB_SPEED = 0x9,
	KB_UP = 0xA,
	KB_DOWN = 0xB,
	KB_ANYUP = 0xC,
	KB_MLOOK = 0xD,
	KB_SPECTATE = 0xE,
	KB_SPECNEXT = 0xF,
	KB_SPECPREV = 0x10,
	KB_ATTACK = 0x11,
	KB_BREATH = 0x12,
	KB_ZOOM = 0x13,
	KB_FRAG = 0x14,
	KB_OFFHANDSECONDARY = 0x15,
	KB_MELEE = 0x16,
	KB_ACTIVATE = 0x17,
	KB_RELOAD = 0x18,
	KB_USE_RELOAD = 0x19,
	KB_PRONE = 0x1A,
	KB_CROUCH = 0x1B,
	KB_THROW = 0x1C,
	KB_SPRINT = 0x1D,
	KB_NIGHTVISION = 0x1E,
	KB_USE_ALTERNATE = 0x1F,
	KB_TALK = 0x20,
	KB_ATTACK_ACCESSIBLE = 0x21,
	KB_ADS_ACCESSIBLE = 0x22,
	NUM_BUTTONS = 0x23,
};

enum GamepadPhysicalAxis
{
	GPAD_PHYSAXIS_RSTICK_X = 0x0,
	GPAD_PHYSAXIS_RSTICK_Y = 0x1,
	GPAD_PHYSAXIS_LSTICK_X = 0x2,
	GPAD_PHYSAXIS_LSTICK_Y = 0x3,
	GPAD_PHYSAXIS_RTRIGGER = 0x4,
	GPAD_PHYSAXIS_LTRIGGER = 0x5,
	GPAD_PHYSAXIS_COUNT = 0x6,
	GPAD_PHYSAXIS_NONE = -1,
};

enum GamepadVirtualAxis
{
	GPAD_VIRTAXIS_SIDE = 0x0,
	GPAD_VIRTAXIS_FORWARD = 0x1,
	GPAD_VIRTAXIS_UP = 0x2,
	GPAD_VIRTAXIS_YAW = 0x3,
	GPAD_VIRTAXIS_PITCH = 0x4,
	GPAD_VIRTAXIS_ATTACK = 0x5,
	GPAD_VIRTAXIS_COUNT = 0x6,
	GPAD_VIRTAXIS_NONE = -1,
};

enum GamepadMapping
{
	GPAD_MAP_LINEAR = 0x0,
	GPAD_MAP_SQUARED = 0x1,
	GPAD_MAP_COUNT = 0x2,
	GPAD_MAP_NONE = -1,
};

struct GamepadVirtualAxisMapping
{
	GamepadPhysicalAxis physicalAxis;
	GamepadMapping mapType;
};

struct GpadAxesGlob
{
	int axesValues[6];
	GamepadVirtualAxisMapping virtualAxes[6];
};

enum uiMenuCommand_t
{
	UIMENU_NONE = 0x0,
	UIMENU_MAIN = 0x1,
	UIMENU_INGAME = 0x2,
	UIMENU_PREGAME = 0x3,
	UIMENU_POSTGAME = 0x4,
	UIMENU_SCRIPT_POPUP = 0x5,
	UIMENU_SCOREBOARD = 0x6,
	UIMENU_CONTROLLERREMOVED = 0x7,
	UIMENU_MIGRATION = 0x8,
	UIMENU_MLG_SPECTATOR = 0x9,
};

// Globals (defined in the files named; linked from the original binary in the hybrid build)
extern PlayerKeyState playerKeys[1];         // client/cl_keys.cpp
extern keyname_t keynames[];                  // client/cl_keys.cpp
extern keyname_t keynames_localized[];        // client/cl_keys.cpp
extern const char *frenchNumberKeysMap[10];   // client/cl_keys.cpp
extern keyNum_t menuScrollButtonList[8];      // client/cl_gamepad.cpp
extern clientUIActive_t clientUIActives[1];   // client_mp/cl_main_mp.cpp
extern clientStatic_t cls;                    // client_mp/cl_main_mp.cpp
extern unsigned int frame_msec;               // client_mp/cl_main_mp.cpp
extern int cl_multi_gamepads_enabled;         // client/splitscreen.cpp
extern const dvar_t *gpad_dpadDebounceTime;   // gamepad/gamepad_utility.cpp

// client/cl_keys.cpp
int Key_GetOverstrikeMode(LocalClientNum_t localClientNum);
void Key_SetOverstrikeMode(LocalClientNum_t localClientNum, int state);
int Key_IsDown(LocalClientNum_t localClientNum, int keynum);
int Key_StringToKeynum(const char *str);
bool Key_IsValidGamePadChar(const char key);
const char *Key_KeynumToString(int keynum, int translate, int gamePadOnly);
void Key_SetBinding(LocalClientNum_t localClientNum, int keynum, int binding);
int Key_GetBindingForCmd(const char *command);
int Key_GetBinding(LocalClientNum_t localClientNum, int keynum);
int Key_GetCommandAssignmentInternal(LocalClientNum_t localClientNum, const char *command, int *const twokeys,
                                     int gamePadOnly);
int Key_GetCommandAssignment(LocalClientNum_t localClientNum, const char *command, int *const twokeys);
void Key_Unbind_f();
void Key_Unbindall_f();
void Key_Bind_f();
void Key_SwapBind_f();
void CL_InitKeyCommands();
void Key_ClearStates(LocalClientNum_t localClientNum);
int CL_GetKeyBindingInternal(LocalClientNum_t localClientNum, const char *command, char (*const keyNames)[128],
                             int gamePadOnly);
int CL_GetGamePadBinding(LocalClientNum_t localClientNum, const char *command, char (*const keyNames)[128]);
void Key_Shutdown();
bool Key_IsCatcherActive(LocalClientNum_t localClientNum, int mask);
void Key_RemoveCatcher(LocalClientNum_t localClientNum, int andMask);
void Key_SetCatcher(LocalClientNum_t localClientNum, int catcher);
void CL_KeyEvent(LocalClientNum_t localClientNum, int key, int down, unsigned int time);
void CL_CharEvent(LocalClientNum_t localClientNum, int key);

// client/cl_gamepad.cpp
void CL_InitGamepadCommands();
void CL_InitGamepadAxisBindings();
void Axis_Bind_f();
void Axis_Unbindall_f();
bool CL_CheckForIgnoreDueToRepeat(LocalClientNum_t localClientNum, int key, int repeatCount, int time);
void CL_GamepadButtonEvent(LocalClientNum_t localClientNum, int controllerIndex, int key, int down, unsigned int time);

// client_mp/cl_input.cpp
void CL_UseReload(LocalClientNum_t localClientNum, int key);
void CL_SpecPrev(LocalClientNum_t localClientNum, int key);
void CL_SpecNext(LocalClientNum_t localClientNum, int key);
void CL_ToggleSpec(LocalClientNum_t localClientNum, int key);
void CL_ExecBinding(LocalClientNum_t localClientNum, int binding, int key, int prevDown);  // empty in the server build

// elsewhere
int CL_GetFirstActiveControllerIndex();                             // client/splitscreen.cpp
GamerSettingState *GamerProfile_GetProfileSettings(int controllerIndex); // win32/win_gamerprofile.cpp
void UI_MouseEvent(LocalClientNum_t localClientNum, int x, int y);   // ui_mp/ui_main_mp.cpp
int CL_ControllerIndexFromClientNum(LocalClientNum_t clientNum);   // client/splitscreen.cpp
void Key_KeynumToStringBuf(int keynum, char *buf, int buflen, int gamePadOnly);  // client_mp/cl_ui_mp.cpp
uiMenuCommand_t UI_GetActiveMenu(LocalClientNum_t localClientNum); // ui_mp/ui_main_mp.cpp
void UI_KeyEvent(LocalClientNum_t localClientNum, int key, int down); // ui_mp/ui_main_mp.cpp
bool CG_TranslateGamepadButton(LocalClientNum_t localClientNum, int key, int binding); // cgame/cg_gamepad.cpp

// Inline from client/client.h: the UI globals of a local client. One local client in this build, and the code
// always indexes [0] (the parameter is not used in the shipped code).
inline clientUIActive_t *CL_GetLocalClientUIGlobals(LocalClientNum_t localClientNum)
{
	return &clientUIActives[0];
}
