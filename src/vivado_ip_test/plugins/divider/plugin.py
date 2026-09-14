from vivado_ip_test.domain import (
    BuildRequest,
    SimulationRequest,
    Stage,
    Status,
    TestCase,
    TestbenchArtifacts,
)
from vivado_ip_test.infrastructure import RepositoryLayout, output_files_match
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.divider.testbench import DividerTestbenchBackend
from vivado_ip_test.strategies import StrategyRegistry


class DividerPlugin:
    ip_type = "divider"

    def __init__(
        self,
        layout: RepositoryLayout,
        strategy_registry: StrategyRegistry,
    ) -> None:
        self._layout = layout
        self._testbench_backend = DividerTestbenchBackend(layout, strategy_registry)

    def validate_case(self, case: TestCase) -> None:
        if case.vendor != "xilinx.com" or case.ip_name != "div_gen":
            raise PluginError(
                f"{case.case_id} 不是受支持的 Xilinx Divider Generator"
            )

        required = {"dividend_width", "divisor_width", "operand_sign"}
        missing = required - case.parameters.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise PluginError(f"{case.case_id} 缺少 Divider 参数：{names}")
        unknown = case.parameters.keys() - required
        if unknown:
            names = ", ".join(sorted(unknown))
            raise PluginError(f"{case.case_id} 包含未知 Divider 参数：{names}")

        for name in ("dividend_width", "divisor_width"):
            value = case.parameters[name]
            if type(value) is not int or value <= 0:
                raise PluginError(f"{case.case_id}.{name} 必须是正整数")

        if case.parameters["operand_sign"] not in {"Unsigned", "Signed"}:
            raise PluginError(
                f"{case.case_id}.operand_sign 必须是 Unsigned 或 Signed"
            )

        allowed_targets = {
            "systematic_values",
            "division_relations",
            "complete_input_space",
            "boundary_values",
            "sign_combinations",
            "nonzero_divisor",
        }
        unknown_targets = set(case.verification.coverage_targets) - allowed_targets
        if unknown_targets:
            raise PluginError(
                f"{case.case_id} 包含 Divider 不支持的覆盖目标："
                f"{', '.join(sorted(unknown_targets))}"
            )

    def build_request(self, case: TestCase) -> BuildRequest:
        run_dir = self._layout.case_run_dir(case)
        return BuildRequest(
            description="Running Divider IP creation:",
            source_path=self._layout.tcl_path("ip/divider/create_ip.tcl"),
            tclargs=(
                str(run_dir),
                str(case.parameters["dividend_width"]),
                str(case.parameters["divisor_width"]),
                str(case.parameters["operand_sign"]),
            ),
            log_path=self._layout.stage_log_path(case, Stage.CREATE_IP),
            journal_path=self._layout.stage_log_path(case, Stage.CREATE_IP).with_suffix(".jou"),
            success_marker="Divider IP generated successfully.",
            artifact_glob="**/div_gen_0.xci",
        )

    def generate_testbench(self, case: TestCase) -> TestbenchArtifacts:
        return self._testbench_backend.generate(case)

    def simulation_request(
        self, case: TestCase, stage: Stage
    ) -> SimulationRequest:
        run_dir = self._layout.case_run_dir(case)
        project_path = run_dir / "proj" / "divider_ip_test.xpr"

        if stage is Stage.SIM_DEMO:
            return SimulationRequest(
                description="Running Divider demo simulation:",
                project_path=project_path,
                testbench_path=(
                    run_dir
                    / "proj"
                    / "divider_ip_test.gen"
                    / "sources_1"
                    / "ip"
                    / "div_gen_0"
                    / "demo_tb"
                    / "tb_div_gen_0.vhd"
                ),
                top_name="tb_div_gen_0",
                log_path=self._layout.stage_log_path(case, stage),
                journal_path=self._layout.stage_log_path(case, stage).with_suffix(".jou"),
                success_marker="Test completed successfully",
                failure_markers=(
                    "ERROR: m_axis_dout_tdata is invalid",
                    "ERROR: terminating test with failures.",
                ),
                failure_status=Status.LOG_CHECK_FAILED,
            )

        if stage is Stage.SIM_SELFCHECK:
            return SimulationRequest(
                description="Running Divider self-check simulation:",
                project_path=project_path,
                testbench_path=run_dir / "tb" / "tb_divider_selfcheck.vhd",
                top_name="tb_divider_selfcheck",
                log_path=self._layout.stage_log_path(case, stage),
                journal_path=self._layout.stage_log_path(case, stage).with_suffix(".jou"),
                success_marker="DIVIDER_SELF_CHECK_STATUS: PASS",
                failure_markers=("DIVIDER_SELF_CHECK_STATUS: FAIL",),
                failure_status=Status.SIMULATION_FAILED,
            )

        raise PluginError(f"Divider 不支持仿真阶段：{stage.value}")

    def verify_simulation(self, case: TestCase, stage: Stage) -> Status:
        if stage is Stage.SIM_DEMO:
            return Status.PASS
        if stage is Stage.SIM_SELFCHECK:
            run_dir = self._layout.case_run_dir(case)
            expected_path = run_dir / "vectors" / "expected_output.txt"
            actual_path = run_dir / "outputs" / "actual_output.txt"
            if not output_files_match(expected_path, actual_path):
                return Status.VERIFICATION_FAILED
            return Status.PASS
        raise PluginError(f"Divider 不支持仿真阶段：{stage.value}")
