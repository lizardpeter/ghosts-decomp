// qcommon/cm_clipmap.h: the collision map (clipMap_t, asset col_map_mp) and the map entities it carries, Store-build
// layouts.
//
// Layouts are the servers' PDBs' (iw6_ds_xb3); every offset a Store loader touches is checked against it, and the
// whole asset against the game by tools/fastfile/clipmap.py (tests/fastfile/clipmap_check.py). docs/assets/collision.md.
#pragma once

#include "database/db_stream_api.h"  // scr_string_t
#include "qcommon/cm_brush.h"
#include "universal/com_math.h"  // Bounds

struct ClipMaterial
{
	const char *name;
	int surfaceFlags;
	int contents;
};
static_assert(sizeof(ClipMaterial) == 0x10, "ClipMaterial");

struct cLeafBrushNodeLeaf_t
{
	unsigned short *brushes;
};

struct cLeafBrushNodeChildren_t
{
	float dist;
	float range;
	unsigned short childOffset[2];
};

union cLeafBrushNodeData_t
{
	cLeafBrushNodeLeaf_t leaf;
	cLeafBrushNodeChildren_t children;
};

struct cLeafBrushNode_s
{
	unsigned char axis;
	short leafBrushCount;
	int contents;
	cLeafBrushNodeData_t data;
};
static_assert(sizeof(cLeafBrushNode_s) == 0x18, "cLeafBrushNode_s");
static_assert(__builtin_offsetof(cLeafBrushNode_s, data) == 0x08, "cLeafBrushNode_s");

struct ClipInfo
{
	int planeCount;
	cplane_s *planes;
	unsigned int numMaterials;
	ClipMaterial *materials;
	unsigned int numBrushSides;
	cbrushside_t *brushsides;
	unsigned int numBrushEdges;
	unsigned char *brushEdges;
	unsigned int leafbrushNodesCount;
	cLeafBrushNode_s *leafbrushNodes;
	unsigned int numLeafBrushes;
	unsigned short *leafbrushes;
	unsigned short numBrushes;
	cbrush_t *brushes;
	Bounds *brushBounds;
	int *brushContents;
};
static_assert(sizeof(ClipInfo) == 0x80, "ClipInfo");
static_assert(__builtin_offsetof(ClipInfo, leafbrushNodes) == 0x48, "ClipInfo");
static_assert(__builtin_offsetof(ClipInfo, numBrushes) == 0x60, "ClipInfo");
static_assert(__builtin_offsetof(ClipInfo, brushContents) == 0x78, "ClipInfo");

struct TriggerModel
{
	int contents;
	unsigned short hullCount;
	unsigned short firstHull;
};
static_assert(sizeof(TriggerModel) == 8, "TriggerModel");

struct TriggerHull
{
	Bounds bounds;
	int contents;
	unsigned short slabCount;
	unsigned short firstSlab;
};
static_assert(sizeof(TriggerHull) == 0x20, "TriggerHull");

struct TriggerSlab
{
	float dir[3];
	float midPoint;
	float halfSize;
};
static_assert(sizeof(TriggerSlab) == 0x14, "TriggerSlab");

struct MapTriggers
{
	unsigned int count;
	TriggerModel *models;
	unsigned int hullCount;
	TriggerHull *hulls;
	unsigned int slabCount;
	TriggerSlab *slabs;
};
static_assert(sizeof(MapTriggers) == 0x30, "MapTriggers");

struct ClientTriggerAabbNode
{
	Bounds bounds;
	unsigned short firstChild;
	unsigned short childCount;
};
static_assert(sizeof(ClientTriggerAabbNode) == 0x1C, "ClientTriggerAabbNode");

struct ClientTriggers
{
	MapTriggers trigger;
	unsigned short numClientTriggerNodes;
	ClientTriggerAabbNode *clientTriggerAabbTree;
	unsigned int triggerStringLength;
	char *triggerString;
	short *visionSetTriggers;
	unsigned char *triggerType;
	float (*origins)[3];
	float *scriptDelay;
	short *audioTriggers;
	short *blendLookup;
	short *npcTriggers;
};
static_assert(sizeof(ClientTriggers) == 0x88, "ClientTriggers");
static_assert(__builtin_offsetof(ClientTriggers, triggerString) == 0x48, "ClientTriggers");
static_assert(__builtin_offsetof(ClientTriggers, npcTriggers) == 0x80, "ClientTriggers");

struct ClientTriggerBlendNode
{
	float pointA[3];
	float pointB[3];
	unsigned short triggerA;
	unsigned short triggerB;
};
static_assert(sizeof(ClientTriggerBlendNode) == 0x1C, "ClientTriggerBlendNode");

struct ClientTriggerBlend
{
	unsigned short numClientTriggerBlendNodes;
	ClientTriggerBlendNode *blendNodes;
};
static_assert(sizeof(ClientTriggerBlend) == 0x10, "ClientTriggerBlend");

struct SpawnPointEntityRecord
{
	unsigned short index;
	scr_string_t name;
	scr_string_t target;
	scr_string_t script_noteworthy;
	float origin[3];
	float angles[3];
};
static_assert(sizeof(SpawnPointEntityRecord) == 0x28, "SpawnPointEntityRecord");

struct SpawnPointRecordList
{
	unsigned short spawnsCount;
	SpawnPointEntityRecord *spawns;
};
static_assert(sizeof(SpawnPointRecordList) == 0x10, "SpawnPointRecordList");

struct SplinePointEntityRecord
{
	int splineId;
	int splineNodeId;
	char *splineNodeLabel;  // 0x40 bytes when set
	float splineNodeTension;
	float origin[3];
	float corridorDims[2];
	float tangent[3];
	float distToNextNode;
	float (*positionCubic)[3];     // 4 entries
	float (*tangentQuadratic)[3];  // 3 entries
};
static_assert(sizeof(SplinePointEntityRecord) == 0x48, "SplinePointEntityRecord");
static_assert(__builtin_offsetof(SplinePointEntityRecord, positionCubic) == 0x38, "SplinePointEntityRecord");

struct SplinePointRecordList
{
	unsigned short splinePointCount;
	float splineLength;
	SplinePointEntityRecord *splinePoints;
};
static_assert(sizeof(SplinePointRecordList) == 0x10, "SplinePointRecordList");

struct SplineRecordList
{
	unsigned short splineCount;
	SplinePointRecordList *splines;
};
static_assert(sizeof(SplineRecordList) == 0x10, "SplineRecordList");

struct MapEnts
{
	const char *name;
	char *entityString;
	int numEntityChars;
	MapTriggers trigger;
	ClientTriggers clientTrigger;
	ClientTriggerBlend clientTriggerBlend;
	SpawnPointRecordList spawnList;
	SplineRecordList splineList;
};
static_assert(sizeof(MapEnts) == 0x100, "MapEnts");
static_assert(__builtin_offsetof(MapEnts, trigger) == 0x18, "MapEnts");
static_assert(__builtin_offsetof(MapEnts, clientTrigger) == 0x48, "MapEnts");
static_assert(__builtin_offsetof(MapEnts, clientTriggerBlend) == 0xD0, "MapEnts");
static_assert(__builtin_offsetof(MapEnts, splineList) == 0xF0, "MapEnts");

void Load_MapTriggers(bool atStreamStart);
void Load_ClientTriggers(bool atStreamStart);
void Load_ClientTriggerBlend(bool atStreamStart);
void Load_SpawnPointEntityRecord(bool atStreamStart);
void Load_SpawnPointRecordList(bool atStreamStart);
void Load_SplinePointEntityRecord(bool atStreamStart);
void Load_SplinePointRecordList(bool atStreamStart);
void Load_SplineRecordList(bool atStreamStart);
void Load_MapEnts(bool atStreamStart);
void Load_cbrushside_t(bool atStreamStart);
void Load_cbrush_t(bool atStreamStart);
void Load_cLeafBrushNodeLeaf_t(bool atStreamStart);
void Load_ClipInfo(bool atStreamStart);
