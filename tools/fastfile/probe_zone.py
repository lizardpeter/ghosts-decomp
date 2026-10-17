#!/usr/bin/env python3
"""Verify complete original Ghosts PC FastFile compressed zones.

- Authenticated IWff0100: SHA-256 verifies complete 8192-byte data blocks
  against their 8192-byte master before making bytes available to zlib.
- Unsigned IWffu100: direct zlib.
- No decompressed file is emitted. A 112-byte XFile header is retained.
- The declared size, total decompressed bytes and streaming counts must agree.
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

from probe_headers import read_header, MAX_IMAGE_ROWS

BLOCK = 8192
HASHES_PER_MASTER = BLOCK // 32
PREFIX_LIMIT = 4 * 1024 * 1024
MAX_OUTPUT = 4 * 1024 * 1024 * 1024
ZONE_HEADER_BYTES = 72
ASSET_LIST_HEADER_BYTES = 40


class StreamStats:
    def __init__(self) -> None:
        self.sha256_blocks = 0
        self.partial_tail_bytes = 0
        self.compressed_bytes = 0


def outer_header(file):
    prefix = file.read(28)
    if len(prefix) != 28:
        raise ValueError("truncated FastFile prefix")
    count = struct.unpack_from("<I", prefix, 24)[0]
    if count > MAX_IMAGE_ROWS:
        raise ValueError(f"streamed-image entry count exceeds cap: {count}")
    required = 44 + count * 24 + 8
    if required > PREFIX_LIMIT:
        raise ValueError(f"FastFile header exceeds {PREFIX_LIMIT}-byte cap")
    file.seek(0)
    header = read_header(file.read(required))
    return header


def verified_authenticated_chunks(file, start, stats):
    file.seek(start)
    marker = file.read(BLOCK)
    if len(marker) != BLOCK or marker[:8] != b"IWffs100":
        raise ValueError("original authenticated envelope missing or truncated")
    while True:
        master = file.read(BLOCK)
        if not master:
            return
        if len(master) != BLOCK:
            raise ValueError("truncated SHA-256 master block")
        for k in range(HASHES_PER_MASTER):
            data = file.read(BLOCK)
            if not data:
                return
            if len(data) == BLOCK:
                actual = hashlib.sha256(data).digest()
                expected = master[k * 32:(k + 1) * 32]
                if actual != expected:
                    raise ValueError(
                        f"IW6 compressed block SHA-256 mismatch after {stats.sha256_blocks} validated blocks"
                    )
                stats.sha256_blocks += 1
            else:
                stats.partial_tail_bytes += len(data)
            stats.compressed_bytes += len(data)
            yield data
            if len(data) != BLOCK:
                return


def direct_chunks(file, start, stats):
    file.seek(start)
    while True:
        chunk = file.read(1024 * 1024)
        if not chunk:
            return
        stats.compressed_bytes += len(chunk)
        yield chunk


def inflate_summary(chunks, max_output=MAX_OUTPUT):
    inflater = zlib.decompressobj()
    total = 0
    prefix = bytearray()
    for chunk in chunks:
        if inflater.eof:
            # Continue iterating the compressed source to authenticate all
            # physical blocks, even after the zlib member ends.
            continue
        pending = chunk
        while pending and not inflater.eof:
            output = inflater.decompress(pending, 65536)
            pending = inflater.unconsumed_tail
            total += len(output)
            if total > max_output:
                raise ValueError(f"decompressed zone exceeds {max_output}-byte limit")
            if len(prefix) < ZONE_HEADER_BYTES + ASSET_LIST_HEADER_BYTES:
                keep = ZONE_HEADER_BYTES + ASSET_LIST_HEADER_BYTES - len(prefix)
                prefix.extend(output[:keep])
            if not pending:
                break
    if not inflater.eof:
        raise ValueError("original IW6 compressed stream did not reach valid zlib end-of-stream")
    if len(prefix) != ZONE_HEADER_BYTES + ASSET_LIST_HEADER_BYTES:
        raise ValueError("decompressed zone too short for XFile and XAssetList")
    declared = struct.unpack_from("<Q", prefix, 0)[0]
    if declared + ZONE_HEADER_BYTES != total:
        raise ValueError(
            f"retail IW6 XFile size disagreement: header={declared + 72}, decoded={total}"
        )
    external = struct.unpack_from("<Q", prefix, 8)[0]
    block_sizes = struct.unpack_from("<7Q", prefix, 16)
    strings, string_ref, assets, asset_ref, graphics_ref = struct.unpack_from("<5Q", prefix, 72)
    return {
        "decoded_bytes": total,
        "declared_content_bytes": declared,
        "external_bytes": external,
        "block_sizes": list(block_sizes),
        "script_strings": strings,
        "assets": assets,
        "script_ref_upper32": hex(string_ref >> 32),
        "asset_ref_upper32": hex(asset_ref >> 32),
        "graphics_ref_upper32": hex(graphics_ref >> 32),
    }


def verify_source(path: pathlib.Path, max_output=MAX_OUTPUT):
    stats = StreamStats()
    with path.open("rb") as source:
        actual_bytes = path.stat().st_size
        header = outer_header(source)
        if header.byte_count_a != actual_bytes:
            raise ValueError(f"source size mismatch for {path.name}: {header.byte_count_a} != {actual_bytes}")
        if header.envelope == "sha256-master-blocks":
            chunks = verified_authenticated_chunks(source, header.stream_offset, stats)
        else:
            chunks = direct_chunks(source, header.stream_offset, stats)
        summary = inflate_summary(chunks, max_output)
    return {
        "file": path.name,
        "source_bytes": actual_bytes,
        "envelope": header.envelope,
        "streamed_images": header.image_count,
        "verified_sha256_blocks": stats.sha256_blocks,
        "unverified_partial_tail_bytes": stats.partial_tail_bytes,
        "compressed_stream_bytes": stats.compressed_bytes,
        **summary,
        "validation": "full_compressed_stream_inflated; no individual asset bodies decoded",
    }


class ZoneVerificationTests(unittest.TestCase):
    def signed_fixture(self, corrupt=False):
        decoded = bytearray(112)
        struct.pack_into("<Q", decoded, 0, 40)
        struct.pack_into("<Q", decoded, 72, 5)
        struct.pack_into("<Q", decoded, 88, 17)
        stream = zlib.compress(decoded)
        data = bytearray(BLOCK)
        data[:len(stream)] = stream
        digest = hashlib.sha256(data).digest()
        master = bytearray(BLOCK)
        master[:32] = digest
        if corrupt:
            data[300] ^= 1
        auth = bytearray(BLOCK)
        auth[:8] = b"IWffs100"
        header = bytearray(44)
        header[:8] = b"IWff0100"
        struct.pack_into("<I", header, 8, 0x235)
        size = 44 + 3 * BLOCK
        struct.pack_into("<QQ", header, 28, size, size)
        return bytes(header + auth + master + data)

    def test_authenticated_good_and_corrupt_blocks(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            file = pathlib.Path(td) / "signed.ff"
            file.write_bytes(self.signed_fixture())
            record = verify_source(file)
            self.assertEqual(record["assets"], 17)
            self.assertEqual(record["script_strings"], 5)
            self.assertEqual(record["verified_sha256_blocks"], 1)
            file.write_bytes(self.signed_fixture(corrupt=True))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_source(file)

    def test_unsigned_zone(self):
        import tempfile
        decoded = bytearray(112)
        struct.pack_into("<Q", decoded, 0, 40)
        struct.pack_into("<Q", decoded, 88, 6)
        data = zlib.compress(decoded)
        head = bytearray(44)
        head[:8] = b"IWffu100"
        struct.pack_into("<I", head, 8, 0x235)
        struct.pack_into("<QQ", head, 28, 44 + len(data), 44 + len(data))
        with tempfile.TemporaryDirectory() as td:
            file = pathlib.Path(td) / "unsigned.ff"
            file.write_bytes(bytes(head) + data)
            record = verify_source(file)
            self.assertEqual(record["assets"], 6)
            self.assertEqual(record["verified_sha256_blocks"], 0)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", nargs="*", type=pathlib.Path)
    p.add_argument("--test", action="store_true")
    opts = p.parse_args()
    if opts.test:
        tests = unittest.main(argv=[sys.argv[0]], exit=False)
        return 0 if tests.result.wasSuccessful() else 1
    if not opts.files:
        p.error("supply original local FastFiles or use --test")
    ok = True
    for path in opts.files:
        try:
            print(json.dumps(verify_source(path), sort_keys=True), flush=True)
        except (OSError, ValueError, zlib.error) as error:
            print(json.dumps({"file": path.name, "error": str(error)}), flush=True)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
