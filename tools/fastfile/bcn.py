"""Block-compressed texture decoding (BC1-BC5) to RGBA8, and a PNG writer. Standard library only.

For previews and checks of decoded images (tools/fastfile/image.py); the formats are the public Direct3D ones
(BC1 = DXT1, BC2 = DXT3, BC3 = DXT5, BC4 = ATI1, BC5 = ATI2). BC6H and BC7 are not decoded here: export them as DDS.
"""
from __future__ import annotations

import struct
import zlib


def _565(c):
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def _color_block(blk, out, x0, y0, w, rowlen, bc1):
    c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
    a, b = _565(c0), _565(c1)
    if c0 > c1 or not bc1:
        pal = [a + (255,), b + (255,),
               tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,),
               tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)]
    else:
        pal = [a + (255,), b + (255,), tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,), (0, 0, 0, 0)]
    for i in range(16):
        x, y = x0 + (i & 3), y0 + (i >> 2)
        if x < w and y * rowlen + x * 4 + 3 < len(out):
            p = pal[(bits >> (2 * i)) & 3]
            o = (y * w + x) * 4
            out[o:o + 3] = bytes(p[:3])
            if bc1:
                out[o + 3] = p[3]


def _alpha_block(blk, signed=False):
    """BC4-style 8-byte block -> 16 values 0-255."""
    a0, a1 = blk[0], blk[1]
    if signed:
        a0, a1 = (a0 ^ 0x80), (a1 ^ 0x80)
    bits = int.from_bytes(blk[2:8], "little")
    if a0 > a1:
        pal = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    else:
        pal = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
    return [pal[(bits >> (3 * i)) & 7] for i in range(16)]


def decode(fmt_name: str, data: bytes, width: int, height: int) -> bytes:
    """One mip level -> RGBA8 (width * height * 4). BC4 gives grey; BC5 gives red/green with blue reconstructed as
    a normal map's z (sqrt(1 - x^2 - y^2), shown in 0-255)."""
    out = bytearray(b"\0\0\0\xff" * (width * height))
    bw, bh = (width + 3) // 4, (height + 3) // 4
    f = fmt_name.split("_")[0]
    size = 8 if f in ("BC1", "BC4") else 16
    signed = fmt_name.endswith("SNORM")
    rowlen = width * 4
    for by in range(bh):
        for bx in range(bw):
            blk = data[(by * bw + bx) * size:(by * bw + bx + 1) * size]
            if len(blk) < size:
                continue
            x0, y0 = bx * 4, by * 4
            if f == "BC1":
                _color_block(blk, out, x0, y0, width, rowlen, True)
            elif f in ("BC2", "BC3"):
                _color_block(blk[8:], out, x0, y0, width, rowlen, False)
                if f == "BC2":
                    al = [((int.from_bytes(blk[:8], "little") >> (4 * i)) & 15) * 17 for i in range(16)]
                else:
                    al = _alpha_block(blk[:8])
                for i in range(16):
                    x, y = x0 + (i & 3), y0 + (i >> 2)
                    if x < width and y < height:
                        out[(y * width + x) * 4 + 3] = al[i]
            elif f in ("BC4", "BC5"):
                r = _alpha_block(blk[:8], signed)
                g = _alpha_block(blk[8:16], signed) if f == "BC5" else r
                for i in range(16):
                    x, y = x0 + (i & 3), y0 + (i >> 2)
                    if x < width and y < height:
                        o = (y * width + x) * 4
                        if f == "BC4":
                            out[o:o + 3] = bytes((r[i],) * 3)
                        else:
                            nx, ny = r[i] / 127.5 - 1, g[i] / 127.5 - 1
                            nz = max(0.0, 1 - nx * nx - ny * ny) ** 0.5
                            out[o:o + 3] = bytes((r[i], g[i], int(nz * 127.5 + 127.5)))
            else:
                raise NotImplementedError(fmt_name)
    return bytes(out)


def png(rgba: bytes, width: int, height: int) -> bytes:
    raw = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
