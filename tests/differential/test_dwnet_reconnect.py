"""Run packet submission through the reconstructed handle-refresh chain.

The ordinary sender cases retain their original fake boundary. Additional cases
execute the original/reconstructed refresh implementation before sender admission.
"""
from test_dwnet import CASES as BASE_CASES, SEND, STORE, FAKES
from test_dwaddress import REFRESH_FAKES, _refresh_setup
import struct

base = next(c for c in BASE_CASES if c['symbol'] == SEND)
inputs = [{**inp, 'fakes': FAKES} for inp in base['inputs']]
for index in (0, 3):
    for second in (1, 2):
        for found in (False, True):
            for candidate in ('new', 'old', 'null'):
                for count in (0, 1, 2):
                    inputs.append({
                        'args': [4, b'iw6!', struct.pack('<4I', 4, 0, 0, index)],
                        'setup': _refresh_setup(index=index, second=second, found=found,
                                                 candidate=candidate, count=count),
                        'fakes': REFRESH_FAKES,
                    })
CASES = [{**base, 'fakes': {}, 'inputs': inputs}]
