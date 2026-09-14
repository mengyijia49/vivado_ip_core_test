import tempfile
import unittest
from pathlib import Path

from vivado_ip_test.domain import (
    SimulationRequest,
    Stage,
    Status,
    TestCase as DomainTestCase,
    VerificationProfile,
)
from vivado_ip_test.infrastructure import CommandResult, RepositoryLayout
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.services import SimulationRunner


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
