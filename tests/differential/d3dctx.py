"""A Direct3D 11 device context for differential tests of the renderer's per-frame code (com.py's COM model).

Every ID3D11DeviceContext method the back end calls has a signature here, and its arguments are logged by content:
the arrays the Set* methods take (constant buffers, shader resources, samplers, vertex buffers with strides and
offsets, render targets), viewports and scissor rectangles, blend factors and clear colours. Objects are logged as
("obj", id), so a test sees which state object, view or buffer was bound; anything else by value.

Map hands out a zeroed block of model memory for pData; Unmap logs what was written into it (MAP_LOG bytes), so the
constant uploads are compared byte for byte. OMGetRenderTargets returns the views a test chose (model.bound_rtv,
model.bound_dsv: an object or 0); the caller owns the references it gets, so the test sees the Release calls.

Use: model = install(w) in a setup; model.ctx is the context object.
"""
import struct

from com import ComModel

CTX, RES, VIEW, STATE, SHADER, LAYOUT, UNK = ("ID3D11DeviceContext", "ID3D11Resource", "ID3D11View",
                                              "ID3D11State", "ID3D11Shader", "ID3D11InputLayout", "IUnknown")
MAP_LOG = 0x600   # bytes of a mapped block logged at Unmap
MAP_SIZE = 0x2000

M = {}


def _rec(*entry):
    M["m"].observed.append(entry)


def _val(model, x):
    if x in model.objects:
        return ("obj", model.objects[x][1])
    return x


def _q(mu, a, n):
    return struct.unpack(f"<{n}Q", bytes(mu.mem_read(a, 8 * n))) if a and n else ()


def _u(mu, a, n):
    return struct.unpack(f"<{n}I", bytes(mu.mem_read(a, 4 * n))) if a and n else ()


def _objs(call, a, n):
    return tuple(_val(call.model, x) for x in _q(call.mu, a, min(n, 128)))


def _set_array(name):
    """XSSet{ConstantBuffers,ShaderResources,Samplers}(start, count, array)"""
    def fn(call):
        _rec("ctx", name, call.arg(0), call.arg(1), _objs(call, call.arg(2), call.arg(1)))
    return fn


def _vertex_buffers(call):
    n = min(call.arg(1), 16)
    _rec("ctx", "IASetVertexBuffers", call.arg(0), call.arg(1), _objs(call, call.arg(2), n),
         _u(call.mu, call.arg(3), n), _u(call.mu, call.arg(4), n))


def _render_targets(call):
    _rec("ctx", "OMSetRenderTargets", call.arg(0), _objs(call, call.arg(1), call.arg(0)), _val(call.model, call.arg(2)))


def _blend(call):
    _rec("ctx", "OMSetBlendState", _val(call.model, call.arg(0)), _u(call.mu, call.arg(1), 4), call.arg(2))


def _viewports(call):
    _rec("ctx", "RSSetViewports", call.arg(0), _u(call.mu, call.arg(1), 6 * min(call.arg(0), 16)))


def _scissors(call):
    _rec("ctx", "RSSetScissorRects", call.arg(0), _u(call.mu, call.arg(1), 4 * min(call.arg(0), 16)))


def _clear_rtv(call):
    _rec("ctx", "ClearRenderTargetView", _val(call.model, call.arg(0)), _u(call.mu, call.arg(1), 4))


def _map(call):
    model = call.model
    block = model.alloc(bytes(MAP_SIZE), call.mu)
    model.mapped[call.arg(0)] = block
    if call.arg(4):
        call.mu.mem_write(call.arg(4), struct.pack("<QII", block, MAP_SIZE, MAP_SIZE))
    return model.map_result


def _unmap(call):
    block = call.model.mapped.pop(call.arg(0), None)
    _rec("ctx", "Unmap.data", bytes(call.mu.mem_read(block, MAP_LOG)) if block else None)


def _get_render_targets(call):
    model = call.model
    n = call.arg(0)
    if call.arg(1) and n:
        call.mu.mem_write(call.arg(1), struct.pack("<Q", model.bound_rtv))
    if call.arg(2):
        call.mu.mem_write(call.arg(2), struct.pack("<Q", model.bound_dsv))


# slot: (signature after `this`, name). Letters as in com.py.
CONTEXT_METHODS = {
    7: ("iip", "VSSetConstantBuffers"), 8: ("iip", "PSSetShaderResources"), 9: ("ppi", "PSSetShader"),
    10: ("iip", "PSSetSamplers"), 11: ("ppi", "VSSetShader"), 12: ("iii", "DrawIndexed"), 13: ("ii", "Draw"),
    14: ("piiip", "Map"), 15: ("pi", "Unmap"), 16: ("iip", "PSSetConstantBuffers"), 17: ("p", "IASetInputLayout"),
    18: ("iippp", "IASetVertexBuffers"), 19: ("pii", "IASetIndexBuffer"), 20: ("iiiii", "DrawIndexedInstanced"),
    21: ("iiii", "DrawInstanced"), 24: ("i", "IASetPrimitiveTopology"), 25: ("iip", "VSSetShaderResources"),
    26: ("iip", "VSSetSamplers"), 33: ("ipp", "OMSetRenderTargets"), 35: ("ppi", "OMSetBlendState"),
    36: ("pi", "OMSetDepthStencilState"), 41: ("iii", "Dispatch"), 43: ("p", "RSSetState"),
    44: ("ip", "RSSetViewports"), 45: ("ip", "RSSetScissorRects"), 50: ("pp", "ClearRenderTargetView"),
    53: ("pifb", "ClearDepthStencilView"), 59: ("iip", "HSSetShaderResources"), 60: ("ppi", "HSSetShader"),
    62: ("iip", "HSSetConstantBuffers"), 63: ("iip", "DSSetShaderResources"), 64: ("ppi", "DSSetShader"),
    65: ("iip", "DSSetSamplers"), 66: ("iip", "DSSetConstantBuffers"), 67: ("iip", "CSSetShaderResources"),
    68: ("iipp", "CSSetUnorderedAccessViews"), 69: ("ppi", "CSSetShader"), 71: ("iip", "CSSetConstantBuffers"),
    89: ("ipp", "OMGetRenderTargets"),
}

DETAIL = {
    18: _vertex_buffers, 33: _render_targets, 35: _blend, 44: _viewports, 45: _scissors, 50: _clear_rtv,
    14: _map, 15: _unmap, 89: _get_render_targets,
}
for _slot, (_sig, _name) in CONTEXT_METHODS.items():
    if _sig == "iip" and _slot not in DETAIL:
        DETAIL[_slot] = _set_array(_name)

SIGS = {(CTX, slot * 8): sig for slot, (sig, _) in CONTEXT_METHODS.items()}
SIGS.update({(VIEW, 2 * 8): "", (RES, 2 * 8): "", (STATE, 2 * 8): ""})  # Release


def install(w, extra_sigs=None, extra_results=None):
    """A model with a context object (model.ctx) as the current machine's COM model."""
    M["m"] = w.m
    results = {(CTX, slot * 8): fn for slot, fn in DETAIL.items()}
    results.update(extra_results or {})
    model = ComModel({**SIGS, **(extra_sigs or {})}, results)
    model.mapped, model.map_result = {}, 0
    model.bound_rtv = model.bound_dsv = 0
    model.install(w.m)
    model.ctx = model.new(CTX)
    return model
