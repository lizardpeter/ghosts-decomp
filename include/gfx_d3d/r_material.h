// gfx_d3d/r_material.h: materials, technique sets, techniques, passes, shaders and vertex declarations as the
// Microsoft Store build (iw6mp64_MSStore_ship) loads them from fastfiles. docs/assets/materials.md describes every
// field, the stream layout and what is verified.
//
// Names and types are the server PDBs' (iw6_ds_xb3/iw6_ds_ps4, gfx_d3d/r_material_load_db.h and tr_types). The PC
// client's layouts differ from the servers': the servers strip everything a dedicated server does not draw, and the
// PC adds a fourth group of 103 techniques (412 instead of 309), so Material and MaterialTechniqueSet are larger. Every
// offset asserted here is read by the Store build's loaders (src/gfx_d3d/r_material_load_db.cpp) or by the renderer
// code named next to it.
#pragma once

struct ID3D11Buffer;
struct ID3D11VertexShader;
struct ID3D11HullShader;
struct ID3D11DomainShader;
struct ID3D11PixelShader;
struct ID3D11InputLayout;
struct GfxImage;

// ---- enums --------------------------------------------------------------------------------------------------------

// Technique slots of a technique set. The server PDB names 309 (three groups of 103: standard, instanced,
// no-displacement). The Store build has 412: R_SetupDrawGroup's PC counterpart (1406148D0) adds 0x67 for instanced
// static models, 0xCE for surface types 7, 13 and 14 (a group the servers lack: Catmull-Clark subdivision patches,
// whose techniques the game's technique sets name subdiv_patch_* and draw with hull and domain shaders; the
// SUBDIV_PATCH_ prefix is ours) and 0x135 for the no-displacement variant, and Load_MaterialTechniqueSet reads 0x19C
// pointers.
enum MaterialTechniqueType
{
	// standard: 0x0..0x66
	TECHNIQUE_DEPTH_PREPASS = 0x0,
	TECHNIQUE_BUILD_SHADOWMAP_DEPTH = 0x1,
	TECHNIQUE_UNLIT = 0x2,
	TECHNIQUE_EMISSIVE = 0x3,
	TECHNIQUE_EMISSIVE_DFOG = 0x4,
	TECHNIQUE_EMISSIVE_SHADOW = 0x5,
	TECHNIQUE_EMISSIVE_SHADOW_DFOG = 0x6,
	TECHNIQUE_LIT = 0x7,
	TECHNIQUE_LIT_DIR = 0x8,
	TECHNIQUE_LIT_DIR_SHADOW = 0x9,
	TECHNIQUE_LIT_SPOT = 0xa,
	TECHNIQUE_LIT_SPOT_SHADOW = 0xb,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS = 0xc,
	TECHNIQUE_LIT_OMNI = 0xd,
	TECHNIQUE_LIT_OMNI_SHADOW = 0xe,
	TECHNIQUE_LIT_DIR_SPOT = 0xf,
	TECHNIQUE_LIT_DIR_SPOT_SHADOW = 0x10,
	TECHNIQUE_LIT_DIR_SPOT_SHADOW_CUCOLORIS = 0x11,
	TECHNIQUE_LIT_DIR_OMNI = 0x12,
	TECHNIQUE_LIT_DIR_OMNI_SHADOW = 0x13,
	TECHNIQUE_LIT_DIR_SHADOW_SPOT = 0x14,
	TECHNIQUE_LIT_DIR_SHADOW_SPOT_SHADOW = 0x15,
	TECHNIQUE_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS = 0x16,
	TECHNIQUE_LIT_DIR_SHADOW_OMNI = 0x17,
	TECHNIQUE_LIT_DIR_SHADOW_OMNI_SHADOW = 0x18,
	TECHNIQUE_LIT_SPOT_SPOT = 0x19,
	TECHNIQUE_LIT_SPOT_SPOT_SHADOW = 0x1a,
	TECHNIQUE_LIT_SPOT_SPOT_SHADOW_CUCOLORIS = 0x1b,
	TECHNIQUE_LIT_SPOT_OMNI = 0x1c,
	TECHNIQUE_LIT_SPOT_OMNI_SHADOW = 0x1d,
	TECHNIQUE_LIT_SPOT_SHADOW_SPOT = 0x1e,
	TECHNIQUE_LIT_SPOT_SHADOW_SPOT_SHADOW = 0x1f,
	TECHNIQUE_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS = 0x20,
	TECHNIQUE_LIT_SPOT_SHADOW_OMNI = 0x21,
	TECHNIQUE_LIT_SPOT_SHADOW_OMNI_SHADOW = 0x22,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_SPOT = 0x23,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW = 0x24,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS = 0x25,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_OMNI = 0x26,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW = 0x27,
	TECHNIQUE_LIT_OMNI_OMNI = 0x28,
	TECHNIQUE_LIT_OMNI_OMNI_SHADOW = 0x29,
	TECHNIQUE_LIT_OMNI_SHADOW_OMNI = 0x2a,
	TECHNIQUE_LIT_OMNI_SHADOW_OMNI_SHADOW = 0x2b,
	TECHNIQUE_LIT_DYNAMIC_BRANCHING_CUCOLORIS = 0x2c,
	TECHNIQUE_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS = 0x2d,
	TECHNIQUE_LIT_DYNAMIC_BRANCHING = 0x2e,
	TECHNIQUE_LIT_SUN_DYNAMIC_BRANCHING = 0x2f,
	TECHNIQUE_LIT_DFOG = 0x30,
	TECHNIQUE_LIT_DIR_DFOG = 0x31,
	TECHNIQUE_LIT_DIR_SHADOW_DFOG = 0x32,
	TECHNIQUE_LIT_SPOT_DFOG = 0x33,
	TECHNIQUE_LIT_SPOT_SHADOW_DFOG = 0x34,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x35,
	TECHNIQUE_LIT_OMNI_DFOG = 0x36,
	TECHNIQUE_LIT_OMNI_SHADOW_DFOG = 0x37,
	TECHNIQUE_LIT_DIR_SPOT_DFOG = 0x38,
	TECHNIQUE_LIT_DIR_SPOT_SHADOW_DFOG = 0x39,
	TECHNIQUE_LIT_DIR_SPOT_SHADOW_CUCOLORIS_DFOG = 0x3a,
	TECHNIQUE_LIT_DIR_OMNI_DFOG = 0x3b,
	TECHNIQUE_LIT_DIR_OMNI_SHADOW_DFOG = 0x3c,
	TECHNIQUE_LIT_DIR_SHADOW_SPOT_DFOG = 0x3d,
	TECHNIQUE_LIT_DIR_SHADOW_SPOT_SHADOW_DFOG = 0x3e,
	TECHNIQUE_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0x3f,
	TECHNIQUE_LIT_DIR_SHADOW_OMNI_DFOG = 0x40,
	TECHNIQUE_LIT_DIR_SHADOW_OMNI_SHADOW_DFOG = 0x41,
	TECHNIQUE_LIT_SPOT_SPOT_DFOG = 0x42,
	TECHNIQUE_LIT_SPOT_SPOT_SHADOW_DFOG = 0x43,
	TECHNIQUE_LIT_SPOT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x44,
	TECHNIQUE_LIT_SPOT_OMNI_DFOG = 0x45,
	TECHNIQUE_LIT_SPOT_OMNI_SHADOW_DFOG = 0x46,
	TECHNIQUE_LIT_SPOT_SHADOW_SPOT_DFOG = 0x47,
	TECHNIQUE_LIT_SPOT_SHADOW_SPOT_SHADOW_DFOG = 0x48,
	TECHNIQUE_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0x49,
	TECHNIQUE_LIT_SPOT_SHADOW_OMNI_DFOG = 0x4a,
	TECHNIQUE_LIT_SPOT_SHADOW_OMNI_SHADOW_DFOG = 0x4b,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_DFOG = 0x4c,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_DFOG = 0x4d,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS_DFOG = 0x4e,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_DFOG = 0x4f,
	TECHNIQUE_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW_DFOG = 0x50,
	TECHNIQUE_LIT_OMNI_OMNI_DFOG = 0x51,
	TECHNIQUE_LIT_OMNI_OMNI_SHADOW_DFOG = 0x52,
	TECHNIQUE_LIT_OMNI_SHADOW_OMNI_DFOG = 0x53,
	TECHNIQUE_LIT_OMNI_SHADOW_OMNI_SHADOW_DFOG = 0x54,
	TECHNIQUE_LIT_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0x55,
	TECHNIQUE_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0x56,
	TECHNIQUE_LIT_DYNAMIC_BRANCHING_DFOG = 0x57,
	TECHNIQUE_LIT_SUN_DYNAMIC_BRANCHING_DFOG = 0x58,
	TECHNIQUE_LIGHT_SPOT = 0x59,
	TECHNIQUE_LIGHT_OMNI = 0x5a,
	TECHNIQUE_LIGHT_SPOT_SHADOW = 0x5b,
	TECHNIQUE_LIGHT_SPOT_SHADOW_CUCOLORIS = 0x5c,
	TECHNIQUE_FAKELIGHT_NORMAL = 0x5d,
	TECHNIQUE_FAKELIGHT_VIEW = 0x5e,
	TECHNIQUE_SUNLIGHT_PREVIEW = 0x5f,
	TECHNIQUE_CASE_TEXTURE = 0x60,
	TECHNIQUE_WIREFRAME_SOLID = 0x61,
	TECHNIQUE_WIREFRAME_SHADED = 0x62,
	TECHNIQUE_THERMAL = 0x63,
	TECHNIQUE_VELOCITY_RIGID = 0x64,
	TECHNIQUE_VELOCITY_SKINNED = 0x65,
	TECHNIQUE_DEBUG_BUMPMAP = 0x66,
	// instanced: 0x67..0xcd
	TECHNIQUE_INSTANCED_DEPTH_PREPASS = 0x67,
	TECHNIQUE_INSTANCED_BUILD_SHADOWMAP_DEPTH = 0x68,
	TECHNIQUE_INSTANCED_UNLIT = 0x69,
	TECHNIQUE_INSTANCED_EMISSIVE = 0x6a,
	TECHNIQUE_INSTANCED_EMISSIVE_DFOG = 0x6b,
	TECHNIQUE_INSTANCED_EMISSIVE_SHADOW = 0x6c,
	TECHNIQUE_INSTANCED_EMISSIVE_SHADOW_DFOG = 0x6d,
	TECHNIQUE_INSTANCED_LIT = 0x6e,
	TECHNIQUE_INSTANCED_LIT_DIR = 0x6f,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW = 0x70,
	TECHNIQUE_INSTANCED_LIT_SPOT = 0x71,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW = 0x72,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS = 0x73,
	TECHNIQUE_INSTANCED_LIT_OMNI = 0x74,
	TECHNIQUE_INSTANCED_LIT_OMNI_SHADOW = 0x75,
	TECHNIQUE_INSTANCED_LIT_DIR_SPOT = 0x76,
	TECHNIQUE_INSTANCED_LIT_DIR_SPOT_SHADOW = 0x77,
	TECHNIQUE_INSTANCED_LIT_DIR_SPOT_SHADOW_CUCOLORIS = 0x78,
	TECHNIQUE_INSTANCED_LIT_DIR_OMNI = 0x79,
	TECHNIQUE_INSTANCED_LIT_DIR_OMNI_SHADOW = 0x7a,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_SPOT = 0x7b,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_SPOT_SHADOW = 0x7c,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS = 0x7d,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_OMNI = 0x7e,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_OMNI_SHADOW = 0x7f,
	TECHNIQUE_INSTANCED_LIT_SPOT_SPOT = 0x80,
	TECHNIQUE_INSTANCED_LIT_SPOT_SPOT_SHADOW = 0x81,
	TECHNIQUE_INSTANCED_LIT_SPOT_SPOT_SHADOW_CUCOLORIS = 0x82,
	TECHNIQUE_INSTANCED_LIT_SPOT_OMNI = 0x83,
	TECHNIQUE_INSTANCED_LIT_SPOT_OMNI_SHADOW = 0x84,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_SPOT = 0x85,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_SPOT_SHADOW = 0x86,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS = 0x87,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_OMNI = 0x88,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_OMNI_SHADOW = 0x89,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_SPOT = 0x8a,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW = 0x8b,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS = 0x8c,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_OMNI = 0x8d,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW = 0x8e,
	TECHNIQUE_INSTANCED_LIT_OMNI_OMNI = 0x8f,
	TECHNIQUE_INSTANCED_LIT_OMNI_OMNI_SHADOW = 0x90,
	TECHNIQUE_INSTANCED_LIT_OMNI_SHADOW_OMNI = 0x91,
	TECHNIQUE_INSTANCED_LIT_OMNI_SHADOW_OMNI_SHADOW = 0x92,
	TECHNIQUE_INSTANCED_LIT_DYNAMIC_BRANCHING_CUCOLORIS = 0x93,
	TECHNIQUE_INSTANCED_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS = 0x94,
	TECHNIQUE_INSTANCED_LIT_DYNAMIC_BRANCHING = 0x95,
	TECHNIQUE_INSTANCED_LIT_SUN_DYNAMIC_BRANCHING = 0x96,
	TECHNIQUE_INSTANCED_LIT_DFOG = 0x97,
	TECHNIQUE_INSTANCED_LIT_DIR_DFOG = 0x98,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_DFOG = 0x99,
	TECHNIQUE_INSTANCED_LIT_SPOT_DFOG = 0x9a,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_DFOG = 0x9b,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x9c,
	TECHNIQUE_INSTANCED_LIT_OMNI_DFOG = 0x9d,
	TECHNIQUE_INSTANCED_LIT_OMNI_SHADOW_DFOG = 0x9e,
	TECHNIQUE_INSTANCED_LIT_DIR_SPOT_DFOG = 0x9f,
	TECHNIQUE_INSTANCED_LIT_DIR_SPOT_SHADOW_DFOG = 0xa0,
	TECHNIQUE_INSTANCED_LIT_DIR_SPOT_SHADOW_CUCOLORIS_DFOG = 0xa1,
	TECHNIQUE_INSTANCED_LIT_DIR_OMNI_DFOG = 0xa2,
	TECHNIQUE_INSTANCED_LIT_DIR_OMNI_SHADOW_DFOG = 0xa3,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_SPOT_DFOG = 0xa4,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_SPOT_SHADOW_DFOG = 0xa5,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0xa6,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_OMNI_DFOG = 0xa7,
	TECHNIQUE_INSTANCED_LIT_DIR_SHADOW_OMNI_SHADOW_DFOG = 0xa8,
	TECHNIQUE_INSTANCED_LIT_SPOT_SPOT_DFOG = 0xa9,
	TECHNIQUE_INSTANCED_LIT_SPOT_SPOT_SHADOW_DFOG = 0xaa,
	TECHNIQUE_INSTANCED_LIT_SPOT_SPOT_SHADOW_CUCOLORIS_DFOG = 0xab,
	TECHNIQUE_INSTANCED_LIT_SPOT_OMNI_DFOG = 0xac,
	TECHNIQUE_INSTANCED_LIT_SPOT_OMNI_SHADOW_DFOG = 0xad,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_SPOT_DFOG = 0xae,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_SPOT_SHADOW_DFOG = 0xaf,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0xb0,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_OMNI_DFOG = 0xb1,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_OMNI_SHADOW_DFOG = 0xb2,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_DFOG = 0xb3,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_DFOG = 0xb4,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS_DFOG = 0xb5,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_DFOG = 0xb6,
	TECHNIQUE_INSTANCED_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW_DFOG = 0xb7,
	TECHNIQUE_INSTANCED_LIT_OMNI_OMNI_DFOG = 0xb8,
	TECHNIQUE_INSTANCED_LIT_OMNI_OMNI_SHADOW_DFOG = 0xb9,
	TECHNIQUE_INSTANCED_LIT_OMNI_SHADOW_OMNI_DFOG = 0xba,
	TECHNIQUE_INSTANCED_LIT_OMNI_SHADOW_OMNI_SHADOW_DFOG = 0xbb,
	TECHNIQUE_INSTANCED_LIT_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0xbc,
	TECHNIQUE_INSTANCED_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0xbd,
	TECHNIQUE_INSTANCED_LIT_DYNAMIC_BRANCHING_DFOG = 0xbe,
	TECHNIQUE_INSTANCED_LIT_SUN_DYNAMIC_BRANCHING_DFOG = 0xbf,
	TECHNIQUE_INSTANCED_LIGHT_SPOT = 0xc0,
	TECHNIQUE_INSTANCED_LIGHT_OMNI = 0xc1,
	TECHNIQUE_INSTANCED_LIGHT_SPOT_SHADOW = 0xc2,
	TECHNIQUE_INSTANCED_LIGHT_SPOT_SHADOW_CUCOLORIS = 0xc3,
	TECHNIQUE_INSTANCED_FAKELIGHT_NORMAL = 0xc4,
	TECHNIQUE_INSTANCED_FAKELIGHT_VIEW = 0xc5,
	TECHNIQUE_INSTANCED_SUNLIGHT_PREVIEW = 0xc6,
	TECHNIQUE_INSTANCED_CASE_TEXTURE = 0xc7,
	TECHNIQUE_INSTANCED_WIREFRAME_SOLID = 0xc8,
	TECHNIQUE_INSTANCED_WIREFRAME_SHADED = 0xc9,
	TECHNIQUE_INSTANCED_THERMAL = 0xca,
	TECHNIQUE_INSTANCED_VELOCITY_RIGID = 0xcb,
	TECHNIQUE_INSTANCED_VELOCITY_SKINNED = 0xcc,
	TECHNIQUE_INSTANCED_DEBUG_BUMPMAP = 0xcd,
	// subdivision patches (PC only): 0xce..0x134
	TECHNIQUE_SUBDIV_PATCH_DEPTH_PREPASS = 0xce,
	TECHNIQUE_SUBDIV_PATCH_BUILD_SHADOWMAP_DEPTH = 0xcf,
	TECHNIQUE_SUBDIV_PATCH_UNLIT = 0xd0,
	TECHNIQUE_SUBDIV_PATCH_EMISSIVE = 0xd1,
	TECHNIQUE_SUBDIV_PATCH_EMISSIVE_DFOG = 0xd2,
	TECHNIQUE_SUBDIV_PATCH_EMISSIVE_SHADOW = 0xd3,
	TECHNIQUE_SUBDIV_PATCH_EMISSIVE_SHADOW_DFOG = 0xd4,
	TECHNIQUE_SUBDIV_PATCH_LIT = 0xd5,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR = 0xd6,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW = 0xd7,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT = 0xd8,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW = 0xd9,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS = 0xda,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI = 0xdb,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_SHADOW = 0xdc,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SPOT = 0xdd,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SPOT_SHADOW = 0xde,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SPOT_SHADOW_CUCOLORIS = 0xdf,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_OMNI = 0xe0,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_OMNI_SHADOW = 0xe1,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_SPOT = 0xe2,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_SPOT_SHADOW = 0xe3,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS = 0xe4,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_OMNI = 0xe5,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_OMNI_SHADOW = 0xe6,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SPOT = 0xe7,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SPOT_SHADOW = 0xe8,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SPOT_SHADOW_CUCOLORIS = 0xe9,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_OMNI = 0xea,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_OMNI_SHADOW = 0xeb,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_SPOT = 0xec,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_SPOT_SHADOW = 0xed,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS = 0xee,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_OMNI = 0xef,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_OMNI_SHADOW = 0xf0,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_SPOT = 0xf1,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW = 0xf2,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS = 0xf3,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_OMNI = 0xf4,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW = 0xf5,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_OMNI = 0xf6,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_OMNI_SHADOW = 0xf7,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_SHADOW_OMNI = 0xf8,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_SHADOW_OMNI_SHADOW = 0xf9,
	TECHNIQUE_SUBDIV_PATCH_LIT_DYNAMIC_BRANCHING_CUCOLORIS = 0xfa,
	TECHNIQUE_SUBDIV_PATCH_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS = 0xfb,
	TECHNIQUE_SUBDIV_PATCH_LIT_DYNAMIC_BRANCHING = 0xfc,
	TECHNIQUE_SUBDIV_PATCH_LIT_SUN_DYNAMIC_BRANCHING = 0xfd,
	TECHNIQUE_SUBDIV_PATCH_LIT_DFOG = 0xfe,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_DFOG = 0xff,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_DFOG = 0x100,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_DFOG = 0x101,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_DFOG = 0x102,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x103,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_DFOG = 0x104,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_SHADOW_DFOG = 0x105,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SPOT_DFOG = 0x106,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SPOT_SHADOW_DFOG = 0x107,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SPOT_SHADOW_CUCOLORIS_DFOG = 0x108,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_OMNI_DFOG = 0x109,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_OMNI_SHADOW_DFOG = 0x10a,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_SPOT_DFOG = 0x10b,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_SPOT_SHADOW_DFOG = 0x10c,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0x10d,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_OMNI_DFOG = 0x10e,
	TECHNIQUE_SUBDIV_PATCH_LIT_DIR_SHADOW_OMNI_SHADOW_DFOG = 0x10f,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SPOT_DFOG = 0x110,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SPOT_SHADOW_DFOG = 0x111,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x112,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_OMNI_DFOG = 0x113,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_OMNI_SHADOW_DFOG = 0x114,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_SPOT_DFOG = 0x115,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_SPOT_SHADOW_DFOG = 0x116,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0x117,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_OMNI_DFOG = 0x118,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_OMNI_SHADOW_DFOG = 0x119,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_DFOG = 0x11a,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_DFOG = 0x11b,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS_DFOG = 0x11c,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_DFOG = 0x11d,
	TECHNIQUE_SUBDIV_PATCH_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW_DFOG = 0x11e,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_OMNI_DFOG = 0x11f,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_OMNI_SHADOW_DFOG = 0x120,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_SHADOW_OMNI_DFOG = 0x121,
	TECHNIQUE_SUBDIV_PATCH_LIT_OMNI_SHADOW_OMNI_SHADOW_DFOG = 0x122,
	TECHNIQUE_SUBDIV_PATCH_LIT_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0x123,
	TECHNIQUE_SUBDIV_PATCH_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0x124,
	TECHNIQUE_SUBDIV_PATCH_LIT_DYNAMIC_BRANCHING_DFOG = 0x125,
	TECHNIQUE_SUBDIV_PATCH_LIT_SUN_DYNAMIC_BRANCHING_DFOG = 0x126,
	TECHNIQUE_SUBDIV_PATCH_LIGHT_SPOT = 0x127,
	TECHNIQUE_SUBDIV_PATCH_LIGHT_OMNI = 0x128,
	TECHNIQUE_SUBDIV_PATCH_LIGHT_SPOT_SHADOW = 0x129,
	TECHNIQUE_SUBDIV_PATCH_LIGHT_SPOT_SHADOW_CUCOLORIS = 0x12a,
	TECHNIQUE_SUBDIV_PATCH_FAKELIGHT_NORMAL = 0x12b,
	TECHNIQUE_SUBDIV_PATCH_FAKELIGHT_VIEW = 0x12c,
	TECHNIQUE_SUBDIV_PATCH_SUNLIGHT_PREVIEW = 0x12d,
	TECHNIQUE_SUBDIV_PATCH_CASE_TEXTURE = 0x12e,
	TECHNIQUE_SUBDIV_PATCH_WIREFRAME_SOLID = 0x12f,
	TECHNIQUE_SUBDIV_PATCH_WIREFRAME_SHADED = 0x130,
	TECHNIQUE_SUBDIV_PATCH_THERMAL = 0x131,
	TECHNIQUE_SUBDIV_PATCH_VELOCITY_RIGID = 0x132,
	TECHNIQUE_SUBDIV_PATCH_VELOCITY_SKINNED = 0x133,
	TECHNIQUE_SUBDIV_PATCH_DEBUG_BUMPMAP = 0x134,
	// no displacement: 0x135..0x19b
	TECHNIQUE_NO_DISPLACEMENT_DEPTH_PREPASS = 0x135,
	TECHNIQUE_NO_DISPLACEMENT_BUILD_SHADOWMAP_DEPTH = 0x136,
	TECHNIQUE_NO_DISPLACEMENT_UNLIT = 0x137,
	TECHNIQUE_NO_DISPLACEMENT_EMISSIVE = 0x138,
	TECHNIQUE_NO_DISPLACEMENT_EMISSIVE_DFOG = 0x139,
	TECHNIQUE_NO_DISPLACEMENT_EMISSIVE_SHADOW = 0x13a,
	TECHNIQUE_NO_DISPLACEMENT_EMISSIVE_SHADOW_DFOG = 0x13b,
	TECHNIQUE_NO_DISPLACEMENT_LIT = 0x13c,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR = 0x13d,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW = 0x13e,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT = 0x13f,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW = 0x140,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS = 0x141,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI = 0x142,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_SHADOW = 0x143,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SPOT = 0x144,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SPOT_SHADOW = 0x145,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SPOT_SHADOW_CUCOLORIS = 0x146,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_OMNI = 0x147,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_OMNI_SHADOW = 0x148,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_SPOT = 0x149,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_SPOT_SHADOW = 0x14a,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS = 0x14b,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_OMNI = 0x14c,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_OMNI_SHADOW = 0x14d,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SPOT = 0x14e,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SPOT_SHADOW = 0x14f,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SPOT_SHADOW_CUCOLORIS = 0x150,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_OMNI = 0x151,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_OMNI_SHADOW = 0x152,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_SPOT = 0x153,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_SPOT_SHADOW = 0x154,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS = 0x155,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_OMNI = 0x156,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_OMNI_SHADOW = 0x157,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_SPOT = 0x158,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW = 0x159,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS = 0x15a,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_OMNI = 0x15b,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW = 0x15c,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_OMNI = 0x15d,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_OMNI_SHADOW = 0x15e,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_SHADOW_OMNI = 0x15f,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_SHADOW_OMNI_SHADOW = 0x160,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DYNAMIC_BRANCHING_CUCOLORIS = 0x161,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS = 0x162,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DYNAMIC_BRANCHING = 0x163,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SUN_DYNAMIC_BRANCHING = 0x164,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DFOG = 0x165,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_DFOG = 0x166,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_DFOG = 0x167,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_DFOG = 0x168,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_DFOG = 0x169,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x16a,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_DFOG = 0x16b,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_SHADOW_DFOG = 0x16c,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SPOT_DFOG = 0x16d,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SPOT_SHADOW_DFOG = 0x16e,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SPOT_SHADOW_CUCOLORIS_DFOG = 0x16f,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_OMNI_DFOG = 0x170,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_OMNI_SHADOW_DFOG = 0x171,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_SPOT_DFOG = 0x172,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_SPOT_SHADOW_DFOG = 0x173,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0x174,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_OMNI_DFOG = 0x175,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DIR_SHADOW_OMNI_SHADOW_DFOG = 0x176,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SPOT_DFOG = 0x177,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SPOT_SHADOW_DFOG = 0x178,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SPOT_SHADOW_CUCOLORIS_DFOG = 0x179,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_OMNI_DFOG = 0x17a,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_OMNI_SHADOW_DFOG = 0x17b,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_SPOT_DFOG = 0x17c,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_SPOT_SHADOW_DFOG = 0x17d,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_SPOT_SHADOW_CUCOLORIS_DFOG = 0x17e,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_OMNI_DFOG = 0x17f,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_OMNI_SHADOW_DFOG = 0x180,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_DFOG = 0x181,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_DFOG = 0x182,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_SPOT_SHADOW_CUCOLORIS_DFOG = 0x183,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_DFOG = 0x184,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SPOT_SHADOW_CUCOLORIS_OMNI_SHADOW_DFOG = 0x185,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_OMNI_DFOG = 0x186,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_OMNI_SHADOW_DFOG = 0x187,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_SHADOW_OMNI_DFOG = 0x188,
	TECHNIQUE_NO_DISPLACEMENT_LIT_OMNI_SHADOW_OMNI_SHADOW_DFOG = 0x189,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0x18a,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SUN_DYNAMIC_BRANCHING_CUCOLORIS_DFOG = 0x18b,
	TECHNIQUE_NO_DISPLACEMENT_LIT_DYNAMIC_BRANCHING_DFOG = 0x18c,
	TECHNIQUE_NO_DISPLACEMENT_LIT_SUN_DYNAMIC_BRANCHING_DFOG = 0x18d,
	TECHNIQUE_NO_DISPLACEMENT_LIGHT_SPOT = 0x18e,
	TECHNIQUE_NO_DISPLACEMENT_LIGHT_OMNI = 0x18f,
	TECHNIQUE_NO_DISPLACEMENT_LIGHT_SPOT_SHADOW = 0x190,
	TECHNIQUE_NO_DISPLACEMENT_LIGHT_SPOT_SHADOW_CUCOLORIS = 0x191,
	TECHNIQUE_NO_DISPLACEMENT_FAKELIGHT_NORMAL = 0x192,
	TECHNIQUE_NO_DISPLACEMENT_FAKELIGHT_VIEW = 0x193,
	TECHNIQUE_NO_DISPLACEMENT_SUNLIGHT_PREVIEW = 0x194,
	TECHNIQUE_NO_DISPLACEMENT_CASE_TEXTURE = 0x195,
	TECHNIQUE_NO_DISPLACEMENT_WIREFRAME_SOLID = 0x196,
	TECHNIQUE_NO_DISPLACEMENT_WIREFRAME_SHADED = 0x197,
	TECHNIQUE_NO_DISPLACEMENT_THERMAL = 0x198,
	TECHNIQUE_NO_DISPLACEMENT_VELOCITY_RIGID = 0x199,
	TECHNIQUE_NO_DISPLACEMENT_VELOCITY_SKINNED = 0x19a,
	TECHNIQUE_NO_DISPLACEMENT_DEBUG_BUMPMAP = 0x19b,
	TECHNIQUE_COUNT = 0x19c,
};
#define TECHNIQUES_PER_GROUP 0x67

// MaterialShaderArgument::type (server PDB)
enum MaterialShaderArgumentType
{
	MTL_ARG_CODE_CONST = 0x0,      // u.codeConst: a code constant (CONST_SRC_*), rows firstRow..firstRow+rowCount-1
	MTL_ARG_CODE_TEXTURE = 0x1,    // u.codeSampler: a code texture (TEXTURE_SRC_*), shader resource view only
	MTL_ARG_CODE_SAMPLER = 0x2,    // u.codeSampler: a code texture with its sampler
	MTL_ARG_MATERIAL_CONST = 0x3,  // u.nameHash: a constant of the material's constant table, by name hash
	MTL_ARG_LITERAL_CONST = 0x4,   // u.literalConst: four floats stored in the technique set (loaded inline)
	MTL_ARG_MATERIAL_TEXTURE = 0x5,// u.nameHash: a texture of the material's texture table, by name hash
	MTL_ARG_MATERIAL_SAMPLER = 0x6,// u.nameHash: the same with its sampler
	MTL_ARG_COUNT = 0x7,
};

// MaterialShaderArgument::shader (server PDB)
enum MaterialShaderType
{
	MTL_COMPUTE_SHADER = 0x0,
	MTL_VERTEX_SHADER = 0x1,
	MTL_HULL_SHADER = 0x2,
	MTL_DOMAIN_SHADER = 0x3,
	MTL_PIXEL_SHADER = 0x4,
	MTL_SHADER_TYPE_COUNT = 0x5,
};

// MaterialTextureDef::semantic (server PDB). TS_WATER_MAP is the one the loader treats specially: its u is a water_t.
enum MaterialTextureSemantic
{
	TS_2D = 0x0,
	TS_FUNCTION = 0x1,
	TS_COLOR_MAP = 0x2,
	TS_DETAIL_MAP = 0x3,
	TS_UNUSED_2 = 0x4,
	TS_NORMAL_MAP = 0x5,
	TS_UNUSED_3 = 0x6,
	TS_UNUSED_4 = 0x7,
	TS_SPECULAR_MAP = 0x8,
	TS_UNUSED_5 = 0x9,
	TS_OCEANFLOW_DISPLACEMENT_MAP = 0xa,
	TS_WATER_MAP = 0xb,
	TS_OCEAN_DISPLACEMENT_MAP = 0xc,
	TS_DISPLACEMENT_MAP = 0xd,
	TS_PARALLAX_MAP = 0xe,
	TS_COUNT = 0xf,
};

// Material::cameraRegion (server PDB GfxCameraRegionType; CAMERA_REGION_NONE == 8 is tested by the Store build's
// R_AddBModelSurfacesCamera counterpart, 140651710)
enum GfxCameraRegionType
{
	CAMERA_REGION_LIT_OPAQUE = 0x0,
	CAMERA_REGION_LIT_DECAL = 0x1,
	CAMERA_REGION_LIT_TRANS = 0x2,
	CAMERA_REGION_EMISSIVE = 0x3,
	CAMERA_REGION_DEPTH_HACK = 0x4,
	CAMERA_REGION_LIGHT_MAP_OPAQUE = 0x5,
	CAMERA_REGION_HUD_OUTLINE = 0x6,
	CAMERA_REGION_MOTIONBLUR = 0x7,
	CAMERA_REGION_COUNT = 0x8,
	CAMERA_REGION_NONE = 0x8,
};

// GfxStateBits::depthStencilState has one index per depth-stencil mode (server PDB GfxDepthStencilMode)
enum GfxDepthStencilMode
{
	GFX_DEPTH_STENCIL_MODE_DEFAULT = 0x0,
	GFX_DEPTH_STENCIL_MODE_HUD_OUTLINE = 0x1,
	GFX_DEPTH_STENCIL_MODE_HUD_OUTLINE_ZFAIL = 0x2,
	GFX_DEPTH_STENCIL_MODE_MOTION_BLUR_HQ = 0x3,
	GFX_DEPTH_STENCIL_MODE_DEPTH_HACK = 0x4,
	GFX_DEPTH_STENCIL_MODE_FORCE_DEPTH_WRITE = 0x5,
	GFX_DEPTH_STENCIL_MODE_FORCE_DEPTH_WRITE_HUD_OUTLINE = 0x6,
	GFX_DEPTH_STENCIL_MODE_FORCE_DEPTH_WRITE_HUD_OUTLINE_ZFAIL = 0x7,
	GFX_DEPTH_STENCIL_MODE_CACHED_SPOT_STENCIL_INCR_SAT = 0x8,
	GFX_DEPTH_STENCIL_MODE_CACHED_SPOT_STENCIL_INCR_SAT_CLEAR_DEPTH = 0x9,
	GFX_DEPTH_STENCIL_MODE_CACHED_SPOT_STENCIL_FULL_MASK = 0xa,
	GFX_DEPTH_STENCIL_MODE_COUNT = 0xb,
};

// ---- material -----------------------------------------------------------------------------------------------------

union GfxDrawSurf  // server PDB GfxDrawSurfFields: two 64-bit words of bit fields
{
	unsigned long long packed[2];
};

struct MaterialInfo  // 0x28, same as the servers'
{
	const char *name;
	unsigned char gameFlags;
	unsigned char sortKey;
	unsigned char textureAtlasRowCount;
	unsigned char textureAtlasColumnCount;
	unsigned char textureAtlasFrameBlend;
	unsigned char textureAtlasAsArray;
	unsigned char renderFlags;
	GfxDrawSurf drawSurf;
	unsigned int surfaceTypeBits;
	unsigned short hashIndex;
};
static_assert(sizeof(MaterialInfo) == 0x28, "MaterialInfo");
static_assert(__builtin_offsetof(MaterialInfo, drawSurf) == 0x10, "MaterialInfo");

struct water_t;

union MaterialTextureDefInfo
{
	GfxImage *image;  // every semantic but TS_WATER_MAP
	water_t *water;   // TS_WATER_MAP
};

struct MaterialTextureDef  // 0x10
{
	unsigned int nameHash;  // R_HashString of the sampler name the technique set's arguments refer to
	char nameStart;         // first and last character of that name
	char nameEnd;
	unsigned char samplerState;
	unsigned char semantic;  // MaterialTextureSemantic
	MaterialTextureDefInfo u;
};
static_assert(sizeof(MaterialTextureDef) == 0x10, "MaterialTextureDef");
static_assert(__builtin_offsetof(MaterialTextureDef, semantic) == 7, "Load_MaterialTextureDefInfo reads +7");

struct MaterialConstantDef  // 0x20
{
	unsigned int nameHash;
	char name[12];
	float literal[4];
};
static_assert(sizeof(MaterialConstantDef) == 0x20, "MaterialConstantDef");

struct GfxStateBits  // 0x1C
{
	unsigned int loadBits[3];               // GFXS0_* / GFXS1_* / GFXS_* blend bits (docs)
	unsigned char zone;                     // set to the loading zone's index by the loader
	unsigned char depthStencilState[11];    // per GfxDepthStencilMode: index into dx.depthStencilStateTables[zone]
	unsigned char blendState;               // index into dx.blendStateTables[zone]
	unsigned char rasterizerState;          // index into dx.rasterizerStates[32]
};
static_assert(sizeof(GfxStateBits) == 0x1C, "GfxStateBits");
static_assert(__builtin_offsetof(GfxStateBits, zone) == 0xC, "GfxStateBits");

struct MaterialConstantBufferDef  // 0x80, same as the servers'
{
	unsigned int vsDataSize;
	unsigned int hsDataSize;
	unsigned int dsDataSize;
	unsigned int psDataSize;
	unsigned int vsOffsetDataSize;
	unsigned int hsOffsetDataSize;
	unsigned int dsOffsetDataSize;
	unsigned int psOffsetDataSize;
	unsigned char *vsData;
	unsigned char *hsData;
	unsigned char *dsData;
	unsigned char *psData;
	unsigned short *vsOffsetData;
	unsigned short *hsOffsetData;
	unsigned short *dsOffsetData;
	unsigned short *psOffsetData;
	ID3D11Buffer *vsConstantBuffer;  // created by Load_InitMaterialConstantBuffer
	ID3D11Buffer *hsConstantBuffer;
	ID3D11Buffer *dsConstantBuffer;
	ID3D11Buffer *psConstantBuffer;
};
static_assert(sizeof(MaterialConstantBufferDef) == 0x80, "MaterialConstantBufferDef");
static_assert(__builtin_offsetof(MaterialConstantBufferDef, vsConstantBuffer) == 0x60, "MaterialConstantBufferDef");

struct MaterialTechniqueSet;

struct Material  // 0x3A8 in the Store build (0x2D0 in the servers)
{
	MaterialInfo info;
	unsigned char stateBitsEntry[TECHNIQUE_COUNT];  // per technique: index of its first pass's GfxStateBits
	unsigned char textureCount;
	unsigned char constantCount;
	unsigned char stateBitsCount;
	unsigned char stateFlags;    // bit 0: draw the depth prepass with rgp.depthPrepassMaterial (1406148D0)
	unsigned char cameraRegion;  // GfxCameraRegionType
	unsigned char materialType;
	unsigned char layerCount;    // PC only: entries of subMaterials
	unsigned char assetFlags;    // bit 0: dynamic constant buffers; bit 1: tested by the scene code (docs)
	MaterialTechniqueSet *techniqueSet;
	MaterialTextureDef *textureTable;
	MaterialConstantDef *constantTable;
	GfxStateBits *stateBitsTable;
	unsigned char constantBufferIndex[TECHNIQUE_COUNT];  // per technique: index into constantBufferTable
	MaterialConstantBufferDef *constantBufferTable;
	unsigned char constantBufferCount;
	const char **subMaterials;  // PC only: layerCount names (layered materials)
};
static_assert(sizeof(Material) == 0x3A8, "Material (Store build)");
static_assert(__builtin_offsetof(Material, stateBitsEntry) == 0x28, "Material");
static_assert(__builtin_offsetof(Material, textureCount) == 0x1C4, "Material");
static_assert(__builtin_offsetof(Material, stateFlags) == 0x1C7, "Material");
static_assert(__builtin_offsetof(Material, cameraRegion) == 0x1C8, "Material");
static_assert(__builtin_offsetof(Material, materialType) == 0x1C9, "Material");
static_assert(__builtin_offsetof(Material, layerCount) == 0x1CA, "Material");
static_assert(__builtin_offsetof(Material, assetFlags) == 0x1CB, "Material");
static_assert(__builtin_offsetof(Material, techniqueSet) == 0x1D0, "Material");
static_assert(__builtin_offsetof(Material, textureTable) == 0x1D8, "Material");
static_assert(__builtin_offsetof(Material, constantTable) == 0x1E0, "Material");
static_assert(__builtin_offsetof(Material, stateBitsTable) == 0x1E8, "Material");
static_assert(__builtin_offsetof(Material, constantBufferIndex) == 0x1F0, "Material");
static_assert(__builtin_offsetof(Material, constantBufferTable) == 0x390, "Material");
static_assert(__builtin_offsetof(Material, constantBufferCount) == 0x398, "Material");
static_assert(__builtin_offsetof(Material, subMaterials) == 0x3A0, "Material");

// ---- shaders ------------------------------------------------------------------------------------------------------

// The program is DXBC (a D3D11 shader container). loadForRenderer is compared with r_rendererInUse before the
// shader is created. Vertex and pixel shaders carry 8 more bytes (the servers' microCodeCrc), hull and domain
// shaders do not.
struct GfxVertexShaderLoadDef  // 0x18
{
	unsigned char *program;
	unsigned int programSize;
	unsigned short loadForRenderer;
	unsigned int microCodeCrc;
};
struct GfxPixelShaderLoadDef  // 0x18
{
	unsigned char *program;
	unsigned int programSize;
	unsigned short loadForRenderer;
	unsigned int microCodeCrc;
};

struct GfxHullShaderLoadDef  // 0x10
{
	unsigned char *program;
	unsigned int programSize;
	unsigned short loadForRenderer;
};
struct GfxDomainShaderLoadDef  // 0x10
{
	unsigned char *program;
	unsigned int programSize;
	unsigned short loadForRenderer;
};
static_assert(sizeof(GfxVertexShaderLoadDef) == 0x18 && sizeof(GfxPixelShaderLoadDef) == 0x18, "VS/PS load defs");
static_assert(sizeof(GfxHullShaderLoadDef) == 0x10 && sizeof(GfxDomainShaderLoadDef) == 0x10, "HS/DS load defs");
static_assert(__builtin_offsetof(GfxHullShaderLoadDef, programSize) == 0x8, "Load_Gfx*ShaderLoadDef reads +8");
static_assert(__builtin_offsetof(GfxHullShaderLoadDef, loadForRenderer) == 0xC, "Load_CreateMaterial*Shader");

struct MaterialVertexShaderProgram
{
	ID3D11VertexShader *vs;
	GfxVertexShaderLoadDef loadDef;
};
struct MaterialPixelShaderProgram
{
	ID3D11PixelShader *ps;
	GfxPixelShaderLoadDef loadDef;
};
struct MaterialHullShaderProgram
{
	ID3D11HullShader *hs;
	GfxHullShaderLoadDef loadDef;
};
struct MaterialDomainShaderProgram
{
	ID3D11DomainShader *ds;
	GfxDomainShaderLoadDef loadDef;
};

struct MaterialVertexShader  // 0x28
{
	const char *name;
	MaterialVertexShaderProgram prog;
};
struct MaterialPixelShader  // 0x28
{
	const char *name;
	MaterialPixelShaderProgram prog;
};
struct MaterialHullShader  // 0x20
{
	const char *name;
	MaterialHullShaderProgram prog;
};
struct MaterialDomainShader  // 0x20
{
	const char *name;
	MaterialDomainShaderProgram prog;
};
static_assert(sizeof(MaterialVertexShader) == 0x28 && sizeof(MaterialPixelShader) == 0x28, "VS/PS (Store build)");
static_assert(sizeof(MaterialHullShader) == 0x20 && sizeof(MaterialDomainShader) == 0x20, "HS/DS (Store build)");
static_assert(__builtin_offsetof(MaterialPixelShader, prog.loadDef) == 0x10, "MaterialPixelShader");

// ---- vertex declarations ------------------------------------------------------------------------------------------

struct MaterialStreamRouting  // one vertex shader input: where it comes from and which semantic it feeds
{
	unsigned char source;  // STREAM_SRC_*: a row of s_streamSourceInfo[vertDeclType]
	unsigned char dest;    // STREAM_DST_*: a row of s_streamDestInfo (semantic name and index)
	unsigned char mask;
};

#define VERTEXDECL_TYPE_COUNT 249  // 242 in the xb3 server

struct MaterialVertexStreamRouting
{
	MaterialStreamRouting data[31];  // STREAM_DST_COUNT
	ID3D11InputLayout *decl[VERTEXDECL_TYPE_COUNT];  // built at load for every vertex declaration type
};
static_assert(__builtin_offsetof(MaterialVertexStreamRouting, decl) == 0x60, "MaterialVertexStreamRouting");
static_assert(sizeof(MaterialVertexStreamRouting) == 0x828, "MaterialVertexStreamRouting (Store build)");

struct MaterialVertexDeclaration  // 0x838
{
	const char *name;
	unsigned char streamCount;  // entries of routing.data in use
	bool hasOptionalSource;
	MaterialVertexStreamRouting routing;
};
static_assert(sizeof(MaterialVertexDeclaration) == 0x838, "MaterialVertexDeclaration (Store build)");

// ---- techniques -------------------------------------------------------------------------------------------------

struct MaterialArgumentCodeConst
{
	unsigned short index;  // CONST_SRC_* (the Store build's s_codeConstantName order)
	unsigned char firstRow;
	unsigned char rowCount;
};

union MaterialArgumentDef
{
	const float *literalConst;
	MaterialArgumentCodeConst codeConst;
	unsigned int codeSampler;  // TEXTURE_SRC_* (s_codeTextureName order)
	unsigned int nameHash;
};

struct MaterialShaderArgument  // 0x10
{
	unsigned char type;    // MaterialShaderArgumentType
	unsigned char shader;  // MaterialShaderType
	unsigned short dest;   // constant register (float4 row) or texture/sampler slot
	MaterialArgumentDef u;
};
static_assert(sizeof(MaterialShaderArgument) == 0x10, "MaterialShaderArgument");

struct MaterialPass  // 0x48, same as the servers'
{
	MaterialVertexShader *vertexShader;
	MaterialVertexDeclaration *vertexDecl;
	MaterialHullShader *hullShader;
	MaterialDomainShader *domainShader;
	MaterialPixelShader *pixelShader;
	unsigned char pixelOutputMask;
	unsigned char perPrimArgCount;
	unsigned char perObjArgCount;
	unsigned char stableArgCount;
	unsigned short perPrimArgSize;
	unsigned short perObjArgSize;
	unsigned short stableArgSize;
	unsigned char zone;  // set to the loading zone's index by the loader
	unsigned char perPrimConstantBuffer;
	unsigned char perObjConstantBuffer;
	unsigned char stableConstantBuffer;
	unsigned int customBufferFlags;
	unsigned char customSamplerFlags;
	unsigned char precompiledIndex;
	unsigned char stageConfig;
	MaterialShaderArgument *args;  // perPrimArgCount + perObjArgCount + stableArgCount arguments, in that order
};
static_assert(sizeof(MaterialPass) == 0x48, "MaterialPass");
static_assert(__builtin_offsetof(MaterialPass, perPrimArgCount) == 0x29, "MaterialPass");
static_assert(__builtin_offsetof(MaterialPass, zone) == 0x32, "MaterialPass");
static_assert(__builtin_offsetof(MaterialPass, args) == 0x40, "MaterialPass");

struct MaterialTechnique  // 0x10 + passCount * 0x48
{
	const char *name;
	unsigned short flags;
	unsigned short passCount;
	MaterialPass passArray[1];
};
static_assert(__builtin_offsetof(MaterialTechnique, passCount) == 0xA, "MaterialTechnique");
static_assert(__builtin_offsetof(MaterialTechnique, passArray) == 0x10, "MaterialTechnique");

struct MaterialTechniqueSet  // 0xCF0 in the Store build (0x9B8 in the servers)
{
	const char *name;
	unsigned short flags;
	unsigned char worldVertFormat;
	unsigned char preDisplacementOnlyCount;
	MaterialTechnique *techniques[TECHNIQUE_COUNT];
};
static_assert(sizeof(MaterialTechniqueSet) == 0xCF0, "MaterialTechniqueSet (Store build)");

// ---- water (TS_WATER_MAP textures) --------------------------------------------------------------------------------

struct water_t  // 0x58 in the Store build; only what the loader reads is spelled out
{
	unsigned char unknown_00[8];
	float *H0X;    // M * N floats each
	float *H0Y;
	float *wTerm;
	int M;
	int N;
	unsigned char unknown_28[0x20];
	GfxImage *image;
	GfxImage *imageAlt;  // name unknown
};
static_assert(sizeof(water_t) == 0x58, "water_t (Store build)");
static_assert(__builtin_offsetof(water_t, M) == 0x20, "water_t");
static_assert(__builtin_offsetof(water_t, image) == 0x48, "water_t");

// ---- asset header ------------------------------------------------------------------------------------------------

struct ComputeShader;

union XAssetHeader
{
	Material *material;
	ComputeShader *computeShader;
	MaterialVertexShader *vertexShader;
	MaterialHullShader *hullShader;
	MaterialDomainShader *domainShader;
	MaterialPixelShader *pixelShader;
	MaterialVertexDeclaration *vertexDecl;
	MaterialTechniqueSet *techniqueSet;
};

// ---- gfx_d3d/r_material_load_db.h (Store build, src/gfx_d3d/r_material_load_db.cpp) ------------------------------

void Load_MaterialInfo(bool atStreamStart);
void Load_Material(bool atStreamStart);
void Load_MaterialHandle(bool atStreamStart);
void Load_MaterialHandleArray(bool atStreamStart, unsigned long long count);
void Load_MaterialTextureDefInfo(bool atStreamStart);
void Load_GfxStateBits(bool atStreamStart);
void Load_MaterialConstantBufferDefArray(bool atStreamStart, unsigned long long count);
void Load_MaterialTechniqueSet(bool atStreamStart);
void Load_MaterialTechniqueSetPtr(bool atStreamStart);
void Load_MaterialTechnique(bool atStreamStart);
void Load_MaterialPassArray(bool atStreamStart, unsigned long long count);
void Load_GfxVertexShaderLoadDef(bool atStreamStart);
void Load_GfxPixelShaderLoadDef(bool atStreamStart);
void Load_GfxHullShaderLoadDef(bool atStreamStart);
void Load_GfxDomainShaderLoadDef(bool atStreamStart);
void Load_MaterialVertexShader(bool atStreamStart);
void Load_MaterialVertexShaderPtr(bool atStreamStart);
void Load_MaterialPixelShader(bool atStreamStart);
void Load_MaterialPixelShaderPtr(bool atStreamStart);
void Load_MaterialHullShader(bool atStreamStart);
void Load_MaterialHullShaderPtr(bool atStreamStart);
void Load_MaterialDomainShader(bool atStreamStart);
void Load_MaterialDomainShaderPtr(bool atStreamStart);
void Load_MaterialVertexDeclaration(bool atStreamStart);
void Load_MaterialVertexDeclarationPtr(bool atStreamStart);
void Load_water_t(bool atStreamStart);

// ---- gfx_d3d/r_material.cpp (load-time creation) -----------------------------------------------------------------

void Load_InitMaterialConstantBuffer(unsigned char *constantBufferCount, Material *material);
void Load_CreateMaterialVertexShader(unsigned char **data, MaterialVertexShader *shader);
void Load_CreateMaterialPixelShader(unsigned char **data, MaterialPixelShader *shader);
void Load_CreateMaterialHullShader(unsigned char **data, MaterialHullShader *shader);
void Load_CreateMaterialDomainShader(unsigned char **data, MaterialDomainShader *shader);
void Load_MaterialVertexStreamRouting(MaterialVertexStreamRouting *routing, unsigned int streamCount,
                                      MaterialVertexShader *vs);
