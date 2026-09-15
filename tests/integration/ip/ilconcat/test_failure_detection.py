import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.ilconcat.plugin import IlConcatPlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class InlineConcatFailureDetectionTests(unittest.TestCase):
    def run_fault(self, mode, name):
        rows = [("00000000", "00000000"), ("10000000", "00000001"),
                ("00100000", "00000100"), ("10101010", "10100101"),
                ("01010011", "00111010"), ("00001000", "10000000"),
                ("11111111", "11111111")]
        return run_cycle_fixture(self, IlConcatPlugin, {"input_widths": [1,3,4]}, rows, mode, name)

    def test_control(self):
        self.run_fault(0, "control")

    def test_reversed_ports(self):
        self.run_fault(1, "reversed_ports")

    def test_lost_high(self):
        self.run_fault(2, "lost_high")

    def test_unknown(self):
        _, paths = self.run_fault(3, "unknown")
        self.assertIn("X", paths["actual_output"].read_text())
