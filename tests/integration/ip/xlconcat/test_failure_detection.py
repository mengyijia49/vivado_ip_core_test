import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.xlconcat.plugin import XlConcatPlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class ConcatFailureDetectionTests(unittest.TestCase):
    def test_extra_input_bit_is_rejected(self):
        run_cycle_fixture(self, XlConcatPlugin, {"input_widths": [1, 3, 4]},
            [("000000000", "00000000")], 0, "extra_input", expected_error="binary row width")

    def test_nonbinary_input_is_rejected(self):
        run_cycle_fixture(self, XlConcatPlugin, {"input_widths": [1, 3, 4]},
            [("0000000X", "00000000")], 0, "nonbinary_input", expected_error="nonbinary row")

    def test_extra_expected_bit_is_rejected(self):
        run_cycle_fixture(self, XlConcatPlugin, {"input_widths": [1, 3, 4]},
            [("00000000", "000000000")], 0, "extra_expected", expected_error="binary row width")

    def test_nonbinary_expected_is_rejected(self):
        run_cycle_fixture(self, XlConcatPlugin, {"input_widths": [1, 3, 4]},
            [("00000000", "0000000X")], 0, "nonbinary_expected", expected_error="nonbinary row")

    def run_fault(self, mode, name):
        rows = [("00000000", "00000000"), ("10000000", "00000001"),
                ("00100000", "00000100"), ("10101010", "10100101"),
                ("01010011", "00111010"), ("00001000", "10000000"),
                ("11111111", "11111111")]
        return run_cycle_fixture(self, XlConcatPlugin, {"input_widths": [1, 3, 4]}, rows, mode, name)

    def test_control(self):
        self.run_fault(0, "control")

    def test_reversed_ports(self):
        self.run_fault(1, "reversed_ports")

    def test_cross_port_bit_swap(self):
        self.run_fault(2, "bit_swap")

    def test_lost_high_bit(self):
        self.run_fault(3, "lost_high_bit")

    def test_unknown(self):
        result, paths = self.run_fault(4, "unknown")
        self.assertIn("X", paths["actual_output"].read_text())

    def test_missing_partial_lane(self):
        self.run_fault(5, "missing_lane")
