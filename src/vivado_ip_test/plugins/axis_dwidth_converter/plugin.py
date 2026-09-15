from vivado_ip_test.domain import Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.byte_testbench import ByteStreamTestbenchBackend, raw_audit
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec, payload_ports
from vivado_ip_test.plugins.axis_dwidth_converter.reference import expected_transactions
from vivado_ip_test.plugins.axis_dwidth_converter.vectors import prepare_frames


class AxisDwidthConverterPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_dwidth_converter"
    version = "1.1"

    def __init__(self, layout, strategy_registry):
        super().__init__(layout, strategy_registry)
        self._backend = ByteStreamTestbenchBackend(layout, strategy_registry)

    def describe(self, p):
        validate_parameters(p, {"input_bytes": range(1, 513), "output_bytes": range(1, 513),
            "id_width": range(0, 33), "dest_width": range(0, 33), "user_bits_per_byte": range(0, 2049),
            "has_keep": bool, "has_strb": bool, "has_last": bool})
        if max(p["input_bytes"], p["output_bytes"]) * p["user_bits_per_byte"] > 4096:
            raise PluginError("每侧 TUSER 位宽不能超过 4096")
        s, m = p["input_bytes"], p["output_bytes"]
        controls = p["has_last"] or p["id_width"] or p["dest_width"]
        added_keep = bool((controls or m % s) if m >= s else (s % m and controls))
        source = payload_ports({**p, "data_bytes": s, "user_width": s * p["user_bits_per_byte"]})
        sink = payload_ports({**p, "data_bytes": m, "user_width": m * p["user_bits_per_byte"],
                              "has_keep": p["has_keep"] or added_keep})
        settings = {"S_TDATA_NUM_BYTES": s, "M_TDATA_NUM_BYTES": m,
            "TID_WIDTH": p["id_width"], "TDEST_WIDTH": p["dest_width"],
            "TUSER_BITS_PER_BYTE": p["user_bits_per_byte"], "HAS_TKEEP": int(p["has_keep"]),
            "HAS_TSTRB": int(p["has_strb"]), "HAS_TLAST": int(p["has_last"]),
            "HAS_MI_TKEEP": int(added_keep), "HAS_TREADY": 1, "HAS_ACLKEN": 0}
        return StreamSpec(source, settings, {"C_S_AXIS_TDATA_WIDTH": s * 8,
            "C_M_AXIS_TDATA_WIDTH": m * 8, "C_AXIS_TID_WIDTH": max(1, p["id_width"]),
            "C_AXIS_TDEST_WIDTH": max(1, p["dest_width"]),
            "C_S_AXIS_TUSER_WIDTH": max(1, s * p["user_bits_per_byte"]),
            "C_M_AXIS_TUSER_WIDTH": max(1, m * p["user_bits_per_byte"])},
            output_payload=sink, capacity=max(s, m) + 2, masked_outputs=True)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda generated: prepare_frames(generated, case.parameters, spec),
            lambda frames: expected_transactions(frames, spec.payload))

    def verify_simulation(self, case, stage):
        status = super().verify_simulation(case, stage)
        if status is Status.PASS and not raw_audit(self._layout.case_run_dir(case), self.describe(case.parameters)):
            return Status.VERIFICATION_FAILED
        return status
