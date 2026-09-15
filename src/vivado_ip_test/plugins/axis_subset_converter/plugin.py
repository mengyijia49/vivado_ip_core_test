from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec, payload_ports
from vivado_ip_test.plugins.axis_subset_converter.remap import MAPPINGS, build_remaps
from vivado_ip_test.plugins.axis_subset_converter.reference import expected_transactions
from vivado_ip_test.plugins.axis_subset_converter.vectors import prepare_frames


class AxisSubsetConverterPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_subset_converter"
    version = "1.1"

    def describe(self, p):
        rules = {"mapping": MAPPINGS, "last_period": range(257)}
        for side in ("input", "output"):
            rules.update({f"{side}_bytes": range(513), f"{side}_user_width": range(4097),
                          f"{side}_id_width": range(33), f"{side}_dest_width": range(33)})
            rules.update({f"{side}_has_{name}": bool for name in ("keep", "strb", "last")})
        validate_parameters({k: v for k, v in p.items() if k != "remap"}, rules)
        if p["input_has_keep"] and not p["output_has_keep"]:
            raise PluginError("删除输入 TKEEP 的告警接口尚未接入")
        if p["last_period"] and (p["input_has_last"] or not p["output_has_last"]):
            raise PluginError("包尾计数要求无输入 TLAST 且有输出 TLAST")
        ports, settings, model = {}, {"HAS_ACLKEN": 0, "S_HAS_TREADY": 1, "M_HAS_TREADY": 1,
                                    "DEFAULT_TLAST": p["last_period"]}, {"C_DEFAULT_TLAST": p["last_period"]}
        for side, prefix in (("input", "S"), ("output", "M")):
            if not p[f"{side}_bytes"] and (p[f"{side}_has_keep"] or p[f"{side}_has_strb"]):
                raise PluginError("无 TDATA 时不能启用字节限定信号")
            config = {"data_bytes": p[f"{side}_bytes"], "user_width": p[f"{side}_user_width"],
                      "id_width": p[f"{side}_id_width"], "dest_width": p[f"{side}_dest_width"],
                      **{f"has_{n}": p[f"{side}_has_{n}"] for n in ("keep", "strb", "last")}}
            ports[side] = tuple(port for port in payload_ports(config) if port.width)
            settings.update({f"{prefix}_TDATA_NUM_BYTES": config["data_bytes"],
                f"{prefix}_TUSER_WIDTH": config["user_width"], f"{prefix}_TID_WIDTH": config["id_width"],
                f"{prefix}_TDEST_WIDTH": config["dest_width"],
                **{f"{prefix}_HAS_T{n.upper()}": int(config[f"has_{n}"]) for n in ("keep", "strb", "last")}})
            model.update({f"C_{prefix}_AXIS_TDATA_WIDTH": max(8, 8 * config["data_bytes"]),
                          **{f"C_{prefix}_AXIS_T{name.upper()}_WIDTH": max(1, config[f"{name}_width"])
                             for name in ("user", "id", "dest")}})
        source, sink = ports["input"], ports["output"]
        if not source or not sink:
            raise PluginError("当前检查器要求每侧至少有一个有效载荷信号")
        mode = p["mapping"]
        if mode != "resize" and not p["output_bytes"]:
            raise PluginError("非默认数据映射要求输出 TDATA")
        if mode in {"reverse_bytes", "reverse_bits", "rotate_bytes", "repeat_low_byte", "data_user_swap"} and not p["input_bytes"]:
            raise PluginError("该映射要求输入 TDATA")
        if mode in {"user_to_data", "data_user_swap"} and not p["input_user_width"]:
            raise PluginError("该映射要求输入 TUSER")
        if mode == "data_user_swap" and not p["output_user_width"]:
            raise PluginError("数据/用户字段交换要求输出 TUSER")
        remap = p.get("remap", {})
        if not isinstance(remap, dict) or set(remap) - {port.name for port in sink}:
            raise PluginError("remap 只能指定实际存在的输出字段")
        if p["last_period"] and "tlast" in remap:
            raise PluginError("自动包尾不能同时指定 TLAST 映射")
        settings.update({name.upper() + "_REMAP": expression for name, expression
                         in build_remaps(p, source, sink).items()})
        return StreamSpec(source, settings, model, output_payload=sink)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, case.parameters, spec.payload, spec.sink_payload),
            prepare=lambda frames: prepare_frames(frames, spec, case.parameters["last_period"]))
