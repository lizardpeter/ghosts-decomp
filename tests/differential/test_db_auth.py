"""Differential cases for database/db_auth.cpp: the signed-fastfile block chain and the inflater.

SHA-256 (libtomcrypt), zlib and I_strncpyz run for real in both runs. The RSA calls are scripted (find_hash,
rsa_import, rsa_verify_hash_ex with its stat output, rsa_free record their arguments): a real 2048-bit
verification is millions of instructions, and the Store build's own verification of real zones is checked by
tests/fastfile (store_emu.py loads signed zones through it). Where a case needs it, the block checker
(sub_1403489E0) and the signature check are scripted too, for both runs alike.

g_authLoad is drawn per input: secure or not, the group/chunk counters, a header whose master block hashes and a
master block whose chunk hashes match the input's blocks some of the time, the copy buffer's fill, the stream.

These cases are the Store build's (its layouts and callees differ from the servers'; records/functions.tsv keeps
the server copies at compiles with the reason).
"""
import hashlib
import random
import struct
import zlib

from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP

from harness import HEAP
from syms import va

M = {}
AUTH = {"isSecure": 0x0, "name": 0x4, "header": 0x24, "master": 0x2000, "group": 0x4000, "chunk": 0x4004,
        "stream": 0x4008, "copyEnd": 0x4060, "copy": 0x406C}
SIZE = 0x6070
MAGIC = b"IWffs100"


def _u64(mu, a):
    return struct.unpack("<Q", bytes(mu.mem_read(a, 8)))[0]


def _args(mu, n):
    regs = [mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)]
    rsp = mu.reg_read(UC_X86_REG_RSP)
    return (regs + [_u64(mu, rsp + 0x28 + 8 * i) for i in range(max(0, n - 4))])[:n]


def _rec(*e):
    M["m"].observed.append(e)


def _next(kind, default):
    lst = M.get(kind) or []
    return lst.pop(0) if lst else default


def fake_find_hash(mu):
    _rec("find_hash", M["m"].read_cstr(_args(mu, 1)[0]))
    return _next("find", 0)


def fake_rsa_import(mu):
    a = _args(mu, 3)
    _rec("rsa_import", a[0], a[1], a[2] != 0)
    return _next("import", 0)


def fake_rsa_verify(mu):
    a = _args(mu, 9)
    sig, siglen, h, hlen, pad, idx, salt, stat, key = a
    _rec("rsa_verify_hash_ex", bytes(mu.mem_read(sig, 8)), siglen, bytes(mu.mem_read(h, 8)), hlen, pad & 0xFFFFFFFF,
         idx & 0xFFFFFFFF, salt & 0xFFFFFFFF, bytes(mu.mem_read(stat, 4)))  # unsigned long: 32 bits
    mu.mem_write(stat, struct.pack("<i", _next("stat", 1)))
    return _next("verify", 0)


def fake_rsa_free(mu):
    _rec("rsa_free")
    return 0


def fake_validate(mu):
    h, s = _args(mu, 2)
    _rec("DBX_AuthLoad_ValidateSignature", bytes(mu.mem_read(h, 32)), bytes(mu.mem_read(s, 8)))
    return _next("valid", 1)


def fake_process(mu):
    block, out = _args(mu, 2)
    nd = _next("notdata", 0)
    mu.mem_write(out, bytes([nd]))
    _rec("sub_1403489E0", bytes(mu.mem_read(block, 16)))
    return _next("process", 1)


RSA = {"find_hash": fake_find_hash, "rsa_import": fake_rsa_import, "rsa_verify_hash_ex": fake_rsa_verify,
       "rsa_free": fake_rsa_free}
VALIDATE = {"?DBX_AuthLoad_ValidateSignature@@YA_NPEBUDB_AuthHash@@PEBUDB_AuthSignature@@@Z": fake_validate}
PROCESS = {"?sub_1403489E0@@YA_NPEBEPEA_N@Z": fake_process}


def scripts(r):
    M["find"] = [r.choice([0, 0, 3, -1 & 0xFFFFFFFF])]
    M["import"] = [r.choice([0, 0, 0, 13])]
    M["verify"] = [r.choice([0, 0, 0, 7])]
    M["stat"] = [r.choice([1, 1, 0])]
    M["valid"] = [r.choice([1, 1, 0])]
    M["notdata"] = [r.choice([0, 1]) for _ in range(8)]
    M["process"] = [r.choice([1, 1, 1, 0]) for _ in range(8)]


def header_block(r, name, good):
    hdr = bytearray(r.randbytes(0x2000))
    hdr[:8] = MAGIC if r.random() < 0.9 else b"IWffs101"
    sub = bytearray(hdr[0x12C:0x12C + 0x1EA4])
    sub[:32] = name.ljust(32, b"\0")[:32]
    if r.random() < 0.1:
        sub[31] = 1
    hdr[0x12C:0x12C + 0x1EA4] = sub
    hdr[0xC:0x2C] = hashlib.sha256(bytes(sub)).digest() if good else r.randbytes(32)
    return bytes(hdr)


def auth_state(r, w, blocks=()):
    """g_authLoad: counters, a header and a master block that match `blocks` some of the time."""
    base = va("g_authLoad")
    w.write(base, bytes(SIZE))
    w.u32(base + AUTH["isSecure"], r.choice([0, 1, 1]))
    name = r.choice([b"mp_alien_town_path", b"zone", b""])
    w.write(base + AUTH["name"], name.ljust(32, b"\0"))
    group = r.choice([0, 1, 1, 2, 244])
    chunk = r.choice([0, 1, 2, 0x100, 0xFF])
    w.u32(base + AUTH["group"], group)
    w.u32(base + AUTH["chunk"], chunk)
    hashes = [hashlib.sha256(b).digest() if r.random() < 0.7 else r.randbytes(32) for b in blocks] or [r.randbytes(32)]
    if group:
        w.write(base + AUTH["header"] + 0x150 + 32 * (group - 1), r.choice(hashes))
    if chunk:
        w.write(base + AUTH["master"] + 32 * (chunk - 1), r.choice(hashes))
    w.u32(base + AUTH["copyEnd"], r.choice([0, 0, 0x1000, 0x1FFF, 0x2000]))
    w.write(base + AUTH["header"] + 0x2C, r.randbytes(0x100))
    return name


def inputs(seed, build, n=150):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        args, prep = build(r)
        s = r.getrandbits(32)

        def setup(w, s=s, prep=prep):
            M["m"] = w.m
            rr = random.Random(s)
            scripts(rr)
            prep(rr, w)
        out.append({"args": args, "setup": setup})
    return out


def compressor(w, r):
    w.u32(va("g_compressor"), r.choice([0, 0, 2, 1]))


def descriptors(w):
    """What DB_AuthLoad_InflateInit leaves for the RSA code: ltc_mp = ltm_desc, sha256 registered."""
    w.write(va("ltc_mp"), bytes(w.m.mu.mem_read(va("ltm_desc"), 0x188)))


# --- cases ---------------------------------------------------------------------------------------------------------

def hash_args(r):
    data = r.randbytes(r.choice([0, 1, 64, 0x2000]))
    want = hashlib.sha256(data).digest() if r.random() < 0.5 else r.randbytes(32)
    buf = data + bytes(-len(data) % 16) + want
    return [buf, len(data), HEAP + len(data) + (-len(data) % 16)], lambda r, w: None


def process_args(r):
    blocks = [r.randbytes(0x2000)]
    kind = r.random()
    if kind < 0.4:
        blocks = [header_block(r, r.choice([b"mp_alien_town_path", b"zone"]), r.random() < 0.7)]
    return [blocks[0], bytes(8)], lambda rr, w: auth_state(rr, w, blocks)


def inflate_args(r):
    raw = r.randbytes(r.choice([0, 16, 300])) + bytes(r.choice([0, 500]))
    comp = zlib.compress(raw) if r.random() < 0.7 else raw
    avail_in = min(len(comp), r.choice([0, 5, len(comp), 0x2000]))
    out_size = r.choice([0, 1, 64, 0x400])
    # the caller's stream: next_in -> HEAP + 0x1000 (the data), next_out -> HEAP + 0x5000
    stream = struct.pack("<QIIQII", HEAP + 0x1000, avail_in, 0, HEAP + 0x5000, out_size, 0) + bytes(0x58 - 0x20)
    mem = bytearray(0x6000)
    mem[0:0x58] = stream
    mem[0x1000:0x1000 + len(comp)] = comp

    def prep(rr, w):
        auth_state(rr, w)
        compressor(w, rr)
        base = va("g_authLoad")
        if rr.random() < 0.5:   # a data block already in g_authLoad's stream
            w.u64(base + AUTH["stream"], base + AUTH["copy"])
            w.u32(base + AUTH["stream"] + 8, rr.choice([0, 0x10, 0x2000]))
            w.write(base + AUTH["copy"], rr.randbytes(0x40))
    return [bytes(mem), r.choice([0, 2, 4]), 0], prep


def init_args(r):
    stream = struct.pack("<QIIQII", 0x1234, 7, 9, 0x5678, 11, 13) + r.randbytes(0x38)
    name = r.choice([b"mp_alien_town_path", b"a" * 40, b""]) + b"\0"
    return [stream, r.choice([0, 1, 2]), name], lambda rr, w: (auth_state(rr, w), compressor(w, rr))


def end_args(r):
    stream = r.randbytes(0x58)
    return [stream], lambda rr, w: (auth_state(rr, w), compressor(w, rr))


def sig_args(r):
    return [bytes(0x100)], lambda rr, w: auth_state(rr, w)


def validate_args(r):
    return [r.randbytes(32), r.randbytes(256)], lambda rr, w: descriptors(w)


CASES = [
    {"build": "iw6mp64_MSStore_ship", "symbol": "?sub_140348BA0@@YA_NPEBEIPEBUDB_AuthHash@@@Z", "ret": "char", "inputs": inputs(0x5A0, hash_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?sub_140348900@@YAXPEBEIPEAE@Z", "ret": "void",
     "inputs": inputs(0x5A1, lambda r: ([r.randbytes(0x100), r.choice([0, 3, 0x100]), bytes(32)], lambda rr, w: None))},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?sub_140348960@@YAXPEAE@Z", "ret": "void", "inputs": inputs(0x5A2, sig_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DBX_AuthLoad_ValidateSignature_Try@@YA_NPEBUDB_AuthHash@@PEBUDB_AuthSignature@@@Z", "ret": "char",
     "fakes": RSA, "inputs": inputs(0x5A3, validate_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DBX_AuthLoad_ValidateSignature@@YA_NPEBUDB_AuthHash@@PEBUDB_AuthSignature@@@Z", "ret": "char",
     "fakes": RSA, "inputs": inputs(0x5A4, validate_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?sub_1403489E0@@YA_NPEBEPEA_N@Z", "ret": "char", "fakes": VALIDATE, "inputs": inputs(0x5A5, process_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DB_AuthLoad_Inflate@@YAHPEAUdb_z_stream_s@@HH@Z", "ret": "int", "fakes": PROCESS,
     "inputs": inputs(0x5A6, inflate_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DB_AuthLoad_InflateInit@@YAHPEAUdb_z_stream_s@@HPEBD@Z", "ret": "int", "inputs": inputs(0x5A7, init_args)},
    {"build": "iw6mp64_MSStore_ship", "symbol": "?DB_AuthLoad_InflateEnd@@YAXPEAUdb_z_stream_s@@@Z", "ret": "void", "inputs": inputs(0x5A8, end_args)},
]
