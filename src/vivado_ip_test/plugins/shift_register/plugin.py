from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.shift_register.reference import ShiftRegisterModel


class ShiftRegisterPlugin(CycleIpPlugin):
    ip_type = "shift_register"
    ip_name = "c_shift_ram"
    version = "12.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 257), "depth": range(1, 1025), "clock_enable": bool})
        return CycleSpec(
            inputs=(Port("D", p["width"]), *((Port("CE", scalar=True),) if p["clock_enable"] else ())),
            outputs=(Port("Q", p["width"]),),
            settings={"Width": p["width"], "Depth": p["depth"], "ShiftRegType": "Fixed_Length",
                      "CE": p["clock_enable"], "RegLastBit": True, "SCLR": False,
                      "SINIT": False, "SSET": False, "DefaultData": "0" * p["width"],
                      "DefaultDataRadix": 2, "ReadMifFile": False,
                      "AsyncInitVal": "0" * p["width"], "AsyncInitRadix": 2},
            model_parameters={"C_DEPTH": p["depth"], "C_SHIFT_TYPE": 0, "C_HAS_A": 0,
                              "C_DEFAULT_DATA": "0" * p["width"], "C_REG_LAST_BIT": 1},
            model_factory=lambda: ShiftRegisterModel(p), flush_cycles=p["depth"],
            prefix=({"D": (1 << p["width"]) - 1},) + ({"D": 0},) * p["depth"],
            neutral={"CE": 1} if p["clock_enable"] else {},
        )
