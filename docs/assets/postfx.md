# Post-processing (Colorization, ColorizationSet, ToneMapping)

The colour grading and filmic tone curve a map or vision set uses, as the Microsoft Store build loads them.
`tools/fastfile/postfx.py` loads and reads them; `src/gfx_d3d/r_postfx_load_db.cpp` reconstructs the six loaders in
C++, each matching the exe in `tests/differential/test_misc_asset_load.py`. Whole real zones with them are equal to
the game (docs/fastfiles.md, section 12).

| Type | Name | Size | Store loader |
|---|---|---|---|
| 0x38 | colorization | 0x30 | Load_ColorizationPtr 14034B8C0 → Load_Colorization 14034B830 |
| 0x39 | colorizationset | 0x68 | Load_ColorizationSetPtr 14034BAD0 → Load_ColorizationSet 14034B9B0 |
| 0x3A | tonemapping | 0x70 | Load_ToneMappingPtr 140358440 → Load_ToneMapping 1403583B0 |

**Colorization (0x30):** the renderer's GfxColorization constants, then the name (+0x28):

| Off | Field |
|---|---|
| +0x00 | powerAndDesaturation[4] |
| +0x10 | scale[3] |
| +0x1C | bias[3] |
| +0x28 | name |

**ColorizationSet (0x68):** name, lowAndHighEndPoints[4] (+8), midEndPoints[4] (+0x18),
alternateDepthScaleAndBias[2] (+0x28), five colorizations (+0x30 colorization, +0x38 alternate, +0x40 low, +0x48 mid,
+0x50 high; each an asset pointer, usually to a colorization of the same zone), alternateMaskMaterial (+0x58), flags
(+0x60).

**ToneMapping (0x70):** the renderer's GfxToneMapping, per colour channel: toeStrength, toeAngleNumerator,
toeAngleDenominator, linearStrength, linearAngle, shoulderStrength, whitePoint, exposure (3 floats each from +0), and
adaptationRates[2] (+0x60); the name at +0x68. How the shaders evaluate the curve is not established here.

The layouts are the servers' PDBs'. `postfx.read_colorization`, `read_colorization_set` and `read_tone_mapping` give
them as dataclasses.
