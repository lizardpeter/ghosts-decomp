// Static data in the hybrid build.
//
// Build environment, not game source. A `static` variable in the original (file scope or inside a
// function) lives at a fixed address in the original binary, but it has no public symbol, so it can't
// be linked by name like globals can. While the reconstruction is tested against the original, it
// must read and write that same storage. So reconstructed code declares original statics like this:
//
//     #define IW6_SOURCE "universal/com_math.cpp"   // once per file: the PDB source path
//
//     IW6_STATIC unsigned int holdrand IW6_AT("", "holdrand");
//     IW6_STATIC const float sRGBtoXYZ[4][4] IW6_AT("", "sRGBtoXYZ") IW6_INIT(= { ... });
//
//     int BoxOnPlaneSide(...)
//     {
//         IW6_STATIC int bops_initialized IW6_AT("BoxOnPlaneSide", "bops_initialized");
//
// IW6_AT(scope, name): scope is "" for a file static, or the enclosing function's name.
// tools/build_recon.py resolves every such symbol to the address in analysis/<build>/pdb/statics.tsv.
// IW6_INIT keeps the original initializer readable in the source; in the hybrid build the original
// binary's storage already holds it.
#pragma once

#define IW6_STATIC extern
#define IW6_AT(scope, name) __asm__("iw6s@" IW6_SOURCE "@" scope "@" name)
#define IW6_INIT(...)
