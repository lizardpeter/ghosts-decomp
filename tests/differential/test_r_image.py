"""Differential cases for gfx_d3d/r_image.cpp, r_image_load_common.cpp and r_rendertarget.cpp against the Store build.

Images are GfxImage buffers (Store layout, 0x68 bytes) passed by pointer and compared after the call. The device and
the immediate context are COM model objects (com.py): every Direct3D call is compared with its arguments. Texture
descriptions are compared by content, view descriptions by the bytes their view dimension defines (the rest of a
view description is left uninitialised by the original), initial data by its subresource entries. Creation calls
succeed, fail with NULL or fail leaving the out pointer alone, from a random script per input. sub_1401B0040 (the
texture memory total) and sub_14062E8D0 (the image's card memory) are faked and their arguments compared; the
depth format getters are faked with random formats.
"""
import random
import struct

from com import ComModel
from harness import STACK, STACK_SIZE
from syms import va

STORE = "iw6mp64_MSStore_ship"
DEV, CTX, RES, VIEW = "ID3D11Device", "ID3D11DeviceContext", "ID3D11Resource", "ID3D11View"
SWAP, DXGIDEV, ADAPTER, UNK = "IDXGISwapChain", "IDXGIFactory", "IDXGIAdapter", "IUnknown"
DATA = 0x5C0000          # scratch: texture data and initial data built by the tests
OBJECTS = 0x008A0000     # com.py: objects are handed out from here, 0x40 bytes each, in creation order
E_OUTOFMEMORY = 0x8007000E

# device slots
CREATE_TEX1D, CREATE_TEX2D, CREATE_TEX3D, CREATE_SRV, CREATE_UAV, CREATE_RTV, CREATE_DSV = (n * 8 for n in range(4, 11))
QUERY_INTERFACE, ADD_REF, RELEASE = 0, 8, 16

FORMATS = [0, 2, 10, 11, 15, 16, 19, 20, 21, 26, 27, 28, 29, 30, 31, 32, 34, 39, 40, 41, 45, 49, 53, 54, 55, 56,
           61, 65, 70, 71, 72, 73, 74, 75, 76, 77, 78, 80, 83, 84, 95, 96, 98, 99, 100]
FLAG_BITS = [0x1, 0x2, 0x20, 0x800, 0x1000, 0x8000, 0x10000, 0x20000, 0x800000, 0x1000000, 0x2000000, 0x4000000,
             0x10000000, 0x20000000, 0x40000000, 0x80000000]


def obj_va(n):
    """Address of the n-th model object created in a setup (0-based)."""
    return OBJECTS + 0x40 * n


def rand_format(r):
    return r.choice(FORMATS) if r.random() < 0.9 else r.randint(0, 130)


def rand_flags(r):
    flags = 0
    for bit in FLAG_BITS:
        if r.random() < 0.3:
            flags |= bit
    if r.random() < 0.1:
        flags |= r.getrandbits(32)
    return flags


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def image_bytes(r, texture=None, **fields):
    """A random GfxImage (Store layout); fields override: format, mapType, semantic, category, flags, width, height,
    depth, numElements, levelCount, levels [(w, h, bits)] * 4, name."""
    tex = texture if texture is not None else [r.choice([0, r.getrandbits(48)]) for _ in range(3)]
    f = {
        "format": rand_format(r), "mapType": r.choice([2, 3, 4, 5, 6, r.randint(0, 9)]), "semantic": r.getrandbits(8),
        "category": r.choice([0, 3, 5, 6, r.getrandbits(8)]), "flags": r.getrandbits(8),
        "picmip": r.getrandbits(16), "track": r.getrandbits(8), "card": [r.getrandbits(32), r.getrandbits(32)],
        "width": r.choice([1, 4, 16, 64, 256, 1000, r.getrandbits(16)]),
        "height": r.choice([1, 4, 16, 64, 256, 1000, r.getrandbits(16)]),
        "depth": r.choice([1, 1, 2, 8, r.getrandbits(16)]), "numElements": r.choice([0, 1, 2, 6, r.getrandbits(16)]),
        "levelCount": r.choice([0, 1, 2, 5, 10, r.getrandbits(8)]),
        "unknown": bytes(r.getrandbits(8) for _ in range(11)),
        "levels": [(r.getrandbits(16), r.getrandbits(16), r.getrandbits(32)) for _ in range(4)],
        "name": r.choice([0, 0x140890F80, r.getrandbits(40)]),
    }
    f.update(fields)
    return (struct.pack("<3QI4B2sB", *tex, f["format"], f["mapType"], f["semantic"], f["category"], f["flags"],
                        struct.pack("<H", f["picmip"]), f["track"])
            + b"\0" + struct.pack("<2I4HB", *f["card"], f["width"], f["height"], f["depth"], f["numElements"],
                                  f["levelCount"])
            + f["unknown"] + b"".join(struct.pack("<2HI", *lv) for lv in f["levels"]) + struct.pack("<Q", f["name"]))


assert len(image_bytes(random.Random(0))) == 0x68


# ---- logging what the model's methods are given -----------------------------------------------------------------

def _log(call, *entry):
    call.model.machine.observed.append(("desc", call.offset, *entry))


def _read(call, va_, n):
    return bytes(call.mu.mem_read(va_, n))


SRV_BYTES = {1: 16, 2: 16, 3: 24, 4: 16, 5: 24, 6: 8, 7: 16, 8: 16, 9: 16, 10: 24, 11: 20}
RTV_BYTES = {1: 16, 2: 12, 3: 20, 4: 12, 5: 20, 6: 8, 7: 16, 8: 20}
DSV_BYTES = {1: 16, 2: 24, 3: 16, 4: 24, 5: 12, 6: 20}
UAV_BYTES = {1: 20, 2: 12, 3: 20, 4: 12, 5: 20, 8: 20}


def log_view_desc(call, i, table):
    """A view description by the bytes its dimension defines."""
    p = call.arg(i)
    if not p:
        _log(call, None)
        return
    dim = struct.unpack("<I", _read(call, p + 4, 4))[0]
    _log(call, _read(call, p, table.get(dim, 8)))


def _subresource_count(call):
    """Number of subresources a texture description describes."""
    p = call.arg(0)
    if call.offset == CREATE_TEX1D:
        width, mips, array = struct.unpack("<3I", _read(call, p, 12))
        dims = [width]
    elif call.offset == CREATE_TEX2D:
        width, height, mips, array = struct.unpack("<4I", _read(call, p, 16))
        dims = [width, height]
    else:
        width, height, depth, mips = struct.unpack("<4I", _read(call, p, 16))
        array, dims = 1, [width, height, depth]
    # a full mip chain (MipLevels 0) with initial data reads entries nobody filled in: not logged
    return min(mips * array, 64) if mips else 0


def log_init_data(call, i):
    """Initial data by its entries; data on the stack (whose address differs between the builds) by content."""
    p = call.arg(i)
    if not p:
        _log(call, None)
        return
    entries = []
    for k in range(_subresource_count(call)):
        sysmem, pitch, slice_ = struct.unpack("<QII", _read(call, p + 16 * k, 16))
        if STACK <= sysmem < STACK + STACK_SIZE:
            entries.append(("stack", _read(call, sysmem, 64), pitch, slice_))
        else:
            entries.append((sysmem, pitch, slice_))
    _log(call, entries)


class Script:
    """Outcomes of creation calls, consumed in call order (the same order in both runs)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def next(self):
        return self.outcomes.pop(0) if self.outcomes else "ok"


def rand_outcomes(r, n=12, fail=0.2, keep=True):
    """Creation outcomes; without `keep`, a failure always writes NULL (for out pointers to the caller's locals,
    which differ between the builds when left alone)."""
    failures = ["fail_null", "fail_keep"] if keep else ["fail_null"]
    return [r.choice(failures) if r.random() < fail else "ok" for _ in range(n)]


def creator(script, kind, out_index, log=None):
    """A creation method: logs what log() reads, then succeeds (new object of `kind` through the out pointer) or
    fails per the script."""
    def fn(call):
        if log:
            log(call)
        outcome = script.next()
        if outcome == "ok":
            call.out_object(out_index, kind)
            return 0
        if outcome == "fail_null" and call.arg(out_index):
            call.write(call.arg(out_index), bytes(8))
        return E_OUTOFMEMORY
    return fn


DEVICE_SIGS = {
    (DEV, CREATE_TEX1D): "ppp", (DEV, CREATE_TEX2D): "ppp", (DEV, CREATE_TEX3D): "ppp",
    (DEV, CREATE_SRV): "ppp", (DEV, CREATE_UAV): "ppp", (DEV, CREATE_RTV): "ppp", (DEV, CREATE_DSV): "ppp",
}
DEVICE_DUMPS = {(DEV, CREATE_TEX1D): {0: 0x20}, (DEV, CREATE_TEX2D): {0: 0x2C}, (DEV, CREATE_TEX3D): {0: 0x24}}


def device_results(script):
    return {
        (DEV, CREATE_TEX1D): creator(script, RES, 2, lambda c: log_init_data(c, 1)),
        (DEV, CREATE_TEX2D): creator(script, RES, 2, lambda c: log_init_data(c, 1)),
        (DEV, CREATE_TEX3D): creator(script, RES, 2, lambda c: log_init_data(c, 1)),
        (DEV, CREATE_SRV): creator(script, VIEW, 2, lambda c: log_view_desc(c, 1, SRV_BYTES)),
        (DEV, CREATE_UAV): creator(script, VIEW, 2, lambda c: log_view_desc(c, 1, UAV_BYTES)),
        (DEV, CREATE_RTV): creator(script, VIEW, 2, lambda c: log_view_desc(c, 1, RTV_BYTES)),
        (DEV, CREATE_DSV): creator(script, VIEW, 2, lambda c: log_view_desc(c, 1, DSV_BYTES)),
    }


def install_model(w, sigs=None, results=None, dumps=None, device=True, context=False):
    """A model with a device (dx.d3d11device) and optionally an immediate context; returns the model."""
    model = ComModel({**DEVICE_SIGS, **(sigs or {})}, results, {**DEVICE_DUMPS, **(dumps or {})})
    model.install(w.m)
    w.u64(va("dx") + 0x8, model.new(DEV) if device else 0)
    if context:
        w.u64(va("dx") + 0x10, model.new(CTX))
    return model


def dvar(w, value, fmt="<B"):
    d = w.alloc(bytes(0x60))
    w.write(d + 0x10, struct.pack(fmt, value))
    return d


# ---- fakes ------------------------------------------------------------------------------------------------------

def _stack_args(mu, n):
    from unicorn.x86_const import UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP
    regs = [mu.reg_read(x) for x in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9)]
    rsp = mu.reg_read(UC_X86_REG_RSP)
    return (regs + [struct.unpack("<Q", bytes(mu.mem_read(rsp + 0x28 + 8 * k, 8)))[0] for k in range(n - 4)])[:n]


class Recorder:
    """Fakes whose arguments are appended to the machine's observed calls (set .machine in the setup)."""
    machine = None
    model = None


REC = Recorder()


def fake_track(mu):
    """sub_1401B0040(image): the image by content (it may be a copy on the stack)."""
    image = _stack_args(mu, 1)[0]
    REC.machine.observed.append(("sub_1401B0040", bytes(mu.mem_read(image, 0x68))))
    return 0


def fake_card_memory(mu):
    """sub_14062E8D0(image, imageFlags, imageFormat, width, height, depth, numElements)."""
    args = _stack_args(mu, 7)
    REC.machine.observed.append(("sub_14062E8D0", args[0], *(a & 0xFFFFFFFF for a in args[1:])))
    return 0


def fake_format(value):
    def fn(mu):
        REC.machine.observed.append(("format getter", value))
        return value
    return fn


TRACK = "?sub_1401B0040@@YAXPEAUGfxImage@@@Z"
CARD = "?sub_14062E8D0@@YAXPEAUGfxImage@@HW4DXGI_FORMAT@@HHHH@Z"
FMT_GE2 = "?sub_14064F310@@YA?AW4DXGI_FORMAT@@XZ"
FMT_LT2 = "?sub_14064F350@@YA?AW4DXGI_FORMAT@@XZ"
IMAGE_FAKES = {TRACK: fake_track, CARD: fake_card_memory}


def case(symbol, inputs, ret="void", fakes=None, observe=None):
    c = {"symbol": symbol, "build": STORE, "ret": ret, "inputs": inputs, "fakes": {**IMAGE_FAKES, **(fakes or {})}}
    if observe:
        c["observe"] = observe
    return c


def model_setup(r, extra=None, context=False, device=True, sigs=None, results=None, dumps=None, keep=True):
    """A setup installing a model whose creation calls follow a random script, then `extra(w, model)`."""
    outcomes = rand_outcomes(r, keep=keep)

    def setup(w):
        REC.machine = w.m
        script = Script(outcomes)
        res = device_results(script)
        if results:
            res.update(results(script))
        model = install_model(w, sigs, res, dumps, device=device, context=context)
        REC.model = model
        if extra:
            extra(w, model)
    return setup


# ---- pure functions ---------------------------------------------------------------------------------------------

def format_inputs(seed):
    r = random.Random(seed)
    return [[f] for f in range(0, 132)] + [[r.getrandbits(32)] for _ in range(20)]


def card_memory_inputs(seed):
    r = random.Random(seed)
    out = []
    for f in list(range(0, 104)) * 2:
        out.append([f, r.choice([1, 2, 3, 4, 5, 7, 64, 1000, r.getrandbits(16), r.getrandbits(32)]),
                    r.choice([1, 2, 3, 4, 5, 7, 64, 1000, r.getrandbits(16), r.getrandbits(32)]),
                    r.choice([1, 2, 6, r.getrandbits(16), r.getrandbits(32)])])
    return out


def count_mipmaps_inputs(seed):
    r = random.Random(seed)
    dims = [0, 1, 2, 3, 4, 5, 7, 8, 9, 255, 256, 257, 1000, 4096, 65535, 0x40000000, 0x80000000]
    return [[r.choice([0, 0, 2, 1, 3, r.getrandbits(32)]), r.choice(dims), r.choice(dims), r.choice(dims)]
            for _ in range(300)]


def usage_inputs(seed):
    r = random.Random(seed)
    out = []
    for _ in range(300):
        out.append([rand_flags(r), struct.pack("<I", r.getrandbits(32)), struct.pack("<I", r.getrandbits(32)),
                    struct.pack("<I", r.getrandbits(32))])
    return out


def alloc_prog_inputs(seed):
    r = random.Random(seed)
    return [[r.choice([0, 1, 0x51, r.randint(0, 0x1C0)]), r.getrandbits(8), r.getrandbits(8)] for _ in range(100)]


def msaa_inputs(seed):
    r = random.Random(seed)
    out = []
    for _ in range(100):
        count = r.choice([0, 1, 2, 4, 8, r.getrandbits(32)])
        out.append({"args": [bytes(r.getrandbits(8) for _ in range(0x2C)), rand_flags(r)],
                    "setup": (lambda c: lambda w: w.u32(va("unk_14A3852BC"), c))(count)})
    return out


def stream_level_inputs(seed):
    r = random.Random(seed)
    return [[image_bytes(r), r.randint(0, 3)] for _ in range(100)]


# ---- texture creation -------------------------------------------------------------------------------------------

def _init_data(r):
    """None, or a scratch array of subresource entries (the creation functions pass it through)."""
    if r.random() < 0.4:
        return 0, None
    entries = b"".join(struct.pack("<QII", DATA + 0x100 * k, r.getrandbits(12), r.getrandbits(16)) for k in range(64))
    return DATA, entries


def _create_input(r, args_fn):
    init_va, entries = _init_data(r)
    sample_count = r.choice([1, 2, 4, 8, r.getrandbits(32)])

    def extra(w, model):
        w.u32(va("unk_14A3852BC"), sample_count)
        if entries:
            w.m.mu.mem_write(init_va, entries)
    return {"args": args_fn(r, init_va), "setup": model_setup(r, extra)}


def _dim(r):
    return r.choice([1, 2, 4, 16, 64, 256, 1024, r.getrandbits(16)])


def _mips(r):
    return r.choice([0, 1, 2, 5, 10, r.getrandbits(32)])


def create_inputs(seed, args_fn, n=150):
    r = random.Random(seed)
    return [_create_input(r, args_fn) for _ in range(n)]


CREATE_1D = lambda r, init: [image_bytes(r), _dim(r), _mips(r), rand_flags(r), rand_format(r), init]
CREATE_2D = lambda r, init: [image_bytes(r), _dim(r), _dim(r), _mips(r), rand_flags(r), rand_format(r), init]
CREATE_3D = lambda r, init: [image_bytes(r), _dim(r), _dim(r), _dim(r), _mips(r), rand_flags(r), rand_format(r), init]
CREATE_ARRAY = lambda r, init: [image_bytes(r), _dim(r), _dim(r), r.choice([1, 2, 6, r.getrandbits(16)]), _mips(r),
                                rand_flags(r), rand_format(r), init]
CREATE_CUBE = lambda r, init: [image_bytes(r), _dim(r), _mips(r), rand_flags(r), rand_format(r), init]


def stream_create_inputs(seed, n=150):
    """sub_14062B110(image, picmip, outTexture)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        image = image_bytes(r, levels=[(_dim(r), _dim(r), r.getrandbits(32)) for _ in range(4)])
        out.append({"args": [image, r.randint(0, 3), bytes(r.getrandbits(8) for _ in range(0x18))],
                    "setup": model_setup(r)})
    return out


def color_rt_inputs(seed, n=100):
    r = random.Random(seed)
    return [{"args": [r.getrandbits(32), image_bytes(r, texture=[obj_va(1), 0, 0]), rand_flags(r), rand_format(r)],
             "setup": model_setup(r, lambda w, model: model.new(RES))} for _ in range(n)]


def depth_rt_inputs(seed, n=100):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        lt2, ge2 = r.choice([20, 40, r.randint(0, 120)]), r.choice([20, 55, r.randint(0, 120)])
        out.append({"args": [r.choice([0, 1, 2, 3, 0xFFFFFFFF, r.getrandbits(32)]),
                             image_bytes(r, texture=[obj_va(1), 0, 0])],
                    "setup": model_setup(r, lambda w, model: model.new(RES)), "fakes": {FMT_LT2: fake_format(lt2), FMT_GE2: fake_format(ge2)}})
    return out


# ---- image setup ------------------------------------------------------------------------------------------------

def _maptype_flags(r):
    flags = rand_flags(r) & ~0x38000
    return flags | r.choice([0, 0, 0x8000, 0x10000, 0x20000, 0x18000, 0x28000, 0x30000, 0x38000])


def setup_inputs(seed, kind, n=200):
    """Image_Setup (kind "setup"), Image_SetupAndLoad ("load") and the render target setups ("rt", "rtmips")."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        enabled = r.random() < 0.85
        init_va, entries = _init_data(r)
        sample_count = r.choice([1, 4, r.getrandbits(32)])

        def extra(w, model, enabled=enabled, init_va=init_va, entries=entries, sample_count=sample_count):
            w.u64(va("r_loadForRenderer"), dvar(w, enabled))
            w.u32(va("unk_14A3852BC"), sample_count)
            if entries:
                w.m.mu.mem_write(init_va, entries)
        image = image_bytes(r, name=r.choice([0, 0x140890F80]))
        name = r.choice([0, 0x140890F80, 0x14088E740])
        w_, h_ = r.choice([_dim(r), r.getrandbits(32)]), r.choice([_dim(r), r.getrandbits(32)])
        if kind == "setup":
            args = [image, w_, h_, _dim(r), r.choice([1, 2, 6, r.getrandbits(32)]), _maptype_flags(r), rand_format(r),
                    name, init_va]
        elif kind == "load":
            args = [image, w_, h_, _dim(r), _maptype_flags(r), rand_format(r), name]
        elif kind == "rt":
            args = [image, _dim(r), _dim(r), _maptype_flags(r), rand_format(r), name]
        else:
            args = [image, _dim(r), _dim(r), rand_format(r), name]
        out.append({"args": args, "setup": model_setup(r, extra)})
    return out


def default_depth_inputs(seed, n=40):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        enabled = r.random() < 0.85
        image = image_bytes(r, name=r.choice([0, 0x14088E740]))

        def extra(w, model, enabled=enabled, image=image):
            w.u64(va("r_loadForRenderer"), dvar(w, enabled))
            w.write(va("g_imageProgs") + 0x51 * 0x68, image)
        out.append({"args": [], "setup": model_setup(r, extra),
                    "fakes": {FMT_LT2: fake_format(r.choice([20, 40, r.randint(0, 120)]))}})
    return out


# ---- loading and streaming --------------------------------------------------------------------------------------

def _loaded_image(r, texture=None, map_types=(2, 3, 3, 4, 5, 6, None)):
    map_type = r.choice(map_types)
    if map_type is None:
        map_type = r.randint(0, 9)
    levels = r.choice([0, 1, 2, 3, 5, 9])
    return map_type, levels, image_bytes(
        r, texture=texture, mapType=map_type, levelCount=levels, numElements=r.choice([0, 1, 2, 3, 6]),
        width=r.choice([1, 3, 4, 16, 64, 100, 256]), height=r.choice([1, 3, 4, 16, 64, 100, 256]),
        depth=r.choice([1, 1, 2, 4, 8]), format=rand_format(r), category=r.choice([0, 3, 5, 5, 6]),
        levels=[(r.choice([1, 2, 4, 16, 64, 100, 256]), r.choice([1, 2, 4, 16, 64, 100, 256]),
                 r.choice([0, 1, 2, 3, 5, 9]) << 26 | r.getrandbits(26)) for _ in range(4)])


def load_texture_inputs(seed, n=200):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        enabled = r.random() < 0.9
        picmip = r.choice([0, 1, 2, 3, 7, r.getrandbits(16)])
        # any other map type is created as a cube from one face's data: the other five faces' entries were never
        # filled in (only water images, which take no data, are tested with them)
        category = r.choice([0, 3, 5, 5, 6])
        _, _, image = _loaded_image(r, map_types=(3, 3, 4, 5, 6) if category != 5 else (2, 3, 4, 5, 6, None))
        image = image[:0x1E] + bytes([category]) + image[0x1F:]

        def extra(w, model, enabled=enabled, picmip=picmip):
            w.u64(va("r_loadForRenderer"), dvar(w, enabled))
            w.u64(va("r_picmip_water"), dvar(w, picmip, "<i"))
        out.append({"args": [struct.pack("<Q", DATA), image], "setup": model_setup(r, extra)})
    return out


CTX_SIGS = {(CTX, 46 * 8): "piiiipiq", (CTX, 48 * 8): "piqqii"}


def _mip_chain(width, height, depth):
    count, res = 1, 1
    while res < width or res < height or res < depth:
        res += res
        count += 1
    return count


def upload_inputs(seed, n=200):
    """sub_14062B580(texture, image, picmip, data). At picmip 0 the upload count is the full mip chain of the level's
    size while the layout covers the level's mip count: level 0 gets at least the full chain (else the original reads
    entries it never filled in)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        _, _, image = _loaded_image(r)
        depth = struct.unpack_from("<H", image, 0x30)[0]
        for level in range(4):
            w0, h0, bits = struct.unpack_from("<2HI", image, 0x40 + 8 * level)
            if bits >> 26 == 0:  # nothing laid out, one level uploaded
                bits |= 1 << 26
            chain = _mip_chain(w0, h0, depth)
            if level == 0 and 1 < bits >> 26 < chain:
                bits = (bits & 0x3FFFFFF) | r.choice([chain, chain + 1]) << 26
            image = image[:0x44 + 8 * level] + struct.pack("<I", bits) + image[0x48 + 8 * level:]
        texture = struct.pack("<3Q", obj_va(2), r.getrandbits(48), r.getrandbits(48))
        out.append({"args": [texture, image, r.choice([0, 0, 1, 2, 3]), DATA + r.getrandbits(8)],
                    "setup": model_setup(r, lambda w, model: model.new(RES), context=True, sigs=CTX_SIGS)})
    return out


def copy_inputs(seed, n=100):
    """sub_14062AB70(dest, destSubresource, source, sourceSubresource, count)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        dest = struct.pack("<3Q", obj_va(2), 0, 0)
        source = image_bytes(r, texture=[obj_va(3), 0, 0])
        out.append({"args": [dest, r.choice([0, 1, 2, r.getrandbits(32)]), source, r.choice([0, 1, 5, r.getrandbits(32)]),
                             r.choice([0, 1, 2, 5, 13, -1, -100])],
                    "setup": model_setup(r, lambda w, model: (model.new(RES), model.new(RES)), context=True,
                                         sigs=CTX_SIGS)})
    return out


IMAGE_T = "PEAUGfxImage@@"
CASES = [
    case("?Image_AllocProg@@YAPEAUGfxImage@@HEE@Z", alloc_prog_inputs(0xAB40), ret="int64"),
    case("?sub_14062AB70@@YAXPEAUGfxTexture@@IPEAUGfxImage@@IH@Z", copy_inputs(0xAB70)),
    case("?sub_14062AC10@@YAXPEAUGfxImage@@GHHW4DXGI_FORMAT@@PEBUD3D11_SUBRESOURCE_DATA@@@Z",
         create_inputs(0xAC10, CREATE_1D)),
    case("?Image_Create2DTexture_PC@@YAXPEAUGfxImage@@GGHHW4DXGI_FORMAT@@PEBUD3D11_SUBRESOURCE_DATA@@@Z",
         create_inputs(0xACD0, CREATE_2D, 300)),
    case("?Image_Create3DTexture_PC@@YAXPEAUGfxImage@@GGGHHW4DXGI_FORMAT@@PEBUD3D11_SUBRESOURCE_DATA@@@Z",
         create_inputs(0xAE30, CREATE_3D)),
    case("?sub_14062AF40@@YAXPEAUGfxImage@@GGGHHW4DXGI_FORMAT@@PEBUD3D11_SUBRESOURCE_DATA@@@Z",
         create_inputs(0xAF40, CREATE_ARRAY)),
    case("?Image_CreateCubeTexture_PC@@YAXPEAUGfxImage@@GHHW4DXGI_FORMAT@@PEBUD3D11_SUBRESOURCE_DATA@@@Z",
         create_inputs(0xB020, CREATE_CUBE)),
    case("?sub_14062B110@@YAXPEAUGfxImage@@IPEAUGfxTexture@@@Z", stream_create_inputs(0xB110)),
    case("?Image_GetColorRenderTarget@@YAPEAUID3D11RenderTargetView@@IPEAUGfxImage@@HW4DXGI_FORMAT@@@Z",
         color_rt_inputs(0xB310), ret="int64"),
    case("?Image_GetDepthStencilRenderTarget@@YAPEAUID3D11DepthStencilView@@IPEAUGfxImage@@@Z",
         depth_rt_inputs(0xB360), ret="int64"),
    case("?sub_14062B580@@YAXPEAUGfxTexture@@PEAUGfxImage@@IPEBE@Z", upload_inputs(0xB580)),
    case("?Image_SetTextureDescMSAASettings@@YAXPEAUD3D11_TEXTURE2D_DESC@@I@Z", msaa_inputs(0xB960)),
    case("?Image_SetupRenderTarget@@YAXPEAUGfxImage@@GGHW4DXGI_FORMAT@@PEBD@Z", setup_inputs(0xB980, "rt", 100)),
    case("?Image_SetupRenderTargetDepth@@YAXPEAUGfxImage@@GGHW4DXGI_FORMAT@@PEBD@Z", setup_inputs(0xB9C0, "rt", 100)),
    case("?Image_SetupRenderTargetTypeless@@YAXPEAUGfxImage@@GGHW4DXGI_FORMAT@@PEBD@Z",
         setup_inputs(0xBA00, "rt", 100)),
    case("?Image_SetupRenderTargetWithMips@@YAXPEAUGfxImage@@GGW4DXGI_FORMAT@@PEBD@Z",
         setup_inputs(0xBA40, "rtmips", 100)),
    case("?Load_Texture@@YAXPEAPEAUGfxImageLoadDef@@PEAUGfxImage@@@Z", load_texture_inputs(0xBA80)),
    case("?R_InitDefaultDepthImage@@YAXXZ", default_depth_inputs(0xC040)),
    case("?R_MakeSRGBFormat@@YA?AW4DXGI_FORMAT@@W41@@Z", format_inputs(0xC3D0), ret="int"),
    case("?sub_14062C460@@YA?AW4DXGI_FORMAT@@W41@@Z", format_inputs(0xC460), ret="int"),
    case("?sub_14062DA40@@YAXPEAUGfxImage@@I@Z", stream_level_inputs(0xDA40)),
    case("?Image_CountMipmaps@@YAIIIII@Z", count_mipmaps_inputs(0xE0C0), ret="int"),
    case("?Image_CubemapFace@@YAII@Z", [[x] for x in (0, 1, 5, 6, 0xFFFFFFFF, 0x80000000, 12345)], ret="int"),
    case("?Image_GetCardMemoryAmountForMipLevel@@YAIW4DXGI_FORMAT@@III@Z", card_memory_inputs(0xE300), ret="int"),
    case("?Image_Setup@@YAXPEAUGfxImage@@HHHHHW4DXGI_FORMAT@@PEBDPEBUD3D11_SUBRESOURCE_DATA@@@Z",
         setup_inputs(0xE4F0, "setup", 300)),
    case("?Image_SetupAndLoad@@YAXPEAUGfxImage@@HHHHW4DXGI_FORMAT@@PEBD@Z", setup_inputs(0xE690, "load", 300)),
    case("?sub_14062E820@@YAXHPEAW4D3D11_USAGE@@PEAI1@Z", usage_inputs(0xE820)),
    case("?sub_14062E8A0@@YA?AW4DXGI_FORMAT@@W41@@Z", format_inputs(0xE8A0), ret="int"),
]


# ---- render targets (r_rendertarget.cpp) ------------------------------------------------------------------------

RT_SIZE = 0x50
GET_RESOURCE, RTV_GET_DESC, GET_BUFFER = 7 * 8, 8 * 8, 9 * 8
VIEW_SIGS = {(VIEW, ADD_REF): "", (VIEW, RELEASE): "", (VIEW, GET_RESOURCE): "p", (VIEW, RTV_GET_DESC): "p",
             (RES, RELEASE): "", (RES, ADD_REF): "", (SWAP, GET_BUFFER): "ipp"}
VIEW_DUMPS = {(SWAP, GET_BUFFER): {1: 16}}


def view_results(descs=()):
    """GetResource hands out a new resource; GetDesc writes render target view descriptions from a list (cycling)."""
    def results(script):
        queue = list(descs)

        def get_desc(call):
            d = queue.pop(0) if queue else struct.pack("<5I", 28, 4, 0, 0, 0)
            queue.append(d)
            call.write(call.arg(0), d)
            return None

        def get_resource(call):
            call.out_object(0, RES)
            return None
        return {(VIEW, GET_RESOURCE): get_resource, (VIEW, RTV_GET_DESC): get_desc,
                (SWAP, GET_BUFFER): creator(script, RES, 2)}
    return results


def rt_fake(name, n, letters):
    """A fake logging its n arguments (letters: i 32-bit, h 16-bit, q 64-bit, s string)."""
    def fn(mu):
        args = _stack_args(mu, n)
        out = [name]
        for a, k in zip(args, letters):
            if k == "s":
                out.append(REC.machine.read_cstr(a) if a else None)
            else:
                out.append(a & {"i": 0xFFFFFFFF, "h": 0xFFFF, "q": (1 << 64) - 1}[k])
        REC.machine.observed.append(tuple(out))
        return 0
    return fn


INIT_RT = "?R_InitRenderTargetImage@@YAXHGG_KW4DXGI_FORMAT@@W4RenderTargetUsage@@PEAUGfxRenderTarget@@@Z"
INIT_FULLSCREEN = ("?R_InitFullscreenRenderTargetImage@@YAXHW4FullscreenType@@H_KW4DXGI_FORMAT@@W4RenderTargetUsage@@"
                   "PEAUGfxRenderTarget@@@Z")
INIT_SURFACE = "?R_InitImageAndSurface@@YAXPEAUGfxImageAndSurface@@HGGHW4DXGI_FORMAT@@W4RenderTargetUsage@@PEBD@Z"
SHARE = "?R_ShareRenderTarget@@YAXW4GfxRenderTargetId@@0@Z"
CREATE_DS = "?R_CreateDepthStencilSurface@@YAPEAUID3D11DepthStencilView@@IPEAPEAUID3D11ShaderResourceView@@@Z"
RT_FAKES = {
    INIT_RT: rt_fake("R_InitRenderTargetImage", 7, "ihhqiiq"),
    INIT_FULLSCREEN: rt_fake("R_InitFullscreenRenderTargetImage", 7, "iiiqiiq"),
    INIT_SURFACE: rt_fake("R_InitImageAndSurface", 8, "qihhiiis"),
    SHARE: rt_fake("R_ShareRenderTarget", 2, "ii"),
}


def fake_create_depth_stencil(mu):
    flags, out = _stack_args(mu, 2)
    REC.machine.observed.append(("R_CreateDepthStencilSurface", flags & 0xFFFFFFFF, out))
    return REC.model.new(VIEW)


def set_vidconfig(w, sizes, unknown11=0):
    w.write(va("vidConfig"), struct.pack("<4I2B", *sizes, 0, unknown11))


def rand_sizes(r):
    return [r.choice([0, 1, 2, 640, 1280, 1920, 1080, 720, r.getrandbits(16), r.getrandbits(32)]) for _ in range(4)]


def render_target_bytes(r, objects=(), garbage=True):
    """A GfxRenderTarget: images and views random or the given model objects."""
    ptrs = [r.choice(list(objects) + [0] + ([r.getrandbits(40)] if garbage else [])) for _ in range(8)]
    return struct.pack("<8Q3I4x", *ptrs, r.getrandbits(32), r.getrandbits(32), rand_format(r))


def va_of_rt(index):
    """The address of gfxRenderTargets[index] in the Store build (inputs are built before syms.BUILD is set)."""
    return 0x14B07F600 + RT_SIZE * index


def create_depth_stencil_inputs(seed, n=100):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        sizes, count = rand_sizes(r), r.choice([0, 1, 4, 8, r.getrandbits(32)])

        def extra(w, model, sizes=sizes, count=count):
            set_vidconfig(w, sizes)
            w.u32(va("unk_14A3852BC"), count)
        out.append({"args": [rand_flags(r), bytes(r.getrandbits(8) for _ in range(8))],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS, results=view_results(), keep=False)})
    return out


def depth_view_image_inputs(seed, n=100):
    """R_InitDepthOrStencilViewImage(imageProgType, renderTarget, format, msaaState): the target's depth-stencil
    views are objects 1 and 2."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        rt = struct.pack("<8Q3I4x", r.getrandbits(40), r.getrandbits(40), obj_va(1), r.getrandbits(40),
                         r.getrandbits(40), r.getrandbits(40), obj_va(2), r.getrandbits(40),
                         r.getrandbits(32), r.getrandbits(32), rand_format(r))
        image = image_bytes(r)
        type_ = r.choice([0x15, 0x19D, r.randint(0, 0x1C0)])

        def extra(w, model, image=image, type_=type_):
            model.new(VIEW)
            model.new(VIEW)
            w.write(va("g_imageProgs") + 0x68 * type_, image)
        out.append({"args": [type_, rt, rand_format(r), r.choice([0, 1])],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS, results=view_results())})
    return out


def framebuffer_inputs(seed, n=120):
    """R_InitFrameBufferRenderTarget(): swap chain object 1, the scene's depth-stencil view object 2 and the frame
    buffer's colour view object 3 (which the faked R_InitRenderTargetImage would make in the letterbox case)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        sizes, unknown11 = rand_sizes(r), r.choice([0, 1])
        count, minimal = r.choice([0, 0, 4]), r.choice([0, 1])
        fmt = r.choice([27, 28, 29, 87, 24, 10, 15, 39, 53, 70, 73, 76, r.randint(0, 120)])
        desc = struct.pack("<5I", fmt, 4, r.getrandbits(8), 0, 0)
        desc2 = struct.pack("<5I", r.choice([28, 87, r.randint(0, 120)]), 4, 0, 0, 0)
        rts = [render_target_bytes(r, (obj_va(2), obj_va(3))) for _ in range(8)]

        def extra(w, model, sizes=sizes, unknown11=unknown11, count=count, minimal=minimal, rts=rts):
            model.new(SWAP)
            model.new(VIEW)
            model.new(VIEW)
            set_vidconfig(w, sizes, unknown11)
            w.u32(va("unk_14A3852BC"), count)
            w.write(va("g_allocateMinimalResources"), bytes([minimal]))
            w.u64(va("unk_14A385300"), obj_va(1))
            base = va("gfxRenderTargets")
            for i, rt in enumerate(rts):
                w.write(base + RT_SIZE * i, rt)
            w.u64(base + RT_SIZE * 3 + 0x10, obj_va(2))
            w.u64(base + RT_SIZE * 1 + 0x08, obj_va(3))
        out.append({"args": [], "setup": model_setup(r, extra, sigs=VIEW_SIGS, dumps=VIEW_DUMPS,
                                                     results=view_results([desc, desc2]), keep=False),
                    "fakes": RT_FAKES})
    return out


def fullscreen_inputs(seed, n=200):
    """R_InitFullscreenRenderTargetImage(imageProgType, screenType, picmip, imageFlagsArg, format, usage, renderTarget)
    with R_InitRenderTargetImage and R_CreateDepthStencilSurface faked."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        sizes = rand_sizes(r)
        surfaces = [r.choice([0, 1]), r.choice([0, 1])]

        def extra(w, model, sizes=sizes, surfaces=surfaces):
            set_vidconfig(w, sizes)
            for have, name in zip(surfaces, ("unk_14A3852C8", "unk_14A3852D8")):
                w.u64(va(name), model.new(VIEW) if have else 0)
        flags = rand_flags(r) | r.choice([0, 0, 1 << 32, r.getrandbits(32) << 32])
        out.append({"args": [r.randint(0, 0x1C0), r.choice([0, 1, 2, 3, -1]), r.choice([0, 1, 2, 5, 31, 33, -1]),
                             flags, rand_format(r), r.choice([0, 1, 2, 3, 4, 5, 6, 7]), render_target_bytes(r)],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS),
                    "fakes": {INIT_RT: RT_FAKES[INIT_RT], CREATE_DS: fake_create_depth_stencil}})
    return out


def image_and_surface_inputs(seed, n=200):
    """R_InitImageAndSurface(out, imageProgType, width, height, imageFlags, format, usage, imageName): the image
    setup and views run for real (reconstructed), with the image memory functions and format getters faked."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        enabled = r.random() < 0.9
        type_ = r.choice([8, 9, 0x51, r.randint(0, 0x1C0)])
        image = image_bytes(r, name=r.choice([0, 0x14088E740]))

        def extra(w, model, enabled=enabled, type_=type_, image=image):
            w.u64(va("r_loadForRenderer"), dvar(w, enabled))
            w.u32(va("unk_14A3852BC"), 4)
            w.write(va("g_imageProgs") + 0x68 * type_, image)
        out.append({"args": [bytes(r.getrandbits(8) for _ in range(0x20)), type_, _dim(r), _dim(r),
                             _maptype_flags(r) & ~0x38000 | r.choice([0, 0, 0x8000]), rand_format(r),
                             r.choice([0, 1, 2, 3, 4, 5, 6, 7]), r.choice([0, 0x140890F80, 0x1408A59A8])],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS, keep=False),
                    "fakes": {FMT_LT2: fake_format(20), FMT_GE2: fake_format(40)}})
    return out


def pip_inputs(seed, n=120):
    """R_InitPIPRenderTargets(width, height) with R_InitRenderTargetImage and R_ShareRenderTarget faked; the depth
    view images (R_InitDepthOrStencilViewImage) run for real."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        count = r.choice([0, 0, 2, 4])
        # the multisampled depth-stencil of the PIP scene is shared even without multisampling: NULL or a view
        rts = {i: render_target_bytes(r, (obj_va(1),), garbage=i != 13) for i in (13, 14, 15, 16)}
        old_sets = bytes(r.getrandbits(8) for _ in range(0x30))

        def extra(w, model, count=count, rts=rts, old_sets=old_sets):
            model.new(VIEW)
            w.u32(va("unk_14A3852BC"), count)
            base = va("gfxRenderTargets")
            for i, rt in rts.items():
                w.write(base + RT_SIZE * i, rt)
            w.write(va("unk_14A385350"), old_sets)
        out.append({"args": [_dim(r), _dim(r)],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS, results=view_results(), keep=False),
                    "fakes": {INIT_RT: RT_FAKES[INIT_RT], SHARE: RT_FAKES[SHARE]}})
    return out


MSAA_TARGETS = [3, 4, 13, 15, 16, 17, 18, 19, 26, 64, 72, 73]


def init_rt_inputs(seed, n=200):
    """R_InitRenderTargetImage(imageProgType, width, height, imageFlagsArg, format, usage, renderTarget) with
    R_InitImageAndSurface faked; the target is a gfxRenderTargets entry (its index names it)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        index = r.choice(MSAA_TARGETS + [0, 1, 2, 5, 6, 14, r.randint(0, 90)])
        rt = render_target_bytes(r)

        def extra(w, model, index=index, rt=rt):
            w.write(va("gfxRenderTargets") + RT_SIZE * index, rt)
        flags = rand_flags(r) | r.choice([0, 0, 1 << 32, r.getrandbits(32) << 32])
        out.append({"args": [r.randint(0, 0x1C0), _dim(r), _dim(r), flags, rand_format(r), r.randint(0, 7),
                             va_of_rt(index)],
                    "setup": model_setup(r, extra), "fakes": {INIT_SURFACE: RT_FAKES[INIT_SURFACE]}})
    return out


def mipmap_inputs(seed, n=150):
    """R_InitRenderTargetImageMipmap(imageProgType, renderTarget, baseImage, format, mipLevel): the base image's
    shader view is object 1."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        type_ = r.randint(0, 0x1C0)
        image = image_bytes(r)

        def extra(w, model, type_=type_, image=image):
            model.new(VIEW)
            w.write(va("g_imageProgs") + 0x68 * type_, image)
        base = image_bytes(r, texture=[r.getrandbits(40), obj_va(1), 0])
        out.append({"args": [type_, render_target_bytes(r), base, rand_format(r), r.choice([0, 1, 2, 5, 31, 32, 33])],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS, results=view_results())})
    return out


def cached_shadow_inputs(seed, n=150):
    """R_InitRenderTargetImage_CachedShadows(imageProgType, width, height, imageFlags, format, renderTarget)."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        enabled = r.random() < 0.9
        type_ = r.randint(0, 0x1C0)
        image = image_bytes(r, name=r.choice([0, 0x14088E740]))

        def extra(w, model, enabled=enabled, type_=type_, image=image):
            w.u64(va("r_loadForRenderer"), dvar(w, enabled))
            w.write(va("g_imageProgs") + 0x68 * type_, image)
        out.append({"args": [type_, _dim(r), _dim(r), _maptype_flags(r) & ~0x38000, rand_format(r),
                             render_target_bytes(r)],
                    "setup": model_setup(r, extra, sigs=VIEW_SIGS, keep=False)})
    return out


def share_inputs(seed, n=150):
    """R_ShareRenderTarget(idFrom, idTo): the source's colour views are model objects or NULL."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        src, dst = r.randint(0, 90), r.randint(0, 90)
        if r.random() < 0.1:
            dst = src
        dst_bytes = render_target_bytes(r)
        picks = [r.choice([0, 1, 2]) for _ in range(8)]

        def extra(w, model, src=src, dst=dst, dst_bytes=dst_bytes, picks=picks):
            objs = [0, model.new(VIEW), model.new(VIEW)]
            base = va("gfxRenderTargets")
            w.write(base + RT_SIZE * dst, dst_bytes)
            w.write(base + RT_SIZE * src, struct.pack("<8Q3I4x", *(objs[p] for p in picks), 1, 2, 28))
        out.append({"args": [src, dst], "setup": model_setup(r, extra, sigs=VIEW_SIGS)})
    return out


CASES += [
    case(CREATE_DS, create_depth_stencil_inputs(0xE3A0), ret="int64"),
    case("?R_InitDepthOrStencilViewImage@@YAPEAUGfxImage@@HPEAUGfxRenderTarget@@W4DXGI_FORMAT@@W4GfxMSAAState@@@Z",
         depth_view_image_inputs(0xF360), ret="int64"),
    case("?R_InitFrameBufferRenderTarget@@YA?AW4DXGI_FORMAT@@XZ", framebuffer_inputs(0xF420), ret="int"),
    case(INIT_FULLSCREEN, fullscreen_inputs(0xF720)),
    case(INIT_SURFACE, image_and_surface_inputs(0x0140)),
    case("?R_InitPIPRenderTargets@@YAXGG@Z", pip_inputs(0x02B0)),
    case(INIT_RT, init_rt_inputs(0x05B0)),
    case("?R_InitRenderTargetImageMipmap@@YAXHPEAUGfxRenderTarget@@PEAUGfxImage@@W4DXGI_FORMAT@@H@Z",
         mipmap_inputs(0x0700)),
    case("?R_InitRenderTargetImage_CachedShadows@@YAXHGGHW4DXGI_FORMAT@@PEAUGfxRenderTarget@@@Z",
         cached_shadow_inputs(0x0810)),
    case(SHARE, share_inputs(0x1310)),
]


# ---- compute buffer views (r_compute.cpp) and adapter memory (r_init.cpp) ----------------------------------------

BUFFER_GET_DESC = 10 * 8


def buffer_view_inputs(seed, structured, n=150):
    """The buffer view functions: the buffer is object 1, its description random (byte width 0 and odd sizes
    included); a zero element size faults the original (division) and is skipped."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        desc = struct.pack("<6I", r.choice([0, 3, 4, 64, 0x1B58 * 4, r.getrandbits(32)]), r.getrandbits(2),
                           r.getrandbits(8), 0, r.getrandbits(8), r.getrandbits(8))

        def results(script, desc=desc):
            return {(RES, BUFFER_GET_DESC): lambda call: (call.write(call.arg(0), desc), None)[1]}
        name = r.choice([0, 0x14080D7C0])
        args = [obj_va(1)] + ([r.choice([0, 1, 4, 12, 16, 0x88, r.getrandbits(32)])] if structured else []) \
            + [name, bytes(r.getrandbits(8) for _ in range(8))]
        out.append({"args": args, "setup": model_setup(r, lambda w, model: model.new(RES),
                                                       sigs={(RES, BUFFER_GET_DESC): "p"}, results=results)})
    return out


DXGI_SIGS = {(DEV, QUERY_INTERFACE): "pp", (UNK, 7 * 8): "p", (ADAPTER, 8 * 8): "p", (UNK, RELEASE): "",
             (ADAPTER, RELEASE): ""}


def adapter_inputs(seed, n=150):
    """The adapter memory queries: QueryInterface gives an IDXGIDevice, GetAdapter an adapter whose description is
    random; r_amdGPU and the scale (NaN, negative, huge included) for the scaled one."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        sizes = [r.choice([0, 1 << 30, 4 << 30, r.getrandbits(40), r.getrandbits(63), r.getrandbits(64)])
                 for _ in range(3)]
        desc = bytes(r.getrandbits(8) for _ in range(0x110)) + struct.pack("<3Q", *sizes) + struct.pack("<Q", 7)
        amd = r.choice([0, 1])
        scale = r.choice([1.0, 0.5, 0.0, -1.0, 2.0, 1e30, float("nan"), float("inf"), r.uniform(0, 4)])

        def results(script, desc=desc):
            return {(DEV, QUERY_INTERFACE): lambda call: (call.out_object(1, UNK), 0)[1],
                    (UNK, 7 * 8): lambda call: (call.out_object(0, ADAPTER), 0)[1],
                    (ADAPTER, 8 * 8): lambda call: (call.write(call.arg(0), desc), 0)[1]}

        def extra(w, model, amd=amd, scale=scale):
            w.u64(va("r_amdGPU"), dvar(w, amd))
            w.u64(va("r_amdGPUVideoMemoryScale"), dvar(w, scale, "<f"))
        out.append({"args": [], "setup": model_setup(r, extra, sigs=DXGI_SIGS, dumps={(DEV, QUERY_INTERFACE): {0: 16}},
                                                     results=results)})
    return out


CASES += [
    case("?sub_1401AC380@@YAXPEAUID3D11Buffer@@PEBDPEAPEAUID3D11UnorderedAccessView@@@Z",
         buffer_view_inputs(0xC380, False)),
    case("?sub_1401AC3F0@@YAXPEAUID3D11Buffer@@PEBDPEAPEAUID3D11ShaderResourceView@@@Z",
         buffer_view_inputs(0xC3F0, False)),
    case("?sub_1401AC4D0@@YAXPEAUID3D11Buffer@@IPEBDPEAPEAUID3D11UnorderedAccessView@@@Z",
         buffer_view_inputs(0xC4D0, True)),
    case("?sub_1401AC540@@YAXPEAUID3D11Buffer@@IPEBDPEAPEAUID3D11ShaderResourceView@@@Z",
         buffer_view_inputs(0xC540, True)),
    case("?sub_140630CA0@@YA_KXZ", adapter_inputs(0x0CA0), ret="int64"),
    case("?sub_140630D20@@YA_KXZ", adapter_inputs(0x0D20), ret="int64"),
]
