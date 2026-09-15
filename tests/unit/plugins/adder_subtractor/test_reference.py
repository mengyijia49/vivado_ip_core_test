import unittest

from unit.plugins.cycle_helpers import plugin_case


class AdderReferenceTests(unittest.TestCase):
    def test_mixed_sign_subtraction_hold_and_clear(self):
        plugin, case = plugin_case("adder_subtractor")
        spec = plugin.describe(case.parameters)
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"A": 255, "B": 15})), {"S": 254})
        self.assertEqual(model.step(spec.frame({"A": 0, "B": 15, "ADD": 0})), {"S": 1})
        self.assertEqual(model.step(spec.frame({"CE": 0})), {"S": 1})
        self.assertEqual(model.step(spec.frame({"CE": 0, "SCLR": 1})), {"S": 0})

    def test_combinational_truncation_and_reset_priority(self):
        plugin, case = plugin_case("adder_subtractor")
        p = {**case.parameters, "a_width": 8, "b_width": 8, "output_width": 8,
             "a_type": "Unsigned", "b_type": "Unsigned", "latency": 0,
             "clock_enable": False, "sync_clear": False}
        spec = plugin.describe(p)
        self.assertEqual(spec.model_factory().step(spec.frame({"A": 255, "B": 2})), {"S": 1})
        spec = plugin.describe({**case.parameters, "ce_overrides_reset": True})
        model = spec.model_factory()
        model.step(spec.frame({"A": 3}))
        self.assertEqual(model.step(spec.frame({"SCLR": 1, "CE": 0})), {"S": 3})
