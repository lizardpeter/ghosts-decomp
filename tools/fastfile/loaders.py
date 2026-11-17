#!/usr/bin/env python3
"""Every asset loader tools/fastfile has, registered into iw6ff.py's reader in one call: register_all().

With it, iw6ff.read_fastfile walks a zone as far as the asset types it can load (Zone.complete when every asset
was). tests/fastfile/zone_check.py compares a whole walked zone with the zone as the game loaded it.
"""
import clipmap
import fx
import gfxworld
import image
import iw6ff
import mapfx
import material
import postfx
import sound
import strings
import weapon
import xanim
import xmodel


def register_all(loaders=None):
    """Add every loader to `loaders` (default iw6ff.ASSET_LOADERS) and set the cross-module asset pointer rules."""
    L = iw6ff.ASSET_LOADERS if loaders is None else loaders
    L.update({t: material.asset_ptr(t, f) for t, f in material.ASSET_LOADERS.items()})
    xmodel_ptr = lambda s, f: xmodel.load_xmodel_ptr(s, f, material.load_material_ptr)  # noqa: E731
    xmodel.register(L, material_loader=material.load_material_ptr)
    image.register(L, material)
    for m in (sound, gfxworld, strings):
        m.register(L)
    xanim.register(L, scriptable_ptr=lambda s, f: clipmap.load_scriptable_def_ptr(s, f, xmodel_ptr),
                   fx_ptr=fx.load_effect_ptr)
    clipmap.register(L, xmodel_ptr=xmodel_ptr)
    fx.register(L, material_ptr=material.load_material_ptr, xmodel_ptr=xmodel_ptr, image_ptr=image.load_gfx_image_ptr)
    postfx.register(L, material_ptr=material.load_material_ptr)
    weapon.register(L, material_ptr=material.load_material_ptr, xmodel_ptr=xmodel_ptr,
                    xanim_ptr=xanim.load_xanim_parts_ptr, fx_ptr=fx.load_effect_ptr, snd=clipmap.load_snd_alias_custom,
                    physpreset_ptr=lambda s, f: xmodel.asset_ptr(s, f, xmodel.ASSET_PHYSPRESET, xmodel.load_physpreset),
                    physcollmap_ptr=lambda s, f: xmodel.asset_ptr(s, f, xmodel.ASSET_PHYSCOLLMAP,
                                                                  xmodel.load_physcollmap))
    mapfx.register(L, material_ptr=material.load_material_ptr, fx_ptr=fx.load_effect_ptr,
                   snd=clipmap.load_snd_alias_custom,
                   physpreset_ptr=lambda s, f: xmodel.asset_ptr(s, f, xmodel.ASSET_PHYSPRESET, xmodel.load_physpreset))
    return L
