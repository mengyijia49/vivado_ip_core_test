import os
import unittest

from integration.cycle_fixture import run_cycle_fixture
from integration.ip.fifo_generator.literal_trace import run_literal_trace
from integration.ip.fifo_generator.test_failure_detection import ROWS as FWFT_ROWS, MASKS as FWFT_MASKS
from vivado_ip_test.plugins.fifo_generator.plugin import FifoGeneratorPlugin


PARAMETERS = {"width": 8, "depth": 16, "memory_type": "Block_RAM", "active_low_flags": False,
              "dout_reset_value": 165, "read_mode": "standard", "data_count_width": 4,
              "prog_full_assert": 3, "prog_empty_assert": 2}
ROWS = (
    ("00000000001", "1010010100001100000001"),
    ("00100101100", "0000000000100100000101"),
    ("01001010100", "0000000000100000001001"),
    ("01101111100", "0000000000100000001101"),
    ("00000000000", "0000000000000000001110"),
    ("00000000010", "0010010100000010001010"),
    ("00000000010", "0100101000000110000101"),
    ("00000000010", "0110111100001110000001"),
    ("00000000010", "0000000000001101000001"),
    ("00000000001", "1010010100001100000001"),
)
MASKS = (
    "1111111111111111111111",
    "0000000011111111111111",
    "0000000011111111111111",
    "0000000011111111111111",
    "0000000011111111111111",
    "1111111111111111111111",
    "1111111111111111111111",
    "1111111111111111111111",
    "0000000011111111111111",
    "1111111111111111111111",
)


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class FifoStatusFailureDetectionTests(unittest.TestCase):
    def test_control_and_status_faults(self):
        for mode, name in enumerate(("control", "wrong_count", "early_full", "late_empty",
                                    "unknown_count", "late_count", "stale_reset_count")):
            with self.subTest(name=name):
                run_cycle_fixture(self, FifoGeneratorPlugin, PARAMETERS, ROWS, mode,
                                  "status_" + name, masks=MASKS, fixture_file="faulty_status.vhd")

    def test_real_standard_ip_matches_literal_status_trace(self):
        run_literal_trace(self, PARAMETERS, ROWS, MASKS, "standard_status_literal")

    def test_real_fwft_ip_counts_pending_first_words(self):
        parameters = {**PARAMETERS, "read_mode": "fwft", "data_count_width": 5,
                      "prog_full_assert": 5, "prog_empty_assert": 4}
        counts = ("00000", "00001", "00010", "00010", "00010", "00001", "00000", "00000")
        rows = tuple((stimulus, expected + count + "01")
                     for (stimulus, expected), count in zip(FWFT_ROWS, counts))
        masks = tuple(mask + "1111111" for mask in FWFT_MASKS)
        run_literal_trace(self, parameters, rows, masks, "fwft_status_literal")
