// database/db_auth.cpp (Store build)
//
// Signed fastfiles: the compressed data comes in 8 KiB blocks. The first is the authentication header (magic
// "IWffs100", the zone name, the SHA-256 of the subheader, an RSA-2048 PSS signature of that hash, the hashes of
// up to 244 master blocks); then each group is a master block (256 SHA-256 hashes) and up to 256 data blocks.
// A block is checked when all 8 KiB of it are in; a data block is then inflated. Names and layout: the PS4/Xbox One
// server PDBs (database/db_auth.cpp, DB_AuthLoadGlob); the Store build checks the three kinds of block in one
// function (sub_1403489E0, where the servers have DBX_AuthLoad_ProcessHeader, _ProcessMasterBlock and
// _ProcessDataBlock) and inlines DBX_AuthLoad_InflateCopyBuffer into DB_AuthLoad_Inflate. docs/fastfiles.md.

#include <iw6_static.h>

#include "database/db_local.h"

#define IW6_SOURCE "database/db_auth.cpp"

extern "C"
{
	void *memset(void *dst, int c, unsigned long long n);
	void *memcpy(void *dst, const void *src, unsigned long long n);
	int memcmp(const void *a, const void *b, unsigned long long n);

	// libtomcrypt / libtommath (statically linked)
	struct Hash_state
	{
		unsigned char opaque[0x70];
	};
	struct Rsa_key
	{
		unsigned char opaque[0x50];
	};
	struct ltc_math_descriptor
	{
		unsigned char opaque[0x188];
	};
	struct ltc_hash_descriptor;
	int sha256_init(Hash_state *md);
	int sha256_process(Hash_state *md, const unsigned char *in, unsigned long inlen);
	int sha256_done(Hash_state *md, unsigned char *out);
	int find_hash(const char *name);
	int register_hash(const ltc_hash_descriptor *hash);
	int rsa_import(const unsigned char *in, unsigned long inlen, Rsa_key *key);
	int rsa_verify_hash_ex(const unsigned char *sig, unsigned long siglen, const unsigned char *hash,
	                       unsigned long hashlen, int padding, int hash_idx, unsigned long saltlen, int *stat,
	                       Rsa_key *key);
	void rsa_free(Rsa_key *key);
	extern ltc_math_descriptor ltc_mp;
	extern const ltc_math_descriptor ltm_desc;
	extern const ltc_hash_descriptor sha256_desc;

	// zlib, renamed for the database (db_inflate.c, db_zutil.c)
	struct db_z_stream_s;
	int db_inflate(db_z_stream_s *strm, int flush);
	int db_inflateInit_(db_z_stream_s *strm, const char *version, int stream_size);
	int db_inflateEnd(db_z_stream_s *strm);
	void DB_Zip_InitThreadMemory(db_z_stream_s *stream, void *memory, int size);
	void DB_Zip_ShutdownThreadMemory(db_z_stream_s *stream);
}

void tom_game_mem_begin(void *buffer, unsigned long long size);
void tom_game_mem_end();
void I_strncpyz(char *dest, const char *src, int destsize);

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

struct DB_AuthHash  // 0x20
{
	unsigned char bytes[32];
};

struct DB_AuthSignature  // 0x100
{
	unsigned char bytes[256];
};

struct DB_AuthSubheader  // 0x1EA4
{
	char fastfileName[32];
	unsigned int reserved;
	DB_AuthHash masterBlockHashes[244];
};

struct DB_AuthHeader  // 0x1FD0
{
	unsigned char magic[8];
	unsigned int reserved;
	DB_AuthHash subheaderHash;
	DB_AuthSignature signedSubheaderHash;
	DB_AuthSubheader subheader;
};

struct DB_MasterBlock  // 0x2000
{
	DB_AuthHash chunkHashes[256];
};

struct DB_AuthLoadGlob  // 0x6070 in the Store build
{
	int isSecure;
	char expectedFastfileName[32];
	DB_AuthHeader header;
	unsigned char pad[0xC];
	DB_MasterBlock masterBlock;
	unsigned int authedGroupCount;
	unsigned int authedChunkInGroupCount;
	db_z_stream_s stream;
	unsigned int copyBufferEnd;
	unsigned char pad2[8];
	unsigned char copyBuffer[0x2000];
	unsigned char pad3[4];
};

IW6_STATIC DB_AuthLoadGlob g_authLoad IW6_AT("", "g_authLoad");
IW6_STATIC unsigned char db_zipMemory[0x20000] IW6_AT("", "db_zipMemory");
extern unsigned char s_publicKey[0x10E];
extern DB_CompressorType g_compressor;

#define DB_AUTH_MAGIC 0x3030317366665749ull  // "IWffs100"

// Store 140348900 (name unknown): SHA-256 of a buffer (the image pak index's check uses it).
void sub_140348900(const unsigned char *data, unsigned int size, unsigned char *hash)
{
	Hash_state md;
	sha256_init(&md);
	sha256_process(&md, data, size);
	sha256_done(&md, hash);
}

// Store 140348960 (name unknown): DB_LoadXFile's last step hands back the zone's signature (zeros for an unsigned
// zone).
void sub_140348960(unsigned char *signature)
{
	if (g_authLoad.isSecure)
	{
		memcpy(signature, &g_authLoad.header.signedSubheaderHash, sizeof(DB_AuthSignature));
		return;
	}
	memset(signature, 0, sizeof(DB_AuthSignature));
}

// Store 140348BA0 (name unknown): does the SHA-256 of a buffer equal `hash`?
bool sub_140348BA0(const unsigned char *data, unsigned int size, const DB_AuthHash *hash)
{
	Hash_state md;
	unsigned char digest[32];
	sha256_init(&md);
	sha256_process(&md, data, size);
	sha256_done(&md, digest);
	return memcmp(hash, digest, 32) == 0;
}

// Store 140348C60 (PS4 PDB database/db_auth.cpp:225): RSA PSS (padding 3 = LTC_PKCS_1_PSS), SHA-256, salt 8.
bool DBX_AuthLoad_ValidateSignature_Try(const DB_AuthHash *hash, const DB_AuthSignature *signature)
{
	int hashIndex = find_hash("sha256");
	if (hashIndex == -1)
		return false;
	Rsa_key key;
	int stat;
	if (rsa_import(s_publicKey, sizeof(s_publicKey), &key))
		return false;
	stat = 0;
	int err = rsa_verify_hash_ex(signature->bytes, sizeof(signature->bytes), hash->bytes, sizeof(hash->bytes), 3,
	                             hashIndex, 8, &stat, &key);
	rsa_free(&key);
	return !err && stat == 1;
}

// Store 140348C10 (PS4 PDB database/db_auth.cpp:280): the bignum code allocates from a 48000-byte stack arena.
bool DBX_AuthLoad_ValidateSignature(const DB_AuthHash *hash, const DB_AuthSignature *signature)
{
	unsigned char arena[48000];
	tom_game_mem_begin(arena, sizeof(arena));
	bool valid = DBX_AuthLoad_ValidateSignature_Try(hash, signature);
	tom_game_mem_end();
	return valid;
}

// Store 1403489E0 (name unknown; the servers' DBX_AuthLoad_ProcessHeader, _ProcessMasterBlock and _ProcessDataBlock
// in one): checks one 8 KiB block. *notData tells the caller that the block was the header or a master block
// (nothing to inflate).
bool sub_1403489E0(const unsigned char *block, bool *notData)
{
	if (g_authLoad.authedGroupCount)
	{
		if (!g_authLoad.authedChunkInGroupCount)
		{
			*notData = true;
			if (!sub_140348BA0(block, 0x2000,
			                   &g_authLoad.header.subheader.masterBlockHashes[g_authLoad.authedGroupCount - 1]))
				return false;
			memcpy(&g_authLoad.masterBlock, block, sizeof(DB_MasterBlock));
			g_authLoad.authedChunkInGroupCount = 1;
			return true;
		}
		*notData = false;
		if (!sub_140348BA0(block, 0x2000, &g_authLoad.masterBlock.chunkHashes[g_authLoad.authedChunkInGroupCount - 1]))
			return false;
		if (++g_authLoad.authedChunkInGroupCount == 0x101)
		{
			++g_authLoad.authedGroupCount;
			g_authLoad.authedChunkInGroupCount = 0;
		}
		return true;
	}
	*notData = true;
	const DB_AuthHeader *header = (const DB_AuthHeader *)block;
	if (*(const unsigned long long *)header->magic != DB_AUTH_MAGIC || header->subheader.fastfileName[31])
		return false;
	Hash_state md;
	DB_AuthHash digest;
	sha256_init(&md);
	sha256_process(&md, (const unsigned char *)&header->subheader, sizeof(header->subheader));
	sha256_done(&md, digest.bytes);
	if (memcmp(&header->subheaderHash, &digest, sizeof(digest)) ||
	    !DBX_AuthLoad_ValidateSignature(&header->subheaderHash, &header->signedSubheaderHash) ||
	    memcmp(g_authLoad.expectedFastfileName, header->subheader.fastfileName, 32))
		return false;
	memcpy(&g_authLoad.header, block, sizeof(DB_AuthHeader));
	g_authLoad.authedGroupCount = 1;
	g_authLoad.authedChunkInGroupCount = 0;
	return true;
}

// Store 140348D30 (PS4 PDB DB_AuthLoad_Inflate, database/db_auth.cpp:1199, with DBX_AuthLoad_InflateCopyBuffer
// (:988) inlined): unsigned, inflate (or copy, for passthrough) straight from the caller's stream; signed, gather
// 8 KiB, check it, and inflate a data block from g_authLoad's own stream.
int DB_AuthLoad_Inflate(db_z_stream_s *stream, int flush, int finish)
{
	if (!g_authLoad.isSecure)
	{
		if (g_compressor == DB_COMPRESSOR_ZLIB)
			return stream->avail_in ? db_inflate(stream, flush) : 0;
		if (g_compressor != DB_COMPRESSOR_PASSTHROUGH)
			return -3;
		unsigned int n = stream->avail_in;
		if (stream->avail_out <= n)
			n = stream->avail_out;
		memcpy(stream->next_out, stream->next_in, n);
		stream->avail_in -= n;
		stream->next_in += n;
		stream->total_in += n;
		stream->avail_out -= n;
		stream->next_out += n;
		stream->total_out += n;
		return 0;
	}
	for (;;)
	{
		if (g_authLoad.copyBufferEnd < 0x2000)
		{
			unsigned int n = 0x2000 - g_authLoad.copyBufferEnd;
			if ((int)stream->avail_in <= (int)n)
				n = stream->avail_in;
			memcpy(g_authLoad.copyBuffer + g_authLoad.copyBufferEnd, stream->next_in, n);
			stream->next_in += n;
			stream->avail_in -= n;
			stream->total_in += n;
			g_authLoad.copyBufferEnd += n;
			if (g_authLoad.copyBufferEnd < 0x2000)
				return 0;
			bool notData;
			if (!sub_1403489E0(g_authLoad.copyBuffer, &notData))
			{
				g_authLoad.copyBufferEnd = 0;
				return -6;
			}
			if (notData)
			{
				g_authLoad.copyBufferEnd = 0;
				continue;
			}
			g_authLoad.stream.next_in = g_authLoad.copyBuffer;
			g_authLoad.stream.avail_in = 0x2000;
		}
		g_authLoad.stream.total_out = stream->total_out;
		g_authLoad.stream.next_out = stream->next_out;
		g_authLoad.stream.avail_out = stream->avail_out;
		int err;
		if (g_compressor == DB_COMPRESSOR_ZLIB)
		{
			err = db_inflate(&g_authLoad.stream, flush);
		}
		else if (g_compressor == DB_COMPRESSOR_PASSTHROUGH)
		{
			unsigned int n = g_authLoad.stream.avail_out;
			if (g_authLoad.stream.avail_in < n)
				n = g_authLoad.stream.avail_in;
			memcpy(g_authLoad.stream.next_out, g_authLoad.stream.next_in, n);
			g_authLoad.stream.avail_in -= n;
			g_authLoad.stream.next_in += n;
			g_authLoad.stream.total_in += n;
			g_authLoad.stream.avail_out -= n;
			g_authLoad.stream.next_out += n;
			g_authLoad.stream.total_out += n;
			err = 0;
		}
		else
		{
			err = -3;
		}
		stream->total_out = g_authLoad.stream.total_out;
		stream->next_out = g_authLoad.stream.next_out;
		stream->avail_out = g_authLoad.stream.avail_out;
		if (!g_authLoad.stream.avail_in)
		{
			g_authLoad.copyBufferEnd = 0;
			g_authLoad.stream.next_in = nullptr;
		}
		if (err)
			return err;
		if (!g_authLoad.stream.avail_out)
			return 0;
	}
}

// Store 140348F60 (PS4 PDB database/db_auth.cpp:1153)
void DB_AuthLoad_InflateEnd(db_z_stream_s *stream)
{
	if (g_authLoad.isSecure)
	{
		if (g_compressor == DB_COMPRESSOR_ZLIB)
		{
			db_inflateEnd(&g_authLoad.stream);
			DB_Zip_ShutdownThreadMemory(&g_authLoad.stream);
		}
		*stream = g_authLoad.stream;
		memset(&g_authLoad, 0, sizeof(g_authLoad));
		return;
	}
	memset(&g_authLoad, 0, sizeof(g_authLoad));
	if (g_compressor == DB_COMPRESSOR_ZLIB)
	{
		db_inflateEnd(stream);
		DB_Zip_ShutdownThreadMemory(stream);
	}
}

// Store 140349030 (PS4 PDB database/db_auth.cpp:1080)
int DB_AuthLoad_InflateInit(db_z_stream_s *stream, int isSecure, const char *expectedFastfileName)
{
	memset(&g_authLoad, 0, sizeof(g_authLoad));
	g_authLoad.stream = *stream;  // all but the input side, which starts empty
	g_authLoad.stream.avail_in = 0;
	g_authLoad.stream.total_in = 0;
	g_authLoad.stream.next_in = nullptr;
	g_authLoad.isSecure = isSecure;
	I_strncpyz(g_authLoad.expectedFastfileName, expectedFastfileName, sizeof(g_authLoad.expectedFastfileName));
	if (!g_authLoad.isSecure)
	{
		if (g_compressor == DB_COMPRESSOR_ZLIB)
		{
			DB_Zip_InitThreadMemory(stream, db_zipMemory, sizeof(db_zipMemory));
			return db_inflateInit_(stream, "1.1.4", sizeof(db_z_stream_s));
		}
		if (g_compressor == DB_COMPRESSOR_PASSTHROUGH)
		{
			stream->total_in = 0;
			stream->total_out = 0;
			return 0;
		}
		return -3;
	}
	ltc_mp = ltm_desc;
	register_hash(&sha256_desc);
	if (g_compressor == DB_COMPRESSOR_ZLIB)
	{
		DB_Zip_InitThreadMemory(&g_authLoad.stream, db_zipMemory, sizeof(db_zipMemory));
		return db_inflateInit_(&g_authLoad.stream, "1.1.4", sizeof(db_z_stream_s));
	}
	if (g_compressor == DB_COMPRESSOR_PASSTHROUGH)
	{
		g_authLoad.stream.total_in = 0;
		g_authLoad.stream.total_out = 0;
		return 0;
	}
	return -3;
}
