from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.axi_protocol_checker.testbench import AxiProtocolCheckerTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.vectors import port_space


DATA_WIDTHS = {32, 64, 128, 256, 512, 1024}
ADDRESS_WIDTHS = {32, 40, 64}
ID_WIDTHS = {1, 4, 8, 16, 32}
MAX_BURST_LENGTHS = {4, 8, 16, 32, 64, 128, 256}
MAX_OUTSTANDING = {2, 8, 32, 256}


class AxiProtocolCheckerPlugin:
    ip_type = ip_name = "axi_protocol_checker"
    version = "2.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxiProtocolCheckerTestbenchBackend(layout, strategy_registry)

    def generated_ports(self, p):
        return (Port("sample_id", p["id_width"]),
                Port("sample_address", p["address_width"]),
                Port("sample_data", p["data_width"]))

    def describe(self, p):
        validate_parameters(p, {"data_width": range(32, 1025),
            "address_width": range(32, 65), "id_width": range(1, 33),
            "max_burst_length": range(4, 257), "max_outstanding": range(2, 257),
            "supports_narrow_burst": bool, "check_error_response": bool})
        for key, value, allowed in (("data_width", p["data_width"], DATA_WIDTHS),
                ("address_width", p["address_width"], ADDRESS_WIDTHS),
                ("id_width", p["id_width"], ID_WIDTHS),
                ("max_burst_length", p["max_burst_length"], MAX_BURST_LENGTHS),
                ("max_outstanding", p["max_outstanding"], MAX_OUTSTANDING)):
            if value not in allowed:
                raise PluginError(f"AXI Protocol Checker 参数 {key} 不受支持")
        settings = {"PROTOCOL": "AXI4", "READ_WRITE_MODE": "READ_WRITE",
            "ADDR_WIDTH": p["address_width"], "DATA_WIDTH": p["data_width"],
            "ID_WIDTH": p["id_width"], "AWUSER_WIDTH": 0, "ARUSER_WIDTH": 0,
            "RUSER_WIDTH": 0, "WUSER_WIDTH": 0, "BUSER_WIDTH": 0,
            "MAX_RD_BURSTS": p["max_outstanding"], "MAX_WR_BURSTS": p["max_outstanding"],
            "HAS_SYSTEM_RESET": 0, "MAX_AW_WAITS": 0, "MAX_AR_WAITS": 0,
            "MAX_W_WAITS": 0, "MAX_R_WAITS": 0, "MAX_B_WAITS": 0,
            "MAX_CONTINUOUS_WTRANSFERS_WAITS": 0, "MAX_WLAST_TO_AWVALID_WAITS": 0,
            "MAX_WRITE_TO_BVALID_WAITS": 0, "MAX_CONTINUOUS_RTRANSFERS_WAITS": 0,
            "MESSAGE_LEVEL": 0, "SUPPORTS_NARROW_BURST": int(p["supports_narrow_burst"]),
            "MAX_BURST_LENGTH": p["max_burst_length"], "LIGHT_WEIGHT": 0,
            "PC_MASTER_SIDE": 0, "ENABLE_CONTROL": 0,
            "ENABLE_MARK_DEBUG": 0, "CHK_ERR_RESP": int(p["check_error_response"]),
            "HAS_WSTRB": 1}
        models = {"C_AXI_PROTOCOL": 0, "C_AXI_ID_WIDTH": p["id_width"],
            "C_AXI_DATA_WIDTH": p["data_width"], "C_AXI_ADDR_WIDTH": p["address_width"],
            "C_AXI_AWUSER_WIDTH": 1, "C_AXI_ARUSER_WIDTH": 1,
            "C_AXI_WUSER_WIDTH": 1, "C_AXI_RUSER_WIDTH": 1,
            "C_AXI_BUSER_WIDTH": 1, "C_HAS_WSTRB": 1,
            "C_PC_MAXRBURSTS": p["max_outstanding"],
            "C_PC_MAXWBURSTS": p["max_outstanding"], "C_PC_LIGHT_WEIGHT": 0,
            "C_PC_MASTER_SIDE": 0, "C_PC_MESSAGE_LEVEL": 0,
            "C_PC_SUPPORTS_NARROW_BURST": int(p["supports_narrow_burst"]),
            "C_PC_MAX_BURST_LENGTH": p["max_burst_length"], "C_ENABLE_CONTROL": 0,
            "C_PC_STATUS_WIDTH": 160, "C_CHK_ERR_RESP": int(p["check_error_response"]),
            "C_ENABLE_MARK_DEBUG": 0}
        lanes = p["data_width"] // 8
        inputs = [Port("aresetn", scalar=True), Port("pc_axi_awid", p["id_width"]),
            Port("pc_axi_awaddr", p["address_width"]), Port("pc_axi_awlen", 8),
            Port("pc_axi_awsize", 3), Port("pc_axi_awburst", 2), Port("pc_axi_awlock", 1),
            Port("pc_axi_awcache", 4), Port("pc_axi_awprot", 3), Port("pc_axi_awqos", 4),
            Port("pc_axi_awregion", 4), Port("pc_axi_awvalid", scalar=True),
            Port("pc_axi_awready", scalar=True), Port("pc_axi_wlast", scalar=True),
            Port("pc_axi_wdata", p["data_width"]), Port("pc_axi_wstrb", lanes),
            Port("pc_axi_wvalid", scalar=True), Port("pc_axi_wready", scalar=True),
            Port("pc_axi_bid", p["id_width"]), Port("pc_axi_bresp", 2),
            Port("pc_axi_bvalid", scalar=True), Port("pc_axi_bready", scalar=True),
            Port("pc_axi_arid", p["id_width"]), Port("pc_axi_araddr", p["address_width"]),
            Port("pc_axi_arlen", 8), Port("pc_axi_arsize", 3), Port("pc_axi_arburst", 2),
            Port("pc_axi_arlock", 1), Port("pc_axi_arcache", 4),
            Port("pc_axi_arprot", 3), Port("pc_axi_arqos", 4),
            Port("pc_axi_arregion", 4), Port("pc_axi_arvalid", scalar=True),
            Port("pc_axi_arready", scalar=True), Port("pc_axi_rid", p["id_width"]),
            Port("pc_axi_rlast", scalar=True), Port("pc_axi_rdata", p["data_width"]),
            Port("pc_axi_rresp", 2), Port("pc_axi_rvalid", scalar=True),
            Port("pc_axi_rready", scalar=True)]
        outputs = [Port("pc_status", 160), Port("pc_asserted", scalar=True)]
        return CycleSpec(tuple(inputs), tuple(outputs), settings, models, lambda: None, clock="aclk")

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXI Protocol Checker IP 标识不匹配")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("AXI Protocol Checker 未接入官方 demo")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError("AXI Protocol Checker 覆盖目标不受支持")
        self.describe(case.parameters)
        space = port_space(self.generated_ports(case.parameters),
                           case.verification.boundary_mode == "systematic")
        if not len(space.directed_cases) <= case.verification.case_budget <= space.total_case_count:
            raise PluginError("AXI Protocol Checker 向量预算不在有效范围")

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AXI Protocol Checker IP creation:",
            source_path=self._layout.tcl_path("ip/axi_protocol_checker/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)), *(item for key, value in spec.settings.items()
                for item in (f"CONFIG.{key}", str(value)))), log_path=log,
            journal_path=log.with_suffix(".jou"), success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters),
                                      self.generated_ports(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXI Protocol Checker 不支持阶段：{stage}")
        run, log = self._layout.case_run_dir(case), self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AXI Protocol Checker behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_axi_protocol_checker.vhd",
            top_name="tb_axi_protocol_checker", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXI_PROTOCOL_CHECKER_STATUS: PASS",
            failure_markers=("AXI_PROTOCOL_CHECKER_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
