import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.xlconstant.plugin import XlConstantPlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class ConstantFailureDetectionTests(unittest.TestCase):
    def run_fault(self, mode, name, *, malformed=False):
        word = "1" + "0" * 4094 + "1"
        return run_cycle_fixture(self, XlConstantPlugin, {"width": 4096, "value": "b" + word},
            [("1" if malformed else "", word)] * 64, mode, name, malformed=malformed)

    def test_control(self):
        self.run_fault(0, "control")

    def test_lost_high_bit(self):
        self.run_fault(1, "lost_high_bit")

    def test_lost_low_bit(self):
        self.run_fault(2, "lost_low_bit")

    def test_unknown_high_bit(self):
        self.run_fault(3, "unknown_high_bit")

    def test_later_output_change(self):
        result, paths = self.run_fault(4, "later_change")
        self.assertIn("cycle=10 ", result.output)
        self.assertEqual(len(paths["actual_output"].read_text().splitlines()), 11)

    def test_nonempty_input_row_is_rejected(self):
        self.run_fault(0, "unexpected_input", malformed=True)
