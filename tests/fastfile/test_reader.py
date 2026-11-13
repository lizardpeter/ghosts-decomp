"""Unit tests of tools/fastfile/iw6ff.py on synthetic fastfiles (no game data, no exe)."""
import hashlib
import random
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zonegen as zg  # noqa: E402
from zonegen import iw6ff  # noqa: E402


def simple_zone():
    z = zg.Zone()
    z.strings = [None, b"alpha", b"beta"]
    z.globals = 0
    z.assets = [(0x2C, zg.INLINE, zg.rawfile(b"maps/a.cfg", b"0123456789")),
                (0x00, zg.INSERT, zg.physpreset(b"crate", b"snd_crate")),
                (0x2D, zg.INLINE, zg.scriptfile(b"1001", b"src", b"\x01\x02"))]
    return z


class Prefix(unittest.TestCase):
    def test_rows_and_offset(self):
        rows = [(0, 1, 0x100, 0x200), (1, 3, 0x10, 0x20), (0, 0, 0, 0)]
        p = iw6ff.read_prefix(zg.prefix(iw6ff.MAGIC_SIGNED, rows=rows, sizes=(7, 9)))
        self.assertEqual([(r.localized, r.file, r.offset, r.end) for r in p.stream_images], rows)
        self.assertEqual(p.payload_offset, 44 + 24 * 3)
        self.assertEqual(p.loadbar_sizes, (7, 9))
        self.assertTrue(p.signed)
        self.assertEqual([r.path for r in p.stream_images], ["imagefile1.pak", "<language>_imagefile3.pak", None])

    def test_rejections(self):
        good = zg.prefix(iw6ff.MAGIC_UNSIGNED)
        for bad, check in ((b"IWffx100" + good[8:], "DB_DirtyDiscError"),
                           (good[:8] + struct.pack("<I", 0x234) + good[12:], "version"),
                           (good[:13] + b"\x01" + good[14:], "DB_SetFileLoadCompressor"),
                           (good[:24] + struct.pack("<I", 0x6281) + good[28:], "DB_DirtyDiscError"),
                           (good[:30], "DB_DirtyDiscError")):
            with self.assertRaises(iw6ff.FastFileError) as e:
                iw6ff.read_prefix(bad)
            self.assertEqual(e.exception.check, check)
        iw6ff.read_prefix(good[:24] + struct.pack("<I", 0) + good[28:])


class Stream(unittest.TestCase):
    def test_push_pop_temp_reuse(self):
        s = iw6ff.Stream(b"\0" * 0x48 + bytes(range(64)), [64, 0, 64, 64, 0, 0, 0])
        s.push(0)
        s.load(True, s.addr(), 8)
        s.push(3)
        s.load(True, s.addr(), 4)
        s.pop()
        self.assertEqual(s.pos[0], 8)
        s.pop()                           # leaving temp: back to where temp was at the push
        self.assertEqual((s.index, s.pos[0], s.pos[3]), (0, 0, 4))
        s.push(2)                         # runtime: zero-filled, nothing read
        s.load(True, s.addr(), 16)
        s.pop()
        self.assertEqual((s.pos[2], s.cursor), (16, 0x48 + 12))

    def test_alignment_and_pointers(self):
        s = iw6ff.Stream(b"\0" * 0x48, [16, 0, 0, 64, 0, 0, 0], bases=[0x1000, 0, 0, 0x8000, 0, 0, 0])
        s.push(3)
        s.pos[3] = 5
        self.assertEqual(s.align(4), 0x8008)
        self.assertEqual(s.insert_pointer(), 0x8008)
        self.assertEqual(s.pos[3], 16)
        self.assertEqual(s.unpack_offset(zg.packed(3, 0x20)), (3, 0x20))
        self.assertEqual(s.offset_to_pointer((0x7 << 36) | zg.packed(3, 0x20)), 0x8020)  # bits above 35 ignored
        s.put_u64(0x8020, 0xABCDEF)
        self.assertEqual(s.offset_to_alias(zg.packed(3, 0x20)), 0xABCDEF)

    def test_overflow_is_reported(self):
        s = iw6ff.Stream(b"\0" * 0x48 + b"x" * 32, [0, 0, 0, 8, 0, 0, 0])
        s.push(3)
        with self.assertRaises(iw6ff.FastFileError):
            s.load(True, s.addr(), 16)


class Zones(unittest.TestCase):
    def test_walk(self):
        data = zg.unsigned(simple_zone().xfile(zg.BIG))
        z = iw6ff.read_fastfile(data)
        self.assertTrue(z.complete)
        self.assertEqual(z.script_strings, [None, b"alpha", b"beta"])
        self.assertEqual([(a.type_name, a.name) for a in z.assets],
                         [("rawfile", "maps/a.cfg"), ("physpreset", "crate"), ("scriptfile", "1001")])
        s = z.stream
        self.assertEqual(s.read(s.u64(z.assets[0].header + 0x10), 10), b"0123456789")
        self.assertEqual(s.cstr(s.u64(z.assets[1].header + 0x20)), b"snd_crate")
        self.assertIsNotNone(z.assets[1].slot)
        self.assertEqual(s.u64(z.assets[1].slot), z.assets[1].header)
        self.assertEqual(s.u64(z.string_table + 8), 1)       # script string handles, in order
        self.assertEqual(s.cursor, len(s.zone))

    def test_passthrough(self):
        xf = simple_zone().xfile(zg.BIG)
        a = iw6ff.read_fastfile(zg.unsigned(xf, compressor=2))
        self.assertEqual([x.name for x in a.assets], ["maps/a.cfg", "crate", "1001"])

    def test_unknown_type_stops(self):
        z = simple_zone()
        z.assets.insert(1, (0x05, zg.INLINE, b"\0" * 0x3A8))
        r = iw6ff.read_fastfile(zg.unsigned(z.xfile(zg.BIG)))
        self.assertFalse(r.complete)
        self.assertEqual(r.stopped_at, 1)
        self.assertEqual([a.type for a in r.assets], [0x2C, 0x05, 0x00, 0x2D])

    def test_random_zones_roundtrip(self):
        r = random.Random(77)
        for _ in range(60):
            z = zg.random_zone(r)
            z = zg.with_references(z, r)
            out = iw6ff.read_fastfile(zg.unsigned(z.xfile(zg.BIG)))
            self.assertTrue(out.complete)
            self.assertEqual(len(out.assets), len(z.assets))
            self.assertEqual(out.stream.cursor, len(out.stream.zone))


class Signed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = zg.test_key()
        cls.pub = cls.key[:2]
        cls.xf = simple_zone().xfile(zg.BIG)
        cls.ff = zg.signed(cls.xf, "test_zone", cls.key)

    def test_verifies(self):
        z = iw6ff.read_fastfile(self.ff, "test_zone", self.pub)
        self.assertEqual((z.auth.zone_name, z.auth.signature_checked, z.auth.groups), ("test_zone", True, 1))
        self.assertEqual([a.name for a in z.assets], ["maps/a.cfg", "crate", "1001"])

    def test_der_key(self):
        n, e = self.pub
        nb = b"\0" + n.to_bytes(256, "big")
        der = b"\x30\x82\x01\x0a" + b"\x02\x82\x01\x01" + nb + b"\x02\x03" + e.to_bytes(3, "big")
        self.assertEqual(len(der), iw6ff.PUBLIC_KEY_LEN)
        self.assertEqual(iw6ff.parse_public_key(der), self.pub)

    def test_many_groups(self):
        big = zg.Zone()
        big.assets = [(0x2C, zg.INLINE, zg.rawfile(b"noise", random.Random(5).randbytes(0x220000)))]
        ff = zg.signed(big.xfile(zg.BIG[:3] + [0x240000] + zg.BIG[4:]), "z", self.key)
        z = iw6ff.read_fastfile(ff, "z", self.pub)
        self.assertGreater(z.auth.groups, 1)
        self.assertEqual(z.assets[0].name, "noise")

    def tamper(self, at, check):
        bad = bytearray(self.ff)
        bad[at] ^= 1
        with self.assertRaises(iw6ff.FastFileError) as e:
            iw6ff.read_fastfile(bytes(bad), "test_zone", self.pub)
        self.assertIn(check, str(e.exception))

    def test_tampering(self):
        base = 44
        self.tamper(base + 0x14, "subheader hash")             # the hash itself
        self.tamper(base + 0x40, "RSA signature")              # the signature
        self.tamper(base + 0x2000 + 5, "master block")         # a master block
        self.tamper(base + 0x4000 + 9, "data block")           # a data block
        self.tamper(base + 0x200, "subheader hash")            # the subheader (name, master hashes)

    def test_wrong_name(self):
        with self.assertRaises(iw6ff.FastFileError) as e:
            iw6ff.read_fastfile(self.ff, "other_zone", self.pub)
        self.assertIn("zone name", str(e.exception))

    def test_pss_rejects_other_hash(self):
        sig = zg.pss_sign(self.key, hashlib.sha256(b"a").digest(), b"12345678")
        self.assertTrue(iw6ff.rsa_pss_verify(self.pub, hashlib.sha256(b"a").digest(), sig))
        self.assertFalse(iw6ff.rsa_pss_verify(self.pub, hashlib.sha256(b"b").digest(), sig))
        self.assertFalse(iw6ff.rsa_pss_verify(self.pub, hashlib.sha256(b"a").digest(), sig[:-1] + b"\0"))


if __name__ == "__main__":
    unittest.main()
