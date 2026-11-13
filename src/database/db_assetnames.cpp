// database/db_assetnames.cpp (Store build)
//
// Per-type handlers for an asset's name and header size, three tables indexed by XAssetType (the PS4 PDB's
// db_assetnames.cpp statics). The Store build's tables are at 1409924A0 (get name), 1409926A0 (set name) and
// 1409928A0 (size); docs/fastfiles.md lists the sizes and name offsets. ui_map, aitype, mptype, character and
// xmodelalias have no handlers (null entries) in this build.

#include <iw6_static.h>

#include "database/db_local.h"

#define IW6_SOURCE "database/db_assetnames.cpp"

IW6_STATIC const char *(*DB_XAssetGetNameHandler[])(const XAssetHeader *) IW6_AT("", "DB_XAssetGetNameHandler");
IW6_STATIC void (*DB_XAssetSetNameHandler[])(XAssetHeader *, const char *) IW6_AT("", "DB_XAssetSetNameHandler");
IW6_STATIC int (*DB_GetXAssetSizeHandler[])() IW6_AT("", "DB_GetXAssetSizeHandler");

// Store 1403488B0 (PS4 PDB database/db_assetnames.cpp). Entry 0x40 of the Store build's getter table is a folded
// set-name handler (`*header = rdx`), so for that type the original stores the table address it left in RDX.
const char *DB_GetXAssetName(const XAsset *asset)
{
	return DB_XAssetGetNameHandler[asset->type](&asset->header);
}

// Store 1403488E0 (PS4 PDB database/db_assetnames.cpp)
void DB_SetXAssetName(XAsset *asset, const char *name)
{
	DB_XAssetSetNameHandler[asset->type](&asset->header, name);
}

// Store 1403488D0 (PS4 PDB database/db_assetnames.cpp)
int DB_GetXAssetTypeSize(int type)
{
	return DB_GetXAssetSizeHandler[type]();
}
