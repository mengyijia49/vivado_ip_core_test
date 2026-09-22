from dataclasses import dataclass

from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.ahblite_axi_bridge.testbench import AhbLiteAxiTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.metadata import setting_text


DATA_WIDTHS = {32, 64}
ADDRESS_WIDTHS = {32, 40, 64}
ID_WIDTHS = {1, 4, 8, 16}
TIMEOUTS = {0, 32, 64, 128, 256}
STALLS = {0, 1, 3, 7}
DELAYS = {0, 1, 4, 8}


@dataclass(frozen=True)
class AhbLiteAxiSpec:
    metadata: CycleSpec
    settings: dict[str, object]
    parameters: dict[str, object]


def _metadata_ports(p):
    data, addr, ident, lanes = p["data_width"], p["address_width"], p["id_width"], p["data_width"] // 8
    s = lambda name: Port(name, scalar=True)
    v = lambda name, width: Port(name, width)
    inputs = (s("s_ahb_hresetn"), s("s_ahb_hsel"), v("s_ahb_haddr", addr),
        v("s_ahb_hprot", 4), v("s_ahb_htrans", 2), v("s_ahb_hsize", 3),
        s("s_ahb_hwrite"), v("s_ahb_hburst", 3), v("s_ahb_hwdata", data),
        s("s_ahb_hready_in"), s("m_axi_awready"), s("m_axi_wready"),
        v("m_axi_bid", ident), v("m_axi_bresp", 2), s("m_axi_bvalid"),
        s("m_axi_arready"), v("m_axi_rid", ident), v("m_axi_rdata", data),
        v("m_axi_rresp", 2), s("m_axi_rvalid"), s("m_axi_rlast"))
    outputs = (s("s_ahb_hready_out"), v("s_ahb_hrdata", data), s("s_ahb_hresp"),
        v("m_axi_awid", ident), v("m_axi_awlen", 8), v("m_axi_awsize", 3),
        v("m_axi_awburst", 2), v("m_axi_awcache", 4), v("m_axi_awaddr", addr),
        v("m_axi_awprot", 3), s("m_axi_awvalid"), s("m_axi_awlock"),
        v("m_axi_wdata", data), v("m_axi_wstrb", lanes), s("m_axi_wlast"),
        s("m_axi_wvalid"), s("m_axi_bready"), v("m_axi_arid", ident),
        v("m_axi_arlen", 8), v("m_axi_arsize", 3), v("m_axi_arburst", 2),
        v("m_axi_arprot", 3), v("m_axi_arcache", 4), s("m_axi_arvalid"),
        v("m_axi_araddr", addr), s("m_axi_arlock"), s("m_axi_rready"))
    return inputs, outputs


class AhbLiteAxiBridgePlugin:
    ip_type = ip_name = "ahblite_axi_bridge"
    version = "3.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AhbLiteAxiTestbenchBackend(layout)

    def describe(self, p):
        validate_parameters(p, {"data_width": range(32, 65), "address_width": range(32, 65),
            "id_width": range(1, 17), "narrow_burst": bool, "non_secure": bool,
            "timeout_cycles": range(0, 257), "stall_cycles": range(0, 8),
            "response_delay_cycles": range(0, 9)})
        for name, allowed in (("data_width", DATA_WIDTHS), ("address_width", ADDRESS_WIDTHS),
                ("id_width", ID_WIDTHS), ("timeout_cycles", TIMEOUTS),
                ("stall_cycles", STALLS), ("response_delay_cycles", DELAYS)):
            if p[name] not in allowed:
                raise PluginError(f"AHB-Lite to AXI Bridge 参数 {name} 不受支持")
        if p["timeout_cycles"] and p["stall_cycles"] + p["response_delay_cycles"] + 8 >= p["timeout_cycles"]:
            raise PluginError("测试端延迟必须明显小于桥接器超时值")
        settings = {"C_S_AHB_DATA_WIDTH": p["data_width"],
            "C_EXTENDED_ADDRESS_WIDTH": p["address_width"],
            "C_M_AXI_THREAD_ID_WIDTH": p["id_width"],
            "C_M_AXI_SUPPORTS_NARROW_BURST": int(p["narrow_burst"]),
            "C_M_AXI_NON_SECURE": int(p["non_secure"]),
            "C_AHB_AXI_TIMEOUT": p["timeout_cycles"]}
        models = {"C_FAMILY": "artix7", "C_INSTANCE": "dut_0",
            "C_M_AXI_SUPPORTS_NARROW_BURST": int(p["narrow_burst"]),
            "C_M_AXI_NON_SECURE": int(p["non_secure"]),
            "C_S_AHB_ADDR_WIDTH": p["address_width"], "C_M_AXI_ADDR_WIDTH": p["address_width"],
            "C_S_AHB_DATA_WIDTH": p["data_width"], "C_M_AXI_DATA_WIDTH": p["data_width"],
            "C_M_AXI_PROTOCOL": "AXI4", "C_M_AXI_THREAD_ID_WIDTH": p["id_width"],
            "C_AHB_AXI_TIMEOUT": p["timeout_cycles"]}
        inputs, outputs = _metadata_ports(p)
        metadata = CycleSpec(inputs, outputs, settings, models, lambda: None, clock="s_ahb_hclk")
        return AhbLiteAxiSpec(metadata, settings, dict(p))

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AHB-Lite to AXI Bridge IP 标识不匹配")
        if tuple(case.stages) != (Stage.CREATE_IP, Stage.GENERATE_TESTBENCH, Stage.SIM_SELFCHECK):
            raise PluginError("AHB-Lite to AXI Bridge 只支持创建、自检生成和行为仿真")
        if set(case.verification.coverage_targets) - {"port_boundaries"}:
            raise PluginError("AHB-Lite to AXI Bridge 仅支持 port_boundaries")
        if not 16 <= case.verification.case_budget <= 4096:
            raise PluginError("AHB-Lite to AXI Bridge 向量预算需为 16 到 4096")
        self.describe(case.parameters)

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AHB-Lite to AXI Bridge IP creation:",
            source_path=self._layout.tcl_path("ip/ahblite_axi_bridge/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)), *(item for key, value in spec.settings.items()
                for item in (f"CONFIG.{key}", setting_text(value)))), log_path=log,
            journal_path=log.with_suffix(".jou"), success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AHB-Lite to AXI Bridge 不支持阶段：{stage}")
        run, log = self._layout.case_run_dir(case), self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AHB-Lite to AXI Bridge behavioral self-check:",
            project_path=run / "proj/ip_test.xpr", testbench_path=run / "tb/tb_ahblite_axi_bridge.vhd",
            top_name="tb_ahblite_axi_bridge", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AHBLITE_AXI_STATUS: PASS", failure_markers=("AHBLITE_AXI_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
