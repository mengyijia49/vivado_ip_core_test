from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import payload_ports, payload_settings
from vivado_ip_test.plugins.axis_switch.spec import SwitchSpec
from vivado_ip_test.plugins.axis_switch.testbench import SwitchTestbenchBackend


ARBITERS = {"round_robin": 0, "fixed_priority": 1, "true_round_robin": 3}


class AxisSwitchPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_switch"
    version = "1.1"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = SwitchTestbenchBackend(layout, strategy_registry)

    def describe(self, p):
        validate_parameters(p, {"inputs": range(1, 17), "outputs": range(1, 17),
            "data_bytes": range(513), "user_width": range(4097), "id_width": range(33),
            "dest_width": range(33), "has_keep": bool, "has_strb": bool, "has_last": bool,
            "decoder_reg": bool, "output_reg": bool, "arbiter": tuple(ARBITERS),
            "arbitrate_transfers": range(1025), "arbitrate_cycles": range(1025), "arbitrate_last": bool,
            "routing": ("balanced", "reversed", "singletons", "gapped")})
        n, m = p["inputs"], p["outputs"]
        if n == m == 1:
            raise PluginError("Switch 至少需要两个输入或输出")
        if not p["data_bytes"] and (p["has_keep"] or p["has_strb"]):
            raise PluginError("无 DATA 时不能启用 KEEP/STRB")
        if (1 << p["dest_width"]) < m * (2 if p["routing"] == "gapped" else 1):
            raise PluginError("TDEST 位宽不足以覆盖路由表")
        if m == 1 and (p["decoder_reg"] or p["routing"] != "balanced"):
            raise PluginError("单输出时关闭译码寄存，只使用 balanced 路由")
        if n == 1 and (p["output_reg"] or p["arbiter"] != "round_robin" or
                       p["arbitrate_transfers"] != 1 or p["arbitrate_cycles"] or p["arbitrate_last"]):
            raise PluginError("单输入时仲裁参数固定为默认值，并关闭输出寄存")
        if p["arbitrate_last"] and not p["has_last"]:
            raise PluginError("按包尾仲裁需要 TLAST")
        if not p["arbitrate_transfers"] and not p["arbitrate_last"]:
            raise PluginError("必须按传输次数或包尾释放仲裁")
        if n > 1 and m > 1 and p["arbitrate_transfers"] != 1 and not p["arbitrate_last"] and not p["arbitrate_cycles"]:
            raise PluginError("多进多出且不按包尾仲裁时，需要空闲周期释放条件")
        payload = tuple(port for port in payload_ports(p) if port.width)
        tag_bits = (n - 1).bit_length()
        tag = next((name for name in ("tdata", "tuser", "tid")
                    if any(port.name == name and port.width > tag_bits for port in payload)), None)
        if tag is None:
            raise PluginError("自检需要一个数值字段，且位宽大于来源标记位数")
        limit = 1 << p["dest_width"]
        if p["routing"] in {"balanced", "reversed"}:
            routes = tuple((i * limit // m, (i + 1) * limit // m - 1) for i in range(m))
            if p["routing"] == "reversed":
                routes = routes[::-1]
        else:
            step = 2 if p["routing"] == "gapped" else 1
            routes = tuple((step * i, step * i) for i in range(m))
        settings = {"NUM_SI": n, "NUM_MI": m, **payload_settings(p), "ROUTING_MODE": 0,
            "HAS_TREADY": 1, "HAS_ACLKEN": 0, "DECODER_REG": int(p["decoder_reg"]),
            "OUTPUT_REG": int(p["output_reg"]), "ARB_ALGORITHM": ARBITERS[p["arbiter"]],
            "ARB_ON_MAX_XFERS": p["arbitrate_transfers"], "ARB_ON_NUM_CYCLES": p["arbitrate_cycles"],
            "ARB_ON_TLAST": int(p["arbitrate_last"])}
        for branch, (low, high) in enumerate(routes):
            settings.update({f"M{branch:02d}_AXIS_BASETDEST": f"0x{low:08x}",
                             f"M{branch:02d}_AXIS_HIGHTDEST": f"0x{high:08x}"})
            settings.update({f"M{branch:02d}_S{lane:02d}_CONNECTIVITY": 1 for lane in range(n)})
        dest_bits = max(1, p["dest_width"])
        signal_set = 1 + (2 if p["data_bytes"] else 0) + (4 if p["has_strb"] else 0) + (
            8 if p["has_keep"] else 0) + (16 if p["has_last"] else 0) + (32 if p["id_width"] else 0) + (
            64 if p["dest_width"] else 0) + (128 if p["user_width"] else 0)
        model = {"C_NUM_SI_SLOTS": n, "C_NUM_MI_SLOTS": m,
            "C_AXIS_TDATA_WIDTH": max(8, p["data_bytes"] * 8), "C_AXIS_TID_WIDTH": max(1, p["id_width"]),
            "C_AXIS_TDEST_WIDTH": dest_bits, "C_AXIS_TUSER_WIDTH": max(1, p["user_width"]),
            "C_ARB_ALGORITHM": ARBITERS[p["arbiter"]], "C_ARB_ON_MAX_XFERS": p["arbitrate_transfers"],
            "C_ARB_ON_NUM_CYCLES": p["arbitrate_cycles"], "C_ARB_ON_TLAST": int(p["arbitrate_last"]),
            "C_DECODER_REG": int(p["decoder_reg"]), "C_OUTPUT_REG": int(p["output_reg"]),
            "C_ROUTING_MODE": 0, "C_M_AXIS_CONNECTIVITY_ARRAY": bin((1 << (m*n)) - 1),
            "C_AXIS_SIGNAL_SET": bin(signal_set),
            "C_M_AXIS_BASETDEST_ARRAY": bin(sum(low << (i*dest_bits) for i, (low, high) in enumerate(routes))),
            "C_M_AXIS_HIGHTDEST_ARRAY": bin(sum(high << (i*dest_bits) for i, (low, high) in enumerate(routes)))}
        return SwitchSpec(payload, n, m, tag, tag_bits, routes, dict(p), settings, model)

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters), self.ip_name, self.version)
