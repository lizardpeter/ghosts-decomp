# Effects (FxEffectDef "fx", GfxLightDef "lightdef", FxParticleSimAnimation "particlesimanimation")

What the Microsoft Store build loads for an effect and how it is laid out. `tools/fastfile/fx.py` loads and reads
effects; `tests/fastfile/fx_check.py` checks the loader against the game's own code; `src/effectscore/fx_load_db.cpp`
reconstructs the loaders in C++.

## 1. How it was checked

- **Loader against the game.** The Store build's loaders run in the emulator (`tests/fastfile/store_emu.py`). At a
  chosen call of `Load_FxEffectDefHandle` (14034D120) the stream state is handed to `fx.load_effect_ptr`; when the
  game's call returns, the zone position, every block position, the block memory and the asset pool must be the same
  (`world_check.compare`). Equal for calls 0, 1, 20, 100 and 172 of common_alien_mp (the Extinction aliens' shared
  zone) and 0, 100, 200, 300, 400 and 500 of mp_alien_town (Point of Contact).
- **C++.** `src/effectscore/fx_load_db.cpp` reconstructs the 13 loaders (Load_FxEffectDefHandle down to the trail
  and flare definitions, and the GfxLightDef and FxParticleSimAnimation loaders), each tested against the Store exe
  in `tests/differential/test_fx_load.py` (200 or 300 random inputs each; 16 deliberate mutations, among them a wrong
  count, alignment, element type, call order or missing reference, all fail).
- **Reader.** `fx.read_effect` on every effect of common_alien_mp as the game loaded it: 175 effects, 881 elements.

## 2. Asset types

| Type | Name | Header | Store loader |
|---|---|---|---|
| 0x25 | fx (FxEffectDef) | 0x40 | Load_FxEffectDefHandle 14034D120 → Load_FxEffectDef 14034D040 |
| 0x1B | lightdef (GfxLightDef) | 0x30 | Load_GfxLightDefPtr 14034F560 → Load_GfxLightDef 14034F470 |
| 0x3E | particlesimanimation (FxParticleSimAnimation) | 0x60 | Load_FxParticleSimAnimationPtr 14034E760 → Load_FxParticleSimAnimation 14034E5D0 |

Light defs and particle animations are loaded inline from an effect's visuals (or as assets of their own). The
particle animation's header is aligned to 32; every other header to 4.

## 3. FxEffectDef (0x40)

| Off | Field |
|---|---|
| +0x00 | name |
| +0x08 | flags |
| +0x0C | totalSize |
| +0x10 | msecLoopingLife |
| +0x14 | elemDefCountLooping |
| +0x18 | elemDefCountOneShot |
| +0x1C | elemDefCountEmission |
| +0x20 | elemMaxRadius |
| +0x24 | occlusionQueryDepthBias |
| +0x28, +0x2C | occlusionQueryFadeIn, occlusionQueryFadeOut |
| +0x30 | occlusionQueryScaleRange (FxFloatRange) |
| +0x38 | elemDefs: looping, then one-shot, then emission elements |

The loader takes **any** non-null elemDefs as inline (aligned 4): there is no offset form. The element count is the
sum of the three counts, added as ints and sign-extended.

## 4. FxElemDef (0x138), Load_FxElemDefArray 14034D340

The layout is the servers' PDB's. Ranges are FxFloatRange / FxIntRange `{base, amplitude}`.

| Off | Field |
|---|---|
| +0x000, +0x004 | flags, flags2 |
| +0x008 | spawn: looping {intervalMsec, count} or one-shot count range |
| +0x010 | spawnRange |
| +0x018, +0x020 | fadeInRange, fadeOutRange |
| +0x028 | spawnFrustumCullRadius |
| +0x02C, +0x034 | spawnDelayMsec, lifeSpanMsec |
| +0x03C | spawnOrigin[3] |
| +0x054, +0x05C | spawnOffsetRadius, spawnOffsetHeight |
| +0x064 | spawnAngles[3] |
| +0x07C | angularVelocity[3] |
| +0x094 | initialRotation |
| +0x09C | gravity |
| +0x0A4 | reflectionFactor |
| +0x0AC | atlas (behavior, index, fps, loopCount, colIndexBits, rowIndexBits, entryCount) |
| +0x0B4 | elemType (section 5) |
| +0x0B5 | elemLitType |
| +0x0B6 | visualCount |
| +0x0B7 | velIntervalCount |
| +0x0B8 | visStateIntervalCount |
| +0x0C0 | velSamples: velIntervalCount + 1 × FxElemVelStateSample (0x60: local and world {velocity, totalDelta} as base + amplitude vectors) |
| +0x0C8 | visSamples: visStateIntervalCount + 1 × FxElemVisStateSample (0x50: base and amplitude {color[4], unlitHDRScale, rotationDelta, rotationTotal, size[2], scale}) |
| +0x0D0 | visuals (below) |
| +0x0D8 | collBounds (midpoint, half size) |
| +0x0F0, +0x0F8, +0x100 | effectOnImpact, effectOnDeath, effectEmitted (FxEffectDefRef) |
| +0x108, +0x110 | emitDist, emitDistVariance |
| +0x118 | extended (below) |
| +0x120..+0x123 | sortOrder, lightingFrac, useItemClip, fadeInfo |
| +0x124 | randomSeed |
| +0x128 | litMaxColorChangePerSec |
| +0x12C | unlitHDRScalar |

**Samples:** any non-null pointer is inline, aligned 4.

**Effect references** (the servers' Load_FxEffectDefRef, inline in the Store build): the name's XString rule, then
Load_FxEffectDefFromName (140371ED0) replaces a non-null name with what DB_FindXAssetHeader (type 0x25) finds. An
effect of another zone leaves no name behind once loaded, so fx.py keeps the names it saw in `s.fx_ref_names`, and
fx_check.py records them from the game's calls.

**Visuals** (Load_FxElemDefVisuals 14034D600):

- a **decal** has a mark array (any non-null value: aligned 4): visualCount × 0x18, three material handles each
  (Load_MaterialHandleArray, 3);
- with visualCount 0 or 1, the one visual is the field itself (Load_FxElemVisuals 14034D900);
- otherwise an array of visualCount (any non-null value: aligned 4; Load_FxElemVisualsArray 14034D9E0).

A visual, by element type: a model (Load_XModelPtr), a runner's effect reference (as above), a sound or vector
field name (XString), a particle animation, nothing for an omni light, a light def for a spot light, and a material
for everything else.

**Extended definitions** (Load_FxElemExtendedDefPtr 14034D750), inline (aligned 4) when -1, else an offset:

| Type | Struct | Size | Then |
|---|---|---|---|
| trail | FxTrailDef (Load_FxTrailDef 14034E850) | 0x30 | vertCount × 0x18 vertices (pos[2], normal[2], texCoord[2]), aligned 4; indCount u16 indices, aligned 2 |
| spark fountain | FxSparkFountainDef | 0x34 | |
| spot light | FxSpotLightDef | 0x18 | |
| flare | FxFlareDef (Load_FxFlareDef 14034DBD0) | 0x70 | four curves of intervalCount + 1 floats (intensityX, intensityY, srcCosIntensity, srcCosScale) |

For any other type a non-null value gets one byte at the stream position, unaligned (the generator's unknownDef;
varvoid, 144424A08, points at it).

## 5. Element types

The Store build's numbers, by what its loaders do with each value and, for 8 and 9, by the materials their elements
use (cloud_whitesmoke, spark_rndhit_64):

| Store | Type | Servers |
|---|---|---|
| 0 | sprite billboard | 0 |
| 1 | sprite oriented | 1 |
| 2 | tail | 2 |
| 3 | trail (extended: FxTrailDef) | 3 |
| 4 | flare (extended: FxFlareDef) | 4 |
| 5 | particle simulation animation (visual: FxParticleSimAnimation) | 5 |
| 6, 7 | not identified (material visuals; none in the zones checked) | |
| 8 | cloud | 6 |
| 9 | spark cloud | 7 |
| 10 | spark fountain (extended: FxSparkFountainDef) | 8 |
| 11 | model (visual: XModel) | 9 |
| 12 | omni light (no visual) | 10 |
| 13 | spot light (visual: GfxLightDef; extended: FxSpotLightDef) | 11 |
| 14 | sound (visual: alias name) | 12 |
| 15 | decal (visuals: mark arrays) | 13 |
| 16 | runner (visual: effect reference) | 14 |
| 17 | vector field (visual: name) | 15 |

In common_alien_mp: 461 billboards, 152 tails, 95 models, 69 omni lights, 47 runners, 17 spark fountains, 15 trails,
6 sounds, 6 decals, 5 oriented sprites, 4 clouds, 2 spark clouds, 2 flares; every element has velocity samples and
834 of 881 visual-state samples. Most elements (764) have one visual, 2 have none, the rest 2 to 6.

## 6. GfxLightDef (0x30) and FxParticleSimAnimation (0x60)

**GfxLightDef:** name (+0), attenuation (+8) and cucoloris (+0x18) GfxLightImage (image pointer, samplerState), each
image by Load_GfxImagePtr; lmapLookupStart (+0x28).

**FxParticleSimAnimation:** name (+0), material (+8), a 0x38-byte header (+0x10: playbackRate, duration, frameCount,
min xyz, bounds deltas, maxWidth, maxHeight, colorTableSize, particleDataCount, two flags), then particleData
(+0x48: particleDataCount × 0x20, aligned 32), frames (+0x50: frameCount × {particleDataOffset,
numActiveParticles}, aligned 4) and colorTable (+0x58: colorTableSize × 4 floats, aligned 4).

## 7. Decoder (tools/fastfile/fx.py)

- **Loaders:** load_effect_ptr, load_light_def_ptr, load_particle_sim_animation_ptr, statement for statement;
  `register(iw6ff.ASSET_LOADERS, material_ptr=, xmodel_ptr=, image_ptr=)` adds them and the asset pointer rules
  they call.
- **Reader:** read_effect gives an Effect with its elements: every field above, visuals by name, the velocity and
  visual-state samples, the extended definitions with their arrays. to_json makes it plain data.
- **Tests (tests/fastfile/test_fx.py):** a hand-made effect with samples, a trail, a decal and an unknown extension
  (what the loader consumes, where the pointers go, what the reader gives back); offsets; and, with IW6_FASTFILES and
  IW6_ORIGINALS, the loader against the game on common_alien_mp.

## Not established

| What | Status |
|---|---|
| Element types 6 and 7 | none in the zones checked; loaded as material visuals |
| flags, flags2, elemLitType values | read, not decoded |
| How the game evaluates the samples (FX_ code) | not reconstructed |
| Impact tables (impactfx 0x26), surface effects (0x27), map effects (fx_map 0x19), vector fields (0x3C) | not loaded yet |
