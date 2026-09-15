import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.ilslice.plugin import IlSlicePlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class InlineSliceFailureDetectionTests(unittest.TestCase):
    def run_fault(self, mode, name):
        rows = [("00000000", "0000"), ("00000100", "0001"), ("00100000", "1000"),
                ("10000000", "0000"), ("01000000", "0000"), ("11111111", "1111")]
        return run_cycle_fixture(self, IlSlicePlugin,
            {"input_width": 8, "high_bit": 5, "low_bit": 2}, rows, mode, name)

    def test_control(self):
        self.run_fault(0, "control")

    def test_wrong_offset(self):
        self.run_fault(1, "wrong_offset")

    def test_leaked_high(self):
        self.run_fault(2, "leaked_high")

    def test_unknown(self):
        _, paths = self.run_fault(3, "unknown")
        self.assertIn("X", paths["actual_output"].read_text())
