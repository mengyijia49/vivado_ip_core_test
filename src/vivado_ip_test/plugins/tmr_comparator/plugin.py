from dataclasses import replace

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.common.redundancy import fault_sequence
from vivado_ip_test.plugins.tmr_comparator.reference import TmrComparatorModel


class TmrComparatorPlugin(CycleIpPlugin):
    ip_type = "tmr_comparator"
    ip_name = "tmr_comparator"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 1025), "triple": bool,
            "disable_port": bool, "input_register": bool, "voter_check": bool,
            "include_mask": range(1 << 64)})
        if not p["triple"] and p["voter_check"]:
            raise PluginError("锁步比较器没有投票自检输入")
        if p["disable_port"] and not p["voter_check"]:
            raise PluginError("没有投票自检时 TMR_Disable 不影响离散比较结果")
        settings = {"C_INTERFACE": 0, "C_TMR": int(p["triple"]),
            "C_DISCRETE_WIDTH": p["width"], "C_USE_TMR_DISABLE": int(p["disable_port"]),
            "C_INPUT_REGISTER": int(p["input_register"]), "C_VOTER_CHECK": int(p["voter_check"]),
            "C_INCLUDE_MASK": f'0x{p["include_mask"]:016X}', "C_TEST_COMPARATOR": 0,
            "C_TEMPORAL_DEPTH1": 0, "C_TEMPORAL_DEPTH2": 0}
        inputs = tuple(Port(f"Discrete{i}", p["width"])
                       for i in range(1, 4 if p["triple"] else 3))
        if p["voter_check"]:
            inputs += (Port("Discrete", p["width"]),)
        if p["disable_port"]:
            inputs += (Port("TMR_Disable", scalar=True),)
        if p["input_register"]:
            inputs += (Port("Rst", scalar=True),)
        spec = CycleSpec(inputs=inputs, outputs=(Port("Compare", 4 if p["triple"] else 1),),
            settings=settings, model_parameters=settings,
            model_parameter_radices={"C_INCLUDE_MASK": 16},
            model_factory=lambda: TmrComparatorModel(p),
            clock="Clk" if p["input_register"] else None,
            idle_values={"Rst": 0} if p["input_register"] else {})
        return replace(spec, prefix=lambda: fault_sequence(p, spec, p["voter_check"]))
