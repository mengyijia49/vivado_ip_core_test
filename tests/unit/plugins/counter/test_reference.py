import unittest

from unit.plugins.cycle_helpers import plugin_case


class CounterReferenceTests(unittest.TestCase):
    def test_load_wrap_direction_hold_and_clear(self):
        plugin, case = plugin_case("counter")
        spec = plugin.describe(case.parameters)
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"L": 255, "LOAD": 1})), {"Q": 255})
        self.assertEqual(model.step(spec.frame()), {"Q": 2})
        self.assertEqual(model.step(spec.frame({"UP": 0})), {"Q": 255})
        self.assertEqual(model.step(spec.frame({"CE": 0, "LOAD": 1})), {"Q": 255})
        self.assertEqual(model.step(spec.frame({"CE": 0, "SCLR": 1})), {"Q": 0})

    def test_ce_overrides_reset_is_explicit(self):
        plugin, case = plugin_case("counter")
        spec = plugin.describe({**case.parameters, "ce_overrides_reset": True})
        model = spec.model_factory()
        model.step(spec.frame({"L": 7, "LOAD": 1}))
        self.assertEqual(model.step(spec.frame({"CE": 0, "SCLR": 1})), {"Q": 7})
