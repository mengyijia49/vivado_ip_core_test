import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.ilvector_logic.plugin import IlVectorLogicPlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class InlineVectorFailureDetectionTests(unittest.TestCase):
    def run_fault(self, mode, name):
        rows = [("0000000000000000","00000000"),("1000000000000000","10000000"),
                ("0000000010000000","10000000"),("0101010110101010","11111111"),
                ("1111111100000001","11111110"),("1111111111111111","00000000")]
        return run_cycle_fixture(self,IlVectorLogicPlugin,{"width":8,"operation":"xor"},rows,mode,name)

    def test_control(self):
        self.run_fault(0,"control")

    def test_lost_high_bit(self):
        self.run_fault(1,"high_lost")

    def test_wrong_operation(self):
        self.run_fault(2,"wrong_operation")

    def test_shifted_input(self):
        self.run_fault(3,"shifted_input")

    def test_unknown(self):
        _,paths = self.run_fault(4,"unknown")
        self.assertIn("X",paths["actual_output"].read_text())
