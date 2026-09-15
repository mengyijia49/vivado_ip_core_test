from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.domain import Stage, StageResult, Status, TestCase
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins import PluginRegistry


class IpBuilder:
    """执行插件提供的 IP 创建请求，并统一分类基础设施故障。"""

    def __init__(
        self,
        registry: PluginRegistry,
        layout: RepositoryLayout,
        vivado: VivadoBatchRunner,
    ) -> None:
        self._registry = registry
        self._layout = layout
        self._vivado = vivado

    def build(self, case: TestCase) -> StageResult:
        request = self._registry.resolve(case.ip_type).build_request(case)
        run_dir = self._layout.case_run_dir(case)
        self._layout.runs_dir.mkdir(parents=True, exist_ok=True)
        self._layout.log_dir.mkdir(parents=True, exist_ok=True)

        result = self._vivado.run(
            work_dir=self._layout.stage_work_dir(case, Stage.CREATE_IP),
            description=request.description,
            source=request.source_path,
            tclargs=request.tclargs,
            journal_path=request.journal_path,
            log_path=request.log_path,
        )

        if result is None:
            status = Status.VIVADO_NOT_FOUND
        elif result.timed_out:
            status = Status.TIMEOUT
        elif result.returncode != 0:
            status = Status.CREATE_IP_FAILED
        elif not request.log_path.exists():
            status = Status.LOG_NOT_FOUND
        elif request.success_marker not in request.log_path.read_text(errors="ignore"):
            status = Status.LOG_CHECK_FAILED
        elif not list(run_dir.glob(request.artifact_glob)):
            status = request.missing_artifact_status
        else:
            status = Status.PASS

        return StageResult(
            case_id=case.case_id,
            stage=Stage.CREATE_IP,
            status=status,
            run_dir=run_dir,
            log_path=request.log_path,
            ip_type=case.ip_type,
            parameters=case.parameters,
            verification=case.verification,
            metrics={} if result is None else result.metrics(),
        )
