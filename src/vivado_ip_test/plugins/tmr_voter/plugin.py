from dataclasses import replace

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.common.redundancy import fault_sequence
from vivado_ip_test.plugins.tmr_voter.reference import TmrVoterModel


class TmrVoterPlugin(CycleIpPlugin):
    ip_type = "tmr_voter"
    ip_name = "tmr_voter"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 1025), "triple": bool,
            "disable_port": bool, "comparator": bool, "input_register": bool,
            "voter_check": bool, "include_mask": range(1 << 64)})
        if not p["triple"] and (p["voter_check"] or p["disable_port"]):
            raise PluginError("锁步模式不启用投票自检或 TMR_Disable")
        if not p["comparator"] and (p["input_register"] or p["voter_check"] or
                                      p["include_mask"] != (1 << 64) - 1):
            raise PluginError("未启用比较器时不设置寄存器、自检或比较掩码")
        settings = {"C_INTERFACE": 0, "C_TMR": int(p["triple"]),
            "C_DISCRETE_WIDTH": p["width"], "C_USE_TMR_DISABLE": int(p["disable_port"]),
            "C_COMPARATOR": int(p["comparator"]), "C_INPUT_REGISTER": int(p["input_register"]),
            "C_VOTER_CHECK": int(p["voter_check"]), "C_INCLUDE_MASK": f'0x{p["include_mask"]:016X}',
            "C_TEST_COMPARATOR": 0, "C_TEMPORAL_DEPTH1": 0, "C_TEMPORAL_DEPTH2": 0}
        inputs = tuple(Port(f"Discrete{i}", p["width"])
                       for i in range(1, 4 if p["triple"] else 3))
        if p["disable_port"]:
            inputs += (Port("TMR_Disable", scalar=True),)
        outputs = (Port("Discrete", p["width"]),)
        if p["comparator"]:
            outputs += (Port("Compare", 4),)
        spec = CycleSpec(inputs=inputs, outputs=outputs, settings=settings,
            model_parameters=settings,
            model_parameter_radices={"C_INCLUDE_MASK": 16},
            model_factory=lambda: TmrVoterModel(p),
            clock="Clk" if p["input_register"] else None,
            masked_outputs=p["comparator"] and not p["triple"])
        return replace(spec, prefix=lambda: fault_sequence(p, spec))
