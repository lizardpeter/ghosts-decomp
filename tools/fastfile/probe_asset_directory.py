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
            if any(x in ("follows","insert") for x in children):
                lightdef={"status":"blocked_on_inline_GfxImage_dependency",
                    "first_lightdef_offset":light_start,
                    "nested_image_pointer_kinds":children}
            else:
                lightdef={"status":"fixed_header_and_name_walked",
                    "first_lightdef_offset":light_start,
                    "after_lightdef_offset":c.at,
                    "nested_image_pointer_kinds":children,
                    "next_asset_type":ASSET_TYPES[u64(asset_bytes,24*16)]}
            c.pop()
            c.pop()
        except ValueError as error:
            lightdef={"status":"blocked","reason":str(error)}
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
    return {
        "file":path.name, "original_size":path.stat().st_size,
        "decoded_size":len(data),
        "decoded_sha256":sha.hexdigest(),
        "authenticated_sha256_blocks":stats.sha256_blocks,
        "unverified_partial_tail_bytes":stats.partial_tail_bytes,
        **prelude,
        "first_netconst_body_probe":body_probe,
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
