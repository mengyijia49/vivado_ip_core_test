from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.cordic.reference import ROUND_MODES, expected_transactions
from vivado_ip_test.plugins.cordic.vectors import prepare_frames
from vivado_ip_test.plugins.cordic.sin_cos.reference import (
    expected_transactions as sin_cos_expected, tolerances as sin_cos_tolerances)
from vivado_ip_test.plugins.cordic.sin_cos.vectors import prepare_frames as prepare_sin_cos


class CordicPlugin(StreamIpPlugin):
    ip_type = ip_name = "cordic"
    version = "6.0"

    def describe(self, p):
        if p.get("function") == "Sin_and_Cos":
            return self._describe_sin_cos(p)
        validate_parameters(p, {"function": {"Square_Root"}, "input_width": range(8, 49),
            "output_width": range(5, 49), "data_format": {"UnsignedInteger", "UnsignedFraction"},
            "rounding": ROUND_MODES, "architecture": {"Parallel"},
            "pipelining": {"No_Pipelining", "Optimal", "Maximum"},
            "optimization": {"Resources", "Performance"}, "has_last": bool, "user_width": range(257)})
        integer = p["data_format"] == "UnsignedInteger"
        if integer and p["output_width"] != p["input_width"] // 2 + 1:
            raise PluginError("CORDIC integer square root output width must be input_width // 2 + 1")
        if not integer and p["output_width"] < 8:
            raise PluginError("CORDIC fractional square root output width must be at least 8")
        source_width = ((p["input_width"] + 7) // 8) * 8
        sink_width = ((p["output_width"] + 7) // 8) * 8
        sidebands = ([Port("tlast", scalar=True)] if p["has_last"] else [])
        if p["user_width"]:
            sidebands.append(Port("tuser", p["user_width"]))
        settings = {"Functional_Selection": p["function"], "Architectural_Configuration": p["architecture"],
            "Pipelining_Mode": p["pipelining"], "Data_Format": p["data_format"], "Phase_Format": "Radians",
            "Input_Width": p["input_width"], "Output_Width": p["output_width"], "Round_Mode": p["rounding"],
            "Iterations": 0, "Precision": 0, "Coarse_Rotation": False,
            "Compensation_Scaling": "No_Scale_Compensation", "flow_control": "Blocking",
            "optimize_goal": p["optimization"], "out_tready": True, "ACLKEN": False, "ARESETN": True,
            "cartesian_has_tlast": p["has_last"], "cartesian_has_tuser": bool(p["user_width"]),
            "cartesian_tuser_width": p["user_width"] or 1, "phase_has_tlast": False,
            "phase_has_tuser": False, "phase_tuser_width": 1,
            "out_tlast_behv": "Pass_Cartesian_TLAST" if p["has_last"] else "Null"}
        metadata = {"C_ARCHITECTURE": 2, "C_CORDIC_FUNCTION": 6, "C_COARSE_ROTATE": 0,
            "C_DATA_FORMAT": 2 if integer else 1, "C_HAS_ACLK": 1, "C_HAS_ACLKEN": 0, "C_HAS_ARESETN": 1,
            "C_HAS_S_AXIS_CARTESIAN": 1, "C_HAS_S_AXIS_PHASE": 0,
            "C_INPUT_WIDTH": p["input_width"], "C_OUTPUT_WIDTH": p["output_width"],
            "C_ITERATIONS": 0, "C_PRECISION": 0, "C_PHASE_FORMAT": 0,
            "C_PIPELINE_MODE": {"No_Pipelining": 0, "Optimal": -1, "Maximum": -2}[p["pipelining"]],
            "C_ROUND_MODE": ROUND_MODES[p["rounding"]], "C_SCALE_COMP": 0,
            "C_THROTTLE_SCHEME": 1 if p["optimization"] == "Resources" else 2,
            "C_TLAST_RESOLUTION": int(p["has_last"]),
            "C_HAS_S_AXIS_CARTESIAN_TLAST": int(p["has_last"]),
            "C_HAS_S_AXIS_CARTESIAN_TUSER": int(bool(p["user_width"])),
            "C_S_AXIS_CARTESIAN_TUSER_WIDTH": p["user_width"] or 1,
            "C_HAS_S_AXIS_PHASE_TLAST": 0, "C_HAS_S_AXIS_PHASE_TUSER": 0,
            "C_S_AXIS_CARTESIAN_TDATA_WIDTH": source_width,
            "C_M_AXIS_DOUT_TDATA_WIDTH": sink_width, "C_M_AXIS_DOUT_TUSER_WIDTH": p["user_width"] or 1}
        return StreamSpec((Port("tdata", source_width), *sidebands), settings, metadata,
            capacity=p["output_width"] + 8, output_payload=(Port("tdata", sink_width), *sidebands),
            input_prefix="s_axis_cartesian", output_prefix="m_axis_dout")

    def _describe_sin_cos(self, p):
        validate_parameters(p, {"function": {"Sin_and_Cos"}, "input_width": range(8, 49),
            "output_width": range(8, 49), "phase_format": {"Radians", "Scaled_Radians"},
            "rounding": ROUND_MODES, "architecture": {"Parallel"},
            "pipelining": {"No_Pipelining", "Optimal", "Maximum"},
            "optimization": {"Resources", "Performance"}, "coarse_rotation": bool,
            "has_last": bool, "user_width": range(257)})
        source_width = ((p["input_width"] + 7) // 8) * 8
        field_width = ((p["output_width"] + 7) // 8) * 8
        sidebands = ([Port("tlast", scalar=True)] if p["has_last"] else [])
        if p["user_width"]:
            sidebands.append(Port("tuser", p["user_width"]))
        settings = {"Functional_Selection": p["function"], "Architectural_Configuration": p["architecture"],
            "Pipelining_Mode": p["pipelining"], "Data_Format": "SignedFraction",
            "Phase_Format": p["phase_format"], "Input_Width": p["input_width"],
            "Output_Width": p["output_width"], "Round_Mode": p["rounding"],
            "Iterations": 0, "Precision": 0, "Coarse_Rotation": p["coarse_rotation"],
            "Compensation_Scaling": "No_Scale_Compensation", "flow_control": "Blocking",
            "optimize_goal": p["optimization"], "out_tready": True, "ACLKEN": False, "ARESETN": True,
            "cartesian_has_tlast": False, "cartesian_has_tuser": False, "cartesian_tuser_width": 1,
            "phase_has_tlast": p["has_last"], "phase_has_tuser": bool(p["user_width"]),
            "phase_tuser_width": p["user_width"] or 1,
            "out_tlast_behv": "Pass_Phase_TLAST" if p["has_last"] else "Null"}
        metadata = {"C_ARCHITECTURE": 2, "C_CORDIC_FUNCTION": 2,
            "C_COARSE_ROTATE": int(p["coarse_rotation"]), "C_DATA_FORMAT": 0,
            "C_HAS_ACLK": 1, "C_HAS_ACLKEN": 0, "C_HAS_ARESETN": 1,
            "C_HAS_S_AXIS_CARTESIAN": 0, "C_HAS_S_AXIS_PHASE": 1,
            "C_INPUT_WIDTH": p["input_width"], "C_OUTPUT_WIDTH": p["output_width"],
            "C_ITERATIONS": 0, "C_PRECISION": 0,
            "C_PHASE_FORMAT": int(p["phase_format"] == "Scaled_Radians"),
            "C_PIPELINE_MODE": {"No_Pipelining": 0, "Optimal": -1, "Maximum": -2}[p["pipelining"]],
            "C_ROUND_MODE": ROUND_MODES[p["rounding"]], "C_SCALE_COMP": 0,
            "C_THROTTLE_SCHEME": 1 if p["optimization"] == "Resources" else 2,
            "C_TLAST_RESOLUTION": 2 if p["has_last"] else 0,
            "C_HAS_S_AXIS_PHASE_TLAST": int(p["has_last"]),
            "C_HAS_S_AXIS_PHASE_TUSER": int(bool(p["user_width"])),
            "C_S_AXIS_PHASE_TUSER_WIDTH": p["user_width"] or 1,
            "C_S_AXIS_PHASE_TDATA_WIDTH": source_width,
            "C_HAS_S_AXIS_CARTESIAN_TLAST": 0, "C_HAS_S_AXIS_CARTESIAN_TUSER": 0,
            "C_S_AXIS_CARTESIAN_TUSER_WIDTH": 1,
            "C_S_AXIS_CARTESIAN_TDATA_WIDTH": 2 * source_width,
            "C_M_AXIS_DOUT_TDATA_WIDTH": 2 * field_width,
            "C_M_AXIS_DOUT_TUSER_WIDTH": p["user_width"] or 1}
        tolerance_fields = ((field_width, True), (field_width, True),
                            *((port.width, False) for port in sidebands))
        return StreamSpec((Port("tdata", source_width), *sidebands), settings, metadata,
            capacity=p["output_width"] + 16,
            output_payload=(Port("tdata", 2 * field_width), *sidebands),
            input_prefix="s_axis_phase", output_prefix="m_axis_dout", drain_cycles=128,
            tolerance_fields=tolerance_fields)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        if case.parameters["function"] == "Sin_and_Cos":
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: sin_cos_expected(frames, case.parameters),
                prepare=lambda frames: prepare_sin_cos(frames, spec, case.parameters),
                tolerances=lambda frames, expected: sin_cos_tolerances(
                    frames, expected, case.parameters),
                reference_contract={"model": "cordic_sin_cos_decimal:1.0",
                    "arithmetic": "decimal_taylor_stable_quantization",
                    "rounding": case.parameters["rounding"], "vendor_bit_accurate": False,
                    "internal_precision": "automatic", "valid_phase_range_only": True,
                    "accuracy": "ideal_result_within_two_lsb_per_cartesian_field",
                    "mismatch_requires_precision_review": True,
                    "output_fields": "cosine_low_sine_high_sign_extended"})
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, case.parameters),
            prepare=lambda frames: prepare_frames(frames, spec, case.parameters),
            reference_contract={"model": "cordic_sqrt_exact_math:1.0",
                "rounding_input": "exact_mathematical_root", "vendor_bit_accurate": False,
                "internal_precision": "automatic",
                "mismatch_requires_precision_review": True, "output_padding": "sign_extension"})
