"""S17/B0009: high-bit key names must never index before playerKeys."""
import struct

# The pinned Microsoft Store cmd_args global; see tests/direct/admission.py.
NESTING = 0x1469CEDA0
ARGC = 0x1469CEDE4
ARGV = 0x1469CEE08

def arguments(args):
    def setup(w):
        pointers = [w.cstr(a) for a in args]
        argv = w.alloc(struct.pack("<" + "Q" * len(pointers), *pointers))
        w.u32(NESTING, 0)
        w.u32(ARGC, len(pointers))
        w.u64(ARGV, argv)
    return setup

def test_reject_signed_high_ascii_key(env):
    # Key_StringToKeynum returns signed -128 for a one-byte 0x80 name.
    # The originals check only !=-1, then index playerKeys[-128].
    commands = (
        ("Iw6SecureBind", [b"bind", bytes([0x80]), b"+attack"]),
        ("Iw6SecureUnbind", [b"unbind", bytes([0x80])]),
        ("Iw6SecureSwapBind", [b"swapbind", bytes([0x80]), b"a"]),
    )
    for export, args in commands:
        touched = []
        def reject(mu):
            touched.append(True)
            raise AssertionError("invalid key reached a binding accessor")
        # The original call targets are pinned in src/client/cl_keys.cpp.
        _, _, _, _ = env.call(export, [], setup=arguments(args), fakes={
            0x1400AD440: reject,  # Key_SetBinding
            0x1400ACFE0: reject,  # Key_GetBinding
        })
        assert not touched, export

def test_reject_unbound_sentinel(env):
    # Check the ordinary -1 rejection path, which must remain unchanged.
    for export, args in (
        ("Iw6SecureBind", [b"bind", b"unknown_key_name", b"+attack"]),
        ("Iw6SecureUnbind", [b"unbind", b"unknown_key_name"]),
    ):
        env.call(export, [], setup=arguments(args))
