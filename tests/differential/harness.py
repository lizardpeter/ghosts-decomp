"""Run original and reconstructed x86 functions side by side in one emulator.
# NOT PORTED YET: this is the x86-32 harness from black-ops-1-decomp, kept as the starting point. IW6 is x64:
# the port needs UC_MODE_64, Win64 arguments (rcx/rdx/r8/r9 and xmm0-3 by position, 32-byte shadow space,
# 16-byte stack alignment), returns in rax/xmm0, no x87 state, and a GS-based TEB. See docs/verification.md.

The original exe (verified by sha256 against target.toml) and build/recon.dll are both mapped into a
single Unicorn x86-32 address space. A call pushes cdecl arguments, runs to a sentinel return address,
then reads EAX/ST0 and every buffer passed by pointer. Comparing the two runs on the same inputs
checks behaviour, independent of which compiler built the reconstruction.
"""
import hashlib
import math
import os
import struct
import tomllib
from pathlib import Path

import pefile
from unicorn import UC_ARCH_X86, UC_HOOK_MEM_WRITE, UC_MODE_32, Uc, UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_FP0,
                               UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG, UC_X86_REG_MXCSR)

ROOT = Path(__file__).resolve().parents[2]
STACK, STACK_SIZE = 0x00100000, 0x00100000
HEAP, HEAP_SIZE = 0x00300000, 0x00100000
SENTINEL = 0x00200000


def _page(n):
    return (n + 0xFFF) & ~0xFFF


def _st0(mu):
    top = (mu.reg_read(UC_X86_REG_FPSW) >> 11) & 7
    mant, se = mu.reg_read(UC_X86_REG_FP0 + top)
    sign = -1.0 if se & 0x8000 else 1.0
    exp = se & 0x7FFF
    if exp == 0 and mant == 0:
        return math.copysign(0.0, sign)
    if exp == 0x7FFF:
        return sign * math.inf if (mant << 1) & ((1 << 64) - 1) == 0 else math.nan
    return sign * mant / (1 << 63) * 2.0 ** (exp - 16383)


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


def original_exe(build="CoDMPServer") -> Path:
    """Locate the original exe: $IW6_ORIGINALS/<build>.exe, verified against target.toml."""
    cfg = tomllib.loads((ROOT / "target.toml").read_text())
    spec = next(b for b in cfg["build"] if b["id"] == build)["exe"]
    path = Path(os.environ.get("IW6_ORIGINALS", ROOT / ".work" / "originals")) / f"{build}.exe"
    if not path.exists():
        raise SystemExit(f"missing {path}: run tools/fetch_originals.py {build} {path.parent}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise SystemExit(f"{path} does not match target.toml sha256")
    return path


class Machine:
    def __init__(self, *images: Image):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        for img in images:
            self.mu.mem_map(img.base, img.size)
            self.mu.mem_write(img.base, img.data[:img.size])
        self.mu.mem_map(STACK, STACK_SIZE)
        self.mu.mem_map(HEAP, HEAP_SIZE)
        self.mu.mem_map(SENTINEL, 0x1000)
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
        """args: ints, floats ('f', x), or bytes (passed by pointer, read back after).

        Returns (return value, [buffer contents after the call], {address: byte} written in mapped
        images). Image writes are rolled back afterwards, so calls never see each other's state.
        A crash returns ("fault: ...", [], writes)."""
        mu = self.mu
        mu.mem_write(HEAP, b"\0" * HEAP_SIZE)
        heap = HEAP
        words, bufs = [], []
        for a in args:
            if isinstance(a, (bytes, bytearray)):
                mu.mem_write(heap, bytes(a))
                bufs.append((heap, len(a)))
                words.append(heap)
                heap += _page(len(a) + 16)
            elif isinstance(a, tuple) and a[0] == "f":
                words.append(struct.unpack("<I", struct.pack("<f", a[1]))[0])
            elif isinstance(a, tuple) and a[0] == "d":
                words.extend(struct.unpack("<II", struct.pack("<d", a[1])))
            else:
                words.append(a & 0xFFFFFFFF)
        sp = STACK + STACK_SIZE - 0x100
        for w in reversed(words):
            sp -= 4
            mu.mem_write(sp, struct.pack("<I", w))
        sp -= 4
        mu.mem_write(sp, struct.pack("<I", SENTINEL))
        mu.reg_write(UC_X86_REG_ESP, sp)
        mu.reg_write(UC_X86_REG_EBP, 0)
        # FPU state as Windows starts a thread: x87 control word 0x27F (53-bit precision, round to
        # nearest, all exceptions masked), empty x87 stack, MXCSR 0x1F80 (all SSE exceptions masked).
        # Unmasked exceptions would send the CRT's floor() etc. into exception handling.
        mu.reg_write(UC_X86_REG_FPCW, 0x27F)
        mu.reg_write(UC_X86_REG_FPSW, 0)
        mu.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
        mu.reg_write(UC_X86_REG_MXCSR, 0x1F80)
        self._journal = {}
        try:
            mu.emu_start(va, SENTINEL, count=1_000_000)
            fault = None
        except UcError as e:
            fault = f"fault: {e}"
        # side effects on globals: final bytes of every written address, then roll back
        globals_written = {a: bytes(mu.mem_read(a, 1)) for a in sorted(self._journal)}
        for a, old in self._journal.items():
            mu.mem_write(a, old)
        self._journal = {}
        if fault:
            return fault, [], globals_written
        eax = mu.reg_read(UC_X86_REG_EAX)
        value = {"int": eax if eax < 1 << 31 else eax - (1 << 32),
                 "char": struct.unpack("<b", bytes([eax & 0xFF]))[0],
                 "short": struct.unpack("<h", struct.pack("<H", eax & 0xFFFF))[0],
                 "float": _st0(mu) if ret == "float" else None,
                 "void": None}[ret]
        return value, [bytes(mu.mem_read(a, n)) for a, n in bufs], globals_written
