from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import (
    CycleSpec, Port, control_ports, control_settings, validate_parameters,
)
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.accumulator.reference import AccumulatorModel


class AccumulatorPlugin(CycleIpPlugin):
    ip_type = "accumulator"
    ip_name = "c_accum"
    version = "12.0"

    def describe(self, p):
        validate_parameters(p, {
            "input_width": range(1, 257), "output_width": range(1, 257),
            "input_type": {"Signed", "Unsigned"}, "operation": {"Add", "Subtract", "Add_Subtract"},
            "clock_enable": bool, "sync_clear": bool, "ce_overrides_reset": bool, "bypass": bool,
        })
        if p["output_width"] < p["input_width"]:
            raise PluginError("累加输出位宽不得小于输入位宽")
        controls = control_ports(p, dynamic="ADD" if p["operation"] == "Add_Subtract" else None)
        if p["bypass"]:
            controls += (Port("BYPASS", scalar=True),)
        neutral = {port.name: int(port.name in {"CE", "ADD"}) for port in controls}
        maximum = (1 << p["input_width"]) - 1
        prefix = [{"B": maximum}, {"B": 1}, {"B": 1}, {"B": 0}] * 4
        if p["bypass"]:
            prefix = [{"B": maximum, "BYPASS": 1}, {"B": 1}, {"B": 0, "BYPASS": 1}] + prefix
        if p["clock_enable"] and p["bypass"]:
            prefix = [{"B": 1, "BYPASS": 1, "CE": 1},
                      {"B": 0, "BYPASS": 1, "CE": 0},
                      {"B": 0, "BYPASS": 0, "CE": 0}] + prefix
        return CycleSpec(
            inputs=(Port("B", p["input_width"]), *controls), outputs=(Port("Q", p["output_width"]),),
            settings={"Input_Width": p["input_width"], "Output_Width": p["output_width"],
                      "Input_Type": p["input_type"], "Accum_Mode": p["operation"],
                      "Implementation": "Fabric", "Latency": 1, "Latency_Configuration": "Manual",
                      "Scale": 0, "C_In": False, "Bypass": p["bypass"],
                      "Bypass_Sense": "Active_High", **control_settings(p)},
            model_parameters={"C_LATENCY": 1, "C_SCALE": 0, "C_IMPLEMENTATION": 0,
                              "C_B_TYPE": int(p["input_type"] == "Unsigned"),
                              "C_ADD_MODE": ("Add", "Subtract", "Add_Subtract").index(p["operation"]),
                              "C_CE_OVERRIDES_SCLR": int(p["ce_overrides_reset"])},
            model_factory=lambda: AccumulatorModel(p), prefix=tuple(prefix), neutral=neutral,
        )
