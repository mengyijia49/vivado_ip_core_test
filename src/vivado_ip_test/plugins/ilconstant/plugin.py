from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.inline_metadata import INLINE_BD_GLOB
from vivado_ip_test.plugins.common.integer_literals import parse_unsigned_literal
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.ilconstant.reference import InlineConstantModel


class IlConstantPlugin(CycleIpPlugin):
    ip_type = ip_name = "ilconstant"
    version = "1.0"

    def validate_case(self, case):
        if case.verification.case_budget != 1 or case.verification.coverage_targets != ("complete_input_space",):
            raise PluginError("Inline constant has one inputless state; use budget 1 and complete_input_space")
        if case.verification.timing_mode != "continuous":
            raise PluginError("Inline constant has no input timing")
        super().validate_case(case)

    def describe(self, p):
        if set(p) != {"width", "value"} or type(p["width"]) is not int or not 1 <= p["width"] <= 4096:
            raise PluginError("Inline constant requires width from 1 to 4096 and value")
        try:
            value = parse_unsigned_literal(p["value"])
        except ValueError as exc:
            raise PluginError(str(exc)) from exc
        if value.bit_length() > p["width"]:
            raise PluginError("Inline constant value does not fit the configured width")
        settings = {"CONST_WIDTH": p["width"], "CONST_VAL": p["value"]}
        return CycleSpec((), (Port("dout", p["width"]),), settings, {},
            lambda: InlineConstantModel(value), clock=None, flush_cycles=63,
            inline_bd_glob=INLINE_BD_GLOB)
