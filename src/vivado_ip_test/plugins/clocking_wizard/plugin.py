from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.clocking_wizard.reference import ClockPlan
from vivado_ip_test.plugins.clocking_wizard.testbench import ClockingWizardTestbenchBackend
from vivado_ip_test.plugins.common.cycle import validate_parameters


class ClockingWizardPlugin:
    ip_type = "clocking_wizard"
    ip_name = "clk_wiz"
    version = "6.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = ClockingWizardTestbenchBackend(layout)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError(f"{case.case_id} 的 vendor 或 ip_name 不匹配")
        validate_parameters(case.parameters, {
            "input_frequency_mhz": range(10, 801),
            "output_frequency_mhz": range(5, 801),
            "primitive": {"MMCM", "PLL"},
            "reset_active_high": bool,
        })
        if case.parameters["input_frequency_mhz"] not in {50, 100, 200}:
            raise PluginError("当前输入频率只支持 50、100、200 MHz")
        if case.parameters["output_frequency_mhz"] not in {25, 50, 100, 125, 200}:
            raise PluginError("当前输出频率不在已验证集合中")
        if (case.parameters["primitive"] == "PLL"
                and case.parameters["output_frequency_mhz"] not in {50, 100, 200}):
            raise PluginError("当前 PLL 配置只使用已验证能精确产生的 50、100、200 MHz")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("Clocking Wizard 尚未接入官方示例")
        if set(case.verification.coverage_targets) != {"clock_period", "lock_reset_recovery"}:
            raise PluginError("Clocking Wizard 需要 clock_period 和 lock_reset_recovery 覆盖目标")
        if case.verification.case_budget != 1:
            raise PluginError("Clocking Wizard 的每组配置预算固定为 1 个时钟计划")
        ClockPlan.from_parameters(case.parameters)

    def build_request(self, case):
        plan = ClockPlan.from_parameters(case.parameters)
        settings = self._backend.metadata_spec(plan).settings
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(
            description="Running Clocking Wizard IP creation:",
            source_path=self._layout.tcl_path("ip/clocking_wizard/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)),
                     *(item for key, value in settings.items()
                       for item in (f"CONFIG.{key}", str(value).lower() if isinstance(value, bool)
                                    else str(value)))),
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="Configured IP generated successfully.",
            artifact_glob="proj/*.srcs/sources_1/ip/dut_0/dut_0.xci",
        )

    def generate_testbench(self, case):
        return self._backend.generate(case)

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Clocking Wizard 不支持仿真阶段：{stage.value}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(
            description="Running Clocking Wizard self-check simulation:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_clocking_wizard_selfcheck.vhd",
            top_name="tb_clocking_wizard_selfcheck",
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="CLOCK_WIZARD_SELF_CHECK_STATUS: PASS",
            failure_markers=("CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Clocking Wizard 不支持仿真阶段：{stage.value}")
        run = self._layout.case_run_dir(case)
        expected = run / "vectors/expected_output.txt"
        actual = run / "outputs/actual_output.txt"
        if not expected.is_file() or not actual.is_file():
            return Status.VERIFICATION_FAILED
        return (Status.PASS if expected.read_bytes() == actual.read_bytes()
                else Status.VERIFICATION_FAILED)
