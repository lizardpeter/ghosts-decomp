#!/usr/bin/env python3
"""String tables and localized text in Call of Duty: Ghosts PC zones (Microsoft Store build): StringTable (asset
type 0x2E, "stringtable": the game's CSV files, such as mp/camoTable.csv) and LocalizeEntry (0x21, "localize": one
localized string, such as the name a map or weapon shows).

1. Loaders, the Store build's statement for statement: Load_StringTablePtr (140357B00) and Load_StringTable
   (140357980); Load_LocalizeEntryPtr (1403527E0) and Load_LocalizeEntry (1403526F0).
   tests/fastfile/zone_check.py checks them against the game; src/database/db_stringtable_load_db.cpp is the same
   in C++.
2. Readers: read_string_table (a table's rows of cells, with each cell's stored hash checked against
   StringTable_HashString, 140536D10), read_localize (name and text) and the game's lookups
   (StringTable_GetColumnValueForRow 140536B00, StringTable_LookupRowNumForValue 140536C50).

    python3 tools/fastfile/strings.py <zone.ff> --out <folder>    # every table as CSV, the localized text as JSON

docs/assets/strings.md has the format.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import iw6ff

BLOCK_VIRTUAL = 3
ASSET_LOCALIZE, ASSET_STRINGTABLE = 0x21, 0x2E
STRINGTABLE_SIZE, CELL_SIZE, LOCALIZE_SIZE = 0x18, 0x10, 0x10


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


# ==== 1. loaders ===================================================================================================

def load_string_table(s, h: int, at_stream_start: bool = True):
    """140357980 (Load_StringTable): 0x18 bytes, in the virtual block: name (+0); values (+0x10, any non-null value:
    columnCount (+8) x rowCount (+0xC) cells of 0x10, aligned 4), each cell's string (+0) an XString; the hash
    (+8) stays as stored."""
    s.load(at_stream_start, h, STRINGTABLE_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    if s.u64(h + 0x10):
        p = s.align(4)
        s.put_u64(h + 0x10, p)
        n = (_i32(s, h + 0xC) * _i32(s, h + 8)) & 0xFFFFFFFF   # an int product, sign-extended
        n = n - (1 << 32) if n & 0x80000000 else n
        s.load(True, p, n * CELL_SIZE)
        for i in range(n):
            s.load(False, p + CELL_SIZE * i, CELL_SIZE)
            s.xstring_ptr(p + CELL_SIZE * i)
    s.pop()


def load_localize(s, h: int, at_stream_start: bool = True):
    """1403526F0 (Load_LocalizeEntry): 0x10 bytes, in the virtual block: value (+0) and name (+8), XStrings."""
    s.load(at_stream_start, h, LOCALIZE_SIZE)
    s.push(BLOCK_VIRTUAL)
    s.xstring_ptr(h)
    s.xstring_ptr(h + 8)
    s.pop()


load_string_table_ptr = iw6ff.asset_ptr(ASSET_STRINGTABLE, lambda s, h: load_string_table(s, h, True))  # 140357B00
load_localize_ptr = iw6ff.asset_ptr(ASSET_LOCALIZE, lambda s, h: load_localize(s, h, True))            # 1403527E0


def register(asset_loaders: dict):
    asset_loaders[ASSET_STRINGTABLE] = load_string_table_ptr
    asset_loaders[ASSET_LOCALIZE] = load_localize_ptr


# ==== 2. readers ===================================================================================================

def string_hash(text: bytes | str) -> int:
    """StringTable_HashString (140536D10): h = h * 31 + tolower(c) over the bytes, in 32-bit signed arithmetic. The
    bytes are signed chars: one from 0x80 adds a negative value (tolower leaves it as it is)."""
    if isinstance(text, str):
        text = text.encode("latin1")
    h = 0
    for c in text:
        c = c - 256 if c >= 0x80 else c
        lo = c + 32 if 65 <= c <= 90 else c          # tolower in the C locale
        h = (h * 31 + lo) & 0xFFFFFFFF
    return h - (1 << 32) if h & 0x80000000 else h


@dataclass
class StringTable:
    name: str
    columns: int
    rows: int
    cells: list           # rows of cells (str, or None for a null string)
    bad_hashes: int       # cells whose stored hash isn't StringTable_HashString of their text

    def value(self, row: int, column: int) -> str:
        """StringTable_GetColumnValueForRow (140536B00): the cell, or "" outside the table or for a null string."""
        if column >= self.columns or row >= self.rows or row < 0 or column < 0:
            return ""
        v = self.cells[row][column]
        return "" if v is None else v

    def find_row(self, column: int, text: str) -> int:
        """StringTable_LookupRowNumForValue (140536C50): the last row whose cell in `column` equals `text`
        (case-insensitively, by hash then comparison), or -1."""
        if self.columns == 0:
            return -1
        for row in range(self.rows - 1, -1, -1):
            v = self.cells[row][column]
            if v is not None and v.lower() == text.lower():
                return row
        return -1


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


def read_string_table(mem, a: int) -> StringTable:
    name_p, columns, rows, values = struct.unpack("<QiiQ", mem.read(a, STRINGTABLE_SIZE))
    cells, bad = [], 0
    n = columns * rows if values and columns > 0 and rows > 0 else 0
    raw = mem.read(values, CELL_SIZE * n) if n else b""
    flat = []
    for i in range(n):
        p, h = struct.unpack_from("<Qi", raw, CELL_SIZE * i)
        text = _cstr(mem, p)
        if text is not None and string_hash(text) != h:
            bad += 1
        flat.append(text)
    for r in range(rows if n else 0):
        cells.append(flat[r * columns:(r + 1) * columns])
    return StringTable(_cstr(mem, name_p), columns, rows, cells, bad)


def read_localize(mem, a: int) -> tuple[str | None, str | None]:
    """(name, text) of a LocalizeEntry."""
    value_p, name_p = struct.unpack("<QQ", mem.read(a, LOCALIZE_SIZE))
    return _cstr(mem, name_p), _cstr(mem, value_p)


def to_csv(table: StringTable) -> str:
    import csv
    import io
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    for row in table.cells:
        w.writerow(["" if v is None else v for v in row])
    return out.getvalue()


def main(argv=None) -> int:
    import argparse
    import json
    import os
    import sys
    ap = argparse.ArgumentParser(description="Write a Ghosts PC zone's string tables as CSV and its localized text "
                                             "as JSON.")
    ap.add_argument("fastfile")
    ap.add_argument("--out", default=".")
    opts = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loaders
    loaders.register_all()
    with open(opts.fastfile, "rb") as f:
        zone = iw6ff.read_fastfile(f.read(), os.path.basename(opts.fastfile).rsplit(".", 1)[0])
    if not zone.complete:
        print(f"the reader stopped at asset {zone.stopped_at} (type {zone.assets[zone.stopped_at].type:#x})")
    m = zone.stream
    tables, text, bad = 0, {}, 0
    for a in zone.assets:
        if not a.header:
            continue
        if a.type == ASSET_STRINGTABLE:
            t = read_string_table(m, a.header)
            path = os.path.join(opts.out, *t.name.replace("\\", "/").split("/"))
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(to_csv(t))
            tables += 1
            bad += t.bad_hashes
        elif a.type == ASSET_LOCALIZE:
            k, v = read_localize(m, a.header)
            text[k] = v
    if text:
        os.makedirs(opts.out, exist_ok=True)
        with open(os.path.join(opts.out, "localize.json"), "w", encoding="utf-8") as f:
            json.dump(text, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{tables} string tables, {len(text)} localized strings written to {opts.out}"
          + (f"; {bad} cells whose stored hash differs" if bad else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
