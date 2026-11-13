// database/db_file_load.cpp (Store build)
//
// Reading a fastfile: 256 KiB stages into two alternating buffers (g_fileBuf), asynchronously with ReadFileEx and
// an alertable SleepEx, or by copying from a memory-backed DBFile (handle NULL); the uncompressed prefix is read
// straight from the stage buffers (DB_ReadXFileUncompressed), the rest through DB_AuthLoad_Inflate (db_auth.cpp).
// Names: the PS4/Xbox One server PDBs (database/db_file_load.cpp). The Store build's DB_LoadData is 0xD0 bytes (the
// servers' 0xB0, with a zlib 1.2 z_stream of 0x58 bytes); its file and the end offset of each read started are
// also kept in two words in front of it (read by 1403766FF, a load progress query; names unknown).

#include <iw6_static.h>
#include <windows.h>

#include "database/db_local.h"
#include "qcommon/qcommon.h"

#define IW6_SOURCE "database/db_file_load.cpp"

struct _OVERLAPPED  // Win32
{
	unsigned long long Internal;
	unsigned long long InternalHigh;
	unsigned int Offset;
	unsigned int OffsetHigh;
	void *hEvent;
};
typedef _OVERLAPPED OVERLAPPED;
typedef void (*LPOVERLAPPED_COMPLETION_ROUTINE)(DWORD, DWORD, OVERLAPPED *);
#define ERROR_HANDLE_EOF 38

extern "C"
{
	BOOL ReadFileEx(HANDLE file, void *buffer, DWORD bytes, OVERLAPPED *overlapped,
	                                      LPOVERLAPPED_COMPLETION_ROUTINE completion);
	DWORD SleepEx(DWORD milliseconds, BOOL alertable);
	BOOL CloseHandle(HANDLE handle);
	DWORD GetLastError(void);
	void *memset(void *dst, int c, unsigned long long n);
	void *memcpy(void *dst, const void *src, unsigned long long n);
	int remove(const char *path);
}

struct db_z_stream_s  // zlib's z_stream (1.2 layout, uLong = 32 bits): 0x58
{
	unsigned char *next_in;
	unsigned int avail_in;
	unsigned int total_in;
	unsigned char *next_out;
	unsigned int avail_out;
	unsigned int total_out;
	char *msg;
	void *state;
	void *zalloc;
	void *zfree;
	void *opaque;
	int data_type;
	unsigned int adler;
	unsigned int reserved;
};

struct DB_LoadData  // 0xD0 in the Store build
{
	DBFile *file;
	unsigned char *fileBuffer;
	unsigned long long readSize;            // still to read: -1 (unknown) until a short read
	unsigned long long completedReadSize;
	unsigned long long offset;
	unsigned char *start_in;
	OVERLAPPED overlapped;
	unsigned int readError;
	db_z_stream_s stream;
	int readingResident;                    // the load bar counts the bytes read
	unsigned char unknown[0x1C];
};

IW6_STATIC DB_LoadData g_load IW6_AT("", "g_load");
IW6_STATIC volatile unsigned int g_loadOutstandingRead IW6_AT("", "g_loadOutstandingRead");
IW6_STATIC unsigned char g_fileBuf[2][0x40000] IW6_AT("", "g_fileBuf");
IW6_STATIC bool s_compressorTypeIsSet IW6_AT("", "s_compressorTypeIsSet");
IW6_STATIC int s_compressorTypeIndex IW6_AT("", "s_compressorTypeIndex");
IW6_STATIC DBFile *unk_1443A4888 IW6_AT("", "unk_1443A4888");                       // the file of the last read
IW6_STATIC unsigned long long unk_1443A4890 IW6_AT("", "unk_1443A4890");            // its end offset

extern DB_CompressorType g_compressor;

void Sys_Error(const char *fmt, ...);
int I_strcmp(const char *s0, const char *s1);
const char *LiveStorage_GetLocalPlaylistFilename();
void Sys_WaitDatabaseThread();                            // Store 14046FFB0
void LoadBar_ReadResident(unsigned long long bytes);      // Store 140190E40
int DB_AuthLoad_Inflate(db_z_stream_s *stream, int flush, int finish);  // db_auth.cpp, Store 140348D30
int DB_AuthLoad_InflateInit(db_z_stream_s *stream, int isSecure, const char *expectedFastfileName);
void DB_AuthLoad_InflateEnd(db_z_stream_s *stream);
void DB_ReadXFileStage();
void DB_WaitXFileStage();

// The common fatal path (inline in the Store build): a broken mp_playlists download is deleted before the error.
static void DB_RemoveBrokenPlaylists()
{
	if (!I_strcmp(g_load.file->name, "mp_playlists"))
	{
		CloseHandle(g_load.file->handle);
		remove(LiveStorage_GetLocalPlaylistFilename());
	}
}

// Store 1403496B0 (PS4 PDB database/db_file_load.cpp:1557)
void DB_DirtyDiscError()
{
	DB_RemoveBrokenPlaylists();
	Sys_Error("Disc read error '%s'", g_load.file->name);
}

// Store 140349710 (PS4 PDB DB_FileReadCompletion): ReadFileEx's completion routine.
void DB_FileReadCompletion(unsigned long dwErrorCode, unsigned long dwNumberOfBytesTransfered, OVERLAPPED *lpOverlapped)
{
	g_load.readError = dwErrorCode;
	g_load.completedReadSize = dwErrorCode ? 0 : dwNumberOfBytesTransfered;
}

// Store 140349730 (PS4 PDB database/db_file_load.cpp:406)
void DB_FinishLoadXFile()
{
	g_load.file = nullptr;
}

// Store 1403497F0: the file being loaded (name unknown; image streaming takes it for rows in the fastfile itself).
DBFile *sub_1403497F0()
{
	return g_load.file;
}

// Store 140349820 (PS4 PDB database/db_file_load.cpp:1122): a signed file always goes through the authentication
// layer; an unsigned one only when it is memory-backed (handle NULL) - a disk file with an unsigned header is a
// disc error.
void DB_InflateInit(int isSecure)
{
	if ((isSecure || !g_load.file->handle) &&
	    !DB_AuthLoad_InflateInit(&g_load.stream, isSecure, g_load.file->name))
		return;
	DB_DirtyDiscError();
}

// Store 140349890 (PS4 PDB database/db_file_load.cpp:1212)
void DB_InflateShutdown()
{
	DB_AuthLoad_InflateEnd(&g_load.stream);
}

// Store 1403498A0 (PS4 PDB database/db_file_load.cpp:1563)
void DB_InitLoadXFile(DBFile *file, unsigned long long offset)
{
	memset(&g_load, 0, sizeof(g_load));
	g_load.file = file;
	g_load.fileBuffer = g_fileBuf[0];
	g_load.offset = offset;
	g_load.readSize = ~0ull;
	g_load.readingResident = 1;
	if (g_loadOutstandingRead == 1)
		SleepEx(INFINITE, 1);
	g_loadOutstandingRead = 0;
	DB_ReadXFileStage();
	if (!g_loadOutstandingRead)
	{
		DB_RemoveBrokenPlaylists();
		Com_Error(ERR_DROP, "Fastfile for zone '%s' is empty.", g_load.file->name);
	}
}

// Store 140349A50 (PS4 PDB database/db_file_load.cpp:978): finish the outstanding stage, hand its buffer to the
// stream, switch buffers and start the next stage while any of the file is left.
void DB_WaitXFileStage()
{
	if (!g_loadOutstandingRead)
	{
		DB_RemoveBrokenPlaylists();
		Sys_Error("Disc read error '%s'", g_load.file->name);
	}
	if (g_loadOutstandingRead == 1)
		SleepEx(INFINITE, 1);
	g_loadOutstandingRead = 0;
	if (g_load.readError && g_load.readError != ERROR_HANDLE_EOF)
		g_load.completedReadSize = 0;
	g_load.offset += g_load.completedReadSize;
	g_load.readSize = g_load.completedReadSize == 0x40000 ? g_load.readSize - 0x40000 : 0;
	g_load.stream.avail_in = (unsigned int)g_load.completedReadSize;
	g_load.stream.next_in = g_load.fileBuffer;
	g_load.start_in = g_load.fileBuffer;
	unsigned char *next = g_load.fileBuffer + 0x40000;
	g_load.fileBuffer = next == g_fileBuf[0] + sizeof(g_fileBuf) ? g_fileBuf[0] : next;
	if (g_load.readingResident)
		LoadBar_ReadResident(g_load.completedReadSize);
	if (g_load.readSize)
		DB_ReadXFileStage();
}

// Store 140349B80 (PS4 PDB database/db_file_load.cpp:1272)
void DB_ReadXFile(unsigned char *pos, unsigned long long size, int flush)
{
	g_load.stream.next_out = pos;
	g_load.stream.avail_out = (unsigned int)size;
	for (;;)
	{
		if ((unsigned int)DB_AuthLoad_Inflate(&g_load.stream, 2, flush) > 1)
		{
			DB_RemoveBrokenPlaylists();
			Sys_Error("Disc read error '%s'", g_load.file->name);
		}
		if (!g_load.stream.avail_out)
			return;
		DB_WaitXFileStage();
	}
}

// Store 140349C30 (PS4 PDB database/db_file_load.cpp:468): start reading the next 256 KiB (or what is left).
void DB_ReadXFileStage()
{
	Sys_WaitDatabaseThread();
	unsigned int bytes = g_load.readSize > 0x40000 ? 0x40000 : (unsigned int)g_load.readSize;
	if (!g_load.file->handle)
	{
		g_load.readError = 0;
		if (!g_load.file->memoryBufferSize)
		{
			g_load.completedReadSize = 0;
			return;
		}
		int n = (int)g_load.file->memoryBufferSize;
		if (n >= (int)bytes)
			n = (int)bytes;
		memcpy(g_load.fileBuffer, g_load.file->memoryBuffer, (unsigned int)n);
		g_load.file->memoryBuffer += (unsigned int)n;
		g_load.file->memoryBufferSize -= (unsigned int)n;
		g_load.completedReadSize = (unsigned int)n;
		g_loadOutstandingRead = 2;
		return;
	}
	unk_1443A4888 = g_load.file;
	unk_1443A4890 = g_load.offset + bytes;
	g_load.overlapped.Internal = 0;
	g_load.overlapped.InternalHigh = 0;
	g_load.overlapped.Offset = (unsigned int)g_load.offset;
	g_load.overlapped.OffsetHigh = (unsigned int)(g_load.offset >> 32);
	g_load.overlapped.hEvent = nullptr;
	if (ReadFileEx(g_load.file->handle, g_load.fileBuffer, bytes, &g_load.overlapped,
	               (LPOVERLAPPED_COMPLETION_ROUTINE)DB_FileReadCompletion))
	{
		g_loadOutstandingRead = 1;
		return;
	}
	unsigned int err = GetLastError();
	if (err != ERROR_HANDLE_EOF)
		Sys_Error("Read error of file '%s' (0x%08x)", g_load.file->name, err);
}

// Store 140349E20 (PS4 PDB database/db_file_load.cpp:1220): bytes straight from the stage buffers (the header in
// front of the compressed data); a NULL pos skips them.
void DB_ReadXFileUncompressed(unsigned char *pos, unsigned long long size)
{
	g_load.stream.next_out = pos;
	g_load.stream.avail_out = (unsigned int)size;
	for (;;)
	{
		if (g_load.stream.avail_in)
		{
			unsigned int n = g_load.stream.avail_out;
			if (n >= g_load.stream.avail_in)
				n = g_load.stream.avail_in;
			if (g_load.stream.next_out)
			{
				memcpy(g_load.stream.next_out, g_load.stream.next_in, n);
				g_load.stream.next_out += n;
			}
			g_load.stream.next_in += n;
			g_load.stream.avail_in -= n;
			g_load.stream.avail_out -= n;
			if (!g_load.stream.avail_out)
				return;
		}
		DB_WaitXFileStage();
	}
}

// Store 14034A000 (PS4 PDB database/db_file_load.cpp:1828): the first zone fixes the compressor for the process.
void DB_SetFileLoadCompressor(int compressor)
{
	if (s_compressorTypeIsSet)
	{
		if (s_compressorTypeIndex != compressor)
			Sys_Error("Mixed compression types are not supported");
		return;
	}
	s_compressorTypeIsSet = true;
	s_compressorTypeIndex = compressor;
	if (compressor == 0)
	{
		g_compressor = DB_COMPRESSOR_ZLIB;
		return;
	}
	if (compressor != 2)
	{
		Sys_Error("Unknown compression type");
		return;
	}
	g_compressor = DB_COMPRESSOR_PASSTHROUGH;
}
