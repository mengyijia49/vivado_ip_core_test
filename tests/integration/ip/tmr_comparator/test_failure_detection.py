import os
import unittest

from integration.ip.tmr_fixture import check_fixture


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class TmrComparatorFailureDetectionTests(unittest.TestCase):
    def test_correct_control(self):
        check_fixture(self, "tmr_comparator", "control", {"Discrete": 1}, True)

    def test_missing_voter_error_flag_is_detected(self):
        check_fixture(self, "tmr_comparator", "voter_error", {"Discrete": 0x80}, False)
