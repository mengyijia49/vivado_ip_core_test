from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.domain.counts import count_for_report
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.metadata import setting_text
from vivado_ip_test.plugins.common.testbench import CycleTestbenchBackend
from vivado_ip_test.plugins.common.vectors import cycle_space


class CycleIpPlugin:
    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = CycleTestbenchBackend(layout, strategy_registry)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError(f"{case.case_id} 的 vendor 或 ip_name 不匹配")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError(f"{self.ip_type} 尚未接入官方 demo")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError(f"{self.ip_type} 仅支持 port_boundaries、complete_input_space")
        spec = self.describe(case.parameters)
        space = cycle_space(spec, case.verification.boundary_mode == "systematic")
        budget = case.verification.case_budget
        if case.verification.strategy == "exhaustive":
            if budget < space.total_case_count:
                raise PluginError("穷举预算不足以覆盖单周期输入空间")
        elif not len(space.directed_cases) <= budget <= space.total_case_count:
            raise PluginError(f"{case.case_id} 预算需在 {len(space.directed_cases)} 到 "
                              f"{count_for_report(space.total_case_count)} 之间")

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(
            description=f"Running {self.ip_type} IP creation:",
            source_path=self._layout.tcl_path(f"ip/{self.ip_type}/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)),
                     *(item for key, value in spec.settings.items()
                       for item in (f"CONFIG.{key}", setting_text(value)))),
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="Configured IP generated successfully.",
            artifact_glob=getattr(spec, "inline_bd_glob", None) or getattr(spec, "xci_glob", "**/dut_0.xci"),
            missing_artifact_status=(Status.BLOCK_DESIGN_NOT_FOUND if getattr(spec, "inline_bd_glob", None)
                                     else Status.XCI_NOT_FOUND),
        )

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters), self.ip_name, self.version)

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"不支持的仿真阶段：{stage}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(
            description=f"Running {self.ip_type} cycle self-check:",
            project_path=run / "proj" / "ip_test.xpr",
            testbench_path=run / "tb" / "tb_cycle_selfcheck.vhd", top_name="tb_cycle_selfcheck",
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="CYCLE_SELF_CHECK_STATUS: PASS",
            failure_markers=("CYCLE_SELF_CHECK_STATUS: FAIL",), failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"不支持的仿真阶段：{stage}")
        run = self._layout.case_run_dir(case)
        masked = getattr(self.describe(case.parameters), "masked_outputs", False)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
                run / "outputs/actual_output.txt", mask_path=run / "vectors/expected_mask.txt" if masked else None
                ) else Status.VERIFICATION_FAILED
