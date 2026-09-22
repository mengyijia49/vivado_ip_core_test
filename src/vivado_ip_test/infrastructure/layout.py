from dataclasses import dataclass, field
from pathlib import Path

from vivado_ip_test.domain import Stage, TestCase
from vivado_ip_test.infrastructure.run_identity import create_run_id


@dataclass(frozen=True)
class RepositoryLayout:
    root: Path
    source_root: Path | None = None
    vivado_version: str | None = None
    run_id: str = field(default_factory=create_run_id, init=False)

    @property
    def config_path(self) -> Path:
        return self.root / "configs" / "ip_matrix.json"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def log_dir(self) -> Path:
        return self.runs_dir / "logs"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def report_path(self) -> Path:
        return self._versioned(self.reports_dir / "history") / self.run_id / "report.csv"

    @property
    def batch_dir(self) -> Path:
        return self._versioned(self.runs_dir / "batches") / self.run_id

    @property
    def batch_log_dir(self) -> Path:
        return self._versioned(self.log_dir / "batches") / self.run_id

    @property
    def artifact_dir(self) -> Path:
        return self._versioned(self.runs_dir / "history") / self.run_id

    @property
    def artifact_log_dir(self) -> Path:
        return self._versioned(self.log_dir / "history") / self.run_id

    def _versioned(self, path: Path) -> Path:
        return path / self.vivado_version if self.vivado_version else path

    def case_run_dir(self, case: TestCase) -> Path:
        return self.batch_dir / case.ip_type / case.case_id

    def case_log_dir(self, case: TestCase) -> Path:
        return self.batch_log_dir / case.ip_type / case.case_id

    def stage_log_path(self, case: TestCase, stage: Stage) -> Path:
        return self.case_log_dir(case) / f"{stage.value}.log"

    def stage_work_dir(self, case: TestCase, stage: Stage) -> Path:
        return self.case_run_dir(case) / "work" / stage.value

    def tcl_path(self, name: str) -> Path:
        return (self.source_root or self.root) / "tcl" / name
