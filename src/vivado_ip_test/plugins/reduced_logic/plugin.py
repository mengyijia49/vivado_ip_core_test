from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.reduced_logic.reference import ReducedLogicModel


class ReducedLogicPlugin(CycleIpPlugin):
    ip_type = "reduced_logic"
    ip_name = "util_reduced_logic"
    version = "2.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 257), "operation": {"and", "or", "xor"}})
        return CycleSpec(inputs=(Port("Op1", p["width"]),), outputs=(Port("Res", scalar=True),),
                         clock=None, settings={"C_SIZE": p["width"], "C_OPERATION": p["operation"]},
                         model_parameters={"C_SIZE": p["width"], "C_OPERATION": p["operation"]},
                         model_factory=lambda: ReducedLogicModel(p))
