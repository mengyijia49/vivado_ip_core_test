from vivado_ip_test.plugins.axi_apb_bridge.harness import apb_harness
from vivado_ip_test.plugins.axi_apb_bridge.reference import AxiApbBridgeModel, REGION_BYTES
from vivado_ip_test.plugins.axi_apb_bridge.vectors import prepare_operations
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters


SLAVE_COUNTS = (1, 2, 4, 8, 16)
ADDRESS_WIDTHS = (16, 20, 32)


def _address_settings(parameters):
    settings = {}
    for index in range(parameters["num_slaves"]):
        base = parameters["base_address"] + index * REGION_BYTES
        high = base + REGION_BYTES - 1
        prefix = "" if index == 0 else f"S_AXI_RNG{index+1}_"
        settings[f"C_{prefix}BASEADDR"] = f"0x{base:016X}"
        settings[f"C_{prefix}HIGHADDR"] = f"0x{high:016X}"
    return settings


class AxiApbBridgePlugin(AxiLiteIpPlugin):
    ip_type = ip_name = "axi_apb_bridge"
    version = "3.0"

    def describe(self, p):
        validate_parameters(p, {
            "address_width": range(1, 65), "num_slaves": range(1, 17),
            "base_address": range(0, 1 << 32), "wait_cycles": range(0, 5),
            "error_response": bool,
        })
        if p["address_width"] not in ADDRESS_WIDTHS:
            raise PluginError("AXI APB Bridge 地址宽度只接入 16、20、32")
        if p["num_slaves"] not in SLAVE_COUNTS:
            raise PluginError("AXI APB Bridge 从设备数量只接入 1、2、4、8、16")
        if p["base_address"] % REGION_BYTES:
            raise PluginError("AXI APB Bridge 基地址必须按 4 KiB 对齐")
        if p["base_address"] + p["num_slaves"] * REGION_BYTES > 1 << p["address_width"]:
            raise PluginError("AXI APB Bridge 地址窗口超出配置位宽")

        address_settings = _address_settings(p)
        settings = {"C_ADDR_WIDTH": p["address_width"],
                    "C_APB_NUM_SLAVES": p["num_slaves"],
                    "C_M_APB_PROTOCOL": "apb4", **address_settings}
        models = {"C_S_AXI_ADDR_WIDTH": p["address_width"],
                  "C_S_AXI_DATA_WIDTH": 32,
                  "C_M_APB_ADDR_WIDTH": p["address_width"],
                  "C_M_APB_DATA_WIDTH": 32,
                  "C_APB_NUM_SLAVES": p["num_slaves"],
                  "C_M_APB_PROTOCOL": "apb4", **address_settings,
                  "C_DPHASE_TIMEOUT": 0}
        inputs = [
            Port("s_axi_aresetn", scalar=True), Port("s_axi_awaddr", p["address_width"]),
            Port("s_axi_awprot", 3), Port("s_axi_awvalid", scalar=True),
            Port("s_axi_wdata", 32), Port("s_axi_wstrb", 4),
            Port("s_axi_wvalid", scalar=True), Port("s_axi_bready", scalar=True),
            Port("s_axi_araddr", p["address_width"]), Port("s_axi_arprot", 3),
            Port("s_axi_arvalid", scalar=True), Port("s_axi_rready", scalar=True),
            Port("m_apb_pready", p["num_slaves"]), Port("m_apb_prdata", 32),
        ]
        inputs.extend(Port(f"m_apb_prdata{index}", 32)
                      for index in range(2, p["num_slaves"] + 1))
        inputs.append(Port("m_apb_pslverr", p["num_slaves"]))
        outputs = (
            Port("s_axi_awready", scalar=True), Port("s_axi_wready", scalar=True),
            Port("s_axi_bresp", 2), Port("s_axi_bvalid", scalar=True),
            Port("s_axi_arready", scalar=True), Port("s_axi_rdata", 32),
            Port("s_axi_rresp", 2), Port("s_axi_rvalid", scalar=True),
            Port("m_apb_paddr", p["address_width"]), Port("m_apb_psel", p["num_slaves"]),
            Port("m_apb_penable", scalar=True), Port("m_apb_pwrite", scalar=True),
            Port("m_apb_pwdata", 32), Port("m_apb_pprot", 3), Port("m_apb_pstrb", 4),
        )
        metadata_spec = CycleSpec(
            inputs=tuple(inputs), outputs=outputs, settings=settings, model_parameters=models,
            model_factory=lambda: None, clock="s_axi_aclk",
        )
        declarations, statements, mappings = apb_harness(p)
        slave_width = max(1, (p["num_slaves"] - 1).bit_length())
        generated = (
            Port("sample_slave", slave_width, maximum=p["num_slaves"] - 1),
            Port("sample_word", 8), Port("sample_data", 32),
            Port("sample_strobe", 4), Port("sample_prot", 3),
        )
        parameters = dict(p)
        return AxiLiteSpec(
            p["address_width"], (Port("s_axi_awprot", 3), Port("s_axi_arprot", 3)), (),
            generated, settings, models, lambda: AxiApbBridgeModel(parameters),
            lambda rows: prepare_operations(rows, parameters), settle_cycles=2,
            reset_cycles=20, minimum_ip_revision=21, metadata_spec=metadata_spec,
            extra_mappings=mappings, testbench_declarations=declarations,
            testbench_statements=statements,
        )
