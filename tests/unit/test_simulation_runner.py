import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vivado_ip_test.domain import (
    SimulationRequest,
    Stage,
    Status,
    TestCase as DomainTestCase,
    VerificationProfile,
)
from vivado_ip_test.infrastructure import CommandResult, RepositoryLayout, sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.services import RunRecorder, SimulationRunner


class FakePlugin:
    ip_type = "fake_ip"

    def __init__(self, layout, verification_status=Status.PASS):
        self.layout = layout
        self.verification_status = verification_status
        self.verify_calls = []

    def simulation_request(self, case, stage):
        return SimulationRequest(
            description="Running fake simulation:",
            project_path=self.layout.root / "fake.xpr",
            testbench_path=self.layout.root / "tb.vhd",
            top_name="tb",
            log_path=self.layout.log_dir / "fake.log",
            journal_path=self.layout.log_dir / "fake.jou",
            success_marker="TB_STATUS: PASS",
            failure_markers=("TB_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case, stage):
        self.verify_calls.append((case.case_id, stage))
        return self.verification_status


class FakeVivado:
    def __init__(self, result, log_text=None):
        self.result = result
        self.log_text = log_text
        self.calls = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        if self.log_text is not None:
            kwargs["log_path"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["log_path"].write_text(self.log_text)
        return self.result


def make_case():
    return DomainTestCase(
        case_id="fake_case",
        ip_type="fake_ip",
        vendor="example.com",
        ip_name="fake",
        parameters={},
        stages=(Stage.SIM_SELFCHECK,),
        verification=VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=1,
            case_budget=1,
            coverage_targets=("boundary_values",),
        ),
    )


class SimulationRunnerTests(unittest.TestCase):
    def make_runner(self, root, vivado, verification_status=Status.PASS):
        layout = RepositoryLayout(root)
        plugin = FakePlugin(layout, verification_status)
        registry = PluginRegistry()
        registry.register(plugin)
        return SimulationRunner(registry, layout, vivado), plugin

    def test_full_difference_groups_are_archived_but_report_metrics_are_compact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner, plugin = self.make_runner(root,
                FakeVivado(CommandResult(1, ""), "XSIM_STAGE_STATUS: FAIL\n"))
            case = make_case()
            run_dir = plugin.layout.case_run_dir(case)
            with RunRecorder(plugin.layout, [case]) as recorder:
                (run_dir / "vectors").mkdir(parents=True)
                (run_dir / "outputs").mkdir()
                (run_dir / "vectors/expected_output.txt").write_text("00\n00\n")
                (run_dir / "outputs/actual_output.txt").write_text("10\n01\n")
                (run_dir / "manifest.json").write_text(json.dumps({
                    "output_layout": binary_output_layout((("irq", 1), ("data", 1)))}))
                result = runner.run(case, Stage.SIM_SELFCHECK)
                recorder.capture(result)
            self.assertEqual(result.status, Status.SIMULATION_FAILED)
            compact = result.metrics["failure_evidence"]["difference_summary"]
            self.assertNotIn("groups", compact)
            self.assertEqual(compact["retained_group_count"], 2)
            report = json.loads((recorder.report_dir / "report.json").read_text())[0]
            failure = Path(report["run_dir"]) / report["metrics"]["failure_detail_file"]
            self.assertEqual(sha256_file(failure), report["metrics"]["failure_detail_sha256"])
            self.assertEqual(recorder.hashes[str(failure.relative_to(root))], sha256_file(failure))
            full = json.loads(failure.read_text())
            self.assertEqual(full["output_index"], 0)
            self.assertEqual([group["output_field"] for group in full["difference_summary"]["groups"]],
                             ["irq", "data"])
            self.assertEqual({key: value for key, value in full["difference_summary"].items()
                              if key != "groups"}, compact)

    def test_matching_numeric_output_does_not_override_protocol_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            vivado = FakeVivado(CommandResult(1, ""), "XSIM_STAGE_STATUS: FAIL\n")
            runner, plugin = self.make_runner(Path(directory), vivado)
            run_dir = plugin.layout.case_run_dir(make_case())
            (run_dir / "vectors").mkdir(parents=True)
            (run_dir / "outputs").mkdir()
            (run_dir / "vectors/expected_output.txt").write_text("01\n")
            (run_dir / "outputs/actual_output.txt").write_text("01\n")
            result = runner.run(make_case(), Stage.SIM_SELFCHECK)
            self.assertEqual(result.status, Status.SIMULATION_FAILED)
            self.assertEqual(result.metrics["failure_evidence"]["kind"], "no_numeric_difference")
            self.assertEqual(result.metrics["failure_evidence"]["difference_summary"]["difference_rows"], 0)
            self.assertTrue((run_dir / "outputs/failure.json").exists())
            vivado.result, vivado.log_text = CommandResult(0, ""), "XSIM_STAGE_STATUS: PASS\n"
            result = runner.run(make_case(), Stage.SIM_SELFCHECK)
            self.assertEqual(result.status, Status.PASS)
            self.assertFalse((run_dir / "outputs/failure.json").exists())
            self.assertNotIn("failure_evidence", result.metrics)
            self.assertNotIn("failure_detail_file", result.metrics)

    def test_runs_generic_tcl_and_verifies_successful_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(
                CommandResult(0, ""),
                "XSIM_STAGE_STATUS: PASS\n",
            )
            runner, plugin = self.make_runner(Path(temp_dir), vivado)

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.PASS)
            self.assertEqual(
                vivado.calls[0]["source"],
                Path(temp_dir) / "tcl" / "run_xsim_batch.tcl",
            )
            self.assertEqual(vivado.calls[0]["tclargs"][-1], "TB_STATUS: FAIL")
            self.assertEqual(plugin.verify_calls, [("fake_case", Stage.SIM_SELFCHECK)])

    def test_rejects_log_containing_generic_failure_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(
                CommandResult(0, ""),
                "XSIM_STAGE_STATUS: PASS\nXSIM_STAGE_STATUS: FAIL\n",
            )
            runner, plugin = self.make_runner(Path(temp_dir), vivado)

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.SIMULATION_FAILED)
            self.assertEqual(plugin.verify_calls, [])

    def test_ignores_echoed_source_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(
                CommandResult(0, ""),
                '# puts "XSIM_STAGE_STATUS: FAIL"\nXSIM_STAGE_STATUS: PASS\n',
            )
            runner, _ = self.make_runner(Path(temp_dir), vivado)
            self.assertEqual(runner.run(make_case(), Stage.SIM_SELFCHECK).status, Status.PASS)
            vivado.log_text = '# puts "XSIM_STAGE_STATUS: PASS"\n'
            self.assertEqual(runner.run(make_case(), Stage.SIM_SELFCHECK).status, Status.SIMULATION_FAILED)

    def test_failed_simulation_reports_partial_output_and_process_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vivado = FakeVivado(
                CommandResult(1, "mismatch", elapsed_seconds=3.5),
                "XSIM_STAGE_STATUS: FAIL\n",
            )
            runner, plugin = self.make_runner(root, vivado)
            actual = plugin.layout.case_run_dir(make_case()) / "outputs/actual_output.txt"
            actual.parent.mkdir(parents=True)
            actual.write_text("01\nXX\n")
            result = runner.run(make_case(), Stage.SIM_SELFCHECK)
            self.assertEqual(result.status, Status.SIMULATION_FAILED)
            self.assertEqual(result.metrics["output_count"], 2)
            self.assertEqual(result.metrics["elapsed_seconds"], 3.5)
            self.assertEqual(result.metrics["returncode"], 1)
            self.assertIn("actual_output_sha256", result.metrics)

    def test_output_count_does_not_load_the_whole_file(self):
        with tempfile.TemporaryDirectory() as directory:
            runner, plugin = self.make_runner(Path(directory),
                FakeVivado(CommandResult(0, ""), "XSIM_STAGE_STATUS: PASS\n"))
            actual = plugin.layout.case_run_dir(make_case()) / "outputs/actual_output.txt"
            actual.parent.mkdir(parents=True)
            actual.write_text("0" * 150000 + "\n" + "1" * 150000)
            original = Path.read_text

            def guarded_read(path, *args, **kwargs):
                self.assertNotEqual(path, actual, "输出计数不应整文件读入内存")
                return original(path, *args, **kwargs)

            with patch.object(Path, "read_text", guarded_read):
                result = runner.run(make_case(), Stage.SIM_SELFCHECK)
            self.assertEqual(result.metrics["output_count"], 2)
            self.assertIs(result.status, Status.PASS)

    def test_preserves_post_simulation_verification_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(
                CommandResult(0, ""),
                "XSIM_STAGE_STATUS: PASS\n",
            )
            runner, _ = self.make_runner(
                Path(temp_dir), vivado, Status.VERIFICATION_FAILED
            )

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.VERIFICATION_FAILED)

    def test_classifies_missing_vivado(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner, plugin = self.make_runner(Path(temp_dir), FakeVivado(None))

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.VIVADO_NOT_FOUND)
            self.assertEqual(plugin.verify_calls, [])

    def test_classifies_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(CommandResult(124, "", timed_out=True))
            runner, _ = self.make_runner(Path(temp_dir), vivado)

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.TIMEOUT)

    def test_classifies_missing_log(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(CommandResult(0, ""))
            runner, _ = self.make_runner(Path(temp_dir), vivado)

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.LOG_NOT_FOUND)

    def test_uses_plugin_failure_status_for_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vivado = FakeVivado(
                CommandResult(1, ""),
                "XSIM_STAGE_STATUS: FAIL\n",
            )
            runner, _ = self.make_runner(Path(temp_dir), vivado)

            result = runner.run(make_case(), Stage.SIM_SELFCHECK)

            self.assertEqual(result.status, Status.SIMULATION_FAILED)
