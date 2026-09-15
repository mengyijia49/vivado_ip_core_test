from vivado_ip_test.plugins.common.bit_patterns import bit_identity_frames
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.inline_metadata import INLINE_BD_GLOB
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.ilreduced_logic.reference import InlineReducedLogicModel


class IlReducedLogicPlugin(CycleIpPlugin):
    ip_type = ip_name = "ilreduced_logic"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 65537), "operation": {"and", "or", "xor"}})
        width, operation = p["width"], p["operation"]
        ports = (Port("Op1", width),)
        mask = (1 << width) - 1

        def prefix():
            yield from bit_identity_frames(ports)
            # A reduction can hide a missing bit in dense random inputs; isolate every bit.
            for bit in range(width):
                yield {"Op1": 1 << bit}
                yield {"Op1": mask ^ (1 << bit)}

        return CycleSpec(ports, (Port("Res", scalar=True),),
            {"C_SIZE": width, "C_OPERATION": operation}, {},
            lambda: InlineReducedLogicModel(width, operation), clock=None,
            prefix=prefix, inline_bd_glob=INLINE_BD_GLOB)
