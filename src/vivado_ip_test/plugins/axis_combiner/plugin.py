from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import payload_ports
from vivado_ip_test.plugins.axis_combiner.spec import CombinerSpec
from vivado_ip_test.plugins.axis_combiner.reference import expected_transactions
from vivado_ip_test.plugins.axis_combiner.testbench import render_testbench
from vivado_ip_test.plugins.axis_combiner.vectors import prepare_frames, lane_gaps


class AxisCombinerPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_combiner"
    version = "1.1"

    def describe(self, p):
        validate_parameters(p, {"inputs": range(2, 17), "data_bytes": range(513),
            "user_width": range(4097), "id_width": range(33), "dest_width": range(33),
            "has_keep": bool, "has_strb": bool, "has_last": bool, "primary_input": range(16)})
        if p["data_bytes"] * p["inputs"] > 512:
            raise PluginError("汇合后 TDATA 不能超过 512 字节")
        if p["primary_input"] >= p["inputs"]:
            raise PluginError("主接口编号必须小于输入通道数")
        if not (p["has_last"] or p["id_width"] or p["dest_width"]) and p["primary_input"]:
            raise PluginError("没有主接口字段时，主接口编号必须为 0")
        if not p["data_bytes"] and (p["has_keep"] or p["has_strb"]):
            raise PluginError("无 TDATA 时不能启用字节限定信号")
        payload = tuple(port for port in payload_ports(p) if port.width)
        if not any(port.name in {"tdata", "tuser", "tid", "tdest"} for port in payload):
            raise PluginError("汇合器当前要求至少有一个数值输入字段")
        settings = {"NUM_SI": p["inputs"], "TDATA_NUM_BYTES": p["data_bytes"],
            "TUSER_WIDTH": p["user_width"], "TID_WIDTH": p["id_width"], "TDEST_WIDTH": p["dest_width"],
            "MASTER_PORT_NUM": p["primary_input"], "HAS_CMD_ERR": 0, "HAS_ACLKEN": 0,
            **{f"HAS_T{name.upper()}": int(p[f"has_{name}"]) for name in ("keep", "strb", "last")}}
        model = {"C_NUM_SI_SLOTS": p["inputs"], "C_MASTER_PORT_NUM": p["primary_input"],
            "C_AXIS_TDATA_WIDTH": max(8, p["data_bytes"] * 8), "C_AXIS_TUSER_WIDTH": max(1, p["user_width"]),
            "C_AXIS_TID_WIDTH": max(1, p["id_width"]), "C_AXIS_TDEST_WIDTH": max(1, p["dest_width"])}
        return CombinerSpec(payload, p["inputs"], p["primary_input"], settings, model)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, spec),
            prepare=lambda frames: prepare_frames(frames, spec), renderer=render_testbench,
            source_timing=lambda schedule, profile: lane_gaps(schedule, profile, spec.input_lane_count))
