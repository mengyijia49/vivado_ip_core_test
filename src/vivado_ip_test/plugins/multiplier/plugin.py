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
from vivado_ip_test.plugins.multiplier.testbench import MultiplierTestbenchBackend
from vivado_ip_test.strategies import StrategyRegistry


class MultiplierPlugin:
    ip_type = "multiplier"

    def __init__(
        self,
        layout: RepositoryLayout,
        strategy_registry: StrategyRegistry,
    ) -> None:
        self._layout = layout
        self._testbench_backend = MultiplierTestbenchBackend(
            layout, strategy_registry
        )

    def validate_case(self, case: TestCase) -> None:
        if case.vendor != "xilinx.com" or case.ip_name != "mult_gen":
            raise PluginError(
                f"{case.case_id} 不是受支持的 Xilinx Multiplier Generator"
            )

        required = {
            "a_width",
            "b_width",
            "a_type",
            "b_type",
            "pipeline_stages",
        }
        missing = required - case.parameters.keys()
        if missing:
            raise PluginError(
                f"{case.case_id} 缺少 Multiplier 参数：{', '.join(sorted(missing))}"
            )
        unknown = case.parameters.keys() - required
        if unknown:
            raise PluginError(
                f"{case.case_id} 包含未知 Multiplier 参数："
                f"{', '.join(sorted(unknown))}"
            )

        for name in ("a_width", "b_width"):
            value = case.parameters[name]
            if type(value) is not int or not 2 <= value <= 64:
                raise PluginError(f"{case.case_id}.{name} 必须是 2 到 64 的整数")
        for name in ("a_type", "b_type"):
            if case.parameters[name] not in {"Unsigned", "Signed"}:
                raise PluginError(
                    f"{case.case_id}.{name} 必须是 Unsigned 或 Signed"
                )
        pipeline_stages = case.parameters["pipeline_stages"]
        if type(pipeline_stages) is not int or not 1 <= pipeline_stages <= 64:
            raise PluginError(
                f"{case.case_id}.pipeline_stages 必须是 1 到 64 的整数"
            )
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("Multiplier Generator 不提供官方 demo testbench")

        allowed_targets = {
            "systematic_values",
            "boundary_values",
            "sign_combinations",
            "full_precision",
            "complete_input_space",
            "operand_magnitude",
        }
        unknown_targets = set(case.verification.coverage_targets) - allowed_targets
        if unknown_targets:
            raise PluginError(
                f"{case.case_id} 包含 Multiplier 不支持的覆盖目标："
                f"{', '.join(sorted(unknown_targets))}"
            )

    def build_request(self, case: TestCase) -> BuildRequest:
        run_dir = self._layout.case_run_dir(case)
        return BuildRequest(
            description="Running Multiplier IP creation:",
            source_path=self._layout.tcl_path("ip/multiplier/create_ip.tcl"),
            tclargs=(
                str(run_dir),
                str(case.parameters["a_width"]),
                str(case.parameters["b_width"]),
                str(case.parameters["a_type"]),
                str(case.parameters["b_type"]),
                str(case.parameters["pipeline_stages"]),
            ),
            log_path=self._layout.stage_log_path(case, Stage.CREATE_IP),
            journal_path=self._layout.stage_log_path(case, Stage.CREATE_IP).with_suffix(".jou"),
            success_marker="Multiplier IP generated successfully.",
            artifact_glob="**/mult_gen_0.xci",
        )

    def generate_testbench(self, case: TestCase) -> TestbenchArtifacts:
        return self._testbench_backend.generate(case)

    def simulation_request(
        self, case: TestCase, stage: Stage
    ) -> SimulationRequest:
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Multiplier 不支持仿真阶段：{stage.value}")
        run_dir = self._layout.case_run_dir(case)
        return SimulationRequest(
            description="Running Multiplier self-check simulation:",
            project_path=run_dir / "proj" / "multiplier_ip_test.xpr",
            testbench_path=run_dir / "tb" / "tb_multiplier_selfcheck.vhd",
            top_name="tb_multiplier_selfcheck",
            log_path=self._layout.stage_log_path(case, stage),
            journal_path=self._layout.stage_log_path(case, stage).with_suffix(".jou"),
            success_marker="MULTIPLIER_SELF_CHECK_STATUS: PASS",
            failure_markers=("MULTIPLIER_SELF_CHECK_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case: TestCase, stage: Stage) -> Status:
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Multiplier 不支持仿真阶段：{stage.value}")
        run_dir = self._layout.case_run_dir(case)
        if not output_files_match(
            run_dir / "vectors" / "expected_output.txt",
            run_dir / "outputs" / "actual_output.txt",
        ):
            return Status.VERIFICATION_FAILED
        return Status.PASS
