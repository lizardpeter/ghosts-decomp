"""Synthetic fastfiles for the tests: a zone stream built from a list of items, wrapped as an unsigned or a signed
fastfile. Nothing here comes from game data; signed files use a key generated for the test.
"""
import hashlib
import random
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import iw6ff  # noqa: E402

INLINE, INSERT = iw6ff.PTR_INLINE, iw6ff.PTR_INSERT


def packed(block: int, offset: int) -> int:
    """The encoding DB_GetPackedOffsetStreamPos decodes: block in bits 32-35, offset + 1 below."""
    return (block << 32) | (offset + 1)


class Zone:
    """The decompressed stream after the XFile header: the XAssetList and what the loaders read, in order."""

    def __init__(self):
        self.strings = []        # bytes (inline), None (null), or ("offset", block, offset)
        self.globals = None      # None: no XGlobals; else the gfxGlobals pointer value (0 for none)
        self.assets = []         # (type, pointer value, body bytes)

    def stream(self) -> bytes:
        out = bytearray()
        out += struct.pack("<iiQiiQQ", len(self.strings), 0, INLINE if self.strings else 0,
                           len(self.assets), 0, INLINE if self.assets else 0,
                           INLINE if self.globals is not None else 0)
        for s in self.strings:
            out += struct.pack("<Q", 0 if s is None else INLINE if isinstance(s, bytes) else packed(*s[1:]))
        for s in self.strings:
            if isinstance(s, bytes):
                out += s + b"\0"
        if self.globals is not None:
            out += struct.pack("<Q", self.globals)
        for t, ptr, _ in self.assets:
            out += struct.pack("<iiQ", t, 0, ptr)
        for _, ptr, body in self.assets:
            if ptr in (INLINE, INSERT):
                out += body
        return bytes(out)

    def xfile(self, block_sizes) -> bytes:
        body = self.stream()
        return struct.pack("<9Q", len(body), 0, *block_sizes) + body


def name_field(name):
    """An XString pointer and what follows it: (pointer value, inline bytes)."""
    if name is None:
        return 0, b""
    if isinstance(name, tuple):
        return packed(*name), b""
    return INLINE, name + b"\0"


def rawfile(name, data: bytes, buffer=True, clen=None):
    nptr, ninline = name_field(name)
    clen = len(data) if clen is None else clen
    return (struct.pack("<QiiQ", nptr, clen, len(data) + 7, INLINE if buffer else 0) + ninline +
            (data[:max(clen, 0)] if buffer else b""))


def physpreset(name, alias):
    nptr, ninline = name_field(name)
    aptr, ainline = name_field(alias)
    body = bytearray(0x58)
    struct.pack_into("<Q", body, 0, nptr)
    struct.pack_into("<f", body, 0xC, 1.5)
    struct.pack_into("<Q", body, 0x20, aptr)
    return bytes(body) + ninline + ainline


def scriptfile(name, source: bytes, bytecode: bytes):
    nptr, ninline = name_field(name)
    return (struct.pack("<QiiiiQQ", nptr, len(source), len(source) * 3, len(bytecode), 0,
                        INLINE if source else 0, INLINE if bytecode else 0) + ninline + source + bytecode)


def prefix(magic: bytes, compressor=0, rows=(), sizes=(0, 0)) -> bytes:
    out = bytearray(magic + struct.pack("<I", iw6ff.VERSION) + bytes([1, compressor, 8, 4]) + b"\0" * 8)
    out += struct.pack("<I", len(rows))
    for loc, file, off, end in rows:
        out += struct.pack("<HHIQQ", loc, file, 0, off, end)
    out += struct.pack("<QQ", *sizes)
    return bytes(out)


def unsigned(xfile: bytes, compressor=0, rows=()) -> bytes:
    body = zlib.compress(xfile) if compressor == 0 else xfile
    return prefix(iw6ff.MAGIC_UNSIGNED, compressor, rows) + body


# --- signed files --------------------------------------------------------------------------------------------------

def _probable_prime(bits, r):
    while True:
        n = r.getrandbits(bits) | (1 << (bits - 1)) | 1
        if all(n % p for p in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)) and _miller_rabin(n, r):
            return n


def _miller_rabin(n, r, rounds=24):
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for _ in range(rounds):
        x = pow(r.randrange(2, n - 1), d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


_KEY = None


def test_key():
    """A 2048-bit RSA key made for the tests: (n, e, d)."""
    global _KEY
    if _KEY is None:
        r = random.Random(0x1A6)
        e = 65537
        while True:
            p, q = _probable_prime(1024, r), _probable_prime(1024, r)
            n, phi = p * q, (p - 1) * (q - 1)
            if n.bit_length() == 2048 and phi % e:
                _KEY = (n, e, pow(e, -1, phi))
                break
    return _KEY


def pss_sign(key, digest: bytes, salt: bytes) -> bytes:
    n, _, d = key
    em_bits = n.bit_length() - 1
    em_len = (em_bits + 7) // 8
    h = hashlib.sha256(b"\0" * 8 + digest + salt).digest()
    db = b"\0" * (em_len - len(salt) - 32 - 2) + b"\1" + salt
    mask = iw6ff._mgf1(h, len(db))
    masked = bytearray(a ^ b for a, b in zip(db, mask))
    masked[0] &= 0xFF >> (8 * em_len - em_bits)
    em = bytes(masked) + h + b"\xbc"
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(256, "big")


def signed(xfile: bytes, zone_name: str, key=None, rows=(), chunks_per_group=iw6ff.AUTH_CHUNKS_PER_GROUP) -> bytes:
    """The authenticated container: header block, then per group a master block and its data blocks."""
    key = key or test_key()
    comp = zlib.compress(xfile)
    comp += b"\0" * (-len(comp) % iw6ff.AUTH_BLOCK)
    data = [comp[i:i + iw6ff.AUTH_BLOCK] for i in range(0, len(comp), iw6ff.AUTH_BLOCK)]
    groups = [data[i:i + chunks_per_group] for i in range(0, len(data), chunks_per_group)]
    masters = []
    for g in groups:
        m = b"".join(hashlib.sha256(b).digest() for b in g)
        masters.append(m + b"\0" * (iw6ff.AUTH_BLOCK - len(m)))
    sub = bytearray(0x1EA4)
    sub[:len(zone_name)] = zone_name.encode()
    for i, m in enumerate(masters):
        sub[0x24 + 32 * i:0x44 + 32 * i] = hashlib.sha256(m).digest()
    sub_hash = hashlib.sha256(sub).digest()
    hdr = bytearray(iw6ff.AUTH_BLOCK)
    hdr[:8] = iw6ff.MAGIC_AUTH
    hdr[0xC:0x2C] = sub_hash
    hdr[0x2C:0x12C] = pss_sign(key, sub_hash, b"saltsalt")
    hdr[0x12C:0x12C + len(sub)] = sub
    out = bytearray(prefix(iw6ff.MAGIC_SIGNED, 0, rows) + hdr)
    for m, g in zip(masters, groups):
        out += m + b"".join(g)
    return bytes(out)


# --- random zones --------------------------------------------------------------------------------------------------

BIG = [0x10000, 0, 0x1000, 0x40000, 0, 0, 0x10000]


def random_zone(r: random.Random) -> Zone:
    """A zone of random script strings and raw files, phys presets and script files, with every pointer kind the
    loaders know: inline, null, offsets to earlier strings, -2 assets (alias slots) and aliases to them."""
    z = Zone()
    for _ in range(r.choice([0, 0, 1, 3, 9])):
        z.strings.append(None if r.random() < 0.2 else bytes(r.choice(b"abcdefgh_") for _ in range(r.randrange(0, 12))))
    z.globals = r.choice([None, None, 0])
    for _ in range(r.randrange(0, 7)):
        t = r.choice([0x00, 0x2C, 0x2D])
        name = bytes(r.choice(b"abcxyz/_.") for _ in range(r.randrange(1, 20)))
        ptr = r.choice([INLINE, INLINE, INSERT, 0])
        if t == 0x2C:
            body = rawfile(name, r.randbytes(r.randrange(0, 40)), buffer=r.random() < 0.8)
        elif t == 0x00:
            body = physpreset(name, r.choice([None, b"snd_" + name]))
        else:
            body = scriptfile(name, r.randbytes(r.randrange(0, 30)), r.randbytes(r.randrange(0, 30)))
        z.assets.append((t, ptr, body))
    return z


def with_references(z: Zone, r: random.Random, rounds=3) -> Zone:
    """Turn some pointers into offsets to things an earlier walk placed: script strings that point at earlier
    inline strings (DB_ConvertOffsetToPointer) first, then asset entries that alias the slot of an earlier -2 asset
    (DB_ConvertOffsetToAlias). Each change refers backwards and is made after a fresh walk, and string changes
    (which move everything after them) all come before the aliases."""
    for _ in range(rounds):
        _, s, *_ = iw6ff.walk_zone(z.xfile(BIG))
        inline = [i for i, x in enumerate(z.strings) if isinstance(x, bytes)]
        later = [i for i in inline[1:] if r.random() < 0.4]
        if not later:
            break
        i = later[0]
        k = r.randrange(inline.index(i))   # one of the inline strings before it
        z.strings[i] = ("offset", *s.locate(s.xstrings[k]))
    for _ in range(rounds):
        _, s, strings, assets, *_ = iw6ff.walk_zone(z.xfile(BIG))
        choices = [i for i, a in enumerate(assets) if any(b.slot is not None for b in assets[:i])
                   and z.assets[i][1] in (INLINE, INSERT)]
        if not choices or r.random() < 0.2:
            break
        i = r.choice(choices)
        slot = r.choice([b.slot for b in assets[:i] if b.slot is not None])
        t, _, body = z.assets[i]
        z.assets[i] = (t, packed(*s.locate(slot)), body)
    return z
