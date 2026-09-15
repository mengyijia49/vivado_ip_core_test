from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import payload_ports
from vivado_ip_test.plugins.axis_broadcaster.spec import BroadcasterSpec
from vivado_ip_test.plugins.axis_broadcaster.remap import DATA_MAPPINGS, USER_MAPPINGS, expression
from vivado_ip_test.plugins.axis_broadcaster.reference import expected_transactions
from vivado_ip_test.plugins.axis_broadcaster.testbench import render_testbench
from vivado_ip_test.plugins.axis_broadcaster.vectors import prepare_frames, ready_matrix


class AxisBroadcasterPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_broadcaster"
    version = "1.1"

    def describe(self, p):
        validate_parameters(p, {"branches": range(2, 17), "input_bytes": range(513),
            "output_bytes": range(513), "input_user_width": range(4097), "output_user_width": range(4097),
            "id_width": range(33), "dest_width": range(33), "has_keep": bool, "has_strb": bool,
            "has_last": bool, "data_mapping": DATA_MAPPINGS, "user_mapping": USER_MAPPINGS})
        for source, sink, key in ((8 * p["input_bytes"], 8 * p["output_bytes"], "data_mapping"),
                                   (p["input_user_width"], p["output_user_width"], "user_mapping")):
            if bool(source) != bool(sink):
                raise PluginError("广播器当前要求对应字段两侧同时存在或同时关闭")
            if not source and p[key] != "replicate":
                raise PluginError("不存在的字段只能使用默认映射")
            if p[key] == "split" and source < sink * p["branches"]:
                raise PluginError("拆分模式要求输入宽度至少覆盖所有支路切片")
        if (p["has_keep"] or p["has_strb"]) and (not p["input_bytes"] or p["input_bytes"] != p["output_bytes"]):
            raise PluginError("当前字节限定信号要求存在 TDATA 且两侧字节宽度一致")
        source = tuple(port for port in payload_ports({**p, "data_bytes": p["input_bytes"],
                       "user_width": p["input_user_width"]}) if port.width)
        sink = tuple(port for port in payload_ports({**p, "data_bytes": p["output_bytes"],
                     "user_width": p["output_user_width"]}) if port.width)
        if not any(port.name not in {"tkeep", "tstrb", "tlast"} for port in source):
            raise PluginError("广播器当前要求至少有一个数值输入字段")
        settings = {"NUM_MI": p["branches"], "HAS_SPLITTER": 1, "HAS_TREADY": 1, "HAS_ACLKEN": 0,
            "S_TDATA_NUM_BYTES": p["input_bytes"], "M_TDATA_NUM_BYTES": p["output_bytes"],
            "S_TUSER_WIDTH": p["input_user_width"], "M_TUSER_WIDTH": p["output_user_width"],
            "TID_WIDTH": p["id_width"], "TDEST_WIDTH": p["dest_width"],
            **{f"HAS_T{name.upper()}": int(p[f"has_{name}"]) for name in ("keep", "strb", "last")}}
        for branch in range(p["branches"]):
            settings[f"M{branch:02d}_TDATA_REMAP"] = expression("tdata", 8 * p["input_bytes"],
                8 * p["output_bytes"], p["data_mapping"], branch)
            settings[f"M{branch:02d}_TUSER_REMAP"] = expression("tuser", p["input_user_width"],
                p["output_user_width"], p["user_mapping"], branch)
        model = {"C_NUM_MI_SLOTS": p["branches"],
            "C_S_AXIS_TDATA_WIDTH": max(8, 8 * p["input_bytes"]),
            "C_M_AXIS_TDATA_WIDTH": max(8, 8 * p["output_bytes"]),
            "C_S_AXIS_TUSER_WIDTH": max(1, p["input_user_width"]),
            "C_M_AXIS_TUSER_WIDTH": max(1, p["output_user_width"]),
            "C_AXIS_TID_WIDTH": max(1, p["id_width"]), "C_AXIS_TDEST_WIDTH": max(1, p["dest_width"])}
        return BroadcasterSpec(source, sink, p["branches"], settings, model)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, case.parameters, spec),
            prepare=lambda frames: prepare_frames(frames, spec), renderer=render_testbench,
            sink_pattern=lambda profile: ready_matrix(profile, spec.branch_count))
