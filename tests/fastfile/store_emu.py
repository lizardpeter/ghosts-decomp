"""Run the Store build's own fastfile loader (DB_LoadXFile, 140349300) on a real zone in the emulator.

The zone is handed to the game as a memory-backed DBFile (handle NULL, memoryBuffer/memoryBufferSize set), which the
Store build's DB_ReadXFileStage (140349C30) reads with memcpy instead of ReadFileEx, so everything from the header
checks through authentication (SHA-256 blocks, the RSA-PSS signature in libtomcrypt), zlib inflate, the stream, the
pointer rules, the script string list and the XAsset list runs as the game's code. Only these are replaced by Python:

- PMem_AllocFromSource (140543A40): a bump allocator in a large mapped region (the zone's block memory);
- SL_GetString (14047D4D0): records each script string and returns its 1-based index;
- DB_LinkXAssetEntry1 (14036D830): records (type, name) of every asset the loader links, copies the header
  (DB_GetXAssetTypeSize bytes) into a pool region, 16-byte aligned one after another, and returns an entry whose
  header is that copy, as for an asset of a new name (the reader's Stream.link does the same);
- the load bar (140190C90 LoadBar_IsComplete, 140190E40) and two engine callbacks of the asset linkers
  (140264A70, 1404A8B60), which don't touch the stream;
- Com_Error (14045FB30), Com_Error-like Sys_Error (14054D9C0) and DB_DirtyDiscError (1403496B0) stop the run with an
  error (a failed check).

Imports are stubs (tests/differential/harness.py style), with memcpy/memmove/memset/memcmp/strncpy/strcmp and a malloc/calloc/realloc heap implemented.
"""
import struct
import sys
from pathlib import Path

from unicorn import UC_ARCH_X86, UC_HOOK_CODE, UC_MODE_64, Uc, UcError
from unicorn.x86_const import (UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX,
                               UC_X86_REG_RIP, UC_X86_REG_RSP, UC_X86_REG_MXCSR)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "differential"))
from harness import Image, original_exe  # noqa: E402

STORE = "iw6mp64_MSStore_ship"
STACK, STACK_SIZE = 0x01000000, 0x00200000
SENTINEL = 0x00200000
TEB = 0x00400000
TLS_BLOCK = 0x00410000
STUBS = 0x00420000
SCRATCH = 0x00500000          # DBFile, XZoneMemory, the output buffer, link entries
FILEBUF = 0x10000000          # the .ff bytes
ARENA = 0x40000000            # zone block memory (PMem_AllocFromSource)
POOL, POOL_SIZE = 0x30000000, 0x01000000  # asset headers (DB_LinkXAssetEntry1)
CRT_HEAP, CRT_HEAP_SIZE = 0x20000000, 0x01000000  # malloc/calloc/realloc (libtomcrypt's bignums)

DB_LoadXFile = 0x140349300
FAKE_ALLOC, FAKE_SL_GETSTRING, FAKE_LINK = 0x140543A40, 0x14047D4D0, 0x14036D830
LOAD_XASSET = 0x14035D5F0
FAKE_RET0 = (0x140264A70, 0x1404A8B60, 0x140190E40)
FAKE_RET1 = (0x140190C90,)
ERRORS = {0x14045FB30: "Com_Error", 0x14054D9C0: "Sys_Error", 0x1403496B0: "DB_DirtyDiscError"}
# globals the run reports (Store addresses; docs/fastfiles.md)
G_STREAM_POS_ARRAY = 0x145F06618  # g_streamPosArray[7]
G_VAR_XASSET_LIST = 0x144310BF8   # g_varXAssetList (XAssetList, 0x28 bytes)
G_STREAM_IMAGE_COUNT = 0x1443A4820
G_STREAM_IMAGE_ROWS = 0x144310C20  # the rows, 0x18 bytes each


# offset of the name pointer in an asset header, by type (the name getters at 1409924A0)
NAME_OFFSET = {0x0D: 0x60, 0x0F: 8, 0x10: 8, 0x11: 8, 0x1F: 8, 0x21: 8, 0x38: 0x28, 0x3A: 0x68}


# DB_GetXAssetTypeSize (1403488D0), by type: read from the exe's table at 1409928A0 (`mov eax, size; ret` each)
def _type_sizes(img):
    out = {}
    for t in range(0x3F):
        fn = struct.unpack_from("<Q", img.data, 0x1409928A0 - img.base + 8 * t)[0]
        code = img.data[fn - img.base:fn - img.base + 6] if fn else b""
        if code[:1] == b"\xb8" and code[5:6] == b"\xc3":
            out[t] = struct.unpack_from("<I", code, 1)[0]
    return out


_IMAGE = None


class LoadError(Exception):
    pass


def _page(n):
    return (n + 0xFFF) & ~0xFFF


class StoreLoader:
    def __init__(self, arena_size=0x10000000):
        global _IMAGE
        if _IMAGE is None:
            _IMAGE = Image(original_exe(STORE))   # parsed once per process: it is large
        self.img = _IMAGE
        global TYPE_SIZE
        TYPE_SIZE = _type_sizes(self.img)
        mu = self.mu = Uc(UC_ARCH_X86, UC_MODE_64)
        mu.mem_map(self.img.base, self.img.size)
        mu.mem_write(self.img.base, self.img.data[:self.img.size])
        for base, size in ((STACK, STACK_SIZE), (SENTINEL, 0x1000), (TEB, 0x10000), (TLS_BLOCK, 0x10000),
                           (STUBS, 0x10000), (SCRATCH, 0x100000)):
            mu.mem_map(base, size)
        mu.mem_write(TEB + 0x08, struct.pack("<Q", STACK + STACK_SIZE))
        mu.mem_write(TEB + 0x10, struct.pack("<Q", STACK))
        mu.mem_write(TEB + 0x30, struct.pack("<Q", TEB))
        mu.mem_write(TEB + 0x60, struct.pack("<Q", TEB + 0x2000))
        mu.mem_write(TEB + 0x58, struct.pack("<Q", TEB + 0x3000))
        mu.mem_write(TEB + 0x3000, struct.pack("<Q", TLS_BLOCK))
        if self.img.tls:
            mu.mem_write(TLS_BLOCK, self.img.tls[0])
        mu.msr_write(0xC0000101, TEB)
        self.arena_size = arena_size
        mu.mem_map(ARENA, arena_size)
        mu.mem_map(CRT_HEAP, CRT_HEAP_SIZE)
        mu.mem_map(POOL, POOL_SIZE)
        # A null COM object for the D3D11 device and immediate context (dx.device 14A37D628, dx.context
        # 14A37D630): every method returns S_OK; the device's Create* methods hand back this same object through
        # their out pointer. Loading creates GPU objects through it (XGfxGlobals' buffers, materials' state
        # objects); nothing it returns reaches the stream.
        com = SCRATCH + 0xF0000
        vtbl, code = com + 0x10, com + 0x1000
        mu.mem_write(com + 0x8, struct.pack("<Q", vtbl))
        for slot in range(256):
            mu.mem_write(vtbl + 8 * slot, struct.pack("<Q", code + 4 * slot))
            mu.mem_write(code + 4 * slot, b"\x31\xc0\xc3\x90")
        self.com, self.com_code = com + 0x8, code
        mu.hook_add(UC_HOOK_CODE, self._on_com, begin=code, end=code + 0x400)
        self.stub_names = {}
        for slot, name in self.img.iat.items():
            stub = STUBS + 0x10 * len(self.stub_names)
            self.stub_names[stub + 2] = name.split("!", 1)[1]  # on the ret, after `xor eax, eax`
            mu.mem_write(stub, b"\x31\xc0\xc3")
            mu.mem_write(slot, struct.pack("<Q", stub))
        mu.hook_add(UC_HOOK_CODE, self._on_stub, begin=STUBS, end=STUBS + 0xFFFF)
        self.fakes = {LOAD_XASSET: self._load_xasset, FAKE_ALLOC: self._alloc, FAKE_SL_GETSTRING: self._sl_getstring, FAKE_LINK: self._link}
        for a in FAKE_RET0:
            self.fakes[a] = lambda mu: 0
        for a in FAKE_RET1:
            self.fakes[a] = lambda mu: 1
        for a, name in ERRORS.items():
            self.fakes[a] = self._error(name)
        for a in self.fakes:
            mu.hook_add(UC_HOOK_CODE, self._on_fake, begin=a, end=a)

    # --- helpers -------------------------------------------------------------------------------------------------
    def u64(self, va):
        return struct.unpack("<Q", bytes(self.mu.mem_read(va, 8)))[0]

    def cstr(self, va, limit=4096):
        out = bytearray()
        while len(out) < limit:
            chunk = bytes(self.mu.mem_read(va + len(out), 64))
            i = chunk.find(b"\0")
            if i >= 0:
                return bytes(out + chunk[:i])
            out += chunk
        return bytes(out)

    def _ret(self, mu, value):
        rsp = mu.reg_read(UC_X86_REG_RSP)
        ret = self.u64(rsp)
        if value is not None:
            mu.reg_write(UC_X86_REG_RAX, value & (2 ** 64 - 1))
        mu.reg_write(UC_X86_REG_RSP, rsp + 8)
        mu.reg_write(UC_X86_REG_RIP, ret)

    def _on_fake(self, mu, address, size, user):
        fn = self.fakes.get(address)
        if fn:
            value = fn(mu)
            if value is not False:
                self._ret(mu, value)

    def _load_xasset(self, mu):
        if self.stop_at_assets:
            self.stopped = True
            mu.emu_stop()
            return None
        return False  # run the real Load_XAsset

    def _error(self, name):
        def fn(mu):
            fmt = mu.reg_read(UC_X86_REG_RDX if name == "Com_Error" else UC_X86_REG_RCX)
            self.error = f"{name}: {self.cstr(fmt).decode('latin1') if fmt else ''}"
            mu.emu_stop()
            return 0
        return fn

    def _on_stub(self, mu, address, size, user):
        name = self.stub_names.get(address)
        if name is None:
            return
        rcx, rdx, r8 = (mu.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8))
        if name in ("memcpy", "memmove"):
            if r8:
                mu.mem_write(rcx, bytes(mu.mem_read(rdx, r8)))
            mu.reg_write(UC_X86_REG_RAX, rcx)
        elif name == "memset":
            if r8:
                mu.mem_write(rcx, bytes([rdx & 0xFF]) * r8)
            mu.reg_write(UC_X86_REG_RAX, rcx)
        elif name == "memcmp":
            a, b = bytes(mu.mem_read(rcx, r8)), bytes(mu.mem_read(rdx, r8))
            mu.reg_write(UC_X86_REG_RAX, 0 if a == b else (2 ** 64 - 1 if a < b else 1))
        elif name == "strncpy":
            src = self.cstr(rdx, limit=r8 + 64)[:r8]
            mu.mem_write(rcx, src + b"\0" * (r8 - len(src)))
            mu.reg_write(UC_X86_REG_RAX, rcx)
        elif name in ("strcmp", "_stricmp"):
            a, b = self.cstr(rcx), self.cstr(rdx)
            if name == "_stricmp":
                a, b = a.lower(), b.lower()
            mu.reg_write(UC_X86_REG_RAX, 0 if a == b else (2 ** 64 - 1 if a < b else 1))
        elif name in ("malloc", "calloc", "realloc"):
            size = {"malloc": rcx, "calloc": rcx * rdx, "realloc": rdx}[name]
            at = self.heap_next
            self.heap_next = (at + 16 + size + 15) & ~15
            if self.heap_next > CRT_HEAP + CRT_HEAP_SIZE:
                raise LoadError("CRT heap exhausted")
            mu.mem_write(at, struct.pack("<Q", size))
            if name == "realloc" and rcx:
                old = struct.unpack("<Q", bytes(mu.mem_read(rcx - 16, 8)))[0]
                mu.mem_write(at + 16, bytes(mu.mem_read(rcx, min(old, size))))
            elif size:
                mu.mem_write(at + 16, b"\0" * size)
            mu.reg_write(UC_X86_REG_RAX, at + 16)
        elif name == "free":
            pass
        else:
            self.imports.append(name)

    # ID3D11Device slot -> where its out pointer is: a register, or a stack argument (index from 0)
    COM_OUT = {**{i: UC_X86_REG_R9 for i in range(3, 11)}, 11: 5, **{i: 4 for i in (12, 13, 15, 16, 17, 18)},
               14: 9, **{i: UC_X86_REG_R8 for i in range(20, 24)}}

    def _on_com(self, mu, address, size, user):
        off = address - self.com_code
        if off % 4 != 2:  # on the ret
            return
        where = self.COM_OUT.get(off // 4)
        if where is None:
            return
        rsp = mu.reg_read(UC_X86_REG_RSP)
        out = self.u64(rsp + 8 + 8 * where) if isinstance(where, int) and where < 16 else mu.reg_read(where)
        if out:
            mu.mem_write(out, struct.pack("<Q", self.com))

    def _alloc(self, mu):
        size, align = mu.reg_read(UC_X86_REG_RCX), mu.reg_read(UC_X86_REG_RDX)
        at = (self.arena_next + align - 1) & ~(align - 1)
        if at + size > ARENA + self.arena_size:
            raise LoadError(f"arena too small for {size:#x} bytes")
        self.arena_next = at + size
        self.allocs.append((at, size))
        return at

    def _sl_getstring(self, mu):
        self.script_strings.append(self.cstr(mu.reg_read(UC_X86_REG_RCX)))
        return len(self.script_strings)

    def _link(self, mu):
        asset_type, header_ptr = mu.reg_read(UC_X86_REG_RCX) & 0xFFFFFFFF, mu.reg_read(UC_X86_REG_RDX)
        header = self.u64(header_ptr)
        name_ptr = self.u64(header + NAME_OFFSET.get(asset_type, 0))
        self.linked.append((asset_type, header, self.cstr(name_ptr) if name_ptr else None))
        at = (self.pool_next + 15) & ~15
        mu.mem_write(at, bytes(mu.mem_read(header, TYPE_SIZE[asset_type])))
        self.pool_next = at + TYPE_SIZE[asset_type]
        entry = SCRATCH + 0x80000 + 0x20 * len(self.linked)
        mu.mem_write(entry, struct.pack("<QQ", asset_type, at))
        return entry

    # --- the run -------------------------------------------------------------------------------------------------
    def load(self, ff: bytes, zone_name: str, assets=True, limit=0):
        """DB_LoadXFile(&zoneMem, &file, out) on `ff`. Returns a dict of what the game saw.

        assets=False stops at the first Load_XAsset (14035D5F0): the header checks, authentication, the XFile
        header, the block allocation, the script string list, XGlobals and the XAsset array have run, the asset
        bodies have not. (Loading some asset types for real needs renderer state the emulator lacks: registered
        dvars and a device.)"""
        mu = self.mu
        self.stop_at_assets = not assets
        self.error, self.imports, self.allocs, self.script_strings, self.linked = None, [], [], [], []
        if getattr(self, "arena_next", ARENA) > ARENA:   # block memory starts zeroed, so runs compare cleanly
            mu.mem_write(ARENA, b"\0" * (self.arena_next - ARENA))
        self.arena_next = ARENA
        if getattr(self, "pool_next", POOL) > POOL:
            mu.mem_write(POOL, b"\0" * (self.pool_next - POOL))
        self.pool_next = POOL
        self.stopped = False
        self.heap_next = CRT_HEAP
        try:
            mu.mem_unmap(FILEBUF, self._filebuf_size)
        except AttributeError:
            pass
        self._filebuf_size = _page(len(ff) + 0x1000)
        mu.mem_map(FILEBUF, self._filebuf_size)
        mu.mem_write(FILEBUF, ff)
        mu.mem_write(SCRATCH, b"\0" * 0xF0000)
        mu.mem_write(0x14A37D628, struct.pack("<QQ", self.com, self.com))
        # r_loadForRenderer (14A2E1D98) -> a bool dvar that is off: no GPU resources are created from the zone
        # (Load_VertexBuffer, Load_Texture, the shader creators clear their pointer instead), as on a server.
        mu.mem_write(SCRATCH + 0xE0000, b"\0" * 0x60)
        mu.mem_write(0x14A2E1D98, struct.pack("<Q", SCRATCH + 0xE0000))
        dbfile, zonemem, out = SCRATCH, SCRATCH + 0x100, SCRATCH + 0x200
        name = zone_name.encode()[:63]
        mu.mem_write(dbfile, struct.pack("<QQQ", 0, len(ff), FILEBUF) + name + b"\0")
        sp = STACK + STACK_SIZE - 0x1000 - 8
        mu.mem_write(sp, struct.pack("<Q", SENTINEL))
        mu.reg_write(UC_X86_REG_RSP, sp)
        mu.reg_write(UC_X86_REG_RCX, zonemem)
        mu.reg_write(UC_X86_REG_RDX, dbfile)
        mu.reg_write(UC_X86_REG_R8, out)
        mu.reg_write(UC_X86_REG_R9, 0)
        mu.reg_write(UC_X86_REG_MXCSR, 0x1F80)
        try:
            mu.emu_start(DB_LoadXFile, SENTINEL, count=limit)
        except UcError as e:
            raise LoadError(f"fault {e} at {mu.reg_read(UC_X86_REG_RIP):#x}") from e
        if self.error:
            raise LoadError(self.error)
        blocks = [struct.unpack_from("<QQ", bytes(mu.mem_read(zonemem + 16 * i, 16))) for i in range(7)]
        ends = [self.u64(G_STREAM_POS_ARRAY + 8 * i) for i in range(7)]
        xal = bytes(mu.mem_read(G_VAR_XASSET_LIST, 0x28))
        count, = struct.unpack_from("<i", xal, 0x10)
        assets_ptr, = struct.unpack_from("<Q", xal, 0x18)
        assets = [struct.unpack_from("<iiQ", bytes(mu.mem_read(assets_ptr + 16 * i, 16)))[::2]
                  for i in range(count)] if assets_ptr else []
        return {
            "blocks": [(size, (end - data) if data else 0) for (data, size), end in zip(blocks, ends)],
            "block_data": [(data, bytes(mu.mem_read(data, size)) if data else b"") for data, size in blocks],
            "script_strings": list(self.script_strings),
            "string_count": struct.unpack_from("<i", xal, 0)[0],
            "asset_types": [t for t, _ in assets],
            "linked": [(t, n) for t, _, n in self.linked],
            "stream_image_count": struct.unpack("<I", bytes(mu.mem_read(G_STREAM_IMAGE_COUNT, 4)))[0],
            "stream_image_rows": bytes(mu.mem_read(G_STREAM_IMAGE_ROWS, 0x18 * struct.unpack(
                "<I", bytes(mu.mem_read(G_STREAM_IMAGE_COUNT, 4)))[0])),
            "auth_out": bytes(mu.mem_read(out, 0x100)),
            "imports": sorted(set(self.imports)),
            "complete": not self.stopped,
            "pool": bytes(mu.mem_read(POOL, self.pool_next - POOL)),
        }


if __name__ == "__main__":
    import time
    t = time.time()
    path = Path(sys.argv[1])
    r = StoreLoader().load(path.read_bytes(), path.stem, assets="--headers" not in sys.argv)
    for k, v in r.items():
        if k == "block_data":
            continue
        print(k, v if not isinstance(v, list) or len(v) < 12 else v[:12] + [f"... {len(v)}"])
    print(f"{time.time() - t:.1f}s")
