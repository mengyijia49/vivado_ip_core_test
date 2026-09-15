import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from vivado_ip_test.plugins.xlslice.plugin import XlSlicePlugin


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class SliceFailureDetectionTests(unittest.TestCase):
    def run_fault(self, mode, name):
        words = [(0x00, 0x0), (0x04, 0x1), (0x08, 0x2), (0x10, 0x4), (0x20, 0x8),
                 (0x3c, 0xf), (0xc3, 0x0), (0x55, 0x5), (0xaa, 0xa), (0xff, 0xf)]
        rows = [(f"{data:08b}", f"{expected:04b}") for data, expected in words]
        return run_cycle_fixture(self, XlSlicePlugin, {"input_width": 8, "high_bit": 5, "low_bit": 2},
                                 rows, mode, name)

    def test_control(self):
        self.run_fault(0, "control")

    def test_off_by_one(self):
        self.run_fault(1, "off_by_one")

    def test_reversed_bits(self):
        self.run_fault(2, "reversed_bits")

    def test_unselected_bit_leak(self):
        self.run_fault(3, "unselected_bit_leak")

    def test_unknown(self):
        self.run_fault(4, "unknown")

    def test_stuck_bit(self):
        self.run_fault(5, "stuck_bit")
