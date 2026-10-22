"""Original Store address-table aging and clearing, without SDK or network calls."""
import random
import struct

from test_dwnet import FAKES, STORE, _setup
from syms import static

AGE = '?sub_1405A8790@@YAXXZ'
CLEAR = '?sub_1405A87E0@@YAXPEBUnetadr_s@@@Z'


def _table_setup(local, mask, lifetimes):
    def setup(w):
        _setup(local, lifetimes=lifetimes)(w)
        table = static('dw/dwnet.cpp', 'addressHandles')
        for i in range(8):
            if not (mask & (1 << i)):
                w.u64(table + 16*i, 0)
    return setup


rng = random.Random(0xA8790)
age_inputs = []
for local in range(9):
    for mask in (0, 1, 0x55, 0xAA, 0x80, 0xFF):
        for values in ([0]*8, [1]*8, [0, 1, 2, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 1, 0],
                       [rng.getrandbits(32) for _ in range(8)]):
            age_inputs.append({'args': [], 'setup': _table_setup(local, mask, values)})


clear_inputs = []
for local in (0, 1, 3, 7):
    for index in range(8):
        for mask in (0, 0x55, 0xFF):
            clear_inputs.append({'args': [struct.pack('<4I', 4, 0, 0, index)],
                                 'setup': _table_setup(local, mask, [rng.getrandbits(32) for _ in range(8)])})

CASES = [
    {'symbol': AGE, 'build': STORE, 'ret': 'void', 'fakes': FAKES, 'inputs': age_inputs},
    {'symbol': CLEAR, 'build': STORE, 'ret': 'void', 'fakes': FAKES, 'inputs': clear_inputs},
]
