"""Run original and reconstructed x64 functions side by side in one emulator.

The original exe (verified by sha256 against target.toml) and build/recon.dll are both mapped into a single
Unicorn x86-64 address space. A call follows the Win64 calling convention, runs to a sentinel return address,
then reads RAX/XMM0 and every buffer passed by pointer. Comparing the two runs on the same inputs checks
behaviour, independent of which compiler built the reconstruction.

Ported from black-ops-1-decomp's x86-32 harness. What changed for x64 (docs/verification.md):
- Win64 arguments: position i < 4 goes in RCX/RDX/R8/R9, or XMM0..XMM3 for float/double (by position, not by
  count of each kind); later arguments on the stack above 32 bytes of shadow space; RSP is 16-byte aligned
  before the call, so RSP % 16 == 8 at entry.
- Returns in RAX, or XMM0 for float/double. No x87 state: x64 MSVC does all floating point in SSE.
- A TEB is reachable through GS (self pointer, stack base/limit for __chkstk, PEB with the image base).
"""
import hashlib
import os
import struct
import tomllib
from pathlib import Path

import pefile
from unicorn import UC_ARCH_X86, UC_HOOK_MEM_WRITE, UC_MODE_64, Uc, UcError
from unicorn.x86_const import (UC_X86_REG_MXCSR, UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RAX, UC_X86_REG_RBP,
                               UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP, UC_X86_REG_XMM0,
                               UC_X86_REG_XMM1, UC_X86_REG_XMM2, UC_X86_REG_XMM3)

ROOT = Path(__file__).resolve().parents[2]
STACK, STACK_SIZE = 0x00100000, 0x00100000
HEAP, HEAP_SIZE = 0x00300000, 0x00100000
SENTINEL = 0x00200000
TEB = 0x00400000
INT_REGS = (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)
XMM_REGS = (UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2, UC_X86_REG_XMM3)
MASK64 = (1 << 64) - 1


def _page(n):
    return (n + 0xFFF) & ~0xFFF


class Image:
    def __init__(self, path: Path):
        self.pe = pefile.PE(str(path), fast_load=True)
        self.pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = _page(self.pe.OPTIONAL_HEADER.SizeOfImage)
        self.data = self.pe.get_memory_mapped_image()
        self.exports = {}
        if hasattr(self.pe, "DIRECTORY_ENTRY_EXPORT"):
            for e in self.pe.DIRECTORY_ENTRY_EXPORT.symbols:
                self.exports[e.name.decode()] = self.base + e.address


def reference_build() -> str:
    """The build tests run against: the first reference build with a MAP in target.toml."""
    cfg = tomllib.loads((ROOT / "target.toml").read_text())
    return next(b["id"] for b in cfg["build"] if b.get("kind") == "reference" and "map" in b)


def original_exe(build: str | None = None) -> Path:
    """Locate the original exe: $IW6_ORIGINALS/<build>.exe, verified against target.toml."""
    build = build or reference_build()
    cfg = tomllib.loads((ROOT / "target.toml").read_text())
    spec = next(b for b in cfg["build"] if b["id"] == build)
    # Arxan-protected builds are tested from their unpacked image (tools/unpack/arxan.py)
    want = spec.get("unpacked_sha256") or spec["exe"]["sha256"]
    path = Path(os.environ.get("IW6_ORIGINALS", ROOT / ".work" / "originals")) / f"{build}.exe"
    if not path.exists():
        raise SystemExit(f"missing {path}: run tools/fetch_originals.py {build} {path.parent}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != want:
        raise SystemExit(f"{path} does not match target.toml sha256")
    return path


def _is_float(a):
    return isinstance(a, tuple) and a[0] in ("f", "d")


def _float_bits(a) -> int:
    return struct.unpack("<I", struct.pack("<f", a[1]))[0] if a[0] == "f" else struct.unpack("<Q", struct.pack("<d", a[1]))[0]


class Machine:
    def __init__(self, *images: Image):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_64)
        for img in images:
            self.mu.mem_map(img.base, img.size)
            self.mu.mem_write(img.base, img.data[:img.size])
        self.mu.mem_map(STACK, STACK_SIZE)
        self.mu.mem_map(HEAP, HEAP_SIZE)
        self.mu.mem_map(SENTINEL, 0x1000)
        self.mu.mem_map(TEB, 0x10000)
        self.mu.mem_write(TEB + 0x08, struct.pack("<Q", STACK + STACK_SIZE))  # NT_TIB.StackBase
        self.mu.mem_write(TEB + 0x10, struct.pack("<Q", STACK))               # NT_TIB.StackLimit
        self.mu.mem_write(TEB + 0x30, struct.pack("<Q", TEB))                 # NT_TIB.Self
        self.mu.mem_write(TEB + 0x60, struct.pack("<Q", TEB + 0x2000))        # PEB
        if images:
            self.mu.mem_write(TEB + 0x2000 + 0x10, struct.pack("<Q", images[0].base))  # PEB.ImageBaseAddress
        self.mu.msr_write(0xC0000101, TEB)                                    # IA32_GS_BASE
        # Writes into any mapped image (the original's globals) are journaled so each call can be
        # rolled back and its side effects compared: see call().
        self.images = images
        self._journal = {}
        self.mu.hook_add(UC_HOOK_MEM_WRITE, self._on_write)

    def _on_write(self, mu, access, address, size, value, user):
        for img in self.images:
            if img.base <= address < img.base + img.size:
                for a in range(address, address + size):
                    if a not in self._journal:
                        self._journal[a] = bytes(mu.mem_read(a, 1))
                return

    def poke(self, va, data: bytes):
        self.mu.mem_write(va, data)

    def call(self, va, args, ret="int"):
        """args: ints, floats ('f', x), doubles ('d', x), or bytes (passed by pointer, read back after).
        ret: int (32-bit), int64, char, short, float, double, void.

        Returns (return value, [buffer contents after the call], {address: byte} written in mapped images).
        Image writes are rolled back afterwards, so calls never see each other's state.
        A crash returns ("fault: ...", [], writes)."""
        mu = self.mu
        mu.mem_write(HEAP, b"\0" * HEAP_SIZE)
        heap = HEAP
        slots, bufs = [], []  # slot: (is_float, 64-bit value)
        for a in args:
            if isinstance(a, (bytes, bytearray)):
                mu.mem_write(heap, bytes(a))
                bufs.append((heap, len(a)))
                slots.append((False, heap))
                heap += _page(len(a) + 16)
            elif _is_float(a):
                slots.append((True, _float_bits(a)))
            else:
                slots.append((False, a & MASK64))
        # stack: [ret][shadow 4x8][arg5][arg6]... ; RSP % 16 == 8 at entry
        nstack = max(0, len(slots) - 4)
        top = STACK + STACK_SIZE - 0x100
        sp = (top - (8 + 0x20 + 8 * nstack)) & ~0xF
        sp -= 8
        mu.mem_write(sp, struct.pack("<Q", SENTINEL))
        for i, (_, v) in enumerate(slots[4:]):
            mu.mem_write(sp + 8 + 0x20 + 8 * i, struct.pack("<Q", v))
        for i, (isf, v) in enumerate(slots[:4]):
            if isf:
                mu.reg_write(XMM_REGS[i], v)
            # MSVC also passes floating-point values of varargs in the integer register; harmless otherwise
            mu.reg_write(INT_REGS[i], v)
        mu.reg_write(UC_X86_REG_RSP, sp)
        mu.reg_write(UC_X86_REG_RBP, 0)
        mu.reg_write(UC_X86_REG_MXCSR, 0x1F80)  # all SSE exceptions masked, round to nearest
        self._journal = {}
        try:
            mu.emu_start(va, SENTINEL, count=2_000_000)
            fault = None
        except UcError as e:
            fault = f"fault: {e}"
        globals_written = {a: bytes(mu.mem_read(a, 1)) for a in sorted(self._journal)}
        for a, old in self._journal.items():
            mu.mem_write(a, old)
        self._journal = {}
        if fault:
            return fault, [], globals_written
        rax = mu.reg_read(UC_X86_REG_RAX)
        xmm0 = mu.reg_read(UC_X86_REG_XMM0)
        eax = rax & 0xFFFFFFFF
        value = {
            "int": eax if eax < 1 << 31 else eax - (1 << 32),
            "int64": rax if rax < 1 << 63 else rax - (1 << 64),
            "char": struct.unpack("<b", bytes([rax & 0xFF]))[0],
            "short": struct.unpack("<h", struct.pack("<H", rax & 0xFFFF))[0],
            "float": struct.unpack("<f", struct.pack("<I", xmm0 & 0xFFFFFFFF))[0],
            "double": struct.unpack("<d", struct.pack("<Q", xmm0 & MASK64))[0],
            "void": None,
        }[ret]
        return value, [bytes(mu.mem_read(a, n)) for a, n in bufs], globals_written
