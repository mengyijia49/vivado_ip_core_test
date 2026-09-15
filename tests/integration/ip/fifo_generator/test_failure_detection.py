import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from integration.ip.fifo_generator.literal_trace import run_literal_trace
from vivado_ip_test.plugins.fifo_generator.plugin import FifoGeneratorPlugin


PARAMETERS = {"width": 8, "depth": 16, "memory_type": "Block_RAM", "active_low_flags": False,
              "dout_reset_value": 165, "read_mode": "fwft"}
# Input: din/wr_en/rd_en/srst. Output: dout and all eight flags, in declared order.
ROWS = tuple((stimulus, expected) for stimulus, expected in (
    ("00000000001", "1010010100001100"),
    ("00100101110", "0000000000101101"),
    ("01001010110", "0000000000101101"),
    ("00000000000", "0010010100000010"),
    ("00000000000", "0010010100000010"),
    ("00000000010", "0100101000000110"),
    ("00000000010", "0000000000001100"),
    ("00000000010", "0000000000001101")))
MASKS = ("1111111111111111", "0000000011111111", "0000000011111111", "1111111111111111",
         "1111111111111111", "1111111111111111", "0000000011111111", "0000000011111111")


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class FwftFailureDetectionTests(unittest.TestCase):
    def test_control_and_each_output_fault(self):
        for mode, name in enumerate(("control", "wrong_data", "early_valid", "unstable_hold", "full",
                "almost_full", "wr_ack", "overflow", "empty", "almost_empty", "underflow", "unknown_data")):
            with self.subTest(mode=mode, name=name):
                result, paths = run_cycle_fixture(self, FifoGeneratorPlugin, PARAMETERS, ROWS, mode,
                                                  "fwft_" + name, masks=MASKS)
                if mode == 0:
                    self.assertIn("X", paths["actual_output"].read_text())
                elif mode == 11:
                    self.assertIn("X", result.output)

    def test_real_ip_matches_literal_trace_without_python_reference(self):
        run_literal_trace(self, PARAMETERS, ROWS, MASKS, "fwft_literal")
