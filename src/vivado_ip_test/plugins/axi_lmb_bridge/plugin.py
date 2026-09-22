from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.axi_lmb_bridge.testbench import AxiLmbTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.vectors import port_space


DATA_WIDTHS = {32, 64}
ADDRESS_WIDTHS = {32, 40, 64}
ID_WIDTHS = {1, 4, 8, 16}
PROTOCOLS = {"Standard": 0, "Frequency": 1}


class AxiLmbBridgePlugin:
    ip_type = "axi_lmb_bridge"
    ip_name = "axi_lmb_bridge"
    version = "1.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxiLmbTestbenchBackend(layout, strategy_registry)

    def generated_ports(self, p):
        return (Port("sample_address", p["address_width"]),
                Port("sample_data", p["data_width"]),
                Port("sample_strobe", p["data_width"] // 8),
                Port("sample_id", p["id_width"]), Port("sample_prot", 3),
                Port("sample_wait", 2))

    def describe(self, p):
        validate_parameters(p, {"data_width": range(32, 65),
            "address_width": range(32, 65), "id_width": range(1, 17),
            "use_pause": bool, "lmb_protocol": set(PROTOCOLS), "protection": bool})
        if p["data_width"] not in DATA_WIDTHS:
            raise PluginError("AXI to LMB Bridge 数据位宽只接入 32 或 64")
        if p["address_width"] not in ADDRESS_WIDTHS:
            raise PluginError("AXI to LMB Bridge 地址位宽只接入 32、40 或 64")
        if p["id_width"] not in ID_WIDTHS:
            raise PluginError("AXI to LMB Bridge ID 位宽只接入 1、4、8 或 16")
        settings = {"C_DATA_WIDTH": p["data_width"], "C_ADDR_WIDTH": p["address_width"],
            "C_AXI_AW_DEPTH": 2, "C_AXI_W_DEPTH": 8, "C_AXI_AR_DEPTH": 2,
            "C_AXI_R_DEPTH": 8, "C_AXI_ID_WIDTH": p["id_width"],
            "C_USE_PAUSE": int(p["use_pause"]),
            "C_LMB_PROTOCOL": PROTOCOLS[p["lmb_protocol"]],
            "C_LMB_HAS_PROT": int(p["protection"])}
        inputs = [Port("Rst", scalar=True), Port("S_AXI_AWID", p["id_width"]),
            Port("S_AXI_AWADDR", p["address_width"]), Port("S_AXI_AWLEN", 8),
            Port("S_AXI_AWSIZE", 3), Port("S_AXI_AWBURST", 2),
            Port("S_AXI_AWVALID", scalar=True), Port("S_AXI_AWPROT", 3),
            Port("S_AXI_WDATA", p["data_width"]), Port("S_AXI_WSTRB", p["data_width"] // 8),
            Port("S_AXI_WLAST", scalar=True), Port("S_AXI_WVALID", scalar=True),
            Port("S_AXI_BREADY", scalar=True), Port("S_AXI_ARID", p["id_width"]),
            Port("S_AXI_ARADDR", p["address_width"]), Port("S_AXI_ARLEN", 8),
            Port("S_AXI_ARSIZE", 3), Port("S_AXI_ARBURST", 2),
            Port("S_AXI_ARVALID", scalar=True), Port("S_AXI_ARPROT", 3),
            Port("S_AXI_RREADY", scalar=True), Port("LMB_ReadDBus", p["data_width"]),
            Port("LMB_Ready", scalar=True), Port("LMB_Wait", scalar=True),
            Port("LMB_CE", scalar=True), Port("LMB_UE", scalar=True)]
        outputs = [Port("S_AXI_AWREADY", scalar=True), Port("S_AXI_WREADY", scalar=True),
            Port("S_AXI_BRESP", 2), Port("S_AXI_BID", p["id_width"]),
            Port("S_AXI_BVALID", scalar=True), Port("S_AXI_ARREADY", scalar=True),
            Port("S_AXI_RID", p["id_width"]), Port("S_AXI_RDATA", p["data_width"]),
            Port("S_AXI_RRESP", 2), Port("S_AXI_RLAST", scalar=True),
            Port("S_AXI_RVALID", scalar=True), Port("M_ABus", p["address_width"]),
            Port("M_DBus", p["data_width"]), Port("M_AddrStrobe", scalar=True),
            Port("M_ReadStrobe", scalar=True), Port("M_WriteStrobe", scalar=True),
            Port("M_BE", p["data_width"] // 8), Port("M_Prot", 2)]
        if p["use_pause"]:
            inputs.append(Port("Pause", scalar=True))
            outputs.append(Port("Pause_Ack", scalar=True))
        return CycleSpec(tuple(inputs), tuple(outputs), settings, dict(settings),
                         lambda: None, clock="Clk")

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXI to LMB Bridge IP 标识不匹配")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("AXI to LMB Bridge 未接入官方 demo")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError("AXI to LMB Bridge 覆盖目标不受支持")
        self.describe(case.parameters)
        space = port_space(self.generated_ports(case.parameters),
                           case.verification.boundary_mode == "systematic")
        budget = case.verification.case_budget
        if case.verification.strategy == "exhaustive":
            if budget < space.total_case_count:
                raise PluginError("AXI to LMB Bridge 穷举预算不足")
        elif not len(space.directed_cases) <= budget <= space.total_case_count:
            raise PluginError(f"AXI to LMB Bridge 预算需在 {len(space.directed_cases)} "
                              f"到 {space.total_case_count} 之间")

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AXI to LMB Bridge IP creation:",
            source_path=self._layout.tcl_path("ip/axi_lmb_bridge/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)),
                *(item for key, value in spec.settings.items()
                  for item in (f"CONFIG.{key}", str(value)))),
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="Configured IP generated successfully.", artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters),
                                      self.generated_ports(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXI to LMB Bridge 不支持阶段：{stage}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AXI to LMB Bridge behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_axi_lmb_selfcheck.vhd",
            top_name="tb_axi_lmb_selfcheck", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXI_LMB_SELF_CHECK_STATUS: PASS",
            failure_markers=("AXI_LMB_SELF_CHECK_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXI to LMB Bridge 不支持阶段：{stage}")
        run = self._layout.case_run_dir(case)
        return (Status.PASS if output_files_match(run / "vectors/expected_output.txt",
                run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED)
