#!/usr/bin/env python3
"""Sounds in Call of Duty: Ghosts PC zones (Microsoft Store build): sound alias lists (asset type 0x0E, "sound"),
loaded sounds (0x12), the curves, speaker maps and doppler presets they use, and the audio itself.

1. Loader: the Store build's loaders statement for statement (Load_snd_alias_list_ptr 140361F10 and the functions
   under it; Load_LoadedSoundPtr 140352600); tests/fastfile/sound_check.py checks them against the game on real
   zones.
2. Reader: read_alias_list (the aliases with their parameters and where their audio is), read_loaded_sound.
3. Audio: a sound file is loaded (its data is in the zone: a LoadedSound), streamed (a byte range of
   soundfile<N>.pak, or of <language>_soundfile<N>.pak when localized) or primed (the start loaded, the rest
   streamed). On PC the data is FLAC (the packed range is a whole FLAC stream; ffmpeg decodes it). extract() writes
   them out. docs/assets/sound.md.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import iw6ff

PTR_INLINE = 0xFDFDFDFFFFFFFFFF
PTR_INSERT = 0xFDFDFDFFFFFFFFFE
BLOCK_TEMP, BLOCK_VIRTUAL = 0, 3
ASSET_SOUND, ASSET_SNDCURVE, ASSET_LPFCURVE, ASSET_REVERBCURVE = 0x0E, 0x0F, 0x10, 0x11
ASSET_LOADED_SOUND, ASSET_DOPPLER = 0x12, 0x3D
ALIAS_SIZE = 0xC8
SOUND_FILE_LOADED, SOUND_FILE_STREAMED, SOUND_FILE_PRIMED = 1, 2, 3


# ==== 1. loader ===================================================================================================

def _u16(s, a):
    return struct.unpack("<H", s.read(a, 2))[0]


def _i32(s, a):
    return struct.unpack("<i", s.read(a, 4))[0]


def _xstring_field(s, at):
    """The XString rule on a field already read (Load_Stream(false) then FOLLOWING or an offset)."""
    s.xstring_ptr(at)


def _named_asset(size: int, name_at: int):
    """An asset header of `size` bytes whose only pointer is an XString at name_at, in the virtual block (SndCurve
    140356D40 and its lpf / reverb twins, DopplerPreset 14034C0C0)."""
    def body(s, h):
        s.load(True, h, size)
        s.push(BLOCK_VIRTUAL)
        _xstring_field(s, h + name_at)
        s.pop()
    return body


load_snd_curve_ptr = iw6ff.asset_ptr(ASSET_SNDCURVE, _named_asset(0x98, 8))        # 140356DD0
load_lpf_curve_ptr = iw6ff.asset_ptr(ASSET_LPFCURVE, _named_asset(0x98, 8))        # 140352960
load_reverb_curve_ptr = iw6ff.asset_ptr(ASSET_REVERBCURVE, _named_asset(0x98, 8))  # 1403559A0
load_doppler_preset_ptr = iw6ff.asset_ptr(ASSET_DOPPLER, _named_asset(0x20, 0))    # 14034C150


def load_xa2_sound(s, at: int, at_stream_start: bool = False):
    """14035C8F0 (Load_XA2Sound): data (+0, in the temp block: inline or insert, loadedSize (+0x28) bytes, then the
    engine registers it (1406AEBD0); else an alias), seekTable (+8: inline, seekTableSize (+0x2C) bytes, or an
    offset)."""
    s.load(at_stream_start, at, 0x30)
    s.push(BLOCK_TEMP)
    v = s.u64(at)
    if v:
        if v in (PTR_INLINE, PTR_INSERT):
            p = s.addr()
            s.put_u64(at, p)
            slot = s.insert_pointer() if v == PTR_INSERT else None
            s.load(True, p, _i32(s, at + 0x28))
            # the engine (1406AEBD0) copies the data to sound memory it allocates (140535BE0, the size at +0x14)
            # and keeps that copy: the stream's caller may supply engine_copy(at, temp address, size) -> address
            copy = getattr(s, "engine_copy", None)
            if copy is not None:
                s.put_u64(at, copy(at, p, _i32(s, at + 0x28)))
            if slot is not None:
                s.put_u64(slot, s.u64(at))
        else:
            s.put_u64(at, s.offset_to_alias(v))
    s.pop()
    v = s.u64(at + 8)
    if not v:
        return
    if v == PTR_INLINE:
        p = s.addr()
        s.put_u64(at + 8, p)
        s.load(True, p, _i32(s, at + 0x2C))
    else:
        s.put_u64(at + 8, s.offset_to_pointer(v))


def load_loaded_sound(s, h: int, at_stream_start: bool = True):
    """140352560 (Load_LoadedSound): 0x38 bytes, name, the XA2Sound at +8."""
    s.load(at_stream_start, h, 0x38)
    s.push(BLOCK_VIRTUAL)
    _xstring_field(s, h)
    load_xa2_sound(s, h + 8, False)
    s.pop()


load_loaded_sound_ptr = iw6ff.asset_ptr(ASSET_LOADED_SOUND, lambda s, h: load_loaded_sound(s, h, True))  # 140352600


def _stream_file_name(s, at: int):
    """The StreamFileName (0x18) at `at`, already read: when fileIndex (+2) is 0 the info is raw: dir and name
    XStrings (140357840); else packed offset and length (nothing to load)."""
    if _u16(s, at + 2) == 0:
        _xstring_field(s, at + 8)
        _xstring_field(s, at + 0x10)


def load_sound_file(s, at: int, at_stream_start: bool = True):
    """140357080 (Load_SoundFile): 0x38 bytes; type (+0) 1: a LoadedSound pointer at +8; 2: StreamedSound (+8, 0x20,
    140357920); 3: PrimedSound (+8, 0x30, 1403556E0: the stream file name, then a LoadedSound pointer at +0x20)."""
    s.load(at_stream_start, at, 0x38)
    t = s.read(at, 1)[0]
    u = at + 8
    if t == SOUND_FILE_LOADED:
        load_loaded_sound_ptr(s, u)
    elif t == SOUND_FILE_STREAMED:
        _stream_file_name(s, u)
    elif t == SOUND_FILE_PRIMED:
        _stream_file_name(s, u)
        load_loaded_sound_ptr(s, u + 0x18)


def _inline_struct(s, field_at: int, size: int, body=None):
    """A pointer that is inline (aligned 4) or an offset."""
    v = s.u64(field_at)
    if not v:
        return
    if v == PTR_INLINE:
        p = s.align(4)
        s.put_u64(field_at, p)
        if body:
            body(s, p)
        else:
            s.load(True, p, size)
    else:
        s.put_u64(field_at, s.offset_to_pointer(v))


def _speaker_map(s, p):
    """140357250 (Load_SpeakerMap): 0x1A0 bytes, the name XString at +8."""
    s.load(True, p, 0x1A0)
    _xstring_field(s, p + 8)


def load_alias_array(s, at: int, count: int):
    """1403620F0 (Load_snd_alias_tArray): count × 0xC8."""
    s.load(True, at, ALIAS_SIZE * count)
    for i in range(count):
        a = at + ALIAS_SIZE * i
        for off in (0, 8, 0x10, 0x18, 0x20):            # aliasName, subtitle, secondaryAliasName, chain, mixerGroup
            _xstring_field(s, a + off)
        _inline_struct(s, a + 0x28, 0x38, lambda s_, p: load_sound_file(s_, p, True))
        load_snd_curve_ptr(s, a + 0x78)
        load_lpf_curve_ptr(s, a + 0x80)
        load_reverb_curve_ptr(s, a + 0x88)
        _inline_struct(s, a + 0xA0, 0x1A0, _speaker_map)
        _inline_struct(s, a + 0xB0, 0x20)                 # occlusion shape
        load_doppler_preset_ptr(s, a + 0xC0)


def load_alias_list(s, h: int, at_stream_start: bool = True):
    """140362000 (Load_snd_alias_list_t): 0x18 bytes: aliasName, head (count +0x10 aliases: inline or an offset)."""
    s.load(at_stream_start, h, 0x18)
    s.push(BLOCK_VIRTUAL)
    _xstring_field(s, h)
    v = s.u64(h + 8)
    if v:
        if v == PTR_INLINE:
            p = s.align(4)
            s.put_u64(h + 8, p)
            load_alias_array(s, p, _i32(s, h + 0x10))
        else:
            s.put_u64(h + 8, s.offset_to_pointer(v))
    s.pop()


load_alias_list_ptr = iw6ff.asset_ptr(ASSET_SOUND, lambda s, h: load_alias_list(s, h, True))   # 140361F10


def register(asset_loaders: dict):
    asset_loaders[ASSET_SOUND] = load_alias_list_ptr
    asset_loaders[ASSET_LOADED_SOUND] = load_loaded_sound_ptr
    asset_loaders[ASSET_SNDCURVE] = load_snd_curve_ptr
    asset_loaders[ASSET_LPFCURVE] = load_lpf_curve_ptr
    asset_loaders[ASSET_REVERBCURVE] = load_reverb_curve_ptr
    asset_loaders[ASSET_DOPPLER] = load_doppler_preset_ptr


# ==== 2. reader ===================================================================================================

def _cstr(mem, a):
    if not a:
        return None
    out = bytearray()
    while True:
        b = mem.read(a, 64)
        i = b.find(b"\0")
        if i >= 0:
            out += b[:i]
            return out.decode("latin1")
        out += b
        a += 64


def _q(mem, a):
    return struct.unpack("<Q", mem.read(a, 8))[0]


@dataclass
class LoadedSound:
    name: str
    sample_rate: int
    data_bytes: int
    samples: int
    channels: int
    bits: int
    block_align: int
    format: int
    data: bytes
    seek_table: bytes


@dataclass
class SoundFile:
    kind: str                       # loaded, streamed, primed
    exists: bool
    pak: str | None = None          # soundfile<N>.pak (streamed, primed)
    offset: int = 0
    length: int = 0
    raw_name: tuple | None = None   # (dir, name) when the file isn't packed
    total_msec: int = 0
    loaded: LoadedSound | None = None


@dataclass
class Alias:
    name: str
    subtitle: str | None
    secondary: str | None
    chain: str | None
    mixer_group: str | None
    file: SoundFile | None
    params: dict = field(default_factory=dict)


def read_loaded_sound(mem, a: int) -> LoadedSound:
    h = mem.read(a, 0x38)
    data_p, seek_p = struct.unpack_from("<QQ", h, 8)
    sr, nbytes, nsamples, avg, ch, bits, align = struct.unpack_from("<IIIIHHH", h, 0x18)
    fmt = h[0x2E]
    loaded, seek = struct.unpack_from("<ii", h, 0x30)
    return LoadedSound(_cstr(mem, _q(mem, a)), sr, nbytes, nsamples, ch, bits, align, fmt,
                       mem.read(data_p, loaded) if data_p and loaded > 0 else b"",
                       mem.read(seek_p, seek) if seek_p and seek > 0 else b"")


def _stream_name(mem, at: int, sf: SoundFile, language: str = "english"):
    localized, index = struct.unpack("<HH", mem.read(at, 4))
    if index == 0:
        sf.raw_name = (_cstr(mem, _q(mem, at + 8)), _cstr(mem, _q(mem, at + 0x10)))
    else:
        sf.pak = f"{language}_soundfile{index}.pak" if localized else f"soundfile{index}.pak"
        sf.offset, sf.length = struct.unpack("<QQ", mem.read(at + 8, 16))


def read_sound_file(mem, a: int, language: str = "english") -> SoundFile:
    t, exists = mem.read(a, 2)
    u = a + 8
    if t == SOUND_FILE_LOADED:
        p = _q(mem, u)
        return SoundFile("loaded", bool(exists), loaded=read_loaded_sound(mem, p) if p else None)
    if t == SOUND_FILE_STREAMED:
        sf = SoundFile("streamed", bool(exists))
        _stream_name(mem, u, sf, language)
        sf.total_msec = struct.unpack("<I", mem.read(u + 0x18, 4))[0]
        return sf
    if t == SOUND_FILE_PRIMED:
        sf = SoundFile("primed", bool(exists))
        _stream_name(mem, u, sf, language)
        p = _q(mem, u + 0x18)
        sf.loaded = read_loaded_sound(mem, p) if p else None
        return sf
    return SoundFile(f"type{t}", bool(exists))


PARAMS = (("sequence", 0x30, "i"), ("volMin", 0x34, "f"), ("volMax", 0x38, "f"), ("volModIndex", 0x3C, "i"),
          ("pitchMin", 0x40, "f"), ("pitchMax", 0x44, "f"), ("distMin", 0x48, "f"), ("distMax", 0x4C, "f"),
          ("velocityMin", 0x50, "f"), ("flags", 0x54, "I"), ("masterPriority", 0x58, "B"),
          ("masterPercentage", 0x5C, "f"), ("slavePercentage", 0x60, "f"), ("probability", 0x64, "f"),
          ("lfePercentage", 0x68, "f"), ("centerPercentage", 0x6C, "f"), ("startDelay", 0x70, "i"),
          ("envelopMin", 0x90, "f"), ("envelopMax", 0x94, "f"), ("envelopPercentage", 0x98, "f"),
          ("wetMixOverride", 0xA8, "f"), ("allowDoppler", 0xB8, "B"))


def read_alias_list(mem, a: int, language: str = "english") -> tuple[str, list[Alias]]:
    name = _cstr(mem, _q(mem, a))
    head, count = struct.unpack("<Qi", mem.read(a + 8, 12))
    out = []
    for i in range(count if head else 0):
        p = head + ALIAS_SIZE * i
        h = mem.read(p, ALIAS_SIZE)
        strs = [_cstr(mem, x) for x in struct.unpack_from("<5Q", h, 0)]
        sfp = struct.unpack_from("<Q", h, 0x28)[0]
        params = {k: struct.unpack_from("<" + f, h, off)[0] for k, off, f in PARAMS}
        for k, off in (("volumeFalloffCurve", 0x78), ("lpfCurve", 0x80), ("reverbSendCurve", 0x88),
                       ("speakerMap", 0xA0), ("dopplerPreset", 0xC0)):
            q = struct.unpack_from("<Q", h, off)[0]
            nm_at = {"speakerMap": 8, "dopplerPreset": 0}.get(k, 8)
            params[k] = _cstr(mem, _q(mem, q + nm_at)) if q else None
        out.append(Alias(strs[0], strs[1], strs[2], strs[3], strs[4],
                         read_sound_file(mem, sfp, language) if sfp else None, params))
    return name, out


# ==== 3. audio ====================================================================================================

def stream_bytes(sf: SoundFile, pak_dir) -> bytes | None:
    """The bytes of a streamed or primed file's range in its sound pak (None if the pak isn't there)."""
    import os
    if not sf.pak:
        return None
    path = os.path.join(pak_dir, sf.pak)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        f.seek(sf.offset)
        return f.read(sf.length)


FORMATS = {0: "invalid", 1: "pcm", 2: "xma2", 3: "adpcm", 4: "xwma", 5: "mp3", 6: "wiiudsp", 7: "flac"}  # snd_format_t


def wav_bytes(ld: LoadedSound) -> bytes:
    """A PCM LoadedSound (format 1: interleaved little-endian samples) as a RIFF WAVE file."""
    rate, ch, bits = ld.sample_rate, max(ld.channels, 1), ld.bits or 16
    align = ld.block_align or ch * bits // 8
    fmt = struct.pack("<HHIIHH", 1, ch, rate, rate * align, align, bits)
    return (b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + len(ld.data)) + b"WAVE" +
            b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(ld.data)) + ld.data)


def flac_header(ld: LoadedSound, min_block: int = 16, max_block: int = 65535) -> bytes:
    """fLaC and a STREAMINFO for FLAC frames stored without one (a primed file's loaded start, format 7): the
    frames carry their own sizes, the header gives a decoder the rate, channels and sample size."""
    info = (min_block << 16 | max_block).to_bytes(4, "big") + bytes(6)
    v = (ld.sample_rate << 44) | ((max(ld.channels, 1) - 1) << 41) | (((ld.bits or 16) - 1) << 36) | ld.samples
    info += v.to_bytes(8, "big") + bytes(16)
    return b"fLaC" + bytes([0x80, 0, 0, len(info)]) + info


def audio_bytes(sf: SoundFile, pak_dir) -> tuple[bytes | None, str]:
    """(the file's audio, its container: wav, flac or another format's name). A streamed file is a whole FLAC
    stream in its pak; a primed file's whole audio is its stream too (the loaded part only its first frames, which
    serve when the pak isn't there); a loaded file is PCM (as WAVE) or FLAC frames."""
    if sf.kind in ("streamed", "primed") and pak_dir:
        b = stream_bytes(sf, pak_dir)
        if b is not None:
            return b, "flac" if b[:4] == b"fLaC" else "bin"
    ld = sf.loaded
    if ld is None or not ld.data:
        return None, ""
    if ld.format == 1:
        return wav_bytes(ld), "wav"
    if ld.format == 7:
        return (ld.data if ld.data[:4] == b"fLaC" else flac_header(ld) + ld.data), "flac"
    return ld.data, FORMATS.get(ld.format, "bin")


def to_wav(data: bytes, container: str) -> bytes:
    """Decode to WAVE (ffmpeg for FLAC)."""
    if container == "wav":
        return data
    import subprocess
    return subprocess.run(["ffmpeg", "-v", "error", "-f", container, "-i", "pipe:0", "-f", "wav", "pipe:1"],
                          input=data, capture_output=True, check=True).stdout


def extract(mem, alias_lists, out_dir, pak_dir=None, decode=True, language="english"):
    """Write the audio of every alias of the alias lists at `alias_lists` (addresses in `mem`) to
    out_dir/<alias name>[_<n>].<wav|flac|...>; returns (written, missing) where missing lists the aliases whose
    audio is elsewhere (a pak that isn't there, a loaded sound of another zone)."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    written, missing, seen = [], [], {}
    for address in alias_lists:
        name, aliases = read_alias_list(mem, address, language)
        for al in aliases:
            data, kind = audio_bytes(al.file, pak_dir) if al.file else (None, "")
            if data is None:
                missing.append((al.name, al.file))
                continue
            if decode and kind == "flac":
                try:
                    data, kind = to_wav(data, kind), "wav"
                except Exception:
                    pass
            base = (al.name or name or "sound").replace("/", "_")
            n = seen.get(base, 0)
            seen[base] = n + 1
            path = os.path.join(out_dir, f"{base}{'_' + str(n) if n else ''}.{kind}")
            with open(path, "wb") as f:
                f.write(data)
            written.append(path)
    return written, missing


def main(argv=None) -> int:
    import argparse
    import os
    import sys
    ap = argparse.ArgumentParser(description="Write the sounds of a Ghosts PC zone as WAVE (or FLAC) files.")
    ap.add_argument("fastfile")
    ap.add_argument("--out", default=".")
    ap.add_argument("--paks", help="the folder with soundfile<N>.pak (for streamed and primed sounds)")
    ap.add_argument("--flac", action="store_true", help="keep FLAC as it is (don't decode with ffmpeg)")
    opts = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loaders
    loaders.register_all()          # every asset type, so the walk reaches the sounds
    with open(opts.fastfile, "rb") as f:
        zone = iw6ff.read_fastfile(f.read(), os.path.basename(opts.fastfile).rsplit(".", 1)[0])
    if not zone.complete:
        print(f"the reader stopped at asset {zone.stopped_at} (type {zone.assets[zone.stopped_at].type:#x}); "
              "tests/fastfile/sound_check.py --extract reads the zone the game loaded")
    lists = [a.header for a in zone.assets if a.type == ASSET_SOUND and a.header]
    written, missing = extract(zone.stream, lists, opts.out, opts.paks, not opts.flac)
    paks = sorted({m[1].pak for m in missing if m[1] is not None and m[1].pak})
    print(f"{len(written)} files written; {len(missing)} aliases' audio elsewhere" +
          (f" (paks: {', '.join(paks)})" if paks else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
