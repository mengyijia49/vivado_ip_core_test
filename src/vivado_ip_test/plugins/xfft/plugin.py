from dataclasses import dataclass
import math

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.common.stream.testbench import render_testbench, signal_wiring
from vivado_ip_test.plugins.xfft.reference import expected_transactions, output_width, padded_width
from vivado_ip_test.plugins.xfft.vectors import prepare_frames


ARCHITECTURES = {
    "pipelined_streaming_io": 3,
    "radix_2_burst_io": 2,
    "radix_2_lite_burst_io": 4,
    "radix_4_burst_io": 1,
}
EVENT_PORTS = (
    "event_frame_started", "event_tlast_unexpected", "event_tlast_missing",
    "event_status_channel_halt", "event_data_in_channel_halt",
    "event_data_out_channel_halt",
)


@dataclass(frozen=True)
class XfftSpec(StreamSpec):
    config_value: int = 1

    @property
    def inputs(self):
        return (*super().inputs, Port("s_axis_config_tdata", 8),
                Port("s_axis_config_tvalid", scalar=True))

    @property
    def outputs(self):
        return (*super().outputs, Port("s_axis_config_tready", scalar=True))


def render_xfft_testbench(spec, paths, count, max_gap, initial_stall):
    wiring = signal_wiring(spec)
    config_bits = format(spec.config_value, "08b")
    wiring["signals"] += "\n" + "\n".join((
        "  signal config_tdata : std_logic_vector(7 downto 0) := "
        f"\"{config_bits}\";",
        "  signal config_tvalid, config_tready : std_logic := '0';",
        "  signal event_tlast_unexpected, event_tlast_missing : std_logic := '0';",
    ))
    mappings = wiring["mappings"]
    mappings = mappings.replace("event_tlast_unexpected => open",
                                "event_tlast_unexpected => event_tlast_unexpected")
    mappings = mappings.replace("event_tlast_missing => open",
                                "event_tlast_missing => event_tlast_missing")
    mappings += (",\n      s_axis_config_tdata => config_tdata,"
                 "\n      s_axis_config_tvalid => config_tvalid,"
                 "\n      s_axis_config_tready => config_tready")
    wiring["mappings"] = mappings
    wiring["assignments"] = """      if accepted_count = 0 then
        config_tvalid <= '1';
        loop
          wait until rising_edge(s_clk);
          assert config_tready = '0' or config_tready = '1'
            report "AXIS_SELF_CHECK_STATUS: FAIL unknown config ready" severity failure;
          exit when config_tready = '1';
        end loop;
        wait until falling_edge(s_clk);
        config_tvalid <= '0';
      end if;
""" + wiring["assignments"]
    wiring["captures"] = """      assert event_tlast_unexpected = '0'
        report "AXIS_SELF_CHECK_STATUS: FAIL unexpected input TLAST event" severity failure;
      assert event_tlast_missing = '0'
        report "AXIS_SELF_CHECK_STATUS: FAIL missing input TLAST event" severity failure;
""" + wiring["captures"]
    return render_testbench(spec, paths, count, max_gap, initial_stall,
                            output_count=count, extra=wiring)


class XfftPlugin(StreamIpPlugin):
    ip_type = "xfft"
    ip_name = "xfft"
    version = "9.1"

    def describe(self, p):
        validate_parameters(p, {
            "transform_length": range(8, 257),
            "input_width": range(8, 35),
            "phase_factor_width": range(8, 35),
            "direction": {"forward", "inverse"},
            "output_ordering": {"natural_order", "bit_reversed_order"},
            "architecture": set(ARCHITECTURES),
        })
        if p["transform_length"] not in {8, 16, 32, 64, 128, 256}:
            raise PluginError("FFT 点数必须是 8 至 256 之间受支持的 2 的幂")
        if p["architecture"] == "radix_4_burst_io" and p["transform_length"] < 64:
            raise PluginError("Radix-4 Burst FFT 的点数不能小于 64")
        length = p["transform_length"]
        input_lane = padded_width(p["input_width"])
        result_width = output_width(p["input_width"], length)
        output_lane = padded_width(result_width)
        index_width = int(math.log2(length))
        settings = {
            "channels": 1, "transform_length": length,
            "implementation_options": p["architecture"],
            "run_time_configurable_transform_length": False,
            "data_format": "fixed_point", "input_width": p["input_width"],
            "phase_factor_width": p["phase_factor_width"], "scaling_options": "unscaled",
            "rounding_modes": "truncation", "aclken": False, "aresetn": True,
            "xk_index": True, "throttle_scheme": "nonrealtime",
            "output_ordering": p["output_ordering"], "cyclic_prefix_insertion": False,
            "super_sample_rates": 1,
        }
        models = {
            "C_S_AXIS_CONFIG_TDATA_WIDTH": 8,
            "C_S_AXIS_DATA_TDATA_WIDTH": 2 * input_lane,
            "C_M_AXIS_DATA_TDATA_WIDTH": 2 * output_lane,
            "C_M_AXIS_DATA_TUSER_WIDTH": padded_width(index_width),
            "C_NSSR": 1, "C_CHANNELS": 1, "C_NFFT_MAX": index_width,
            "C_ARCH": ARCHITECTURES[p["architecture"]], "C_HAS_NFFT": 0,
            "C_USE_FLT_PT": 0, "C_INPUT_WIDTH": p["input_width"],
            "C_TWIDDLE_WIDTH": p["phase_factor_width"], "C_OUTPUT_WIDTH": result_width,
            "C_HAS_SCALING": 0, "C_HAS_BFP": 0, "C_HAS_ROUNDING": 0,
            "C_HAS_ACLKEN": 0, "C_HAS_ARESETN": 1, "C_HAS_OVFLO": 0,
            "C_HAS_NATURAL_INPUT": 1,
            "C_HAS_NATURAL_OUTPUT": int(p["output_ordering"] == "natural_order"),
            "C_HAS_CYCLIC_PREFIX": 0, "C_HAS_XK_INDEX": 1,
        }
        return XfftSpec(
            payload=(Port("tdata", 2 * input_lane), Port("tlast", scalar=True)),
            settings=settings, model_parameters=models,
            output_payload=(Port("tdata", 2 * output_lane),
                            Port("tuser", padded_width(index_width)),
                            Port("tlast", scalar=True)),
            input_prefix="s_axis_data", output_prefix="m_axis_data",
            capacity=length, drain_cycles=max(128, 4 * length),
            ignored_outputs=tuple(Port(name, scalar=True) for name in EVENT_PORTS),
            config_value=int(p["direction"] == "forward"),
        )

    def generate_testbench(self, case):
        p = case.parameters
        return self._backend.generate(
            case, self.describe(p), self.ip_name, self.version,
            lambda frames: expected_transactions(frames, p),
            prepare=lambda frames: prepare_frames(frames, p), renderer=render_xfft_testbench,
            reference_contract={
                "model": "integer_dft_exact_patterns:1.0",
                "direction": p["direction"], "normalization": "none",
                "output_ordering": p["output_ordering"],
                "numeric_scope": "integer_exact_zero_impulse_constant_alternating_quarter_phase",
                "advances_on": "accepted_axis_transfer",
                "vendor_bit_accurate_model": False,
            },
        )
