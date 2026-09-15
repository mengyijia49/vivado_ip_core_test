import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.ilconstant.plugin import IlConstantPlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class InlineConstantFailureDetectionTests(unittest.TestCase):
    def run_fault(self, mode, name):
        expected = "1" + "0"*4094 + "1"
        return run_cycle_fixture(self, IlConstantPlugin,
            {"width": 4096, "value": "0x8" + "0"*1022 + "1"}, [("", expected)]*64, mode, name)

    def test_control(self):
        self.run_fault(0, "control")

    def test_lost_high(self):
        self.run_fault(1, "lost_high")

    def test_late_change(self):
        result, paths = self.run_fault(2, "late_change")
        self.assertIn("cycle=10", result.output)
        self.assertEqual(len(paths["actual_output"].read_text().splitlines()), 11)

    def test_unknown(self):
        _, paths = self.run_fault(3, "unknown")
        self.assertIn("X", paths["actual_output"].read_text())
