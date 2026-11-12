"""S17/B0009: high-bit key names must never index before playerKeys."""
import struct

# The pinned Store cmd_args global used by enhanced bindings and the game.
# See docs/direct-connect.md and tests/direct/game.py. The older
# 0x1469CEDA0 triplet belongs to a different argument buffer and made the
# previous negative-only test pass vacuously without invoking the bind code.
NESTING = 0x1469CECF0
ARGC = 0x1469CED34
ARGV = 0x1469CED58

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
        # Use the Store Key_SetBinding match, not the PS4 server reference VA.
        # Also intercept the enhanced replacement itself to catch accidental
        # negative-index dispatch through source-linked calls.
        _, _, _, _ = env.call(export, [], setup=arguments(args), fakes={
            0x140310B30: reject,  # Store original Key_SetBinding
            "?Key_SetBinding@@YAXW4LocalClientNum_t@@HH@Z": reject,
            "?Key_GetBinding@@YAHW4LocalClientNum_t@@H@Z": reject
        })
        assert not touched, export

def test_reject_unbound_sentinel(env):
    # Check the ordinary -1 rejection path, which must remain unchanged.
    for export, args in (
        ("Iw6SecureBind", [b"bind", b"unknown_key_name", b"+attack"]),
        ("Iw6SecureUnbind", [b"unbind", b"unknown_key_name"]),
    ):
        env.call(export, [], setup=arguments(args))

def test_normal_unbind_reaches_binding_write(env):
    # The negative tests are meaningful only if ordinary commands actually
    # read the constructed cmd_args and reach their intended handler.
    calls = []
    def binding(mu):
        from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8
        calls.append(tuple(mu.reg_read(r) for r in
                           (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8)))
    env.call("Iw6SecureUnbind", [], setup=arguments([b"unbind", b"a"]),
             fakes={0x140310B30: binding,
                    "?Key_SetBinding@@YAXW4LocalClientNum_t@@HH@Z": binding})
    assert calls == [(0, ord("a"), 0)], calls

def test_normal_bind_uses_store_name_table(env):
    # Real Windows regression: a source-linked PS4 Key_GetBindingForCmd
    # dereferenced the unresolved address 0x200000000, causing a native
    # 0xc0000005 before menu initialization. The enhanced adapter must
    # route the read-only name lookup to the pinned original Store helper
    # at 0x140310810 instead, retaining bounds checks around setters.
    from unicorn.x86_const import (
        UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8
    )
    looked_up, writes = [], []
    def lookup(mu):
        looked_up.append(mu.reg_read(UC_X86_REG_RCX))
        mu.reg_write(UC_X86_REG_RAX, 7)
    def write(mu):
        writes.append(tuple(mu.reg_read(r) for r in
                            (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8)))
    result = env.call(
        "Iw6SecureBind", [],
        setup=arguments([b"bind", b"a", b"+attack"]),
        fakes={
            0x140310810: lookup,  # matched Store name table, not PS4 reconstruction
            0x140310B30: write,
            "?Key_SetBinding@@YAXW4LocalClientNum_t@@HH@Z": write,
        },
    )
    assert not (isinstance(result[0], str) and result[0].startswith("fault")), result
    assert looked_up, "did not use the original Store binding-name lookup"
    assert writes == [(0, ord("a"), 7)], writes
