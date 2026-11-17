// ui/ui_menu_load.h: the old menu system's structures as the zone loaders see them (src/ui/ui_menu_load_db.cpp).
// Generated from the PS4 server PDB's layouts (analysis/iw6_ds_ps4/pdb/types.h); every size matches the Microsoft
// Store build's loaders. docs/assets/menus.md describes them.
#pragma once

#include <stddef.h>

#include "database/db_stream_api.h"

enum expDataType : int;
enum operationEnum : int;

struct ConditionalScript;
struct ExpressionPersistentState;
struct ExpressionString;
struct ExpressionSupportingData;
struct ItemFloatExpression;
struct ItemKeyHandler;
struct Material;
struct MenuEventHandler;
struct MenuEventHandlerSet;
struct MenuList;
struct Operand;
struct SetLocalVarData;
struct Statement_s;
struct StaticDvar;
struct StaticDvarList;
struct StringList;
struct UIFunctionList;
struct columnInfo_s;
struct dvar_t;
struct editFieldDef_s;
struct expressionEntry;
struct itemDef_t;
struct listBoxDef_s;
struct menuData_t;
struct menuDef_t;
struct menuTransition;
struct multiDef_s;
struct newsTickerDef_s;
struct rectDef_s;
struct snd_alias_list_t;
struct textScrollDef_s;
struct windowDef_t;
typedef float vec2_t[2];

struct MenuList
{
	const char *name;                                       // +0x000
	int menuCount;                                          // +0x008
	menuDef_t **menus;                                      // +0x010
};
static_assert(sizeof(MenuList) == 0x18, "MenuList");
static_assert(offsetof(MenuList, name) == 0x0, "MenuList::name");
static_assert(offsetof(MenuList, menus) == 0x10, "MenuList::menus");

struct rectDef_s
{
	float x;                                                // +0x000
	float y;                                                // +0x004
	float w;                                                // +0x008
	float h;                                                // +0x00C
	unsigned char horzAlign;                                // +0x010
	unsigned char vertAlign;                                // +0x011
};
static_assert(sizeof(rectDef_s) == 0x14, "rectDef_s");

struct windowDef_t
{
	const char *name;                                       // +0x000
	rectDef_s rect;                                         // +0x008
	rectDef_s rectClient;                                   // +0x01C
	const char *group;                                      // +0x030
	int style;                                              // +0x038
	int border;                                             // +0x03C
	int ownerDraw;                                          // +0x040
	int ownerDrawFlags;                                     // +0x044
	float borderSize;                                       // +0x048
	int staticFlags;                                        // +0x04C
	int dynamicFlags[1];                                    // +0x050
	int nextTime;                                           // +0x054
	float foreColor[4];                                     // +0x058
	float backColor[4];                                     // +0x068
	float borderColor[4];                                   // +0x078
	float outlineColor[4];                                  // +0x088
	float disableColor[4];                                  // +0x098
	Material *background;                                   // +0x0A8
};
static_assert(sizeof(windowDef_t) == 0xB0, "windowDef_t");
static_assert(offsetof(windowDef_t, name) == 0x0, "windowDef_t::name");
static_assert(offsetof(windowDef_t, group) == 0x30, "windowDef_t::group");
static_assert(offsetof(windowDef_t, background) == 0xA8, "windowDef_t::background");

struct menuDef_t
{
	menuData_t *data;                                       // +0x000
	windowDef_t window;                                     // +0x008
	int itemCount;                                          // +0x0B8
	itemDef_t **items;                                      // +0x0C0
};
static_assert(sizeof(menuDef_t) == 0xC8, "menuDef_t");
static_assert(offsetof(menuDef_t, data) == 0x0, "menuDef_t::data");
static_assert(offsetof(menuDef_t, items) == 0xC0, "menuDef_t::items");

struct menuTransition
{
	int transitionType;                                     // +0x000
	int startTime;                                          // +0x004
	float startVal;                                         // +0x008
	float endVal;                                           // +0x00C
	float time;                                             // +0x010
	int endTriggerType;                                     // +0x014
};
static_assert(sizeof(menuTransition) == 0x18, "menuTransition");

struct menuData_t
{
	int fullScreen;                                         // +0x000
	int fadeCycle;                                          // +0x004
	float fadeClamp;                                        // +0x008
	float fadeAmount;                                       // +0x00C
	float fadeInAmount;                                     // +0x010
	float blurRadius;                                       // +0x014
	MenuEventHandlerSet *onOpen;                            // +0x018
	MenuEventHandlerSet *onCloseRequest;                    // +0x020
	MenuEventHandlerSet *onClose;                           // +0x028
	MenuEventHandlerSet *onESC;                             // +0x030
	MenuEventHandlerSet *onFocusDueToClose;                 // +0x038
	ItemKeyHandler *onKey;                                  // +0x040
	Statement_s *visibleExp;                                // +0x048
	const char *allowedBinding;                             // +0x050
	const char *soundName;                                  // +0x058
	float focusColor[4];                                    // +0x060
	Statement_s *rectXExp;                                  // +0x070
	Statement_s *rectYExp;                                  // +0x078
	Statement_s *rectWExp;                                  // +0x080
	Statement_s *rectHExp;                                  // +0x088
	Statement_s *openSoundExp;                              // +0x090
	Statement_s *closeSoundExp;                             // +0x098
	Statement_s *soundLoopExp;                              // +0x0A0
	int cursorItem[1];                                      // +0x0A8
	menuTransition scaleTransition[1];                      // +0x0AC
	menuTransition alphaTransition[1];                      // +0x0C4
	menuTransition xTransition[1];                          // +0x0DC
	menuTransition yTransition[1];                          // +0x0F4
	ExpressionSupportingData *expressionData;               // +0x110
	unsigned char priority;                                 // +0x118
};
static_assert(sizeof(menuData_t) == 0x120, "menuData_t");
static_assert(offsetof(menuData_t, onOpen) == 0x18, "menuData_t::onOpen");
static_assert(offsetof(menuData_t, onCloseRequest) == 0x20, "menuData_t::onCloseRequest");
static_assert(offsetof(menuData_t, onClose) == 0x28, "menuData_t::onClose");
static_assert(offsetof(menuData_t, onESC) == 0x30, "menuData_t::onESC");
static_assert(offsetof(menuData_t, onFocusDueToClose) == 0x38, "menuData_t::onFocusDueToClose");
static_assert(offsetof(menuData_t, onKey) == 0x40, "menuData_t::onKey");
static_assert(offsetof(menuData_t, visibleExp) == 0x48, "menuData_t::visibleExp");
static_assert(offsetof(menuData_t, allowedBinding) == 0x50, "menuData_t::allowedBinding");
static_assert(offsetof(menuData_t, soundName) == 0x58, "menuData_t::soundName");
static_assert(offsetof(menuData_t, rectXExp) == 0x70, "menuData_t::rectXExp");
static_assert(offsetof(menuData_t, rectYExp) == 0x78, "menuData_t::rectYExp");
static_assert(offsetof(menuData_t, rectWExp) == 0x80, "menuData_t::rectWExp");
static_assert(offsetof(menuData_t, rectHExp) == 0x88, "menuData_t::rectHExp");
static_assert(offsetof(menuData_t, openSoundExp) == 0x90, "menuData_t::openSoundExp");
static_assert(offsetof(menuData_t, closeSoundExp) == 0x98, "menuData_t::closeSoundExp");
static_assert(offsetof(menuData_t, soundLoopExp) == 0xA0, "menuData_t::soundLoopExp");
static_assert(offsetof(menuData_t, expressionData) == 0x110, "menuData_t::expressionData");

union itemDefData_t
{
	listBoxDef_s *listBox;                                  // +0x000
	editFieldDef_s *editField;                              // +0x000
	multiDef_s *multi;                                      // +0x000
	const char *enumDvarName;                               // +0x000
	newsTickerDef_s *ticker;                                // +0x000
	textScrollDef_s *scroll;                                // +0x000
	void *data;                                             // +0x000
};
static_assert(sizeof(itemDefData_t) == 0x8, "itemDefData_t");
static_assert(offsetof(itemDefData_t, listBox) == 0x0, "itemDefData_t::listBox");
static_assert(offsetof(itemDefData_t, editField) == 0x0, "itemDefData_t::editField");
static_assert(offsetof(itemDefData_t, multi) == 0x0, "itemDefData_t::multi");
static_assert(offsetof(itemDefData_t, enumDvarName) == 0x0, "itemDefData_t::enumDvarName");
static_assert(offsetof(itemDefData_t, ticker) == 0x0, "itemDefData_t::ticker");
static_assert(offsetof(itemDefData_t, scroll) == 0x0, "itemDefData_t::scroll");
static_assert(offsetof(itemDefData_t, data) == 0x0, "itemDefData_t::data");

struct itemDef_t
{
	windowDef_t window;                                     // +0x000
	rectDef_s textRect[1];                                  // +0x0B0
	int type;                                               // +0x0C4
	int dataType;                                           // +0x0C8
	int alignment;                                          // +0x0CC
	int fontEnum;                                           // +0x0D0
	int textAlignMode;                                      // +0x0D4
	float textalignx;                                       // +0x0D8
	float textaligny;                                       // +0x0DC
	float textscale;                                        // +0x0E0
	int textStyle;                                          // +0x0E4
	int gameMsgWindowIndex;                                 // +0x0E8
	int gameMsgWindowMode;                                  // +0x0EC
	const char *text;                                       // +0x0F0
	int itemFlags;                                          // +0x0F8
	menuDef_t *parent;                                      // +0x100
	MenuEventHandlerSet *mouseEnterText;                    // +0x108
	MenuEventHandlerSet *mouseExitText;                     // +0x110
	MenuEventHandlerSet *mouseEnter;                        // +0x118
	MenuEventHandlerSet *mouseExit;                         // +0x120
	MenuEventHandlerSet *action;                            // +0x128
	MenuEventHandlerSet *accept;                            // +0x130
	MenuEventHandlerSet *onFocus;                           // +0x138
	MenuEventHandlerSet *hasFocus;                          // +0x140
	MenuEventHandlerSet *leaveFocus;                        // +0x148
	const char *dvar;                                       // +0x150
	const char *dvarTest;                                   // +0x158
	ItemKeyHandler *onKey;                                  // +0x160
	const char *enableDvar;                                 // +0x168
	const char *localVar;                                   // +0x170
	int dvarFlags;                                          // +0x178
	snd_alias_list_t *focusSound;                           // +0x180
	float special;                                          // +0x188
	int cursorPos[1];                                       // +0x18C
	itemDefData_t typeData;                                 // +0x190
	int floatExpressionCount;                               // +0x198
	ItemFloatExpression *floatExpressions;                  // +0x1A0
	Statement_s *visibleExp;                                // +0x1A8
	Statement_s *disabledExp;                               // +0x1B0
	Statement_s *textExp;                                   // +0x1B8
	Statement_s *materialExp;                               // +0x1C0
	float glowColor[4];                                     // +0x1C8
	bool decayActive;                                       // +0x1D8
	int fxBirthTime;                                        // +0x1DC
	int fxLetterTime;                                       // +0x1E0
	int fxDecayStartTime;                                   // +0x1E4
	int fxDecayDuration;                                    // +0x1E8
	int lastSoundPlayedTime;                                // +0x1EC
	Statement_s *textAlignYExp;                             // +0x1F0
};
static_assert(sizeof(itemDef_t) == 0x1F8, "itemDef_t");
static_assert(offsetof(itemDef_t, text) == 0xF0, "itemDef_t::text");
static_assert(offsetof(itemDef_t, parent) == 0x100, "itemDef_t::parent");
static_assert(offsetof(itemDef_t, mouseEnterText) == 0x108, "itemDef_t::mouseEnterText");
static_assert(offsetof(itemDef_t, mouseExitText) == 0x110, "itemDef_t::mouseExitText");
static_assert(offsetof(itemDef_t, mouseEnter) == 0x118, "itemDef_t::mouseEnter");
static_assert(offsetof(itemDef_t, mouseExit) == 0x120, "itemDef_t::mouseExit");
static_assert(offsetof(itemDef_t, action) == 0x128, "itemDef_t::action");
static_assert(offsetof(itemDef_t, accept) == 0x130, "itemDef_t::accept");
static_assert(offsetof(itemDef_t, onFocus) == 0x138, "itemDef_t::onFocus");
static_assert(offsetof(itemDef_t, hasFocus) == 0x140, "itemDef_t::hasFocus");
static_assert(offsetof(itemDef_t, leaveFocus) == 0x148, "itemDef_t::leaveFocus");
static_assert(offsetof(itemDef_t, dvar) == 0x150, "itemDef_t::dvar");
static_assert(offsetof(itemDef_t, dvarTest) == 0x158, "itemDef_t::dvarTest");
static_assert(offsetof(itemDef_t, onKey) == 0x160, "itemDef_t::onKey");
static_assert(offsetof(itemDef_t, enableDvar) == 0x168, "itemDef_t::enableDvar");
static_assert(offsetof(itemDef_t, localVar) == 0x170, "itemDef_t::localVar");
static_assert(offsetof(itemDef_t, focusSound) == 0x180, "itemDef_t::focusSound");
static_assert(offsetof(itemDef_t, floatExpressions) == 0x1A0, "itemDef_t::floatExpressions");
static_assert(offsetof(itemDef_t, visibleExp) == 0x1A8, "itemDef_t::visibleExp");
static_assert(offsetof(itemDef_t, disabledExp) == 0x1B0, "itemDef_t::disabledExp");
static_assert(offsetof(itemDef_t, textExp) == 0x1B8, "itemDef_t::textExp");
static_assert(offsetof(itemDef_t, materialExp) == 0x1C0, "itemDef_t::materialExp");
static_assert(offsetof(itemDef_t, textAlignYExp) == 0x1F0, "itemDef_t::textAlignYExp");

struct columnInfo_s
{
	int xpos;                                               // +0x000
	int ypos;                                               // +0x004
	int width;                                              // +0x008
	int height;                                             // +0x00C
	int maxChars;                                           // +0x010
	int alignment;                                          // +0x014
};
static_assert(sizeof(columnInfo_s) == 0x18, "columnInfo_s");

struct listBoxDef_s
{
	int startPos[1];                                        // +0x000
	int endPos[1];                                          // +0x004
	int drawPadding;                                        // +0x008
	float elementWidth;                                     // +0x00C
	float elementHeight;                                    // +0x010
	int elementStyle;                                       // +0x014
	int numColumns;                                         // +0x018
	columnInfo_s columnInfo[16];                            // +0x01C
	MenuEventHandlerSet *onDoubleClick;                     // +0x1A0
	int notselectable;                                      // +0x1A8
	int noScrollBars;                                       // +0x1AC
	int usePaging;                                          // +0x1B0
	float selectBorder[4];                                  // +0x1B4
	Material *selectIcon;                                   // +0x1C8
	Statement_s *elementHeightExp;                          // +0x1D0
};
static_assert(sizeof(listBoxDef_s) == 0x1D8, "listBoxDef_s");
static_assert(offsetof(listBoxDef_s, onDoubleClick) == 0x1A0, "listBoxDef_s::onDoubleClick");
static_assert(offsetof(listBoxDef_s, selectIcon) == 0x1C8, "listBoxDef_s::selectIcon");
static_assert(offsetof(listBoxDef_s, elementHeightExp) == 0x1D0, "listBoxDef_s::elementHeightExp");

struct multiDef_s
{
	const char *dvarList[32];                               // +0x000
	const char *dvarStr[32];                                // +0x100
	float dvarValue[32];                                    // +0x200
	int count;                                              // +0x280
	int strDef;                                             // +0x284
};
static_assert(sizeof(multiDef_s) == 0x288, "multiDef_s");
static_assert(offsetof(multiDef_s, dvarList) == 0x0, "multiDef_s::dvarList");
static_assert(offsetof(multiDef_s, dvarStr) == 0x100, "multiDef_s::dvarStr");

struct editFieldDef_s
{
	float minVal;                                           // +0x000
	float maxVal;                                           // +0x004
	float stepVal;                                          // +0x008
	float range;                                            // +0x00C
	int maxChars;                                           // +0x010
	int maxCharsGotoNext;                                   // +0x014
	int maxPaintChars;                                      // +0x018
	int paintOffset;                                        // +0x01C
};
static_assert(sizeof(editFieldDef_s) == 0x20, "editFieldDef_s");

struct newsTickerDef_s
{
	int feedId;                                             // +0x000
	int speed;                                              // +0x004
	int spacing;                                            // +0x008
};
static_assert(sizeof(newsTickerDef_s) == 0xC, "newsTickerDef_s");

struct textScrollDef_s
{
	int startTime;                                          // +0x000
};
static_assert(sizeof(textScrollDef_s) == 0x4, "textScrollDef_s");

struct MenuEventHandlerSet
{
	int eventHandlerCount;                                  // +0x000
	MenuEventHandler **eventHandlers;                       // +0x008
};
static_assert(sizeof(MenuEventHandlerSet) == 0x10, "MenuEventHandlerSet");
static_assert(offsetof(MenuEventHandlerSet, eventHandlers) == 0x8, "MenuEventHandlerSet::eventHandlers");

union EventData
{
	const char *unconditionalScript;                        // +0x000
	ConditionalScript *conditionalScript;                   // +0x000
	MenuEventHandlerSet *elseScript;                        // +0x000
	SetLocalVarData *setLocalVarData;                       // +0x000
};
static_assert(sizeof(EventData) == 0x8, "EventData");
static_assert(offsetof(EventData, unconditionalScript) == 0x0, "EventData::unconditionalScript");
static_assert(offsetof(EventData, conditionalScript) == 0x0, "EventData::conditionalScript");
static_assert(offsetof(EventData, elseScript) == 0x0, "EventData::elseScript");
static_assert(offsetof(EventData, setLocalVarData) == 0x0, "EventData::setLocalVarData");

struct MenuEventHandler
{
	EventData eventData;                                    // +0x000
	unsigned char eventType;                                // +0x008
};
static_assert(sizeof(MenuEventHandler) == 0x10, "MenuEventHandler");

struct ConditionalScript
{
	MenuEventHandlerSet *eventHandlerSet;                   // +0x000
	Statement_s *eventExpression;                           // +0x008
};
static_assert(sizeof(ConditionalScript) == 0x10, "ConditionalScript");
static_assert(offsetof(ConditionalScript, eventHandlerSet) == 0x0, "ConditionalScript::eventHandlerSet");
static_assert(offsetof(ConditionalScript, eventExpression) == 0x8, "ConditionalScript::eventExpression");

struct SetLocalVarData
{
	const char *localVarName;                               // +0x000
	Statement_s *expression;                                // +0x008
};
static_assert(sizeof(SetLocalVarData) == 0x10, "SetLocalVarData");
static_assert(offsetof(SetLocalVarData, localVarName) == 0x0, "SetLocalVarData::localVarName");
static_assert(offsetof(SetLocalVarData, expression) == 0x8, "SetLocalVarData::expression");

struct ItemKeyHandler
{
	int key;                                                // +0x000
	MenuEventHandlerSet *action;                            // +0x008
	ItemKeyHandler *next;                                   // +0x010
};
static_assert(sizeof(ItemKeyHandler) == 0x18, "ItemKeyHandler");
static_assert(offsetof(ItemKeyHandler, action) == 0x8, "ItemKeyHandler::action");
static_assert(offsetof(ItemKeyHandler, next) == 0x10, "ItemKeyHandler::next");

struct ExpressionString
{
	const char *string;                                     // +0x000
};
static_assert(sizeof(ExpressionString) == 0x8, "ExpressionString");
static_assert(offsetof(ExpressionString, string) == 0x0, "ExpressionString::string");

// The operand packs its 8-byte union to 4 (Operand is 0xC bytes, its type at +8), as the game was built
#pragma pack(push, 4)
union operandInternalDataUnion
{
	int intVal;                                             // +0x000
	float floatVal;                                         // +0x000
	ExpressionString stringVal;                             // +0x000
	Statement_s *function;                                  // +0x000
};
static_assert(sizeof(operandInternalDataUnion) == 0x8, "operandInternalDataUnion");
static_assert(offsetof(operandInternalDataUnion, function) == 0x0, "operandInternalDataUnion::function");

struct Operand
{
	operandInternalDataUnion internals;                     // +0x000
	expDataType dataType;                                   // +0x008
};
static_assert(sizeof(Operand) == 0xC, "Operand");
#pragma pack(pop)

struct ExpressionPersistentState
{
	int flags;                                              // +0x000
	int playerDataKey[4];                                   // +0x004
	int lastExecuteTime[4];                                 // +0x014
	Operand lastResult[4];                                  // +0x024
};
static_assert(sizeof(ExpressionPersistentState) == 0x54, "ExpressionPersistentState");

struct Statement_s
{
	int numEntries;                                         // +0x000
	expressionEntry *entries;                               // +0x008
	ExpressionSupportingData *supportingData;               // +0x010
	ExpressionPersistentState persistentState;              // +0x018
};
static_assert(sizeof(Statement_s) == 0x70, "Statement_s");
static_assert(offsetof(Statement_s, entries) == 0x8, "Statement_s::entries");
static_assert(offsetof(Statement_s, supportingData) == 0x10, "Statement_s::supportingData");

union entryInternalData
{
	operationEnum op;                                       // +0x000
	Operand operand;                                        // +0x000
};
static_assert(sizeof(entryInternalData) == 0xC, "entryInternalData");

struct expressionEntry
{
	entryInternalData data;                                 // +0x000
	int type;                                               // +0x00C
};
static_assert(sizeof(expressionEntry) == 0x10, "expressionEntry");

struct UIFunctionList
{
	int totalFunctions;                                     // +0x000
	Statement_s **functions;                                // +0x008
};
static_assert(sizeof(UIFunctionList) == 0x10, "UIFunctionList");
static_assert(offsetof(UIFunctionList, functions) == 0x8, "UIFunctionList::functions");

struct StaticDvarList
{
	int numStaticDvars;                                     // +0x000
	StaticDvar **staticDvars;                               // +0x008
};
static_assert(sizeof(StaticDvarList) == 0x10, "StaticDvarList");
static_assert(offsetof(StaticDvarList, staticDvars) == 0x8, "StaticDvarList::staticDvars");

struct StringList
{
	int totalStrings;                                       // +0x000
	const char **strings;                                   // +0x008
};
static_assert(sizeof(StringList) == 0x10, "StringList");
static_assert(offsetof(StringList, strings) == 0x8, "StringList::strings");

struct ExpressionSupportingData
{
	UIFunctionList uifunctions;                             // +0x000
	StaticDvarList staticDvarList;                          // +0x010
	StringList uiStrings;                                   // +0x020
};
static_assert(sizeof(ExpressionSupportingData) == 0x30, "ExpressionSupportingData");

struct StaticDvar
{
	dvar_t *dvar;                                           // +0x000
	const char *dvarName;                                   // +0x008
};
static_assert(sizeof(StaticDvar) == 0x10, "StaticDvar");
static_assert(offsetof(StaticDvar, dvar) == 0x0, "StaticDvar::dvar");
static_assert(offsetof(StaticDvar, dvarName) == 0x8, "StaticDvar::dvarName");

struct ItemFloatExpression
{
	int target;                                             // +0x000
	Statement_s *expression;                                // +0x008
};
static_assert(sizeof(ItemFloatExpression) == 0x10, "ItemFloatExpression");
static_assert(offsetof(ItemFloatExpression, expression) == 0x8, "ItemFloatExpression::expression");

void Load_MenuList(bool atStreamStart);
void Load_MenuListPtr(bool atStreamStart);
void Load_menuDef_ptr(bool atStreamStart);
void Load_menuDef_t(bool atStreamStart);
void Load_menuData_t(bool atStreamStart);
void Load_windowDef_t(bool atStreamStart);
void Load_itemDef_t(bool atStreamStart);
void Load_itemDefData_t(bool atStreamStart);
void Load_listBoxDef_ptr(bool atStreamStart);
void Load_listBoxDef_t(bool atStreamStart);
void Load_editFieldDef_ptr(bool atStreamStart);
void Load_multiDef_ptr(bool atStreamStart);
void Load_newsTickerDef_ptr(bool atStreamStart);
void Load_textScrollDef_ptr(bool atStreamStart);
void Load_MenuEventHandlerSet(bool atStreamStart);
void Load_MenuEventHandlerSetPtr(bool atStreamStart);
void Load_ConditionalScriptPtr(bool atStreamStart);
void Load_SetLocalVarDataPtr(bool atStreamStart);
void Load_SetLocalVarData(bool atStreamStart);
void Load_ItemKeyHandler(bool atStreamStart);
void Load_StatementPtr(bool atStreamStart);
void Load_Statement(bool atStreamStart);
void Load_ExpressionString(bool atStreamStart);
void Load_ExpressionSupportingDataPtr(bool atStreamStart);
void Load_ExpressionSupportingData(bool atStreamStart);
void Load_UIFunctionList(bool atStreamStart);
void Load_StaticDvarList(bool atStreamStart);
void Load_StaticDvar(bool atStreamStart);
void Load_XString(bool atStreamStart);
void Load_XStringArray(bool atStreamStart, unsigned long long count);
