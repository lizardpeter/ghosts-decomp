// database/db_fastfile_load.cpp (Store build)
//
// Loading one zone (DB_LoadXFile): the uncompressed prefix (magic, version, the compressor, the streamed image rows,
// two sizes for the load bar), then through the inflater the XFile header, the block allocation and the XAssetList,
// and the asset loads. docs/fastfiles.md describes the format. Names: the PS4/Xbox One server PDBs
// (database/db_fastfile_load.cpp); the streamed image rows, the third parameter and the image pak index load at the
// end are the PC client's (no server has them; names unknown).

#include <iw6_static.h>

#include "database/db_local.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "database/db_fastfile_load.cpp"

struct StreamImageRow  // 0x18 (docs/fastfiles.md)
{
	unsigned short localized;
	unsigned short fileIndex;
	unsigned int pad;
	unsigned long long offset;
	unsigned long long end;
};

IW6_STATIC XAssetList g_varXAssetList IW6_AT("", "g_varXAssetList");
IW6_STATIC unsigned int unk_1443A4820 IW6_AT("", "unk_1443A4820");                // streamed image row count
IW6_STATIC StreamImageRow unk_144310C20[0x6280] IW6_AT("", "unk_144310C20");      // the rows
IW6_STATIC unsigned int unk_144310BF4 IW6_AT("", "unk_144310BF4");                // next row to hand out

void DB_InitLoadXFile(DBFile *file, unsigned long long offset);
void DB_DirtyDiscError();
void DB_FinishLoadXFile();
void DB_SetFileLoadCompressor(int compressor);
void DB_InflateInit(int isSecure);
void DB_InflateShutdown();
int LoadBar_IsComplete();
void LoadBar_LoadingFastfile(unsigned long long size, unsigned long long extra);
void DB_AllocXZoneMemory(unsigned long long *const blockSize, const char *filename, XZoneMemory *zoneMem);
void Load_ScriptStringList(bool atStreamStart);
void Load_XGlobalsPtr(bool atStreamStart);
XAsset *AllocLoad_XAsset();
void Load_XAsset(bool atStreamStart);
void sub_140348960(unsigned char *signature);   // db_auth.cpp: the zone's RSA signature, or zeros
void sub_140375350();                           // loads the index of every image pak opened for this zone

#define DB_MAGIC_SIGNED 0x3030313066665749ull    // "IWff0100"
#define DB_MAGIC_UNSIGNED 0x3030317566665749ull  // "IWffu100"
#define DB_VERSION 0x235

// Store 140349300 (PS4 PDB database/db_fastfile_load.cpp:130; the Store build adds `signature`, 256 bytes)
void DB_LoadXFile(XZoneMemory *zoneMem, DBFile *file, unsigned char *signature)
{
	DB_InitLoadXFile(file, 0);
	unsigned long long magic;
	DB_ReadXFileUncompressed((unsigned char *)&magic, 8);
	if (magic != DB_MAGIC_SIGNED && magic != DB_MAGIC_UNSIGNED)
		DB_DirtyDiscError();
	unsigned int version;
	DB_ReadXFileUncompressed((unsigned char *)&version, 4);
	if (version != DB_VERSION)
	{
		if (!file->handle)
		{
			DB_FinishLoadXFile();
			return;
		}
		Com_Error(ERR_DROP,
		          version >= DB_VERSION ? "Fastfile for zone '%s' is newer than client executable (version %d, expecting %d)"
		                                : "Fastfile for zone '%s' is out of date (version %d, expecting %d)",
		          file->name, version, DB_VERSION);
	}
	unsigned char flags0, compressor, flags2, flags3;
	unsigned int unused0, unused1;
	DB_ReadXFileUncompressed(&flags0, 1);
	DB_ReadXFileUncompressed(&compressor, 1);
	DB_ReadXFileUncompressed(&flags2, 1);
	DB_ReadXFileUncompressed(&flags3, 1);
	DB_ReadXFileUncompressed((unsigned char *)&unused0, 4);
	DB_ReadXFileUncompressed((unsigned char *)&unused1, 4);
	DB_SetFileLoadCompressor(compressor);
	DB_ReadXFileUncompressed((unsigned char *)&unk_1443A4820, 4);
	if (unk_1443A4820 > 0x6280)
		DB_DirtyDiscError();
	for (unsigned int i = 0; i < unk_1443A4820; ++i)
		DB_ReadXFileUncompressed((unsigned char *)&unk_144310C20[i], sizeof(StreamImageRow));
	unsigned long long loadSize, loadEnd;
	DB_ReadXFileUncompressed((unsigned char *)&loadSize, 8);
	DB_ReadXFileUncompressed((unsigned char *)&loadEnd, 8);
	unk_144310BF4 = 0;
	DB_InflateInit(magic != DB_MAGIC_UNSIGNED);
	XFile xfile;
	DB_ReadXFile((unsigned char *)&xfile, sizeof(xfile), 0);
	if (!LoadBar_IsComplete())
		LoadBar_LoadingFastfile(loadSize, loadEnd - loadSize);
	DB_AllocXZoneMemory(xfile.blockSize, file->name, zoneMem);
	DB_InitStreams(zoneMem);
	varXAssetList = &g_varXAssetList;
	DB_ReadXFile((unsigned char *)&g_varXAssetList, sizeof(XAssetList), 0);
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	varScriptStringList = &varXAssetList->stringList;
	Load_ScriptStringList(false);
	varXGlobalsPtr = &varXAssetList->globals;
	Load_XGlobalsPtr(false);
	DB_PopStreamPos();
	DB_PushStreamPos(XFILE_BLOCK_VIRTUAL);
	if (varXAssetList->assets)
	{
		varXAssetList->assets = AllocLoad_XAsset();
		varXAsset = varXAssetList->assets;
		int count = varXAssetList->assetCount;
		Load_Stream(true, varXAsset, (long long)count * sizeof(XAsset));
		XAsset *asset = varXAsset;
		if (count > 0)
		{
			for (long long n = count; n; --n, ++asset)
			{
				varXAsset = asset;
				Load_XAsset(false);
			}
		}
	}
	DB_PopStreamPos();
	sub_140348960(signature);
	DB_InflateShutdown();
	DB_FinishLoadXFile();
	sub_140375350();
}

// Store 1403492E0 (name unknown): the next streamed image row (Load_ImageStream, 140374E70, takes four per image).
StreamImageRow *sub_1403492E0()
{
	return &unk_144310C20[unk_144310BF4++];
}
