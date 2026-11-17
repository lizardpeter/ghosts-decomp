"""tools/fastfile/menu.py: a menu file on a small hand-made stream (one menu, its window, one item with an event
script and an expression), and, with IW6_FASTFILES, mp_alien_armory's menus. No game data is part of this file."""
import os
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import iw6ff  # noqa: E402
import menu  # noqa: E402
from test_zone import FOLLOWING, stream  # noqa: E402

FOLLOW = FOLLOWING


def _window(name_follows=True):
    w = bytearray(0xB0)
    struct.pack_into("<Q", w, 0, FOLLOW if name_follows else 0)
    struct.pack_into("<4f", w, 8, 10.0, 20.0, 300.0, 40.0)
    return w


class Loader(unittest.TestCase):
    def test_menu_file_with_one_item(self):
        materials, sounds = [], []
        menu.HOOKS["material_ptr"] = lambda s, at: materials.append(at)
        menu.HOOKS["snd_alias_list_ptr"] = lambda s, at: sounds.append(s.u64(at))
        try:
            ml = struct.pack("<QiiQ", FOLLOW, 1, 0, 1)                       # name, one menu, pointers follow
            menus = struct.pack("<Q", FOLLOW)                                # the menu follows (asset pointer)
            m = bytearray(0xC8)
            m[8:8 + 0xB0] = _window()
            struct.pack_into("<iiQ", m, 0xB8, 1, 0, 1)                       # one item pointer
            item_ptrs = struct.pack("<Q", 1)                                 # any non-null: the item follows
            it = bytearray(0x1F8)
            it[0:0xB0] = _window(False)
            struct.pack_into("<i", it, 0xC4, 0)                              # a plain item
            struct.pack_into("<Q", it, 0xF0, FOLLOW)                         # text
            struct.pack_into("<Q", it, 0x128, 1)                             # action: a handler set
            struct.pack_into("<Q", it, 0x1A8, FOLLOW)                        # visibleExp
            handler_set = struct.pack("<iiQ", 1, 0, 1)
            handler_ptrs = struct.pack("<Q", 1)
            handler = struct.pack("<QB7x", FOLLOW, 0)                        # kind 0: a script string
            statement = bytearray(0x70)                                      # no entries, no supporting data
            zone = (ml + b"ui/test.menu\0" + menus + bytes(m) + b"main\0" + item_ptrs + bytes(it) + b"PLAY\0"
                    + handler_set + handler_ptrs + handler + b"open menu\0" + bytes(statement))
            s, slot = stream(zone)
            menu.load_menu_list_ptr(s, slot)
            self.assertEqual(s.cursor, iw6ff.XFILE_SIZE + len(zone))
            got = menu.read_menu_list(s, s.u64(slot))
            self.assertEqual(got["name"], "ui/test.menu")
            mm = got["menus"][0]
            self.assertEqual((mm["name"], mm["rect"]), ("main", (10.0, 20.0, 300.0, 40.0)))
            self.assertEqual(mm["items"][0]["text"], "PLAY")
            self.assertEqual(mm["items"][0]["action"], ["open menu"])
            self.assertEqual(len(materials), 2)                              # the menu's and the item's backgrounds
            self.assertEqual(sounds, [0])
        finally:
            menu.HOOKS["material_ptr"] = menu.HOOKS["snd_alias_list_ptr"] = None


class RealZone(unittest.TestCase):
    def test_nightfall_menus(self):
        folder = os.environ.get("IW6_FASTFILES")
        zone = Path(folder or ".") / "mp_alien_armory.ff"
        if not folder or not zone.exists():
            self.skipTest("needs mp_alien_armory.ff in IW6_FASTFILES")
        import loaders
        loaders.register_all()
        z = iw6ff.read_fastfile(zone.read_bytes(), zone.stem)
        self.assertTrue(z.complete)
        names = [menu.read_menu_list(z.stream, a.header)["name"] for a in z.assets
                 if a.type == menu.ASSET_MENUFILE and a.header]
        self.assertIn("ui/scriptmenus/start.menu", names)


if __name__ == "__main__":
    unittest.main()
