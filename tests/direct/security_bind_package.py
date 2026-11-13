#!/usr/bin/env python3
"""Run patched *Store executable entries* for S17 bind/unbind/swap in Unicorn.

This verifies the actual native detours and Win64 ABI in the canonical enhanced
package, rather than invoking only replacement exports. No live networking.
"""
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "offline"),
                str(ROOT / "tests" / "differential")]
import package
from harness import Image, Machine, original_exe
from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8

KEY_SETTER = "?Key_SetBinding@@YAXW4LocalClientNum_t@@HH@Z"
ENTRIES = (
    (0x1403106D0, [b"bind", bytes([0x80]), b"+attack"]),
    (0x140310EB0, [b"unbind", bytes([0xff])]),
    (0x140310D20, [b"bind_swap", bytes([0x80]), b"a"]),
)


def arguments(values):
    def apply(w):
        ptrs = [w.cstr(v) for v in values]
        argv = w.alloc(struct.pack("<" + "Q" * len(ptrs), *ptrs))
        # Store cmd_args, unlike the older admission-model scratch layout.
        w.u32(0x1469CECF0, 0)
        w.u32(0x1469CED34, len(ptrs))
        w.u64(0x1469CED58, argv)
    return apply


def main():
    original = original_exe(package.BUILD)
    enhanced = ROOT / "build" / package.BUILD / "enhanced" / "recon.dll"
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "enhanced"
        manifest = package.package(original, enhanced, output, mode="direct")
        guards = {int(g["va"], 16): g["symbol"] for g in manifest["guards"]}
        for va, _ in ENTRIES:
            assert guards[va] == package.DIRECT[va]
        exe = Image(output / "iw6mp64_enhanced.exe")
        dll = Image(output / "recon.dll")
        machine = Machine(exe, dll)
        for slot, name in exe.iat.items():
            if name.startswith("recon.dll!"):
                machine.mu.mem_write(
                    slot, struct.pack("<Q", dll.exports[name.split("!", 1)[1]]))
        assert KEY_SETTER in dll.exports, "enhanced binding guard is not exported"
        calls = []

        def setter(mu):
            calls.append(tuple(mu.reg_read(r) for r in (
                UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8)))

        fake_setters = {0x140310B30: setter, dll.exports[KEY_SETTER]: setter}
        for va, argv in ENTRIES:
            calls.clear()
            result = machine.call(va, [], ret="void",
                                  setup=arguments(argv), fakes=fake_setters)
            assert not (isinstance(result[0], str) and
                        result[0].startswith("fault")), (hex(va), result[0])
            assert not calls, ("invalid key reached native binding accessor", hex(va), calls)
        calls.clear()
        # Without a positive case an incorrect cmd_args setup could let every
        # negative case pass simply by returning at the argument-count check.
        result = machine.call(0x140310EB0, [], ret="void",
                              setup=arguments([b"unbind", b"a"]),
                              fakes=fake_setters)
        assert not (isinstance(result[0], str) and
                    result[0].startswith("fault")), result[0]
        assert calls == [(0, ord("a"), 0)], calls
    print("PASS: patched Store native bind handlers reject high-byte keys, valid unbind dispatches")


if __name__ == "__main__":
    main()
