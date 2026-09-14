import tempfile
import unittest
from pathlib import Path

from vivado_ip_test.plugins.divider.verification import output_files_match


class DividerVerificationTests(unittest.TestCase):
    def test_accepts_identical_nonempty_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = Path(temp_dir) / "expected.txt"
            actual = Path(temp_dir) / "actual.txt"
            expected.write_text("0011\n1010\n")
            actual.write_text("0011\n1010\n")

            self.assertTrue(output_files_match(expected, actual))

    def test_rejects_intentionally_corrupted_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = Path(temp_dir) / "expected.txt"
            actual = Path(temp_dir) / "actual.txt"
            expected.write_text("0011\n1010\n")
            actual.write_text("0011\n1011\n")

            self.assertFalse(output_files_match(expected, actual))

    def test_rejects_missing_or_empty_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = Path(temp_dir) / "expected.txt"
            actual = Path(temp_dir) / "actual.txt"
            expected.write_text("")
            actual.write_text("")

            self.assertFalse(output_files_match(expected, actual))
