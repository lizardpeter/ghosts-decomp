#!/usr/bin/env python3
"""Read the exact IW6 XAsset directory from authenticated ORIGINAL FF bytes.

Only aggregate type counts, source offsets and validation digests are emitted.
No retail bytes, names, decoded assets or game data are committed or exported.
This is independent research evidence for the private Rust-test loader.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import struct
import sys
import unittest
import zlib

from probe_zone import (
    MAX_OUTPUT, StreamStats, outer_header, verified_authenticated_chunks, direct_chunks
)

ASSET_TYPES = (
    "physpreset physcollmap xanimparts xmodel_surfs xmodel material computeshader "
    "vertexshader hullshader domainshader pixelshader vertexdecl technique_set image sound "
    "sound_curve lpf_curve reverb_curve loaded_sound clipmap comworld glassworld pathdata "
    "vehicle_track map_ents fxworld gfxworld light_def ui_map font menulist menu animclass "
    "localize_entry attachment weapon snddriver_globals fx impact_fx surface_fx aitype "
    "mptype character xmodelalias rawfile scriptfile stringtable leaderboard structured_data_def "
    "tracer vehicle addon_map_ents net_const_strings reverb_preset lua_file scriptable "
    "colorization colorizationset tonemapping equipment_snd_table vectorfield doppler_preset "
    "particle_sim_animation string assetlist"
).split()
TAG_MASK = 0xfffffff000000000
TAG_VALUE = 0xfdfdfdf000000000

def pointer_kind(value: int) -> str:
    if value == 0:
        return "null"
    if value & TAG_MASK != TAG_VALUE:
        raise ValueError(f"untagged IW6 pointer 0x{value:016x}")
    low = value & 0xffffffff
    if low == 0xffffffff:
        return "follows"
    if low == 0xfffffffe:
        return "insert"
    if low == 0xfffffffd:
        raise ValueError("source pointer -3 needs separate verification")
    if low == 0:
        raise ValueError("zero packed pointer index")
    block = (value >> 32) & 0xf
    if block >= 7:
        raise ValueError(f"unknown IW6 logical block {block}")
    return "alias"

def u64(data: bytes, at: int) -> int:
    if at < 0 or at+8 > len(data):
        raise ValueError("truncated source u64")
    return struct.unpack_from("<Q", data, at)[0]

def u32(data: bytes, at: int) -> int:
    if at < 0 or at+4 > len(data):
        raise ValueError("truncated source u32")
    return struct.unpack_from("<I", data, at)[0]

class Cursor:
    def __init__(self, data: bytes, sizes: tuple[int, ...]):
        self.data = data
        self.at = 72
        self.current = 0
        self.offsets = [0]*7
        self.limits = sizes
        self.stack = []
        # The first 72 XFile bytes were read as a TEMP logical allocation.
        self.offsets[0] = 72

    def push(self, block: int) -> None:
        self.stack.append(self.current)
        self.current = block

    def pop(self) -> None:
        self.current = self.stack.pop()

    def align(self, mask: int) -> None:
        end = (self.offsets[self.current] + mask) & ~mask
        if end > self.limits[self.current]:
            raise ValueError(f"IW6 block {self.current} alignment overflow")
        self.offsets[self.current] = end

    def take(self, n: int) -> bytes:
        if n < 0 or self.offsets[self.current] + n > self.limits[self.current]:
            raise ValueError(f"IW6 logical block {self.current} overflow")
        self.offsets[self.current] += n
        if self.current == 2:
            return b""
        last = self.at + n
        if last > len(self.data):
            raise ValueError(f"source XFile ends at {len(self.data)} before {last}")
        out = self.data[self.at:last]
        self.at = last
        return out

    def string(self) -> None:
        last = self.data.find(b"\0", self.at, min(len(self.data),self.at+65537))
        if last < 0:
            raise ValueError("unterminated original IW6 XString")
        self.take(last - self.at + 1)

def table(c: Cursor, raw: bytes, off: int, count: int, stride: int, runtime: bool) -> None:
    if count > 1_000_000:
        raise ValueError("XGfxGlobals count exceeds bound")
    if pointer_kind(u64(raw,off)) not in ("follows", "insert"):
        return
    if runtime:
        c.push(2)
    c.align(3)
    c.take(count * stride)
    if runtime:
        c.pop()

def gfx_globals(c: Cursor) -> None:
    raw = c.take(104)
    depth, blend = u32(raw,0), u32(raw,4)
    prim, obj, stable = u32(raw,40),u32(raw,44),u32(raw,48)
    for off,count,width,runtime in [
        (8,depth,8,False),(16,blend,4,False),
        (24,depth,8,True),(32,blend,8,True),
        (56,prim,4,False),(64,obj,4,False),(72,stable,4,False),
        (80,prim,8,True),(88,obj,8,True),(96,stable,8,True),
    ]:
        table(c,raw,off,count,width,runtime)

def directory(data: bytes) -> dict:
    if len(data)<112:
        raise ValueError("truncated original XFile + XAssetList")
    declared, external, *limits = struct.unpack_from("<9Q",data,0)
    if declared + 72 != len(data):
        raise ValueError("XFile declared size mismatch")
    strings, stringptr, assets, assetptr, globalptr = struct.unpack_from("<5Q",data,72)
    if strings>2_000_000 or assets>2_000_000:
        raise ValueError("XAssetList unreasonable counts")
    c=Cursor(data,tuple(limits))
    c.take(40)
    c.push(3)
    c.push(3)
    if strings:
        if pointer_kind(stringptr) not in ("follows","insert"):
            raise ValueError("noninline original script strings need owner-zone resolution")
        array=c.take(strings*8)
        for i in range(strings):
            ptr=u64(array,i*8)
            if pointer_kind(ptr) in ("follows","insert"):
                c.string()
    c.pop()
    if pointer_kind(globalptr) in ("follows","insert"):
        inner=u64(c.take(8),0)
        if pointer_kind(inner) in ("follows","insert"):
            gfx_globals(c)
    c.pop()
    if pointer_kind(assetptr) not in ("follows","insert"):
        raise ValueError("original XAsset directory is not inline")
    c.push(3)
    c.align(3)
    table_at=c.at
    if assets*16>len(data)-c.at:
        raise ValueError("original XAsset directory outside XFile")
    raw=c.take(assets*16)
    kinds=collections.Counter()
    for i in range(assets):
        kind=u64(raw,i*16)
        if kind>=len(ASSET_TYPES):
            raise ValueError(f"invalid source XAsset type {kind} at index {i}")
        pointer_kind(u64(raw,i*16+8))
        kinds[ASSET_TYPES[kind]]+=1
    # Coverage of KIND IDs in private Rust-test, not of decoded asset bodies.
    supported={0,1,3,4,5,7,8,9,10,11,12,13,20,26,27,33,44,45,46,52,56,57,58,61}
    first_unsupported=next((
        {"index":i,"type":ASSET_TYPES[u64(raw,i*16)]}
        for i in range(assets) if u64(raw,i*16) not in supported
    ),None)
    runs=[]
    for i in range(assets):
        name=ASSET_TYPES[u64(raw,i*16)]
        if runs and runs[-1]["type"]==name:
            runs[-1]["count"]+=1
        else:
            runs.append({"index":i,"type":name,"count":1})
    return {
        "exact_asset_table_offset":table_at,
        "asset_count":assets,
        "script_strings":strings,
        "has_gfx_globals":bool(globalptr),
        "type_counts":dict(sorted(kinds.items())),
        "first_16_asset_types":[ASSET_TYPES[u64(raw,i*16)] for i in range(min(assets,16))],
        "first_unsupported_body_type":first_unsupported,
        "first_24_type_runs":runs[:24],
    }

def walk_original_source_material(c: Cursor, assets: bytes, idx: int) -> dict:
    """Read one IW6 Material in retail order. Stop at unknown inline types."""
    if u64(assets,idx*16)!=5:
        raise ValueError("source XAsset order moved beyond the material group")
    slot=pointer_kind(u64(assets,idx*16+8))
    if slot in ("null","alias"):
        return {"asset":idx,"alias":True,"images":0}
    start=c.at
    c.push(0)
    c.align(3)
    h=c.take(936)
    c.push(3)
    fields={"name":0,"tech":464,"textures":472,"constants":480,
        "states":488,"buffers":912,"layers":928}
    ptrs={k:pointer_kind(u64(h,off)) for k,off in fields.items()}
    if ptrs["name"] in ("follows","insert"):
        c.string()
    if ptrs["tech"] in ("follows","insert"):
        raise ValueError("nested MaterialTechniqueSet needs exact shader-pass walker")
    ntex=h[452]
    images=0
    if ptrs["textures"] in ("follows","insert"):
        c.align(3)
        tex=c.take(16*ntex)
        for i in range(ntex):
            ptr=pointer_kind(u64(tex,16*i+8))
            if tex[16*i+7]==11 and ptr in ("follows","insert"):
                raise ValueError("inline water_t texture needs separate water loader")
            if ptr not in ("follows","insert"):
                continue
            c.push(0)
            c.align(3)
            img=c.take(104)
            c.push(3)
            ip=pointer_kind(u64(img,96))
            if ip in ("follows","insert"):
                c.string()
            px=pointer_kind(u64(img,56))
            datalen=1 if img[29]==11 else u32(img,36)
            if datalen>512*1024*1024:
                raise ValueError("nested GfxImage data exceeds allocation cap")
            if px in ("follows","insert"):
                c.push(0)
                c.align(3)
                c.take(datalen)
                c.pop()
            width,height=struct.unpack_from("<HH",img,44)
            empty=width==0 and height==0 and u32(img,24)==0 and px=="null" and not img[53]
            if (width==0 or height==0) and not empty:
                raise ValueError("nested material image has invalid dimensions")
            images+=1
            c.pop()
            c.pop()
    elif ntex:
        raise ValueError("nonzero texture count without original inline table")
    for key,count,stride,mask in [
        ("constants",h[453],32,15),("states",h[454],28,3)]:
        if ptrs[key] in ("follows","insert"):
            c.align(mask)
            c.take(count*stride)
        elif count and ptrs[key]=="null":
            raise ValueError(f"nonzero {key} count without original pointer")
    if ptrs["buffers"] in ("follows","insert"):
        c.align(3)
        buffers=c.take(h[920]*128)
        for j in range(h[920]):
            cb=buffers[j*128:(j+1)*128]
            for count_at,ptr_at,mask in [(0,32,15),(16,64,1)]:
                for k in range(4):
                    count=u32(cb,count_at+4*k)
                    if count>32*1024*1024:
                        raise ValueError("material stage array count exceeds bound")
                    if pointer_kind(u64(cb,ptr_at+8*k)) in ("follows","insert"):
                        c.align(mask)
                        c.take(count)
    elif h[920] and ptrs["buffers"]=="null":
        raise ValueError("nonzero constant buffer count without source pointer")
    if ptrs["layers"] in ("follows","insert"):
        c.align(7)
        layers=c.take(h[458]*8)
        for k in range(h[458]):
            if pointer_kind(u64(layers,k*8)) in ("follows","insert"):
                c.string()
    elif h[458] and ptrs["layers"]=="null":
        raise ValueError("nonzero material layer count without source pointer")
    c.pop()
    c.pop()
    return {"asset":idx,"alias":False,"images":images,"bytes":c.at-start}

def walk_iw6_animation_record(c: Cursor, assets: bytes, idx: int) -> dict:
    """Read original IW6 XAnimParts tracks and pools using PC layout.

    The delta-track and flat-pool ownership order comes from independently
    published IW6 type metadata; the output is strictly metadata and every
    referenced span is bounded by the original authenticated XFile.
    """
    if u64(assets,idx*16)!=2:
        raise ValueError(f"asset #{idx} not XAnimParts")
    if pointer_kind(u64(assets,idx*16+8)) not in ("follows","insert"):
        return {"asset":idx,"alias":True,"bytes":0}
    start=c.at
    c.push(0)
    c.align(3)
    h=c.take(136)
    c.push(3)
    numframes=struct.unpack_from("<H",h,18)[0]
    wide=numframes>=256
    def elements(at,count,stride,align):
        k=pointer_kind(u64(h,at))
        if k in ("follows","insert"):
            c.align(align)
            c.take(count*stride)
        elif k=="null" and count:
            raise ValueError(f"array@{at} null with count {count}")
    if pointer_kind(u64(h,0)) in ("follows","insert"):
        c.string()
    elements(56,h[30],4,3)
    elements(120,h[31],8,3)
    delta=pointer_kind(u64(h,128))
    delta_tracks=0
    if delta in ("follows","insert"):
        c.align(3)
        d=c.take(24)
        for pos,width in [(0,3),(8,4),(16,8)]:
            p=pointer_kind(u64(d,pos))
            if p not in ("follows","insert"):
                continue
            delta_tracks+=1
            c.align(3)
            dh=c.take(8)
            keys=struct.unpack_from("<H",dh,0)[0]
            if keys>65535:raise ValueError("delta track exceeds 65535 keyed frames")
            if pos==0:
                if keys:
                    frames=c.take(32)
                    c.take((keys+1)*(2 if wide else 1))
                    if pointer_kind(u64(frames,24)) in ("follows","insert"):
                        small=bool(dh[2])
                        c.align(0 if small else 3)
                        c.take((3 if small else 6)*(keys+1))
                else:
                    c.take(12)
            else:
                if keys:
                    frames=c.take(8)
                    c.take((keys+1)*(2 if wide else 1))
                    if pointer_kind(u64(frames,0)) in ("follows","insert"):
                        c.align(3)
                        c.take(width*(keys+1))
                else:
                    c.take(width)
    for at,count,stride,align in [
        (64,struct.unpack_from("<H",h,8)[0],1,0),
        (72,struct.unpack_from("<H",h,10)[0],2,1),
        (80,struct.unpack_from("<H",h,12)[0],4,3),
        (88,u32(h,36),2,1),
        (96,struct.unpack_from("<H",h,14)[0],1,0),
        (104,struct.unpack_from("<H",h,16)[0],4,3),
        (112,u32(h,40),2 if wide else 1,1 if wide else 0)
    ]:
        if count>32*1024*1024:
            raise ValueError("animation pool exceeds 32M elements")
        elements(at,count,stride,align)
    c.pop()
    c.pop()
    return {"asset":idx,"alias":False,"bytes":c.at-start,
        "frames":numframes,"delta_tracks":delta_tracks}

def verify_first_22_netconst_bodies(data: bytes) -> dict:
    """Validate the source body's 32-byte NetConstStrings loader proposal.

    Advance the *physical* source stream across 22 records and their
    source-owned inline strings. Never report proprietary string contents.
    Source ABI remains provisional until this authentic-data probe succeeds.
    """
    info=directory(data)
    if info["first_16_asset_types"][:16] != ["net_const_strings"]*16:
        return {"status":"not-netconst-world"}
    sizes=struct.unpack_from("<7Q",data,16)
    c=Cursor(data,sizes)
    c.take(40)
    c.push(3)
    c.push(3)
    string_count=u64(data,72)
    ptrs=c.take(string_count*8) if string_count else b""
    for i in range(string_count):
        if pointer_kind(u64(ptrs,i*8)) in ("follows","insert"):
            c.string()
    c.pop()
    globalptr=u64(data,104)
    if pointer_kind(globalptr) in ("follows","insert"):
        inner=u64(c.take(8),0)
        if pointer_kind(inner) in ("follows","insert"):
            gfx_globals(c)
    c.pop()
    c.push(3)
    c.align(3)
    count=u64(data,88)
    asset_bytes=c.take(count*16)
    if c.at!=info["exact_asset_table_offset"]+count*16:
        raise ValueError("first body cursor drifted from authenticated directory")
    base=c.at
    counts=[]
    for i in range(22):
        kind=u64(asset_bytes,i*16)
        if kind!=52:
            raise ValueError(f"original asset #{i} is {kind}, not net_const_strings")
        ptr=pointer_kind(u64(asset_bytes,i*16+8))
        if ptr not in ("follows","insert"):
            raise ValueError(f"original net_const_strings #{i} lacks inline owner")
        c.push(0)
        c.align(3)
        raw=c.take(32)
        c.push(3)
        nameptr=pointer_kind(u64(raw,0))
        if nameptr in ("follows","insert"):
            c.string()
        n=u32(raw,16)
        if n>1_000_000:
            raise ValueError(f"original net string count {n} exceeds limit at #{i}")
        valueptr=pointer_kind(u64(raw,24))
        if valueptr in ("follows","insert"):
            c.align(7)
            table=c.take(n*8)
            for j in range(n):
                if pointer_kind(u64(table,j*8)) in ("follows","insert"):
                    c.string()
        elif n:
            raise ValueError(f"original net strings #{i} references an unclosed source table")
        counts.append(n)
        c.pop()
        c.pop()
    # Inspect the NEXT original ComWorld body at index 22. The layout below
    # is a candidate inferred from existing Rust code; real data must prove
    # that its lengths/pointers permit safe source-order traversal.
    comworld={"status":"not-validated"}
    try:
        if u64(asset_bytes,22*16)!=20:
            raise ValueError("XAsset #22 is not ComWorld")
        if pointer_kind(u64(asset_bytes,22*16+8)) not in ("follows","insert"):
            raise ValueError("ComWorld owner is not inline")
        com_start=c.at
        c.push(0)
        c.align(3)
        raw=c.take(40)
        c.push(3)
        if pointer_kind(u64(raw,0)) in ("follows","insert"):
            c.string()
        light_count=u32(raw,12)
        if light_count>100000:
            raise ValueError(f"ComWorld light count out of range {light_count}")
        positions=[]
        if pointer_kind(u64(raw,16)) in ("follows","insert"):
            c.align(3)
            source_lights=c.take(light_count*120)
            # Each serialized light contains the original XString reference at
            # offset 112. Do not expose source strings in public logs.
            for i in range(light_count):
                ptr=pointer_kind(u64(source_lights,i*120+112))
                if ptr in ("follows","insert"):
                    c.string()
                positions.append(ptr)
        elif light_count:
            raise ValueError("ComWorld primary light array not inline")
        secondary_count=u32(raw,24)
        if secondary_count>100000:
            raise ValueError(f"ComWorld auxiliary array count out of range {secondary_count}")
        if pointer_kind(u64(raw,32)) in ("follows","insert"):
            c.align(3)
            c.take(secondary_count*10)
        c.pop()
        c.pop()
        comworld={"status":"candidate_40_byte_ComWorld_walk_passed",
            "first_comworld_offset":com_start,
            "after_comworld_offset":c.at,
            "primary_light_count":light_count,
            "primary_light_name_pointers":dict(collections.Counter(positions)),
            "secondary_array_count":secondary_count,
            "next_asset_type":ASSET_TYPES[u64(asset_bytes,23*16)]}
    except ValueError as error:
        comworld={"status":"blocked", "reason":str(error)}
    # Probe the next LightDef fixed header without taking unsupported
    # nested image assets out of order. A nested inline image is a HARD
    # frontier until its loader has independently been verified.
    lightdef={"status":"not-validated"}
    if comworld["status"]=="candidate_40_byte_ComWorld_walk_passed":
        try:
            if u64(asset_bytes,23*16)!=27:
                raise ValueError("asset #23 is not LightDef")
            if pointer_kind(u64(asset_bytes,23*16+8)) not in ("follows","insert"):
                raise ValueError("asset #23 owner not inline")
            light_start=c.at
            c.push(0)
            c.align(3)
            light_hdr=c.take(48)
            c.push(3)
            nm=pointer_kind(u64(light_hdr,0))
            if nm in ("follows","insert"):
                c.string()
            children=[pointer_kind(u64(light_hdr,x)) for x in (8,24)]
            images=[]
            for image_ref in children:
                if image_ref not in ("follows","insert"):
                    continue
                # Fixed original 104-byte GfxImage ABI. Do not guess bytes
                # for a missing inline image or interpret its pixel format.
                image_at=c.at
                c.push(0)
                c.align(3)
                image_raw=c.take(104)
                c.push(3)
                width,height=struct.unpack_from("<HH",image_raw,44)
                image_name_kind=pointer_kind(u64(image_raw,96))
                if image_name_kind in ("follows","insert"):
                    c.string()
                pixel_kind=pointer_kind(u64(image_raw,56))
                pixel_len=1 if image_raw[29]==11 else u32(image_raw,36)
                if pixel_len>512*1024*1024:
                    raise ValueError(f"inline GfxImage pixel length exceeds cap {pixel_len}")
                if pixel_kind in ("follows","insert"):
                    c.push(0)
                    c.align(3)
                    c.take(pixel_len)
                    c.pop()
                c.pop()
                c.pop()
                # Retail sometimes embeds a named placeholder GfxImage
                # without a GPU texture. Preserve its source identity, but
                # never lower it to a renderable image.
                missing=(width==0 or height==0)
                empty=(width==0 and height==0 and u32(image_raw,24)==0
                    and image_raw[53]==0 and pixel_kind=="null")
                if missing and not empty:
                    raise ValueError(f"invalid GfxImage dimensions at {image_at}; "
                        f"{width}x{height}, format={u32(image_raw,24)}, "
                        f"pixel={pixel_kind}, streamed={image_raw[53]}")
                images.append({
                    "source_only_null_image":empty,
                    "source_offset":image_at,
                    "width":width,"height":height,
                    "dxgi_format":u32(image_raw,24),
                    "streamed":bool(image_raw[53]),
                    "inline_pixel_bytes":pixel_len if pixel_kind in ("follows","insert") else 0,
                })
            lightdef={"status":"candidate_LightDef_and_nested_GfxImage_walk_passed",
                "first_lightdef_offset":light_start,
                "after_lightdef_offset":c.at,
                "nested_image_pointer_kinds":children,
                "nested_image_headers":images,
                "next_asset_type":ASSET_TYPES[u64(asset_bytes,24*16)]}
            c.pop()
            c.pop()
        except ValueError as error:
            lightdef={"status":"blocked","reason":str(error)}
    technique={"status":"not_validated"}
    if lightdef["status"]=="candidate_LightDef_and_nested_GfxImage_walk_passed":
        try:
            if u64(asset_bytes,24*16)!=12:
                raise ValueError("next original asset #24 is not TechniqueSet")
            if pointer_kind(u64(asset_bytes,24*16+8)) not in ("follows","insert"):
                raise ValueError("TechniqueSet handle not inline")
            start=c.at
            c.push(0)
            c.align(3)
            hdr=c.take(3312)
            c.push(3)
            nameptr=pointer_kind(u64(hdr,0))
            if nameptr in ("follows","insert"):
                c.string()
            refs=[pointer_kind(u64(hdr,16+8*i)) for i in range(412)]
            dist=dict(collections.Counter(refs))
            firstinline=next((i for i,k in enumerate(refs) if k in ("follows","insert")),None)
            technique={"status":"candidate_3312_byte_TechniqueSet_fixed_header_validated",
                "first_techniqueset_offset":start,
                "after_techniqueset_header_and_name_offset":c.at,
                "name_pointer_kind":nameptr,
                "original_technique_ref_kinds":dist,
                "first_inline_technique":firstinline,
                "nested_technique_body_walk":"not_yet_attempted"}
            c.pop()
            c.pop()
        except ValueError as error:
            technique={"status":"blocked","reason":str(error)}
    first_material={"status":"not_validated"}
    if technique["status"]=="candidate_3312_byte_TechniqueSet_fixed_header_validated" and technique["first_inline_technique"] is None:
        try:
            if u64(asset_bytes,25*16)!=5:
                raise ValueError("original #25 is not MATERIAL")
            start=c.at
            c.push(0)
            c.align(3)
            hdr=c.take(936)
            c.push(3)
            fields={"name":0,"techniqueSet":464,"textureTable":472,
                "constantTable":480,"stateBitsTable":488,
                "constantBufferTable":912,"subMaterials":928}
            refs={k:pointer_kind(u64(hdr,v)) for k,v in fields.items()}
            first_material={
                "status":"original_936_byte_Material_header_validated",
                "source_header_offset":start,
                "after_fixed_header_offset":c.at,
                "pointer_kinds":refs,
                "textureCount":hdr[452],
                "constantCount":hdr[453],
                "stateBitsCount":hdr[454],
                "constantBufferCount":hdr[920],
                "layerCount":hdr[458],
                "nested_deps":"not_yet_walked",
            }
            if refs["name"] in ("follows","insert"):
                c.string()
            if refs["techniqueSet"] in ("follows","insert"):
                raise ValueError("material #25 has a nested inline TechniqueSet; pass walker needed")
            if refs["textureTable"] in ("follows","insert"):
                n=hdr[452]
                c.align(3)
                tex=c.take(n*16)
                image_pointers=[pointer_kind(u64(tex,i*16+8)) for i in range(n)]
                first_material["image_pointer_kinds"]=image_pointers
                image_summaries=[]
                for kind in image_pointers:
                    if kind not in ("follows","insert"):
                        continue
                    at=c.at
                    c.push(0)
                    c.align(3)
                    iraw=c.take(104)
                    c.push(3)
                    nameptr=pointer_kind(u64(iraw,96))
                    if nameptr in ("follows","insert"):
                        c.string()
                    pixelptr=pointer_kind(u64(iraw,56))
                    length=1 if iraw[29]==11 else u32(iraw,36)
                    if length>512*1024*1024:
                        raise ValueError("authored inline image >512 MiB")
                    if pixelptr in ("follows","insert"):
                        c.push(0)
                        c.align(3)
                        c.take(length)
                        c.pop()
                    width,height=struct.unpack_from("<HH",iraw,44)
                    null=(width==0 and height==0 and pixelptr=="null"
                          and u32(iraw,24)==0 and iraw[53]==0)
                    if (width==0 or height==0) and not null:
                        raise ValueError(f"material nested image invalid dimensions at {at}")
                    image_summaries.append({
                        "source_offset":at,"width":width,"height":height,
                        "format":u32(iraw,24),
                        "inline_pixel_bytes":length if pixelptr in ("follows","insert") else 0,
                        "null_gpu_resource":null,"streamed":bool(iraw[53])})
                    c.pop()
                    c.pop()
                first_material["nested_images"]=image_summaries
            if refs["constantTable"] in ("follows","insert"):
                c.align(15)
                c.take(hdr[453]*32)
            if refs["stateBitsTable"] in ("follows","insert"):
                c.align(3)
                c.take(hdr[454]*28)
            if refs["constantBufferTable"] in ("follows","insert"):
                raise ValueError("material #25 inline ConstantBufferTable needs per-stage stream walker")
            if refs["subMaterials"] in ("follows","insert"):
                raise ValueError("material #25 inline SubMaterials needs source string walker")
            first_material["status"]="original_material_25_inline_loader_order_passed"
            first_material["after_full_material_offset"]=c.at
            first_material["next_source_pointer_kind"]=pointer_kind(u64(data,c.at))
            c.pop()
            c.pop()
        except ValueError as error:
            first_material["status"]="blocked"
            first_material["reason"]=str(error)
    materials_scan={"status":"not_attempted"}
    if first_material.get("status")=="original_material_25_inline_loader_order_passed":
        start=c.at
        decoded=1
        aliases=0
        image_count=len(first_material.get("nested_images",[]))
        first_blocker=None
        for idx in range(26,725):
            try:
                info=walk_original_source_material(c,asset_bytes,idx)
                decoded+=1
                aliases+=int(info.get("alias",False))
                image_count+=info.get("images",0)
            except (ValueError,struct.error) as error:
                first_blocker={"asset_index":idx,
                    "source_offset":c.at,"reason":str(error)}
                break
        materials_scan={
            "status":"all_700_material_handles_walked" if first_blocker is None
                else "blocked_on_original_material_dependency",
            "handles_consumed":decoded,
            "aliased_handles":aliases,
            "inline_gfximages_walked":image_count,
            "first_blocker":first_blocker,
            "after_consumed_offset":c.at,
            "first_xanim_asset_index":725,
        }
    anim_header={"status":"not_attempted"}
    if materials_scan["status"]=="all_700_material_handles_walked":
        try:
            if u64(asset_bytes,725*16)!=2:
                raise ValueError("next source XAsset is not XAnimParts")
            # Header-only observation must not advance the live body
            # cursor. The following full animation walk consumes this record.
            at=c.at
            h=data[at:at+136]
            if len(h)!=136:
                raise ValueError("first authored XAnimParts header truncated")
            ptr_fields={"name":0,"names":56,"dataByte":64,"dataShort":72,
                "dataInt":80,"randomShort":88,"randomByte":96,
                "randomInt":104,"indices":112,"notify":120,"deltaPart":128}
            kinds={name:pointer_kind(u64(h,off)) for name,off in ptr_fields.items()}
            anim_header={
                "status":"original_136_byte_XAnimParts_header_validated",
                "asset_index":725,"source_offset":at,
                "ptr_kinds":kinds,
                "dataByteCount":struct.unpack_from("<H",h,8)[0],
                "dataShortCount":struct.unpack_from("<H",h,10)[0],
                "dataIntCount":struct.unpack_from("<H",h,12)[0],
                "randomDataByteCount":struct.unpack_from("<H",h,14)[0],
                "randomDataIntCount":struct.unpack_from("<H",h,16)[0],
                "numframes":struct.unpack_from("<H",h,18)[0],
                "flags":h[20],
                "boneCount":list(h[21:31]),
                "notifyCount":h[31],
                "randomDataShortCount":u32(h,36),
                "indexCount":u32(h,40),
                "nested_pool_walk":"not_yet_attempted",
            }
        except (ValueError,struct.error) as error:
            anim_header={"status":"blocked","reason":str(error)}
    anim_scan={"status":"not_attempted"}
    if anim_header["status"]=="original_136_byte_XAnimParts_header_validated":
        count=0
        bytes_before=c.at
        failure=None
        delta_count=0
        for idx in range(725,770):
            try:
                record=walk_iw6_animation_record(c,asset_bytes,idx)
                count+=1
                delta_count+=record.get("delta_tracks",0)
            except (ValueError,struct.error) as error:
                failure={"asset_index":idx,"source_offset":c.at,"reason":str(error)}
                break
        anim_scan={
            "status":"all_45_original_XAnimParts_walked" if failure is None
                else "blocked_on_original_animation_layout",
            "handles_consumed":count,
            "delta_track_headers":delta_count,
            "first_blocker":failure,
            "first_animation_offset":bytes_before,
            "after_consumed_offset":c.at,
            "next_type_if_complete":"technique_set",
        }
    # First authenticated FX source blocker follows 25 technique sets
    # after XAnimParts. This does not invent shader bytecode or passes.
    postanim_techniques={"status":"not_attempted"}
    first_fx={"status":"not_attempted"}
    if anim_scan["status"]=="all_45_original_XAnimParts_walked":
        count=0
        aliases=0
        blocker=None
        start=c.at
        for idx in range(770,795):
            try:
                if u64(asset_bytes,idx*16)!=12:
                    raise ValueError(f"XAsset #{idx} should be TechniqueSet")
                assetptr=pointer_kind(u64(asset_bytes,idx*16+8))
                if assetptr not in ("follows","insert"):
                    aliases+=1
                    count+=1
                    continue
                c.push(0)
                c.align(3)
                ts=c.take(3312)
                c.push(3)
                if pointer_kind(u64(ts,0)) in ("follows","insert"):
                    c.string()
                refs=[pointer_kind(u64(ts,16+j*8)) for j in range(412)]
                if any(k in ("follows","insert") for k in refs):
                    raise ValueError("authored nested MaterialTechnique requires pass/shader traversal")
                c.pop()
                c.pop()
                count+=1
            except (ValueError,struct.error) as error:
                blocker={"asset_index":idx,"source_offset":c.at,"reason":str(error)}
                break
        postanim_techniques={
            "status":"all_25_technique_sets_traversed" if blocker is None else "blocked_on_original_technique_dependency",
            "first_technique_source_offset":start,
            "technique_handles_advanced":count,
            "aliased_technique_handles":aliases,
            "after_source_offset":c.at,
            "first_blocker":blocker,
        }
        if blocker is None:
            try:
                if u64(asset_bytes,795*16)!=37:
                    raise ValueError("XAsset #795 expected original FX effect")
                if pointer_kind(u64(asset_bytes,795*16+8)) not in ("follows","insert"):
                    raise ValueError("first FX asset unexpectedly not source-owned inline")
                source_at=c.at
                fx=data[source_at:source_at+64]
                if len(fx)!=64:
                    raise ValueError("first original FxEffectDef header truncated")
                looping=u32(fx,20)
                one_shot=u32(fx,24)
                emission=u32(fx,28)
                total=looping+one_shot+emission
                if total>100000:
                    raise ValueError("original FX element count exceeds bounded source parser")
                first_fx={
                    "status":"original_FxEffectDef_fixed_header_observed",
                    "asset_index":795,
                    "source_offset":source_at,
                    "name_pointer_class":pointer_kind(u64(fx,0)),
                    "effects_pointer_class":pointer_kind(u64(fx,56)),
                    "looping_elements":looping,
                    "one_shot_elements":one_shot,
                    "emission_elements":emission,
                    "total_elements":total,
                    "candidate_serialized_element_bytes":total*312,
                    "nested_elements_walked":False,
                }
            except (ValueError,struct.error) as error:
                first_fx={"status":"blocked","reason":str(error)}
    return {
        "status":"22_original_net_const_strings_bodies_walked",
        "first_body_offset":base,
        "after_22_source_offset":c.at,
        "net_const_record_count":len(counts),
        "net_const_string_count_total":sum(counts),
        "first_6_record_counts":counts[:6],
        "next_xasset_type":ASSET_TYPES[u64(asset_bytes,22*16)],
        "comworld_probe":comworld,
        "lightdef_probe":lightdef,
        "techniqueset_probe":technique,
        "first_material_probe":first_material,
        "material_prefix_scan":materials_scan,
        "first_anim_header":anim_header,
        "anim_prefix_scan":anim_scan,
        "post_anim_technique_scan":postanim_techniques,
        "first_original_fx_header":first_fx,
    }

def inspect_pathdata_header(data: bytes) -> dict:
    """Audit the 136-byte IW6 PathData header at the authenticated asset cursor.

    Numeric fields and tagged pointers are read from real FF bytes. Nothing is
    skipped or reported as a full navigation graph until source arrays close.
    """
    d=directory(data)
    if d["asset_count"]!=2 or d["first_16_asset_types"]!=["pathdata","rawfile"]:
        raise ValueError("source zone is not the two-entry original path zone")
    at=d["exact_asset_table_offset"]+32
    end=at+136
    if end>len(data):
        raise ValueError("original PathData header truncated")
    hdr=data[at:end]
    ptr_fields={"name":0,"nodes":16,"pathVis":32,"nodeTree":48,
        "dynamicNodeGroups":64,"pathExposure":80,"pathNoPeekVis":96,
        "pathZones":112,"pathDynStates":128}
    kinds={name:pointer_kind(u64(hdr,off)) for name,off in ptr_fields.items()}
    counts={name:u32(hdr,at) for name,at in {
        "nodeCount":8,"visBytes":28,"nodeTreeCount":40,
        "dynamicNodeGroupCount":56,"exposureBytes":72,
        "noPeekVisBytes":88,"zoneCount":104,
        "zonesBytes":108,"dynStatesBytes":120
    }.items()}
    counts["version"]=struct.unpack_from("<H",hdr,26)[0]
    if counts["nodeCount"]>1000000 or counts["nodeTreeCount"]>1000000:
        raise ValueError("original PathData counts exceed safe cap")
    if counts["zoneCount"]>counts["nodeCount"]:
        raise ValueError("original zone node count exceeds nodes")
    return {
        "status":"retail_PathData_136_byte_header_verified_only",
        "source_header_offset":at,
        "source_header_end":end,
        "counts":counts,
        "source_pointer_kinds":kinds,
        "nodes_inline_bytes_if_present":counts["nodeCount"]*176
            if kinds["nodes"] in ("follows","insert") else 0,
        "full_nested_pathdata_walk":"not_yet_attempted",
    }

def inspect(path: pathlib.Path) -> dict:
    stats=StreamStats()
    with path.open("rb") as f:
        header=outer_header(f)
        if header.byte_count_a != path.stat().st_size:
            raise ValueError("original R2 file length does not match signed FF header")
        chunks=(verified_authenticated_chunks(f,header.stream_offset,stats)
                if header.envelope=="sha256-master-blocks"
                else direct_chunks(f,header.stream_offset,stats))
        inflated=zlib.decompressobj()
        data=bytearray()
        sha=hashlib.sha256()
        for chunk in chunks:
            if inflated.eof:
                continue
            out=inflated.decompress(chunk)
            if len(data)+len(out)>MAX_OUTPUT:
                raise ValueError("source decompression exceeds 4 GiB guard")
            data.extend(out)
            sha.update(out)
        if not inflated.eof:
            raise ValueError("original compressed stream did not terminate")
    prelude=directory(bytes(data))
    body_probe=(verify_first_22_netconst_bodies(bytes(data))
                if path.name=="mp_alien_town.ff" else None)
    path_probe=(inspect_pathdata_header(bytes(data))
                if path.name=="mp_alien_town_path.ff" else None)
    return {
        "file":path.name, "original_size":path.stat().st_size,
        "decoded_size":len(data),
        "decoded_sha256":sha.hexdigest(),
        "authenticated_sha256_blocks":stats.sha256_blocks,
        "unverified_partial_tail_bytes":stats.partial_tail_bytes,
        **prelude,
        "first_netconst_body_probe":body_probe,
        "pathdata_header_probe":path_probe,
        "status":"retail_compressed_stream_verified_and_xasset_prelude_walked",
    }

class Tests(unittest.TestCase):
    def test_inline_prelude_and_source_order(self):
        # Synthetic test checks our cursor arithmetic, not retail correctness.
        inline=0xfdfdfdf0ffffffff
        body=bytearray(72+40)
        struct.pack_into("<5Q",body,72,1,inline,2,inline,0)
        body.extend(struct.pack("<Q",inline))
        body.extend(b"original\0")
        for kind in (13,26):
            body.extend(struct.pack("<QQ",kind,inline))
        struct.pack_into("<Q",body,0,len(body)-72)
        struct.pack_into("<Q",body,16,4096)
        struct.pack_into("<Q",body,40,4096)
        got=directory(bytes(body))
        self.assertEqual(got["exact_asset_table_offset"],129)
        self.assertEqual(got["first_16_asset_types"],["image","gfxworld"])
        self.assertEqual(got["type_counts"],{"gfxworld":1,"image":1})

if __name__=="__main__":
    if sys.argv[1:]==["--test"]:
        unittest.main(argv=[sys.argv[0]])
    else:
        for filename in sys.argv[1:]:
            print(json.dumps(inspect(pathlib.Path(filename)),sort_keys=True),flush=True)
