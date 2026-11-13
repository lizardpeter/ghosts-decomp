"""Differential cases for database/db_assetnames.cpp: the per-type name and size handlers, for every XAssetType
(and the ones without handlers, where the original faults and the input is skipped). The XAsset and a header with
a name pointer at each offset a getter uses (0, 8, 0x28, 0x60, 0x68) are passed in buffers."""
import random
import struct

from harness import HEAP


def asset_buffer(r, default=True):
    """[XAsset {type, header -> HEAP + 0x100}] then at +0x100 a header with name pointers at every name offset.
    Type 0x40 (ASSET_TYPE_ASSETLIST) is left out of DB_GetXAssetName's inputs: its "name getter" entry is the
    folded `*header = rdx` of a set-name handler, so the original stores whatever RDX held (the table address)."""
    t = r.choice(range(0x3F)) if r.random() < 0.9 else r.choice([0x1C, 0x28, 0x3F] + ([0x40] if default else []))
    buf = bytearray(0x200)
    struct.pack_into("<iiQ", buf, 0, t, 0, HEAP + 0x100)
    for k, off in enumerate((0, 8, 0x28, 0x60, 0x68)):
        struct.pack_into("<Q", buf, 0x100 + off, HEAP + 0x180 + 8 * k)
    return bytes(buf)


def inputs(seed, args, n=300):
    r = random.Random(seed)
    return [args(r) for _ in range(n)]


CASES = [
    {"symbol": "?DB_GetXAssetName@@YAPEBDPEBUXAsset@@@Z", "ret": "int64",
     "inputs": inputs(0x2A0, lambda r: [asset_buffer(r, default=False)])},
    {"symbol": "?DB_SetXAssetName@@YAXPEAUXAsset@@PEBD@Z", "ret": "void",
     "inputs": inputs(0x2A1, lambda r: [asset_buffer(r), r.choice([0, 0x5F0000, r.getrandbits(48)])])},
    {"symbol": "?DB_GetXAssetTypeSize@@YAHH@Z", "ret": "int",
     "inputs": inputs(0x2A2, lambda r: [r.choice(range(0x3F)) if r.random() < 0.9 else r.choice([0x1C, 0x2A, 0x40])])},
]
