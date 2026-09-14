import tempfile
import unittest
import csv
import json
from pathlib import Path
from unittest.mock import Mock

from vivado_ip_test.application import AutomationPipeline
from vivado_ip_test.domain import (
    Stage,
    StageResult,
    Status,
    TestCase as DomainTestCase,
    VerificationProfile,
)
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.services import ReportGenerator, RunRecorder
from vivado_ip_test.strategies import create_default_strategy_registry


class FakePlugin:
    ip_type = "fake_ip"

    def validate_case(self, case):
        return None


class FakeIpBuilder:
    def __init__(self, status=Status.PASS):
        self.status = status
        self.calls = []

    def build(self, case):
        self.calls.append(case.case_id)
        return StageResult(
            case_id=case.case_id,
            stage=Stage.CREATE_IP,
            status=self.status,
            run_dir=Path("/tmp") / case.case_id,
            log_path=Path("/tmp") / f"{case.case_id}_create_ip.log",
        )


class FakeTestbenchGenerator:
    def generate(self, case):
        raise AssertionError("该测试不应调用 testbench 生成器")


class FakeSimulationRunner:
    def __init__(self):
        self.calls = []

    def run(self, case, stage):
        self.calls.append((case.case_id, stage))
        return StageResult(
            case_id=case.case_id,
            stage=stage,
            status=Status.PASS,
            run_dir=Path("/tmp") / case.case_id,
            log_path=Path("/tmp") / f"{case.case_id}_{stage.value}.log",
        )


def make_case():
    return DomainTestCase(
        case_id="name_does_not_encode_ip_type",
        ip_type="fake_ip",
        vendor="example.com",
        ip_name="fake",
        parameters={},
        stages=(Stage.CREATE_IP, Stage.SIM_DEMO),
        verification=VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=1,
            case_budget=1,
            coverage_targets=("boundary_values",),
        ),
    )


class PipelineTests(unittest.TestCase):
    def test_recorder_owns_timestamped_report_and_preserves_archived_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = RepositoryLayout(Path(directory))
            reporter = Mock()
            pipeline = AutomationPipeline(
                PluginRegistry(), reporter, FakeTestbenchGenerator(),
                FakeSimulationRunner(), FakeIpBuilder(), create_default_strategy_registry(),
            )
            with RunRecorder(layout, [make_case()]) as recorder:
                pipeline.run([make_case()], layout.report_path, recorder)
            reporter.write_bundle.assert_not_called()
            rows = json.loads(layout.report_path.with_suffix(".json").read_text())
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(Path(row["run_dir"]).is_relative_to(recorder.artifact_dir) for row in rows))
            metadata = json.loads((recorder.report_dir / "run.json").read_text())
            self.assertEqual(metadata["outcome"], "NO_FAILURE_OBSERVED")

    def test_interruption_preserves_only_current_completed_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.csv"
            report_path.write_text("stale success report")
            report_path.with_suffix(".json").write_text('[{"case_id": "stale"}]')
            builder = FakeIpBuilder()

            def check_cleared_report(case):
                self.assertEqual(json.loads(report_path.with_suffix(".json").read_text()), [])
                return builder.build(case)

            pipeline = AutomationPipeline(
                PluginRegistry(), ReportGenerator(), FakeTestbenchGenerator(),
                Mock(run=Mock(side_effect=KeyboardInterrupt)),
                Mock(build=check_cleared_report), create_default_strategy_registry(),
            )
            with self.assertRaises(KeyboardInterrupt):
                pipeline.run([make_case()], report_path)
            records = json.loads(report_path.with_suffix(".json").read_text())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["stage"], "create_ip")
            with report_path.open() as stream:
                csv_records = list(csv.DictReader(stream))
            self.assertEqual(len(csv_records), 1)
            self.assertEqual(csv_records[0]["case_id"], make_case().case_id)

    def run_pipeline(self, plugin, build_status=Status.PASS):
        registry = PluginRegistry()
        registry.register(plugin)
        simulation_runner = FakeSimulationRunner()
        ip_builder = FakeIpBuilder(build_status)
        pipeline = AutomationPipeline(
            registry,
            ReportGenerator(),
            FakeTestbenchGenerator(),
            simulation_runner,
            ip_builder,
            create_default_strategy_registry(),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.csv"
            pipeline.validate([make_case()])
            return (
                pipeline.run([make_case()], report_path),
                simulation_runner,
                ip_builder,
            )

    def test_dispatches_by_explicit_ip_type_and_runs_configured_stages(self):
        plugin = FakePlugin()

        results, simulation_runner, ip_builder = self.run_pipeline(plugin)

        self.assertEqual(ip_builder.calls, ["name_does_not_encode_ip_type"])
        self.assertEqual(
            simulation_runner.calls,
            [("name_does_not_encode_ip_type", Stage.SIM_DEMO)],
        )
        self.assertEqual([result.status for result in results], [Status.PASS] * 2)

    def test_stops_dependent_stages_after_create_failure(self):
        plugin = FakePlugin()

        results, simulation_runner, ip_builder = self.run_pipeline(
            plugin, Status.CREATE_IP_FAILED
        )

        self.assertEqual(ip_builder.calls, ["name_does_not_encode_ip_type"])
        self.assertEqual(simulation_runner.calls, [])
        self.assertEqual(results[0].status, Status.CREATE_IP_FAILED)
