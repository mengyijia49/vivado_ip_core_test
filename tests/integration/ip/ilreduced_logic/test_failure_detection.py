import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.ilreduced_logic.plugin import IlReducedLogicPlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class InlineReductionFailureDetectionTests(unittest.TestCase):
    def run_fault(self,mode,name):
        rows = [("00000000000000000","0"),("10000000000000000","1"),
                ("00000000000000001","1"),("10000000000000001","0"),
                ("11111111111111111","1"),("11111111111111110","0")]
        return run_cycle_fixture(self,IlReducedLogicPlugin,{"width":17,"operation":"xor"},rows,mode,name)

    def test_control(self):
        self.run_fault(0,"control")

    def test_lost_high_bit(self):
        self.run_fault(1,"high_lost")

    def test_wrong_operation(self):
        self.run_fault(2,"wrong_operation")

    def test_unknown(self):
        _,paths = self.run_fault(3,"unknown")
        self.assertIn("X",paths["actual_output"].read_text())
