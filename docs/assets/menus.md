# Menus (MenuList, menuDef_t)

The old menu system: menu files holding menus, each a window with items, event scripts and expressions. Ghosts
draws its interface with Lua; these remain for a few script and developer menus (the Extinction maps carry three).
`tools/fastfile/menu.py` loads them as the Microsoft Store build does and reads them (`python3
tools/fastfile/menu.py <zone.ff>` lists every menu file, menu and item).

| Type | Name | Size | Store loader |
|---|---|---|---|
| 0x1E | menufile | 0x18 | Load_MenuListPtr 140354980 → Load_MenuList 140354870 |
| 0x1F | menu | 0xC8 | Load_menuDef_ptr 140361710 → Load_menuDef_t 140361800 |

The matcher's names for most of these Store addresses are wrong (it pairs 140361800 with Load_itemDef_ptrArray and
14034F120 with Load_MenuList, although they are Load_menuDef_t and Load_GfxImage); the functions below are named by
what they load, against the PS4 PDB's layouts.

## Layout and loaders

| Store | Loads | Size | Notes |
|---|---|---|---|
| 140354870 | MenuList | 0x18 | name, menuCount (+8), menu pointers (+0x10, any non-null value: aligned 8), each a Load_menuDef_ptr |
| 140361800 | menuDef_t | 0xC8 | virtual block; menuData_t (+0, aligned 4), windowDef_t (+8), itemCount (+0xB8) item pointers (+0xC0, aligned 8), each item aligned 4 |
| 140361350 | menuData_t | 0x120 | expression data (+0x110), five event handler sets (onOpen +0x18, onClose +0x28, onCloseRequest +0x20, onESC +0x30, onFocusDueToClose +0x38, in that order), onKey (+0x40), visibleExp (+0x48), allowedBinding and soundName (+0x50, +0x58), seven expressions (+0x70..+0xA0) |
| 140362620 | windowDef_t | 0xB0 | name (+0), rect (+8), group (+0x30), background material (+0xA8) |
| 140360960 | itemDef_t | 0x1F8 | the window (+0), text (+0xF0), nine event handler sets (+0x108..+0x148), dvar, dvarTest, onKey (+0x160), enableDvar, localVar, focusSound (+0x180, a whole sound alias list), the type's data (+0x190), float expressions (+0x1A0, count +0x198), five expressions |
| 1403608B0 | itemDefData_t | 8 | by itemDef_t.type (+0xC4): 6 a list box (0x1D8: onDoubleClick, selectIcon, elementHeightExp), the edit field types (mask 0xC74E11: 0x20 bytes), 0xC a multi (0x288: two arrays of 32 strings), 0xD the dvar enum's name, 0x14 a news ticker (0xC), 0x15 a text scroll (4) |
| 140354640 | MenuEventHandlerSet | 0x10 | count (+0), handler pointers (+8, aligned 8), each 0x10 (aligned 4) by its kind (+8): 0 a script string, 1 a conditional script (expression, then handler set), 2 an else (handler set), 3..6 a local variable set (name, expression) |
| 1403521A0 | ItemKeyHandler | 0x18 | a linked list: key (+0), action (+8), next (+0x10) |
| 140357650 | Statement_s pointer | 8 | -1: a Statement_s follows (aligned 4); another value an offset |
| 140357510 | Statement_s | 0x70 | numEntries (+0) entries of 0x10 (+8): an operand (+0, 0xC) when the entry's type (+0xC) is non-zero, a string for dataType (+8) 2, a nested expression for 3; supporting data (+0x10) |
| 14034CCE0 | ExpressionSupportingData | 0x30 | UI functions (+0: count, expressions), static dvars (+0x10: count, {dvar, name}), strings (+0x20: count, strings) |

Pointers are "any non-null value: the data follows" except expressions and supporting data, which test for -1 and
are otherwise offsets to data loaded earlier (menus share expressions).

## C++

`src/ui/ui_menu_load_db.cpp` reconstructs every loader above, 30 functions, with `include/ui/ui_menu_load.h`
(the layouts, generated from the PS4 PDB). Each one matches the exe in `tests/differential/test_menu_load.py`, and
17 deliberate mutations were all caught (two only after the tests were widened: negative string counts, and a fake that leaves the stream 4-aligned). Points the C++ shows:

- The Store build inlines many of the generated array loaders:
  - in Load_MenuList and Load_menuDef_t: the menu and item pointer arrays;
  - in Load_MenuEventHandlerSet: the event handlers;
  - in Load_Statement: the expression entries;
  - in Load_itemDef_t: the float expressions, plus its statement pointers;
  - in Load_UIFunctionList and Load_StaticDvarList: the static dvar arrays;
  - the bodies of Load_multiDef_t and Load_ConditionalScript.
- Load_ItemKeyHandler walks its linked list in a loop. Each next handler is read with atStreamStart, then the loop
  repeats without it.
- Load_itemDefData_t tail-calls its type's loader with its own atStreamStart.
- The Operand packs its 8-byte value to 4 bytes, so the Operand is 0xC bytes with its type at +8.

## How it was checked

mp_alien_armory.ff (Nightfall: 2732 assets), which used to stop at its first menu file, walks whole with
`tools/fastfile/loaders.py` and equals the game (`tests/fastfile/zone_check.py --full`). One step happens at link
time: Load_MenuAsset (140372E50) sets every item's parent (+0x100) to the linked menu; `menu.load_menu_ptr`
does the same. Its
menu files are `ui/scriptmenus/start.menu`, `dev_vision_exec.menu` and `dev_vision_noloc.menu`, one menu with one
item each.

## Not established

| What | Status |
|---|---|
| Menus with list boxes, multis, key handlers or float expressions | not in the zones checked; their loaders are transcribed but unexercised against the game |
| Reading expressions back as text | the reader shows a placeholder for conditions |
