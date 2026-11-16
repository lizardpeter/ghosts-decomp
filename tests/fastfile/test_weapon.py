"""tools/fastfile/pdbtypes.py (struct layouts from the servers' PDB) and weapon.read_weapon (animation slots and camo
variations), on hand-made memory laid out by the PDB's own offsets. Also, with IW6_FASTFILES, every weapon of a real
zone. No game data is part of this file."""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import pdbtypes  # noqa: E402
import weapon  # noqa: E402

TYPES = """
enum colour_t : int32_t {
    RED = 0x0,
    BLUE = 0x1,
};
struct Inner { /* Size=0x8 */
    /* 0x0000 */ float x;
    /* 0x0004 */ int16_t y[2];
};
struct Outer { /* Size=0x30 */
    /* 0x0000 */ const char* name;
    /* 0x0008 */ colour_t colour;
    /* 0x000c */ Inner inner;
    /* 0x0018 */ char tag[8];
    /* 0x0020 */ XModel** models;
    /* 0x0028 */ uint32_t count;
};
"""


class Mem:
    """Flat little-endian memory from `base`, with a bump allocator."""

    def __init__(self, base=0x10000, size=0x40000):
        self.base, self.data, self.top = base, bytearray(size), base

    def alloc(self, n, align=16):
        self.top = (self.top + align - 1) & ~(align - 1)
        a, self.top = self.top, self.top + n
        return a

    def read(self, a, n):
        return bytes(self.data[a - self.base:a - self.base + n])

    def put(self, a, fmt, *v):
        struct.pack_into("<" + fmt, self.data, a - self.base, *v)

    def cstr(self, text):
        a = self.alloc(len(text) + 1, 1)
        self.data[a - self.base:a - self.base + len(text)] = text.encode()
        return a

    def asset(self, name):
        """A header whose first field is the name (XModel, Material, ...)."""
        h = self.alloc(16)
        self.put(h, "Q", self.cstr(name))
        return h


class Layouts(unittest.TestCase):
    def test_parse_and_read(self):
        with tempfile.NamedTemporaryFile("w", suffix=".h", delete=False) as f:
            f.write(TYPES)
        try:
            structs, enums = pdbtypes.parse(Path(f.name))
        finally:
            os.unlink(f.name)
        self.assertEqual(enums["colour_t"], {0: "RED", 1: "BLUE"})
        o = structs["Outer"]
        self.assertEqual([(x.offset, x.name, x.pointers, x.dims) for x in o.fields][-3:],
                         [(0x18, "tag", 0, (8,)), (0x20, "models", 2, ()), (0x28, "count", 0, ())])
        saved = pdbtypes._CACHE.get("t")
        pdbtypes._CACHE["t"] = (structs, enums)
        try:
            m = Mem()
            a = m.alloc(0x30)
            models = m.alloc(16)
            m.put(models, "QQ", m.asset("gun"), 0)
            m.put(a, "QifhhQ", m.cstr("thing"), 1, 2.5, -3, 4, 0)
            m.data[a + 0x18 - m.base:a + 0x1B - m.base] = b"abc"
            m.put(a + 0x20, "QI", models, 2)
            ctx = pdbtypes.Context(counts={("Outer", "models"): lambda d: d["count"]})
            got = pdbtypes.read_struct(m, a, "Outer", ctx)
        finally:
            if saved is None:
                pdbtypes._CACHE.pop("t")
            else:
                pdbtypes._CACHE["t"] = saved
        self.assertEqual(got, {"name": "thing", "colour": "BLUE", "inner": {"x": 2.5, "y": [-3, 4]}, "tag": "abc",
                               "models": ["gun", None], "count": 2})

    def test_known_counts_name_pointer_fields(self):
        structs, _ = pdbtypes.types()
        for (owner, name) in pdbtypes.COUNTS:
            fields = {f.name: f for f in structs[owner].fields}
            self.assertIn(name, fields, owner)
            self.assertGreaterEqual(fields[name].pointers, 1, (owner, name))


def _offsets(name):
    return {f.name: f.offset for f in pdbtypes.types()[0][name].fields}


class Weapons(unittest.TestCase):
    def test_slots_and_camos(self):
        c, d = _offsets("WeaponCompleteDef"), _offsets("WeaponDef")
        m = Mem()
        w, wd = m.alloc(0x128), m.alloc(0xA98)
        m.put(w + c["szInternalName"], "Q", m.cstr("iw6_test_mp"))
        m.put(w + c["weapDef"], "Q", wd)
        anims = m.alloc(8 * 124)
        m.put(w + c["szXAnims"], "Q", anims)
        m.put(anims + 8 * 1, "Q", m.asset("viewmodel_test_idle"))          # XAnimParts headers
        m.put(anims + 8 * 3, "Q", m.asset("viewmodel_test_fire"))
        guns, worlds, targets = m.alloc(8 * 64), m.alloc(8 * 64), m.alloc(8 * 63)
        m.put(wd + d["gunXModel"], "Q", guns)
        m.put(wd + d["worldModel"], "Q", worlds)
        m.put(wd + d["camoMaterialTarget"], "Q", targets)
        m.put(guns, "Q", m.asset("viewmodel_test"))
        m.put(worlds, "Q", m.asset("weapon_test"))
        m.put(guns + 8 * 2, "Q", m.asset("viewmodel_test_gold"))           # a model variant
        m.put(targets + 8 * (5 - 1), "Q", m.asset("mtl_camo_snow"))         # a material camo, variation 5
        m.put(wd + d["camoViewModelMaterialOverride"], "Q", m.asset("mtl_test_body"))
        m.put(wd + d["camoWorldModel"], "Q", m.asset("weapon_test_camo"))
        got = weapon.read_weapon(m, w)
        slots = pdbtypes.enum_names("weapAnimFiles_t")
        self.assertEqual(got["szInternalName"], "iw6_test_mp")
        self.assertEqual(got["anims"], {slots[1]: "viewmodel_test_idle", slots[3]: "viewmodel_test_fire"})
        self.assertEqual(got["camos"], [
            {"variation": 2, "view_model": "viewmodel_test_gold", "world_model": None},
            {"variation": 5, "camo_material": "mtl_camo_snow",
             "view_model": "viewmodel_test", "view_material_replaced": "mtl_test_body",
             "world_model": "weapon_test_camo", "world_material_replaced": None}])

    def test_real_zone(self):
        folder = os.environ.get("IW6_FASTFILES")
        zone = Path(folder or ".") / "common_alien_mp.ff"
        if not folder or not zone.exists():
            self.skipTest("needs common_alien_mp.ff in IW6_FASTFILES")
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(weapon.main([str(zone), "--out", out]), 0)
            import json
            files = sorted(Path(out).glob("*.json"))
            self.assertGreater(len(files), 10)
            slots = set(pdbtypes.enum_names("weapAnimFiles_t").values())
            for f in files:
                w = json.loads(f.read_text())
                self.assertEqual(w["szInternalName"] + ".json", f.name)
                self.assertTrue(set(w["anims"]) <= slots)


if __name__ == "__main__":
    unittest.main()
