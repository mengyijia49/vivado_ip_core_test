import json
from pathlib import Path

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.domain import Stage, StageResult, Status, TestCase
from vivado_ip_test.infrastructure import (
    CommandResult,
    RepositoryLayout,
    sha256_file,
)
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.services.failure_analysis import analyze_outputs


class SimulationRunner:
    """通过统一 XSim 入口执行插件描述的仿真任务。"""

    _PASS_MARKER = "XSIM_STAGE_STATUS: PASS"
    _FAIL_MARKER = "XSIM_STAGE_STATUS: FAIL"

    def __init__(
        self,
        registry: PluginRegistry,
        layout: RepositoryLayout,
        vivado: VivadoBatchRunner,
    ) -> None:
        self._registry = registry
        self._layout = layout
        self._vivado = vivado

    def run(self, case: TestCase, stage: Stage) -> StageResult:
        plugin = self._registry.resolve(case.ip_type)
        request = plugin.simulation_request(case, stage)
        self._layout.log_dir.mkdir(parents=True, exist_ok=True)

        result = self._vivado.run(
            work_dir=self._layout.stage_work_dir(case, stage),
            description=request.description,
            source=self._layout.tcl_path("run_xsim_batch.tcl"),
            tclargs=[
                str(request.project_path),
                str(request.testbench_path),
                request.top_name,
                request.success_marker,
                *request.failure_markers,
            ],
            journal_path=request.journal_path,
            log_path=request.log_path,
        )

        status = self._execution_status(result, request.log_path, request.failure_status)
        if status is Status.PASS:
            status = plugin.verify_simulation(case, stage)

        metrics = {} if result is None else result.metrics()
        if stage is Stage.SIM_SELFCHECK:
            run_dir = self._layout.case_run_dir(case)
            failure_path = run_dir / "outputs/failure.json"
            if failure_path.exists():
                failure_path.unlink()
            actual_path = (
                self._layout.case_run_dir(case)
                / "outputs"
                / "actual_output.txt"
            )
            if actual_path.exists():
                metrics["output_count"] = len(actual_path.read_text().splitlines())
                metrics["actual_output_sha256"] = sha256_file(actual_path)
            if status is not Status.PASS:
                evidence = analyze_outputs(run_dir)
                metrics["failure_evidence"] = evidence
                failure_path.parent.mkdir(parents=True, exist_ok=True)
                failure_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")

        return StageResult(
            case_id=case.case_id,
            stage=stage,
            status=status,
            run_dir=self._layout.case_run_dir(case),
            log_path=request.log_path,
            ip_type=case.ip_type,
            parameters=case.parameters,
            verification=case.verification,
            metrics=metrics,
        )

    def _execution_status(
        self,
        result: CommandResult | None,
        log_path: Path,
        failure_status: Status,
    ) -> Status:
        if result is None:
            return Status.VIVADO_NOT_FOUND
        if result.timed_out:
            return Status.TIMEOUT
        if not log_path.exists():
            return Status.LOG_NOT_FOUND

        log_text = log_path.read_text(errors="ignore")
        lines = {line.strip() for line in log_text.splitlines()}
        if (
            result.returncode != 0
            or self._PASS_MARKER not in lines
            or self._FAIL_MARKER in lines
        ):
            return failure_status
        return Status.PASS
