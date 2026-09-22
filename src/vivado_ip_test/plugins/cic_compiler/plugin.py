from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.cic_compiler.reference import (
    causal_input_counts, expected_transactions, full_precision_width, physical_width)
from vivado_ip_test.plugins.cic_compiler.vectors import prepare_frames, source_timing


class CicCompilerPlugin(StreamIpPlugin):
    ip_type = "cic_compiler"
    ip_name = "cic_compiler"
    version = "4.0"

    def describe(self, p):
        validate_parameters(p, {
            "filter_type": {"Decimation", "Interpolation"},
            "input_width": range(2, 33),
            "stages": range(2, 7),
            "differential_delay": range(1, 3),
            "rate": range(4, 8193),
        })
        output_width = full_precision_width(
            p["filter_type"], p["input_width"], p["stages"],
            p["differential_delay"], p["rate"])
        if output_width > 104:
            raise PluginError("CIC 全精度输出超过 104 位")
        input_physical = physical_width(p["input_width"])
        output_physical = physical_width(output_width)
        sample_period = p["rate"] if p["filter_type"] == "Interpolation" else 1
        settings = {
            "Filter_Type": p["filter_type"], "Number_Of_Stages": p["stages"],
            "Differential_Delay": p["differential_delay"], "Number_Of_Channels": 1,
            "Sample_Rate_Changes": "Fixed", "Fixed_Or_Initial_Rate": p["rate"],
            "RateSpecification": "Sample_Period", "SamplePeriod": sample_period,
            "Input_Data_Width": p["input_width"], "Quantization": "Full_Precision",
            "Use_Xtreme_DSP_Slice": True, "Use_Streaming_Interface": True,
            "HAS_ACLKEN": False, "HAS_ARESETN": True, "HAS_DOUT_TREADY": True,
        }
        models = {
            "C_FILTER_TYPE": 1 if p["filter_type"] == "Decimation" else 0,
            "C_NUM_STAGES": p["stages"], "C_DIFF_DELAY": p["differential_delay"],
            "C_RATE": p["rate"], "C_INPUT_WIDTH": p["input_width"],
            "C_OUTPUT_WIDTH": output_width, "C_NUM_CHANNELS": 1, "C_RATE_TYPE": 0,
            "C_S_AXIS_DATA_TDATA_WIDTH": input_physical,
            "C_M_AXIS_DATA_TDATA_WIDTH": output_physical,
            "C_HAS_DOUT_TREADY": 1, "C_HAS_ACLKEN": 0, "C_HAS_ARESETN": 1,
        }
        return StreamSpec(
            (Port("tdata", input_physical),), settings, models,
            output_payload=(Port("tdata", output_physical),),
            input_prefix="s_axis_data", output_prefix="m_axis_data",
            capacity=max(16, 2 * p["rate"]),
            transfer_interval_cycles=sample_period,
            drain_cycles=max(128, 4 * p["rate"]),
            preserves_transfer_count=False,
            ignored_outputs=(Port("event_halted", scalar=True),),
        )

    def generate_testbench(self, case):
        parameters = case.parameters
        spec = self.describe(parameters)
        return self._backend.generate(
            case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, parameters),
            prepare=lambda frames: prepare_frames(frames, parameters),
            source_timing=lambda schedule, profile: source_timing(schedule, profile, parameters),
            causal_inputs=lambda frames, expected: causal_input_counts(
                frames, expected, parameters),
            reference_contract={
                "model": "integer_cic_filter:1.0", "quantization": "full_precision",
                "filter_type": parameters["filter_type"],
                "rate_change": parameters["rate"],
                "advances_on": "accepted_axis_transfer",
                "vendor_bit_accurate": True,
            },
        )
