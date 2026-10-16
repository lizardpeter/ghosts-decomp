"""Differential cases for gfx_d3d/r_state.cpp against the Store build.

The immediate context is a model object (com.py) or NULL; the shader caches start with random values. Every
call to the context is compared with its arguments."""
import random
import struct

from com import ComModel
from syms import va

STORE = "iw6mp64_MSStore_ship"
CTX = "ID3D11DeviceContext"
SIGS = {(CTX, 9 * 8): "ppi", (CTX, 11 * 8): "ppi", (CTX, 60 * 8): "ppi", (CTX, 64 * 8): "ppi", (CTX, 17 * 8): "p"}


def _input(r):
    has_ctx = r.random() < 0.8
    caches = [r.getrandbits(64) for _ in range(5)]

    def setup(w):
        model = ComModel(SIGS)
        model.install(w.m)
        w.u64(va("dx") + 0x10, model.new(CTX) if has_ctx else 0)
        for name, value in zip(("unk_14BAD2778", "unk_14BAD2780", "unk_14BAD2788", "unk_14BAD2790",
                                "unk_14BAD04B0"), caches):
            w.u64(va(name), value)
    return {"args": [], "setup": setup}


def inputs(seed, n=50):
    r = random.Random(seed)
    return [_input(r) for _ in range(n)]


CASES = [{"symbol": f"?sub_{v}@@YAXXZ", "build": STORE, "ret": "void", "inputs": inputs(int(v, 16) & 0xFFFF)}
         for v in ("14068D190", "14068D1D0", "14068D210", "14068D240", "14068D270")]
