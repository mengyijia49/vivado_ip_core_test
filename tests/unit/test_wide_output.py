from pathlib import Path
import tempfile
import unittest

from vivado_ip_test.infrastructure.output import first_output_difference


class WideOutputTests(unittest.TestCase):
    def test_wide_unmasked_rows_still_detect_one_wrong_bit(self):
        with tempfile.TemporaryDirectory() as directory:
            expected, actual = (Path(directory) / name for name in ("expected", "actual"))
            row = "01" * 75000
            expected.write_text(row + "\n" + row + "\n")
            actual.write_bytes(expected.read_bytes())
            self.assertIsNone(first_output_difference(expected, actual))
            actual.write_text(row + "\n" + row[:-1] + "0\n")
            difference = first_output_difference(expected, actual)
            self.assertEqual(difference["kind"], "value_mismatch")
            self.assertEqual(difference["output_index"], 1)

    def test_equal_invalid_rows_do_not_take_the_fast_path(self):
        with tempfile.TemporaryDirectory() as directory:
            expected, actual = (Path(directory) / name for name in ("expected", "actual"))
            for text in ("\n", "01X\n", "01 1\n", "01q\n"):
                expected.write_text(text)
                actual.write_text(text)
                self.assertEqual(first_output_difference(expected, actual)["kind"], "invalid_expected_output")
