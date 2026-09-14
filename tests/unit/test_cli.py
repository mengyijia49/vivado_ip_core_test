from contextlib import redirect_stdout
from dataclasses import replace
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from vivado_ip_test.application.main import main
from unit.test_pipeline import make_case


class CliTests(unittest.TestCase):
    def test_limit_is_applied_after_resuming_completed_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [replace(make_case(), case_id=name) for name in ("first", "second", "third")]
            with patch("vivado_ip_test.application.main.load_test_cases", return_value=cases), \
                 patch("vivado_ip_test.application.main.remaining_cases", return_value=cases[1:]), \
                 patch("vivado_ip_test.application.main.build_pipeline"), \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(Path(directory), ["--resume-from", "run.json", "--limit", "1", "--list-cases"]), 0)
            self.assertIn("second", output.getvalue())
            self.assertNotIn("third", output.getvalue())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_case_seed_and_budget_are_saved_in_effective_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = MagicMock()
            pipeline = MagicMock()
            pipeline.run.return_value = []
            with patch("vivado_ip_test.application.main.load_test_cases", return_value=[make_case(), replace(make_case(), case_id="second")]), \
                 patch("vivado_ip_test.application.main.build_pipeline", return_value=pipeline), \
                 patch("vivado_ip_test.application.main.RunRecorder", return_value=recorder) as factory, \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(main(root, ["--case", "second", "--seed", "123", "--budget", "40"]), 0)
            cases = factory.call_args.args[1]
            self.assertEqual([case.case_id for case in cases], ["second"])
            self.assertEqual(cases[0].verification.random_seed, 123)
            self.assertEqual(cases[0].verification.case_budget, 40)

    def test_list_cases_does_not_start_vivado_or_create_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("vivado_ip_test.application.main.load_test_cases", return_value=[make_case()]), \
                 patch("vivado_ip_test.application.main.build_pipeline") as factory, \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(Path(directory), ["--list-cases"]), 0)
            self.assertIn(make_case().case_id, output.getvalue())
            factory.return_value.run.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])
