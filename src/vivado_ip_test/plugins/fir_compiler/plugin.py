from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.fir_compiler.reference import expected_transactions, vendor_output_width
from vivado_ip_test.plugins.fir_compiler.vectors import prepare_frames


ARCHITECTURES = {"Systolic_Multiply_Accumulate", "Transpose_Multiply_Accumulate"}


class FirCompilerPlugin(StreamIpPlugin):
    ip_type = "fir_compiler"
    ip_name = "fir_compiler"
    version = "7.2"

    def describe(self, p):
        scalar_rules = {"data_width": range(8, 33), "coefficient_width": range(2, 25),
            "architecture": ARCHITECTURES, "has_last": bool, "user_width": range(65)}
        if set(p) != set(scalar_rules) | {"coefficients"}:
            raise PluginError("FIR parameter names do not match the supported schema")
        validate_parameters({name: p[name] for name in scalar_rules}, scalar_rules)
        coefficients = p.get("coefficients")
        if (not isinstance(coefficients, list) or not 1 <= len(coefficients) <= 256
                or any(type(value) is not int for value in coefficients)):
            raise PluginError("FIR coefficients must be a nonempty integer list of at most 256 taps")
        low, high = -(1 << (p["coefficient_width"] - 1)), (1 << (p["coefficient_width"] - 1)) - 1
        if any(not low <= value <= high for value in coefficients) or not any(coefficients):
            raise PluginError("FIR coefficient does not fit coefficient_width or all taps are zero")
        if p["architecture"] == "Transpose_Multiply_Accumulate" and coefficients == coefficients[::-1]:
            raise PluginError("Transpose architecture does not accept symmetric coefficient optimization")
        output_width = vendor_output_width(p["data_width"], coefficients)
        source_width = ((p["data_width"] + 7) // 8) * 8
        sink_width = ((output_width + 7) // 8) * 8
        sidebands = ([Port("tlast", scalar=True)] if p["has_last"] else [])
        if p["user_width"]:
            sidebands.append(Port("tuser", p["user_width"]))
        settings = {"Filter_Type": "Single_Rate", "DataCoefficientType": "Real",
            "CoefficientSource": "Vector", "Coefficient_Sets": 1, "Coefficient_Reload": False,
            "Coefficient_Structure": "Non_Symmetric", "Quantization": "Integer_Coefficients",
            "Data_Sign": "Signed", "Data_Width": p["data_width"],
            "Coefficient_Sign": "Signed" if any(value < 0 for value in coefficients) else "Unsigned",
            "Coefficient_Width": p["coefficient_width"],
            "CoefficientVector": ",".join(str(value) for value in coefficients),
            "Output_Rounding_Mode": "Full_Precision", "Filter_Architecture": p["architecture"],
            "Number_Channels": 1, "Number_Paths": 1, "RateSpecification": "Input_Sample_Period",
            "SamplePeriod": 1, "M_DATA_Has_TREADY": True, "S_DATA_Has_FIFO": True,
            "Has_ARESETn": True, "Reset_Data_Vector": True, "Has_ACLKEN": False,
            "DATA_Has_TLAST": "Packet_Framing" if p["has_last"] else "Not_Required",
            "S_DATA_Has_TUSER": "User_Field" if p["user_width"] else "Not_Required",
            "M_DATA_Has_TUSER": "User_Field" if p["user_width"] else "Not_Required",
            "DATA_TUSER_Width": p["user_width"] or 1}
        models = {"C_DATA_WIDTH": p["data_width"], "C_COEF_WIDTH": p["coefficient_width"],
            "C_NUM_TAPS": len(coefficients), "C_OUTPUT_WIDTH": output_width,
            "C_S_DATA_TDATA_WIDTH": source_width, "C_M_DATA_TDATA_WIDTH": sink_width,
            "C_S_DATA_TUSER_WIDTH": p["user_width"] or 1,
            "C_M_DATA_TUSER_WIDTH": p["user_width"] or 1}
        return StreamSpec((Port("tdata", source_width), *sidebands), settings, models,
            capacity=max(16, len(coefficients) + 8),
            output_payload=(Port("tdata", sink_width), *sidebands),
            input_prefix="s_axis_data", output_prefix="m_axis_data", drain_cycles=256)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, case.parameters),
            prepare=lambda frames: prepare_frames(frames, spec, case.parameters),
            reference_contract={"model": "integer_fir_convolution:1.0",
                "history_initialization": "zero", "advances_on": "accepted_input_transfer",
                "rounding": "full_precision", "vendor_bit_accurate": True})
