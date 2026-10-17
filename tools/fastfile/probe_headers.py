#!/usr/bin/env python3
"""Offline, byte-accurate IW6 FastFile prefix inspection.

Used in public Ghosts format research with 64 KiB HTTP Range probes. Reads *only* bytes
that were actually received and never mistakes a file-name catalog for decoded
assets. Produces small machine-readable JSON without copying proprietary data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys
import unittest
import zlib
from dataclasses import asdict, dataclass

MAGIC = b"IWffu100"
SIGNED_MAGIC = b"IWff0100"
AUTH_MAGIC = b"IWffs100"
VERSION = 0x235
FIXED_PREFIX = 28
STREAM_ROW_BYTES = 24
MIN_HEADER = 44
MAX_IMAGE_ROWS = 131072
MAX_SAMPLE_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class StreamImage:
    localized: int
    package: int
    begin: int
    end: int


@dataclass(frozen=True)
class Header:
    file: str
    magic: str
    envelope: str
    version: int
    flags: int
    image_count: int
    stream_offset: int
    byte_count_a: int
    byte_count_b: int
    zlib_cmf: int | None
    zlib_flg: int | None
    packages: dict[str, int]
    sampled_bytes: int


def read_header(source: bytes, name: str = "source.ff") -> Header:
    if len(source) < FIXED_PREFIX:
        raise ValueError("IW6 fixed header truncated")
    signed = source[:8] == SIGNED_MAGIC
    if not signed and source[:8] != MAGIC:
        raise ValueError("unsupported IW6 unsigned/signed PC FastFile magic")
    version, flags = struct.unpack_from("<II", source, 8)
    if version != VERSION:
        raise ValueError(f"unexpected IW6 version 0x{version:x}")
    (count,) = struct.unpack_from("<I", source, 24)
    if count > MAX_IMAGE_ROWS:
        raise ValueError(f"excessive IW6 streamed-image row count {count}")
    stream = MIN_HEADER + STREAM_ROW_BYTES * count
    if stream + 2 > len(source):
        raise ValueError(f"IW6 streamed-image table needs {stream+2} sampled bytes, got {len(source)}")
    packages: dict[str, int] = {}
    for index in range(count):
        at = FIXED_PREFIX + STREAM_ROW_BYTES * index
        localized, package = struct.unpack_from("<HH", source, at)
        begin, end = struct.unpack_from("<QQ", source, at + 8)
        if begin and end < begin:
            raise ValueError(f"stream image row {index} ends before it starts")
        key = ("localized-" if localized else "global-") + str(package)
        packages[key] = packages.get(key, 0) + 1
    a, b = struct.unpack_from("<QQ", source, stream - 16)
    if signed:
        if len(source) < stream + 8 or source[stream:stream + 8] != AUTH_MAGIC:
            raise ValueError(f"missing IW6 SHA-256 authenticated envelope at 0x{stream:x}")
        cmf, flg = None, None
        envelope = "sha256-master-blocks"
    else:
        cmf, flg = source[stream:stream + 2]
        if (cmf & 15) != 8 or (cmf >> 4) > 7 or ((cmf << 8) | flg) % 31 or (flg & 32):
            raise ValueError(f"invalid zlib marker at offset 0x{stream:x}: {cmf:02x}{flg:02x}")
        envelope = "direct-zlib"
    return Header(name, source[:8].decode("ascii"), envelope, version, flags,
                  count, stream, a, b, cmf, flg, packages, len(source))


AUTH_BLOCK_BYTES = 8192
ZONE_PREFIX_BYTES = 112


def probe_source_prefix(source: bytes, header: Header) -> dict:
    """Verify first authenticated data block and inspect only XFile prefix.

    This is evidence about the source, not an asset/geometry decoder. The
    complete compressed zone is never fetched by this survey.
    """
    offset = header.stream_offset
    authenticated = None
    if header.envelope == "sha256-master-blocks":
        need = offset + 3 * AUTH_BLOCK_BYTES
        if len(source) < need:
            return {"first_block_sha256_valid": None, "xfile_prefix": None}
        master = source[offset + AUTH_BLOCK_BYTES:offset + 2 * AUTH_BLOCK_BYTES]
        block = source[offset + 2 * AUTH_BLOCK_BYTES:need]
        authenticated = hashlib.sha256(block).digest() == master[:32]
        if not authenticated:
            raise ValueError("first original IW6 authenticated data block SHA-256 mismatch")
        compressed_prefix = block
    else:
        compressed_prefix = source[offset:]
    try:
        decoded = zlib.decompressobj().decompress(
            compressed_prefix, ZONE_PREFIX_BYTES
        )
    except zlib.error as exc:
        raise ValueError(f"original IW6 compressed zone prefix rejected: {exc}") from exc
    if len(decoded) < ZONE_PREFIX_BYTES:
        return {"first_block_sha256_valid": authenticated, "xfile_prefix": None}
    words = struct.unpack_from("<9Q", decoded, 0)
    strings, string_ref, assets, asset_ref, graphics_ref = struct.unpack_from(
        "<5Q", decoded, 72
    )
    xfile = {
        "declared_content_bytes": words[0],
        "external_bytes": words[1],
        "seven_block_bytes": list(words[2:]),
        "script_string_count": strings,
        "asset_count": assets,
        "string_ref_tag": hex(string_ref >> 32),
        "asset_ref_tag": hex(asset_ref >> 32),
        "graphics_ref_tag": hex(graphics_ref >> 32),
        "inspection": "first_112_inflated_bytes_only",
    }
    return {"first_block_sha256_valid": authenticated, "xfile_prefix": xfile}


def audit(path: pathlib.Path) -> dict:
    if path.stat().st_size > MAX_SAMPLE_BYTES:
        raise ValueError("refusing to read a sample over the bounded maximum")
    source = path.read_bytes()
    if len(source) > MAX_SAMPLE_BYTES:
        raise ValueError(f"range probe exceeded {MAX_SAMPLE_BYTES} bytes; HTTP Range may have been ignored")
    header = read_header(source, path.name)
    result = asdict(header)
    result.update(probe_source_prefix(source, header))
    result["validation"] = "range_header_only"
    result["payload_decoded"] = False
    return result


class HeaderTests(unittest.TestCase):
    def sample(self, images: int = 0) -> bytes:
        h = bytearray(MIN_HEADER + 24 * images + 2)
        h[:8] = MAGIC
        struct.pack_into("<II", h, 8, VERSION, 0x04080001)
        struct.pack_into("<I", h, 24, images)
        for i in range(images):
            struct.pack_into("<HHIQQ", h, 28 + 24 * i, 0, i + 1, 0, 8, 99)
        at = MIN_HEADER + images * 24
        struct.pack_into("<QQ", h, at - 16, 150, 150)
        h[at:at + 2] = b"\x78\x9c"
        return bytes(h)

    def test_zero_and_multiple_streamed_image_rows(self):
        for count in (0, 1, 2, 13):
            item = read_header(self.sample(count))
            self.assertEqual(item.stream_offset, 44 + 24 * count)
            self.assertEqual(item.image_count, count)

    def test_signed_pc_envelope_is_distinguished(self):
        sample = bytearray(self.sample(2))
        sample[:8] = SIGNED_MAGIC
        at = MIN_HEADER + 2 * 24
        sample[at:at + 2] = AUTH_MAGIC[:2]
        sample.extend(AUTH_MAGIC[2:])
        parsed = read_header(bytes(sample))
        self.assertEqual(parsed.envelope, "sha256-master-blocks")
        self.assertEqual(parsed.stream_offset, at)
        self.assertIsNone(parsed.zlib_cmf)

    def test_retail_sized_streamed_image_table(self):
        # Point of Contact's retail FF reports 8,160 streamed images.
        value = read_header(self.sample(8160))
        self.assertEqual(value.image_count, 8160)
        self.assertEqual(value.stream_offset, 44 + 24 * 8160)

    def test_signed_master_block_authenticates_first_zone_prefix(self):
        original = bytearray(self.sample())
        original[:8] = SIGNED_MAGIC
        original[MIN_HEADER:] = b""
        auth = bytearray(AUTH_BLOCK_BYTES)
        auth[:8] = AUTH_MAGIC
        zone = bytearray(ZONE_PREFIX_BYTES)
        struct.pack_into("<Q", zone, 0, ZONE_PREFIX_BYTES - 72)
        struct.pack_into("<Q", zone, 88, 17)
        block = bytearray(AUTH_BLOCK_BYTES)
        packed = zlib.compress(zone)
        block[:len(packed)] = packed
        master = bytearray(AUTH_BLOCK_BYTES)
        master[:32] = hashlib.sha256(block).digest()
        original.extend(auth)
        original.extend(master)
        original.extend(block)
        hdr = read_header(bytes(original))
        evidence = probe_source_prefix(bytes(original), hdr)
        self.assertTrue(evidence["first_block_sha256_valid"])
        self.assertEqual(evidence["xfile_prefix"]["asset_count"], 17)
        original[-1] ^= 0x01
        with self.assertRaises(ValueError):
            probe_source_prefix(bytes(original), hdr)

    def test_bad_prefix_rejected(self):
        with self.assertRaises(ValueError):
            read_header(self.sample()[:16])
        data = bytearray(self.sample(1))
        data[24:28] = struct.pack("<I", MAX_IMAGE_ROWS + 1)
        with self.assertRaises(ValueError):
            read_header(bytes(data))
        data = bytearray(self.sample())
        data[-1] = 0
        with self.assertRaises(ValueError):
            read_header(bytes(data))

    def test_truncated_image_table(self):
        with self.assertRaises(ValueError):
            read_header(self.sample(3)[:-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("samples", nargs="*", type=pathlib.Path)
    ap.add_argument("--test", action="store_true")
    opts = ap.parse_args()
    if opts.test:
        result = unittest.main(argv=[sys.argv[0]], exit=False)
        return 0 if result.result.wasSuccessful() else 1
    if not opts.samples:
        ap.error("supply one or more local FF prefix files, or --test")
    ok = True
    for path in opts.samples:
        try:
            print(json.dumps(audit(path), sort_keys=True))
        except (OSError, ValueError, struct.error) as exc:
            print(json.dumps({"source": path.name, "error": str(exc)}))
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
