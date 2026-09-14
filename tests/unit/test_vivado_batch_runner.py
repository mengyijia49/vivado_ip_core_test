from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandResult


class VivadoBatchRunnerTests(unittest.TestCase):
    def test_uses_separate_work_directory_for_tool_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "runs/current/divider/case/work/create_ip"
            runner = Mock(run=Mock(return_value=CommandResult(0, "done")))
            with patch("vivado_ip_test.adapters.vivado.runner.shutil.which", return_value="/tools/vivado"), redirect_stdout(io.StringIO()):
                VivadoBatchRunner(runner, root).run(
                    description="test", source=root / "create.tcl", tclargs=[],
                    log_path=root / "runs/logs/test.log", journal_path=root / "runs/logs/test.jou",
                    work_dir=work,
                )
            self.assertTrue(work.is_dir())
            self.assertEqual(runner.run.call_args.args[1], work)
            record = json.loads((root / "runs/logs/test.invocation.json").read_text())
            self.assertEqual(record["cwd"], str(work))

    def invoke(self, root, command_runner, executable):
        runner = VivadoBatchRunner(command_runner, root)
        with patch("vivado_ip_test.adapters.vivado.runner.shutil.which", return_value=executable), redirect_stdout(io.StringIO()):
            return runner.run(
                description="测试 Vivado 执行器",
                source=root / "create.tcl", tclargs=["a path with spaces"],
                log_path=root / "run.log", journal_path=root / "run.jou",
            )

    def test_missing_vivado_removes_stale_success_but_records_current_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("run.log", "run.jou", "run.process.log", "run.invocation.json"):
                (root / name).write_text("old success")
            commands = Mock()
            self.assertIsNone(self.invoke(root, commands, None))
            commands.run.assert_not_called()
            self.assertFalse((root / "run.log").exists())
            self.assertFalse((root / "run.jou").exists())
            self.assertIn("VIVADO_NOT_FOUND", (root / "run.process.log").read_text())
            metadata = json.loads((root / "run.invocation.json").read_text())
            self.assertEqual(metadata["state"], "unavailable")
            self.assertIsNone(metadata["returncode"])
            self.assertEqual(metadata["command"][-1], "a path with spaces")

    def test_timeout_output_survives_even_without_vivado_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = CommandResult(124, "runtime stalled\n", timed_out=True, elapsed_seconds=2.5)
            self.assertEqual(self.invoke(root, Mock(run=Mock(return_value=result)), "/tools/vivado"), result)
            self.assertFalse((root / "run.log").exists())
            self.assertEqual((root / "run.process.log").read_text(), result.output)
            metadata = json.loads((root / "run.invocation.json").read_text())
            self.assertEqual(metadata["returncode"], 124)
            self.assertTrue(metadata["timed_out"])
            self.assertIn("finished_at", metadata)

    def test_startup_os_error_is_reported_as_failed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.invoke(root, Mock(run=Mock(side_effect=PermissionError("denied"))), "/tools/vivado")
            self.assertEqual(result.returncode, 127)
            self.assertIn("denied", (root / "run.process.log").read_text())

    def test_interruption_is_recorded_and_propagated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(KeyboardInterrupt):
                self.invoke(root, Mock(run=Mock(side_effect=KeyboardInterrupt)), "/tools/vivado")
            metadata = json.loads((root / "run.invocation.json").read_text())
            self.assertEqual(metadata["state"], "interrupted")
