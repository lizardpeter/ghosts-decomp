"""Differential cases for Com_InitDvars (qcommon/common.cpp, Store build).

Every Dvar_Register* is faked: it logs its name, default, limits, flags and description (strings by content, floats
by bits, the enum value list by address) and returns a distinct scratch dvar_t per call, so every dvar pointer stored
is compared. Sys_GetCpuCount returns 0, 1, 2 or 16 (sys_smp_allowed's default), and the two registration functions
of other modules and the empty one are faked and logged, so their order among the registrations shows.
"""
import random

from win32_display import CURRENT, log_value

STORE = "iw6mp64_MSStore_ship"
DVARS = 0x5C0000  # scratch dvar_t's handed out by the fakes


class Registry:
    def __init__(self, cpus):
        self.cpus = cpus
        self.n = 0

    def setup(self, w):
        CURRENT["m"] = w.m
        self.n = 0

    def register(self, kind, sig):
        def run(mu):
            m = CURRENT["m"]
            m.observed.append(("call", kind, *(log_value(mu, c, i) for i, c in enumerate(sig))))
            self.n += 1
            return DVARS + 0x60 * self.n
        return run

    def call(self, name, result=None):
        def run(mu):
            CURRENT["m"].observed.append(("call", name))
            return result
        return run

    def fakes(self):
        return {
            "?Dvar_RegisterBool@@YAPEBUdvar_t@@PEBD_NI0@Z": self.register("Bool", "sbis"),
            "?Dvar_RegisterInt@@YAPEBUdvar_t@@PEBDHHHI0@Z": self.register("Int", "siiiis"),
            "?Dvar_RegisterString@@YAPEBUdvar_t@@PEBD0I0@Z": self.register("String", "ssis"),
            "?Dvar_RegisterEnum@@YAPEBUdvar_t@@PEBDQEBQEBDHI0@Z": self.register("Enum", "sqiis"),
            "?Dvar_RegisterFloat@@YAPEBUdvar_t@@PEBDMMMI0@Z": self.register("Float", "sfffis"),
            "?Sys_GetCpuCount@@YAIXZ": self.call("Sys_GetCpuCount", self.cpus),
            "?sub_1403358C0@@YAXXZ": self.call("sub_1403358C0"),
            "?sub_140223D30@@YAXXZ": self.call("sub_140223D30"),
            "?sub_140464DE0@@YAXXZ": self.call("sub_140464DE0"),
        }


def _input(r):
    reg = Registry(r.choice([0, 1, 2, 16]))
    return {"args": [], "setup": reg.setup, "fakes": reg.fakes()}


r = random.Random(5328)
CASES = [{"symbol": "?Com_InitDvars@@YAXXZ", "build": STORE, "ret": "void", "inputs": [_input(r) for _ in range(20)]}]
