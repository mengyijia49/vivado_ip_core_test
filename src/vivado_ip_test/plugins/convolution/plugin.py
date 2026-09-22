from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.convolution.reference import (
    convolution_codes, expected_transactions)
from vivado_ip_test.plugins.convolution.vectors import prepare_frames


class ConvolutionPlugin(StreamIpPlugin):
    ip_type = "convolution"
    ip_name = "convolution"
    version = "9.0"

    def describe(self, p):
        validate_parameters(p, {
            "constraint_length": range(3, 10),
            "output_rate": range(2, 8),
            "code_family": {"ascending", "descending", "spread"},
        })
        codes = convolution_codes(p["constraint_length"], p["output_rate"],
                                  p["code_family"])
        settings = {
            "Punctured": False,
            "Output_Rate": p["output_rate"],
            "Constraint_Length": p["constraint_length"],
            "Convolution_Code_Radix": "Binary",
            "TREADY": True,
            "ACLKEN": False,
        }
        settings.update({f"Convolution_Code{index}":
                         format(code, f"0{p['constraint_length']}b")
                         for index, code in enumerate(codes)})
        model = {
            "C_HAS_M_AXIS_DATA_TREADY": 1,
            "C_HAS_ACLKEN": 0,
            "C_OUTPUT_RATE": p["output_rate"],
            "C_CONSTRAINT_LENGTH": p["constraint_length"],
            "C_PUNCTURED": 0,
            "C_DUAL_CHANNEL": 0,
        }
        model.update({f"C_CONVOLUTION_CODE{index}": code
                      for index, code in enumerate(codes)})
        return StreamSpec(
            (Port("tdata", 8),), settings, model,
            output_payload=(Port("tdata", 8),),
            input_prefix="s_axis_data", output_prefix="m_axis_data",
            capacity=16, drain_cycles=96,
        )

    def generate_testbench(self, case):
        parameters = case.parameters
        spec = self.describe(parameters)
        codes = convolution_codes(parameters["constraint_length"],
                                  parameters["output_rate"],
                                  parameters["code_family"])
        return self._backend.generate(
            case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, parameters),
            prepare=lambda frames: prepare_frames(frames, parameters),
            reference_contract={
                "model": "binary_convolution_encoder:1.0",
                "constraint_length": parameters["constraint_length"],
                "output_rate": parameters["output_rate"],
                "convolution_codes": list(codes),
                "advances_on": "accepted_axis_transfer",
                "vendor_bit_accurate": True,
            },
        )
