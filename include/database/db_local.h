// database/: the fastfile loader's types (PS4/Xbox One server PDB layouts; the Store build uses the same ones,
// docs/fastfiles.md).
#pragma once

typedef unsigned char byte_t;

enum XAssetType
{
	ASSET_TYPE_PHYSPRESET = 0x00,
	ASSET_TYPE_PHYSCOLLMAP = 0x01,
	ASSET_TYPE_XANIMPARTS = 0x02,
	ASSET_TYPE_XMODEL_SURFS = 0x03,
	ASSET_TYPE_XMODEL = 0x04,
	ASSET_TYPE_MATERIAL = 0x05,
	ASSET_TYPE_COMPUTESHADER = 0x06,
	ASSET_TYPE_VERTEXSHADER = 0x07,
	ASSET_TYPE_HULLSHADER = 0x08,
	ASSET_TYPE_DOMAINSHADER = 0x09,
	ASSET_TYPE_PIXELSHADER = 0x0A,
	ASSET_TYPE_VERTEXDECL = 0x0B,
	ASSET_TYPE_TECHNIQUE_SET = 0x0C,
	ASSET_TYPE_IMAGE = 0x0D,
	ASSET_TYPE_SOUND = 0x0E,
	ASSET_TYPE_SOUND_CURVE = 0x0F,
	ASSET_TYPE_LPF_CURVE = 0x10,
	ASSET_TYPE_REVERB_CURVE = 0x11,
	ASSET_TYPE_LOADED_SOUND = 0x12,
	ASSET_TYPE_CLIPMAP = 0x13,
	ASSET_TYPE_COMWORLD = 0x14,
	ASSET_TYPE_GLASSWORLD = 0x15,
	ASSET_TYPE_PATHDATA = 0x16,
	ASSET_TYPE_VEHICLE_TRACK = 0x17,
	ASSET_TYPE_MAP_ENTS = 0x18,
	ASSET_TYPE_FXWORLD = 0x19,
	ASSET_TYPE_GFXWORLD = 0x1A,
	ASSET_TYPE_LIGHT_DEF = 0x1B,
	ASSET_TYPE_UI_MAP = 0x1C,
	ASSET_TYPE_FONT = 0x1D,
	ASSET_TYPE_MENULIST = 0x1E,
	ASSET_TYPE_MENU = 0x1F,
	ASSET_TYPE_ANIMCLASS = 0x20,
	ASSET_TYPE_LOCALIZE_ENTRY = 0x21,
	ASSET_TYPE_ATTACHMENT = 0x22,
	ASSET_TYPE_WEAPON = 0x23,
	ASSET_TYPE_SNDDRIVER_GLOBALS = 0x24,
	ASSET_TYPE_FX = 0x25,
	ASSET_TYPE_IMPACT_FX = 0x26,
	ASSET_TYPE_SURFACE_FX = 0x27,
	ASSET_TYPE_AITYPE = 0x28,
	ASSET_TYPE_MPTYPE = 0x29,
	ASSET_TYPE_CHARACTER = 0x2A,
	ASSET_TYPE_XMODELALIAS = 0x2B,
	ASSET_TYPE_RAWFILE = 0x2C,
	ASSET_TYPE_SCRIPTFILE = 0x2D,
	ASSET_TYPE_STRINGTABLE = 0x2E,
	ASSET_TYPE_LEADERBOARD = 0x2F,
	ASSET_TYPE_STRUCTURED_DATA_DEF = 0x30,
	ASSET_TYPE_TRACER = 0x31,
	ASSET_TYPE_VEHICLE = 0x32,
	ASSET_TYPE_ADDON_MAP_ENTS = 0x33,
	ASSET_TYPE_NET_CONST_STRINGS = 0x34,
	ASSET_TYPE_REVERB_PRESET = 0x35,
	ASSET_TYPE_LUA_FILE = 0x36,
	ASSET_TYPE_SCRIPTABLE = 0x37,
	ASSET_TYPE_COLORIZATION = 0x38,
	ASSET_TYPE_COLORIZATIONSET = 0x39,
	ASSET_TYPE_TONEMAPPING = 0x3A,
	ASSET_TYPE_EQUIPMENT_SND_TABLE = 0x3B,
	ASSET_TYPE_VECTORFIELD = 0x3C,
	ASSET_TYPE_DOPPLER_PRESET = 0x3D,
	ASSET_TYPE_PARTICLE_SIM_ANIMATION = 0x3E,
	ASSET_TYPE_COUNT = 0x3F,
	ASSET_TYPE_STRING = 0x3F,
	ASSET_TYPE_ASSETLIST = 0x40,
};

enum
{
	XFILE_BLOCK_TEMP = 0,
	XFILE_BLOCK_PHYSICAL = 1,
	XFILE_BLOCK_RUNTIME = 2,
	XFILE_BLOCK_VIRTUAL = 3,
	XFILE_BLOCK_LARGE = 4,
	XFILE_BLOCK_CALLBACK = 5,
	XFILE_BLOCK_SCRIPT = 6,
	MAX_XFILE_COUNT = 7,
};

enum DB_CompressorType
{
	DB_COMPRESSOR_INVALID = -1,
	DB_COMPRESSOR_ZLIB = 0,
	DB_COMPRESSOR_LZX = 1,
	DB_COMPRESSOR_PASSTHROUGH = 2,
};

enum scr_string_t
{
};

// A pointer in the stream: 0, an offset packed by DB_GetPackedOffsetStreamPos, or one of these markers.
#define DB_PTR_INLINE ((unsigned long long)0xFDFDFDFFFFFFFFFFull)   // the data follows in the stream
#define DB_PTR_INSERT ((unsigned long long)0xFDFDFDFFFFFFFFFEull)   // follows, and reserves an alias slot

struct XBlock  // 0x10
{
	unsigned char *data;
	unsigned long long size;
};

struct XZoneMemory  // 0x70
{
	XBlock blocks[MAX_XFILE_COUNT];
};

struct XFile  // 0x48: the first bytes of the decompressed zone
{
	unsigned long long size;
	unsigned long long externalSize;
	unsigned long long blockSize[MAX_XFILE_COUNT];
};

struct StreamPosInfo  // 0x10
{
	unsigned char *pos;
	unsigned int index;
};

struct ScriptStringList  // 0x10
{
	int count;
	const char **strings;
};

union XAssetHeader
{
	void *data;
	const char **name;  // most types start with their name; see DB_GetXAssetName for the others
};

struct XAsset  // 0x10
{
	XAssetType type;
	XAssetHeader header;
};

struct XGfxGlobals;

struct XGlobals  // 0x8
{
	XGfxGlobals *gfxGlobals;
};

struct XAssetList  // 0x28
{
	ScriptStringList stringList;
	int assetCount;
	XAsset *assets;
	XGlobals *globals;
};

struct DBFile  // 0x58
{
	void *handle;
	unsigned long long memoryBufferSize;
	unsigned char *memoryBuffer;
	char name[64];
};

// stream (db_stream.cpp, db_stream_load.cpp, db_fastfile_pointer.cpp)
extern unsigned char *g_streamPos;
extern unsigned char *g_streamPosArray[MAX_XFILE_COUNT];
extern unsigned int g_streamPosIndex;
extern XZoneMemory *g_streamZoneMem;

void DB_InitStreams(XZoneMemory *mem);
void DB_PushStreamPos(unsigned int index);
void DB_PopStreamPos();
unsigned char *DB_InsertPointer();
void Load_Stream(bool atStreamStart, void *ptr, unsigned long long size);
void DB_ConvertOffsetToAlias(unsigned long long *data);
void DB_ConvertOffsetToPointer(unsigned long long *data);
void DB_GetPackedOffsetStreamPos(unsigned long long packed, unsigned int *__restrict blockIndex,
                                 unsigned long long *__restrict offset);
void Load_XStringCustom(const char **str);
void Load_TempStringCustom(const char **str);
void Load_ScriptStringCustom(scr_string_t *var);

// file reading (db_file_load.cpp)
void DB_ReadXFile(unsigned char *pos, unsigned long long size, int flush);
void DB_ReadXFileUncompressed(unsigned char *pos, unsigned long long size);

// the generated loaders' current-object pointers (db_load: varXAssetList, varXString, ...)
extern XAssetList *varXAssetList;
extern XAsset *varXAsset;
extern ScriptStringList *varScriptStringList;
extern XGlobals **varXGlobalsPtr;
extern const char **varXString;
extern const char *varConstChar;
extern const char **varTempString;

scr_string_t SL_GetString(const char *str, unsigned int user);
