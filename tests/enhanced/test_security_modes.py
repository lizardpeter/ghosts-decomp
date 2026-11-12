"""S23/B0036: DXGI must never write beyond dx.displayModes[256] or the
renderer mode name tables in the enhanced Store build.

These are dynamic COM-callback simulations using the real enhanced C++ in the
hybrid DLL, not a text-only/synthetic copy of its bounds helper.
"""
import struct

from com import ComModel
from test_r_init import (
    SIGS, OUT, OUTPUT, DISPLAY_MODE_COUNT, RESOLUTION_NAMES, HMONITOR_BASE,
    Display, dx, fake, ENUM_DVAR,
)
from syms import va

ENTRY = "?R_EnumDisplayModes@@YAXXZ"
NATIVE_ADAPTER = "Iw6SecureEnumDisplayModes"
GET_DESC = (OUT, 7 * 8)
GET_MODES = (OUT, 8 * 8)
MODE_COUNT_OFFSET = DISPLAY_MODE_COUNT
NAME_TABLE_OFFSET = RESOLUTION_NAMES

def _exercise(env, requested, denominator=1, fail_second=False):
    modes = [struct.pack("<7I", 640 + (i // 2) * 8, 480 + (i // 2) * 4,
                         60 + i % 2, denominator, 0x1C, 1, 1)
             for i in range(min(requested, 5000))]
    caps = []
    def setup(w):
        m = w.m
        display = Display()
        def get_desc(call):
            name = "\\\\.\\DISPLAY1".encode("utf-16-le").ljust(0x40, b"\0")
            call.write(call.arg(0), name + struct.pack("<4iiiQ", 0, 0, 1920, 1080, 1, 1, HMONITOR_BASE))
            return 0
        def get_modes(call):
            count, buffer = call.arg(2), call.arg(3)
            if not buffer:
                m._emulated_write(count, struct.pack("<I", requested))
                return 0
            capacity = struct.unpack("<I", bytes(call.mu.mem_read(count, 4)))[0]
            caps.append(capacity)
            assert capacity <= 4096, "driver was handed unbounded mode-list capacity"
            if fail_second:
                return 0x887A0003   # MORE_DATA; output should not be consumed
            length = min(capacity, len(modes))
            if length:
                m._emulated_write(buffer, b"".join(modes[:length]))
            m._emulated_write(count, struct.pack("<I", length))
            return 0 if length == requested else 0x887A0003
        com = ComModel(SIGS, {GET_DESC: get_desc, GET_MODES: get_modes})
        com.install(m)
        display.com = com
        display.install(m)
        w.u64(dx(OUTPUT), com.new(OUT))
        w.u32(dx(DISPLAY_MODE_COUNT), 17)
        w.u32(va("unk_14A346B40"), 0)
        # A stale prior name table must not be mistaken for a valid result.
        w.write(dx(NAME_TABLE_OFFSET), b"Z" * (2 * 257 * 8))
    hooks = {
        "va": fake("va", "sii"),
        "?Sys_DirectXFatalError@@YAXXZ": fake("Sys_DirectXFatalError"),
        "?Dvar_RegisterEnum@@YAPEBUdvar_t@@PEBDQEBQEBDHI0@Z":
            fake("Dvar_RegisterEnum", "sqiis", ENUM_DVAR),
    }
    # The alias used by the native EXE package must be exported and callable.
    assert NATIVE_ADAPTER in env.dll.exports
    result, _, writes, observed = env.call(ENTRY, [], setup=setup, fakes=hooks)
    assert result is None
    assert len(caps) <= 1
    if requested == 0 or requested > 4096:
        assert not caps, (requested, caps)
    else:
        assert caps == [requested], (requested, caps)
    # Every outcome gives the engine at most 256 entries, even when DXGI
    # reports more, has a zero denominator or returns MORE_DATA.
    base = dx(MODE_COUNT_OFFSET)
    def read_new_u32(addr, default=17):
        return struct.unpack("<I", b"".join(writes.get(addr + i, struct.pack("<I", default)[i:i+1])
                                             for i in range(4)))[0]
    # Some emulator models record only modified bytes. The count is written
    # unconditionally by our enhanced path before sorting.
    count = read_new_u32(base)
    assert 0 < count <= 256, (requested, count)
    assert sum(1 for o in observed if "Dvar_RegisterEnum" in str(o)) <= 2
    return count

def test_driver_mode_count_never_exceeds_engine_allocation(env):
    for n in (1, 32, 256, 257, 300, 4097, 5000):
        count = _exercise(env, n)
        assert count == (min(n, 256) if n <= 4096 else 1), (n, count)

def test_driver_more_data_fails_closed(env):
    assert _exercise(env, 300, fail_second=True) == 1

def test_invalid_refresh_denominator_does_not_divide_by_zero(env):
    _exercise(env, 300, denominator=0)
