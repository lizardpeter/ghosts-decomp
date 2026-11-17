"""Differential cases for src/ui/ui_menu_load_db.cpp (menu files, menus, items, event handlers, expressions) against
the Store build.

Each loader runs on random structures with dbstream.py's logged stream fakes and a logged fake for every other loader
it calls (the asset linkers, Load_MaterialHandle and Load_snd_alias_list_ptr included). Pointers are null, inline,
insert or an offset; counts are 0, 1 or a few. The zone bytes are laid out in the order each loader reads them: its
inlined arrays and elements, and each inline XString as the fake reads it (a length byte and the letters); loaders
that are fakes read nothing. tools/fastfile/menu.py is the same logic, checked against the game on real zones
(docs/assets/menus.md).
"""
import random
import struct

import dbstream as ds
from dbstream import FOLLOWING, INSERT, OFF_STRUCT
from harness import HEAP
from syms import va

STORE = "iw6mp64_MSStore_ship"
M64 = 2 ** 64 - 1


def _rec(name, spec, *globals_):
    return ds.recorder(name, spec, globals_)


def _bool_loader(name, *globals_):
    return (f"?{name}@@YAX_N@Z", _rec(name, "b", *globals_, "g_streamPos"))


FAKES = dict([
    *ds.STREAM_FAKES.items(),
    ("?Load_MenuAsset@@YAXPEAPEAUmenuDef_t@@@Z", ds.asset_linker("Load_MenuAsset")),
    ("?Load_MenuListAsset@@YAXPEAPEAUMenuList@@@Z", ds.asset_linker("Load_MenuListAsset")),
    ("?Load_XStringArray@@YAX_N_K@Z", _rec("Load_XStringArray", "bq", "varXString", "g_streamPos")),
    _bool_loader("Load_MaterialHandle", "varMaterialHandle"),
    _bool_loader("Load_snd_alias_list_ptr", "varsnd_alias_list_ptr"),
    _bool_loader("Load_XString", "varXString"),
    _bool_loader("Load_ExpressionString", "varExpressionString"),
    _bool_loader("Load_StatementPtr", "varStatementPtr"),
    _bool_loader("Load_Statement", "varStatement"),
    _bool_loader("Load_ExpressionSupportingDataPtr", "varExpressionSupportingDataPtr"),
    _bool_loader("Load_ExpressionSupportingData", "varExpressionSupportingData"),
    _bool_loader("Load_UIFunctionList", "varUIFunctionList"),
    _bool_loader("Load_StaticDvarList", "varStaticDvarList"),
    _bool_loader("Load_StaticDvar", "varStaticDvar"),
    _bool_loader("Load_MenuEventHandlerSet", "varMenuEventHandlerSet"),
    _bool_loader("Load_MenuEventHandlerSetPtr", "varMenuEventHandlerSetPtr"),
    _bool_loader("Load_ConditionalScriptPtr", "varConditionalScriptPtr"),
    _bool_loader("Load_SetLocalVarData", "varSetLocalVarData"),
    _bool_loader("Load_SetLocalVarDataPtr", "varSetLocalVarDataPtr"),
    _bool_loader("Load_ItemKeyHandler", "varItemKeyHandler"),
    _bool_loader("Load_windowDef_t", "varwindowDef_t"),
    _bool_loader("Load_listBoxDef_t", "varlistBoxDef_t"),
    _bool_loader("Load_listBoxDef_ptr", "varlistBoxDef_ptr"),
    _bool_loader("Load_editFieldDef_ptr", "vareditFieldDef_ptr"),
    _bool_loader("Load_multiDef_ptr", "varmultiDef_ptr"),
    _bool_loader("Load_newsTickerDef_ptr", "varnewsTickerDef_ptr"),
    _bool_loader("Load_textScrollDef_ptr", "vartextScrollDef_ptr"),
    _bool_loader("Load_itemDefData_t", "varitemDefData_t", "varitemDef_t"),
    _bool_loader("Load_itemDef_t", "varitemDef_t"),
    _bool_loader("Load_menuData_t", "varmenuData_t"),
    _bool_loader("Load_menuDef_t", "varmenuDef_t"),
    _bool_loader("Load_menuDef_ptr", "varmenuDef_ptr"),
    _bool_loader("Load_MenuList", "varMenuList"),
])


def case(symbol, seed, make, n=200, fakes=None):
    rnd = random.Random(seed)
    f = {k: v for k, v in FAKES.items() if k != symbol}
    f.update(fakes or {})
    return {"symbol": symbol, "build": STORE, "ret": "void", "fakes": f, "inputs": [make(rnd) for _ in range(n)]}


def _q(b, off, v):
    struct.pack_into("<Q", b, off, v & M64)


def _gq(b, off):
    return struct.unpack_from("<Q", b, off)[0]


def _nonnull(r, null=0.3):
    return 0 if r.random() < null else r.choice([FOLLOWING, r.getrandbits(64) | 1])


def _xs(r, value):
    """The zone bytes the XString fake reads for a field holding `value`."""
    if value != FOLLOWING:
        return b""
    n = r.randrange(24)
    return bytes([n]) + r.randbytes(n)


def _small(r, top=3):
    return r.choice([0, 1, r.randint(0, top), top])


def _input(r, struct_bytes, feed, var, aux=None, aux_var=None, extra_args=()):
    """`struct_bytes` at OFF_STRUCT with `var` pointing at it (`aux` at OFF_AUX for `aux_var`); the zone is the
    structure when the loader is called with atStreamStart, then `feed`."""
    flag = r.random() < 0.5
    buf = bytearray(r.randbytes(ds.BUF_SIZE))
    buf[OFF_STRUCT:OFF_STRUCT + len(struct_bytes)] = struct_bytes
    if aux is not None:
        buf[ds.OFF_AUX:ds.OFF_AUX + len(aux)] = aux
    zone = ds.Zone(r, (bytes(struct_bytes) if flag else b"") + bytes(feed) + r.randbytes(0x80))

    def setup(w):
        zone.start(w)
        w.u64(va(var), HEAP + OFF_STRUCT)
        if aux_var:
            w.u64(va(aux_var), HEAP + ds.OFF_AUX)
    return {"args": [flag, *extra_args, bytes(buf)], "setup": setup}


def _make(size, fill, var, **kw):
    """A loader input: `fill(r, b)` sets the fields of `size` random bytes and returns the zone bytes after them."""
    def make(r):
        b = bytearray(r.randbytes(size))
        feed = fill(r, b)
        return _input(r, b, feed, var, **kw)
    return make


# ---- strings and simple pointers ----

def _string_fields(*offsets):
    def fill(r, b):
        feed = b""
        for off in offsets:
            _q(b, off, ds.pointer(r))
            feed += _xs(r, _gq(b, off))
        return feed
    return fill


def _xstring_array(r):
    count = _small(r, 5)
    ptrs = [ds.pointer(r) & M64 for _ in range(count)]
    data = b"".join(struct.pack("<Q", p) for p in ptrs)
    return _input(r, data, b"".join(_xs(r, p) for p in ptrs), "varXString", extra_args=(count,))


def _ptr(*, inline_size=0, tested=False):
    """A pointer to something: FOLLOWING/any value. With inline_size, the pointed-to bytes follow in the zone."""
    def fill(r, b):
        _q(b, 0, ds.pointer(r) if tested else _nonnull(r))
        return r.randbytes(inline_size) if inline_size and _gq(b, 0) else b""
    return fill


def _multi_ptr(r, b):
    _q(b, 0, _nonnull(r))
    if not _gq(b, 0):
        return b""
    m = bytearray(r.randbytes(0x288))
    for i in range(64):
        _q(m, 8 * i, ds.pointer(r))
    return bytes(m)


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


# ---- expressions ----

def _statement(r, b):
    struct.pack_into("<i", b, 0, _small(r, 4))
    _q(b, 8, _nonnull(r))
    _q(b, 0x10, ds.pointer(r))
    if not _gq(b, 8):
        return b""
    out = b""
    for _ in range(struct.unpack_from("<i", b, 0)[0]):
        e = bytearray(r.randbytes(0x10))
        _q(e, 0, ds.pointer(r))
        struct.pack_into("<I", e, 8, r.choice([0, 1, 2, 2, 3, 3, 4, r.getrandbits(32)]))
        struct.pack_into("<i", e, 0xC, r.choice([0, 0, 1, r.getrandbits(32) - (1 << 31)]))
        out += e
    return out


def _counted_slots(count_off, ptr_off, top=4, slot=lambda r: _nonnull(r) & M64):
    def fill(r, b):
        n = _small(r, top)
        struct.pack_into("<i", b, count_off, n)
        _q(b, ptr_off, _nonnull(r))
        return b"".join(struct.pack("<Q", slot(r)) for _ in range(n)) if _gq(b, ptr_off) else b""
    return fill


def _supporting(r, b):
    struct.pack_into("<i", b, 0x20, r.choice([_small(r, 5), -1, -3]))   # the count is sign-extended
    _q(b, 0x28, _nonnull(r))
    return b""


# ---- event handlers ----

def _handler_set(r, b):
    n = _small(r, 4)
    struct.pack_into("<i", b, 0, n)
    _q(b, 8, _nonnull(r))
    if not _gq(b, 8):
        return b""
    slots = [_nonnull(r) for _ in range(n)]
    out = b"".join(struct.pack("<Q", s & M64) for s in slots)
    for s in slots:
        if s:
            h = bytearray(r.randbytes(0x10))
            _q(h, 0, ds.pointer(r))
            h[8] = r.choice([0, 0, 1, 2, 3, 4, 5, 6, 7, r.getrandbits(8)])
            out += bytes(h) + (_xs(r, _gq(h, 0)) if h[8] == 0 else b"")
    return out


def _key_handler(r, b):
    out = b""
    node, depth = b, 0
    while True:
        _q(node, 8, _nonnull(r))
        depth += 1
        _q(node, 0x10, _nonnull(r) if depth < 4 else 0)
        if node is not b:
            out += bytes(node)
        if not _gq(node, 0x10):
            return out
        node = bytearray(r.randbytes(0x18))


# ---- items and menus ----

def _item_data(r):
    item = bytearray(r.randbytes(0x1F8))
    struct.pack_into("<i", item, 0xC4, r.choice([6, 0xC, 0xD, 0x14, 0x15, 0, 4, 9, 0x17, 0x18, 0x1F, r.randint(0, 0x20),
                                                 r.getrandbits(32) - (1 << 31)]))
    return _input(r, r.randbytes(8), b"", "varitemDefData_t", aux=item, aux_var="varitemDef_t")


ITEM_SETS = range(0x108, 0x150, 8)
ITEM_STRINGS = (0xF0, 0x150, 0x158, 0x168, 0x170)


def _item(r, b):
    for off in ITEM_SETS:
        _q(b, off, _nonnull(r))
    _q(b, 0x160, _nonnull(r))
    feed = b""
    for off in ITEM_STRINGS:
        _q(b, off, ds.pointer(r))
        feed += _xs(r, _gq(b, off))
    n = _small(r, 3)
    struct.pack_into("<i", b, 0x198, n)
    _q(b, 0x1A0, _nonnull(r))
    if _gq(b, 0x1A0):
        for _ in range(n):
            e = bytearray(r.randbytes(0x10))
            _q(e, 8, ds.pointer(r))
            feed += e
    for off in (0x1A8, 0x1B0, 0x1B8, 0x1C0, 0x1F0):
        _q(b, off, ds.pointer(r))
    return feed


def _menu_data(r, b):
    for off in (0x18, 0x20, 0x28, 0x30, 0x38, 0x40):
        _q(b, off, _nonnull(r))
    feed = b""
    for off in (0x50, 0x58):
        _q(b, off, ds.pointer(r))
        feed += _xs(r, _gq(b, off))
    return feed


def _menu(r, b):
    _q(b, 0, _nonnull(r))
    return _counted_slots(0xB8, 0xC0)(r, b)


def _menu_list(r, b):
    _q(b, 0, ds.pointer(r))
    feed = _xs(r, _gq(b, 0))
    n = _small(r, 4)
    struct.pack_into("<i", b, 8, n)
    _q(b, 0x10, _nonnull(r))
    return feed + (r.randbytes(8 * n) if _gq(b, 0x10) else b"")


def _sym(name):
    return f"?{name}@@YAX_N@Z"


CASES = [
    case(_sym("Load_XString"), 0xE950, _make(8, _string_fields(0), "varXString")),
    case("?Load_XStringArray@@YAX_N_K@Z", 0xE9C0, _xstring_array),
    case(_sym("Load_ExpressionString"), 0xCC60, _make(8, _string_fields(0), "varExpressionString")),
    case(_sym("Load_StatementPtr"), 0x7650, _make(8, _ptr(tested=True), "varStatementPtr")),
    case(_sym("Load_Statement"), 0x7510, _make(0x70, _statement, "varStatement")),
    case(_sym("Load_ExpressionSupportingDataPtr"), 0xCDA0, _make(8, _ptr(tested=True), "varExpressionSupportingDataPtr")),
    case(_sym("Load_ExpressionSupportingData"), 0xCCE0, _make(0x30, _supporting, "varExpressionSupportingData")),
    case(_sym("Load_UIFunctionList"), 0x86C0, _make(0x10, _counted_slots(0, 8, slot=lambda r: ds.pointer(r)),
                                                  "varUIFunctionList")),
    case(_sym("Load_StaticDvar"), 0x76D0, _make(0x10, _string_fields(8), "varStaticDvar")),
    # Load_StaticDvar's fake leaves g_streamPos 4-aligned, so the next StaticDvar's alignment (4) shows
    case(_sym("Load_StaticDvarList"), 0x7750, _make(0x10, _counted_slots(0, 8), "varStaticDvarList"),
         fakes={_sym("Load_StaticDvar"): ds.clobbering(FAKES[_sym("Load_StaticDvar")],
                                                       g_streamPos=HEAP + ds.OFF_STREAM + 0x404)}),
    case(_sym("Load_MenuEventHandlerSet"), 0x4640, _make(0x10, _handler_set, "varMenuEventHandlerSet")),
    case(_sym("Load_MenuEventHandlerSetPtr"), 0x4810, _make(8, _ptr(), "varMenuEventHandlerSetPtr")),
    case(_sym("Load_ConditionalScriptPtr"), 0xC030, _make(8, _ptr(inline_size=0x10), "varConditionalScriptPtr")),
    case(_sym("Load_SetLocalVarData"), 0x6C50, _make(0x10, _string_fields(0), "varSetLocalVarData")),
    case(_sym("Load_SetLocalVarDataPtr"), 0x6CE0, _make(8, _ptr(), "varSetLocalVarDataPtr")),
    case(_sym("Load_ItemKeyHandler"), 0x21A0, _make(0x18, _key_handler, "varItemKeyHandler")),
    case(_sym("Load_windowDef_t"), 0x2620, _make(0xB0, _string_fields(0, 0x30), "varwindowDef_t")),
    case(_sym("Load_listBoxDef_t"), 0x12A0, _make(0x1D8, lambda r, b: _q(b, 0x1A0, _nonnull(r)) or b"",
                                                  "varlistBoxDef_t")),
    case(_sym("Load_listBoxDef_ptr"), 0x1240, _make(8, _ptr(), "varlistBoxDef_ptr")),
    case(_sym("Load_editFieldDef_ptr"), 0x0850, _make(8, _ptr(inline_size=0x20), "vareditFieldDef_ptr")),
    case(_sym("Load_newsTickerDef_ptr"), 0x1A20, _make(8, _ptr(inline_size=0xC), "varnewsTickerDef_ptr")),
    case(_sym("Load_textScrollDef_ptr"), 0x2470, _make(8, _ptr(inline_size=4), "vartextScrollDef_ptr")),
    case(_sym("Load_multiDef_ptr"), 0x1980, _make(8, _multi_ptr, "varmultiDef_ptr")),
    case(_sym("Load_itemDefData_t"), 0x08B0, _item_data),
    case(_sym("Load_itemDef_t"), 0x0960, _make(0x1F8, _item, "varitemDef_t")),
    case(_sym("Load_menuData_t"), 0x1350, _make(0x120, _menu_data, "varmenuData_t")),
    case(_sym("Load_menuDef_t"), 0x1800, _make(0xC8, _menu, "varmenuDef_t")),
    case(_sym("Load_menuDef_ptr"), 0x1710, _handle("varmenuDef_ptr", "varmenuDef_t")),
    case(_sym("Load_MenuList"), 0x4870, _make(0x18, _menu_list, "varMenuList")),
    case(_sym("Load_MenuListPtr"), 0x4980, _handle("varMenuListPtr", "varMenuList")),
]
