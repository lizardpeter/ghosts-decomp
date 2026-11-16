"""tools/fastfile/sound.py: the reader and audio on hand-made sounds, and the loaders against the game on a real zone
(tests/fastfile/sound_check.py, with IW6_FASTFILES and IW6_ORIGINALS)."""
import io
import math
import os
import shutil
import struct
import subprocess
import sys
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "fastfile"))
import sound  # noqa: E402


class Mem:
    """Flat little memory: put() returns the address."""

    def __init__(self):
        self.data = bytearray(0x100)

    def put(self, b: bytes) -> int:
        a = (len(self.data) + 15) & ~15
        self.data += bytes(a - len(self.data)) + b
        return a

    def read(self, a, n):
        return bytes(self.data[a:a + n]).ljust(n, b"\0")


def pcm(n=480, rate=48000):
    return b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))


def loaded_sound(m: Mem, name: str, data: bytes, fmt=1, rate=48000, ch=1, bits=16, samples=None):
    d = m.put(data)
    h = bytearray(0x38)
    struct.pack_into("<QQQ", h, 0, m.put(name.encode() + b"\0"), d, 0)
    struct.pack_into("<IIIIHHH", h, 0x18, rate, len(data), samples or len(data) // 2, rate * 2, ch, bits, 2 * ch)
    h[0x2E] = fmt
    struct.pack_into("<ii", h, 0x30, len(data), 0)
    return m.put(bytes(h))


class Reader(unittest.TestCase):
    def test_alias_list_with_loaded_and_streamed_files(self):
        m = Mem()
        ls = loaded_sound(m, "beep", pcm())
        f1 = bytearray(0x38)
        f1[0], f1[1] = sound.SOUND_FILE_LOADED, 1
        struct.pack_into("<Q", f1, 8, ls)
        f2 = bytearray(0x38)
        f2[0], f2[1] = sound.SOUND_FILE_STREAMED, 1
        struct.pack_into("<HH4xQQI", f2, 8, 0, 3, 0x800, 0x1234, 1500)   # soundfile3.pak at 0x800
        f3 = bytearray(0x38)
        f3[0], f3[1] = sound.SOUND_FILE_STREAMED, 1
        struct.pack_into("<HH", f3, 8, 1, 7)                             # english_soundfile7.pak
        files = [m.put(bytes(f)) for f in (f1, f2, f3)]
        aliases = bytearray()
        for i, f in enumerate(files):
            a = bytearray(sound.ALIAS_SIZE)
            struct.pack_into("<Q", a, 0, m.put(f"alias{i}".encode() + b"\0"))
            struct.pack_into("<Q", a, 0x28, f)
            struct.pack_into("<ff", a, 0x34, 0.5, 0.75)                   # volMin, volMax
            aliases += a
        head = m.put(bytes(aliases))
        lst = m.put(struct.pack("<QQi", m.put(b"my_list\0"), head, 3).ljust(0x18, b"\0"))
        name, out = sound.read_alias_list(m, lst)
        self.assertEqual(name, "my_list")
        self.assertEqual([a.name for a in out], ["alias0", "alias1", "alias2"])
        self.assertEqual(out[0].params["volMax"], 0.75)
        self.assertEqual(out[0].file.kind, "loaded")
        self.assertEqual(out[0].file.loaded.name, "beep")
        self.assertEqual((out[1].file.pak, out[1].file.offset, out[1].file.length, out[1].file.total_msec),
                         ("soundfile3.pak", 0x800, 0x1234, 1500))
        self.assertEqual(out[2].file.pak, "english_soundfile7.pak")


class Audio(unittest.TestCase):
    def test_pcm_as_wave(self):
        m = Mem()
        data = pcm()
        ld = sound.read_loaded_sound(m, loaded_sound(m, "beep", data))
        b, kind = sound.audio_bytes(sound.SoundFile("loaded", True, loaded=ld), None)
        self.assertEqual(kind, "wav")
        with wave.open(io.BytesIO(b)) as w:
            self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth()), (48000, 1, 2))
            self.assertEqual(w.readframes(10_000), data)

    def test_stream_range_of_pak(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "soundfile3.pak").write_bytes(bytes(0x800) + b"fLaC" + bytes(12))
            sf = sound.SoundFile("streamed", True, pak="soundfile3.pak", offset=0x800, length=16)
            self.assertEqual(sound.audio_bytes(sf, d), (b"fLaC" + bytes(12), "flac"))
            self.assertEqual(sound.audio_bytes(sf, None), (None, ""))

    @unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
    def test_flac_frames_without_header_decode(self):
        """A primed file's loaded start is FLAC frames with no fLaC/STREAMINFO: flac_header makes them decodable."""
        data = pcm(9000)
        wav = sound.wav_bytes(sound.LoadedSound("x", 48000, len(data), 9000, 1, 16, 2, 1, data, b""))
        flac = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "flac", "pipe:1"], input=wav,
                              capture_output=True, check=True).stdout
        at = 4
        while True:                                   # skip the metadata blocks to the first frame
            last, size = flac[at] & 0x80, int.from_bytes(flac[at + 1:at + 4], "big")
            at += 4 + size
            if last:
                break
        ld = sound.LoadedSound("x", 48000, 0, 9000, 1, 16, 2, 7, flac[at:], b"")
        b, kind = sound.audio_bytes(sound.SoundFile("primed", True, loaded=ld), None)
        self.assertEqual(kind, "flac")
        out = sound.to_wav(b, kind)
        with wave.open(io.BytesIO(out)) as w:
            self.assertEqual(w.getframerate(), 48000)
            self.assertEqual(w.readframes(100_000), data)


class Game(unittest.TestCase):
    """The loaders against the game on an Extinction zone's first alias lists and loaded sounds."""

    @classmethod
    def setUpClass(cls):
        folder = os.environ.get("IW6_FASTFILES")
        if not folder or not os.environ.get("IW6_ORIGINALS"):
            raise unittest.SkipTest("needs IW6_FASTFILES and IW6_ORIGINALS")
        cls.zone = Path(folder) / "common_alien_mp.ff"
        if not cls.zone.exists():
            raise unittest.SkipTest("no common_alien_mp.ff in IW6_FASTFILES")

    def test_loaders_equal_game(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import sound_check
        ff = self.zone.read_bytes()
        for fn, occ in ((sound_check.compare_alias_list, 0), (sound_check.compare_loaded_sound, 1)):
            d, _ = fn(ff, self.zone.stem, occ)
            self.assertEqual(d, [], (fn.__name__, occ))


if __name__ == "__main__":
    unittest.main()
