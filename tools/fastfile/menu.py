#!/usr/bin/env python3
"""Menus in Call of Duty: Ghosts PC zones (Microsoft Store build): MenuList (asset type 0x1E, "menufile") and
menuDef_t (0x1F, "menu"), the old menu system (windows, items, event scripts and expressions) that a few zones
still carry next to the Lua UI.

1. Loaders, the Store build's statement for statement: Load_MenuListPtr (140354980) and Load_MenuList (140354870),
   Load_menuDef_ptr (140361710), Load_menuDef_t (140361800) and the functions under them (listed at each).
   tests/fastfile/zone_check.py checks them against the game. The matcher's names for most of these Store
   addresses are shifted by one or more functions; the names here are by structure (records/names.tsv).
2. A reader: read_menu_list and read_menu (names, windows, items with their types and texts, the event scripts).

    python3 tools/fastfile/menu.py <zone.ff>        # every menu file, its menus and items

docs/assets/menus.md has the format.
"""
from __future__ import annotations

import struct

import iw6ff

BLOCK_VIRTUAL = 3
ASSET_MENUFILE, ASSET_MENU = 0x1E, 0x1F
HOOKS = {"material_ptr": None, "snd_alias_list_ptr": None}
WINDOW_SIZE = 0xB0


def _h(name):
    fn = HOOKS[name]
    if fn is None:
        raise NotImplementedError(f"menu.HOOKS[{name!r}] is not set (register() sets it)")
    return fn


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _follow(s, at, align):
    """A pointer whose data follows whenever it is set (no test for -1): point it at the stream, aligned."""
    if not s.u64(at):
        return 0
    p = s.align(align)
    s.put_u64(at, p)
    return p


def _inline_or_offset(s, at, align):
    """-1: the data follows (aligned); another non-zero value is an offset (DB_ConvertOffsetToPointer)."""
    v = s.u64(at)
    if not v:
        return 0
    if v == iw6ff.PTR_INLINE:
        p = s.align(align)
        s.put_u64(at, p)
        return p
    s.put_u64(at, s.offset_to_pointer(v))
    return 0


def _xstring(s, at):
    s.load(False, at, 8)
    s.xstring_ptr(at)


def load_xstring_array(s, at, count, at_stream_start):
    """14035E9C0 (Load_XStringArray): count XString pointers."""
    s.load(at_stream_start, at, 8 * count)
    for i in range(count):
        _xstring(s, at + 8 * i)


# ==== expressions =================================================================================================

def load_statement_ptr(s, at, at_stream_start=False):
    """140357650 (Load_StatementPtr): -1: a Statement_s follows, aligned 4."""
    s.load(at_stream_start, at, 8)
    p = _inline_or_offset(s, at, 4)
    if p:
        load_statement(s, p, True)


def load_statement(s, st, at_stream_start=True):
    """140357510 (Load_Statement): 0x70 bytes: numEntries (+0) entries of 0x10 (+8, any non-null value, aligned 4),
    each with a non-zero +0xC an operand (0xC bytes): +8 = 2 a string (14034CC60), 3 a nested statement; then the
    supporting data (+0x10)."""
    s.load(at_stream_start, st, 0x70)
    p = _follow(s, st + 8, 4)
    if p:
        n = _i32(s, st)
        s.load(True, p, n * 0x10)
        for i in range(n):
            e = p + 0x10 * i
            s.load(False, e, 0x10)
            if _i32(s, e + 0xC):
                s.load(False, e, 0xC)
                kind = s.u32(e + 8)
                if kind == 2:
                    s.load(False, e, 8)                  # 14034CC60
                    _xstring(s, e)
                elif kind == 3:
                    load_statement_ptr(s, e, False)
    load_supporting_data_ptr(s, st + 0x10, False)


def load_supporting_data_ptr(s, at, at_stream_start=False):
    """14034CDA0 (Load_ExpressionSupportingDataPtr): -1: 0x30 bytes follow (aligned 4, 14034CCE0): the UI
    functions (+0, 1403586C0), static dvars (+0x10, 140357750) and a string list (+0x20)."""
    s.load(at_stream_start, at, 8)
    e = _inline_or_offset(s, at, 4)
    if not e:
        return
    s.load(True, e, 0x30)
    # UIFunctionList: count (+0), statements (+8, any non-null value: aligned 8)
    s.load(False, e, 0x10)
    p = _follow(s, e + 8, 8)
    if p:
        n = _i32(s, e)
        s.load(True, p, 8 * n)
        for i in range(n):
            load_statement_ptr(s, p + 8 * i, False)
    # StaticDvarList: count (+0x10), StaticDvar pointers (+0x18), each 0x10 bytes with the dvar's name at +8
    s.load(False, e + 0x10, 0x10)
    p = _follow(s, e + 0x18, 8)
    if p:
        n = _i32(s, e + 0x10)
        s.load(True, p, 8 * n)
        for i in range(n):
            slot = p + 8 * i
            s.load(False, slot, 8)
            d = _follow(s, slot, 4)
            if d:
                s.load(True, d, 0x10)                    # 1403576D0
                _xstring(s, d + 8)
    # StringList: count (+0x20), strings (+0x28)
    s.load(False, e + 0x20, 0x10)
    p = _follow(s, e + 0x28, 8)
    if p:
        load_xstring_array(s, p, _i32(s, e + 0x20), True)


# ==== event handlers ==============================================================================================

def load_handler_set_ptr(s, at, at_stream_start=False):
    """140354810 (Load_MenuEventHandlerSetPtr): any non-null value: a MenuEventHandlerSet follows (aligned 4)."""
    s.load(at_stream_start, at, 8)
    p = _follow(s, at, 4)
    if p:
        load_handler_set(s, p, True)


def load_handler_set(s, h, at_stream_start=True):
    """140354640 (Load_MenuEventHandlerSet): 0x10 bytes: eventHandlerCount (+0) handler pointers (+8, aligned 8),
    each 0x10 bytes (aligned 4): +8 the kind: 0 an unconditional script (a string), 1 a conditional script
    (14034C030), 2 an else script (a nested set), 3..6 a local variable set (140356CE0)."""
    s.load(at_stream_start, h, 0x10)
    p = _follow(s, h + 8, 8)
    if not p:
        return
    n = _i32(s, h)
    s.load(True, p, 8 * n)
    for i in range(n):
        slot = p + 8 * i
        s.load(False, slot, 8)
        e = _follow(s, slot, 4)
        if not e:
            continue
        s.load(True, e, 0x10)
        kind = s.read(e + 8, 1)[0]
        if kind == 0:
            _xstring(s, e)
        elif kind == 1:
            s.load(False, e, 8)                          # 14034C030 (Load_ConditionalScriptPtr)
            c = _follow(s, e, 4)
            if c:
                s.load(True, c, 0x10)
                load_statement_ptr(s, c + 8, False)
                load_handler_set_ptr(s, c, False)
        elif kind == 2:
            load_handler_set_ptr(s, e, False)
        elif 3 <= kind <= 6:
            s.load(False, e, 8)                          # 140356CE0 (Load_SetLocalVarDataPtr)
            v = _follow(s, e, 4)
            if v:
                s.load(True, v, 0x10)                    # 140356C50
                _xstring(s, v)
                load_statement_ptr(s, v + 8, False)


def load_key_handlers(s, k, at_stream_start=True):
    """1403521A0 (Load_ItemKeyHandler): a linked list of 0x18 bytes: the actions (+8, an event handler set) and the
    next one (+0x10, aligned 4)."""
    while True:
        s.load(at_stream_start, k, 0x18)
        load_handler_set_ptr(s, k + 8, False)
        nxt = _follow(s, k + 0x10, 4)
        if not nxt:
            return
        at_stream_start, k = True, nxt


# ==== windows, items, menus =======================================================================================

def load_window(s, w, at_stream_start=False):
    """140362620 (Load_windowDef_t): 0xB0 bytes: name (+0), group (+0x30), background material (+0xA8)."""
    s.load(at_stream_start, w, WINDOW_SIZE)
    _xstring(s, w)
    _xstring(s, w + 0x30)
    _h("material_ptr")(s, w + 0xA8)


ITEM_TYPE_LISTBOX, ITEM_TYPE_MULTI, ITEM_TYPE_DVARENUM, ITEM_TYPE_NEWS_TICKER, ITEM_TYPE_TEXT_SCROLL = 6, 0xC, 0xD, 0x14, 0x15
EDIT_FIELD_TYPES = 0xC74E11                             # bit per item type below 0x18


def load_item_data(s, at, item_type):
    """1403608B0 (Load_itemDefData_t): by the item's type (+0xC4): a list box (0x1D8 bytes, 1403612A0), an edit field
    (0x20), a multi (0x288: two arrays of 32 strings), the dvar enum's name, a news ticker (0xC), a text scroll (4).
    Any non-null value: the data follows, aligned 4."""
    if item_type == ITEM_TYPE_LISTBOX:
        s.load(False, at, 8)
        p = _follow(s, at, 4)
        if p:
            s.load(True, p, 0x1D8)
            load_handler_set_ptr(s, p + 0x1A0, False)
            _h("material_ptr")(s, p + 0x1C8)
            load_statement_ptr(s, p + 0x1D0, False)
    elif item_type < 0x18 and (EDIT_FIELD_TYPES >> item_type) & 1:
        s.load(False, at, 8)
        p = _follow(s, at, 4)
        if p:
            s.load(True, p, 0x20)
    elif item_type == ITEM_TYPE_MULTI:
        s.load(False, at, 8)
        p = _follow(s, at, 4)
        if p:
            s.load(True, p, 0x288)
            load_xstring_array(s, p, 0x20, False)
            load_xstring_array(s, p + 0x100, 0x20, False)
    elif item_type == ITEM_TYPE_DVARENUM:
        _xstring(s, at)
    elif item_type in (ITEM_TYPE_NEWS_TICKER, ITEM_TYPE_TEXT_SCROLL):
        s.load(False, at, 8)
        p = _follow(s, at, 4)
        if p:
            s.load(True, p, 0xC if item_type == ITEM_TYPE_NEWS_TICKER else 4)


ITEM_HANDLERS = range(0x108, 0x150, 8)                   # mouseEnterText .. accept: nine event handler sets
ITEM_STATEMENTS = (0x1A8, 0x1B0, 0x1B8, 0x1C0, 0x1F0)    # visibleExp, disabledExp, textExp, materialExp, ...


def load_item(s, it, at_stream_start=True):
    """140360960 (Load_itemDef_t): 0x1F8 bytes: the window (+0), text (+0xF0), nine event handler sets
    (+0x108..+0x148), two strings (+0x150, +0x158), key handlers (+0x160), two strings (+0x168, +0x170), a sound
    alias list (+0x180, loaded whole), the type's data (+0x190), float expressions (+0x1A0, count +0x198, 0x10
    each with a statement at +8) and five statements."""
    s.load(at_stream_start, it, 0x1F8)
    s.load(False, it, WINDOW_SIZE)
    load_window(s, it, False)
    _xstring(s, it + 0xF0)
    for off in ITEM_HANDLERS:
        load_handler_set_ptr(s, it + off, False)
    _xstring(s, it + 0x150)
    _xstring(s, it + 0x158)
    k = _follow(s, it + 0x160, 4)
    if k:
        load_key_handlers(s, k, True)
    _xstring(s, it + 0x168)
    _xstring(s, it + 0x170)
    _h("snd_alias_list_ptr")(s, it + 0x180)
    load_item_data(s, it + 0x190, s.u32(it + 0xC4))
    p = _follow(s, it + 0x1A0, 4)
    if p:
        n = _i32(s, it + 0x198)
        s.load(True, p, 0x10 * n)
        for i in range(n):
            e = p + 0x10 * i
            s.load(False, e, 0x10)
            load_statement_ptr(s, e + 8, False)
    for off in ITEM_STATEMENTS:
        load_statement_ptr(s, it + off, False)


MENU_HANDLERS = (0x18, 0x28, 0x20, 0x30, 0x38)           # in the Store build's order
MENU_STATEMENTS = range(0x70, 0xA8, 8)


def load_menu_data(s, d, at_stream_start=True):
    """140361350 (Load_menuData_t): 0x120 bytes: the supporting data (+0x110), five event handler sets, key
    handlers (+0x40), a statement (+0x48), two strings (+0x50, +0x58) and seven statements (+0x70..+0xA0)."""
    s.load(at_stream_start, d, 0x120)
    load_supporting_data_ptr(s, d + 0x110, False)
    for off in MENU_HANDLERS:
        load_handler_set_ptr(s, d + off, False)
    k = _follow(s, d + 0x40, 4)
    if k:
        load_key_handlers(s, k, True)
    load_statement_ptr(s, d + 0x48, False)
    _xstring(s, d + 0x50)
    _xstring(s, d + 0x58)
    for off in MENU_STATEMENTS:
        load_statement_ptr(s, d + off, False)


def load_menu(s, m, at_stream_start=True):
    """140361800 (Load_menuDef_t): 0xC8 bytes, in the virtual block: the menu data (+0, aligned 4), the window (+8),
    and itemCount (+0xB8) item pointers (+0xC0, aligned 8), each item aligned 4."""
    s.load(at_stream_start, m, 0xC8)
    s.push(BLOCK_VIRTUAL)
    d = _follow(s, m, 4)
    if d:
        load_menu_data(s, d, True)
    s.load(False, m + 8, WINDOW_SIZE)
    load_window(s, m + 8, False)
    p = _follow(s, m + 0xC0, 8)
    if p:
        n = _i32(s, m + 0xB8)
        s.load(True, p, 8 * n)
        for i in range(n):
            slot = p + 8 * i
            s.load(False, slot, 8)
            it = _follow(s, slot, 4)
            if it:
                load_item(s, it, True)
    s.pop()


def load_menu_ptr(s, varptr):
    """140361710 (Load_menuDef_ptr): the asset pointer rule (iw6ff.asset_ptr), with Load_MenuAsset's (140372E50)
    fix-up after linking: every item's parent (+0x100) becomes the linked menu."""
    s.push(iw6ff.XFILE_BLOCK_TEMP)
    v = s.u64(varptr)
    if v:
        if v not in (iw6ff.PTR_INLINE, iw6ff.PTR_INSERT):
            s.put_u64(varptr, s.offset_to_alias(v))
        else:
            h = s.align(4)
            s.put_u64(varptr, h)
            slot = s.insert_pointer() if v == iw6ff.PTR_INSERT else None
            load_menu(s, h, True)
            linked = s.link(ASSET_MENU, h)
            s.put_u64(varptr, linked)
            items = s.u64(h + 0xC0)
            for i in range(max(_i32(s, h + 0xB8), 0)):
                s.put_u64(s.u64(items + 8 * i) + 0x100, linked)
            if slot is not None:
                s.put_u64(slot, s.u64(varptr))
    s.pop()


def load_menu_list(s, h, at_stream_start=True):
    """140354870 (Load_MenuList): 0x18 bytes, in the virtual block: name, menuCount (+8) menu pointers (+0x10, any
    non-null value: aligned 8), each a Load_menuDef_ptr."""
    s.load(at_stream_start, h, 0x18)
    s.push(BLOCK_VIRTUAL)
    _xstring(s, h)
    p = _follow(s, h + 0x10, 8)
    if p:
        n = _i32(s, h + 8)
        s.load(True, p, 8 * n)
        for i in range(n):
            load_menu_ptr(s, p + 8 * i)
    s.pop()


load_menu_list_ptr = iw6ff.asset_ptr(ASSET_MENUFILE, lambda s, h: load_menu_list(s, h, True))  # 140354980


def register(asset_loaders: dict, material_ptr=None, snd_alias_list_ptr=None):
    asset_loaders[ASSET_MENUFILE] = load_menu_list_ptr
    asset_loaders[ASSET_MENU] = load_menu_ptr
    if material_ptr is not None:
        HOOKS["material_ptr"] = material_ptr
    if snd_alias_list_ptr is not None:
        HOOKS["snd_alias_list_ptr"] = snd_alias_list_ptr


# ==== 2. reader ===================================================================================================

def _cstr(mem, a):
    if not a:
        return None
    out = bytearray()
    while True:
        chunk = mem.read(a + len(out), 64)
        i = chunk.find(b"\0")
        if i >= 0:
            return (out + chunk[:i]).decode("latin1")
        out += chunk


def _q(mem, a):
    return struct.unpack("<Q", mem.read(a, 8))[0]


def read_window(mem, w):
    rect = struct.unpack("<4f", mem.read(w + 8, 16))
    return {"name": _cstr(mem, _q(mem, w)), "group": _cstr(mem, _q(mem, w + 0x30)), "rect": rect}


def read_handler_set(mem, h, depth=0):
    """The scripts of an event handler set: strings for plain scripts, nested lists for conditions and else."""
    if not h or depth > 8:
        return []
    n = struct.unpack("<i", mem.read(h, 4))[0]
    p = _q(mem, h + 8)
    out = []
    for i in range(n if p else 0):
        e = _q(mem, p + 8 * i)
        if not e:
            continue
        kind = mem.read(e + 8, 1)[0]
        if kind == 0:
            out.append(_cstr(mem, _q(mem, e)))
        elif kind == 1:
            c = _q(mem, e)
            out.append({"if": "<expression>", "then": read_handler_set(mem, _q(mem, c), depth + 1) if c else []})
        elif kind == 2:
            out.append({"else": read_handler_set(mem, _q(mem, e), depth + 1)})
        else:
            v = _q(mem, e)
            out.append({"set": _cstr(mem, _q(mem, v)) if v else None, "kind": kind})
    return out


def read_item(mem, it):
    item = read_window(mem, it)
    item["type"] = struct.unpack("<i", mem.read(it + 0xC4, 4))[0]
    item["text"] = _cstr(mem, _q(mem, it + 0xF0))
    item["action"] = read_handler_set(mem, _q(mem, it + 0x128))
    return item


def read_menu(mem, m):
    menu = read_window(mem, m + 8)
    n = struct.unpack("<i", mem.read(m + 0xB8, 4))[0]
    items = _q(mem, m + 0xC0)
    menu["items"] = [read_item(mem, _q(mem, items + 8 * i)) for i in range(n if items else 0) if _q(mem, items + 8 * i)]
    d = _q(mem, m)
    menu["onOpen"] = read_handler_set(mem, _q(mem, d + 0x18)) if d else []
    return menu


def read_menu_list(mem, h):
    n = struct.unpack("<i", mem.read(h + 8, 4))[0]
    p = _q(mem, h + 0x10)
    return {"name": _cstr(mem, _q(mem, h)),
            "menus": [read_menu(mem, _q(mem, p + 8 * i)) for i in range(n if p else 0) if _q(mem, p + 8 * i)]}


def main(argv=None) -> int:
    import argparse
    import json
    import os
    import sys
    ap = argparse.ArgumentParser(description="Print a Ghosts PC zone's menu files.")
    ap.add_argument("fastfile")
    ap.add_argument("--json", action="store_true")
    opts = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loaders
    loaders.register_all()
    with open(opts.fastfile, "rb") as f:
        zone = iw6ff.read_fastfile(f.read(), os.path.basename(opts.fastfile).rsplit(".", 1)[0])
    if not zone.complete:
        print(f"the reader stopped at asset {zone.stopped_at} (type {zone.assets[zone.stopped_at].type:#x})")
    lists = [read_menu_list(zone.stream, a.header) for a in zone.assets if a.type == ASSET_MENUFILE and a.header]
    if opts.json:
        print(json.dumps(lists, indent=1))
        return 0
    for ml in lists:
        print(ml["name"])
        for m in ml["menus"]:
            print(f"  menu {m['name']}: {len(m['items'])} items")
            for it in m["items"]:
                print(f"    {it['name'] or '-'} (type {it['type']}) {it['text'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
