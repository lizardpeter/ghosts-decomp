"""Differential cases for src/database/db_misc_load_db.cpp (Lua files, sound driver globals, reverb presets, vector
fields, leaderboards, compute shaders) against the Store build: random headers (every pointer null, inline, insert or
an offset; counts of 0, 1 and more) with dbstream.py's logged stream fakes and logged fakes for the nested loaders,
the asset linkers and Load_CreateComputeShader. tools/fastfile/misc_assets.py is the same logic, checked against the
game on real zones (docs/assets/misc.md)."""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
M64 = 2 ** 64 - 1

FAKES = {
    **ds.STREAM_FAKES,
    "?Load_LuaFileAsset@@YAXPEAPEAULuaFile@@@Z": ds.asset_linker("Load_LuaFileAsset"),
    "?Load_SndDriverGlobalsAsset@@YAXPEAPEAUSndDriverGlobals@@@Z": ds.asset_linker("Load_SndDriverGlobalsAsset"),
    "?Load_ReverbPresetAsset@@YAXPEAPEAUReverbPreset@@@Z": ds.asset_linker("Load_ReverbPresetAsset"),
    "?Load_VectorFieldAsset@@YAXPEAPEAUVectorField@@@Z": ds.asset_linker("Load_VectorFieldAsset"),
    "?Load_LeaderboardDefAsset@@YAXPEAPEAULeaderboardDef@@@Z": ds.asset_linker("Load_LeaderboardDefAsset"),
    "?Load_ComputeShaderAsset@@YAXPEAPEAUComputeShader@@@Z": ds.asset_linker("Load_ComputeShaderAsset"),
    "?Load_CreateComputeShader@@YAXPEAPEAEPEAUComputeShader@@@Z":
        ds.recorder("Load_CreateComputeShader", "qq", ("varbyte4",)),
    "?Load_LuaFile@@YAX_N@Z": ds.recorder("Load_LuaFile", "b", ("varLuaFile", "g_streamPos")),
    "?Load_SndDriverGlobals@@YAX_N@Z": ds.recorder("Load_SndDriverGlobals", "b", ("varSndDriverGlobals", "g_streamPos")),
    "?Load_ReverbPreset@@YAX_N@Z": ds.recorder("Load_ReverbPreset", "b", ("varReverbPreset", "g_streamPos")),
    "?Load_VectorField@@YAX_N@Z": ds.recorder("Load_VectorField", "b", ("varVectorField", "g_streamPos")),
    "?Load_LeaderboardDef@@YAX_N@Z": ds.recorder("Load_LeaderboardDef", "b", ("varLeaderboardDef", "g_streamPos")),
    "?Load_LbColumnDef@@YAX_N@Z": ds.recorder("Load_LbColumnDef", "b", ("varLbColumnDef", "g_streamPos")),
    "?Load_ComputeShader@@YAX_N@Z": ds.recorder("Load_ComputeShader", "b", ("varComputeShader", "g_streamPos")),
    "?Load_GfxComputeShaderLoadDef@@YAX_N@Z":
        ds.recorder("Load_GfxComputeShaderLoadDef", "b", ("varGfxComputeShaderLoadDef", "g_streamPos")),
}


def case(symbol, seed, make, n=200):
    rnd = random.Random(seed)
    return {"symbol": symbol, "build": STORE, "ret": "void",
            "fakes": {k: v for k, v in FAKES.items() if k != symbol}, "inputs": [make(rnd) for _ in range(n)]}


def _loader(size, var, fill, feed=0x2000, extra=()):
    """A header of `size` random bytes with `fill` applied, at var; `extra` names more globals to point into the
    buffer (var, offset into the header)."""
    def make(r):
        b = bytearray(r.randbytes(size))
        struct.pack_into("<Q", b, 0, ds.pointer(r) & M64)
        fill(r, b)
        flag = r.random() < 0.5
        buf = bytearray(r.randbytes(ds.BUF_SIZE))
        buf[OFF_STRUCT:OFF_STRUCT + size] = b
        zone = ds.Zone(r, (bytes(b) if flag else b"") + r.randbytes(feed))

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            for v, off in extra:
                w.u64(va(v), HEAP + OFF_STRUCT + off)
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _any(r):
    return r.choice([0, 1, FOLLOWING, r.getrandbits(64)])


def _lua(r, b):
    struct.pack_into("<i", b, 8, r.choice([0, 1, 7, 33, -1, -0x40, r.randint(0, 0x400)]))
    struct.pack_into("<Q", b, 0x10, _any(r))


def _snd(r, b):
    struct.pack_into("<Q", b, 0x10, _any(r))


def _vector_field(r, b):
    struct.pack_into("<Q", b, 8, ds.pointer(r) & M64)
    struct.pack_into("<3I", b, 0x34, *(r.choice([0, 1, 2, 3, 5]) for _ in range(3)))


def _leaderboard(r, b):
    struct.pack_into("<i", b, 0xC, r.choice([0, 1, 2, r.randint(0, 6)]))
    struct.pack_into("<Q", b, 0x18, _any(r))


def _column(r, b):
    struct.pack_into("<Q", b, 0x18, ds.pointer(r) & M64)


def _compute_shader(r, b):
    struct.pack_into("<Q", b, 0x10, ds.pointer(r) & M64)
    struct.pack_into("<I", b, 0x18, r.choice([0, 4, 0x40, r.randint(0, 0x800)]))


def _load_def(r, b):
    struct.pack_into("<Q", b, 0, ds.pointer(r) & M64)
    struct.pack_into("<I", b, 8, r.choice([0, 4, 0x40, 0x80000000 | r.getrandbits(4), r.randint(0, 0x800)]))


def _handle(var, inner):
    def make(r):
        buf, flag = bytearray(r.randbytes(ds.BUF_SIZE)), r.random() < 0.3
        value = r.choice([0, FOLLOWING, INSERT, INSERT, r.getrandbits(64), 1])
        struct.pack_into("<Q", buf, OFF_STRUCT, value)
        zone = ds.Zone(r, (struct.pack("<Q", value) if flag else b"") + r.randbytes(0x100))

        def setup(w):
            zone.start(w)
            w.u64(va(var), HEAP + OFF_STRUCT)
            w.u64(va(inner), HEAP + 0x30000 + r.getrandbits(8))
        return {"args": [flag, bytes(buf)], "setup": setup}
    return make


def _ptr_case(name, seed):
    return case(f"?Load_{name}Ptr@@YAX_N@Z", seed, _handle(f"var{name}Ptr", f"var{name}"))


CASES = [
    case("?Load_LuaFile@@YAX_N@Z", 0x2A50, _loader(0x18, "varLuaFile", _lua)),
    _ptr_case("LuaFile", 0x2B20),
    case("?Load_SndDriverGlobals@@YAX_N@Z", 0x6EC0, _loader(0x18, "varSndDriverGlobals", _snd)),
    _ptr_case("SndDriverGlobals", 0x6F90),
    case("?Load_ReverbPreset@@YAX_N@Z", 0x5A90, _loader(0x48, "varReverbPreset", lambda r, b: None)),
    _ptr_case("ReverbPreset", 0x5B20),
    case("?Load_VectorField@@YAX_N@Z", 0x8770, _loader(0x50, "varVectorField", _vector_field)),
    _ptr_case("VectorField", 0x8870),
    case("?Load_LbColumnDef@@YAX_N@Z", 0x2280, _loader(0x38, "varLbColumnDef", _column)),
    case("?Load_LeaderboardDef@@YAX_N@Z", 0x2360, _loader(0x28, "varLeaderboardDef", _leaderboard)),
    _ptr_case("LeaderboardDef", 0x2470),
    case("?Load_GfxComputeShaderLoadDef@@YAX_N@Z", 0xEF40,
         _loader(0x10, "varGfxComputeShaderLoadDef", _load_def, extra=(("varComputeShader", 0x100),))),
    case("?Load_ComputeShader@@YAX_N@Z", 0xBE80, _loader(0x20, "varComputeShader", _compute_shader)),
    _ptr_case("ComputeShader", 0xBF40),
]
