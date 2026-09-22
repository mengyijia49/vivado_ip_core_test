from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.axi_protocol_converter.testbench import AxiProtocolConverterTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.vectors import port_space


DATA_WIDTHS = {32, 64}
ADDRESS_WIDTHS = {12, 32, 64}
ID_WIDTHS = {1, 4, 8, 16, 32}
BURST_LENGTHS = {1, 2, 4, 8, 16}
STALL_CYCLES = {0, 1, 2, 4}


class AxiProtocolConverterPlugin:
    ip_type = ip_name = "axi_protocol_converter"
    version = "2.1"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxiProtocolConverterTestbenchBackend(layout, strategy_registry)

    def generated_ports(self, p):
        return (Port("sample_address", p["address_width"]),
                Port("sample_data", p["data_width"]),
                Port("sample_strobe", p["data_width"] // 8),
                Port("sample_id", p["id_width"]), Port("sample_prot", 3))

    def describe(self, p):
        validate_parameters(p, {"data_width": range(32, 1025),
            "address_width": range(12, 65), "id_width": range(1, 33),
            "burst_length": range(1, 17), "downstream_stall_cycles": range(0, 5)})
        if p["data_width"] not in DATA_WIDTHS:
            raise PluginError("AXI Protocol Converter 数据位宽不受支持")
        if p["address_width"] not in ADDRESS_WIDTHS:
            raise PluginError("AXI Protocol Converter 地址位宽不受支持")
        if p["id_width"] not in ID_WIDTHS:
            raise PluginError("AXI Protocol Converter ID 位宽不受支持")
        if p["burst_length"] not in BURST_LENGTHS:
            raise PluginError("AXI Protocol Converter burst 长度不受支持")
        if p["downstream_stall_cycles"] not in STALL_CYCLES:
            raise PluginError("AXI Protocol Converter 下游停顿长度不受支持")
        settings = {"SI_PROTOCOL": "AXI4", "MI_PROTOCOL": "AXI4LITE",
            "READ_WRITE_MODE": "READ_WRITE", "TRANSLATION_MODE": 2,
            "ADDR_WIDTH": p["address_width"], "DATA_WIDTH": p["data_width"],
            "ID_WIDTH": p["id_width"], "AWUSER_WIDTH": 0, "ARUSER_WIDTH": 0,
            "RUSER_WIDTH": 0, "WUSER_WIDTH": 0, "BUSER_WIDTH": 0}
        models = {"C_M_AXI_PROTOCOL": 2, "C_S_AXI_PROTOCOL": 0, "C_IGNORE_ID": 0,
            "C_AXI_ID_WIDTH": p["id_width"], "C_AXI_ADDR_WIDTH": p["address_width"],
            "C_AXI_DATA_WIDTH": p["data_width"], "C_AXI_SUPPORTS_WRITE": 1,
            "C_AXI_SUPPORTS_READ": 1, "C_AXI_SUPPORTS_USER_SIGNALS": 0,
            "C_AXI_AWUSER_WIDTH": 1, "C_AXI_ARUSER_WIDTH": 1,
            "C_AXI_WUSER_WIDTH": 1, "C_AXI_RUSER_WIDTH": 1,
            "C_AXI_BUSER_WIDTH": 1, "C_TRANSLATION_MODE": 2}
        inputs = [Port("aresetn", scalar=True), Port("s_axi_awid", p["id_width"]),
            Port("s_axi_awaddr", p["address_width"]), Port("s_axi_awlen", 8),
            Port("s_axi_awsize", 3), Port("s_axi_awburst", 2), Port("s_axi_awlock", 1),
            Port("s_axi_awcache", 4), Port("s_axi_awprot", 3), Port("s_axi_awregion", 4),
            Port("s_axi_awqos", 4), Port("s_axi_awvalid", scalar=True),
            Port("s_axi_wdata", p["data_width"]), Port("s_axi_wstrb", p["data_width"] // 8),
            Port("s_axi_wlast", scalar=True), Port("s_axi_wvalid", scalar=True),
            Port("s_axi_bready", scalar=True), Port("s_axi_arid", p["id_width"]),
            Port("s_axi_araddr", p["address_width"]), Port("s_axi_arlen", 8),
            Port("s_axi_arsize", 3), Port("s_axi_arburst", 2), Port("s_axi_arlock", 1),
            Port("s_axi_arcache", 4), Port("s_axi_arprot", 3), Port("s_axi_arregion", 4),
            Port("s_axi_arqos", 4), Port("s_axi_arvalid", scalar=True),
            Port("s_axi_rready", scalar=True), Port("m_axi_awready", scalar=True),
            Port("m_axi_wready", scalar=True), Port("m_axi_bresp", 2),
            Port("m_axi_bvalid", scalar=True), Port("m_axi_arready", scalar=True),
            Port("m_axi_rdata", p["data_width"]), Port("m_axi_rresp", 2),
            Port("m_axi_rvalid", scalar=True)]
        outputs = [Port("s_axi_awready", scalar=True), Port("s_axi_wready", scalar=True),
            Port("s_axi_bid", p["id_width"]), Port("s_axi_bresp", 2),
            Port("s_axi_bvalid", scalar=True), Port("s_axi_arready", scalar=True),
            Port("s_axi_rid", p["id_width"]), Port("s_axi_rdata", p["data_width"]),
            Port("s_axi_rresp", 2), Port("s_axi_rlast", scalar=True),
            Port("s_axi_rvalid", scalar=True), Port("m_axi_awaddr", p["address_width"]),
            Port("m_axi_awprot", 3), Port("m_axi_awvalid", scalar=True),
            Port("m_axi_wdata", p["data_width"]), Port("m_axi_wstrb", p["data_width"] // 8),
            Port("m_axi_wvalid", scalar=True), Port("m_axi_bready", scalar=True),
            Port("m_axi_araddr", p["address_width"]), Port("m_axi_arprot", 3),
            Port("m_axi_arvalid", scalar=True), Port("m_axi_rready", scalar=True)]
        return CycleSpec(tuple(inputs), tuple(outputs), settings, models, lambda: None, clock="aclk")

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXI Protocol Converter IP 标识不匹配")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("AXI Protocol Converter 未接入官方 demo")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError("AXI Protocol Converter 覆盖目标不受支持")
        self.describe(case.parameters)
        space = port_space(self.generated_ports(case.parameters),
                           case.verification.boundary_mode == "systematic")
        budget = case.verification.case_budget
        if not len(space.directed_cases) <= budget <= space.total_case_count:
            raise PluginError("AXI Protocol Converter 向量预算不在有效范围")

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AXI Protocol Converter IP creation:",
            source_path=self._layout.tcl_path("ip/axi_protocol_converter/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)), *(item for key, value in spec.settings.items()
                for item in (f"CONFIG.{key}", str(value)))), log_path=log,
            journal_path=log.with_suffix(".jou"), success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters),
                                      self.generated_ports(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXI Protocol Converter 不支持阶段：{stage}")
        run, log = self._layout.case_run_dir(case), self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AXI Protocol Converter behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_axi_protocol_converter.vhd",
            top_name="tb_axi_protocol_converter", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXI_PROTOCOL_CONVERTER_STATUS: PASS",
            failure_markers=("AXI_PROTOCOL_CONVERTER_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
