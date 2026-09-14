import json
import platform
import shutil
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from itertools import groupby

from vivado_ip_test.domain import Stage, StageResult, TestCase
from vivado_ip_test.infrastructure import RepositoryLayout, sha256_file
from vivado_ip_test.infrastructure.source_inventory import source_inventory
from vivado_ip_test.services.report_generator import ReportGenerator


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRecorder:
    """保存每次运行的独立证据；阶段失败只登记为待分析异常。"""

    def __init__(self, layout: RepositoryLayout, cases: list[TestCase]) -> None:
        self.layout = layout
        self.run_id = layout.run_id
        self.artifact_dir = layout.runs_dir / "history" / self.run_id
        self.log_dir = layout.log_dir / "history" / self.run_id
        self.report_dir = layout.report_path.parent
        self.cases = cases
        self.results: list[StageResult] = []
        self.hashes: dict[str, str] = {}
        self.metadata: dict[str, object] = {}
        self._reporter = ReportGenerator()

    def __enter__(self):
        for directory in (self.layout.batch_dir, self.layout.batch_log_dir,
                          self.artifact_dir, self.log_dir, self.report_dir):
            directory.mkdir(parents=True, exist_ok=False)
        source_root = self.layout.source_root or self.layout.root
        sources = source_inventory(source_root)
        for relative in sources:
            self._copy(source_root / relative, self.artifact_dir / "source" / relative)

        effective_config = {
            "schema_version": 2,
            "cases": [
                {
                    "case_id": case.case_id,
                    "ip_type": case.ip_type,
                    "vendor": case.vendor,
                    "ip_name": case.ip_name,
                    "parameters": dict(case.parameters),
                    "stages": [stage.value for stage in case.stages],
                    "verification": case.verification.as_dict(),
                }
                for case in self.cases
            ],
        }
        config_path = self.artifact_dir / "ip_matrix.json"
        if len({case.ip_type for case in self.cases}) > 1:
            includes = []
            for index, (ip_type, group) in enumerate(groupby(effective_config["cases"], key=lambda case: case["ip_type"])):
                child = self.artifact_dir / "configs" / ip_type / f"batch_{index}.json"
                child.parent.mkdir(parents=True, exist_ok=True)
                self._write_json(child, {"schema_version": 2, "cases": list(group)})
                self.hashes[str(child.relative_to(self.layout.root))] = sha256_file(child)
                includes.append(str(child.relative_to(self.artifact_dir)))
            effective_config = {"schema_version": 2, "includes": includes}
        self._write_json(config_path, effective_config)
        self.hashes[str(config_path.relative_to(self.layout.root))] = sha256_file(config_path)
        self.metadata = {
            "schema_version": 1,
            "run_id": self.run_id,
            "state": "running",
            "started_at": _timestamp(),
            "working_directory": str(self.layout.batch_dir),
            "working_log_directory": str(self.layout.batch_log_dir),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "vivado_executable": shutil.which("vivado"),
            "git_commit": self._git(source_root, "rev-parse", "HEAD"),
            "git_status": self._git(source_root, "status", "--short"),
            "source_sha256": sources,
            "expected_stages": [[case.case_id, stage.value] for case in self.cases for stage in case.stages],
            "replay_command": [
                "python3", str(self.artifact_dir / "source/scripts/run_all.py"),
                "--workspace", str(self.layout.root), "--config", str(config_path),
            ],
        }
        self._checkpoint()
        self._publish_latest()
        return self

    def _publish_latest(self) -> None:
        latest = self.layout.reports_dir / "latest"
        if latest.exists() and not latest.is_symlink():
            backup = self.layout.reports_dir / "legacy" / self.run_id / "latest"
            backup.parent.mkdir(parents=True, exist_ok=False)
            latest.rename(backup)
        temporary = self.layout.reports_dir / f".latest_{self.run_id}"
        temporary.symlink_to(self.report_dir.relative_to(self.layout.reports_dir), target_is_directory=True)
        temporary.replace(latest)

    def capture(self, result: StageResult) -> None:
        ip_type = next(case.ip_type for case in self.cases if case.case_id == result.case_id)
        case_dir = self.artifact_dir / "cases" / ip_type / result.case_id
        log_dir = self.log_dir / ip_type / result.case_id / result.stage.value
        log_path = log_dir / result.log_path.name
        if result.log_path.is_file():
            self._copy(result.log_path, log_path)
        for suffix in (".jou", ".process.log", ".invocation.json"):
            companion = result.log_path.with_suffix(suffix)
            if companion.is_file():
                self._copy(companion, log_dir / companion.name)
        if result.stage is Stage.CREATE_IP and result.passed:
            for source in result.run_dir.glob("proj/**/*.xci"):
                self._copy(source, case_dir / source.relative_to(result.run_dir))
        elif result.stage is Stage.GENERATE_TESTBENCH and result.passed:
            for name in ("manifest.json", "tb", "vectors"):
                self._copy_tree(result.run_dir / name, case_dir / name)
        elif result.stage in {Stage.SIM_DEMO, Stage.SIM_SELFCHECK}:
            if result.stage is Stage.SIM_SELFCHECK:
                self._copy_tree(result.run_dir / "outputs", case_dir / "outputs")
            for sim_dir in result.run_dir.glob("proj/*.sim/sim_1/behav/xsim"):
                for source in sorted(sim_dir.rglob("*")):
                    if not source.is_file():
                        continue
                    relative = source.relative_to(sim_dir)
                    if source.suffix in {".log", ".jou"}:
                        self._copy(source, log_dir / "xsim" / relative)
                    elif source.suffix in {".sh", ".prj", ".tcl", ".ini"}:
                        self._copy(source, case_dir / "simulation" / result.stage.value / relative)
        self.results.append(replace(result, run_dir=case_dir, log_path=log_path))
        self._checkpoint()

    def __exit__(self, exc_type, exc, traceback):
        self.metadata["state"] = (
            "completed" if exc_type is None else
            "interrupted" if issubclass(exc_type, KeyboardInterrupt) else "error"
        )
        self.metadata["finished_at"] = _timestamp()
        if exc_type is not None:
            self.metadata["exception"] = f"{exc_type.__name__}: {exc}"
        self._checkpoint()
        return False

    def _checkpoint(self) -> None:
        failures = [
            {"case_id": result.case_id, "stage": result.stage.value, "status": result.status.value,
             "evidence": result.metrics.get("failure_evidence"),
             "replay_command": [*self.metadata["replay_command"], "--case", result.case_id]}
            for result in self.results if not result.passed
        ]
        self.metadata.update({
            "completed_stages": [[result.case_id, result.stage.value] for result in self.results],
            "observed_failures": failures,
            "outcome": (
                "INCOMPLETE" if self.metadata["state"] != "completed" else
                "FAILURES_OBSERVED" if failures else
                "NO_FAILURE_OBSERVED" if [[r.case_id, r.stage.value] for r in self.results] == self.metadata["expected_stages"] else
                "INCOMPLETE"
            ),
            "artifact_sha256": dict(self.hashes),
        })
        self._reporter.write_bundle(self.report_dir / "report.csv", self.results)
        self._write_json(self.report_dir / "run.json", self.metadata)

    def _copy_tree(self, source: Path, target: Path) -> None:
        if source.is_file():
            self._copy(source, target)
        elif source.is_dir():
            for file in sorted(source.rglob("*")):
                if file.is_file():
                    self._copy(file, target / file.relative_to(source))

    def _copy(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self.hashes[str(target.relative_to(self.layout.root))] = sha256_file(target)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)

    @staticmethod
    def _git(root: Path, *arguments: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *arguments], text=True,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None
