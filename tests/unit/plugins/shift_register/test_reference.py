import unittest

from unit.plugins.cycle_helpers import plugin_case


class ShiftReferenceTests(unittest.TestCase):
    def test_depth_and_enable_preserve_order(self):
        plugin, case = plugin_case("shift_register")
        spec = plugin.describe({"width": 8, "depth": 3, "clock_enable": True})
        model = spec.model_factory()
        rows = [{"D": 7}, {"D": 8}, {"D": 9, "CE": 0}, {"D": 10}, {"D": 11}]
        self.assertEqual([model.step(spec.frame(row))["Q"] for row in rows], [0, 0, 0, 7, 8])

    def test_depth_one_and_complete_flush(self):
        plugin, case = plugin_case("shift_register")
        spec = plugin.describe({"width": 1, "depth": 1, "clock_enable": False})
        self.assertEqual(spec.model_factory().step({"D": 1}), {"Q": 1})
        self.assertEqual(plugin.describe(case.parameters).flush_cycles, 17)
