from vivado_ip_test.plugins.common.bit_patterns import bit_identity_frames
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.inline_metadata import INLINE_BD_GLOB
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.ilvector_logic.reference import InlineVectorLogicModel


class IlVectorLogicPlugin(CycleIpPlugin):
    ip_type = ip_name = "ilvector_logic"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 65537), "operation": {"and", "or", "xor", "not"}})
        width, operation = p["width"], p["operation"]
        ports = (Port("Op1", width),) + (() if operation == "not" else (Port("Op2", width),))
        mask = (1 << width) - 1

        def prefix():
            if operation == "not":
                yield from bit_identity_frames(ports)
                return
            # Each operand is varied while the other permits its bits to reach the output.
            for row in bit_identity_frames((Port("value", width),)):
                value = row["value"]
                for a, b in ((value, 0), (0, value), (value, mask), (mask, value),
                             (value, value), (value, mask ^ value)):
                    yield {"Op1": a, "Op2": b}

        return CycleSpec(ports, (Port("Res", width),),
            {"C_SIZE": width, "C_OPERATION": operation}, {},
            lambda: InlineVectorLogicModel(width, operation), clock=None,
            prefix=prefix, inline_bd_glob=INLINE_BD_GLOB)
