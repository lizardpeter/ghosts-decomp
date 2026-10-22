"""Preserve original wrapper cases, then exercise common-address conversion end to end."""
from test_win_net import CASES as BASE_CASES
from test_dwcommon import COMMON_FAKES, SERIALIZED, SECURITY_ID, common_setup

WRAPPER = '?sub_14054FC70@@YA_NPEBEPEAIPEAG@Z'
base = next(c for c in BASE_CASES if c['symbol'] == WRAPPER)
inputs = [{**inp, 'fakes': base['fakes']} for inp in base['inputs']]
for pattern in ('equal0', 'empty2', 'full_oldest2', 'zero_bound'):
    for registered in (False, True):
        for handle in (False, True):
            for loopback in (False, True):
                for net in (False, True):
                    inputs.append({
                        'args': [SECURITY_ID+SERIALIZED, bytes([0xA5])*4, bytes([0x5A])*2],
                        'setup': common_setup(pattern, registered=registered, handle=handle,
                                             loopback=loopback, net=net, seed=len(inputs)+10),
                        'fakes': COMMON_FAKES,
                    })
CASES = [{**base, 'fakes': {}, 'inputs': inputs}]
