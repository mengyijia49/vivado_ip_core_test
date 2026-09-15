from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.vector_logic.reference import VectorLogicModel


class VectorLogicPlugin(CycleIpPlugin):
    ip_type = "vector_logic"
    ip_name = "util_vector_logic"
    version = "2.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 257), "operation": {"and", "or", "xor", "not"}})
        inputs = (Port("Op1", p["width"]),)
        if p["operation"] != "not":
            inputs += (Port("Op2", p["width"]),)
        return CycleSpec(inputs=inputs, outputs=(Port("Res", p["width"]),), clock=None,
                         settings={"C_SIZE": p["width"], "C_OPERATION": p["operation"]},
                         model_parameters={"C_SIZE": p["width"], "C_OPERATION": p["operation"]},
                         model_factory=lambda: VectorLogicModel(p))
