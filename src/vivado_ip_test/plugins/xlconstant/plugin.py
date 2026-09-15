from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.metadata import BLOCK_DESIGN_XCI_GLOB
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.xlconstant.reference import ConstantModel, parse_literal


class XlConstantPlugin(CycleIpPlugin):
    ip_type = ip_name = "xlconstant"
    version = "1.1"

    def validate_case(self, case):
        if case.verification.case_budget != 1 or case.verification.coverage_targets != ("complete_input_space",):
            raise PluginError("A constant has one inputless state; use budget 1 and complete_input_space")
        if case.verification.timing_mode != "continuous":
            raise PluginError("An inputless constant does not have input gap or burst timing")
        super().validate_case(case)

    def describe(self, p):
        if set(p) != {"width", "value"} or type(p["width"]) is not int or not 1 <= p["width"] <= 4096:
            raise PluginError("Constant parameters require width from 1 to 4096 and value")
        try:
            value = parse_literal(p["value"])
        except ValueError as exc:
            raise PluginError(str(exc)) from exc
        if value.bit_length() > p["width"]:
            raise PluginError("Constant value exceeds its configured width")
        settings = {"CONST_WIDTH": p["width"], "CONST_VAL": p["value"]}
        model_parameters = {"CONST_WIDTH": p["width"], "CONST_VAL": hex(value)}
        return CycleSpec((), (Port("dout", p["width"]),), settings, model_parameters,
            lambda: ConstantModel(value), clock=None, flush_cycles=63,
            model_parameter_radices={"CONST_VAL": 16}, xci_glob=BLOCK_DESIGN_XCI_GLOB)
