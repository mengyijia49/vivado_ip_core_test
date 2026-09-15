import os
import unittest

from integration.ip.tmr_fixture import check_fixture


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class TmrVoterFailureDetectionTests(unittest.TestCase):
    def test_correct_control(self):
        check_fixture(self, "tmr_voter", "control", {"Discrete1": 3, "Discrete2": 5, "Discrete3": 6}, True)

    def test_wrong_vote_is_detected_even_when_flags_are_correct(self):
        check_fixture(self, "tmr_voter", "vote_error", {"Discrete1": 0xA5}, False)

    def test_missing_flags_are_detected_even_when_vote_is_correct(self):
        check_fixture(self, "tmr_voter", "compare_error", {"Discrete1": 0x5A}, False)
