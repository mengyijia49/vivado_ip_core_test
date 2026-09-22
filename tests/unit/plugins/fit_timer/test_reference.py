from dataclasses import replace
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.fit_timer.reference import FitTimerPlan
from unit.plugins.cycle_helpers import plugin_case


class FitTimerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("fit_timer")

    def test_exact_and_tolerant_period_contracts(self):
        exact = FitTimerPlan.from_parameters(
            {"no_clocks": 1009, "inaccuracy": 0, "reset_active_high": True})
        tolerant = FitTimerPlan.from_parameters(
            {"no_clocks": 1009, "inaccuracy": 15, "reset_active_high": False})
        self.assertEqual((exact.minimum_period, exact.maximum_period), (1009, 1009))
        self.assertEqual((tolerant.minimum_period, tolerant.maximum_period), (994, 1024))
        self.assertFalse(tolerant.reset_active_high)

    def test_spec_matches_catalog_ports_parameters_and_revision(self):
        plan = FitTimerPlan.from_parameters(self.case.parameters)
        spec = self.plugin._backend.metadata_spec(plan)
        self.assertEqual([port.name for port in spec.inputs], ["Rst"])
        self.assertEqual([port.name for port in spec.outputs], ["Interrupt"])
        self.assertEqual(spec.clock, "Clk")
        self.assertEqual(spec.settings["C_NO_CLOCKS"], plan.no_clocks)
        self.assertEqual(spec.model_parameters["C_FAMILY"], "artix7")

    def test_shipped_case_and_validation_rules(self):
        self.plugin.validate_case(self.case)
        for parameters in (
            {"no_clocks": 2, "inaccuracy": 0, "reset_active_high": True},
            {"no_clocks": 3, "inaccuracy": 1000, "reset_active_high": True},
            {"no_clocks": 3, "inaccuracy": 0, "reset_active_high": 1},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(self.case, parameters=parameters))
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))

    def test_budget_and_coverage_contract_are_fixed(self):
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(
                self.case, verification=replace(self.case.verification, case_budget=2)))
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(
                self.case, verification=replace(
                    self.case.verification, coverage_targets=("period",))))


if __name__ == "__main__":
    unittest.main()
