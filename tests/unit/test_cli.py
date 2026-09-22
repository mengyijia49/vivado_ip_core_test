from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from vivado_ip_test.application.main import main
from vivado_ip_test.configuration import ConfigError
from unit.test_configuration import valid_config
from unit.test_pipeline import make_case


class CliTests(unittest.TestCase):
    def test_wrong_vivado_version_is_rejected_before_running(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('vivado_ip_test.application.main.detect_vivado_version', return_value='2026.0'), \
             patch('vivado_ip_test.application.main.build_pipeline') as factory, \
             redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main(Path(directory), []), 2)
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertIn('2026.1', errors.getvalue())
        factory.assert_not_called()

    def test_case_listing_does_not_require_selected_vivado_version(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('vivado_ip_test.application.main.detect_vivado_version') as detect, \
             patch('vivado_ip_test.application.main.iter_test_cases', return_value=(c for c in [make_case()])), \
             patch('vivado_ip_test.application.main.build_pipeline'), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(main(Path(directory), ['--list-cases']), 0)
        detect.assert_not_called()

    def test_late_duplicate_with_limit_starts_no_tool_and_writes_no_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = valid_config()
            value['cases'].append(dict(value['cases'][0]))
            path = root / 'matrix.json'
            path.write_text(json.dumps(value))
            with patch('vivado_ip_test.application.main.build_pipeline') as factory, \
                 patch('vivado_ip_test.application.main.RunRecorder') as recorder, \
                 redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main(root, ['--config', str(path), '--limit', '1']), 2)
            self.assertIn('唯一', errors.getvalue())
            factory.return_value.run.assert_not_called()
            recorder.assert_not_called()
            self.assertEqual(list(root.iterdir()), [path])

    def test_validation_failure_closes_the_input_iterator(self):
        closed = []
        def stream():
            try:
                yield make_case()
                yield replace(make_case(), case_id='second')
            finally:
                closed.append(True)
        with tempfile.TemporaryDirectory() as directory, \
             patch('vivado_ip_test.application.main.iter_test_cases', return_value=stream()), \
             patch('vivado_ip_test.application.main.build_pipeline') as factory, \
             redirect_stderr(io.StringIO()):
            factory.return_value.validate.side_effect = ConfigError('invalid parameter')
            self.assertEqual(main(Path(directory), ['--limit', '1']), 2)
            self.assertEqual(closed, [True])
            factory.return_value.run.assert_not_called()

    def test_ip_filter_and_all_choose_extended_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = [make_case(), replace(make_case(), case_id="second", ip_type="counter")]
            for arguments, expected in ((["--ip-type", "counter"], "second"), (["--all"], make_case().case_id)):
                with patch("vivado_ip_test.application.main.iter_test_cases", return_value=(c for c in cases)) as loader, \
                     patch("vivado_ip_test.application.main.build_pipeline") as factory, \
                     redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(root, [*arguments, "--list-cases"]), 0)
                self.assertEqual(loader.call_args.args[0], root / "configs/extended_regression.json")
                self.assertIn(expected, output.getvalue())
                factory.return_value.run.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])

    def test_limit_is_applied_after_resuming_completed_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [replace(make_case(), case_id=name) for name in ("first", "second", "third")]
            with patch("vivado_ip_test.application.main.iter_test_cases", return_value=(c for c in cases)), \
                 patch("vivado_ip_test.application.main.load_completed_cases", return_value={'first': [cases[0]]}), \
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
            with patch("vivado_ip_test.application.main.iter_test_cases", return_value=(c for c in [make_case(), replace(make_case(), case_id="second")])), \
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
            with patch("vivado_ip_test.application.main.iter_test_cases", return_value=(c for c in [make_case()])), \
                 patch("vivado_ip_test.application.main.build_pipeline") as factory, \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(Path(directory), ["--list-cases"]), 0)
            self.assertIn(make_case().case_id, output.getvalue())
            factory.return_value.run.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])
