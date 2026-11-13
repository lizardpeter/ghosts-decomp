#!/usr/bin/env python3
"""Reference reader for Call of Duty: Ghosts PC fastfiles (.ff), following the Microsoft Store build's loader.

    python3 tools/fastfile/iw6ff.py ZONE.ff [--exe iw6mp64_MSStore_ship.exe] [--strings] [--json]

Standard library only (zlib, hashlib). Every rule below is the Store build's code; docs/fastfiles.md gives the
addresses. In order:

1. The prefix, read uncompressed (DB_LoadXFile 140349300 through DB_ReadXFileUncompressed 140349E20): magic
   "IWff0100" (signed) or "IWffu100" (unsigned), anything else is DB_DirtyDiscError; version 0x235; four bytes
   (the second is the compressor: 0 zlib, 2 passthrough); 8 bytes the loader reads and ignores; the streamed image
   row count (at most 0x6280) and its 24-byte rows; two 64-bit sizes (the load bar's).
2. The container (DB_AuthLoad_*, 140348D30 / 1403489E0): a signed file is a chain of 8 KiB blocks: an
   authentication header ("IWffs100", the zone name, a SHA-256 of the subheader, an RSA-2048 PSS signature of that
   hash, up to 244 master block hashes), then for each group a master block of 256 SHA-256 hashes followed by up to
   256 data blocks. Only whole 8 KiB blocks are ever processed. The data blocks are one zlib stream. An unsigned
   file is the compressed stream directly.
3. The zone (the decompressed stream): the XFile header (0x48 bytes), then the XAssetList (0x28 bytes, read
   straight into g_varXAssetList), then everything the Load_* functions read through Load_Stream, in order: the
   script strings, XGlobals, the XAsset array, and each asset.

The stream (class Stream) is the game's DB_* stream: seven blocks, a current block, a push/pop stack, alignment,
and the pointer encoding. It keeps an image of each block's memory, laid out exactly as the game lays it out
(Load_Stream copies into the current block position; the runtime block is zero-filled, never read from the file),
with pointers written as the game writes them, at block base addresses the caller chooses.

Asset bodies are parsed by the loaders in ASSET_LOADERS (type -> function(stream, varptr_address)); one that is
missing stops the walk, since the next asset starts where the previous one ended. Per-type work adds loaders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

# --- constants (Store build) ------------------------------------------------------------------------------------

MAGIC_SIGNED = b"IWff0100"     # 0x3030313066665749
MAGIC_UNSIGNED = b"IWffu100"   # 0x3030317566665749
MAGIC_AUTH = b"IWffs100"       # 0x3030317366665749
VERSION = 0x235
MAX_STREAM_IMAGE_ROWS = 0x6280
STREAM_IMAGE_ROW = 0x18
AUTH_BLOCK = 0x2000
AUTH_CHUNKS_PER_GROUP = 0x100  # data blocks per master block (the counter wraps at 0x101, master included)
AUTH_MAX_GROUPS = 244          # DB_AuthHeader.masterBlockHashes[244]
COMPRESSOR_ZLIB, COMPRESSOR_PASSTHROUGH = 0, 2
STORE_EXE_PUBLIC_KEY_VA, PUBLIC_KEY_LEN = 0x140992AA0, 0x10E

XFILE_SIZE = 0x48
XASSET_LIST_SIZE = 0x28
BLOCK_NAMES = ("temp", "physical", "runtime", "virtual", "large", "callback", "script")
XFILE_BLOCK_TEMP, XFILE_BLOCK_PHYSICAL, XFILE_BLOCK_RUNTIME, XFILE_BLOCK_VIRTUAL = 0, 1, 2, 3
PTR_INLINE = 0xFDFDFDFFFFFFFFFF   # -1 with FD fill: the data follows in the stream
PTR_INSERT = 0xFDFDFDFFFFFFFFFE   # -2: follows in the stream, and an alias slot is reserved (DB_InsertPointer)

# (enum value, name from the type name table 1409920A0, header size from DB_GetXAssetTypeSize's table 1409928A0,
#  offset of the name pointer in the header from the name getter table 1409924A0); None: no handlers in this build
ASSET_TYPES = {
    0x00: ("physpreset", 0x58, 0x0), 0x01: ("phys_collmap", 0x58, 0x0), 0x02: ("xanim", 0x88, 0x0),
    0x03: ("xmodelsurfs", 0x38, 0x0), 0x04: ("xmodel", 0x258, 0x0), 0x05: ("material", 0x3A8, 0x0),
    0x06: ("computeshader", 0x20, 0x0), 0x07: ("vertexshader", 0x28, 0x0), 0x08: ("hullshader", 0x20, 0x0),
    0x09: ("domainshader", 0x20, 0x0), 0x0A: ("pixelshader", 0x28, 0x0), 0x0B: ("vertexdecl", 0x838, 0x0),
    0x0C: ("techset", 0xCF0, 0x0), 0x0D: ("image", 0x68, 0x60), 0x0E: ("sound", 0x18, 0x0),
    0x0F: ("sndcurve", 0x98, 0x8), 0x10: ("lpfcurve", 0x98, 0x8), 0x11: ("reverbsendcurve", 0x98, 0x8),
    0x12: ("loaded_sound", 0x38, 0x0), 0x13: ("col_map_mp", 0x280, 0x0), 0x14: ("com_map", 0x28, 0x0),
    0x15: ("glass_map", 0x10, 0x0), 0x16: ("aipaths", 0x88, 0x0), 0x17: ("vehicle_track", 0x18, 0x0),
    0x18: ("map_ents", 0x100, 0x0), 0x19: ("fx_map", 0xB0, 0x0), 0x1A: ("gfx_map", 0xA30, 0x0),
    0x1B: ("lightdef", 0x30, 0x0), 0x1C: ("ui_map", None, None), 0x1D: ("font", 0x28, 0x0),
    0x1E: ("menufile", 0x18, 0x0), 0x1F: ("menu", 0xC8, 0x8), 0x20: ("animclass", 0x58, 0x0),
    0x21: ("localize", 0x10, 0x8), 0x22: ("attachment", 0x118, 0x0), 0x23: ("weapon", 0xA98, 0x0),
    0x24: ("snddriverglobals", 0x18, 0x0), 0x25: ("fx", 0x40, 0x0), 0x26: ("impactfx", 0x10, 0x0),
    0x27: ("surfacefx", 0x10, 0x0), 0x28: ("aitype", None, None), 0x29: ("mptype", None, None),
    0x2A: ("character", None, None), 0x2B: ("xmodelalias", None, None), 0x2C: ("rawfile", 0x18, 0x0),
    0x2D: ("scriptfile", 0x28, 0x0), 0x2E: ("stringtable", 0x18, 0x0), 0x2F: ("leaderboarddef", 0x28, 0x0),
    0x30: ("structureddatadef", 0x18, 0x0), 0x31: ("tracer", 0x78, 0x0), 0x32: ("vehicle", 0x610, 0x0),
    0x33: ("addon_map_ents", 0x68, 0x0), 0x34: ("netconststrings", 0x20, 0x0), 0x35: ("reverbpreset", 0x48, 0x0),
    0x36: ("luafile", 0x18, 0x0), 0x37: ("scriptable", 0x40, 0x0), 0x38: ("colorization", 0x30, 0x28),
    0x39: ("colorizationset", 0x68, 0x0), 0x3A: ("tonemapping", 0x70, 0x68), 0x3B: ("equipsndtable", 0x58, 0x0),
    0x3C: ("vectorfield", 0x50, 0x0), 0x3D: ("dopplerpreset", 0x20, 0x0), 0x3E: ("particlesimanimation", 0x60, 0x0),
}


class FastFileError(Exception):
    """A check the game makes failed; `check` names it (as the game's error or the failing function)."""

    def __init__(self, check: str, detail: str = ""):
        super().__init__(f"{check}: {detail}" if detail else check)
        self.check = check


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# --- RSA (the game's libtomcrypt rsa_verify_hash_ex, LTC_PKCS_1_PSS, SHA-256, salt length 8) ---------------------

def _der_int(data: bytes, at: int) -> tuple[int, int]:
    if data[at] != 0x02:
        raise ValueError("DER INTEGER expected")
    n, at = _der_len(data, at + 1)
    return int.from_bytes(data[at:at + n], "big"), at + n


def _der_len(data: bytes, at: int) -> tuple[int, int]:
    first = data[at]
    if first < 0x80:
        return first, at + 1
    k = first & 0x7F
    return int.from_bytes(data[at + 1:at + 1 + k], "big"), at + 1 + k


def parse_public_key(der: bytes) -> tuple[int, int]:
    """PKCS#1 RSAPublicKey (SEQUENCE { n, e }), as rsa_import reads the game's key: (n, e)."""
    if der[0] != 0x30:
        raise ValueError("DER SEQUENCE expected")
    _, at = _der_len(der, 1)
    n, at = _der_int(der, at)
    e, _ = _der_int(der, at)
    return n, e


def public_key_from_exe(path: str | Path) -> tuple[int, int]:
    """The Store build's fastfile key: 0x10E bytes at 140992AA0 (passed to rsa_import by 140348C60)."""
    data = Path(path).read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec, optsize = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
    rva = STORE_EXE_PUBLIC_KEY_VA - base
    for i in range(nsec):
        s = pe + 24 + optsize + 40 * i
        vsize, va, rawsize, raw = struct.unpack_from("<IIII", data, s + 8)
        if va <= rva < va + max(vsize, rawsize):
            off = raw + rva - va
            return parse_public_key(data[off:off + PUBLIC_KEY_LEN])
    raise ValueError("key address not in any section")


def _mgf1(seed: bytes, length: int) -> bytes:
    out, counter = b"", 0
    while len(out) < length:
        out += _sha256(seed + counter.to_bytes(4, "big"))
        counter += 1
    return out[:length]


def rsa_pss_verify(key: tuple[int, int], digest: bytes, signature: bytes, salt_len: int = 8) -> bool:
    """EMSA-PSS verification of a SHA-256 digest (RFC 8017 9.1.2), as libtomcrypt's pkcs_1_pss_decode with
    modulus_bitlen - 1 bits."""
    n, e = key
    k = (n.bit_length() + 7) // 8
    if len(signature) != k:
        return False
    s = int.from_bytes(signature, "big")
    if s >= n:
        return False
    em_bits = n.bit_length() - 1
    em_len = (em_bits + 7) // 8
    em = pow(s, e, n).to_bytes(k, "big")
    if em_len < k:          # the modulus' top byte holds only the sign bit of EM
        if em[0] != 0:
            return False
        em = em[1:]
    h_len = 32
    if em_len < h_len + salt_len + 2 or em[-1] != 0xBC:
        return False
    masked, h = em[:em_len - h_len - 1], em[em_len - h_len - 1:-1]
    top_bits = 8 * em_len - em_bits
    if masked[0] >> (8 - top_bits) if top_bits else 0:
        return False
    db = bytes(a ^ b for a, b in zip(masked, _mgf1(h, len(masked))))
    db = bytes([db[0] & (0xFF >> top_bits)]) + db[1:]
    pad = em_len - h_len - salt_len - 2
    if db[:pad] != b"\0" * pad or db[pad] != 1:
        return False
    salt = db[pad + 1:]
    return _sha256(b"\0" * 8 + digest + salt) == h


# --- the prefix ----------------------------------------------------------------------------------------------------

@dataclass
class StreamImageRow:
    """One 24-byte row (Load_ImageStream 140374E70 takes four per streamed GfxImage, one per picmip level):
    localized selects "<language>_imagefile<N>.pak" over "imagefile<N>.pak"; file 0 is the fastfile itself."""
    localized: int
    file: int
    offset: int
    end: int

    @property
    def path(self) -> str | None:
        if self.offset == 0 and self.end == 0 and self.file == 0:
            return None
        if self.file == 0:
            return "<this fastfile>"
        return f"{'<language>_' if self.localized else ''}imagefile{self.file}.pak"


@dataclass
class Prefix:
    magic: bytes
    version: int
    header_bytes: bytes      # four bytes; [1] is the compressor
    unused: bytes            # eight bytes the loader reads and drops
    stream_images: list[StreamImageRow]
    loadbar_sizes: tuple[int, int]
    payload_offset: int

    @property
    def signed(self) -> bool:
        return self.magic != MAGIC_UNSIGNED      # DB_InflateInit(magic != "IWffu100")

    @property
    def compressor(self) -> int:
        return self.header_bytes[1]


def read_prefix(data: bytes) -> Prefix:
    def take(at, n):
        if at + n > len(data):
            raise FastFileError("DB_DirtyDiscError", "file ends inside the prefix")
        return data[at:at + n]
    magic = take(0, 8)
    if magic not in (MAGIC_SIGNED, MAGIC_UNSIGNED):
        raise FastFileError("DB_DirtyDiscError", f"magic {magic!r}")
    version, = struct.unpack("<I", take(8, 4))
    if version != VERSION:
        raise FastFileError("version", f"{version:#x}, expecting {VERSION:#x}")
    header_bytes, unused = take(12, 4), take(16, 8)
    if header_bytes[1] not in (COMPRESSOR_ZLIB, COMPRESSOR_PASSTHROUGH):
        raise FastFileError("DB_SetFileLoadCompressor", "Unknown compression type")
    count, = struct.unpack("<I", take(24, 4))
    if count > MAX_STREAM_IMAGE_ROWS:
        raise FastFileError("DB_DirtyDiscError", f"{count} streamed image rows")
    rows = []
    for i in range(count):
        loc, file, _pad, off, end = struct.unpack("<HHIQQ", take(28 + STREAM_IMAGE_ROW * i, STREAM_IMAGE_ROW))
        rows.append(StreamImageRow(loc, file, off, end))
    at = 28 + STREAM_IMAGE_ROW * count
    sizes = struct.unpack("<QQ", take(at, 16))
    return Prefix(magic, version, header_bytes, unused, rows, sizes, at + 16)


# --- the container -------------------------------------------------------------------------------------------------

@dataclass
class AuthReport:
    zone_name: str
    signature: bytes
    signature_checked: bool
    groups: int
    data_blocks: int
    trailing_bytes: int      # bytes after the last whole 8 KiB block: never processed by the game


def _auth_blocks(payload: bytes, expected_name: str | None, key) -> tuple[list[bytes], AuthReport]:
    """The game's block chain (1403489E0): header block, then per group a master block and its data blocks."""
    blocks = [payload[i:i + AUTH_BLOCK] for i in range(0, len(payload) - AUTH_BLOCK + 1, AUTH_BLOCK)]
    trailing = len(payload) % AUTH_BLOCK
    if not blocks:
        raise FastFileError("DB_AuthLoad", "no authentication header block")
    hdr = blocks[0]
    if hdr[:8] != MAGIC_AUTH or hdr[0x14B] != 0:
        raise FastFileError("DB_AuthLoad header", "magic or unterminated name")
    sub_hash, signature, subheader = hdr[0xC:0x2C], hdr[0x2C:0x12C], hdr[0x12C:0x12C + 0x1EA4]
    if _sha256(subheader) != sub_hash:
        raise FastFileError("DB_AuthLoad header", "subheader hash")
    if key is not None and not rsa_pss_verify(key, sub_hash, signature):
        raise FastFileError("DB_AuthLoad header", "RSA signature")
    name_field = subheader[:0x20]
    if expected_name is not None:
        want = expected_name.encode("latin1")[:0x1F]
        if name_field != want + b"\0" * (0x20 - len(want)):
            raise FastFileError("DB_AuthLoad header", f"zone name {name_field.rstrip(b'\0')!r}")
    master_hashes = subheader[0x24:]
    data, group, chunk, master = [], 1, 0, None
    for b in blocks[1:]:
        if chunk == 0:
            if group > AUTH_MAX_GROUPS:
                # the game would index past masterBlockHashes[243] (docs/fastfiles.md); no retail file gets here
                raise FastFileError("DB_AuthLoad master block", f"group {group} beyond {AUTH_MAX_GROUPS}")
            if _sha256(b) != master_hashes[32 * (group - 1):32 * group]:
                raise FastFileError("DB_AuthLoad master block", f"group {group}")
            master, chunk = b, 1
            continue
        if _sha256(b) != master[32 * (chunk - 1):32 * chunk]:
            raise FastFileError("DB_AuthLoad data block", f"group {group} block {chunk}")
        data.append(b)
        chunk += 1
        if chunk == AUTH_CHUNKS_PER_GROUP + 1:
            group, chunk = group + 1, 0
    report = AuthReport(name_field.rstrip(b"\0").decode("latin1"), signature, key is not None,
                        group if chunk else group - 1, len(data), trailing)
    return data, report


def decompress(data: bytes, prefix: Prefix, zone_name: str | None = None, key=None):
    """Verify and decompress: (zone bytes, AuthReport or None)."""
    payload = data[prefix.payload_offset:]
    report = None
    if prefix.signed:
        chunks, report = _auth_blocks(payload, zone_name, key)
    else:
        chunks = [payload]
    if prefix.compressor == COMPRESSOR_PASSTHROUGH:
        return b"".join(chunks), report
    z = zlib.decompressobj()
    out = bytearray()
    try:
        for c in chunks:
            out += z.decompress(c)
    except zlib.error as e:
        raise FastFileError("inflate", str(e)) from e
    return bytes(out), report


# --- the stream ----------------------------------------------------------------------------------------------------

POOL_BASE = 0xF << 40   # where Stream.link puts asset headers (the game's asset pools)


def default_bases() -> list[int]:
    return [(i + 1) << 40 for i in range(7)]


class Stream:
    """The game's zone stream (database/db_stream.cpp, db_stream_load.cpp; Store 1403746E0 and following).

    pos[i] is the current offset in block i (g_streamPosArray, held as offsets; the address is bases[i] + pos[i]).
    """

    def __init__(self, zone: bytes, block_sizes, bases=None, pool_base=POOL_BASE):
        self.zone, self.cursor = zone, XFILE_SIZE
        self.pool_base, self.pool = pool_base, bytearray()
        self.sizes = list(block_sizes)
        self.bases = list(bases or default_bases())
        self.mem = [bytearray(s) for s in self.sizes]
        self.pos = [0] * 7
        self.index = 0
        self.stack: list[tuple[int, int]] = []   # g_streamPosStack: (pos, index)
        self.string_table = 0                    # address of the XAssetList's script string table
        self.inserts: list[int] = []             # every DB_InsertPointer slot, in order
        self.xstrings: list[int] = []            # every inline XString's address, in order
        self.links: list[tuple[int, int]] = []   # every Stream.link: (type, pool address), in order

    # file side
    def read_file(self, n: int) -> bytes:
        """DB_ReadXFile: the next n bytes of the decompressed stream."""
        if self.cursor + n > len(self.zone):
            raise FastFileError("DB_ReadXFile", f"read past the end of the zone ({self.cursor + n:#x})")
        b = self.zone[self.cursor:self.cursor + n]
        self.cursor += n
        return b

    # memory side
    def addr(self, block: int | None = None, off: int | None = None) -> int:
        block = self.index if block is None else block
        return self.bases[block] + (self.pos[block] if off is None else off)

    def locate(self, address: int) -> tuple[int, int]:
        """(block, offset) of an address in a block; block 7 is the asset pool (Stream.link)."""
        for i, b in enumerate(self.bases):
            if b <= address < b + max(self.sizes[i], 1):
                return i, address - b
        if self.pool_base <= address < self.pool_base + len(self.pool):
            return 7, address - self.pool_base
        raise FastFileError("address", f"{address:#x} is in no block")

    def _region(self, i):
        return self.pool if i == 7 else self.mem[i]

    def link(self, asset_type: int, header: int) -> int:
        """What Load_<Type>Asset does through DB_LinkXAssetEntry1 (14036D830) for a new asset: the header
        (DB_GetXAssetTypeSize bytes) is copied into the type's pool and the asset pointer becomes the pool copy.
        Pool entries here are 16-byte aligned, one after another."""
        size = ASSET_TYPES[asset_type][1]
        at = (len(self.pool) + 15) & ~15
        self.pool += b"\0" * (at - len(self.pool)) + self.read(header, size)
        self.links.append((asset_type, self.pool_base + at))
        return self.pool_base + at

    def write(self, address: int, data: bytes):
        i, off = self.locate(address)
        if i == 7:
            self.pool[off:off + len(data)] = data
            return
        if off + len(data) > self.sizes[i]:
            raise FastFileError("block overflow", f"{BLOCK_NAMES[i]} block: {off + len(data):#x} > {self.sizes[i]:#x}")
        self.mem[i][off:off + len(data)] = data

    def read(self, address: int, n: int) -> bytes:
        i, off = self.locate(address)
        return bytes(self._region(i)[off:off + n])

    def u32(self, address: int) -> int:
        return struct.unpack("<I", self.read(address, 4))[0]

    def i32(self, address: int) -> int:
        return struct.unpack("<i", self.read(address, 4))[0]

    def u16(self, address: int) -> int:
        return struct.unpack("<H", self.read(address, 2))[0]

    def u64(self, address: int) -> int:
        return struct.unpack("<Q", self.read(address, 8))[0]

    def put_u64(self, address: int, v: int):
        self.write(address, struct.pack("<Q", v & (2 ** 64 - 1)))

    def put_u32(self, address: int, v: int):
        self.write(address, struct.pack("<I", v & 0xFFFFFFFF))

    def cstr(self, address: int) -> bytes:
        i, off = self.locate(address)
        r = self._region(i)
        return bytes(r[off:r.index(0, off)])

    # the game's functions
    def load(self, at_stream_start: bool, address: int, size: int):
        """Load_Stream (1403749E0): with atStreamStart, `size` bytes go to `address` (the current position) and
        the position advances; the runtime block is zero-filled instead of read."""
        if not at_stream_start or not size:
            return
        if self.index == XFILE_BLOCK_RUNTIME:
            self.write(address, b"\0" * size)
        else:
            self.write(address, self.read_file(size))
        self.pos[self.index] += size

    def align(self, alignment: int) -> int:
        """`g_streamPos = (g_streamPos + a - 1) & ~(a - 1)`, inline in every Load_*; returns the new address."""
        self.pos[self.index] = (self.pos[self.index] + alignment - 1) & ~(alignment - 1)
        return self.addr()

    def push(self, index: int):
        """DB_PushStreamPos (1403748D0): StreamPosInfo {pos: the position of the block switched to, index: the
        block switched from}."""
        self.stack.append((self.pos[index], self.index))
        self.index = index

    def pop(self):
        """DB_PopStreamPos (140374850): leaving the temp block puts its position back where it was at the push,
        so temp memory is reused by the next asset; any other block keeps what was loaded into it."""
        saved_pos, saved_index = self.stack.pop()
        if self.index == XFILE_BLOCK_TEMP:
            self.pos[XFILE_BLOCK_TEMP] = saved_pos
        self.index = saved_index

    def insert_pointer(self) -> int:
        """DB_InsertPointer (140374750): an 8-byte, 8-aligned slot in the virtual block."""
        self.push(XFILE_BLOCK_VIRTUAL)
        self.pos[XFILE_BLOCK_VIRTUAL] = (self.pos[XFILE_BLOCK_VIRTUAL] + 7) & ~7
        slot = self.addr()
        self.pos[XFILE_BLOCK_VIRTUAL] += 8
        self.pop()
        self.inserts.append(slot)
        return slot

    def unpack_offset(self, v: int) -> tuple[int, int]:
        """DB_GetPackedOffsetStreamPos (1401905A0): block in bits 32-35, offset + 1 in the low 32 bits."""
        return (v >> 32) & 0xF, (v & 0xFFFFFFFF) - 1

    def offset_to_pointer(self, v: int) -> int:
        """DB_ConvertOffsetToPointer (1403749A0)."""
        block, off = self.unpack_offset(v)
        return (self.bases[block] + off) & (2 ** 64 - 1)

    def offset_to_alias(self, v: int) -> int:
        """DB_ConvertOffsetToAlias (140374960): the pointer stored at that place."""
        return self.u64(self.offset_to_pointer(v))

    def xstring(self, ptr_address: int):
        """Load_XStringCustom (140374AC0): the string's bytes up to and including NUL, at the current position."""
        start = self.u64(ptr_address)
        self.xstrings.append(start)
        n = self.zone.index(b"\0", self.cursor) - self.cursor + 1
        self.write(start, self.read_file(n))
        self.pos[self.index] += n

    def xstring_ptr(self, field_address: int):
        """The generated XString pointer rule: inline (-1) -> Load_XStringCustom at the current position (no
        alignment); another non-zero value -> DB_ConvertOffsetToPointer."""
        v = self.u64(field_address)
        if v == 0:
            return
        if v == PTR_INLINE:
            self.put_u64(field_address, self.addr())
            self.xstring(field_address)
        else:
            self.put_u64(field_address, self.offset_to_pointer(v))


# --- the zone ------------------------------------------------------------------------------------------------------

@dataclass
class Asset:
    type: int
    name: str | None = None
    header: int | None = None   # address of the asset's header: its pool copy (Stream.link), as the game's
    # Load_<Type>Asset leaves it; for an alias, the earlier asset's
    slot: int | None = None     # its DB_InsertPointer slot (a -2 pointer), which later assets may alias

    @property
    def type_name(self) -> str:
        return ASSET_TYPES.get(self.type, (f"type{self.type}",))[0]


@dataclass
class Zone:
    prefix: Prefix
    auth: AuthReport | None
    xfile_size: int
    external_size: int
    block_sizes: list[int]
    script_strings: list[bytes | None]
    assets: list[Asset]
    complete: bool                        # every asset body was walked
    stopped_at: int | None = None         # index of the first asset without a loader
    stream: Stream | None = field(default=None, repr=False)
    string_table: int = 0                 # address of the script string pointer table


ASSET_LOADERS = {}   # type -> fn(stream, varptr_address); see the loaders below


def walk_zone(zone: bytes, bases=None, stop_on_unknown=True, max_assets=None, pool_base=POOL_BASE):
    """DB_LoadXFile's stream part: XFile header, XAssetList, script strings, XGlobals, the XAsset array, assets.
    max_assets: walk at most that many asset bodies (0: stop right after the XAsset array).

    Returns (xfile tuple, stream, script strings, assets, complete, stopped_at, string table address)."""
    if len(zone) < XFILE_SIZE + XASSET_LIST_SIZE:
        raise FastFileError("DB_ReadXFile", "zone shorter than its headers")
    xfile = struct.unpack_from("<9Q", zone, 0)
    s = Stream(zone, xfile[2:], bases, pool_base)
    xal = bytearray(s.read_file(XASSET_LIST_SIZE))   # into g_varXAssetList, not into a block
    string_count, strings_ptr, asset_count, assets_ptr, globals_ptr = (
        struct.unpack_from("<i", xal, 0)[0], struct.unpack_from("<Q", xal, 8)[0],
        struct.unpack_from("<i", xal, 0x10)[0], struct.unpack_from("<Q", xal, 0x18)[0],
        struct.unpack_from("<Q", xal, 0x20)[0])
    s.push(XFILE_BLOCK_VIRTUAL)
    # Load_ScriptStringList (140355E20)
    s.push(XFILE_BLOCK_VIRTUAL)
    strings: list[bytes | None] = []
    table = 0
    if strings_ptr:
        table = s.align(8)
        s.load(True, table, string_count * 8)
        for i in range(string_count):
            slot = table + 8 * i
            v = s.u64(slot)
            if v == 0:
                strings.append(None)
            elif v == PTR_INLINE:
                s.put_u64(slot, s.addr())
                s.xstring(slot)
                strings.append(s.cstr(s.u64(slot)))
                # Load_TempStringCustom: SL_GetString(str, 4) replaces the pointer with the script string handle
                s.put_u64(slot, sum(1 for x in strings if x is not None))
            else:
                s.put_u64(slot, s.offset_to_pointer(v))
                strings.append(None)
    s.pop()
    s.string_table = table
    # Load_XGlobalsPtr (14035DF80): any non-zero value means inline
    if globals_ptr:
        g = s.align(4)
        s.load(True, g, 8)
        if s.u64(g):
            gfx = s.align(4)
            s.put_u64(g, gfx)
            load_xgfxglobals(s, gfx)
    s.pop()
    s.push(XFILE_BLOCK_VIRTUAL)
    assets: list[Asset] = []
    complete, stopped = True, None
    if assets_ptr:
        arr = s.align(4)                                  # AllocLoad_XAsset (14034A060)
        s.load(True, arr, 16 * asset_count)
        assets = [Asset(s.i32(arr + 16 * i)) for i in range(asset_count)]
        for i, a in enumerate(assets):
            if max_assets is not None and i >= max_assets:
                complete, stopped = False, i
                break
            loader = ASSET_LOADERS.get(a.type)
            if loader is None:
                if stop_on_unknown:
                    complete, stopped = False, i
                    break
                raise FastFileError("Load_XAsset", f"no loader for type {a.type:#x}")
            varptr = arr + 16 * i + 8
            before = len(s.inserts)
            loader(s, varptr)
            if len(s.inserts) > before:
                a.slot = s.inserts[before]
            a.header = s.u64(varptr)
            noff = ASSET_TYPES[a.type][2]
            nptr = s.u64(a.header + noff) if a.header else 0
            a.name = s.cstr(nptr).decode("latin1") if nptr else None
    s.pop()
    return xfile, s, strings, assets, complete, stopped, table


def load_xgfxglobals(s: Stream, at: int):
    """Load_XGfxGlobals (14035DBB0), with atStreamStart: a 0x68-byte header and its arrays. The arrays of GPU
    object pointers live in the runtime block (zero-filled, never in the file)."""
    s.load(True, at, 0x68)
    c0, c1 = s.u32(at), s.u32(at + 4)
    c10, c11, c12 = s.i32(at + 0x28), s.i32(at + 0x2C), s.i32(at + 0x30)

    def array(field, size):
        if s.u64(at + field):
            p = s.align(4)
            s.put_u64(at + field, p)
            s.load(True, p, size)

    def runtime_ptrs(field, count):
        s.push(XFILE_BLOCK_RUNTIME)
        if s.u64(at + field):
            p = s.align(4)
            s.put_u64(at + field, p)
            load_ptr_array_1(s, p, count)
        s.pop()

    array(0x08, c0 * 8)
    array(0x10, c1 * 4)
    runtime_ptrs(0x18, c0)
    runtime_ptrs(0x20, c1)
    array(0x38, c10 * 4)
    array(0x40, c11 * 4)
    array(0x48, c12 * 4)
    runtime_ptrs(0x50, c10)
    runtime_ptrs(0x58, c11)
    runtime_ptrs(0x60, c12)


def load_ptr_array_1(s: Stream, at: int, count: int):
    """140351F50: `count` pointers; each non-zero one gets one byte at the current position (no alignment)."""
    s.load(True, at, count * 8)
    for i in range(count):
        p = at + 8 * i
        if s.u64(p):
            s.put_u64(p, s.addr())
            s.load(True, s.addr(), 1)


def asset_ptr(asset_type, header_loader, align=4):
    """The generated Load_<Type>Ptr rule (e.g. Load_PathDataPtr 1403551C0): in the temp block, a null pointer stays
    null, an offset is an alias to an asset loaded earlier (DB_ConvertOffsetToAlias), -1/-2 mean the header follows
    (aligned to 4), with -2 also reserving an alias slot (DB_InsertPointer) that receives the header pointer after
    DB_Add (Load_<Type>Asset: the header moves to the asset pool, Stream.link)."""
    def load(s: Stream, varptr: int):
        s.push(XFILE_BLOCK_TEMP)
        v = s.u64(varptr)
        if v:
            if v not in (PTR_INLINE, PTR_INSERT):
                s.put_u64(varptr, s.offset_to_alias(v))
            else:
                h = s.align(align)
                s.put_u64(varptr, h)
                slot = s.insert_pointer() if v == PTR_INSERT else None
                header_loader(s, h)
                s.put_u64(varptr, s.link(asset_type, h))
                if slot is not None:
                    s.put_u64(slot, s.u64(varptr))
        s.pop()
    return load


def load_rawfile(s: Stream, at: int):
    """Load_RawFile (140355760): name, compressedLen (+8), len (+0xC), buffer (+0x10): compressedLen bytes
    (sign-extended), unaligned, whatever len says."""
    s.load(True, at, 0x18)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    if s.u64(at + 0x10):
        p = s.addr()
        s.put_u64(at + 0x10, p)
        s.load(True, p, s.i32(at + 8))
    s.pop()


def load_pathdata(s: Stream, at: int):
    """Load_PathData (140354DD0)."""
    s.load(True, at, 0x88)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    node_count = s.u32(at + 8)
    if s.u64(at + 0x10):                                     # nodes: pathnode_t[nodeCount], 0xB0 each
        p = s.align(4)
        s.put_u64(at + 0x10, p)
        s.load(True, p, node_count * 0xB0)
        for i in range(node_count):
            load_pathnode(s, p + 0xB0 * i)
    for field, count_field in ((0x20, 0x1C),):              # pathVis: bytes, no alignment
        if s.u64(at + field):
            p = s.addr()
            s.put_u64(at + field, p)
            s.load(True, p, s.i32(at + count_field))
    if s.u64(at + 0x30):                                     # nodeTree: pathnode_tree_t[nodeTreeCount]
        p = s.align(4)
        s.put_u64(at + 0x30, p)
        load_pathnode_tree_array(s, p, s.i32(at + 0x28))
    if s.u64(at + 0x40):                                     # dynamicNodeGroups[dynamicNodeGroupCount], 0x10 each
        p = s.align(4)
        s.put_u64(at + 0x40, p)
        n = s.i32(at + 0x38)
        s.load(True, p, n * 0x10)
        for i in range(n):
            g = p + 0x10 * i
            if s.u64(g + 8):
                q = s.align(4)
                s.put_u64(g + 8, q)
                load_pathnode_tree_array(s, q, s.i32(g + 4))
    for field, count_field in ((0x50, 0x48), (0x60, 0x58), (0x70, 0x6C), (0x80, 0x78)):
        if s.u64(at + field):                                # pathExposure, pathNoPeekVis, pathZones, pathDynStates
            p = s.addr()
            s.put_u64(at + field, p)
            s.load(True, p, s.i32(at + count_field))
    s.pop()


def load_pathnode(s: Stream, at: int):
    """140361A80 for one pathnode_t (0xB0 bytes, already loaded): script string fields are converted in place
    (Load_ScriptStringCustom), then the links at +0x48: totalLinkCount (+0x44, u16) entries of 12 bytes."""
    for off in (0x8, 0xC, 0x10, 0x14, 0x18):
        _script_string(s, at + off)
    if not PATHNODE_SKIP_0x38:
        _script_string(s, at + 0x38)
    if s.u64(at + 0x48):
        p = s.align(4)
        s.put_u64(at + 0x48, p)
        s.load(True, p, s.u16(at + 0x44) * 0xC)


# 140361A80 converts the script string at +0x38 only while the byte at 146700658 is zero (a global the loader
# doesn't set; zero in a freshly started game). The reader follows the zero case.
PATHNODE_SKIP_0x38 = False


def _script_string(s: Stream, address: int):
    """Load_ScriptStringCustom (14037AF90): *(u32*)p = stringList.strings[*(u32*)p] (the low 32 bits)."""
    idx = s.u32(address)
    s.put_u32(address, s.u64(s.string_table + 8 * idx) & 0xFFFFFFFF)


def load_pathnode_tree_array(s: Stream, at: int, count: int):
    """140361D90: pathnode_tree_t[count] (0x18 each) and their contents."""
    s.load(True, at, count * 0x18)
    for i in range(count):
        load_pathnode_tree(s, at + 0x18 * i)


def load_pathnode_tree(s: Stream, at: int):
    """140361C00 on one pathnode_tree_t: axis (+0) >= 0 -> two child pointers at +8 (140361CF0 each: -1 means a
    tree follows, aligned to 4, else an offset); < 0 -> a node list at +8: count (+8, i32) and u16 indices at
    +0x10 (aligned to 2) (140361C80)."""
    if s.i32(at) >= 0:
        for k in range(2):
            child = at + 8 + 8 * k
            v = s.u64(child)
            if v == 0:
                continue
            if v == PTR_INLINE:
                p = s.align(4)
                s.put_u64(child, p)
                s.load(True, p, 0x18)
                load_pathnode_tree(s, p)
            else:
                s.put_u64(child, s.offset_to_pointer(v))
    else:
        if s.u64(at + 0x10):
            p = (s.pos[s.index] + 1) & ~1
            s.pos[s.index] = p
            p = s.addr()
            s.put_u64(at + 0x10, p)
            s.load(True, p, s.i32(at + 8) * 2)


def load_physpreset(s: Stream, at: int):
    """Load_PhysPreset (140355500): 0x58 bytes; the XStrings name (+0) and sndAliasPrefix (+0x20)."""
    s.load(True, at, 0x58)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    s.xstring_ptr(at + 0x20)
    s.pop()


def load_scriptfile(s: Stream, at: int):
    """Load_ScriptFile (140355C10): name; then in the script block, the buffer (+0x18, compressedLen (+8) bytes)
    and the bytecode (+0x20, bytecodeLen (+0x10) bytes), each in its own push of block 6, unaligned."""
    s.load(True, at, 0x28)
    s.push(XFILE_BLOCK_VIRTUAL)
    s.xstring_ptr(at)
    for field, count in ((0x18, 0x8), (0x20, 0x10)):
        s.push(6)
        if s.u64(at + field):
            p = s.addr()
            s.put_u64(at + field, p)
            s.load(True, p, s.i32(at + count))
        s.pop()
    s.pop()


ASSET_LOADERS[0x00] = asset_ptr(0x00, load_physpreset)  # physpreset: Load_PhysPresetPtr 1403555F0
ASSET_LOADERS[0x2D] = asset_ptr(0x2D, load_scriptfile)  # scriptfile: Load_ScriptFilePtr 140355D30
ASSET_LOADERS[0x16] = asset_ptr(0x16, load_pathdata)   # aipaths: Load_PathDataPtr 1403551C0
ASSET_LOADERS[0x2C] = asset_ptr(0x2C, load_rawfile)    # rawfile: Load_RawFilePtr 140355820


def read_fastfile(data: bytes, zone_name: str | None = None, key=None, bases=None, max_assets=None,
                  pool_base=POOL_BASE) -> Zone:
    """Open, verify, decompress and walk a fastfile."""
    prefix = read_prefix(data)
    zone, auth = decompress(data, prefix, zone_name, key)
    if len(zone) < XFILE_SIZE:
        raise FastFileError("DB_ReadXFile", "zone shorter than the XFile header")
    xfile, s, strings, assets, complete, stopped, table = walk_zone(zone, bases, max_assets=max_assets, pool_base=pool_base)
    # xfile[0] + XFILE_SIZE is the decompressed length on every file measured; the game never compares it
    return Zone(prefix, auth, xfile[0], xfile[1], list(xfile[2:]), strings, assets, complete, stopped, s, table)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fastfile", type=Path)
    ap.add_argument("--exe", type=Path, help="Store exe: also verify the RSA signature with its key")
    ap.add_argument("--name", help="zone name the game expects (default: the file name without .ff)")
    ap.add_argument("--strings", action="store_true", help="list the script strings")
    ap.add_argument("--json", action="store_true")
    opts = ap.parse_args(argv)
    data = opts.fastfile.read_bytes()
    key = public_key_from_exe(opts.exe) if opts.exe else None
    name = opts.name or opts.fastfile.name.rsplit(".", 1)[0]
    try:
        z = read_fastfile(data, name, key)
    except FastFileError as e:
        print(f"rejected: {e}", file=sys.stderr)
        return 1
    out = {
        "magic": z.prefix.magic.decode(), "signed": z.prefix.signed, "compressor": z.prefix.compressor,
        "stream_image_rows": len(z.prefix.stream_images), "loadbar_sizes": list(z.prefix.loadbar_sizes),
        "auth": None if not z.auth else {"zone": z.auth.zone_name, "signature_checked": z.auth.signature_checked,
                                         "groups": z.auth.groups, "data_blocks": z.auth.data_blocks,
                                         "trailing_bytes": z.auth.trailing_bytes},
        "xfile": {"size": z.xfile_size, "external_size": z.external_size,
                  "blocks": dict(zip(BLOCK_NAMES, z.block_sizes))},
        "script_strings": len(z.script_strings),
        "assets": [[a.type_name, a.name] for a in z.assets],
        "complete": z.complete,
    }
    if opts.strings:
        out["strings"] = [None if x is None else x.decode("latin1") for x in z.script_strings]
    if opts.json:
        print(json.dumps(out, indent=1))
        return 0
    for k, v in out.items():
        if k not in ("assets", "strings"):
            print(f"{k}: {v}")
    if opts.strings:
        for i, x in enumerate(out["strings"]):
            print(f"  string {i}: {x}")
    for i, (t, n) in enumerate(out["assets"]):
        note = "" if z.complete or i < z.stopped_at else "  (not walked: no loader for an earlier asset)"
        print(f"  asset {i}: {t} {n if n is not None else '?'}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
