// xanim/xmodel_load_db.h (Store build): the zone loaders of XModel and XModelSurfs.
//
// In the original these are generated loader functions in xanim/xmodel_load_db.h, included into
// database/db_load.cpp (db_load.obj in the PS4/xb3 servers, whose PDBs give names and lines). The code here is
// the Store build's (iw6mp64_MSStore_ship), tagged with Store addresses: its XModel (0x258 bytes) and XModelLodInfo
// (0x40) are larger than the servers' (0x228, 0x38) and it loads one more array (XModel::unknown230); otherwise the
// statements are the servers' in the same order. DB_XModelSurfsFixup and Load_XModelSurfsFixup are
// database/db_registry.cpp's (PS4 PDB) and are kept here with the loader that calls them.
//
// The stream contract (Load_Stream, the inline/insert/offset pointer markers, the block stack) is described in
// include/database/db_stream_api.h; the formats in docs/assets/models.md.

#include "xanim/xmodel.h"

// Store 14035E020 (xanim/xmodel_load_db.h:1542 in the PS4 PDB)
void Load_XModel(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXModel, sizeof(XModel));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varXModel->name;
	Load_Stream(false, varXModel, sizeof(const char *));
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
	if (varXModel->boneNames)
	{
		if ((unsigned long long)varXModel->boneNames == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varXModel->boneNames = (scr_string_t *)g_streamPos;
			varscr_string_t = (scr_string_t *)g_streamPos;
			Load_scr_string_tArray(true, varXModel->numBones);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->boneNames);
		}
	}
	if (varXModel->parentList)
	{
		if ((unsigned long long)varXModel->parentList == DB_PTR_FOLLOWING)
		{
			varXModel->parentList = g_streamPos;
			varbyte = g_streamPos;
			Load_Stream(true, g_streamPos, varXModel->numBones - varXModel->numRootBones);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->parentList);
		}
	}
	if (varXModel->quats)
	{
		if ((unsigned long long)varXModel->quats == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
			varXModel->quats = (short *)g_streamPos;
			varshort = (short *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(short) * (4 * (varXModel->numBones - varXModel->numRootBones)));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->quats);
		}
	}
	if (varXModel->trans)
	{
		if ((unsigned long long)varXModel->trans == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varXModel->trans = (float *)g_streamPos;
			varfloat = (float *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(float) * (3 * (varXModel->numBones - varXModel->numRootBones)));
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->trans);
		}
	}
	if (varXModel->partClassification)
	{
		if ((unsigned long long)varXModel->partClassification == DB_PTR_FOLLOWING)
		{
			varXModel->partClassification = g_streamPos;
			varbyte = g_streamPos;
			Load_Stream(true, g_streamPos, varXModel->numBones);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->partClassification);
		}
	}
	if (varXModel->baseMat)
	{
		if ((unsigned long long)varXModel->baseMat == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
			varXModel->baseMat = (DObjAnimMat *)g_streamPos;
			varDObjAnimMat = (DObjAnimMat *)g_streamPos;
			Load_Stream(true, g_streamPos, sizeof(DObjAnimMat) * (unsigned long long)varXModel->numBones);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->baseMat);
		}
	}
	if (varXModel->reactiveMotionParts)
	{
		if ((unsigned long long)varXModel->reactiveMotionParts == DB_PTR_FOLLOWING)
		{
			g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 15) & ~15ull);
			varXModel->reactiveMotionParts = (ReactiveMotionModelPart *)g_streamPos;
			varReactiveMotionModelPart = (ReactiveMotionModelPart *)g_streamPos;
			Load_Stream(true, g_streamPos,
			            sizeof(ReactiveMotionModelPart) * (unsigned long long)varXModel->numReactiveMotionParts);
		}
		else
		{
			DB_ConvertOffsetToPointer((unsigned long long *)&varXModel->reactiveMotionParts);
		}
	}
	if (varXModel->materialHandles)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 7) & ~7ull);
		varXModel->materialHandles = (Material **)g_streamPos;
		varMaterialHandle = (Material **)g_streamPos;
		Load_MaterialHandleArray(true, varXModel->numsurfs);
	}
	varXModelLodInfo = varXModel->lodInfo;
	Load_Stream(false, varXModelLodInfo, sizeof(XModelLodInfo) * 6);
	XModelLodInfo *lodInfo = varXModelLodInfo;
	for (unsigned long long i = 6; i; i--)
	{
		varXModelLodInfo = lodInfo;
		Load_Stream(false, lodInfo, sizeof(XModelLodInfo));
		XModelSurfs **modelSurfs = &varXModelLodInfo->modelSurfs;
		varXModelSurfsPtr = modelSurfs;
		Load_XModelSurfsPtr(false);
		Load_XModelSurfsFixup(modelSurfs, varXModelLodInfo);
		lodInfo++;
	}
	if (varXModel->collSurfs)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		varXModel->collSurfs = (XModelCollSurf_s *)g_streamPos;
		varXModelCollSurf = (XModelCollSurf_s *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(XModelCollSurf_s) * (long long)varXModel->numCollSurfs);
	}
	if (varXModel->boneInfo)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		varXModel->boneInfo = (XBoneInfo *)g_streamPos;
		varXBoneInfo = (XBoneInfo *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(XBoneInfo) * (unsigned long long)varXModel->numBones);
	}
	if (varXModel->unknown230)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 1) & ~1ull);
		varXModel->unknown230 = (unsigned short *)g_streamPos;
		unk_144424D18 = (unsigned short *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(unsigned short) * (unsigned long long)varXModel->numsurfs);
	}
	varPhysPresetPtr = &varXModel->physPreset;
	Load_PhysPresetPtr(false);
	varPhysCollmapPtr = &varXModel->physCollmap;
	Load_PhysCollmapPtr(false);
	DB_PopStreamPos();
}

// Store 14035E530 (xanim/xmodel_load_db.h:2257 in the PS4 PDB)
void Load_XModelPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXModelPtr, sizeof(XModel *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	XModel **modelPtr = varXModelPtr;
	unsigned long long value = (unsigned long long)*varXModelPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varXModelPtr);
			DB_PopStreamPos();
			return;
		}
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		*varXModelPtr = (XModel *)g_streamPos;
		varXModel = (XModel *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_XModel(true);
		Load_XModelAsset(modelPtr);
		if (inserted)
			*(XModel **)inserted = *modelPtr;
	}
	DB_PopStreamPos();
}

// Store 14035E620 (xanim/xmodel_load_db.h:2315 in the PS4 PDB)
void Load_XModelPtrArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varXModelPtr, sizeof(XModel *) * count);
	XModel **modelPtr = varXModelPtr;
	for (; count; count--)
	{
		varXModelPtr = modelPtr;
		Load_Stream(false, modelPtr, sizeof(XModel *));
		DB_PushStreamPos(XFILE_BLOCK_TEMP);
		XModel **current = varXModelPtr;
		unsigned long long value = (unsigned long long)*varXModelPtr;
		if (value)
		{
			if (DB_PTR_IS_INLINE(value))
			{
				g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
				*varXModelPtr = (XModel *)g_streamPos;
				varXModel = (XModel *)g_streamPos;
				unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
				Load_XModel(true);
				Load_XModelAsset(current);
				if (inserted)
					*(XModel **)inserted = *current;
			}
			else
			{
				DB_ConvertOffsetToAlias((unsigned long long *)varXModelPtr);
			}
		}
		DB_PopStreamPos();
		modelPtr++;
	}
}

// Store 14035E750 (xanim/xmodel_load_db.h:887 in the PS4 PDB)
void Load_XModelSurfs(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXModelSurfs, sizeof(XModelSurfs));
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varXString = &varXModelSurfs->name;
	Load_Stream(false, varXModelSurfs, sizeof(const char *));
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
	if (varXModelSurfs->surfs)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		varXModelSurfs->surfs = (XSurface *)g_streamPos;
		varXSurface = (XSurface *)g_streamPos;
		unsigned long long count = varXModelSurfs->numsurfs;
		Load_Stream(true, g_streamPos, sizeof(XSurface) * count);
		XSurface *surf = varXSurface;
		for (; count; count--)
		{
			varXSurface = surf;
			Load_XSurface(false);
			surf++;
		}
	}
	DB_PopStreamPos();
}

// Store 14035E860 (xanim/xmodel_load_db.h:1021 in the PS4 PDB)
void Load_XModelSurfsPtr(bool atStreamStart)
{
	Load_Stream(atStreamStart, varXModelSurfsPtr, sizeof(XModelSurfs *));
	DB_PushStreamPos(XFILE_BLOCK_TEMP);
	XModelSurfs **surfsPtr = varXModelSurfsPtr;
	unsigned long long value = (unsigned long long)*varXModelSurfsPtr;
	if (value)
	{
		if (!DB_PTR_IS_INLINE(value))
		{
			DB_ConvertOffsetToAlias((unsigned long long *)varXModelSurfsPtr);
			DB_PopStreamPos();
			return;
		}
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		*varXModelSurfsPtr = (XModelSurfs *)g_streamPos;
		varXModelSurfs = (XModelSurfs *)g_streamPos;
		unsigned char *inserted = value == DB_PTR_INSERT ? DB_InsertPointer() : nullptr;
		Load_XModelSurfs(true);
		Load_XModelSurfsAsset(surfsPtr);
		if (inserted)
			*(XModelSurfs **)inserted = *surfsPtr;
	}
	DB_PopStreamPos();
}

// ---- database/db_registry.cpp ----------------------------------------------------------------------------------

// Store 140374250 (database/db_registry.cpp:2003 in the PS4 PDB)
void Load_XModelSurfsFixup(XModelSurfs **modelSurfs, XModelLodInfo *lodInfo)
{
	XModelSurfs *surfs = *modelSurfs;
	if (surfs)
	{
		for (int i = 0; i < 8; i++)
			lodInfo->partBits[i] = surfs->partBits[i];
		lodInfo->surfs = (*modelSurfs)->surfs;
	}
}

// Store 1403712F0 (database/db_registry.cpp:2161 in the PS4 PDB). Unlike the servers' copy it does not skip a
// LOD whose modelSurfs is null.
void DB_XModelSurfsFixup(XAssetHeader header, void *data)
{
	XModel *model = header.model;
	model->flags &= ~XMODEL_FLAG_DEFAULT_SURFS;
	short surfIndex = 0;
	for (int lod = 0; lod < model->numLods; lod++)
	{
		XModelLodInfo *lodInfo = &model->lodInfo[lod];
		XModelSurfs *modelSurfs = lodInfo->modelSurfs;
		for (int i = 0; i < 8; i++)
			lodInfo->partBits[i] = modelSurfs->partBits[i];
		lodInfo->surfs = modelSurfs->surfs;
		lodInfo->numsurfs = modelSurfs->numsurfs;
		lodInfo->surfIndex = surfIndex;
		if (modelSurfs->surfs == g_defaultSurfs)
			model->flags |= XMODEL_FLAG_DEFAULT_SURFS;
		surfIndex += modelSurfs->numsurfs;
	}
	model->numsurfs = (unsigned char)surfIndex;
}
