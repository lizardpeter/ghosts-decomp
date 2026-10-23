"""Faithful vendor initialization order and command registration, with dependencies modeled."""
INIT='?LiveAntiCheat_Init@@YAXXZ'
RESET='?LiveAntiCheat_ResetAllChallenges@@YAXXZ'
CONTROLLER='?sub_1405F0450@@YAXH@Z'
COMMAND='?Cmd_AddCommandInternal@@YAXPEBDP6AXXZPEAUcmd_function_s@@@Z'

def nothing(mu):return None

CASES=[{'symbol':INIT,'build':'iw6mp64_MSStore_ship','ret':'void',
        'inputs':[[]], 'fakes':{RESET:nothing,CONTROLLER:nothing,COMMAND:nothing},
        'observe':{RESET:'',CONTROLLER:'i',COMMAND:'sqq'}}]
