from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import (
    CycleSpec, Port, control_ports, control_settings, validate_parameters,
)
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.adder_subtractor.reference import AdderModel


class AdderSubtractorPlugin(CycleIpPlugin):
    ip_type = "adder_subtractor"
    ip_name = "c_addsub"
    version = "12.0"

    def describe(self, p):
        validate_parameters(p, {
            "a_width": range(1, 257), "b_width": range(1, 257), "output_width": range(1, 257),
            "a_type": {"Signed", "Unsigned"}, "b_type": {"Signed", "Unsigned"},
            "operation": {"Add", "Subtract", "Add_Subtract"}, "latency": range(0, 2),
            "clock_enable": bool, "sync_clear": bool, "ce_overrides_reset": bool,
        })
        if p["output_width"] < max(p["a_width"], p["b_width"]):
            raise PluginError("当前加减法后端要求 output_width 不小于两个输入位宽")
        if p["output_width"] > max(p["a_width"], p["b_width"]) + 1:
            raise PluginError("当前加减法后端最多保留一位扩展结果")
        if not p["latency"] and (p["clock_enable"] or p["sync_clear"]):
            raise PluginError("组合加减法不能启用 CE 或 SCLR")
        dynamic = p["operation"] == "Add_Subtract"
        controls = control_ports(p, dynamic="ADD" if dynamic else None)
        neutral = {port.name: int(port.name != "SCLR") for port in controls}
        return CycleSpec(
            inputs=(Port("A", p["a_width"]), Port("B", p["b_width"]), *controls),
            outputs=(Port("S", p["output_width"]),),
            settings={"A_Width": p["a_width"], "B_Width": p["b_width"],
                      "Out_Width": p["output_width"], "A_Type": p["a_type"], "B_Type": p["b_type"],
                      "Add_Mode": p["operation"], "Implementation": "Fabric", "Latency": p["latency"],
                      "Latency_Configuration": "Manual", "C_In": False, "C_Out": False,
                      "B_Constant": False, "Bypass": False, **control_settings(p)},
            model_parameters={"C_LATENCY": p["latency"], "C_IMPLEMENTATION": 0,
                              "C_A_TYPE": int(p["a_type"] == "Unsigned"),
                              "C_B_TYPE": int(p["b_type"] == "Unsigned"),
                              "C_ADD_MODE": ("Add", "Subtract", "Add_Subtract").index(p["operation"]),
                              "C_CE_OVERRIDES_SCLR": int(p["ce_overrides_reset"])},
            model_factory=lambda: AdderModel(p), clock="CLK" if p["latency"] else None,
            neutral=neutral,
        )
