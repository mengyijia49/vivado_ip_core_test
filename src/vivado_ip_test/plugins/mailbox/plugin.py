from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.mailbox.reference import AxisMailboxPlan, MailboxPlan, mailbox_plan
from vivado_ip_test.plugins.mailbox.testbench import MailboxTestbenchBackend


class MailboxPlugin:
    ip_type = ip_name = "mailbox"
    version = "2.1"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = MailboxTestbenchBackend(layout)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError(f"{case.case_id} 的 vendor 或 ip_name 不匹配")
        mode = case.parameters.get("interface_mode")
        if mode == "Axi4Lite":
            validate_parameters(case.parameters, {
                "interface_mode": ("Axi4Lite",), "depth": range(16, 8193),
                "memory_style": ("Distributed_RAM", "Block_RAM"),
                "enable_bus_error": bool, "registered_interrupts": bool,
            })
            wanted = {"bidirectional_fifo", "full_empty_errors", "fifo_clear",
                      "threshold_interrupts", "axi_backpressure"}
        elif mode == "Axis":
            validate_parameters(case.parameters, {
                "interface_mode": ("Axis",), "depth": range(16, 8193),
                "memory_style": ("Distributed_RAM", "Block_RAM"),
                "async_clocks": bool, "data_width": range(1, 1025),
            })
            wanted = {"bidirectional_stream", "tlast", "fifo_full_backpressure",
                      "output_backpressure", "concurrent_directions", "reset_flush"}
        else:
            raise PluginError(f"Mailbox 接口模式不受支持：{mode!r}")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("Mailbox 没有接入官方示例")
        if set(case.verification.coverage_targets) != wanted:
            raise PluginError("Mailbox 覆盖目标不完整")
        if case.verification.case_budget != 1:
            raise PluginError("Mailbox 每组配置使用一个确定性状态计划")
        mailbox_plan(case.parameters)

    def build_request(self, case):
        plan = mailbox_plan(case.parameters)
        settings = self._backend.metadata_spec(plan).settings
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(
            description="Running Mailbox IP creation:",
            source_path=self._layout.tcl_path("ip/mailbox/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)),
                     *(item for key, value in settings.items()
                       for item in (f"CONFIG.{key}", str(value)))),
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="Configured IP generated successfully.",
            artifact_glob="proj/*.srcs/sources_1/ip/dut_0/dut_0.xci",
        )

    def generate_testbench(self, case):
        return self._backend.generate(case)

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Mailbox 不支持仿真阶段：{stage.value}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        axis = isinstance(mailbox_plan(case.parameters), AxisMailboxPlan)
        return SimulationRequest(
            description="Running Mailbox behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb" / ("tb_mailbox_axis_selfcheck.vhd" if axis else "tb_mailbox_selfcheck.vhd"),
            top_name="tb_mailbox_axis_selfcheck" if axis else "tb_mailbox_selfcheck", log_path=log,
            journal_path=log.with_suffix(".jou"),
            success_marker="MAILBOX_AXIS_SELF_CHECK_STATUS: PASS" if axis else "MAILBOX_SELF_CHECK_STATUS: PASS",
            failure_markers=(("MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL" if axis else "MAILBOX_SELF_CHECK_STATUS: FAIL"),),
            failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Mailbox 不支持结果校验阶段：{stage.value}")
        run = self._layout.case_run_dir(case)
        expected = run / "vectors/expected_output.txt"
        actual = run / "outputs/actual_output.txt"
        if not expected.is_file() or not actual.is_file():
            return Status.VERIFICATION_FAILED
        return Status.PASS if expected.read_bytes() == actual.read_bytes() else Status.VERIFICATION_FAILED
