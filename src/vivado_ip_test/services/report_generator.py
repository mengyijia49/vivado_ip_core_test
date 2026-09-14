import csv
import json
from pathlib import Path
from typing import Iterable

from vivado_ip_test.domain import StageResult


class ReportGenerator:
    HEADER = [
        "case_id",
        "stage",
        "status",
        "ip_type",
        "parameters",
        "strategy",
        "strategy_version",
        "random_seed",
        "case_budget",
        "coverage_targets",
        "metrics",
        "run_dir",
        "log_path",
    ]

    def write_bundle(self, path: Path, results: Iterable[StageResult]) -> None:
        records = list(results)
        self.write_csv(path, records)
        self.write_json(path.with_suffix(".json"), records)
        ip_root = path.parent / "ip"
        if not records and ip_root.exists():
            for directory in ip_root.iterdir():
                if directory.is_dir() and not directory.is_symlink():
                    for name in ("report.csv", "report.json"):
                        (directory / name).unlink(missing_ok=True)
                    if not any(directory.iterdir()):
                        directory.rmdir()
        for ip_type in sorted({record.ip_type for record in records if record.ip_type}):
            selected = [record for record in records if record.ip_type == ip_type]
            self.write_csv(ip_root / ip_type / "report.csv", selected)
            self.write_json(ip_root / ip_type / "report.json", selected)

    def write_csv(self, path: Path, results: Iterable[StageResult]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as report_file:
            writer = csv.writer(report_file)
            writer.writerow(self.HEADER)
            writer.writerows(result.as_csv_row() for result in results)

    def write_json(self, path: Path, results: Iterable[StageResult]) -> None:
        records = [
            {
                "case_id": result.case_id,
                "ip_type": result.ip_type,
                "stage": result.stage.value,
                "status": result.status.value,
                "parameters": dict(result.parameters),
                "verification": None
                if result.verification is None
                else result.verification.as_dict(),
                "metrics": dict(result.metrics),
                "run_dir": str(result.run_dir),
                "log_path": str(result.log_path),
            }
            for result in results
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
