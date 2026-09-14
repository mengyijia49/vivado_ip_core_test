import traceback
from time import perf_counter

from vivado_ip_test.domain import Stage, StageResult, Status, TestCase
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins import PluginRegistry


class TestbenchGenerator:
    def __init__(
        self,
        registry: PluginRegistry,
        layout: RepositoryLayout,
    ) -> None:
        self._registry = registry
        self._layout = layout

    def generate(self, case: TestCase) -> StageResult:
        run_dir = self._layout.case_run_dir(case)
        log_path = self._layout.stage_log_path(case, Stage.GENERATE_TESTBENCH)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        started = perf_counter()
        try:
            artifacts = self._registry.resolve(case.ip_type).generate_testbench(case)
            log_text = (
                "TESTBENCH_GENERATION_STATUS: PASS\n"
                f"testbench={artifacts.testbench_path}\n"
                f"vectors={artifacts.vector_count}\n"
                f"manifest={artifacts.manifest_path}\n"
            )
            status = Status.PASS
        except Exception:
            log_text = (
                "TESTBENCH_GENERATION_STATUS: FAIL\n"
                f"{traceback.format_exc()}"
            )
            status = Status.TESTBENCH_GENERATION_FAILED

        log_path.write_text(log_text)
        return StageResult(
            case_id=case.case_id,
            stage=Stage.GENERATE_TESTBENCH,
            status=status,
            run_dir=run_dir,
            log_path=log_path,
            ip_type=case.ip_type,
            parameters=case.parameters,
            verification=case.verification,
            metrics={
                **(artifacts.metrics if status is Status.PASS else {}),
                "elapsed_seconds": perf_counter() - started,
            },
        )
