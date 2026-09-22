from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.axi_sideband_util.reference import AxiSidebandUtilModel
from vivado_ip_test.plugins.axi_sideband_util.vectors import directed_sequence


DATA_WIDTHS = {32, 64, 128, 256, 512, 1024}
SMID_MODES = {"Bypass", "Insert", "Remove"}


class AxiSidebandUtilPlugin(CycleIpPlugin):
    ip_type = ip_name = "axi_sideband_util"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {
            "data_width": range(32, 1025), "id_width": range(1, 33),
            "address_user_width": range(1, 513), "smid_mode": SMID_MODES,
            "smid_width": range(1, 33), "smid_value": range(0, 1 << 32),
        })
        if p["data_width"] not in DATA_WIDTHS:
            raise PluginError("AXI Sideband Utility 数据位宽不受支持")
        if p["smid_width"] > p["address_user_width"]:
            raise PluginError("SMID 位宽不能超过地址 USER 位宽")
        if p["smid_value"] >= 1 << p["smid_width"]:
            raise PluginError("SMID 固定值超出 smid_width")
        if p["smid_mode"] != "Insert" and p["smid_value"] != 0:
            raise PluginError("只有 Insert 模式使用 smid_value")

        output_user_width = p["address_user_width"]
        if p["smid_mode"] == "Insert":
            output_user_width += p["smid_width"]
        elif p["smid_mode"] == "Remove":
            output_user_width -= p["smid_width"]
            if output_user_width < 1:
                raise PluginError("Remove 模式至少保留一位地址 USER")

        inputs = [Port("aresetn", scalar=True), Port("aclken", scalar=True)]
        for channel in ("aw", "ar"):
            inputs.extend((
                Port(f"s_axi_{channel}id", p["id_width"]),
                Port(f"s_axi_{channel}addr", 32), Port(f"s_axi_{channel}len", 8),
                Port(f"s_axi_{channel}size", 3), Port(f"s_axi_{channel}burst", 2),
                Port(f"s_axi_{channel}lock", 1), Port(f"s_axi_{channel}cache", 4),
                Port(f"s_axi_{channel}prot", 3), Port(f"s_axi_{channel}qos", 4),
                Port(f"s_axi_{channel}user", p["address_user_width"]),
                Port(f"s_axi_{channel}valid", scalar=True),
            ))
        inputs.extend((
            Port("s_axi_wdata", p["data_width"]), Port("s_axi_wstrb", p["data_width"] // 8),
            Port("s_axi_wlast", scalar=True), Port("s_axi_wvalid", scalar=True),
            Port("s_axi_bready", scalar=True), Port("s_axi_rready", scalar=True),
            Port("m_axi_awready", scalar=True), Port("m_axi_wready", scalar=True),
            Port("m_axi_bid", p["id_width"]), Port("m_axi_bresp", 2),
            Port("m_axi_bvalid", scalar=True), Port("m_axi_arready", scalar=True),
            Port("m_axi_rid", p["id_width"]), Port("m_axi_rdata", p["data_width"]),
            Port("m_axi_rresp", 2), Port("m_axi_rlast", scalar=True),
            Port("m_axi_rvalid", scalar=True),
            Port("w_parity_error_injection", scalar=True),
            Port("r_parity_error_injection", scalar=True),
        ))

        outputs = []
        for channel in ("aw", "ar"):
            outputs.extend((
                Port(f"m_axi_{channel}id", p["id_width"]),
                Port(f"m_axi_{channel}addr", 32), Port(f"m_axi_{channel}len", 8),
                Port(f"m_axi_{channel}size", 3), Port(f"m_axi_{channel}burst", 2),
                Port(f"m_axi_{channel}lock", 1), Port(f"m_axi_{channel}cache", 4),
                Port(f"m_axi_{channel}prot", 3), Port(f"m_axi_{channel}qos", 4),
                Port(f"m_axi_{channel}user", output_user_width),
                Port(f"m_axi_{channel}valid", scalar=True),
                Port(f"s_axi_{channel}ready", scalar=True),
            ))
        outputs.extend((
            Port("m_axi_wdata", p["data_width"]), Port("m_axi_wstrb", p["data_width"] // 8),
            Port("m_axi_wlast", scalar=True), Port("m_axi_wvalid", scalar=True),
            Port("s_axi_wready", scalar=True), Port("s_axi_bid", p["id_width"]),
            Port("s_axi_bresp", 2), Port("s_axi_bvalid", scalar=True),
            Port("m_axi_bready", scalar=True), Port("s_axi_rid", p["id_width"]),
            Port("s_axi_rdata", p["data_width"]), Port("s_axi_rresp", 2),
            Port("s_axi_rlast", scalar=True), Port("s_axi_rvalid", scalar=True),
            Port("m_axi_rready", scalar=True), Port("w_parity_error", scalar=True),
            Port("r_parity_error", scalar=True),
        ))

        mode = p["smid_mode"].upper()
        settings = {
            "PROTOCOL": "AXI4", "READ_WRITE_MODE": "READ_WRITE",
            "ADDR_WIDTH": 32, "DATA_WIDTH": p["data_width"],
            "S_ID_WIDTH": p["id_width"],
            "S_AWUSER_WIDTH": p["address_user_width"],
            "S_ARUSER_WIDTH": p["address_user_width"],
            "S_WUSER_BITS_PER_BYTE": 0, "S_RUSER_BITS_PER_BYTE": 0,
            "S_BUSER_WIDTH": 0, "SMID_MODE": mode,
            "MI_PARITY": "NONE", "SI_PARITY": "NONE",
        }
        if mode != "BYPASS":
            settings["SMID_WIDTH"] = p["smid_width"]
        if mode == "INSERT":
            settings["SMID_VALUE"] = f"0x{p['smid_value']:08X}"
        effective_smid_width = 6 if mode == "BYPASS" else p["smid_width"]
        effective_smid_value = p["smid_value"] if mode == "INSERT" else 0
        model_parameters = {
            "C_PROTOCOL": 0, "C_ADDR_WIDTH": 32,
            "C_RDATA_WIDTH": p["data_width"], "C_WDATA_WIDTH": p["data_width"],
            "C_S_ID_WIDTH": p["id_width"],
            "C_S_AWUSER_WIDTH": p["address_user_width"],
            "C_S_ARUSER_WIDTH": p["address_user_width"],
            "C_M_ID_WIDTH": p["id_width"],
            "C_M_AWUSER_WIDTH": output_user_width,
            "C_M_ARUSER_WIDTH": output_user_width,
            "C_INSERT_SMID": int(mode == "INSERT"),
            "C_EXTRACT_SMID": 0, "C_REMOVE_SMID": int(mode == "REMOVE"),
            "C_SMID_WIDTH": effective_smid_width,
            "C_SMID_VALUE": f"0x{effective_smid_value:08X}",
            "C_MI_PARITY": 0, "C_SI_PARITY": 0,
        }
        parameters = dict(p)
        return CycleSpec(
            inputs=tuple(inputs), outputs=tuple(outputs), settings=settings,
            model_parameters=model_parameters,
            model_factory=lambda: AxiSidebandUtilModel(parameters), clock="aclk",
            prefix=lambda: directed_sequence(parameters), flush_cycles=2,
            neutral={"aresetn": 1, "aclken": 1}, combine_scalar_controls=False,
        )
