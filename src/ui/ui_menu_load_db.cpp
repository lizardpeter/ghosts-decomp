// ui/ui_menu_load_db.cpp (Store build): the zone loaders of the old menu system, menu files (asset type 0x1E) and
// menus (0x1F), with the window, item, event handler, key handler and expression loaders under them. Generated
// loader code (the servers' PDB places it in gfx_d3d/r_material_load_db.h), tagged with Store addresses; the names
// and var globals are the Xbox One server's (the Store build inlines several of its array loaders, noted where it
// does). tools/fastfile/menu.py is the same in Python, checked against the game on real zones (docs/assets/menus.md);
// tests/differential/test_menu_load.py checks this file against the exe.

#include "ui/ui_menu_load.h"

// database/db_registry.cpp: register a loaded asset (DB_LinkXAssetEntry); Load_MenuAsset also points each item's
// parent at the linked menu
void Load_MenuListAsset(MenuList **asset);                         // Store 140372F60
void Load_MenuAsset(menuDef_t **asset);                            // Store 140372E50
// gfx_d3d/r_material_load_db.cpp and sound: the asset handles menus refer to
void Load_MaterialHandle(bool atStreamStart);                      // Store 140353700
void Load_snd_alias_list_ptr(bool atStreamStart);                  // Store 140361F10

extern Material **varMaterialHandle;                               // Store 144425D20
extern snd_alias_list_t **varsnd_alias_list_ptr;                   // Store 144426678
extern MenuList *varMenuList;                                      // Store 144426EE0
extern MenuList **varMenuListPtr;                                  // Store 144426EE8
extern menuDef_t **varmenuDef_ptr;                                 // Store 144426ED8
extern menuDef_t *varmenuDef_t;                                    // Store 144426ED0
extern menuData_t *varmenuData_t;                                  // Store 144426EC8
extern windowDef_t *varWindow;                                     // Store 144426E90
extern windowDef_t *varwindowDef_t;                                // Store 144426E88
extern itemDef_t **varitemDef_ptr;                                 // Store 144426EC0
extern itemDef_t *varitemDef_t;                                    // Store 144426EB8
extern itemDefData_t *varitemDefData_t;                            // Store 144426EA8
extern ItemFloatExpression *varItemFloatExpression;                // Store 144426EB0
extern listBoxDef_s **varlistBoxDef_ptr;                           // Store 144426E30
extern listBoxDef_s *varlistBoxDef_t;                              // Store 144426E28
extern editFieldDef_s **vareditFieldDef_ptr;                       // Store 144426E40
extern editFieldDef_s *vareditFieldDef_t;                          // Store 144426E38
extern multiDef_s **varmultiDef_ptr;                               // Store 144426E50
extern multiDef_s *varmultiDef_t;                                  // Store 144426E48
extern newsTickerDef_s **varnewsTickerDef_ptr;                     // Store 144426E60
extern newsTickerDef_s *varnewsTickerDef_t;                        // Store 144426E58
extern textScrollDef_s **vartextScrollDef_ptr;                     // Store 144426E70
extern textScrollDef_s *vartextScrollDef_t;                        // Store 144426E68
extern MenuEventHandlerSet **varMenuEventHandlerSetPtr;            // Store 144426DD8
extern MenuEventHandlerSet *varMenuEventHandlerSet;                // Store 144426E18
extern MenuEventHandler **varMenuEventHandlerPtr;                  // Store 144426E10
extern MenuEventHandler *varMenuEventHandler;                      // Store 144426E08
extern EventData *varEventData;                                    // Store 144426E00
extern ConditionalScript **varConditionalScriptPtr;                // Store 144426DE8
extern ConditionalScript *varConditionalScript;                    // Store 144426DE0
extern SetLocalVarData **varSetLocalVarDataPtr;                    // Store 144426DF8
extern SetLocalVarData *varSetLocalVarData;                        // Store 144426DF0
extern ItemKeyHandler *varItemKeyHandler;                          // Store 144426E98
extern ItemKeyHandler *varItemKeyHandlerNext;                      // Store 144426EA0
extern Statement_s **varStatementPtr;                              // Store 144426A88
extern Statement_s *varStatement;                                  // Store 144426AB8
extern expressionEntry *varexpressionEntry;                        // Store 144426A78
extern entryInternalData *varentryInternalData;                    // Store 144426A58
extern Operand *varOperand;                                        // Store 144426A48
extern operandInternalDataUnion *varoperandInternalDataUnion;      // Store 144426AC0
extern ExpressionString *varExpressionString;                      // Store 144426A38
extern ExpressionSupportingData **varExpressionSupportingDataPtr;  // Store 144426AB0
extern ExpressionSupportingData *varExpressionSupportingData;      // Store 144426AA8
extern UIFunctionList *varUIFunctionList;                          // Store 144426A90
extern StaticDvarList *varStaticDvarList;                          // Store 144426A80
extern StringList *varStringList;                                  // Store 144426A98
extern StaticDvar **varStaticDvarPtr;                              // Store 144426A70
extern StaticDvar *varStaticDvar;                                  // Store 144426A68

static inline unsigned char *AlignStreamPos(unsigned long long mask)
{
	g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + mask) & ~mask);
	return g_streamPos;
}

// varXString already points at the field: an inline string, or an offset
static inline void FixXString()
{
	if (!*varXString)
		return;
	if ((unsigned long long)*varXString == DB_PTR_FOLLOWING)
	{
		*varXString = (const char *)g_streamPos;
		varConstChar = (const char *)g_streamPos;
		Load_XStringCustom(varXString);
	}
	else
	{
		DB_ConvertOffsetToPointer((unsigned long long *)varXString);
	}
}

// An XString field, as the generated code inlines it (varXString = field; Load_Stream(false, field, 8); ...)
static inline void LoadXString(const char **field)
{
	varXString = field;
	Load_Stream(false, field, 8);
	FixXString();
}

// Load_MenuEventHandlerSetPtr(false) on a field, inlined
static inline void LoadEventHandlerSetField(MenuEventHandlerSet **field)
{
	varMenuEventHandlerSetPtr = field;
	Load_Stream(false, field, 8);
	if (*varMenuEventHandlerSetPtr)
	{
		*varMenuEventHandlerSetPtr = (MenuEventHandlerSet *)AlignStreamPos(3);
		varMenuEventHandlerSet = (MenuEventHandlerSet *)g_streamPos;
		Load_MenuEventHandlerSet(true);
	}
}

// Load_StatementPtr(false) on a field, inlined (Load_itemDef_t)
static inline void LoadStatementField(Statement_s **field)
{
	varStatementPtr = field;
	Load_Stream(false, field, 8);
	if (!*varStatementPtr)
		return;
	if ((unsigned long long)*varStatementPtr == DB_PTR_FOLLOWING)
	{
		*varStatementPtr = (Statement_s *)AlignStreamPos(3);
		varStatement = (Statement_s *)g_streamPos;
		Load_Statement(true);
	}
	else
	{
		DB_ConvertOffsetToPointer((unsigned long long *)varStatementPtr);
	}
}

// A pointer to a block of `size` plain bytes (aligned 4): editField, newsTicker, textScroll
#define LOAD_PLAIN_PTR(name, T, ptrVar, var)                                            \
	void Load_##name(bool atStreamStart)                                                \
	{                                                                                   \
		Load_Stream(atStreamStart, ptrVar, sizeof(T *));                                \
		if (*ptrVar)                                                                    \
		{                                                                               \
			*ptrVar = (T *)AlignStreamPos(3);                                           \
			var = (T *)g_streamPos;                                                     \
			Load_Stream(true, g_streamPos, sizeof(T));                                  \
		}                                                                               \
	}

// ---- strings ------------------------------------------------------------------------------------------------------

// Store 14035E950
void Load_XString(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXString, 8);
	FixXString();
}

// Store 14035E9C0
void Load_XStringArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varXString, count * 8);
	const char **str = varXString;
	for (; count; --count)
	{
		varXString = str;
		Load_Stream(false, str, 8);
		FixXString();
		++str;
	}
}

// Store 14034CC60
void Load_ExpressionString(bool atStreamStart)
{
	Load_Stream(atStreamStart, varExpressionString, sizeof(ExpressionString));
	LoadXString(&varExpressionString->string);
}

// ---- expressions --------------------------------------------------------------------------------------------------

// Store 140357650
void Load_StatementPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStatementPtr, sizeof(Statement_s *));
	if (!*varStatementPtr)
		return;
	if ((unsigned long long)*varStatementPtr == DB_PTR_FOLLOWING)
	{
		*varStatementPtr = (Statement_s *)AlignStreamPos(3);
		varStatement = (Statement_s *)g_streamPos;
		Load_Statement(true);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varStatementPtr);
}

// Store 140357510 (Load_expressionEntryArray inlined)
void Load_Statement(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStatement, sizeof(Statement_s));
	if (varStatement->entries)
	{
		varStatement->entries = (expressionEntry *)AlignStreamPos(3);
		varexpressionEntry = (expressionEntry *)g_streamPos;
		long long count = varStatement->numEntries;
		Load_Stream(true, g_streamPos, count << 4);
		expressionEntry *entry = varexpressionEntry;
		for (; count; --count)
		{
			varexpressionEntry = entry;
			Load_Stream(false, entry, sizeof(expressionEntry));
			varentryInternalData = &varexpressionEntry->data;
			if (varexpressionEntry->type)
			{
				varOperand = &varentryInternalData->operand;
				Load_Stream(false, varOperand, sizeof(Operand));
				varoperandInternalDataUnion = &varOperand->internals;
				unsigned int dataType = (unsigned int)varOperand->dataType;
				if (dataType > 1)
				{
					if (dataType == 2)
					{
						varExpressionString = &varoperandInternalDataUnion->stringVal;
						Load_ExpressionString(false);
					}
					else if (dataType == 3)
					{
						varStatementPtr = &varoperandInternalDataUnion->function;
						Load_StatementPtr(false);
					}
				}
			}
			++entry;
		}
	}
	varExpressionSupportingDataPtr = &varStatement->supportingData;
	Load_ExpressionSupportingDataPtr(false);
}

// Store 14034CDA0
void Load_ExpressionSupportingDataPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varExpressionSupportingDataPtr, sizeof(ExpressionSupportingData *));
	if (!*varExpressionSupportingDataPtr)
		return;
	if ((unsigned long long)*varExpressionSupportingDataPtr == DB_PTR_FOLLOWING)
	{
		*varExpressionSupportingDataPtr = (ExpressionSupportingData *)AlignStreamPos(3);
		varExpressionSupportingData = (ExpressionSupportingData *)g_streamPos;
		Load_ExpressionSupportingData(true);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)varExpressionSupportingDataPtr);
}

// Store 1403586C0 (Load_StatementPtrArray inlined)
void Load_UIFunctionList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varUIFunctionList, sizeof(UIFunctionList));
	if (!varUIFunctionList->functions)
		return;
	varUIFunctionList->functions = (Statement_s **)AlignStreamPos(7);
	varStatementPtr = (Statement_s **)g_streamPos;
	long long count = varUIFunctionList->totalFunctions;
	Load_Stream(true, g_streamPos, count * 8);
	Statement_s **slot = varStatementPtr;
	for (; count; --count)
	{
		varStatementPtr = slot;
		Load_StatementPtr(false);
		++slot;
	}
}

// Store 1403576D0
void Load_StaticDvar(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStaticDvar, sizeof(StaticDvar));
	LoadXString(&varStaticDvar->dvarName);
}

// Store 140357750 (Load_StaticDvarPtrArray inlined)
void Load_StaticDvarList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varStaticDvarList, sizeof(StaticDvarList));
	if (!varStaticDvarList->staticDvars)
		return;
	varStaticDvarList->staticDvars = (StaticDvar **)AlignStreamPos(7);
	varStaticDvarPtr = (StaticDvar **)g_streamPos;
	long long count = varStaticDvarList->numStaticDvars;
	Load_Stream(true, g_streamPos, count * 8);
	StaticDvar **slot = varStaticDvarPtr;
	for (; count; --count)
	{
		varStaticDvarPtr = slot;
		Load_Stream(false, slot, 8);
		if (*varStaticDvarPtr)
		{
			*varStaticDvarPtr = (StaticDvar *)AlignStreamPos(3);
			varStaticDvar = (StaticDvar *)g_streamPos;
			Load_StaticDvar(true);
		}
		++slot;
	}
}

// Store 14034CCE0
void Load_ExpressionSupportingData(bool atStreamStart)
{
	Load_Stream(atStreamStart, varExpressionSupportingData, sizeof(ExpressionSupportingData));
	varUIFunctionList = &varExpressionSupportingData->uifunctions;
	Load_UIFunctionList(false);
	varStaticDvarList = &varExpressionSupportingData->staticDvarList;
	Load_StaticDvarList(false);
	varStringList = &varExpressionSupportingData->uiStrings;
	Load_Stream(false, varStringList, sizeof(StringList));
	if (varStringList->strings)
	{
		varStringList->strings = (const char **)AlignStreamPos(7);
		varXString = (const char **)g_streamPos;
		Load_XStringArray(true, (long long)varStringList->totalStrings);
	}
}

// ---- event handlers -----------------------------------------------------------------------------------------------

// Store 140354640 (Load_MenuEventHandlerPtrArray and Load_MenuEventHandler inlined)
void Load_MenuEventHandlerSet(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMenuEventHandlerSet, sizeof(MenuEventHandlerSet));
	if (!varMenuEventHandlerSet->eventHandlers)
		return;
	varMenuEventHandlerSet->eventHandlers = (MenuEventHandler **)AlignStreamPos(7);
	varMenuEventHandlerPtr = (MenuEventHandler **)g_streamPos;
	long long count = varMenuEventHandlerSet->eventHandlerCount;
	Load_Stream(true, g_streamPos, count * 8);
	MenuEventHandler **slot = varMenuEventHandlerPtr;
	for (; count; --count)
	{
		varMenuEventHandlerPtr = slot;
		Load_Stream(false, slot, 8);
		if (*varMenuEventHandlerPtr)
		{
			*varMenuEventHandlerPtr = (MenuEventHandler *)AlignStreamPos(3);
			varMenuEventHandler = (MenuEventHandler *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(MenuEventHandler));
			varEventData = &varMenuEventHandler->eventData;
			unsigned char eventType = varMenuEventHandler->eventType;
			if (eventType == 0)
			{
				LoadXString(&varMenuEventHandler->eventData.unconditionalScript);
			}
			else if (eventType == 1)
			{
				varConditionalScriptPtr = &varMenuEventHandler->eventData.conditionalScript;
				Load_ConditionalScriptPtr(false);
			}
			else if (eventType == 2)
			{
				varMenuEventHandlerSetPtr = &varMenuEventHandler->eventData.elseScript;
				Load_MenuEventHandlerSetPtr(false);
			}
			else if ((unsigned char)(eventType - 3) < 4)
			{
				varSetLocalVarDataPtr = &varMenuEventHandler->eventData.setLocalVarData;
				Load_SetLocalVarDataPtr(false);
			}
		}
		++slot;
	}
}

// Store 140354810
void Load_MenuEventHandlerSetPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMenuEventHandlerSetPtr, sizeof(MenuEventHandlerSet *));
	if (*varMenuEventHandlerSetPtr)
	{
		*varMenuEventHandlerSetPtr = (MenuEventHandlerSet *)AlignStreamPos(3);
		varMenuEventHandlerSet = (MenuEventHandlerSet *)g_streamPos;
		Load_MenuEventHandlerSet(true);
	}
}

// Store 14034C030 (Load_ConditionalScript inlined)
void Load_ConditionalScriptPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varConditionalScriptPtr, sizeof(ConditionalScript *));
	if (!*varConditionalScriptPtr)
		return;
	*varConditionalScriptPtr = (ConditionalScript *)AlignStreamPos(3);
	varConditionalScript = (ConditionalScript *)g_streamPos;
	Load_Stream(true, g_streamPos, sizeof(ConditionalScript));
	varStatementPtr = &varConditionalScript->eventExpression;
	Load_StatementPtr(false);
	varMenuEventHandlerSetPtr = &varConditionalScript->eventHandlerSet;
	Load_MenuEventHandlerSetPtr(false);
}

// Store 140356C50
void Load_SetLocalVarData(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSetLocalVarData, sizeof(SetLocalVarData));
	LoadXString(&varSetLocalVarData->localVarName);
	varStatementPtr = &varSetLocalVarData->expression;
	Load_StatementPtr(false);
}

// Store 140356CE0
void Load_SetLocalVarDataPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSetLocalVarDataPtr, sizeof(SetLocalVarData *));
	if (*varSetLocalVarDataPtr)
	{
		*varSetLocalVarDataPtr = (SetLocalVarData *)AlignStreamPos(3);
		varSetLocalVarData = (SetLocalVarData *)g_streamPos;
		Load_SetLocalVarData(true);
	}
}

// Store 1403521A0: a linked list; the generated recursion through Load_ItemKeyHandlerNext became a loop
void Load_ItemKeyHandler(bool atStreamStart)
{
	for (;;)
	{
		Load_Stream(atStreamStart, varItemKeyHandler, sizeof(ItemKeyHandler));
		LoadEventHandlerSetField(&varItemKeyHandler->action);
		if (!varItemKeyHandler->next)
			return;
		varItemKeyHandler->next = (ItemKeyHandler *)AlignStreamPos(3);
		varItemKeyHandlerNext = (ItemKeyHandler *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(ItemKeyHandler));
		varItemKeyHandler = varItemKeyHandlerNext;
		atStreamStart = false;
	}
}

// ---- items --------------------------------------------------------------------------------------------------------

// Store 140362620
void Load_windowDef_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varwindowDef_t, sizeof(windowDef_t));
	LoadXString(&varwindowDef_t->name);
	LoadXString(&varwindowDef_t->group);
	varMaterialHandle = &varwindowDef_t->background;
	Load_MaterialHandle(false);
}

// Store 1403612A0
void Load_listBoxDef_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varlistBoxDef_t, sizeof(listBoxDef_s));
	LoadEventHandlerSetField(&varlistBoxDef_t->onDoubleClick);
	varMaterialHandle = &varlistBoxDef_t->selectIcon;
	Load_MaterialHandle(false);
	varStatementPtr = &varlistBoxDef_t->elementHeightExp;
	Load_StatementPtr(false);
}

// Store 140361240
void Load_listBoxDef_ptr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varlistBoxDef_ptr, sizeof(listBoxDef_s *));
	if (*varlistBoxDef_ptr)
	{
		*varlistBoxDef_ptr = (listBoxDef_s *)AlignStreamPos(3);
		varlistBoxDef_t = (listBoxDef_s *)g_streamPos;
		Load_listBoxDef_t(true);
	}
}

// Store 140360850
LOAD_PLAIN_PTR(editFieldDef_ptr, editFieldDef_s, vareditFieldDef_ptr, vareditFieldDef_t)
// Store 140361A20
LOAD_PLAIN_PTR(newsTickerDef_ptr, newsTickerDef_s, varnewsTickerDef_ptr, varnewsTickerDef_t)
// Store 140362470
LOAD_PLAIN_PTR(textScrollDef_ptr, textScrollDef_s, vartextScrollDef_ptr, vartextScrollDef_t)

// Store 140361980 (Load_multiDef_t inlined)
void Load_multiDef_ptr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varmultiDef_ptr, sizeof(multiDef_s *));
	if (!*varmultiDef_ptr)
		return;
	*varmultiDef_ptr = (multiDef_s *)AlignStreamPos(3);
	varmultiDef_t = (multiDef_s *)g_streamPos;
	Load_Stream(true, g_streamPos, sizeof(multiDef_s));
	varXString = varmultiDef_t->dvarList;
	Load_XStringArray(false, 32);
	varXString = varmultiDef_t->dvarStr;
	Load_XStringArray(false, 32);
}

// Store 1403608B0: by the item's type; each case is a tail call passing atStreamStart on
void Load_itemDefData_t(bool atStreamStart)
{
	unsigned int type = (unsigned int)varitemDef_t->type;
	if (type == 6)
	{
		varlistBoxDef_ptr = &varitemDefData_t->listBox;
		Load_listBoxDef_ptr(atStreamStart);
		return;
	}
	if (type < 0x18 && ((0xC74E11u >> (type & 0x1F)) & 1))
	{
		vareditFieldDef_ptr = &varitemDefData_t->editField;
		Load_editFieldDef_ptr(atStreamStart);
		return;
	}
	if (type == 0xC)
	{
		varmultiDef_ptr = &varitemDefData_t->multi;
		Load_multiDef_ptr(atStreamStart);
		return;
	}
	if (type == 0xD)
	{
		varXString = &varitemDefData_t->enumDvarName;
		Load_XString(atStreamStart);
		return;
	}
	if (type == 0x14)
	{
		varnewsTickerDef_ptr = &varitemDefData_t->ticker;
		Load_newsTickerDef_ptr(atStreamStart);
		return;
	}
	if (type == 0x15)
	{
		vartextScrollDef_ptr = &varitemDefData_t->scroll;
		Load_textScrollDef_ptr(atStreamStart);
	}
}

// Store 140360960 (Load_ItemFloatExpressionArray and the statement pointers inlined)
void Load_itemDef_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varitemDef_t, sizeof(itemDef_t));
	varWindow = &varitemDef_t->window;
	Load_Stream(false, varWindow, sizeof(windowDef_t));
	varwindowDef_t = varWindow;
	Load_windowDef_t(false);
	LoadXString(&varitemDef_t->text);
	LoadEventHandlerSetField(&varitemDef_t->mouseEnterText);
	LoadEventHandlerSetField(&varitemDef_t->mouseExitText);
	LoadEventHandlerSetField(&varitemDef_t->mouseEnter);
	LoadEventHandlerSetField(&varitemDef_t->mouseExit);
	LoadEventHandlerSetField(&varitemDef_t->action);
	LoadEventHandlerSetField(&varitemDef_t->accept);
	LoadEventHandlerSetField(&varitemDef_t->onFocus);
	LoadEventHandlerSetField(&varitemDef_t->hasFocus);
	LoadEventHandlerSetField(&varitemDef_t->leaveFocus);
	LoadXString(&varitemDef_t->dvar);
	LoadXString(&varitemDef_t->dvarTest);
	if (varitemDef_t->onKey)
	{
		varitemDef_t->onKey = (ItemKeyHandler *)AlignStreamPos(3);
		varItemKeyHandler = (ItemKeyHandler *)g_streamPos;
		Load_ItemKeyHandler(true);
	}
	LoadXString(&varitemDef_t->enableDvar);
	LoadXString(&varitemDef_t->localVar);
	varsnd_alias_list_ptr = &varitemDef_t->focusSound;
	Load_snd_alias_list_ptr(false);
	varitemDefData_t = &varitemDef_t->typeData;
	Load_itemDefData_t(false);
	if (varitemDef_t->floatExpressions)
	{
		varitemDef_t->floatExpressions = (ItemFloatExpression *)AlignStreamPos(3);
		varItemFloatExpression = (ItemFloatExpression *)g_streamPos;
		long long count = varitemDef_t->floatExpressionCount;
		Load_Stream(true, g_streamPos, count << 4);
		ItemFloatExpression *e = varItemFloatExpression;
		for (; count; --count)
		{
			varItemFloatExpression = e;
			Load_Stream(false, e, sizeof(ItemFloatExpression));
			LoadStatementField(&varItemFloatExpression->expression);
			++e;
		}
	}
	LoadStatementField(&varitemDef_t->visibleExp);
	LoadStatementField(&varitemDef_t->disabledExp);
	LoadStatementField(&varitemDef_t->textExp);
	LoadStatementField(&varitemDef_t->materialExp);
	LoadStatementField(&varitemDef_t->textAlignYExp);
}

// ---- menus --------------------------------------------------------------------------------------------------------

// Store 140361350: the handler sets in the order onOpen, onClose, onCloseRequest (the layout has onCloseRequest
// second)
void Load_menuData_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varmenuData_t, sizeof(menuData_t));
	varExpressionSupportingDataPtr = &varmenuData_t->expressionData;
	Load_ExpressionSupportingDataPtr(false);
	LoadEventHandlerSetField(&varmenuData_t->onOpen);
	LoadEventHandlerSetField(&varmenuData_t->onClose);
	LoadEventHandlerSetField(&varmenuData_t->onCloseRequest);
	LoadEventHandlerSetField(&varmenuData_t->onESC);
	LoadEventHandlerSetField(&varmenuData_t->onFocusDueToClose);
	if (varmenuData_t->onKey)
	{
		varmenuData_t->onKey = (ItemKeyHandler *)AlignStreamPos(3);
		varItemKeyHandler = (ItemKeyHandler *)g_streamPos;
		Load_ItemKeyHandler(true);
	}
	varStatementPtr = &varmenuData_t->visibleExp;
	Load_StatementPtr(false);
	LoadXString(&varmenuData_t->allowedBinding);
	LoadXString(&varmenuData_t->soundName);
	Statement_s **expressions[] = {&varmenuData_t->rectXExp, &varmenuData_t->rectYExp, &varmenuData_t->rectWExp,
	                               &varmenuData_t->rectHExp, &varmenuData_t->openSoundExp,
	                               &varmenuData_t->closeSoundExp, &varmenuData_t->soundLoopExp};
	for (Statement_s **field : expressions)
	{
		varStatementPtr = field;
		Load_StatementPtr(false);
	}
}

// Store 140361800 (Load_itemDef_ptrArray inlined)
void Load_menuDef_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varmenuDef_t, sizeof(menuDef_t));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	if (varmenuDef_t->data)
	{
		varmenuDef_t->data = (menuData_t *)AlignStreamPos(3);
		varmenuData_t = (menuData_t *)g_streamPos;
		Load_menuData_t(true);
	}
	varWindow = &varmenuDef_t->window;
	Load_Stream(false, varWindow, sizeof(windowDef_t));
	varwindowDef_t = varWindow;
	Load_windowDef_t(false);
	if (varmenuDef_t->items)
	{
		varmenuDef_t->items = (itemDef_t **)AlignStreamPos(7);
		varitemDef_ptr = (itemDef_t **)g_streamPos;
		long long count = varmenuDef_t->itemCount;
		Load_Stream(true, g_streamPos, count * 8);
		itemDef_t **slot = varitemDef_ptr;
		for (; count; --count)
		{
			varitemDef_ptr = slot;
			Load_Stream(false, slot, 8);
			if (*varitemDef_ptr)
			{
				*varitemDef_ptr = (itemDef_t *)AlignStreamPos(3);
				varitemDef_t = (itemDef_t *)g_streamPos;
				Load_itemDef_t(true);
			}
			++slot;
		}
	}
	DB_PopStreamPos();
}

// The generated Load_<T>Ptr: in the temp block, null stays null, an offset is an alias, -1 and -2 mean the asset
// follows (aligned 4), -2 also reserving an alias slot that receives the linked header.
#define LOAD_ASSET_PTR(fn, T, ptrVar, var, body, linker)                                \
	void fn(bool atStreamStart)                                                         \
	{                                                                                   \
		Load_Stream(atStreamStart, ptrVar, sizeof(T *));                                \
		DB_PushStreamPos(XFILE_BLOCK_TEMP);                                             \
		T **ptr = ptrVar;                                                               \
		unsigned long long value = (unsigned long long)*ptrVar;                         \
		if (value)                                                                      \
		{                                                                               \
			if (!DB_PTR_IS_INLINE(value))                                               \
			{                                                                           \
				DB_ConvertOffsetToAlias((unsigned long long *)ptrVar);                  \
				DB_PopStreamPos();                                                      \
				return;                                                                 \
			}                                                                           \
			*ptrVar = (T *)AlignStreamPos(3);                                           \
			var = (T *)g_streamPos;                                                     \
			unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr; \
			body(true);                                                                 \
			linker(ptr);                                                                \
			if (inserted)                                                               \
				*(T **)inserted = *ptr;                                                 \
		}                                                                               \
		DB_PopStreamPos();                                                              \
	}

// Store 140361710
LOAD_ASSET_PTR(Load_menuDef_ptr, menuDef_t, varmenuDef_ptr, varmenuDef_t, Load_menuDef_t, Load_MenuAsset)

// Store 140354870 (Load_menuDef_ptrArray inlined)
void Load_MenuList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMenuList, sizeof(MenuList));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	LoadXString(&varMenuList->name);
	if (varMenuList->menus)
	{
		varMenuList->menus = (menuDef_t **)AlignStreamPos(7);
		varmenuDef_ptr = (menuDef_t **)g_streamPos;
		long long count = varMenuList->menuCount;
		Load_Stream(true, g_streamPos, count * 8);
		menuDef_t **slot = varmenuDef_ptr;
		for (; count; --count)
		{
			varmenuDef_ptr = slot;
			Load_menuDef_ptr(false);
			++slot;
		}
	}
	DB_PopStreamPos();
}

// Store 140354980
LOAD_ASSET_PTR(Load_MenuListPtr, MenuList, varMenuListPtr, varMenuList, Load_MenuList, Load_MenuListAsset)
