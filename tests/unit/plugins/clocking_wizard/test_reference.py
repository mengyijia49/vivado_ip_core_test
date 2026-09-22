import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.clocking_wizard.reference import ClockPlan


class ClockPlanTests(unittest.TestCase):
    def test_exact_periods_and_reset_polarity(self):
        plan = ClockPlan.from_parameters({"input_frequency_mhz": 100,
                                          "output_frequency_mhz": 125,
                                          "primitive": "MMCM",
                                          "reset_active_high": False})
        self.assertEqual(plan.input_half_period_ps, 5000)
        self.assertEqual(plan.output_period_ps, 8000)
        self.assertEqual(plan.output_high_ps, 4000)
        self.assertFalse(plan.reset_active_high)

    def test_non_integral_picosecond_plan_is_rejected(self):
        with self.assertRaises(PluginError):
            ClockPlan.from_parameters({"input_frequency_mhz": 99,
                                       "output_frequency_mhz": 50,
                                       "primitive": "MMCM",
                                       "reset_active_high": True})
