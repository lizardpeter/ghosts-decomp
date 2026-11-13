"""The reader against the game: the Store build's own DB_LoadXFile (store_emu.py) and tools/fastfile/iw6ff.py load the
same fastfile, and everything both produce must be identical:

- the script strings the game hands to SL_GetString, in order;
- the XAsset array's types, and the (type, name) of every asset the game links;
- every byte of every zone block (the reader is given the game's block addresses, so stored pointers compare too),
  and the asset pool copies of every header;
- the streamed image rows the game keeps (count and bytes);
- the 256 bytes DB_LoadXFile hands back at its end (a signed zone's RSA signature, else zeros).

Synthetic unsigned zones (zonegen.py: every pointer kind, all three loaders, zlib and passthrough) run whenever the
Store exe is available ($IW6_ORIGINALS, as for the differential tests). Real zones run when $IW6_FASTFILES names a
folder of .ff files (never committed): each one fully when the reader has a loader for every asset in it, else up
to the XAsset array (the game stopped at its first Load_XAsset). A file named <zone>.ff.part is a prefix of a
fastfile (enough for the headers, e.g. a 4 MB range of a map zone) and runs up to the XAsset array.

The runtime block is left out when the zone has XGfxGlobals: the renderer creates GPU buffers into it while
loading (the emulator's null device hands back its own object), which is no part of the file.
"""
import os
import random
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zonegen as zg  # noqa: E402
from zonegen import iw6ff  # noqa: E402

ORIGINALS = Path(os.environ.get("IW6_ORIGINALS", Path(__file__).resolve().parents[2] / ".work" / "originals"))
HAVE_EXE = (ORIGINALS / "iw6mp64_MSStore_ship.exe").exists()
FASTFILES = os.environ.get("IW6_FASTFILES")

_LOADER = None


def loader(arena, fresh):
    """A fresh image for each real zone (loading materials and XGfxGlobals leaves renderer state behind); the
    synthetic zones (raw files, phys presets, script files) share one."""
    global _LOADER
    import store_emu
    if fresh or _LOADER is None or _LOADER.arena_size < arena:
        _LOADER = store_emu.StoreLoader(arena)
    return _LOADER


def compare(ff: bytes, name: str, full: bool, fresh=False):
    """[] when the game and the reader agree on `ff`, else a list of differences."""
    sizes = iw6ff.read_fastfile(ff, name, max_assets=0).block_sizes
    arena = max(0x4000000, (sum(sizes) + 7 * 0x1000 + 0xFFFFFF) & ~0xFFFFFF)
    g = loader(arena, fresh).load(ff, name, assets=full)
    bases = [d or ((i + 1) << 40) for i, (d, _) in enumerate(g["block_data"])]
    import store_emu
    z = iw6ff.read_fastfile(ff, name, bases=bases, max_assets=None if full else 0, pool_base=store_emu.POOL)
    out = []
    if [x for x in z.script_strings if x is not None] != g["script_strings"]:
        out.append("script strings")
    if [a.type for a in z.assets] != g["asset_types"]:
        out.append("asset types")
    if full:
        if not z.complete:
            out.append("reader stopped early")
        names = iw6ff.ASSET_TYPES
        linked = [(t, z.stream.cstr(z.stream.u64(h + names[t][2])) if z.stream.u64(h + names[t][2]) else None)
                  for t, h in z.stream.links]
        if linked != g["linked"]:
            out.append(f"linked assets: game {g['linked'][:5]} reader {linked[:5]}")
        if bytes(z.stream.pool) != g["pool"]:
            out.append("asset pool")
    gfx = z.stream.sizes[iw6ff.XFILE_BLOCK_RUNTIME] and any(g["block_data"][2][1])
    for i, (_, data) in enumerate(g["block_data"]):
        if i == iw6ff.XFILE_BLOCK_RUNTIME and gfx:
            continue
        if bytes(z.stream.mem[i]) != data:
            first = next(j for j in range(len(data)) if data[j] != z.stream.mem[i][j])
            out.append(f"{iw6ff.BLOCK_NAMES[i]} block differs from {first:#x}")
    rows = b"".join(struct.pack("<HHIQQ", r.localized, r.file, 0, r.offset, r.end) for r in z.prefix.stream_images)
    if (len(z.prefix.stream_images), rows) != (g["stream_image_count"], g["stream_image_rows"]):
        out.append("stream image rows")
    want_sig = z.auth.signature if z.auth else b"\0" * 256
    if full and g["auth_out"] != want_sig:      # written at the end of DB_LoadXFile
        out.append("auth output")
    return out


@unittest.skipUnless(HAVE_EXE, "needs the Store exe ($IW6_ORIGINALS)")
class Synthetic(unittest.TestCase):
    def test_random_zones(self):
        r = random.Random(0x5A)
        last = None
        for k in range(40):
            z = zg.with_references(zg.random_zone(r), r)
            comp = r.choice([0, 0, 2])
            rows = [(r.randrange(2), r.randrange(4), r.randrange(1 << 40), r.randrange(1 << 40))
                    for _ in range(r.choice([0, 0, 4]))]
            ff = zg.unsigned(z.xfile(zg.BIG), compressor=comp, rows=rows)
            # DB_SetFileLoadCompressor (14034A000) fixes the compressor for the process: a zone with the other
            # one is "Mixed compression types are not supported" (Com_Error), so a change needs a fresh image
            diff = compare(ff, f"synthetic{k}", True, fresh=comp != last)
            last = comp
            self.assertEqual(diff, [], f"zone {k}: {[(hex(t), hex(p)) for t, p, _ in z.assets]} {z.strings}")

    def test_simple_zone_with_globals(self):
        z = zg.Zone()
        z.strings = [None, b"a", b"bb"]
        z.globals = 0
        z.assets = [(0x2C, zg.INSERT, zg.rawfile(b"r", b"xyz")), (0x2C, zg.INLINE, zg.rawfile(b"s", b""))]
        self.assertEqual(compare(zg.unsigned(z.xfile(zg.BIG)), "simple", True), [])

    def test_mixed_compressors_are_refused(self):
        """The game's rule the reader can't see across files: one compressor per process."""
        import store_emu
        z = zg.Zone()
        z.assets = [(0x2C, zg.INLINE, zg.rawfile(b"r", b"xyz"))]
        L = store_emu.StoreLoader(0x4000000)
        L.load(zg.unsigned(z.xfile(zg.BIG), compressor=0), "a")
        with self.assertRaises(store_emu.LoadError) as e:
            L.load(zg.unsigned(z.xfile(zg.BIG), compressor=2), "b")
        self.assertIn("Mixed compression types", str(e.exception))

    def test_mutations_are_caught(self):
        """The comparison fails for a reader that differs from the game in one rule."""
        z = zg.Zone()
        z.strings = [b"one", b"tw"]
        z.assets = [(0x2C, zg.INLINE, zg.rawfile(b"r", b"xyz")), (0x00, zg.INSERT, zg.physpreset(b"p", b"q"))]
        ff = zg.unsigned(z.xfile(zg.BIG))
        self.assertEqual(compare(ff, "m", True, fresh=True), [])

        def pop_keeping_temp(self):                   # DB_PopStreamPos without the temp block rewind
            self.index = self.stack.pop()[1]

        def rawfile_len(s, at):                       # Load_RawFile sized by len instead of compressedLen
            s.load(True, at, 0x18)
            s.push(iw6ff.XFILE_BLOCK_VIRTUAL)
            s.xstring_ptr(at)
            if s.u64(at + 0x10):
                s.put_u64(at + 0x10, s.addr())
                s.load(True, s.addr(), s.i32(at + 0xC))
            s.pop()

        def insert_unaligned(self):                   # DB_InsertPointer without its 8-byte alignment
            self.push(iw6ff.XFILE_BLOCK_VIRTUAL)
            slot = self.addr()
            self.pos[iw6ff.XFILE_BLOCK_VIRTUAL] += 8
            self.pop()
            self.inserts.append(slot)
            return slot

        def detected():
            try:
                return compare(ff, "m", True) != []
            except iw6ff.FastFileError:
                return True               # the reader itself runs off the zone

        mutants = [(iw6ff.Stream, "pop", pop_keeping_temp), (iw6ff.Stream, "insert_pointer", insert_unaligned)]
        for cls, attr, mutant in mutants:
            saved = getattr(cls, attr)
            setattr(cls, attr, mutant)
            try:
                self.assertTrue(detected(), attr)
            finally:
                setattr(cls, attr, saved)
        saved = iw6ff.ASSET_LOADERS[0x2C]
        iw6ff.ASSET_LOADERS[0x2C] = iw6ff.asset_ptr(0x2C, rawfile_len)
        try:
            self.assertTrue(detected(), "rawfile")
        finally:
            iw6ff.ASSET_LOADERS[0x2C] = saved


@unittest.skipUnless(HAVE_EXE and FASTFILES, "needs the Store exe and $IW6_FASTFILES")
class Real(unittest.TestCase):
    def test_zones(self):
        files = sorted(p for p in Path(FASTFILES).iterdir() if p.name.endswith((".ff", ".ff.part")))
        self.assertTrue(files, f"no .ff files in {FASTFILES}")
        for p in files:
            data, name = p.read_bytes(), p.name.split(".")[0]
            full = p.name.endswith(".ff")
            if full:
                walk = iw6ff.read_fastfile(data, name)
                full = walk.complete
            with self.subTest(zone=p.name, mode="full" if full else "headers"):
                self.assertEqual(compare(data, name, full, fresh=True), [])


if __name__ == "__main__":
    unittest.main()
