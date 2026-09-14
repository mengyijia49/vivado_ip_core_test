import csv
from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path

from vivado_ip_test.domain import Stage, StageResult, Status, VerificationProfile
from vivado_ip_test.services import ReportGenerator


class ModelsAndReportTests(unittest.TestCase):
    def test_bundle_separates_ip_reports_and_clears_stale_views(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest/report.csv"
            reporter = ReportGenerator()
            divider = StageResult("first", Stage.CREATE_IP, Status.PASS, Path("/run"), Path("/log"), ip_type="divider")
            multiplier = replace(divider, case_id="second", ip_type="multiplier")
            reporter.write_bundle(path, [divider, multiplier])
            records = json.loads((path.parent / "ip/divider/report.json").read_text())
            self.assertEqual([record["case_id"] for record in records], ["first"])
            reporter.write_bundle(path, [])
            self.assertFalse((path.parent / "ip/divider/report.csv").exists())
            self.assertEqual(json.loads(path.with_suffix(".json").read_text()), [])

    def test_stage_result_serializes_to_compatible_csv_row(self):
        result = StageResult(
            case_id="case_a",
            stage=Stage.CREATE_IP,
            status=Status.PASS,
            run_dir=Path("/tmp/runs/case_a"),
            log_path=Path("/tmp/runs/logs/case_a_create.log"),
            ip_type="divider",
            parameters={"dividend_width": 16},
            verification=VerificationProfile(
                strategy="directed_random",
                strategy_version="1.0",
                random_seed=12,
                case_budget=16,
                coverage_targets=("boundary_values",),
            ),
            metrics={"generated_count": 16},
        )

        self.assertTrue(result.passed)
        self.assertEqual(
            result.as_csv_row(),
            [
                "case_a",
                "create_ip",
                "PASS",
                "divider",
                '{"dividend_width":16}',
                "directed_random",
                "1.0",
                "12",
                "16",
                '["boundary_values"]',
                '{"generated_count":16}',
                "/tmp/runs/case_a",
                "/tmp/runs/logs/case_a_create.log",
            ],
        )

    def test_report_generator_writes_header_and_rows(self):
        result = StageResult(
            case_id="case_a",
            stage=Stage.SIM_DEMO,
            status=Status.LOG_CHECK_FAILED,
            run_dir=Path("/tmp/runs/case_a"),
            log_path=Path("/tmp/runs/logs/case_a_demo_sim.log"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "reports" / "report.csv"
            ReportGenerator().write_csv(report_path, [result])
            with report_path.open(newline="") as report_file:
                rows = list(csv.reader(report_file))

        self.assertEqual(rows[0], ReportGenerator.HEADER)
        self.assertEqual(rows[1][0:3], ["case_a", "sim_demo", "LOG_CHECK_FAILED"])

    def test_report_generator_writes_machine_readable_json(self):
        result = StageResult(
            case_id="case_a",
            stage=Stage.SIM_SELFCHECK,
            status=Status.PASS,
            run_dir=Path("/tmp/runs/case_a"),
            log_path=Path("/tmp/runs/logs/case_a.log"),
            ip_type="multiplier",
            parameters={"a_width": 8},
            verification=VerificationProfile(
                strategy="exhaustive",
                strategy_version="1.0",
                random_seed=9,
                case_budget=16,
                coverage_targets=("complete_input_space",),
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.json"
            ReportGenerator().write_json(report_path, [result])
            records = json.loads(report_path.read_text())

        self.assertEqual(records[0]["ip_type"], "multiplier")
        self.assertEqual(records[0]["parameters"], {"a_width": 8})
        self.assertEqual(records[0]["verification"]["random_seed"], 9)
        self.assertEqual(records[0]["verification"]["strategy"], "exhaustive")
