from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.axi_clock_converter.reference import AxiClockConverterReference
from vivado_ip_test.plugins.axi_clock_converter.testbench import AxiClockConverterTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.vectors import port_space


DATA_WIDTHS = {32, 64, 128, 256, 512, 1024}
ADDRESS_WIDTHS = {32, 40, 64}
ID_WIDTHS = {1, 4, 8, 16, 32}
USER_WIDTHS = {1, 8, 32, 128, 1024}
OUTPUT_PERIODS = {6, 10, 14, 20, 30}


class AxiClockConverterPlugin:
    ip_type = ip_name = "axi_clock_converter"
    version = "2.1"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxiClockConverterTestbenchBackend(layout, strategy_registry)

    def generated_ports(self, p):
        return (Port("sample_channel", 3, maximum=4), Port("sample_id", p["id_width"]),
                Port("sample_address", p["address_width"]), Port("sample_data", p["data_width"]),
                Port("sample_user", p["user_width"]), Port("sample_hold", 2))

    def describe(self, p):
        validate_parameters(p, {"data_width": range(32, 1025), "address_width": range(1, 65),
            "id_width": range(1, 33), "user_width": range(1, 1025),
            "synchronization_stages": range(2, 9), "output_period_ns": range(6, 31)})
        for key, supported in (("data_width", DATA_WIDTHS), ("address_width", ADDRESS_WIDTHS),
                               ("id_width", ID_WIDTHS), ("user_width", USER_WIDTHS)):
            if p[key] not in supported:
                raise PluginError(f"AXI Clock Converter 参数 {key} 不受支持")
        if p["output_period_ns"] not in OUTPUT_PERIODS:
            raise PluginError("AXI Clock Converter 输出时钟周期不受支持")
        settings = {"PROTOCOL": "AXI4", "READ_WRITE_MODE": "READ_WRITE",
            "ADDR_WIDTH": p["address_width"], "DATA_WIDTH": p["data_width"],
            "ID_WIDTH": p["id_width"], "AWUSER_WIDTH": p["user_width"],
            "ARUSER_WIDTH": p["user_width"], "WUSER_WIDTH": p["user_width"],
            "RUSER_WIDTH": p["user_width"], "BUSER_WIDTH": p["user_width"],
            "ACLK_ASYNC": 1, "SYNCHRONIZATION_STAGES": p["synchronization_stages"]}
        models = {"C_AXI_PROTOCOL": 0, "C_AXI_ID_WIDTH": p["id_width"],
            "C_AXI_ADDR_WIDTH": p["address_width"], "C_AXI_DATA_WIDTH": p["data_width"],
            "C_AXI_IS_ACLK_ASYNC": 1, "C_AXI_SUPPORTS_USER_SIGNALS": 1,
            "C_AXI_AWUSER_WIDTH": p["user_width"], "C_AXI_ARUSER_WIDTH": p["user_width"],
            "C_AXI_WUSER_WIDTH": p["user_width"], "C_AXI_RUSER_WIDTH": p["user_width"],
            "C_AXI_BUSER_WIDTH": p["user_width"], "C_AXI_SUPPORTS_WRITE": 1,
            "C_AXI_SUPPORTS_READ": 1, "C_SYNCHRONIZER_STAGE": p["synchronization_stages"]}
        address = (("id", p["id_width"]), ("addr", p["address_width"]), ("len", 8),
            ("size", 3), ("burst", 2), ("lock", 1), ("cache", 4), ("prot", 3),
            ("region", 4), ("qos", 4), ("user", p["user_width"]))
        fields = {"aw": address, "w": (("data", p["data_width"]),
            ("strb", p["data_width"] // 8), ("last", 1), ("user", p["user_width"])),
            "b": (("id", p["id_width"]), ("resp", 2), ("user", p["user_width"])),
            "ar": address, "r": (("id", p["id_width"]), ("data", p["data_width"]),
                ("resp", 2), ("last", 1), ("user", p["user_width"]))}
        inputs = [Port("s_axi_aclk", scalar=True), Port("s_axi_aresetn", scalar=True),
                  Port("m_axi_aclk", scalar=True), Port("m_axi_aresetn", scalar=True)]
        outputs = []
        for channel in ("aw", "w", "ar"):
            inputs.extend(Port(f"s_axi_{channel}{name}", width, scalar=name == "last")
                          for name, width in fields[channel])
            inputs.extend((Port(f"s_axi_{channel}valid", scalar=True),
                           Port(f"m_axi_{channel}ready", scalar=True)))
            outputs.extend(Port(f"m_axi_{channel}{name}", width, scalar=name == "last")
                           for name, width in fields[channel])
            outputs.extend((Port(f"m_axi_{channel}valid", scalar=True),
                            Port(f"s_axi_{channel}ready", scalar=True)))
        for channel in ("b", "r"):
            inputs.extend(Port(f"m_axi_{channel}{name}", width, scalar=name == "last")
                          for name, width in fields[channel])
            inputs.extend((Port(f"m_axi_{channel}valid", scalar=True),
                           Port(f"s_axi_{channel}ready", scalar=True)))
            outputs.extend(Port(f"s_axi_{channel}{name}", width, scalar=name == "last")
                           for name, width in fields[channel])
            outputs.extend((Port(f"s_axi_{channel}valid", scalar=True),
                            Port(f"m_axi_{channel}ready", scalar=True)))
        return CycleSpec(inputs=tuple(inputs), outputs=tuple(outputs), settings=settings,
            model_parameters=models, model_factory=lambda: AxiClockConverterReference(), clock=None)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXI Clock Converter IP 标识不匹配")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("AXI Clock Converter 未接入官方 demo")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError("AXI Clock Converter 覆盖目标不受支持")
        self.describe(case.parameters)
        space = port_space(self.generated_ports(case.parameters),
                           case.verification.boundary_mode == "systematic")
        budget = case.verification.case_budget
        if not len(space.directed_cases) <= budget <= space.total_case_count:
            raise PluginError("AXI Clock Converter 向量预算不在有效范围")

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AXI Clock Converter IP creation:",
            source_path=self._layout.tcl_path("ip/axi_clock_converter/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)), *(item for key, value in spec.settings.items()
                for item in (f"CONFIG.{key}", str(value)))), log_path=log,
            journal_path=log.with_suffix(".jou"), success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters),
                                      self.generated_ports(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXI Clock Converter 不支持阶段：{stage}")
        run, log = self._layout.case_run_dir(case), self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AXI Clock Converter behavioral self-check:",
            project_path=run / "proj/ip_test.xpr", testbench_path=run / "tb/tb_axi_clock_converter.vhd",
            top_name="tb_axi_clock_converter", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXI_CLOCK_CONVERTER_STATUS: PASS",
            failure_markers=("AXI_CLOCK_CONVERTER_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
