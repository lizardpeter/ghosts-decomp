# Animations (XAnimParts, asset type 2 "xanim")

What the Microsoft Store build loads for an animation, how its data is laid out, and how the game evaluates it.
`tools/fastfile/xanim.py` loads, reads and evaluates animations and adds them to a model's glTF;
`tests/fastfile/xanim_check.py` checks the loader and the evaluator against the game's own code.

## 1. How it was checked

- **Loader.** The Store build's loader runs in the emulator (`tests/fastfile/store_emu.py`) on Point of Contact
  (mp_alien_town, 1077 animations). At a chosen call of `Load_XAnimPartsPtr` (14035D3D0) the stream state is handed
  to `xanim.load_xanim_parts_ptr`; when the game's call returns, the zone position, every block position, the block
  memory and the asset pool must be the same (`world_check.compare`, which can now stop at the call's own return
  for animations loaded from inside other assets, such as weapon animation arrays).
- **Evaluator.** After the game has loaded the zone, its `XAnimCalcParts` (14055EE30 for animations under 256
  frames, 140560280 from 256) and `XAnimCalcNonLoopEnd` (140563620, the last frame) are called on every animation of
  the zone at seven times (0, 0.25, 0.5, 0.999, 1, and two others) with weight 1, an identity bone map and no
  ignored bones. The rotTransArray they accumulate (per bone: quaternion, translation, translation weight) equals
  `xanim.calc_parts` bit for bit for all 1077 × 7 cases, among them 6 animations of 256 frames or more (5 with the
  split frame index tables of section 4) and 100 with no frames; and for all 724 animations of common_alien_mp.ff
  (the Extinction aliens' shared zone: the drone, queen and spitter sets) × 7.
- The translation code masks with `g_keepXYZ` ({~0, ~0, ~0, 0}, Store 149B76820), which a dynamic initializer sets
  at startup; the emulator doesn't run it, so the check sets it first.

## 2. XAnimParts (0x88 bytes; Load_XAnimParts 14035D040)

The servers' PDB layout (iw6_ds_xb3) is the Store build's.

| offset | field | |
|---|---|---|
| +0x00 | name | XString |
| +0x08 | dataByteCount (u16, read as a signed short by the loader) | |
| +0x0A, +0x0C | dataShortCount, dataIntCount (u16) | |
| +0x0E, +0x10 | randomDataByteCount, randomDataIntCount (u16) | |
| +0x12 | numframes (u16) | frame intervals: the animation has numframes + 1 frames |
| +0x14 | flags (u8) | |
| +0x15 | boneCount[10] (u8) | per part group (below); [9] is the total |
| +0x1F | notifyCount (u8) | |
| +0x20, +0x21 | assetType, ikType | |
| +0x24 | randomDataShortCount (u32) | |
| +0x28 | indexCount (u32) | |
| +0x2C, +0x30 | framerate, frequency (float) | |
| +0x38 | names | boneCount[9] script strings, aligned 4 |
| +0x40 | dataByte | unaligned |
| +0x48 | dataShort | aligned 2 |
| +0x50 | dataInt | aligned 4 (floats) |
| +0x58 | randomDataShort | aligned 2 |
| +0x60 | randomDataByte | unaligned |
| +0x68 | randomDataInt | aligned 4 |
| +0x70 | indices | bytes under 256 frames (unaligned), else u16 (aligned 2) |
| +0x78 | notify | notifyCount × {name (script string), time (0..1)}, aligned 4 |
| +0x80 | deltaPart | root motion, aligned 4 (below) |

The stream order is: name, names, notify, deltaPart, dataByte, dataShort, dataInt, randomDataShort, randomDataByte,
randomDataInt, indices. Every pointer is "non-zero means it follows" (no offset form).

**deltaPart** (0x18: trans, quat2, quat; 14035CA20). Each part starts with a u16 size (keys − 1) in an 8-byte
header; size 0 is followed by the single value (trans: 3 floats; quat2: 2 shorts; quat: 4 shorts). Otherwise a
frames header follows (trans: mins[3], size[3] and the keys pointer, 0x20 bytes; quats: the keys pointer), then the
frame index table (size + 1 entries, bytes or u16 as `indices`), then the keys (trans: 3 bytes per key when
smallTrans (+2) is set, else 3 u16 aligned 4; quat2: 2 shorts, quat: 4 shorts per key, aligned 4).

## 3. Part groups

The animation's bones are split into groups, in this order (boneCount[0..8]); `names` lists them in the same order.

| group | data |
|---|---|
| 0 no rotation | the rotation is identity (adds weight to w) |
| 1 2D rotation | keyed (z, w): u16 key count − 1 in dataShort, frame index table, 2 shorts per key in randomDataShort |
| 2 rotation | keyed (x, y, z, w): as above, 4 shorts per key |
| 3 2D rotation, one key | (z, w): 2 shorts in dataShort |
| 4 rotation, one key | 4 shorts in dataShort |
| 5 small translation | bone (a byte of dataByte), keyed: mins and size (6 floats in dataInt), 3 bytes per key in randomDataByte |
| 6 translation | bone byte, keyed: mins and size, 3 u16 per key in randomDataShort (after the rotation keys) |
| 7 one translation | bone byte, 3 floats in dataInt |
| 8 no translation | bone byte (adds weight to the translation weight) |

Rotation groups take bones in order (part 0, 1, ...); translation groups name the part with a byte. Rotation values
are shorts / 32767 (the game's constant 3.051851e-05). A translation is `key × size + mins` per axis.

## 4. Evaluation (XAnimCalcParts)

For normalised time t (0..1), `frame = numframes × t` (float32) and its integer part select a key: the frame index
table holds the frame number of each key, and the key i with `table[i] <= frame < table[i + 1]` is taken; the value
is `k[i] + (k[i+1] − k[i]) × (frame − table[i]) / (table[i+1] − table[i])`, then multiplied by the weight and added
to the bone's accumulators. Rotations are normalised afterwards (XAnimNormalizeRotScaleTransArray), translations
divided by their weight.

Where the frame index tables live:

- **Under 256 frames**: bytes in dataByte, right after the key count (translations: after the bone byte).
- **256 frames and more**: u16 in dataShort after the key count, when a part has fewer than 0x40 keys. From 0x40
  keys the Store build splits the table: dataShort holds a coarse table of every 256th entry (((n − 1) >> 8) + 2
  entries for n + 1 keys) and the full table is in `indices`; the lookup searches the coarse table, then the 256
  entries after it. (The servers' code reads the u16 tables from `indices` only; the PC format differs.)

At t = 1 and for animations without frames the game calls XAnimCalcNonLoopEnd, which takes the last key of every
part (the tables are skipped).

## 5. Applying an animation to a model

The game (the servers' CalcSkelNonRootBones, xanim/dobj_skel.cpp) uses the normalised animation rotation as the
bone's local rotation, and adds the animation translation to the bone's base local translation (the XModel's
`trans`): translations are offsets, not positions. Animation bones are matched to model bones by name.

## 6. Use in glTF

`xanim.sample(anim, t)` gives each animation bone's normalised local rotation and translation (None where the
animation doesn't set one). `xanim.add_to_gltf` adds an animation to a document from `xmodel.to_gltf`, matching
animation bones to the model's bones by name: a rotation channel for every rotated bone and a translation channel
for every translated bone (base translation + offset), one key per frame at the animation's frame rate. The model's other bones keep their base
pose. The root motion (deltaPart) is decoded by `read_xanim` but not applied.

## 7. Not done

- Root motion (the deltaPart) is read but its evaluation (XAnim_CalcDeltaForTime, Store 140565550) is not
  reconstructed or checked.
- Blending, additive animations, animation trees (animclass assets) and notetracks beyond reading them.
- C reconstructions of the loaders and evaluators.
