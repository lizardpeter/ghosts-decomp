# Field of view

How the client turns `cg_fov` into the renderer's projection, from the Microsoft Store build
(`iw6mp64_MSStore_ship`). Reconstructed and tested: `src/cgame/cg_camera.cpp` (CG_GetViewFov, CG_CalcFov,
sub_1402E9060) and the tangent helper at the end of `src/universal/com_math.cpp` (sub_140532D80).

## Once a frame

1. **CG_GetViewFov** (1402E8D20) picks the FOV in degrees.
   - Special cases come first: 90 for pm_type 6; the weapon's ADS FOV while linkFlags 4 is set; `missileRemoteFOV`
     on a remote missile's camera; another remote camera's own FOV; a scripted FOV (eFlags 0x3800 or
     otherFlags 0x200000); and a hybrid scope's two FOVs and the switch between them.
   - Otherwise it starts from `cg_fov`. For a weapon that zooms, it blends toward the ADS FOV by the zoom
     fraction (CG_GetWeaponZoom): `fov = (1 - z)·cg_fov + z·min(cg_fov, adsFov)`. The ADS FOV is the
     variable-zoom scope's level if there is one, otherwise BG_ADSZoomFov.
   - Then it multiplies by `cg_fovScale` and by 0.9 in third person, applies two camera adjustments, and clamps
     to [`cg_fovMin`, 170].
2. **CG_CalcFov** (1402EB4D0) turns that FOV into the refdef's tangents:
   - `tan(fovY/2) = 0.75·tan(fov/2)`
   - `tan(fovX/2) = tan(fovY/2)·viewAspect·viewMult`
   - It also sets `zoomSensitivity = tan(fov/2) / tan(32.5°)`.
3. **The renderer** (140657FF0 → 140658120) copies the tangents into the view parameters and builds the
   perspective matrix from them and the near plane (`r_znear`, 4 by default).

So `cg_fov` is the **horizontal FOV of a 4:3 view**. The vertical FOV depends only on it, and wider windows see
more at the sides (Hor+), as in CoD4 to MW3.

| cg_fov | horizontal at 16:9 |
|---:|---:|
| 65 (default and minimum) | 80.7° |
| 70 | 86.1° |
| 73.74 | 90.0° |
| 80 (maximum) | 96.4° |

MW2019's FOV setting is the horizontal FOV at 16:9. To get the same view, use
`cg_fov = 2·atan(0.75·tan(F/2))`. MW2019's default of 80 gives 64.37. The full table is in docs/roadmap.md §8.

## FOV and mouse sensitivity

The client sends `zoomSensitivity` to CL_SetFOVSensitivityScale (from 1402AB060, multiplied by a script-set
factor when that factor is nonzero). It becomes `clientActive_t::cgameFOVSensitivityScale`, which multiplies every
mouse movement (docs/input.md). The scale is measured against the fixed 65, not against your own `cg_fov`, and it
applies to hip fire as well as ADS. That has two consequences (B0023):

- **Hip-fire sensitivity grows with `cg_fov`.** It is ×1.0 at 65, ×1.099 at 70 and ×1.317 at 80.
- **ADS sensitivity does not depend on `cg_fov`.** It is tan(adsFov/2)/tan(32.5°) whatever the hip FOV.

For the same turn per mouse count as MW2019 sensitivity 1.5 (0.0099° per count, 28.9 cm/360 at 3200 DPI), divide
0.45 by the factor:

| cg_fov | factor | sensitivity |
|---:|---:|---:|
| 64.37 (MW2019 FOV 80) | 0.988 | 0.456 |
| 65 | 1.000 | 0.450 |
| 70 | 1.099 | 0.409 |
| 80 | 1.317 | 0.342 |

## Aspect ratio

`cgs.viewAspect` comes from `cls.vidConfig.windowAspectRatio`. The renderer's window setup (140630670, like
Black Ops' R_StoreWindowSettings) chooses it from `r_aspectRatio`: auto, standard 4:3, wide 16:10 or wide 16:9.

With auto, it rounds the window's shape to one of the three:

- 16:10 when `floor(16·h/w + 0.5)` is 10;
- 16:9 when it is below 10;
- 4:3 when it is above 10.

A per-mode flag can force 16:9. As a result, ultrawide windows (21:9, 32:9) are projected as 16:9 and stretched
sideways, and 5:4 is projected as 4:3 (B0021). The enhanced build will use the real ratio.

## Limits worth changing

- B0021: the aspect ratio is rounded to 4:3, 16:10 or 16:9 (ultrawide is stretched).
- B0022: `cg_fov` only goes from 65 to 80.
- B0023: the FOV sensitivity scale is relative to 65 and also applies to hip fire.
- B0024: `com_maxfps` is capped at 100 (default 85).
