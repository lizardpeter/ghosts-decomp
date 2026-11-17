# Fonts (Font_s)

Bitmap fonts: each glyph a rectangle in a texture atlas, as the Microsoft Store build loads them.
`tools/fastfile/font.py` loads and reads them (every font's glyphs as JSON); `src/gfx_d3d/r_font_load_db.cpp`
reconstructs the loaders in C++, matching the exe in `tests/differential/test_font_load.py`.

| Type | Name | Size | Store loader |
|---|---|---|---|
| 0x1D | font | 0x28 | Load_FontHandle 14034CF50 → Load_Font 14034CE20 |

**Font_s (0x28):** name (+0, `fonts/bigFont`), pixelHeight (+8), glyphCount (+0xC), the atlas material (+0x10)
and a glow material (+0x18), and the glyphs (+0x20, -1: glyphCount x 0x18 bytes, aligned 4; another value an
offset).

**Glyph (0x18):** the character (+0, UCS-2), x0 and y0 (+2, +3, signed: the glyph's top left from the pen
position, y0 negative above the baseline), dx (+4, the advance), pixelWidth and pixelHeight (+5, +6), then its
rectangle in the atlas as s0, t0, s1, t1 (+8, 0..1). Drawing a string: for each character, copy the atlas
rectangle (its alpha is the coverage) to pen + (x0, y0) at pixelWidth x pixelHeight, then advance the pen by dx.

## Where they are

english/eng_code_post_gfx_mp.ff has the 14 multiplayer fonts, all in one atlas, `fonts/gamefonts_pc` (BC3,
1024x1404, in the zone): normalFont, boldFont, objectiveFont (35 px), bigFont (65), extraBigFont (42),
smallFont, consoleFont (14), the HUD fonts (20, 25, 30) and the digital HUD fonts (20, 26, 30, 40 px, 96 glyphs);
the text fonts have 268 to 325 glyphs (Latin-1 and more).

## How it was checked

- **Whole zone.** english/eng_code_post_gfx_mp.ff (161 assets: its 14 fonts, 139 string tables, materials, sounds),
  which used to stop at its first font, walked by `tools/fastfile/loaders.py` equals the game's
  (`tests/fastfile/zone_check.py --full`).
- **Drawn.** Text set from the read glyphs and the atlas (bigFont, hudDigitalFont40) reads correctly, with even
  spacing and baselines.
- **C++.** Load_Font and Load_FontHandle match the exe on random structures; five mutations (material order, glyph
  size, alignment, the offset case, the stream flag) each fail a test.

## Not established

| What | Status |
|---|---|
| What the glow material is used for | not looked at |
| The game's text drawing (R_DrawText and the glyph lookup) | not reconstructed |
