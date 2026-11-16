// xanim/xanim_load_db.h (Store build): the zone loaders of animations (XAnimParts).
//
// Generated loader functions (database/db_load.cpp includes them; db_load.obj in the servers, whose MAP gives the
// names). The code is the Store build's, tagged with Store addresses; tools/fastfile/xanim.py is the same logic in
// Python, checked against the game on real zones (docs/assets/animations.md).

#include "xanim/xanim.h"

void Load_ScriptStringCustom(scr_string_t *var);  // Store 14037AF90

extern XAnimParts **varXAnimPartsPtr;                                   // Store 144425998
extern XAnimParts *varXAnimParts;                                       // Store 144425990
extern XAnimNotifyInfo *varXAnimNotifyInfo;                             // Store 144425988
extern XAnimDeltaPart *varXAnimDeltaPart;                               // Store 144425948
extern XAnimPartTrans *varXAnimPartTrans;                               // Store 144425980
extern XAnimPartTransData *varXAnimPartTransData;                       // Store 144425978
extern XAnimPartTransFrames *varXAnimPartTransFrames;                   // Store 144425970
extern XAnimDynamicFrames *varXAnimDynamicFrames;                       // Store 144425968
extern XAnimDynamicIndices *varXAnimDynamicIndicesTrans;                // Store 144425950
extern XAnimDeltaPartQuat2 *varXAnimDeltaPartQuat2;                     // Store 144425920
extern XAnimDeltaPartQuatData2 *varXAnimDeltaPartQuatData2;             // Store 144425918
extern XAnimDeltaPartQuatDataFrames2 *varXAnimDeltaPartQuatDataFrames2; // Store 144425910
extern XAnimDynamicIndices *varXAnimDynamicIndicesDeltaQuat2;           // Store 144425908
extern XAnimDeltaPartQuat *varXAnimDeltaPartQuat;                       // Store 144425940
extern XAnimDeltaPartQuatData *varXAnimDeltaPartQuatData;               // Store 144425938
extern XAnimDeltaPartQuatDataFrames *varXAnimDeltaPartQuatDataFrames;   // Store 144425930
extern XAnimDynamicIndices *varXAnimDynamicIndicesDeltaQuat;            // Store 144425928
extern XAnimIndices *varXAnimIndices;                                   // Store 144425900
extern short (*varXQuat2)[2];                                           // Store 144424D38
extern short (*varXQuat)[4];                                            // Store 144424D28
extern unsigned short (*varUShortVec)[3];                               // Store 144425960
extern unsigned char (*varByteVec)[3];                                  // Store 144425958
extern float (*varvec3_t)[3];                                           // Store 144424C88
extern unsigned short *varuint16_t;                                     // Store 144424D48
extern unsigned short *varushort;                                       // Store 144424D18
extern int *varint;                                                     // Store 144424A88

#define ALIGN_POS(a) (g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + ((a) - 1)) & ~((unsigned long long)(a) - 1)))

// Store 14035CF10
void Load_XAnimIndices(bool atStreamStart)
{
	(void)atStreamStart;
	if (varXAnimParts->numframes < 0x100)
	{
		if (!varXAnimIndices->data)
			return;
		varXAnimIndices->_1 = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varXAnimParts->indexCount);
		return;
	}
	if (!varXAnimIndices->data)
		return;
	ALIGN_POS(2);
	varXAnimIndices->_2 = (unsigned short *)g_streamPos;
	varushort = (unsigned short *)g_streamPos;
	Load_Stream(true, g_streamPos, (unsigned long long)varXAnimParts->indexCount * 2);
}

// The three dynamic index loaders: size + 1 entries, bytes or u16 by the animation's frame count, unaligned.
static void Load_DynamicIndices(XAnimDynamicIndices *indices, unsigned short size)
{
	if (varXAnimParts->numframes < 0x100)
	{
		Load_Stream(true, indices, 0);
		varbyte = indices->_1;
		Load_Stream(true, indices->_1, (unsigned long long)size + 1);
		return;
	}
	Load_Stream(true, indices, 0);
	varuint16_t = indices->_2;
	Load_Stream(true, indices->_2, (unsigned long long)size * 2 + 2);
}

// Store 14035CE90
void Load_XAnimDynamicIndicesTrans(bool atStreamStart)
{
	(void)atStreamStart;
	Load_DynamicIndices(varXAnimDynamicIndicesTrans, varXAnimPartTrans->size);
}

// Store 14035CD90
void Load_XAnimDynamicIndicesDeltaQuat2(bool atStreamStart)
{
	(void)atStreamStart;
	Load_DynamicIndices(varXAnimDynamicIndicesDeltaQuat2, varXAnimDeltaPartQuat2->size);
}

// Store 14035CE10
void Load_XAnimDynamicIndicesDeltaQuat(bool atStreamStart)
{
	(void)atStreamStart;
	Load_DynamicIndices(varXAnimDynamicIndicesDeltaQuat, varXAnimDeltaPartQuat->size);
}

// Store 14035CCE0
void Load_XAnimDynamicFrames(bool atStreamStart)
{
	(void)atStreamStart;
	if (!varXAnimPartTrans->smallTrans)
	{
		if (!varXAnimDynamicFrames->_2)
			return;
		ALIGN_POS(4);
		varXAnimDynamicFrames->_2 = (unsigned short (*)[3])g_streamPos;
		varUShortVec = (unsigned short (*)[3])g_streamPos;
		unsigned short size = varXAnimPartTrans->size;
		Load_Stream(true, g_streamPos, size ? ((unsigned long long)size + 1) * 6 : 0);
		return;
	}
	if (!varXAnimDynamicFrames->_1)
		return;
	varXAnimDynamicFrames->_1 = (unsigned char (*)[3])g_streamPos;
	varByteVec = (unsigned char (*)[3])g_streamPos;
	unsigned short size = varXAnimPartTrans->size;
	Load_Stream(true, g_streamPos, size ? ((unsigned long long)size + 1) * 3 : 0);
}

// Store 14035CFA0
void Load_XAnimPartTrans(bool atStreamStart)
{
	(void)atStreamStart;  // the Store build always loads it at the stream position
	Load_Stream(true, varXAnimPartTrans, 8);
	XAnimPartTransData *data = &varXAnimPartTrans->u;
	varXAnimPartTransData = data;
	if (varXAnimPartTrans->size)
	{
		varXAnimPartTransFrames = &data->frames;
		Load_Stream(true, &data->frames, 0x20);
		varXAnimDynamicIndicesTrans = &data->frames.indices;
		Load_XAnimDynamicIndicesTrans(true);
		varXAnimDynamicFrames = &varXAnimPartTransFrames->frames;
		Load_XAnimDynamicFrames(false);
		return;
	}
	varvec3_t = (float (*)[3])data->frame0;
	Load_Stream(true, data->frame0, 0xC);
}

// Store 14035CBA0
void Load_XAnimDeltaPartQuatDataFrames2(bool atStreamStart)
{
	(void)atStreamStart;  // the Store build always loads it at the stream position
	Load_Stream(true, varXAnimDeltaPartQuatDataFrames2, 8);
	varXAnimDynamicIndicesDeltaQuat2 = &varXAnimDeltaPartQuatDataFrames2->indices;
	Load_XAnimDynamicIndicesDeltaQuat2(true);
	if (!varXAnimDeltaPartQuatDataFrames2->frames)
		return;
	ALIGN_POS(4);
	varXAnimDeltaPartQuatDataFrames2->frames = (short (*)[2])g_streamPos;
	varXQuat2 = (short (*)[2])g_streamPos;
	unsigned short size = varXAnimDeltaPartQuat2->size;
	Load_Stream(true, g_streamPos, size ? (unsigned long long)size * 4 + 4 : 0);
}

// Store 14035CC40
void Load_XAnimDeltaPartQuatDataFrames(bool atStreamStart)
{
	(void)atStreamStart;  // the Store build always loads it at the stream position
	Load_Stream(true, varXAnimDeltaPartQuatDataFrames, 8);
	varXAnimDynamicIndicesDeltaQuat = &varXAnimDeltaPartQuatDataFrames->indices;
	Load_XAnimDynamicIndicesDeltaQuat(true);
	if (!varXAnimDeltaPartQuatDataFrames->frames)
		return;
	ALIGN_POS(4);
	varXAnimDeltaPartQuatDataFrames->frames = (short (*)[4])g_streamPos;
	varXQuat = (short (*)[4])g_streamPos;
	unsigned short size = varXAnimDeltaPartQuat->size;
	Load_Stream(true, g_streamPos, size ? (unsigned long long)size * 8 + 8 : 0);
}

// Store 14035CA20
void Load_XAnimDeltaPart(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXAnimDeltaPart, sizeof(XAnimDeltaPart));
	if (varXAnimDeltaPart->trans)
	{
		ALIGN_POS(4);
		varXAnimDeltaPart->trans = (XAnimPartTrans *)g_streamPos;
		varXAnimPartTrans = (XAnimPartTrans *)g_streamPos;
		Load_XAnimPartTrans(true);
	}
	if (varXAnimDeltaPart->quat2)
	{
		ALIGN_POS(4);
		XAnimDeltaPartQuat2 *quat2 = (XAnimDeltaPartQuat2 *)g_streamPos;
		varXAnimDeltaPart->quat2 = quat2;
		varXAnimDeltaPartQuat2 = quat2;
		Load_Stream(true, quat2, 8);
		varXAnimDeltaPartQuatData2 = &quat2->u;
		if (!varXAnimDeltaPartQuat2->size)
		{
			varXQuat2 = (short (*)[2])quat2->u.frame0;
			Load_Stream(true, quat2->u.frame0, 4);
		}
		else
		{
			varXAnimDeltaPartQuatDataFrames2 = &quat2->u.frames;
			Load_XAnimDeltaPartQuatDataFrames2(true);
		}
	}
	if (!varXAnimDeltaPart->quat)
		return;
	ALIGN_POS(4);
	XAnimDeltaPartQuat *quat = (XAnimDeltaPartQuat *)g_streamPos;
	varXAnimDeltaPart->quat = quat;
	varXAnimDeltaPartQuat = quat;
	Load_Stream(true, quat, 8);
	varXAnimDeltaPartQuatData = &quat->u;
	if (varXAnimDeltaPartQuat->size)
	{
		varXAnimDeltaPartQuatDataFrames = &quat->u.frames;
		Load_XAnimDeltaPartQuatDataFrames(true);
		return;
	}
	varXQuat = (short (*)[4])quat->u.frame0;
	Load_Stream(true, quat->u.frame0, 8);
}

// Store 14035D040
void Load_XAnimParts(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXAnimParts, sizeof(XAnimParts));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varXAnimParts->name;
	Load_Stream(false, varXString, 8);
	if (*varXString)
	{
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
	if (varXAnimParts->names)
	{
		ALIGN_POS(4);
		varXAnimParts->names = (scr_string_t *)g_streamPos;
		varscr_string_t = (scr_string_t *)g_streamPos;
		Load_scr_string_tArray(true, varXAnimParts->boneCount[9]);
	}
	if (varXAnimParts->notify)
	{
		ALIGN_POS(4);
		varXAnimParts->notify = (XAnimNotifyInfo *)g_streamPos;
		varXAnimNotifyInfo = (XAnimNotifyInfo *)g_streamPos;
		unsigned long long count = varXAnimParts->notifyCount;
		Load_Stream(true, g_streamPos, count * sizeof(XAnimNotifyInfo));
		XAnimNotifyInfo *info = varXAnimNotifyInfo;
		for (; count; count--)
		{
			varXAnimNotifyInfo = info;
			Load_Stream(false, info, sizeof(XAnimNotifyInfo));
			varscr_string_t = &varXAnimNotifyInfo->name;
			Load_Stream(false, varscr_string_t, 4);
			Load_ScriptStringCustom(varscr_string_t);
			info++;
		}
	}
	if (varXAnimParts->deltaPart)
	{
		ALIGN_POS(4);
		varXAnimParts->deltaPart = (XAnimDeltaPart *)g_streamPos;
		varXAnimDeltaPart = (XAnimDeltaPart *)g_streamPos;
		Load_XAnimDeltaPart(true);
	}
	if (varXAnimParts->dataByte)
	{
		varXAnimParts->dataByte = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varXAnimParts->dataByteCount);
	}
	if (varXAnimParts->dataShort)
	{
		ALIGN_POS(2);
		varXAnimParts->dataShort = (short *)g_streamPos;
		varshort = (short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varXAnimParts->dataShortCount * 2);
	}
	if (varXAnimParts->dataInt)
	{
		ALIGN_POS(4);
		varXAnimParts->dataInt = (int *)g_streamPos;
		varint = (int *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varXAnimParts->dataIntCount * 4);
	}
	if (varXAnimParts->randomDataShort)
	{
		ALIGN_POS(2);
		varXAnimParts->randomDataShort = (short *)g_streamPos;
		varshort = (short *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varXAnimParts->randomDataShortCount * 2);
	}
	if (varXAnimParts->randomDataByte)
	{
		varXAnimParts->randomDataByte = g_streamPos;
		varbyte = g_streamPos;
		Load_Stream(true, g_streamPos, varXAnimParts->randomDataByteCount);
	}
	if (varXAnimParts->randomDataInt)
	{
		ALIGN_POS(4);
		varXAnimParts->randomDataInt = (int *)g_streamPos;
		varint = (int *)g_streamPos;
		Load_Stream(true, g_streamPos, (unsigned long long)varXAnimParts->randomDataIntCount * 4);
	}
	varXAnimIndices = &varXAnimParts->indices;
	Load_XAnimIndices(false);
	DB_PopStreamPos();
}

// Store 14035D3D0
void Load_XAnimPartsPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXAnimPartsPtr, sizeof(XAnimParts *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	XAnimParts **partsPtr = varXAnimPartsPtr;
	unsigned long long value = (unsigned long long)*varXAnimPartsPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varXAnimPartsPtr);
			DB_PopStreamPos();
			return;
		}
		ALIGN_POS(4);
		*varXAnimPartsPtr = (XAnimParts *)g_streamPos;
		varXAnimParts = (XAnimParts *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_XAnimParts(true);
		Load_XAnimPartsAsset(partsPtr);
		if (inserted)
			*(XAnimParts **)inserted = *partsPtr;
	}
	DB_PopStreamPos();
}
