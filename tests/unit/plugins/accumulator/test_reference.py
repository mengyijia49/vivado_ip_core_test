import unittest

from unit.plugins.cycle_helpers import plugin_case


class AccumulatorReferenceTests(unittest.TestCase):
    def test_signed_accumulation_load_hold_and_reset(self):
        plugin, case = plugin_case("accumulator")
        spec = plugin.describe(case.parameters)
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"B": 255})), {"Q": 65535})
        self.assertEqual(model.step(spec.frame({"B": 2})), {"Q": 1})
        self.assertEqual(model.step(spec.frame({"B": 2, "ADD": 0})), {"Q": 65535})
        self.assertEqual(model.step(spec.frame({"B": 7, "BYPASS": 1})), {"Q": 7})
        self.assertEqual(model.step(spec.frame({"B": 9, "CE": 0})), {"Q": 7})
        self.assertEqual(model.step(spec.frame({"CE": 0, "SCLR": 1})), {"Q": 0})

    def test_unsigned_wrap_and_state_are_not_stateless_products(self):
        plugin, case = plugin_case("accumulator")
        spec = plugin.describe({**case.parameters, "input_type": "Unsigned", "output_width": 8})
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"B": 255})), {"Q": 255})
        self.assertEqual(model.step(spec.frame({"B": 2})), {"Q": 1})

    def test_ce_stall_interpretation_is_not_changed_to_match_observed_bypass(self):
        plugin, case = plugin_case("accumulator")
        spec = plugin.describe(case.parameters)
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"B": 1, "BYPASS": 1})), {"Q": 1})
        self.assertEqual(model.step(spec.frame({"B": 0, "BYPASS": 1, "CE": 0})), {"Q": 1})
