// qcommon/cm_load_db.h (Store build): the zone loaders of the collision map (clipMap_t) and the map entities.
//
// Generated loader functions (included into database/db_load.cpp; db_load.obj in the servers, whose PDBs give the
// names). Where the servers load a whole array and the Store build one element per call, the element loader keeps
// the generator's Load_<Type> name. The code is the Store build's, tagged with Store addresses.
// tools/fastfile/clipmap.py is the same logic in Python, checked against the game on real maps
// (docs/assets/collision.md).

#include "qcommon/cm_clipmap.h"
#include "database/db_stream_api.h"

void Load_ScriptStringCustom(scr_string_t *var);  // Store 14037AF90

extern MapTriggers *varMapTriggers;                        // Store 1444255E0
extern TriggerModel *varTriggerModel;                      // Store 1444255D8
extern TriggerHull *varTriggerHull;                        // Store 1444255D0
extern TriggerSlab *varTriggerSlab;                        // Store 1444255C8
extern ClientTriggers *varClientTriggers;                  // Store 1444255E8
extern ClientTriggerAabbNode *varClientTriggerAabbNode;    // Store 1444255C0
extern ClientTriggerBlend *varClientTriggerBlend;          // Store 1444255F8
extern ClientTriggerBlendNode *varClientTriggerBlendNode;  // Store 1444255F0
extern SpawnPointRecordList *varSpawnPointRecordList;      // Store 144425608
extern SpawnPointEntityRecord *varSpawnPointEntityRecord;  // Store 144425600
extern SplineRecordList *varSplineRecordList;              // Store 144425620
extern SplinePointRecordList *varSplinePointRecordList;    // Store 144425618
extern SplinePointEntityRecord *varSplinePointEntityRecord;  // Store 144425610
extern MapEnts *varMapEnts;                                // Store 144425628
extern cbrush_t *varcbrush_t;                              // Store 1444249A8
extern cbrush_t *varcbrush_array_t;                        // Store 144425580
extern cLeafBrushNode_s *varcLeafBrushNode_t;              // Store 144425558
extern cLeafBrushNodeData_t *varcLeafBrushNodeData_t;      // Store 144425550
extern cLeafBrushNodeLeaf_t *varcLeafBrushNodeLeaf_t;      // Store 144425540
extern unsigned short *varLeafBrush;                       // Store 144425598
extern ClipInfo *varClipInfo;                              // Store 1444255A8
extern ClipMaterial *varClipMaterial;                      // Store 1444255A0
extern Bounds *varBounds;                                  // Store 144425590
extern char *varchar;                                      // Store 144424A38
extern short *varshort;                                    // Store 144424CE8
extern unsigned char *varbyte;                             // Store 144424A18
extern float (*varvec3_t)[3];                              // Store 144424C88
extern float *varfloat;                                    // Store 144424B98
extern int *varint;                                        // Store 144424A88

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

static void Load_XStringField(const char **field)
{
	varXString = field;
	Load_Stream(false, varXString, 8);
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

// Store 140352E40
void Load_MapTriggers(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMapTriggers, sizeof(MapTriggers));
	if (varMapTriggers->models)
	{
		if ((unsigned long long)varMapTriggers->models == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varMapTriggers->models = (TriggerModel *)g_streamPos;
			varTriggerModel = (TriggerModel *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMapTriggers->count * sizeof(TriggerModel));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMapTriggers->models);
		}
	}
	if (varMapTriggers->hulls)
	{
		if ((unsigned long long)varMapTriggers->hulls == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varMapTriggers->hulls = (TriggerHull *)g_streamPos;
			varTriggerHull = (TriggerHull *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMapTriggers->hullCount * sizeof(TriggerHull));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMapTriggers->hulls);
		}
	}
	if (varMapTriggers->slabs)
	{
		if ((unsigned long long)varMapTriggers->slabs == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varMapTriggers->slabs = (TriggerSlab *)g_streamPos;
			varTriggerSlab = (TriggerSlab *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varMapTriggers->slabCount * sizeof(TriggerSlab));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varMapTriggers->slabs);
		}
	}
}

// Store 14034B0A0
void Load_ClientTriggers(bool atStreamStart)
{
	Load_Stream(atStreamStart, varClientTriggers, sizeof(ClientTriggers));
	varMapTriggers = &varClientTriggers->trigger;
	Load_MapTriggers(false);
	if (varClientTriggers->clientTriggerAabbTree)
	{
		ALIGN_POS(4);
		varClientTriggers->clientTriggerAabbTree = (ClientTriggerAabbNode *)g_streamPos;
		varClientTriggerAabbNode = (ClientTriggerAabbNode *)g_streamPos;
		Load_Stream(true, g_streamPos,
		            (unsigned long long)varClientTriggers->numClientTriggerNodes * sizeof(ClientTriggerAabbNode));
	}
	if (varClientTriggers->triggerString)
	{
		varClientTriggers->triggerString = (char *)g_streamPos;
		varchar = (char *)g_streamPos;
		Load_Stream(true, g_streamPos, varClientTriggers->triggerStringLength);
	}
	if (varClientTriggers->visionSetTriggers)
	{
		ALIGN_POS(2);
		varClientTriggers->visionSetTriggers = (short *)g_streamPos;
		varshort = (short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClientTriggers->trigger.count * 2);
	}
	if (varClientTriggers->triggerType)
	{
		varClientTriggers->triggerType = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varClientTriggers->trigger.count);
	}
	if (varClientTriggers->origins)
	{
		ALIGN_POS(4);
		varClientTriggers->origins = (float (*)[3])g_streamPos;
		varvec3_t = (float (*)[3])g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClientTriggers->trigger.count * 0xC);
	}
	if (varClientTriggers->scriptDelay)
	{
		ALIGN_POS(4);
		varClientTriggers->scriptDelay = (float *)g_streamPos;
		varfloat = (float *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClientTriggers->trigger.count * 4);
	}
	if (varClientTriggers->audioTriggers)
	{
		ALIGN_POS(2);
		varClientTriggers->audioTriggers = (short *)g_streamPos;
		varshort = (short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClientTriggers->trigger.count * 2);
	}
	if (varClientTriggers->blendLookup)
	{
		ALIGN_POS(2);
		varClientTriggers->blendLookup = (short *)g_streamPos;
		varshort = (short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClientTriggers->trigger.count * 2);
	}
	if (varClientTriggers->npcTriggers)
	{
		ALIGN_POS(2);
		varClientTriggers->npcTriggers = (short *)g_streamPos;
		varshort = (short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClientTriggers->trigger.count * 2);
	}
}

// Store 14034B030
void Load_ClientTriggerBlend(bool atStreamStart)
{
	Load_Stream(atStreamStart, varClientTriggerBlend, sizeof(ClientTriggerBlend));
	if (!varClientTriggerBlend->blendNodes)
		return;
	ALIGN_POS(4);
	varClientTriggerBlend->blendNodes = (ClientTriggerBlendNode *)g_streamPos;
	varClientTriggerBlendNode = (ClientTriggerBlendNode *)g_streamPos;
	Load_Stream(true, g_streamPos,
	            (unsigned long long)varClientTriggerBlend->numClientTriggerBlendNodes * sizeof(ClientTriggerBlendNode));
}

// Store 140357100
void Load_SpawnPointEntityRecord(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSpawnPointEntityRecord, sizeof(SpawnPointEntityRecord));
	varscr_string_t = &varSpawnPointEntityRecord->name;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	varscr_string_t = &varSpawnPointEntityRecord->target;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
	varscr_string_t = &varSpawnPointEntityRecord->script_noteworthy;
	Load_Stream(false, varscr_string_t, 4);
	Load_ScriptStringCustom(varscr_string_t);
}

// Store 1403571A0
void Load_SpawnPointRecordList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSpawnPointRecordList, sizeof(SpawnPointRecordList));
	if (!varSpawnPointRecordList->spawns)
		return;
	ALIGN_POS(4);
	varSpawnPointRecordList->spawns = (SpawnPointEntityRecord *)g_streamPos;
	varSpawnPointEntityRecord = (SpawnPointEntityRecord *)g_streamPos;
	unsigned long long count = varSpawnPointRecordList->spawnsCount;
	Load_Stream(true, g_streamPos, count * sizeof(SpawnPointEntityRecord));
	SpawnPointEntityRecord *record = varSpawnPointEntityRecord;
	for (; count; count--)
	{
		varSpawnPointEntityRecord = record;
		Load_SpawnPointEntityRecord(false);
		record++;
	}
}

// Store 1403572D0
void Load_SplinePointEntityRecord(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSplinePointEntityRecord, sizeof(SplinePointEntityRecord));
	if (varSplinePointEntityRecord->splineNodeLabel)
	{
		varSplinePointEntityRecord->splineNodeLabel = (char *)g_streamPos;
		varchar = (char *)g_streamPos;
		Load_Stream(true, g_streamPos, 0x40);
	}
	if (varSplinePointEntityRecord->positionCubic)
	{
		ALIGN_POS(4);
		varSplinePointEntityRecord->positionCubic = (float (*)[3])g_streamPos;
		varvec3_t = (float (*)[3])g_streamPos;
		Load_Stream(true, g_streamPos, 0x30);
	}
	if (varSplinePointEntityRecord->tangentQuadratic)
	{
		ALIGN_POS(4);
		varSplinePointEntityRecord->tangentQuadratic = (float (*)[3])g_streamPos;
		varvec3_t = (float (*)[3])g_streamPos;
		Load_Stream(true, g_streamPos, 0x24);
	}
}

// Store 1403573B0
void Load_SplinePointRecordList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSplinePointRecordList, sizeof(SplinePointRecordList));
	if (!varSplinePointRecordList->splinePoints)
		return;
	ALIGN_POS(4);
	varSplinePointRecordList->splinePoints = (SplinePointEntityRecord *)g_streamPos;
	varSplinePointEntityRecord = (SplinePointEntityRecord *)g_streamPos;
	unsigned long long count = varSplinePointRecordList->splinePointCount;
	Load_Stream(true, g_streamPos, count * sizeof(SplinePointEntityRecord));
	SplinePointEntityRecord *point = varSplinePointEntityRecord;
	for (; count; count--)
	{
		varSplinePointEntityRecord = point;
		Load_SplinePointEntityRecord(false);
		point++;
	}
}

// Store 140357460
void Load_SplineRecordList(bool atStreamStart)
{
	Load_Stream(atStreamStart, varSplineRecordList, sizeof(SplineRecordList));
	if (!varSplineRecordList->splines)
		return;
	ALIGN_POS(4);
	varSplineRecordList->splines = (SplinePointRecordList *)g_streamPos;
	varSplinePointRecordList = (SplinePointRecordList *)g_streamPos;
	unsigned long long count = varSplineRecordList->splineCount;
	Load_Stream(true, g_streamPos, count * sizeof(SplinePointRecordList));
	SplinePointRecordList *list = varSplinePointRecordList;
	for (; count; count--)
	{
		varSplinePointRecordList = list;
		Load_SplinePointRecordList(false);
		list++;
	}
}

// Store 140352C10
void Load_MapEnts(bool atStreamStart)
{
	Load_Stream(atStreamStart, varMapEnts, sizeof(MapEnts));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	Load_XStringField(&varMapEnts->name);
	if (varMapEnts->entityString)
	{
		varMapEnts->entityString = (char *)g_streamPos;
		varchar = (char *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varMapEnts->numEntityChars);
	}
	varMapTriggers = &varMapEnts->trigger;
	Load_MapTriggers(false);
	varClientTriggers = &varMapEnts->clientTrigger;
	Load_ClientTriggers(false);
	varClientTriggerBlend = &varMapEnts->clientTriggerBlend;
	Load_ClientTriggerBlend(false);
	varSpawnPointRecordList = &varMapEnts->spawnList;
	Load_SpawnPointRecordList(false);
	varSplineRecordList = &varMapEnts->splineList;
	Load_SplineRecordList(false);
	DB_PopStreamPos();
}

// Store 14035F9D0
void Load_cbrushside_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varcbrushside_t, sizeof(cbrushside_t));
	if (!varcbrushside_t->plane)
		return;
	if ((unsigned long long)varcbrushside_t->plane == DB_PTR_FOLLOWING)
	{
		ALIGN_POS(4);
		varcbrushside_t->plane = (cplane_s *)g_streamPos;
		varcplane_t = (cplane_s *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(cplane_s));
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)&varcbrushside_t->plane);
}

// Store 14035F900
void Load_cbrush_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varcbrush_t, sizeof(cbrush_t));
	if (varcbrush_t->sides)
	{
		if ((unsigned long long)varcbrush_t->sides == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varcbrush_t->sides = (cbrushside_t *)g_streamPos;
			varcbrushside_t = (cbrushside_t *)g_streamPos;
			Load_cbrushside_t(true);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varcbrush_t->sides);
		}
	}
	if (!varcbrush_t->baseAdjacentSide)
		return;
	if ((unsigned long long)varcbrush_t->baseAdjacentSide == DB_PTR_FOLLOWING)
	{
		varcbrush_t->baseAdjacentSide = g_streamPos;
		varcbrushedge_t = g_streamPos;
		Load_Stream(true, g_streamPos, 1);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)&varcbrush_t->baseAdjacentSide);
}

// Store 14035F7D0
void Load_cLeafBrushNodeLeaf_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varcLeafBrushNodeLeaf_t, sizeof(cLeafBrushNodeLeaf_t));
	if (!varcLeafBrushNodeLeaf_t->brushes)
		return;
	if ((unsigned long long)varcLeafBrushNodeLeaf_t->brushes == DB_PTR_FOLLOWING)
	{
		ALIGN_POS(2);
		varcLeafBrushNodeLeaf_t->brushes = (unsigned short *)g_streamPos;
		varLeafBrush = (unsigned short *)g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varcLeafBrushNode_t->leafBrushCount * 2);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)&varcLeafBrushNodeLeaf_t->brushes);
}

// Store 14034B360
void Load_ClipInfo(bool atStreamStart)
{
	Load_Stream(atStreamStart, varClipInfo, sizeof(ClipInfo));
	if (varClipInfo->planes)
	{
		if ((unsigned long long)varClipInfo->planes == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varClipInfo->planes = (cplane_s *)g_streamPos;
			varcplane_t = (cplane_s *)g_streamPos;
			Load_Stream(true, g_streamPos, (long long)varClipInfo->planeCount * sizeof(cplane_s));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->planes);
		}
	}
	if (varClipInfo->materials)
	{
		if ((unsigned long long)varClipInfo->materials == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varClipInfo->materials = (ClipMaterial *)g_streamPos;
			varClipMaterial = (ClipMaterial *)g_streamPos;
			unsigned int count = varClipInfo->numMaterials;
			Load_Stream(true, g_streamPos, (unsigned long long)count * sizeof(ClipMaterial));
			ClipMaterial *material = varClipMaterial;
			for (unsigned long long i = count; i; i--)
			{
				varClipMaterial = material;
				Load_Stream(false, material, sizeof(ClipMaterial));
				Load_XStringField(&varClipMaterial->name);
				material++;
			}
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->materials);
		}
	}
	if (varClipInfo->brushsides)
	{
		if ((unsigned long long)varClipInfo->brushsides == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varClipInfo->brushsides = (cbrushside_t *)g_streamPos;
			varcbrushside_t = (cbrushside_t *)g_streamPos;
			Load_cbrushside_tArray(true, varClipInfo->numBrushSides);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->brushsides);
		}
	}
	if (varClipInfo->brushEdges)
	{
		if ((unsigned long long)varClipInfo->brushEdges == DB_PTR_FOLLOWING)
		{
			varClipInfo->brushEdges = g_streamPos;
			varcbrushedge_t = g_streamPos;
			Load_Stream(true, g_streamPos, varClipInfo->numBrushEdges);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->brushEdges);
		}
	}
	if (varClipInfo->leafbrushNodes)
	{
		if ((unsigned long long)varClipInfo->leafbrushNodes == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(4);
			varClipInfo->leafbrushNodes = (cLeafBrushNode_s *)g_streamPos;
			varcLeafBrushNode_t = (cLeafBrushNode_s *)g_streamPos;
			unsigned long long count = varClipInfo->leafbrushNodesCount;
			Load_Stream(true, g_streamPos, count * sizeof(cLeafBrushNode_s));
			cLeafBrushNode_s *node = varcLeafBrushNode_t;
			for (; count; count--)
			{
				varcLeafBrushNode_t = node;
				Load_Stream(false, node, sizeof(cLeafBrushNode_s));
				varcLeafBrushNodeData_t = &varcLeafBrushNode_t->data;
				if (varcLeafBrushNode_t->leafBrushCount > 0)
				{
					varcLeafBrushNodeLeaf_t = &varcLeafBrushNodeData_t->leaf;
					Load_cLeafBrushNodeLeaf_t(false);
				}
				node++;
			}
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->leafbrushNodes);
		}
	}
	if (varClipInfo->leafbrushes)
	{
		if ((unsigned long long)varClipInfo->leafbrushes == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(2);
			varClipInfo->leafbrushes = (unsigned short *)g_streamPos;
			varLeafBrush = (unsigned short *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varClipInfo->numLeafBrushes * 2);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->leafbrushes);
		}
	}
	if (varClipInfo->brushes)
	{
		if ((unsigned long long)varClipInfo->brushes == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(128);
			varClipInfo->brushes = (cbrush_t *)g_streamPos;
			varcbrush_array_t = (cbrush_t *)g_streamPos;
			unsigned long long count = varClipInfo->numBrushes;
			Load_Stream(true, g_streamPos, count * sizeof(cbrush_t));
			cbrush_t *brush = varcbrush_array_t;
			for (; count; count--)
			{
				varcbrush_array_t = brush;
				Load_Stream(false, brush, sizeof(cbrush_t));
				varcbrush_t = varcbrush_array_t;
				Load_cbrush_t(false);
				brush++;
			}
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->brushes);
		}
	}
	if (varClipInfo->brushBounds)
	{
		if ((unsigned long long)varClipInfo->brushBounds == DB_PTR_FOLLOWING)
		{
			ALIGN_POS(128);
			varClipInfo->brushBounds = (Bounds *)g_streamPos;
			varBounds = (Bounds *)g_streamPos;
			Load_Stream(true, g_streamPos, (unsigned long long)varClipInfo->numBrushes * sizeof(Bounds));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->brushBounds);
		}
	}
	if (!varClipInfo->brushContents)
		return;
	if ((unsigned long long)varClipInfo->brushContents == DB_PTR_FOLLOWING)
	{
		ALIGN_POS(4);
		varClipInfo->brushContents = (int *)g_streamPos;
		varint = (int *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varClipInfo->numBrushes * 4);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)&varClipInfo->brushContents);
}
