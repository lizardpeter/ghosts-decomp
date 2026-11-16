# Sounds (snd_alias_list_t "sound", LoadedSound "loaded_sound", curves and presets)

What the Microsoft Store build loads for sounds, where the audio is, and how to get it out.
`tools/fastfile/sound.py` loads, reads and extracts them; `tests/fastfile/sound_check.py` checks the loaders against
the game's own code and extracts a zone's audio from the zone as the game loaded it.

## 1. How it was checked

- **Loaders.** The Store build's loaders run in the emulator (`tests/fastfile/store_emu.py`) on common_alien_mp
  (the Extinction aliens' shared zone: 359 alias lists, 742 aliases). At a chosen call of `Load_snd_alias_list_ptr`
  (140361F10) or `Load_LoadedSoundPtr` (140352600) the stream state is handed to sound.py's loader; when the game's
  call returns, the zone position, every block position, the block memory and the asset pool must be the same
  (`world_check.compare`). Equal for alias-list calls 0, 1, 5, 50, 200 and 358 and loaded-sound calls 0, 1 and 100.
- **One pointer the reader cannot predict.** The engine copies a loaded sound's data to memory it allocates
  (section 4), and keeps that address. The check lets the reader store a marker there, then accepts the game's
  address only if the game's copy holds exactly the bytes the reader loaded.
- **Reader.** `read_alias_list` on every alias list of the zone the game loaded: 612 loaded, 112 streamed and 18
  primed sound files.
- **Audio.** 437 files extracted from common_alien_mp alone (419 PCM, 18 primed starts decoded through ffmpeg); the
  others need sound paks (section 5).

## 2. Asset types

| Type | Name | Header | Store loader |
|---|---|---|---|
| 0x0E | sound (snd_alias_list_t) | 0x18 | Load_snd_alias_list_ptr 140361F10 → Load_snd_alias_list_t 140362000 |
| 0x0F | sndcurve | 0x98 | Load_SndCurvePtr 140356DD0 → Load_SndCurve 140356D40 |
| 0x10 | lpfcurve | 0x98 | Load_LpfCurvePtr 140352960 |
| 0x11 | reverbcurve | 0x98 | Load_ReverbCurvePtr 1403559A0 |
| 0x12 | loaded_sound | 0x38 | Load_LoadedSoundPtr 140352600 → Load_LoadedSound 140352560 |
| 0x3D | dopplerpreset | 0x20 | Load_DopplerPresetPtr 14034C150 → Load_DopplerPreset 14034C0C0 |

The three curves and the doppler preset have one pointer each, their name (an XString at +8; the doppler preset's
at +0), and live in the virtual block.

## 3. Alias lists

**snd_alias_list_t (0x18):** aliasName (+0), head (+8), count (+0x10). head is inline (aligned 4) or an offset.

**snd_alias_t (0xC8)**, loaded by Load_snd_alias_tArray (1403620F0):

| Off | Field |
|---|---|
| +0x00 | aliasName |
| +0x08 | subtitle |
| +0x10 | secondaryAliasName |
| +0x18 | chainAliasName |
| +0x20 | mixerGroup |
| +0x28 | SoundFile * (inline, aligned 4, or an offset) |
| +0x30 | sequence (int) |
| +0x34, +0x38 | volMin, volMax |
| +0x3C | volModIndex |
| +0x40, +0x44 | pitchMin, pitchMax |
| +0x48, +0x4C | distMin, distMax |
| +0x50 | velocityMin |
| +0x54 | flags |
| +0x58 | masterPriority (byte) |
| +0x5C, +0x60 | masterPercentage, slavePercentage |
| +0x64 | probability |
| +0x68, +0x6C | lfePercentage, centerPercentage |
| +0x70 | startDelay |
| +0x78 | volumeFalloffCurve (SndCurve asset pointer) |
| +0x80 | lpfCurve |
| +0x88 | reverbSendCurve |
| +0x90..+0x98 | envelopMin, envelopMax, envelopPercentage |
| +0xA0 | SpeakerMap * (inline 0x1A0 bytes with its name at +8, Load_SpeakerMap 140357250; or an offset) |
| +0xA8 | wetMixOverride |
| +0xB0 | occlusion shape (inline 0x20 bytes or an offset) |
| +0xB8 | allowDoppler (byte) |
| +0xC0 | DopplerPreset (asset pointer) |

The five strings are XStrings. The names are the servers' PDB's where the offsets agree; the parameters are read
by position and not all are confirmed by the Store code.

**SoundFile (0x38)**, Load_SoundFile 140357080: type (+0, byte), exists (+1, byte), then at +8:

| Type | Name | At +8 |
|---|---|---|
| 1 | loaded | LoadedSound * (the asset pointer rule) |
| 2 | streamed | StreamedSound (Load_StreamedSound 140357920): StreamFileName (0x18), then totalMsec (+0x18) |
| 3 | primed | PrimedSound (Load_PrimedSound 1403556E0): StreamFileName, then LoadedSound * (+0x18): the start |

**StreamFileName (0x18):** isLocalized (+0, u16), fileIndex (+2, u16), then +8:

- fileIndex 0: raw names, dir and name XStrings (Load_StreamFileNameRaw 140357840);
- otherwise packed: offset (+8, u64) and length (+0x10, u64) into `soundfile<fileIndex>.pak`, or
  `<language>_soundfile<fileIndex>.pak` when localized. Nothing more to load.

## 4. LoadedSound and the audio data

**LoadedSound (0x38):** name (+0), then an XA2Sound (+8, 0x30), Load_XA2Sound 14035C8F0:

| Off (in LoadedSound) | Field |
|---|---|
| +0x08 | data |
| +0x10 | seekTable |
| +0x18 | sampleRate |
| +0x1C | dataByteCount |
| +0x20 | numSamples |
| +0x24 | avgBytesPerSec |
| +0x28 | channels (u16) |
| +0x2A | bitsPerSample (u16) |
| +0x2C | blockAlign (u16) |
| +0x2E | format (byte, snd_format_t: 1 PCM, 7 FLAC; the others are console formats) |
| +0x30 | loadedSize |
| +0x34 | seekTableSize |

**Data.** The data pointer is inline or insert: loadedSize bytes are loaded into the **temp block**, and then the
engine (1406AEBD0) allocates dataByteCount bytes of sound memory (140535BE0), copies the loaded bytes there
(1405362F0) and stores the new address in the LoadedSound (and the insert slot). Any other value is an alias. The
seek table (seekTableSize bytes) is inline in the stream block or an offset.

**What the data is, on PC (common_alien_mp):**

- **Loaded** files are 16-bit PCM (format 1), mono or stereo, at 22050, 44100 or 48000 Hz; dataByteCount equals
  loadedSize.
- **Primed** files are FLAC (format 7). The loaded part is the stream's first FLAC frames, without the fLaC
  header and STREAMINFO block; dataByteCount is the size of all the frames, so the engine's buffer has room for
  the rest, which comes from the pak.
- **Streamed and primed** files' pak ranges are whole FLAC streams (fLaC, STREAMINFO, frames). In the paks seen,
  streams start at 2048-byte-aligned offsets.

## 5. Sound paks

Streams are in `soundfile<N>.pak` beside the zones (DB_DirtyDiscError when one fails to open, docs/assets/images.md).
common_alien_mp's streamed and primed sounds use soundfile62 (90 aliases), 7 (28), 1 (5), 4 (4) and 31 (3).

## 6. Decoder (tools/fastfile/sound.py)

- **Loaders**, statement for statement: load_alias_list_ptr, load_loaded_sound_ptr, the curve and doppler pointers
  (`register(iw6ff.ASSET_LOADERS)`). A stream may set `engine_copy(at, temp, size) -> address` to stand in for the
  engine's copy (without it, the pointer stays in the temp block).
- **Readers:** read_alias_list (aliases with their parameters and files), read_sound_file, read_loaded_sound.
- **Audio:** audio_bytes gives a file's audio and container: a stream's range of its pak (FLAC), a loaded PCM
  sound as a WAVE file, or a primed start's FLAC frames behind a made-up fLaC header and STREAMINFO (flac_header:
  rate, channels, bits and sample count from the LoadedSound, block sizes 16..65535), which ffmpeg decodes. to_wav
  decodes FLAC to WAVE with ffmpeg. extract writes a zone's sounds, one file per alias.
- **Command line:** `python3 tools/fastfile/sound.py <zone.ff> --out <dir> --paks <dir>` uses iw6ff.py's reader,
  which stops at asset types it has no loader for yet (in common_alien_mp, colorizationset 0x39 comes first; weapons
  0x23, vehicles 0x32 and tonemapping 0x3A are also missing,
  some before the sounds). Until it has them, `python3 tests/fastfile/sound_check.py <zone.ff> --extract <out dir>
  [<pak dir>]` extracts from the zone the game loaded in the emulator.

**Tests (tests/fastfile/test_sound.py):** an alias list in hand-made memory (loaded, packed and localized files);
PCM to WAVE; a pak range; FLAC frames with their header stripped (as primed starts are) decoding to the same
samples once flac_header is added; and, with IW6_FASTFILES and IW6_ORIGINALS, the loaders against the game on
common_alien_mp.

## Not established

| What | Status |
|---|---|
| The alias parameters after +0x30 | names and types by position from the servers' layout |
| Occlusion shape (+0xB0) contents | loaded as 0x20 bytes |
| SpeakerMap contents beyond its name | loaded as 0x1A0 bytes |
| Seek tables | none in common_alien_mp |
| Raw (fileIndex 0) stream names | none in common_alien_mp |
